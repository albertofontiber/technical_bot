import pytest

from src import config
from src.rag import coverage_runtime
from src.release_profiles import (
    C1_PROFILE,
    C1_V2_PROFILE,
    COVERAGE_LANE_FLAGS,
    OFF_PROFILE,
    load_coverage_release_policy,
    validate_release_contract,
)


def _validate(env, *, production=True, must_preserve=False, lanes=None):
    policy = load_coverage_release_policy(env)
    validate_release_contract(
        policy,
        production=production,
        must_preserve_enabled=must_preserve,
        coverage_lanes=lanes or {},
    )
    return policy


def test_explicit_off_is_inert_and_valid():
    policy = _validate(
        {"COVERAGE_RELEASE_PROFILE": OFF_PROFILE},
        must_preserve=False,
    )
    assert not policy.post_rerank_coverage
    assert not policy.structural_neighbor_coverage
    assert not policy.coverage_mandatory_callout
    assert not policy.mp_mandatory_verb_trigger


def test_c1_profile_is_one_complete_atomic_unit():
    policy = _validate(
        {"COVERAGE_RELEASE_PROFILE": C1_PROFILE},
        must_preserve=True,
        lanes={"RERANK_POOL_COVERAGE": False},
    )
    assert policy.post_rerank_coverage
    assert policy.structural_neighbor_coverage
    assert policy.coverage_mandatory_callout
    assert policy.mp_mandatory_verb_trigger
    assert not policy.document_local_coverage
    assert policy.safe_snapshot()["profile"] == C1_PROFILE
    assert policy.safe_snapshot()["document_local_coverage"] is False


def test_c1_v2_atomically_adds_only_document_local_lane():
    policy = _validate(
        {"COVERAGE_RELEASE_PROFILE": C1_V2_PROFILE},
        must_preserve=True,
    )
    assert policy.post_rerank_coverage
    assert policy.structural_neighbor_coverage
    assert policy.coverage_mandatory_callout
    assert policy.mp_mandatory_verb_trigger
    assert policy.document_local_coverage
    assert policy.safe_snapshot()["profile"] == C1_V2_PROFILE
    assert policy.safe_snapshot()["document_local_coverage"] is True


@pytest.mark.parametrize("profile", (C1_PROFILE, C1_V2_PROFILE))
def test_c1_requires_must_preserve_contract(profile):
    with pytest.raises(RuntimeError, match="MUST_PRESERVE_CONTRACT"):
        _validate(
            {"COVERAGE_RELEASE_PROFILE": profile},
            must_preserve=False,
        )


def test_c1_v1_rejects_document_local_leaf_override():
    with pytest.raises(RuntimeError, match="remove legacy overrides"):
        _validate(
            {
                "COVERAGE_RELEASE_PROFILE": C1_PROFILE,
                "DOCUMENT_LOCAL_COVERAGE": "on",
            },
            must_preserve=True,
        )


@pytest.mark.parametrize("profile", (C1_PROFILE, C1_V2_PROFILE))
def test_c1_profiles_reject_every_other_coverage_lane(profile):
    for lane in (
        "TABLE_PREAMBLE_CLOSURE",
        "CANONICAL_HYQ_COVERAGE",
        "COMPATIBILITY_BUNDLE_COVERAGE",
        "RERANK_POOL_COVERAGE",
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
    ):
        expected_error = (
            "isolates structural coverage"
            if profile == C1_PROFILE
            else "permits exactly"
        )
        with pytest.raises(RuntimeError, match=expected_error):
            _validate(
                {"COVERAGE_RELEASE_PROFILE": profile},
                must_preserve=True,
                lanes={lane: True},
            )


@pytest.mark.parametrize("profile", (OFF_PROFILE, C1_PROFILE, C1_V2_PROFILE))
def test_explicit_profiles_reject_all_profile_owned_leaf_flags(profile):
    for leaf in (
        "POST_RERANK_COVERAGE",
        "STRUCTURAL_NEIGHBOR_COVERAGE",
        "COVERAGE_MANDATORY_CALLOUT",
        "MP_MANDATORY_VERB_TRIGGER",
        "DOCUMENT_LOCAL_COVERAGE",
    ):
        with pytest.raises(RuntimeError, match="remove legacy overrides"):
            _validate(
                {"COVERAGE_RELEASE_PROFILE": profile, leaf: "off"},
                must_preserve=profile != OFF_PROFILE,
            )


