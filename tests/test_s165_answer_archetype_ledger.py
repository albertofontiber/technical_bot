import pytest

from scripts.s165_answer_archetype_ledger import (
    FACETS,
    MAX_SELECTED_IDS,
    SYSTEM,
    ledger_schema,
    validate_ledger,
)


def test_s165_facets_are_generic_and_cover_safety_and_verification():
    assert len(FACETS) == 8
    assert "safety_warning_exception_or_conflict" in FACETS
    assert "verification_commissioning_or_recovery" in FACETS
    forbidden = ("notifier", "detnov", "morley", "pearl", "asd535", "rp1r", "am-8200")
    assert not any(token in SYSTEM.casefold() for token in forbidden)


def test_s165_schema_and_validator_accept_known_unique_ids():
    value = {
        "selections": [
            {"facet": FACETS[0], "unit_ids": ["E1"]},
            {"facet": FACETS[6], "unit_ids": ["E2"]},
        ]
    }
    assert ledger_schema()["properties"]["selections"]["type"] == "array"
    assert validate_ledger(value, {"E1", "E2"}) == {
        FACETS[0]: ["E1"],
        FACETS[6]: ["E2"],
    }


@pytest.mark.parametrize(
    "value",
    [
        {"selections": [{"facet": FACETS[0], "unit_ids": ["unknown"]}]},
        {
            "selections": [
                {"facet": FACETS[0], "unit_ids": ["E1"]},
                {"facet": FACETS[0], "unit_ids": ["E2"]},
            ]
        },
        {
            "selections": [
                {"facet": FACETS[0], "unit_ids": ["E1"]},
                {"facet": FACETS[1], "unit_ids": ["E1"]},
            ]
        },
    ],
)
def test_s165_validator_fails_closed(value):
    with pytest.raises(ValueError):
        validate_ledger(value, {"E1", "E2"})


def test_s165_validator_caps_total_selected_ids():
    ids = [f"E{i}" for i in range(MAX_SELECTED_IDS + 1)]
    with pytest.raises(ValueError):
        validate_ledger(
            {"selections": [{"facet": FACETS[0], "unit_ids": ids}]}, set(ids)
        )
