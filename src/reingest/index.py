"""Etapa B8 del pipeline de re-ingesta — indexación en chunks_v2.

Inserta los chunks (ya con metadata, contexto y embedding) en la tabla
`chunks_v2` de Supabase, vía PostgREST. Reutiliza `SupabaseHTTP` de la capa de
ingestión — su lógica de reintento ante 5xx ya está probada en producción.

Idempotencia: re-procesar un documento borra primero sus filas previas
(`DELETE WHERE extraction_sha256 = X`) y luego re-inserta. La Etapa B es
re-ejecutable infinitas veces — re-correr el pipeline sobre un archivo nunca
duplica chunks.

Uso (s323: resolver_documento primero; index_chunks EXIGE document_id):
    from src.reingest.index import index_chunks, resolve_document_id
    doc_id = resolve_document_id(sb, sha256, filename)
    index_chunks(chunks, extraction_sha256=sha256, document_id=doc_id, supabase=sb)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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


class EstadoResolucion(str, Enum):
    """Resultado TIPADO de resolver un documento (s323 fase B, dúo r32).

    ANTES: `resolve_document_id` devolvía `None` para CUATRO situaciones
    distintas — documento nuevo, solo filas no-activas, ambigüedad (2+ filas) y
    excepción de red tragada — y el llamador no podía distinguirlas. Ese `None`
    indistinguible es la causa raíz de TECH_DEBT #80/#81: los chunks se
    indexaban con `document_id=NULL` (huérfanos) o quedaban ligados a filas ya
    retiradas, y `must_preserve` dejaba de atestar.
    """
    ACTIVO = "activo"                  # 1 fila y está activa → enlazar
    SOLO_NO_ACTIVO = "solo_no_activo"  # casa, pero retired/superseded/needs_review
    SIN_MATCH = "sin_match"            # documento aún no dado de alta
    AMBIGUO = "ambiguo"                # 2+ filas casan: no se elige a ojo
    ERROR = "error"                    # fallo de infraestructura: NO se traga


@dataclass(frozen=True)
class ResolucionDocumento:
    estado: EstadoResolucion
    document_id: str | None = None
    detalle: str = ""

    @property
    def enlazable(self) -> bool:
        return self.estado is EstadoResolucion.ACTIVO and bool(self.document_id)


def resolver_documento(supabase: SupabaseHTTP, extraction_sha256: str,
                       source_filename: str,
                       manufacturer: str | None = None) -> ResolucionDocumento:
    """Resuelve la fila de `documents` del PDF extraido, distinguiendo los casos.

    IDENTIDAD (duo r33, critico de Sol): la unicidad del esquema es por
    `(manufacturer, source_pdf_sha256)` (migrations/001_document_management.sql),
    asi que el hash se consulta ACOTADO a la marca cuando se conoce; sin acotar,
    un OEM/relabel podria enlazarse al documento de otra marca.

    El NOMBRE no es corroboracion, es un FALLBACK independiente y peligroso (un
    PDF re-exportado cambia de hash, y un nombre generico de manual se repite
    entre fabricantes), asi que solo se usa ACOTADO a la marca; sin marca
    conocida no se usa en absoluto.

    El filtro `status='active'` se aplica EN SERVIDOR: filtrarlo en cliente sobre
    un `limit` podia ocultar una segunda fila activa y devolver ACTIVO donde
    habia AMBIGUO (segundo critico de Sol).

    Los errores de infraestructura se DEVUELVEN como ERROR — no se tragan como
    "no hay match", que es lo que enmascaraba fallos de red.
    """
    def _rows(campo: str, valor: str, solo_activas: bool) -> list:
        filtros = {campo: f"eq.{valor}"}
        if solo_activas:
            filtros["status"] = "eq.active"
        if manufacturer:
            filtros["manufacturer"] = f"eq.{manufacturer}"
        return supabase.fetch_rows("documents", select="id,status",
                                   filters=filtros, limit=5)

    try:
        candidatos = [("source_pdf_sha256", extraction_sha256)]
        if manufacturer:                      # sin marca, el nombre NO se usa
            candidatos.append(("source_pdf_filename", source_filename))
        for campo, valor in candidatos:
            if not valor:
                continue
            activas = _rows(campo, valor, solo_activas=True)
            if len(activas) == 1:
                return ResolucionDocumento(
                    EstadoResolucion.ACTIVO, activas[0]["id"],
                    f"1 activa por {campo}"
                    + (" (marca acotada)" if manufacturer else ""))
            if len(activas) > 1:
                return ResolucionDocumento(
                    EstadoResolucion.AMBIGUO, None,
                    f"{len(activas)} filas ACTIVAS casan por {campo}: "
                    "no se elige a ojo")
            todas = _rows(campo, valor, solo_activas=False)
            if todas:
                estados = sorted({r.get("status") for r in todas})
                return ResolucionDocumento(
                    EstadoResolucion.SOLO_NO_ACTIVO, None,
                    f"casa por {campo} pero solo con filas {estados}")
    except Exception as e:                                    # noqa: BLE001
        logger.error("resolver_documento ERROR de infraestructura para %s: %s",
                     source_filename, e)
        return ResolucionDocumento(EstadoResolucion.ERROR, None, repr(e)[:200])
    return ResolucionDocumento(EstadoResolucion.SIN_MATCH, None,
                               "sin fila ACTIVA en documents (alta pendiente?)")


def resolve_document_id(supabase: SupabaseHTTP, extraction_sha256: str,
                        source_filename: str) -> str | None:
    """Compat: el id SOLO si hay exactamente una fila ACTIVA; si no, None.
    Los llamadores nuevos deben usar `resolver_documento` y mirar el estado."""
    return resolver_documento(supabase, extraction_sha256,
                              source_filename).document_id


def index_chunks(chunks: list, extraction_sha256: str,
                 document_id: str | None = None,
                 supabase: SupabaseHTTP | None = None) -> int:
    """Indexa los chunks de un documento en chunks_v2 (B8). Devuelve nº insertado.

    Borra primero las filas previas de este `extraction_sha256` (idempotencia)
    y luego inserta por lotes.
    """
    sb = supabase or SupabaseHTTP()

    # GUARDA s323 fase B (dúo r32, crítico de Sol): el DELETE va ANTES del
    # INSERT, así que indexar sin `document_id` no solo crea huérfanos — BORRA
    # las filas buenas primero. Un gate posterior solo constataría el daño. Por
    # eso la guarda vive AQUÍ, en el writer, y no solo en `process_file`.
    if not document_id:
        raise ValueError(
            "index_chunks: document_id obligatorio (s323 #80/#81). Resuelve con "
            "resolver_documento() y trata su estado: SIN_MATCH exige dar de alta "
            "el documento primero; SOLO_NO_ACTIVO / AMBIGUO / ERROR no se ingestan.")

    # OJO: la guarda cubre tambien el caso chunks=[] — el DELETE se ejecuta
    # igual, asi que un vacio accidental de otro llamador borraria filas buenas.
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
