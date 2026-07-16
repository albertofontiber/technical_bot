from __future__ import annotations

import copy

import pytest

from scripts.s125_replay_m1_known_hold_answers import (
    ADJUDICATION_PATH,
    build_from_files,
    build_replay,
    load_json,
    load_yaml,
)


def _inputs():
    adjudication = load_yaml(ADJUDICATION_PATH)
    root = ADJUDICATION_PATH.parent.parent
    contract = load_json(root / adjudication["frozen_inputs"]["migration_contract"]["path"])
    answers = load_json(root / adjudication["frozen_inputs"]["frozen_answers"]["path"])
    return adjudication, contract, answers


def test_real_replay_reconciles_exact_core_and_supplementary_histograms():
    result = build_from_files()
    assert result["summary"] == {
        "content_claim_count": 58,
        "supplementary_claim_count": 12,
        "content_stage_histogram": {
            "OK": 32,
            "synthesis-miss": 10,
            "synthesis-not-measured": 16,
        },
        "supplementary_stage_histogram": {
            "supplementary-covered": 3,
            "supplementary-not-covered": 2,
            "supplementary-not-measured": 7,
        },
        "retrieval_pass": 58,
        "rerank_pass": 58,
        "answer_executed_qids": 10,
        "answer_unexecuted_qids": 3,
        "model_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
    }


def test_unexecuted_qid_cannot_be_scored_as_a_miss():
    adjudication, contract, answers = _inputs()
    tampered = copy.deepcopy(adjudication)
    tampered["qid_receipts"]["cat012"]["core_default"] = "synthesis_not_covered"
    with pytest.raises(ValueError, match="unexecuted answer cannot be scored"):
        build_replay(tampered, contract, answers)


def test_answer_hash_change_fails_closed():
    adjudication, contract, answers = _inputs()
    tampered = copy.deepcopy(answers)
    row = next(row for row in tampered["rows"] if row["qid"] == "cat005")
    row["answer"] += " changed"
    with pytest.raises(ValueError, match="answer bytes do not match"):
        build_replay(adjudication, contract, tampered)


def test_supplementary_coverage_must_be_exact():
    adjudication, contract, answers = _inputs()
    tampered = copy.deepcopy(adjudication)
    tampered["supplementary_claims"].pop(next(iter(tampered["supplementary_claims"])))
    with pytest.raises(ValueError, match="supplementary adjudication coverage is not exact"):
        build_replay(tampered, contract, answers)


def test_unexecuted_supplementary_claim_cannot_be_scored():
    adjudication, contract, answers = _inputs()
    tampered = copy.deepcopy(adjudication)
    tampered["supplementary_claims"][
        "m1.cat012.859bf84ece1e1301.tolerance_factor"
    ]["coverage"] = "synthesis_covered"
    with pytest.raises(ValueError, match="unexecuted supplementary answer cannot be scored"):
        build_replay(tampered, contract, answers)


def test_replay_is_deterministic():
    assert build_from_files() == build_from_files()
