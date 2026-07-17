from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.rag.evidence_coverage_verifier import (
    EvidenceCoverageVerification,
    merge_verified_selection,
    validate_verification_value,
)
from src.rag.evidence_selector import EvidenceSelection, prepare_evidence_units


def _prepared():
    return prepare_evidence_units(
        [
            {"id": "a", "content": "Reset condition and threshold."},
            {"id": "b", "content": "Safety prerequisite before maintenance."},
        ]
    )


def test_complete_verification_has_no_additions() -> None:
    prepared = _prepared()
    selected = (prepared[0],)
    status, facets, additions = validate_verification_value(
        {"status": "COMPLETE", "missing_facets": [], "additional_unit_ids": []},
        prepared,
        selected,
    )
    assert (status, facets, additions) == ("COMPLETE", (), ())


def test_incomplete_verification_adds_only_new_known_ids() -> None:
    prepared = _prepared()
    selected = (prepared[0],)
    value = {
        "status": "INCOMPLETE",
        "missing_facets": ["safety prerequisite"],
        "additional_unit_ids": [prepared[1].unit.unit_id],
    }
    _, facets, additions = validate_verification_value(value, prepared, selected)
    assert facets == ("safety prerequisite",)
    primary = EvidenceSelection(selected, "s", "cheap", 10, 2)
    verification = EvidenceCoverageVerification(
        "INCOMPLETE", facets, additions, "v", "verifier", 20, 3
    )
    merged = merge_verified_selection(primary, verification)
    assert merged.selected == tuple(prepared)
    assert merged.input_tokens == 30


def test_verification_rejects_selected_unknown_and_malformed_additions() -> None:
    prepared = _prepared()
    selected = (prepared[0],)
    with pytest.raises(RuntimeError):
        validate_verification_value(
            {
                "status": "INCOMPLETE",
                "missing_facets": ["x"],
                "additional_unit_ids": [prepared[0].unit.unit_id],
            },
            prepared,
            selected,
        )
    with pytest.raises(RuntimeError):
        validate_verification_value(
            {"status": "COMPLETE", "missing_facets": ["x"], "additional_unit_ids": []},
            prepared,
            selected,
        )
