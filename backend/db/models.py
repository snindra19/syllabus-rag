"""SQLAlchemy ORM models for syllabi and chunks tables."""

from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base

_EMBEDDING_DIM = 1536  # text-embedding-3-small


class Syllabus(Base):
    """One row per uploaded syllabus file."""

    __tablename__ = "syllabi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    course_code: Mapped[str | None] = mapped_column(Text)
    course_title: Mapped[str | None] = mapped_column(Text)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    processed_markdown: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="syllabus", cascade="all, delete-orphan"
    )


class Chunk(Base):
    """One row per markdown section chunk, with a pgvector embedding."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    syllabus_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("syllabi.id", ondelete="CASCADE"), nullable=False
    )
    section_header: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(_EMBEDDING_DIM), nullable=False)
    is_asu_boilerplate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content_tsv: Mapped[None] = mapped_column(
        "content_tsv",
        TSVECTOR,
        nullable=True,
    )

    syllabus: Mapped["Syllabus"] = relationship("Syllabus", back_populates="chunks")

    __table_args__ = (
        # Cosine distance index for vector search
        Index(
            "ix_chunks_embedding_cosine",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # GIN index for full-text search
        Index("ix_chunks_content_tsv", "content_tsv", postgresql_using="gin"),
        # Standard FK index
        Index("ix_chunks_syllabus_id", "syllabus_id"),
    )
