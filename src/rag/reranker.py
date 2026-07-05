"""
Reranker using Claude to re-score retrieved chunks by true relevance.
This is the second stage of the retrieval pipeline:
  1. Hybrid search (vector + keyword) → 10 candidates
  2. Reranking with Claude → top 5 most relevant
  3. Response generation with Claude
"""

import json
import logging

import anthropic

from ..config import (
    ANTHROPIC_API_KEY,
    RERANK_PREVIEW_CHARS,
    RERANK_TOP_K,
    RERANKER_BACKEND,
)
from .retriever import SPEC_INTENT, TROUBLESHOOT_INTENT, WIRING_INTENT

logger = logging.getLogger(__name__)

RERANK_MODEL = "claude-sonnet-4-6"  # Fast model for reranking
RERANK_MAX_TOKENS = 512


class RerankStrictError(RuntimeError):
    """Fail-open del reranker en modo estricto (harness de eval): el backend cayó a
    fallback (orden de entrada / truncado) — en eval eso es dato corrupto, no
    disponibilidad (diseño s61 §4, F6-v4)."""


def _tag(chunks: list[dict], backend: str) -> list[dict]:
    # rerank_backend_used: provenance por chunk para el assert del harness y el
    # manifest del freeze (s61 §4 — el manifest no puede mentir sobre qué corrió).
    for c in chunks:
        c["rerank_backend_used"] = backend
    return chunks


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = RERANK_TOP_K,
    target_models: list[str] | None = None,
    *,
    strict: bool = False,
    relevance_instruction: str | None = None,
) -> list[dict]:
    """Rerank chunks using Claude to determine true relevance.

    Args:
        query: The technician's question.
        chunks: Retrieved chunks from hybrid search.
        top_k: Number of top chunks to return after reranking.
        target_models: Product models detected in the query (e.g. ["CAD-250"]).
        strict: eval harness mode — fail-opens raise RerankStrictError instead of
            silently returning input order (prod keeps strict=False: availability).

    Returns:
        Reranked list of chunks (most relevant first), limited to top_k.
    """
    if len(chunks) <= top_k:
        return _tag(chunks, "short-circuit")

    # Build a compact representation for Claude to evaluate.
    # IMPORTANT: we expose the [DIAGRAMA DISPONIBLE] tag so Claude can factor
    # diagram availability into its relevance judgement — wiring/installation
    # queries need diagram chunks surfaced even when their OCR'd text is
    # sparser than adjacent prose chunks.
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        product = chunk.get("product_model", "desconocido")
        section = chunk.get("section_title", "")
        content_type = chunk.get("content_type", "")
        has_diagram = bool(chunk.get("has_diagram") and chunk.get("diagram_url"))
        diagram_tag = " [DIAGRAMA DISPONIBLE]" if has_diagram else ""
        # Show enough content for Claude to judge relevance accurately. La ventana
        # (default 800, prod inerte) es configurable por RERANK_PREVIEW_CHARS — s74/2c:
        # el hecho decisivo a veces cae más allá del char 800 y el reranker no lo ve.
        content_preview = chunk.get("content", "")[:RERANK_PREVIEW_CHARS]

        chunk_summaries.append(
            f"[{i}] Producto: {product} | Sección: {section} | Tipo: {content_type}{diagram_tag}\n{content_preview}"
        )

    chunks_text = "\n\n".join(chunk_summaries)

    # Add model priority instruction if specific models are mentioned
    model_instruction = ""
    if target_models and len(target_models) == 1:
        models_str = target_models[0]
        model_instruction = f"""
IMPORTANTE: La pregunta hace referencia al producto {models_str}.
PRIORIZA fragmentos que pertenezcan a ese producto. Solo incluye fragmentos de otros productos si aportan información directamente relevante que no está en los fragmentos del producto preguntado."""
    elif target_models and len(target_models) >= 2:
        models_str = ", ".join(target_models)
        model_instruction = f"""
IMPORTANTE: La pregunta COMPARA o hace referencia a VARIOS productos: {models_str}.
Selecciona fragmentos de TODOS los productos mencionados de forma equilibrada.
Necesitamos información de cada uno para poder responder la comparativa."""

    # Add query-type-aware reranking hints
    type_instruction = ""
    if WIRING_INTENT.search(query):
        type_instruction = (
            "\nPara esta pregunta de CONEXIONADO/INSTALACIÓN, prioriza fragmentos con "
            "[DIAGRAMA DISPONIBLE] que muestren esquemas de conexión, bornes o procedimientos "
            "de instalación — aunque su texto parezca más corto, el diagrama es crítico para "
            "que el técnico entienda el cableado en campo. Si no hay ninguno disponible, "
            "prioriza descripciones textuales del conexionado."
        )
    elif SPEC_INTENT.search(query):
        type_instruction = "\nPara esta pregunta de ESPECIFICACIONES, prioriza fragmentos con datos numéricos (voltajes, consumos, dimensiones, temperaturas, pesos)."
    elif TROUBLESHOOT_INTENT.search(query):
        type_instruction = "\nPara esta pregunta de AVERÍA/FALLO, prioriza fragmentos con procedimientos de diagnóstico, LEDs indicadores, códigos de error o pasos de resolución."

    prompt = f"""Pregunta del técnico PCI: {query}

Fragmentos candidatos recuperados de manuales técnicos:

{chunks_text}

{relevance_instruction or "Evalúa qué fragmentos son REALMENTE relevantes para responder la pregunta del técnico."}{model_instruction}{type_instruction}
Devuelve SOLO un JSON array con los índices de los {top_k} fragmentos más relevantes, ordenados de más a menos relevante.
Formato: [4, 1, 7, 0, 3]

Si menos de {top_k} fragmentos son relevantes, devuelve solo los relevantes.
Responde ÚNICAMENTE con el JSON array, sin explicación."""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        response = client.messages.create(
            model=RERANK_MODEL,
            max_tokens=RERANK_MAX_TOKENS,
            temperature=0,  # eval reproducibility — same candidates → same ranking
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()

        # Parse the JSON array
        # Handle cases where Claude wraps it in markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        indices = json.loads(raw)

        if not isinstance(indices, list):
            if strict:
                raise RerankStrictError(f"LLM rerank devolvió no-lista: {raw[:120]}")
            return _tag(chunks[:top_k], "fallback-truncate")

        # Reorder chunks by Claude's ranking
        reranked = []
        seen = set()
        for idx in indices:
            if isinstance(idx, int) and 0 <= idx < len(chunks) and idx not in seen:
                seen.add(idx)
                reranked.append(chunks[idx])

        # If Claude returned fewer than expected, pad with remaining chunks.
        # Padding is LEGITIMATE prod behavior (the prompt allows returning fewer
        # relevant indices) but it re-injects input order → tagged distinctly so
        # eval harnesses can detect/report it (F6-v4: detectable, not hidden).
        padded = len(reranked) < top_k
        if padded:
            for i, chunk in enumerate(chunks):
                if i not in seen and len(reranked) < top_k:
                    reranked.append(chunk)

        return _tag(reranked, "llm-padded" if padded else "llm")

    except RerankStrictError:
        raise
    except Exception as e:
        # If reranking fails, fall back to original order
        logger.error(f"Reranking failed: {e}")
        if strict:
            raise RerankStrictError(f"LLM rerank fail-open: {type(e).__name__}: {e}") from e
        return _tag(chunks[:top_k], "fallback-truncate")


_voyage_rerank_client = None
VOYAGE_RERANK_MODEL = "rerank-2.5"
VOYAGE_RERANK_DOC_CHARS = 4000  # el cross-encoder lee el doc (vs los 800 del LLM)


def _get_voyage_rerank_client():
    global _voyage_rerank_client
    if _voyage_rerank_client is None:
        import os

        import voyageai

        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "VOYAGE_API_KEY no configurada — requerida para el reranker Voyage"
            )
        _voyage_rerank_client = voyageai.Client(api_key=api_key)
    return _voyage_rerank_client


