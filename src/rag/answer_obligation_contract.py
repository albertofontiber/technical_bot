"""Canonical, versioned identity for source-bound answer obligations.

This module is deliberately independent from the generator and cache backend.
It gives any caller a deterministic packet and cache identity while keeping
policy (whether a cached answer may be reused) at the orchestration boundary.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Iterable

ANSWER_OBLIGATION_CONTRACT_VERSION = "answer_obligation_contract_v1"
ENFORCED_ANSWER_CACHE_IDENTITY_VERSION = "enforced_answer_generation_cache_identity_v2"
ENFORCEMENT_POLICY_VERSION = "answer_enforcement_s122_v2"
VALIDATOR_CONTRACT_VERSION = "answer_contract_validator_s122_v1"
RENDERER_CONTRACT_VERSION = "source_bound_renderer_s124_v1"
CONFLICT_SCHEMA_VERSION = "answer_conflict_s122_v1"


def stable_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def canonical_obligation_packet(
    plan: Iterable[Any],
    *,
    contract_version: str = ANSWER_OBLIGATION_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Return the exact ordered packet rendered into an answer prompt.

    Order is intentional: changing obligation order changes the guidance seen
    by the model and therefore must change the packet identity.
    """
    if not contract_version.strip():
        raise ValueError("contract_version must be non-empty")
    obligations = []
    for item in plan:
        row = item.to_dict() if hasattr(item, "to_dict") else dict(item)
        obligations.append(row)
    return {
        "contract_version": contract_version,
        "obligations": obligations,
    }


def obligation_packet_sha256(
    plan: Iterable[Any],
    *,
    contract_version: str = ANSWER_OBLIGATION_CONTRACT_VERSION,
) -> str:
    return stable_sha256(
        canonical_obligation_packet(plan, contract_version=contract_version)
    )


def build_answer_cache_identity(
    *,
    generation_request_envelope: Mapping[str, Any],
    plan: Iterable[Any],
    contract_version: str = ANSWER_OBLIGATION_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Build a fail-closed identity from the exact provider request envelope.

    The caller must pass the same complete mapping that is sent to the model
    provider, including rendered messages/context headers and every sampling or
    provider option.  Accepting one envelope instead of a hand-maintained field
    list prevents new output-affecting parameters from being omitted silently.
    """
    if not isinstance(generation_request_envelope, Mapping) or not generation_request_envelope:
        raise ValueError("generation_request_envelope must be a non-empty mapping")
    packet = canonical_obligation_packet(plan, contract_version=contract_version)
    payload = {
        "identity_contract": "answer_generation_cache_identity_v1",
        "obligation_contract_version": contract_version,
        "canonical_obligation_packet_sha256": stable_sha256(packet),
        "exact_generation_request_envelope_sha256": stable_sha256(
            generation_request_envelope
        ),
    }
    return {**payload, "cache_key_sha256": stable_sha256(payload)}


def canonical_enforced_answer_contract(
    plan: Iterable[Any],
    conflicts: Iterable[Any],
    *,
    planner_contract_version: str = "answer_planner_s122_v1",
    enforcement_policy_version: str = ENFORCEMENT_POLICY_VERSION,
    validator_contract_version: str = VALIDATOR_CONTRACT_VERSION,
    renderer_contract_version: str = RENDERER_CONTRACT_VERSION,
    conflict_schema_version: str = CONFLICT_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Return every output-affecting local enforcement input in exact order."""
    versions = {
        "planner_contract_version": planner_contract_version,
        "enforcement_policy_version": enforcement_policy_version,
        "validator_contract_version": validator_contract_version,
        "renderer_contract_version": renderer_contract_version,
        "conflict_schema_version": conflict_schema_version,
    }
    if not all(str(value).strip() for value in versions.values()):
        raise ValueError("enforced answer contract versions must be non-empty")
    obligations = [
        item.to_dict() if hasattr(item, "to_dict") else dict(item)
        for item in plan
    ]
    conflict_rows = [
        item.to_dict() if hasattr(item, "to_dict") else dict(item)
        for item in conflicts
    ]
    return {
        "identity_contract": ENFORCED_ANSWER_CACHE_IDENTITY_VERSION,
        **versions,
        "obligations": obligations,
        "conflicts": conflict_rows,
    }


def build_enforced_answer_cache_identity(
    *,
    generation_request_envelope: Mapping[str, Any],
    plan: Iterable[Any],
    conflicts: Iterable[Any],
    planner_contract_version: str = "answer_planner_s122_v1",
    enforcement_policy_version: str = ENFORCEMENT_POLICY_VERSION,
    validator_contract_version: str = VALIDATOR_CONTRACT_VERSION,
    renderer_contract_version: str = RENDERER_CONTRACT_VERSION,
    conflict_schema_version: str = CONFLICT_SCHEMA_VERSION,
) -> dict[str, Any]:
    if not isinstance(generation_request_envelope, Mapping) or not generation_request_envelope:
        raise ValueError("generation_request_envelope must be a non-empty mapping")
    contract = canonical_enforced_answer_contract(
        plan,
        conflicts,
        planner_contract_version=planner_contract_version,
        enforcement_policy_version=enforcement_policy_version,
        validator_contract_version=validator_contract_version,
        renderer_contract_version=renderer_contract_version,
        conflict_schema_version=conflict_schema_version,
    )
    payload = {
        "identity_contract": ENFORCED_ANSWER_CACHE_IDENTITY_VERSION,
        "canonical_enforced_answer_contract_sha256": stable_sha256(contract),
        "exact_generation_request_envelope_sha256": stable_sha256(
            generation_request_envelope
        ),
    }
    return {**payload, "cache_key_sha256": stable_sha256(payload)}
