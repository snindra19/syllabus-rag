"""/upload endpoint — full ingestion pipeline."""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import Syllabus
from ingestion.chunker import chunk_markdown
from ingestion.file_parser import extract_raw_text
from ingestion.llm_preprocessor import preprocess_syllabus
from models.schemas import SyllabusMeta, SyllabusUploadResponse
from retrieval.embeddings import embed_texts

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
_DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
_RAW_DIR = _DATA_ROOT / "raw_uploads"
_MD_DIR = _DATA_ROOT / "processed_markdown"

# Headers that are ASU boilerplate shared across all syllabi
_BOILERPLATE_HEADERS = {"ASU-Wide Policies", "Academic Integrity"}


def _parse_course_info(markdown: str) -> tuple[str | None, str | None]:
    """
    Extract course_code and course_title from the processed markdown.

    Looks for the '**Course Code & Title**' line produced by SYLLABUS_TEMPLATE.md.
    Returns (course_code, course_title), both may be None if not found or not specified.
    """
    match = re.search(
        r"\*\*Course Code.*?Title\*\*\s*[:\-–—]?\s*(.+)",
        markdown,
        re.IGNORECASE,
    )
    if not match:
        return None, None

    raw = match.group(1).strip()
    if not raw or raw.lower().startswith("not specified"):
        return None, None

    # Try explicit separator first: "CSE 110: Intro" / "CSE 110 - Intro" / "CSE 110 – Intro"
    parts = re.split(r"\s*[:\-–—]\s*", raw, maxsplit=1)
    if len(parts) == 1:
        # No separator — try to split after the course-code token (LETTERS DIGITS)
        # e.g. "CSE 564 Software Design" → code="CSE 564", title="Software Design"
        m = re.match(r'^([A-Z]{2,4}\s+\d{3}[A-Z]?)\s+(.+)$', raw)
        if m:
            parts = [m.group(1), m.group(2)]
    code = parts[0].strip() or None
    title = parts[1].strip() if len(parts) > 1 else None
    return code, title


