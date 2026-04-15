#!/usr/bin/env python3
"""Reclassify 23 Morley PDFs currently in DB as manufacturer='Notifier'.

These PDFs were ingested historically when Morley wasn't distinguished
from the Notifier parent brand. We UPDATE the existing chunks (manufacturer
+ product_model + category) instead of re-ingesting to avoid paying for
embeddings again — the content is identical, only the metadata was wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingestion.chunker import (  # noqa: E402
    MORLEY_SOURCE_FILE_TO_CATEGORY,
    MORLEY_SOURCE_FILE_TO_MODEL,
    detect_product_model,
)
from src.ingestion.supabase_client import get_supabase  # noqa: E402


BATCH_SIZE = 100  # rows per UPDATE — small enough to stay under statement_timeout
                  # with HNSW MVCC reindex overhead


def _fetch_chunk_ids(sb, stem: str) -> list[str]:
    """Paginate through chunks for this source_file and collect their UUIDs."""
    ids: list[str] = []
    offset = 0
    page = 1000
    while True:
        h = {
            "apikey": sb.service_key,
            "Authorization": f"Bearer {sb.service_key}",
            "Range-Unit": "items",
            "Range": f"{offset}-{offset + page - 1}",
        }
        r = sb.client.get(
            f"{sb.url}/rest/v1/chunks",
            headers=h,
            params={"source_file": f"eq.{stem}", "select": "id"},
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        ids.extend(row["id"] for row in data)
        if len(data) < page:
            break
        offset += page
    return ids


def _patch_batch(sb, ids: list[str], patch: dict) -> None:
    """PATCH a batch of rows by id=in.(...). Uses return=minimal."""
    import time
    headers = {
        "apikey": sb.service_key,
        "Authorization": f"Bearer {sb.service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    id_list = ",".join(ids)
    last_exc = None
    for attempt in range(4):
        try:
            resp = sb.client.patch(
                f"{sb.url}/rest/v1/chunks",
                headers=headers,
                params={"id": f"in.({id_list})"},
                json=patch,
                timeout=120.0,
            )
            if resp.status_code in (500, 502, 503, 504):
                last_exc = Exception(f"{resp.status_code}: {resp.text[:150]}")
                if attempt < 3:
                    time.sleep(2.0 * (2 ** attempt))
                    continue
            resp.raise_for_status()
            return
        except Exception as e:
            last_exc = e
            if attempt < 3:
                time.sleep(2.0 * (2 ** attempt))
                continue
            raise last_exc from None


def reclassify_file(sb, stem: str) -> tuple[int, dict]:
    """UPDATE all chunks with source_file=stem to Morley + correct model/category.

    Uses id-batched UPDATEs to stay under Postgres statement_timeout when
    the HNSW index on `embedding` forces a reindex on every row rewrite.
    """
    model = detect_product_model(text="", filename=f"{stem}.pdf", manufacturer="Morley")
    category = MORLEY_SOURCE_FILE_TO_CATEGORY.get(stem)
    if not category:
        raise ValueError(f"No category override for {stem!r}")

    patch = {
        "manufacturer": "Morley",
        "product_model": model,
        "category": category,
    }

    ids = _fetch_chunk_ids(sb, stem)
    if not ids:
        return 0, patch

    for i in range(0, len(ids), BATCH_SIZE):
        _patch_batch(sb, ids[i:i + BATCH_SIZE], patch)

    return len(ids), patch


# Files that were reported as SKIPPED in the ingest log — their chunks already
# exist in DB but with manufacturer='Notifier'.
TARGETS = [
    "ASD Cold Environments_SP",
    "ASD Harsh Environments_SP",
    "D391 Issue 3 WR2001 ",
    "Enlace entre TG",
    "HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr",
    "HLSI-MA-192_05 Guia Rapida UCIP GPRS_SP",
    "HLSI-MA-192_05 Quick Start Guide UCIP GPRS_GB",
    "HLSI-MN-103I_RP1r-Supra_lr",
    "HLSI-MN-103_RP1r-Supra_lr",
    "HLSI-MN-192_UCIP",
    "HLSI-MN-963_POL-200-TS",
    "HSR-E24_Multi",
    "HSR-INT24_Multi",
    "I56-1756-000_400 Series Bases",
    "I56-2006-004 MI-DMMI_DMM2I_D2ICMO",
    "I56-6574-005_ES -HS Stand Alone FAAST LT-200 QIG",
    "I56-6575-005_ES FAAST LT-200 Loop QIG",
    "IRK-2E",
    "LEER PRIMERO_MADT951_10",
    "PSU User Manual_MLT LNG",
    "TG-Honeywell_Usuario",
    "Tg-Honeywell_Introduccion",
    "Tg-Honeywell_Tecnico",
]


def main() -> int:
    sb = get_supabase()
    print(f"Reclassifying {len(TARGETS)} files Notifier -> Morley")
    print("=" * 70)
    total_updated = 0
    errors = 0
    for stem in TARGETS:
        try:
            n, patch = reclassify_file(sb, stem)
            if n == 0:
                print(f"  [WARN]  0 rows affected: {stem}")
                continue
            total_updated += n
            print(f"  [OK]    {n:5d} rows  model={patch['product_model']:22s}  cat={patch['category']:25s}  {stem}")
        except Exception as e:
            errors += 1
            print(f"  [FAIL]  {stem}: {type(e).__name__}: {e}")

    print("=" * 70)
    print(f"Total rows updated: {total_updated}")
    print(f"Errors:             {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
