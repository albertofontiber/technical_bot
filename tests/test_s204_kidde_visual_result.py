from __future__ import annotations

import json
from pathlib import Path

from src.rag.visual_gold import stable_sha


ROOT = Path(__file__).resolve().parents[1]


def _sealed(name: str):
    value = json.loads((ROOT / "evals" / name).read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    return value


def test_s204_execution_is_complete_bounded_and_no_go():
    ledger = _sealed("s204_kidde_frontier_call_ledger_v1.json")
    assert ledger["status"] == "COMPLETE"
    assert len(ledger["calls"]) == 8
    assert [row["provider"] for row in ledger["calls"]] == [
        "sol",
        "sol",
        "sol",
        "fable",
        "fable",
        "fable",
        "sol",
        "fable",
    ]
    assert ledger["conservative_cost_usd"] == 15.729345
    assert all(row["status"] in {"completed", "end_turn"} for row in ledger["calls"])

    result = _sealed("s204_kidde_visual_canary_result_v1.json")
    assert result["status"] == "NO_GO_VISUAL_GOLD"
    assert result["calls"] == 8
    assert result["generation"] == {"sol_valid": 3, "fable_valid": 3}
    assert result["cross_review"] == {
        "sol_of_fable_all_pass": False,
        "fable_of_sol_all_pass": True,
    }
    assert result["official_fact_credit"] == 0
    assert result["bot_evaluation_opened"] is False
    assert result["chunks_v3_status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"


def test_s204_failure_is_real_and_not_the_nonblocking_note_bug():
    sol = _sealed("s204_kidde_sol_review_of_fable_v1.json")["review"]
    fable = _sealed("s204_kidde_fable_review_of_sol_v1.json")["review"]
    assert [row["verdict"] for row in sol["reviews"]] == ["FAIL", "PASS", "PASS"]
    assert [row["verdict"] for row in fable["reviews"]] == ["PASS", "PASS", "PASS"]
    failed = sol["reviews"][0]
    assert failed["gold_complete"] is False
    assert len(failed["blocking_issues"]) == 2
    assert failed["nonblocking_notes"] == []
    assert all(
        fact["supported"] and fact["page_correct"] and fact["answer_entails"]
        for fact in failed["fact_verdicts"]
    )
    assert all(
        row["blocking_issues"] == [] and row["verdict"] == "PASS"
        for row in fable["reviews"]
    )


def test_s204_diagnosis_forbids_salvage_and_moves_zero_facts():
    diagnosis = json.loads(
        (ROOT / "evals/s204_kidde_visual_canary_diagnosis_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert diagnosis["status"] == "CLOSED_NO_GO_VISUAL_GOLD"
    assert diagnosis["contract_observations"]["review_schema_false_block"] is False
    assert diagnosis["contract_observations"]["clean_symmetric_pairs"] == 2
    assert diagnosis["contract_observations"]["clean_principal_candidates"] == 3
    assert diagnosis["decision"] == {
        "same_cohort_retry": False,
        "repair_or_salvage": False,
        "postselect_two_clean_pairs": False,
        "official_gold_added": 0,
        "official_fact_credit": 0,
        "bot_evaluation_opened": False,
    }
