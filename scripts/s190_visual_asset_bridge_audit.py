#!/usr/bin/env python3
"""Read-only audit of reusable manual-page assets across chunk generations.

The active ``chunks_v2`` table deliberately does not own visual assets: a page
image belongs to a document revision and page, not to a particular chunking of
that page.  This audit measures whether the immutable legacy asset receipts can
be rebound safely by ``(document_id, page_number)`` without mutating either
table.  It never downloads source manuals and never writes to Supabase.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
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


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
DEFAULT_OUTPUT = ROOT / "evals" / "s190_visual_asset_bridge_audit_v1.json"
PAGE_SIZE = 1_000
RETRYABLE = {429, 500, 502, 503, 504}


async def _fetch_page(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    select: str,
    offset: int,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    params = {
        "select": select,
        "limit": str(PAGE_SIZE),
        "offset": str(offset),
        "order": "id.asc",
    }
    params.update(filters or {})
    for attempt in range(4):
        try:
            response = await client.get(url, headers=headers, params=params, timeout=60)
            if response.status_code not in RETRYABLE:
                response.raise_for_status()
                return response.json()
        except httpx.TransportError:
            if attempt == 3:
                raise
        if attempt == 3:
            response.raise_for_status()
        await asyncio.sleep(0.5 * (2**attempt))
    raise RuntimeError("unreachable")


async def _fetch_all(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    select: str,
    expected_rows: int,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for offset in range(0, expected_rows, PAGE_SIZE):
        rows.extend(
            await _fetch_page(
                client,
                url=url,
                headers=headers,
                select=select,
                offset=offset,
                filters=filters,
            )
        )
        if offset % 10_000 == 0:
            print(f"read-only snapshot: {url.rsplit('/', 1)[-1]} {len(rows)}/{expected_rows}", flush=True)
    return rows


async def _stream_into_sqlite(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    select: str,
    expected_rows: int,
    consume: Any,
    filters: dict[str, str] | None = None,
) -> int:
    observed = 0
    last_id: str | None = None
    while observed < expected_rows:
        params = {
            "select": select,
            "limit": str(PAGE_SIZE),
            "order": "id.asc",
            **(filters or {}),
        }
        if last_id is not None:
            params["id"] = f"gt.{last_id}"
        page: list[dict[str, Any]] | None = None
        for attempt in range(4):
            try:
                response = await client.get(url, headers=headers, params=params, timeout=60)
                if response.status_code not in RETRYABLE:
                    response.raise_for_status()
                    page = response.json()
                    break
            except httpx.TransportError:
                if attempt == 3:
                    raise
            if attempt == 3:
                response.raise_for_status()
            await asyncio.sleep(0.5 * (2**attempt))
        if not page:
            break
        consume(page)
        observed += len(page)
        last_id = str(page[-1]["id"])
        if (observed - len(page)) % 10_000 == 0:
            print(
                f"read-only snapshot: {url.rsplit('/', 1)[-1]} "
                f"{observed}/{expected_rows}",
                flush=True,
            )
        if len(page) < PAGE_SIZE:
            break
    if observed != expected_rows:
        raise RuntimeError(
            f"Snapshot cardinality changed for {url}: expected {expected_rows}, observed {observed}"
        )
    return observed


async def _count(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    filters: dict[str, str] | None = None,
) -> int:
    count_headers = {**headers, "Prefer": "count=exact"}
    for attempt in range(4):
        try:
            response = await client.head(
                url,
                headers=count_headers,
                params={**(filters or {}), "limit": "1"},
                timeout=60,
            )
            if response.status_code not in RETRYABLE:
                response.raise_for_status()
                return int(response.headers["content-range"].rsplit("/", 1)[1])
        except httpx.TransportError:
            if attempt == 3:
                raise
        if attempt == 3:
            response.raise_for_status()
        await asyncio.sleep(0.5 * (2**attempt))
    raise RuntimeError("unreachable")


def _page_key(row: dict[str, Any]) -> tuple[str, int] | None:
    document_id = str(row.get("document_id") or "").strip()
    page_number = row.get("page_number")
    if not document_id or not isinstance(page_number, int):
        return None
    return document_id, page_number


def reconcile_assets(
    legacy_rows: list[dict[str, Any]], active_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return deterministic page-level bridge metrics for two frozen snapshots."""
    legacy_by_page: dict[tuple[str, int], set[str]] = defaultdict(set)
    legacy_sources: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in legacy_rows:
        key = _page_key(row)
        diagram_url = str(row.get("diagram_url") or "").strip()
        if key is None or not diagram_url:
            continue
        legacy_by_page[key].add(diagram_url)
        source_file = str(row.get("source_file") or "").strip().casefold()
        if source_file:
            legacy_sources[key].add(source_file)

    active_keys: set[tuple[str, int]] = set()
    active_rows_by_key: Counter[tuple[str, int]] = Counter()
    active_sources: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in active_rows:
        key = _page_key(row)
        if key is None:
            continue
        active_keys.add(key)
        active_rows_by_key[key] += 1
        source_file = str(row.get("source_file") or "").strip().casefold()
        if source_file:
            active_sources[key].add(source_file)

    matched = active_keys & legacy_by_page.keys()
    single_url = {key for key in matched if len(legacy_by_page[key]) == 1}
    source_consistent = {
        key
        for key in single_url
        if legacy_sources[key]
        and active_sources[key]
        and legacy_sources[key] == active_sources[key]
    }
    ambiguous = {key for key in matched if len(legacy_by_page[key]) > 1}
    rebound_rows = sum(active_rows_by_key[key] for key in source_consistent)

    stable_receipts = [
        {
            "document_id": key[0],
            "page_number": key[1],
            "source_file_sha256": hashlib.sha256(
                next(iter(active_sources[key])).encode("utf-8")
            ).hexdigest(),
            "diagram_url_sha256": hashlib.sha256(
                next(iter(legacy_by_page[key])).encode("utf-8")
            ).hexdigest(),
            "active_chunk_rows": active_rows_by_key[key],
        }
        for key in sorted(source_consistent)
    ]

    return {
        "legacy_rows_with_url": len(legacy_rows),
        "legacy_unique_document_pages": len(legacy_by_page),
        "active_rows": len(active_rows),
        "active_unique_document_pages": len(active_keys),
        "exact_document_page_matches": len(matched),
        "single_url_matches": len(single_url),
        "source_consistent_single_url_matches": len(source_consistent),
        "ambiguous_multi_url_matches": len(ambiguous),
        "active_rows_rebindable": rebound_rows,
        "active_row_rebindable_rate": round(rebound_rows / max(1, len(active_rows)), 8),
        "active_page_rebindable_rate": round(
            len(source_consistent) / max(1, len(active_keys)), 8
        ),
        "legacy_url_multiplicity": dict(
            sorted(Counter(len(urls) for urls in legacy_by_page.values()).items())
        ),
        "stable_receipts": stable_receipts,
    }


