from __future__ import annotations

from src.rag.query_evidence_compiler import claim_schema as claim_schema_v1
from src.rag.query_evidence_compiler_v3 import (
    MAX_MODEL_CLAIMS_PER_CHUNK,
    claim_schema,
    validate_claim_response,
)


def test_s212_schema_is_the_provider_supported_s210_contract():
    assert claim_schema() == claim_schema_v1()
    assert "maxItems" not in claim_schema()["properties"]["claims"]


def test_s212_deterministically_binds_all_seventeen_in_two_batches():
    quotes = [f"quote {index:02d}" for index in range(17)]
    content = " | ".join(quotes)
    value = {
        "claims": [
            {
                "facet": "direct_answer",
                "claim_text": f"claim {index:02d}",
                "exact_quote": quote,
            }
            for index, quote in enumerate(quotes)
        ]
    }
    claims, stats = validate_claim_response(
        value,
        chunk={"id": "chunk", "content": content},
        fragment_number=1,
    )
    assert MAX_MODEL_CLAIMS_PER_CHUNK == 16
    assert len(claims) == 17
    assert [claim.exact_quote for claim in claims] == quotes
    assert stats["legacy_limit_excess_claims"] == 1
    assert stats["binding_batches"] == 2


def test_s212_under_limit_behavior_is_byte_equivalent_and_drops_nothing():
    value = {
        "claims": [
            {
                "facet": "verification",
                "claim_text": "verify",
                "exact_quote": "verify exactly",
            }
        ]
    }
    claims, stats = validate_claim_response(
        value,
        chunk={"id": "chunk", "content": "verify exactly"},
        fragment_number=1,
    )
    assert [claim.exact_quote for claim in claims] == ["verify exactly"]
    assert stats["legacy_limit_excess_claims"] == 0
    assert stats["binding_batches"] == 1
