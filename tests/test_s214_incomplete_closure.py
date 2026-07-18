from __future__ import annotations

import json
from pathlib import Path

from src.rag.query_evidence_compiler import portable_file_sha
from src.rag.visual_gold import stable_sha


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "evals/s214_frontier_call_ledger_v1.json"
CLOSURE = ROOT / "evals/s214_kidde_multisource_incomplete_closure_v1.json"

DOWNSTREAM = (
    "s214_kidde_fable_generations_v1.json",
    "s214_kidde_sol_reviews_of_fable_v1.json",
    "s214_kidde_fable_reviews_of_sol_v1.json",
    "s214_kidde_pixel_gold_v1.json",
    "s214_kidde_sol_support_mappings_v1.json",
    "s214_kidde_fable_support_reviews_v1.json",
    "s214_kidde_supported_gold_v1.json",
)


def _assert_sealed(value: dict) -> None:
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected


def test_s214_interrupted_ledger_is_final_and_not_resumable():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    _assert_sealed(ledger)
    assert ledger["status"] == "INCOMPLETE_FINAL"
    assert len(ledger["calls"]) == 5
    assert [row["provider"] for row in ledger["calls"]] == [
        "sol",
        "sol",
        "sol",
        "sol",
        "fable",
    ]
    assert ledger["calls"][-1]["model"] == "claude-fable-5"
    assert ledger["calls"][-1]["status"] == "max_tokens"
    assert ledger["closure"] == {
        "reason": "FABLE_MAX_TOKENS_FIRST_AUTHOR_ITEM",
        "provider_retries": 0,
        "same_item_retry": False,
        "resume": False,
        "official_fact_credit": 0,
    }


def test_s214_incomplete_closure_is_fail_closed_and_awards_no_credit():
    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    _assert_sealed(closure)
    assert closure["status"] == "NO_GO_INCOMPLETE_FAIL_CLOSED"
    assert closure["failure"]["classification"] == "PROVIDER_COMPLETION_LIMIT"
    assert closure["failure"]["provider_status"] == "max_tokens"
    assert closure["failure"]["input_tokens"] == 62_668
    assert closure["failure"]["output_tokens"] == 8_000
    assert closure["failure"]["raw_output_chars"] == 8_723
    assert closure["execution"]["provider_retries"] == 0
    assert not closure["execution"]["same_item_retry"]
    assert not closure["execution"]["resume"]
    assert closure["execution"]["reciprocal_review_calls"] == 0
    assert closure["execution"]["support_calls"] == 0
    assert closure["credit"]["facts_moved_to_ok"] == 0
    assert closure["credit"]["facts_ok_after"] == 143
    assert closure["credit"]["denominator"] == 157
    assert closure["unattempted_items"] == [
        "kidde_2xa_interface_tradeoffs",
        "kidde_mcp_surface_kit_selection",
        "kidde_modulaser_role_selection",
    ]
    assert closure["inputs"]["closed_call_ledger_sha256"] == portable_file_sha(
        LEDGER
    )
    assert closure["invariants"]["chunks_v2"] == "ACTIVE_READ_ONLY"
    assert (
        closure["invariants"]["chunks_v3"]
        == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    )
    assert not closure["invariants"]["railway_merge_gate"]
    for name in DOWNSTREAM:
        assert not (ROOT / "evals" / name).exists()
