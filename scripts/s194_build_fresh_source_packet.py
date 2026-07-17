#!/usr/bin/env python3
"""Freeze a fresh, read-only chunks_v2 packet for the S194 planner gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s146_build_fresh_source_packet import _excluded_documents, file_sha
from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s167_build_independent_ledger_source import build_from_rows
from scripts.s167_build_independent_ledger_source_support import collect_uuid_strings
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
DEFAULT_OUT = ROOT / "evals/s194_fresh_source_packet_v1.json"
SEED = "s194-decomposed-evidence-planner-fresh-v1"
PAGE_SIZE = 1_000
SELECT = (
    "id,content,document_id,manufacturer,product_model,source_file,page_number,"
    "section_title,section_path,extraction_sha256"
)
PRIOR_PACKETS = tuple(
    ROOT / "evals" / name
    for name in (
        "s142_independent_source_packet_v1.json",
        "s146_fresh_source_packet_v1.json",
        "s147_fresh_source_packet_v1.json",
        "s157_multichunk_source_packet_v1.json",
        "s167_independent_ledger_source_packet_v1.json",
        "s168_source_unit_gold_packet_v1.json",
    )
)
S114 = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
TARGET_FILES = tuple(
    ROOT / "evals" / name
    for name in (
        "s141_source_bound_technical_obligations_v1.json",
        "s149_target_evidence_selector_probe_v1.json",
        "s150_target_coverage_verifier_probe_v1.json",
        "s158_target_table_preamble_probe_v1.json",
        "s159_target_table_preamble_probe_v2.json",
        "s160_target_table_preamble_probe_v3.json",
        "s163_synthesis_residual_audit_v1.json",
        "s173_single_source_omission_cohort_v1.json",
        "s173_single_source_omission_correction_v1.json",
        "s193_terra_id_planner_deterministic_append_v1.json",
    )
)


def _credentials(env_file: Path) -> tuple[str, dict[str, str]]:
    values = dotenv_values(env_file)
    base_url = str(values.get("SUPABASE_URL") or "").rstrip("/")
    key = str(
        values.get("SUPABASE_SERVICE_KEY") or values.get("SUPABASE_KEY") or ""
    ).strip()
    if not base_url or not key:
        raise RuntimeError("S194 Supabase read credentials missing")
    return base_url, {"apikey": key, "Authorization": f"Bearer {key}"}


def _count(client: httpx.Client, url: str, headers: dict[str, str]) -> int:
    response = client.head(
        url,
        headers={**headers, "Prefer": "count=exact"},
        params={"select": "id"},
    )
    response.raise_for_status()
    content_range = response.headers.get("content-range", "")
    if "/" not in content_range:
        raise RuntimeError("S194 exact chunks_v2 count missing")
    return int(content_range.rsplit("/", 1)[1])


def read_chunks_v2(
    env_file: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base_url, headers = _credentials(env_file)
    url = f"{base_url}/rest/v1/chunks_v2"
    rows: list[dict[str, Any]] = []
    requests = 0
    last_id: str | None = None
    with httpx.Client(timeout=90.0) as client:
        count_before = _count(client, url, headers)
        requests += 1
        while len(rows) < count_before:
            params = {
                "select": SELECT,
                "order": "id.asc",
                "limit": str(PAGE_SIZE),
            }
            if last_id is not None:
                params["id"] = f"gt.{last_id}"
            response = client.get(url, headers=headers, params=params)
            requests += 1
            response.raise_for_status()
            page = response.json()
            if not page:
                break
            rows.extend(page)
            last_id = str(page[-1]["id"])
            if len(page) < PAGE_SIZE:
                break
        count_after = _count(client, url, headers)
        requests += 1
    if len(rows) != count_before or count_after != count_before:
        raise RuntimeError(
            "S194 chunks_v2 cardinality changed during the read-only freeze: "
            f"before={count_before}, rows={len(rows)}, after={count_after}"
        )
    if len({str(row["id"]) for row in rows}) != len(rows):
        raise RuntimeError("S194 chunks_v2 snapshot contains duplicate IDs")
    return rows, {
        "table": "chunks_v2",
        "rows": len(rows),
        "get_requests": requests,
        "database_writes": 0,
        "snapshot_sha256": stable_sha(rows),
    }


def _prior_contract() -> tuple[
    set[str], set[tuple[str, str]], set[str], dict[str, str]
]:
    prior_documents = set(_excluded_documents())
    development_pairs: set[tuple[str, str]] = set()
    prior_source_files: set[str] = set()
    dependencies: dict[str, str] = {}
    for path in PRIOR_PACKETS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["items"]:
            if row.get("document_id"):
                prior_documents.add(str(row["document_id"]))
            source_file = str(row.get("source_file") or row.get("filename") or "")
            if source_file:
                prior_source_files.add(source_file.casefold())
            if row.get("manufacturer") and row.get("product_model"):
                development_pairs.add(
                    (
                        str(row["manufacturer"]).casefold(),
                        str(row["product_model"]).casefold(),
                    )
                )
        dependencies[str(path.relative_to(ROOT)).replace("\\", "/")] = file_sha(path)
    s114 = json.loads(S114.read_text(encoding="utf-8"))
    for selected in s114["chosen"]:
        source = s114["source_rows"][selected["chunk_id"]]
        prior_documents.add(str(source["document_id"]))
        development_pairs.add(
            (
                str(selected.get("manufacturer") or "").casefold(),
                str(selected.get("product_model") or "").casefold(),
            )
        )
    dependencies[str(S114.relative_to(ROOT)).replace("\\", "/")] = file_sha(S114)
    return prior_documents, development_pairs, prior_source_files, dependencies


def build_packet(rows: list[dict[str, Any]], read_receipt: dict[str, Any]) -> dict[str, Any]:
    prior_documents, development_pairs, prior_source_files, dependencies = _prior_contract()
    target_ids: set[str] = set()
    for path in TARGET_FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        target_ids.update(collect_uuid_strings(payload))
        dependencies[str(path.relative_to(ROOT)).replace("\\", "/")] = file_sha(path)
    normalized = [{**row, "kind": "chunk"} for row in rows]
    prior_documents.update(
        str(row["document_id"])
        for row in normalized
        if str(row.get("source_file") or "").casefold() in prior_source_files
    )
    active = {str(row["document_id"]) for row in normalized}
    packet = build_from_rows(
        normalized,
        active,
        prior_documents,
        target_ids,
        development_pairs,
        seed=SEED,
        instrument="s194_fresh_source_packet_v1",
        item_prefix="s194_src",
    )
    packet.pop("packet_sha256", None)
    packet["status"] = "SEALED_FRESH_LIVE_CHUNKS_V2_GET_ONLY"
    packet["selection"]["source_table"] = "chunks_v2"
    packet["selection"]["fresh_after_s193"] = True
    for row in packet["items"]:
        units = build_header_aware_evidence_units(
            row["excerpt"], fragment_number=1, candidate_id=row["item_id"]
        )
        row["evidence_unit_manifest"] = [
            {
                "unit_id": unit.unit_id,
                "unit_kind": unit.unit_kind,
                "source_spans": [list(span) for span in unit.source_spans],
                "content_sha256": unit.content_sha256,
            }
            for unit in units
        ]
    packet["read_receipt"] = read_receipt
    packet["dependencies"] = dependencies
    unitizer = ROOT / "src/rag/evidence_units_v2.py"
    packet["dependencies"][str(unitizer.relative_to(ROOT)).replace("\\", "/")] = (
        file_sha(unitizer)
    )
    return {**packet, "packet_sha256": stable_sha(packet)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows, read_receipt = read_chunks_v2(args.env_file)
    packet = build_packet(rows, read_receipt)
    args.out.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": packet["status"],
                **{
                    key: packet["selection"][key]
                    for key in (
                        "items",
                        "manufacturers",
                        "unique_documents",
                        "table",
                        "prose",
                        "prior_document_overlap",
                        "target_document_overlap",
                        "development_product_pair_overlap",
                    )
                },
                "read_rows": read_receipt["rows"],
                "database_writes": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
