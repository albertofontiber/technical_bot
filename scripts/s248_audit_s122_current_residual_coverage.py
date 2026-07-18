#!/usr/bin/env python3
"""Replay S122 locally against the exact current synthesis-residual set."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.answer_planner import (  # noqa: E402
    ANSWER_PLANNER_CONTRACT_S122,
    build_answer_conflicts,
    build_answer_plan,
    enforce_answer_contract,
    enforceable_answer_plan,
)
from src.rag.visual_gold import write_json  # noqa: E402

GENERATION = ROOT / "evals/s235_direct_clause_bound_generation_packet_v1.json"
SCORE = ROOT / "evals/s235_direct_clause_bound_score_packet_v1.json"
TAXONOMY = ROOT / "evals/s243_synthesis_miss_causal_taxonomy_v1.yaml"
OUTPUT = ROOT / "evals/s248_s122_current_residual_coverage_v1.json"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report() -> dict[str, Any]:
    generation = _json(GENERATION)
    score = _json(SCORE)
    taxonomy = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    score_by_qid = {str(item["qid"]): item for item in score["items"]}
    taxonomy_keys = {
        (str(row["qid"]), str(row["obligation_id"])) for row in taxonomy["rows"]
    }
    if len(taxonomy_keys) != 12:
        raise ValueError("S243 population drift")

    rows: list[dict[str, Any]] = []
    residual_plan_hits = 0
    residual_enforced_hits = 0
    fail_closed_questions = 0
    changed_questions = 0
    for item in generation["items"]:
        qid = str(item["qid"])
        scored = score_by_qid[qid]
        residual_ids = {str(value) for value in scored["residual_obligation_ids"]}
        if {(qid, value) for value in residual_ids} - taxonomy_keys:
            raise ValueError(f"residual identity drift: {qid}")

        plan = build_answer_plan(
            str(item["question"]),
            item["context"],
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        enforced = enforceable_answer_plan(
            plan, planner_contract_version=ANSWER_PLANNER_CONTRACT_S122
        )
        conflicts = build_answer_conflicts(
            str(item["question"]),
            item["context"],
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        answer_after, receipt = enforce_answer_contract(
            str(item["question"]),
            str(scored["canonical_answer"]),
            plan,
            conflicts,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        plan_ids = {row.obligation_id for row in plan}
        enforced_ids = {row.obligation_id for row in enforced}
        plan_hits = sorted(residual_ids & plan_ids)
        enforced_hits = sorted(residual_ids & enforced_ids)
        residual_plan_hits += len(plan_hits)
        residual_enforced_hits += len(enforced_hits)
        changed = answer_after != scored["canonical_answer"]
        changed_questions += int(changed)
        fail_closed = receipt["action"] == "fail_closed"
        fail_closed_questions += int(fail_closed)
        rows.append(
            {
                "qid": qid,
                "residual_obligation_ids": sorted(residual_ids),
                "s122_plan": [row.to_dict() for row in plan],
                "s122_enforced_plan": [row.to_dict() for row in enforced],
                "residual_plan_hits": plan_hits,
                "residual_enforced_hits": enforced_hits,
                "enforcement_action": receipt["action"],
                "query_core_coverage": receipt["query_core_coverage"],
                "canonical_answer_changed": changed,
                "answer_chars_before": len(str(scored["canonical_answer"])),
                "answer_chars_after": len(answer_after),
            }
        )

    candidate = residual_enforced_hits >= 1 and fail_closed_questions == 0
    return {
        "schema": "s248_s122_current_residual_coverage_v1",
        "status": "S122_NOT_APPLICABLE_TO_CURRENT_RESIDUALS",
        "population": {"questions": len(rows), "synthesis_residuals": 12},
        "measurement": {
            "residual_plan_coverage": residual_plan_hits,
            "residual_enforced_coverage": residual_enforced_hits,
            "fail_closed_questions": fail_closed_questions,
            "canonical_answers_changed": changed_questions,
        },
        "candidate_gate_passed": candidate,
        "rows": rows,
        "decision": {
            "enable_s122_enforced": False,
            "extend_with_s141_target_specific_kinds": False,
            "paid_calls_authorized": False,
            "facts_moved_to_ok": 0,
            "reason": (
                "S122 enforces none of the twelve residual obligations and fail-closes "
                "hp017 on unrelated default-rule obligations."
            ),
        },
        "resources": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
    }


def main() -> int:
    report = build_report()
    expected = {
        "residual_plan_coverage": 1,
        "residual_enforced_coverage": 0,
        "fail_closed_questions": 1,
        "canonical_answers_changed": 1,
    }
    if report["measurement"] != expected:
        raise ValueError(f"unexpected S122 replay: {report['measurement']}")
    if report["candidate_gate_passed"]:
        raise ValueError("S122 must not pass the current-residual gate")
    write_json(OUTPUT, report)
    print(json.dumps({"status": report["status"], **report["measurement"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

