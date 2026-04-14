"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SyllabusUploadResponse(BaseModel):
    """Returned after a syllabus file is successfully ingested."""

    syllabus_id: int
    filename: str
    course_code: str | None
    course_title: str | None
    message: str


class ChatRequest(BaseModel):
    """Incoming chat message."""

    message: str
    syllabus_ids: list[int] | None = None  # None = search all uploaded syllabi


class ChatSource(BaseModel):
    """Citation attached to a chat answer."""

    syllabus_id: int
    course_code: str | None
    section_header: str
    excerpt: str


class ChatResponse(BaseModel):
    """Full (non-streaming) chat response."""

    answer: str
    sources: list[ChatSource]


class SyllabusMeta(BaseModel):
    """Summary row for the syllabus list UI."""

    id: int
    filename: str
    course_code: str | None
    course_title: str | None
    upload_date: datetime
    metadata: dict[str, Any]
