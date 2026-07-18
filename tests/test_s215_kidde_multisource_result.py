from __future__ import annotations

import json
from pathlib import Path

from src.rag.multisource_visual_gold import principal_publication_gate
from src.rag.visual_gold import stable_sha


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "evals/s215_frontier_call_ledger_v1.json"
GENERATIONS = ROOT / "evals/s215_kidde_fable_generations_v1.json"
SOL_REVIEWS = ROOT / "evals/s215_kidde_sol_reviews_of_fable_v1.json"
FABLE_REVIEWS = ROOT / "evals/s215_kidde_fable_reviews_of_sol_v1.json"
RESULT = ROOT / "evals/s215_kidde_multisource_continuation_result_v1.json"
ANALYSIS = ROOT / "evals/s215_kidde_multisource_failure_analysis_v1.json"


def _sealed(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    return value


def test_s215_call_geometry_is_complete_exact_model_and_zero_retry():
    ledger = _sealed(LEDGER)
    assert ledger["status"] == "COMPLETE"
    assert ledger["conservative_cost_usd"] == 17.78412
    assert len(ledger["calls"]) == 9
    assert [row["provider"] for row in ledger["calls"]] == [
        "fable",
        "fable",
        "fable",
        "sol",
        "fable",
        "sol",
        "fable",
        "sol",
        "fable",
    ]
    for row in ledger["calls"]:
        if row["provider"] == "sol":
            assert row["model"] == "gpt-5.6-sol"
            assert row["reasoning_effort"] == "xhigh"
            assert row["status"] == "completed"
        else:
            assert row["model"] == "claude-fable-5"
            assert row["status"] == "end_turn"


def test_s215_three_valid_authors_yield_only_two_principal_publication_passes():
    generations = _sealed(GENERATIONS)
    sol_reviews = _sealed(SOL_REVIEWS)
    fable_reviews = _sealed(FABLE_REVIEWS)
    assert generations["status"] == "COMPLETE"
    assert len(generations["items"]) == 3
    assert all(row["validation_status"] == "VALID" for row in generations["items"])
    assert [row["review"]["reviews"][0]["verdict"] for row in sol_reviews["items"]] == [
        "FAIL",
        "FAIL",
        "FAIL",
    ]
    assert [row["review"]["reviews"][0]["verdict"] for row in fable_reviews["items"]] == [
        "PASS",
        "PASS",
        "PASS",
    ]
    publication = []
    for sol_row, fable_row in zip(sol_reviews["items"], fable_reviews["items"]):
        assert sol_row["canary_id"] == fable_row["canary_id"]
        if principal_publication_gate(fable_row["review"], sol_row["review"]):
            publication.append(sol_row["canary_id"])
    assert publication == [
        "kidde_2xa_interface_tradeoffs",
        "kidde_modulaser_role_selection",
    ]


def test_s215_result_and_analysis_are_fail_closed_with_zero_credit():
    result = _sealed(RESULT)
    analysis = _sealed(ANALYSIS)
    assert result["status"] == "NO_GO_S215_PIXEL_REVIEW"
    assert result["published_items"] == [
        "kidde_2xa_interface_tradeoffs",
        "kidde_modulaser_role_selection",
    ]
    assert result["frontier_calls"] == 9
    assert result["conservative_frontier_cost_usd"] == 17.78412
    assert result["provider_retries"] == 0
    assert result["official_fact_credit"] == 0
    assert result["official_denominator_change"] == 0
    assert analysis["status"] == "FINAL_NO_GO_S215_THREE_OF_THREE"
    assert analysis["cause"]["actual_published_items"] == 2
    assert analysis["credit"]["facts_ok_after"] == 143
    assert analysis["credit"]["facts_moved_to_ok"] == 0
    assert analysis["decision"]["fable_convergence_round"] is False
    assert analysis["decision"]["output_conditioned_top_up_item"] is False
    assert analysis["invariants"]["chunks_v2"] == "ACTIVE_READ_ONLY"
    assert (
        analysis["invariants"]["chunks_v3"]
        == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    )
    for name in (
        "s215_kidde_pixel_gold_v1.json",
        "s215_kidde_sol_support_mappings_v1.json",
        "s215_kidde_fable_support_reviews_v1.json",
        "s215_kidde_supported_gold_v1.json",
    ):
        assert not (ROOT / "evals" / name).exists()
