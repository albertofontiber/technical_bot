#!/usr/bin/env python3
"""Freeze a manufacturer/role-stratified visual-utility cohort, read-only."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from PIL import Image

try:
    from scripts.s190_visual_asset_bridge_audit import (
        _count,
        _page_key,
        _stream_into_sqlite,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from s190_visual_asset_bridge_audit import _count, _page_key, _stream_into_sqlite


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
DEFAULT_OUTPUT = ROOT / "evals" / "s191_visual_utility_cohort_v1.json"
SEED = "s191_visual_utility_v1"
STRATA = ("first_page", "wiring", "procedure", "specification", "other")
PER_STRATUM = 12


def _stable_score(row: dict[str, Any]) -> str:
    value = f"{SEED}|{row['document_id']}|{row['page_number']}|{row['stratum']}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def choose_stratified_cohort(
    candidates: list[dict[str, Any]],
    *,
    per_stratum: int = PER_STRATUM,
    manufacturer_cap: int = 12,
) -> list[dict[str, Any]]:
    """Choose deterministically, maximizing manufacturer diversity per stratum."""
    manufacturer_counts = Counter(row["manufacturer"] for row in candidates)
    eligible_manufacturers = [
        manufacturer
        for manufacturer, _ in sorted(
            manufacturer_counts.items(), key=lambda item: (-item[1], item[0])
        )[:manufacturer_cap]
    ]
    selected: list[dict[str, Any]] = []
    used: set[tuple[str, int]] = set()

    for stratum in STRATA:
        pool = [
            row
            for row in candidates
            if row["stratum"] == stratum
            and row["manufacturer"] in eligible_manufacturers
            and (row["document_id"], row["page_number"]) not in used
        ]
        by_manufacturer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in pool:
            by_manufacturer[row["manufacturer"]].append(row)
        for rows in by_manufacturer.values():
            rows.sort(key=_stable_score)

        stratum_rows: list[dict[str, Any]] = []
        for manufacturer in eligible_manufacturers:
            if by_manufacturer[manufacturer] and len(stratum_rows) < per_stratum:
                stratum_rows.append(by_manufacturer[manufacturer][0])

        if len(stratum_rows) < per_stratum:
            already = {
                (row["document_id"], row["page_number"]) for row in stratum_rows
            }
            remaining = sorted(
                [
                    row
                    for row in pool
                    if (row["document_id"], row["page_number"]) not in already
                ],
                key=_stable_score,
            )
            stratum_rows.extend(remaining[: per_stratum - len(stratum_rows)])

        if len(stratum_rows) != per_stratum:
            raise RuntimeError(
                f"Insufficient frozen candidates for {stratum}: "
                f"needed {per_stratum}, found {len(stratum_rows)}"
            )
        selected.extend(stratum_rows)
        used.update((row["document_id"], row["page_number"]) for row in stratum_rows)

    return selected


async def _freeze(env_path: Path) -> dict[str, Any]:
    load_dotenv(env_path, override=True)
    base_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    handle = tempfile.NamedTemporaryFile(prefix="s191_visual_", suffix=".sqlite", delete=False)
    database_path = Path(handle.name)
    handle.close()
    database = sqlite3.connect(database_path)
    database.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE active (
          row_id TEXT PRIMARY KEY,
          document_id TEXT NOT NULL,
          page_number INTEGER NOT NULL,
          source_hash TEXT NOT NULL,
          manufacturer TEXT NOT NULL,
          content_type TEXT NOT NULL
        );
        CREATE TABLE legacy (
          document_id TEXT NOT NULL,
          page_number INTEGER NOT NULL,
          source_hash TEXT NOT NULL,
          url_hash TEXT NOT NULL,
          url_value TEXT NOT NULL,
          PRIMARY KEY(document_id,page_number,source_hash,url_hash)
        );
        CREATE INDEX active_page ON active(document_id,page_number);
        CREATE INDEX legacy_page ON legacy(document_id,page_number);
        """
    )

    def source_hash(row: dict[str, Any]) -> str:
        source = str(row.get("source_file") or "").strip().casefold()
        return hashlib.sha256(source.encode("utf-8")).hexdigest() if source else ""

    def consume_active(rows: list[dict[str, Any]]) -> None:
        database.executemany(
            "INSERT OR IGNORE INTO active VALUES (?,?,?,?,?,?)",
            (
                (
                    str(row["id"]),
                    str(row["document_id"]),
                    row["page_number"],
                    source_hash(row),
                    str(row.get("manufacturer") or "unknown").strip() or "unknown",
                    str(row.get("content_type") or "general").strip() or "general",
                )
                for row in rows
                if _page_key(row) is not None and source_hash(row)
            ),
        )
        database.commit()

    def consume_legacy(rows: list[dict[str, Any]]) -> None:
        database.executemany(
            "INSERT OR IGNORE INTO legacy VALUES (?,?,?,?,?)",
            (
                (
                    str(row["document_id"]),
                    row["page_number"],
                    source_hash(row),
                    hashlib.sha256(str(row["diagram_url"]).encode("utf-8")).hexdigest(),
                    str(row["diagram_url"]),
                )
                for row in rows
                if _page_key(row) is not None
                and source_hash(row)
                and row.get("diagram_url")
            ),
        )
        database.commit()

    try:
        async with httpx.AsyncClient() as client:
            active_url = f"{base_url}/rest/v1/chunks_v2"
            legacy_url = f"{base_url}/rest/v1/chunks"
            active_count, legacy_count = await asyncio.gather(
                _count(client, url=active_url, headers=headers),
                _count(
                    client,
                    url=legacy_url,
                    headers=headers,
                    filters={"diagram_url": "not.is.null"},
                ),
            )
            await _stream_into_sqlite(
                client,
                url=active_url,
                headers=headers,
                select="id,document_id,source_file,page_number,manufacturer,content_type",
                expected_rows=active_count,
                consume=consume_active,
            )
            await _stream_into_sqlite(
                client,
                url=legacy_url,
                headers=headers,
                select="id,document_id,source_file,page_number,diagram_url",
                expected_rows=legacy_count,
                consume=consume_legacy,
                filters={"diagram_url": "not.is.null"},
            )

        stable_rows = database.execute(
            """
            SELECT a.document_id,a.page_number,MIN(a.source_hash),MIN(l.url_hash),
                   MIN(l.url_value),MIN(a.manufacturer),GROUP_CONCAT(DISTINCT a.content_type)
            FROM active a JOIN legacy l USING(document_id,page_number)
            GROUP BY a.document_id,a.page_number
            HAVING COUNT(DISTINCT l.url_hash)=1
               AND COUNT(DISTINCT a.source_hash)=1
               AND COUNT(DISTINCT l.source_hash)=1
               AND MIN(a.source_hash)=MIN(l.source_hash)
            ORDER BY a.document_id,a.page_number
            """
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for document_id, page, source, url_hash, url, manufacturer, types_csv in stable_rows:
            content_types = sorted(set(types_csv.split(",")))
            if page <= 1:
                stratum = "first_page"
            elif "wiring" in content_types:
                stratum = "wiring"
            elif "procedure" in content_types:
                stratum = "procedure"
            elif "specification" in content_types:
                stratum = "specification"
            else:
                stratum = "other"
            candidates.append(
                {
                    "document_id": document_id,
                    "page_number": page,
                    "source_file_sha256": source,
                    "diagram_url_sha256": url_hash,
                    "_diagram_url": url,
                    "manufacturer": manufacturer,
                    "content_types": content_types,
                    "stratum": stratum,
                }
            )

        cohort = choose_stratified_cohort(candidates)
        semaphore = asyncio.Semaphore(8)

        async def inspect_asset(row: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(row["_diagram_url"], timeout=60)
                response.raise_for_status()
            binary = response.content
            with Image.open(io.BytesIO(binary)) as image:
                width, height = image.size
                media_format = image.format
            frozen = {key: value for key, value in row.items() if not key.startswith("_")}
            frozen.update(
                {
                    "asset_sha256": hashlib.sha256(binary).hexdigest(),
                    "asset_bytes": len(binary),
                    "width": width,
                    "height": height,
                    "media_format": media_format,
                    "http_content_type": response.headers.get("content-type"),
                }
            )
            return frozen

        frozen_rows = await asyncio.gather(*(inspect_asset(row) for row in cohort))
        for index, row in enumerate(frozen_rows, 1):
            row["item_id"] = f"s191_visual_{index:03d}"
        canonical = json.dumps(frozen_rows, sort_keys=True, separators=(",", ":"))
        return {
            "instrument": "s191_visual_utility_cohort_v1",
            "status": "FROZEN_BEFORE_LABELING",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": SEED,
            "selection": {
                "eligible_exact_pages": len(candidates),
                "items": len(frozen_rows),
                "per_stratum": dict(Counter(row["stratum"] for row in frozen_rows)),
                "per_manufacturer": dict(
                    sorted(Counter(row["manufacturer"] for row in frozen_rows).items())
                ),
                "distinct_manufacturers": len(
                    {row["manufacturer"] for row in frozen_rows}
                ),
                "cohort_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            },
            "rows": frozen_rows,
            "authorization": {
                "database_reads": True,
                "storage_gets": len(frozen_rows),
                "database_writes": False,
                "production_changes": False,
                "model_calls": 0,
                "usd": 0,
            },
        }
    finally:
        database.close()
        database_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = asyncio.run(_freeze(args.env))
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["selection"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
