from __future__ import annotations

import json
from pathlib import Path

from src.rag.query_evidence_compiler import portable_file_sha, stable_sha


ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "evals/s210_query_evidence_compiler_incomplete_closure_v1.json"
PARTIAL = ROOT / "evals/s210_query_evidence_compiler_calls_v1.partial.jsonl"


def test_s210_incomplete_run_is_sealed_at_first_generic_contract_violation():
    value = json.loads(CLOSURE.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    assert value["status"] == "NO_GO_INCOMPLETE_FAIL_CLOSED"
    assert value["execution"] == {
        "sealed_calls": 126,
        "planned_calls": 202,
        "completed_answer_rows": 19,
        "planned_answer_rows": 36,
        "role_calls": {"extractor": 88, "planner": 19, "verifier": 19},
        "model_calls": {"claude-haiku-4-5-20251001": 88, "gpt-5.6-terra": 38},
        "provider_retries": 0,
        "resume_attempts": 0,
        "estimated_cost_usd": 0.958119,
    }
    assert value["inputs"]["partial_journal_sha256"] == portable_file_sha(PARTIAL)
    assert value["first_failure"]["observed_claims"] == 17
    assert value["first_failure"]["local_claim_limit"] == 16
    assert value["first_failure"]["provider_schema_claims_max_items"] is None
    assert value["causal_analysis"]["category"] == "SCHEMA_VALIDATOR_BOUND_DRIFT"
    assert value["causal_analysis"]["target_specific"] is False


def test_s210_incomplete_run_moves_no_fact_and_cannot_be_resumed_or_scored():
    value = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert value["credit"]["facts_moved_to_ok"] == 0
    assert value["credit"]["canonical_facts_ok"] == 143
    assert value["credit"]["relation_projection_allowed"] is False
    assert value["decision"]["same_run_resume"] is False
    assert value["decision"]["same_run_retry"] is False
    assert value["decision"]["partial_result_scoring"] is False
    assert value["decision"]["next"] == (
        "S211_SCHEMA_VALIDATOR_BOUND_EQUIVALENCE_FRESH_PREREG"
    )
    assert not (
        ROOT / "evals/s210_query_evidence_compiler_receipts_v1.json"
    ).exists()
    assert not (ROOT / "evals/s210_query_evidence_compiler_score_v1.json").exists()
