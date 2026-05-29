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

from ..config import ANTHROPIC_API_KEY, RERANK_TOP_K
from .retriever import SPEC_INTENT, TROUBLESHOOT_INTENT, WIRING_INTENT

logger = logging.getLogger(__name__)

RERANK_MODEL = "claude-sonnet-4-6"  # Fast model for reranking
RERANK_MAX_TOKENS = 512


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = RERANK_TOP_K,
    target_models: list[str] | None = None,
) -> list[dict]:
    """Rerank chunks using Claude to determine true relevance.

    Args:
        query: The technician's question.
        chunks: Retrieved chunks from hybrid search.
        top_k: Number of top chunks to return after reranking.
        target_models: Product models detected in the query (e.g. ["CAD-250"]).

    Returns:
        Reranked list of chunks (most relevant first), limited to top_k.
    """
    if len(chunks) <= top_k:
        return chunks

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
        # Show enough content for Claude to judge relevance accurately
        content_preview = chunk.get("content", "")[:800]

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

Evalúa qué fragmentos son REALMENTE relevantes para responder la pregunta del técnico.{model_instruction}{type_instruction}
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
            return chunks[:top_k]

        # Reorder chunks by Claude's ranking
        reranked = []
        seen = set()
        for idx in indices:
            if isinstance(idx, int) and 0 <= idx < len(chunks) and idx not in seen:
                seen.add(idx)
                reranked.append(chunks[idx])

        # If Claude returned fewer than expected, pad with remaining chunks
        if len(reranked) < top_k:
            for i, chunk in enumerate(chunks):
                if i not in seen and len(reranked) < top_k:
                    reranked.append(chunk)

        return reranked

    except Exception as e:
        # If reranking fails, fall back to original order
        logger.error(f"Reranking failed: {e}")
        return chunks[:top_k]


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


def rerank_chunks_voyage(
    query: str,
    chunks: list[dict],
    top_k: int = RERANK_TOP_K,
    model: str = VOYAGE_RERANK_MODEL,
) -> list[dict]:
    """Rerank con cross-encoder dedicado de Voyage (rerank-2.5).

    A diferencia del reranker LLM (que emite un ranking JSON y solo ve 800 chars
    por chunk), el cross-encoder puntúa cada par (query, doc) con un score calibrado
    y lee el doc completo. Fail-open al orden de retrieval si la API falla.
    """
    if len(chunks) <= top_k:
        return chunks
    docs = [(c.get("content") or "")[:VOYAGE_RERANK_DOC_CHARS] for c in chunks]
    try:
        client = _get_voyage_rerank_client()
        res = client.rerank(query=query, documents=docs, model=model, top_k=top_k)
        return [chunks[r.index] for r in res.results]
    except Exception as e:
        logger.error(f"Voyage rerank failed: {e}")
        return chunks[:top_k]
