"""
Logging helpers for query logs and feedback.
Inserts are non-blocking — failures are logged but don't affect bot responses.
"""

import logging
from datetime import datetime

import httpx

from .config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logger = logging.getLogger(__name__)

_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def log_query(
    telegram_user_id: int,
    query: str,
    source: str = "text",
    transcription: str | None = None,
    product_models: list[str] | None = None,
    category: str | None = None,
    chunks_used: int = 0,
    response_length: int = 0,
    response_time_ms: int = 0,
):
    """Log a query to the query_logs table. Non-blocking."""
    try:
        row = {
            "telegram_user_id": telegram_user_id,
            "query": query,
            "source": source,
            "transcription": transcription,
            "product_models": product_models or [],
            "category": category,
            "chunks_used": chunks_used,
            "response_length": response_length,
            "response_time_ms": response_time_ms,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/query_logs",
                headers=_HEADERS,
                json=row,
            )
            if resp.status_code >= 400:
                logger.warning(f"Failed to log query: {resp.status_code}")
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
