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


def test_s207_no_go_is_sealed_before_planner_or_target():
    result = _json("evals/s207_decomposed_planner_holdout_result_v1.json")
    _assert_sealed(result)
    assert result["status"] == "NO_GO_S207_SUPPORT_MAPPING"
    assert result["frontier_calls"] == 9
    assert result["planner_calls"] == 0
    assert result["target_calls"] == 0
    assert result["target_prereg_authorized"] is False
    assert result["official_fact_credit"] == 0
    assert result["chunks_v3_status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert not (ROOT / "evals/s207_fable_support_review_v1.json").exists()
    assert not (ROOT / "evals/s207_terra_planner_receipts_v1.json").exists()


def test_s207_frontier_geometry_and_pixel_gold_are_complete():
    ledger = _json("evals/s207_frontier_call_ledger_v1.json")
    _assert_sealed(ledger)
    assert ledger["status"] == "COMPLETE"
    assert len(ledger["calls"]) == 9
    assert sum(row["provider"] == "sol" for row in ledger["calls"]) == 5
    assert sum(row["provider"] == "fable" for row in ledger["calls"]) == 4
    assert ledger["conservative_cost_usd"] == 13.08288
    assert ledger["calls"][-1]["call_label"] == "map:gold_facts_to_units"

    gold = _json("evals/s207_kidde_visual_gold_v1.json")
    _assert_sealed(gold)
    assert gold["status"] == "PIXEL_GOLD_PASS_UNINTEGRATED"
    assert len(gold["questions"]) == 3
    assert gold["official_fact_credit"] == 0
    for path in (
        "evals/s207_kidde_fable_review_of_sol_v1.json",
        "evals/s207_kidde_sol_review_of_fable_v1.json",
    ):
        review = _json(path)
        _assert_sealed(review)
        assert [row["verdict"] for row in review["review"]["reviews"]] == [
            "PASS",
            "PASS",
            "PASS",
        ]


def test_s207_failure_is_exactly_two_cross_page_scope_bindings():
    ledger = _json("evals/s207_frontier_call_ledger_v1.json")
    mapping = json.loads(ledger["calls"][-1]["raw_output"])
    packet = _json("evals/s207_decomposed_planner_holdout_packet_v1.json")
    gold = _json("evals/s207_kidde_visual_gold_v1.json")
    item_by_id = {item["canary_id"]: item for item in packet["items"]}
    gold_by_id = {item["canary_id"]: item for item in gold["questions"]}
    cross_page = []
    fact_count = 0
    for item_mapping in mapping["mappings"]:
        item_id = item_mapping["canary_id"]
        units = {
            unit["unit_id"]: unit for unit in item_by_id[item_id]["evidence_units"]
        }
        facts = {
            fact["fact_id"]: fact for fact in gold_by_id[item_id]["atomic_facts"]
        }
        for row in item_mapping["facts"]:
            fact_count += 1
            cited_page = facts[row["fact_id"]]["citation"]["page"]
            mapped_pages = {
                units[unit_id]["fragment_number"]
                for unit_id in row["support_unit_ids"]
            }
            if mapped_pages != {cited_page}:
                cross_page.append((item_id, row["fact_id"], mapped_pages))
    assert fact_count == 9
    assert cross_page == [
        ("kidde_mcp_isolation_parasitics", "F02", {15, 16}),
        ("kidde_mcp_isolation_parasitics", "F03", {15, 16}),
    ]

    analysis = _json("evals/s207_support_mapping_failure_analysis_v1.json")
    assert analysis["status"] == "RECORDED_NO_GO_NO_RETRY"
    assert analysis["mapping_audit"]["same_page_mappings"] == 7
    assert analysis["mapping_audit"]["cross_page_mappings"] == 2
    assert analysis["next_independent_line"]["fresh_holdout_required"] is True
    assert analysis["next_independent_line"]["same_cohort_retry"] is False
