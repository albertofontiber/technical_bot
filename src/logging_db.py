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
TERMS_VERSION = "v1"

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
):
    """Log a query to query_logs; failures never escape into the answer path."""
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
                else:
                    _warn_trace_compatibility_fallback_once()
            elif resp.status_code >= 400:
                logger.warning("Failed to log query: %s", resp.status_code)
    except Exception as e:
        logger.warning(f"Failed to log query: {e}")


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
