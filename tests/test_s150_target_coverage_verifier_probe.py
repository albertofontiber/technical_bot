from __future__ import annotations

from src.rag.evidence_selector import prepare_evidence_units
from scripts.s150_target_coverage_verifier_probe import reconstruct_primary_selection


def test_primary_selection_reconstruction_validates_content_receipt() -> None:
    prepared = prepare_evidence_units([{"id": "source", "content": "Exact technical source."}])
    unit = prepared[0].unit
    row = {
        "selected_unit_receipts": [
            {"unit_id": unit.unit_id, "content_sha256": unit.content_sha256}
        ]
    }
    selection = reconstruct_primary_selection(row, prepared, "response")
    assert selection.selected == (prepared[0],)
    assert selection.response_id == "response"
