#!/usr/bin/env python3
"""Quick diagnostic: inspect chunks of source_file '15584' to determine
whether the content came from native PDF text or from Claude Vision.

Signals:
- Presence of '[CONTENIDO VISUAL]' marker → Vision was used
- Presence of '[TABLA EXTRAIDA]' marker → pdfplumber table extraction
- Avg content length per chunk
- First 500 chars of a middle chunk for eyeballing
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
    supabase = get_supabase()
    url = f"{supabase.url}/rest/v1/chunks"

    # 1. Find any source_file that starts with '15584'
    params = {
        "select": "source_file",
        "source_file": "like.15584*",
        "limit": "5",
    }
    resp = supabase.client.get(url, headers=supabase.headers, params=params)
    resp.raise_for_status()
    matches = {r["source_file"] for r in resp.json()}
    if not matches:
        print("No source_file starts with '15584'. Trying exact '15584'...")
        return 1
    print(f"Matching source_files: {matches}")
    sf = sorted(matches)[0]
    print(f"Inspecting: {sf}\n")

    # 2. Fetch all chunks for this source_file
    params = {
        "select": "id,page_number,content",
        "source_file": f"eq.{sf}",
        "order": "page_number.asc,id.asc",
        "limit": "1000",
    }
    resp = supabase.client.get(url, headers=supabase.headers, params=params)
    resp.raise_for_status()
    rows = resp.json()
    n = len(rows)
    if n == 0:
        print("No chunks found")
        return 1

    lengths = [len(r.get("content") or "") for r in rows]
    vision_count = sum(1 for r in rows if "[CONTENIDO VISUAL]" in (r.get("content") or ""))
    table_count = sum(1 for r in rows if "[TABLA EXTRAÍDA]" in (r.get("content") or "")
                      or "[TABLA EXTRAIDA]" in (r.get("content") or ""))

    print(f"Total chunks: {n}")
    print(f"Pages covered: {min(r.get('page_number') or 0 for r in rows)} → "
          f"{max(r.get('page_number') or 0 for r in rows)}")
    print(f"Chunk length — min={min(lengths)}, max={max(lengths)}, "
          f"avg={sum(lengths)/n:.0f} chars")
    print(f"Chunks with [CONTENIDO VISUAL] marker: {vision_count}/{n}")
    print(f"Chunks with [TABLA EXTRAÍDA] marker:   {table_count}/{n}")
    print()

    # 3. Dump first 500 chars of a middle chunk
    mid = rows[n // 2]
    content = mid.get("content") or ""
    print(f"--- Middle chunk (id={mid.get('id')}, page={mid.get('page_number')}) ---")
    print(content[:600])
    print("..." if len(content) > 600 else "")
    print()

    # 4. Verdict
    if vision_count > 0:
        pct = 100 * vision_count / n
        print(f"VERDICT: Vision was used on {pct:.0f}% of chunks — "
              "scanned doc extracted via Claude Vision.")
    elif sum(lengths) / n < 200:
        print("VERDICT: No Vision markers AND avg chunk length is short — "
              "likely native text layer with poor extraction.")
    else:
        print("VERDICT: No Vision markers but rich content — "
              "document has a proper native text layer (not fully scanned).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
