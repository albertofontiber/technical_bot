from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.s165_answer_archetype_ledger import stable_sha


ROOT = Path(__file__).resolve().parents[1]


def test_executed_no_go_is_sealed_receipted_and_closes_lane() -> None:
    paths = {
        "gate": ROOT / "evals/s200_point_first_replay_gate_v1.json",
        "cohort": ROOT / "evals/s200_point_first_replay_screened_cohort_v1.json",
        "receipts": ROOT / "evals/s200_point_author_receipts_v1.json",
        "diagnosis": ROOT / "evals/s200_point_first_replay_diagnosis_v1.json",
    }
    for path in paths.values():
        assert b"\r\n" not in path.read_bytes()

    gate = json.loads(paths["gate"].read_text(encoding="utf-8"))
    result_sha = gate.pop("result_sha256")
    assert result_sha == stable_sha(gate)
    assert gate["status"] == "NO_GO_POINT_PLAN_STRUCTURAL_GATE"
    assert gate["population_checks"]["eligible_items_gte_12"] is False
    assert gate["population_checks"]["eligible_manufacturers_gte_12"] is False
    assert gate["cost"]["total_usd"] == 0.144517
    assert gate["cost"]["point_screen_usd"] == 0.0
    assert gate["cost"]["question_writer_usd"] == 0.0
    assert gate["decision"]["official_fact_credit"] == 0
    assert gate["decision"]["diagnostic_facts_moved_to_ok"] == 0

    cohort = json.loads(paths["cohort"].read_text(encoding="utf-8"))
    cohort_sha = cohort.pop("cohort_sha256")
    assert cohort_sha == stable_sha(cohort)
    receipt_sha = hashlib.sha256(paths["receipts"].read_bytes()).hexdigest()
    receipt_key = paths["receipts"].relative_to(ROOT).as_posix()
    assert cohort["receipt_hashes"][receipt_key] == receipt_sha

    diagnosis = json.loads(paths["diagnosis"].read_text(encoding="utf-8"))
    assert diagnosis["status"] == "CLOSED_POINT_FIRST_FRESH_GENERALIZATION_LANE"
    assert diagnosis["lane_closure"]["further_point_first_cohorts"] == 0
    assert diagnosis["facts"]["current_comparable"] == {
        "denominator": 157,
        "ok": 143,
        "synthesis_miss": 12,
        "retrieval_miss": 2,
    }
    assert diagnosis["chunks_v3_lane"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert diagnosis["railway_deploy_gate"] is False
