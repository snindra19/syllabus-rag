"""Raw text extraction from PDF and DOCX files."""

import subprocess
import tempfile
from pathlib import Path

import fitz  # pymupdf


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from a PDF using pymupdf."""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        pages = [page.get_text() for page in doc]
    return "\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract raw text from a DOCX file using pandoc."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    result = subprocess.run(
        ["pandoc", str(tmp_path), "-t", "plain", "--wrap=none"],
        capture_output=True,
        text=True,
        check=True,
    )
    tmp_path.unlink(missing_ok=True)
    return result.stdout


def extract_raw_text(filename: str, file_bytes: bytes) -> str:
    """Dispatch to the correct parser based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    if ext in {".docx", ".doc"}:
        return extract_text_from_docx(file_bytes)
    raise ValueError(f"Unsupported file type: {ext}")
