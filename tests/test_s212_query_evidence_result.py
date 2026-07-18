from __future__ import annotations

import json
from pathlib import Path

from src.rag.query_evidence_compiler import stable_sha


ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "evals/s212_query_evidence_compiler_receipts_v1.json"
SCORE = ROOT / "evals/s212_query_evidence_compiler_score_v1.json"
FUNNEL = ROOT / "evals/s212_query_evidence_compiler_relation_funnel_v1.json"


def _sealed(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    return value


def test_s212_complete_run_is_bounded_fresh_and_has_no_legacy_claim_drop():
    value = _sealed(RECEIPTS)
    assert value["status"] == "COMPLETE"
    assert value["calls"] == 202
    assert len(value["rows"]) == 36
    assert value["cost"]["estimated_usd"] == 1.4833295
    assert value["cost"]["estimated_usd"] < value["cost"]["budget_ceiling_usd"]
    assert value["lineage"]["prior_outputs_reused"] is False
    assert value["legacy_claim_limit"] == {
        "policy": "BIND_ALL_IN_PROVIDER_ORDER_USING_BATCHES_OF_16",
        "calls_exceeding_legacy_limit": 0,
        "excess_claims_fully_bound": 0,
        "max_raw_claims": 0,
        "calls": [],
    }


def test_s212_is_clear_no_go_with_only_one_stable_residual_gain():
    value = _sealed(SCORE)
    assert value["status"] == "NO_GO"
    metrics = value["metrics"]
    assert metrics["stable_residual_relation_gains"] == 1
    assert metrics["stable_hp017_relation_gains"] == 0
    assert metrics["previously_covered_target_regressions"] == 0
    assert metrics["guardrail_point_regressions"] == 0
    assert metrics["selected_evidence_precision"] == 0.953125
    assert metrics["invalid_citation_calls"] == 0
    assert metrics["baseline_prefix_failures"] == 0
    assert value["decision"]["frontier_atomic_review"] is False
    assert value["decision"]["facts_moved_to_ok"] == 0
    assert value["relation_proxy_projection"]["canonical_facts_ok_before"] == 143
    assert value["relation_proxy_projection"]["claim_98_percent_allowed"] is False


def test_s212_funnel_locates_five_upstream_and_six_selection_misses():
    value = _sealed(FUNNEL)
    assert value["status"] == "COMPLETE_CAUSAL_NO_GO_ANALYSIS"
    assert value["residual_relations"] == 12
    assert value["stable_stage_counts"] == {
        "answer_covered": 1,
        "candidate_pool_span": 7,
        "deterministic_fallback_span": 4,
        "model_exact_claim_span": 3,
        "qualified": 1,
        "selected_span": 1,
    }
    assert value["classifications"] == {
        "DOWNSTREAM_SELECTION_MISS": 6,
        "STABLE_QUALIFIED_GAIN": 1,
        "UPSTREAM_CANDIDATE_COVERAGE_MISS": 5,
    }
    by_key = {(row["qid"], row["kind"]): row for row in value["rows"]}
    assert by_key[("hp002", "maintenance_isolation_prerequisite")][
        "classification"
    ] == "STABLE_QUALIFIED_GAIN"
    assert sum(
        row["qid"] == "hp017"
        and row["classification"] == "UPSTREAM_CANDIDATE_COVERAGE_MISS"
        for row in value["rows"]
    ) == 3
    assert value["decision"]["facts_moved_to_ok"] == 0
    assert value["decision"]["next"] == (
        "TARGET_UPSTREAM_CANDIDATE_COVERAGE_BEFORE_SELECTION"
    )
