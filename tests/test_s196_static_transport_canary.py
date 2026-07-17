from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

import scripts.s196_static_transport_canary as s196
from scripts.s196_static_transport_canary import (
    FACETS,
    FORBIDDEN_SCHEMA_KEYS,
    SYNTHETIC_FIXTURE,
    classify_bad_request,
    execute,
    normalize_canary,
    static_transport_schema,
    validate_static_schema,
    write_json_exclusive,
)


def _point(*, active, claim="", facet="", supports=("", "", "")):
    return {
        "active": active,
        "claim": claim,
        "facet": facet,
        "support_1": supports[0],
        "support_2": supports[1],
        "support_3": supports[2],
    }


def _valid_payload():
    return {
        "item_id": "s196_canary_01",
        "eligible": True,
        "question": "What must be done before and after maintenance?",
        "answer_point_slots": {
            "point_1": _point(
                active=True,
                claim="Disconnect power before maintenance.",
                facet=FACETS[0],
                supports=("E001", "", ""),
            ),
            "point_2": _point(
                active=True,
                claim="Reinstall the safety cover before restoring power.",
                facet=FACETS[3],
                supports=("E002", "", ""),
            ),
            "point_3": _point(active=False),
            "point_4": _point(active=False),
        },
    }


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def test_static_schema_has_no_arrays_refs_combinators_or_dynamic_values():
    schema = static_transport_schema()
    validate_static_schema(schema)
    assert not any(node.get("type") == "array" for node in _walk_dicts(schema))
    assert not any(FORBIDDEN_SCHEMA_KEYS.intersection(node) for node in _walk_dicts(schema))
    serialized = json.dumps(schema)
    assert SYNTHETIC_FIXTURE["item_id"] not in serialized
    assert "E001" not in serialized
    assert not any(facet in serialized for facet in FACETS)


def test_static_schema_is_deterministic_and_has_exact_rectangular_slots():
    assert static_transport_schema() == static_transport_schema()
    slots = static_transport_schema()["properties"]["answer_point_slots"]
    assert slots["required"] == ["point_1", "point_2", "point_3", "point_4"]
    for point in slots["properties"].values():
        assert point["required"] == [
            "active",
            "claim",
            "facet",
            "support_1",
            "support_2",
            "support_3",
        ]


def test_valid_static_payload_normalizes_to_canonical_arrays():
    normalized = normalize_canary(_valid_payload())
    assert normalized["eligible"] is True
    assert len(normalized["answer_points"]) == 2
    assert [point["support_unit_ids"] for point in normalized["answer_points"]] == [
        ["E001"],
        ["E002"],
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["answer_point_slots"]["point_1"].update(
                support_1="UNKNOWN"
            ),
            "unknown support ID",
        ),
        (
            lambda payload: payload["answer_point_slots"]["point_1"].update(
                support_2="E001"
            ),
            "duplicate support ID",
        ),
        (
            lambda payload: payload["answer_point_slots"]["point_3"].update(
                claim="hidden content"
            ),
            "inactive answer-point slot",
        ),
        (
            lambda payload: payload["answer_point_slots"]["point_1"].update(
                support_1="", support_2="E001"
            ),
            "support slots must be non-empty then empty",
        ),
    ],
)
def test_deterministic_adapter_rejects_invalid_support_shapes(mutation, message):
    payload = _valid_payload()
    mutation(payload)
    with pytest.raises(ValueError, match=message):
        normalize_canary(payload)


def test_deterministic_adapter_rejects_noncontiguous_active_points():
    payload = _valid_payload()
    payload["answer_point_slots"]["point_2"] = _point(active=False)
    payload["answer_point_slots"]["point_3"] = _point(
        active=True,
        claim="Late point",
        facet=FACETS[3],
        supports=("E002", "", ""),
    )
    with pytest.raises(ValueError, match="contiguous"):
        normalize_canary(payload)


