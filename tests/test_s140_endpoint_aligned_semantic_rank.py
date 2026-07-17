from __future__ import annotations

import copy

import pytest

from scripts import s140_endpoint_aligned_semantic_rank as audit


def frozen() -> tuple[dict, dict, dict, dict]:
    prereg = audit.files.load_yaml(audit.DEFAULT_PREREG)
    packet = audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["packet"]["path"]
    )
    mapping = audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["mapping"]["path"]
    )
    sol = audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["sol_valid"]["path"]
    )
    return prereg, packet, mapping, sol


def test_prereg_and_endpoint_projection_are_valid() -> None:
    prereg, packet, _, sol = frozen()
    audit.validate_prereg(prereg)
    endpoint = audit.endpoint_from_full(sol["judgement"])
    audit.validate_endpoint(endpoint, packet)


def test_endpoint_rank_projection_matches_full_s138_rank_projection() -> None:
    _, packet, mapping, sol = frozen()
    endpoint = audit.endpoint_from_full(sol["judgement"])
    assert audit.endpoint_ranks(endpoint, mapping) == audit.s138.semantic_ranks(
        sol["judgement"], mapping
    )
    audit.validate_endpoint(endpoint, packet)


def test_endpoint_validator_is_closed_over_questions_sets_and_ids() -> None:
    _, packet, _, sol = frozen()
    endpoint = audit.endpoint_from_full(sol["judgement"])
    broken = copy.deepcopy(endpoint)
    broken["judgements"][0]["set_judgements"].pop()
    with pytest.raises(audit.S140Failure, match="evidence-set mismatch"):
        audit.validate_endpoint(broken, packet)

    broken = copy.deepcopy(endpoint)
    broken["judgements"][0]["set_judgements"][0][
        "minimum_sufficient_evidence_ids"
    ] = ["UNKNOWN"]
    with pytest.raises(audit.S140Failure, match="invalid minimum set"):
        audit.validate_endpoint(broken, packet)


def test_noncomplete_endpoint_cannot_carry_a_minimum_set() -> None:
    _, packet, _, sol = frozen()
    endpoint = audit.endpoint_from_full(sol["judgement"])
    row = endpoint["judgements"][0]["set_judgements"][0]
    row["answerability"] = "PARTIAL"
    with pytest.raises(audit.S140Failure, match="non-complete with evidence"):
        audit.validate_endpoint(endpoint, packet)


def test_incremental_caps_are_below_internal_ceiling() -> None:
    prereg, _, _, _ = frozen()
    incremental = audit.incremental_worst(
        prereg, prereg["models"]["completion"]["max_counted_input_tokens"]
    )
    total = (
        prereg["budget"]["known_s138_cost_before_s140_usd"]
        + prereg["budget"]["failed_520_unknown_cost_reserve_usd"]
        + incremental
    )
    assert incremental == prereg["budget"]["s140_incremental_caps_worst_case_usd"]
    assert total < prereg["budget"]["s138_internal_ceiling_usd"]
