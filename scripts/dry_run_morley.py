#!/usr/bin/env python3
"""Dry-run de parsing + chunking para los manuales Morley.

Procesa los 87 PDFs de Manuales_Morley/ sin generar embeddings ni tocar
Supabase. Al final imprime un informe agregado que detecta:
  - Archivos con 0 chunks (parse roto)
  - Archivos con product_model == 'unknown'
  - Archivos con manufacturer != 'Morley' (falla de detección)
  - Distribución de categorías
  - Total de chunks estimado para la ingesta real

Uso:
    python scripts/dry_run_morley.py
    python scripts/dry_run_morley.py --fast   # parse ligero sin tablas/vision
"""
from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingestion.chunker import chunk_document  # noqa: E402
from src.ingestion.pdf_parser import parse_pdf  # noqa: E402
from src.ingestion.language_filter import filter_spanish_pages  # noqa: E402

MORLEY_DIR = ROOT / "Manuales_Morley"


def process_one(pdf_path: Path) -> dict:
    """Parse + chunk un PDF, devuelve stats."""
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
    pdfs = sorted(MORLEY_DIR.glob("*.pdf"))
    print(f"=== Dry-run Morley: {len(pdfs)} PDFs ===\n")

    results: list[dict] = []
    for i, pdf in enumerate(pdfs, 1):
        r = process_one(pdf)
        results.append(r)
        if "error" in r:
            print(f"  [{i:2d}/{len(pdfs)}] ERROR ({r['elapsed']:.1f}s): {r['file']}")
            print(f"           {r['error']}")
            continue
        if r["n_chunks"] == 0:
            print(f"  [{i:2d}/{len(pdfs)}] ZERO-CHUNKS ({r['elapsed']:.1f}s): {r['file']}")
            continue
        print(
            f"  [{i:2d}/{len(pdfs)}] OK ({r['elapsed']:.1f}s, {r['n_chunks']:4d} chunks) "
            f"{r['manufacturer']:10s} | {r['product_model']:25s} | {r['category']}"
        )

    # ===== Informe agregado =====
    print("\n" + "=" * 70)
    print("INFORME AGREGADO")
    print("=" * 70)

    ok = [r for r in results if "error" not in r and r["n_chunks"] > 0]
    errors = [r for r in results if "error" in r]
    zero_chunks = [r for r in results if "error" not in r and r["n_chunks"] == 0]

    print(f"\nArchivos procesados:   {len(results)}")
    print(f"  OK:                  {len(ok)}")
    print(f"  Errores de parse:    {len(errors)}")
    print(f"  Zero-chunks:         {len(zero_chunks)}")

    if errors:
        print("\n[!] Errores de parse:")
        for r in errors:
            print(f"    - {r['file']}: {r['error']}")

    if zero_chunks:
        print("\n[!] Zero-chunks (no se generó contenido):")
        for r in zero_chunks:
            print(f"    - {r['file']} ({r.get('pages', '?')} páginas)")

    total_chunks = sum(r["n_chunks"] for r in ok)
    print(f"\nTotal chunks estimados: {total_chunks:,}")

    # Manufacturer check
    bad_mfr = [r for r in ok if r["manufacturer"] != "Morley"]
    if bad_mfr:
        print(f"\n[!] {len(bad_mfr)} archivos con manufacturer != 'Morley':")
        for r in bad_mfr:
            print(f"    - {r['file']}: {r['manufacturer']}")
    else:
        print("\n[OK] Todos los archivos detectados como Morley")

    # Model check
    unknown_models = [r for r in ok if r["product_model"] == "unknown"]
    if unknown_models:
        print(f"\n[!] {len(unknown_models)} archivos con product_model='unknown':")
        for r in unknown_models:
            print(f"    - {r['file']}")
    else:
        print("[OK] Todos los archivos con product_model conocido")

    # Category distribution
    cats = Counter(r["category"] for r in ok)
    print("\nDistribución de categorías:")
    for c, n in cats.most_common():
        print(f"  {n:3d}  {c}")

    # Top chunks
    top = sorted(ok, key=lambda r: r["n_chunks"], reverse=True)[:5]
    print("\nTop 5 archivos por nº de chunks:")
    for r in top:
        print(f"  {r['n_chunks']:4d}  {r['file']}")

    # Bottom chunks (excluding zero)
    bot = sorted([r for r in ok if r["n_chunks"] < 20], key=lambda r: r["n_chunks"])[:10]
    if bot:
        print("\nArchivos con <20 chunks (revisar si parsing está OK):")
        for r in bot:
            print(f"  {r['n_chunks']:4d}  {r['file']}")

    elapsed = sum(r["elapsed"] for r in results)
    print(f"\nTiempo total dry-run: {elapsed:.1f}s")
    print(f"Estimación ingesta real (+embeddings): ~{elapsed + total_chunks*0.05:.0f}s")

    # Exit code: fallo si hay errores críticos
    critical = len(errors) + len(zero_chunks) + len(bad_mfr)
    return 1 if critical > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
