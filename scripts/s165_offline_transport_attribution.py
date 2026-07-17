#!/usr/bin/env python3
"""Attribute S165 invalid outputs by unioning repeated IDs offline.

This script cannot grant S165 credit. It only determines whether a separately
versioned transport schema is justified without another semantic model call.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s147_fresh_source_packet_v1.json"
COHORT = ROOT / "evals/s147_fresh_obligation_cohort_v1.json"
RECEIPTS = ROOT / "evals/s165_answer_archetype_ledger_receipts_v1.json"
DEFAULT_OUT = ROOT / "evals/s165_answer_archetype_ledger_transport_attribution_v1.json"


def run() -> dict[str, Any]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    receipts = json.loads(RECEIPTS.read_text(encoding="utf-8"))["receipts"]
    source_by = {row["item_id"]: row for row in source["items"]}
    cohort_by = {row["item_id"]: row for row in cohort["items"]}
    rows = []
    total_claims = covered_claims = selected_total = useful_total = complete = 0
    duplicate_only_failures = unknown_id_failures = parse_failures = 0
    for receipt in receipts:
        item_id = receipt["item_id"]
        item = cohort_by[item_id]
        source_row = source_by[item_id]
        units = build_header_aware_evidence_units(
            source_row["excerpt"], fragment_number=1, candidate_id=item_id
        )
        by_id = {unit.unit_id: unit for unit in units}
        try:
            value = json.loads(receipt["raw_text"])
            raw_ids = [
                unit_id
                for selection in value.get("selections", [])
                for unit_id in selection.get("unit_ids", [])
            ]
        except (json.JSONDecodeError, AttributeError):
            raw_ids = []
            parse_failures += 1
        unique_ids = list(dict.fromkeys(raw_ids))
        unknown = sorted(set(unique_ids) - set(by_id))
        if unknown:
            unknown_id_failures += 1
        if receipt.get("validation_error") and not unknown and raw_ids:
            duplicate_only_failures += 1
        selected = [by_id[unit_id] for unit_id in unique_ids if unit_id in by_id]
        claim_hits = [
            any(point["exact_quote"] in unit.content for unit in selected)
            for point in item["answer_points"]
        ]
        useful_hits = [
            any(point["exact_quote"] in unit.content for point in item["answer_points"])
            for unit in selected
        ]
        total_claims += len(claim_hits)
        covered_claims += sum(claim_hits)
        selected_total += len(selected)
        useful_total += sum(useful_hits)
        complete += int(bool(claim_hits) and all(claim_hits))
        rows.append(
            {
                "item_id": item_id,
                "original_validation_error": receipt.get("validation_error"),
                "raw_id_assignments": len(raw_ids),
                "unique_known_ids": len(selected),
                "unknown_ids": unknown,
                "claims": len(claim_hits),
                "claims_covered_after_union": sum(claim_hits),
                "complete_after_union": all(claim_hits),
                "useful_units_after_union": sum(useful_hits),
            }
        )
    recall = covered_claims / total_claims
    precision = useful_total / max(1, selected_total)
    complete_rate = complete / len(rows)
    justifies = bool(
        recall >= 0.90
        and precision >= 0.80
        and complete_rate >= 0.75
        and not unknown_id_failures
        and not parse_failures
    )
    return {
        "instrument": "s165_answer_archetype_ledger_transport_attribution_v1",
        "status": (
            "TRANSPORT_ONLY_SUCCESSOR_JUSTIFIED"
            if justifies
            else "NO_SEMANTIC_SIGNAL_CLOSE_BRANCH"
        ),
        "population": {
            "questions": len(rows),
            "answer_points": total_claims,
            "paid_calls": 0,
        },
        "attribution": {
            "duplicate_only_failures": duplicate_only_failures,
            "unknown_id_failures": unknown_id_failures,
            "parse_failures": parse_failures,
        },
        "offline_union_metrics": {
            "claims_covered": covered_claims,
            "claim_recall": round(recall, 8),
            "selected_units": selected_total,
            "useful_units": useful_total,
            "unit_precision": round(precision, 8),
            "questions_complete": complete,
            "question_complete_rate": round(complete_rate, 8),
        },
        "decision": {
            "s165_credit": False,
            "transport_only_successor": justifies,
            "new_semantic_prompt_iteration": False,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
        },
        "rows": rows,
        "cost": {"model_calls": 0, "usd": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = run()
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                **result["attribution"],
                **result["offline_union_metrics"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
