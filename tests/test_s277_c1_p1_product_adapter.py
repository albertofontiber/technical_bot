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
            "document_id": "doc-pearl",
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

    def conflict_guard(_query, _chunks_arg, answer, *args, **kwargs):
        return answer + "\nConflictos verificados.", {
            "schema": "answer_conflict_guard_v1",
            "action": "not_applicable",
        }

    monkeypatch.setattr(serving_pipeline, "apply_profiled_post_rerank_coverage", coverage)
    monkeypatch.setattr(generator_module, "apply_answer_planner", planner)
    monkeypatch.setattr(generator_module, "apply_must_preserve_contract", must_preserve)
    monkeypatch.setattr(
        generator_module, "apply_answer_conflict_guard", conflict_guard
    )

    base = product.load_product_runtime()
    return replace(
        base,
        retrieve=retrieve,
        observe_structural_shadow=lambda _query, _rows: None,
        structural_fetcher=structural_fetcher,
    )


class _PostgrestReceiptSource:
    def __init__(self, *, visual: bool = False, document_local: bool = False):
        self.calls = 0
        self.visual = visual
        self.document_local = document_local

    def __call__(self):
        self.calls += 1
        if self.calls == 1:
            return ()
        receipts = [
            {
                "schema": product.POSTGREST_REQUEST_RECEIPT_SCHEMA,
                "ordinal": 1,
                "method": "POST",
                "path": "/rest/v1/rpc/match_chunks_v2",
                "status": 200,
                "request_id": "postgrest-product-test",
                "body_sha256": "8" * 64,
            },
        ]
        if self.visual:
            receipts.append(
                {
                    "schema": product.POSTGREST_REQUEST_RECEIPT_SCHEMA,
                    "ordinal": 2,
                    "method": "GET",
                    "path": p1.VISUAL_REST_GET_PATH,
                    "status": 200,
                    "request_id": "postgrest-visual-test",
                    "body_sha256": "a" * 64,
                }
            )
        if self.document_local:
            receipts.append(
                {
                    "schema": product.POSTGREST_REQUEST_RECEIPT_SCHEMA,
                    "ordinal": len(receipts) + 1,
                    "method": "GET",
                    "path": product._DOCUMENT_LOCAL_RPC_PATH,
                    "status": 200,
                    "request_id": "postgrest-document-local-test",
                    "body_sha256": "b" * 64,
                }
            )
        return tuple(receipts)


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


def _document_local_v2_runtime(monkeypatch) -> product.ProductRuntime:
    from src.rag import serving_pipeline

    runtime = _runtime(monkeypatch)

    def coverage(query, prefix, *, retrieval_pool, structural_fetcher):
        del query, retrieval_pool
        _hydrated, candidates, _trace = structural_fetcher(prefix[:1], limit=4)
        document_local = {
            **_chunks()[1],
            "id": "document-local-target",
            "retrieval_lane": product._DOCUMENT_LOCAL_LANE,
            "document_local_coverage_validated": True,
        }
        return [*prefix, candidates[0], document_local], {
            "enabled": True,
            "status": "appended",
            "lanes": [
                {
                    "lane": "structural_neighbor_coverage_v1",
                    "status": "selected",
                    "selected_ids": [candidates[0]["id"]],
                    "http_requests": 0,
                },
                {
                    "lane": product._DOCUMENT_LOCAL_LANE,
                    "status": "selected",
                    "selected_ids": [document_local["id"]],
                    "satisfied_ids": [document_local["id"]],
                    "satisfaction_route": "coverage_append",
                    "http_requests": 1,
                    "seed_sources": {"governed_source_contract": 1},
                    "seed_scope_count": 1,
                    "seed_scopes_sha256": "c" * 64,
                    "seed_scopes_truncated": False,
                },
            ],
            "appended_ids": [candidates[0]["id"], document_local["id"]],
        }

    monkeypatch.setattr(serving_pipeline, "apply_profiled_post_rerank_coverage", coverage)
    return runtime


