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


def test_s208_no_go_is_sealed_before_planner_or_target():
    result = _json("evals/s208_multipage_planner_holdout_result_v1.json")
    _assert_sealed(result)
    assert result["status"] == "NO_GO_S208_SUPPORT_MAPPING"
    assert result["frontier_calls"] == 10
    assert result["planner_calls"] == 0
    assert result["target_calls"] == 0
    assert result["target_prereg_authorized"] is False
    assert result["official_fact_credit"] == 0
    assert result["chunks_v3_status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert result["railway_merge_gate"] is False
    assert not (ROOT / "evals/s208_fable_support_review_v1.json").exists()
    assert not (ROOT / "evals/s208_terra_planner_receipts_v1.json").exists()


def test_s208_frontier_geometry_and_pixel_gold_completed():
    ledger = _json("evals/s208_frontier_call_ledger_v1.json")
    _assert_sealed(ledger)
    assert ledger["status"] == "COMPLETE"
    assert len(ledger["calls"]) == 10
    assert sum(row["provider"] == "sol" for row in ledger["calls"]) == 5
    assert sum(row["provider"] == "fable" for row in ledger["calls"]) == 5
    assert ledger["conservative_cost_usd"] == 26.72139
    assert ledger["calls"][-1]["call_label"] == "review:support_mapping"

    gold = _json("evals/s208_kidde_visual_gold_v1.json")
    _assert_sealed(gold)
    assert gold["status"] == "PIXEL_GOLD_PASS_UNINTEGRATED"
    assert len(gold["questions"]) == 3
    assert sum(len(row["atomic_facts"]) for row in gold["questions"]) == 20
    assert gold["official_fact_credit"] == 0


def test_s208_failure_is_positive_notes_in_blocking_issues_field():
    ledger = _json("evals/s208_frontier_call_ledger_v1.json")
    review = json.loads(ledger["calls"][-1]["raw_output"])
    assert [row["verdict"] for row in review["reviews"]] == ["PASS"] * 3
    fact_rows = [fact for row in review["reviews"] for fact in row["fact_reviews"]]
    assert len(fact_rows) == 20
    assert all(not row["blocking_issues"] for row in review["reviews"])
    assert all(
        fact[field] is True
        for fact in fact_rows
        for field in (
            "pixel_supported",
            "unit_text_supported",
            "minimal_complete",
            "citation_pages_complete",
            "alternative_paths_complete",
        )
    )
    assert all(len(fact["issues"]) == 1 for fact in fact_rows)

    analysis = _json("evals/s208_support_review_failure_analysis_v1.json")
    assert analysis["status"] == "RECORDED_NO_GO_NO_RETRY"
    assert analysis["failure"]["fact_issue_lists_nonempty"] == 20
    assert analysis["interpretation"]["planner_hypothesis"] == "UNMEASURED"
    assert analysis["next_independent_line"]["fresh_holdout_required"] is True
    assert analysis["next_independent_line"]["reuse_s208_questions_facts_or_mappings"] is False
