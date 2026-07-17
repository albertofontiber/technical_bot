from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

import scripts.s198_question_schema_canary as s198
from scripts.s198_question_schema_canary import (
    FORBIDDEN_SCHEMA_KEYS,
    SYNTHETIC_FIXTURE,
    canary_prompt,
    classify_bad_request,
    execute,
    normalize_canary,
    question_schema,
    validate_authorization,
    validate_question_schema,
)


def _valid_payload():
    return {
        "item_id": SYNTHETIC_FIXTURE["item_id"],
        "question": (
            "¿Qué debe hacer con la alimentación y la cubierta antes y después "
            "del mantenimiento?"
        ),
    }


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def test_question_schema_is_minimal_static_and_source_agnostic():
    schema = question_schema()
    validate_question_schema(schema)
    assert schema == {
        "type": "object",
        "additionalProperties": False,
        "required": ["item_id", "question"],
        "properties": {
            "item_id": {"type": "string"},
            "question": {"type": "string"},
        },
    }
    assert not any(node.get("type") == "array" for node in _walk_dicts(schema))
    assert not any(FORBIDDEN_SCHEMA_KEYS.intersection(node) for node in _walk_dicts(schema))
    serialized = json.dumps(schema)
    assert SYNTHETIC_FIXTURE["item_id"] not in serialized
    assert "SYNTHETIC_VENDOR" not in serialized
    assert "claim" not in serialized


def test_valid_payload_normalizes_whitespace_without_semantic_claim():
    payload = _valid_payload()
    payload["question"] = "  " + payload["question"].replace(" ", "  ") + "  "
    normalized = normalize_canary(payload)
    assert normalized == _valid_payload()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(item_id="other"), "wrong synthetic item_id"),
        (lambda value: value.update(question="corta"), "length bounds"),
        (
            lambda value: value.update(
                question="¿Qué indican los puntos aceptados de este fixture sintético?"
            ),
            "meta wording",
        ),
        (lambda value: value.update(extra="forbidden"), "Additional properties"),
    ],
)
def test_normalizer_rejects_structural_identity_bound_and_meta_errors(
    mutation, message
):
    payload = copy.deepcopy(_valid_payload())
    mutation(payload)
    with pytest.raises(ValueError, match=message):
        normalize_canary(payload)


def test_fixture_and_prompt_are_synthetic_and_contain_no_real_source_identity():
    serialized = json.dumps(SYNTHETIC_FIXTURE, ensure_ascii=False)
    assert SYNTHETIC_FIXTURE["manufacturer"] == "SYNTHETIC_VENDOR"
    assert len(SYNTHETIC_FIXTURE["accepted_points"]) == 2
    assert "document_id" not in serialized
    assert "chunk_id" not in serialized
    assert "source_file" not in serialized
    prompt = canary_prompt()
    assert SYNTHETIC_FIXTURE["item_id"] in prompt
    assert "accepted_points" in prompt
    assert "evidence_units" not in prompt


class _Usage:
    def model_dump(self, *, mode):
        assert mode == "json"
        return {"input_tokens": 120, "output_tokens": 45}


class _Messages:
    def __init__(self, events, lock_path, prepaid_path, *, counted_input=120):
        self.events = events
        self.lock_path = lock_path
        self.prepaid_path = prepaid_path
        self.counted_input = counted_input

    def count_tokens(self, **kwargs):
        assert self.lock_path.exists()
        assert kwargs["output_config"]["format"]["type"] == "json_schema"
        assert kwargs["output_config"]["format"]["schema"] == question_schema()
        self.events.append("preflight")
        return SimpleNamespace(input_tokens=self.counted_input)

    def create(self, **kwargs):
        assert self.prepaid_path.exists()
        assert kwargs["max_tokens"] == 300
        self.events.append("inference_after_checkpoint")
        return SimpleNamespace(
            id="msg_s198_synthetic_canary",
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(_valid_payload()))],
            usage=_Usage(),
        )


