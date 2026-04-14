"""Generate embeddings using OpenAI text-embedding-3-small."""

import logging

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Return a list of embedding vectors for the given texts.

    Batches all texts in a single API call (max 2048 inputs per call).
    """
    response = await _client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    logger.info(
        "Embedding call: %d texts, %d total tokens",
        len(texts),
        response.usage.total_tokens,
    )
    return [item.embedding for item in response.data]


async def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    vectors = await embed_texts([query])
    return vectors[0]
