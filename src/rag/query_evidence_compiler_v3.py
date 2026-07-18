"""S212 provider-compatible deterministic full binding for exact claims."""
from __future__ import annotations

from copy import deepcopy
from math import ceil
from typing import Any

from jsonschema import Draft202012Validator

from . import query_evidence_compiler as v1


DETERMINISTIC_BATCHED_FULL_BINDING_V3 = "query_evidence_compiler_s212_v3"
MAX_MODEL_CLAIMS_PER_CHUNK = v1.MAX_MODEL_CLAIMS_PER_CHUNK


def claim_schema() -> dict[str, Any]:
    """Return the provider-supported S210 schema (Anthropic rejects maxItems)."""
    return deepcopy(v1.claim_schema())


def validate_claim_response(
    value: dict[str, Any],
    *,
    chunk: dict[str, Any],
    fragment_number: int,
):
    """Bind every claim in deterministic batches that satisfy the frozen validator."""
    errors = sorted(Draft202012Validator(claim_schema()).iter_errors(value), key=str)
    if errors:
        raise ValueError(f"claim schema validation failed: {errors[0].message}")
    raw_claims = value.get("claims")
    claims = []
    stats = {
        "whitespace_only_repairs": 0,
        "invalid_quote_drops": 0,
        "duplicate_span_drops": 0,
    }
    seen_spans: set[tuple[int, int, int, str]] = set()
    for start in range(0, len(raw_claims), MAX_MODEL_CLAIMS_PER_CHUNK):
        batch = {"claims": raw_claims[start : start + MAX_MODEL_CLAIMS_PER_CHUNK]}
        bound, observed = v1.validate_claim_response(
            batch, chunk=chunk, fragment_number=fragment_number
        )
        for key in stats:
            stats[key] += observed[key]
        for claim in bound:
            identity = (
                claim.fragment_number,
                claim.source_start,
                claim.source_end,
                claim.candidate_id,
            )
            if identity in seen_spans:
                stats["duplicate_span_drops"] += 1
                continue
            seen_spans.add(identity)
            claims.append(claim)
    return claims, {
        **stats,
        "legacy_limit_excess_claims": max(
            0, len(raw_claims) - MAX_MODEL_CLAIMS_PER_CHUNK
        ),
        "binding_batches": ceil(len(raw_claims) / MAX_MODEL_CLAIMS_PER_CHUNK)
        if raw_claims
        else 0,
    }
