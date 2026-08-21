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
import os
import re
from collections.abc import Callable
from functools import lru_cache

from ..orchestrator.contracts import Asuncion

logger = logging.getLogger(__name__)


# ─────────────────────── corrección DESPUÉS de transcribir (s324f)
#
# POR QUÉ EXISTE, y por qué el hint no bastaba. En el piloto, una pregunta por
# voz sobre *Detnov* se transcribió **«Death Knob»** — y el bot no encontró nada,
# porque el fabricante había desaparecido de la pregunta. Lo revelador es que
# «Detnov» YA ESTABA en el prompt que se le manda a Whisper: el prompt es una
# pista de contexto, no un diccionario que obligue, y con 990 de 1000 caracteres
# ocupados por códigos de modelo la señal de una marca se diluye. Meter los 30
# fabricantes ahí habría diluido más, no menos.
#
# Un nombre de fabricante mal transcrito cuesta MUCHO más que un modelo mal
# transcrito: sin marca, el turno entero se queda sin ancla y la respuesta es
# «no tengo eso», que es justo la respuesta que hunde la confianza de quien
# prueba el bot por primera vez.
#
# DISCIPLINA (la misma que `_MANUFACTURER_ALIASES` del retriever, curada a mano y
# CORTA a propósito): aquí **sólo entra lo OBSERVADO en una transcripción real**.
# Nada de confusiones hipotéticas: cada entrada inventada es una forma nueva de
# corromper una pregunta que estaba bien. Al añadir una, se cita dónde se vio.
#
# (s332 §3) Fila = (patron, correcto, modo, case_sensitive, flag, cita).
#   · `modo`      'reescrito' sustituye el texto; 'aviso' lo deja INTACTO y sólo
#                 declara la confusión (para confusiones con lectura legítima).
#   · `case_sensitive`  el IGNORECASE es POR FILA: global cazaría el «id» español
#                 (imperativo de «ir») en la fila `ID`.
#   · `flag`      None = fila SIEMPRE activa (la conducta desplegada en s324f);
#                 'ASR_AVISOS' = fila gobernada por el lever (default off).
_CONFUSIONES_OBSERVADAS: tuple[tuple[str, str, str, bool, str | None, str], ...] = (
    (r"death\s+knob", "Detnov", "reescrito", False, None,
     "17-ago-2026 piloto: audio Detnov→«Death Knob»"),
    (r"bqide", "Kidde", "reescrito", False, "ASR_AVISOS",
     "query_logs 02055e5d 21-ago: audio Kidde→«BQide»"),
    # 4ª y 5ª corrupciones OBSERVADAS de «Kidde» en un solo día (verificado: ni
    # «kide» ni «itide» existen como marca, término gobernado ni token del corpus).
    (r"kide", "Kidde", "reescrito", False, "ASR_AVISOS",
     "query_logs 044c584a 21-ago 13:27Z: audio «Quería decir de KIDE»"),
    (r"itide", "Kidde", "reescrito", False, "ASR_AVISOS",
     "query_logs 11469925 21-ago 13:27Z: audio Kidde→«ITIDE»"),
    # 8ª corrupción observada de «Kidde» (verificado: «quide» no existe como marca,
    # alias, término gobernado ni token del corpus — 0 hits en chunks_v2). Con esta
    # fila, «Quería decir quide» recorre la cadena entera tabla→plantilla→rebuild
    # (la ruta verificada de s334 con KIDE). Su gemela «quiere» (7ª, misma
    # conversación) NO se tabula JAMÁS: palabra española real con 145 apariciones
    # en el corpus — reescribirla corrompería texto legítimo. Hueco declarado.
    (r"quide", "Kidde", "reescrito", False, "ASR_AVISOS",
     "query_logs f8dcb59a 21-ago 15:54Z: audio «Quería decir quide.»"),
    # Sin IGNORECASE y sólo aislada: `\b` no corta ID3000/ID3002/IDNet (letra→dígito
    # y letra→letra no son frontera), y «id» minúscula queda fuera. Modo `aviso`
    # porque la familia ID existe de verdad: reescribir sería corromper al legítimo.
    (r"ID", "Kidde", "aviso", True, "ASR_AVISOS",
     "query_logs 2b3febb6/838e71a6 21-ago (misma conversación) + testimonio de Alberto"),
)


