"""Cross-encoder reranking with ms-marco-MiniLM-L6-v2."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"
_reranker: "CrossEncoder | None" = None


def _get_reranker() -> "CrossEncoder":
    """Lazy-load the cross-encoder model (downloads on first call)."""
    from sentence_transformers import CrossEncoder  # noqa: PLC0415 — intentional lazy import

    global _reranker
    if _reranker is None:
        logger.info("Loading cross-encoder model: %s", _MODEL_NAME)
        _reranker = CrossEncoder(_MODEL_NAME)
    return _reranker


def rerank(query: str, chunks: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    """
    Score each chunk against the query and return the top_k highest-scoring chunks.

    Sync — CPU-bound. Call via rerank_async from async contexts.
    Input chunks must have a 'content' key.
    """
    if not chunks:
        return []

    model = _get_reranker()
    pairs = [(query, chunk["content"]) for chunk in chunks]
    scores = model.predict(pairs)

    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in ranked[:top_k]]


async def rerank_async(
    query: str, chunks: list[dict[str, Any]], top_k: int = 5
) -> list[dict[str, Any]]:
    """Async wrapper — runs the cross-encoder in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(rerank, query, chunks, top_k)
