"""
Embedding generator for document chunks.
Uses OpenAI text-embedding-3-small for generating vector embeddings.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path

from ..config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

# --- Cache de embeddings de QUERY, solo-harness (ciclo A s63, FINAL §2) -----
# EMBED_CACHE_PATH (env) apunta a un json {key: vector}. Lo usan los dos brazos
# de un A/B dual-arm para compartir EXACTAMENTE el mismo vector por query y
# aislar la variable de tratamiento del drift de embed_query entre llamadas
# (medido s61: 0.003 mueve golds frontera — DEC-042d). En prod la variable no
# existe → branch dormant. Write-through: el primer brazo puebla, el segundo lee.
_EMBED_CACHE: dict | None = None


def _embed_cache_path() -> Path | None:
    p = os.getenv("EMBED_CACHE_PATH")
    return Path(p) if p else None


def _embed_cache() -> dict | None:
    global _EMBED_CACHE
    path = _embed_cache_path()
    if path is None:
        return None
    if _EMBED_CACHE is None:
        try:
            _EMBED_CACHE = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception as exc:
            logger.warning("EMBED_CACHE_PATH ilegible (%s) — cache vacío", exc)
            _EMBED_CACHE = {}
    return _EMBED_CACHE

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
    """Generate embedding for a single query text.

    El proveedor depende de la tabla activa (CHUNKS_TABLE):
      - chunks    → OpenAI text-embedding-3-small (1536)
      - chunks_v2 → Voyage voyage-4-large (1024), input_type='query'
    El vector de la query DEBE coincidir en modelo/dim con el corpus indexado;
    si no, la similitud coseno es basura (o falla por dimensión).

    Con EMBED_CACHE_PATH (solo harness, ver cabecera): el vector se sirve/
    persiste por clave (proveedor+modelo+texto limpio) — mismo texto = mismo
    vector entre brazos de un A/B.
    """
    from ..config import CHUNKS_IS_V2
    cleaned = " ".join(query.split())[:8000]
    provider = "voyage-4-large|query" if CHUNKS_IS_V2 else f"openai-{model}|{dimensions}"
    cache = _embed_cache()
    cache_key = None
    if cache is not None:
        cache_key = hashlib.sha256(f"{provider}|{cleaned}".encode("utf-8")).hexdigest()
        hit = cache.get(cache_key)
        if hit is not None:
            return hit

    if CHUNKS_IS_V2:
        # Voyage: input_type='query' (asimétrico doc/query — los chunks se
        # embebieron con input_type='document' en B8).
        from ..reingest.embed import embed as voyage_embed
        vector = voyage_embed([cleaned], input_type="query")[0]
    else:
        client = get_client()
        response = client.embeddings.create(
            input=[cleaned],
            model=model,
            dimensions=dimensions,
        )
        vector = response.data[0].embedding

    if cache is not None and cache_key is not None:
        cache[cache_key] = vector
        try:
            _embed_cache_path().write_text(json.dumps(cache), encoding="utf-8")
        except Exception as exc:
            logger.warning("EMBED_CACHE_PATH no escribible (%s) — cache solo en memoria", exc)
    return vector
