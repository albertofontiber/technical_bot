"""Etapa B8 del pipeline de re-ingesta — indexación en chunks_v2.

Inserta los chunks (ya con metadata, contexto y embedding) en la tabla
`chunks_v2` de Supabase, vía PostgREST. Reutiliza `SupabaseHTTP` de la capa de
ingestión — su lógica de reintento ante 5xx ya está probada en producción.

Idempotencia: re-procesar un documento borra primero sus filas previas
(`DELETE WHERE extraction_sha256 = X`) y luego re-inserta. La Etapa B es
re-ejecutable infinitas veces — re-correr el pipeline sobre un archivo nunca
duplica chunks.

Uso:
    from src.reingest.index import index_chunks, resolve_document_id
    doc_id = resolve_document_id(sb, sha256, filename)
    index_chunks(chunks, extraction_sha256=sha256, document_id=doc_id, supabase=sb)
"""
from __future__ import annotations

import logging

from ..ingestion.supabase_client import SupabaseHTTP

logger = logging.getLogger(__name__)

TABLE = "chunks_v2"
_INSERT_BATCH = 200


def _vector_literal(embedding: list[float] | None) -> str | None:
    """Embedding → literal de texto de pgvector ('[0.1,0.2,...]')."""
    if embedding is None:
        return None
    return "[" + ",".join(format(x, ".7g") for x in embedding) + "]"


def _chunk_to_row(chunk, extraction_sha256: str,
                  document_id: str | None) -> dict:
    """Mapea un Chunk a una fila de chunks_v2. `search_vector` lo puebla el
    trigger; `created_at` toma su default."""
    return {
        "id": chunk.id,
        "document_id": document_id,
        "extraction_sha256": extraction_sha256,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "context": chunk.context,
        "embedding": _vector_literal(chunk.embedding),
        "language": chunk.language,
        "section_title": chunk.section_title,
        "section_path": chunk.section_path,
        "content_type": chunk.content_type,
        "is_flow_diagram": chunk.is_flow_diagram,
        "confidence": chunk.confidence,
        "product_model": chunk.product_model,
        "manufacturer": chunk.manufacturer,
        "distributor": chunk.distributor,
        "protocol": chunk.protocol,
        "doc_type": chunk.doc_type,
        "category": chunk.category,
        "has_diagram": chunk.has_diagram,
        "diagram_url": None,  # pendiente del pipeline de imágenes (follow-up B4)
        "source_file": chunk.source_file,
        "page_number": chunk.page_number,
        "duplicate_of": chunk.duplicate_of,
    }


def resolve_document_id(supabase: SupabaseHTTP, extraction_sha256: str,
                        source_filename: str) -> str | None:
    """Enlaza el documento extraído con su fila en `documents`, si existe.

    `documents` NO se reconstruye (es idempotente por hash). Se intenta casar
    primero por hash del PDF y, si no, por nombre de archivo único. Devuelve
    None si no hay match — el retriever trata document_id NULL como chunk sin
    ciclo de vida (se conserva), así que no enlazar es seguro.
    """
    try:
        rows = supabase.fetch_rows(
            "documents", select="id",
            filters={"source_pdf_sha256": f"eq.{extraction_sha256}"}, limit=2)
        if len(rows) == 1:
            return rows[0]["id"]
        rows = supabase.fetch_rows(
            "documents", select="id",
            filters={"source_pdf_filename": f"eq.{source_filename}"}, limit=2)
        if len(rows) == 1:
            return rows[0]["id"]
    except Exception as e:
        logger.warning("resolve_document_id falló para %s: %s", source_filename, e)
    return None


def index_chunks(chunks: list, extraction_sha256: str,
                 document_id: str | None = None,
                 supabase: SupabaseHTTP | None = None) -> int:
    """Indexa los chunks de un documento en chunks_v2 (B8). Devuelve nº insertado.

    Borra primero las filas previas de este `extraction_sha256` (idempotencia)
    y luego inserta por lotes.
    """
    sb = supabase or SupabaseHTTP()

    # Idempotencia: limpiar lo previo de este archivo antes de re-insertar.
    sb.delete_rows(TABLE, {"extraction_sha256": f"eq.{extraction_sha256}"})

    if not chunks:
        return 0

    # ORDENAR canónicos primero, duplicados después. La FK chunks_v2.duplicate_of
    # → chunks_v2.id se valida por fila; sin este orden, un duplicado en el batch N
    # puede referenciar a un canonical que aún no ha entrado (batch N+1) y rompe
    # con 23503. Con canonicos primero, todo id referenciado ya existe.
    chunks_sorted = sorted(chunks,
                           key=lambda c: (c.duplicate_of is not None, c.chunk_index))
    rows = [_chunk_to_row(c, extraction_sha256, document_id) for c in chunks_sorted]
    for i in range(0, len(rows), _INSERT_BATCH):
        # on_conflict='id' → UPSERT: si el retry POSTea filas que ya entraron
        # server-side (su respuesta se perdió), se merge en vez de 409.
        sb.insert_rows(TABLE, rows[i:i + _INSERT_BATCH], on_conflict="id")
    return len(rows)
