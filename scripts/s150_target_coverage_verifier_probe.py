#!/usr/bin/env python3
"""Apply one bounded coverage verifier pass to the frozen S149 selections."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s141_source_bound_technical_obligations import TARGET_KINDS, attested, plan_for
from scripts.s149_target_evidence_selector_probe import relation_anchors_covered
from src.rag.evidence_coverage_verifier import (
    EVIDENCE_COVERAGE_VERIFIER_MODEL,
    SYSTEM,
    build_verification_prompt,
    merge_verified_selection,
    verification_schema,
    verify_evidence_coverage,
)
from src.rag.evidence_selector import EvidenceSelection, prepare_evidence_units


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
S149_RESULT = ROOT / "evals/s149_target_evidence_selector_probe_v1.json"
S149_RECEIPTS = ROOT / "evals/s149_target_evidence_selector_receipts_v1.json"
DEFAULT_PREREG = ROOT / "evals/s150_target_coverage_verifier_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s150_target_coverage_verifier_execution_permit_v1.yaml"
DEFAULT_RECEIPTS = ROOT / "evals/s150_target_coverage_verifier_receipts_v1.json"
DEFAULT_OUT = ROOT / "evals/s150_target_coverage_verifier_probe_v1.json"
DEFAULT_ENV = Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env")
QIDS = ("cat018", "hp002", "hp011", "hp017")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reconstruct_primary_selection(
    row: dict[str, Any], prepared: list[Any], response_id: str
) -> EvidenceSelection:
    by_id = {item.unit.unit_id: item for item in prepared}
    selected = []
    for receipt in row["selected_unit_receipts"]:
        item = by_id.get(receipt["unit_id"])
        if item is None or item.unit.content_sha256 != receipt["content_sha256"]:
            raise RuntimeError("S150 frozen primary selection drift")
        selected.append(item)
    return EvidenceSelection(
        selected=tuple(selected),
        response_id=response_id,
        model="claude-haiku-4-5-20251001",
        input_tokens=None,
        output_tokens=None,
    )


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S150 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_FINAL":
        raise RuntimeError("S150 execution is not permitted")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S150 frozen input drift: {label}")
    for label, spec in permit["frozen_artifacts"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S150 permitted artifact drift: {label}")
    return prereg


def execute(prereg: dict[str, Any], env_file: Path, receipts_path: Path) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    if receipts_path.exists():
        raise RuntimeError("S150 checkpoint exists; retries are forbidden")
    secrets = dotenv_values(env_file)
    key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("S150 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in freeze["rows"]}
    s149 = json.loads(S149_RESULT.read_text(encoding="utf-8"))
    s149_by = {row["qid"]: row for row in s149["rows"]}
    s149_receipts = json.loads(S149_RECEIPTS.read_text(encoding="utf-8"))
    response_by = {row["qid"]: row["response_id"] for row in s149_receipts["receipts"]}
    model = prereg["model"]
    prices = prereg["pricing_usd_per_million_tokens"]
    budget = prereg["budget"]

    prepared_rows = []
    counted_total = 0
    for qid in QIDS:
        row = frozen[qid]
        chunks = attested(row)
        prepared = prepare_evidence_units(chunks)
        primary = reconstruct_primary_selection(s149_by[qid], prepared, response_by[qid])
        prompt = build_verification_prompt(row["question"], prepared, primary.selected)
        counted = client.messages.count_tokens(
            model=model["id"],
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": verification_schema()}},
        ).input_tokens
        counted_total += counted
        expected = [obligation for obligation in plan_for(row) if obligation.kind in TARGET_KINDS[qid]]
        prepared_rows.append((qid, row, prepared, primary, expected, counted))
    if counted_total > model["max_counted_input_tokens_total"]:
        raise RuntimeError("S150 counted input exceeds cap")
    worst = (
        counted_total * prices["input"]
        + len(prepared_rows) * model["max_output_tokens_per_call"] * prices["output"]
    ) / 1_000_000
    if worst >= budget["internal_ceiling_usd"]:
        raise RuntimeError("S150 worst-case cost exceeds cap")

    receipts = []
    rows = []
    relations_total = relations_covered = additions_total = 0
    actual_cost = 0.0
    for qid, row, prepared, primary, expected, counted in prepared_rows:
        verification = verify_evidence_coverage(
            row["question"],
            prepared,
            primary,
            client=client,
            model=model["id"],
            max_output_tokens=model["max_output_tokens_per_call"],
        )
        merged = merge_verified_selection(primary, verification)
        relation_rows = [
            {
                "kind": obligation.kind,
                "anchors_covered": relation_anchors_covered(obligation, merged.selected),
            }
            for obligation in expected
        ]
        relations_total += len(relation_rows)
        relations_covered += sum(item["anchors_covered"] for item in relation_rows)
        additions_total += len(verification.additions)
        cost = (
            (verification.input_tokens or 0) * prices["input"]
            + (verification.output_tokens or 0) * prices["output"]
        ) / 1_000_000
        actual_cost += cost
        receipts.append(
            {
                "qid": qid,
                "response_id": verification.response_id,
                "counted_input_tokens": counted,
                "input_tokens": verification.input_tokens,
                "output_tokens": verification.output_tokens,
                "conservative_cost_usd": round(cost, 8),
            }
        )
        _write(
            receipts_path,
            {
                "instrument": "s150_target_coverage_verifier_receipts_v1",
                "status": "IN_PROGRESS",
                "model": model["id"],
                "receipts": receipts,
            },
        )
        rows.append(
            {
                "qid": qid,
                "verifier_status": verification.status,
                "missing_facets": list(verification.missing_facets),
                "primary_units": len(primary.selected),
                "additional_units": len(verification.additions),
                "verified_units": len(merged.selected),
                "expected_relations": len(relation_rows),
                "covered_relations": sum(item["anchors_covered"] for item in relation_rows),
                "relations": relation_rows,
                "additional_unit_receipts": [
                    {
                        "unit_id": item.unit.unit_id,
                        "fragment_number": item.unit.fragment_number,
                        "candidate_id": item.unit.candidate_id,
                        "unit_kind": item.unit.unit_kind,
                        "source_spans": [list(span) for span in item.unit.source_spans],
                        "content_sha256": item.unit.content_sha256,
                    }
                    for item in verification.additions
                ],
            }
        )
    _write(
        receipts_path,
        {
            "instrument": "s150_target_coverage_verifier_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": model["id"],
            "receipts": receipts,
        },
    )
    go = relations_covered == relations_total == prereg["validation"]["target_relations"]
    body = {
        "instrument": "s150_target_coverage_verifier_probe_v1",
        "status": "GO_TO_FRESH_BROAD_COHORT" if go else "NO_GO",
        "result": {
            "questions": len(rows),
            "target_relations": relations_total,
            "covered_relations": relations_covered,
            "coverage_rate": round(relations_covered / relations_total, 8),
            "primary_units": sum(row["primary_units"] for row in rows),
            "additional_units": additions_total,
            "verified_units": sum(row["verified_units"] for row in rows),
            "invalid_ids": 0,
            "verifier_passes": 1,
        },
        "cost": {
            "calls": len(rows),
            "counted_input_tokens_total": counted_total,
            "conservative_actual_usd": round(actual_cost, 8),
            "worst_case_preflight_usd": round(worst, 8),
            "internal_ceiling_usd": budget["internal_ceiling_usd"],
        },
        "rows": rows,
        "decision": {
            "fresh_broad_cohort": "GO" if go else "NO_GO",
            "four_answer_probe": "NO_GO",
            "production": "NO_GO",
            "facts_moved_to_ok": 0,
        },
    }
    return {**body, "result_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-paid", action="store_true")
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute_paid:
        raise RuntimeError("S150 paid execution requires --execute-paid")
    prereg = validate_authorization(args.prereg, args.permit)
    result = execute(prereg, args.env_file, args.receipts)
    _write(args.out, result)
    print(json.dumps({"status": result["status"], **result["result"], **result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
