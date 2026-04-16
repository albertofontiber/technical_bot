#!/usr/bin/env python3
"""Backfill migration 001 — populate documents table from existing chunks.

This script walks every unique `source_file` currently in the chunks table,
creates one row in the new `documents` table per unique source, and updates
the `chunks.document_id` column so chunks are linked to their parent document.

Idempotent: re-running is safe. For source_files that already have a
document row, the script reuses the existing document_id and only PATCHes
chunks that still have document_id=NULL. Documents created by the ingestion
pipeline (with .pdf suffix in source_pdf_filename) are matched against
chunks.source_file (without .pdf suffix) by normalizing both sides.

WHAT THIS SCRIPT DOES NOT DO (intentionally — those come in later phases):
  - It does NOT parse revision/version/date from filenames (Phase 2 does that
    via src/ingestion/revision_parser.py). Every backfilled document is
    created with revision=NULL, status='active'.
  - It does NOT compute the real SHA-256 of the PDF content — we store the
    sha256 of the source_file string itself as a placeholder, marked with
    'backfill:' prefix. A follow-up pass during Phase 3 will replace these
    with real content hashes when each PDF is re-processed.
  - It does NOT detect document groups or supersede chains.

Usage:
    python scripts/migrations/001_backfill_documents.py            # dry run
    python scripts/migrations/001_backfill_documents.py --commit   # actually write
"""
from __future__ import annotations

import hashlib
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402

# Retry config for transient 5xx errors
_RETRY_STATUSES = {500, 502, 503, 504}
_RETRY_MAX = 4
_RETRY_BASE = 2.0  # seconds, doubled each attempt


def _strip_pdf(name: str) -> str:
    """Normalize a filename by stripping .pdf extension (case-insensitive)."""
    lower = name.lower()
    if lower.endswith(".pdf"):
        return name[:-4]
    return name


