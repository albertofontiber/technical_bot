import pytest

from scripts.s252_score_adaptive_reasoning_writer_ab import _replicas


def _row(replica: int) -> dict:
    return {
        "replicate": replica,
        "baseline_answer": "control",
        "treatment_answer": "treatment",
    }


def test_s252_requires_exactly_two_named_replicas() -> None:
    assert [row["replicate"] for row in _replicas({"replicas": [_row(2), _row(1)]})] == [1, 2]
    with pytest.raises(ValueError, match="exactly two"):
        _replicas({"replicas": [_row(1)]})
    with pytest.raises(ValueError, match="exactly 1 and 2"):
        _replicas({"replicas": [_row(1), _row(3)]})


def test_s252_rejects_empty_arm_answer() -> None:
    rows = [_row(1), _row(2)]
    rows[1]["treatment_answer"] = ""
    with pytest.raises(ValueError, match="non-empty treatment_answer"):
        _replicas({"replicas": rows})

