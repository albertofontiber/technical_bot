"""
Telegram bot for PCI technicians.
Receives questions, queries the RAG pipeline, and returns formatted answers with diagrams.
"""

import asyncio
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
    RETRIEVAL_TOP_K,
    RERANK_TOP_K,
    LLM_MODEL,
    REWRITER_MODEL,
    VOICE_TRANSCRIPTION_MODEL,
    COVERAGE_RELEASE_POLICY,
    ORCHESTRATOR_PATH,
    CONVO_SHADOW,
    CONVO_MAINTENANCE,
    validate_config,
)
from ..rag.retriever import (
    retrieve_chunks, extract_product_models, get_category_models,
    get_manufacturers_by_docs, get_products_by_manufacturer,
    _MANUFACTURER_ALIASES, resolve_manufacturer_alias,
    get_all_models_by_category, CATEGORY_TERMS, PCI_TERMS,
    lookup_model_manufacturer, get_available_manufacturers, manufacturer_in_db,
)
from ..rag.reranker import rerank
from ..rag.generator import generate_answer
from ..rag.runtime_trace import build_rag_serving_trace
from ..rag.serving_pipeline import RagServingAdapters, execute_rag_turn
from ..rag.structural_neighbor_shadow import observe_structural_neighbor_shadow
from ..logging_db import (
    log_query,
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

# --- Pre-pipeline classifiers ---

# Greetings / non-technical messages (skip RAG entirely)
_GREETING_PATTERNS = re.compile(
    r"^(hola|hey|buenas|buenos\s*días|buenas\s*tardes|buenas\s*noches|"
    r"saludos|qué\s*tal|que\s*tal|hi|hello)[\s!.,?]*$",
    re.IGNORECASE,
)
_THANKS_PATTERNS = re.compile(
    r"^(gracias|muchas\s*gracias|genial|perfecto|ok|vale|entendido|"
    r"de\s*acuerdo|recibido|thanks|thank\s*you)[\s!.,?]*$",
    re.IGNORECASE,
)
_BYE_PATTERNS = re.compile(
    r"^(adiós|adios|hasta\s*luego|chao|nos\s*vemos|bye)[\s!.,?]*$",
    re.IGNORECASE,
)

# Catalog questions (answer with DB query, not RAG).
# Includes "fabricantes" / "marcas" / "empresas" so queries like "¿qué
# fabricantes tienes?" hit the catalog shortcut instead of leaking through
# the RAG pipeline (sesión 21 smoke step 6: query produced a confusing
# first sentence saying "solo Notifier" before listing the 3 manufacturers).
_CATALOG_PATTERNS = re.compile(
    r"(qué\s+(productos?|modelos?|equipos?|detectores?|centrales?|fabricantes?|marcas?|empresas?)\s+(tienes|hay|tenéis|tienen|soporta)|"
    r"(listado|catálogo|catalogo|lista)\s+de\s+(productos?|modelos?|equipos?|fabricantes?|marcas?)|"
    r"para\s+qué\s+(productos?|modelos?|equipos?|fabricantes?|marcas?)\s+tienes\s+información|"
    r"qué\s+información\s+tienes|"
    r"qué\s+tienes)",
    re.IGNORECASE,
)

# Known manufacturer names (for detection in queries — NOT for blocking)
# (s307) Intención de INVENTARIO sobre un fabricante — 2º fallo orgánico: «¿qué
# productos de Securiton tienes?» no casaba con _CATALOG_PATTERNS (exige «productos»
# y «tienes» ADYACENTES) y caía al RAG, que enumeró una MUESTRA de 10 chunks como si
# fuera el inventario (faltaron ASD531 y ASD535).
#
# v2 tras el dúo (H2: la v1 era ANCHA y desviaba consultas técnicas al listado —
# «lista de averías/eventos» es vocabulario NUCLEAR de la UI de centrales PCI, y
# «¿qué centrales Notifier tienen salida de relé?» es un filtro de specs, no un
# inventario). Dos discriminadores, ambos empíricos:
#   1. el verbo de posesión va AL FINAL — una pregunta de inventario TERMINA en el
#      verbo («…tienes?»); una de specs continúa tras él («…tienen salida de relé»);
#   2. la palabra-de-lista solo cuenta pegada a un sustantivo DE INVENTARIO
#      («listado de productos» sí; «lista de averías» no) — o al nombre del
#      fabricante, que se comprueba aparte porque no puede vivir en un regex.
# `gama` FUERA (colisiona con recomendaciones: «¿qué central de la gama X me
# recomiendas?»). OJO DEC-059: aquel fall-through medido es para preguntas DE
# MODELO; esta ruta cubre INVENTARIO, población que DEC-059 no midió — el
# fall-through de modelo queda INTACTO.
_ENUM_FABRICANTE = re.compile(
    r"(qu[eé]|cu[aá]l(?:es)?)\s+(productos?|modelos?|equipos?|centrales?|detectores?|"
    r"manuales?|documentaci[oó]n|informaci[oó]n)[^?]{0,40}"
    r"\b(tienes|ten[eé]is|tienen|hay|dispones?|dispon[eé]is|disponen|"
    r"soportas?|cubres?|conoces)\s*\??\s*$"
    r"|\b(listado|lista|cat[aá]logo|inventario)\s+de\s+"
    r"(productos?|modelos?|equipos?|detectores?|centrales?|manuales?|documentaci[oó]n)\b"
    # EN mínimo (Sol s307: el corpus y los técnicos son ES/EN; una consulta EN caía a
    # RAG = status quo, pero cubrirla es barato con los MISMOS discriminadores). El
    # orden inglés mete la MARCA entre medias («what Securiton products» · «list of
    # Notifier panels») → se toleran 1-2 palabras antes del sustantivo:
    r"|(what|which)\s+(?:[\w-]+\s+){0,2}(products?|models?|equipment|panels?|detectors?)"
    r"[^?]{0,40}\b(do\s+you\s+(have|know|support|cover)|are\s+(there|available))\s*\??\s*$"
    r"|\b(list|catalog(?:ue)?|inventory)\s+of\s+(?:[\w-]+\s+){0,2}"
    r"(products?|models?|equipment|detectors?|panels?)\b",
    re.IGNORECASE,
)


# Pre-gate barato del paso 5-bis: solo si hay señal de inventario se paga la
# resolución de marca contra la DB. Cualquier término dispara el CHEQUEO, no la ruta.
_PREGATE_INVENTARIO = re.compile(
    r"\b(productos?|modelos?|equipos?|centrales?|detectores?|manuales?|"
    r"documentaci[oó]n|informaci[oó]n|listado|lista|cat[aá]logo|inventario|"
    r"products?|models?|equipment|panels?|detectors?|list|catalog|inventory)\b",
    re.IGNORECASE,
)


def _intencion_inventario(query: str, marca: str | None = None) -> bool:
    """¿La consulta pide el INVENTARIO? Regex estático + la variante con el nombre
    del fabricante («catálogo de securiton»), que no puede pre-compilarse."""
    if _ENUM_FABRICANTE.search(query):
        return True
    if marca:
        return bool(re.search(
            rf"\b(listado|lista|cat[aá]logo|inventario)\s+(de\s+)?{re.escape(marca)}\b",
            query, re.IGNORECASE,
        ))
    return False

_MANUFACTURER_NAMES = re.compile(
    r"\b(notifier|honeywell|siemens|bosch|esser|kilsen|cerberus|"
    r"tyco|johnson\s*controls|simplex|edwards|kidde|hochiki|"
    r"apollo|nittan|morley|ziton|argus|fenwal|minimax|"
    r"system\s*sensor|gamewell|vigilant|autronica|schrack|"
    r"detnov|securiton|pfannenberg|spectrex|lda)\b",
    re.IGNORECASE,
)

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


def _feedback_keyboard(query_log_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍", callback_data=f"fb:u:{query_log_id}"),
        InlineKeyboardButton("👎", callback_data=f"fb:d:{query_log_id}"),
    ]])


