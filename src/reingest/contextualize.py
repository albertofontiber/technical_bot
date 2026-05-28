"""Etapa B7 del pipeline de re-ingesta — contextual retrieval.

Contextual Retrieval (Anthropic, sept 2024): antes de embeber cada chunk se le
genera un blurb de 1-2 frases que lo sitúa en el documento completo. Reduce el
fallo de retrieval ~49% según Anthropic — resuelve los chunks que pierden su
referente al separarse del documento ("el detector" → "el detector ASD535 de la
sección 4.2 de aspiración").

El blurb se genera con Claude Haiku (modelo barato) y PROMPT CACHING: el
documento completo va en un bloque cacheado, idéntico en las N llamadas de sus N
chunks. La primera llamada escribe la caché; las demás la leen a 0,1x el coste.

El blurb se guarda en `chunk.context`, SEPARADO de `chunk.content`: B8 lo
antepone al contenido para embeber e indexar FTS, pero la cita textual que ve el
técnico queda limpia.

Uso:
    from src.reingest.contextualize import contextualize_document, full_document_text
    contextualize_document(full_document_text(record), chunks)
"""
from __future__ import annotations

import logging

from anthropic import Anthropic

from ..config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Haiku 4.5 — barato y suficiente para una tarea de resumen acotada.
_MODEL = "claude-haiku-4-5-20251001"
# Tope del documento que se cachea (~50k tokens). Casi todos los manuales caben;
# uno mayor se trunca — el blurb de los chunks finales pierde algo de contexto.
_MAX_DOC_CHARS = 200_000
# Tope del texto del chunk en el prompt — un chunk no necesita ir entero para
# que el modelo lo sitúe.
_MAX_CHUNK_CHARS = 6_000

_INSTRUCTION = (
    "Aquí está el fragmento que queremos situar dentro del documento de arriba:\n"
    "<chunk>\n{chunk}\n</chunk>\n\n"
    "Da un contexto breve y conciso (1-2 frases) que sitúe este fragmento dentro "
    "del documento completo, para mejorar su recuperación en una búsqueda. "
    "Indica el producto y la sección a la que pertenece y de qué trata. "
    "Responde SOLO con ese contexto, en español, sin preámbulos."
)

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY no configurada (.env)")
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def full_document_text(extraction_record: dict) -> str:
    """Markdown completo del documento extraído (todas las páginas en orden)."""
    pages = extraction_record.get("result", {}).get("pages", [])
    parts = []
    for p in pages:
        md = p.get("md") or p.get("text") or ""
        if md.strip():
            parts.append(md)
    return "\n\n".join(parts)


def contextualize_document(document_text: str, chunks: list,
                           client: Anthropic | None = None) -> int:
    """Genera `chunk.context` para cada chunk del documento (B7).

    Secuencial a propósito: las llamadas comparten el bloque cacheado del
    documento, así que ir en serie maximiza los aciertos de caché. La
    paralelización entre documentos distintos es cosa del orquestador.

    Si una llamada falla, ese chunk queda con context=None (sigue siendo
    embebible por su contenido) y se continúa. Devuelve cuántos blurbs generó.
    """
    if not chunks:
        return 0
    client = client or _get_client()
    doc = document_text[:_MAX_DOC_CHARS]
    cached_doc_block = {
        "type": "text",
        "text": f"<document>\n{doc}\n</document>",
        "cache_control": {"type": "ephemeral"},
    }

    done = 0
    for ch in chunks:
        try:
            resp = client.messages.create(
                model=_MODEL,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": [
                        cached_doc_block,
                        {"type": "text",
                         "text": _INSTRUCTION.format(chunk=ch.content[:_MAX_CHUNK_CHARS])},
                    ],
                }],
            )
            ch.context = resp.content[0].text.strip()
            done += 1
        except Exception as e:
            logger.warning("contextualize: chunk %s falló: %s", ch.id[:8], e)
            ch.context = None
    return done
