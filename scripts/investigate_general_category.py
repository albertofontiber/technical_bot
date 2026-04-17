#!/usr/bin/env python3
"""Investigate documents/chunks with category='General' (fallback value).

These are likely PDFs where category detection failed at ingest time.
This script reports:
  - How many distinct source_files have General chunks
  - The filenames + manufacturer + model for each
  - Whether ALL chunks of that file are General, or only some
  - Total chunk count per file

No writes — read-only investigation.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402


def fetch_paginated(supabase, table: str, params: dict, page_size: int = 1000) -> list[dict]:
    """Paginate through PostgREST GET. Avoids the 1000-row default ceiling."""
    out: list[dict] = []
    offset = 0
    while True:
        page_params = {**params, "limit": str(page_size), "offset": str(offset)}
        url = f"{supabase.url}/rest/v1/{table}"
        resp = supabase.client.get(url, headers=supabase.headers, params=page_params)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        out.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
        if offset > 1_000_000:
            break
    return out


def main() -> int:
    supabase = get_supabase()

    print("Fetching all chunks where category='General'...")
    general_chunks = fetch_paginated(
        supabase,
        "chunks",
        {
            "select": "source_file,manufacturer,product_model,category",
            "category": "eq.General",
            "order": "id",
        },
    )
    print(f"  {len(general_chunks):,} chunks with category='General'")
    print()

    # Group by source_file
    by_file: dict[str, dict] = defaultdict(lambda: {
        "general_count": 0,
        "manufacturer": None,
        "product_model": None,
    })
    for c in general_chunks:
        sf = c["source_file"]
        by_file[sf]["general_count"] += 1
        by_file[sf]["manufacturer"] = c.get("manufacturer")
        by_file[sf]["product_model"] = c.get("product_model")

    print(f"Unique source_files with General chunks: {len(by_file)}")
    print()

    # For each, get total chunk count to see if it's "all General" or "some General"
    print("Fetching total chunk counts per file (this may take a moment)...")
    for sf in by_file.keys():
        url = f"{supabase.url}/rest/v1/chunks"
        headers = {**supabase.headers, "Prefer": "count=exact"}
        params = {
            "select": "id",
            "source_file": f"eq.{sf}",
            "limit": "0",
        }
        resp = supabase.client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        cr = resp.headers.get("content-range", "")
        total = int(cr.split("/")[1]) if "/" in cr else 0
        by_file[sf]["total_count"] = total

    print()
    print("=" * 100)
    print(f"{'source_file':<60s} {'mfr':<10s} {'model':<15s} {'gen':>5s} {'tot':>5s} {'%gen':>5s}")
    print("=" * 100)

    sorted_files = sorted(by_file.items(), key=lambda x: -x[1]["general_count"])
    for sf, info in sorted_files:
        gen = info["general_count"]
        tot = info["total_count"]
        pct = (gen / tot * 100) if tot else 0
        mfr = (info["manufacturer"] or "?")[:10]
        model = (info["product_model"] or "?")[:15]
        sf_short = sf if len(sf) <= 60 else sf[:57] + "..."
        print(f"{sf_short:<60s} {mfr:<10s} {model:<15s} {gen:>5d} {tot:>5d} {pct:>4.0f}%")

    print()
    print(f"Total: {len(by_file)} unique source_files with General chunks "
          f"({len(general_chunks):,} chunks total)")

    # How many are "all General" vs "partial General"
    all_general = [sf for sf, info in by_file.items()
                   if info["general_count"] == info["total_count"]]
    partial_general = [sf for sf, info in by_file.items()
                       if info["general_count"] < info["total_count"]]
    print(f"  All chunks are General:  {len(all_general)} files")
    print(f"  Some chunks are General: {len(partial_general)} files (mixed)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
