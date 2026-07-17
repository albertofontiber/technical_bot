import pytest

from scripts import s170_per_chunk_relation_store_gate as base
from scripts import s171_bounded_relation_store_gate as s171
from scripts import s186_provider_compatible_relation_store_gate as s186


def _relation():
    return {
        "relation_type": "configuration_or_assignment",
        "subject": "point",
        "predicate": "uses",
        "object": "zone",
        "conditions": [],
        "qualifiers": [],
        "source_unit_ids": ["E001_test"],
    }


def test_provider_schema_removes_only_unsupported_cardinality_keyword():
    prior = s171.extraction_schema()
    current = s186.provider_extraction_schema()
    assert prior["properties"]["relations"]["maxItems"] == 30
    assert "maxItems" not in current["properties"]["relations"]
    prior["properties"]["relations"].pop("maxItems")
    assert current == prior
    assert s186.EXTRACTOR_SYSTEM == s171.EXTRACTOR_SYSTEM


def test_application_still_rejects_more_than_thirty_relations():
    s186.configure_base()
    with pytest.raises(ValueError, match="relation population out of bounds"):
        base.validate_relations(
            {"relations": [_relation() for _ in range(31)]}, {}, []
        )
