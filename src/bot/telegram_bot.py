"""
Telegram bot for PCI technicians.
Receives questions, queries the RAG pipeline, and returns formatted answers with diagrams.
"""

import asyncio
import json
import logging
import os
import re
import tempfile
import time as _time
import unicodedata
import uuid
from pathlib import Path

import httpx
from telegram import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    ReplyKeyboardRemove,
    Update,
)
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from ..config import (
    TELEGRAM_BOT_TOKEN,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    RETRIEVAL_TOP_K,
    RERANK_TOP_K,
    LLM_MODEL,
    REWRITER_MODEL,
    VOICE_TRANSCRIPTION_MODEL,
    COVERAGE_RELEASE_POLICY,
    CONVO_SHADOW,
    CONVO_MAINTENANCE,
    validate_config,
)
from ..rag.retriever import (
    extract_product_models, get_category_models,
    get_manufacturers_by_docs, get_products_by_manufacturer,
    _MANUFACTURER_ALIASES, resolve_manufacturer_alias,
    get_all_models_by_category, CATEGORY_TERMS, PCI_TERMS,
    lookup_model_manufacturer, get_available_manufacturers, manufacturer_in_db,
)
# s319 PR-C: retrieve_chunks/rerank/generate_answer/RagServingAdapters/
# execute_rag_turn ya NO se importan aquí — el handler dejó de construir el
# pipeline inline; los adapters de producción los arma el orquestador
# (from_production) y el seam execute_rag_turn vive en serving_pipeline.
from ..rag.runtime_trace import build_rag_serving_trace
from ..logging_db import (
    log_query,
    log_bot_error,
    log_feedback,
    log_answer_feedback,
    set_feedback_reason,
    set_feedback_comment,
    has_feedback_reason,
    query_log_id_for_message,
    stamp_answer_messages,
    has_consent,
    set_consent,
    seudonimo_de,
    asegurar_seudonimo,
)
from .response_formatter import (
    DEFAULT_MESSAGE_LIMIT,
    format_telegram_messages,
    telegram_html_to_plain,
)
from .audio_input import audio_file_suffix
from . import error_taxonomy
from .voice_query_normalization import normalize_voice_query
from .whisper_vocabulary import get_whisper_prompt

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_EMPTY_ANSWER_FALLBACK = (
    "No he podido generar una respuesta completa y segura. Inténtalo de nuevo."
)

# S281 Phase-1 (F1) direct-route copy. A CLARIFY turn answers with the policy's
# ``clarify_question`` verbatim (already user-facing prose); a DECLINE turn maps
# its rationale CODE (``decline_reason`` is a trace token, never shown raw) to a
# user-facing message. No gold exercises DECLINE (conversation_policy_impl
# docstring) — the map keeps the single served reason honest, with a fallback.
_F1_DECLINE_MESSAGES = {
    "fuera_de_dominio_pci_fuego": (
        "Esa consulta queda fuera del dominio que cubro (protección contra "
        "incendios). ¿Puedo ayudarte con algún equipo o sistema de detección o "
        "extinción de incendios?"
    ),
}
_F1_DECLINE_DEFAULT = (
    "Esa consulta queda fuera del dominio de PCI (protección contra incendios) "
    "que cubro. ¿Puedo ayudarte con algún equipo de detección o extinción?"
)
_INVISIBLE_GRAPHIC_CODEPOINTS = frozenset("\u2800\u3164\u115f\u1160\uffa0")


def _has_visible_text(value: object) -> bool:
    """Require a visible letter, number, punctuation mark, or symbol."""
    if not isinstance(value, str):
        return False
    return any(
        character not in _INVISIBLE_GRAPHIC_CODEPOINTS
        and unicodedata.category(character)[0] in {"L", "N", "P", "S"}
        for character in value
    )


def _plain_transport_parts(text: str) -> list[str]:
    """Last-resort Telegram-safe split with formatting disabled."""
    value = str(text or "")
    if not _has_visible_text(value):
        value = _EMPTY_ANSWER_FALLBACK
    return [
        value[index : index + DEFAULT_MESSAGE_LIMIT]
        for index in range(0, len(value), DEFAULT_MESSAGE_LIMIT)
    ]

# Silence httpx / httpcore INFO logs — they emit each HTTP request URL in
# clear text, which leaks secrets that live in the URL itself (notably the
# Telegram bot token, which Telegram embeds in the path:
#   POST https://api.telegram.org/bot<TOKEN>/getUpdates).
# Supabase and Anthropic put their secrets in headers (not URLs), but we
# silence at this level for defense in depth across all current and future
# endpoints. App-level INFO logs (this module, ingestion, RAG) are unaffected.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# --- Pre-pipeline classifiers (s316e, fase A DEC-200) ---
# Los clasificadores y el predicado de la guardia viven en orchestrator/turn_plan.py --
# el punto de decision UNICO del turno. Aqui quedan re-exports (compatibilidad de
# tests/scripts) y los WRAPPERS con el fetch perezoso de la lista de marcas.
from ..orchestrator import turn_plan as _turn_plan  # noqa: E402
from ..orchestrator.conversation_policy import WorkingState  # noqa: E402
from ..orchestrator.turn_plan import (  # noqa: E402,F401 -- re-exports deliberados
    _BYE_PATTERNS, _CATALOG_PATTERNS, _ENUM_FABRICANTE, _FEEDBACK_PATTERNS,
    _GREETING_PATTERNS, _MANUFACTURER_NAMES, _MARCAS_AMBIGUAS, _PREGATE_INVENTARIO,
    _SWITCH_FRASE, _THANKS_PATTERNS, _VOCABULARIO_DOMINIO, Hecho, Meta, TurnPlan,
    _intencion_inventario, plan_turn, plan_turn_hechos,
)


def _aplicar_estado(user_data: dict, ws) -> None:
    """El UNICO punto de escritura de `mt_working_state` (invariante de fase B,
    fijado por AST en el instrumento). Toda transicion -- plan (INVALIDAR), politica
    F1 (resolve/backfill) o `transicion_basica` (regimen stub) -- se produce como
    VALOR puro y se aplica aqui. El cluster de telemetria de feedback
    (`last_query`/`last_response`/`last_query_log_id`) queda FUERA del invariante:
    ancla feedback, no conversacion (dueno declarado: _process_query)."""
    user_data["mt_working_state"] = ws


def _lexico_marcas_cacheado():
    """La lista de marcas para la decision de invalidacion y el 5-bis: UNA disciplina
    de cache (proceso, fallo no cacheado) para TODOS los consumidores. (Fable r-build
    m6: la guardia historica hacia fetch FRESCO por turno de switch mientras el plan
    usaba la cache -- al retirar la guardia, la disciplina queda unificada en cache;
    coste: una marca ingestada mid-proceso no dispara switches hasta el restart, que
    ya es la norma operativa del resto de consumidores de la lista)."""
    global _marcas_db_cache
    if _marcas_db_cache is None:
        try:
            _marcas_db_cache = get_available_manufacturers()
        except Exception:                        # noqa: BLE001 -- fail-open
            return None
    return _marcas_db_cache


def _estado_modelos_conversacion(user_data: dict) -> tuple[str, ...]:
    """Marshalling MECANICO (sin decision): los modelos del estado vivo + legacy."""
    ws = user_data.get("mt_working_state")
    return tuple(getattr(ws, "last_target_models", ()) or ())


# (fase B, DEC-200 v3) La guardia de grupo -1 (`brand_switch_guard`) y su nucleo
# (`_invalidar_si_cambio_de_marca`) se RETIRARON: la invalidacion es la transicion del
# plan, aplicada por el escritor unico en handle_message (texto) y handle_voice (voz).
# El predicado sigue siendo turn_plan._decidir_transicion -- el mismo codigo que la
# guardia ejecutaba, ahora con una sola fuente activa y sin doble computo por turno.


# s286 telemetría: feedback 1-tap 👍/👎. TELEGRAM_FEEDBACK (default off =
# byte-idéntico) gatea SOLO el attach del keyboard; el CallbackQueryHandler se
# registra INCONDICIONALMENTE en run_bot para que un keyboard viejo en el
# historial siempre resuelva (apagar el flag no deja botones muertos girando).
# callback_data autocontenido "fb:u:<uuid>"/"fb:d:<uuid>" (41 bytes < 64 de
# Telegram) → taps tras días/restart funcionan sin estado en memoria.
_FEEDBACK_CALLBACK_PATTERN = re.compile(r"^fb:(u|d):([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$")

# s294 (#60 punto 5): motivo del 👎. Comparte el prefijo `fb:` A PROPÓSITO para
# entrar por el MISMO CallbackQueryHandler (registrado incondicionalmente): un
# teclado viejo en el historial siempre resuelve su spinner, aunque el flag esté
# apagado. "fb:r:wrong:<uuid>" = 46 bytes < 64 de Telegram.
_FEEDBACK_REASON_PATTERN = re.compile(
    r"^fb:r:(info|wrong|scope|other):"
    r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$"
)
_FEEDBACK_EXPLAIN_PATTERN = re.compile(
    r"^fb:x:([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$"
)
# Texto adjudicado por Alberto: es el MISMO acuse que el canal de texto libre
# (`handle_feedback`), para que el tecnico vea la misma respuesta venga por donde venga.
_FEEDBACK_REASON_PROMPT = (
    "Gracias por el aviso 🙏\n\n"
    "Tu feedback queda registrado. ¿Puedes indicarme qué dato concreto "
    "es incorrecto y qué dice el manual? Así podré mejorar."
)
# «Otra cosa» sale: en la prueba real de Alberto fue la unica que encajaba con
# «la ruta de menu esta mal anidada» y no informaba de nada. Su hueco lo ocupa la
# ACCION de explicar, que es lo que si informa.
_FEEDBACK_REASON_LABELS = (
    ("info", "Faltó información"),
    ("wrong", "Dato incorrecto"),
    ("scope", "No era mi pregunta"),
)
_FEEDBACK_EXPLAIN_LABEL = "✍️ Te lo explico"
# ForceReply es el mecanismo NATIVO de Telegram para esto: el cliente abre la caja
# apuntando a este mensaje, asi que el siguiente mensaje ES un reply por construccion
# y se ancla exacto. Si el tecnico pasa y pregunta otra cosa, la escribe en el chat
# normal y el bot la responde como siempre — la ambiguedad se resuelve por diseno.
_FEEDBACK_EXPLAIN_PROMPT = (
    "Cuéntame qué dato es incorrecto y qué dice el manual 👇"
)
_FEEDBACK_EXPLAIN_PLACEHOLDER = "El manual dice…"
_FEEDBACK_EXPLAIN_ACK = "Anotado 👍"


def _feedback_keyboard_enabled() -> bool:
    return os.getenv("TELEGRAM_FEEDBACK", "off").strip().lower() == "on"


def _feedback_reason_enabled() -> bool:
    """Flag propio (default off), independiente del teclado 👍/👎: el follow-up
    añade un mensaje más por cada 👎 y esa conducta se enciende aparte."""
    return os.getenv("TELEGRAM_FEEDBACK_REASON", "off").strip().lower() == "on"


def _feedback_reason_keyboard(query_log_id: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(label, callback_data=f"fb:r:{code}:{query_log_id}")
        for code, label in _FEEDBACK_REASON_LABELS
    ]
    explain = InlineKeyboardButton(
        _FEEDBACK_EXPLAIN_LABEL, callback_data=f"fb:x:{query_log_id}"
    )
    return InlineKeyboardMarkup([buttons[:2], [buttons[2], explain]])


def _error_logging_enabled() -> bool:
    return os.getenv("BOT_ERROR_LOGGING", "off").strip().lower() == "on"


def _error_reply_enabled() -> bool:
    """Kill-switch del MENSAJE de error al técnico (s324e). Default ON.

    Va aparte de `BOT_ERROR_LOGGING` porque son dos mecanismos con dos riesgos
    distintos — la disciplina de s317 (#72): cada mecanismo lleva el suyo. Aquí
    el default es ON y no OFF, al contrario que el resto de flags nuevas del
    repo, y es deliberado: la conducta de HOY es el silencio, y una red de
    seguridad apagada por defecto no es una red de seguridad. Apagarlo devuelve
    exactamente el silencio de hoy, sin deploy, si en el piloto apareciera un
    bucle de mensajes de error que no hayamos previsto.
    """
    return os.getenv("BOT_ERROR_REPLY", "on").strip().lower() not in {
        "off", "0", "false", "no"
    }


def _feedback_keyboard(query_log_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍", callback_data=f"fb:u:{query_log_id}"),
        InlineKeyboardButton("👎", callback_data=f"fb:d:{query_log_id}"),
    ]])


# Feedback detection: _FEEDBACK_PATTERNS vive en turn_plan (re-export arriba).
# (Fable r-build, m3) Aqui habia un re.compile DUPLICADO que sombreaba el re-export:
# funcionaba solo por el cache de `re`, y editar una copia desincronizaria el serving
# (el plan usa la de turn_plan) de quien leyera bot._FEEDBACK_PATTERNS.


