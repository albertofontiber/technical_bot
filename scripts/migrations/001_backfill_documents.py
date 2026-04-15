#!/usr/bin/env python3
"""Backfill migration 001 — populate documents table from existing chunks.

This script walks every unique `source_file` currently in the chunks table,
creates one row in the new `documents` table per unique source, and updates
the `chunks.document_id` column so chunks are linked to their parent document.

Idempotent: re-running is safe. Skips source_files that already have a
document row. Skips chunks that already have document_id set.

WHAT THIS SCRIPT DOES NOT DO (intentionally — those come later phases):
  - It does NOT parse revision/version/date from filenames (that's Phase 2,
    once src/ingestion/revision_parser.py exists). Every backfilled document
    is created with revision=NULL, status='active'.
  - It does NOT compute the real SHA-256 of the PDF content — we store the
    sha256 of the source_file string itself as a placeholder, marked with
    'backfill:' prefix. A follow-up pass during Phase 3 will replace these
    with real content hashes when each PDF is re-processed.
  - It does NOT detect document groups or supersede chains.

This is deliberate: Phase 1 is about getting the data model live with
minimal disruption. Phase 2/3 iterate on top.

Usage:
    python scripts/migrations/001_backfill_documents.py            # dry run
    python scripts/migrations/001_backfill_documents.py --commit   # actually write
"""
from __future__ import annotations

import hashlib
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402


def fetch_all_source_files(supabase) -> list[dict]:
    """Return [{source_file, manufacturer, product_model, count}] for every
    unique source_file currently in chunks.

    Paginates through all chunks because PostgREST has a default max-rows
    ceiling (~1000 in Supabase). Without pagination the script would silently
    miss 99% of the data on any table above that threshold. We page through
    with limit+offset and deduplicate in Python.
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
            "order": "id",  # deterministic pagination order
        }
        resp = supabase.client.get(url, headers=headers, params=params)
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
        if offset > 10_000_000:  # safety stop
            break
    print(f"  paginated through {total_rows} chunks, {len(seen)} unique source_files")
    return list(seen.values())


def fetch_existing_documents(supabase) -> set[str]:
    """Return the set of source_pdf_filename values already present in
    the documents table (for idempotency)."""
    url = f"{supabase.url}/rest/v1/documents"
    resp = supabase.client.get(
        url, headers=supabase.headers, params={"select": "source_pdf_filename"}
    )
    if resp.status_code == 404:
        # documents table doesn't exist → migration SQL wasn't applied
        raise RuntimeError(
            "The `documents` table does not exist. Run migrations/001_document_management.sql "
            "in the Supabase SQL editor first."
        )
    resp.raise_for_status()
    return {row["source_pdf_filename"] for row in resp.json()}


def update_chunks_document_id(
    supabase, source_file: str, document_id: str, commit: bool
) -> int:
    """Set chunks.document_id = document_id for all chunks where
    source_file matches and document_id is NULL. Returns count updated."""
    if not commit:
        # Count would-be affected rows (for dry-run)
        url = f"{supabase.url}/rest/v1/chunks"
        headers = {**supabase.headers, "Prefer": "count=exact"}
        params = {
            "select": "id",
            "source_file": f"eq.{source_file}",
            "document_id": "is.null",
        }
        resp = supabase.client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return len(resp.json())

    # Real PATCH
    url = f"{supabase.url}/rest/v1/chunks"
    headers = {
        **supabase.headers,
        "Prefer": "return=representation,count=exact",
    }
    params = {
        "source_file": f"eq.{source_file}",
        "document_id": "is.null",
    }
    resp = supabase.client.patch(
        url, headers=headers, params=params, json={"document_id": document_id}
    )
    resp.raise_for_status()
    return len(resp.json())


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
    # Strip .pdf / .PDF extension for document_family
    family = source_file
    for ext in (".pdf", ".PDF", ".Pdf"):
        if family.endswith(ext):
            family = family[: -len(ext)]
            break

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
    resp = supabase.client.post(url, headers=headers, json=row)
    if resp.status_code == 409:
        # Race: another run created it. Fetch and return its id.
        params = {
            "manufacturer": f"eq.{manufacturer}",
            "source_pdf_sha256": f"eq.{placeholder_hash}",
            "select": "id",
        }
        fetch = supabase.client.get(
            f"{supabase.url}/rest/v1/documents", headers=supabase.headers, params=params
        )
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
    print("Fetching existing documents (for idempotency check)...")
    existing = fetch_existing_documents(supabase)
    print(f"  {len(existing)} documents already in table\n")

    print("Fetching unique source_files from chunks...")
    sources = fetch_all_source_files(supabase)
    print(f"  {len(sources)} unique (source_file, manufacturer, product_model) combinations\n")

    skipped = 0
    created = 0
    chunks_linked = 0
    errors: list[tuple[str, str]] = []

    for i, src in enumerate(sources, 1):
        sf = src["source_file"]
        mfr = src["manufacturer"] or "unknown"
        model = src["product_model"]
        n = src["count"]

        if sf in existing:
            skipped += 1
            if i % 100 == 0:
                print(f"  [{i}/{len(sources)}] skipped={skipped} created={created} linked={chunks_linked}")
            continue

        try:
            doc_id = create_document_row(supabase, sf, mfr, model, commit)
            if commit and doc_id:
                updated = update_chunks_document_id(supabase, sf, doc_id, commit)
                chunks_linked += updated
            else:
                # dry-run: just count what would be updated
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
            print(f"  [{i}/{len(sources)}] ERROR on {sf}: {e}")

    print("\n" + "=" * 70)
    print(f"Unique source_files:      {len(sources)}")
    print(f"  Skipped (already done): {skipped}")
    print(f"  Created (documents):    {created}")
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
