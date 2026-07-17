import pytest

from scripts.s170_per_chunk_relation_store_gate import (
    RELATION_TYPES, score_relations, validate_relations, validate_selection,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


def _fixture():
    source = {
        "item_id": "i1", "manufacturer": "Maker", "product_model": "P1",
        "document_id": "doc", "chunk_id": "chunk", "excerpt_sha256": "a" * 64,
        "excerpt": "## Setup\n\nBefore connecting, select Safe mode.\n\nVerify the green LED.",
    }
    units = build_header_aware_evidence_units(source["excerpt"], fragment_number=1, candidate_id="i1")
    return source, units


def test_s170_relation_validation_binds_known_source_units_and_assigns_ids():
    source, units = _fixture()
    rows = validate_relations({"relations": [{
        "relation_type": RELATION_TYPES[0], "subject": "technician", "predicate": "selects",
        "object": "Safe mode", "conditions": ["before connecting"], "qualifiers": [],
        "source_unit_ids": [units[-1].unit_id],
    }]}, source, units)
    assert rows[0]["relation_id"].startswith("R01_")
    assert rows[0]["source_unit_receipts"][0]["content_sha256"] == units[-1].content_sha256


def test_s170_selection_rejects_unknown_or_duplicate_relation_ids():
    assert validate_selection({"relation_ids": ["R1"]}, {"R1"}) == ["R1"]
    with pytest.raises(ValueError):
        validate_selection({"relation_ids": ["R1", "R1"]}, {"R1"})
    with pytest.raises(ValueError):
        validate_selection({"relation_ids": ["unknown"]}, {"R1"})


def test_s170_relation_scoring_materializes_source_unit_union():
    source, units = _fixture()
    relations = validate_relations({"relations": [{
        "relation_type": RELATION_TYPES[0], "subject": "technician", "predicate": "selects",
        "object": "Safe mode", "conditions": [], "qualifiers": [],
        "source_unit_ids": [units[-1].unit_id],
    }]}, source, units)
    item = {
        "answer_points": [
            {"facet": "access_or_prerequisite", "support_unit_ids": [units[-1].unit_id]},
            {"facet": "verification_commissioning_or_recovery", "support_unit_ids": [units[-1].unit_id]},
        ]
    }
    score = score_relations(item, units, relations, [relations[0]["relation_id"]])
    assert score["claims_covered"] == 2
    assert score["complete"] is True