# Feedback detection
_FEEDBACK_PATTERNS = re.compile(
    r"(no\s+es\s+correcto|incorrecto|está\s+mal|esta\s+mal|"
    r"eso\s+no\s+es|el\s+manual\s+dice\s+otra\s+cosa|"
    r"error\s+en\s+la\s+respuesta|dato\s+erróneo|dato\s+erroneo|"
    r"respuesta\s+incorrecta|información\s+incorrecta|informacion\s+incorrecta)",
    re.IGNORECASE,
)


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


def _inventario_fabricante(nombre: str) -> str | None:
    """Respuesta de inventario para un fabricante, o None para caer al RAG.

    Del corpus, no de una ventana de retrieval; ACOTADA a `_PRESUPUESTO_MSG` por
    construcción (las que no caben se resumen en «…y N más»); «referencias» y no
    «modelos» (varias marcas taguean a FAMILIA — deliberado, T3/s285). Éxito
    cacheado por proceso; fallo NO cacheado pero con backoff (60 s) y → RAG.
    """
    global _inventario_falla_ts
    nombre = resolve_manufacturer_alias(nombre)   # s308/#67: «lda» → LDA audioTech
    clave = nombre.strip().lower()
    if clave in _inventario_cache:
        return _inventario_cache[clave]
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