def _request_with_retry(method, url, *, client, headers, params=None, json=None):
    """Execute an HTTP request with retry on transient 5xx errors.

    Returns the httpx.Response on success, raises on exhausted retries.
    """
    import httpx
    last_exc = None
    for attempt in range(_RETRY_MAX):
        try:
            if method == "PATCH":
                resp = client.patch(url, headers=headers, params=params, json=json)
            elif method == "POST":
                resp = client.post(url, headers=headers, json=json)
            elif method == "GET":
                resp = client.get(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unknown method: {method}")

            if resp.status_code in _RETRY_STATUSES:
                last_exc = Exception(f"{resp.status_code} from {url}")
                if attempt < _RETRY_MAX - 1:
                    delay = _RETRY_BASE * (2 ** attempt)
                    time.sleep(delay)
                    continue
            return resp
        except Exception as e:
            if "timeout" in str(e).lower() or "transport" in str(e).lower():
                last_exc = e
                if attempt < _RETRY_MAX - 1:
                    delay = _RETRY_BASE * (2 ** attempt)
                    time.sleep(delay)
                    continue
            raise
    raise last_exc


def fetch_all_source_files(supabase) -> list[dict]:
    """Return [{source_file, manufacturer, product_model, count}] for every
    unique source_file currently in chunks.

    Paginates through all chunks because PostgREST has a default max-rows
    ceiling (~1000 in Supabase). Without pagination the script would silently
    miss 99% of the data on any table above that threshold.
    """
    url = f"{supabase.url}/rest/v1/chunks"
    headers = {**supabase.headers}
    page_size = 1000

    seen: dict[tuple, dict] = {}
    offset = 0
    total_rows = 0
    while True:
        params = {
            "select": "source_file,manufacturer,product_model",
            "limit": str(page_size),
            "offset": str(offset),
            "order": "id",
        }
        resp = _request_with_retry("GET", url, client=supabase.client,
                                    headers=headers, params=params)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        total_rows += len(rows)
        for r in rows:
            key = (r.get("source_file"), r.get("manufacturer"), r.get("product_model"))
            if key[0] is None:
                continue
            if key not in seen:
                seen[key] = {
                    "source_file": key[0],
                    "manufacturer": key[1],
                    "product_model": key[2],
                    "count": 0,
                }
            seen[key]["count"] += 1
        if len(rows) < page_size:
            break
        offset += page_size
        if offset > 10_000_000:
            break
    print(f"  paginated through {total_rows} chunks, {len(seen)} unique source_files")
    return list(seen.values())


def fetch_existing_documents(supabase) -> dict[str, str]:
    """Return a mapping of normalized_filename → document_id for every
    document already in the table.

    Normalizes by stripping .pdf extension so that both ingestion-created
    documents (with .pdf) and backfill-created documents (without .pdf)
    can be matched against chunks.source_file.

    Paginates to avoid the 1000-row PostgREST ceiling.
    """
    url = f"{supabase.url}/rest/v1/documents"
    headers = {**supabase.headers}
    page_size = 1000

    result: dict[str, str] = {}  # normalized_name → document_id
    offset = 0
    while True:
        params = {
            "select": "id,source_pdf_filename",
            "limit": str(page_size),
            "offset": str(offset),
            "order": "ingested_at",
        }
        resp = _request_with_retry("GET", url, client=supabase.client,
                                    headers=headers, params=params)
        if resp.status_code == 404:
            raise RuntimeError(
                "The `documents` table does not exist. Run "
                "migrations/001_document_management.sql in the Supabase SQL editor first."
            )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        for row in rows:
            normalized = _strip_pdf(row["source_pdf_filename"])
            # Later documents (by ingested_at) win — they're from the real
            # pipeline and have real SHA hashes, not placeholders.
            result[normalized] = row["id"]
        if len(rows) < page_size:
            break
        offset += page_size
        if offset > 100_000:
            break
    return result


def update_chunks_document_id(
    supabase, source_file: str, document_id: str, commit: bool
) -> int:
    """Set chunks.document_id = document_id for all chunks where
    source_file matches and document_id is NULL. Returns count updated.

    Uses retry with exponential backoff on transient 5xx errors.
    """
    if not commit:
        url = f"{supabase.url}/rest/v1/chunks"
        headers = {**supabase.headers, "Prefer": "count=exact"}
        params = {
            "select": "id",
            "source_file": f"eq.{source_file}",
            "document_id": "is.null",
            "limit": "0",
        }
        resp = _request_with_retry("GET", url, client=supabase.client,
                                    headers=headers, params=params)
        resp.raise_for_status()
        cr = resp.headers.get("content-range", "")
        if "/" in cr:
            return int(cr.split("/")[1])
        return 0

    # Real PATCH with retry
    url = f"{supabase.url}/rest/v1/chunks"
    headers = {
        **supabase.headers,
        "Prefer": "return=minimal,count=exact",
    }
    params = {
        "source_file": f"eq.{source_file}",
        "document_id": "is.null",
    }
    resp = _request_with_retry("PATCH", url, client=supabase.client,
                                headers=headers, params=params,
                                json={"document_id": document_id})
    resp.raise_for_status()
    # Count from Content-Range header
    cr = resp.headers.get("content-range", "")
    if "/" in cr:
        return int(cr.split("/")[1])
    return 0


def create_document_row(
    supabase,
    source_file: str,
    manufacturer: str,
    product_model: str | None,
    commit: bool,
) -> str | None:
    """Create a row in documents for this source_file. Returns the new id.

    Phase 1 defaults:
        document_family = source_file (stem, no normalization yet)
        revision = NULL
        revision_date = NULL
        language = NULL
        doc_type = NULL
        source_pdf_sha256 = 'backfill:<sha256 of source_file string>'
            (placeholder, will be replaced with real content hash in Phase 3)
        status = 'active'
    """
    family = _strip_pdf(source_file)

    # Placeholder hash — will be replaced in Phase 3 with real content hash
    placeholder_hash = "backfill:" + hashlib.sha256(source_file.encode("utf-8")).hexdigest()

    row = {
        "document_family": family,
        "revision": None,
        "revision_date": None,
        "language": None,
        "doc_type": None,
        "manufacturer": manufacturer or "unknown",
        "product_model": product_model,
        "source_pdf_filename": source_file,
        "source_pdf_sha256": placeholder_hash,
        "status": "active",
        "notes": "Backfilled from pre-migration chunks (Phase 1 of document-management refactor).",
    }

    if not commit:
        return "dry-run-id"

    url = f"{supabase.url}/rest/v1/documents"
    headers = {**supabase.headers, "Prefer": "return=representation"}
    resp = _request_with_retry("POST", url, client=supabase.client,
                                headers=headers, json=row)
    if resp.status_code == 409:
        # Race or duplicate: fetch existing row by hash
        params = {
            "manufacturer": f"eq.{manufacturer}",
            "source_pdf_sha256": f"eq.{placeholder_hash}",
            "select": "id",
        }
        fetch = _request_with_retry("GET", f"{supabase.url}/rest/v1/documents",
                                     client=supabase.client,
                                     headers=supabase.headers, params=params)
        fetch.raise_for_status()
        data = fetch.json()
        if not data:
            raise RuntimeError(
                f"409 on insert but no existing row found for {source_file}"
            )
        return data[0]["id"]
    resp.raise_for_status()
    return resp.json()[0]["id"]


def main() -> int:
    commit = "--commit" in sys.argv
    if not commit:
        print("DRY RUN — no changes will be written. Use --commit to apply.\n")

    supabase = get_supabase()

    # Increase timeout for large operations
    import httpx
    supabase.client = httpx.Client(timeout=120.0)

    print("Fetching existing documents (for idempotency check)...")
    existing = fetch_existing_documents(supabase)
    print(f"  {len(existing)} documents already in table\n")

    print("Fetching unique source_files from chunks...")
    sources = fetch_all_source_files(supabase)
    print(f"  {len(sources)} unique (source_file, manufacturer, product_model) combinations\n")

    skipped = 0
    created = 0
    reused = 0
    chunks_linked = 0
    errors: list[tuple[str, str]] = []

    for i, src in enumerate(sources, 1):
        sf = src["source_file"]
        mfr = src["manufacturer"] or "unknown"
        model = src["product_model"]
        n = src["count"]

        normalized = _strip_pdf(sf)

        try:
            if normalized in existing:
                # Document already exists (created by prior backfill or ingestion).
                # Reuse its ID and try to link any remaining unlinked chunks.
                doc_id = existing[normalized]
                if commit:
                    updated = update_chunks_document_id(supabase, sf, doc_id, commit)
                    chunks_linked += updated
                else:
                    updated = update_chunks_document_id(supabase, sf, "dummy", commit=False)
                    chunks_linked += updated
                if updated > 0:
                    reused += 1
                else:
                    skipped += 1
            else:
                # Create new document row + link chunks
                doc_id = create_document_row(supabase, sf, mfr, model, commit)
                if commit and doc_id:
                    updated = update_chunks_document_id(supabase, sf, doc_id, commit)
                    chunks_linked += updated
                    existing[normalized] = doc_id  # track for dedup within this run
                else:
                    updated = update_chunks_document_id(supabase, sf, "dummy", commit=False)
                    chunks_linked += updated
                created += 1

            if i % 50 == 0 or i == len(sources):
                print(
                    f"  [{i}/{len(sources)}] {sf[:50]:50s} "
                    f"[{mfr[:10]:10s}] chunks={n} linked={updated}"
                )
        except Exception as e:
            errors.append((sf, f"{type(e).__name__}: {e}"))
            if len(errors) <= 10:
                print(f"  [{i}/{len(sources)}] ERROR on {sf}: {e}")
            elif len(errors) == 11:
                print(f"  [{i}/{len(sources)}] (suppressing further error logs...)")

    print("\n" + "=" * 70)
    print(f"Unique source_files:      {len(sources)}")
    print(f"  Skipped (fully linked): {skipped}")
    print(f"  Reused (linked more):   {reused}")
    print(f"  Created (new docs):     {created}")
    print(f"  Chunks linked:          {chunks_linked}")
    print(f"  Errors:                 {len(errors)}")
    if errors:
        print("\nErrors:")
        for sf, err in errors[:20]:
            print(f"  - {sf}: {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors)-20} more")
    if not commit:
        print("\nDRY RUN complete. Re-run with --commit to apply.")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
