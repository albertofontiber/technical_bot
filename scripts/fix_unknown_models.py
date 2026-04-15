#!/usr/bin/env python3
"""
Fix product_model='unknown' chunks by extracting model from source_file name.
Maps known filenames to their correct product models.

Usage:
    py -3.14 -X utf8 scripts/fix_unknown_models.py --dry-run
    py -3.14 -X utf8 scripts/fix_unknown_models.py
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

HEADERS_READ = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}
HEADERS_WRITE = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Manual mapping: source_file substring → product_model
# Covers all 44 files with unknown models
FILE_TO_MODEL = {
    # Detección de gas
    "Manual-de-Usuario-S3-2": "S3-T2",
    "Manual-de-Usuario-CS4": "CS4",
    "Manual-de-Usuario-MS3RS485": "MS3-RS485",

    # PA/VA Evacuación por voz
    "ONE500S01-MU": "ONE-500",
    "ONE500": "ONE-500",
    "NEO8060S02-MU": "NEO-8060",
    "NEO8060": "NEO-8060",
    "LDA BA Series": "BA-Series",
    "ATxxxS0x-MU": "AT-Series",
    "AT Series": "AT-Series",
    "LDARCD21RS03": "RCD-21",
    "VAP1S0x-MU": "VAP-1",
    "VAP rev": "VAP-1",
    "MPS8ZS02": "MPS-8",
    "MPS rev": "MPS-8",
    "A1S02-MU": "A-1",
    "Manual de usuario A-1": "A-1",
    "VCC-64": "VCC-64",
    "ZES-22": "ZES-22",
    "ZES22S02": "ZES-22",

    # Detección convencional
    "Tarjeta de Pasarela": "TPG-100",
    "PCD-100WP": "PCD-100WP",
    "PAD-10 ES FR GB IT (x8)": "PAD-10",
    "TCD-100 Tarjeta comunicadora": "TCD-100",
    "TCD-106 kit": "TCD-106",
    "zocalo con relé Z-200-R": "Z-200-R",
    "Z-200-R": "Z-200-R",
    "TMD-100": "TMD-100",
    "TRD-100 TSD-100": "TRD-100",
    "SFD-220": "SFD-220",

    # Detección analógica
    "CAD150R Instalacion": "CAD-150R",
    "PAD-20": "PAD-20",
    "PAD-10A ES FR GB IT": "PAD-10A",
    "Buzzer Analogico PAD-10A": "PAD-10A",
    "TED-151-CL": "TED-151-CL",

    # Detectores especiales
    "PY X-M-05": "PY-X-M",
    "PY X-S-05": "PY-X-S",
    "PYX-L-15": "PY-X-L",
    "DS10_Installation": "DS-10",
    "40-40r-single-ir": "40/40R",
    "40-40-air-shield": "40/40-AIR",
    "SGMCB200": "SGMCB200",
    "conduct detector": "CONDUCT",
    "210-Series_CZ": "210-CZ",
    "SGCWE100": "SGCWE100",
    "LocatorPlus": "LocatorPlus",
    "SGCP100 RNG": "SGCP100",
    "SGCP100-IS": "SGCP100-IS",
    "SGFI200-S": "SGFI200-S",

    # Accesorios
    "TUL500": "TUL-500",

    # Sistema de extinción
    "REXD-103": "REXD-103",
}


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("FIX UNKNOWN PRODUCT MODELS")
    if dry_run:
        print("[DRY RUN]")
    print("=" * 60)

    # Fetch unknown chunks
    print("\n1. Fetching unknown chunks...")
    all_chunks = []
    offset = 0
    while True:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/chunks",
            headers=HEADERS_READ,
            params={
                "product_model": "eq.unknown",
                "select": "id,source_file",
                "offset": str(offset),
                "limit": "500",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_chunks.extend(batch)
        offset += len(batch)
    print(f"   Total unknown: {len(all_chunks)}")

    # Match against FILE_TO_MODEL
    fixes = []
    unmatched_files = {}
    for chunk in all_chunks:
        source = chunk["source_file"]
        matched_model = None
        for pattern, model in FILE_TO_MODEL.items():
            if pattern in source:
                matched_model = model
                break
        if matched_model:
            fixes.append({"id": chunk["id"], "model": matched_model, "source": source})
        else:
            unmatched_files[source] = unmatched_files.get(source, 0) + 1

    print(f"   Can fix: {len(fixes)}")
    print(f"   Still unmatched: {len(all_chunks) - len(fixes)}")

    # Show fix summary by model
    fix_summary = {}
    for f in fixes:
        fix_summary[f["model"]] = fix_summary.get(f["model"], 0) + 1
    print("\n   Fixes by model:")
    for model, count in sorted(fix_summary.items()):
        print(f"     {model:15s}: {count:4d}")

    if unmatched_files:
        print(f"\n   Still unmatched files ({len(unmatched_files)}):")
        for f, count in sorted(unmatched_files.items(), key=lambda x: -x[1]):
            print(f"     {count:4d} | {f[:70]}")

    if dry_run:
        print(f"\n[DRY RUN] Would fix {len(fixes)} chunks.")
        return

    # Apply fixes
    print(f"\n2. Applying {len(fixes)} fixes...")
    errors = 0
    for i, fix in enumerate(fixes):
        try:
            resp = httpx.patch(
                f"{SUPABASE_URL}/rest/v1/chunks?id=eq.{fix['id']}",
                headers=HEADERS_WRITE,
                json={"product_model": fix["model"]},
                timeout=15.0,
            )
            resp.raise_for_status()
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"   Error: {e}")
        if (i + 1) % 500 == 0:
            print(f"   Updated {i + 1} / {len(fixes)}")

    print(f"\n{'=' * 60}")
    print(f"FIXES COMPLETE")
    print(f"{'=' * 60}")
    print(f"Fixed: {len(fixes) - errors} / {len(fixes)}")
    if errors:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
