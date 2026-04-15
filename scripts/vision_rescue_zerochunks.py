#!/usr/bin/env python3
"""Vision rescue pass: force Claude Vision on every page of zero-chunk PDFs.

Reads _dry_run_results.json from a folder, finds the PDFs that produced 0
chunks (scanned, no extractable text), and re-parses them forcing Vision on
EVERY page — bypassing the has_large_images heuristic that won't fire on
fully-rasterized scans.

Writes:
  - _vision_rescue_results.json  per-file outcome (n_chunks, pages, cost)

Usage:
    python scripts/vision_rescue_zerochunks.py Manuales_Notifier_Privado Notifier
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.chunker import chunk_document  # noqa: E402
from src.ingestion.language_filter import filter_spanish_pages  # noqa: E402
from src.ingestion.pdf_parser import enrich_with_vision, parse_pdf  # noqa: E402

# Sonnet Vision pricing (per MTok)
PRICE_IN = 3.0
PRICE_OUT = 15.0
# Approximate: one 200-dpi page ≈ 1568 image tokens
TOKENS_PER_PAGE_IMG = 1600


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/vision_rescue_zerochunks.py <dir> <manufacturer>")
        return 2
    folder = ROOT / sys.argv[1]
    results_path = folder / "_dry_run_results.json"
    if not results_path.exists():
        print(f"[!] Missing {results_path}")
        return 2
    dry = json.loads(results_path.read_text(encoding="utf-8"))
    zero = [r for r in dry if "error" not in r and r.get("n_chunks", 0) == 0]
    total_pages = sum(r.get("pages", 0) for r in zero)
    print(f"Zero-chunk PDFs: {len(zero)}  total pages: {total_pages}")
    est_cost = total_pages * TOKENS_PER_PAGE_IMG / 1_000_000 * PRICE_IN + total_pages * 500 / 1_000_000 * PRICE_OUT
    print(f"Estimated cost: ~${est_cost:.2f}\n")

    results: list[dict] = []
    t0 = time.time()
    for i, r in enumerate(zero, 1):
        fname = r["file"]
        pdf_path = folder / fname
        n_pages = r.get("pages", 0) or 0
        print(f"  [{i:2d}/{len(zero)}] {fname}  ({n_pages}p)", flush=True)
        try:
            parsed = parse_pdf(pdf_path)
            # Force Vision on ALL pages
            all_page_nums = [p.page_number for p in parsed.pages]
            enriched = enrich_with_vision(parsed, page_numbers=all_page_nums)
            spanish_pages = filter_spanish_pages(parsed) or parsed.pages
            chunks = chunk_document(parsed, spanish_pages)
            n_ch = len(chunks)
            mdl = chunks[0].product_model if chunks else "unknown"
            cat = chunks[0].category if chunks else "unknown"
            print(f"           enriched={enriched}  chunks={n_ch}  model={mdl}  cat={cat}")
            results.append({
                "file": fname,
                "pages": n_pages,
                "vision_pages": enriched,
                "n_chunks": n_ch,
                "product_model": mdl,
                "category": cat,
            })
        except Exception as e:
            print(f"           ERROR: {type(e).__name__}: {e}")
            results.append({"file": fname, "error": f"{type(e).__name__}: {e}"})
        # Periodic checkpoint
        if i % 5 == 0:
            (folder / "_vision_rescue_results.json").write_text(
                json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    (folder / "_vision_rescue_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    ok = [r for r in results if "error" not in r and r.get("n_chunks", 0) > 0]
    still_zero = [r for r in results if "error" not in r and r.get("n_chunks", 0) == 0]
    errors = [r for r in results if "error" in r]
    recovered_chunks = sum(r["n_chunks"] for r in ok)

    print("\n" + "=" * 70)
    print(f"Processed:        {len(results)}")
    print(f"  Recovered:      {len(ok)}  ({recovered_chunks:,} chunks)")
    print(f"  Still zero:     {len(still_zero)}")
    print(f"  Errors:         {len(errors)}")
    print(f"Elapsed:          {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
