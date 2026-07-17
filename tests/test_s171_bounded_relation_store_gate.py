from scripts import s170_per_chunk_relation_store_gate as base
from scripts.s171_bounded_relation_store_gate import (
    MAX_RELATIONS, SOURCE, COHORT, configure_base, extraction_schema,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


def test_s171_schema_and_local_validator_share_thirty_relation_bound():
    configure_base()
    assert extraction_schema()["properties"]["relations"]["maxItems"] == MAX_RELATIONS
    assert base.MAX_RELATIONS_PER_CHUNK == MAX_RELATIONS
    source = {
        "manufacturer": "Maker", "product_model": "P", "document_id": "d",
        "chunk_id": "c", "excerpt_sha256": "a" * 64,
    }
    units = build_header_aware_evidence_units(
        "## Technical\n\nSet output to 5 V.", fragment_number=1, candidate_id="i"
    )
    relations = []
    for index in range(24):
        relations.append({
            "relation_type": base.RELATION_TYPES[index % len(base.RELATION_TYPES)],
            "subject": f"subject {index}", "predicate": "sets", "object": "5 V",
            "conditions": [], "qualifiers": [], "source_unit_ids": [units[-1].unit_id],
        })
    assert len(base.validate_relations({"relations": relations}, source, units)) == 24


def test_s171_uses_different_s147_development_cohort():
    assert SOURCE.name == "s147_fresh_source_packet_v1.json"
    assert COHORT.name == "s171_s147_source_unit_gold_v1.json"
