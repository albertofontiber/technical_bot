from __future__ import annotations

import copy

import pytest

from scripts.s125_project_m1_reconciled_bridge import (
    PREREG_PATH,
    build_from_files,
    build_projection,
    canonical_sha256,
    load_json,
    load_yaml,
)


def _inputs():
    prereg = load_yaml(PREREG_PATH)
    root = PREREG_PATH.parent.parent
    receipts = prereg["frozen_inputs"]
    prior = load_yaml(root / receipts["prior_hybrid_gate"]["path"])
    replay = load_json(root / receipts["migrated_cohort_replay"]["path"])
    bridge = load_json(root / receipts["atomic_bridge"]["path"])
    return prereg, prior, replay, bridge


def test_real_projection_reconciles_exact_histogram_without_bot_credit():
    result = build_from_files()
    diagnostic = result["provisional_hybrid_diagnostic"]
    assert diagnostic["content_denominator"] == 157
    assert diagnostic["stage_histogram"] == {
        "OK": 111,
        "rest": 5,
        "retrieval-miss": 2,
        "synthesis-miss": 12,
        "synthesis-not-measured": 27,
    }
    assert diagnostic["measured_content_denominator"] == 130
    assert diagnostic["measured_ok_rate"] == pytest.approx(111 / 130)
    assert diagnostic["all_provisional_content_ok_rate"] == pytest.approx(111 / 157)
    assert diagnostic["provisional_target_ok_for_95_percent"] == 150
    assert diagnostic["provisional_gap_to_95_percent"] == 39
    limitations = result["credit_and_limitations"]
    assert limitations["facts_moved_to_ok_due_to_bot_change"] == 0
    assert limitations["confirmed_ok_claims_exposed_by_measurement_reconciliation"] == 32
    assert limitations["remaining_provisional_legacy_carries"] == 77
    assert limitations["official_atomic_content_denominator"] is None
    assert limitations["official_ok_count"] is None
    assert limitations["official_95_percent_claim"] is None


def test_projection_fails_if_prior_hold_population_drifts():
    prereg, prior, replay, bridge = _inputs()
    tampered = copy.deepcopy(prior)
    tampered["reconciled_hybrid_diagnostic"]["stage_histogram"]["known-m1-contract-hold"] = 32
    with pytest.raises(ValueError, match="prior hold population mismatch"):
        build_projection(prereg, tampered, replay, bridge)


def test_supplementary_claim_cannot_leak_into_content_funnel():
    prereg, prior, replay, bridge = _inputs()
    tampered = copy.deepcopy(replay)
    row = next(row for row in tampered["rows"] if not row["content_eligible"])
    old_stage = row["stage_bucket"]
    row["stage_bucket"] = "OK"
    histogram = tampered["summary"]["supplementary_stage_histogram"]
    histogram[old_stage] -= 1
    if histogram[old_stage] == 0:
        histogram.pop(old_stage)
    histogram["OK"] = 1
    body = dict(tampered)
    body.pop("payload_sha256")
    tampered["payload_sha256"] = canonical_sha256(body)
    tampered_prereg = copy.deepcopy(prereg)
    tampered_prereg["frozen_inputs"]["migrated_cohort_replay"]["payload_sha256"] = tampered[
        "payload_sha256"
    ]
    with pytest.raises(ValueError, match="supplementary claim leaked"):
        build_projection(tampered_prereg, prior, tampered, bridge)


def test_replay_summary_is_recomputed_from_rows():
    prereg, prior, replay, bridge = _inputs()
    tampered = copy.deepcopy(replay)
    tampered["summary"]["content_stage_histogram"]["OK"] += 1
    body = dict(tampered)
    body.pop("payload_sha256")
    tampered["payload_sha256"] = canonical_sha256(body)
    tampered_prereg = copy.deepcopy(prereg)
    tampered_prereg["frozen_inputs"]["migrated_cohort_replay"]["payload_sha256"] = tampered[
        "payload_sha256"
    ]
    with pytest.raises(ValueError, match="replay summary does not match rows"):
        build_projection(tampered_prereg, prior, tampered, bridge)


def test_projection_is_deterministic():
    assert build_from_files() == build_from_files()
