from __future__ import annotations

import pytest

from src.rag.typed_relations import (
    build_claim_selection_prompt,
    validate_claim_selection,
    validate_extraction_value,
)


def test_typed_relations_are_exact_source_bound_and_deterministic() -> None:
    chunks = [{"chunk_id": "a", "content": "Before maintenance, isolate the output.\nThen reset."}]
    value = {
        "chunks": [
            {
                "chunk_id": "a",
                "claims": [
                    {
                        "relation_type": "safety_condition",
                        "claim_text": "The output must be isolated before maintenance.",
                        "exact_quote": "Before maintenance, isolate the output.",
                    }
                ],
            }
        ]
    }
    first, stats = validate_extraction_value(value, chunks)
    second, _ = validate_extraction_value(value, chunks)
    assert first == second
    assert stats == {"whitespace_only_repairs": 0, "invalid_quote_drops": 0}
    assert chunks[0]["content"][first[0].source_start : first[0].source_end] == first[0].exact_quote


def test_invalid_quote_drops_without_poisoning_other_claims() -> None:
    chunks = [{"chunk_id": "a", "content": "Exact threshold is 20 %."}]
    value = {
        "chunks": [
            {
                "chunk_id": "a",
                "claims": [
                    {"relation_type": "threshold", "claim_text": "20 percent", "exact_quote": "Exact threshold is 20 %."},
                    {"relation_type": "warning", "claim_text": "invented", "exact_quote": "not in source"},
                ],
            }
        ]
    }
    relations, stats = validate_extraction_value(value, chunks)
    assert len(relations) == 1
    assert stats["invalid_quote_drops"] == 1


def test_claim_selection_rejects_unknown_ids_and_preserves_intent() -> None:
    chunks = [{"chunk_id": "a", "content": "Reset is inhibited for 30 seconds."}]
    relations, _ = validate_extraction_value(
        {"chunks": [{"chunk_id": "a", "claims": [{"relation_type": "constraint", "claim_text": "Reset inhibit", "exact_quote": "Reset is inhibited for 30 seconds."}]}]},
        chunks,
    )
    intent, selected = validate_claim_selection(
        {"intent": "reset_recovery", "claim_ids": [relations[0].claim_id]}, relations
    )
    assert intent == "reset_recovery"
    assert selected == tuple(relations)
    assert relations[0].claim_id in build_claim_selection_prompt("Why no reset?", relations)
    with pytest.raises(RuntimeError):
        validate_claim_selection({"intent": "other", "claim_ids": ["unknown"]}, relations)
