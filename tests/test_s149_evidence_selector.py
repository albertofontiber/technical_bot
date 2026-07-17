from __future__ import annotations

import pytest

from src.rag.evidence_selector import (
    EvidenceSelection,
    materialize_selected_chunks,
    prepare_evidence_units,
    validate_selection_value,
)


def _fixed_table_chunk() -> dict:
    return {
        "id": "manual-a",
        "manufacturer": "Example",
        "product_model": "M1",
        "content": (
            "Feature              Allowed     Setting\n"
            "                     (Y/N)\n\n"
            "Delayed alarm        N           Clear all\n"
            "Code 31\n\n"
            "Verified alarm       Y           Set or clear\n"
            "Code 41\n"
        ),
    }


def test_selected_table_unit_materializes_header_and_exact_source_receipts() -> None:
    prepared = prepare_evidence_units([_fixed_table_chunk()])
    target = next(
        row
        for row in prepared
        if row.unit.unit_kind == "table_row_with_header" and "Delayed alarm" in row.unit.content
    )
    selected = validate_selection_value({"unit_ids": [target.unit.unit_id]}, prepared)
    selection = EvidenceSelection(
        selected=selected,
        response_id="response-1",
        model="cheap-model",
        input_tokens=10,
        output_tokens=2,
    )
    chunks = materialize_selected_chunks(selection)
    assert len(chunks) == 1
    assert "Allowed" in chunks[0]["content"]
    assert "Delayed alarm" in chunks[0]["content"]
    assert chunks[0]["evidence_selector"]["source_spans"] == [
        list(span) for span in target.unit.source_spans
    ]


def test_unknown_duplicate_and_empty_selections_fail_closed() -> None:
    prepared = prepare_evidence_units([{"id": "a", "content": "Technical source."}])
    valid = prepared[0].unit.unit_id
    with pytest.raises(RuntimeError):
        validate_selection_value({"unit_ids": []}, prepared)
    with pytest.raises(RuntimeError):
        validate_selection_value({"unit_ids": ["unknown"]}, prepared)
    with pytest.raises(RuntimeError):
        validate_selection_value({"unit_ids": [valid, valid]}, prepared)


def test_anonymous_chunk_identity_is_deterministic() -> None:
    chunks = [{"content": "First technical paragraph."}]
    first = prepare_evidence_units(chunks)
    second = prepare_evidence_units(chunks)
    assert first == second
    assert all(row.unit.candidate_id.startswith("anonymous-f1-") for row in first)
