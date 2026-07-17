"""
Telegram bot for PCI technicians.
Receives questions, queries the RAG pipeline, and returns formatted answers with diagrams.
"""

import asyncio
import logging
import re
import tempfile
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import (
    Application,
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
    VOICE_TRANSCRIPTION_MODEL,
    validate_config,
)
from ..rag.retriever import (
    retrieve_chunks, extract_product_models, get_category_models,
    get_all_models_by_category, CATEGORY_TERMS, PCI_TERMS,
    lookup_model_manufacturer, get_available_manufacturers, manufacturer_in_db,
)
from ..rag.reranker import rerank
from ..rag.generator import generate_answer
from ..rag.post_rerank_coverage import apply_post_rerank_coverage
from ..rag.structural_neighbor_shadow import observe_structural_neighbor_shadow
from ..logging_db import log_query, log_feedback, has_consent, set_consent
from .response_formatter import (
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
_MANUFACTURER_NAMES = re.compile(
    r"\b(notifier|honeywell|siemens|bosch|esser|kilsen|cerberus|"
    r"tyco|johnson\s*controls|simplex|edwards|kidde|hochiki|"
    r"apollo|nittan|morley|ziton|argus|fenwal|minimax|"
    r"system\s*sensor|gamewell|vigilant|autronica|schrack|"
    r"detnov|securiton|pfannenberg|spectrex|lda)\b",
    re.IGNORECASE,
)

# Feedback detection
_FEEDBACK_PATTERNS = re.compile(
    r"(no\s+es\s+correcto|incorrecto|está\s+mal|esta\s+mal|"
    r"eso\s+no\s+es|el\s+manual\s+dice\s+otra\s+cosa|"
    r"error\s+en\s+la\s+respuesta|dato\s+erróneo|dato\s+erroneo|"
    r"respuesta\s+incorrecta|información\s+incorrecta|informacion\s+incorrecta)",
    re.IGNORECASE,
)


_WELCOME_TEXT = (
    "🤖 *Asistente técnico PCI*\n\n"
    "Tengo información de los manuales de *Notifier*, *Morley* y *Detnov*. "
    "Puedo ayudarte con:\n"
    "• Instalación y conexionado\n"
    "• Especificaciones técnicas\n"
    "• Configuración de centrales y módulos\n"
    "• Resolución de problemas\n\n"
    "Pregúntame en texto o envíame un *audio* 🎤.\n\n"
    "_Ejemplo: ¿Cómo configuro la central CAD-250?_"
)


_CONSENT_TERMS = (
    "🤖 *Asistente técnico PCI* — _versión beta_\n\n"
    "Te doy información de los manuales técnicos de *Notifier*, *Morley* y *Detnov*. "
    "Puedes preguntarme por texto o por audio 🎤.\n\n"
    "⚠️ *Antes de empezar — términos de uso*\n\n"
    "Para mejorar el sistema durante esta fase de pruebas, registramos:\n"
    "• Cada pregunta (texto y audio original)\n"
    "• La transcripción del audio\n"
    "• La respuesta que te doy\n"
    "• Fecha/hora y tu ID de Telegram\n\n"
    "*Para qué se usa*: identificar errores, mejorar respuestas, calibrar el sistema con preguntas reales del sector.\n\n"
    "*Quién accede*: equipo técnico de Fontiber Industrial Partners.\n\n"
    "*Terceros*: las preguntas pasan por Anthropic (modelo Claude), los audios por OpenAI (Whisper), y los registros se almacenan en Supabase. No se comparten con nadie más.\n\n"
    "*Tus derechos*: puedes pedir el borrado de tus datos contactando con tu interlocutor en Fontiber. Si no aceptas, simplemente no uses el bot.\n\n"
    "Para aceptar y empezar, envía:\n"
    "`/accept [tu nombre]`  _(el nombre es opcional pero ayuda a la revisión)_"
)


_NEEDS_CONSENT = (
    "Antes de empezar, lee los términos en /start y acepta con `/accept [tu nombre]`."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — show terms if no consent yet, otherwise welcome."""
    user_id = update.effective_user.id if update.effective_user else 0
    if has_consent(user_id):
        await update.message.reply_text(_WELCOME_TEXT, parse_mode="Markdown")
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

    name_part = f", {display_name}" if display_name else ""
    await update.message.reply_text(
        f"✅ Aceptado{name_part}. Ya puedes empezar.\n\n" + _WELCOME_TEXT,
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "*Comandos disponibles:*\n\n"
        "/start - Términos / mensaje de bienvenida\n"
        "/accept [nombre] - Aceptar términos de uso\n"
        "/help - Esta ayuda\n\n"
        "*Consejos para mejores respuestas:*\n"
        "• Menciona el modelo de equipo (ej: CAD-250, MAD-402, FT-2000, MS-25)\n"
        "• Sé específico en tu pregunta\n"
        "• Puedes preguntar sobre procedimientos paso a paso\n"
        "• 🎤 También puedes enviar audios — los transcribo automáticamente\n\n"
        "*Fabricantes cubiertos*: Notifier, Morley, Detnov.",
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text messages — classifies and routes before RAG pipeline."""
    query = update.message.text.strip()
    if not query:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    if not has_consent(user_id):
        await update.message.reply_text(_NEEDS_CONSENT, parse_mode="Markdown")
        return

    # --- Pre-pipeline classification (saves API calls) ---

    # 1. Greetings
    if _GREETING_PATTERNS.match(query):
        await update.message.reply_text(
            "¡Hola! 👋 Soy el asistente técnico PCI.\n\n"
            "Pregúntame lo que necesites sobre instalación, conexionado, "
            "especificaciones o resolución de problemas de equipos *Notifier*, *Morley* o *Detnov*.\n\n"
            "También puedes enviarme un audio 🎤",
            parse_mode="Markdown",
        )
        return

    # 2. Thanks
    if _THANKS_PATTERNS.match(query):
        await update.message.reply_text(
            "De nada 👍 ¿Necesitas algo más?"
        )
        return

    # 3. Bye
    if _BYE_PATTERNS.match(query):
        await update.message.reply_text(
            "¡Hasta luego! Aquí estaré cuando lo necesites. 🔧"
        )
        return

    # 4. Catalog questions
    if _CATALOG_PATTERNS.search(query):
        await update.message.chat.send_action("typing")
        await _handle_catalog(update)
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
                if actual_manufacturer.lower() != mentioned_manufacturer.lower():
                    # Model exists but under a different manufacturer
                    await update.message.reply_text(
                        f"El *{model}* es un producto de *{actual_manufacturer}*, "
                        f"no de _{mentioned_manufacturer}_.\n\n"
                        f"¿Te refieres al *{model}* de *{actual_manufacturer}*? "
                        f"Si es así, dime tu pregunta y te ayudo.",
                        parse_mode="Markdown",
                    )
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
                    await update.message.reply_text(
                        f"No dispongo de manuales de _{mentioned_manufacturer}_.\n\n"
                        f"Tengo información de: {manufacturers_str}.\n"
                        f"¿Puedo ayudarte con alguno de estos?",
                        parse_mode="Markdown",
                    )
                    return
                # else: manufacturer IS in DB → fall through to RAG (model index desynced)
        else:
            # No model code, just a manufacturer name mentioned
            if not manufacturer_in_db(mentioned_manufacturer):
                # Manufacturer not in DB
                available = get_available_manufacturers()
                manufacturers_str = ", ".join(f"*{m}*" for m in available)
                await update.message.reply_text(
                    f"No dispongo de manuales de _{mentioned_manufacturer}_.\n\n"
                    f"Tengo información de: {manufacturers_str}.\n"
                    f"¿Puedo ayudarte con alguno de estos?",
                    parse_mode="Markdown",
                )
                return
            # else: manufacturer IS in DB → fall through to RAG

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

        lines = ["🔥 *Productos disponibles* (Notifier, Morley, Detnov):\n"]
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
    )

    await update.message.reply_text(
        "Gracias por el aviso 🙏\n\n"
        "Tu feedback queda registrado. ¿Puedes indicarme qué dato concreto "
        "es incorrecto y qué dice el manual? Así podré mejorar."
    )


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

        # Step 1b: Carry forward model context from previous query if within session
        query_for_retrieval = query
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
                await update.message.reply_text(
                    f"Para darte información precisa sobre *{query_clean}*, "
                    f"necesito saber el modelo de equipo.\n\n"
                    f"Por ejemplo: _{query_clean} en la CAD-250_ o "
                    f"_{query_clean} del MAD-461_.\n\n"
                    f"¿Qué equipo (Notifier, Morley o Detnov) estás usando?",
                    parse_mode="Markdown",
                )
                return

        # Step 1d: Retrieve candidate chunks
        chunks = retrieve_chunks(query_for_retrieval, top_k=RETRIEVAL_TOP_K)
        retrieval_pool = list(chunks)

        # Step 2: Rerank (using original query for semantic evaluation). Dispatcher
        # RERANKER_BACKEND (s61): con target_models SIEMPRE LLM (dispatch condicional Y1
        # — solo se enruta a voyage el path que el A/B midió).
        chunks = rerank(query, chunks, top_k=RERANK_TOP_K, target_models=target_models)

        # Default-off observer: it has no return path into ``chunks`` or the
        # generator. Errors and telemetry failures are contained internally.
        try:
            observe_structural_neighbor_shadow(query, chunks)
        except Exception as exc:
            # Defense in depth: even a bug outside the observer's own fail-open
            # boundary cannot interrupt the answer path.
            logger.warning(
                "structural-neighbor shadow failed open (%s)", type(exc).__name__
            )

        # Default-off serving seam.  The main reranker's output is preserved as
        # an immutable prefix; only independently validated real source chunks
        # can be appended.  Each lane contains its own fail-open boundary.
        chunks = apply_post_rerank_coverage(
            query, chunks, retrieval_pool=retrieval_pool
        )

        # Step 2b: Get available models in detected category (for dynamic conversation)
        available_models = None
        detected_category = None
        if not target_models:
            query_lower = query.lower()
            for term, cat in CATEGORY_TERMS.items():
                if term in query_lower:
                    available_models = get_category_models(cat)
                    detected_category = cat
                    break

        # Step 3: Generate answer from reranked chunks
        result = generate_answer(query, chunks, available_models=available_models)
        answer = result["answer"]
        diagrams = result["diagrams"]

        # Store last query/response for feedback tracking + conversation context
        context.user_data["last_query"] = query
        context.user_data["last_response"] = answer[:500]
        context.user_data["last_query_time"] = _time.time()
        if target_models:
            context.user_data["last_detected_models"] = target_models

        # Log query
        elapsed_ms = int((_time.time() - start_time) * 1000)
        user_id = update.effective_user.id if update.effective_user else 0
        log_query(
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
        )

        # Step 4: Render at the transport boundary.  The factual answer kept in
        # logs/evaluation remains untouched; every part is independently valid
        # Telegram HTML, so splitting cannot leave formatting delimiters open.
        for answer_part in format_telegram_messages(answer):
            try:
                await update.message.reply_text(answer_part, parse_mode="HTML")
            except Exception:
                # Fail open without exposing raw HTML tags or entities.  This
                # fallback preserves all technical text and evidence locators.
                await update.message.reply_text(telegram_html_to_plain(answer_part))

        # Step 5: Send diagrams if available (with descriptive captions)
        for i, diagram in enumerate(diagrams):
            try:
                product = diagram.get("product", "")
                section = diagram.get("section", "")
                content_type = diagram.get("content_type", "")

                # Build descriptive caption
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

                caption = " ".join(caption_parts)

                await update.message.reply_photo(
                    photo=diagram["url"],
                    caption=caption,
                )
            except Exception as e:
                logger.warning(f"Failed to send diagram: {e}")

    except Exception as e:
        logger.error(f"Error processing query '{query}': {e}")
        await update.message.reply_text(
            "Ha ocurrido un error procesando tu pregunta. Por favor, inténtalo de nuevo."
        )


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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("Bot started. Listening for text and voice messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
