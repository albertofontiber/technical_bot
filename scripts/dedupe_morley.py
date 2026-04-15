#!/usr/bin/env python3
"""Remove duplicate Morley chunks left behind by the fallback row-by-row
insert that triggered on batch-500 failures during initial ingestion.

Duplicate key: (source_file, page_number, content_md5). For each group of
duplicates, we keep the first row and delete the rest in id-batched calls.
"""
from __future__ import annotations

import hashlib
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingestion.supabase_client import get_supabase  # noqa: E402

DELETE_BATCH = 100


def fetch_all_morley_rows(sb) -> list[dict]:
    h = {"apikey": sb.service_key, "Authorization": f"Bearer {sb.service_key}"}
    rows = []
    offset = 0
    while True:
        hh = {**h, "Range-Unit": "items", "Range": f"{offset}-{offset+999}"}
        r = sb.client.get(
            f"{sb.url}/rest/v1/chunks",
            headers=hh,
            params={
                "manufacturer": "eq.Morley",
                "select": "id,source_file,page_number,content",
            },
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        rows.extend(data)
        if len(data) < 1000:
            break
        offset += 1000
    return rows


def delete_ids(sb, ids: list[str]) -> None:
    h = {
        "apikey": sb.service_key,
        "Authorization": f"Bearer {sb.service_key}",
        "Prefer": "return=minimal",
    }
    for attempt in range(4):
        try:
            resp = sb.client.delete(
                f"{sb.url}/rest/v1/chunks",
                headers=h,
                params={"id": f"in.({','.join(ids)})"},
                timeout=120.0,
            )
            if resp.status_code in (500, 502, 503, 504):
                if attempt < 3:
                    time.sleep(2.0 * (2 ** attempt))
                    continue
            resp.raise_for_status()
            return
        except Exception:
            if attempt < 3:
                time.sleep(2.0 * (2 ** attempt))
                continue
            raise


def main() -> int:
    sb = get_supabase()
    print("Fetching all Morley chunks...")
    rows = fetch_all_morley_rows(sb)
    print(f"  {len(rows)} rows fetched")

    groups: dict[tuple, list[str]] = defaultdict(list)
    for row in rows:
        key = (
            row["source_file"],
            row["page_number"],
            hashlib.md5(row["content"].encode()).hexdigest(),
        )
        groups[key].append(row["id"])

    # For each duplicate group, delete all but the first id
    to_delete: list[str] = []
    for ids in groups.values():
        if len(ids) > 1:
            to_delete.extend(ids[1:])

    print(f"Duplicate groups: {sum(1 for v in groups.values() if len(v) > 1)}")
    print(f"IDs to delete:    {len(to_delete)}")

    if not to_delete:
        print("Nothing to delete.")
        return 0

    for i in range(0, len(to_delete), DELETE_BATCH):
        batch = to_delete[i:i + DELETE_BATCH]
        delete_ids(sb, batch)
        print(f"  Deleted {min(i+DELETE_BATCH, len(to_delete))}/{len(to_delete)}")

    # Verify
    h = {**{"apikey": sb.service_key, "Authorization": f"Bearer {sb.service_key}"},
         "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"}
    r = sb.client.get(f"{sb.url}/rest/v1/chunks", headers=h,
                      params={"manufacturer": "eq.Morley", "select": "id"})
    total = r.headers["Content-Range"].split("/")[-1]
    print(f"\nMorley chunks after dedup: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
