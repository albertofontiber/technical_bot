#!/usr/bin/env python3
"""Run the bounded S149 selector-only probe over 13 synthesis facts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s141_source_bound_technical_obligations import TARGET_KINDS, attested, plan_for
from src.rag.evidence_selector import (
    EVIDENCE_SELECTOR_MODEL,
    SYSTEM,
    build_selection_prompt,
    prepare_evidence_units,
    select_evidence,
    selection_schema,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
DEFAULT_PREREG = ROOT / "evals/s149_target_evidence_selector_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s149_target_evidence_selector_execution_permit_v1.yaml"
DEFAULT_RECEIPTS = ROOT / "evals/s149_target_evidence_selector_receipts_v1.json"
DEFAULT_OUT = ROOT / "evals/s149_target_evidence_selector_probe_v1.json"
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


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def relation_anchors_covered(obligation: Any, selected: tuple[Any, ...]) -> bool:
    same_source = "\n".join(
        row.unit.content
        for row in selected
        if row.unit.candidate_id == obligation.candidate_id
    )
    folded = _fold(same_source)
    return bool(folded) and all(_fold(anchor) in folded for anchor in obligation.required_anchors)


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S149 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_FINAL":
        raise RuntimeError("S149 execution is not permitted")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S149 frozen input drift: {label}")
    for label, spec in permit["frozen_artifacts"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S149 permitted artifact drift: {label}")
    return prereg


def execute(prereg: dict[str, Any], env_file: Path, receipts_path: Path) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    if receipts_path.exists():
        raise RuntimeError("S149 checkpoint exists; retries are forbidden")
    secrets = dotenv_values(env_file)
    key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("S149 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in payload["rows"]}
    model = prereg["model"]
    prices = prereg["pricing_usd_per_million_tokens"]
    budget = prereg["budget"]

    prepared = []
    counted_total = 0
    for qid in QIDS:
        row = frozen[qid]
        chunks = attested(row)
        units = prepare_evidence_units(chunks)
        prompt = build_selection_prompt(row["question"], units)
        counted = client.messages.count_tokens(
            model=model["id"],
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": selection_schema()}},
        ).input_tokens
        counted_total += counted
        expected = [obligation for obligation in plan_for(row) if obligation.kind in TARGET_KINDS[qid]]
        if {obligation.kind for obligation in expected} != TARGET_KINDS[qid]:
            raise RuntimeError(f"S149 expected relation drift: {qid}")
        prepared.append((qid, row, chunks, units, expected, counted))
    if counted_total > model["max_counted_input_tokens_total"]:
        raise RuntimeError("S149 counted input exceeds cap")
    worst = (
        counted_total * prices["input"]
        + len(prepared) * model["max_output_tokens_per_call"] * prices["output"]
    ) / 1_000_000
    if worst >= budget["internal_ceiling_usd"]:
        raise RuntimeError("S149 worst-case cost exceeds cap")

    receipts = []
    rows = []
    total_relations = covered_relations = 0
    actual_cost = 0.0
    for qid, row, chunks, _units, expected, counted in prepared:
        selection = select_evidence(
            row["question"],
            chunks,
            client=client,
            model=model["id"],
            max_output_tokens=model["max_output_tokens_per_call"],
        )
        cost = (
            (selection.input_tokens or 0) * prices["input"]
            + (selection.output_tokens or 0) * prices["output"]
        ) / 1_000_000
        actual_cost += cost
        relation_rows = [
            {
                "kind": obligation.kind,
                "anchors_covered": relation_anchors_covered(obligation, selection.selected),
            }
            for obligation in expected
        ]
        total_relations += len(relation_rows)
        covered_relations += sum(item["anchors_covered"] for item in relation_rows)
        receipts.append(
            {
                "qid": qid,
                "response_id": selection.response_id,
                "counted_input_tokens": counted,
                "input_tokens": selection.input_tokens,
                "output_tokens": selection.output_tokens,
                "conservative_cost_usd": round(cost, 8),
            }
        )
        _write(
            receipts_path,
            {
                "instrument": "s149_target_evidence_selector_receipts_v1",
                "status": "IN_PROGRESS",
                "model": model["id"],
                "receipts": receipts,
            },
        )
        rows.append(
            {
                "qid": qid,
                "expected_relations": len(relation_rows),
                "covered_relations": sum(item["anchors_covered"] for item in relation_rows),
                "relations": relation_rows,
                "selected_units": len(selection.selected),
                "selected_unit_receipts": [
                    {
                        "unit_id": item.unit.unit_id,
                        "fragment_number": item.unit.fragment_number,
                        "candidate_id": item.unit.candidate_id,
                        "unit_kind": item.unit.unit_kind,
                        "source_spans": [list(span) for span in item.unit.source_spans],
                        "content_sha256": item.unit.content_sha256,
                    }
                    for item in selection.selected
                ],
            }
        )
    _write(
        receipts_path,
        {
            "instrument": "s149_target_evidence_selector_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": model["id"],
            "receipts": receipts,
        },
    )
    go = covered_relations == total_relations == prereg["validation"]["target_relations"]
    body = {
        "instrument": "s149_target_evidence_selector_probe_v1",
        "status": "GO_TO_FOUR_ANSWER_PROBE" if go else "NO_GO",
        "result": {
            "questions": len(rows),
            "target_relations": total_relations,
            "covered_relations": covered_relations,
            "coverage_rate": round(covered_relations / total_relations, 8),
            "selected_units": sum(row["selected_units"] for row in rows),
            "invalid_ids": 0,
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
            "four_answer_probe": "GO" if go else "NO_GO",
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
        raise RuntimeError("S149 paid execution requires --execute-paid")
    prereg = validate_authorization(args.prereg, args.permit)
    result = execute(prereg, args.env_file, args.receipts)
    _write(args.out, result)
    print(json.dumps({"status": result["status"], **result["result"], **result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
