"""HyDE (Hypothetical Document Embeddings) — Gao et al. 2022.

Generates a hypothetical manual passage answering the technician's query,
then the embedding of that passage is used for retrieval. Resolves the
vocabulary mismatch problem where:
- Technician uses informal/colloquial terms ("programación", "menú avanzao",
  "configurar la centralita")
- Manual uses formal sector terminology ("AJUSTES > AVANZADO > Sistema",
  "panel de control direccionable", "configuración de parámetros")

The hypothesis is written in the formal style of a PCI manual, so its
embedding clusters near the actual manual chunks even when the original
query's vocabulary diverges.

Reference: Gao et al. 2022, "Precise Zero-Shot Dense Retrieval without
Relevance Labels" (arxiv.org/abs/2212.10496). Canonical implementation in
LangChain `HypotheticalDocumentEmbedder` and LlamaIndex `HyDEQueryTransform`.

Especially critical for Fontiber: técnicos PCI con léxico no sofisticado
usarán jerga regional, abreviaturas, errores ortográficos. HyDE adapta
dinámicamente, synonyms estáticos no escalan.
"""

from __future__ import annotations

import logging
import os

import anthropic

from ..config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

HYDE_MODEL = os.getenv("HYDE_MODEL", "claude-haiku-4-5")
HYDE_MAX_TOKENS = 400

# Feature flag. Default OFF desde s46 (DEC-019c): el path validado en s44 (retrieve-wide,
# FALLO ~6->1) se midió HyDE-OFF; off = 100% determinista (on corre temp=0 = casi, hay
# variación server-side) y ahorra una llamada Haiku/query. Override: HYDE_ENABLED=true.
# PENDIENTE (gaps): confirmar on/off@50 en chunks_v2 (gate F1; la medición s29 sobre corpus
# viejo NO transfiere) + re-evaluar el beneficio real de HyDE —vocabulary mismatch de jerga
# informal, TECH_DEBT #25— con técnicos reales (el gold actual es formal).
HYDE_ENABLED = os.getenv("HYDE_ENABLED", "false").lower() == "true"

HYDE_SYSTEM_PROMPT = """Eres un manual técnico oficial de sistemas de protección contra incendios (PCI). \
Recibes una consulta de un técnico de campo y debes escribir el párrafo del manual que contendría la respuesta.

REGLAS DEL ESTILO:
1. Escribe en estilo de manual técnico formal (NO conversacional, NO instrucciones al técnico).
2. Usa la terminología formal del sector PCI:
   - "menú AJUSTES", "submenú AVANZADO", "submenú SISTEMA", "OPCIONES PERIFÉRICAS"
   - "panel de control direccionable", "central analógica", "central convencional"
   - "lazo SLC", "circuito monitor", "circuito de control", "estilo NFPA 4/6/7"
   - "módulo de aislamiento", "módulo monitor", "módulo de control", "tarjeta LIB"
   - "fuente de alimentación supervisada", "batería de respaldo", "corriente nominal"
   - "detector óptico", "detector iónico", "detector termovelocimétrico", "pulsador manual direccionable"
   - "configuración", "programación", "puesta en marcha", "puesta en servicio"
3. Si el técnico usa terminología coloquial/informal/abreviada/regional, **tradúcela a la terminología formal**.
   Ejemplos: "el menú avanzao" → "submenú AVANZADO"; "programar la central" → "configurar el panel de control";
   "el bicho que monitorea" → "módulo monitor".
4. NO respondas con instrucciones conversacionales ("Para hacer X, sigue estos pasos..."). \
Escribe como ENTRADA DE MANUAL: cabecera de sección + párrafo descriptivo.
5. Sé específico con nombres de menús, terminales, parámetros, procedimientos. NO genérico.
6. NO inventes valores numéricos concretos (voltajes, corrientes, capacidades, dimensiones). \
Usa términos genéricos: "según especificación", "valor nominal", "configurable según parámetro".
7. Longitud: ~100-200 palabras. Un solo párrafo coherente o sección corta con cabecera.

Tu salida será usada para hacer retrieval semántico contra el corpus de manuales reales. Cuanto más se parezca \
al estilo y terminología de un manual real, mejor matchea con los chunks correctos."""


def generate_hypothetical_document(query: str) -> str:
    """Generate a hypothetical manual passage answering the query (HyDE).

    Args:
        query: The technician's query, possibly using informal vocabulary.

    Returns:
        A ~100-200 word hypothetical manual passage in formal PCI terminology.
        On any error or if HyDE disabled, returns the original query (graceful
        fallback — embedding the query directly is the pre-HyDE behavior).
    """
    if not HYDE_ENABLED:
        return query
    if not query or len(query.strip()) < 5:
        return query

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=HYDE_MODEL,
            max_tokens=HYDE_MAX_TOKENS,
            temperature=0,  # determinism
            system=HYDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": query}],
        )
        hypothesis = resp.content[0].text.strip()
        if not hypothesis or len(hypothesis) < 20:
            logger.warning(f"HyDE produced empty/tiny output for query '{query[:60]}...'")
            return query
        return hypothesis
    except Exception as e:
        logger.warning(f"HyDE failed for query '{query[:60]}...': {type(e).__name__}: {e}")
        return query  # graceful fallback
