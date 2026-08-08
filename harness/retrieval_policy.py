"""Authoritative static retrieval-policy classification for chunks_v3."""
from __future__ import annotations

from typing import Any


POLICY_CLASSES = (
    "eligible",
    "register_only",
    "unsupported_language",
    "duplicate",
)

POLICY_PRECEDENCE = (
    "policy_excluded_register_only",
    "policy_excluded_language",
    "duplicate",
    "eligible",
)

_PRETERMINAL_TO_CLASS = {
    "policy_excluded_register_only": "register_only",
    "policy_excluded_language": "unsupported_language",
}


def classify(preterminal: str | None, duplicate_of: Any) -> str:
    """Return one closed policy class after dedup has been finalized."""
    if preterminal is not None:
        try:
            return _PRETERMINAL_TO_CLASS[preterminal]
        except KeyError as exc:
            raise ValueError(f"unknown retrieval preterminal: {preterminal}") from exc
    if duplicate_of is not None:
        return "duplicate"
    return "eligible"


def is_eligible(policy_class: str) -> bool:
    if policy_class not in POLICY_CLASSES:
        raise ValueError(f"unknown retrieval policy class: {policy_class}")
    return policy_class == "eligible"


def contract_payload() -> dict[str, Any]:
    """Return the closed, serializable policy contract."""
    return {
        "schema": "s117_m26_retrieval_policy_v1",
        "classes": list(POLICY_CLASSES),
        "precedence": list(POLICY_PRECEDENCE),
        "preterminal_mapping": dict(sorted(_PRETERMINAL_TO_CLASS.items())),
    }
