from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts import s277_c1_p1 as p1
from scripts import s277_c1_p1_product_adapter as product


QUESTION = "¿Cómo se programa el retardo de salida en la central PEARL?"
REPLICA = p1.Replica("hp017", "r1")


def _input_contract() -> dict:
    return {
        "hp017": {
            "question": QUESTION,
            "target_models": ["PEARL"],
            "query_for_retrieval": QUESTION,
            "available_models": None,
        }
    }


def _genesis() -> dict:
    return {
        "authorization_id": "auth-product-test",
        "authorization_receipt_sha256": "1" * 64,
        "run_id": "run-product-test",
        "run_genesis_sha256": "2" * 64,
        "runtime_layout_sha256": "3" * 64,
        "release_config_sha256": "4" * 64,
        "prereg_sha256": "5" * 64,
        "tested_commit_sha": "6" * 40,
        "tested_tree_sha": "7" * 40,
        "target_semantic_config": {
            "generation": {"visual_assets_registry": False}
        },
    }


def _spec(operation: str, provider: str, model: str, max_input: int, max_output: int):
    return SimpleNamespace(
        call_key=f"{REPLICA.key}:{operation}",
        provider=provider,
        model=model,
        max_input_tokens=max_input,
        max_output_tokens=max_output,
    )


class OfflineBoundary:
    def __init__(self, *, terminal_operation: str | None = None):
        self.run_genesis = _genesis()
        specs = [
            _spec("embedding", "voyage", "voyage-4-large", 2_000, 0),
            _spec("rerank", "anthropic", "claude-sonnet-4-6", 20_000, 1_000),
            _spec("synthesis", "anthropic", "claude-sonnet-4-6", 30_000, 3_500),
        ]
        self.budget = SimpleNamespace(specs={row.call_key: row for row in specs})
        self.intents: list[product.ProductProviderIntent] = []
        self.terminal_operation = terminal_operation

    def invoke_product(self, intent: product.ProductProviderIntent):
        self.intents.append(intent)
        if intent.operation == "embedding":
            payload = {
                "model": intent.model,
                "usage": {"total_tokens": 17},
                "embeddings": [[0.01] * 1024],
            }
        elif intent.operation == "rerank":
            payload = {
                "id": "msg_rerank_test",
                "model": intent.model,
                "stop_reason": (
                    "max_tokens" if self.terminal_operation == "rerank" else "end_turn"
                ),
                "usage": {"input_tokens": 321, "output_tokens": 12},
                "content": [{"type": "text", "text": str(list(range(10)))}],
            }
        else:
            payload = {
                "id": "msg_synthesis_test",
                "model": intent.model,
                "stop_reason": (
                    "max_tokens"
                    if self.terminal_operation == "synthesis"
                    else "end_turn"
                ),
                "usage": {"input_tokens": 654, "output_tokens": 40},
                "content": [
                    {
                        "type": "text",
                        "text": "Configure el retardo en Causa y Efecto [F1].",
                    }
                ],
            }
        receipt = product.build_transport_receipt(
            intent=intent,
            payload=payload,
            provider_request_id=f"req_{intent.operation}_test",
            observed_at=datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc),
        )
        return product.ProductProviderResult(payload, receipt)


def _chunks() -> list[dict]:
    return [
        {
            "id": f"chunk-{index}",
            "content": f"Texto fuente {index}: programación del retardo.",
            "similarity": 0.95,
            "product_model": "PEARL",
            "section_title": "Causa y Efecto",
            "content_type": "text",
            "source_file": "Pearl.pdf",
            "page_number": index + 1,
        }
        for index in range(11)
    ]


def _runtime(monkeypatch) -> product.ProductRuntime:
    from src.rag import generator as generator_module
    from src.rag import serving_pipeline
    from src.reingest.embed import embed

    def retrieve(query: str, **_kwargs):
        embed([query], input_type="query")
        return _chunks()

    def structural_fetcher(seeds, **_kwargs):
        candidate = {
            **_chunks()[0],
            "id": "coverage-1",
            "content": "Retardo de activación de salidas y tipo de retardo.",
            "page_number": 20,
        }
        return list(seeds), [candidate], {"status": "ok", "rows": 1}

    def coverage(query, prefix, *, retrieval_pool, structural_fetcher):
        _hydrated, candidates, _trace = structural_fetcher(prefix[:1], limit=4)
        return prefix + candidates[:1], {
            "enabled": True,
            "status": "appended",
            "lanes": ["structural"],
        }

    def planner(_query, _chunks_arg, answer, *args, **kwargs):
        return answer + "\nPlan verificado.", {"status": "evaluated"}

    def must_preserve(_query, _chunks_arg, answer, *args, **kwargs):
        return answer + "\nContrato conservado.", {"status": "evaluated"}

    monkeypatch.setattr(serving_pipeline, "apply_profiled_post_rerank_coverage", coverage)
    monkeypatch.setattr(generator_module, "apply_answer_planner", planner)
    monkeypatch.setattr(generator_module, "apply_must_preserve_contract", must_preserve)

    base = product.load_product_runtime()
    return replace(
        base,
        retrieve=retrieve,
        observe_structural_shadow=lambda _query, _rows: None,
        structural_fetcher=structural_fetcher,
    )


