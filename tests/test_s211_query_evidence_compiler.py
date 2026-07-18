from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.s210_run_query_evidence_compiler import (
    conservative_execution_upper_bound_usd,
)
from src.rag.query_evidence_compiler import portable_file_sha, stable_sha


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals/s211_query_evidence_compiler_prereg_v1.yaml"
PREFLIGHT = ROOT / "evals/s211_query_evidence_compiler_preflight_v1.json"
PERMIT = ROOT / "evals/s211_query_evidence_compiler_execution_permit_v1.yaml"


def test_s211_prereg_is_only_the_generic_schema_validator_equivalence_delta():
    value = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    assert value["status"] == "FROZEN_BEFORE_PAID_EXECUTION"
    assert value["main_sha"] == "dd7d35b214f8913e89c614bf2d534327edcd926b"
    assert value["contract_delta"] == {
        "only_change": "provider_claims_array_maxItems_equals_local_limit",
        "provider_claims_max_items": 16,
        "local_claim_limit": 16,
        "synthetic_boundary_tests": ["16_accept", "17_reject"],
        "prompts_changed": False,
        "selection_changed": False,
        "gates_changed": False,
        "prior_outputs_reused": False,
    }
    assert value["population"]["target_cohort_prior_partial_exposure"] is True
    assert value["population"]["prior_partial_result_scored"] is False
    assert value["population"]["fresh_generalization_evidence"] is False
    assert value["execution"]["paid_calls_max"] == 202
    assert value["execution"]["provider_retries"] == 0
    assert value["invariants"]["chunks_v3"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"


def test_s211_every_preregistered_input_uses_portable_frozen_hashes():
    value = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    for spec in value["frozen_inputs"].values():
        assert portable_file_sha(ROOT / spec["path"]) == spec["sha256"]


def test_s211_preflight_is_zero_call_complete_and_explicitly_not_fresh():
    value = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    assert value["status"] == "GO_ZERO_CALL_PREFLIGHT"
    assert all(value["checks"].values())
    assert value["call_geometry"] == {
        "extractor_calls": 130,
        "planner_calls": 36,
        "verifier_calls": 36,
        "total_paid_calls_max": 202,
        "provider_retries": 0,
    }
    assert value["lineage"] == {
        "engine": "S210_FROZEN_EXECUTION_ENGINE",
        "contract_delta": "PROVIDER_CLAIMS_MAX_ITEMS_EQUALS_LOCAL_LIMIT_16",
        "s210_outputs_reused": False,
        "target_cohort_prior_partial_exposure": True,
        "fresh_generalization_evidence": False,
    }
    assert value["cost"] == {"model_calls": 0, "network_calls": 0, "usd": 0}


def test_s211_worst_case_cost_remains_below_the_sealed_internal_ceiling():
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    prices = {
        "extractor": {"input": 2.0, "output": 10.0},
        "planner": {"input": 2.5, "output": 15.0},
    }
    assert conservative_execution_upper_bound_usd(preflight, prices) == 22.948314


def test_s211_is_unwired_and_has_no_execution_artifacts_before_frontier_gate():
    assert "query_evidence_compiler_v2" not in (
        ROOT / "src/rag/generator.py"
    ).read_text(encoding="utf-8")
    assert "query_evidence_compiler_v2" not in (
        ROOT / "src/bot/telegram_bot.py"
    ).read_text(encoding="utf-8")
    for path in (
        "evals/s211_query_evidence_compiler_calls_v1.partial.jsonl",
        "evals/s211_query_evidence_compiler_receipts_v1.json",
        "evals/s211_query_evidence_compiler_score_v1.json",
    ):
        assert not (ROOT / path).exists()


def test_s211_permit_requires_both_frontier_passes_and_frozen_contract():
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    assert permit["status"] == "EXECUTION_GO_PAID_BOUNDED_NO_RETRY"
    assert permit["preflight_sha256"] == portable_file_sha(PREFLIGHT)
    assert permit["frontier_rerun_integrity_gate"]["principal"] == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "verdict": "PASS",
    }
    assert permit["frontier_rerun_integrity_gate"]["independent"] == {
        "model": "claude-fable-5",
        "verdict": "PASS",
    }
    assert permit["frontier_rerun_integrity_gate"]["blockers"] == 0
    assert permit["contract_delta"]["prior_s210_outputs_reused"] is False
    assert permit["contract_delta"]["fresh_generalization_evidence"] is False
    assert permit["conservative_full_run_upper_bound_usd"] < 75
    for spec in permit["frozen_artifacts"]:
        assert portable_file_sha(ROOT / spec["path"]) == spec["sha256"]
