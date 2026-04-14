"""Chat endpoint — streaming grounded answers from Claude Haiku."""

import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from chat.prompt_builder import _SYSTEM_PROMPT, build_messages
from config import settings
from db.database import get_db
from models.schemas import ChatRequest
from retrieval.hybrid_search import hybrid_search
from retrieval.reranker import rerank_async

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

_NO_INFO_MSG = "I don't have that information in the uploaded syllabi."
_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _stream_claude(messages: list[dict], system: str) -> Iterator[str]:
    """
    Sync generator that streams tokens from Claude Haiku.

    Called inside a thread by StreamingResponse (FastAPI runs sync iterables
    in a thread pool automatically). Usage is logged after the stream closes.
    """
    with _client.messages.stream(
        model=settings.chat_model,
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for token in stream.text_stream:
            yield token
        # Capture usage while the stream context is still open
        final_msg = stream.get_final_message()

    logger.info(
        "Chat LLM: input=%d output=%d tokens (model=%s)",
        final_msg.usage.input_tokens,
        final_msg.usage.output_tokens,
        settings.chat_model,
    )


async def _no_info_stream() -> AsyncIterator[str]:
    """Yield the no-information message without calling the LLM."""
    yield _NO_INFO_MSG


@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream a grounded answer from Claude Haiku.

    Pipeline:
    1. Embed query → hybrid search (vector cosine + FTS RRF fusion) → top 15 chunks
    2. Cross-encoder rerank (thread) → top 5 chunks
    3. Build context block with numbered citations
    4. Stream Claude Haiku response
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # --- Retrieval strategy ---
    # When specific syllabi are selected, retrieve independently per syllabus (4 chunks each)
    # then rerank the merged pool. This guarantees every selected course gets representation —
    # global top-k pooling would let high-scoring syllabi crowd out others entirely.
    #
    # When all syllabi are searched (no filter), use global retrieval scaled to syllabus count.
    if request.syllabus_ids:
        # Per-syllabus retrieval — no global reranking.
        #
        # The cross-encoder (ms-marco-MiniLM-L6-v2) is trained on web passages and
        # scores structured markdown tables (grade breakdowns, schedules) poorly
        # relative to prose chunks. When reranking per-syllabus candidates it
        # consistently deprioritises grading tables in favour of prose sections.
        #
        # The hybrid search RRF score (vector cosine + FTS) is a reliable enough
        # relevance signal within a single syllabus. Taking the top 3 RRF-ranked
        # chunks per selected syllabus guarantees grading/content sections reach
        # the LLM without cross-encoder interference.
        seen: set[int] = set()
        top_chunks: list[dict[str, Any]] = []
        for sid in request.syllabus_ids:
            # Hybrid search for general relevance
            for chunk in await hybrid_search(db, request.message, [sid], top_k=3):
                if chunk["id"] not in seen:
                    seen.add(chunk["id"])
                    top_chunks.append(chunk)
            # Guaranteed inclusion: fetch grading/exam chunks by section header.
            # Vector similarity can't reliably surface short structured tables
            # (grade breakdowns) when the query contains many unrelated keywords.
            # A direct lookup by header name ensures these are always in context.
            grade_rows = await db.execute(
                text("""
                    SELECT c.id, c.syllabus_id, c.section_header, c.content,
                           s.course_code, s.course_title
                    FROM chunks c
                    JOIN syllabi s ON s.id = c.syllabus_id
                    WHERE c.syllabus_id = :sid
                      AND c.section_header ILIKE ANY(ARRAY[
                            '%grade breakdown%', '%grade scale%',
                            '%grading%', '%exam mode%'
                          ])
                    ORDER BY c.id
                    LIMIT 4
                """),
                {"sid": sid},
            )
            for row in grade_rows:
                chunk = dict(row._mapping)
                if chunk["id"] not in seen:
                    seen.add(chunk["id"])
                    top_chunks.append(chunk)
    else:
        # Global retrieval + reranking scaled to total syllabus count
        result = await db.execute(text("SELECT COUNT(*) FROM syllabi"))
        n_syllabi = result.scalar_one() or 1
        retrieval_k = max(15, n_syllabi * 4)
        rerank_k = max(5, n_syllabi * 2)
        candidates = await hybrid_search(db, request.message, None, top_k=retrieval_k)
        top_chunks = await rerank_async(request.message, candidates, top_k=rerank_k)

    logger.info(
        "Returning %d chunks to LLM for query=%r",
        len(top_chunks),
        request.message[:60],
    )

    # No relevant content found — return the no-info message without an LLM call
    if not top_chunks:
        return StreamingResponse(_no_info_stream(), media_type="text/plain; charset=utf-8")

    # Steps 3 + 4: build prompt and stream
    messages = build_messages(request.message, top_chunks)
    return StreamingResponse(
        _stream_claude(messages, _SYSTEM_PROMPT),
        media_type="text/plain; charset=utf-8",
    )
