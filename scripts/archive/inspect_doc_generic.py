#!/usr/bin/env python3
"""Quick ad-hoc inspector: dumps first chunk + metadata for a given source_file.

Usage:
    python scripts/inspect_doc_generic.py <source_file>
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_doc_generic.py <source_file>")
        return 1
    sf = sys.argv[1]

    supabase = get_supabase()
    url = f"{supabase.url}/rest/v1/chunks"
    params = {
        "select": "id,page_number,content,category,product_model,manufacturer",
        "source_file": f"eq.{sf}",
        "order": "page_number.asc,id.asc",
        "limit": "1000",
    }
    resp = supabase.client.get(url, headers=supabase.headers, params=params)
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        print(f"No chunks for source_file='{sf}'")
        return 1

    n = len(rows)
    lengths = [len(r.get("content") or "") for r in rows]
    vision_count = sum(1 for r in rows if "[CONTENIDO VISUAL]" in (r.get("content") or ""))
    meta = rows[0]
    pages = sorted({r.get("page_number") for r in rows if r.get("page_number") is not None})

    print(f"source_file: {sf}")
    print(f"manufacturer: {meta.get('manufacturer')}")
    print(f"current category: {meta.get('category')}")
    print(f"product_model: {meta.get('product_model')}")
    print(f"chunks: {n}  |  pages: {min(pages)} → {max(pages)} (distinct: {len(pages)})")
    print(f"chunk length: min={min(lengths)} max={max(lengths)} avg={sum(lengths)//n}")
    print(f"chunks with [CONTENIDO VISUAL]: {vision_count}/{n}")
    print()
    print("--- First chunk (truncated 1200 chars) ---")
    print((rows[0].get("content") or "")[:1200])
    print()
    if n > 2:
        print("--- Middle chunk (truncated 1000 chars) ---")
        mid = rows[n // 2]
        print(f"[page {mid.get('page_number')}]")
        print((mid.get("content") or "")[:1000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
