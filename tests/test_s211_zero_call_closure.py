from __future__ import annotations

import json
from pathlib import Path

from src.rag.query_evidence_compiler import stable_sha


ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "evals/s211_query_evidence_compiler_zero_call_closure_v1.json"


def test_s211_provider_capability_rejection_is_sealed_as_zero_model_call():
    value = json.loads(CLOSURE.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    assert value["status"] == "NO_GO_ZERO_MODEL_CALL_PROVIDER_SCHEMA_UNSUPPORTED"
    assert value["execution"] == {
        "network_requests": 1,
        "model_calls": 0,
        "tokens": 0,
        "estimated_cost_usd": 0.0,
        "provider_retries": 0,
        "resume_attempts": 0,
    }
    assert value["first_failure"]["http_status"] == 400
    assert "maxItems" in value["first_failure"]["message"]
    assert value["causal_analysis"]["target_output_observed"] is False
    assert value["causal_analysis"]["target_specific"] is False


def test_s211_zero_call_moves_no_fact_and_has_no_execution_artifacts():
    value = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert value["credit"]["facts_moved_to_ok"] == 0
    assert value["decision"]["same_run_retry"] is False
    assert value["decision"]["next"] == (
        "S212_DETERMINISTIC_OVERFLOW_DROP_FRESH_PREREG"
    )
    for path in (
        "evals/s211_query_evidence_compiler_calls_v1.partial.jsonl",
        "evals/s211_query_evidence_compiler_receipts_v1.json",
        "evals/s211_query_evidence_compiler_score_v1.json",
    ):
        assert not (ROOT / path).exists()
