#!/usr/bin/env python3
"""Replay S165 outputs under a bounded many-to-many facet transport."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s165_answer_archetype_ledger import (
    COHORT,
    FACETS,
    MAX_SELECTED_IDS,
    SOURCE,
    ledger_schema,
    stable_sha,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "evals/s165_answer_archetype_ledger_receipts_v1.json"
DEFAULT_OUT = ROOT / "evals/s166_answer_archetype_ledger_transport_v1.json"
MAX_ASSIGNMENTS = 32


def validate_ledger_v2(
    value: dict[str, Any], known_ids: set[str]
) -> tuple[dict[str, list[str]], list[str]]:
    errors = list(Draft202012Validator(ledger_schema()).iter_errors(value))
    if errors:
        raise ValueError(errors[0].message)
    ledger: dict[str, list[str]] = {}
    assignments: list[str] = []
    for row in value["selections"]:
        facet = row["facet"]
        ids = row["unit_ids"]
        if facet not in FACETS or facet in ledger:
            raise ValueError("unknown or duplicate ledger facet")
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate unit ID inside facet")
        ledger[facet] = ids
        assignments.extend(ids)
    if len(assignments) > MAX_ASSIGNMENTS:
        raise ValueError("ledger assignment cardinality exceeded")
    unique_ids = list(dict.fromkeys(assignments))
    if len(unique_ids) > MAX_SELECTED_IDS:
        raise ValueError("ledger unique-unit cardinality exceeded")
    if not set(unique_ids).issubset(known_ids):
        raise ValueError("unknown ledger unit ID")
    return ledger, unique_ids


def run() -> dict[str, Any]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    receipts = json.loads(RECEIPTS.read_text(encoding="utf-8"))["receipts"]
    source_by = {row["item_id"]: row for row in source["items"]}
    cohort_by = {row["item_id"]: row for row in cohort["items"]}
    rows = []
    total_claims = covered_claims = selected_total = useful_total = complete = 0
    invalid = 0
    for receipt in receipts:
        item_id = receipt["item_id"]
        item = cohort_by[item_id]
        source_row = source_by[item_id]
        units = build_header_aware_evidence_units(
            source_row["excerpt"], fragment_number=1, candidate_id=item_id
        )
        by_id = {unit.unit_id: unit for unit in units}
        error = None
        try:
            ledger, unique_ids = validate_ledger_v2(
                json.loads(receipt["raw_text"]), set(by_id)
            )
        except (json.JSONDecodeError, ValueError) as exc:
            ledger, unique_ids = {}, []
            error = str(exc)
            invalid += 1
        selected = [by_id[unit_id] for unit_id in unique_ids]
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
                "valid": error is None,
                "validation_error": error,
                "facets_filled": sorted(ledger),
                "unique_selected_units": len(selected),
                "claims": len(claim_hits),
                "claims_covered": sum(claim_hits),
                "complete": all(claim_hits),
                "useful_units": sum(useful_hits),
                "selected_unit_receipts": [
                    {
                        "unit_id": unit.unit_id,
                        "source_spans": [list(span) for span in unit.source_spans],
                        "content_sha256": unit.content_sha256,
                    }
                    for unit in selected
                ],
            }
        )
    recall = covered_claims / total_claims
    precision = useful_total / max(1, selected_total)
    complete_rate = complete / len(rows)
    checks = {
        "claim_recall_gte_0_90": recall >= 0.90,
        "unit_precision_gte_0_80": precision >= 0.80,
        "question_complete_rate_gte_0_75": complete_rate >= 0.75,
        "invalid_outputs_zero": invalid == 0,
        "deterministic_second_replay": True,
    }
    passed = all(checks.values())
    body: dict[str, Any] = {
        "instrument": "s166_answer_archetype_ledger_transport_v1",
        "status": "LOCAL_GO_TO_FRESH_INDEPENDENT" if passed else "NO_GO",
        "population": {
            "questions": len(rows),
            "answer_points": total_claims,
            "target_question_overlap": 0,
            "model_calls": 0,
        },
        "metrics": {
            "claims_covered": covered_claims,
            "claim_recall": round(recall, 8),
            "selected_units": selected_total,
            "useful_units": useful_total,
            "unit_precision": round(precision, 8),
            "questions_complete": complete,
            "question_complete_rate": round(complete_rate, 8),
            "invalid_outputs": invalid,
        },
        "checks": checks,
        "rows": rows,
        "decision": {
            "s165_posthoc_credit": False,
            "fresh_independent_test": passed,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
        },
        "cost": {"model_calls": 0, "network_calls": 0, "usd": 0},
    }
    return {**body, "result_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    first = run()
    second = run()
    first_body = {key: value for key, value in first.items() if key != "result_sha256"}
    second_body = {key: value for key, value in second.items() if key != "result_sha256"}
    if first_body != second_body:
        raise RuntimeError("S166 replay is not deterministic")
    args.out.write_text(
        json.dumps(first, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": first["status"],
                **first["metrics"],
                "cost_usd": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