# ── Resumen de fabricantes (s307) ────────────────────────────────────────────
# La intro decía «Notifier, Morley y Detnov» desde el primer día, con 30
# fabricantes reales en corpus (lo señaló Alberto con el pantallazo del /accept).
# La lista se deriva de `documents` (status=active) UNA vez por proceso — otra
# constante solo volvería a caducar en el fabricante 31. Fail-open al texto
# genérico: un hiccup de la base jamás rompe un saludo. El fallo NO se cachea
# (el siguiente saludo reintenta); el éxito sí.
_FABRICANTES_TOP_N = 5
_FABRICANTES_FALLBACK = ("*Notifier*, *Morley*, *Detnov* y más fabricantes de PCI", None)
_fabricantes_cache: tuple[str, int | None] | None = None


def _fabricantes_resumen() -> tuple[str, int | None]:
    """(línea de marcas en Markdown, nº total) — p.ej. («*Notifier*, …», 30)."""
    global _fabricantes_cache
    if _fabricantes_cache is not None:
        return _fabricantes_cache
    try:
        marcas = get_manufacturers_by_docs()
        if not marcas:
            return _FABRICANTES_FALLBACK
        top = ", ".join(f"*{m}*" for m, _ in marcas[:_FABRICANTES_TOP_N])
        linea = f"{top} y más" if len(marcas) > _FABRICANTES_TOP_N else top
        _fabricantes_cache = (linea, len(marcas))
    except Exception as exc:                             # noqa: BLE001
        logger.warning("resumen de fabricantes fail-open (%s)", type(exc).__name__)
        return _FABRICANTES_FALLBACK
    return _fabricantes_cache


_inventario_cache: dict[str, str] = {}
_inventario_falla_ts: float = 0.0
_FALLA_BACKOFF_S = 60.0            # tras un fallo de DB, no re-pagar el timeout en
                                   # cada consulta (dúo H5: httpx síncrono en handler
                                   # async — con DB caída bloqueaba el loop por turno)
_PRESUPUESTO_MSG = 3500            # dúo H1: el inventario de Notifier medía 4.377
                                   # chars > límite Telegram 4.096 → BadRequest sin
                                   # handler = el técnico recibía NADA. Cota por
                                   # CONSTRUCCIÓN, no por confianza.


def _pm_plano(pm: str) -> str:
    """Markdown v1 de Telegram rompe con `*`/`_`/`` ` `` sueltos en nombres de
    producto — se sirven planos (Sol s307: un metacarácter en un pm = BadRequest)."""
    return pm.replace("*", "").replace("_", " ").replace("`", "")