async def _run(env_path: Path) -> dict[str, Any]:
    load_dotenv(env_path, override=True)
    base_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    temp_db = tempfile.NamedTemporaryFile(prefix="s190_visual_", suffix=".sqlite", delete=False)
    temp_path = Path(temp_db.name)
    temp_db.close()
    database = sqlite3.connect(temp_path)
    database.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE active (
          row_id TEXT PRIMARY KEY,
          document_id TEXT NOT NULL,
          page_number INTEGER NOT NULL,
          source_hash TEXT NOT NULL
        );
        CREATE TABLE legacy (
          document_id TEXT NOT NULL,
          page_number INTEGER NOT NULL,
          source_hash TEXT NOT NULL,
          url_hash TEXT NOT NULL,
          url_value TEXT NOT NULL,
          PRIMARY KEY (document_id, page_number, source_hash, url_hash)
        );
        CREATE INDEX active_page ON active(document_id, page_number);
        CREATE INDEX legacy_page ON legacy(document_id, page_number);
        """
    )

    def source_hash(row: dict[str, Any]) -> str:
        value = str(row.get("source_file") or "").strip().casefold()
        return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""

    def consume_active(rows: list[dict[str, Any]]) -> None:
        database.executemany(
            "INSERT OR IGNORE INTO active VALUES (?, ?, ?, ?)",
            (
                (str(row["id"]), str(row["document_id"]), row["page_number"], source_hash(row))
                for row in rows
                if _page_key(row) is not None and source_hash(row)
            ),
        )
        database.commit()

    def consume_legacy(rows: list[dict[str, Any]]) -> None:
        database.executemany(
            "INSERT OR IGNORE INTO legacy VALUES (?, ?, ?, ?, ?)",
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
        legacy_url = f"{base_url}/rest/v1/chunks"
        active_url = f"{base_url}/rest/v1/chunks_v2"
        legacy_count, active_count = await asyncio.gather(
            _count(
                client,
                url=legacy_url,
                headers=headers,
                filters={"diagram_url": "not.is.null"},
            ),
            _count(client, url=active_url, headers=headers),
        )
        print(
            f"read-only counts: legacy_assets={legacy_count}, active_chunks={active_count}",
            flush=True,
        )
        active_observed = await _stream_into_sqlite(
            client,
            url=active_url,
            headers=headers,
            select="id,document_id,source_file,page_number",
            expected_rows=active_count,
            consume=consume_active,
        )
        legacy_observed = await _stream_into_sqlite(
            client,
            url=legacy_url,
            headers=headers,
            select="id,document_id,source_file,page_number,diagram_url",
            expected_rows=legacy_count,
            consume=consume_legacy,
            filters={"diagram_url": "not.is.null"},
        )

      cursor = database.cursor()
      scalar = lambda sql: cursor.execute(sql).fetchone()[0]
      active_pages = scalar(
          "SELECT COUNT(*) FROM (SELECT 1 FROM active GROUP BY document_id,page_number)"
      )
      legacy_pages = scalar(
          "SELECT COUNT(*) FROM (SELECT 1 FROM legacy GROUP BY document_id,page_number)"
      )
      matched_pages = scalar(
          """SELECT COUNT(*) FROM (
          SELECT 1 FROM active a JOIN legacy l USING(document_id,page_number)
          GROUP BY a.document_id,a.page_number)"""
      )
      single_url_pages = scalar(
          """SELECT COUNT(*) FROM (
          SELECT a.document_id,a.page_number FROM active a
          JOIN legacy l USING(document_id,page_number)
          GROUP BY a.document_id,a.page_number HAVING COUNT(DISTINCT l.url_hash)=1)"""
      )
      source_consistent_query = """
          SELECT a.document_id,a.page_number,MIN(a.source_hash),MIN(l.url_hash),COUNT(DISTINCT a.row_id)
          FROM active a JOIN legacy l USING(document_id,page_number)
          GROUP BY a.document_id,a.page_number
          HAVING COUNT(DISTINCT l.url_hash)=1
             AND COUNT(DISTINCT a.source_hash)=1
             AND COUNT(DISTINCT l.source_hash)=1
             AND MIN(a.source_hash)=MIN(l.source_hash)
          ORDER BY a.document_id,a.page_number
      """
      stable_rows = cursor.execute(source_consistent_query).fetchall()
      stable_digest = hashlib.sha256()
      for row in stable_rows:
          stable_digest.update(json.dumps(row, separators=(",", ":")).encode("utf-8"))
          stable_digest.update(b"\n")
      ambiguous_pages = scalar(
          """SELECT COUNT(*) FROM (
          SELECT a.document_id,a.page_number FROM active a
          JOIN legacy l USING(document_id,page_number)
          GROUP BY a.document_id,a.page_number HAVING COUNT(DISTINCT l.url_hash)>1)"""
      )
      rebindable_rows = sum(row[4] for row in stable_rows)
      multiplicity = dict(
          cursor.execute(
              """SELECT urls,COUNT(*) FROM (
              SELECT COUNT(DISTINCT url_hash) urls FROM legacy
              GROUP BY document_id,page_number) GROUP BY urls ORDER BY urls"""
          ).fetchall()
      )
      sampled_urls: list[tuple[str, str]] = []
      seen_url_hashes: set[str] = set()
      for stable_row in stable_rows:
          url_hash = stable_row[3]
          if url_hash in seen_url_hashes:
              continue
          seen_url_hashes.add(url_hash)
          url_value = cursor.execute(
              "SELECT MIN(url_value) FROM legacy WHERE url_hash=?", (url_hash,)
          ).fetchone()[0]
          sampled_urls.append((url_hash, url_value))
          if len(sampled_urls) == 30:
              break

      async def check_asset(url_hash: str, url_value: str) -> dict[str, Any]:
          try:
              async with httpx.AsyncClient(follow_redirects=True) as asset_client:
                  response = await asset_client.head(url_value, timeout=30)
              return {
                  "diagram_url_sha256": url_hash,
                  "http_status": response.status_code,
                  "content_type": response.headers.get("content-type"),
                  "content_length": int(response.headers.get("content-length") or 0),
              }
          except httpx.HTTPError as error:
              return {
                  "diagram_url_sha256": url_hash,
                  "http_status": -1,
                  "error_type": type(error).__name__,
              }

      asset_checks = await asyncio.gather(
          *(check_asset(url_hash, url_value) for url_hash, url_value in sampled_urls)
      )
      metrics = {
          "legacy_rows_with_url_observed": legacy_observed,
          "legacy_unique_document_pages": legacy_pages,
          "active_rows_observed": active_observed,
          "active_unique_document_pages": active_pages,
          "exact_document_page_matches": matched_pages,
          "single_url_matches": single_url_pages,
          "source_consistent_single_url_matches": len(stable_rows),
          "ambiguous_multi_url_matches": ambiguous_pages,
          "active_rows_rebindable": rebindable_rows,
          "active_row_rebindable_rate": round(rebindable_rows / max(1, active_observed), 8),
          "active_page_rebindable_rate": round(len(stable_rows) / max(1, active_pages), 8),
          "legacy_url_multiplicity": multiplicity,
          "stable_receipt_sha256": stable_digest.hexdigest(),
          "stable_receipt_sample": [
              {
                  "document_id": row[0],
                  "page_number": row[1],
                  "source_file_sha256": row[2],
                  "diagram_url_sha256": row[3],
                  "active_chunk_rows": row[4],
              }
              for row in stable_rows[:25]
          ],
          "sampled_asset_http_checks": asset_checks,
          "sampled_assets_http_200": sum(
              check["http_status"] == 200 for check in asset_checks
          ),
          "active_has_diagram_true": active_count,
          "active_diagram_url_present": 0,
      }
      return {
        "instrument": "s190_visual_asset_bridge_audit_v1",
        "status": "READ_ONLY_MEASUREMENT_COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tables": {"legacy_asset_source": "chunks", "active_serving": "chunks_v2"},
        "join_contract": ["document_id", "page_number", "source_file_exact"],
        "measurement": metrics,
        "authorization": {
            "database_reads": True,
            "database_writes": False,
            "storage_writes": False,
            "production_changes": False,
            "model_calls": 0,
        },
      }
    finally:
      database.close()
      temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = asyncio.run(_run(args.env))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = result["measurement"]
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key != "stable_receipts"},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
