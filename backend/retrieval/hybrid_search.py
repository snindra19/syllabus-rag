"""Combine vector similarity and PostgreSQL full-text search (RRF fusion)."""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from retrieval.embeddings import embed_query
from retrieval.vector_store import vector_search

logger = logging.getLogger(__name__)

_RRF_K = 60  # Reciprocal Rank Fusion constant


async def hybrid_search(
    db: AsyncSession,
    query: str,
    syllabus_ids: list[int] | None = None,
    top_k: int = 15,
) -> list[dict[str, Any]]:
    """
    Merge vector cosine-similarity results with PostgreSQL full-text search using RRF.

    Vector search uses the IVFFlat index via CAST(:embedding AS vector).
    FTS uses the pre-built content_tsv GIN index (populated by DB trigger on insert).

    Returns up to top_k de-duplicated chunks ranked by combined RRF score.
    """
    query_embedding = await embed_query(query)

    # --- Vector search ---
    vec_results = await vector_search(db, query_embedding, syllabus_ids, top_k=top_k)

    # --- Full-text search (uses ix_chunks_content_tsv GIN index) ---
    filter_clause = "AND c.syllabus_id = ANY(:ids)" if syllabus_ids else ""
    fts_rows = await db.execute(
        text(
            f"""
            SELECT c.id, c.syllabus_id, c.section_header, c.content,
                   s.course_code, s.course_title,
                   ts_rank_cd(c.content_tsv, query) AS score
            FROM chunks c
            JOIN syllabi s ON s.id = c.syllabus_id,
                 plainto_tsquery('english', :query) AS query
            WHERE c.content_tsv @@ query
              {filter_clause}
            ORDER BY score DESC
            LIMIT :top_k
            """
        ),
        {"query": query, "ids": syllabus_ids, "top_k": top_k},
    )
    fts_results = [dict(row._mapping) for row in fts_rows]

    logger.debug(
        "Hybrid search: %d vector hits, %d FTS hits for query=%r",
        len(vec_results),
        len(fts_results),
        query[:60],
    )

    # --- RRF fusion ---
    scores: dict[int, float] = {}
    chunks_by_id: dict[int, dict] = {}

    for rank, row in enumerate(vec_results):
        cid = row["id"]
        scores[cid] = scores.get(cid, 0) + 1 / (_RRF_K + rank + 1)
        chunks_by_id[cid] = row

    for rank, row in enumerate(fts_results):
        cid = row["id"]
        scores[cid] = scores.get(cid, 0) + 1 / (_RRF_K + rank + 1)
        chunks_by_id[cid] = row

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [chunks_by_id[cid] for cid, _ in ranked]