def _marca_en_consulta(query: str) -> str | None:
    """Nombre REAL (de la DB) de un fabricante mencionado en la consulta.

    Cubre las marcas FUERA del regex hardcodeado `_MANUFACTURER_NAMES` (dúo s307/F2:
    «¿qué productos de Xtralis tienes?» reproducía el fallo Securiton literal — el fix
    dependía de la misma constante que diagnosticaba). Matching conservador: nombre
    completo con frontera de palabra, o su primera palabra si es ÚNICA entre las marcas
    y ≥4 chars («argus» → Argus Security). Los nombres demasiado cortos para eso
    («lda») se resuelven por la tabla de ALIAS curados (s308, cierra #67).
    """
    global _marcas_db_cache
    # (s308/#67) Alias curados primero. HONESTIDAD de alcance (sub-agente s308):
    # para lda/argus este bucle es HOY inalcanzable en serving — ambos están en
    # _MANUFACTURER_NAMES y el paso 5 los captura antes (donde el alias resuelve
    # vía manufacturer_in_db + inventario). Se conserva para alias FUTUROS de
    # marcas fuera del regex; el camino load-bearing está testeado aparte.
    for alias, real in _MANUFACTURER_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", query, re.IGNORECASE):
            return real
    if _marcas_db_cache is None:
        try:
            _marcas_db_cache = get_available_manufacturers()
        except Exception:                                # noqa: BLE001
            return None      # fallo NO cacheado: el siguiente intento reintenta
    primeras: dict[str, list[str]] = {}
    for nombre in _marcas_db_cache:
        primeras.setdefault(nombre.split()[0].lower(), []).append(nombre)
    for nombre in _marcas_db_cache:
        if re.search(rf"\b{re.escape(nombre)}\b", query, re.IGNORECASE):
            return nombre
        primera = nombre.split()[0]
        if (len(primera) >= 4 and len(primeras[primera.lower()]) == 1
                and re.search(rf"\b{re.escape(primera)}\b", query, re.IGNORECASE)):
            return nombre
    return None


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
        confirmation = f"🎤 {raw_transcription}"
        if normalization.changed:
            recognized = list(
                dict.fromkeys(item.canonical for item in normalization.substitutions)
            )
            confirmation += f"\n🔎 Modelo interpretado: {', '.join(recognized)}"
        # Plain text avoids Telegram Markdown parse failures on arbitrary ASR.
        await update.message.reply_text(confirmation)

        # Process the normalized query while preserving raw ASR for audits.
        await _process_query(
            update,
            context,
            query,
            source="voice",
            transcription=raw_transcription,
        )

    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await update.message.reply_text(
            "Ha ocurrido un error procesando el audio. ¿Puedes escribir tu pregunta?"
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

    # --- Pre-pipeline classification (saves API calls) ---

    # s301 (#31): los shortcuts de CONSULTA loggean antes de retornar — sin esto, las
    # métricas de uso por canal eran ciegas («¿qué fabricantes tienes?» no existía en
    # query_logs). La CORTESÍA (saludo/gracias/adiós) NO se loggea, a conciencia: el
    # aviso v7 promete literalmente «Los saludos y las despedidas no se registran» y la
    # ponderación de interés legítimo usa esa minimización como argumento (§3 del LIA).
    # Cazado por el dúo s301: loggearla habría ampliado el tratamiento contra el
    # contrato aceptado. Los valores greeting/thanks/bye del CHECK quedan RESERVADOS
    # para un aviso futuro que lo cambie; hoy ningún camino los emite.

    # 1. Greetings (SIN log: promesa del aviso)
    if _GREETING_PATTERNS.match(query):
        await update.message.reply_text(
            "¡Hola! 👋 Soy el asistente técnico PCI.\n\n"
            "Pregúntame lo que necesites sobre instalación, conexionado, "
            f"especificaciones o resolución de problemas de equipos de {_fabricantes_resumen()[0]}.\n\n"
            "También puedes enviarme un audio 🎤",
            parse_mode="Markdown",
        )
        return

    # 2. Thanks (SIN log: promesa del aviso)
    if _THANKS_PATTERNS.match(query):
        await update.message.reply_text(
            "De nada 👍 ¿Necesitas algo más?"
        )
        return

    # 3. Bye (SIN log: promesa del aviso)
    if _BYE_PATTERNS.match(query):
        await update.message.reply_text(
            "¡Hasta luego! Aquí estaré cuando lo necesites. 🔧"
        )
        return

    # 4. Catalog questions (consulta de contenido: SÍ se loggea, como toda consulta)
    if _CATALOG_PATTERNS.search(query):
        await update.message.chat.send_action("typing")
        await _handle_catalog(update)
        # La respuesta vive dentro del handler (catálogo dinámico); para la métrica de
        # canal basta la consulta y la ruta — no se duplica el texto aquí.
        log_query(telegram_user_id=user_id, query=query, route="catalog_shortcut")
        asegurar_seudonimo(user_id)
        return

    # 5. Smart manufacturer detection (dynamic — queries Supabase)
    manufacturer_match = _MANUFACTURER_NAMES.search(query)
    if manufacturer_match:
        mentioned_manufacturer = manufacturer_match.group(0)
        models_in_query = extract_product_models(query)

        if models_in_query:
            # User mentioned a model + a manufacturer — check if the model exists
            model = models_in_query[0]
            actual_manufacturer = lookup_model_manufacturer(model)

            if actual_manufacturer:
                # (dúo s308) comparar contra el alias RESUELTO: sin esto, una
                # consulta modelo+«lda» respondería «es de LDA audioTech, no de
                # lda» — mismatch falso de la misma marca.
                _mencionado_real = resolve_manufacturer_alias(mentioned_manufacturer)
                if actual_manufacturer.lower() != _mencionado_real.lower():
                    # Model exists but under a different manufacturer
                    respuesta = (
                        f"El *{model}* es un producto de *{actual_manufacturer}*, "
                        f"no de _{mentioned_manufacturer}_.\n\n"
                        f"¿Te refieres al *{model}* de *{actual_manufacturer}*? "
                        f"Si es así, dime tu pregunta y te ayudo."
                    )
                    await update.message.reply_text(respuesta, parse_mode="Markdown")
                    log_query(telegram_user_id=user_id, query=query,
                              route="manufacturer_mismatch",
                              response=respuesta, response_length=len(respuesta))
                    asegurar_seudonimo(user_id)
                    return
                # else: correct manufacturer + model → fall through to RAG
            else:
                # Model not in the product_model index. That index is KNOWN to be
                # desynced from the corpus (TECH_DEBT #49: marketing FAMILY vs stored
                # VARIANT — CAD-150 vs CAD-150-8, ZXe vs ZX2e/ZX5e, 40/40 vs 40-40L/M).
                # So None here does NOT mean "we lack this product". If we HAVE the
                # mentioned manufacturer's manuals, fall through to RAG and let
                # retrieval + the generator's conduct rules resolve it; hard-refuse
                # only when the manufacturer itself is absent. (s77/DEC-059 — measured
                # judge-free: scripts/s77_fallthrough_measure.py + s77_regression_probes.py
                # → fall-through gives correct-mfr answer / refuse-inference / clarify,
                # never cross-brand hallucination; absent or near-miss model under a
                # known brand still admits no-info. The model-index is an unreliable
                # oracle for availability; retrieval+generator see the real content.)
                if not manufacturer_in_db(mentioned_manufacturer):
                    available = get_available_manufacturers()
                    manufacturers_str = ", ".join(f"*{m}*" for m in available)
                    respuesta = (
                        f"No dispongo de manuales de _{mentioned_manufacturer}_.\n\n"
                        f"Tengo información de: {manufacturers_str}.\n"
                        f"¿Puedo ayudarte con alguno de estos?"
                    )
                    await update.message.reply_text(respuesta, parse_mode="Markdown")
                    log_query(telegram_user_id=user_id, query=query,
                              route="manufacturer_no_model",
                              response=respuesta, response_length=len(respuesta))
                    asegurar_seudonimo(user_id)
                    return
                # else: manufacturer IS in DB → fall through to RAG (model index desynced)
        else:
            # No model code, just a manufacturer name mentioned
            if not manufacturer_in_db(mentioned_manufacturer):
                # Manufacturer not in DB
                available = get_available_manufacturers()
                manufacturers_str = ", ".join(f"*{m}*" for m in available)
                respuesta = (
                    f"No dispongo de manuales de _{mentioned_manufacturer}_.\n\n"
                    f"Tengo información de: {manufacturers_str}.\n"
                    f"¿Puedo ayudarte con alguno de estos?"
                )
                await update.message.reply_text(respuesta, parse_mode="Markdown")
                log_query(telegram_user_id=user_id, query=query,
                          route="manufacturer_no_model",
                          response=respuesta, response_length=len(respuesta))
                asegurar_seudonimo(user_id)
                return
            if _intencion_inventario(query, mentioned_manufacturer):
                # (s307) Pregunta de INVENTARIO sobre un fabricante que SÍ tenemos:
                # se responde desde el inventario real (chunks curados × docs activos),
                # completo por construcción — no desde la ventana del RAG. Fail-open:
                # cualquier fallo cae al RAG de siempre, nunca a una respuesta peor.
                respuesta = _inventario_fabricante(mentioned_manufacturer)
                if respuesta is not None:
                    await update.message.reply_text(respuesta, parse_mode="Markdown")
                    log_query(telegram_user_id=user_id, query=query,
                              route="catalog_shortcut",
                              response=respuesta, response_length=len(respuesta))
                    asegurar_seudonimo(user_id)
                    return
            # else: manufacturer IS in DB → fall through to RAG

    # 5-bis (s307, dúo F2): inventario para marcas FUERA del regex hardcodeado de
    # arriba — «¿qué productos de Xtralis tienes?» reproducía el fallo Securiton
    # literal porque el fix dependía de la MISMA constante que diagnosticaba. El
    # nombre se resuelve contra la lista REAL de la DB (cacheada); el pre-gate
    # barato evita pagar la resolución en cada consulta normal.
    if not manufacturer_match and _PREGATE_INVENTARIO.search(query) \
            and not extract_product_models(query):
        marca_db = _marca_en_consulta(query)
        if marca_db and _intencion_inventario(query, marca_db):
            respuesta = _inventario_fabricante(marca_db)
            if respuesta is not None:
                await update.message.reply_text(respuesta, parse_mode="Markdown")
                log_query(telegram_user_id=user_id, query=query,
                          route="catalog_shortcut",
                          response=respuesta, response_length=len(respuesta))
                asegurar_seudonimo(user_id)
                return

    # 6. Feedback
    if _FEEDBACK_PATTERNS.search(query):
        await _handle_feedback(update, context, query)
        return

    # --- Normal RAG pipeline ---
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

        # S281 Phase-1 (F1) activation gate — default OFF, read at RUNTIME so a
        # Railway flip / in-process A/B toggles without a restart. Requires BOTH
        # the MT-0d ORCHESTRATOR_PATH seam (import-time constant) AND
        # CONVERSATION_POLICY=impl (the runtime flag conversation_policy_active()
        # already reads). When OFF everything below is the historical single-turn
        # path; the full suite is the byte-invariance guard. The import is skipped
        # unless ORCHESTRATOR_PATH is on, so the legacy hot path pays nothing.
        f1_active = False
        if ORCHESTRATOR_PATH:
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
                last_models = context.user_data.get("last_detected_models", [])
                last_time = context.user_data.get("last_query_time", 0)
                if last_models and (_time.time() - last_time) < SESSION_TIMEOUT:
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
                context.user_data["mt_working_state"] = f1_new_state
                context.user_data["last_query"] = query
                context.user_data["last_response"] = direct_reply[:500]
                context.user_data["last_query_time"] = _time.time()
                await update.message.reply_text(direct_reply)
                # s301 (dúo): CLARIFY/DECLINE de F1 también son respuestas a consultas
                # — sin log, «quién usa el bot y cuánto» tenía un agujero por aquí.
                log_query(
                    telegram_user_id=(update.effective_user.id
                                      if update.effective_user else 0),
                    query=query, source=source,
                    route=("clarify"
                           if f1_resolution.route is PolicyRoute.CLARIFY
                           else "decline"),
                    response=direct_reply, response_length=len(direct_reply),
                )
                return

            # Retrieving route: surface the resolved models to logging + state.
            target_models = list(f1_resolution.target_models or ())

        # Transport-neutral orchestrator seam (MT-0d), default OFF. The request
        # is built only when a Phase-0 seam is active; with both flags OFF this
        # block reduces to the historical inline pipeline (the ``else`` below is
        # textually the old path — the full suite is the byte-invariance guard).
        if ORCHESTRATOR_PATH or CONVO_SHADOW:
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

        if ORCHESTRATOR_PATH:
            # Drive the turn through the orchestrator; isolate the synchronous
            # hot path in an executor so the event loop is never blocked.
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
        else:
            # One production seam shared with the deterministic release gate.  The
            # adapters are built here so existing handler tests can patch only I/O.
            pipeline = execute_rag_turn(
                query=query,
                query_for_retrieval=query_for_retrieval,
                target_models=target_models,
                available_models=available_models,
                retrieval_top_k=RETRIEVAL_TOP_K,
                rerank_top_k=RERANK_TOP_K,
                adapters=RagServingAdapters(
                    retrieve=retrieve_chunks,
                    rerank=rerank,
                    observe_structural_shadow=observe_structural_neighbor_shadow,
                    generate=generate_answer,
                ),
            )
            chunks = pipeline["chunks"]
            coverage_trace = pipeline["coverage_trace"]
            retrieval_health = pipeline.get("retrieval_health") or {}

            # Step 3: Generate answer from reranked + governed coverage chunks.
            result = pipeline["generation"]
            answer = result["answer"]
            diagrams = result["diagrams"]

        empty_answer_fallback = not _has_visible_text(answer)
        if empty_answer_fallback:
            # A provider can complete with no visible text after tool calls.
            # Never turn that upstream defect into a silent Telegram turn.
            logger.error("generator returned an empty answer")
            answer = _EMPTY_ANSWER_FALLBACK

        # Store last query/response for feedback tracking + conversation context
        context.user_data["last_query"] = query
        context.user_data["last_response"] = answer[:500]
        context.user_data["last_query_time"] = _time.time()
        if target_models:
            context.user_data["last_detected_models"] = target_models

        # S281 Phase-1 (F1) durable working-state backfill — the TODO closed. After
        # generation, re-advance from the SAME prior state + resolution, now with
        # the answer excerpt (first ~500 chars; advance_working_state truncates), so
        # the next turn's rewriter can resolve content anaphora ("ese aviso")
        # against the prior answer. IN MEMORY only (no restart durability).
        if f1_active and f1_resolution is not None:
            from ..orchestrator.conversation_policy_impl import advance_working_state

            context.user_data["mt_working_state"] = advance_working_state(
                f1_prev_state,
                f1_resolution,
                query,
                answer,
                f1_now,
                f1_new_state.available_models,
            )

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
                from ..orchestrator.shadow import (
                    maybe_shadow_persist,
                    turn_result_from_pipeline,
                )
                shadow_result = (
                    turn if ORCHESTRATOR_PATH
                    else turn_result_from_pipeline(request, pipeline)
                )
                maybe_shadow_persist(request, shadow_result)
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
        # s286 BOT_ERROR_LOGGING (default off): error rows carry an ALLOWLISTED
        # summary (exception class @ stage), never str(e) — raw exception text
        # can embed URLs that contain the bot token (same risk the httpx
        # silencing above defends against). user_id is re-extracted here: the
        # happy-path binding may not have been reached when the failure was
        # earlier in the pipeline. handle_voice/_handle_catalog swallow their
        # own exceptions and are OUT of scope for error rows (declared, s286).
        if _error_logging_enabled():
            try:
                error_user_id = update.effective_user.id if update.effective_user else 0
                log_query(
                    telegram_user_id=error_user_id,
                    query=query,
                    source="error",
                    response=f"{type(e).__name__}@process_query",
                )
            except Exception:
                logger.warning("BOT_ERROR_LOGGING failed open")
        await update.message.reply_text(
            "Ha ocurrido un error procesando tu pregunta. Por favor, inténtalo de nuevo."
        )


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

    logger.info("Bot started. Listening for text and voice messages...")
    # s307: calienta la caché de fabricantes ANTES del polling — el primer saludo
    # no paga la llamada REST; si falla, el saludo usa el fallback y reintenta.
    try:
        _fabricantes_resumen()
    except Exception:                                    # noqa: BLE001
        pass
    app.run_polling(allowed_updates=Update.ALL_TYPES)