def _voyage_doc(chunk: dict) -> str:
    """Representación del doc al cross-encoder (s61 §2.0, header de PARIDAD).

    Mismas expresiones LITERALES que el LLM-rerank usa en sus chunk_summaries
    (rerank_chunks arriba, .get con los mismos defaults — quirks incluidos): el
    CE debe ver la misma metadata de IDENTIDAD (Producto/Sección/Tipo) que el
    LLM ve, o en 31 marcas con OEM relabels confunde manuales equivalentes
    (X1-s61). Sin índice de lista (rompería la orden-insensibilidad) y sin
    diagram_tag (canal muerto #45; su re-introducción = contrato de ese ciclo).
    """
    product = chunk.get("product_model", "desconocido")
    section = chunk.get("section_title", "")
    content_type = chunk.get("content_type", "")
    header = f"Producto: {product} | Sección: {section} | Tipo: {content_type}\n"
    return header + (chunk.get("content") or "")[:VOYAGE_RERANK_DOC_CHARS]


def rerank_chunks_voyage(
    query: str,
    chunks: list[dict],
    top_k: int = RERANK_TOP_K,
    model: str = VOYAGE_RERANK_MODEL,
    *,
    strict: bool = False,
) -> list[dict]:
    """Rerank con cross-encoder dedicado de Voyage (rerank-2.5).

    A diferencia del reranker LLM (que emite un ranking JSON y solo ve 800 chars
    por chunk), el cross-encoder devuelve un score de relevancia por par
    (query, doc) y lee 4000 chars + header de paridad (_voyage_doc). Fail-open
    al orden de retrieval si la API falla (strict=True → raise, eval harness).
    """
    if len(chunks) <= top_k:
        return _tag(chunks, "short-circuit")
    docs = [_voyage_doc(c) for c in chunks]
    try:
        client = _get_voyage_rerank_client()
        res = client.rerank(query=query, documents=docs, model=model, top_k=top_k)
        return _tag([chunks[r.index] for r in res.results], "voyage")
    except Exception as e:
        logger.error(f"Voyage rerank failed: {e}")
        if strict:
            raise RerankStrictError(f"Voyage rerank fail-open: {type(e).__name__}: {e}") from e
        return _tag(chunks[:top_k], "fallback-truncate")


def rerank(
    query: str,
    chunks: list[dict],
    top_k: int = RERANK_TOP_K,
    target_models: list[str] | None = None,
    *,
    strict: bool = False,
) -> list[dict]:
    """Dispatcher del reranker (s61, `evals/_s61_lever_design.md` §4).

    RERANKER_BACKEND=llm|voyage (config, default llm — reversible por entorno).
    Con voyage, SOLO las llamadas SIN target_models van al cross-encoder
    (dispatch condicional Y1: el A/B mide exactamente ese path — el harness de
    eval nunca pasa target_models); las llamadas CON target_models conservan el
    LLM-rerank con sus instrucciones de producto (comportamiento de prod
    intacto en el path no-medido, hasta su migración con medición propia).
    """
    if RERANKER_BACKEND == "voyage" and not target_models:
        return rerank_chunks_voyage(query, chunks, top_k=top_k, strict=strict)
    return rerank_chunks(
        query, chunks, top_k=top_k, target_models=target_models, strict=strict
    )
