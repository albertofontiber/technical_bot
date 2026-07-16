import json

import pytest

from scripts.s133_unmeasured_answer_probe import (
    _checkpoint_matches,
    _load_checkpoints,
    _parse_requested,
    _validate_reconciliation,
)


def _reconciliation():
    return {
        "status": "LOCAL_RECONCILIATION_COMPLETE_GENERATION_NOT_EXECUTED",
        "reconciliation": {
            "distinct_qids_requiring_exact_answers": 2,
            "unmeasured_claims": 3,
        },
        "questions": [
            {"qid": "q1", "claim_count": 2, "claim_ids": ["c1", "c2"]},
            {"qid": "q2", "claim_count": 1, "claim_ids": ["c3"]},
        ],
    }


def test_reconciliation_contract_is_bijective():
    assert [row["qid"] for row in _validate_reconciliation(_reconciliation())] == [
        "q1",
        "q2",
    ]
    payload = _reconciliation()
    payload["questions"][1]["claim_ids"] = ["c2"]
    with pytest.raises(RuntimeError, match="not unique"):
        _validate_reconciliation(payload)


def test_requested_qids_are_bounded_to_reconciled_cohort():
    assert _parse_requested("q2,q1,q2", {"q1", "q2"}) == {"q1", "q2"}
    with pytest.raises(RuntimeError, match="outside S130 cohort"):
        _parse_requested("q3", {"q1", "q2"})


def test_checkpoint_reuse_requires_full_runtime_identity():
    expected = {
        "qid": "q1",
        "guided_prompt_sha256": "prompt",
        "serving_context_sha256": "context",
        "model": "model",
        "max_output_tokens": 3500,
    }
    checkpoint = {**expected, "answer": "measured"}
    assert _checkpoint_matches(checkpoint, expected) == (True, [])
    checkpoint["serving_context_sha256"] = "other"
    matches, drift = _checkpoint_matches(checkpoint, expected)
    assert not matches
    assert drift == ["serving_context_sha256"]


def test_checkpoint_loader_rejects_duplicate_paid_rows(tmp_path):
    path = tmp_path / "checkpoint.jsonl"
    row = {"qid": "q1", "answer": "a"}
    path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="duplicate checkpoint"):
        _load_checkpoints(path)
