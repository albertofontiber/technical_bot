"""
Whisper transcription vocabulary hint for PCI domain.

Whisper struggles with alphanumeric model codes ("CAD-250" → "cabe doscientos
cincuenta") and domain jargon. The `prompt` argument lets us seed the decoder
with vocabulary it should recognize. Limit is ~244 tokens (~ 200 words).

Strategy:
  - Static base: manufacturer names + common PCI terminology that Whisper
    rarely gets right out-of-the-box.
  - Dynamic extension: model codes del catálogo curado (data/model_catalog.json,
    vía src/rag/catalog.py) — la MISMA fuente única que el retriever, para no
    mantener dos listas de modelos. Cacheado. Degrada al hint estático si el
    snapshot no está disponible.
"""

import logging
from collections.abc import Callable
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


def _select_hard_models(
    models: list[str],
    manufacturer_lookup: Callable[[str], str | None] | None = None,
) -> list[str]:
    """Pick model codes most likely to need transcription help.

    Heuristic: alphanumeric codes (letra + dígito: CAD-250, ID3000, AFP1010,
    20/20I) son los que Whisper-es destroza. Nombres puramente alfabéticos
    (p.ej. "VESDA", "PEARL") suelen transcribirse bien y se omiten para ahorrar
    tokens.
    """
    # Preserva el orden de entrada (all_models() viene por frecuencia desc) para
    # que, al truncar por el límite de Whisper, queden los modelos más comunes.
    seen: set[str] = set()
    out: list[str] = []
    for m in models:
        if m in seen:
            continue
        if any(c.isalpha() for c in m) and any(c.isdigit() for c in m):
            seen.add(m)
            out.append(m)
    if manufacturer_lookup is None:
        return out

    # ``all_models`` is globally frequency-sorted. Taking that prefix alone
    # starves long-tail manufacturers. Reserve one high-frequency code per
    # manufacturer, then fill the rest in the original global order. This
    # stays data-driven and scales without per-brand vocabulary lists.
    first_per_manufacturer: list[str] = []
    represented: set[str] = set()
    for model in out:
        try:
            manufacturer = manufacturer_lookup(model)
        except Exception:
            manufacturer = None
        if manufacturer and manufacturer not in represented:
            represented.add(manufacturer)
            first_per_manufacturer.append(model)

    prioritized = set(first_per_manufacturer)
    return first_per_manufacturer + [model for model in out if model not in prioritized]


@lru_cache(maxsize=1)
def get_whisper_prompt() -> str:
    """Build the Whisper prompt: static base + DB-derived model codes.

    Cached for the process lifetime. If the DB lookup fails on first call,
    the static base is returned and the next call retries (lru_cache traps
    return values, so on exception we let it propagate then catch).
    """
    return _build_prompt()


def _build_prompt() -> str:
    """Assemble the prompt from the curated model catalog — la MISMA fuente
    única que usa el retriever (data/model_catalog.json), no una consulta a BD
    aparte. Así el vocabulario de voz se auto-actualiza al regenerar el catálogo
    (sin mantener dos listas). Degrada al hint estático si falta el snapshot."""
    try:
        # Import perezoso para evitar carga de config en import-time.
        from ..rag.catalog import all_models, catalog_available, model_manufacturer
        if not catalog_available():
            logger.warning("Whisper vocab: catálogo no disponible, solo hint estático")
            return _STATIC_HINT
        hard_models = _select_hard_models(
            all_models(), manufacturer_lookup=model_manufacturer
        )
    except Exception as e:
        logger.warning(f"Whisper vocab: fallo leyendo catálogo, hint estático ({e})")
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
