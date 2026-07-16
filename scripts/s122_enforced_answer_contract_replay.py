"""Local S122 enforcement replay over the frozen 39-row S113 cohort.

The runner makes no model, network, retrieval, rerank or database calls.  Twelve
rows with no frozen answer remain explicitly not_measured and never enter an
enforcement or answer-delta denominator.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.answer_planner import (
    ANSWER_ENFORCEMENT_POLICY_S122,
    ANSWER_PLANNER_CONTRACT_S120,
    ANSWER_PLANNER_CONTRACT_S122,
    SOURCE_BOUND_RENDERER_S122,
    SOURCE_BOUND_RENDERER_S122_V1,
    apply_answer_planner,
    build_answer_conflicts,
    build_answer_plan,
)

CONTEXTS = ROOT / "evals" / "s113_full_contexts_freeze_v1.json"
BASELINE = ROOT / "evals" / "s113_full_answer_regression_v1.json"
S121 = ROOT / "evals" / "s121_s120_three_answer_probe_v1.json"
OUTPUT = ROOT / "evals" / "s122_enforced_answer_contract_replay_v1.json"

EXPECTED_INPUT_SHA256 = {
    "evals/s113_full_contexts_freeze_v1.json": "22f2026df5e5df65eb20470a56234b92bdec070ae2836304a7b9391006bf488d",
    "evals/s113_full_answer_regression_v1.json": "8fbfe4801f6c35c2447af9440c459b080e4405b76e2899f3a00e66b230497f69",
    "evals/s121_s120_three_answer_probe_v1.json": "dc0dc1e078fef615008f29f66bd2c2ca126485a18a5924dece481a9fe18a64c4",
}
NOT_MEASURED_QIDS = (
    "cat008",
    "cat012",
    "cat017",
    "cat019",
    "hp001",
    "hp002",
    "hp011",
    "hp012",
    "hp013",
    "hp014",
    "hp015",
    "hp018",
)
S121_OVERLAY_QIDS = ("hp005", "hp009", "hp017")
EXPECTED_ACTIONS = {
    "hp005": "pass",
    "hp009": "source_bound_reconstruction",
    "hp017": "fail_closed",
}
ACTION_ALLOWLIST = {
    "source_bound_reconstruction": ("hp009",),
    "fail_closed": ("hp017",),
}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(
    renderer_contract_version: str = SOURCE_BOUND_RENDERER_S122_V1,
) -> dict[str, Any]:
    paths = {str(path.relative_to(ROOT)).replace("\\", "/"): path for path in (CONTEXTS, BASELINE, S121)}
    actual_receipts = {name: _file_sha256(path) for name, path in paths.items()}
    if actual_receipts != EXPECTED_INPUT_SHA256:
        raise ValueError("S122 frozen input receipt drift")

    contexts_payload = _load(CONTEXTS)
    baseline_payload = _load(BASELINE)
    s121_payload = _load(S121)
    contexts = {row["qid"]: row for row in contexts_payload["rows"]}
    baseline = {row["qid"]: row for row in baseline_payload["rows"]}
    overlay = {row["qid"]: row for row in s121_payload["rows"]}
    if len(contexts) != 39 or set(contexts) != set(baseline):
        raise ValueError("S122 frozen 39-row population drift")
    if tuple(sorted(overlay)) != tuple(sorted(S121_OVERLAY_QIDS)):
        raise ValueError("S122 overlay qids drift")
    observed_nulls = tuple(sorted(qid for qid, row in baseline.items() if row.get("answer") is None))
    if observed_nulls != tuple(sorted(NOT_MEASURED_QIDS)):
        raise ValueError("S122 not_measured population drift")

    rows = []
    measured_actions: dict[str, str] = {}
    plan_delta_qids = []
    for qid in sorted(contexts):
        context_row = contexts[qid]
        question = context_row["question"]
        chunks = context_row["context"]
        s120_plan = build_answer_plan(
            question,
            chunks,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S120,
        )
        s122_plan = build_answer_plan(
            question,
            chunks,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        s120_packet = [item.to_dict() for item in s120_plan]
        s122_packet = [item.to_dict() for item in s122_plan]
        if s120_packet != s122_packet:
            plan_delta_qids.append(qid)

        if qid in NOT_MEASURED_QIDS:
            rows.append(
                {
                    "qid": qid,
                    "measurement": "not_measured",
                    "action": "not_measured",
                    "s120_plan": s120_packet,
                    "s122_plan": s122_packet,
                }
            )
            continue

        answer_source = "s121_overlay" if qid in overlay else "s113_baseline"
        answer = overlay[qid]["answer"] if qid in overlay else baseline[qid]["answer"]
        if not isinstance(answer, str):
            raise ValueError(f"measured answer missing for {qid}")
        conflicts = build_answer_conflicts(
            question,
            chunks,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        revised, metadata = apply_answer_planner(
            question,
            chunks,
            answer,
            mode="enforced",
            plan=s122_plan,
            conflicts=conflicts,
            renderer_contract_version=renderer_contract_version,
        )
        action = metadata["action"]
        measured_actions[qid] = action
        rows.append(
            {
                "qid": qid,
                "measurement": "measured",
                "answer_source": answer_source,
                "action": action,
                "answer_byte_identical": revised == answer,
                "answer_sha256_before": _text_sha256(answer),
                "answer_sha256_after": _text_sha256(revised),
                "query_core_coverage": metadata["query_core_coverage"],
                "s120_plan": s120_packet,
                "s122_plan": s122_packet,
                "conflicts": [item.to_dict() for item in conflicts],
                "initial_validation": metadata["initial_validation"],
                "initial_conflict_validation": metadata["initial_conflict_validation"],
                "final_validation": metadata["validation"],
                "final_conflict_validation": metadata["conflict_validation"],
                "answer_after": revised if qid in S121_OVERLAY_QIDS else None,
            }
        )

    action_histogram: dict[str, int] = {}
    for action in measured_actions.values():
        action_histogram[action] = action_histogram.get(action, 0) + 1
    unexpected_reconstruction = sorted(
        qid
        for qid, action in measured_actions.items()
        if action == "source_bound_reconstruction"
        and qid not in ACTION_ALLOWLIST["source_bound_reconstruction"]
    )
    unexpected_fail_closed = sorted(
        qid
        for qid, action in measured_actions.items()
        if action == "fail_closed" and qid not in ACTION_ALLOWLIST["fail_closed"]
    )
    non_identical_pass = sorted(
        row["qid"]
        for row in rows
        if row["action"] == "pass" and not row["answer_byte_identical"]
    )
    target_action_mismatches = {
        qid: {"expected": expected, "actual": measured_actions.get(qid)}
        for qid, expected in EXPECTED_ACTIONS.items()
        if measured_actions.get(qid) != expected
    }
    not_measured_action_leakage = sorted(
        row["qid"]
        for row in rows
        if row["measurement"] == "not_measured" and row["action"] != "not_measured"
    )
    checks = {
        "frozen_input_receipts": True,
        "total_rows_39": len(rows) == 39,
        "measured_answers_27": len(measured_actions) == 27,
        "not_measured_rows_12": sum(row["measurement"] == "not_measured" for row in rows) == 12,
        "not_measured_qids_exact": tuple(
            sorted(row["qid"] for row in rows if row["measurement"] == "not_measured")
        ) == tuple(sorted(NOT_MEASURED_QIDS)),
        "not_measured_action_leakage_zero": not not_measured_action_leakage,
        "target_actions_exact": not target_action_mismatches,
        "unexpected_reconstruction_zero": not unexpected_reconstruction,
        "unexpected_fail_closed_zero": not unexpected_fail_closed,
        "byte_identical_pass_answers": not non_identical_pass,
        "plan_delta_qids_allowlisted": set(plan_delta_qids) <= set(S121_OVERLAY_QIDS),
    }
    status = (
        "LOCAL_ENFORCED_ANSWER_CONTRACT_GO"
        if all(checks.values())
        else "LOCAL_ENFORCED_ANSWER_CONTRACT_NO_GO"
    )
    return {
        "instrument": "s122_enforced_answer_contract_replay_v1",
        "status": status,
        "authority": "local_deterministic_replay_only",
        "input_receipts": actual_receipts,
        "versions": {
            "planner": ANSWER_PLANNER_CONTRACT_S122,
            "enforcement_policy": ANSWER_ENFORCEMENT_POLICY_S122,
            "validator": "answer_contract_validator_s122_v1",
            "renderer": renderer_contract_version,
            "conflict_schema": "answer_conflict_s122_v1",
        },
        "counts": {
            "total_rows": len(rows),
            "measured_answers": len(measured_actions),
            "not_measured": len(NOT_MEASURED_QIDS),
            "actions": action_histogram,
            "plan_delta_qids": plan_delta_qids,
            "unexpected_reconstruction": unexpected_reconstruction,
            "unexpected_fail_closed": unexpected_fail_closed,
            "not_measured_action_leakage": not_measured_action_leakage,
        },
        "checks": checks,
        "target_action_mismatches": target_action_mismatches,
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "retrieval_calls": 0,
            "rerank_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
            "llm_judge_calls": 0,
        },
        "rows": rows,
        "limitations": [
            "Cached-answer replay is diagnostic and cannot move a fact to causal OK.",
            "This artifact does not authorize fresh generation, serving or deployment.",
        ],
    }


def main() -> int:
    report = build_report()
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], **report["counts"]}, ensure_ascii=False))
    return 0 if report["status"] == "LOCAL_ENFORCED_ANSWER_CONTRACT_GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
