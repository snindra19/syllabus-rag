"""Async SQLAlchemy engine and session setup."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
)


# Note: pgvector.asyncpg.register_vector is NOT used here.
# pgvector.sqlalchemy.Vector.bind_processor already converts Python lists to the
# '[x, y, ...]' string representation. Registering the asyncpg binary codec on top
# causes a double-encoding conflict (codec receives a string instead of a list).
# For vector columns we rely on text-protocol via explicit CAST(:val AS vector) in SQL.

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        yield session
