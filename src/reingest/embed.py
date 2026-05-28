"""Etapa B8 del pipeline de re-ingesta — embedding (abstracción de proveedor).

Por defecto: Voyage `voyage-4-large` a 1024 dimensiones — líder de retrieval
multilingüe (mayo 2026). 1024 es un CONTRATO de schema: todos los modelos
serios soportan Matryoshka, así que un cambio futuro de modelo no obliga a
migrar `chunks_v2`.

`embed(texts, input_type)` es agnóstico al proveedor: cambiar de modelo o de
proveedor es configuración (variables de entorno), no reescritura. El adaptador
de Voyage está implementado; añadir Cohere u OpenAI es una función nueva en
`_PROVIDERS` con la misma firma.

Contextual retrieval (B7): el texto que se embebe es `context + content` — el
blurb antepuesto, según el método de Anthropic. La cita textual (`content`)
queda intacta en su columna.

Variables de entorno:
    VOYAGE_API_KEY      (obligatoria para el proveedor voyage)
    EMBED_PROVIDER      (default: voyage)
    EMBED_MODEL         (default: voyage-4-large)

Uso:
    from src.reingest.embed import embed_chunks
    embed_chunks(chunks)   # fija chunk.embedding (1024-dim) in-place
"""
from __future__ import annotations

import logging
import os
import time

from ..config import PROJECT_DIR  # noqa: F401 — import dispara load_dotenv para VOYAGE_API_KEY

logger = logging.getLogger(__name__)

# Dimensión-contrato de chunks_v2.embedding. NO cambiar sin migrar el schema.
EMBED_DIMENSIONS = 1024

EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "voyage")
EMBED_MODEL = os.getenv("EMBED_MODEL", "voyage-4-large")

# Texto máximo por chunk que se manda a embeber. El chunk ya viene acotado
# (~7000) + blurb (~600); 16000 es un tope de seguridad holgado.
_MAX_EMBED_CHARS = 16_000
# Batching conservador: nº de textos y presupuesto de caracteres por petición.
_BATCH_SIZE = 128
_BATCH_CHAR_BUDGET = 320_000

_voyage_client = None


def embedding_text(chunk) -> str:
    """Texto a embeber: blurb de contexto (B7) antepuesto al contenido."""
    body = chunk.content or ""
    if chunk.context:
        text = f"{chunk.context}\n\n{body}"
    else:
        text = body
    return text[:_MAX_EMBED_CHARS]


def _batches(texts: list[str]) -> list[tuple[int, int]]:
    """Particiona en lotes que respetan tope de nº de textos y de caracteres."""
    spans: list[tuple[int, int]] = []
    start = 0
    chars = 0
    for i, t in enumerate(texts):
        if i > start and (i - start >= _BATCH_SIZE or chars + len(t) > _BATCH_CHAR_BUDGET):
            spans.append((start, i))
            start = i
            chars = 0
        chars += len(t)
    if start < len(texts):
        spans.append((start, len(texts)))
    return spans


def _get_voyage():
    global _voyage_client
    if _voyage_client is None:
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "VOYAGE_API_KEY no configurada — añádela al .env para la "
                "Etapa B8 (embedding). El resto del pipeline no la necesita."
            )
        import voyageai
        _voyage_client = voyageai.Client(api_key=api_key)
    return _voyage_client


def _embed_voyage(texts: list[str], input_type: str) -> list[list[float]]:
    """Adaptador Voyage. `voyage-4-large` devuelve 1024 dims nativos — el SDK
    0.2.4 no expone `output_dimension`; la dimensión se verifica tras la
    respuesta (un cambio futuro de modelo a otra dim revienta aquí, no
    silenciosamente al insertar)."""
    client = _get_voyage()
    out: list[list[float]] = []
    for start, end in _batches(texts):
        batch = texts[start:end]
        for attempt in range(4):
            try:
                result = client.embed(
                    batch,
                    model=EMBED_MODEL,
                    input_type=input_type,
                )
                for vec in result.embeddings:
                    if len(vec) != EMBED_DIMENSIONS:
                        raise RuntimeError(
                            f"{EMBED_MODEL} devolvió vector de {len(vec)} dims, "
                            f"esperado {EMBED_DIMENSIONS}. Schema `chunks_v2."
                            f"embedding vector({EMBED_DIMENSIONS})` exige esa dim."
                        )
                out.extend(result.embeddings)
                break
            except Exception as e:
                if attempt == 3:
                    raise RuntimeError(
                        f"Voyage embed falló (lote {start}-{end}, "
                        f"{len(batch)} textos): {e}"
                    ) from e
                delay = 2.0 * (2 ** attempt)
                logger.warning("Voyage embed reintento %d en %.0fs: %s",
                               attempt + 1, delay, e)
                time.sleep(delay)
    return out


# Adaptadores por proveedor — misma firma (texts, input_type) -> embeddings.
_PROVIDERS = {
    "voyage": _embed_voyage,
}


def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Embebe una lista de textos. `input_type`: 'document' | 'query'.

    Devuelve un vector de EMBED_DIMENSIONS por texto, en el mismo orden.
    """
    if not texts:
        return []
    provider = _PROVIDERS.get(EMBED_PROVIDER)
    if provider is None:
        raise RuntimeError(
            f"EMBED_PROVIDER='{EMBED_PROVIDER}' sin adaptador. "
            f"Disponibles: {sorted(_PROVIDERS)}"
        )
    vectors = provider(texts, input_type)
    if len(vectors) != len(texts):
        raise RuntimeError(
            f"El proveedor devolvió {len(vectors)} vectores para "
            f"{len(texts)} textos — desajuste, abortando."
        )
    return vectors


def embed_chunks(chunks: list) -> int:
    """Fija `chunk.embedding` para cada chunk (B8). Devuelve cuántos embebió.

    Embebe `context + content` (contextual retrieval). Falla en bloque si el
    proveedor falla: un embedding a cero corrompería en silencio el retrieval
    (lección heredada de src/ingestion/embedder.py).
    """
    if not chunks:
        return 0
    texts = [embedding_text(c) for c in chunks]
    vectors = embed(texts, input_type="document")
    for chunk, vector in zip(chunks, vectors):
        chunk.embedding = vector
    return len(chunks)
