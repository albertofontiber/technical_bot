from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from scripts import s277_c1_p1 as p1
from scripts import s277_c1_p1_release_config as release_config


NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


def _raw_variables() -> dict[str, str]:
    return {
        **release_config.REQUIRED_EXACT_VALUES,
        "VISUAL_ASSETS_REGISTRY": "on",
        "COVERAGE_MANDATORY_CALLOUT": "on",
        "MP_MANDATORY_VERB_TRIGGER": "on",
        "SUPABASE_SERVICE_KEY": "must-never-escape",
        "ANTHROPIC_API_KEY": "must-never-escape-either",
    }


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key.casefold(), default)


class _Response:
    status = 200

    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")
        self.headers = _Headers({"x-request-id": "railway-request-1"})

    def read(self) -> bytes:
        return self._raw


def _opener_for(raw_variables: dict[str, str]):
    def opener(request, timeout):
        assert timeout == 20
        assert request.full_url == release_config.RAILWAY_GRAPHQL_URL
        assert request.get_header("Project-access-token") == "operator-token"
        return _Response({"data": {"variables": raw_variables}})

    return opener


def test_capture_projects_only_safe_variables_and_resolves_defaults():
    receipt = release_config.capture_railway_snapshot(
        token="operator-token",
        now=NOW,
        opener=_opener_for(_raw_variables()),
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert "must-never-escape" not in encoded
    assert "SUPABASE_SERVICE_KEY" not in encoded
    assert "ANTHROPIC_API_KEY" not in encoded
    assert receipt["ignored_variable_count"] == 2
    assert receipt["live_snapshot"]["HYDE_ENABLED"] == "false"
    assert receipt["live_snapshot"]["TABLE_PREAMBLE_CLOSURE"] == "off"
    assert receipt["live_snapshot"]["VISUAL_ASSETS_REGISTRY"] == "on"
    assert receipt["receipt_sha256"] == p1.sha256_json(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )
    assert release_config.verify_railway_snapshot_receipt(
        receipt, now=NOW
    ) == receipt


def test_capture_rejects_required_drift_without_exposing_value():
    raw = _raw_variables()
    raw["RERANK_TOP_K"] = "11"
    with pytest.raises(release_config.RailwaySnapshotError) as caught:
        release_config.capture_railway_snapshot(
            token="operator-token",
            now=NOW,
            opener=_opener_for(raw),
        )

    assert "11" not in str(caught.value)
    assert "RERANK_TOP_K" in str(caught.value)


def test_verify_rejects_stale_or_tampered_receipt():
    receipt = release_config.capture_railway_snapshot(
        token="operator-token",
        now=NOW,
        opener=_opener_for(_raw_variables()),
    )
    with pytest.raises(release_config.RailwaySnapshotError, match="stale"):
        release_config.verify_railway_snapshot_receipt(
            receipt, now=NOW + timedelta(minutes=31)
        )

    tampered = json.loads(json.dumps(receipt))
    tampered["live_snapshot"]["VISUAL_ASSETS_REGISTRY"] = "off"
    with pytest.raises(
        release_config.RailwaySnapshotError, match="hash|provenance"
    ):
        release_config.verify_railway_snapshot_receipt(tampered, now=NOW)


def test_projection_requires_visual_flag_to_be_explicit():
    raw = _raw_variables()
    raw.pop("VISUAL_ASSETS_REGISTRY")
    with pytest.raises(release_config.RailwaySnapshotError, match="physically present"):
        release_config.project_safe_snapshot(raw)


def test_presence_only_values_can_never_escape_receipt():
    raw = _raw_variables()
    raw["COVERAGE_RELEASE_PROFILE"] = "sk-live-must-not-escape"
    raw["POST_RERANK_COVERAGE"] = "another-secret-value"
    receipt = release_config.capture_railway_snapshot(
        token="operator-token",
        now=NOW,
        opener=_opener_for(raw),
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert "sk-live-must-not-escape" not in encoded
    assert "another-secret-value" not in encoded
    assert {
        "COVERAGE_RELEASE_PROFILE",
        "POST_RERANK_COVERAGE",
    }.issubset(receipt["presence_only_names_present"])


def test_verify_rejects_rehashed_wrong_target_and_false_presence():
    receipt = release_config.capture_railway_snapshot(
        token="operator-token",
        now=NOW,
        opener=_opener_for(_raw_variables()),
    )
    wrong_target = json.loads(json.dumps(receipt))
    wrong_target["project_id"] = "wrong-production"
    wrong_target["receipt_sha256"] = p1.sha256_json(
        {key: value for key, value in wrong_target.items() if key != "receipt_sha256"}
    )
    with pytest.raises(release_config.RailwaySnapshotError, match="non-canonical"):
        release_config.verify_railway_snapshot_receipt(wrong_target, now=NOW)

    false_presence = json.loads(json.dumps(receipt))
    false_presence["safe_names_absent"].remove("ANSWER_OBLIGATION_PLANNER")
    false_presence["safe_names_present"].append("ANSWER_OBLIGATION_PLANNER")
    false_presence["safe_names_present"].sort()
    false_presence["receipt_sha256"] = p1.sha256_json(
        {key: value for key, value in false_presence.items() if key != "receipt_sha256"}
    )
    with pytest.raises(release_config.RailwaySnapshotError, match="provenance"):
        release_config.verify_railway_snapshot_receipt(false_presence, now=NOW)


def test_capture_rejects_noncanonical_ids_before_network():
    with pytest.raises(release_config.RailwaySnapshotError, match="canonical"):
        release_config.capture_railway_snapshot(
            token="operator-token",
            project_id="wrong",
            environment_id=release_config.RAILWAY_ENVIRONMENT_ID,
            service_id=release_config.RAILWAY_SERVICE_ID,
            now=NOW,
            opener=lambda *_args, **_kwargs: pytest.fail("network must not run"),
        )


def test_materialize_always_captures_live_in_same_call(monkeypatch):
    seen = {}

    def fake_materializer(receipt, **kwargs):
        seen["receipt"] = receipt
        seen["kwargs"] = kwargs
        return {"status": "built"}

    monkeypatch.setattr(
        release_config, "_materialize_verified_release_config", fake_materializer
    )
    result = release_config.materialize_release_config(
        token="operator-token",
        now=NOW,
        opener=_opener_for(_raw_variables()),
    )

    assert result == {"status": "built"}
    assert seen["receipt"]["project_id"] == release_config.RAILWAY_PROJECT_ID
    assert seen["receipt"]["captured_at"] == "2026-07-21T12:00:00Z"


def test_materialize_rejects_git_identity_change_after_hashing():
    receipt = release_config.capture_railway_snapshot(
        token="operator-token",
        now=NOW,
        opener=_opener_for(_raw_variables()),
    )
    initial = p1.RuntimeIdentity("a" * 40, "b" * 40, True, True)
    changed = p1.RuntimeIdentity("a" * 40, "b" * 40, True, False)
    observations = iter((initial, changed))

    with pytest.raises(release_config.RailwaySnapshotError, match="changed"):
        release_config._materialize_verified_release_config(
            receipt,
            now=NOW,
            identity_inspector=lambda: next(observations),
        )


def test_env_inventory_is_fail_closed_and_covers_mandated_switches(monkeypatch):
    for name in (
        "ANSWER_OBLIGATION_PLANNER",
        "GENERATOR_INCLUDE_CONTEXT",
        "IDENTITY_FETCH",
    ):
        assert name in release_config.ALLOWED_SAFE_VALUES

    monkeypatch.setattr(
        release_config,
        "_env_read_inventory",
        lambda: (frozenset({"NEW_UNSEALED_SWITCH"}), frozenset()),
    )
    with pytest.raises(release_config.RailwaySnapshotError, match="NEW_UNSEALED_SWITCH"):
        release_config.assert_env_inventory_complete()