def test_document_local_lane_is_inventoried_and_requires_master():
    assert "DOCUMENT_LOCAL_COVERAGE" in COVERAGE_LANE_FLAGS
    with pytest.raises(RuntimeError, match="require POST_RERANK_COVERAGE"):
        _validate(
            {"DOCUMENT_LOCAL_COVERAGE": "on"},
            production=False,
        )
    with pytest.raises(RuntimeError, match="requires STRUCTURAL_NEIGHBOR_COVERAGE"):
        _validate(
            {
                "POST_RERANK_COVERAGE": "on",
                "DOCUMENT_LOCAL_COVERAGE": "on",
            },
            production=False,
        )


def test_explicit_profile_rejects_ambiguous_legacy_override():
    env = {
        "COVERAGE_RELEASE_PROFILE": OFF_PROFILE,
        "COVERAGE_MANDATORY_CALLOUT": "on",
    }
    with pytest.raises(RuntimeError, match="remove legacy overrides"):
        _validate(env)


def test_legacy_c1_switches_are_forbidden_in_production():
    env = {
        "POST_RERANK_COVERAGE": "on",
        "STRUCTURAL_NEIGHBOR_COVERAGE": "on",
        "COVERAGE_MANDATORY_CALLOUT": "on",
        "MP_MANDATORY_VERB_TRIGGER": "on",
    }
    with pytest.raises(RuntimeError, match="explicit COVERAGE_RELEASE_PROFILE"):
        _validate(env, must_preserve=True)


def test_even_inert_legacy_mode_is_offline_only():
    with pytest.raises(RuntimeError, match="production requires an explicit"):
        _validate({})
    _validate({}, production=False)


def test_lane_without_master_and_cascade_without_pool_fail_fast():
    with pytest.raises(RuntimeError, match="require POST_RERANK_COVERAGE"):
        _validate(
            {},
            production=False,
            lanes={"CANONICAL_HYQ_COVERAGE": True},
        )

    with pytest.raises(RuntimeError, match="requires RERANK_POOL_COVERAGE"):
        _validate(
            {"POST_RERANK_COVERAGE": "on"},
            production=False,
            lanes={"STRUCTURAL_CASCADE_COVERAGE": True},
        )


def test_view_modifier_cannot_masquerade_as_an_append_lane():
    with pytest.raises(RuntimeError, match="at least one coverage lane"):
        _validate(
            {"POST_RERANK_COVERAGE": "on"},
            production=False,
            lanes={"LOGICAL_RECORD_COVERAGE": True},
        )
    with pytest.raises(RuntimeError, match="coverage modifiers require"):
        _validate(
            {},
            production=False,
            lanes={"LOGICAL_RECORD_COVERAGE": True},
        )


def test_unknown_profile_and_non_strict_legacy_flag_fail_fast():
    with pytest.raises(RuntimeError, match="COVERAGE_RELEASE_PROFILE"):
        load_coverage_release_policy({"COVERAGE_RELEASE_PROFILE": "latest"})
    with pytest.raises(RuntimeError, match=r"expected on\|off"):
        load_coverage_release_policy({"POST_RERANK_COVERAGE": "enabled"})


def test_profiled_runtime_facade_has_no_per_request_switch_overrides():
    with pytest.raises(TypeError, match="unexpected keyword argument 'enabled'"):
        coverage_runtime.apply_profiled_post_rerank_coverage(
            "query",
            [{"id": "prefix"}],
            enabled=True,
        )


def test_production_contract_is_independent_of_telegram_transport(monkeypatch):
    policy = load_coverage_release_policy(
        {
            "POST_RERANK_COVERAGE": "on",
            "STRUCTURAL_NEIGHBOR_COVERAGE": "on",
            "COVERAGE_MANDATORY_CALLOUT": "on",
            "MP_MANDATORY_VERB_TRIGGER": "on",
        }
    )
    for name in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
    ):
        monkeypatch.setattr(config, name, "present")
    monkeypatch.setattr(config, "COVERAGE_RELEASE_POLICY", policy)
    monkeypatch.setattr(config, "MUST_PRESERVE_CONTRACT", True)
    for name in (
        "TABLE_PREAMBLE_CLOSURE",
        "CANONICAL_HYQ_COVERAGE",
        "COMPATIBILITY_BUNDLE_COVERAGE",
        "RERANK_POOL_COVERAGE",
        "DOCUMENT_LOCAL_COVERAGE",
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
    ):
        monkeypatch.setattr(config, name, False)

    config.validate_config(require_telegram=False, production=False)
    with pytest.raises(RuntimeError, match="explicit COVERAGE_RELEASE_PROFILE"):
        config.validate_config(require_telegram=False, production=True)
