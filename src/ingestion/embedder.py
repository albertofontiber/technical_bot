"""
Embedding generator for document chunks.
Uses OpenAI text-embedding-3-small for generating vector embeddings.
"""

import logging
import time

from ..config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

# Singleton client to avoid creating a new instance per call
_client = None


def get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def embed_texts(
    texts: list[str],
    batch_size: int = 100,
    model: str = EMBEDDING_MODEL,
    dimensions: int = EMBEDDING_DIMENSIONS,
    max_tokens_per_batch: int = 200_000,
) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.
        batch_size: Max number of texts per API call.
        model: OpenAI embedding model name.
        dimensions: Embedding dimensions.
        max_tokens_per_batch: Approximate token limit per batch (chars / 4).

    Returns:
        List of embedding vectors (same order as input texts).
    """
    client = get_client()
    all_embeddings = []

    # Build adaptive batches that respect both count and token limits
    batches = []
    current_batch_start = 0
    current_chars = 0

    for idx, text in enumerate(texts):
        clean = " ".join(text.split())[:8000]
        char_count = len(clean)

        # Approximate tokens as chars / 3 (conservative for multilingual text)
        if (current_chars + char_count) / 3 > max_tokens_per_batch and idx > current_batch_start:
            batches.append((current_batch_start, idx))
            current_batch_start = idx
            current_chars = 0

        current_chars += char_count

        if idx - current_batch_start + 1 >= batch_size:
            batches.append((current_batch_start, idx + 1))
            current_batch_start = idx + 1
            current_chars = 0

    if current_batch_start < len(texts):
        batches.append((current_batch_start, len(texts)))

    for start, end in batches:
        batch = [" ".join(t.split())[:8000] for t in texts[start:end]]

        try:
            response = client.embeddings.create(
                input=batch,
                model=model,
                dimensions=dimensions,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

            if end < len(texts):
                time.sleep(0.1)  # Rate limiting

        except Exception as e:
            logger.error(f"Embedding batch {start}-{end} failed: {e}")
            raise RuntimeError(
                f"Embedding failed for batch {start}-{end} ({len(batch)} texts). "
                f"Cannot continue — zero-vector fallback would corrupt search results. "
                f"Original error: {e}"
            ) from e

    return all_embeddings


def embed_query(
    query: str,
    model: str = EMBEDDING_MODEL,
    dimensions: int = EMBEDDING_DIMENSIONS,
) -> list[float]:
    """Generate embedding for a single query text."""
    client = get_client()
    response = client.embeddings.create(
        input=[" ".join(query.split())[:8000]],
        model=model,
        dimensions=dimensions,
    )
    return response.data[0].embedding
