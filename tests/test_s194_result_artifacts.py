from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def _load(name: str):
    return json.loads((EVALS / name).read_text(encoding="utf-8"))


def test_s194_stopped_upstream_without_planner_or_target_calls():
    result = _load("s194_decomposed_evidence_planner_gate_v1.json")
    assert result["status"] == "NO_GO_COHORT_CONSTRUCTION"
    checks = result["population_checks"]
    assert all(value for key, value in checks.items() if key != "author_invalid_outputs_zero")
    assert checks["author_invalid_outputs_zero"] is False
    assert result["decision"] == {
        "target_probe_opened": False,
        "production": False,
        "facts_moved_to_ok": 0,
    }
    assert result["cost"] == {
        "author_usd": 0.078186,
        "planner_usd": 0,
        "target_usd": 0,
        "total_usd": 0.078186,
    }
    assert not (EVALS / "s194_decomposed_evidence_planner_packet_v1.json").exists()
    assert not (EVALS / "s194_decomposed_evidence_planner_receipts_v1.json").exists()
    assert not (EVALS / "s194_target_planner_receipts_v1.json").exists()


def test_s194_author_failure_is_single_and_causally_attributed():
    author = _load("s194_decomposed_evidence_author_receipts_v1.json")
    cohort = _load("s194_decomposed_evidence_gold_cohort_v1.json")
    source_path = EVALS / "s194_fresh_source_packet_v1.json"
    assert author["status"] == "COMPLETE"
    assert author["model"] == "claude-haiku-4-5-20251001"
    assert len(author["receipts"]) == 14
    assert author["invalid_outputs"] == 1
    invalid = [row for row in author["receipts"] if row["validation_error"]]
    assert [(row["item_id"], row["validation_error"]) for row in invalid] == [
        ("s194_src_09", "invalid answer-point support cardinality")
    ]
    eligible = [row for row in cohort["items"] if row["eligible"]]
    assert len(eligible) == 13
    assert sum(len(row["answer_points"]) for row in eligible) == 50
    assert cohort["source_packet_sha256"] == hashlib.sha256(
        source_path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def test_s194_keeps_chunks_v3_explicit_and_unchanged_even_on_early_no_go():
    result = _load("s194_decomposed_evidence_planner_gate_v1.json")
    lane = result["chunks_v3_lane"]
    assert lane["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert lane["changed_by_s194"] is False
    assert lane["migration_or_materialization"] is False
    assert lane["per_question_patching"] is False
