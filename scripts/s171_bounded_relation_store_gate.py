#!/usr/bin/env python3
"""Run the final bounded S171 relation-store transport successor."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.s170_per_chunk_relation_store_gate as base
from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s167_independent_answer_ledger_gate import DEFAULT_ENV, _write, file_sha


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s147_fresh_source_packet_v1.json"
COHORT = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
DEFAULT_PREREG = ROOT / "evals/s171_bounded_relation_store_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s171_bounded_relation_store_execution_permit_v1.yaml"
DEFAULT_EXTRACTION_RECEIPTS = ROOT / "evals/s171_relation_extraction_receipts_v1.json"
DEFAULT_STORE = ROOT / "evals/s171_relation_store_v1.json"
DEFAULT_SELECTOR_RECEIPTS = ROOT / "evals/s171_relation_selector_receipts_v1.json"
DEFAULT_RESULT = ROOT / "evals/s171_bounded_relation_store_gate_v1.json"
MAX_RELATIONS = 30
BASE_EXTRACTION_SCHEMA = base.extraction_schema

EXTRACTOR_SYSTEM = base.EXTRACTOR_SYSTEM + """
Return at most 30 relations. Keep subject, predicate and object to at most 12 words each. Return at
most two concise conditions and two concise qualifiers per relation. Do not add commentary."""


def extraction_schema() -> dict[str, Any]:
    value = BASE_EXTRACTION_SCHEMA()
    value["properties"]["relations"]["maxItems"] = MAX_RELATIONS
    return value


def configure_base() -> None:
    base.SOURCE = SOURCE
    base.COHORT = COHORT
    base.DEFAULT_EXTRACTION_RECEIPTS = DEFAULT_EXTRACTION_RECEIPTS
    base.DEFAULT_STORE = DEFAULT_STORE
    base.DEFAULT_SELECTOR_RECEIPTS = DEFAULT_SELECTOR_RECEIPTS
    base.DEFAULT_RESULT = DEFAULT_RESULT
    base.MAX_RELATIONS_PER_CHUNK = MAX_RELATIONS
    base.MAX_RELATION_ASSIGNMENTS = 90
    base.EXTRACTOR_SYSTEM = EXTRACTOR_SYSTEM
    base.extraction_schema = extraction_schema


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION" or permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_FINAL":
        raise RuntimeError("S171 execution is not authorized")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S171 frozen input drift: {label}")
    for label, spec in permit["frozen_artifacts"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S171 permitted artifact drift: {label}")
    return prereg


def _rename_artifact(path: Path, instrument: str, checksum_key: str | None = None) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    value["instrument"] = instrument
    if checksum_key:
        value.pop(checksum_key, None)
        value[checksum_key] = stable_sha(value)
    _write(path, value)
    return value


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    configure_base()
    result = base.execute(prereg, env_file)
    _rename_artifact(DEFAULT_EXTRACTION_RECEIPTS, "s171_relation_extraction_receipts_v1")
    _rename_artifact(DEFAULT_STORE, "s171_relation_store_v1", "store_sha256")
    if DEFAULT_SELECTOR_RECEIPTS.exists():
        _rename_artifact(DEFAULT_SELECTOR_RECEIPTS, "s171_relation_selector_receipts_v1")
    result["instrument"] = "s171_bounded_relation_store_gate_v1"
    result.pop("result_sha256", None)
    result["result_sha256"] = stable_sha(result)
    _write(DEFAULT_RESULT, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    result = execute(validate_authorization(args.prereg, args.permit), args.env_file)
    print(json.dumps({"status": result["status"], "population": result.get("population"), "metrics": result.get("metrics"), "cost": result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