def _norm_marca(s: str) -> str:
    import unicodedata as _ud
    plano = _ud.normalize("NFKD", s or "")
    plano = "".join(c for c in plano if not _ud.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", plano)


def _productos_marca(cat, nombre: str) -> list[dict]:
    """Productos del catálogo «que tenemos» para una marca: activos, no
    candidatos, de la marca (prefijo del id o vendido_bajo) y CON docs
    mapeados (catálogo ∩ doc_map — r27 Fable C1: jamás los pm de chunks)."""
    marca_nk = _norm_marca(nombre)
    con_docs = set()
    for dm in cat.doc_map:
        for e in dm.get("entries") or ():
            con_docs.add(cat.follow_redirect(e["id"]))
    propios = []
    for pid, p in cat.products.items():
        if p.get("estado") != "activo" or p.get("candidate"):
            continue
        if not (pid.split(":")[0] == marca_nk
                or any(_norm_marca(v) == marca_nk
                       for v in p.get("vendido_bajo") or ())):
            continue
        if cat.follow_redirect(pid) in con_docs:
            propios.append(p)
    return propios


def _inventario_filtrado(nombre: str, filtros: dict) -> str | None:
    """(s322 #76, DEC-216) Vista de inventario CON FILTROS, desde el CATÁLOGO
    gobernado (r27 Fable C1: los pm de chunks son strings de FAMILIA por diseño
    T3 — el join es catálogo ∩ doc_map, no los pm). None → el llamador degrada
    a la lista completa con línea honesta (jamás lista falsa ni omisión muda).
    """
    from ..rag.catalog_resolver import catalogo_cargado

    cat = catalogo_cargado()
    if cat is None:
        return None
    propios = _productos_marca(cat, nombre)
    if not propios:
        return None
    clasificados = [p for p in propios if p.get("clasificacion")]
    sin_clasificar = len(propios) - len(clasificados)

    def _casa(p: dict) -> tuple[str | None, list[str]]:
        """(descripción|None, faltantes). None = CONTRADICE un filtro con dato;
        faltantes = filtros sin dato ANCLADO en el producto — excluirlo en
        silencio sería mentir por omisión, listarlo como «casa» sería inventar:
        va a su propia sección. (El caso CAD-150-4 original se resolvió luego
        por la regla de sufijo adjudicada por Alberto — derivación DECLARADA en
        la propia cita, no verbatim; ver evals/s322_76_sufijo_cad150_v1.json.)
        Inaplicable ≠ faltante (r28 Fable M2): si el producto ancla la
        capacidad HERMANA (zonas cuando se piden lazos, o viceversa) o su
        tecnología lo delata (convencional⇒sin lazos analógicos), el atributo
        no es «dato ausente» sino concepto ajeno → se EXCLUYE."""
        partes, faltantes = [], []
        if "categoria" in filtros:
            if p["clasificacion"].get("categoria") != filtros["categoria"]:
                return None, []
            partes.append(p["clasificacion"]["categoria"])
        at = p.get("atributos") or {}
        if "tecnologia" in filtros:
            vals = {v.get("valor") for v in at.get("tecnologia") or ()}
            if not vals:
                faltantes.append("tecnología")
            elif filtros["tecnologia"] not in vals:
                return None, []
            else:
                partes.append(filtros["tecnologia"])
        for clave, hermana in (("lazos", "zonas"), ("zonas", "lazos")):
            if clave not in filtros:
                continue
            n = filtros[clave]
            rangos = [(v.get("base"), v.get("max", v.get("base")))
                      for v in at.get(clave) or ()]
            if not rangos:
                # (r28 Fable M2) ¿ausente o INAPLICABLE? Una convencional con
                # zonas ancladas no «carece del dato» de lazos: no tiene lazos
                # como concepto. Señales: la capacidad hermana anclada, o la
                # tecnología incompatible con la clave pedida.
                tecs = {v.get("valor") for v in at.get("tecnologia") or ()}
                inaplicable = bool(at.get(hermana)) or (
                    "convencional" in tecs if clave == "lazos"
                    else bool(tecs & {"analogica", "algoritmica"}))
                if inaplicable:
                    return None, []
                faltantes.append(clave)
            else:
                # Semántica de CAPACIDAD (adjudicada por Alberto 14-ago):
                # «N lazos» = «hasta N» — una central de 8 SIRVE para 4.
                # El filtro es N ≤ max; base queda descriptivo. Ídem zonas
                # (convencionales): mismas reglas, claves separadas.
                caben = [m for _b, m in rangos if isinstance(m, int) and n <= m]
                if not caben:
                    return None, []
                partes.append(f"hasta {max(caben)} {clave}")
        return ", ".join(partes), faltantes

    evaluados = [(p, *_casa(p)) for p in clasificados]
    casan = [(p, d) for p, d, falt in evaluados if d is not None and not falt]
    parciales = [(p, d, falt) for p, d, falt in evaluados
                 if d is not None and falt]
    if not clasificados:
        return None                # población pendiente → lista completa honesta
    nombre_visible = nombre if nombre != nombre.lower() else nombre.title()
    desc = " ".join(
        (f"{filtros[k]} {k}" if k in ("lazos", "zonas") else str(filtros[k]))
        for k in ("categoria", "tecnologia", "lazos", "zonas") if k in filtros)
    if not casan and not parciales:
        lineas = [f"📦 De *{nombre_visible}*, ninguno de los {len(clasificados)} "
                  f"productos clasificados casa con «{desc}»."]
        if sin_clasificar:
            lineas.append(f"_(hay {sin_clasificar} productos aún sin clasificar "
                          f"— puedo estar ciego ahí)_")
        lineas.append("¿Quieres el inventario completo o pregunto de otra forma?")
        return "\n".join(lineas)
    lineas = [f"📦 *{nombre_visible} — {desc}* "
              f"({len(casan)} de {len(propios)} productos):\n"] if casan else [
        f"📦 De *{nombre_visible}*, ninguno tiene TODOS los datos de «{desc}» "
        f"anclados en su manual — los que casan en lo demás:\n"]
    for p, d in sorted(casan, key=lambda x: _clave_natural(
            x[0].get("canonical_model") or "")):
        lineas.append(f"• *{_pm_plano(p.get('canonical_model') or p['id'])}* — {d}")
    if parciales:
        lineas.append("\n_Casan en lo anclado pero su manual no especifica "
                      "el resto:_")
        for p, d, falt in sorted(parciales,
                                 key=lambda x: _clave_natural(
                                     x[0].get("canonical_model") or "")):
            lineas.append(f"• *{_pm_plano(p.get('canonical_model') or p['id'])}*"
                          f" — {d}; sin dato de {'/'.join(falt)} en el manual")
    if sin_clasificar:
        lineas.append(f"\n_(y {sin_clasificar} productos de {nombre_visible} "
                      f"aún sin clasificar por categoría/atributos)_")
    lineas.append("\n¿Sobre cuál necesitas información?")
    return "\n".join(lineas)


# (s322, Alberto 14-ago) Vista agrupada del inventario sin filtros.
_CATEGORIA_ORDEN = ("central", "detector", "pulsador", "sirena", "modulo",
                    "fuente", "repetidor", "aspiracion", "barrera",
                    "retenedor", "pasarela", "software", "accesorio")
_CATEGORIA_PLURAL = {
    "central": "Centrales", "detector": "Detectores",
    "pulsador": "Pulsadores", "sirena": "Sirenas", "modulo": "Módulos",
    "fuente": "Fuentes de alimentación", "repetidor": "Repetidores",
    "aspiracion": "Aspiración", "barrera": "Barreras",
    "retenedor": "Retenedores", "pasarela": "Pasarelas",
    "software": "Software", "accesorio": "Accesorios",
}


def _clave_natural(s: str) -> list:
    """Orden natural (r28 Fable m1): CAD-150-4 antes que CAD-150-12 — el sort
    de strings puro invierte variantes numéricas."""
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", s or "")]


def _inventario_agrupado(nombre: str) -> str | None:
    """(s322, Alberto 14-ago) El inventario GENÉRICO («¿qué productos X
    tienes?») agrupado por tipología y ordenado por familia — no un listado
    plano infinito. Generalizable porque vive en el RENDER de la ruta de
    inventario, no en un phrasing: cualquier consulta que el plan despache a
    inventario sin filtros pasa por aquí. El orden alfabético del modelo
    canónico agrupa las familias por prefijo (CAD-150-*, KE-AS31*). Cota
    `_PRESUPUESTO_MSG` por construcción: TODA categoría aparece siempre con su
    conteo; los modelos que no caben se resumen «…y N más» (la pregunta por
    categoría da la vista completa). None → lista plana de siempre (marca sin
    clasificación o catálogo caído — la degradación honesta ya existente)."""
    from ..rag.catalog_resolver import catalogo_cargado

    cat = catalogo_cargado()
    if cat is None:
        return None
    propios = _productos_marca(cat, nombre)
    if not propios:
        return None
    grupos: dict[str, list[tuple]] = {}
    sueltos = 0
    for p in propios:
        cl = p.get("clasificacion")
        if cl:
            modelo = _pm_plano(p.get("canonical_model") or p["id"])
            # (r28 Sol M4) `familia` es campo GOBERNADO del catálogo: ordena
            # por (familia, modelo) — Morley ZXe/ZXSe se intercalarían en
            # orden alfabético puro. Sin familia declarada, el modelo es su
            # propia familia-de-uno (conserva la adyacencia por prefijo).
            fam = p.get("familia") or modelo
            grupos.setdefault(cl["categoria"], []).append(
                (_clave_natural(fam), _clave_natural(modelo), modelo))
        else:
            sueltos += 1
    if not grupos:
        return None
    nombre_visible = nombre if nombre != nombre.lower() else nombre.title()
    cabecera = (f"📦 *Productos de {nombre_visible} en mi documentación* "
                f"({len(propios)} productos):\n")
    cierre = ("\n_Pregunta por una categoría («¿qué sirenas tienes?») o por "
              "un modelo concreto._")
    lineas = [cabecera]
    usado = len(cabecera) + len(cierre) + 90    # margen: cola sin-clasificar
    pendientes = [c for c in _CATEGORIA_ORDEN if grupos.get(c)]
    for i, categoria in enumerate(pendientes):
        nombres = [t[-1] for t in sorted(grupos[categoria])]
        titulo = _CATEGORIA_PLURAL.get(categoria, categoria.title())
        linea = f"*{titulo}* ({len(nombres)}):"
        # (r28 Sol m1/Fable M1) La cota es POR CONSTRUCCIÓN también para los
        # encabezados: si ni el título+resumen caben, las categorías restantes
        # se compactan en una línea — jamás se apéndiza sin re-chequear.
        if usado + len(linea) + 40 > _PRESUPUESTO_MSG:
            resto = pendientes[i:]
            lineas.append(f"…y {len(resto)} categorías más "
                          f"({', '.join(_CATEGORIA_PLURAL.get(c, c).lower() for c in resto)})"
                          [:120])
            break
        mostrados = 0
        for nm in nombres:
            candidata = linea + (" " if not mostrados else " · ") + nm
            if usado + len(candidata) + 26 > _PRESUPUESTO_MSG:  # 26≈«…y NN más»
                break
            linea, mostrados = candidata, mostrados + 1
        if mostrados < len(nombres):
            linea += f" …y {len(nombres) - mostrados} más"
        lineas.append(linea)
        usado += len(linea) + 1
    if sueltos:
        lineas.append(f"\n_(y {sueltos} productos aún sin clasificar por "
                      f"tipología)_")
    lineas.append(cierre)
    return "\n".join(lineas)


def _inventario_fabricante(nombre: str, filtros: dict | None = None) -> str | None:
    """Respuesta de inventario para un fabricante, o None para caer al RAG.

    Del corpus, no de una ventana de retrieval; ACOTADA a `_PRESUPUESTO_MSG` por
    construcción (las que no caben se resumen en «…y N más»); «referencias» y no
    «modelos» (varias marcas taguean a FAMILIA — deliberado, T3/s285). Éxito
    cacheado por proceso; fallo NO cacheado pero con backoff (60 s) y → RAG.
    s322 #76: `filtros` tipados del plan → vista del catálogo gobernado con
    clave de caché COMPUESTA (r27: la caché por-marca se contaminaría); si la
    vista no puede (catálogo caído / marca sin catalogar / sin clasificación),
    degrada a la lista completa CON línea honesta de por qué.
    """
    global _inventario_falla_ts
    nombre = resolve_manufacturer_alias(nombre)   # s308/#67: «lda» → LDA audioTech
    if filtros:
        clave_f = (nombre.strip().lower() + "|"
                   + json.dumps(filtros, sort_keys=True))
        if clave_f in _inventario_cache:
            return _inventario_cache[clave_f]
        try:
            respuesta = _inventario_filtrado(nombre, filtros)
        except Exception as exc:                  # noqa: BLE001
            logger.warning("inventario filtrado fail-open a lista completa (%s)",
                           type(exc).__name__)
            respuesta = None
        if respuesta is not None:
            _inventario_cache[clave_f] = respuesta
            return respuesta
        completo = _inventario_fabricante(nombre)
        if completo is None:
            return None
        respuesta = ("_Aún no tengo la clasificación por categoría/atributos "
                     "cargada para este fabricante — te muestro el inventario "
                     "completo:_\n\n" + completo)
        _inventario_cache[clave_f] = respuesta
        return respuesta
    clave = nombre.strip().lower()
    if clave in _inventario_cache:
        return _inventario_cache[clave]
    # (s322, Alberto) La vista agrupada va ANTES del backoff de DB: sale del
    # catálogo local, no de la DB — puede servir incluso con la DB caída.
    try:
        agrupado = _inventario_agrupado(nombre)
    except Exception as exc:                             # noqa: BLE001
        logger.warning("inventario agrupado fail-open a lista plana (%s)",
                       type(exc).__name__)
        agrupado = None
    if agrupado is not None:
        _inventario_cache[clave] = agrupado
        return agrupado
    if _time.time() - _inventario_falla_ts < _FALLA_BACKOFF_S:
        return None                                       # DB tocada hace nada → RAG
    try:
        productos = get_products_by_manufacturer(nombre)
    except Exception as exc:                             # noqa: BLE001
        _inventario_falla_ts = _time.time()
        logger.warning("inventario de fabricante fail-open a RAG (%s)",
                       type(exc).__name__)
        return None
    if not productos:
        return None                                       # sin datos → RAG decide
    # (dúo s308) .title() destrozaba los nombres reales («LDA audioTech» →
    # «Lda Audiotech»): solo se titula la mención toda-minúscula del usuario.
    nombre_visible = nombre if nombre != nombre.lower() else nombre.title()
    cabecera = (f"📦 *Productos de {nombre_visible} en mi documentación* "
                f"({len(productos)} referencias):\n")
    cierre = "\n¿Sobre cuál necesitas información?"
    lineas, usado, fuera = [cabecera], len(cabecera) + len(cierre) + 40, 0
    for pm, n_docs in productos:
        docs = "1 documento" if n_docs == 1 else f"{n_docs} documentos"
        linea = f"• *{_pm_plano(pm)}* — {docs}"
        if usado + len(linea) > _PRESUPUESTO_MSG:
            fuera += 1
            continue
        lineas.append(linea)
        usado += len(linea) + 1
    if fuera:
        lineas.append(f"\n…y {fuera} referencias más — dime cuál te interesa "
                      f"o pregunta por un modelo concreto.")
    lineas.append(cierre)
    _inventario_cache[clave] = "\n".join(lineas)
    return _inventario_cache[clave]


_marcas_db_cache: list[str] | None = None

# (s316g) Cliente del clasificador de intencion: UNA construccion por proceso
# (False = construccion fallida, no reintentar en caliente; un restart la reintenta).
_INTENT_FN_CELL: dict = {}


def _intent_seam(intent_obs: dict):
    """(s316h — gates del flip, DEC-203b) Seam INTENT_LLM del transporte.

    Extraido del handler para que el e2e del gate 2 ejecute ESTE codigo, no un
    simil (leccion r11: paridad medido<->servido). Devuelve el IntentFn perezoso
    con el flag ON, o None con OFF (= intent ausente en el resolve, byte-identico).

    `intent_obs` es POR TURNO y es el UNICO canal de telemetria del lever hacia
    la seccion `intent` de rag_trace (gate 1): el wrapper mide y estampa aqui, en
    el mismo hilo de la llamada. La lectura post-resolve de `fn.ultima` (atributo
    compartido a nivel proceso) sale del camino servido: dos turnos concurrentes
    podian pisarse la decision. `ultima` queda para el gate de juicio (secuencial).
    """
    if os.getenv("INTENT_LLM", "").strip().lower() not in {"1", "on", "true"}:
        intent_obs.update(status="off", decision="none", latency_ms=0)
        return None
    intent_obs.update(status="not_invoked", decision="none", latency_ms=0)

    def _lazy_intent(q_amb, ws):
        # celda a nivel PROCESO (Fable r11: por-turno reconstruia el cliente
        # httpx en cada turno = TLS frio por llamada; el gate midio con cliente
        # reutilizado — paridad medido<->servido). Sin lock a proposito (Fable
        # r12): dos primeros turnos concurrentes pueden construir dos clientes;
        # last-write-wins es benigno y un lock seria peso en el camino caliente.
        fn = _INTENT_FN_CELL.get("fn")
        if fn is None:
            # (Fable r11) el fallo de CONSTRUCCION (key mala, import) seria
            # tragado por el try de la rama del lever => flag ON roto en
            # SILENCIO justo en el rollout. Ruidoso y fail-open.
            try:
                from ..orchestrator.intent_llm import construir_intent_fn

                fn = construir_intent_fn(ANTHROPIC_API_KEY)
            except Exception as exc:      # noqa: BLE001
                logger.error("intent_llm: construccion FALLO (%s) — "
                             "flag ON degradado a conducta OFF",
                             type(exc).__name__)
                fn = False                # centinela: no reintentar
            _INTENT_FN_CELL["fn"] = fn
        if fn is False:
            intent_obs["status"] = "construction_failed"
            return None                   # fail-open declarado
        t0 = _time.perf_counter()
        decision = fn(q_amb, ws)
        # Todo lo que no es compat/switch se estampa fail_open porque ESO es lo
        # que la politica sirve (carry). El parser ESTRICTO de intent_llm ya
        # reduce el enum a {compat, switch, None}; un token nuevo del clasificador
        # jamas llega aqui sin tocar ese parser (Fable r12: el guard anti-drift
        # es el parser, no esta coercion).
        intent_obs.update(
            status="invoked",
            decision=decision if decision in ("compat", "switch") else "fail_open",
            latency_ms=int((_time.perf_counter() - t0) * 1000),
        )
        return decision

    return _lazy_intent


def _marca_en_consulta(query: str) -> str | None:
    """Shell de `turn_plan.marca_en_texto` con la cache de proceso de la lista DB
    (semantica de hoy: el fallo de fetch NO se cachea -- el siguiente intento
    reintenta; los alias curados resuelven aun sin lista)."""
    return _turn_plan.marca_en_texto(query, _lexico_marcas_cacheado())


def _welcome_text() -> str:
    linea, n = _fabricantes_resumen()
    cabecera = (
        f"Tengo los manuales de *{n} fabricantes* de PCI — {linea}. "
        if n else f"Tengo los manuales de {linea}. "
    )
    return (
        "🤖 *Asistente técnico PCI*\n\n"
        + cabecera
        + "Puedo ayudarte con:\n"
        "• Instalación y conexionado\n"
        "• Especificaciones técnicas\n"
        "• Configuración de centrales y módulos\n"
        "• Resolución de problemas\n\n"
        "Pregúntame en texto o envíame un *audio* 🎤.\n\n"
        "_Ejemplo: ¿Cómo configuro la central CAD-250?_"
    )


# AVISO EN DOS CAPAS (s295). La primera capa es lo que hay que saber ANTES de aceptar; el
# detalle completo vive en `/privacidad` y se puede leer sin haber aceptado nada. Motivo: los
# términos habían llegado a 25 líneas y 1.800 caracteres — un muro de texto como primer
# contacto se lee peor, y un aviso que nadie lee no informa a nadie. La completitud no se
# pierde, se mueve a donde no estorba.
#
# LOS DESTINATARIOS SE DESCRIBEN POR CATEGORÍA + lista actual (el RGPD pide «destinatarios o
# CATEGORÍAS de destinatarios»). Así, cambiar de proveedor dentro de la misma categoría no
# altera lo que la persona aceptó. Lo que NO se hace es declarar propósitos futuros para
# ahorrarse una re-aceptación: un consentimiento tiene que ser específico, y una cláusula que
# cubra «mejoras futuras» no autoriza nada — solo hace el aviso más vago hoy.
# ⚠️ s307: la línea de marcas de ABAJO también está stale (30 fabricantes reales), pero
# este texto es el que la gente ACEPTÓ (TERMS v7, gate por versión): cambiarlo exige bump
# a v8 + re-aceptación de todos, y el v8 ya está reservado para el cambio de base jurídica
# (PLAN, residuo RGPD) → la corrección de marcas VIAJA EN ESE BUMP, no antes. Además
# infra-promete (decimos menos de lo que hay), que es el lado seguro de un aviso.
_CONSENT_TERMS = (
    "🤖 *Asistente técnico PCI* — _versión beta_\n\n"
    "Te doy información de los manuales técnicos de *Notifier*, *Morley* y *Detnov*. "
    "Puedes preguntarme por texto o por audio 🎤.\n\n"
    "⚠️ *Antes de empezar*\n\n"
    "Para mejorar el sistema, guardamos *las preguntas que respondo y mis respuestas*, junto "
    "con tu ID de Telegram, el nombre que nos des al aceptar y tus valoraciones 👍/👎. Si "
    "mandas un audio, guardamos solo su transcripción: el audio original NO se guarda.\n\n"
    "*Cuánto*: 24 meses vinculado a ti; después se retira tu identificador de tus consultas "
    "y valoraciones.\n"
    "*Quién lo ve*: el equipo técnico de Fontiber. Para funcionar, tus preguntas pasan por "
    "proveedores de IA y de alojamiento que operan *fuera de la UE*.\n"
    "*Tus derechos*: escribe a *info@fontiber.com* para acceder o borrar tus datos.\n\n"
    "📄 Detalle completo (qué proveedores, para qué, y qué pasa a los 24 meses): /privacidad\n\n"
    "Para aceptar y empezar, envía:\n"
    "`/accept [tu nombre]`  _(el nombre es opcional pero ayuda a la revisión)_"
)


# SEGUNDA CAPA — accesible con /privacidad SIN haber aceptado nada, que es la condición para
# que la primera capa cuente como informada.
_PRIVACY_DETAIL = (
    "📄 *Privacidad — detalle completo*\n\n"
    "*Responsable*: Fontiber Industrial Partners, S.L. · CIF B24984759 · Calle de la Palma "
    "10, 28004 Madrid · *info@fontiber.com*\n"
    "*Base jurídica*: tu consentimiento, el que das al enviar `/accept`.\n\n"
    "*Qué se guarda*\n"
    "• Las preguntas que respondo: el texto que escribes o, si mandas un audio, solo su "
    "transcripción — el audio original NO se guarda (se transcribe y se descarta al "
    "momento). Los saludos y las despedidas no se registran\n"
    "• La respuesta que te doy\n"
    "• Fecha/hora, tu ID de Telegram y el nombre que nos des al aceptar\n"
    "• Tu valoración 👍/👎, si la usas, y la explicación que escribas al marcar una "
    "respuesta como incorrecta\n\n"
    "*Para qué*: identificar errores, mejorar respuestas y calibrar el sistema con preguntas "
    "reales del sector.\n\n"
    "*Reconocimiento de aportaciones*: al revisar tu feedback marcamos si sirvió para "
    "corregir algo, y esa valoración puede tenerse en cuenta para reconocer o incentivar "
    "a quien más aporta. La marca la pone una persona al revisar, nunca el sistema, y "
    "**cualquier decisión sobre ti la toma una persona**, no un cálculo automático. No se "
    "te perfila para ninguna otra cosa.\n\n"
    "*Quién accede*: el equipo técnico de Fontiber Industrial Partners.\n\n"
    "*Quién más interviene* (por función, con quién lo hace hoy):\n"
    "• _Canal de mensajería_: *Telegram* — transporta toda la conversación\n"
    "• _Generación de la respuesta_: *Anthropic* (modelo Claude) — recibe tu pregunta\n"
    "• _Búsqueda en los manuales_: *Voyage AI* — recibe tu pregunta\n"
    "• _Transcripción de audio_: *OpenAI* (Whisper) — recibe el audio\n"
    "• _Almacenamiento_: *Supabase* — servidores en la UE (Estocolmo)\n"
    "• _Ejecución del bot_: *Railway*\n\n"
    "Salvo el almacenamiento, todos operan *fuera de la UE* y cada uno aplica su propia "
    "política de conservación. No se comparten con nadie más.\n\n"
    "*Cuánto tiempo*: 24 meses vinculado a ti. Pasado ese plazo se retira tu identificador "
    "de tus consultas y de sus valoraciones; el contenido se conserva disociado para seguir "
    "mejorando el sistema. Tu aceptación de estos términos se conserva como prueba del "
    "consentimiento mientras conservemos datos tuyos.\n\n"
    "*Transferencias fuera de la UE*: puedes pedirnos información sobre las garantías "
    "aplicables escribiendo a *info@fontiber.com*.\n\n"
    "*Tus derechos*: acceso, rectificación, supresión, oposición y portabilidad. Escribe a "
    "*info@fontiber.com* y te atendemos.\n\n"
    "*Retirar el consentimiento*: puedes hacerlo cuando quieras escribiendo a esa misma "
    "dirección. No afecta a lo tratado hasta ese momento; a partir de ahí, deja de usarse.\n\n"
    "*Reclamación*: si crees que no lo hacemos bien, puedes reclamar ante la Agencia Española "
    "de Protección de Datos (aepd.es).\n\n"
    "_Puedes leer esto sin haber aceptado nada. Si no aceptas, simplemente no uses el bot._"
)


_NEEDS_CONSENT = (
    "Antes de empezar, lee los términos en /start y acepta con `/accept [tu nombre]`."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — show terms if no consent yet, otherwise welcome."""
    user_id = update.effective_user.id if update.effective_user else 0
    if has_consent(user_id):
        await update.message.reply_text(_welcome_text(), parse_mode="Markdown")
    else:
        await update.message.reply_text(_CONSENT_TERMS, parse_mode="Markdown")


async def accept_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /accept [name] — record RGPD consent."""
    user_id = update.effective_user.id if update.effective_user else 0
    # context.args is a list of tokens after the command
    display_name = " ".join(context.args).strip() if context.args else None

    ok = set_consent(user_id, display_name=display_name)
    if not ok:
        await update.message.reply_text(
            "Ha ocurrido un error al registrar tu aceptación. Por favor, inténtalo de nuevo en unos segundos."
        )
        return

    # s296: se emite aquí el código estable de esta persona. `/accept` es el punto natural
    # — es obligatorio, ocurre una vez, y no está en el camino caliente de una consulta.
    # Fail-open a propósito: si la emisión falla, el técnico entra igual; el código se
    # emitirá en el siguiente intento. Bloquear el acceso por esto sería desproporcionado.
    seudonimo_de(user_id)

    name_part = f", {display_name}" if display_name else ""
    await update.message.reply_text(
        f"✅ Aceptado{name_part}. Ya puedes empezar.\n\n" + _welcome_text(),
        parse_mode="Markdown",
    )


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Segunda capa del aviso de privacidad.

    NO exige consentimiento: poder leer el detalle ANTES de aceptar es justo lo que hace
    que la primera capa cuente como informada.
    """
    await update.message.reply_text(_PRIVACY_DETAIL, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "*Comandos disponibles:*\n\n"
        "/start - Términos / mensaje de bienvenida\n"
        "/accept [nombre] - Aceptar términos de uso\n"
        "/help - Esta ayuda\n"
        "/privacidad - Qué datos se guardan, quién interviene y por cuánto tiempo\n\n"
        "*Consejos para mejores respuestas:*\n"
        "• Menciona el modelo de equipo (ej: CAD-250, MAD-402, FT-2000, MS-25)\n"
        "• Sé específico en tu pregunta\n"
        "• Puedes preguntar sobre procedimientos paso a paso\n"
        "• 🎤 También puedes enviar audios — los transcribo automáticamente\n\n"
        "*Fabricantes cubiertos*: " + _fabricantes_resumen()[0].replace("*", "") + ".",
        parse_mode="Markdown",
    )


def _transcribe_audio_sync(file_path: str) -> str:
    """Blocking OpenAI transcription call, isolated for async dispatch/tests.

    Passes a PCI-domain vocabulary hint so model codes like CAD-250, AFP-2820,
    ID-3000 are transcribed correctly instead of as spelled-out numbers.
    """
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=VOICE_TRANSCRIPTION_MODEL,
            file=audio_file,
            language="es",
            prompt=get_whisper_prompt(),
        )
    return transcript.text.strip()


async def transcribe_audio(file_path: str) -> str:
    """Transcribe without blocking Telegram's event loop for other users."""
    return await asyncio.to_thread(_transcribe_audio_sync, file_path)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — transcribe with Whisper then process as text."""
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    if not has_consent(user_id):
        await update.message.reply_text(_NEEDS_CONSENT, parse_mode="Markdown")
        return

    await update.message.chat.send_action("typing")

    tmp_path = None
    # (s324e, dúo r37) Lo que el técnico ha DICHO, tal como se conoce en cada
    # momento. Se declara ANTES del try para que el manejador de abajo lo tenga
    # pase lo que pase, y crece en dos pasos: primero la transcripción cruda y
    # luego la consulta normalizada. Es lo que arma la defensa contra ECO —sin
    # esto, `redactar` corría con `prohibido=None` y una excepción que
    # reprodujera la transcripción la habría guardado en `bot_errors`, además
    # SIN enlace (`query_log_id=NULL`), o sea fuera del CASCADE y de cualquier
    # supresión a petición.
    dicho: list[str] = []
    try:
        # Download voice file from Telegram
        file = await context.bot.get_file(voice.file_id)
        suffix = audio_file_suffix(
            file_name=getattr(voice, "file_name", None),
            mime_type=getattr(voice, "mime_type", None),
        )
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            await file.download_to_drive(tmp_path)

        # Transcribe with the explicitly governed ASR arm.
        logger.info(
            "Transcribing voice message (%ss) with %s...",
            voice.duration,
            VOICE_TRANSCRIPTION_MODEL,
        )
        raw_transcription = await transcribe_audio(tmp_path)
        if raw_transcription:
            dicho.append(raw_transcription)

        if not raw_transcription:
            await update.message.reply_text(
                "No he podido entender el audio. ¿Puedes repetirlo o escribir tu pregunta?"
            )
            return

        # Convert only exact, unambiguous spoken forms derived from the model
        # catalog ("i de tres mil" -> "ID3000").  Raw ASR stays visible and is
        # logged unchanged; the retrieval form is explicit when it differs.
        normalization = normalize_voice_query(raw_transcription)
        query = normalization.normalized
        if query and query != raw_transcription:
            dicho.append(query)
        confirmation = f"🎤 {raw_transcription}"
        if normalization.changed:
            recognized = list(
                dict.fromkeys(item.canonical for item in normalization.substitutions)
            )
            confirmation += f"\n🔎 Modelo interpretado: {', '.join(recognized)}"
        # Plain text avoids Telegram Markdown parse failures on arbitrary ASR.
        await update.message.reply_text(confirmation)

        # (#70, fase B) El texto de la voz solo existe tras el ASR, asi que la
        # invalidacion se decide aqui -- con el MISMO predicado puro del plan, el MISMO
        # escritor unico y la MISMA disciplina de cache que el camino de texto.
        # (Expandir la voz al plan completo -- cortesia/catalogo hablados -- sigue
        # siendo una decision de producto SEPARADA, v3 seccion 2.)
        if isinstance(getattr(context, "user_data", None), dict):
            # (Sol fase-B M2) el proveedor va SIN llamar: MarcasDB acepta callable y el
            # core solo lo invoca tras regex-miss + pre-gate — con parentesis, el
            # primer audio tras un restart pagaba 0,54 s de httpx sincrono AUNQUE no
            # hubiera ni estado ni senal de switch.
            # (Sol fase-B M5) fail-open LOCAL con warning (paridad con la guardia
            # historica): el predicado propaga excepciones a proposito, y sin esta
            # frontera un fallo del clasificador tumbaria el turno de voz entero.
            try:
                _transicion_voz, _marca_voz = _turn_plan._decidir_transicion(
                    query, _estado_modelos_conversacion(context.user_data),
                    Meta(fuente="voz"), _lexico_marcas_cacheado)
                if _transicion_voz == _turn_plan.INVALIDAR:
                    _aplicar_estado(context.user_data, WorkingState())
                    logger.info(
                        "plan #70 (voz): cambio de marca a %r -- contexto invalidado",
                        _marca_voz)
            except Exception as exc:             # noqa: BLE001
                logger.warning("invalidacion (voz) no aplicada (%s)",
                               type(exc).__name__)

        # Process the normalized query while preserving raw ASR for audits.
        await _process_query(
            update,
            context,
            query,
            source="voice",
            transcription=raw_transcription,
        )

    except Exception as e:
        # s324e: antes se registraba `f"...: {e}"` — el texto CRUDO de la excepción
        # en el log del proceso, que es justo lo que s295 cerró para la ruta de
        # texto (puede arrastrar la transcripción, y con ella datos personales) y
        # lo que s286 prohibió en las filas de error (una URL de la API de
        # Telegram lleva el token del bot dentro). Ahora pasa por la taxonomía:
        # el mensaje se redacta antes de guardarse y no va al log del worker.
        # `handle_voice` estaba además FUERA del alcance de las filas de error
        # (declarado en s286); con el punto único, ya no lo está.
        # `query=dicho` (dúo r37, CRÍTICO de privacidad): sin ello `redactar`
        # corría sin defensa contra eco y la transcripción del técnico podía
        # acabar en `mensaje_corto`. Se pasan LAS DOS formas —cruda y
        # normalizada— porque la excepción puede reproducir cualquiera. De paso
        # la incidencia queda ENLAZADA a su fila de `query_logs` (con
        # consentimiento), que es lo que la mete en el CASCADE.
        await _reportar_error(
            update, e, etapa="handle_voice", query=dicho or None,
            sufijo="Si te resulta más rápido, escríbeme la pregunta por texto.",
        )
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


async def _capture_reply_explanation(update: Update, user_id: int, text: str) -> bool:
    """¿Este mensaje es una explicación en reply a una respuesta anclada?

    Devuelve True si se ha capturado (y por tanto el mensaje NO debe ir al RAG).

    Binding EXACTO y sin estado en memoria: `message_id → query_log_id` vía
    `answer_messages`, así que funciona tras reinicio de Railway y días después.
    Fail-open total: cualquier problema devuelve False y el mensaje sigue su curso
    normal — jamás se traga una pregunta del técnico por un fallo de telemetría.
    """
    try:
        replied = getattr(update.message, "reply_to_message", None)
        message_id = getattr(replied, "message_id", None)
        chat_id = getattr(getattr(replied, "chat", None), "id", None)
        if not isinstance(message_id, int) or not isinstance(chat_id, int):
            return False
        query_log_id = query_log_id_for_message(chat_id, message_id)
        if not query_log_id:
            return False
        if not set_feedback_comment(query_log_id, user_id, text):
            return False
        # `ReplyKeyboardRemove` CIERRA la caja de respuesta: sin esto el cliente
        # sigue mostrando «Reply to…» y vuelve a pedir explicación después de
        # haberla dado (cazado por Alberto en prueba real, 2-ago).
        await update.message.reply_text(
            _FEEDBACK_EXPLAIN_ACK, reply_markup=ReplyKeyboardRemove()
        )
        # s315 (2º dato vivo de Alberto, 9-ago): ReplyKeyboardRemove NO desarma un
        # ForceReply — el borrador «Reply to…» que el cliente sincroniza apuntando a
        # la INVITACIÓN revive tras el «Anotado». El remedio con dientes es borrar el
        # mensaje-invitación: muerto el mensaje, muere el borrador armado. Guarda
        # ESTRICTA: solo si lo respondido es EXACTAMENTE la invitación (constante) —
        # este handler también captura replies a RESPUESTAS técnicas ancladas y esas
        # jamás se borran. Fail-open aparte: la captura ya está consumada.
        try:
            if getattr(replied, "text", None) == _FEEDBACK_EXPLAIN_PROMPT:
                await replied.delete()
        except Exception:
            logger.warning("borrado de la invitación falló open")
        return True
    except Exception:
        logger.warning("captura de explicación falló open")
        return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text messages — classifies and routes before RAG pipeline."""
    query = update.message.text.strip()
    if not query:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    if not has_consent(user_id):
        await update.message.reply_text(_NEEDS_CONSENT, parse_mode="Markdown")
        return

    # s294 (#60 punto 5b): si el mensaje RESPONDE a un mensaje del bot que está
    # anclado, es una explicación sobre esa consulta — intención explícita, sin
    # heurística de palabras clave. Se anota y NO se manda al RAG.
    # Si no se resuelve el ancla (mensaje ajeno, retención, respuesta anterior a
    # esta telemetría), NO se degrada a «última consulta»: se sigue el camino
    # normal y el bot responde, que es lo que el técnico espera si en realidad
    # estaba preguntando otra cosa (aviso de Alberto: puede «pasar» del feedback).
    if await _capture_reply_explanation(update, user_id, query):
        return

    # --- Plan de turno (fase A DEC-200): decision UNICA, ejecucion tonta ---
    # La cascada entera (cortesia -> catalogo -> marca -> 5-bis -> feedback -> RAG)
    # vive en turn_plan.plan_turn; aqui solo se resuelven los HECHOS que el plan
    # declara y se ejecuta la ruta. La politica de log de cada ruta es un CAMPO del
    # plan (la promesa del aviso v7 --cortesia sin log-- pasa de estar implicita en
    # el orden de los ifs a ser dato verificable).
    meta = Meta(es_reply=update.message.reply_to_message is not None)
    estado_modelos = _estado_modelos_conversacion(context.user_data)
    plan = plan_turn(query, estado_modelos, meta,
                     _resolver_hechos(plan_turn_hechos(query, estado_modelos, meta)))
    # Fase B: la transicion del plan ES la fuente de invalidacion (la guardia -1 se
    # retiro). ORDEN = el contrato de flujo de datos del v3 (Sol r7 C3): la transicion
    # se aplica ANTES de ejecutar la ruta, asi la politica F1 resuelve DESDE el estado
    # post-plan -- sin esto, un carry-forward calculado sobre el estado viejo
    # sobrescribiria la invalidacion y #70 reviviria por construccion.
    if plan.transicion == _turn_plan.INVALIDAR:
        _aplicar_estado(context.user_data, WorkingState())
        logger.info("plan #70: cambio de marca a %r -- contexto de producto invalidado",
                    plan.transicion_marca)
    await _ejecutar_plan(update, context, user_id, query, plan)


def _resolver_hechos(necesita) -> dict:
    """Shell MECANICO del contrato de hechos: trae EXACTAMENTE lo pedido, con las
    funciones y caches de hoy, y CERO decisiones -- este cuerpo no examina jamas el
    texto del usuario (test de mecanicidad por AST)."""
    global _marcas_db_cache
    hechos: dict = {}
    # (Fable r-build, M1) ORDEN DE DEPENDENCIA DECLARADO por el contrato (turn_plan):
    # `marca_de_modelo` se resuelve PRIMERO, y `marca_servida` SOLO si aquel resulto
    # falsy — el short-circuit historico de handle_message. Sin esto, cada turno
    # modelo+marca (la consulta tecnica mas comun) pagaba un roundtrip Supabase extra
    # que HEAD solo pagaba con lookup fallido, y un blip de red MATABA turnos de
    # mismatch/misma-marca que jamas tocaban esa funcion. La dependencia examina
    # VALORES de hechos, nunca el texto (test de mecanicidad).
    orden = sorted(necesita, key=lambda h: 0 if h.tipo == "marca_de_modelo" else 1)
    modelo_resuelto = False
    for h in orden:
        if h.tipo == "marca_de_modelo":
            hechos[h] = lookup_model_manufacturer(h.arg)
            modelo_resuelto = modelo_resuelto or bool(hechos[h])
        elif h.tipo == "marca_servida":
            if modelo_resuelto:
                continue                     # el plan no lo consumira (short-circuit)
            hechos[h] = manufacturer_in_db(h.arg)
        elif h.tipo == "lexico_marcas":
            hechos[h] = _lexico_marcas_cacheado()   # UNA implementación del patrón
    return hechos


async def _ejecutar_plan(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         user_id: int, query: str, plan: TurnPlan):
    """Despachador TONTO: ejecuta la ruta del plan sin re-examinar el texto. Las
    respuestas son las de hoy, byte a byte (tests de equivalencia s316e)."""
    ruta = plan.ruta
    # (Sol r8, C2) plan.typing y plan.log_consulta NO son decorativos: el despachador
    # los CONSULTA. typing del plan cubre la ruta planificada (catálogo); el ejecutor
    # conversacional envía el suyo propio (también cuando se llega por fallback, como
    # hoy). log_consulta gatea TODO log_query de atajo — una ruta nueva que declare
    # log_consulta=False y loggee, o viceversa, rompe sus tests, no la promesa v7.
    if ruta == "inventario":
        respuesta = _inventario_fabricante(plan.datos["marca"],
                                           plan.datos.get("filtros"))
        if respuesta is None:
            # fail-open DECLARADO POR EL PLAN: la degradacion es fallback_ruta
            # (feedback o conversacional), no una segunda decision del despachador.
            ruta = plan.fallback_ruta or "conversacional"
        else:
            await update.message.reply_text(respuesta, parse_mode="Markdown")
            if plan.log_consulta:
                log_query(telegram_user_id=user_id, query=query,
                          route="catalog_shortcut",
                          response=respuesta, response_length=len(respuesta))
                asegurar_seudonimo(user_id)
            return
    if ruta == "cortesia_saludo":
        await update.message.reply_text(
            "\u00a1Hola! \U0001f44b Soy el asistente t\u00e9cnico PCI.\n\n"
            "Preg\u00fantame lo que necesites sobre instalaci\u00f3n, conexionado, "
            f"especificaciones o resoluci\u00f3n de problemas de equipos de {_fabricantes_resumen()[0]}.\n\n"
            "Tambi\u00e9n puedes enviarme un audio \U0001f3a4",
            parse_mode="Markdown",
        )
        return
    if ruta == "cortesia_gracias":
        await update.message.reply_text(
            "De nada \U0001f44d \u00bfNecesitas algo m\u00e1s?"
        )
        return
    if ruta == "cortesia_adios":
        await update.message.reply_text(
            "\u00a1Hasta luego! Aqu\u00ed estar\u00e9 cuando lo necesites. \U0001f527"
        )
        return
    if ruta == "catalogo":
        if plan.typing:
            await update.message.chat.send_action("typing")
        await _handle_catalog(update)
        if plan.log_consulta:
            log_query(telegram_user_id=user_id, query=query, route="catalog_shortcut")
            asegurar_seudonimo(user_id)
        return
    if ruta == "mismatch":
        d = plan.datos
        respuesta = (
            f"El *{d['modelo']}* es un producto de *{d['marca_real']}*, "
            f"no de _{d['marca_mencionada']}_.\n\n"
            f"\u00bfTe refieres al *{d['modelo']}* de *{d['marca_real']}*? "
            f"Si es as\u00ed, dime tu pregunta y te ayudo."
        )
        await update.message.reply_text(respuesta, parse_mode="Markdown")
        if plan.log_consulta:
            log_query(telegram_user_id=user_id, query=query, route="manufacturer_mismatch",
                      response=respuesta, response_length=len(respuesta))
            asegurar_seudonimo(user_id)
        return
    if ruta == "marca_no_servida":
        available = get_available_manufacturers()
        manufacturers_str = ", ".join(f"*{m}*" for m in available)
        respuesta = (
            f"No dispongo de manuales de _{plan.datos['marca_mencionada']}_.\n\n"
            f"Tengo informaci\u00f3n de: {manufacturers_str}.\n"
            f"\u00bfPuedo ayudarte con alguno de estos?"
        )
        await update.message.reply_text(respuesta, parse_mode="Markdown")
        if plan.log_consulta:
            log_query(telegram_user_id=user_id, query=query, route="manufacturer_no_model",
                      response=respuesta, response_length=len(respuesta))
            asegurar_seudonimo(user_id)
        return
    if ruta == "feedback":
        await _handle_feedback(update, context, query)
        return
    # conversacional (default del plan y de los fallbacks)
    await update.message.chat.send_action("typing")
    await _process_query(update, context, query)


async def _handle_catalog(update: Update):
    """Respond to catalog questions with full product list from DB."""
    try:
        catalog = get_all_models_by_category()
        if not catalog:
            await update.message.reply_text(
                "No he podido obtener el catálogo. Inténtalo de nuevo."
            )
            return

        lines = [
            "🔥 *Productos disponibles* "
            f"({_fabricantes_resumen()[0].replace('*', '')}):\n"
        ]
        for category, models in catalog.items():
            models_str = ", ".join(f"*{m}*" for m in models)
            lines.append(f"📁 _{category}_\n{models_str}\n")

        lines.append("Pregúntame sobre cualquiera de estos productos.")
        text = "\n".join(lines)

        try:
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(text.replace("*", "").replace("_", ""))
    except Exception as e:
        logger.error(f"Error getting catalog: {e}")
        await update.message.reply_text(
            "Ha ocurrido un error obteniendo el catálogo. Inténtalo de nuevo."
        )


async def _handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    """Handle technician feedback on previous responses."""
    # Get previous query/response from context if available
    previous_query = context.user_data.get("last_query", "")
    previous_response = context.user_data.get("last_response", "")

    # Log feedback
    user_id = update.effective_user.id if update.effective_user else 0
    log_feedback(
        telegram_user_id=user_id,
        feedback_text=query,
        previous_query=previous_query[:500] if previous_query else None,
        previous_response=previous_response[:500] if previous_response else None,
        query_log_id=context.user_data.get("last_query_log_id"),
    )

    await update.message.reply_text(
        "Gracias por el aviso 🙏\n\n"
        "Tu feedback queda registrado. ¿Puedes indicarme qué dato concreto "
        "es incorrecto y qué dice el manual? Así podré mejorar."
    )


def _diagram_caption(diagram: dict) -> str:
    """Descriptive caption for one diagram: 📐 product — section/type."""
    product = diagram.get("product", "")
    section = diagram.get("section", "")
    content_type = diagram.get("content_type", "")

    caption_parts = ["📐"]
    if product:
        caption_parts.append(product)
    if section:
        # Clean up section title (remove long text)
        short_section = section.strip().split("\n")[0][:80]
        caption_parts.append(f"— {short_section}")
    elif content_type:
        type_labels = {
            "wiring": "Esquema de conexionado",
            "procedure": "Procedimiento",
            "specification": "Especificaciones",
            "troubleshooting": "Resolución de problemas",
            "general": "Información general",
        }
        caption_parts.append(f"— {type_labels.get(content_type, content_type)}")
    return " ".join(caption_parts)


async def _send_diagrams_individually(update: Update, diagrams: list[dict]):
    """Original per-photo transport; each failure is logged and skipped."""
    for diagram in diagrams:
        try:
            await update.message.reply_photo(
                photo=diagram["url"],
                caption=_diagram_caption(diagram),
            )
        except Exception as e:
            logger.warning(f"Failed to send diagram: {e}")


async def _process_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str,
    source: str = "text",
    transcription: str | None = None,
):
    """Core RAG pipeline — shared between text and voice handlers."""
    import time as _time
    start_time = _time.time()

    # Session timeout for conversation context carry-forward (1 hour)
    SESSION_TIMEOUT = 3600

    try:
        # Step 1a: Extract models from current query
        target_models = extract_product_models(query)

        # S281 Phase-1 (F1) activation gate — leído en RUNTIME (un flip de
        # CONVERSATION_POLICY en Railway togglea sin restart). s319 PR-C: el
        # candado a ORCHESTRATOR_PATH murió con la ruta legacy — el orquestador
        # es la ruta única y F1 depende SOLO de su propio flag (el régimen stub
        # sigue disponible por env explícito para el instrumento MT).
        from ..orchestrator.conversation_policy_impl import (
            conversation_policy_active,
        )
        f1_active = conversation_policy_active()

        # Step 1b/1c/2b: legacy single-turn resolution (in-memory carry-forward +
        # vague-query clarify + category options). RETIRED when the Phase-1 policy
        # is active: the deterministic policy SUBSTITUTES step 1b, so running both
        # would be a DOUBLE resolution the CARRY-FORWARD-1H design forbids. These
        # locals are still initialised for the non-F1 code paths; when f1_active is
        # False the block runs byte-identically to the historical handler.
        query_for_retrieval = query
        available_models = None
        detected_category = None
        if not f1_active:
            # Step 1b: Carry forward model context from previous query if within session
            if not target_models:
                # (fase B) el regimen stub lee el MISMO estado que F1; la ventana se
                # mide sobre last_turn_at (test de conversion last_query_time->last_turn_at)
                _ws_stub = context.user_data.get("mt_working_state")
                last_models = list(getattr(_ws_stub, "last_target_models", ()) or ())
                _lt = getattr(_ws_stub, "last_turn_at", None)
                from datetime import datetime as _dt, timezone as _tz
                if last_models and _lt is not None and \
                        (_dt.now(_tz.utc) - _lt).total_seconds() < SESSION_TIMEOUT:
                    target_models = last_models
                    # Append model hint to retrieval query so retriever finds relevant chunks
                    query_for_retrieval = f"{query} (contexto: {', '.join(target_models)})"

            # Step 1c: Detect vague/ultra-short queries (after carry-forward, so context helps)
            words = query.split()
            if len(words) <= 2 and not target_models:
                query_clean = query.lower().strip("¿?¡!., ")
                is_pci_term = any(term in query_clean for term in PCI_TERMS)
                if is_pci_term:
                    respuesta_clarify = (
                        f"Para darte información precisa sobre *{query_clean}*, "
                        f"necesito saber el modelo de equipo.\n\n"
                        f"Por ejemplo: _{query_clean} en la CAD-250_ o "
                        f"_{query_clean} del MAD-461_.\n\n"
                        f"¿Qué equipo (Notifier, Morley o Detnov) estás usando?"
                    )
                    await update.message.reply_text(respuesta_clarify,
                                                    parse_mode="Markdown")
                    # s301 (dúo): esta rama respondía y retornaba SIN log — «cada
                    # respuesta lleva ruta» era falso. Es una consulta de contenido:
                    # se loggea como el resto.
                    log_query(
                        telegram_user_id=(update.effective_user.id
                                          if update.effective_user else 0),
                        query=query, source=source, route="clarify",
                        response=respuesta_clarify,
                        response_length=len(respuesta_clarify),
                    )
                    return

            # Step 2b: Get available models in detected category (for dynamic conversation)
            if not target_models:
                query_lower = query.lower()
                for term, cat in CATEGORY_TERMS.items():
                    if term in query_lower:
                        available_models = get_category_models(cat)
                        detected_category = cat
                        break

        # S281 Phase-1 (F1) resolution. When active, the deterministic
        # conversational policy OWNS turn resolution against durable per-chat
        # working state (context.user_data['mt_working_state'] — IN MEMORY: it does
        # NOT survive a process restart; durable persistence is DDL/RGPD-gated, out
        # of scope). CLARIFY/DECLINE answer directly at $0 (no pipeline); the other
        # routes feed the RESOLVED query to BOTH retrieval AND generation (the
        # measured e2e fix, mirrored from scripts/test_multiturn_vs_gold.run_e2e_flows).
        f1_resolution = None
        f1_prev_state = None
        f1_new_state = None
        f1_now = None
        # (s316h gate 1) Telemetria POR TURNO del lever INTENT_LLM. Se estampa
        # "off" EXPLICITO (F1 inactivo = lever inalcanzable, medido); el seam lo
        # sobreescribe si corre. Un dict sin estampar degrada a "not_wired" en el
        # builder (Sol r12 M1): «sin cablear» jamas se disfraza de «apagado».
        intent_obs: dict = {"status": "off", "decision": "none", "latency_ms": 0}
        if f1_active:
            from datetime import datetime, timezone

            from ..orchestrator.conversation_policy import PolicyRoute, WorkingState
            from ..orchestrator.conversation_policy_impl import (
                resolve_conversational_turn,
            )

            # Lazy source-bound rewriter: BOTH its import and construction are
            # deferred until a REWRITE route actually calls it. $0 routes never
            # touch it (a carry-forward turn builds no client). Model = LLM_MODEL.
            _rewriter_cell: dict = {}

            def _lazy_rewrite(anaphoric_query, ws):
                rewriter = _rewriter_cell.get("rewriter")
                if rewriter is None:
                    from ..orchestrator.rewriter import make_rewriter

                    # (dúo s308) REWRITER_MODEL propio: el rewriter NO tiene los
                    # fixes del #64 — pinearlo a LLM_MODEL habría roto F1 en
                    # silencio con el swap a Opus 5.
                    rewriter = make_rewriter(model=REWRITER_MODEL)
                    _rewriter_cell["rewriter"] = rewriter
                return rewriter(anaphoric_query, ws)

            stored_state = context.user_data.get("mt_working_state")
            f1_prev_state = (
                stored_state if isinstance(stored_state, WorkingState) else WorkingState()
            )
            f1_now = datetime.now(timezone.utc)
            # (s316g lever INTENT_LLM, DEC-203; seam extraido a _intent_seam en
            # s316h — gate 2 del flip: el e2e ejecuta ese codigo, no un simil).
            # Flag default OFF = seam None = byte-idéntico. Con ON, la resolución
            # entera se mueve a to_thread: el resolve corre en el event loop y una
            # llamada síncrona de segundos lo bloquearía TODO (Sol r10 M2).
            _intent_fn = _intent_seam(intent_obs)
            if _intent_fn is not None:
                f1_resolution, f1_new_state = await asyncio.to_thread(
                    resolve_conversational_turn,
                    query, f1_prev_state, f1_now,
                    rewrite=_lazy_rewrite, intent=_intent_fn,
                )
                if intent_obs.get("status") == "invoked":
                    # decisión → log operacional; la traza PERSISTIDA es la
                    # sección `intent` de rag_trace (gate 1 del flip, s316h).
                    logger.info("intent_llm: %s en %d ms",
                                intent_obs["decision"], intent_obs["latency_ms"])
            else:
                f1_resolution, f1_new_state = resolve_conversational_turn(
                    query, f1_prev_state, f1_now, rewrite=_lazy_rewrite
                )

            if f1_resolution.route in (PolicyRoute.CLARIFY, PolicyRoute.DECLINE):
                # $0 direct answer — NO retrieval, NO generation.
                if f1_resolution.route is PolicyRoute.CLARIFY:
                    direct_reply = f1_resolution.clarify_question
                else:
                    direct_reply = _F1_DECLINE_MESSAGES.get(
                        f1_resolution.decline_reason, _F1_DECLINE_DEFAULT
                    )
                direct_reply = direct_reply or _EMPTY_ANSWER_FALLBACK
                # Persist working state. For CLARIFY/DECLINE advance_working_state
                # returns the prior state INTACT (no model fixed, window NOT
                # refreshed — an expired product stays expired).
                _aplicar_estado(context.user_data, f1_new_state)
                context.user_data["last_query"] = query
                context.user_data["last_response"] = direct_reply[:500]
                # (Sol fase-B M1) el anclaje del feedback era MIXTO: se sobrescribia el
                # texto pero la FK seguia apuntando al RAG anterior — un 👎 tras un
                # clarify mezclaba ambos. Mismo patron que la ruta RAG: uuid cliente →
                # log → last_query_log_id coherente (o None si el log fallo).
                _clarify_uuid = str(uuid.uuid4())
                await update.message.reply_text(direct_reply)
                # s301 (dúo): CLARIFY/DECLINE de F1 también son respuestas a consultas
                # — sin log, «quién usa el bot y cuánto» tenía un agujero por aquí.
                _clarify_logged = log_query(
                    telegram_user_id=(update.effective_user.id
                                      if update.effective_user else 0),
                    query=query, source=source,
                    route=("clarify"
                           if f1_resolution.route is PolicyRoute.CLARIFY
                           else "decline"),
                    response=direct_reply, response_length=len(direct_reply),
                    query_log_id=_clarify_uuid,
                )
                context.user_data["last_query_log_id"] = (
                    _clarify_uuid if _clarify_logged else None)
                return

            # Retrieving route: surface the resolved models to logging + state.
            target_models = list(f1_resolution.target_models or ())

        # Transport-neutral orchestrator request (MT-0d; ruta única desde s319
        # PR-C — el request se construye SIEMPRE porque run_turn es el único
        # camino de serving).
        from ..orchestrator.telegram_adapter import build_turn_request
        if f1_active:
            # FIX MEDIDO: the RESOLVED query fills BOTH query (-> generation)
            # and query_for_retrieval (-> retrieval); target/available come from
            # the resolution. For STANDALONE the resolved query == the raw
            # query, so this is byte-identical to the historical path.
            request = build_turn_request(
                query=f1_resolution.query_for_retrieval,
                query_for_retrieval=f1_resolution.query_for_retrieval,
                target_models=f1_resolution.target_models,
                available_models=f1_resolution.available_models,
                update_id=update.update_id,
                chat_id=update.effective_chat.id,
                source=source,
                transcription=transcription,
            )
        else:
            # régimen STUB (env explícito): el request se construye desde la
            # extracción legacy — mismo shape, misma ruta run_turn.
            request = build_turn_request(
                query=query,
                query_for_retrieval=query_for_retrieval,
                target_models=target_models,
                available_models=available_models,
                update_id=update.update_id,
                chat_id=update.effective_chat.id,
                source=source,
                transcription=transcription,
            )

        # s319 PR-C (DEC-211): el orquestador es la ruta ÚNICA de serving. El
        # `else` histórico (execute_rag_turn inline) se retiró tras el período
        # de asentamiento en producción — dos rutas que deben evolucionar
        # juntas son la clase que produjo #70. El SEAM `execute_rag_turn`
        # sigue vivo en serving_pipeline.py (el release gate P1 lo atestigua
        # por string y lo conduce directamente).
        from ..orchestrator import from_production, run_turn
        turn = await asyncio.to_thread(run_turn, request, from_production())
        chunks = list(turn.retrieval.chunks)
        coverage_trace = turn.retrieval.coverage_trace
        retrieval_health = (
            {"channel_failures": list(turn.retrieval.channel_failures)}
            if turn.retrieval.retrieval_measured else None
        )
        result = turn.generation
        answer = result["answer"]
        diagrams = result["diagrams"]
        stage_timings = turn.stage_timings

        empty_answer_fallback = not _has_visible_text(answer)
        if empty_answer_fallback:
            # A provider can complete with no visible text after tool calls.
            # Never turn that upstream defect into a silent Telegram turn.
            logger.error("generator returned an empty answer")
            answer = _EMPTY_ANSWER_FALLBACK

        # Store last query/response for feedback tracking + conversation context
        # Telemetria de feedback (cluster DECLARADO fuera del invariante de estado:
        # ancla el 👎 a la ultima respuesta; dueno = _process_query).
        context.user_data["last_query"] = query
        context.user_data["last_response"] = answer[:500]
        # (fase B) Regimen STUB: el estado conversacional se escribe como transicion
        # PURA sobre el estado unico -- quirk legacy incluido (ver transicion_basica).
        if not f1_active:
            from datetime import datetime as _dt, timezone as _tz
            _aplicar_estado(context.user_data, _turn_plan.transicion_basica(
                context.user_data.get("mt_working_state"), target_models, query,
                answer, _dt.now(_tz.utc)))

        # S281 Phase-1 (F1) durable working-state backfill — the TODO closed. After
        # generation, re-advance from the SAME prior state + resolution, now with
        # the answer excerpt (first ~500 chars; advance_working_state truncates), so
        # the next turn's rewriter can resolve content anaphora ("ese aviso")
        # against the prior answer. IN MEMORY only (no restart durability).
        if f1_active and f1_resolution is not None:
            from ..orchestrator.conversation_policy_impl import advance_working_state

            _aplicar_estado(context.user_data, advance_working_state(
                f1_prev_state,
                f1_resolution,
                query,
                answer,
                f1_now,
                f1_new_state.available_models,
            ))

        # Render once: telemetry records the actual transport split and the
        # send loop consumes these exact same parts. A formatter defect must
        # neither erase the query receipt nor suppress the technical answer.
        transport_status = (
            "empty_answer_fallback" if empty_answer_fallback else "html"
        )
        transport_error_type = "RuntimeError" if empty_answer_fallback else None
        try:
            answer_parts = format_telegram_messages(answer)
            if (
                not isinstance(answer_parts, list)
                or not answer_parts
                or any(
                    not _has_visible_text(telegram_html_to_plain(part))
                    for part in answer_parts
                )
            ):
                raise ValueError("formatter returned empty transport parts")
        except Exception as exc:
            logger.warning(
                "Telegram formatter failed open (%s)", type(exc).__name__
            )
            answer_parts = _plain_transport_parts(answer)
            transport_status = "plain_fallback"
            transport_error_type = type(exc).__name__
        try:
            rag_trace = build_rag_serving_trace(
                coverage_trace=coverage_trace,
                served_chunks=chunks,
                must_preserve_trace=result.get("must_preserve"),
                must_preserve_outcome=result.get("must_preserve_outcome"),
                release_policy=COVERAGE_RELEASE_POLICY.safe_snapshot(),
                transport_parts=len(answer_parts),
                transport_status=transport_status,
                transport_error_type=transport_error_type,
                retrieval_health=retrieval_health,
                stage_timings=stage_timings,
                intent_obs=intent_obs,
            )
        except Exception as exc:
            logger.warning("RAG runtime trace failed open (%s)", type(exc).__name__)
            rag_trace = None

        # Log query. Failure is isolated inside log_query and never changes the
        # answer. The row's UUID is generated client-side (s286): it works with
        # the return=minimal client and the compatibility retry, and it lets the
        # feedback keyboard reference the row without a read-back. If the log is
        # not KNOWN committed, the keyboard is skipped this turn — losing one
        # vote's worth of signal is safe, a dangling FK reference is not.
        elapsed_ms = int((_time.time() - start_time) * 1000)
        user_id = update.effective_user.id if update.effective_user else 0
        query_log_uuid = str(uuid.uuid4())
        query_logged = log_query(
            telegram_user_id=user_id,
            query=query,
            source=source,
            transcription=transcription,
            product_models=target_models or [],
            category=detected_category,
            chunks_used=len(chunks),
            response=answer,
            response_length=len(answer),
            response_time_ms=elapsed_ms,
            rag_trace=rag_trace,
            query_log_id=query_log_uuid,
        )

        # s296: garantizar el código aquí y no solo en `/accept`. Quien ya aceptó y sigue
        # usando el bot NO vuelve a pasar por `/accept`, y quien regresa después de que su
        # vínculo se destruyera, tampoco. Sin código, sus filas quedarían fuera de la
        # agrupación. Cacheado en proceso: una llamada por persona, no por consulta.
        asegurar_seudonimo(user_id)

        # s296: el feedback espontáneo que venga DESPUÉS se ancla a esta consulta, para que
        # la tabla `feedback` cascadee. Solo si la fila está CONFIRMADA: escribir un enlace
        # colgando haría fallar la clave foránea y se perdería el feedback entero — misma
        # política que el teclado de valoración, que también se omite si no está confirmada.
        context.user_data["last_query_log_id"] = query_log_uuid if query_logged else None

        # Step 4: Render at the transport boundary.  The factual answer kept in
        # logs/evaluation remains untouched; every part is independently valid
        # Telegram HTML, so splitting cannot leave formatting delimiters open.
        # The feedback keyboard rides the LAST text part; diagrams sent after it
        # will show below the buttons — accepted (reply_media_group takes no
        # reply_markup) and documented in the s286 brief.
        feedback_markup = (
            _feedback_keyboard(query_log_uuid)
            if _feedback_keyboard_enabled() and query_logged
            else None
        )
        last_part_index = len(answer_parts) - 1
        sent_message_ids: list[int] = []

        def _remember(sent) -> None:
            """Recoge el message_id para el ancla de telemetría (#60 punto 1).

            Defensivo a propósito: si el transporte devuelve None o un objeto sin
            `message_id` entero (dobles de test, cambio de librería), NO se anota y
            el envío sigue igual. El ancla es telemetría: jamás puede romper la
            entrega de la respuesta."""
            message_id = getattr(sent, "message_id", None)
            if isinstance(message_id, int):
                sent_message_ids.append(message_id)

        for part_index, answer_part in enumerate(answer_parts):
            # Flag off (or log not committed) ⇒ markup_kwargs is empty and every
            # reply_text call stays argument-identical to the pre-s286 code.
            markup_kwargs = (
                {"reply_markup": feedback_markup}
                if feedback_markup is not None and part_index == last_part_index
                else {}
            )
            if transport_status == "plain_fallback":
                _remember(await update.message.reply_text(answer_part, **markup_kwargs))
                continue
            try:
                _remember(
                    await update.message.reply_text(
                        answer_part, parse_mode="HTML", **markup_kwargs
                    )
                )
            except Exception:
                # Fail open without exposing raw HTML tags or entities.  This
                # fallback preserves all technical text and evidence locators.
                _remember(
                    await update.message.reply_text(
                        telegram_html_to_plain(answer_part), **markup_kwargs
                    )
                )

        # Ancla message_id → query_log_id (#60 punto 1). Sin ella, una REACCIÓN de
        # Telegram (que solo trae `message_id`) no se puede atribuir a una consulta.
        # Se estampa solo si la fila de query_logs está KNOWN committed — el mismo
        # criterio que el teclado: una FK colgante no aporta señal, la rompe.
        # Fail-open total: `stamp_answer_messages` traga sus propios errores.
        if query_logged and sent_message_ids:
            chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
            if isinstance(chat_id, int):
                stamp_answer_messages(query_log_uuid, chat_id, sent_message_ids)

        # Step 5: Send diagrams if available (with descriptive captions).
        # 1-2 imágenes → fotos sueltas (comportamiento original); >2 → un solo
        # MEDIA GROUP (álbum, S271) para no spamear mensajes: caption solo en
        # la primera (Telegram la muestra bajo el álbum cuando solo un medio
        # lleva caption) listando todas las páginas adjuntas.
        if len(diagrams) > 2:
            try:
                album_caption = "\n".join(
                    _diagram_caption(diagram) for diagram in diagrams
                )[:1024]
                media = [
                    InputMediaPhoto(
                        media=diagram["url"],
                        caption=album_caption if index == 0 else None,
                    )
                    for index, diagram in enumerate(diagrams)
                ]
                await update.message.reply_media_group(media=media)
            except Exception as e:
                # Fail open del transporte: si el álbum falla (una URL mala
                # tumba el media group entero), degradar a fotos sueltas.
                logger.warning(f"Failed to send media group, fallback: {e}")
                await _send_diagrams_individually(update, diagrams)
        else:
            await _send_diagrams_individually(update, diagrams)

        # Step 6 (MT-0d, default OFF): shadow-persist the answered turn into the
        # effectively-once convo store. Runs AFTER the reply; wholly fail-open so
        # a shadow defect can never turn a served answer into a Telegram error.
        # In Phase 0 only tests inject a store (no store -> no-op logged once).
        if CONVO_SHADOW:
            try:
                from ..orchestrator.shadow import maybe_shadow_persist
                # s319 PR-C: la pierna pipeline murió con la ruta legacy —
                # el turn del orquestador es el único resultado que existe.
                maybe_shadow_persist(request, turn)
            except Exception as exc:
                logger.warning(
                    "CONVO_SHADOW block failed open (%s)", type(exc).__name__
                )

    except Exception as e:
        # s295 RGPD: la pregunta NO va al log del proceso. Es texto libre escrito por un
        # técnico —puede llevar un nombre, una empresa o una obra— y el log del worker
        # vive en Railway, fuera de la matriz de retención y de cualquier supresión a
        # petición. Para diagnosticar basta la longitud y la clase de excepción; el texto
        # ya está en `query_logs`, que SÍ está gobernado.
        logger.error(
            "Error processing query (len=%d): %s", len(query or ""), type(e).__name__
        )
        # s324e: el mensaje genérico («Ha ocurrido un error… inténtalo de nuevo»)
        # murió aquí. Decía lo MISMO ante un timeout transitorio —donde reintentar
        # funciona— y ante un defecto nuestro determinista, donde reintentar falla
        # siempre igual y mandarlo a repetir es hacerle perder el tiempo. Ahora
        # decide la taxonomía, y el mismo punto se encarga del registro para
        # insights (que sigue gateado por BOT_ERROR_LOGGING, con la misma fila
        # `source='error'` de s286 más la incidencia estructurada).
        await _reportar_error(update, e, etapa="process_query", query=query)


# ── Manejo de errores: red de seguridad global + insights (s324e) ────────────
# El fallo que cierra: hoy hay 24 `except Exception` dispersos y CERO
# `add_error_handler`. Fuera de `accept_command` y `_process_query`, una
# excepción no manejada deja al técnico en SILENCIO — escribe y no pasa nada.
# Esto lo cierra por los DOS lados: `error_handler` es la red global de PTB
# (nada llega al vacío) y `_reportar_error` es el único sitio que decide qué se
# dice, qué se registra y con qué severidad. Los 24 `except` locales NO se tocan:
# son degradaciones DELIBERADAS (fail-open de telemetría, fallback de transporte)
# que ya responden al técnico; convertirlas en errores sería una regresión.


def _usuario_de(update: object) -> int:
    """id de Telegram del autor, o 0. Tolera un `update` que no sea `Update`:
    PTB entrega al error handler el objeto que provocó el fallo, y no siempre
    es una actualización (p. ej. un job de la JobQueue)."""
    try:
        return getattr(getattr(update, "effective_user", None), "id", 0) or 0
    except Exception:                                        # noqa: BLE001
        return 0


def _mensaje_de(update: object):
    """El mensaje al que responder, o None si no hay a dónde contestar."""
    try:
        mensaje = getattr(update, "effective_message", None)
        return mensaje if hasattr(mensaje, "reply_text") else None
    except Exception:                                        # noqa: BLE001
        return None


def _persistir_incidencia(incidencia, *, user_id: int, query: str | None,
                          avisado: bool) -> None:
    """Escribe la incidencia para INSIGHTS. Gobernanza en dos piezas:

      · la CONSULTA (dato personal, texto libre del técnico) va a `query_logs`
        con `source='error'` — el contenedor que ya está en la matriz de
        retención, ya cascadea y ya lo excluyen las vistas de salud. Es lo que
        el `BOT_ERROR_LOGGING` de s286 ya hacía; no es un tratamiento nuevo:
        la finalidad «diagnóstico» es la declarada para esa tabla.
      · el DIAGNÓSTICO (clase, tipo, módulo:línea, severidad) va a `bot_errors`,
        enlazado por FK. Esa tabla no guarda dato personal DIRECTO, pero es dato
        ENLAZABLE por esa FK (r37): hereda la gobernanza de `query_logs`, no
        queda fuera de ella.

    El consentimiento GATEA la consulta, no la incidencia: un fallo en `/start`
    de alguien que aún no ha aceptado se cuenta (clase y módulo, sin identidad),
    pero su texto no se guarda. Sin este gate, la red de seguridad global sería
    la primera vía del bot para escribir texto de quien no ha aceptado nada.
    """
    query_log_id = None
    try:
        if query and user_id and has_consent(user_id):
            query_log_id = str(uuid.uuid4())
            if not log_query(
                telegram_user_id=user_id,
                query=query,
                source="error",
                # Formato heredado de s286 (`Tipo@etapa`): `bot_health_report`
                # y las vistas ya lo cuentan. El detalle rico vive en la fila
                # hija; aquí no se cambia lo que otros consumidores ya leen.
                response=f"{incidencia.tipo_excepcion}@{incidencia.etapa}",
                query_log_id=query_log_id,
            ):
                # Sin fila padre confirmada, la FK colgaría: la incidencia se
                # guarda SUELTA (misma política que el teclado de feedback —
                # perder el enlace es seguro, una FK rota no).
                query_log_id = None
    except Exception:                                        # noqa: BLE001
        query_log_id = None
    log_bot_error(
        codigo=incidencia.codigo,
        clase=incidencia.clase,
        severidad=incidencia.severidad,
        tipo_excepcion=incidencia.tipo_excepcion,
        etapa=incidencia.etapa,
        origen=incidencia.origen,
        mensaje_corto=incidencia.mensaje_corto,
        query_log_id=query_log_id,
        usuario_avisado=avisado,
        reintentable=incidencia.reintentable,
    )


def _normalizar_consulta(query) -> tuple[str | None, tuple[str, ...]]:
    """`query` → (texto CANÓNICO a guardar, todas las agujas de redacción).

    Acepta un texto o una secuencia. Cuando son varios (ruta de voz: la
    transcripción cruda y luego la normalizada), la ÚLTIMA es la canónica —la
    forma más procesada que se llegó a conocer antes del fallo— y TODAS se usan
    como agujas: la excepción puede hacer eco de cualquiera de ellas.
    """
    if query is None:
        return None, ()
    if isinstance(query, str):
        texto = query.strip()
        return (texto or None), ((texto,) if texto else ())
    try:
        textos = tuple(t.strip() for t in query if isinstance(t, str) and t.strip())
    except TypeError:                                        # noqa: BLE001
        return None, ()
    return (textos[-1] if textos else None), textos


async def _reportar_error(update: object, exc: BaseException | None, *,
                          etapa: str, query=None,
                          sufijo: str | None = None) -> str:
    """Punto ÚNICO de manejo de un fallo: clasifica, avisa al técnico y registra.

    Devuelve el código de incidencia (para el log del proceso y los tests).

    **No lanza NUNCA.** Es la propiedad que lo hace utilizable como red de
    seguridad: cada paso va en su propio `try` y el cuerpo entero en uno más. Un
    manejador de errores que puede fallar no es un manejador de errores — y en
    PTB una excepción escapada de aquí se convierte en el «uncaught error while
    handling an error» que vuelve a dejar al técnico sin respuesta.
    """
    codigo = "????????"
    try:
        consulta, agujas = _normalizar_consulta(query)
        decision = error_taxonomy.clasificar(exc)
        incidencia = error_taxonomy.describir(
            exc, etapa=etapa, decision=decision, consulta=agujas
        )
        codigo = incidencia.codigo

        # 1) Log del proceso. NUNCA el texto de la consulta (s295: los logs de
        #    Railway están fuera de la matriz de retención y de cualquier
        #    supresión a petición). Longitud sí: sirve para diagnosticar.
        registrar = logger.error if incidencia.severidad != "aviso" else logger.warning
        if incidencia.severidad == "critico":
            registrar = logger.critical
        registrar(
            "incidencia %s clase=%s sev=%s tipo=%s etapa=%s origen=%s len_q=%d",
            incidencia.codigo, incidencia.clase, incidencia.severidad,
            incidencia.tipo_excepcion, incidencia.etapa,
            incidencia.origen or "-", len(consulta or ""),
        )

        # 2) Avisar al técnico. Texto PLANO a propósito: un mensaje de error que
        #    Telegram rechace por un metacarácter de Markdown devolvería el
        #    silencio que esto existe para cerrar.
        avisado = False
        mensaje = _mensaje_de(update)
        if decision.entregable and mensaje is not None and _error_reply_enabled():
            texto = error_taxonomy.texto_para_usuario(
                decision, incidencia.codigo, sufijo
            )
            try:
                await mensaje.reply_text(texto)
                avisado = True
            except Exception as envio:                       # noqa: BLE001
                # No se reintenta ni se recursa: si el propio aviso no sale, lo
                # único que queda es dejar constancia.
                logger.error(
                    "incidencia %s: no se pudo avisar al tecnico (%s)",
                    incidencia.codigo, type(envio).__name__,
                )

        # 3) Registrar para insights (gateado, fail-open dentro). Va a un HILO,
        #    el patrón que el propio bot ya usa para lo bloqueante
        #    (`transcribe_audio`, `run_turn`): el registro son hasta tres
        #    peticiones REST de 10 s de timeout cada una y no deben correr EN
        #    el bucle de eventos.
        #
        #    COSTE REAL, declarado (dúo r37 — una versión anterior de este
        #    comentario afirmaba que esto protegía la disponibilidad para los
        #    demás técnicos, y es FALSO): aquí se hace `await`, así que el turno
        #    espera igual; y como PTB procesa los updates DE UNO EN UNO
        #    (`concurrent_updates` no está activado), con Supabase caído los
        #    demás técnicos siguen haciendo cola detrás de estos timeouts. Lo
        #    que `to_thread` sí compra es que el bucle no quede bloqueado
        #    (getUpdates y la JobQueue siguen vivos) y que esto ya esté bien
        #    puesto si algún día se activa `concurrent_updates`.
        #    El arreglo de verdad —esperar acotado, o activar
        #    `concurrent_updates`— es una decisión de serving con su propio dúo:
        #    NO se cuela aquí de tapadillo.
        if _error_logging_enabled():
            try:
                await asyncio.to_thread(
                    _persistir_incidencia,
                    incidencia,
                    user_id=_usuario_de(update),
                    query=consulta,
                    avisado=avisado,
                )
            except Exception:                                # noqa: BLE001
                logger.warning("incidencia %s: registro fallo open", incidencia.codigo)
    except Exception:                                        # noqa: BLE001
        # Último cinturón. `logging.exception` va aquí y solo aquí: si ESTO
        # falla, el stack completo es lo único que permitirá arreglarlo, y el
        # riesgo de que arrastre texto del técnico es preferible a un manejador
        # de errores mudo. Aun así no se persiste: se queda en el log.
        logger.exception("el manejador de errores fallo (etapa=%s)", etapa)
    return codigo


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Red de seguridad GLOBAL de PTB (`Application.add_error_handler`).

    Recoge lo que ningún `except` local atrapa: comandos, el despachador de
    turno, el callback de feedback, los jobs de la JobQueue. `update` llega
    tipado como `object` a propósito — PTB no garantiza que sea un `Update`.
    """
    exc = getattr(context, "error", None)
    # (s324e) 409 Conflict = OTRA instancia con el mismo token haciendo long polling.
    # PTB lo reintenta INDEFINIDAMENTE (`network_retry_loop`, max_retries=-1) y Telegram
    # reparte los updates entre los procesos: los turnos de un mismo técnico caen en
    # instancias distintas y SU SESIÓN SE PARTE EN DOS. Clasificar el Conflict como
    # crítico (error_taxonomy) no basta — hay que PARAR. Auditoría y testigo:
    # `evals/s324e_aislamiento_usuarios_auditoria_v1.md` §P4.
    if isinstance(exc, Conflict):
        logger.critical(
            "409 Conflict: otra instancia con el mismo token está haciendo polling. "
            "Parando ESTE proceso para no partir las sesiones de los usuarios."
        )
        # (dúo r37) Se REGISTRA antes de parar. Antes se retornaba aquí mismo y
        # el proceso moría sin incidencia estructurada: el fallo más grave que
        # el bot sabe detectar era justo el único invisible en los insights, y
        # desmentía que `_reportar_error` fuese el punto único. Sin `query`: el
        # Conflict es del transporte, no de un turno concreto.
        # El registro NO puede impedir la parada — de ahí el try/finally: si el
        # registro se cuelga o revienta (y con un 409 puede que Supabase esté
        # perfectamente, pero no se apuesta), la instancia para igual.
        try:
            await _reportar_error(update, exc, etapa="conflict_instancia")
        finally:
            aplicacion = getattr(context, "application", None)
            if aplicacion is not None:
                aplicacion.stop_running()
        return
    query = None
    try:
        # Solo si el fallo viene de un MENSAJE del técnico. En un callback
        # (pulsación de 👍/👎) `effective_message` es el mensaje del PROPIO BOT:
        # tomarlo como consulta guardaría la respuesta del bot en
        # `query_logs.query` como si la hubiera escrito una persona, y el top-5
        # de «preguntas que fallan» se llenaría de texto nuestro.
        if getattr(update, "callback_query", None) is None:
            mensaje = getattr(update, "effective_message", None)
            texto = getattr(mensaje, "text", None)
            if isinstance(texto, str):
                query = texto.strip() or None
    except Exception:                                        # noqa: BLE001
        query = None
    await _reportar_error(update, exc, etapa="global", query=query)


async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 👍/👎 taps (s286). Every path calls callback_query.answer() —
    otherwise a stale tap leaves the client spinner running forever."""
    callback = update.callback_query
    if callback is None:
        return
    match = _FEEDBACK_CALLBACK_PATTERN.match(callback.data or "")
    reason_match = (
        None if match is not None
        else _FEEDBACK_REASON_PATTERN.match(callback.data or "")
    )
    explain_match = (
        None if (match is not None or reason_match is not None)
        else _FEEDBACK_EXPLAIN_PATTERN.match(callback.data or "")
    )
    if match is None and reason_match is None and explain_match is None:
        # Unknown/malformed fb:* payload — resolve the spinner and drop it.
        await callback.answer()
        return
    tap_user_id = callback.from_user.id if callback.from_user else 0
    # A revoked/expired user can still tap an old keyboard in their history:
    # consent gates the WRITE, mirroring the message path.
    if not has_consent(tap_user_id):
        await callback.answer(
            "Para valorar respuestas acepta primero los términos con /start."
        )
        return

    if explain_match is not None:
        # s294 (#60 punto 5b): «Te lo explico». Se abre la caja de respuesta de
        # Telegram (ForceReply) APUNTANDO a este mensaje, y se ESTAMPA el mensaje en
        # `answer_messages` para que la respuesta del técnico se resuelva exacta.
        # Sin ese estampado la vía de reply queda desabastecida (hallazgo F5 del dúo).
        await callback.answer()
        query_log_id = explain_match.group(1)
        try:
            sent = await callback.message.reply_text(
                _FEEDBACK_EXPLAIN_PROMPT,
                # SIN `selective`: apunta a los usuarios @mencionados o al remitente
                # del mensaje respondido, y esta invitación responde al mensaje del
                # PROPIO BOT — así que `selective=True` no apuntaba al técnico y el
                # cliente dejaba la caja «Reply to…» armada tras contestar (cazado
                # por Alberto en prueba real, 2-ago).
                reply_markup=ForceReply(
                    input_field_placeholder=_FEEDBACK_EXPLAIN_PLACEHOLDER,
                ),
            )
            message_id = getattr(sent, "message_id", None)
            chat_id = getattr(getattr(sent, "chat", None), "id", None)
            if isinstance(message_id, int) and isinstance(chat_id, int):
                stamp_answer_messages(query_log_id, chat_id, [message_id])
        except Exception:
            logger.warning("invitación a explicar falló open")
        return

    if reason_match is not None:
        # s294 (#60 punto 5): motivo del 👎. Se anota SOBRE el voto existente; si
        # no hay voto (fila borrada por retención, teclado viejo) no se inventa
        # uno: un motivo sin verdict no es interpretable.
        recorded = set_feedback_reason(
            query_log_id=reason_match.group(2),
            telegram_user_id=tap_user_id,
            reason_class=reason_match.group(1),
        )
        await callback.answer(
            "Gracias, lo tendré en cuenta." if recorded
            else "No se pudo registrar ahora."
        )
        # El teclado del follow-up se retira SIEMPRE que se pudo anotar: deja de
        # invitar a re-pulsar y el mensaje queda como recibo de lo elegido.
        if recorded:
            try:
                await callback.edit_message_reply_markup(reply_markup=None)
            except Exception:
                logger.debug("no se pudo retirar el teclado de motivo")
        return

    verdict = "up" if match.group(1) == "u" else "down"
    query_log_id = match.group(2)
    ok = log_answer_feedback(
        query_log_id=query_log_id,
        telegram_user_id=tap_user_id,
        verdict=verdict,
    )
    if ok:
        await callback.answer("¡Gracias por tu valoración!")
    else:
        # Includes the stale-keyboard case: the query_logs row was RGPD-deleted
        # and the FK rejects the vote — dropped by design.
        await callback.answer("No se pudo registrar ahora. Inténtalo de nuevo.")
        return

    # Follow-up SOLO tras un 👎 registrado y solo si aún no hay motivo (re-pulsar
    # el mismo teclado no debe volver a preguntar). Es un mensaje más, opcional e
    # ignorable: nada bloquea y cualquier fallo se traga — la valoración ya está
    # guardada y el follow-up jamás puede ponerla en riesgo.
    if verdict == "down" and _feedback_reason_enabled():
        try:
            if not has_feedback_reason(query_log_id, tap_user_id):
                await callback.message.reply_text(
                    _FEEDBACK_REASON_PROMPT,
                    reply_markup=_feedback_reason_keyboard(query_log_id),
                )
        except Exception:
            logger.warning("follow-up de 👎 falló open")


def schedule_maintenance(app, store, interval, *, sender, worker_id="janitor-f0", first=None):
    """Register the convo background sweeps (outbox poller + recovery janitor) on
    PTB's JobQueue. Seam for MT-0d — gated by CONVO_MAINTENANCE (default OFF).

    Returns ``[]`` and schedules NOTHING when the flag is off. When on, registers
    two repeating jobs:
      * ``deliver_pending`` (poller) — re-sends due pending/retryable outbox rows;
      * ``reclaim_and_repair`` (janitor) — reports orphaned runs + seals stuck
        ``sending`` rows so the poller can re-send.

    Phase 0: default OFF and never wired to a REAL store — activation needs the
    store dependencies (signed RGPD matrix, applied DDL, minted ``role=convo_rpc``
    JWT, PGRST_DB_SCHEMAS=convo), the scheduling actor, AND a synchronous
    ``sender`` bridged to ``bot.send_message`` (the outbox send is sync, PTB's
    send is async — that bridge is the declared wiring step). Tested via a fake
    JobQueue / by invoking the callbacks directly against a FakeConvoStore.
    """
    if not CONVO_MAINTENANCE:
        return []

    from datetime import datetime, timezone

    from ..orchestrator.lifecycle import deliver_pending, reclaim_and_repair

    async def _poll(_context):
        await asyncio.to_thread(
            deliver_pending, store, sender, datetime.now(timezone.utc)
        )

    async def _janitor(_context):
        await asyncio.to_thread(
            reclaim_and_repair, store, worker_id, datetime.now(timezone.utc)
        )

    return [
        app.job_queue.run_repeating(
            _poll, interval=interval, first=first, name="convo_deliver_pending"
        ),
        app.job_queue.run_repeating(
            _janitor, interval=interval, first=first, name="convo_reclaim_and_repair"
        ),
    ]


def run_bot():
    """Start the Telegram bot."""
    validate_config(require_telegram=True)

    # (s91 F2-S1, dúo #3) fail-fast del flag de identidad EN ARRANQUE: un misconfig en Railway
    # (flag legacy ON junto a IDENTITY_RESOLVE, o typo en el valor) debe tumbar el deploy
    # visible, no fallar el 100% de queries en runtime.
    from src.rag import catalog_resolver as _resolver
    _resolver.mode()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # (fase B) La guardia de grupo -1 se retiro: la invalidacion de #70 vive en el
    # plan de turno (handle_message/handle_voice), no en un TypeHandler previo.

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("accept", accept_command))
    app.add_handler(CommandHandler("help", help_command))
    # SIN gate de consentimiento a propósito: el detalle tiene que poder leerse antes de
    # aceptar, o la aceptación no sería informada.
    app.add_handler(CommandHandler("privacidad", privacy_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    # Unconditional (NOT gated by TELEGRAM_FEEDBACK): stale keyboards in chat
    # history must always resolve, even after the flag is turned off.
    app.add_handler(CallbackQueryHandler(feedback_callback, pattern=r"^fb:"))

    # s324e — la red de seguridad. Va SIN gatear a propósito, igual que el
    # callback de arriba y por el mismo motivo: la conducta que sustituye es el
    # SILENCIO, y una red que se registra solo si un flag está encendido no es
    # una red. Lo que sí lleva flags son sus dos efectos —el aviso al técnico
    # (BOT_ERROR_REPLY, default on) y el registro (BOT_ERROR_LOGGING, default
    # off)— porque cada uno tiene su propio riesgo y su propio kill-switch.
    app.add_error_handler(error_handler)

    logger.info("Bot started. Listening for text and voice messages...")
    # s307: calienta la caché de fabricantes ANTES del polling — el primer saludo
    # no paga la llamada REST; si falla, el saludo usa el fallback y reintenta.
    try:
        _fabricantes_resumen()
    except Exception:                                    # noqa: BLE001
        pass
    app.run_polling(allowed_updates=Update.ALL_TYPES)