def test_v2_binds_one_document_local_lane_trace_to_one_physical_get(monkeypatch):
    boundary = OfflineBoundary()
    boundary.run_genesis["target_semantic_config"]["coverage"] = {
        "release_profile": "coverage_c1_v2",
        "document_local_coverage": True,
    }
    adapter = product.ProductReplicaAdapter(
        input_contract=_input_contract(),
        postgrest_receipt_source=_PostgrestReceiptSource(document_local=True),
        postgrest_manifest_sha256="9" * 64,
        visual_assets_registry="off",
        runtime=_document_local_v2_runtime(monkeypatch),
    )

    execution = adapter.execute_replica(REPLICA, boundary)

    attestation = execution.adapter_attestation
    evidence = attestation["document_local_coverage"]
    assert evidence["lane_trace"]["selected_ids"] == ["document-local-target"]
    assert evidence["physical_get_ordinals"] == [2]
    assert evidence["served_selected_ids"] == ["document-local-target"]
    assert evidence["served_satisfied_ids"] == ["document-local-target"]
    assert attestation["coverage_trace_sha256"] == p1.sha256_json(
        attestation["coverage_trace"]
    )
    assert attestation["attestation_sha256"] == p1.sha256_json(
        {key: value for key, value in attestation.items() if key != "attestation_sha256"}
    )


def _document_local_contract_inputs(*, status: str = "selected"):
    selected_ids = ["document-local-target"] if status == "selected" else []
    satisfied_ids = (
        ["document-local-target"]
        if status in {"selected", "best_candidate_already_covered"}
        else []
    )
    satisfaction_route = {
        "selected": "coverage_append",
        "best_candidate_already_covered": "already_served",
    }.get(status)
    lane = {
        "lane": product._DOCUMENT_LOCAL_LANE,
        "status": status,
        "selected_ids": selected_ids,
        "satisfied_ids": satisfied_ids,
        "satisfaction_route": satisfaction_route,
        "http_requests": 1,
        "seed_sources": {"governed_source_contract": 1},
        "seed_scope_count": 1,
        "seed_scopes_sha256": "c" * 64,
        "seed_scopes_truncated": False,
    }
    trace = {
        "lanes": [lane],
        "appended_ids": list(selected_ids),
    }
    served = [
        {
            "id": "document-local-target",
            "retrieval_lane": (
                product._DOCUMENT_LOCAL_LANE
                if status == "selected"
                else "protected_rerank_prefix"
            ),
            "document_local_coverage_validated": status == "selected",
        }
    ]
    physical = [
        {
            "ordinal": 2,
            "method": "GET",
            "path": product._DOCUMENT_LOCAL_RPC_PATH,
        }
    ]
    return trace, served, physical


@pytest.mark.parametrize("replica_key", ["hp011:r1", "hp011:r2"])
def test_hp011_v2_requires_selected_id_served_in_context(replica_key):
    trace, served, physical = _document_local_contract_inputs()

    evidence = product._validated_document_local_coverage_evidence(
        replica_key=replica_key,
        coverage_trace=trace,
        served=served,
        postgrest_receipts=physical,
        required=True,
    )

    assert evidence["served_selected_ids"] == ["document-local-target"]
    assert evidence["served_satisfied_ids"] == ["document-local-target"]


