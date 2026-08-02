"""
Logging helpers for query logs, feedback, and RGPD consent.
Inserts are non-blocking — failures are logged but don't affect bot responses.
Consent checks are cached in-memory to avoid a Supabase round-trip per message.
"""

import logging
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
TERMS_VERSION = "v2"

_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# In-memory cache of user_ids with active consent on the current TERMS_VERSION.
# Populated lazily on first has_consent() check, mutated by set_consent().
_consent_cache: set[int] = set()
_consent_cache_misses: set[int] = set()  # users we've already checked and have no consent
_trace_compatibility_warning_emitted = False


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
):
    """Log technician feedback. Non-blocking."""
    try:
        row = {
            "telegram_user_id": telegram_user_id,
            "feedback_text": feedback_text,
            "previous_query": previous_query,
            "previous_response": previous_response,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/feedback",
                headers=_HEADERS,
                json=row,
            )
            if resp.status_code >= 400:
                logger.warning(f"Failed to log feedback: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Failed to log feedback: {e}")


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
    if telegram_user_id in _consent_cache:
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
                _consent_cache.add(telegram_user_id)
                return True
            _consent_cache_misses.add(telegram_user_id)
            return False
    except Exception as e:
        logger.warning(f"Failed to check consent for user {telegram_user_id}: {e}")
        return False


def set_consent(telegram_user_id: int, display_name: str | None = None) -> bool:
    """Record user consent for the current TERMS_VERSION. Returns True on success."""
    try:
        row = {
            "telegram_user_id": telegram_user_id,
            "display_name": display_name,
            "terms_version": TERMS_VERSION,
        }
        # Upsert so re-running /accept refreshes accepted_at and clears revoked_at.
        headers = {**_HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/user_consent",
                headers=headers,
                json=row,
            )
            if resp.status_code >= 400:
                logger.warning(f"Failed to set consent: {resp.status_code} {resp.text}")
                return False
        _consent_cache.add(telegram_user_id)
        _consent_cache_misses.discard(telegram_user_id)
        return True
    except Exception as e:
        logger.warning(f"Failed to set consent: {e}")
        return False
