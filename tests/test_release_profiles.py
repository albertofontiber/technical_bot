import pytest

from src import config
from src.rag import coverage_runtime
from src.release_profiles import (
    C1_PROFILE,
    C1_V2_PROFILE,
    C1_V3_PROFILE,
    C1_V4_PROFILE,
    COVERAGE_LANE_FLAGS,
    OFF_PROFILE,
    PROFILE_OWNED_FLAGS,
    load_coverage_release_policy,
    validate_release_contract,
)


V3_NEW_FLAGS = (
    "EVIDENCE_CONTRACT",
    "OBLIGATION_WARNING_RESERVE",
    "PROSE_SOURCE_CARD",
)

V4_NEW_FLAG = "DOCUMENT_LOCAL_SELECTION_V2"


def _validate(env, *, production=True, must_preserve=False, lanes=None):
    policy = load_coverage_release_policy(env)
    validate_release_contract(
        policy,
        production=production,
        must_preserve_enabled=must_preserve,
        coverage_lanes=lanes or {},
        identity_resolve_policy=env.get("IDENTITY_RESOLVE_POLICY"),
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


def test_c1_v3_enables_all_eight_flags_atomically():
    policy = _validate(
        {
            "COVERAGE_RELEASE_PROFILE": C1_V3_PROFILE,
            "IDENTITY_RESOLVE_POLICY": "replace",
        },
        must_preserve=True,
    )
    assert policy.post_rerank_coverage
    assert policy.structural_neighbor_coverage
    assert policy.coverage_mandatory_callout
    assert policy.mp_mandatory_verb_trigger
    assert policy.document_local_coverage
    assert policy.evidence_contract
    assert policy.obligation_warning_reserve
    assert policy.prose_source_card
    snapshot = policy.safe_snapshot()
    assert snapshot["profile"] == C1_V3_PROFILE
    assert snapshot["evidence_contract"] is True
    assert snapshot["obligation_warning_reserve"] is True
    assert snapshot["prose_source_card"] is True
    for name in V3_NEW_FLAGS:
        assert policy.flag(name) is True


@pytest.mark.parametrize("profile", (OFF_PROFILE, C1_PROFILE, C1_V2_PROFILE))
def test_earlier_profiles_leave_v3_flags_off(profile):
    policy = load_coverage_release_policy({"COVERAGE_RELEASE_PROFILE": profile})
    assert policy.evidence_contract is False
    assert policy.obligation_warning_reserve is False
    assert policy.prose_source_card is False
    snapshot = policy.safe_snapshot()
    assert snapshot["evidence_contract"] is False
    assert snapshot["obligation_warning_reserve"] is False
    assert snapshot["prose_source_card"] is False


@pytest.mark.parametrize("profile", (C1_PROFILE, C1_V2_PROFILE))
def test_v1_and_v2_do_not_require_identity_replace(profile):
    _validate({"COVERAGE_RELEASE_PROFILE": profile}, must_preserve=True)
    _validate(
        {
            "COVERAGE_RELEASE_PROFILE": profile,
            "IDENTITY_RESOLVE_POLICY": "add",
        },
        must_preserve=True,
    )


@pytest.mark.parametrize("identity_env", ({}, {"IDENTITY_RESOLVE_POLICY": "add"}))
def test_c1_v3_fails_fast_unless_identity_policy_is_replace(identity_env):
    with pytest.raises(
        RuntimeError, match="requires IDENTITY_RESOLVE_POLICY=replace"
    ):
        _validate(
            {"COVERAGE_RELEASE_PROFILE": C1_V3_PROFILE, **identity_env},
            must_preserve=True,
        )


def test_c1_v3_identity_check_mirrors_resolver_normalisation():
    # The live resolver strips/lowercases and maps empty to the historical
    # 'add' default; the contract must judge the same resolved value.
    _validate(
        {
            "COVERAGE_RELEASE_PROFILE": C1_V3_PROFILE,
            "IDENTITY_RESOLVE_POLICY": " REPLACE ",
        },
        must_preserve=True,
    )
    with pytest.raises(
        RuntimeError, match="requires IDENTITY_RESOLVE_POLICY=replace"
    ):
        _validate(
            {
                "COVERAGE_RELEASE_PROFILE": C1_V3_PROFILE,
                "IDENTITY_RESOLVE_POLICY": "",
            },
            must_preserve=True,
        )


def test_c1_v3_requires_must_preserve_contract():
    with pytest.raises(RuntimeError, match="MUST_PRESERVE_CONTRACT"):
        _validate(
            {
                "COVERAGE_RELEASE_PROFILE": C1_V3_PROFILE,
                "IDENTITY_RESOLVE_POLICY": "replace",
            },
            must_preserve=False,
        )


def test_c1_v3_rejects_every_other_coverage_lane():
    for lane in (
        "TABLE_PREAMBLE_CLOSURE",
        "CANONICAL_HYQ_COVERAGE",
        "COMPATIBILITY_BUNDLE_COVERAGE",
        "RERANK_POOL_COVERAGE",
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
    ):
        with pytest.raises(RuntimeError, match="permits exactly"):
            _validate(
                {
                    "COVERAGE_RELEASE_PROFILE": C1_V3_PROFILE,
                    "IDENTITY_RESOLVE_POLICY": "replace",
                },
                must_preserve=True,
                lanes={lane: True},
            )


@pytest.mark.parametrize(
    "profile", (OFF_PROFILE, C1_PROFILE, C1_V2_PROFILE, C1_V3_PROFILE)
)
def test_explicit_profiles_reject_v3_leaf_overrides(profile):
    for leaf in V3_NEW_FLAGS:
        with pytest.raises(RuntimeError, match="remove legacy overrides"):
            _validate(
                {
                    "COVERAGE_RELEASE_PROFILE": profile,
                    "IDENTITY_RESOLVE_POLICY": "replace",
                    leaf: "off",
                },
                must_preserve=profile != OFF_PROFILE,
            )


def test_legacy_reads_v3_flags_from_env_strict_and_default_off():
    default = load_coverage_release_policy({})
    assert default.evidence_contract is False
    assert default.obligation_warning_reserve is False
    assert default.prose_source_card is False

    enabled = load_coverage_release_policy(
        {name: "on" for name in V3_NEW_FLAGS}
    )
    assert enabled.evidence_contract is True
    assert enabled.obligation_warning_reserve is True
    assert enabled.prose_source_card is True

    with pytest.raises(RuntimeError, match=r"expected on\|off"):
        load_coverage_release_policy({"EVIDENCE_CONTRACT": "enabled"})


def test_v3_flag_couplings_hold_even_in_legacy_mode():
    with pytest.raises(
        RuntimeError, match="EVIDENCE_CONTRACT requires MUST_PRESERVE_CONTRACT"
    ):
        _validate(
            {"EVIDENCE_CONTRACT": "on"},
            production=False,
            must_preserve=False,
        )
    with pytest.raises(
        RuntimeError,
        match="OBLIGATION_WARNING_RESERVE requires POST_RERANK_COVERAGE",
    ):
        _validate(
            {"OBLIGATION_WARNING_RESERVE": "on"},
            production=False,
        )
    _validate(
        {
            "POST_RERANK_COVERAGE": "on",
            "STRUCTURAL_NEIGHBOR_COVERAGE": "on",
            "OBLIGATION_WARNING_RESERVE": "on",
        },
        production=False,
    )


def test_c1_v4_enables_v3_flags_plus_selection_v2_atomically():
    policy = _validate(
        {
            "COVERAGE_RELEASE_PROFILE": C1_V4_PROFILE,
            "IDENTITY_RESOLVE_POLICY": "replace",
        },
        must_preserve=True,
    )
    assert policy.post_rerank_coverage
    assert policy.structural_neighbor_coverage
    assert policy.coverage_mandatory_callout
    assert policy.mp_mandatory_verb_trigger
    assert policy.document_local_coverage
    assert policy.evidence_contract
    assert policy.obligation_warning_reserve
    assert policy.prose_source_card
    assert policy.document_local_selection_v2
    for name in PROFILE_OWNED_FLAGS:
        assert policy.flag(name) is True
    snapshot = policy.safe_snapshot()
    assert snapshot["profile"] == C1_V4_PROFILE
    assert snapshot["document_local_selection_v2"] is True


@pytest.mark.parametrize(
    "profile", (OFF_PROFILE, C1_PROFILE, C1_V2_PROFILE, C1_V3_PROFILE)
)
def test_earlier_profiles_leave_selection_v2_off(profile):
    policy = load_coverage_release_policy({"COVERAGE_RELEASE_PROFILE": profile})
    assert policy.document_local_selection_v2 is False
    assert policy.flag(V4_NEW_FLAG) is False
    assert policy.safe_snapshot()["document_local_selection_v2"] is False


def test_c1_v3_unit_stays_frozen_after_the_v4_extension():
    # coverage_c1_v3 is semantically frozen: exactly the eight s278 flags, and
    # never the s279 selection switch appended after them in the owned tuple.
    policy = load_coverage_release_policy(
        {"COVERAGE_RELEASE_PROFILE": C1_V3_PROFILE}
    )
    enabled = {name for name in PROFILE_OWNED_FLAGS if policy.flag(name)}
    assert enabled == set(PROFILE_OWNED_FLAGS[:8])
    assert PROFILE_OWNED_FLAGS[8] == V4_NEW_FLAG


def test_c1_v4_requires_must_preserve_contract():
    with pytest.raises(RuntimeError, match="MUST_PRESERVE_CONTRACT"):
        _validate(
            {
                "COVERAGE_RELEASE_PROFILE": C1_V4_PROFILE,
                "IDENTITY_RESOLVE_POLICY": "replace",
            },
            must_preserve=False,
        )


@pytest.mark.parametrize("identity_env", ({}, {"IDENTITY_RESOLVE_POLICY": "add"}))
def test_c1_v4_fails_fast_unless_identity_policy_is_replace(identity_env):
    with pytest.raises(
        RuntimeError,
        match="coverage_c1_v4 requires IDENTITY_RESOLVE_POLICY=replace",
    ):
        _validate(
            {"COVERAGE_RELEASE_PROFILE": C1_V4_PROFILE, **identity_env},
            must_preserve=True,
        )


def test_c1_v4_rejects_every_other_coverage_lane():
    for lane in (
        "TABLE_PREAMBLE_CLOSURE",
        "CANONICAL_HYQ_COVERAGE",
        "COMPATIBILITY_BUNDLE_COVERAGE",
        "RERANK_POOL_COVERAGE",
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
    ):
        with pytest.raises(RuntimeError, match="permits exactly"):
            _validate(
                {
                    "COVERAGE_RELEASE_PROFILE": C1_V4_PROFILE,
                    "IDENTITY_RESOLVE_POLICY": "replace",
                },
                must_preserve=True,
                lanes={lane: True},
            )


@pytest.mark.parametrize(
    "profile",
    (OFF_PROFILE, C1_PROFILE, C1_V2_PROFILE, C1_V3_PROFILE, C1_V4_PROFILE),
)
def test_explicit_profiles_reject_selection_v2_leaf_override(profile):
    with pytest.raises(RuntimeError, match="remove legacy overrides"):
        _validate(
            {
                "COVERAGE_RELEASE_PROFILE": profile,
                "IDENTITY_RESOLVE_POLICY": "replace",
                V4_NEW_FLAG: "off",
            },
            must_preserve=profile != OFF_PROFILE,
        )


def test_legacy_reads_selection_v2_from_env_strict_and_default_off():
    assert load_coverage_release_policy({}).document_local_selection_v2 is False
    enabled = load_coverage_release_policy(
        {
            V4_NEW_FLAG: "on",
            "DOCUMENT_LOCAL_COVERAGE": "on",
        }
    )
    assert enabled.document_local_selection_v2 is True
    with pytest.raises(RuntimeError, match=r"expected on\|off"):
        load_coverage_release_policy({V4_NEW_FLAG: "enabled"})


def test_selection_v2_coupling_holds_even_in_legacy_mode():
    with pytest.raises(
        RuntimeError,
        match="DOCUMENT_LOCAL_SELECTION_V2 requires DOCUMENT_LOCAL_COVERAGE",
    ):
        _validate(
            {V4_NEW_FLAG: "on"},
            production=False,
        )
    _validate(
        {
            "POST_RERANK_COVERAGE": "on",
            "STRUCTURAL_NEIGHBOR_COVERAGE": "on",
            "DOCUMENT_LOCAL_COVERAGE": "on",
            V4_NEW_FLAG: "on",
        },
        production=False,
    )


def test_production_profile_message_lists_v4():
    with pytest.raises(
        RuntimeError,
        match="coverage_c1_v2, coverage_c1_v3, or coverage_c1_v4",
    ):
        _validate({})


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