def _prereg():
    return {
        "model": s198.EXPECTED_MODEL,
        "sdk": s198.EXPECTED_SDK,
        "pricing_usd_per_million_tokens": s198.EXPECTED_PRICING,
        "budget": s198.EXPECTED_BUDGET,
    }


def _isolate_outputs(tmp_path, monkeypatch):
    paths = {
        "DEFAULT_LOCK": tmp_path / "lock.json",
        "DEFAULT_PREPAID": tmp_path / "prepaid.json",
        "DEFAULT_RECEIPTS": tmp_path / "receipts.json",
        "DEFAULT_RESULT": tmp_path / "result.json",
    }
    for name, path in paths.items():
        monkeypatch.setattr(s198, name, path)
    monkeypatch.setattr(s198.importlib.metadata, "version", lambda _: "0.97.0")
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-only\n", encoding="utf-8")
    return paths, env_file


def test_execution_orders_lock_preflight_prepaid_and_single_inference(
    tmp_path, monkeypatch
):
    paths, env_file = _isolate_outputs(tmp_path, monkeypatch)
    events = []

    def factory(*, api_key, max_retries):
        assert api_key == "test-only"
        assert paths["DEFAULT_LOCK"].exists()
        events.append(f"factory_retries_{max_retries}")
        return SimpleNamespace(
            messages=_Messages(
                events, paths["DEFAULT_LOCK"], paths["DEFAULT_PREPAID"]
            )
        )

    outcome = execute(_prereg(), env_file, client_factory=factory)
    assert outcome["status"] == "GO_QUESTION_SCHEMA_CANARY_COMPILED"
    assert outcome["semantic_quality_measured"] is False
    assert outcome["decision"]["fresh_s198_packet_authorized"] is True
    assert events == [
        "factory_retries_0",
        "preflight",
        "inference_after_checkpoint",
    ]
    receipts = json.loads(
        paths["DEFAULT_RECEIPTS"].read_text(encoding="utf-8")
    )
    assert receipts["completed_calls"] == 1
    assert receipts["provider_accepted_schema"] is True
    before = list(events)
    with pytest.raises(RuntimeError, match="checkpoint exists"):
        execute(_prereg(), env_file, client_factory=factory)
    assert events == before


def test_budget_failure_stops_after_preflight_before_paid_inference(
    tmp_path, monkeypatch
):
    paths, env_file = _isolate_outputs(tmp_path, monkeypatch)
    events = []

    def factory(*, api_key, max_retries):
        return SimpleNamespace(
            messages=_Messages(
                events,
                paths["DEFAULT_LOCK"],
                paths["DEFAULT_PREPAID"],
                counted_input=50_000,
            )
        )

    with pytest.raises(RuntimeError, match="preflight exceeds budget"):
        execute(_prereg(), env_file, client_factory=factory)
    assert events == ["preflight"]
    assert paths["DEFAULT_LOCK"].exists()
    assert not paths["DEFAULT_PREPAID"].exists()
    assert not paths["DEFAULT_RECEIPTS"].exists()
    assert not paths["DEFAULT_RESULT"].exists()


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
        "NO_GO_QUESTION_PREFLIGHT_REJECTED",
        False,
    )
    assert classify_bad_request("inference", compile_error) == (
        "NO_GO_QUESTION_SCHEMA_COMPILE_REJECTED",
        True,
    )
    assert classify_bad_request("inference", parameter_error) == (
        "NO_GO_QUESTION_INFERENCE_REJECTED_UNATTRIBUTED",
        False,
    )


def test_actual_prereg_and_permit_hashes_are_self_consistent():
    prereg = validate_authorization(s198.DEFAULT_PREREG, s198.DEFAULT_PERMIT)
    assert prereg["model"] == s198.EXPECTED_MODEL
    assert prereg["execution"]["real_document_items"] == 0


def test_chunks_v3_and_railway_remain_non_gates():
    lane = s198.chunks_v3_lane()
    assert lane["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert lane["changed_by_s198"] is False
    assert lane["historical_metrics_duplicated"] is False