@pytest.mark.parametrize("replica_key", ["hp011:r1", "hp011:r2"])
def test_hp011_v2_accepts_authoritative_winner_already_served_once(replica_key):
    trace, served, physical = _document_local_contract_inputs(
        status="best_candidate_already_covered"
    )

    evidence = product._validated_document_local_coverage_evidence(
        replica_key=replica_key,
        coverage_trace=trace,
        served=served,
        postgrest_receipts=physical,
        required=True,
    )

    assert evidence["served_selected_ids"] == []
    assert evidence["served_satisfied_ids"] == ["document-local-target"]
    assert evidence["lane_trace"]["satisfaction_route"] == "already_served"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing_lane", "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRACE"),
        ("duplicate_lane", "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRACE"),
        ("lane_error", "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRACE"),
        ("missing_get", "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRANSPORT"),
        (
            "selected_not_served",
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_SELECTED_NOT_SERVED",
        ),
        (
            "already_satisfied_not_served",
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_SATISFIED_NOT_SERVED",
        ),
        ("satisfaction_route_mismatch", "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRACE"),
        ("hp011_missing_get", "NO_GO_PRODUCT_DOCUMENT_LOCAL_TARGET_GET"),
        (
            "hp011_not_selected",
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_TARGET_SATISFACTION",
        ),
        (
            "missing_seed_authority",
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_SEED_AUTHORITY",
        ),
        (
            "seed_authority_count_mismatch",
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_SEED_AUTHORITY",
        ),
        (
            "seed_authority_invalid_hash",
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_SEED_AUTHORITY",
        ),
        (
            "seed_authority_mixed_governed_route",
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_SEED_AUTHORITY",
        ),
        (
            "hp011_wrong_seed_route",
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_TARGET_SEED_ROUTE",
        ),
    ],
)
def test_v2_document_local_contract_fails_closed(mutation, expected_code):
    trace, served, physical = _document_local_contract_inputs()
    replica_key = "hp017:r1"
    if mutation == "missing_lane":
        trace["lanes"] = []
    elif mutation == "duplicate_lane":
        trace["lanes"].append(dict(trace["lanes"][0]))
    elif mutation == "lane_error":
        trace["lanes"][0].update(status="error", selected_ids=[])
    elif mutation == "missing_get":
        physical = []
    elif mutation == "selected_not_served":
        served = []
    elif mutation == "already_satisfied_not_served":
        trace, served, physical = _document_local_contract_inputs(
            status="best_candidate_already_covered"
        )
        served = []
    elif mutation == "satisfaction_route_mismatch":
        trace["lanes"][0]["satisfaction_route"] = "already_served"
    elif mutation == "hp011_missing_get":
        replica_key = "hp011:r1"
        trace, served, physical = _document_local_contract_inputs(
            status="no_query_aligned_candidate"
        )
        trace["lanes"][0]["http_requests"] = 0
        physical = []
    elif mutation == "hp011_not_selected":
        replica_key = "hp011:r1"
        trace, served, physical = _document_local_contract_inputs(
            status="no_query_aligned_candidate"
        )
    elif mutation == "missing_seed_authority":
        trace["lanes"][0].pop("seed_sources")
    elif mutation == "seed_authority_count_mismatch":
        trace["lanes"][0]["seed_scope_count"] = 2
    elif mutation == "seed_authority_invalid_hash":
        trace["lanes"][0]["seed_scopes_sha256"] = "not-a-sha256"
    elif mutation == "seed_authority_mixed_governed_route":
        trace["lanes"][0].update(
            seed_sources={
                "governed_source_contract": 1,
                "served_structural_append": 1,
            },
            seed_scope_count=2,
        )
    elif mutation == "hp011_wrong_seed_route":
        replica_key = "hp011:r1"
        trace["lanes"][0]["seed_sources"] = {"served_structural_append": 1}

    with pytest.raises(p1.P1Error) as caught:
        product._validated_document_local_coverage_evidence(
            replica_key=replica_key,
            coverage_trace=trace,
            served=served,
            postgrest_receipts=physical,
            required=True,
        )

    assert caught.value.code == expected_code


def test_v1_rejects_an_unexpected_document_local_get():
    trace, served, physical = _document_local_contract_inputs()

    with pytest.raises(p1.P1Error) as caught:
        product._validated_document_local_coverage_evidence(
            replica_key=REPLICA.key,
            coverage_trace=trace,
            served=served,
            postgrest_receipts=physical,
            required=False,
        )

    assert caught.value.code == "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRANSPORT"


def test_visual_probe_seals_lookup_preexisting_and_transport_selection(monkeypatch):
    from src.rag import generator as generator_module
    from src.rag import visual_assets as visual_module

    runtime = _runtime(monkeypatch)
    monkeypatch.setattr(generator_module, "VISUAL_ASSETS_REGISTRY", True)

    def lookup(document_id, page_number):
        return [
            {
                "document_id": document_id,
                "page_index": page_number,
                "page_label": "A-1",
                "storage_url": "https://assets.test/pearl-delay.png",
                "media_type": "image/png",
                "asset_scope": "page",
                "visual_role": "procedure",
                "technical_utility": "useful",
            }
        ]

    monkeypatch.setattr(visual_module, "lookup_visual_assets", lookup)
    boundary = OfflineBoundary()
    boundary.run_genesis["target_semantic_config"]["generation"][
        "visual_assets_registry"
    ] = True
    adapter = product.ProductReplicaAdapter(
        input_contract=_input_contract(),
        postgrest_receipt_source=_PostgrestReceiptSource(visual=True),
        postgrest_manifest_sha256="9" * 64,
        visual_assets_registry="on",
        runtime=runtime,
    )

    execution = adapter.execute_replica(REPLICA, boundary)

    visual = execution.receipt["visual_assets"]
    assert visual["preexisting_assets"] == []
    assert visual["preexisting_assets_sha256"] == p1.sha256_json([])
    assert visual["lookup_receipts"] == [
        {
            "request": {
                "method": "GET",
                "relation": p1.VISUAL_REST_GET_SURFACE,
                "document_id": "doc-pearl",
                "page_index": 1,
                "technical_utility": "useful",
                "visual_roles": list(p1.VISUAL_SERVABLE_ROLES),
            },
            "request_sha256": visual["lookup_receipts"][0]["request_sha256"],
            "response": [lookup("doc-pearl", 1)[0]],
            "response_sha256": visual["lookup_receipts"][0]["response_sha256"],
        }
    ]
    assert visual["selected_assets"] == [
        {
            "url": "https://assets.test/pearl-delay.png",
            "product": "Pearl",
            "section": "pág. A-1",
            "content_type": "procedure",
        }
    ]
    p1._validate_visual_asset_lineage(
        visual,
        visual_enabled=True,
        answer=execution.receipt["answer"],
        served_context=execution.receipt["served_context"],
        effective_sha=execution.receipt["effective_config"][
            "semantic_config_sha256"
        ],
        answer_sha=execution.receipt["answer_sha256"],
        replica_key=REPLICA.key,
    )
    p1._validate_product_visual_transport_lineage(
        execution.adapter_attestation,
        visual,
        replica_key=REPLICA.key,
    )

    without_get = dict(execution.adapter_attestation)
    without_get["postgrest_request_receipts"] = without_get[
        "postgrest_request_receipts"
    ][:1]
    with pytest.raises(p1.P1Error) as caught:
        p1._validate_product_visual_transport_lineage(
            without_get,
            visual,
            replica_key=REPLICA.key,
        )
    assert caught.value.code == "NO_GO_PRODUCT_VISUAL_TRANSPORT"


