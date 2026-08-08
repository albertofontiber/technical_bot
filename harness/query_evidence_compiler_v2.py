"""S211 contract-equivalent schema wrapper over the frozen S210 compiler."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from jsonschema import Draft202012Validator

from . import query_evidence_compiler as v1


SCHEMA_VALIDATOR_EQUIVALENCE_V2 = "query_evidence_compiler_s211_v2"
MAX_MODEL_CLAIMS_PER_CHUNK = v1.MAX_MODEL_CLAIMS_PER_CHUNK


def claim_schema() -> dict[str, Any]:
    """Expose the same hard claim bound to the provider and local validator."""
    schema = deepcopy(v1.claim_schema())
    schema["properties"]["claims"]["maxItems"] = MAX_MODEL_CLAIMS_PER_CHUNK
    return schema


def validate_claim_response(
    value: dict[str, Any],
    *,
    chunk: dict[str, Any],
    fragment_number: int,
):
    errors = sorted(Draft202012Validator(claim_schema()).iter_errors(value), key=str)
    if errors:
        raise ValueError(f"claim schema validation failed: {errors[0].message}")
    return v1.validate_claim_response(
        value, chunk=chunk, fragment_number=fragment_number
    )