class _PostgrestReceiptSource:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls == 1:
            return ()
        return (
            {
                "schema": product.POSTGREST_REQUEST_RECEIPT_SCHEMA,
                "ordinal": 1,
                "method": "POST",
                "path": "/rest/v1/rpc/match_chunks_v2",
                "status": 200,
                "request_id": "postgrest-product-test",
                "body_sha256": "8" * 64,
            },
        )


def _adapter(monkeypatch) -> product.ProductReplicaAdapter:
    return product.ProductReplicaAdapter(
        input_contract=_input_contract(),
        postgrest_receipt_source=_PostgrestReceiptSource(),
        postgrest_manifest_sha256="9" * 64,
        visual_assets_registry="off",
        runtime=_runtime(monkeypatch),
    )


def _provider_call(intent: product.ProductProviderIntent) -> p1.ProviderCall:
    envelope = intent.request
    return p1.ProviderCall(
        call_key=envelope["call_key"],
        provider=envelope["provider"],
        model=envelope["model"],
        request=envelope["request"],
        run_genesis_sha256=envelope["run_genesis_sha256"],
        lineage_input_sha256=envelope["lineage_input_sha256"],
        input_tokens_upper_bound=envelope["input_tokens_upper_bound"],
        max_output_tokens=envelope["max_output_tokens"],
        max_retries=envelope["max_retries"],
        prompt_cache=envelope["prompt_cache"],
        inference_geo=envelope["inference_geo"],
        service_tier=envelope["service_tier"],
    )


def test_real_product_prompts_run_once_through_offline_boundary(monkeypatch):
    boundary = OfflineBoundary()
    adapter = _adapter(monkeypatch)

    execution = adapter.execute_replica(REPLICA, boundary)

    assert [intent.operation for intent in boundary.intents] == list(
        p1.CALL_OPERATIONS
    )
    rerank_request = boundary.intents[1]
    synthesis_request = boundary.intents[2]
    assert rerank_request.max_output_tokens == 512
    assert rerank_request.physical_payload["max_tokens"] == 512
    assert set(rerank_request.request) == p1._PROVIDER_CALL_ENVELOPE_KEYS
    assert "Pregunta del técnico PCI" in rerank_request.physical_payload["messages"][0][
        "content"
    ]
    assert "system" not in rerank_request.physical_payload
    assert synthesis_request.physical_payload["system"]
    assert "Fragmentos relevantes" in synthesis_request.physical_payload["messages"][0][
        "content"
    ]
    assert execution.receipt["provider"]["stop_reason"] == "end_turn"
    assert execution.adapter_attestation["entrypoint_calls"] == 1
    assert execution.adapter_attestation["provider_operations"] == list(
        p1.CALL_OPERATIONS
    )
    assert (
        execution.adapter_attestation["postgrest_transport_attestation"]
        == "GUARDED_HTTP_RECEIPTS_PERSISTED"
    )
    assert execution.adapter_attestation["postgrest_manifest_sha256"] == "9" * 64
    assert len(execution.adapter_attestation["postgrest_request_receipts"]) == 1
    for intent in boundary.intents:
        spec = boundary.budget.specs[intent.call_key]
        p1.ProviderBoundary._validate_request_envelope(_provider_call(intent), spec)


def test_preregistered_rerank_bound_covers_full_product_preview_envelope(monkeypatch):
    from src.rag import reranker

    captured = {}

    class FakeClient:
        def __init__(self):
            self.messages = SimpleNamespace(create=self.create)

        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(text=json.dumps(list(range(10))))]
            )

    monkeypatch.setattr(reranker.anthropic, "Anthropic", lambda **_kwargs: FakeClient())
    chunks = [
        {
            "content": "x" * 800,
            "product_model": "PEARL",
            "section_title": "Causa y Efecto",
            "content_type": "text",
        }
        for _index in range(43)
    ]

    reranker.rerank_chunks(
        QUESTION,
        chunks,
        top_k=10,
        target_models=["PEARL"],
        strict=True,
    )

    bound = p1.physical_input_token_upper_bound(captured)
    prereg = p1.load_data_object(p1.CANONICAL_PREREG_PATH)
    configured = prereg["cost"]["operations"]["rerank"]["max_input_tokens"]
    assert bound > 10_000
    assert bound <= configured == 95_000


