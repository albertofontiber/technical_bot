from dataclasses import replace

import pytest

from src.rag.answer_obligation_contract import (
    ANSWER_OBLIGATION_CONTRACT_VERSION,
    build_answer_cache_identity,
    build_enforced_answer_cache_identity,
    canonical_enforced_answer_contract,
    canonical_obligation_packet,
    obligation_packet_sha256,
)
from src.rag.answer_planner import AnswerObligation


def _obligation() -> AnswerObligation:
    return AnswerObligation(
        obligation_id="obl_123",
        fragment_number=1,
        candidate_id="candidate-a",
        facet="served_relation:closed_loop_return_path",
        kind="closed_loop_return_path",
        statement="Loop Start OUT returns to Return.",
        required_anchors=("Loop Start", "OUT", "Return"),
        source_start=10,
        source_end=50,
    )


def _identity(
    plan,
    *,
    contract_version=ANSWER_OBLIGATION_CONTRACT_VERSION,
    **overrides,
):
    envelope = {
        "model": "model-a",
        "max_tokens": 3500,
        "temperature": 0,
        "system": "Use only the supplied evidence.",
        "messages": [
            {
                "role": "user",
                "content": "[F1 | Product: ZX | Revision: 1] Context\nQuestion",
            }
        ],
    }
    envelope.update(overrides)
    return build_answer_cache_identity(
        generation_request_envelope=envelope,
        plan=plan,
        contract_version=contract_version,
    )


def test_packet_is_deterministic_and_preserves_prompt_order():
    first = _obligation()
    second = replace(first, obligation_id="obl_456", candidate_id="candidate-b")
    assert canonical_obligation_packet([first])["contract_version"] == (
        ANSWER_OBLIGATION_CONTRACT_VERSION
    )
    assert obligation_packet_sha256([first, second]) == obligation_packet_sha256(
        [first, second]
    )
    assert obligation_packet_sha256([first, second]) != obligation_packet_sha256(
        [second, first]
    )


def test_cache_identity_changes_with_obligation_evidence_and_contract_version():
    obligation = _obligation()
    baseline = _identity([obligation])
    evidence_change = _identity([replace(obligation, candidate_id="candidate-b")])
    version_change = _identity(
        [obligation], contract_version="answer_obligation_contract_v2"
    )
    empty_plan = _identity([])
    assert baseline["cache_key_sha256"] != evidence_change["cache_key_sha256"]
    assert baseline["cache_key_sha256"] != version_change["cache_key_sha256"]
    assert baseline["cache_key_sha256"] != empty_plan["cache_key_sha256"]


def test_cache_identity_changes_with_other_generation_inputs():
    baseline = _identity([_obligation()])
    changed_header = _identity(
        [_obligation()],
        messages=[{"role": "user", "content": "[F1 | Revision: 2] Context\nQuestion"}],
    )
    changed_sampling = _identity([_obligation()], temperature=0.2)
    assert baseline["cache_key_sha256"] != changed_header["cache_key_sha256"]
    assert baseline["cache_key_sha256"] != changed_sampling["cache_key_sha256"]


@pytest.mark.parametrize(
    "envelope",
    [
        {},
        None,
        [],
    ],
)
def test_cache_identity_fails_closed_on_invalid_inputs(envelope):
    with pytest.raises(ValueError):
        build_answer_cache_identity(
            generation_request_envelope=envelope,
            plan=[_obligation()],
        )


def _enforced_identity(*, conflicts=None, **versions):
    return build_enforced_answer_cache_identity(
        generation_request_envelope={
            "model": "model-a",
            "max_tokens": 3500,
            "temperature": 0,
            "system": "code-authored policy only",
            "messages": [{"role": "user", "content": "delimited evidence"}],
        },
        plan=[_obligation()],
        conflicts=conflicts or [],
        **versions,
    )


def test_enforced_identity_binds_conflicts_and_every_local_policy_version():
    baseline = _enforced_identity()
    conflict_change = _enforced_identity(
        conflicts=[{"conflict_id": "conf-1", "values": ["7", "8"]}]
    )
    variants = [
        _enforced_identity(planner_contract_version="answer_planner_s122_v2"),
        _enforced_identity(enforcement_policy_version="answer_enforcement_s122_v3"),
        _enforced_identity(validator_contract_version="validator-v2"),
        _enforced_identity(renderer_contract_version="renderer-v2"),
        _enforced_identity(conflict_schema_version="conflict-v2"),
    ]
    assert baseline["cache_key_sha256"] != conflict_change["cache_key_sha256"]
    assert all(
        baseline["cache_key_sha256"] != variant["cache_key_sha256"]
        for variant in variants
    )


def test_enforced_contract_preserves_obligation_and_conflict_order():
    obligation = _obligation()
    second = replace(obligation, obligation_id="obl_456")
    first_order = canonical_enforced_answer_contract(
        [obligation, second], [{"conflict_id": "a"}, {"conflict_id": "b"}]
    )
    second_order = canonical_enforced_answer_contract(
        [second, obligation], [{"conflict_id": "b"}, {"conflict_id": "a"}]
    )
    assert first_order != second_order
