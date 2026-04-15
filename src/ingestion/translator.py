"""
Translator for PCI technical manuals (EN → ES) using Claude Sonnet.
Translates page-by-page to preserve table structure and technical context.
Used during ingestion for English-only manuals.
"""

import logging
import time

import anthropic

from ..config import ANTHROPIC_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

# Singleton client
_client = None

TRANSLATION_PROMPT = """Traduce el siguiente texto técnico de un manual de protección contra incendios (PCI) \
del inglés al español.

REGLAS:
1. Mantén EXACTAMENTE la misma estructura: tablas, listas, numeración, saltos de línea.
2. Mantén los nombres de producto y códigos de modelo SIN traducir (ej: NFXI-OPT, AM-8200N, VESDA VLP).
3. Mantén las unidades técnicas tal cual (V, mA, °C, mm, kg, IP65, etc.).
4. Usa terminología PCI estándar en español:
   - "fire alarm control panel" → "central de incendios"
   - "smoke detector" → "detector de humo"
   - "loop" → "lazo"
   - "sounder" → "sirena"
   - "beacon" → "baliza"
   - "call point" → "pulsador"
   - "isolator" → "aislador"
   - "end-of-line resistor" → "resistencia de fin de línea"
   - "wiring" → "cableado/conexionado"
   - "commissioning" → "puesta en marcha"
   - "power supply" → "fuente de alimentación"
   - "battery" → "batería"
   - "relay" → "relé"
   - "zone" → "zona"
   - "addressable" → "analógico/direccionable"
   - "conventional" → "convencional"
5. Si hay una tabla, mantén el formato exacto con los separadores | y ---.
6. NO añadas explicaciones ni comentarios. Solo devuelve la traducción.
7. Si el texto ya está en español o es un código/número, déjalo tal cual.

Texto a traducir:
"""

MAX_TOKENS_PER_PAGE = 4096
REQUEST_DELAY = 0.5  # seconds between API calls


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def translate_text(text: str, model: str = LLM_MODEL) -> str:
    """Translate a single text block from English to Spanish.

    Args:
        text: English text to translate.
        model: Claude model to use.

    Returns:
        Spanish translation.
    """
    if not text or not text.strip():
        return text

    # Skip very short texts or texts that are just numbers/codes
    stripped = text.strip()
    if len(stripped) < 10:
        return text

    client = get_client()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS_PER_PAGE,
            messages=[{
                "role": "user",
                "content": TRANSLATION_PROMPT + text,
            }],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        # Return original text on failure — better than losing the content
        return text


def translate_pages(
    pages_text: list[str],
    model: str = LLM_MODEL,
    progress_interval: int = 10,
) -> list[str]:
    """Translate a list of page texts from English to Spanish.

    Args:
        pages_text: List of page texts (one string per page).
        model: Claude model to use.
        progress_interval: Log progress every N pages.

    Returns:
        List of translated page texts (same order and length).
    """
    translated = []
    total = len(pages_text)

    for i, page_text in enumerate(pages_text):
        if not page_text or not page_text.strip():
            translated.append(page_text)
            continue

        result = translate_text(page_text, model=model)
        translated.append(result)

        if (i + 1) % progress_interval == 0:
            logger.info(f"    Translated {i + 1} / {total} pages")

        time.sleep(REQUEST_DELAY)

    logger.info(f"    Translation complete: {total} pages")
    return translated


def should_translate(text: str, threshold: float = 0.06) -> bool:
    """Heuristic check if text is primarily in English and needs translation.

    Uses a low threshold because technical manuals have many product codes and numbers
    that dilute the ratio of common English words.

    Args:
        text: Text to check.
        threshold: Minimum ratio of English markers to consider it English.

    Returns:
        True if text appears to be in English.
    """
    if not text or len(text) < 50:
        return False

    text_lower = text.lower()
    words = text_lower.split()
    if not words:
        return False

    en_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have',
                'will', 'are', 'not', 'can', 'all', 'when', 'should', 'must',
                'each', 'only', 'also', 'been', 'into', 'between', 'through',
                'before', 'after', 'other', 'which', 'their', 'these', 'those',
                'installation', 'maintenance', 'operation', 'connection',
                'warning', 'caution', 'note', 'figure', 'table', 'section'}

    # Also check for absence of Spanish markers (to avoid translating ES text)
    es_words = {'el', 'la', 'los', 'las', 'del', 'de', 'en', 'con', 'para',
                'por', 'una', 'que', 'se', 'no', 'es', 'su', 'al', 'como',
                'instalación', 'instrucciones', 'conexión', 'detección',
                'mantenimiento', 'alimentación', 'advertencia'}

    en_count = sum(1 for w in words if w in en_words)
    es_count = sum(1 for w in words if w in es_words)

    # If more Spanish than English markers, don't translate
    if es_count > en_count:
        return False

    ratio = en_count / len(words)
    return ratio >= threshold