def test_deterministic_adapter_rejects_wrong_identity_or_duplicate_claim():
    wrong = _valid_payload()
    wrong["item_id"] = "other"
    with pytest.raises(ValueError, match="wrong synthetic item_id"):
        normalize_canary(wrong)
    duplicate = copy.deepcopy(_valid_payload())
    duplicate["answer_point_slots"]["point_2"]["claim"] = duplicate[
        "answer_point_slots"
    ]["point_1"]["claim"]
    with pytest.raises(ValueError, match="claims must be distinct"):
        normalize_canary(duplicate)


def test_fixture_is_synthetic_and_contains_no_document_or_chunk_identifiers():
    assert SYNTHETIC_FIXTURE["manufacturer"] == "SYNTHETIC_VENDOR"
    assert SYNTHETIC_FIXTURE["product_model"] == "CANARY_MODEL_1"
    assert set(SYNTHETIC_FIXTURE) == {
        "item_id",
        "manufacturer",
        "product_model",
        "evidence_units",
    }
    assert "document_id" not in json.dumps(SYNTHETIC_FIXTURE)
    assert "chunk_id" not in json.dumps(SYNTHETIC_FIXTURE)


def test_exclusive_prepaid_checkpoint_rejects_a_second_owner(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    write_json_exclusive(checkpoint, {"owner": 1})
    with pytest.raises(FileExistsError):
        write_json_exclusive(checkpoint, {"owner": 2})


class _Usage:
    def model_dump(self, *, mode):
        assert mode == "json"
        return {"input_tokens": 100, "output_tokens": 80}


class _Messages:
    def __init__(self, events, lock_path, checkpoint_path, *, counted_input=100):
        self.events = events
        self.lock_path = lock_path
        self.checkpoint_path = checkpoint_path
        self.counted_input = counted_input

    def count_tokens(self, **kwargs):
        assert self.lock_path.exists()
        assert kwargs["output_config"]["format"]["type"] == "json_schema"
        self.events.append("preflight")
        return SimpleNamespace(input_tokens=self.counted_input)

    def create(self, **kwargs):
        assert self.checkpoint_path.exists()
        self.events.append("inference_after_checkpoint")
        return SimpleNamespace(
            id="msg_synthetic_canary",
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(_valid_payload()))],
            usage=_Usage(),
        )


def _prereg():
    return {
        "model": s196.EXPECTED_MODEL,
        "sdk": s196.EXPECTED_SDK,
        "pricing_usd_per_million_tokens": s196.EXPECTED_PRICING,
        "budget": s196.EXPECTED_BUDGET,
    }


def test_execution_uses_zero_retries_and_preflight_checkpoint_inference_order(
    tmp_path, monkeypatch
):
    receipts = tmp_path / "receipts.json"
    lock = tmp_path / "lock.json"
    prepaid = tmp_path / "prepaid.json"
    result = tmp_path / "result.json"
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-only\n", encoding="utf-8")
    monkeypatch.setattr(s196, "DEFAULT_RECEIPTS", receipts)
    monkeypatch.setattr(s196, "DEFAULT_LOCK", lock)
    monkeypatch.setattr(s196, "DEFAULT_PREPAID", prepaid)
    monkeypatch.setattr(s196, "DEFAULT_RESULT", result)
    events = []

    def factory(*, api_key, max_retries):
        assert api_key == "test-only"
        assert lock.exists()
        events.append(f"factory_retries_{max_retries}")
        return SimpleNamespace(messages=_Messages(events, lock, prepaid))

    outcome = execute(_prereg(), env_file, client_factory=factory)
    assert outcome["status"] == "GO_STATIC_TRANSPORT_COMPILED"
    assert events == [
        "factory_retries_0",
        "preflight",
        "inference_after_checkpoint",
    ]
    sealed = json.loads(receipts.read_text(encoding="utf-8"))
    assert sealed["completed_calls"] == 1
    assert sealed["provider_accepted_schema"] is True
    assert sealed["receipts"][0]["raw_synthetic_output"]
    assert lock.exists()
    assert prepaid.exists()
    before = list(events)
    with pytest.raises(RuntimeError, match="checkpoint exists"):
        execute(_prereg(), env_file, client_factory=factory)
    assert events == before


