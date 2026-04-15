#!/usr/bin/env python3
"""Dry-run de parsing + chunking para cualquier carpeta de manuales.

Procesa todos los PDFs de una carpeta sin generar embeddings ni tocar Supabase.
Imprime un informe agregado con:
  - Archivos con 0 chunks (parse roto / escaneado)
  - Archivos con product_model == 'unknown'  (→ necesitan override)
  - Archivos con manufacturer != expected
  - Distribución de categorías (detecta también 'unknown')
  - Total de chunks estimados

Uso:
    python scripts/dry_run_parse.py <dir> <manufacturer>
    python scripts/dry_run_parse.py Manuales_Notifier_Privado Notifier
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingestion.chunker import chunk_document  # noqa: E402
from src.ingestion.pdf_parser import parse_pdf  # noqa: E402
from src.ingestion.language_filter import filter_spanish_pages  # noqa: E402


def process_one(pdf_path: Path) -> dict:
    t0 = time.time()
    try:
        parsed = parse_pdf(pdf_path)
        spanish_pages = filter_spanish_pages(parsed) or parsed.pages
        chunks = chunk_document(parsed, spanish_pages)
    except Exception as e:
        return {
            "file": pdf_path.name,
            "error": f"{type(e).__name__}: {e}",
            "n_chunks": 0,
            "elapsed": time.time() - t0,
        }
    if not chunks:
        return {
            "file": pdf_path.name,
            "n_chunks": 0,
            "pages": parsed.total_pages,
            "elapsed": time.time() - t0,
        }
    c0 = chunks[0]
    return {
        "file": pdf_path.name,
        "n_chunks": len(chunks),
        "pages": parsed.total_pages,
        "spanish_pages": len(spanish_pages),
        "manufacturer": c0.manufacturer,
        "product_model": c0.product_model,
        "category": c0.category,
        "elapsed": time.time() - t0,
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/dry_run_parse.py <dir> <manufacturer>")
        return 2
    folder = ROOT / sys.argv[1]
    expected_mfr = sys.argv[2]
    pdfs = sorted(folder.glob("*.pdf"))
    print(f"=== Dry-run {expected_mfr}: {len(pdfs)} PDFs in {folder.name}/ ===\n")

    results: list[dict] = []
    for i, pdf in enumerate(pdfs, 1):
        r = process_one(pdf)
        results.append(r)
        if "error" in r:
            print(f"  [{i:3d}/{len(pdfs)}] ERROR ({r['elapsed']:.1f}s): {r['file']}")
            print(f"           {r['error']}")
            continue
        if r["n_chunks"] == 0:
            print(f"  [{i:3d}/{len(pdfs)}] ZERO-CHUNKS ({r['elapsed']:.1f}s): {r['file']}")
            continue
        mfr = r["manufacturer"]
        mdl = r["product_model"]
        cat = r["category"]
        flag = ""
        if mfr != expected_mfr:
            flag += " [!MFR]"
        if mdl == "unknown":
            flag += " [!MODEL]"
        if cat == "unknown" or cat is None:
            flag += " [!CAT]"
        print(
            f"  [{i:3d}/{len(pdfs)}] OK ({r['elapsed']:.1f}s, {r['n_chunks']:4d} ch){flag} "
            f"{mfr:10s} | {str(mdl)[:25]:25s} | {str(cat)[:30]}"
        )

    # ===== Informe =====
    print("\n" + "=" * 78)
    print("INFORME AGREGADO")
    print("=" * 78)

    ok = [r for r in results if "error" not in r and r["n_chunks"] > 0]
    errors = [r for r in results if "error" in r]
    zero_chunks = [r for r in results if "error" not in r and r["n_chunks"] == 0]

    print(f"\nArchivos procesados:     {len(results)}")
    print(f"  OK:                    {len(ok)}")
    print(f"  Errores de parse:      {len(errors)}")
    print(f"  Zero-chunks:           {len(zero_chunks)}")

    if errors:
        print("\n[!] Errores de parse:")
        for r in errors[:20]:
            print(f"    - {r['file']}: {r['error'][:120]}")
        if len(errors) > 20:
            print(f"    ... y {len(errors)-20} más")

    if zero_chunks:
        print(f"\n[!] Zero-chunks ({len(zero_chunks)}) — candidatos a re-parsear con Vision:")
        for r in zero_chunks[:20]:
            print(f"    - {r['file']} ({r.get('pages','?')} páginas)")
        if len(zero_chunks) > 20:
            print(f"    ... y {len(zero_chunks)-20} más")

    total_chunks = sum(r["n_chunks"] for r in ok)
    print(f"\nTotal chunks estimados:  {total_chunks:,}")

    bad_mfr = [r for r in ok if r["manufacturer"] != expected_mfr]
    if bad_mfr:
        print(f"\n[!] {len(bad_mfr)} archivos con manufacturer != '{expected_mfr}':")
        mfr_counter = Counter(r["manufacturer"] for r in bad_mfr)
        for m, n in mfr_counter.most_common():
            print(f"    {n:4d}  → {m}")
        for r in bad_mfr[:10]:
            print(f"      - {r['file']} → {r['manufacturer']}")
    else:
        print(f"\n[OK] Todos detectados como {expected_mfr}")

    unknown_models = [r for r in ok if r["product_model"] == "unknown"]
    print(f"\n[{'!' if unknown_models else 'OK'}] product_model=unknown: {len(unknown_models)} / {len(ok)}")
    if unknown_models:
        print("  (necesitan override o mejor detección por keyword)")
        for r in unknown_models[:30]:
            print(f"    - {r['file']}")
        if len(unknown_models) > 30:
            print(f"    ... y {len(unknown_models)-30} más")

    unknown_cats = [r for r in ok if r["category"] in (None, "unknown")]
    print(f"\n[{'!' if unknown_cats else 'OK'}] category=unknown: {len(unknown_cats)} / {len(ok)}")
    if unknown_cats:
        for r in unknown_cats[:30]:
            print(f"    - {r['file']}")
        if len(unknown_cats) > 30:
            print(f"    ... y {len(unknown_cats)-30} más")

    cats = Counter(r["category"] for r in ok)
    print("\nDistribución de categorías:")
    for c, n in cats.most_common():
        print(f"  {n:4d}  {c}")

    # Dump full results to JSON for downstream processing
    out_path = folder / "_dry_run_results.json"
    out_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nFull results JSON: {out_path}")

    elapsed = sum(r["elapsed"] for r in results)
    print(f"\nTiempo total dry-run: {elapsed:.1f}s")
    print(f"Estimación ingesta real (+embeddings): ~{elapsed + total_chunks*0.05:.0f}s")

    critical = len(errors)
    return 1 if critical > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
