"""
Logging helpers for query logs, feedback, and RGPD consent.
Inserts are non-blocking — failures are logged but don't affect bot responses.
Consent checks are cached in-memory to avoid a Supabase round-trip per message.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from .rag.runtime_trace import validate_rag_serving_trace
from .version import get_bot_version

logger = logging.getLogger(__name__)

# Telegram message limit, also used to cap response storage to keep rows bounded.
_RESPONSE_MAX_CHARS = 4096

# Bump this string when consent terms change → forces users to re-accept.
# v2 (s286): terms now list the 👍/👎 answer verdict as recorded data.
# v3 (s294): el bot ahora PIDE explicaciones en texto libre tras un 👎 — antes
# solo recogia lo que el tecnico escribia por su cuenta. Pedir un dato nuevo
# obliga a re-aceptar (precedente: el voto 👍/👎 subio v1->v2 en s286).
# v4 (s295): plazo de retencion (24 meses -> DISOCIADO; es seudonimizacion, no
# anonimizacion: el texto libre puede identificar), canal de derechos
# (info@fontiber.com) y correccion — se declaraba guardar el "audio original" y
# NO se guarda (solo la transcripcion; el fichero temporal se borra tras Whisper).
# v5 (s295, tras el duo): faltaban DOS encargados que reciben la consulta -- VOYAGE AI
# (embebe la pregunta para buscar en chunks_v2) y RAILWAY (ejecuta el bot) -- mientras el
# texto afirmaba "no se comparten con nadie mas". Ademas se declara la transferencia fuera
# de la UE y se ACOTA la promesa de retirada del identificador a lo que el mecanismo hace
# (consultas y valoraciones; la prueba del consentimiento sigue su propia regla). El MISMO
# salto v5 lleva ademas el aviso en DOS CAPAS (aceptacion corta + /privacidad con el detalle)
# y los destinatarios por CATEGORIA: se agrupa a proposito para que haya UNA sola
# re-aceptacion en vez de dos.
# v6 (s295): identificacion COMPLETA del responsable en el aviso (razon social, CIF y
# domicilio, tomados del aviso legal de fontiber.com). Antes solo constaba el nombre
# comercial y un correo. Se sube version por prudencia: cambia QUIEN responde ante el
# interesado, y eso no es cosmetico aunque no cambie que se trata ni para que.
# v7 (s296): FINALIDAD NUEVA. El aviso decia "no se usa para perfilarte ni para decisiones
# sobre ti", y Alberto quiere poder reconocer/incentivar a quien aporte feedback valioso --
# lo cual ES una decision sobre la persona. Se declara: la marca de utilidad la pone una
# PERSONA al revisar (nunca el sistema) y cualquier decision la toma una persona. Sin este
# cambio, usar el feedback para un bonus contradiria lo prometido.
TERMS_VERSION = "v7"

_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# In-memory cache of user_ids with active consent on the current TERMS_VERSION.
# s297 (duo): entrada -> EXPIRACION (time.monotonic). Antes era un set que no expiraba
# nunca ⇒ un usuario REVOCADO manualmente seguia entrando hasta reiniciar el worker. Con
# TTL, la revocacion surte efecto en <= _CONSENT_CACHE_TTL_S sin reinicio. Los misses se
# quedan sin TTL: un miss caduco solo cuesta una relectura a DB, que ya hace lo correcto.
_CONSENT_CACHE_TTL_S = 600
_consent_cache: dict[int, float] = {}
_consent_cache_misses: set[int] = set()  # users we've already checked and have no consent
_trace_compatibility_warning_emitted = False
# Personas de las que ya sabemos que tienen codigo. Evita una llamada por consulta: el
# codigo, una vez emitido, no cambia nunca.
_seudonimo_emitido: set[int] = set()


def _trace_contract_rejected(response: httpx.Response) -> bool:
    """Return true only for a definitive optional-trace schema rejection.

    Timeouts and uncertain network failures are never retried because the first
    INSERT may have committed. These explicit PostgREST/Postgres errors are
    atomic failures, so one compatibility retry without ``rag_trace`` is safe.
    """
    if response.status_code not in (400, 409):
        return False
    try:
        payload = response.json()
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    code = str(payload.get("code") or "")
    message = " ".join(
        str(payload.get(key) or "") for key in ("message", "details", "hint")
    ).lower()
    if code == "PGRST204" and "rag_trace" in message:
        return True
    if code == "42703" and "rag_trace" in message:
        return True
    return code == "23514" and "query_logs_rag_trace" in message


def _warn_trace_compatibility_fallback_once() -> None:
    global _trace_compatibility_warning_emitted
    if not _trace_compatibility_warning_emitted:
        logger.warning(
            "query_logs accepted without rag_trace after a definitive schema "
            "rejection; apply or inspect the telemetry migration"
        )
        _trace_compatibility_warning_emitted = True


def log_query(
    telegram_user_id: int,
    query: str,
    source: str = "text",
    transcription: str | None = None,
    product_models: list[str] | None = None,
    category: str | None = None,
    chunks_used: int = 0,
    response: str | None = None,
    response_length: int = 0,
    response_time_ms: int = 0,
    rag_trace: dict[str, Any] | None = None,
    query_log_id: str | None = None,
) -> bool:
    """Log a query to query_logs; failures never escape into the answer path.

    ``query_log_id`` lets the caller supply the row's UUID client-side (works
    with ``Prefer: return=minimal`` and survives the compatibility retry, which
    only fires on definitive atomic rejections — same id, no conflict). The
    bool return says whether the row is KNOWN to be committed: a timeout after
    the POST may have committed anyway and still returns False (caller policy:
    treat False as "don't reference this row", e.g. skip the feedback keyboard
    that turn — losing signal is safe, a dangling FK reference is not).
    """
    try:
        safe_trace = None
        if rag_trace is not None:
            safe_trace = validate_rag_serving_trace(rag_trace)
            if safe_trace is None:
                logger.warning("Rejected rag_trace outside the closed storage schema")
        stored_response = response[:_RESPONSE_MAX_CHARS] if response else None
        row = {
            "telegram_user_id": telegram_user_id,
            "query": query,
            "source": source,
            "transcription": transcription,
            "product_models": product_models or [],
            "category": category,
            "chunks_used": chunks_used,
            "response": stored_response,
            "response_length": response_length,
            "response_time_ms": response_time_ms,
            "bot_version": get_bot_version(),
        }
        if query_log_id is not None:
            row["id"] = query_log_id
        if safe_trace is not None:
            row["rag_trace"] = safe_trace
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/query_logs",
                headers=_HEADERS,
                json=row,
            )
            if safe_trace is not None and _trace_contract_rejected(resp):
                fallback_row = dict(row)
                fallback_row.pop("rag_trace", None)
                fallback = client.post(
                    f"{SUPABASE_URL}/rest/v1/query_logs",
                    headers=_HEADERS,
                    json=fallback_row,
                )
                if fallback.status_code >= 400:
                    logger.warning(
                        "Failed to log query after trace compatibility fallback: %s",
                        fallback.status_code,
                    )
                    return False
                _warn_trace_compatibility_fallback_once()
                return True
            if resp.status_code >= 400:
                logger.warning("Failed to log query: %s", resp.status_code)
                return False
            return True
    except Exception as e:
        logger.warning(f"Failed to log query: {e}")
    return False


def log_feedback(
    telegram_user_id: int,
    feedback_text: str,
    previous_query: str | None = None,
    previous_response: str | None = None,
    query_log_id: str | None = None,
):
    """Log technician feedback. Non-blocking.

    ``query_log_id`` (s296): esta tabla guardaba COPIAS del texto de la pregunta y la
    respuesta, sin referencia a ellas, así que un borrado de `query_logs` no la alcanzaba.
    Con el enlace, la fila cascadea sola. Las filas anteriores a s296 quedan huérfanas —
    solo tienen texto, no se pueden emparejar a posteriori — y así se declara en la matriz.
    """
    try:
        row = {
            "telegram_user_id": telegram_user_id,
            "feedback_text": feedback_text,
            "previous_query": previous_query,
            "previous_response": previous_response,
        }
        if query_log_id is not None:
            row["query_log_id"] = query_log_id
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/feedback",
                headers=_HEADERS,
                json=row,
            )
            # s297: si el enlace quedó COLGANDO (la consulta padre se borró entre que se
            # capturó `last_query_log_id` y este POST — p.ej. una supresión a petición),
            # la FK rechaza la fila ENTERA y el feedback se perdería. Se reintenta SIN el
            # enlace: sobrevive suelto, como antes de s296. Mismo patrón que el fallback
            # de `log_query` con la traza. Solo ante el rechazo definitivo de FK (23503):
            # un timeout no se reintenta, porque el primer POST pudo haberse confirmado.
            if resp.status_code >= 400 and "query_log_id" in row and _fk_rejected(resp):
                # El duo cazo el matiz: si el padre desaparecio por una SUPRESION, las
                # copias de la pregunta y la respuesta SON el dato recien borrado --
                # reinsertarlas seria re-materializar lo suprimido, suelto y fuera de toda
                # cascada. El texto del feedback si se conserva: es el mensaje NUEVO del
                # tecnico, tratamiento fresco.
                fallback_row = {k: v for k, v in row.items()
                                if k not in ("query_log_id", "previous_query",
                                             "previous_response")}
                reintento = client.post(
                    f"{SUPABASE_URL}/rest/v1/feedback",
                    headers=_HEADERS,
                    json=fallback_row,
                )
                if reintento.status_code >= 400:
                    logger.warning(
                        "Failed to log feedback after dangling-FK fallback: %s",
                        reintento.status_code,
                    )
                else:
                    logger.warning(
                        "Feedback guardado SIN enlace: su consulta ya no existe (FK 23503)"
                    )
                return
            if resp.status_code >= 400:
                logger.warning(f"Failed to log feedback: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Failed to log feedback: {e}")


def _fk_rejected(response: httpx.Response) -> bool:
    """True solo ante una violación de clave foránea DEFINITIVA (SQLSTATE 23503)."""
    if response.status_code not in (400, 409):
        return False
    try:
        payload = response.json()
    except Exception:
        return False
    return isinstance(payload, dict) and str(payload.get("code") or "") == "23503"


def log_answer_feedback(
    query_log_id: str,
    telegram_user_id: int,
    verdict: str,
) -> bool:
    """Upsert a 1-tap answer verdict; last-wins per (query_log, user).

    The conflict target is the UNIQUE pair, NOT the primary key, so unlike
    ``set_consent`` the ``Prefer: resolution=merge-duplicates`` header alone is
    not enough — PostgREST also needs the ``on_conflict`` query param or the
    👍→👎 toggle would 409 instead of updating. Returns True when the vote is
    known committed. A dangling ``query_log_id`` (row RGPD-deleted, stale
    keyboard) fails the FK and returns False — the tap is dropped, by design.
    """
    try:
        row = {
            "query_log_id": query_log_id,
            "telegram_user_id": telegram_user_id,
            "verdict": verdict,
        }
        headers = {**_HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/answer_feedback",
                headers=headers,
                params={"on_conflict": "query_log_id,telegram_user_id"},
                json=row,
            )
            if resp.status_code >= 400:
                logger.warning("Failed to log answer feedback: %s", resp.status_code)
                return False
        return True
    except Exception as e:
        logger.warning(f"Failed to log answer feedback: {e}")
        return False


FEEDBACK_REASON_CLASSES = ("info", "wrong", "scope", "other")


def set_feedback_reason(
    query_log_id: str,
    telegram_user_id: int,
    reason_class: str,
) -> bool:
    """Anota el MOTIVO de un 👎 sobre la fila del voto que ya existe (#60 punto 5).

    Es un PATCH, no un upsert: el motivo solo tiene sentido si el voto está
    registrado — si no hay fila, no se inventa una (un motivo sin verdict no es
    interpretable). PostgREST devuelve 204 igualmente cuando el filtro no casa, así
    que se pide ``return=representation`` para distinguir «escrito» de «no había
    fila».

    Fail-open: cualquier error devuelve False sin propagar.
    """
    if reason_class not in FEEDBACK_REASON_CLASSES:
        logger.warning("Invalid feedback reason class: %r", reason_class)
        return False
    try:
        headers = {**_HEADERS, "Prefer": "return=representation"}
        params = {
            "query_log_id": f"eq.{query_log_id}",
            "telegram_user_id": f"eq.{telegram_user_id}",
            "select": "id",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.patch(
                f"{SUPABASE_URL}/rest/v1/answer_feedback",
                headers=headers,
                params=params,
                json={"reason_class": reason_class},
            )
            if resp.status_code >= 400:
                logger.warning("Failed to set feedback reason: %s", resp.status_code)
                return False
            return bool(resp.json())
    except Exception as exc:
        logger.warning(f"Failed to set feedback reason: {exc}")
        return False


def set_feedback_comment(
    query_log_id: str,
    telegram_user_id: int,
    comment: str,
    *,
    max_chars: int = 2000,
) -> bool:
    """Guarda la EXPLICACIÓN en prosa sobre el voto que ya existe (#60 punto 5b).

    Va a `answer_feedback.comment` — la columna que s286 (DEC-162f) reservó para
    esto: «la Fase 2 «¿qué faltó?» escribirá `answer_feedback.comment`, NO
    `feedback`». Así la prosa hereda FK, UNIQUE por (consulta, usuario) y CASCADE,
    y queda unible al veredicto y a la evidencia servida sin esquema nuevo.

    PATCH, no upsert: sin voto previo no hay nada que explicar. Fail-open.
    """
    text = (comment or "").strip()
    if not text:
        return False
    try:
        headers = {**_HEADERS, "Prefer": "return=representation"}
        params = {
            "query_log_id": f"eq.{query_log_id}",
            "telegram_user_id": f"eq.{telegram_user_id}",
            "select": "id",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.patch(
                f"{SUPABASE_URL}/rest/v1/answer_feedback",
                headers=headers,
                params=params,
                json={"comment": text[:max_chars]},
            )
            if resp.status_code >= 400:
                logger.warning("Failed to set feedback comment: %s", resp.status_code)
                return False
            return bool(resp.json())
    except Exception as exc:
        logger.warning(f"Failed to set feedback comment: {exc}")
        return False


def has_feedback_reason(query_log_id: str, telegram_user_id: int) -> bool:
    """¿Este voto ya tiene motivo? Evita re-preguntar «¿qué falló?» si el técnico
    vuelve a pulsar 👎 sobre el mismo teclado. Sin estado en memoria: el bot
    reinicia y los teclados viejos siguen siendo válidos (contrato s286).

    Ante error devuelve False = «no consta» ⇒ como mucho se pregunta de más, nunca
    se pierde la oportunidad de preguntar.
    """
    try:
        params = {
            "query_log_id": f"eq.{query_log_id}",
            "telegram_user_id": f"eq.{telegram_user_id}",
            "reason_class": "not.is.null",
            "select": "id",
            "limit": "1",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/answer_feedback",
                headers=_HEADERS,
                params=params,
            )
            if resp.status_code >= 400:
                logger.warning(
                    "Failed to check feedback reason: %s", resp.status_code
                )
                return False
            return bool(resp.json())
    except Exception as exc:
        logger.warning(f"Failed to check feedback reason: {exc}")
        return False


def stamp_answer_messages(
    query_log_id: str,
    telegram_chat_id: int,
    message_ids: list[int],
) -> bool:
    """Ancla los mensajes enviados de una respuesta a su fila de `query_logs`.

    Es el punto 1 del paquete de telemetría (#60): una REACCIÓN de Telegram solo
    trae `message_id`, así que sin esta ancla no hay forma de saber a qué consulta
    se refiere. Se estampan TODAS las partes (la respuesta se envía partida), en un
    único POST.

    No bloqueante y fail-open TOTAL, igual que el resto del logging: cualquier
    excepción o error HTTP se traga con un warning y devuelve False — el técnico ya
    tiene su respuesta y una telemetría caída jamás puede cambiarla.

    Idempotente vía ``resolution=ignore-duplicates`` (``ON CONFLICT DO NOTHING``)
    sobre el UNIQUE (chat, message): un reintento del mismo envío no duplica.
    **NO se usa ``merge-duplicates``** aunque sea el patrón de `answer_feedback`:
    ese es un UPSERT y PostgREST exige privilegio UPDATE, que esta tabla no tiene
    ni necesita — el ancla es de ESCRITURA ÚNICA. Cazado en smoke contra la DB
    real: con merge-duplicates el insert devolvía 403 y, por el fail-open, el
    ancla nunca se habría estampado sin que nada fallara a la vista.
    """
    if not message_ids:
        return False
    try:
        rows = [
            {
                "query_log_id": query_log_id,
                "telegram_chat_id": telegram_chat_id,
                "telegram_message_id": message_id,
                "part_index": index,
            }
            for index, message_id in enumerate(message_ids)
        ]
        headers = {**_HEADERS, "Prefer": "resolution=ignore-duplicates,return=minimal"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/answer_messages",
                headers=headers,
                params={"on_conflict": "telegram_chat_id,telegram_message_id"},
                json=rows,
            )
            if resp.status_code >= 400:
                logger.warning(
                    "Failed to stamp answer messages: %s", resp.status_code
                )
                return False
        return True
    except Exception as exc:
        logger.warning(f"Failed to stamp answer messages: {exc}")
        return False


def query_log_id_for_message(
    telegram_chat_id: int,
    telegram_message_id: int,
) -> str | None:
    """Búsqueda inversa del ancla: (chat, message) → `query_log_id`.

    La consume el handler de reacciones (punto 3 de #60). Devuelve None cuando no
    hay ancla — mensaje ajeno al bot, respuesta anterior a esta telemetría, o fila
    ya borrada por retención RGPD (la cascada se lleva el ancla, por diseño).
    """
    try:
        params = {
            "telegram_chat_id": f"eq.{telegram_chat_id}",
            "telegram_message_id": f"eq.{telegram_message_id}",
            "select": "query_log_id",
            "limit": "1",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/answer_messages",
                headers=_HEADERS,
                params=params,
            )
            if resp.status_code >= 400:
                logger.warning(
                    "Failed to resolve answer message: %s", resp.status_code
                )
                return None
            rows = resp.json()
        if not rows:
            return None
        return str(rows[0].get("query_log_id")) or None
    except Exception as exc:
        logger.warning(f"Failed to resolve answer message: {exc}")
        return None


def has_consent(telegram_user_id: int) -> bool:
    """Check if user has accepted the current TERMS_VERSION.

    Cached in-memory after first successful check. On Supabase failure,
    returns False (fail-closed: don't log queries from un-verified users).
    """
    expiracion = _consent_cache.get(telegram_user_id)
    if expiracion is not None and expiracion > time.monotonic():
        return True
    if telegram_user_id in _consent_cache_misses:
        return False

    try:
        params = {
            "telegram_user_id": f"eq.{telegram_user_id}",
            "terms_version": f"eq.{TERMS_VERSION}",
            "revoked_at": "is.null",
            "select": "telegram_user_id",
            "limit": "1",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/user_consent",
                headers=_HEADERS,
                params=params,
            )
            if resp.status_code == 200 and resp.json():
                _consent_cache[telegram_user_id] = time.monotonic() + _CONSENT_CACHE_TTL_S
                return True
            _consent_cache_misses.add(telegram_user_id)
            return False
    except Exception as e:
        logger.warning(f"Failed to check consent for user {telegram_user_id}: {e}")
        return False


def seudonimo_de(telegram_user_id: int) -> str | None:
    """Código estable de esa persona. Lo emite la primera vez y lo reutiliza siempre.

    Es la pieza que permite AGRUPAR sin identificar: los exports a disco llevan este
    código y nunca el identificador de Telegram, así que el identificador real no sale
    de la base de datos. A los 24 meses el job estampa este mismo código en los registros
    y **borra la correspondencia** — ese borrado es el punto de no retorno, y hasta
    entonces el corpus de un técnico sigue siendo reconocible como suyo.

    Fail-open: si no se puede emitir, devuelve None. Nunca debe romper una respuesta.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/persona_seudonimo",
                headers={**_HEADERS, "Prefer": "return=representation"},
                params={
                    "telegram_user_id": f"eq.{telegram_user_id}",
                    "select": "seudonimo",
                    "limit": "1",
                },
            )
            if resp.status_code == 200 and resp.json():
                _seudonimo_emitido.add(telegram_user_id)
                return resp.json()[0]["seudonimo"]

            # `ignore-duplicates`: si dos mensajes llegan a la vez, el segundo no pisa al
            # primero. El código NUNCA debe cambiar — uno que cambia deja de agrupar.
            creada = client.post(
                f"{SUPABASE_URL}/rest/v1/persona_seudonimo",
                headers={**_HEADERS,
                         "Prefer": "resolution=ignore-duplicates,return=representation"},
                json={"telegram_user_id": telegram_user_id},
            )
            if creada.status_code < 400 and creada.json():
                _seudonimo_emitido.add(telegram_user_id)
                return creada.json()[0]["seudonimo"]
            # Perdió la carrera: la fila la escribió el otro mensaje. Se relee.
            relectura = client.get(
                f"{SUPABASE_URL}/rest/v1/persona_seudonimo",
                headers=_HEADERS,
                params={
                    "telegram_user_id": f"eq.{telegram_user_id}",
                    "select": "seudonimo",
                    "limit": "1",
                },
            )
            if relectura.status_code == 200 and relectura.json():
                _seudonimo_emitido.add(telegram_user_id)
                return relectura.json()[0]["seudonimo"]
    except Exception as e:
        logger.warning(f"No se pudo obtener el seudonimo: {e}")
    return None


def asegurar_seudonimo(telegram_user_id: int) -> None:
    """Garantiza que esa persona tiene código, sin pagar una llamada por consulta.

    `/accept` no basta: quien ya aceptó y sigue usando el bot NO vuelve a pasar por ahí, y
    quien vuelve después de que su vínculo se destruyera tampoco. Sin código, sus filas
    quedarían fuera de la agrupación — y el job las disociaría emitiendo uno nuevo, con el
    corpus partido. Aquí se cierra ese hueco.
    """
    if telegram_user_id in _seudonimo_emitido:
        return
    seudonimo_de(telegram_user_id)


def set_consent(telegram_user_id: int, display_name: str | None = None) -> bool:
    """Record user consent for the current TERMS_VERSION. Returns True on success."""
    try:
        row = {
            "telegram_user_id": telegram_user_id,
            "display_name": display_name,
            "terms_version": TERMS_VERSION,
            # s295: sin estas dos el upsert NO las tocaba y el comentario de abajo era
            # FALSO. `accepted_at` conservaba la fecha de la PRIMERA aceptación (una
            # prueba de consentimiento «v4» fechada en v1) y `revoked_at` seguía puesto,
            # mientras `_consent_cache` daba al usuario por consentido: servido en
            # memoria, revocado en la base, y bloqueado otra vez al reiniciar el proceso.
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "revoked_at": None,
        }
        # s296 APPEND-ONLY: el conflicto se resuelve sobre (persona, VERSIÓN), no sobre la
        # persona. Re-aceptar la MISMA versión refresca su fila; aceptar una versión NUEVA
        # deja intacta la anterior, que es la prueba de que en su día aceptó aquella. Antes
        # el upsert iba por PK de persona y machacaba el histórico de aceptaciones.
        headers = {**_HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/user_consent"
                "?on_conflict=telegram_user_id,terms_version",
                headers=headers,
                json=row,
            )
            if resp.status_code >= 400:
                logger.warning(f"Failed to set consent: {resp.status_code} {resp.text}")
                return False

        # El estado esta COMMITEADO: desde aqui, el tecnico entra pase lo que pase.
        _consent_cache[telegram_user_id] = time.monotonic() + _CONSENT_CACHE_TTL_S
        _consent_cache_misses.discard(telegram_user_id)

        # s297: el LIBRO. `user_consent` es el estado vigente; el evento es la EVIDENCIA
        # (tabla de solo inserción para el bot — inmutabilidad estructural). Se escribe
        # DESPUÉS del estado: si el estado falló, la aceptación no se consumó y no hay qué
        # evidenciar. Fail-open DE VERDAD: en su propio try — el dúo cazó que con el POST
        # dentro del try general, una excepción de transporte tras un estado ya commiteado
        # devolvía False, el bot pedía reintentar con el consentimiento YA dado, y el
        # usuario quedaba atascado en la caché de misses. Bloquear la entrada porque falló
        # la evidencia sería desproporcionado; la divergencia queda declarada en la matriz.
        try:
            with httpx.Client(timeout=10.0) as client:
                evento = client.post(
                    f"{SUPABASE_URL}/rest/v1/consent_events",
                    headers=_HEADERS,
                    json={
                        "telegram_user_id": telegram_user_id,
                        "terms_version": TERMS_VERSION,
                        "evento": "accepted",
                    },
                )
                if evento.status_code >= 400:
                    logger.warning(
                        "Consentimiento registrado SIN evento en el libro (%s): "
                        "aplicar la migracion s297 o revisar consent_events",
                        evento.status_code,
                    )
        except Exception as e:
            logger.warning(
                "Consentimiento registrado SIN evento en el libro (transporte: %s)", e
            )
        return True
    except Exception as e:
        logger.warning(f"Failed to set consent: {e}")
        return False