def test_visual_on_requires_the_product_append_stage(monkeypatch):
    boundary = OfflineBoundary()
    boundary.run_genesis["target_semantic_config"]["generation"][
        "visual_assets_registry"
    ] = True
    adapter = product.ProductReplicaAdapter(
        input_contract=_input_contract(),
        postgrest_receipt_source=_PostgrestReceiptSource(),
        postgrest_manifest_sha256="9" * 64,
        visual_assets_registry="on",
        runtime=_runtime(monkeypatch),
    )

    with pytest.raises(p1.P1Error) as caught:
        adapter.execute_replica(REPLICA, boundary)

    assert caught.value.code == "NO_GO_PRODUCT_STAGE_COUNT"


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


def test_paid_adapter_preflights_both_sdks_before_prepare(monkeypatch):
    observed_distributions = []

    def version(distribution):
        observed_distributions.append(distribution)
        return {"anthropic": "0.97.0", "voyageai": "0.2.4"}[distribution]

    monkeypatch.setattr(product, "package_version", version)
    adapter = product.ProductSDKPaidAdapter(
        anthropic_api_key="anthropic-test", voyage_api_key="voyage-test"
    )
    assert observed_distributions == ["anthropic", "voyageai"]

    def cold_discovery(_distribution):  # pragma: no cover - must stay unused
        raise AssertionError("prepare must not discover SDK metadata")

    monkeypatch.setattr(product, "package_version", cold_discovery)
    voyage_intent = product.ProductProviderIntent(
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
    anthropic_intent = product.ProductProviderIntent(
        replica_key=REPLICA.key,
        operation="rerank",
        call_key=f"{REPLICA.key}:rerank",
        provider="anthropic",
        model="claude-sonnet-4-6",
        physical_payload={
            "model": "claude-sonnet-4-6",
            "max_tokens": 32,
            "temperature": 0,
            "messages": [{"role": "user", "content": "prompt"}],
        },
        lineage_input=_chunks(),
        run_genesis_sha256="2" * 64,
        max_output_tokens=32,
    )

    assert adapter.prepare(_provider_call(voyage_intent))._call.provider == "voyage"
    assert (
        adapter.prepare(_provider_call(anthropic_intent))._call.provider
        == "anthropic"
    )


def test_paid_adapter_fails_construction_on_any_sdk_version_drift(monkeypatch):
    monkeypatch.setattr(
        product,
        "package_version",
        lambda distribution: {
            "anthropic": "0.97.0",
            "voyageai": "0.2.3",
        }[distribution],
    )

    with pytest.raises(p1.P1Error) as caught:
        product.ProductSDKPaidAdapter(
            anthropic_api_key="anthropic-test", voyage_api_key="voyage-test"
        )

    assert caught.value.code == "HOLD_PROVIDER_SDK_VERSION"


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
    monkeypatch.setattr(
        product,
        "package_version",
        lambda distribution: {
            "anthropic": "0.97.0",
            "voyageai": "0.2.4",
        }[distribution],
    )
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
