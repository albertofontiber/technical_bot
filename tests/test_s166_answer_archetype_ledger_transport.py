import pytest

from scripts.s165_answer_archetype_ledger import FACETS
from scripts.s166_answer_archetype_ledger_transport import (
    MAX_ASSIGNMENTS,
    run,
    validate_ledger_v2,
)


def test_s166_allows_one_known_unit_to_satisfy_multiple_facets():
    ledger, ids = validate_ledger_v2(
        {
            "selections": [
                {"facet": FACETS[0], "unit_ids": ["E1"]},
                {"facet": FACETS[6], "unit_ids": ["E1", "E2"]},
            ]
        },
        {"E1", "E2"},
    )
    assert ledger[FACETS[0]] == ["E1"]
    assert ledger[FACETS[6]] == ["E1", "E2"]
    assert ids == ["E1", "E2"]


def test_s166_still_rejects_duplicate_facets_unknown_ids_and_assignment_overflow():
    with pytest.raises(ValueError):
        validate_ledger_v2(
            {
                "selections": [
                    {"facet": FACETS[0], "unit_ids": ["E1"]},
                    {"facet": FACETS[0], "unit_ids": ["E2"]},
                ]
            },
            {"E1", "E2"},
        )
    with pytest.raises(ValueError):
        validate_ledger_v2(
            {"selections": [{"facet": FACETS[0], "unit_ids": ["unknown"]}]},
            {"E1"},
        )
    known = {f"E{i}" for i in range(12)}
    overflowing = [
        {
            "facet": facet,
            "unit_ids": [f"E{i}" for i in range(12 if index < 2 else 9)],
        }
        for index, facet in enumerate(FACETS[:3])
    ]
    assert sum(len(row["unit_ids"]) for row in overflowing) == MAX_ASSIGNMENTS + 1
    with pytest.raises(ValueError):
        validate_ledger_v2(
            {"selections": overflowing},
            known,
        )


def test_s166_replay_passes_unchanged_semantic_gates_without_credit():
    result = run()
    assert result["status"] == "LOCAL_GO_TO_FRESH_INDEPENDENT"
    assert result["metrics"]["claim_recall"] >= 0.90
    assert result["metrics"]["unit_precision"] >= 0.80
    assert result["metrics"]["question_complete_rate"] >= 0.75
    assert result["metrics"]["invalid_outputs"] == 0
    assert result["decision"]["s165_posthoc_credit"] is False
    assert result["decision"]["target_probe"] is False
    assert result["cost"]["usd"] == 0
