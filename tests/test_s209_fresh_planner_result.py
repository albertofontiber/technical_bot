from __future__ import annotations

import json
from pathlib import Path

from src.rag.visual_gold import stable_sha


ROOT = Path(__file__).resolve().parents[1]


def _json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _assert_sealed(value):
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected


def test_s209_no_go_is_sealed_before_fable_planner_or_target():
    result = _json("evals/s209_fresh_planner_holdout_result_v1.json")
    _assert_sealed(result)
    assert result["status"] == "NO_GO_S209_GOLD"
    assert result["reason"] == (
        "sol candidate invalid: candidate marked source insufficient"
    )
    assert result["frontier_calls"] == 2
    assert result["planner_calls"] == 0
    assert result["target_calls"] == 0
    assert result["target_prereg_authorized"] is False
    assert result["official_fact_credit"] == 0
    assert result["conservative_frontier_cost_usd"] == 1.54833
    assert result["chunks_v3_status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert result["railway_merge_gate"] is False

    for path in (
        "evals/s209_kidde_fable_generations_v1.json",
        "evals/s209_kidde_sol_review_v1.json",
        "evals/s209_kidde_fable_review_v1.json",
        "evals/s209_kidde_visual_gold_v1.json",
        "evals/s209_sol_support_mapping_v1.json",
        "evals/s209_fable_support_review_v1.json",
        "evals/s209_terra_planner_receipts_v1.json",
    ):
        assert not (ROOT / path).exists()


def test_s209_ledger_proves_early_stop_and_semantic_overlap():
    ledger = _json("evals/s209_frontier_call_ledger_v1.json")
    _assert_sealed(ledger)
    assert ledger["status"] == "COMPLETE"
    assert ledger["conservative_cost_usd"] == 1.54833
    assert [row["call_label"] for row in ledger["calls"]] == [
        "generate:kidde_dp3020_detection_discrimination",
        "generate:kidde_nc_maintenance_schedule",
    ]
    assert {row["provider"] for row in ledger["calls"]} == {"sol"}
    assert {row["model"] for row in ledger["calls"]} == {"gpt-5.6-sol"}
    assert {row["reasoning_effort"] for row in ledger["calls"]} == {"xhigh"}

    candidates = [json.loads(row["raw_output"]) for row in ledger["calls"]]
    assert candidates[0]["adequacy"] == "SUFFICIENT"
    assert len(candidates[0]["atomic_facts"]) == 5
    assert candidates[1]["adequacy"] == "INSUFFICIENT"
    assert candidates[1]["question"] == ""
    assert candidates[1]["atomic_facts"] == []
    assert "cobertura existente" in candidates[1]["notes"]


def test_s209_analysis_closes_the_planner_holdout_line_without_credit():
    analysis = _json("evals/s209_gold_failure_analysis_v1.json")
    assert analysis["status"] == "RECORDED_NO_GO_NO_RETRY"
    assert analysis["decision"] == "NO_GO_S209_GOLD"
    assert analysis["execution"]["official_fact_credit"] == 0
    assert analysis["execution"]["fable_calls"] == 0
    assert analysis["interpretation"]["planner_hypothesis"] == "UNMEASURED"
    assert analysis["interpretation"]["same_cohort_retry"] is False
    assert analysis["interpretation"]["replacement_cohort"] is False
    assert (
        analysis["next_independent_line"]["planner_holdout_line"]
        == "ABANDON_AFTER_PREREGISTERED_FINAL_FRESH_COHORT"
    )
    assert analysis["next_independent_line"]["new_kidde_question_generation"] is False
    assert analysis["invariants"]["chunks_v2"] == "ACTIVE"
    assert (
        analysis["invariants"]["chunks_v3"]
        == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    )
