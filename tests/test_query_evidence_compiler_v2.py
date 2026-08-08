from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator

from src.rag.query_evidence_compiler import claim_schema as claim_schema_v1
from src.rag.query_evidence_compiler_v2 import (
    MAX_MODEL_CLAIMS_PER_CHUNK,
    claim_schema,
    validate_claim_response,
)


def _claim(index: int) -> dict[str, str]:
    return {
        "facet": "direct_answer",
        "claim_text": f"claim {index}",
        "exact_quote": f"quote {index}",
    }


def test_s211_provider_schema_and_local_validator_share_the_exact_claim_bound():
    schema = claim_schema()
    assert "maxItems" not in claim_schema_v1()["properties"]["claims"]
    assert schema["properties"]["claims"]["maxItems"] == 16
    assert MAX_MODEL_CLAIMS_PER_CHUNK == 16
    validator = Draft202012Validator(schema)
    assert validator.is_valid({"claims": [_claim(index) for index in range(16)]})
    assert not validator.is_valid({"claims": [_claim(index) for index in range(17)]})


def test_s211_local_entrypoint_rejects_seventeen_before_span_binding():
    value = {"claims": [_claim(index) for index in range(17)]}
    with pytest.raises(ValueError, match="too long"):
        validate_claim_response(
            value,
            chunk={"id": "chunk", "content": "no quotes are needed"},
            fragment_number=1,
        )
