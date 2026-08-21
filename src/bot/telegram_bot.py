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
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    TypeHandler,
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
    CLASIFICADOR_PREGUNTAS,
    validate_config,
)
from ..rag.retriever import (
    extract_product_models, get_category_models,
    get_manufacturers_by_docs, get_products_by_manufacturer,
    _MANUFACTURER_ALIASES, resolve_manufacturer_alias,
    get_all_models_by_category, CATEGORY_TERMS, PCI_TERMS,
    lookup_model_manufacturer, get_available_manufacturers, manufacturer_in_db,
    classify_model_manufacturer,
)
# s319 PR-C: retrieve_chunks/rerank/generate_answer/RagServingAdapters/
# execute_rag_turn ya NO se importan aquí — el handler dejó de construir el
# pipeline inline; los adapters de producción los arma el orquestador
# (from_production) y el seam execute_rag_turn vive en serving_pipeline.
from .procedencia import Procedencia  # noqa: E402
from ..rag.runtime_trace import build_rag_serving_trace
from ..flags import inventario_fraseos_activo, mismatch_answer_activo
from .acotar import acotar
from ..logging_db import (
    allowlist_estado,
    canjear_invitacion,
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
from . import access
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
    _SWITCH_FRASE, _THANKS_PATTERNS, _VOCABULARIO_DOMINIO, Hecho, Meta, Preambulo,
    TurnPlan,
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


_CORRECCION_FN_CELL: dict = {}


def _correccion_seam(correccion_obs: dict):
    """(s333 B3) Seam del clasificador CORRECCION/NUEVO — espejo de `_intent_seam`
    (ver su docstring: celda de proceso, construcción ruidosa con centinela,
    telemetría por turno hacia la sección `correccion` de rag_trace).

    Desviación DECLARADA del espejo: el flag se lee con enum ESTRICTO on/off
    (patrón `correction_enabled`/r19 — un typo en Railway revienta ruidoso, no
    degrada en silencio), mientras INTENT_LLM conserva su parser laxo histórico."""
    raw = (os.getenv("F1_CORRECCION_LLM", "") or "").strip().lower()
    if raw in ("", "off"):
        correccion_obs.update(status="off", decision="none", latency_ms=0)
        return None
    if raw != "on":
        raise RuntimeError(
            f"F1_CORRECCION_LLM={raw!r} no reconocido (on|off) — fail-fast")
    correccion_obs.update(status="not_invoked", decision="none", latency_ms=0)

    def _lazy_correccion(q, last_query, marca):
        fn = _CORRECCION_FN_CELL.get("fn")
        if fn is None:
            try:
                from ..orchestrator.correccion_llm import construir_correccion_fn

                fn = construir_correccion_fn(ANTHROPIC_API_KEY)
            except Exception as exc:      # noqa: BLE001
                logger.error("correccion_llm: construccion FALLO (%s) — "
                             "flag ON degradado a conducta OFF",
                             type(exc).__name__)
                fn = False                # centinela: no reintentar
            _CORRECCION_FN_CELL["fn"] = fn
        if fn is False:
            correccion_obs["status"] = "construction_failed"
            return None                   # fail-open declarado
        t0 = _time.perf_counter()
        decision = fn(q, last_query, marca)
        correccion_obs.update(
            status="invoked",
            decision=decision if decision in ("correccion", "nuevo") else "fail_open",
            latency_ms=int((_time.perf_counter() - t0) * 1000),
        )
        return decision

    return _lazy_correccion


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
    # (s324f, v8) El bloque «EN DESARROLLO» va ANTES del de datos a propósito: es lo
    # que más protege a un técnico que vaya a usar una respuesta en una instalación
    # real. Y «una treintena» en vez de una lista cerrada — el v7 nombraba TRES
    # marcas con 30 fabricantes en corpus, y ése es justo el error que caducó.
    "🤖 *Asistente técnico* — _versión beta, en desarrollo_\n\n"
    "Te doy información de los manuales técnicos de *una treintena de fabricantes* "
    "(Notifier, Morley, Detnov, Kidde y más). Por texto o por audio 🎤.\n\n"
    "⚠️ *EN DESARROLLO*: puedo equivocarme. Mis respuestas *no sustituyen al manual "
    "oficial ni al criterio de un técnico cualificado* — contrástalas antes de usarlas "
    "en una instalación. Si algo no cuadra, dímelo con 👎.\n\n"
    "⚠️ *Antes de empezar*\n\n"
    "Para mejorar el sistema, guardamos *las preguntas que respondo y mis respuestas*, junto "
    "con tu ID de Telegram, el nombre que nos des al aceptar y tus valoraciones 👍/👎. Si "
    "mandas un audio, guardamos solo su transcripción: el audio original NO se guarda.\n\n"
    "*Quién responde de tus datos*: *Fontiber Industrial Partners, S.L.* — también si "
    "trabajas en otra empresa del grupo: el responsable es Fontiber, no tu empresa.\n"
    "*Cuánto*: 24 meses vinculado a ti; después se retira tu identificador de tus consultas "
    "y valoraciones.\n"
    # (s324f, v9 — decisión de Alberto) La mención EXPRESA a que los datos salen
    # de la UE baja a `/privacidad`. No desaparece: el RGPD exige informar de las
    # transferencias internacionales y son reales (Anthropic, Voyage, OpenAI y
    # Telegram operan fuera). Lo que cambia es DÓNDE se lee — la segunda capa es
    # justo donde el aviso en dos capas pone el detalle, y esta primera queda
    # para lo que hay que saber antes de decidir si aceptas.
    "*Quién lo ve*: el equipo técnico de Fontiber y los proveedores de IA y "
    "alojamiento necesarios para que funcione (detalle en /privacidad).\n"
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
    "10, 28004 Madrid · *info@fontiber.com* — Fontiber es el responsable del tratamiento "
    "aunque trabajes en otra empresa del grupo.\n"
    "*Base jurídica*: tu consentimiento, el que das al enviar `/accept`. Puedes retirarlo "
    "cuando quieras escribiendo a *info@fontiber.com*; retirarlo no afecta a los "
    "tratamientos ya hechos.\n\n"
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
    "te perfila para ninguna otra cosa. Aplica a todas las personas que usen el "
    "asistente.\n\n"
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


# ── LA PUERTA (s324e): control de acceso al piloto ───────────────────────────
# Va como handler de GRUPO -1 y no como comprobación al principio de cada
# handler. Motivo estructural: PTB evalúa los grupos de menor a mayor y un
# `ApplicationHandlerStop` desde aquí detiene el update para TODOS los demás
# (verificado en el código de PTB 22.7, `Application.process_update`). Así el
# handler número nueve que alguien añada dentro de tres meses nace protegido sin
# acordarse de nada. Un `if not autorizado: return` repetido en cada handler es
# la versión que se olvida — y la que ya se olvidó una vez: el gate de
# consentimiento existe desde s21 y `feedback_callback` no lo tuvo hasta s286.
#
# ORDEN RESPECTO AL CONSENTIMIENTO: **primero la puerta, después el
# consentimiento.** Tres razones, la primera es la que manda:
#   1. MINIMIZACIÓN. Si el consentimiento fuese antes, cualquiera que encuentre
#      el bot podría enviar `/accept Su Nombre` y quedaríamos con su nombre y su
#      id de Telegram guardados para siempre en `user_consent` (tabla cuyo plazo
#      sigue siendo un `[DECIDIR]` en la matriz RGPD) — datos personales de
#      alguien que jamás va a usar el sistema y para una finalidad que no
#      existe. La puerta delante hace que solo se registre a quien fue invitado.
#   2. Es la pregunta que se puede contestar sin tratar nada más: la allowlist
#      necesita el id, que Telegram ya nos entregó al recibir el mensaje.
#   3. Contarle a alguien los términos y el detalle de `/privacidad` para
#      rechazarle después es peor experiencia y peor higiene.
# Las DOS excepciones están abajo, nombradas y con motivo, y hay un test que
# impide que la lista crezca sin querer.

#: Comandos que quedan FUERA de la puerta.
#:   · `/start` — es el ÚNICO sitio por el que Telegram entrega el payload del
#:     enlace de invitación (`?start=<token>` → `context.args`). Si estuviera
#:     detrás de la puerta, ninguna invitación podría canjearse jamás. Hace su
#:     propia comprobación, explícita, y canjea o enseña la puerta.
#:   · `/privacidad` — poder leer el aviso ANTES de aceptar nada es lo que hace
#:     que la aceptación cuente como informada (s295). Gatearlo sería romper esa
#:     promesa por un control de acceso, y el texto no contiene dato personal de
#:     nadie: es el aviso público del responsable.
COMANDOS_SIN_PUERTA = ("/start", "/privacidad")


def _comando_de(update: object) -> str | None:
    """`'/start AbC-123'` → `'/start'`; `'/help@PCI_bot'` → `'/help'`.

    None si el update no es un mensaje de texto que empiece por comando. Se
    normaliza el sufijo `@bot` porque Telegram lo añade en grupos y sin quitarlo
    la exención no casaría."""
    try:
        texto = getattr(getattr(update, "message", None), "text", None)
        if not isinstance(texto, str):
            return None
        texto = texto.strip()
        if not texto.startswith("/"):
            return None
        return texto.split()[0].split("@")[0].lower()
    except Exception:                                        # noqa: BLE001
        return None


def _cuenta_para_cuota(update: object) -> bool:
    """¿Este update gasta cupo diario? Solo los MENSAJES de contenido.

    Fuera quedan los comandos (no cuestan modelo) y las pulsaciones de teclado
    (👍/👎: penalizar el feedback sería exactamente el incentivo contrario). Los
    audios SÍ cuentan: pagan transcripción antes que nada.

    Se cuenta en la puerta y no en el pipeline a propósito: aquí es donde la
    barrera vale también contra un bucle o una cuenta comprometida, aunque el
    precio sea que un «hola» consuma uno de los 30 (el default lleva holgura
    para eso).
    """
    try:
        if getattr(update, "callback_query", None) is not None:
            return False
        mensaje = getattr(update, "message", None)
        if mensaje is None:
            return False
        if getattr(mensaje, "voice", None) or getattr(mensaje, "audio", None):
            return True
        texto = getattr(mensaje, "text", None)
        if not isinstance(texto, str) or not texto.strip():
            return False
        return not texto.strip().startswith("/")
    except Exception:                                        # noqa: BLE001
        return False


async def _responder_puerta(update: object, texto: str) -> None:
    """Avisa de un rechazo. NO LANZA NUNCA: una excepción escapando de aquí
    llegaría a `process_error`, que devuelve False, y PTB seguiría con el
    siguiente grupo — es decir, el rechazo se convertiría en un PASE. Texto
    plano, como los mensajes de error y por el mismo motivo."""
    try:
        callback = getattr(update, "callback_query", None)
        if callback is not None:
            # `answer` acota a 200 caracteres: se manda el primer párrafo, que
            # está escrito para funcionar suelto.
            await callback.answer(texto.split("\n\n")[0][:200], show_alert=True)
            return
        mensaje = _mensaje_de(update)
        if mensaje is not None:
            await mensaje.reply_text(texto)
    except Exception:                                        # noqa: BLE001
        logger.warning("puerta: no se pudo avisar al remitente")


async def access_gate(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """La puerta. Deja pasar, o para el update para todos los grupos.

    **No deja escapar excepciones, y eso es una propiedad de seguridad, no
    higiene.** Verificado leyendo PTB 22.7: si un handler de grupo -1 lanza algo
    que no sea `ApplicationHandlerStop`, `process_update` llama a
    `process_error` y, como nuestro `error_handler` no relanza
    `ApplicationHandlerStop`, devuelve False y el bucle CONTINÚA con el grupo 0.
    O sea: un fallo interno de la puerta abriría la puerta. Por eso el cuerpo va
    entero en un `try` y el camino de excepción termina igualmente en
    `ApplicationHandlerStop` — fail-CLOSED.

    Consecuencia declarada: un defecto aquí deja el bot inaccesible para todos.
    Las dos salidas no exigen deploy — `BOT_ALLOWLIST=off` (kill-switch) y
    `BOT_ALLOWLIST_BOOTSTRAP` (que se resuelve sin tocar base ni caché).
    """
    if not access.acceso_activo():
        return                              # inerte: el bot de HOY, exacto

    veredicto = None
    try:
        tipo_chat = getattr(
            getattr(update, "effective_chat", None), "type", None
        )
        if not access.es_chat_privado(tipo_chat):
            # 1) CHAT PRIVADO, y va ANTES que todo lo demás — incluidos los
            #    comandos exentos. La puerta autoriza a una PERSONA, pero lo que
            #    hay que proteger es dónde se PUBLICA la respuesta: un DG
            #    autorizado que meta el bot en un grupo hace que la lean
            #    participantes no invitados, que es exactamente lo que el red
            #    line prohíbe. Delante de la exención de `/start` a propósito:
            #    un `/start <token>` tecleado en un grupo canjearía la
            #    invitación desde ahí.
            #    Se avisa UNA vez por grupo (`debe_avisar_del_grupo`) y las
            #    demás veces se para en silencio: repetirlo en cada mensaje
            #    sería ruido para ellos y envíos para nosotros.
            chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
            if access.debe_avisar_del_grupo(chat_id):
                logger.warning("puerta: uso en chat NO privado (tipo=%r)",
                               tipo_chat)
                await _responder_puerta(update, access.MENSAJE_SOLO_PRIVADO)
            # cae al `raise ApplicationHandlerStop` del final, sin veredicto
        elif _comando_de(update) in COMANDOS_SIN_PUERTA:
            return
        else:
            user_id = _usuario_de(update)
            # A un HILO: `allowlist_estado` es httpx síncrono con 10 s de timeout
            # y esto corre en CADA update. Mismo patrón que `_reportar_error` y
            # `run_turn`. Con la caché caliente no hay I/O — solo el salto de
            # hilo.
            veredicto = await asyncio.to_thread(
                access.decidir, user_id, allowlist_estado
            )
            if veredicto.permitido and _cuenta_para_cuota(update):
                veredicto = access.consumir_cuota(user_id)
            if veredicto.permitido:
                return
            logger.info("puerta: update rechazado (motivo=%s origen=%s)",
                        veredicto.motivo, veredicto.origen)
    except Exception as exc:                                 # noqa: BLE001
        veredicto = None
        # Por el punto ÚNICO (s324e): clasifica, avisa al técnico y registra la
        # incidencia. Sin `query`: la puerta no ha mirado el contenido.
        await _reportar_error(update, exc, etapa="puerta_acceso")

    if veredicto is not None and veredicto.mensaje:
        await _responder_puerta(update, veredicto.mensaje)
    raise ApplicationHandlerStop


#: (s324f) Última vez que se avisó de cada clase de incidencia crítica, para no
#: inundar. Un fallo de cuota o de credenciales no ocurre UNA vez: ocurre en cada
#: turno hasta que alguien lo arregla, así que sin cota el operador recibiría un
#: Telegram por mensaje y dejaría de mirarlos — que es exactamente perder el
#: aviso. En memoria y declarado: un redespliegue lo reinicia y se vuelve a
#: avisar, que es la degradación correcta (mejor un aviso de más tras un
#: reinicio que ninguno).
_ULTIMO_AVISO_CRITICO: dict[str, float] = {}
#: Una hora entre avisos de la misma clase+etapa. Suficiente para no repetirse
#: en una tormenta y corto para que un problema nuevo del día siguiente avise.
_SILENCIO_AVISO_S = 3600.0


async def _avisar_al_operador(context: ContextTypes.DEFAULT_TYPE,
                              incidencia) -> None:
    """Manda a quien administra un aviso de incidencia CRÍTICA.

    QUÉ RESUELVE: hasta hoy, un fallo que sólo una persona puede arreglar
    —cuota agotada, credenciales rechazadas, canal roto— viajaba al técnico, que
    no puede hacer nada, y al informe de incidencias, que alguien tiene que
    acordarse de mirar. En el piloto eso significó que Alberto se enteró porque
    la usuaria se lo contó.

    NO lleva ni la consulta ni el identificador de quien la hizo: el operador
    necesita saber QUÉ está roto, no quién tropezó. Eso ya vive en
    `bot_errors`/`query_logs` con su gobernanza.

    Nunca lanza: es un aviso, no un paso del turno. Si falla, se deja constancia
    en el log y ya — la incidencia original ya está registrada, y recursar aquí
    sería convertir un fallo en dos.
    """
    try:
        destinos = access.ids_bootstrap()
        if not destinos:
            return
        # (dúo r40) La clave lleva el TIPO de excepción, no sólo clase+etapa:
        # mientras `cuota_agotada` y `AuthenticationError` compartan la clase
        # `llm_fallo` —lo harán hasta que se aplique la 017— una silenciaría a la
        # otra durante una hora, y son dos problemas con dos arreglos distintos.
        clave = f"{incidencia.clase}:{incidencia.etapa}:{incidencia.tipo_excepcion}"
        ahora = _time.time()
        ultimo = _ULTIMO_AVISO_CRITICO.get(clave, 0.0)
        if ahora - ultimo < _SILENCIO_AVISO_S:
            return

        texto = (
            "⚠️ Incidencia CRÍTICA en el bot\n\n"
            f"Qué: {incidencia.tipo_excepcion} en {incidencia.etapa}\n"
            f"Detalle: {(incidencia.mensaje_corto or '-')[:300]}\n"
            f"Código: {incidencia.codigo}\n\n"
            "Le afecta a quien esté usando el bot y no se arregla solo. "
            "No volveré a avisar de esto en una hora."
        )
        entregado = False
        for destino in destinos:
            try:
                await context.bot.send_message(chat_id=destino, text=texto)
                entregado = True
            except Exception as envio:                       # noqa: BLE001
                logger.warning("aviso critico no entregado a %s (%s)",
                               destino, type(envio).__name__)
        # (dúo r40) La cota se marca DESPUÉS y sólo si alguien lo recibió. Antes
        # se marcaba al entrar, así que una caída transitoria de Telegram dejaba
        # al operador sin aviso Y silenciaba la siguiente hora: el peor de los
        # dos mundos, y precisamente cuando algo va mal de verdad.
        if entregado:
            _ULTIMO_AVISO_CRITICO[clave] = ahora
    except Exception:                                        # noqa: BLE001
        logger.warning("el aviso al operador fallo (incidencia %s)",
                       getattr(incidencia, "codigo", "?"))


async def _avisar_canje(context: ContextTypes.DEFAULT_TYPE, update: Update,
                        resultado) -> None:
    """Avisa a quien administra de que se ha canjeado una invitación.

    PARA QUÉ (Alberto): el un-solo-uso limita el daño de un reenvío a UNA
    persona, pero no decide QUÉ persona — quien reciba el enlace y pulse antes,
    entra. Este aviso no lo impide; lo hace DETECTABLE en minutos, enfrentando
    «era para X» con «lo ha canjeado Y». Con eso, la reacción (`revocar-acceso`)
    llega el mismo día en vez de en la siguiente auditoría.

    A QUIÉN: a los ids de `BOT_ALLOWLIST_BOOTSTRAP`, que es quien administra.
    Sin ninguno configurado NO falla: deja constancia en el log y sigue — un
    aviso no puede ser un requisito para dar de alta.

    **NUNCA impide el alta ni rompe el canje**: el alta ya está confirmada en la
    base cuando esto corre, y cada envío va en su propio `try`. Un fallo se
    reporta por el punto ÚNICO (`_reportar_error`) con `update=None`, que es
    deliberado: así la incidencia se clasifica y se registra, pero NO se le
    contesta nada al DG — acaba de recibir «Invitación aceptada» y decirle que
    algo ha fallado sería alarmarle por un problema que no es suyo ni le afecta.
    """
    destinos = access.ids_bootstrap()
    if not destinos:
        logger.warning(
            "canje SIN aviso: BOT_ALLOWLIST_BOOTSTRAP esta vacio, asi que nadie "
            "recibe el contraste 'era para X / lo canjeo Y'"
        )
        return
    autor = getattr(update, "effective_user", None)
    texto = access.texto_aviso_canje(
        nota=getattr(resultado, "nota", None),
        nombre=getattr(autor, "full_name", None) or getattr(autor, "first_name", None),
        alias=getattr(autor, "username", None),
        telegram_user_id=getattr(autor, "id", 0) or 0,
    )
    for administrador in sorted(destinos):
        try:
            await context.bot.send_message(chat_id=administrador, text=texto)
        except Exception as exc:                             # noqa: BLE001
            await _reportar_error(None, exc, etapa="aviso_canje")


async def _canjear_invitacion(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              user_id: int) -> bool:
    """Canjea el enlace que trae `/start`, si lo trae. True = queda dentro.

    Telegram entrega el payload de `https://t.me/<bot>?start=<token>` como
    primer elemento de `context.args`. Se filtra la FORMA antes de preguntar a
    la base (`/start loquesea` no debe costar un roundtrip); la VALIDEZ solo la
    puede decidir el canje atómico.
    """
    args = getattr(context, "args", None) or []
    payload = args[0] if args else None
    if not access.es_payload_plausible(payload):
        await update.message.reply_text(access.MENSAJE_NO_AUTORIZADO)
        return False

    resultado = await asyncio.to_thread(
        canjear_invitacion,
        token_hash=access.hash_token(payload),
        telegram_user_id=user_id,
    )
    if resultado.estado == access.CANJE_OK:
        # La caché guarda el NO de hace un instante (el de la comprobación de
        # arriba): sin este adelanto, el DG recién dado de alta rebotaría contra
        # su propia invitación hasta que caducara el negativo.
        access.recordar_alta(user_id)
        # Sin el `telegram_user_id` (dúo, medio 5): los logs de Railway están
        # fuera de la matriz de retención y de cualquier supresión a petición,
        # así que no son sitio para un identificador. Se registra el id de la
        # INVITACIÓN, que es un uuid y no identifica a nadie por sí solo, y que
        # además correlaciona mejor con el listado del script. Quién canjeó vive
        # donde está gobernado: `bot_invitaciones.canjeada_por` y el aviso.
        logger.info("puerta: invitacion %s canjeada", resultado.invitacion_id)
        # Primero el acuse al DG y después el aviso al administrador: su alta ya
        # está confirmada y su mensaje no debe esperar a un envío ajeno.
        await update.message.reply_text(access.MENSAJE_INVITACION_ACEPTADA)
        await _avisar_canje(context, update, resultado)
        return True
    if resultado.estado == access.CANJE_INDETERMINADO:
        # Mensaje que es VERDAD en los dos casos posibles (dúo, medio 4): el
        # canje pudo confirmarse y perderse la respuesta, y entonces el enlace
        # ya no vale por mucho que reintente. `logging_db` intenta liberarlo;
        # este texto no promete que lo haya conseguido.
        await update.message.reply_text(access.MENSAJE_CANJE_INCIERTO)
        return False
    await update.message.reply_text(access.MENSAJE_INVITACION_NO_VALIDA)
    return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — canje de invitación, luego términos o bienvenida.

    Este handler está EXENTO de la puerta global (ver `COMANDOS_SIN_PUERTA`) y
    por eso comprueba el acceso él mismo. Nota deliberada: si quien pulsa el
    enlace YA está autorizado, el token NO se canjea — se le da la bienvenida y
    la invitación sigue viva para la persona a la que iba dirigida.
    """
    user_id = update.effective_user.id if update.effective_user else 0
    if access.acceso_activo():
        veredicto = await asyncio.to_thread(
            access.decidir, user_id, allowlist_estado
        )
        if not veredicto.permitido:
            if veredicto.motivo == "indeterminado":
                # No se intenta canjear con la base caída: se gastaría el enlace
                # sin poder confirmar el alta.
                await update.message.reply_text(access.MENSAJE_INDETERMINADO)
                return
            if not await _canjear_invitacion(update, context, user_id):
                return

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
        # (s332 §2) Las asunciones del turno se DECLARAN aquí, antes de la respuesta:
        # el técnico ve lo que se asumió por él y puede desmentirlo en el acto — la
        # visibilidad ES el control. No hace falta re-mirar `ASR_AVISOS`: con el lever
        # apagado la tabla no emite asunciones, así que este bucle no itera. `modo` es
        # enum cerrado validado en `Asuncion`, de modo que el `else` ES 'aviso'.
        for asuncion in normalization.asunciones:
            if asuncion.modo == "reescrito":
                confirmation += (
                    f"\n🏷 Entiendo que preguntas por {asuncion.asumido} (el audio se "
                    f"transcribió como «{asuncion.detectado}»). Si no es eso, dímelo."
                )
            else:
                confirmation += (
                    f"\nℹ️ Nota: hay una confusión de voz observada "
                    f"«{asuncion.detectado}»↔{asuncion.asumido}. "
                    f"Si dictaste {asuncion.asumido}, dímelo."
                )
        # Plain text avoids Telegram Markdown parse failures on arbitrary ASR.
        await update.message.reply_text(confirmation)

        # (s324h) La voz entra por el MISMO preludio que el texto. Antes esto era
        # una llamada suelta a `_decidir_transicion` seguida de un salto directo a
        # `_process_query`: el predicado de invalidación corría, pero el PLAN no,
        # así que las nueve rutas de atajo eran inalcanzables hablando. El propio
        # código lo declaraba como aplazamiento de fase B del #70; el piloto lo
        # convirtió en defecto y Alberto lo adjudicó como prioridad (18-ago).
        #
        # `plan_turn` ya llama al predicado por dentro y devuelve la transición, así
        # que la llamada duplicada desaparece: un punto de decisión, no dos.
        #
        # La guarda de `user_data` se conserva (era propia del camino de voz): sin
        # ella, un `context` sin `user_data` de tipo dict reventaría el turno donde
        # hoy sólo se salta la invalidación.
        #
        # RESTRICCIÓN PAGADA QUE SE RETIRA, y por qué (Sol fase-B M5): aquí había un
        # `try/except` local que, ante un fallo del clasificador, escribía un
        # `logger.warning` y dejaba que el turno de voz continuase.
        #
        # La razón que la retira es UNA sola: PARIDAD. El camino de texto nunca la
        # tuvo, y este lote existe para que los dos canales se comporten igual;
        # mantenerla sería conservar a propósito la divergencia que venimos a matar.
        #
        # CORRECCIÓN (Sol, r49) — la primera versión de este comentario añadía una
        # segunda razón, «observabilidad», y era FALSA: decía que la excepción pasa
        # a subir a la taxonomía y a dejar fila en `bot_errors`. No sube. Para ESTE
        # fallo concreto, `plan_turn` la captura en su propio `try/except` de
        # fail-open (`turn_plan.py`, «plan total: fail-open») y preserva la
        # transición. Así que se pierde también el `warning` anterior SIN ganar la
        # incidencia: en observabilidad la conducta nueva es PEOR, no mejor.
        #
        # Eso NO es un defecto que introduzca este lote — el fail-open mudo de
        # `plan_turn` ya se tragaba la misma señal en el camino de texto —, pero
        # queda declarado como deuda en vez de vendido como mejora. Lo que sí sube
        # a la taxonomía, y sí deja incidencia, son los fallos de las consultas de
        # identidad (`_resolver_hechos`), que corren FUERA de ese `try`.
        #
        # Lo que NO se hace, y es deliberado: NO se añade una frontera de fail-open
        # que degrade al RAG. El dúo la mató dos veces — Sol por SEGURIDAD (saltarse
        # `mismatch`/`marca_no_servida` puede contestar con el manual de otra marca
        # cuando no se pudo verificar la identidad) y Fable por OBSERVABILIDAD.
        await _servir_turno(update, context, user_id, query,
                            procedencia=Procedencia.de_voz(raw_transcription),
                            asunciones_asr=normalization.asunciones)

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
    await _servir_turno(update, context, user_id, query,
                        procedencia=Procedencia.de_texto())


#: `Meta.fuente` mantiene su propio vocabulario en castellano. El mapa es
#: EXPLÍCITO a propósito: la primera versión escribía `"voz" if source == "voice"
#: else "texto"`, que manda cualquier canal futuro a «texto» en silencio — el
#: mismo default mentiroso que este lote existe para matar, reintroducido en el
#: propio arreglo (Sol, r47). Con el mapa, un canal sin traducir revienta en el
#: test en vez de clasificarse mal en producción.
_FUENTE_META = {"text": "texto", "voice": "voz"}


async def _servir_turno(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        user_id: int, query: str, *,
                        procedencia: Procedencia,
                        asunciones_asr: tuple = ()) -> None:
    """El turno, igual para los dos canales.

    (s324h) Antes esto vivía dentro de `handle_message` y la voz se lo saltaba
    entero: llamaba al predicado de invalidación por su cuenta y saltaba al RAG,
    así que las NUEVE rutas de atajo eran inalcanzables hablando. Lo que se
    comparte es el PRELUDIO —captura de reply, `Meta`, hechos, plan, transición—;
    el despachador (`_ejecutar_plan`) ya estaba separado.

    Lo ÚNICO que distingue un canal de otro es de dónde sale `query` y qué
    `Procedencia` lo acompaña. Cero ramas por canal aquí dentro.
    """
    # s294 (#60 punto 5b): si el mensaje RESPONDE a un mensaje del bot que está
    # anclado, es una explicación sobre esa consulta. Pasa a correr también en voz
    # (cambio B1, declarado): hoy una explicación hablada en reply se iba al RAG.
    if await _capture_reply_explanation(update, user_id, query):
        return

    # --- Plan de turno (fase A DEC-200): decision UNICA, ejecucion tonta ---
    # La cascada entera (cortesia -> catalogo -> marca -> 5-bis -> feedback -> RAG)
    # vive en turn_plan.plan_turn; aqui solo se resuelven los HECHOS que el plan
    # declara y se ejecuta la ruta. La politica de log de cada ruta es un CAMPO del
    # plan (la promesa del aviso v7 --cortesia sin log-- pasa de estar implicita en
    # el orden de los ifs a ser dato verificable).
    # (s324e — DEC-224 §B / DEC-226 opción (a)) El LEVER entra al plan como DATO:
    # `plan_turn` sigue pura y no lee entorno.
    meta = Meta(es_reply=update.message.reply_to_message is not None,
                mismatch_answer=mismatch_answer_activo(),
                inventario_fraseos=inventario_fraseos_activo(),
                fuente=_FUENTE_META[procedencia.source])
    # (s324h, Fable r49 + hallazgo propio) La guarda de `user_data` protege SÓLO
    # lo que necesita `user_data` —el estado y la invalidación—, no el plan entero.
    # La primera versión la puso como una rama en `handle_voice` que mandaba la voz
    # directa al RAG: funcionalmente, la frontera de fail-open que el comentario de
    # arriba declara muerta dos veces por el dúo. Sin plan no corre `mismatch`, así
    # que podía contestarse con el manual de otra marca — y encima degradaba SIN
    # log. Aquí el plan corre SIEMPRE y en los dos canales; sólo el estado se salta.
    _ud = context.user_data if isinstance(
        getattr(context, "user_data", None), dict) else None
    estado_modelos = _estado_modelos_conversacion(_ud) if _ud is not None else ()
    plan = plan_turn(query, estado_modelos, meta,
                     _resolver_hechos(plan_turn_hechos(query, estado_modelos, meta)))
    # Fase B: la transicion del plan ES la fuente de invalidacion (la guardia -1 se
    # retiro). ORDEN = el contrato de flujo de datos del v3 (Sol r7 C3): la transicion
    # se aplica ANTES de ejecutar la ruta, asi la politica F1 resuelve DESDE el estado
    # post-plan -- sin esto, un carry-forward calculado sobre el estado viejo
    # sobrescribiria la invalidacion y #70 reviviria por construccion.
    if plan.transicion == _turn_plan.INVALIDAR and _ud is not None:
        _aplicar_estado(_ud, WorkingState())
        logger.info("plan #70: cambio de marca a %r -- contexto de producto invalidado",
                    plan.transicion_marca)
    await _ejecutar_plan(update, context, user_id, query, plan,
                         procedencia=procedencia, asunciones_asr=asunciones_asr)


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


def _refrescar_estado_atajo(context, query: str, respuesta: str) -> None:
    """(s334 §3, R8) Tras una ruta terminal de atajo CON contenido: la transición
    de respuesta (last_query fresca, pending consumido) vía el escritor único.
    Flag off = no-op byte-idéntico. Cortesías NO llaman aquí (no cambian de tema).
    Fail-open total: un estado que no se puede refrescar jamás rompe el turno ya
    respondido."""
    from datetime import datetime, timezone

    from ..orchestrator.conversation_policy import WorkingState
    from ..orchestrator.conversation_policy_impl import (
        advance_after_shortcut,
        estado_atajos_enabled,
    )
    try:
        if not estado_atajos_enabled():
            return
        user_data = getattr(context, "user_data", None)
        if not isinstance(user_data, dict):
            return
        ws = user_data.get("mt_working_state")
        if not isinstance(ws, WorkingState):
            ws = WorkingState()
        _aplicar_estado(user_data, advance_after_shortcut(
            ws, query, respuesta[:500], datetime.now(timezone.utc)))
    except Exception:                            # noqa: BLE001 — fail-open declarado
        logger.warning("estado_atajos: refresco fallo — estado intacto")


async def _ejecutar_plan(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         user_id: int, query: str, plan: TurnPlan, *,
                         procedencia: Procedencia,
                         asunciones_asr: tuple = ()):
    """Despachador TONTO: ejecuta la ruta del plan sin re-examinar el texto. Las
    respuestas son las de hoy, byte a byte (tests de equivalencia s316e).

    (s324h) `procedencia` es keyword-only y SIN DEFAULT a propósito: el defecto que
    este lote arregla era justo un default que mentía. Omitirla es un `TypeError`
    aquí y ahora, no una fila de `query_logs` que afirma para siempre que un audio
    se tecleó."""
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
                          source=procedencia.source,
                          transcription=procedencia.transcription,
                          response=respuesta, response_length=len(respuesta))
                asegurar_seudonimo(user_id)
            _refrescar_estado_atajo(context, query, respuesta)
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
    if ruta in ("fabricantes", "catalogo"):
        # (s324f) Las dos preguntas de catálogo comparten manejador porque
        # comparten RESPUESTA: la lista de marcas. La de productos acaba aquí
        # por una razón medida, no por pereza — 756 modelos no caben en un
        # mensaje de Telegram, así que la única respuesta completa que se puede
        # dar a «¿qué tienes?» es «de estas marcas; dime una». Lo que cambia
        # entre ambas es el encabezado, que reconoce lo que se preguntó.
        if plan.typing:
            await update.message.chat.send_action("typing")
        respuesta = _texto_fabricantes(por_producto=(ruta == "catalogo"))
        await _responder_atajo(
            update, respuesta, user_id=user_id, query=query,
            registrar=plan.log_consulta, procedencia=procedencia,
        )
        _refrescar_estado_atajo(context, query, respuesta)
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
                      source=procedencia.source,
                      transcription=procedencia.transcription,
                      response=respuesta, response_length=len(respuesta))
            asegurar_seudonimo(user_id)
        _refrescar_estado_atajo(context, query, respuesta)
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
                      source=procedencia.source,
                      transcription=procedencia.transcription,
                      response=respuesta, response_length=len(respuesta))
            asegurar_seudonimo(user_id)
        _refrescar_estado_atajo(context, query, respuesta)
        return
    if ruta == "feedback":
        await _handle_feedback(update, context, query)
        return
    # conversacional (default del plan y de los fallbacks)
    # (s324h, CRÍTICO convergente de Sol y Opus 5 en r44) La procedencia se
    # REENVÍA. Sin esto, cablear la voz al despachador registraría TODA pregunta
    # técnica hablada —el destino mayoritario del canal— como si fuera texto: una
    # regresión de algo que hoy funciona, porque `handle_voice` sí la pasa cuando
    # llama a `_process_query` por su cuenta.
    await update.message.chat.send_action("typing")
    # (s332 B5) `asunciones_asr` viaja en kwarg PARALELO a la procedencia y su
    # default `()` es VERDAD para todo llamador de texto (a diferencia del
    # `="text"` que s324h mató: aquí omitirlo no miente — texto no tiene ASR).
    await _process_query(update, context, query, preambulo=plan.preambulo,
                         source=procedencia.source,
                         transcription=procedencia.transcription,
                         asunciones_asr=asunciones_asr)


def _texto_fabricantes(*, por_producto: bool) -> str:
    """La lista de fabricantes servibles, acotada y con su follow-up.

    (s324f) Sustituye al volcado de modelos que respondía a esta pregunta. La
    fuente es `get_manufacturers_by_docs()` —`documents` con `status=active`,
    paginado con orden estable— y NO los `product_model` de `chunks`: ésa es la
    regla r27 C1 («jamás los pm de chunks») que este atajo era el último en
    incumplir. Es además la única de las tres fuentes de marcas del bot cuyos
    nombres están limpios: `vendido_bajo` trae cinco grafías de Morley y un
    `unknown`, y publicarlas sin normalizar se ve como un descuido.

    `por_producto` sólo cambia el encabezado: quien pregunta por productos y
    quien pregunta por marcas reciben la misma lista, pero el texto reconoce lo
    que preguntó cada uno en vez de contestar de lado.

    Fail-open igual que el resto del atajo: si la base no responde, se degrada al
    texto estático de siempre en vez de dejar al técnico sin nada.
    """
    try:
        marcas = get_manufacturers_by_docs()
    except Exception as exc:                                     # noqa: BLE001
        logger.warning("lista de fabricantes fail-open (%s)", type(exc).__name__)
        marcas = []
    if not marcas:
        linea, _ = _FABRICANTES_FALLBACK
        return (f"Tengo documentación de {linea}.\n\n"
                "Dime una marca y te enseño lo que tengo de ella.")

    if por_producto:
        encabezado = (f"Tengo manuales de *{len(marcas)} fabricantes*. Son "
                      f"demasiados productos para listarlos aquí, así que te "
                      f"paso las marcas:")
    else:
        encabezado = f"Tengo documentación de *{len(marcas)} fabricantes*:"

    elementos = [f"• {_pm_plano(nombre)} ({n})" for nombre, n in marcas]
    resultado = acotar(
        elementos,
        presupuesto=_PRESUPUESTO_MSG,
        encabezado=encabezado,
        coletilla=("Entre paréntesis, cuántos manuales tengo de cada una.\n"
                   "Dime una marca —o pregúntame directamente por un modelo— y "
                   "te doy el detalle."),
        plural="fabricantes",
    )
    return resultado.texto


async def _responder_atajo(update: Update, respuesta: str, *, user_id: int,
                           query: str, registrar: bool,
                           procedencia: Procedencia) -> None:
    """Envía la respuesta de un atajo REGISTRÁNDOLA ANTES, y con sus botones.

    (s324f, hallazgo del dúo r39) El orden es el arreglo. Hasta hoy los atajos
    enviaban primero y registraban después, y encima sin `response`: colgar el
    teclado de 👍/👎 sobre eso habría creado botones apuntando a una fila que
    todavía no existía —o que falló al escribirse—, que es justo la FK colgante
    contra la que avisa `log_query` en su propia documentación. Se copia el
    patrón de la ruta RAG: generar el id, registrar, y sólo si la fila está
    CONFIRMADA colgar los botones. Si el registro falla se responde igual, sin
    botones: perder la señal de un 👎 es barato, una referencia rota no.

    Y se guarda `response`. Sin eso, un 👎 sobre un atajo señalaba una respuesta
    que no estaba escrita en ninguna parte: no se podía diagnosticar lo que el
    técnico había visto.
    """
    marcado = None
    if registrar:
        query_log_uuid = str(uuid.uuid4())
        registrada = log_query(
            telegram_user_id=user_id, query=query, route="catalog_shortcut",
            source=procedencia.source, transcription=procedencia.transcription,
            response=respuesta, response_length=len(respuesta),
            query_log_id=query_log_uuid,
        )
        asegurar_seudonimo(user_id)
        if _feedback_keyboard_enabled() and registrada:
            marcado = _feedback_keyboard(query_log_uuid)
    try:
        await update.message.reply_text(respuesta, parse_mode="Markdown",
                                        reply_markup=marcado)
    except Exception:                                            # noqa: BLE001
        # Mismo cinturón que `_handle_catalog`: un metacarácter suelto en un
        # nombre de marca rompe Markdown v1 y el técnico se queda sin respuesta.
        await update.message.reply_text(
            respuesta.replace("*", "").replace("_", ""), reply_markup=marcado)


async def _handle_catalog(update: Update):
    """Respond to catalog questions with full product list from DB.

    (s324f) YA NO LO USA NINGUNA RUTA: «¿qué productos tienes?» y «¿qué
    fabricantes tienes?» pasan por `_texto_fabricantes`. Se conserva porque
    `get_all_models_by_category` sigue siendo la única vista por categoría y
    algún consumidor futuro podría quererla — pero **con su defecto declarado**:
    pide `limit=5000` y PostgREST devuelve 1000 sin orden, así que enseña el
    3,8 % de los chunks; y `r.get("category", "General")` no cubre `None`, que
    es el 63 % de las filas que recibe. Servía 22 modelos de 756. Si vuelve a
    usarse, hay que paginar y arreglar el `None` primero.
    """
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


async def _s331_presence_refresh_job(_context) -> None:
    """(s331) Tick del refresher de presencia: single-flight y fuera del event loop
    (to_thread) — el job NUNCA bloquea el bot; un fallo queda en el log y el set
    previo sigue sirviendo (stale ⇒ drops off, fail-open declarado)."""
    import asyncio

    from ..rag.catalog_resolver import refresh_presence
    try:
        await asyncio.to_thread(refresh_presence)
    except Exception:                                    # noqa: BLE001
        logger.warning("s331: tick de refresh de presencia falló (fail-open)")


def _con_sufijo_asunciones(answer: str, f1_resolution) -> str:
    """(s332 §2, B5) Sufijo determinista que declara las asunciones de la
    resolución F1 en el answer SERVIDO. La cita de la pregunta base sale de
    `state_query_override` a propósito: si el rebuild partió de una `last_query`
    rancia (R8), el técnico LO VE y corrige — la visibilidad es el control.
    Con el flag off la rama no emite asunciones y esto es identidad."""
    for asuncion in getattr(f1_resolution, "asunciones", ()) or ():
        if asuncion.kind == "marca_fuzzy":
            # (s334 §2) El disclosure ES la condición de existencia del fuzzy:
            # aquí `detectado` (lo que llegó) SÍ es visible para el técnico —
            # la frontera de privacidad aplica al TRACE, no al mensaje.
            answer += (
                f"\n\nℹ️ Entiendo que te refieres a {asuncion.asumido} "
                f"(llegó «{asuncion.detectado}»). Si no es así, dímelo."
            )
        if asuncion.kind == "marca_corregida":
            base = f1_resolution.state_query_override
            cita = f" («{base}»)" if base else ""
            answer += (
                f"\n\nℹ️ Respondo a tu pregunta anterior{cita} entendiendo "
                f"que la marca es {asuncion.asumido}."
            )
    return answer


def _asunciones_obs(f1_resolution, asunciones_asr) -> dict:
    """(s332 B6) Vista DERIVADA de las asunciones del turno para telemetría —
    kind/modo/asumido por ítem (`asumido` = término gobernado); `detectado` JAMÁS
    (es contenido de usuario/ASR — la misma frontera de privacidad que la mención
    en `_turn_identity_obs`). `status` off = ambos levers s332 apagados; el
    tri-estado `not_wired` lo produce el builder cuando este obs no llega."""
    from ..orchestrator.conversation_policy_impl import correction_enabled
    from .whisper_vocabulary import asr_avisos_on

    if not (asr_avisos_on() or correction_enabled()):
        return {"status": "off"}
    items = list(asunciones_asr or ())
    if f1_resolution is not None:
        items.extend(getattr(f1_resolution, "asunciones", ()) or ())
    return {"status": "on", "items": [
        {"kind": a.kind, "modo": a.modo, "asumido": a.asumido} for a in items]}


def _turn_identity_obs(turn_identity) -> dict:
    """(s331 B5) Vista DERIVADA de la identidad del turno para telemetría — enums y
    booleanos, JAMÁS el string de la mención (frontera de privacidad del trace).
    `status`: 'off' = levers s331 apagados · 'on' = canal activo (con o sin evento).
    El tri-estado 'not_wired' lo produce el BUILDER cuando este obs no llega."""
    from ..orchestrator.conversation_policy_impl import mention_precedence_enabled
    from ..rag.catalog_resolver import presence_estado, turn_resolve_enabled

    if not (turn_resolve_enabled() or mention_precedence_enabled()):
        return {"status": "off"}
    obs: dict = {"status": "on", "presence": presence_estado()}
    ti = turn_identity
    if ti is not None:
        obs.update(
            models_provenance=getattr(ti, "models_provenance", "none"),
            mention_provenance=getattr(ti, "mention_provenance", "none"),
            route_cut=bool(getattr(ti, "route_cut", False)),
        )
    return obs


async def _process_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str,
    *,
    source: str,
    transcription: str | None = None,
    preambulo: Preambulo | None = None,
    asunciones_asr: tuple = (),
):
    """Core RAG pipeline — shared between text and voice handlers.

    (s324e) `preambulo` = la corrección que el PLAN decidió anteponer (DEC-224 §B).
    Default None ⇒ voz y el resto de callers, byte-idénticos. La voz NO pasa por
    `plan_turn` y por eso nunca lo trae: declarado, no olvidado."""
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
                        query=query, source=source, transcription=transcription,
                        route="clarify",
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
        # (s333 B3) telemetría del clasificador de corrección — mismo contrato
        # que `intent_obs`: "off" explícito cuando F1 no corre; el seam lo
        # sobreescribe si corre. Sin estampar ⇒ el builder degrada a not_wired.
        correccion_obs: dict = {"status": "off", "decision": "none", "latency_ms": 0}
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
            # (s324e) El modelo lo resolvió el PLAN; sin pasarlo, F1 re-detecta y el
            # modelo servido podría no ser el del preámbulo.
            _modelo_plan = preambulo.modelo if preambulo is not None else None
            _intent_fn = _intent_seam(intent_obs)
            _correccion_fn = _correccion_seam(correccion_obs)
            # (s333 B3, Sol-1 CRÍTICO de la ronda) `to_thread` con CUALQUIER seam
            # LLM activo — antes solo con `_intent_fn`, y F1_CORRECCION_LLM=on con
            # INTENT_LLM=off habría ejecutado hasta 6 s síncronos EN el event loop.
            if _intent_fn is not None or _correccion_fn is not None:
                f1_resolution, f1_new_state = await asyncio.to_thread(
                    resolve_conversational_turn,
                    query, f1_prev_state, f1_now,
                    rewrite=_lazy_rewrite, intent=_intent_fn,
                    correccion=_correccion_fn,
                    resolved_model=_modelo_plan,
                )
                if intent_obs.get("status") == "invoked":
                    # decisión → log operacional; la traza PERSISTIDA es la
                    # sección `intent` de rag_trace (gate 1 del flip, s316h).
                    logger.info("intent_llm: %s en %d ms",
                                intent_obs["decision"], intent_obs["latency_ms"])
                if correccion_obs.get("status") == "invoked":
                    logger.info("correccion_llm: %s en %d ms",
                                correccion_obs["decision"],
                                correccion_obs["latency_ms"])
            else:
                f1_resolution, f1_new_state = resolve_conversational_turn(
                    query, f1_prev_state, f1_now, rewrite=_lazy_rewrite,
                    resolved_model=_modelo_plan,
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
                _direct_route = ("clarify"
                                 if f1_resolution.route is PolicyRoute.CLARIFY
                                 else "decline")
                # (s331 B9/Sol-1 r-v4) Trace mínimo direct/1: sin él, route_cut sería
                # inobservable justo en la ruta donde ocurre. Con levers OFF el obs
                # devuelve status='off' y NO se adjunta nada — filas byte-idénticas
                # a hoy. La telemetría jamás rompe la respuesta (fail-open).
                _direct_trace = None
                try:
                    _dt_obs = _turn_identity_obs(f1_resolution.turn_identity)
                    if _dt_obs.get("status") == "on":
                        from ..rag.runtime_trace import build_direct_route_trace
                        _direct_trace = build_direct_route_trace(
                            _direct_route, _dt_obs)
                except Exception:                       # noqa: BLE001
                    _direct_trace = None
                # s301 (dúo): CLARIFY/DECLINE de F1 también son respuestas a consultas
                # — sin log, «quién usa el bot y cuánto» tenía un agujero por aquí.
                _clarify_logged = log_query(
                    telegram_user_id=(update.effective_user.id
                                      if update.effective_user else 0),
                    query=query, source=source, transcription=transcription,
                    route=_direct_route,
                    response=direct_reply, response_length=len(direct_reply),
                    rag_trace=_direct_trace,
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
                # (s331 §3.D) La identidad la resolvió la política; aquí solo se
                # COPIA al request. Con los levers de s331 apagados vale None y
                # el request queda byte-idéntico. El régimen sin F1 (`else`) no
                # tiene resolución, así que ni siquiera pasa el kwarg.
                turn_identity=f1_resolution.turn_identity,
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

        # (s324e — DEC-224 §B) Corrección y respuesta son UNA sola respuesta: se componen
        # AQUÍ para que `query_logs.response` y `last_response` guarden exactamente lo que
        # vio el técnico (y el 👎 posterior, anclado a esa fila, lo conserve). Después del
        # fallback: una respuesta vacía sigue llevando su corrección.
        if preambulo is not None:
            answer = f"{_turn_plan.texto_preambulo(preambulo)}\n\n{answer}"

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

        # (s332 §2, B5) Las asunciones de la resolución F1 se DECLARAN como sufijo
        # del answer servido — determinista, byte-nivel, tras el excerpt de estado
        # (la nota es meta-conducta, no contenido para la anáfora del rewriter).
        if f1_active and f1_resolution is not None:
            answer = _con_sufijo_asunciones(answer, f1_resolution)

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
                # (s333 B4) espejo de `intent`: gate del flip de F1_CORRECCION_LLM.
                correccion_obs=correccion_obs,
                # (s331 B5) tri-estado: el builder degrada a not_wired si esto
                # faltara; off = levers apagados; on = canal activo este turno.
                turn_identity_obs=_turn_identity_obs(
                    f1_resolution.turn_identity if f1_active else None),
                # (s332 B6) mismo tri-estado que turn_identity: gate del flip.
                asunciones_obs=_asunciones_obs(
                    f1_resolution if f1_active else None, asunciones_asr),
                mismatch_obs=(
                    {"modelo": preambulo.modelo,
                     "marca_real": preambulo.marca_real,
                     "marca_mencionada": preambulo.marca_mencionada}
                    if preambulo is not None else None),
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

        # 4) (s324f) Avisar a QUIEN PUEDE ARREGLARLO. Nace de un fallo real: la
        #    primera usuaria del piloto se topó con la cuenta de OpenAI sin
        #    saldo, y el único camino por el que eso llegó a Alberto fue que ella
        #    se lo contara. Un fallo crítico —credenciales, cuota, canal roto—
        #    no es información para el técnico, que no puede hacer nada: es
        #    información para el operador.
        #    Sólo `critico`: los avisos y los fallos graves ya se ven en el
        #    informe de incidencias, y mandar un Telegram por cada timeout
        #    convertiría el aviso en ruido que se ignora.
        if incidencia.severidad == "critico":
            await _avisar_al_operador(context, incidencia)
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


def schedule_clasificacion(app, *, interval=6 * 3600, first=600, cap=200):
    """Register the s326 question-classifier sweep on PTB's JobQueue — gated by
    CLASIFICADOR_PREGUNTAS (default OFF: returns ``[]`` and schedules nothing).

    FUERA de la ruta de respuesta a propósito (propuesta s326 §3.B): la corrida
    lee `query_logs`, clasifica pendientes (regla primero, Haiku en el residuo)
    y upserta `query_clasificacion`. Fail-open TOTAL: cualquier fallo — 021 sin
    aplicar, Supabase caído, LLM caído — se queda en un warning del log y se
    reintenta en la corrida siguiente; el bot no se entera. El backfill inicial
    y las re-taxonomizaciones se corren a mano con
    `python -m scripts.clasificar_preguntas` (mismo código, con recibo).
    """
    if not CLASIFICADOR_PREGUNTAS:
        return []
    if app.job_queue is None:
        # PTB sin el extra [job-queue] (apscheduler): requirements.txt lo trae
        # SIN extra a propósito (nada del producto lo usaba). Encender el flag
        # sin el extra NO puede tumbar el arranque: se degrada VISIBLE al modo
        # manual (scripts/clasificar_preguntas.py) y lo dice en el log.
        logger.warning(
            "CLASIFICADOR_PREGUNTAS=on pero PTB no trae JobQueue "
            "(pip install 'python-telegram-bot[job-queue]') — corrida "
            "automática NO programada; el backfill manual sigue disponible")
        return []

    async def _clasificar(_context):
        from ..clasificacion import Catalogo, correr_pendientes

        def _corrida():
            # El catálogo se construye AQUÍ (bot sí importa rag; el módulo de
            # clasificación es raíz y lo recibe inyectado) y en cada corrida,
            # para que un fabricante ingestado ayer cuente hoy.
            catalogo = Catalogo(
                nombres=[n for n, _d in get_manufacturers_by_docs()],
                marca_de_modelo=classify_model_manufacturer,
                resolver_alias=resolve_manufacturer_alias,
            )
            return correr_pendientes(cap, catalogo=catalogo,
                                     api_key=ANTHROPIC_API_KEY)

        try:
            recibo = await asyncio.to_thread(_corrida)
            logger.info("clasificacion_preguntas: %s", recibo)
        except Exception:                                    # noqa: BLE001
            logger.warning("clasificacion_preguntas falló open", exc_info=True)

    return [
        app.job_queue.run_repeating(
            _clasificar, interval=interval, first=first,
            name="clasificacion_preguntas",
        )
    ]


def run_bot():
    """Start the Telegram bot."""
    validate_config(require_telegram=True)

    # (s91 F2-S1, dúo #3) fail-fast del flag de identidad EN ARRANQUE: un misconfig en Railway
    # (flag legacy ON junto a IDENTITY_RESOLVE, o typo en el valor) debe tumbar el deploy
    # visible, no fallar el 100% de queries en runtime.
    from src.rag import catalog_resolver as _resolver
    _resolver.mode()

    # s324e (dúo, crítico 1) — mismo fail-fast que el flag de identidad, y por
    # el mismo motivo: una errata en Railway (`BOT_ALLOWLIST=onn`, un id de
    # bootstrap con un carácter de más) debe tumbar el deploy VISIBLE, no
    # descubrirse porque un DG no puede entrar. La puerta, además, ya no se
    # apaga con un valor que no se entienda — solo con un «off» reconocible.
    access.validar_configuracion()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # (fase B) La guardia de grupo -1 se retiro: la invalidacion de #70 vive en el
    # plan de turno (handle_message/handle_voice), no en un TypeHandler previo.

    # s324e — LA PUERTA, en el grupo -1: PTB evalúa los grupos de menor a mayor
    # (`add_handler` los mantiene ordenados) y un `ApplicationHandlerStop` desde
    # aquí detiene el update para todos los demás. Se registra ANTES que nada
    # para que leer esta función deje claro qué es lo primero que corre; el
    # orden efectivo lo fija el número de grupo, no la línea. Inerte con
    # `BOT_ALLOWLIST=off` (default), que es la conducta de hoy.
    # NINGÚN otro handler puede ir en un grupo < -1: eso lo pondría por delante
    # de la puerta. Lo vigila `test_s324e_allowlist.py::test_la_puerta_va_primero`.
    app.add_handler(TypeHandler(Update, access_gate), group=-1)

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

    # Estado de la puerta, VISIBLE en el arranque: si el piloto corre abierto
    # tiene que constar en los logs de Railway, no descubrirse preguntando.
    if access.acceso_activo():
        logger.info(
            "puerta de acceso ACTIVA: allowlist + invitacion (bootstrap=%d ids, "
            "tope diario=%d)", len(access.ids_bootstrap()), access.limite_diario(),
        )
    else:
        logger.warning(
            "puerta de acceso APAGADA (BOT_ALLOWLIST=off): cualquiera que acepte "
            "los terminos puede usar el bot"
        )

    # s326: la corrida periódica del clasificador de preguntas. Inerte con
    # CLASIFICADOR_PREGUNTAS=off (default); encendida, clasifica en background
    # cada 6 h con fail-open total — jamás toca la ruta de respuesta.
    schedule_clasificacion(app)

    logger.info("Bot started. Listening for text and voice messages...")
    # s307: calienta la caché de fabricantes ANTES del polling — el primer saludo
    # no paga la llamada REST; si falla, el saludo usa el fallback y reintenta.
    try:
        _fabricantes_resumen()
    except Exception:                                    # noqa: BLE001
        pass

    # (s331, Fable-3 r-v5) INTERLOCK de flags EN BOOT, nunca en el hot-path de un
    # turno de usuario: un lote Railway mal aplicado debe tumbar el arranque con
    # un mensaje claro, no soltar errores a técnicos hasta que alguien mire logs.
    # Los tres parsers son estrictos (typo revienta). Con todo apagado (default)
    # el bloque es un no-op y el arranque queda byte-idéntico.
    from ..orchestrator.conversation_policy_impl import mention_precedence_enabled
    from ..rag import catalog_resolver as _cr331
    from ..rag.generator import _no_reask_on
    try:
        _s331_resolve = _cr331.turn_resolve_enabled()
        mention_precedence_enabled()
        _no_reask_on()
    except RuntimeError as exc:
        raise SystemExit(f"s331 interlock de boot: {exc}") from None
    if _s331_resolve:
        # Warm de presencia ANTES del polling (el path de turno no toca red: peek)
        # + refresher SINGLE-FLIGHT a 0,8×TTL (900s → 720s) en el job queue.
        estado = _cr331.refresh_presence()
        logger.info("s331: presencia calentada en boot (%s)", estado)
        if app.job_queue is not None:
            app.job_queue.run_repeating(
                _s331_presence_refresh_job, interval=720, first=720,
                name="s331_presence_refresh",
            )
        else:                                            # pragma: no cover
            logger.warning("s331: job_queue ausente — la presencia refrescará "
                           "solo vía retrieval (stale ⇒ drops off, declarado)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
