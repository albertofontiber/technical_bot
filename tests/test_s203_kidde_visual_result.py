from __future__ import annotations

import json

from scripts.s203_run_kidde_visual_canary import stable_sha


def _sealed(path: str):
    value = json.loads(open(path, encoding="utf-8").read())
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    return value


def test_s203_frontier_execution_is_complete_and_bounded_no_go():
    ledger = _sealed("evals/s203_kidde_frontier_call_ledger_v1.json")
    assert ledger["status"] == "COMPLETE"
    assert len(ledger["calls"]) == 8
    assert [row["provider"] for row in ledger["calls"]] == [
        "sol", "sol", "sol", "fable", "fable", "fable", "sol", "fable"
    ]
    assert ledger["conservative_cost_usd"] == 14.07876
    assert all(row["status"] in {"completed", "end_turn"} for row in ledger["calls"])

    result = _sealed("evals/s203_kidde_visual_canary_result_v1.json")
    assert result["status"] == "NO_GO_VISUAL_GOLD"
    assert result["calls"] == 8
    assert result["generation"] == {"sol_valid": 3, "fable_valid": 3}
    assert result["cross_review"] == {
        "sol_of_fable_all_pass": False,
        "fable_of_sol_all_pass": False,
    }
    assert result["official_fact_credit"] == 0
    assert result["bot_evaluation_opened"] is False
    assert result["chunks_v3_status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"


def test_s203_review_outcomes_and_diagnosis_are_not_postselected():
    sol = _sealed("evals/s203_kidde_sol_review_of_fable_v1.json")["review"]
    fable = _sealed("evals/s203_kidde_fable_review_of_sol_v1.json")["review"]
    assert [row["verdict"] for row in sol["reviews"]] == ["FAIL", "PASS", "PASS"]
    assert [row["verdict"] for row in fable["reviews"]] == ["PASS", "PASS", "PASS"]
    assert len(fable["reviews"][1]["issues"]) == 2
    assert all(
        fact["supported"] and fact["page_correct"] and fact["answer_entails"]
        for fact in fable["reviews"][1]["fact_verdicts"]
    )

    diagnosis = json.loads(
        open("evals/s203_kidde_visual_canary_diagnosis_v1.json", encoding="utf-8").read()
    )
    body = dict(diagnosis)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    assert diagnosis["status"] == "CLOSED_NO_GO_VISUAL_GOLD"
    assert diagnosis["decision"]["same_cohort_retry"] is False
    assert diagnosis["decision"]["salvage_clean_pair"] is False
    assert diagnosis["interpretation"]["diagnostic_facts_moved_to_ok"] == 0
