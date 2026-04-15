"""
Telegram bot for PCI technicians.
Receives questions, queries the RAG pipeline, and returns formatted answers with diagrams.
"""

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

from ..config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, RETRIEVAL_TOP_K, RERANK_TOP_K, validate_config
from ..rag.retriever import (
    retrieve_chunks, extract_product_models, get_category_models,
    get_all_models_by_category, CATEGORY_TERMS, PCI_TERMS,
    lookup_model_manufacturer, get_available_manufacturers, manufacturer_in_db,
)
from ..rag.reranker import rerank_chunks
from ..rag.generator import generate_answer
from ..logging_db import log_query, log_feedback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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

# Catalog questions (answer with DB query, not RAG)
_CATALOG_PATTERNS = re.compile(
    r"(qué\s+(productos?|modelos?|equipos?|detectores?|centrales?)\s+(tienes|hay|tenéis|tienen|soporta)|"
    r"(listado|catálogo|catalogo|lista)\s+de\s+(productos?|modelos?|equipos?)|"
    r"para\s+qué\s+(productos?|modelos?|equipos?)\s+tienes\s+información|"
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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "🔥 *Detnov Technical Bot*\n\n"
        "Soy un asistente técnico especializado en sistemas PCI de Detnov.\n\n"
        "Puedes preguntarme sobre:\n"
        "• Instalación y conexionado de equipos\n"
        "• Especificaciones técnicas\n"
        "• Resolución de problemas\n"
        "• Configuración de centrales y módulos\n\n"
        "Escribe tu pregunta o envía un *audio* 🎤 y te responderé con la información de los manuales.\n\n"
        "_Ejemplo: ¿Cómo conecto las baterías en la CAD-250?_",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "*Comandos disponibles:*\n\n"
        "/start - Mensaje de bienvenida\n"
        "/help - Esta ayuda\n\n"
        "*Consejos para mejores respuestas:*\n"
        "• Menciona el modelo de equipo (ej: CAD-250, MAD-402)\n"
        "• Sé específico en tu pregunta\n"
        "• Puedes preguntar sobre procedimientos paso a paso\n"
        "• 🎤 También puedes enviar audios — los transcribo automáticamente\n",
        parse_mode="Markdown",
    )


async def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file using OpenAI Whisper API."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="es",
        )
    return transcript.text.strip()


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — transcribe with Whisper then process as text."""
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    await update.message.chat.send_action("typing")

    tmp_path = None
    try:
        # Download voice file from Telegram
        file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
            await file.download_to_drive(tmp_path)

        # Transcribe with Whisper
        logger.info(f"Transcribing voice message ({voice.duration}s)...")
        query = await transcribe_audio(tmp_path)

        if not query:
            await update.message.reply_text(
                "No he podido entender el audio. ¿Puedes repetirlo o escribir tu pregunta?"
            )
            return

        # Show transcription to user so they can verify
        await update.message.reply_text(f"🎤 _{query}_", parse_mode="Markdown")

        # Process as a normal text query (with voice metadata for logging)
        await _process_query(update, context, query, source="voice", transcription=query)

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

    # --- Pre-pipeline classification (saves API calls) ---

    # 1. Greetings
    if _GREETING_PATTERNS.match(query):
        await update.message.reply_text(
            "¡Hola! 👋 Soy el asistente técnico de Detnov.\n\n"
            "Pregúntame lo que necesites sobre instalación, conexionado, "
            "especificaciones o resolución de problemas de equipos Detnov.\n\n"
            "También puedes enviarme un audio 🎤"
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
                # Model not found in DB at all
                available = get_available_manufacturers()
                manufacturers_str = ", ".join(f"*{m}*" for m in available)
                await update.message.reply_text(
                    f"No tengo información sobre el modelo *{model}*.\n\n"
                    f"Tengo manuales de: {manufacturers_str}.\n"
                    f"¿Puedo ayudarte con alguno de estos fabricantes?",
                    parse_mode="Markdown",
                )
                return
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

        lines = ["🔥 *Productos Detnov disponibles:*\n"]
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
                    f"¿Qué equipo Detnov estás usando?",
                    parse_mode="Markdown",
                )
                return

        # Step 1d: Retrieve candidate chunks
        chunks = retrieve_chunks(query_for_retrieval, top_k=RETRIEVAL_TOP_K)

        # Step 2: Rerank with Claude (using original query for semantic evaluation)
        chunks = rerank_chunks(query, chunks, top_k=RERANK_TOP_K, target_models=target_models)

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
            response_length=len(answer),
            response_time_ms=elapsed_ms,
        )

        # Step 4: Format and send answer
        answer = format_for_telegram(answer)
        if len(answer) <= 4096:
            try:
                await update.message.reply_text(answer, parse_mode="Markdown")
            except Exception:
                # Fallback: send without formatting if Markdown parsing fails
                await update.message.reply_text(answer)
        else:
            parts = split_message(answer, 4096)
            for part in parts:
                try:
                    await update.message.reply_text(part, parse_mode="Markdown")
                except Exception:
                    await update.message.reply_text(part)

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


def format_for_telegram(text: str) -> str:
    """Convert Claude's Markdown output to Telegram-compatible format.

    Telegram's Markdown mode supports: *bold*, _italic_, `code`, [links](url)
    but NOT: # headers, ## subheaders, ---, > blockquotes, tables, or nested formatting.
    """
    # Convert markdown tables to clean list format
    text = convert_tables(text)

    # Convert headers: ## Title → *Title*  (bold)
    text = re.sub(r'^#{1,3}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Convert horizontal rules to a simple line
    text = re.sub(r'^---+$', '─' * 20, text, flags=re.MULTILINE)

    # Convert blockquotes: > text → text (with indent)
    text = re.sub(r'^>\s*(.+)$', r'  💡 \1', text, flags=re.MULTILINE)

    # Convert **bold** to *bold* (Telegram Markdown uses single *)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)

    # Remove any remaining triple backticks (code blocks)
    text = re.sub(r'```\w*\n?', '', text)

    return text.strip()


def convert_tables(text: str) -> str:
    """Convert Markdown tables to clean bullet-point format for Telegram.

    Example input:
        | Parámetro | Valor |
        |---|---|
        | Consumo | 0.3 mA |

    Example output:
        • Parámetro: Valor
        • Consumo: 0.3 mA
    """
    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Detect table row: starts and ends with |
        if line.startswith("|") and line.endswith("|"):
            # Collect all consecutive table lines
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            # Parse table
            rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                # Skip separator rows (|---|---|)
                if all(re.match(r'^[-:]+$', c) for c in cells):
                    continue
                rows.append(cells)

            if len(rows) >= 2:
                # First row is header
                headers = rows[0]
                for row in rows[1:]:
                    parts = []
                    for h, v in zip(headers, row):
                        if v:
                            parts.append(f"{h}: {v}")
                    result.append("• " + " | ".join(parts))
            elif len(rows) == 1:
                # Single row, just format as text
                result.append("• " + " | ".join(rows[0]))

            continue

        result.append(lines[i])
        i += 1

    return "\n".join(result)


def split_message(text: str, max_length: int = 4096) -> list[str]:
    """Split a long message into parts that fit Telegram's limit."""
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        # Find a good split point (newline or space)
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_length)
        if split_at == -1:
            split_at = max_length
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    return parts


def run_bot():
    """Start the Telegram bot."""
    validate_config(require_telegram=True)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("Bot started. Listening for text and voice messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
