"""Etapa B6 del pipeline de re-ingesta — dedup semántico NO destructivo.

Caza dos clases de redundancia (docs/PLAN_RAG_2026 §Fase 1, decisión 2):
  - Chunks equivalentes en distinto idioma: la versión ES y la EN del mismo
    contenido de un producto. Se conserva la ES; la EN se marca.
  - Duplicación del chunker (TECH_DEBT #7): el mismo texto chunkeado dos veces.

NO destructivo: nunca borra. Marca `chunk.duplicate_of` con el id del chunk
canónico que conserva. El retrieval filtra `duplicate_of IS NULL`, así que el
duplicado deja de competir pero sigue en la tabla — un falso positivo se
revierte poniendo el campo a NULL, sin re-extraer ni re-indexar.

Requiere embeddings: se ejecuta DESPUÉS de B8 (embed), sobre chunks con `id` y
`embedding`. La comparación es intra-producto (chunks del mismo product_model);
los chunks sin modelo se comparan solo dentro de su documento.

NOTA DE CALIBRACIÓN: el umbral por defecto (0.94) es un punto de partida. Las
traducciones ES/EN con voyage-4-large embeben próximas pero no idénticas; la
duplicación exacta da ~1.0. El umbral definitivo se fija inspeccionando los
pares marcados sobre el corpus real (post-extracción) — ver el GATE.

Uso:
    from src.reingest.dedup import mark_duplicates
    n = mark_duplicates(embedded_chunks)   # muta chunk.duplicate_of in-place
"""
from __future__ import annotations

import numpy as np

# Umbral de similitud coseno para considerar dos chunks duplicados.
DEFAULT_THRESHOLD = 0.94


def _group_key(chunk) -> str:
    """Clave de agrupación: el producto, o el documento si no hay modelo."""
    if chunk.product_model:
        return f"model::{chunk.product_model}"
    return f"doc::{chunk.source_file or chunk.id}"


def _preference(chunk) -> tuple:
    """Orden de preferencia para elegir el canónico (menor = más preferido).

    1º el español (política: prefiere ES). 2º el más largo (más completo).
    3º el de menor chunk_index (orden estable).
    """
    return (
        0 if chunk.language == "es" else 1,
        -len(chunk.content),
        chunk.chunk_index,
    )


def mark_duplicates(chunks: list, threshold: float = DEFAULT_THRESHOLD) -> int:
    """Marca los chunks duplicados semánticos (B6). Devuelve cuántos marcó.

    Dentro de cada grupo de producto, recorre los chunks en orden de preferencia
    (el canónico primero): cada chunk aún no marcado se vuelve canónico y absorbe
    a los chunks similares menos preferidos. Así el resultado es estable y
    transitivo — un chunk parecido a dos canónicos se asigna al más preferido.
    """
    groups: dict[str, list] = {}
    for ch in chunks:
        if ch.embedding is None:
            continue
        groups.setdefault(_group_key(ch), []).append(ch)

    marked = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        group.sort(key=_preference)

        # Matriz de embeddings normalizada → producto matricial = cosenos.
        matrix = np.array([c.embedding for c in group], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        matrix /= norms
        sims = matrix @ matrix.T

        for i, canonical in enumerate(group):
            if canonical.duplicate_of is not None:
                continue  # ya es duplicado de otro — no puede ser canónico
            for j in range(i + 1, len(group)):
                other = group[j]
                if other.duplicate_of is not None:
                    continue
                if sims[i, j] >= threshold:
                    other.duplicate_of = canonical.id
                    marked += 1
    return marked
