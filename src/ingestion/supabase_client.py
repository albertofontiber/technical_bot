"""
Shared Supabase HTTP client for ingestion scripts.
Avoids duplicating headers, client creation, and batch operations across scripts.
"""

import logging
import time
from typing import Any

import httpx

from ..config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logger = logging.getLogger(__name__)

# Retry config for transient 5xx / network errors from PostgREST
_RETRY_STATUSES = {500, 502, 503, 504}
_RETRY_MAX_ATTEMPTS = 4
_RETRY_BASE_DELAY = 2.0  # seconds, doubled each attempt


class SupabaseHTTP:
    """Lightweight Supabase client using httpx."""

    def __init__(self, url: str = SUPABASE_URL, service_key: str = SUPABASE_SERVICE_KEY):
        self.url = url.rstrip("/")
        self.service_key = service_key
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        self.client = httpx.Client(timeout=60.0)

    def insert_rows(self, table: str, rows: list[dict],
                    on_conflict: str | None = None):
        """Insert rows into a table via PostgREST, with retry on transient 5xx.

        Si `on_conflict` se pasa (nombre de columna), usa modo UPSERT: las filas
        cuyo valor de esa columna ya existe se MERGEAN en vez de devolver 409
        Conflict. Necesario para idempotencia ante reintentos — si una petición
        se completa server-side pero la respuesta se pierde, el retry POSTea de
        nuevo con los mismos UUIDs y sin upsert eso da 409.

        Retries up to _RETRY_MAX_ATTEMPTS times with exponential backoff for
        5xx responses and httpx transport errors. Raises on final failure or
        any non-retryable error (4xx).
        """
        url = f"{self.url}/rest/v1/{table}"
        headers = self.headers
        params = None
        if on_conflict:
            headers = {**self.headers,
                       "Prefer": "resolution=merge-duplicates,return=minimal"}
            params = {"on_conflict": on_conflict}

        last_exc: Exception | None = None
        for attempt in range(_RETRY_MAX_ATTEMPTS):
            try:
                resp = self.client.post(url, headers=headers, json=rows,
                                        params=params)
                if resp.status_code in _RETRY_STATUSES:
                    last_exc = httpx.HTTPStatusError(
                        f"{resp.status_code} from {resp.url}",
                        request=resp.request,
                        response=resp,
                    )
                    if attempt < _RETRY_MAX_ATTEMPTS - 1:
                        delay = _RETRY_BASE_DELAY * (2 ** attempt)
                        logger.warning(
                            f"insert_rows: {resp.status_code} on attempt {attempt+1}/"
                            f"{_RETRY_MAX_ATTEMPTS}, retrying in {delay:.0f}s "
                            f"({len(rows)} rows)"
                        )
                        time.sleep(delay)
                        continue
                if resp.status_code >= 400:
                    # PostgREST devuelve el detalle del error en el body —
                    # sin esto solo veríamos "Client error" sin saber qué constraint
                    raise httpx.HTTPStatusError(
                        f"{resp.status_code} from {resp.url} :: {resp.text[:500]}",
                        request=resp.request, response=resp)
                return  # success
            except (httpx.TransportError, httpx.ReadTimeout) as e:
                last_exc = e
                if attempt < _RETRY_MAX_ATTEMPTS - 1:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"insert_rows: transport error on attempt {attempt+1}/"
                        f"{_RETRY_MAX_ATTEMPTS} ({type(e).__name__}), retrying in {delay:.0f}s"
                    )
                    time.sleep(delay)
                    continue
                raise
        # Exhausted retries
        if last_exc:
            raise last_exc

    def upload_file(self, bucket: str, path: str, data: bytes, content_type: str = "image/jpeg"):
        """Upload a file to Supabase Storage."""
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        resp = self.client.post(
            f"{self.url}/storage/v1/object/{bucket}/{path}",
            headers=headers,
            content=data,
        )
        resp.raise_for_status()

    def get_public_url(self, bucket: str, path: str) -> str:
        return f"{self.url}/storage/v1/object/public/{bucket}/{path}"

    def fetch_rows(
        self,
        table: str,
        select: str = "*",
        filters: dict[str, str] | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Fetch rows from a table with optional filters."""
        params: dict[str, str] = {"select": select, "limit": str(limit)}
        if filters:
            params.update(filters)

        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        resp = self.client.get(
            f"{self.url}/rest/v1/{table}",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def update_row(self, table: str, row_id: str, data: dict):
        """Update a single row by ID."""
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        resp = self.client.patch(
            f"{self.url}/rest/v1/{table}",
            headers=headers,
            params={"id": f"eq.{row_id}"},
            json=data,
        )
        resp.raise_for_status()

    def delete_rows(self, table: str, filters: dict[str, str]):
        """Delete rows matching filters."""
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        resp = self.client.delete(
            f"{self.url}/rest/v1/{table}",
            headers=headers,
            params=filters,
        )
        resp.raise_for_status()

    def count_rows(self, table: str, filters: dict[str, str] | None = None) -> int:
        """Count rows matching optional filters."""
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Prefer": "count=exact",
        }
        params: dict[str, str] = {"select": "id", "limit": "0"}
        if filters:
            params.update(filters)

        resp = self.client.get(
            f"{self.url}/rest/v1/{table}",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        # Count comes in Content-Range header: "0-0/17698"
        content_range = resp.headers.get("Content-Range", "")
        if "/" in content_range:
            return int(content_range.split("/")[1])
        return 0


def get_supabase() -> SupabaseHTTP:
    """Get a shared Supabase client instance."""
    return SupabaseHTTP()


def batch_update(
    supabase: SupabaseHTTP,
    table: str,
    updates: list[dict],
    id_field: str = "id",
    progress_interval: int = 500,
) -> tuple[int, int]:
    """Apply batch updates to a table with progress reporting.

    Args:
        supabase: Supabase client.
        table: Table name.
        updates: List of dicts with 'id' and fields to update.
        id_field: Name of the ID field.
        progress_interval: Log progress every N updates.

    Returns:
        Tuple of (success_count, error_count).
    """
    success = 0
    errors = 0

    for i, update in enumerate(updates):
        row_id = update.pop(id_field)
        try:
            supabase.update_row(table, row_id, update)
            success += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                logger.error(f"Update failed for {row_id}: {e}")

        if (i + 1) % progress_interval == 0:
            logger.info(f"   Updated {i + 1} / {len(updates)} (errors: {errors})")

    logger.info(f"   Done: {success} updated, {errors} errors")
    return success, errors
