import pytest

from src import config
from src.rag import coverage_runtime
from src.release_profiles import (
    C1_PROFILE,
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
    assert policy.safe_snapshot()["profile"] == C1_PROFILE


def test_c1_requires_must_preserve_contract():
    with pytest.raises(RuntimeError, match="MUST_PRESERVE_CONTRACT"):
        _validate(
            {"COVERAGE_RELEASE_PROFILE": C1_PROFILE},
            must_preserve=False,
        )


def test_c1_rejects_unreleased_lane():
    with pytest.raises(RuntimeError, match="isolates structural coverage"):
        _validate(
            {"COVERAGE_RELEASE_PROFILE": C1_PROFILE},
            must_preserve=True,
            lanes={"RERANK_POOL_COVERAGE": True},
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
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
    ):
        monkeypatch.setattr(config, name, False)

    config.validate_config(require_telegram=False, production=False)
    with pytest.raises(RuntimeError, match="explicit COVERAGE_RELEASE_PROFILE"):
        config.validate_config(require_telegram=False, production=True)