@router.post("/upload", response_model=SyllabusUploadResponse, status_code=201)
async def upload_syllabus(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> SyllabusUploadResponse:
    """
    Ingest a syllabus PDF or DOCX through the full RAG pipeline:

    1. Extract raw text (pymupdf for PDF, pandoc for DOCX)
    2. Claude Haiku → structured markdown (SYLLABUS_TEMPLATE.md prompt)
    3. Chunk markdown at ## / ### headers with 50-token overlap
    4. OpenAI text-embedding-3-small → 1536-dim vectors
    5. Persist syllabus row + all chunk rows to PostgreSQL
    """
    # --- Validate ---
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload a PDF or DOCX file.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- Save raw file ---
    uid = uuid.uuid4().hex[:8]
    safe_name = f"{uid}_{filename}"
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    (_RAW_DIR / safe_name).write_bytes(file_bytes)

    # --- Step 1: extract raw text (sync I/O — run in thread) ---
    try:
        raw_text: str = await asyncio.to_thread(extract_raw_text, filename, file_bytes)
    except Exception as exc:
        logger.exception("File parsing failed for '%s'", filename)
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}") from exc

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the file. Is the PDF scanned/image-only?",
        )

    # --- Step 2: LLM preprocessing (sync network — run in thread) ---
    try:
        processed_markdown, llm_usage = await asyncio.to_thread(preprocess_syllabus, raw_text)
    except Exception as exc:
        logger.exception("LLM preprocessing failed for '%s'", filename)
        raise HTTPException(status_code=502, detail=f"LLM preprocessing failed: {exc}") from exc

    # Save processed markdown to disk for auditing
    _MD_DIR.mkdir(parents=True, exist_ok=True)
    md_filename = f"{uid}_{Path(filename).stem}.md"
    (_MD_DIR / md_filename).write_text(processed_markdown, encoding="utf-8")

    # --- Step 3: chunk ---
    raw_chunks = chunk_markdown(processed_markdown)
    # Drop sections with no body text (e.g. "Not specified in syllabus" placeholders are fine,
    # but truly empty content would cause the embedding API to error)
    chunks = [c for c in raw_chunks if c["content"].strip()]
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Processed markdown produced no chunks. The file may be unreadable.",
        )

    # --- Step 4: embed all chunk texts in one API call ---
    try:
        texts = [c["content"] for c in chunks]
        embeddings = await embed_texts(texts)
    except Exception as exc:
        logger.exception("Embedding generation failed")
        raise HTTPException(status_code=502, detail=f"Embedding failed: {exc}") from exc

    # --- Step 5: persist to DB in a single transaction ---
    course_code, course_title = _parse_course_info(processed_markdown)

    syllabus = Syllabus(
        filename=filename,
        course_code=course_code,
        course_title=course_title,
        upload_date=datetime.now(timezone.utc),
        raw_text=raw_text,
        processed_markdown=processed_markdown,
        metadata_={
            "raw_file": safe_name,
            "md_file": md_filename,
            "chunk_count": len(chunks),
            "raw_chars": len(raw_text),
            "processed_chars": len(processed_markdown),
            "llm_usage": llm_usage,
        },
    )
    db.add(syllabus)
    await db.flush()  # assigns syllabus.id without committing

    # Use raw SQL with CAST(:embedding AS vector) to stay on text protocol.
    # Registering the asyncpg binary codec conflicts with pgvector.sqlalchemy's
    # bind_processor (double-encoding), so explicit CAST is the reliable path.
    chunk_params = [
        {
            "syllabus_id": syllabus.id,
            "section_header": c["section_header"],
            "content": c["content"],
            "embedding": str(embeddings[i]),
            "is_asu_boilerplate": c["section_header"] in _BOILERPLATE_HEADERS,
        }
        for i, c in enumerate(chunks)
    ]
    await db.execute(
        text(
            """
            INSERT INTO chunks (syllabus_id, section_header, content, embedding, is_asu_boilerplate)
            VALUES (:syllabus_id, :section_header, :content, CAST(:embedding AS vector), :is_asu_boilerplate)
            """
        ),
        chunk_params,
    )
    await db.commit()

    logger.info(
        "Ingested '%s' → syllabus_id=%d, %d chunks, course_code='%s'",
        filename,
        syllabus.id,
        len(chunks),
        course_code,
    )

    return SyllabusUploadResponse(
        syllabus_id=syllabus.id,
        filename=filename,
        course_code=course_code,
        course_title=course_title,
        message=f"Successfully ingested {len(chunks)} chunks.",
    )


@router.get("/syllabi", response_model=list[SyllabusMeta])
async def list_syllabi(db: AsyncSession = Depends(get_db)) -> list[SyllabusMeta]:
    """Return all uploaded syllabi ordered by most-recent first."""
    result = await db.execute(
        select(
            Syllabus.id,
            Syllabus.filename,
            Syllabus.course_code,
            Syllabus.course_title,
            Syllabus.upload_date,
            Syllabus.metadata_,
        ).order_by(Syllabus.upload_date.desc())
    )
    rows = result.all()
    return [
        SyllabusMeta(
            id=row.id,
            filename=row.filename,
            course_code=row.course_code,
            course_title=row.course_title,
            upload_date=row.upload_date,
            metadata=row.metadata_,
        )
        for row in rows
    ]


@router.delete("/syllabi/{syllabus_id}", status_code=204)
async def delete_syllabus(
    syllabus_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a syllabus and all its chunks (FK cascade handles chunks).

    Also removes the raw upload and processed markdown files from disk if present.
    """
    result = await db.execute(select(Syllabus).where(Syllabus.id == syllabus_id))
    syllabus = result.scalar_one_or_none()
    if syllabus is None:
        raise HTTPException(status_code=404, detail=f"Syllabus {syllabus_id} not found.")

    # Remove files from disk (best-effort — don't fail the request if missing)
    meta = syllabus.metadata_ or {}
    for key, base_dir in (("raw_file", _RAW_DIR), ("md_file", _MD_DIR)):
        fname = meta.get(key)
        if fname:
            path = base_dir / fname
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not delete file %s", path)

    await db.delete(syllabus)
    await db.commit()
    logger.info("Deleted syllabus id=%d ('%s')", syllabus_id, syllabus.filename)
