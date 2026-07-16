#!/usr/bin/env python3
"""Freeze five product-scoped corpus slices for a zero-model retrieval replay."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals/s114_five_product_corpus_slice_v1.json"
SELECT = (
    "id,content,context,source_file,page_number,section_title,section_path,"
    "product_model,manufacturer,document_id,extraction_sha256,chunk_index,language"
)
SCOPES = {
    "inspire": "*INSPIRE*",
    "asd535": "*ASD535*",
    "dxc": "DXc",
    "adw535": "*ADW535*",
    "ccd103": "*CCD-103*",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_KEY missing")
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    rows_by_id: dict[str, dict] = {}
    counts = {}
    requests = 0
    with httpx.Client(timeout=60.0) as client:
        for name, pattern in SCOPES.items():
            response = client.get(
                f"{url.rstrip('/')}/rest/v1/chunks_v2",
                headers=headers,
                params={
                    "select": SELECT,
                    "product_model": f"ilike.{pattern}",
                    "order": "id.asc",
                    "limit": "1000",
                },
            )
            requests += 1
            response.raise_for_status()
            rows = response.json()
            if len(rows) == 1000:
                raise RuntimeError(f"scope {name} reached the unpaginated safety cap")
            counts[name] = len(rows)
            for row in rows:
                rows_by_id[str(row["id"])] = row

    rows = sorted(rows_by_id.values(), key=lambda row: str(row["id"]))
    payload = {
        "instrument": "s114_five_product_corpus_slice_v1",
        "status": "read_only_frozen_local_replay_slice",
        "scope_filters": SCOPES,
        "scope_counts_before_dedup": counts,
        "unique_rows": len(rows),
        "rows": rows,
        "cost_receipt": {
            "database_get_requests": requests,
            "database_writes": 0,
            "model_calls": 0,
        },
        "limitations": [
            "This slice is a known-failure diagnostic cohort, not held-out release evidence.",
            "Production selectors do not receive QIDs, facts, expected values, or receipt IDs.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "scope_counts_before_dedup": counts,
        "unique_rows": len(rows),
        "cost_receipt": payload["cost_receipt"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
