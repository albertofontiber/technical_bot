#!/usr/bin/env python3
"""Freeze the primary document-binding result before M2.5 fallback exists."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts import s117_m2_legacy_reuse_analysis as m2


ROOT = Path(__file__).resolve().parents[1]
_RECORD_NAME = re.compile(r"^[0-9a-f]{64}\.json$")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(
            f"{path.name}\0{len(raw)}\0{_sha_bytes(raw)}\n".encode("utf-8")
        )
    return digest.hexdigest()


def _classify_primary(
    extraction_sha256: str,
    documents_by_sha: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    matches = documents_by_sha.get(extraction_sha256, [])
    if not matches:
        payload = {
            "extraction_sha256": extraction_sha256,
            "terminal": "primary_absent_pdf_sha",
            "matching_document_count": 0,
            "document_id": None,
            "status": None,
        }
    elif len(matches) > 1:
        payload = {
            "extraction_sha256": extraction_sha256,
            "terminal": "primary_ambiguous_pdf_sha",
            "matching_document_count": len(matches),
            "document_id": None,
            "status": None,
        }
    else:
        document = matches[0]
        status = document.get("status")
        payload = {
            "extraction_sha256": extraction_sha256,
            "terminal": (
                "primary_unique_active_pdf_sha"
                if status == "active"
                else "primary_non_active_pdf_sha"
            ),
            "matching_document_count": 1,
            "document_id": document.get("id"),
            "status": status,
        }
    payload["receipt_sha256"] = _sha_bytes(_canonical(payload))
    return payload


def build_baseline(store: Path, snapshot: Path) -> dict[str, Any]:
    files = sorted(store.glob("*.json"), key=lambda path: path.name)
    records = [path for path in files if _RECORD_NAME.fullmatch(path.name)]
    non_records = [path.name for path in files if path not in records]
    if len(files) != 1069 or len(records) != 1068 or non_records != ["_failures.json"]:
        raise RuntimeError("primary baseline raw store drift")

    header, documents, _chunks, snapshot_receipt = m2.read_snapshot(snapshot)
    if (
        header.get("transaction_read_only") != "on"
        or header.get("transaction_isolation") != "repeatable read"
        or header.get("vector_payloads") != 0
    ):
        raise RuntimeError("primary baseline snapshot proof drift")

    documents_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        value = document.get("source_pdf_sha256")
        if isinstance(value, str):
            documents_by_sha[value].append(document)

    rows = [_classify_primary(path.stem, documents_by_sha) for path in records]
    terminal_counts = Counter(row["terminal"] for row in rows)
    status_counts = Counter(
        row["status"] or "__null__"
        for row in rows
        if row["terminal"] == "primary_non_active_pdf_sha"
    )
    manifest = hashlib.sha256()
    for row in rows:
        manifest.update(_canonical(row) + b"\n")
    if sum(terminal_counts.values()) != 1068:
        raise RuntimeError("primary baseline taxonomy is not closed")

    return {
        "instrument": "s117_m25_primary_binding_baseline_v1",
        "status": "FROZEN",
        "contract": {
            "target_sha_grammar": "^[0-9a-f]{64}$",
            "binding": "exact_source_pdf_sha256",
            "fallback_present": False,
        },
        "source": {
            "raw_store_json_files": len(files),
            "raw_records": len(records),
            "raw_store_manifest_sha256": _store_manifest(files),
            "snapshot": snapshot_receipt,
        },
        "summary": {
            "documents": len(rows),
            "terminals": dict(sorted(terminal_counts.items())),
            "non_active_statuses": dict(sorted(status_counts.items())),
        },
        "primary_manifest_sha256": manifest.hexdigest(),
        "rows": rows,
        "cost": {
            "database_reads": 0,
            "database_writes": 0,
            "model_calls": 0,
            "vector_payloads": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    first = build_baseline(args.store, args.snapshot)
    second = build_baseline(args.store, args.snapshot)
    first_bytes = _canonical(first)
    if first_bytes != _canonical(second):
        raise RuntimeError("primary baseline is not deterministic")
    first["determinism"] = {
        "same_process_byte_identical": True,
        "payload_sha256": _sha_bytes(first_bytes),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(first, allow_nan=False, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in first.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