def test_budget_failure_stops_before_checkpoint_or_inference(tmp_path, monkeypatch):
    receipts = tmp_path / "receipts.json"
    lock = tmp_path / "lock.json"
    prepaid = tmp_path / "prepaid.json"
    result = tmp_path / "result.json"
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-only\n", encoding="utf-8")
    monkeypatch.setattr(s196, "DEFAULT_RECEIPTS", receipts)
    monkeypatch.setattr(s196, "DEFAULT_LOCK", lock)
    monkeypatch.setattr(s196, "DEFAULT_PREPAID", prepaid)
    monkeypatch.setattr(s196, "DEFAULT_RESULT", result)
    events = []

    def factory(*, api_key, max_retries):
        return SimpleNamespace(
            messages=_Messages(events, lock, prepaid, counted_input=50_000)
        )

    with pytest.raises(RuntimeError, match="preflight exceeds budget"):
        execute(_prereg(), env_file, client_factory=factory)
    assert events == ["preflight"]
    assert lock.exists()
    assert not prepaid.exists()
    assert not receipts.exists()
    assert not result.exists()


class _ProviderError(Exception):
    status_code = 400
    request_id = "req_synthetic"

    def __init__(self, message):
        super().__init__(message)
        self.body = {"error": {"type": "invalid_request_error", "message": message}}


def test_bad_request_classification_is_stage_and_message_specific():
    compile_error = _ProviderError("Schema is too complex for compilation")
    parameter_error = _ProviderError("Unknown model parameter")
    assert classify_bad_request("preflight", compile_error) == (
        "NO_GO_PREFLIGHT_REQUEST_REJECTED",
        False,
    )
    assert classify_bad_request("inference", compile_error) == (
        "NO_GO_STATIC_SCHEMA_COMPILE_REJECTED",
        True,
    )
    assert classify_bad_request("inference", parameter_error) == (
        "NO_GO_INFERENCE_REQUEST_REJECTED_UNATTRIBUTED",
        False,
    )
    assert classify_bad_request(
        "inference",
        _ProviderError("Schema compilation succeeded; request complexity exceeded"),
    ) == ("NO_GO_INFERENCE_REQUEST_REJECTED_UNATTRIBUTED", False)
    assert classify_bad_request(
        "inference",
        _ProviderError("Request complexity exceeded while schema remained valid"),
    ) == ("NO_GO_INFERENCE_REQUEST_REJECTED_UNATTRIBUTED", False)


def test_isolated_workspace_lock_blocks_before_client_construction(tmp_path, monkeypatch):
    lock = tmp_path / "lock.json"
    prepaid = tmp_path / "prepaid.json"
    receipts = tmp_path / "receipts.json"
    result = tmp_path / "result.json"
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-only\n", encoding="utf-8")
    lock.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(s196, "DEFAULT_LOCK", lock)
    monkeypatch.setattr(s196, "DEFAULT_PREPAID", prepaid)
    monkeypatch.setattr(s196, "DEFAULT_RECEIPTS", receipts)
    monkeypatch.setattr(s196, "DEFAULT_RESULT", result)

    def forbidden_factory(**kwargs):
        raise AssertionError("client must not be constructed when the lock exists")

    with pytest.raises(RuntimeError, match="checkpoint exists"):
        execute(_prereg(), env_file, client_factory=forbidden_factory)


def test_chunks_v3_lane_is_explicit_without_copying_historical_metrics():
    lane = s196.chunks_v3_lane()
    assert lane["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert lane["changed_by_s196"] is False
    assert lane["historical_metrics_duplicated"] is False
    assert "baseline" not in lane
