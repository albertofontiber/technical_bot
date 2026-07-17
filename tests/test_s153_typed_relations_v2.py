from __future__ import annotations

from src.rag.typed_relations_v2 import (
    single_chunk_extraction_schema,
    validate_single_chunk_extraction,
)


def test_single_chunk_transport_binds_identity_outside_model_output() -> None:
    value = {
        "claims": [
            {
                "relation_type": "threshold",
                "claim_text": "The alarm threshold is 20 percent.",
                "exact_quote": "Alarm threshold: 20 %.",
            }
        ]
    }
    relations, stats = validate_single_chunk_extraction(
        value, chunk_id="immutable-chunk", content="Alarm threshold: 20 %."
    )
    assert relations[0].chunk_id == "immutable-chunk"
    assert stats["invalid_quote_drops"] == 0
    schema = single_chunk_extraction_schema()
    assert "chunk_id" not in schema["properties"]
    assert "chunks" not in schema["properties"]
