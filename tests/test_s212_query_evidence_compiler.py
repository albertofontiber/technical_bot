from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.s210_run_query_evidence_compiler import conservative_execution_upper_bound_usd
from src.rag.query_evidence_compiler import portable_file_sha, stable_sha


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals/s212_query_evidence_compiler_prereg_v1.yaml"
PREFLIGHT = ROOT / "evals/s212_query_evidence_compiler_preflight_v1.json"
PERMIT = ROOT / "evals/s212_query_evidence_compiler_execution_permit_v1.yaml"


def test_s212_prereg_changes_only_generic_deterministic_overflow_policy():
    value = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    assert value["status"] == "FROZEN_BEFORE_PAID_EXECUTION"
    assert value["main_sha"] == "c9f1ced740fc78b4b13ec520974e859cbc8db1d5"
    assert value["contract_delta"] == {
        "only_change": "deterministic_batched_full_binding",
        "provider_schema": "s210_supported_without_maxItems",
        "retained_claims": "all_in_provider_order",
        "binding_batch_size": 16,
        "excess_claims_audited_from_raw_journal": True,
        "first16_drop_design_rejected_by_sol": True,
        "prompts_changed": False,
        "selection_changed": False,
        "gates_changed": False,
        "prior_outputs_reused": False,
    }
    assert value["population"]["s211_target_outputs_observed"] is False
    assert value["population"]["fresh_generalization_evidence"] is False
    assert value["execution"]["paid_calls_max"] == 202
    assert value["execution"]["provider_retries"] == 0
    assert value["invariants"]["chunks_v3"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"


def test_s212_frozen_inputs_are_portable_and_exact():
    value = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    for spec in value["frozen_inputs"].values():
        assert portable_file_sha(ROOT / spec["path"]) == spec["sha256"]


def test_s212_zero_call_preflight_is_complete_bounded_and_not_fresh():
    value = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    assert value["status"] == "GO_ZERO_CALL_PREFLIGHT"
    assert all(value["checks"].values())
    assert value["call_geometry"]["total_paid_calls_max"] == 202
    assert value["lineage"] == {
        "engine": "S210_FROZEN_EXECUTION_ENGINE",
        "contract_delta": "PROVIDER_SUPPORTED_SCHEMA_PLUS_LOCAL_BATCHED_FULL_BINDING",
        "s210_outputs_reused": False,
        "s211_target_outputs_observed": False,
        "target_cohort_prior_partial_exposure": True,
        "fresh_generalization_evidence": False,
    }
    prices = {
        "extractor": {"input": 2.0, "output": 10.0},
        "planner": {"input": 2.5, "output": 15.0},
    }
    assert conservative_execution_upper_bound_usd(value, prices) == 22.948314


def test_s212_remains_unwired_after_result_gate():
    assert "query_evidence_compiler_v3" not in (
        ROOT / "src/rag/generator.py"
    ).read_text(encoding="utf-8")
    assert "query_evidence_compiler_v3" not in (
        ROOT / "src/bot/telegram_bot.py"
    ).read_text(encoding="utf-8")


def test_s212_permit_rejects_first16_and_requires_dual_pass_full_binding():
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    assert permit["status"] == "EXECUTION_GO_PAID_BOUNDED_NO_RETRY"
    assert permit["preflight_sha256"] == portable_file_sha(PREFLIGHT)
    assert permit["frontier_design_gate"]["rejected_v1"]["principal"]["verdict"] == "FAIL"
    assert permit["frontier_design_gate"]["rejected_v1"]["executable"] is False
    corrected = permit["frontier_design_gate"]["corrected_v2"]
    assert corrected["principal"] == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "verdict": "PASS",
    }
    assert corrected["independent"] == {
        "model": "claude-fable-5",
        "verdict": "PASS",
    }
    assert corrected["blockers"] == 0
    assert corrected["executable"] is True
    assert permit["contract_delta"]["claims_dropped_for_legacy_limit"] == 0
    assert permit["conservative_full_run_upper_bound_usd"] < 75
    for spec in permit["frozen_artifacts"]:
        assert portable_file_sha(ROOT / spec["path"]) == spec["sha256"]