def _compilar(filas) -> tuple[tuple[re.Pattern[str], str, str, str | None], ...]:
    """Compila la tabla respetando `case_sensitive` POR FILA. `modo` es enum cerrado:
    un valor no reconocido revienta al importar, no en mitad de un turno."""
    compiladas = []
    for patron, correcto, modo, case_sensitive, flag, _cita in filas:
        if modo not in ("reescrito", "aviso"):
            raise RuntimeError(
                f"modo de fila no reconocido: {modo!r} (reescrito|aviso) — fail-fast")
        banderas = 0 if case_sensitive else re.IGNORECASE
        compiladas.append((re.compile(rf"\b{patron}\b", banderas), correcto, modo, flag))
    return tuple(compiladas)


_CONFUSIONES = _compilar(_CONFUSIONES_OBSERVADAS)


def asr_avisos_on() -> bool:
    """Lever `ASR_AVISOS` (s332 §5): gatea las filas NUEVAS de la tabla y las líneas
    🏷/ℹ️ de la confirmación de voz. Default off = conducta servida byte-idéntica (la
    fila `death knob` de s324f sigue corrigiendo, y sigue muda).

    Se lee en CADA llamada, sin caché de módulo: un flip en Railway togglea sin
    restart. Parser ESTRICTO (patrón `mismatch_answer_activo`/`_strict_on_off`): un
    typo no puede dejar el lever a medias EN SILENCIO.
    """
    raw = (os.getenv("ASR_AVISOS", "") or "").strip().lower()
    if raw in ("", "off"):
        return False
    if raw == "on":
        return True
    raise RuntimeError(f"ASR_AVISOS={raw!r} no reconocido (on|off) — fail-fast")


def corregir_transcripcion_con_asunciones(texto: str) -> tuple[str, tuple[Asuncion, ...]]:
    """Aplica la tabla y DEVUELVE, además del texto, las asunciones que hizo.

    El único llamador es `normalize_voice_query`, así que el contexto `source=voice`
    es por CONSTRUCCIÓN: un turno ESCRITO no pasa por aquí, y por tanto la fila
    `ID`→Kidde no puede tocarlo (la restricción «solo voz» de la spec no necesita
    un parámetro que otro llamador podría rellenar mal).

    Una fila que casa varias veces produce UNA sola asunción, con la PRIMERA
    aparición como `detectado`: el aviso nombra lo que el técnico oyó decir a
    Whisper, no un recuento.
    """
    if not texto:
        return texto, ()
    avisos = asr_avisos_on()
    asunciones: list[Asuncion] = []
    for patron, correcto, modo, flag in _CONFUSIONES:
        if flag is not None and not avisos:
            continue
        match = patron.search(texto)
        if match is None:
            continue
        detectado = match.group(0)
        if modo == "reescrito":
            texto = patron.sub(correcto, texto)
        if avisos:
            asunciones.append(Asuncion(
                kind="marca_asr", detectado=detectado, asumido=correcto, modo=modo))
    return texto, tuple(asunciones)


def corregir_transcripcion(texto: str) -> str:
    """Repara confusiones fonéticas CONOCIDAS de Whisper sobre nombres del dominio.

    Se aplica a la transcripción antes de que nadie la use, así que la forma
    corregida llega a la búsqueda Y a la columna `query` de `query_logs`; el ASR
    crudo queda VISIBLE en la confirmación 🎤 y en la columna `transcription`. Las
    dos mitades son el contrato: se busca por lo corregido y se audita por lo dicho.

    Conservadora por construcción: límites de palabra, sin tocar nada que no esté
    en la tabla, y devuelve la entrada tal cual si no hay coincidencia.

    Envoltorio de compatibilidad de `corregir_transcripcion_con_asunciones` (s332):
    conserva la firma para quien sólo quiere el texto.
    """
    return corregir_transcripcion_con_asunciones(texto)[0]


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
