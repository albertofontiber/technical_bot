from __future__ import annotations

import pytest

from src.reingest import retrieval_policy


@pytest.mark.parametrize(
    ("preterminal", "duplicate_of", "expected"),
    [
        ("policy_excluded_register_only", "duplicate-id", "register_only"),
        ("policy_excluded_language", "duplicate-id", "unsupported_language"),
        (None, "duplicate-id", "duplicate"),
        (None, None, "eligible"),
    ],
)
def test_policy_precedence_is_closed(preterminal, duplicate_of, expected):
    assert retrieval_policy.classify(preterminal, duplicate_of) == expected


def test_unknown_preterminal_fails_closed():
    with pytest.raises(ValueError, match="unknown retrieval preterminal"):
        retrieval_policy.classify("manufacturer_specific_exception", None)


def test_unknown_class_fails_closed():
    with pytest.raises(ValueError, match="unknown retrieval policy class"):
        retrieval_policy.is_eligible("maybe")


def test_contract_payload_is_stable_and_complete():
    payload = retrieval_policy.contract_payload()
    assert payload["classes"] == list(retrieval_policy.POLICY_CLASSES)
    assert payload["precedence"] == list(retrieval_policy.POLICY_PRECEDENCE)
    assert set(payload["preterminal_mapping"].values()) < set(payload["classes"])