def test_missing_boundary_hook_holds_before_network(monkeypatch):
    runtime = _runtime(monkeypatch)
    boundary = SimpleNamespace(
        run_genesis=_genesis(), budget=OfflineBoundary().budget
    )
    adapter = product.ProductReplicaAdapter(
        input_contract=_input_contract(),
        postgrest_receipt_source=_PostgrestReceiptSource(),
        postgrest_manifest_sha256="9" * 64,
        visual_assets_registry="off",
        runtime=runtime,
    )

    with pytest.raises(p1.P1Error) as caught:
        adapter.execute_replica(REPLICA, boundary)

    assert caught.value.code == "HOLD_PRODUCT_BOUNDARY_HOOK_NOT_INSTALLED"


def test_non_terminal_rerank_is_no_go_and_blocks_synthesis(monkeypatch):
    boundary = OfflineBoundary(terminal_operation="rerank")
    adapter = _adapter(monkeypatch)

    with pytest.raises(p1.P1Error) as caught:
        adapter.execute_replica(REPLICA, boundary)

    assert caught.value.code == "NO_GO_PRODUCT_TERMINAL_STOP"
    assert [intent.operation for intent in boundary.intents] == [
        "embedding",
        "rerank",
    ]


def test_local_pre_wal_p1_error_survives_strict_reranker_wrapper(monkeypatch):
    boundary = OfflineBoundary()
    original_invoke = boundary.invoke_product

    def invoke_product(intent):
        if intent.operation == "rerank":
            raise p1.P1Error("HOLD_INPUT_TOKEN_BOUND", intent.call_key)
        return original_invoke(intent)

    boundary.invoke_product = invoke_product

    with pytest.raises(p1.P1Error) as caught:
        _adapter(monkeypatch).execute_replica(REPLICA, boundary)

    assert caught.value.code == "HOLD_INPUT_TOKEN_BOUND"
    assert [intent.operation for intent in boundary.intents] == ["embedding"]


def test_anthropic_transport_captures_raw_http_receipt_without_retry(monkeypatch):
    import anthropic

    intent = product.ProductProviderIntent(
        replica_key=REPLICA.key,
        operation="rerank",
        call_key=f"{REPLICA.key}:rerank",
        provider="anthropic",
        model="claude-sonnet-4-6",
        physical_payload={
            "model": "claude-sonnet-4-6",
            "max_tokens": 512,
            "temperature": 0,
            "messages": [{"role": "user", "content": "prompt"}],
        },
        lineage_input=_chunks(),
        run_genesis_sha256="2" * 64,
        max_output_tokens=512,
    )
    payload = {
        "id": "msg_raw",
        "model": intent.model,
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 2},
        "content": [{"type": "text", "text": "[0]"}],
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    observed = {}

    class FakeClient:
        def __init__(self, **kwargs):
            observed["client"] = kwargs
            raw = SimpleNamespace(
                content=body,
                status_code=200,
                retries_taken=0,
                request_id="req_anthropic_raw",
            )
            self.messages = SimpleNamespace(
                with_raw_response=SimpleNamespace(
                    create=lambda **request: observed.setdefault("request", request)
                    or raw
                )
            )

    # Avoid the truthiness trick in the lambda after recording the request.
    def factory(**kwargs):
        client = FakeClient(**kwargs)

        def create(**request):
            observed["request"] = request
            return SimpleNamespace(
                content=body,
                status_code=200,
                retries_taken=0,
                request_id="req_anthropic_raw",
            )

        client.messages.with_raw_response.create = create
        return client

    monkeypatch.setattr(anthropic, "Anthropic", factory)
    adapter = product.ProductSDKPaidAdapter(
        anthropic_api_key="anthropic-test", voyage_api_key="voyage-test"
    )

    response = adapter.prepare(_provider_call(intent)).send()

    receipt = response.pop("_p1_transport_receipt")
    assert response == payload
    assert observed["client"]["max_retries"] == 0
    assert observed["request"] == intent.physical_payload
    assert receipt["provider_request_id"] == "req_anthropic_raw"
    assert receipt["response_body_sha256"] == hashlib.sha256(body).hexdigest()
    assert receipt["sdk_retries_taken"] == 0


