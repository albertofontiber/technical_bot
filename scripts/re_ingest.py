#!/usr/bin/env python3
"""
Re-ingestion script: clears existing chunks and re-runs the full pipeline
with improved table extraction (pdfplumber) and optional Claude Vision.

Usage:
    py -3.14 -X utf8 scripts/re_ingest.py --dry-run                    # Preview only
    py -3.14 -X utf8 scripts/re_ingest.py --dry-run --single <path>    # Single PDF preview
    py -3.14 -X utf8 scripts/re_ingest.py                              # Full re-ingestion
    py -3.14 -X utf8 scripts/re_ingest.py --use-vision                 # With Claude Vision fallback
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.ingest import ingest_all, ingest_single_pdf


def count_chunks() -> int:
    """Count existing chunks in Supabase."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Prefer": "count=exact",
    }
    resp = httpx.head(
        f"{SUPABASE_URL}/rest/v1/chunks",
        headers=headers,
        params={"select": "id"},
        timeout=30.0,
    )
    resp.raise_for_status()
    count_range = resp.headers.get("content-range", "")
    if "/" in count_range:
        total = count_range.split("/")[1]
        return int(total) if total != "*" else 0
    return 0


def delete_all_chunks():
    """Delete ALL chunks from Supabase. Use with caution."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Prefer": "return=minimal",
    }

    # Delete in batches to avoid timeouts
    deleted = 0
    while True:
        # Fetch a batch of IDs
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/chunks",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
            params={"select": "id", "limit": "500"},
            timeout=30.0,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break

        ids = [r["id"] for r in rows]
        for chunk_id in ids:
            resp = httpx.delete(
                f"{SUPABASE_URL}/rest/v1/chunks?id=eq.{chunk_id}",
                headers=headers,
                timeout=30.0,
            )
            resp.raise_for_status()
            deleted += 1

        print(f"  Deleted {deleted} chunks...")

    return deleted


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    use_vision = "--use-vision" in args
    single_mode = "--single" in args

    print("=" * 60)
    print("RE-INGESTION PIPELINE (pdfplumber + Vision)")
    print("=" * 60)

    if dry_run:
        print("MODE: DRY RUN (no uploads, no deletions)")
    else:
        print("MODE: FULL RE-INGESTION")
    if use_vision:
        print("Claude Vision: ENABLED")
    print()

    if single_mode:
        idx = args.index("--single")
        if idx + 1 >= len(args):
            print("Error: --single requires a PDF path argument")
            sys.exit(1)
        pdf_path = args[idx + 1]
        print(f"Processing single PDF: {pdf_path}")
        chunks = ingest_single_pdf(pdf_path, dry_run=dry_run, use_vision=use_vision)
        print(f"\nGenerated {len(chunks)} chunks")

        # Show chunks with table/vision enrichment
        for i, c in enumerate(chunks):
            has_table = "[TABLA EXTRAÍDA]" in c.content
            has_vision = "[CONTENIDO VISUAL]" in c.content
            markers = ""
            if has_table:
                markers += " [+TABLE]"
            if has_vision:
                markers += " [+VISION]"
            print(f"  [{i}] {c.content_type:15s} p.{c.start_page}-{c.end_page} "
                  f"({len(c.content):5d} chars){markers} | {c.section_title[:50]}")
        return

    # Full re-ingestion
    if not dry_run:
        existing = count_chunks()
        print(f"Existing chunks in Supabase: {existing}")

        if existing > 0:
            print(f"\nWARNING: About to DELETE all {existing} existing chunks!")
            confirm = input("Type 'YES' to confirm deletion: ")
            if confirm != "YES":
                print("Aborted.")
                sys.exit(0)

            print("\nDeleting existing chunks...")
            deleted = delete_all_chunks()
            print(f"Deleted {deleted} chunks\n")

    ingest_all(dry_run=dry_run, use_vision=use_vision)


if __name__ == "__main__":
    main()
