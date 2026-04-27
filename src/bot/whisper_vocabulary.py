"""
Whisper transcription vocabulary hint for PCI domain.

Whisper struggles with alphanumeric model codes ("CAD-250" → "cabe doscientos
cincuenta") and domain jargon. The `prompt` argument lets us seed the decoder
with vocabulary it should recognize. Limit is ~244 tokens (~ 200 words).

Strategy:
  - Static base: manufacturer names + common PCI terminology that Whisper
    rarely gets right out-of-the-box.
  - Dynamic extension: model codes from Supabase (cached on first call).
    Falls back gracefully to the static base if the DB call fails.
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


# Static vocabulary base — manufacturer names + jargon that Whisper-es misreads.
# Hyphens and exact casing matter for the hint; Whisper learns from this exact form.
_STATIC_HINT = (
    "Asistente técnico de sistemas PCI (protección contra incendios). "
    "Fabricantes: Notifier, Morley, Detnov, Honeywell. "
    "Equipos: central, centralita, módulo, detector, sirena, pulsador, "
    "fuente de alimentación, batería, sounder, repetidor, aislador. "
    "Conexionado: lazo, bucle, zona, lazo SLC, lazo MLC, "
    "tensión, mA, polaridad, EOL, resistencia final de línea. "
    "Términos: instalación, programación, direccionamiento, configuración, "
    "puesta en marcha, mantenimiento, avería, alarma, prealarma, supervisión."
)

# Hard cap on total prompt length (chars, not tokens — conservative).
# Whisper's 244-token limit ~ 1000-1100 chars in Spanish.
_MAX_PROMPT_CHARS = 1000


def _select_hard_models(models_by_category: dict[str, list[str]]) -> list[str]:
    """Pick model codes most likely to need transcription help.

    Heuristic: codes with hyphen + digits (CAD-250, AFP-2820, ID-3000) are the
    ones Whisper-es mangles. Plain alphabetic names (e.g. "VESDA") usually
    transcribe fine and are skipped to save tokens.
    """
    selected: list[str] = []
    for models in models_by_category.values():
        for model in models:
            if "-" in model and any(c.isdigit() for c in model):
                selected.append(model)
    return sorted(set(selected))


@lru_cache(maxsize=1)
def get_whisper_prompt() -> str:
    """Build the Whisper prompt: static base + DB-derived model codes.

    Cached for the process lifetime. If the DB lookup fails on first call,
    the static base is returned and the next call retries (lru_cache traps
    return values, so on exception we let it propagate then catch).
    """
    return _build_prompt()


def _build_prompt() -> str:
    """Assemble the prompt, gracefully degrading if Supabase is unreachable."""
    try:
        # Lazy import to avoid circular config loading at module import time.
        from ..rag.retriever import get_all_models_by_category
        models_by_cat = get_all_models_by_category()
        hard_models = _select_hard_models(models_by_cat)
    except Exception as e:
        logger.warning(f"Whisper vocab: DB lookup failed, using static hint only ({e})")
        return _STATIC_HINT

    if not hard_models:
        return _STATIC_HINT

    models_part = "Modelos: " + ", ".join(hard_models) + "."
    full = f"{_STATIC_HINT} {models_part}"

    if len(full) <= _MAX_PROMPT_CHARS:
        return full

    # Truncate model list (preserve static base) to fit limit.
    available = _MAX_PROMPT_CHARS - len(_STATIC_HINT) - len(" Modelos: .") - 5
    truncated_models: list[str] = []
    used = 0
    for m in hard_models:
        cost = len(m) + 2  # ", "
        if used + cost > available:
            break
        truncated_models.append(m)
        used += cost

    if not truncated_models:
        return _STATIC_HINT
    return f"{_STATIC_HINT} Modelos: " + ", ".join(truncated_models) + "."
