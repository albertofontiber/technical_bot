#!/usr/bin/env python3
"""Delete chunks for source_files identified as pathologically duplicated.

The targets were surfaced by scripts/investigate_mega_docs.py: three docs whose
chunk counts are 3–25× higher than their unique-content counts, indicating a
pipeline bug (same table ingested many times). Keeping them inflates retriever
noise and biases ranking.

Safety:
  - Dry-run by default. --apply to execute.
  - Writes a rollback snapshot to logs/pathological_chunks_rollback_<ts>.json
    containing {id, page_number, content, manufacturer, category, product_model,
    source_file, document_id} BEFORE any DELETE. The snapshot is enough to
    INSERT the rows back (losing only the embedding — which we'd want to
    regenerate anyway given the duplication bug).
  - Does NOT touch the `documents` table. Document metadata stays; re-ingestion
    can reattach fresh chunks via document_id FK.
  - Idempotent: matches by source_file only. Running twice after apply is a no-op.

Usage:
    python scripts/delete_pathological_chunks.py              # dry run
    python scripts/delete_pathological_chunks.py --apply      # execute
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402


# source_files to delete (surfaced by investigate_mega_docs.py on 2026-04-17).
# Rationale captured in the commit message that follows.
TARGETS = [
    {
        "source_file": "D1058-1_NFXI-WS-WSF",
        "reason": "1,159 chunks vs 47 unique content hashes (24.7x duplication) "
                  "on a 2-page datasheet. Pipeline bug inflated same table ~80x.",
    },
    {
        "source_file": "D1056-1_NFXI-BS-BSF",
        "reason": "1,174 chunks vs 62 unique content hashes (18.9x duplication) "
                  "on a 2-page datasheet. Same pattern as D1058.",
    },
    {
        "source_file": "170020 21122011 TARJETAS IDIOMAS EXTINCION SUPRA REV A",
        "reason": "138 chunks on a 1-page UI-label reference doc with mojibake "
                  "('�������'). Low retrieval value + 3.5x duplication.",
    },
]


def fetch_chunks_for(sup, source_file: str) -> list[dict]:
    """Fetch all columns we'd need to reinsert, paginated over 1000-row chunks."""
    url = f"{sup.url}/rest/v1/chunks"
    out: list[dict] = []
    offset = 0
    # Grab enough columns to allow manual recovery. Exclude `embedding` —
    # if we ever re-insert, we'd want to regenerate it anyway.
    select = "id,source_file,page_number,content,manufacturer,category," \
             "product_model,document_id,section_title,content_type," \
             "protocol,doc_type,has_diagram,diagram_url,created_at"
    while True:
        r = sup.client.get(url, headers=sup.headers, params={
            "select": select,
            "source_file": f"eq.{source_file}",
            "order": "id",
            "limit": "1000",
            "offset": str(offset),
        })
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        out.extend(rows)
        if len(rows) < 1000:
            break
        offset += 1000
    return out


def delete_chunks_for(sup, source_file: str) -> int:
    """DELETE all chunks matching this source_file. Returns row count via
    Prefer: return=representation."""
    url = f"{sup.url}/rest/v1/chunks"
    headers = {**sup.headers, "Prefer": "return=representation"}
    r = sup.client.delete(
        url, headers=headers,
        params={"source_file": f"eq.{source_file}"},
    )
    r.raise_for_status()
    return len(r.json())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Execute DELETEs")
    args = ap.parse_args()

    sup = get_supabase()
    print(f"Mode: {'APPLY (DELETEs will execute)' if args.apply else 'DRY-RUN (no writes)'}")
    print()

    # Phase 1: build rollback snapshot
    print("Fetching chunks for rollback snapshot...")
    snapshot: list[dict] = []
    total = 0
    for t in TARGETS:
        sf = t["source_file"]
        chunks = fetch_chunks_for(sup, sf)
        n = len(chunks)
        total += n
        snapshot.append({
            "source_file": sf,
            "reason": t["reason"],
            "chunks": chunks,
        })
        print(f"  {sf[:60]:<60s}  {n:>5d} chunks")

    print()
    print(f"Total chunks to delete: {total}")
    if total == 0:
        print("Nothing to delete. Already clean.")
        return 0

    if not args.apply:
        print()
        print("DRY-RUN: no writes. Re-run with --apply to execute.")
        return 0

    # Phase 2: write rollback BEFORE any DELETE
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rollback_path = ROOT / f"logs/pathological_chunks_rollback_{ts}.json"
    rollback_path.parent.mkdir(parents=True, exist_ok=True)
    rollback_path.write_text(
        json.dumps({"timestamp_utc": ts, "total_chunks": total,
                    "entries": snapshot}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Rollback snapshot: {rollback_path.name}  "
          f"({rollback_path.stat().st_size / 1024:.0f} KB)")
    print()

    # Phase 3: delete
    print("Deleting...")
    t0 = time.time()
    total_deleted = 0
    errors = []
    for t in TARGETS:
        sf = t["source_file"]
        try:
            n = delete_chunks_for(sup, sf)
            total_deleted += n
            print(f"  {sf[:60]:<60s}  DELETED {n}")
        except Exception as e:
            errors.append((sf, str(e)))
            print(f"  {sf[:60]:<60s}  FAILED: {type(e).__name__}: {e}")

    elapsed = time.time() - t0
    print()
    print(f"Done in {elapsed:.1f}s. Deleted {total_deleted}/{total} chunks across "
          f"{len(TARGETS)-len(errors)}/{len(TARGETS)} docs.")
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for sf, msg in errors:
            print(f"  - {sf}: {msg}")
        print(f"\nRollback file: {rollback_path.name}")
        return 1

    print()
    print("documents rows left intact — re-ingestion can reattach fresh chunks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