def test_voyage_transport_intercepts_one_raw_request_and_restores(monkeypatch):
    import voyageai
    from voyageai.api_resources.api_requestor import APIRequestor

    intent = product.ProductProviderIntent(
        replica_key=REPLICA.key,
        operation="embedding",
        call_key=f"{REPLICA.key}:embedding",
        provider="voyage",
        model="voyage-4-large",
        physical_payload={
            "model": "voyage-4-large",
            "input_type": "query",
            "texts": [QUESTION],
            "truncation": True,
        },
        lineage_input=_input_contract()["hp017"],
        run_genesis_sha256="2" * 64,
        max_output_tokens=0,
    )
    raw_payload = {
        "model": "voyage-4-large",
        "usage": {"total_tokens": 9},
        "data": [{"index": 0, "embedding": "base64-on-wire"}],
    }
    body = json.dumps(raw_payload, separators=(",", ":")).encode()
    raw = SimpleNamespace(
        content=body,
        status_code=200,
        headers={"request-id": "req_voyage_raw"},
    )
    calls = []

    def fake_request_raw(_requestor, *args, **kwargs):
        calls.append((args, kwargs))
        return raw

    class FakeVoyageClient:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0

        def embed(self, texts, **kwargs):
            APIRequestor.request_raw(object(), "post", "/embeddings")
            return SimpleNamespace(embeddings=[[0.1, 0.2]])

    original = APIRequestor.request_raw
    # voyageai 0.2.4 ships a stale module-level value; distribution metadata
    # remains the canonical version attestation.
    monkeypatch.setattr(voyageai, "__version__", "0.2.3")
    monkeypatch.setattr(voyageai, "Client", FakeVoyageClient)
    monkeypatch.setattr(APIRequestor, "request_raw", fake_request_raw)
    monkeypatch.setattr(product, "package_version", lambda _name: "0.2.4")
    adapter = product.ProductSDKPaidAdapter(
        anthropic_api_key="anthropic-test", voyage_api_key="voyage-test"
    )

    response = adapter.prepare(_provider_call(intent)).send()

    receipt = response.pop("_p1_transport_receipt")
    assert len(calls) == 1
    assert response["data"][0]["embedding"] == [0.1, 0.2]
    assert receipt["provider_request_id"] == "req_voyage_raw"
    assert receipt["response_body_sha256"] == hashlib.sha256(body).hexdigest()
    assert APIRequestor.request_raw is fake_request_raw
    monkeypatch.setattr(APIRequestor, "request_raw", original)


def test_provider_boundary_product_hook_delegates_to_canonical_invoke(monkeypatch):
    intent = product.ProductProviderIntent(
        replica_key=REPLICA.key,
        operation="embedding",
        call_key=f"{REPLICA.key}:embedding",
        provider="voyage",
        model="voyage-4-large",
        physical_payload={
            "model": "voyage-4-large",
            "input_type": "query",
            "texts": [QUESTION],
            "truncation": True,
        },
        lineage_input=_input_contract()["hp017"],
        run_genesis_sha256="2" * 64,
        max_output_tokens=0,
    )
    spec = _spec("embedding", "voyage", "voyage-4-large", 2_000, 0)
    call = _provider_call(intent)
    payload = {
        "model": intent.model,
        "usage": {"total_tokens": 9},
        "data": [{"index": 0, "embedding": [0.1, 0.2]}],
    }
    transport = product.build_transport_receipt(
        intent=intent, payload=payload, provider_request_id="req_hook"
    )
    boundary = object.__new__(p1.ProviderBoundary)
    boundary.budget = SimpleNamespace(specs={intent.call_key: spec})
    boundary.run_genesis = {"run_genesis_sha256": "2" * 64}
    observed = {}

    def rebuild(envelope, **kwargs):
        observed["envelope"] = envelope
        observed["rebuild"] = kwargs
        return call

    def invoke(_self, delegated_call):
        observed["call"] = delegated_call
        return {**payload, "_p1_transport_receipt": transport}

    monkeypatch.setattr(p1, "provider_call_from_sealed_envelope", rebuild)
    monkeypatch.setattr(p1.ProviderBoundary, "invoke", invoke)

    result = boundary.invoke_product(intent)

    assert observed["envelope"] == intent.request
    assert observed["call"] is call
    assert result.payload == payload
    assert result.transport_receipt == transport
