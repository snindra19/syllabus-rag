"""pgvector operations: insert and similarity search."""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def insert_chunk(
    db: AsyncSession,
    syllabus_id: int,
    section_header: str,
    content: str,
    embedding: list[float],
    is_asu_boilerplate: bool = False,
) -> int:
    """Insert a chunk with its embedding. Returns the new chunk id."""
    result = await db.execute(
        text(
            """
            INSERT INTO chunks (syllabus_id, section_header, content, embedding, is_asu_boilerplate)
            VALUES (:syllabus_id, :section_header, :content, CAST(:embedding AS vector), :is_asu_boilerplate)
            RETURNING id
            """
        ),
        {
            "syllabus_id": syllabus_id,
            "section_header": section_header,
            "content": content,
            "embedding": str(embedding),
            "is_asu_boilerplate": is_asu_boilerplate,
        },
    )
    await db.commit()
    return result.scalar_one()


async def vector_search(
    db: AsyncSession,
    query_embedding: list[float],
    syllabus_ids: list[int] | None,
    top_k: int = 15,
) -> list[dict[str, Any]]:
    """
    Return the top_k most similar chunks by cosine distance.

    Optionally filter to specific syllabus IDs.
    """
    filter_clause = "AND c.syllabus_id = ANY(:ids)" if syllabus_ids else ""
    rows = await db.execute(
        text(
            f"""
            SELECT c.id, c.syllabus_id, c.section_header, c.content,
                   s.course_code, s.course_title,
                   1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
            FROM chunks c
            JOIN syllabi s ON s.id = c.syllabus_id
            WHERE 1=1 {filter_clause}
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
            """
        ),
        {"embedding": str(query_embedding), "ids": syllabus_ids, "top_k": top_k},
    )
    return [dict(row._mapping) for row in rows]
