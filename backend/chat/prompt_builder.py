"""Assemble the system prompt and context block for the chat LLM call."""

from typing import Any

_SYSTEM_PROMPT = """\
You are a helpful course assistant for ASU students. You answer questions \
strictly based on the syllabus content provided in the context below.

Rules:
- Only use information from the provided context.
- If the context does not contain the answer, respond exactly: \
  "I don't have that information in the uploaded syllabi."
- Always cite the course and section (e.g., "[CSE 110 — Grading Policies]") \
  at the end of each factual statement.
- Never fabricate policies, dates, percentages, or contact information.
"""


def build_context_block(chunks: list[dict[str, Any]]) -> str:
    """Format retrieved chunks into a numbered context block."""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        course = chunk.get("course_code") or "Unknown Course"
        header = chunk.get("section_header") or "Unknown Section"
        content = chunk.get("content", "")
        parts.append(f"[{i}] {course} — {header}\n{content}")
    return "\n\n---\n\n".join(parts)


def build_messages(user_query: str, chunks: list[dict[str, Any]]) -> list[dict]:
    """Return the messages list to pass to the Claude API."""
    context = build_context_block(chunks)
    user_content = f"Context from uploaded syllabi:\n\n{context}\n\nQuestion: {user_query}"
    return [{"role": "user", "content": user_content}]
