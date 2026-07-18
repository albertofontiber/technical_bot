#!/usr/bin/env python3
"""Bridge S269: genera las filas candidatas de ``document_visual_assets`` desde
el join exacto S190 entre ``chunks`` (legacy, dueña de las URLs) y ``chunks_v2``
(activa), SIN escribir en ninguna tabla existente.

Replica byte-a-byte el join del audit S190 (``scripts/s190_visual_asset_bridge_audit.py``):
    * join exacto (document_id, page_number);
    * una única URL legacy por página;
    * source_file consistente (casefold) entre legacy y activa;
y verifica TOLERANCIA 0 contra ``evals/s190_visual_asset_bridge_audit_v1.json``
(incluye el ``stable_receipt_sha256``, el digest criptográfico de las 5.096
páginas del bridge). Si algo no cuadra, reporta el delta y NO genera el dump.

Modos:
    --verify   solo verificación (lecturas GET; 0 escrituras; no escribe dump).
    (default)  verificación + dump JSONL local (``evals/s269_visual_assets_bridge_dump_v1.jsonl``).
    --load     INSERT del dump a ``document_visual_assets`` vía REST. ABORTA si
               la tabla no existe (requiere aplicar migrations/014 + autorización
               del orquestador). Idempotente (on_conflict=ignore-duplicates).

Contrato duro: este script jamás toca ``chunks``/``chunks_v2`` en escritura.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

try:
    from scripts.s190_visual_asset_bridge_audit import (
        _count,
        _page_key,
        _stream_into_sqlite,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from s190_visual_asset_bridge_audit import _count, _page_key, _stream_into_sqlite


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = ROOT / ".env"
AUDIT_PATH = ROOT / "evals" / "s190_visual_asset_bridge_audit_v1.json"
DEFAULT_DUMP = ROOT / "evals" / "s269_visual_assets_bridge_dump_v1.jsonl"
TARGET_TABLE = "document_visual_assets"
LOAD_BATCH = 500

# Claves del audit S190 verificadas con tolerancia 0. El digest
# stable_receipt_sha256 cubre las 5.096 filas (doc, página, source_hash,
# url_hash, nº de chunks activos) — si UNA página cambió, no cuadra.
VERIFY_KEYS = (
    "legacy_rows_with_url_observed",
    "legacy_unique_document_pages",
    "active_rows_observed",
    "active_unique_document_pages",
    "exact_document_page_matches",
    "single_url_matches",
    "source_consistent_single_url_matches",
    "ambiguous_multi_url_matches",
    "active_rows_rebindable",
    "stable_receipt_sha256",
)


def _headers(env_path: Path) -> tuple[str, dict[str, str]]:
    load_dotenv(env_path, override=True)
    base_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    return base_url, {"apikey": service_key, "Authorization": f"Bearer {service_key}"}


async def _snapshot(env_path: Path) -> tuple[sqlite3.Connection, Path, tuple[int, int]]:
    """Congela chunks (con URL) y chunks_v2 en un sqlite temporal, solo GET.

    Mismo esquema y mismos filtros de consumo que el audit S190 / freeze S191:
    filas sin (document_id, page_number) válidos o sin source_file se descartan
    ANTES del join (paridad exacta con el instrumento que midió 5.096).
    """
    base_url, headers = _headers(env_path)
    handle = tempfile.NamedTemporaryFile(
        prefix="s269_bridge_", suffix=".sqlite", delete=False
    )
    database_path = Path(handle.name)
    handle.close()
    database = sqlite3.connect(database_path)
    database.execute("PRAGMA journal_mode=WAL")
    database.executescript(
        """
        CREATE TABLE active (
          row_id TEXT PRIMARY KEY,
          document_id TEXT NOT NULL,
          page_number INTEGER NOT NULL,
          source_hash TEXT NOT NULL,
          source_file TEXT NOT NULL,
          manufacturer TEXT NOT NULL,
          extraction_sha256 TEXT NOT NULL
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
            "INSERT OR IGNORE INTO active VALUES (?,?,?,?,?,?,?)",
            (
                (
                    str(row["id"]),
                    str(row["document_id"]),
                    row["page_number"],
                    source_hash(row),
                    str(row.get("source_file") or "").strip(),
                    str(row.get("manufacturer") or "unknown").strip() or "unknown",
                    str(row.get("extraction_sha256") or "").strip(),
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
                    hashlib.sha256(
                        str(row["diagram_url"]).encode("utf-8")
                    ).hexdigest(),
                    str(row["diagram_url"]),
                )
                for row in rows
                if _page_key(row) is not None
                and source_hash(row)
                and row.get("diagram_url")
            ),
        )
        database.commit()

    async with httpx.AsyncClient() as client:
        active_url = f"{base_url}/rest/v1/chunks_v2"
        legacy_url = f"{base_url}/rest/v1/chunks"
        active_count = await _count(client, url=active_url, headers=headers)
        legacy_count = await _count(
            client,
            url=legacy_url,
            headers=headers,
            filters={"diagram_url": "not.is.null"},
        )
        active_observed = await _stream_into_sqlite(
            client,
            url=active_url,
            headers=headers,
            select="id,document_id,source_file,page_number,manufacturer,extraction_sha256",
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
    return database, database_path, (legacy_observed, active_observed)


def compute_bridge(
    database: sqlite3.Connection, observed: tuple[int, int]
) -> dict[str, Any]:
    """Métricas + filas del bridge con el MISMO SQL que el audit S190."""
    cursor = database.cursor()
    scalar = lambda sql: cursor.execute(sql).fetchone()[0]  # noqa: E731
    legacy_observed, active_observed = observed

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
    ambiguous_pages = scalar(
        """SELECT COUNT(*) FROM (
        SELECT a.document_id,a.page_number FROM active a
        JOIN legacy l USING(document_id,page_number)
        GROUP BY a.document_id,a.page_number HAVING COUNT(DISTINCT l.url_hash)>1)"""
    )

    # Digest EXACTO del audit: mismas 5 columnas, mismo orden, misma serialización.
    stable_rows = cursor.execute(
        """
        SELECT a.document_id,a.page_number,MIN(a.source_hash),MIN(l.url_hash),COUNT(DISTINCT a.row_id)
        FROM active a JOIN legacy l USING(document_id,page_number)
        GROUP BY a.document_id,a.page_number
        HAVING COUNT(DISTINCT l.url_hash)=1
           AND COUNT(DISTINCT a.source_hash)=1
           AND COUNT(DISTINCT l.source_hash)=1
           AND MIN(a.source_hash)=MIN(l.source_hash)
        ORDER BY a.document_id,a.page_number
        """
    ).fetchall()
    stable_digest = hashlib.sha256()
    for row in stable_rows:
        stable_digest.update(json.dumps(row, separators=(",", ":")).encode("utf-8"))
        stable_digest.update(b"\n")

    # Filas enriquecidas para el dump (mismo HAVING; columnas extra no alteran
    # la selección: url_value / source_file / manufacturer / extraction).
    dump_rows = cursor.execute(
        """
        SELECT a.document_id,a.page_number,MIN(a.source_hash),MIN(l.url_hash),
               COUNT(DISTINCT a.row_id),MIN(l.url_value),MIN(a.source_file),
               MIN(a.manufacturer),
               COUNT(DISTINCT a.extraction_sha256),MIN(a.extraction_sha256)
        FROM active a JOIN legacy l USING(document_id,page_number)
        GROUP BY a.document_id,a.page_number
        HAVING COUNT(DISTINCT l.url_hash)=1
           AND COUNT(DISTINCT a.source_hash)=1
           AND COUNT(DISTINCT l.source_hash)=1
           AND MIN(a.source_hash)=MIN(l.source_hash)
        ORDER BY a.document_id,a.page_number
        """
    ).fetchall()

    return {
        "metrics": {
            "legacy_rows_with_url_observed": legacy_observed,
            "legacy_unique_document_pages": legacy_pages,
            "active_rows_observed": active_observed,
            "active_unique_document_pages": active_pages,
            "exact_document_page_matches": matched_pages,
            "single_url_matches": single_url_pages,
            "source_consistent_single_url_matches": len(stable_rows),
            "ambiguous_multi_url_matches": ambiguous_pages,
            "active_rows_rebindable": sum(row[4] for row in stable_rows),
            "stable_receipt_sha256": stable_digest.hexdigest(),
        },
        "dump_rows": dump_rows,
    }


def verify_against_audit(
    metrics: dict[str, Any], audit_path: Path = AUDIT_PATH
) -> list[str]:
    """Compara con tolerancia 0; devuelve la lista de deltas (vacía = PASS)."""
    audit = json.loads(audit_path.read_text(encoding="utf-8"))["measurement"]
    deltas = []
    for key in VERIFY_KEYS:
        expected = audit[key]
        observed = metrics[key]
        if expected != observed:
            deltas.append(f"{key}: audit={expected!r} observado={observed!r}")
    return deltas


def build_dump_records(dump_rows: list[tuple]) -> list[dict[str, Any]]:
    """Filas candidatas de document_visual_assets (contrato migración 014)."""
    records = []
    for (
        document_id,
        page_number,
        source_file_sha256,
        diagram_url_sha256,
        active_chunk_rows,
        storage_url,
        source_file,
        manufacturer,
        extraction_distinct,
        extraction_sha256,
    ) in dump_rows:
        records.append(
            {
                # ---- columnas de document_visual_assets --------------------
                "document_id": document_id,
                "page_index": page_number,
                "page_label": None,
                # TODO(binario): sustituir por sha256 del binario descargado.
                # De momento es sha256(storage_url) — la procedencia queda
                # declarada en asset_sha256_provenance para que sea imposible
                # confundirlo con un hash binario.
                "asset_sha256": diagram_url_sha256,
                "storage_url": storage_url,
                "media_type": None,  # TODO(binario): recibo de transporte real
                "width": None,
                "height": None,
                "asset_scope": "page_render",
                "visual_role": None,  # lo puebla el clasificador v3
                "technical_utility": "uncertain",  # JAMÁS se sirve sin clasificar
                "classifier_contract": None,
                "classifier_receipt": None,
                "source_extraction_sha256": (
                    extraction_sha256
                    if extraction_distinct == 1 and extraction_sha256
                    else None
                ),
                # ---- metadata del bridge (NO son columnas; el loader las
                # descarta antes del INSERT; el cohort-builder las usa) -------
                "asset_sha256_provenance": "sha256_of_storage_url_TODO_binary",
                "bridge": {
                    "instrument": "s269_visual_assets_bridge_v1",
                    "source_audit": "s190_visual_asset_bridge_audit_v1",
                    "source_file": source_file,
                    "source_file_sha256": source_file_sha256,
                    "manufacturer": manufacturer,
                    "active_chunk_rows": active_chunk_rows,
                },
            }
        )
    return records


TABLE_COLUMNS = (
    "document_id",
    "page_index",
    "page_label",
    "asset_sha256",
    "storage_url",
    "media_type",
    "width",
    "height",
    "asset_scope",
    "visual_role",
    "technical_utility",
    "classifier_contract",
    "classifier_receipt",
    "source_extraction_sha256",
)


def _table_exists(base_url: str, headers: dict[str, str]) -> bool:
    response = httpx.get(
        f"{base_url}/rest/v1/{TARGET_TABLE}",
        headers=headers,
        params={"select": "id", "limit": "1"},
        timeout=30,
    )
    if response.status_code == 404:
        return False
    response.raise_for_status()
    return True


def load_dump(env_path: Path, dump_path: Path) -> int:
    """INSERT idempotente del dump. Solo corre si la tabla ya existe."""
    base_url, headers = _headers(env_path)
    if not _table_exists(base_url, headers):
        print(
            f"ABORT: la tabla {TARGET_TABLE} no existe. --load requiere aplicar "
            "migrations/014_document_visual_assets.sql + autorización del "
            "orquestador. Este script NO aplica migraciones.",
            file=sys.stderr,
        )
        return 2
    records = [
        json.loads(line)
        for line in dump_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    payloads = [
        {column: record[column] for column in TABLE_COLUMNS} for record in records
    ]
    post_headers = {
        **headers,
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }
    inserted = 0
    with httpx.Client(timeout=60) as client:
        for start in range(0, len(payloads), LOAD_BATCH):
            batch = payloads[start : start + LOAD_BATCH]
            response = client.post(
                f"{base_url}/rest/v1/{TARGET_TABLE}",
                headers=post_headers,
                params={"on_conflict": "document_id,page_index,asset_sha256"},
                json=batch,
            )
            response.raise_for_status()
            inserted += len(batch)
            print(f"load: {inserted}/{len(payloads)}", flush=True)
    # Verificación post-carga: el count de la tabla debe cubrir el dump.
    count_response = httpx.head(
        f"{base_url}/rest/v1/{TARGET_TABLE}",
        headers={**headers, "Prefer": "count=exact"},
        params={"limit": "1"},
        timeout=60,
    )
    count_response.raise_for_status()
    total = int(count_response.headers["content-range"].rsplit("/", 1)[1])
    print(f"load: tabla {TARGET_TABLE} tiene {total} filas (dump={len(payloads)})")
    if total < len(payloads):
        print("ABORT: la tabla tiene menos filas que el dump.", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--dump-path", type=Path, default=DEFAULT_DUMP)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Solo verificar contra el audit S190 (no escribe el dump).",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="INSERT del dump a document_visual_assets (requiere migración 014 aplicada).",
    )
    args = parser.parse_args()

    if args.load:
        if not args.dump_path.exists():
            print(f"ABORT: no existe el dump {args.dump_path}", file=sys.stderr)
            return 2
        return load_dump(args.env, args.dump_path)

    import asyncio

    database, database_path, observed = asyncio.run(_snapshot(args.env))
    try:
        bridge = compute_bridge(database, observed)
    finally:
        database.close()
        database_path.unlink(missing_ok=True)

    metrics = bridge["metrics"]
    deltas = verify_against_audit(metrics)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    if deltas:
        print("VERIFY FAIL (tolerancia 0) — deltas vs audit S190:", file=sys.stderr)
        for delta in deltas:
            print(f"  {delta}", file=sys.stderr)
        print("NO se genera el dump.", file=sys.stderr)
        return 1
    print("VERIFY PASS: bridge idéntico al audit S190 (digest incluido).")
    if args.verify:
        return 0

    records = build_dump_records(bridge["dump_rows"])
    manifest = {
        "instrument": "s269_visual_assets_bridge_dump_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(records),
        "verified_against": "evals/s190_visual_asset_bridge_audit_v1.json",
        "stable_receipt_sha256": metrics["stable_receipt_sha256"],
        "manufacturers": dict(
            sorted(Counter(r["bridge"]["manufacturer"] for r in records).items())
        ),
    }
    with args.dump_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    manifest_path = args.dump_path.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"dump: {len(records)} filas -> {args.dump_path}")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
