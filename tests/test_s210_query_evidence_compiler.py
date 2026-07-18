from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from scripts.s210_run_query_evidence_compiler import (
    MAX_PLANNER_PROMPT_BYTES,
    conservative_execution_upper_bound_usd,
)
from src.rag.query_evidence_compiler import stable_sha


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals/s210_query_evidence_compiler_prereg_v1.yaml"
PREFLIGHT = ROOT / "evals/s210_query_evidence_compiler_preflight_v1.json"
PERMIT = ROOT / "evals/s210_query_evidence_compiler_execution_permit_v1.yaml"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_s210_prereg_freezes_exact_models_geometry_and_98_gate():
    value = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    assert value["status"] == "FROZEN_BEFORE_PAID_EXECUTION"
    assert value["models"]["principal_reviewer"] == {
        "provider": "openai",
        "id": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
    }
    assert value["models"]["independent_reviewer"]["id"] == "claude-fable-5"
    assert value["models"]["planner"]["id"] == "gpt-5.6-terra"
    assert value["models"]["planner"]["reasoning_effort"] == "low"
    assert value["execution"]["paid_calls_max"] == 202
    assert value["execution"]["provider_retries"] == 0
    assert value["execution"]["same_cohort_retry"] is False
    assert value["validation"]["stable_residual_relation_gains_min"] == 11
    assert value["validation"]["stable_hp017_relation_gains_min"] == 4
    assert value["validation"]["new_cardinality_contradictions_max"] == 0
    assert value["validation"]["planner_prompt_bytes_hard_max"] == 100_000
    assert value["budget"]["global_conservative_upper_bound_required_before_first_call"]
    assert value["credit"]["diagnostic_projection_after_11_accepted_facts"] == {
        "denominator": 157,
        "ok": 154,
        "ok_rate_percent": 98.09,
    }
    assert value["invariants"]["chunks_v3"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert value["invariants"]["railway_merge_gate"] is False


def test_s210_all_preregistered_inputs_are_byte_frozen():
    value = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    for spec in value["frozen_inputs"].values():
        assert file_sha(ROOT / spec["path"]) == spec["sha256"]


def test_s210_preflight_is_sealed_zero_call_and_has_exact_population():
    value = _json(PREFLIGHT)
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
    assert sum(row["role"] == "target" for row in value["rows"]) == 4
    assert sum(row["role"] == "independent_guardrail" for row in value["rows"]) == 14
    assert sum(len(row["context"]) for row in value["rows"]) == 65
    assert value["cost"] == {"model_calls": 0, "network_calls": 0, "usd": 0}


def test_s210_mechanism_contains_no_target_identity_or_residual_fact_names():
    implementation = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "src/rag/query_evidence_compiler.py",
            "scripts/s210_run_query_evidence_compiler.py",
        )
    ).casefold()
    forbidden = {
        "cat018",
        "hp002",
        "hp011",
        "hp017",
        "software_type_cbe_activation",
        "point_programming_fields",
        "initial_reference_calibration",
        "bounded_fault_window",
        "maintenance_isolation_prerequisite",
        "extinction_duration_range",
        "reset_inhibit_special_state",
        "option_family_cardinality",
        "input_condition_definition",
        "output_condition_action",
        "logic_contradiction_warning",
        "commissioning_rule_verification",
        "am-8200",
        "asd535",
        "rp1r",
        "pearl",
    }
    assert not (forbidden & set(implementation.replace("\n", " ").split()))
    assert all(term not in implementation for term in forbidden)


def test_s210_is_not_wired_into_runtime_before_result_gate():
    generator = (ROOT / "src/rag/generator.py").read_text(encoding="utf-8")
    bot = (ROOT / "src/bot/telegram_bot.py").read_text(encoding="utf-8")
    assert "query_evidence_compiler" not in generator
    assert "query_evidence_compiler" not in bot
    for path in (
        ROOT / "evals/s210_query_evidence_compiler_receipts_v1.json",
        ROOT / "evals/s210_query_evidence_compiler_score_v1.json",
    ):
        assert not path.exists()


def test_s210_execution_permit_requires_both_frontier_passes_and_exact_preflight():
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    assert permit["status"] == "EXECUTION_GO_PAID_BOUNDED_NO_RETRY"
    assert permit["preflight_sha256"] == file_sha(PREFLIGHT)
    assert permit["frontier_design_gate"]["principal"] == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "verdict": "PASS",
        "artifact": "evals/s210_frontier_design_decision_reviews_v1.json",
        "artifact_sha256": file_sha(
            ROOT / "evals/s210_frontier_design_decision_reviews_v1.json"
        ),
    }
    assert permit["frontier_design_gate"]["independent"]["model"] == "claude-fable-5"
    assert permit["frontier_design_gate"]["independent"]["verdict"] == "PASS"
    assert permit["budget_ceiling_usd"] == 75
    assert permit["conservative_full_run_upper_bound_usd"] < 75
    for spec in permit["frozen_artifacts"]:
        assert file_sha(ROOT / spec["path"]) == spec["sha256"]


def test_s210_global_worst_case_cost_is_bounded_before_any_call():
    preflight = _json(PREFLIGHT)
    prices = {
        "extractor": {"input": 2.0, "output": 10.0},
        "planner": {"input": 2.5, "output": 15.0},
    }
    estimate = conservative_execution_upper_bound_usd(preflight, prices)
    assert MAX_PLANNER_PROMPT_BYTES == 100_000
    assert 0 < estimate < 75
