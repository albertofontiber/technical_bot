"""Product-path adapter for the S277 C1 P1 release gate.

This module deliberately does not weaken :mod:`scripts.s277_c1_p1`'s offline
boundary.  It executes the real ``execute_rag_turn`` orchestration and installs
short-lived provider proxies so that the *actual* kwargs assembled by the
product reranker and generator are handed to the P1 WAL/budget boundary.

The central runner needs one small, explicit hook before this adapter can be
installed::

    ProductProviderResult ProviderBoundary.invoke_product(
        ProductProviderIntent intent
    )

The hook must reserve/fsync the call, perform the live fence check, delegate
exactly once, fsync the raw response and transport receipt, and only then return
``ProductProviderResult``.  Until that method exists this adapter fails closed
with ``HOLD_PRODUCT_BOUNDARY_HOOK_NOT_INSTALLED``.  In particular, it never
falls back to the synthetic ``build_operation_payload`` prompts.

Provider proxying is process-global because the current product modules create
their SDK clients internally.  The scope is protected by a non-reentrant lock,
restores every patched object by identity, and is suitable only for the sealed,
single-thread P1 worker.  It must never be installed inside the Telegram bot.
No network call is made merely by importing or constructing this module.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import os
import threading
from types import SimpleNamespace
from typing import Any, Protocol

from scripts import s277_c1_p1 as p1


PRODUCT_INTENT_SCHEMA = "s277_c1_p1_product_provider_intent_v1"
PRODUCT_RESULT_SCHEMA = "s277_c1_p1_product_provider_result_v1"
TRANSPORT_RECEIPT_SCHEMA = "s277_c1_p1_provider_transport_receipt_v1"
PRODUCT_ATTESTATION_SCHEMA = "s277_c1_p1_product_adapter_attestation_v1"
POSTGREST_REQUEST_RECEIPT_SCHEMA = "s277_c1_p1_postgrest_request_receipt_v1"

_DOCUMENT_LOCAL_PROFILE = "coverage_c1_v2"
_DOCUMENT_LOCAL_LANE = "document_local_content_coverage_v1"
_DOCUMENT_LOCAL_RPC_PATH = "/rest/v1/rpc/document_local_snapshot_v2"
_DOCUMENT_LOCAL_REQUIRED_SELECTED_REPLICAS = frozenset(
    {"hp011:r1", "hp011:r2"}
)

_POSTGREST_GET_PATHS = frozenset(
    {"/rest/v1/chunks_v2", "/rest/v1/documents"}
)
_POSTGREST_VISUAL_PATH = "/rest/v1/document_visual_assets"
_POSTGREST_RPC_PATHS = frozenset(
    {
        "/rest/v1/rpc/match_chunks_v2",
        "/rest/v1/rpc/search_chunks_text_v2",
        "/rest/v1/rpc/match_chunks_v2_enunciados",
        "/rest/v1/rpc/match_hyq",
    }
)

_INSTALL_LOCK = threading.Lock()
_VOYAGE_HTTP_LOCK = threading.Lock()
_HEX64 = p1._HEX64


def _fail(code: str, message: str) -> None:
    raise p1.P1Error(code, message)


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        _fail(code, message)


def _json_copy(value: Any, *, field: str) -> Any:
    try:
        copied = json.loads(p1.canonical_json_bytes(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise p1.P1Error("HOLD_PRODUCT_ADAPTER_JSON", field) from exc
    _require(copied == value, "HOLD_PRODUCT_ADAPTER_JSON", field)
    return copied


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validated_postgrest_receipt_delta(
    *,
    before: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, Any]],
    visual_assets_registry: str,
    document_local_coverage: bool = False,
) -> list[dict[str, Any]]:
    """Bind one replica to the guarded PostgREST calls it actually made."""

    before_copy = _json_copy(list(before), field="PostgREST receipts before replica")
    after_copy = _json_copy(list(after), field="PostgREST receipts after replica")
    _require(
        after_copy[: len(before_copy)] == before_copy
        and [row.get("ordinal") for row in after_copy]
        == list(range(1, len(after_copy) + 1)),
        "NO_GO_POSTGREST_RECEIPT_DRIFT",
        "PostgREST receipt stream is not append-only and contiguous",
    )
    delta = after_copy[len(before_copy) :]
    _require(
        bool(delta),
        "NO_GO_POSTGREST_RECEIPT_MISSING",
        "product replica made no guarded PostgREST request",
    )
    allowed_get = set(_POSTGREST_GET_PATHS)
    if visual_assets_registry == "on":
        allowed_get.add(_POSTGREST_VISUAL_PATH)
    if document_local_coverage:
        allowed_get.add(_DOCUMENT_LOCAL_RPC_PATH)
    exact_keys = {
        "schema",
        "ordinal",
        "method",
        "path",
        "status",
        "request_id",
        "body_sha256",
    }
    for row in delta:
        method = row.get("method")
        path = row.get("path")
        request_id = row.get("request_id")
        _require(
            set(row) == exact_keys
            and row.get("schema") == POSTGREST_REQUEST_RECEIPT_SCHEMA
            and type(row.get("ordinal")) is int
            and type(row.get("status")) is int
            and 200 <= row["status"] < 300
            and isinstance(row.get("body_sha256"), str)
            and bool(_HEX64.fullmatch(row["body_sha256"]))
            and (
                request_id is None
                or (
                    isinstance(request_id, str)
                    and 0 < len(request_id) <= 256
                    and request_id.isprintable()
                )
            )
            and (
                (method == "GET" and path in allowed_get)
                or (method == "POST" and path in _POSTGREST_RPC_PATHS)
            ),
            "NO_GO_POSTGREST_RECEIPT_DRIFT",
            "invalid guarded PostgREST receipt",
        )
    _require(
        any(
            row["method"] == "POST"
            and row["path"] == "/rest/v1/rpc/match_chunks_v2"
            for row in delta
        ),
        "NO_GO_POSTGREST_PRIMARY_RETRIEVAL_MISSING",
        "match_chunks_v2 was not observed for the product replica",
    )
    return delta


def _document_local_v2_required(effective: Mapping[str, Any]) -> bool:
    """Resolve the v2 lane from the already sealed semantic configuration."""

    coverage = effective.get("coverage")
    if not isinstance(coverage, Mapping):
        return False
    profile = coverage.get("release_profile")
    enabled = coverage.get("document_local_coverage")
    if profile == _DOCUMENT_LOCAL_PROFILE:
        _require(
            enabled is True,
            "HOLD_PRODUCT_EFFECTIVE_CONFIG_DRIFT",
            "coverage_c1_v2 requires document_local_coverage=true",
        )
        return True
    _require(
        enabled is not True,
        "HOLD_PRODUCT_EFFECTIVE_CONFIG_DRIFT",
        "document_local_coverage=true requires coverage_c1_v2",
    )
    return False


def _validated_document_local_coverage_evidence(
    *,
    replica_key: str,
    coverage_trace: Mapping[str, Any],
    served: Sequence[Mapping[str, Any]],
    postgrest_receipts: Sequence[Mapping[str, Any]],
    required: bool,
) -> dict[str, Any] | None:
    """Bind the v2 semantic lane one-to-one to its guarded physical GET.

    PostgREST receipts intentionally expose only transport facts, not response
    contents.  The hash-bound coverage trace therefore supplies the semantic
    half of the proof while the receipt stream supplies the physical half.
    """

    physical_gets = [
        dict(row)
        for row in postgrest_receipts
        if row.get("method") == "GET"
        and row.get("path") == _DOCUMENT_LOCAL_RPC_PATH
    ]
    if not required:
        _require(
            not physical_gets,
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRANSPORT",
            f"unexpected document-local GET for {replica_key}",
        )
        return None

    lanes = coverage_trace.get("lanes")
    _require(
        isinstance(lanes, list)
        and all(isinstance(row, Mapping) for row in lanes),
        "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRACE",
        f"coverage lanes are absent for {replica_key}",
    )
    lane_traces = [
        row for row in lanes if row.get("lane") == _DOCUMENT_LOCAL_LANE
    ]
    _require(
        len(lane_traces) == 1,
        "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRACE",
        f"expected exactly one document-local lane trace for {replica_key}",
    )
    lane_trace = _json_copy(
        dict(lane_traces[0]), field=f"document-local trace {replica_key}"
    )
    status = lane_trace.get("status")
    _require(
        isinstance(status, str) and bool(status) and status != "error",
        "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRACE",
        f"document-local lane failed for {replica_key}",
    )
    http_requests = lane_trace.get("http_requests")
    _require(
        type(http_requests) is int
        and 0 <= http_requests <= 1
        and len(physical_gets) == http_requests,
        "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRANSPORT",
        f"document-local semantic/physical GET mismatch for {replica_key}",
    )
    selected_ids = lane_trace.get("selected_ids")
    _require(
        isinstance(selected_ids, list)
        and all(isinstance(chunk_id, str) and bool(chunk_id) for chunk_id in selected_ids)
        and len(selected_ids) == len(set(selected_ids))
        and ((status == "selected") is (len(selected_ids) == 1)),
        "NO_GO_PRODUCT_DOCUMENT_LOCAL_TRACE",
        f"invalid document-local selection trace for {replica_key}",
    )

    served_rows_by_id: dict[str, list[Mapping[str, Any]]] = {}
    for row in served:
        served_rows_by_id.setdefault(str(row.get("id") or ""), []).append(row)
    appended_ids = coverage_trace.get("appended_ids")
    if selected_ids:
        selected_id = selected_ids[0]
        selected_rows = served_rows_by_id.get(selected_id, [])
        _require(
            isinstance(appended_ids, list)
            and appended_ids.count(selected_id) == 1
            and len(selected_rows) == 1
            and selected_rows[0].get("retrieval_lane") == _DOCUMENT_LOCAL_LANE
            and selected_rows[0].get("document_local_coverage_validated") is True,
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_TARGET",
            f"selected document-local chunk was not served for {replica_key}",
        )

    if replica_key in _DOCUMENT_LOCAL_REQUIRED_SELECTED_REPLICAS:
        _require(
            status == "selected"
            and http_requests == 1
            and len(physical_gets) == 1
            and len(selected_ids) == 1,
            "NO_GO_PRODUCT_DOCUMENT_LOCAL_TARGET",
            f"required hp011 document-local recovery absent for {replica_key}",
        )

    return {
        "profile": _DOCUMENT_LOCAL_PROFILE,
        "lane_trace": lane_trace,
        "lane_trace_sha256": p1.sha256_json(lane_trace),
        "physical_get_ordinals": [row["ordinal"] for row in physical_gets],
        "physical_get_receipts_sha256": p1.sha256_json(physical_gets),
        "served_selected_ids": list(selected_ids),
    }


def _function_identity(fn: Callable[..., Any]) -> dict[str, str]:
    return {
        "module": str(getattr(fn, "__module__", "")),
        "qualname": str(getattr(fn, "__qualname__", "")),
    }


@dataclass(frozen=True)
class ProductProviderIntent:
    """Exact product SDK intent presented to the P1 physical boundary."""

    replica_key: str
    operation: str
    call_key: str
    provider: str
    model: str
    physical_payload: Mapping[str, Any]
    lineage_input: Any
    run_genesis_sha256: str
    max_output_tokens: int

    def __post_init__(self) -> None:
        _require(
            self.operation in p1.CALL_OPERATIONS,
            "HOLD_UNREGISTERED_CALL",
            self.operation,
        )
        _require(
            self.call_key == f"{self.replica_key}:{self.operation}",
            "HOLD_PRODUCT_CALL_KEY_DRIFT",
            self.call_key,
        )
        _require(
            isinstance(self.physical_payload, Mapping),
            "HOLD_PRODUCT_REQUEST_DRIFT",
            self.call_key,
        )

    @property
    def lineage_input_sha256(self) -> str:
        return p1.sha256_json(self.lineage_input)

    @property
    def product_request(self) -> dict[str, Any]:
        """Product-specific inner request sealed by ``ProviderCall``."""

        return {
            "schema": PRODUCT_INTENT_SCHEMA,
            "replica_key": self.replica_key,
            "operation": self.operation,
            "call_key": self.call_key,
            "provider": self.provider,
            "model": self.model,
            "physical_payload": _json_copy(
                self.physical_payload, field=f"payload {self.call_key}"
            ),
            "physical_payload_sha256": p1.sha256_json(self.physical_payload),
            "lineage_input_sha256": self.lineage_input_sha256,
            "run_genesis_sha256": self.run_genesis_sha256,
            "max_output_tokens": self.max_output_tokens,
        }

    @property
    def request(self) -> dict[str, Any]:
        """Exact ``ProviderCall.sealed_envelope`` persisted in the P1 WAL."""

        return {
            "call_key": self.call_key,
            "provider": self.provider,
            "model": self.model,
            "request": self.product_request,
            "run_genesis_sha256": self.run_genesis_sha256,
            "lineage_input_sha256": self.lineage_input_sha256,
            "input_tokens_upper_bound": p1.physical_input_token_upper_bound(
                self.physical_payload
            ),
            "max_output_tokens": self.max_output_tokens,
            "max_retries": 0,
            "prompt_cache": False,
            "inference_geo": "global",
            "service_tier": "standard_sync",
        }

    @property
    def request_sha256(self) -> str:
        return p1.sha256_json(self.request)


@dataclass(frozen=True)
class ProductProviderResult:
    """Raw provider payload plus a separately bound HTTP/usage receipt."""

    payload: Mapping[str, Any]
    transport_receipt: Mapping[str, Any]

    @classmethod
    def coerce(
        cls, value: "ProductProviderResult | Mapping[str, Any]"
    ) -> "ProductProviderResult":
        if isinstance(value, cls):
            return value
        _require(
            isinstance(value, Mapping)
            and set(value) == {"schema", "payload", "transport_receipt"}
            and value.get("schema") == PRODUCT_RESULT_SCHEMA,
            "NO_GO_PRODUCT_PROVIDER_RESULT",
            "boundary returned an invalid product result",
        )
        return cls(
            payload=value["payload"],
            transport_receipt=value["transport_receipt"],
        )


class ProductBoundary(Protocol):
    run_genesis: Mapping[str, Any]
    budget: Any

    def invoke_product(
        self, intent: ProductProviderIntent
    ) -> ProductProviderResult | Mapping[str, Any]: ...


class _PreparedProductCall:
    def __init__(self, owner: "ProductSDKPaidAdapter", call: p1.ProviderCall):
        self._owner = owner
        self._call = call

    def send(self) -> Mapping[str, Any]:
        if self._call.provider == "anthropic":
            return self._owner._send_anthropic(self._call)
        if self._call.provider == "voyage":
            return self._owner._send_voyage(self._call)
        _fail("HOLD_UNREGISTERED_CALL", self._call.call_key)


class ProductSDKPaidAdapter:
    """No-retry paid transport with HTTP-level provider receipts.

    Construct this adapter before ``ProductReplicaAdapter`` installs its
    product-module proxies.  ``prepare`` is local-only; all network I/O occurs
    in the returned object's ``send`` method, after the WAL reservation and
    live fence checks in :class:`p1.ProviderBoundary`.
    """

    def __init__(self, *, anthropic_api_key: str, voyage_api_key: str):
        _require(
            isinstance(anthropic_api_key, str)
            and bool(anthropic_api_key)
            and isinstance(voyage_api_key, str)
            and bool(voyage_api_key),
            "HOLD_PROVIDER_CREDENTIALS",
            "Anthropic and Voyage credentials are required",
        )
        self._anthropic_api_key = anthropic_api_key
        self._voyage_api_key = voyage_api_key

        expected_versions = {
            "anthropic": "0.97.0",
            "voyageai": "0.2.4",
        }
        for distribution, expected_version in expected_versions.items():
            try:
                observed_version = package_version(distribution)
            except PackageNotFoundError as exc:
                raise p1.P1Error(
                    "HOLD_PROVIDER_SDK_VERSION", f"{distribution} missing"
                ) from exc
            _require(
                observed_version == expected_version,
                "HOLD_PROVIDER_SDK_VERSION",
                f"{distribution} must be exactly {expected_version}",
            )

        # Warm and attest both pinned SDK surfaces before the first live fence
        # watch. ``prepare`` sits between that watch and the physical send, so
        # dependency discovery or a cold import there would age the receipt.
        try:
            import anthropic
            import voyageai
            from voyageai.api_resources.api_requestor import APIRequestor
        except ImportError as exc:
            raise p1.P1Error(
                "HOLD_PROVIDER_SDK_VERSION", "provider client API missing"
            ) from exc
        _require(
            callable(getattr(anthropic, "Anthropic", None)),
            "HOLD_PROVIDER_SDK_VERSION",
            "anthropic client API missing",
        )
        _require(
            callable(getattr(voyageai, "Client", None))
            and callable(getattr(APIRequestor, "request_raw", None)),
            "HOLD_PROVIDER_SDK_VERSION",
            "voyageai client API missing",
        )
        self._anthropic = anthropic
        self._voyageai = voyageai
        self._voyage_api_requestor = APIRequestor

    def prepare(self, call: p1.ProviderCall) -> _PreparedProductCall:
        _require(
            call.provider in {"anthropic", "voyage"}
            and isinstance(call.request, Mapping)
            and call.request.get("schema") == PRODUCT_INTENT_SCHEMA
            and call.max_retries == 0
            and call.prompt_cache is False,
            "HOLD_PRODUCT_REQUEST_DRIFT",
            call.call_key,
        )
        return _PreparedProductCall(self, call)

    @staticmethod
    def _raw_bytes(raw_response: Any) -> bytes:
        content = getattr(raw_response, "content", None)
        content = content() if callable(content) else content
        _require(
            isinstance(content, bytes) and bool(content),
            "NO_GO_PRODUCT_PROVIDER_RESULT",
            "provider response body missing",
        )
        return content

    def _send_anthropic(self, call: p1.ProviderCall) -> Mapping[str, Any]:
        payload = _json_copy(
            call.request["physical_payload"], field=f"{call.call_key} payload"
        )
        client = self._anthropic.Anthropic(
            api_key=self._anthropic_api_key, max_retries=0
        )
        raw = client.messages.with_raw_response.create(**payload)
        body = self._raw_bytes(raw)
        try:
            normalized = json.loads(body)
        except json.JSONDecodeError as exc:
            raise p1.P1Error(
                "NO_GO_PRODUCT_PROVIDER_RESULT", call.call_key
            ) from exc
        _require(
            isinstance(normalized, dict)
            and getattr(raw, "status_code", None) == 200
            and getattr(raw, "retries_taken", None) == 0,
            "NO_GO_PRODUCT_PROVIDER_RESULT",
            call.call_key,
        )
        request_id = getattr(raw, "request_id", None)
        _require(
            isinstance(request_id, str) and bool(request_id),
            "NO_GO_PRODUCT_TRANSPORT_RECEIPT",
            call.call_key,
        )
        receipt = _transport_receipt(
            provider=call.provider,
            call_key=call.call_key,
            request_sha256=call.request_sha256,
            payload=normalized,
            provider_request_id=request_id,
            raw_response_body=body,
            sdk_version="anthropic==0.97.0",
            sdk_retries_taken=0,
        )
        return {**normalized, "_p1_transport_receipt": receipt}

    def _send_voyage(self, call: p1.ProviderCall) -> Mapping[str, Any]:
        voyageai = self._voyageai
        APIRequestor = self._voyage_api_requestor
        acquired = _VOYAGE_HTTP_LOCK.acquire(blocking=False)
        _require(
            acquired,
            "HOLD_PRODUCT_PROXY_ALREADY_ACTIVE",
            "Voyage requestor receipt capture is process-global",
        )
        original_request_raw = APIRequestor.request_raw
        captured: list[Any] = []

        def request_raw_probe(requestor, *args, **kwargs):
            response = original_request_raw(requestor, *args, **kwargs)
            captured.append(response)
            return response

        physical = _json_copy(
            call.request["physical_payload"], field=f"{call.call_key} payload"
        )
        try:
            APIRequestor.request_raw = request_raw_probe
            client = voyageai.Client(api_key=self._voyage_api_key, max_retries=0)
            result = client.embed(
                physical["texts"],
                model=physical["model"],
                input_type=physical["input_type"],
                truncation=physical["truncation"],
            )
        finally:
            APIRequestor.request_raw = original_request_raw
            _VOYAGE_HTTP_LOCK.release()
        _require(
            APIRequestor.request_raw is original_request_raw
            and len(captured) == 1,
            "NO_GO_PRODUCT_TRANSPORT_RECEIPT",
            call.call_key,
        )
        raw = captured[0]
        body = bytes(raw.content)
        try:
            normalized = json.loads(body)
        except json.JSONDecodeError as exc:
            raise p1.P1Error(
                "NO_GO_PRODUCT_PROVIDER_RESULT", call.call_key
            ) from exc
        embeddings = getattr(result, "embeddings", None)
        data = normalized.get("data") if isinstance(normalized, dict) else None
        _require(
            raw.status_code == 200
            and isinstance(normalized, dict)
            and isinstance(data, list)
            and isinstance(embeddings, list)
            and len(data) == len(embeddings) == 1,
            "NO_GO_PRODUCT_PROVIDER_RESULT",
            call.call_key,
        )
        # SDK 0.2.4 requests base64 embeddings internally, then decodes them.
        # Persist the usable normalized payload while separately hashing the
        # exact raw HTTP body in the transport receipt.
        for row, embedding in zip(data, embeddings, strict=True):
            _require(
                isinstance(row, dict) and isinstance(embedding, list),
                "NO_GO_PRODUCT_PROVIDER_RESULT",
                call.call_key,
            )
            row["embedding"] = embedding
        request_id = raw.headers.get("request-id") or raw.headers.get(
            "x-request-id"
        )
        _require(
            isinstance(request_id, str) and bool(request_id),
            "NO_GO_PRODUCT_TRANSPORT_RECEIPT",
            call.call_key,
        )
        receipt = _transport_receipt(
            provider=call.provider,
            call_key=call.call_key,
            request_sha256=call.request_sha256,
            payload=normalized,
            provider_request_id=request_id,
            raw_response_body=body,
            sdk_version="voyageai==0.2.4",
            sdk_retries_taken=0,
        )
        return {**normalized, "_p1_transport_receipt": receipt}


@dataclass(frozen=True)
class ProductRuntime:
    """Versioned product functions used by one P1 replica."""

    execute_turn: Callable[..., dict[str, Any]]
    retrieve: Callable[..., list[dict[str, Any]]]
    rerank: Callable[..., list[dict[str, Any]]]
    observe_structural_shadow: Callable[[str, list[dict[str, Any]]], None]
    generate: Callable[..., dict[str, Any]]
    structural_fetcher: Callable[..., tuple[list[dict], list[dict], dict]]
    renderer: Callable[[str], list[str]]

    @property
    def identity(self) -> dict[str, dict[str, str]]:
        return {
            name: _function_identity(getattr(self, name))
            for name in (
                "execute_turn",
                "retrieve",
                "rerank",
                "observe_structural_shadow",
                "generate",
                "structural_fetcher",
                "renderer",
            )
        }


def observe_product_effective_config(
    *,
    environ: Mapping[str, str] | None = None,
    config_module: Any | None = None,
) -> dict[str, Any]:
    """Project the config actually loaded by the product runtime."""

    if config_module is None:
        from src import config as config_module

    policy = getattr(config_module, "COVERAGE_RELEASE_POLICY", None)
    _require(
        policy is not None and callable(getattr(policy, "safe_snapshot", None)),
        "HOLD_PRODUCT_EFFECTIVE_CONFIG_DRIFT",
        "loaded coverage release policy is unavailable",
    )
    policy_snapshot = policy.safe_snapshot()
    profile = policy_snapshot.get("profile")
    env = os.environ if environ is None else environ
    observed = p1.derive_semantic_config(env, release_profile=profile)
    observed["coverage"] = {
        "release_profile": profile,
        "post_rerank_coverage": policy_snapshot.get("post_rerank_coverage"),
        "structural_neighbor_coverage": policy_snapshot.get(
            "structural_neighbor_coverage"
        ),
        "mandatory_callout": policy_snapshot.get(
            "coverage_mandatory_callout"
        ),
        "mandatory_verb_trigger": policy_snapshot.get(
            "mp_mandatory_verb_trigger"
        ),
        "document_local_coverage": policy_snapshot.get(
            "document_local_coverage"
        ),
    }
    _require(
        config_module.CHUNKS_TABLE == observed["corpus"]["chunks_table"]
        and config_module.RETRIEVAL_TOP_K
        == observed["retrieval"]["retrieval_top_k"]
        and config_module.RERANK_TOP_K == observed["retrieval"]["rerank_top_k"]
        and config_module.RERANKER_BACKEND
        == observed["retrieval"]["reranker_backend"]
        and config_module.RERANK_PREVIEW_CHARS
        == observed["retrieval"]["rerank_preview_chars"]
        and config_module.MERGE_STRATEGY
        == observed["retrieval"]["merge_strategy"]
        and config_module.LLM_MODEL == observed["generation"]["model"]
        and config_module.LLM_MAX_TOKENS
        == observed["generation"]["max_tokens"]
        and config_module.MUST_PRESERVE_CONTRACT
        is observed["generation"]["must_preserve_contract"]
        and config_module.VISUAL_ASSETS_REGISTRY
        is observed["generation"]["visual_assets_registry"]
        and config_module.POST_RERANK_COVERAGE
        is observed["coverage"]["post_rerank_coverage"]
        and config_module.STRUCTURAL_NEIGHBOR_COVERAGE
        is observed["coverage"]["structural_neighbor_coverage"]
        and getattr(config_module, "DOCUMENT_LOCAL_COVERAGE", None)
        is observed["coverage"]["document_local_coverage"],
        "HOLD_PRODUCT_EFFECTIVE_CONFIG_DRIFT",
        "loaded product constants differ from the sealed target environment",
    )
    return observed


def load_product_runtime() -> ProductRuntime:
    """Load the real serving functions lazily, after the sealed env is active."""

    from src.bot.response_formatter import format_telegram_messages
    from src.rag.generator import generate_answer
    from src.rag.reranker import rerank
    from src.rag.retriever import retrieve_chunks
    from src.rag.serving_pipeline import execute_rag_turn
    from src.rag.structural_neighbor_shadow import (
        fetch_structural_neighbor_rows,
        observe_structural_neighbor_shadow,
    )

    runtime = ProductRuntime(
        execute_turn=execute_rag_turn,
        retrieve=retrieve_chunks,
        rerank=rerank,
        observe_structural_shadow=observe_structural_neighbor_shadow,
        generate=generate_answer,
        structural_fetcher=fetch_structural_neighbor_rows,
        renderer=format_telegram_messages,
    )
    expected = {
        "execute_turn": ("src.rag.serving_pipeline", "execute_rag_turn"),
        "retrieve": ("src.rag.retriever", "retrieve_chunks"),
        "rerank": ("src.rag.reranker", "rerank"),
        "observe_structural_shadow": (
            "src.rag.structural_neighbor_shadow",
            "observe_structural_neighbor_shadow",
        ),
        "generate": ("src.rag.generator", "generate_answer"),
        "structural_fetcher": (
            "src.rag.structural_neighbor_shadow",
            "fetch_structural_neighbor_rows",
        ),
        "renderer": ("src.bot.response_formatter", "format_telegram_messages"),
    }
    for name, (module, qualname) in expected.items():
        observed = runtime.identity[name]
        _require(
            observed == {"module": module, "qualname": qualname},
            "HOLD_PRODUCT_RUNTIME_DRIFT",
            f"{name}: {observed}",
        )
    return runtime


def _raw_text(payload: Mapping[str, Any], *, call_key: str) -> str:
    content = payload.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list) and len(content) == 1:
        block = content[0]
        if (
            isinstance(block, Mapping)
            and block.get("type", "text") == "text"
            and isinstance(block.get("text"), str)
            and block["text"].strip()
        ):
            return str(block["text"])
    _fail("NO_GO_PRODUCT_PROVIDER_CONTENT", call_key)


def _sdk_message(payload: Mapping[str, Any], *, call_key: str) -> SimpleNamespace:
    text = _raw_text(payload, call_key=call_key)
    usage = payload.get("usage")
    return SimpleNamespace(
        id=payload.get("id"),
        model=payload.get("model"),
        stop_reason=payload.get("stop_reason"),
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        ),
    )


class _MessagesProxy:
    def __init__(self, router: "_ProviderRouter"):
        self._router = router

    def create(self, **kwargs):
        return self._router.anthropic_create(kwargs)


class _AnthropicClientProxy:
    def __init__(self, router: "_ProviderRouter"):
        self.messages = _MessagesProxy(router)


class _ProviderRouter:
    def __init__(
        self,
        *,
        replica: p1.Replica,
        input_row: Mapping[str, Any],
        boundary: ProductBoundary,
    ):
        self.replica = replica
        self.input_row = _json_copy(input_row, field=f"input {replica.key}")
        self.boundary = boundary
        self.expected_operations = list(p1.CALL_OPERATIONS)
        self.intents: list[ProductProviderIntent] = []
        self.results: dict[str, ProductProviderResult] = {}
        self.validation_failure: p1.P1Error | None = None
        self._lineage: dict[str, Any] = {"embedding": self.input_row}

    def set_lineage(self, operation: str, value: Any) -> None:
        _require(
            operation in {"rerank", "synthesis"} and operation not in self._lineage,
            "HOLD_PRODUCT_LINEAGE_DRIFT",
            f"duplicate/invalid lineage {operation}",
        )
        self._lineage[operation] = _json_copy(
            value, field=f"{self.replica.key}:{operation} lineage"
        )

    def _spec(self, operation: str):
        call_key = f"{self.replica.key}:{operation}"
        spec = getattr(self.boundary, "budget", None)
        specs = getattr(spec, "specs", None)
        value = specs.get(call_key) if isinstance(specs, Mapping) else None
        _require(value is not None, "HOLD_UNREGISTERED_CALL", call_key)
        return value

    def _invoke(
        self,
        *,
        operation: str,
        provider: str,
        model: str,
        payload: Mapping[str, Any],
        max_output_tokens: int,
    ) -> ProductProviderResult:
        index = len(self.intents)
        expected = (
            self.expected_operations[index]
            if index < len(self.expected_operations)
            else None
        )
        _require(
            operation == expected,
            "NO_GO_PRODUCT_CALL_ORDER",
            f"expected {expected}, got {operation}",
        )
        lineage = self._lineage.get(operation)
        _require(
            lineage is not None,
            "HOLD_PRODUCT_LINEAGE_DRIFT",
            f"missing {operation} lineage",
        )
        spec = self._spec(operation)
        _require(
            spec.provider == provider and spec.model == model,
            "NO_GO_PRODUCT_MODEL_DRIFT",
            f"{self.replica.key}:{operation}",
        )
        _require(
            type(max_output_tokens) is int
            and 0 <= max_output_tokens <= spec.max_output_tokens
            and (operation == "embedding") == (max_output_tokens == 0),
            "HOLD_PRODUCT_REQUEST_DRIFT",
            f"{self.replica.key}:{operation} max_output_tokens",
        )
        genesis_sha = self.boundary.run_genesis.get("run_genesis_sha256")
        _require(
            isinstance(genesis_sha, str) and bool(_HEX64.fullmatch(genesis_sha)),
            "HOLD_RUN_IDENTITY",
            self.replica.key,
        )
        intent = ProductProviderIntent(
            replica_key=self.replica.key,
            operation=operation,
            call_key=f"{self.replica.key}:{operation}",
            provider=provider,
            model=model,
            physical_payload=_json_copy(payload, field=f"payload {operation}"),
            lineage_input=lineage,
            run_genesis_sha256=genesis_sha,
            # Bind the intent to the physical request limit, while the budget
            # spec remains the (possibly larger) preregistered reservation.
            max_output_tokens=max_output_tokens,
        )
        hook = getattr(self.boundary, "invoke_product", None)
        _require(
            callable(hook),
            "HOLD_PRODUCT_BOUNDARY_HOOK_NOT_INSTALLED",
            "ProviderBoundary.invoke_product(intent) is required",
        )
        try:
            result = ProductProviderResult.coerce(hook(intent))
            self._validate_result(intent, result, spec)
        except p1.P1Error as exc:
            # The product reranker wraps provider-facing exceptions in
            # RerankStrictError.  Preserve every fail-closed P1 classification,
            # including local envelope/budget failures raised before WAL/send.
            self.validation_failure = exc
            raise
        self.intents.append(intent)
        self.results[operation] = result
        return result

    @staticmethod
    def _validate_result(intent, result, spec) -> None:
        payload = result.payload
        receipt = result.transport_receipt
        _require(
            isinstance(payload, Mapping)
            and isinstance(receipt, Mapping)
            and receipt.get("schema") == TRANSPORT_RECEIPT_SCHEMA,
            "NO_GO_PRODUCT_PROVIDER_RESULT",
            intent.call_key,
        )
        usage = payload.get("usage")
        _require(
            payload.get("model") == intent.model
            and isinstance(usage, Mapping),
            "NO_GO_PRODUCT_PROVIDER_RESULT",
            intent.call_key,
        )
        input_tokens = usage.get("input_tokens", usage.get("total_tokens"))
        output_tokens = usage.get("output_tokens", 0)
        _require(
            type(input_tokens) is int
            and 0 < input_tokens <= spec.max_input_tokens
            and type(output_tokens) is int
            and 0 <= output_tokens <= spec.max_output_tokens,
            "NO_GO_PRODUCT_USAGE",
            intent.call_key,
        )
        if intent.operation in {"rerank", "synthesis"}:
            _require(
                isinstance(payload.get("id"), str)
                and bool(payload["id"])
                and payload.get("stop_reason") == "end_turn"
                and 0 < output_tokens < intent.max_output_tokens,
                "NO_GO_PRODUCT_TERMINAL_STOP",
                intent.call_key,
            )
            _raw_text(payload, call_key=intent.call_key)
        required_receipt = {
            "schema",
            "provider",
            "call_key",
            "request_sha256",
            "provider_request_id",
            "http_status",
            "response_body_sha256",
            "normalized_payload_sha256",
            "usage",
            "usage_source",
            "cost_accounting",
            "sdk_version",
            "sdk_retries_taken",
            "observed_at",
        }
        _require(
            set(receipt) == required_receipt
            and receipt.get("provider") == intent.provider
            and receipt.get("call_key") == intent.call_key
            and receipt.get("request_sha256") == intent.request_sha256
            and isinstance(receipt.get("provider_request_id"), str)
            and bool(receipt["provider_request_id"])
            and receipt.get("http_status") == 200
            and isinstance(receipt.get("response_body_sha256"), str)
            and bool(_HEX64.fullmatch(receipt["response_body_sha256"]))
            and receipt.get("normalized_payload_sha256")
            == p1.sha256_json(payload)
            and receipt.get("usage") == usage
            and receipt.get("usage_source") == "provider_http_response"
            and receipt.get("cost_accounting")
            == "preregistered_max_reservation_until_external_reconciliation"
            and isinstance(receipt.get("sdk_version"), str)
            and bool(receipt["sdk_version"])
            and receipt.get("sdk_retries_taken") == 0,
            "NO_GO_PRODUCT_TRANSPORT_RECEIPT",
            intent.call_key,
        )
        try:
            observed_at = datetime.fromisoformat(
                str(receipt.get("observed_at")).replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise p1.P1Error(
                "NO_GO_PRODUCT_TRANSPORT_RECEIPT", intent.call_key
            ) from exc
        _require(
            observed_at.tzinfo is not None,
            "NO_GO_PRODUCT_TRANSPORT_RECEIPT",
            intent.call_key,
        )

    def voyage_embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        _require(
            len(texts) == 1
            and input_type == "query"
            and texts[0] == self.input_row["question"],
            "HOLD_PRODUCT_EMBEDDING_INPUT_DRIFT",
            self.replica.key,
        )
        spec = self._spec("embedding")
        result = self._invoke(
            operation="embedding",
            provider="voyage",
            model=spec.model,
            payload={
                "model": spec.model,
                "input_type": "query",
                "texts": texts,
                "truncation": True,
            },
            max_output_tokens=0,
        )
        payload = result.payload
        embeddings = payload.get("embeddings")
        if embeddings is None and isinstance(payload.get("data"), list):
            embeddings = [
                row.get("embedding") if isinstance(row, Mapping) else None
                for row in payload["data"]
            ]
        _require(
            isinstance(embeddings, list)
            and len(embeddings) == 1
            and isinstance(embeddings[0], list)
            and bool(embeddings[0])
            and all(isinstance(value, (int, float)) for value in embeddings[0]),
            "NO_GO_PRODUCT_EMBEDDING_RESPONSE",
            self.replica.key,
        )
        return embeddings

    def anthropic_create(self, kwargs: Mapping[str, Any]) -> SimpleNamespace:
        operation = "rerank" if len(self.intents) == 1 else "synthesis"
        _require(
            len(self.intents) in {1, 2},
            "NO_GO_PRODUCT_CALL_ORDER",
            self.replica.key,
        )
        spec = self._spec(operation)
        requested_max = kwargs.get("max_tokens")
        _require(
            kwargs.get("model") == spec.model
            and kwargs.get("temperature") == 0
            and type(requested_max) is int
            and 0 < requested_max <= spec.max_output_tokens
            and "tools" not in kwargs
            and "stream" not in kwargs,
            "HOLD_PRODUCT_REQUEST_DRIFT",
            f"{self.replica.key}:{operation}",
        )
        result = self._invoke(
            operation=operation,
            provider="anthropic",
            model=spec.model,
            payload=kwargs,
            max_output_tokens=requested_max,
        )
        return _sdk_message(result.payload, call_key=f"{self.replica.key}:{operation}")

    def assert_complete(self) -> None:
        _require(
            [intent.operation for intent in self.intents]
            == self.expected_operations,
            "NO_GO_PRODUCT_CALL_PLAN",
            self.replica.key,
        )


@contextmanager
def _installed_product_proxies(router: _ProviderRouter, capture: dict[str, Any]):
    """Install SDK/stage probes for one isolated product turn."""

    acquired = _INSTALL_LOCK.acquire(blocking=False)
    _require(
        acquired,
        "HOLD_PRODUCT_PROXY_ALREADY_ACTIVE",
        "product provider proxies are process-global",
    )
    from src.rag import generator as generator_module
    from src.rag import reranker as reranker_module
    from src.rag import visual_assets as visual_module
    from src.reingest import embed as embed_module

    original_generator_anthropic = generator_module.anthropic
    original_reranker_anthropic = reranker_module.anthropic
    original_embed_provider = embed_module._PROVIDERS.get("voyage")
    original_planner = generator_module.apply_answer_planner
    original_mp = generator_module.apply_must_preserve_contract
    original_conflict_guard = generator_module.apply_answer_conflict_guard
    original_visual_append = generator_module.append_cited_visual_assets
    original_visual_lookup = visual_module.lookup_visual_assets

    def anthropic_factory(*_args, **_kwargs):
        return _AnthropicClientProxy(router)

    def planner_probe(query, chunks, answer, *args, **kwargs):
        _require(
            "planner" not in capture,
            "NO_GO_PRODUCT_STAGE_COUNT",
            router.replica.key,
        )
        output, metadata = original_planner(query, chunks, answer, *args, **kwargs)
        capture["planner"] = {"input": answer, "output": output}
        return output, metadata

    def mp_probe(query, chunks, answer, *args, **kwargs):
        _require(
            "must_preserve" not in capture,
            "NO_GO_PRODUCT_STAGE_COUNT",
            router.replica.key,
        )
        output, trace = original_mp(query, chunks, answer, *args, **kwargs)
        capture["must_preserve"] = {
            "input": answer,
            "output": output,
            "trace": _json_copy(trace, field="must_preserve trace")
            if trace is not None
            else None,
        }
        return output, trace

    def conflict_guard_probe(query, chunks, answer, *args, **kwargs):
        _require(
            "conflict_guard" not in capture,
            "NO_GO_PRODUCT_STAGE_COUNT",
            router.replica.key,
        )
        output, trace = original_conflict_guard(
            query, chunks, answer, *args, **kwargs
        )
        capture["conflict_guard"] = {
            "input": answer,
            "output": output,
            "trace": _json_copy(trace, field="answer conflict guard trace"),
        }
        return output, trace

    def visual_lookup_probe(document_id: str, page_number: int):
        try:
            rows = original_visual_lookup(document_id, page_number)
        except Exception as exc:
            capture.setdefault("visual_errors", []).append(type(exc).__name__)
            raise
        safe_rows = _json_copy(rows, field="visual lookup rows")
        request = {
            "method": "GET",
            "relation": p1.VISUAL_REST_GET_SURFACE,
            "document_id": document_id,
            "page_index": page_number,
            "technical_utility": "useful",
            "visual_roles": list(p1.VISUAL_SERVABLE_ROLES),
        }
        capture.setdefault("visual_lookups", []).append(
            {
                "request": request,
                "request_sha256": p1.sha256_json(request),
                "response": safe_rows,
                "response_sha256": p1.sha256_json(safe_rows),
            }
        )
        return rows

    def visual_append_probe(result, chunks):
        _require(
            "visual_append" not in capture,
            "NO_GO_PRODUCT_STAGE_COUNT",
            f"duplicate visual append for {router.replica.key}",
        )
        before = deepcopy(result.get("diagrams") or [])
        original_visual_append(result, chunks)
        after = deepcopy(result.get("diagrams") or [])
        _require(
            after[: len(before)] == before,
            "NO_GO_VISUAL_SELECTION",
            f"preexisting assets changed for {router.replica.key}",
        )
        capture["visual_append"] = {
            "before": before,
            "after": after,
            "selected": after[len(before) :],
        }

    try:
        product_anthropic = SimpleNamespace(Anthropic=anthropic_factory)
        generator_module.anthropic = product_anthropic
        reranker_module.anthropic = product_anthropic
        embed_module._PROVIDERS["voyage"] = router.voyage_embed
        generator_module.apply_answer_planner = planner_probe
        generator_module.apply_must_preserve_contract = mp_probe
        generator_module.apply_answer_conflict_guard = conflict_guard_probe
        generator_module.append_cited_visual_assets = visual_append_probe
        visual_module.lookup_visual_assets = visual_lookup_probe
        yield
    finally:
        generator_module.anthropic = original_generator_anthropic
        reranker_module.anthropic = original_reranker_anthropic
        if original_embed_provider is None:
            embed_module._PROVIDERS.pop("voyage", None)
        else:
            embed_module._PROVIDERS["voyage"] = original_embed_provider
        generator_module.apply_answer_planner = original_planner
        generator_module.apply_must_preserve_contract = original_mp
        generator_module.apply_answer_conflict_guard = original_conflict_guard
        generator_module.append_cited_visual_assets = original_visual_append
        visual_module.lookup_visual_assets = original_visual_lookup
        _INSTALL_LOCK.release()
        _require(
            generator_module.anthropic is original_generator_anthropic
            and reranker_module.anthropic is original_reranker_anthropic
            and embed_module._PROVIDERS.get("voyage") is original_embed_provider
            and generator_module.apply_answer_planner is original_planner
            and generator_module.apply_must_preserve_contract is original_mp
            and generator_module.apply_answer_conflict_guard is original_conflict_guard
            and generator_module.append_cited_visual_assets is original_visual_append
            and visual_module.lookup_visual_assets is original_visual_lookup,
            "HOLD_PRODUCT_PROXY_RESTORE_FAILED",
            router.replica.key,
        )


@dataclass(frozen=True)
class ProductReplicaExecution:
    receipt: Mapping[str, Any]
    adapter_attestation: Mapping[str, Any]


class ProductReplicaAdapter:
    """Run one preregistered cell through the real production serving seam."""

    def __init__(
        self,
        *,
        input_contract: Mapping[str, Mapping[str, Any]],
        postgrest_receipt_source: Callable[[], Sequence[Mapping[str, Any]]],
        postgrest_manifest_sha256: str,
        visual_assets_registry: str,
        expected_effective_config: Mapping[str, Any] | None = None,
        runtime: ProductRuntime | None = None,
    ):
        _require(
            callable(postgrest_receipt_source)
            and isinstance(postgrest_manifest_sha256, str)
            and bool(_HEX64.fullmatch(postgrest_manifest_sha256))
            and visual_assets_registry in {"on", "off"},
            "HOLD_POSTGREST_GUARD_NOT_BOUND",
            "verified PostgREST receipt source, manifest and visual mode required",
        )
        self.input_contract = _json_copy(input_contract, field="input contract")
        self.postgrest_receipt_source = postgrest_receipt_source
        self.postgrest_manifest_sha256 = postgrest_manifest_sha256
        self.visual_assets_registry = visual_assets_registry
        if runtime is None:
            _require(
                isinstance(expected_effective_config, Mapping),
                "HOLD_PRODUCT_EFFECTIVE_CONFIG_DRIFT",
                "real product runtime requires a sealed expected config",
            )
            self.runtime = load_product_runtime()
            observed = observe_product_effective_config()
            _require(
                observed == expected_effective_config,
                "HOLD_PRODUCT_EFFECTIVE_CONFIG_DRIFT",
                "loaded product config differs from run genesis target",
            )
            self.observed_effective_config: dict[str, Any] | None = observed
        else:
            self.runtime = runtime
            self.observed_effective_config = (
                _json_copy(
                    expected_effective_config,
                    field="expected effective config",
                )
                if isinstance(expected_effective_config, Mapping)
                else None
            )

    def execute_replica(
        self, replica: p1.Replica, boundary: ProductBoundary
    ) -> ProductReplicaExecution:
        """Return the legacy receipt plus a mandatory product attestation.

        The current P1 runner must unwrap this object and persist both mappings;
        treating it as the old synthetic Mapping is intentionally impossible.
        """

        input_row = self.input_contract.get(replica.qid)
        _require(
            isinstance(input_row, Mapping),
            "HOLD_PRODUCT_INPUT_MISSING",
            replica.qid,
        )
        expected_input_keys = {
            "question",
            "target_models",
            "query_for_retrieval",
            "available_models",
        }
        _require(
            set(input_row) == expected_input_keys
            and input_row.get("query_for_retrieval") == input_row.get("question")
            and isinstance(input_row.get("target_models"), list)
            and bool(input_row["target_models"])
            and input_row.get("available_models") is None,
            "HOLD_PRODUCT_INPUT_DRIFT",
            replica.key,
        )
        target_visual = boundary.run_genesis.get("target_semantic_config", {}).get(
            "generation", {}
        ).get("visual_assets_registry")
        effective = self.observed_effective_config or boundary.run_genesis.get(
            "target_semantic_config"
        )
        _require(
            target_visual is (self.visual_assets_registry == "on"),
            "HOLD_POSTGREST_GUARD_NOT_BOUND",
            f"visual mode differs from run genesis for {replica.key}",
        )
        _require(
            isinstance(effective, Mapping)
            and effective == boundary.run_genesis.get("target_semantic_config"),
            "HOLD_PRODUCT_EFFECTIVE_CONFIG_DRIFT",
            replica.key,
        )
        document_local_required = _document_local_v2_required(effective)
        postgrest_before = self.postgrest_receipt_source()
        _require(
            isinstance(postgrest_before, Sequence)
            and not isinstance(postgrest_before, (str, bytes, bytearray)),
            "HOLD_POSTGREST_GUARD_NOT_BOUND",
            "PostgREST receipt source returned an invalid pre-state",
        )
        router = _ProviderRouter(
            replica=replica, input_row=input_row, boundary=boundary
        )
        capture: dict[str, Any] = {
            "entrypoint_calls": 0,
            "retrieval_calls": 0,
            "rerank_calls": 0,
            "generation_calls": 0,
            "structural_fetch_calls": [],
            "visual_lookups": [],
            "observed_effective_config": _json_copy(
                effective, field="observed effective config"
            ),
        }

        def retrieve(query, **kwargs):
            capture["retrieval_calls"] += 1
            _require(
                capture["retrieval_calls"] == 1
                and query == input_row["query_for_retrieval"],
                "NO_GO_PRODUCT_RETRIEVAL_INPUT",
                replica.key,
            )
            rows = self.runtime.retrieve(query, **kwargs)
            _require(
                isinstance(rows, list)
                and bool(rows)
                and all(isinstance(row, dict) for row in rows),
                "NO_GO_PRODUCT_RETRIEVAL",
                replica.key,
            )
            capture["pool"] = deepcopy(rows)
            return rows

        def rerank(query, chunks, **kwargs):
            capture["rerank_calls"] += 1
            _require(
                capture["rerank_calls"] == 1
                and query == input_row["question"]
                and chunks == capture.get("pool")
                and kwargs.get("target_models") == input_row["target_models"],
                "NO_GO_PRODUCT_RERANK_INPUT",
                replica.key,
            )
            router.set_lineage("rerank", chunks)
            try:
                rows = self.runtime.rerank(query, chunks, strict=True, **kwargs)
            except Exception:
                # The production reranker deliberately converts provider errors
                # into its own strict-mode exception. Preserve the adapter's
                # more specific fail-closed classification when one exists.
                if router.validation_failure is not None:
                    raise router.validation_failure
                raise
            _require(
                isinstance(rows, list)
                and bool(rows)
                and all(isinstance(row, dict) for row in rows)
                and all(
                    row.get("rerank_backend_used") in {"llm", "llm-padded"}
                    for row in rows
                ),
                "NO_GO_PRODUCT_RERANK_FALLBACK",
                replica.key,
            )
            capture["prefix"] = deepcopy(rows)
            return rows

        def structural_fetcher(seeds, **kwargs):
            hydrated, candidates, trace = self.runtime.structural_fetcher(
                seeds, **kwargs
            )
            safe = {
                "seeds": deepcopy(seeds),
                "kwargs": _json_copy(kwargs, field="structural fetch kwargs"),
                "hydrated": deepcopy(hydrated),
                "candidates": deepcopy(candidates),
                "read_trace": _json_copy(trace, field="structural fetch trace"),
            }
            safe["receipt_sha256"] = p1.sha256_json(safe)
            capture["structural_fetch_calls"].append(safe)
            return hydrated, candidates, trace

        def generate(query, chunks, **kwargs):
            capture["generation_calls"] += 1
            _require(
                capture["generation_calls"] == 1
                and query == input_row["question"]
                and kwargs.get("available_models") is None,
                "NO_GO_PRODUCT_GENERATION_INPUT",
                replica.key,
            )
            capture["generation_input"] = deepcopy(chunks)
            router.set_lineage("synthesis", chunks)
            return self.runtime.generate(query, chunks, **kwargs)

        from src.rag.serving_pipeline import RagServingAdapters

        with _installed_product_proxies(router, capture):
            capture["entrypoint_calls"] += 1
            pipeline = self.runtime.execute_turn(
                query=input_row["question"],
                query_for_retrieval=input_row["query_for_retrieval"],
                target_models=list(input_row["target_models"]),
                available_models=None,
                retrieval_top_k=50,
                rerank_top_k=10,
                adapters=RagServingAdapters(
                    retrieve=retrieve,
                    rerank=rerank,
                    observe_structural_shadow=self.runtime.observe_structural_shadow,
                    generate=generate,
                    structural_fetcher=structural_fetcher,
                ),
            )

        router.assert_complete()
        _require(
            capture["entrypoint_calls"]
            == capture["retrieval_calls"]
            == capture["rerank_calls"]
            == capture["generation_calls"]
            == 1,
            "NO_GO_PRODUCT_STAGE_COUNT",
            replica.key,
        )
        _require(
            len(capture["structural_fetch_calls"]) == 1,
            "NO_GO_PRODUCT_STRUCTURAL_FETCH_COUNT",
            replica.key,
        )
        _require(
            ("visual_append" in capture) is (target_visual is True),
            "NO_GO_PRODUCT_STAGE_COUNT",
            f"visual append count for {replica.key}",
        )
        served = pipeline.get("chunks")
        coverage_trace = pipeline.get("coverage_trace")
        generation = pipeline.get("generation")
        _require(
            isinstance(served, list)
            and bool(served)
            and isinstance(coverage_trace, Mapping)
            and coverage_trace.get("status") != "error"
            and coverage_trace.get("enabled") is True
            and coverage_trace.get("protected_prefix_equal") is True
            and isinstance(generation, Mapping),
            "NO_GO_PRODUCT_PIPELINE",
            replica.key,
        )
        _require(
            served == capture.get("generation_input")
            and served[: len(capture["prefix"])] == capture["prefix"],
            "NO_GO_PRODUCT_SERVED_CONTEXT_DRIFT",
            replica.key,
        )
        answer = generation.get("answer")
        _require(
            isinstance(answer, str)
            and bool(answer.strip())
            and generation.get("stop_reason") == "end_turn"
            and generation.get("must_preserve_outcome", {}).get("status")
            == "evaluated"
            and "planner" in capture
            and "must_preserve" in capture
            and "conflict_guard" in capture
            and capture["planner"]["output"]
            == capture["must_preserve"]["input"]
            and capture["must_preserve"]["output"]
            == capture["conflict_guard"]["input"]
            and capture["conflict_guard"]["output"] == answer
            and generation.get("answer_conflict_guard")
            == capture["conflict_guard"]["trace"],
            "NO_GO_PRODUCT_GENERATION_CHAIN",
            replica.key,
        )
        _require(
            not capture.get("visual_errors"),
            "NO_GO_PRODUCT_VISUAL_LOOKUP",
            replica.key,
        )
        render_parts = self.runtime.renderer(answer)
        _require(
            isinstance(render_parts, list)
            and bool(render_parts)
            and all(isinstance(part, str) and part for part in render_parts)
            and all(len(part) <= 4096 for part in render_parts),
            "NO_GO_PRODUCT_RENDER",
            replica.key,
        )
        postgrest_after = self.postgrest_receipt_source()
        _require(
            isinstance(postgrest_after, Sequence)
            and not isinstance(postgrest_after, (str, bytes, bytearray)),
            "HOLD_POSTGREST_GUARD_NOT_BOUND",
            "PostgREST receipt source returned an invalid post-state",
        )
        postgrest_receipts = _validated_postgrest_receipt_delta(
            before=postgrest_before,
            after=postgrest_after,
            visual_assets_registry=self.visual_assets_registry,
            document_local_coverage=document_local_required,
        )
        document_local_evidence = _validated_document_local_coverage_evidence(
            replica_key=replica.key,
            coverage_trace=coverage_trace,
            served=served,
            postgrest_receipts=postgrest_receipts,
            required=document_local_required,
        )
        receipt = self._build_receipt(
            replica=replica,
            input_row=input_row,
            boundary=boundary,
            router=router,
            capture=capture,
            served=served,
            coverage_trace=coverage_trace,
            generation=generation,
            render_parts=render_parts,
        )
        attestation_body = {
            "schema": PRODUCT_ATTESTATION_SCHEMA,
            "replica_key": replica.key,
            "entrypoint": "src.rag.serving_pipeline.execute_rag_turn",
            "entrypoint_calls": 1,
            "runtime_functions": self.runtime.identity,
            "provider_operations": [
                intent.operation for intent in router.intents
            ],
            "provider_request_sha256s": {
                intent.operation: intent.request_sha256 for intent in router.intents
            },
            "transport_receipt_sha256s": {
                operation: p1.sha256_json(result.transport_receipt)
                for operation, result in router.results.items()
            },
            "retrieval_pool_sha256": p1.sha256_json(capture["pool"]),
            "rerank_prefix_sha256": p1.sha256_json(capture["prefix"]),
            "structural_fetch_receipts": capture["structural_fetch_calls"],
            "served_context_sha256": p1.sha256_json(served),
            "answer_sha256": _text_sha256(answer),
            "render_parts_sha256": p1.sha256_json(render_parts),
            "visual_lookup_receipts": capture["visual_lookups"],
            "provider_transport_attestation": "RAW_HTTP_RECEIPTS_PERSISTED",
            "postgrest_transport_attestation": "GUARDED_HTTP_RECEIPTS_PERSISTED",
            "postgrest_manifest_sha256": self.postgrest_manifest_sha256,
            "postgrest_request_receipts": postgrest_receipts,
            "postgrest_request_receipts_sha256": p1.sha256_json(
                postgrest_receipts
            ),
        }
        if document_local_evidence is not None:
            coverage_trace_copy = _json_copy(
                dict(coverage_trace), field=f"coverage trace {replica.key}"
            )
            attestation_body.update(
                {
                    "coverage_trace": coverage_trace_copy,
                    "coverage_trace_sha256": p1.sha256_json(coverage_trace_copy),
                    "document_local_coverage": document_local_evidence,
                }
            )
        attestation = {
            **attestation_body,
            "attestation_sha256": p1.sha256_json(attestation_body),
        }
        return ProductReplicaExecution(receipt=receipt, adapter_attestation=attestation)

    @staticmethod
    def _build_receipt(
        *,
        replica,
        input_row,
        boundary,
        router,
        capture,
        served,
        coverage_trace,
        generation,
        render_parts,
    ) -> dict[str, Any]:
        effective = capture["observed_effective_config"]
        effective_sha = p1.sha256_json(effective)
        embedding = router.results["embedding"].payload
        rerank_response = router.results["rerank"].payload
        synthesis = router.results["synthesis"].payload
        answer = generation["answer"]
        answer_sha = _text_sha256(answer)
        raw = _raw_text(synthesis, call_key=f"{replica.key}:synthesis")
        diagram_output = capture["planner"]["input"]
        planner_output = capture["planner"]["output"]
        mp_output = capture["must_preserve"]["output"]
        conflict_guard_output = capture["conflict_guard"]["output"]
        stage_values = (
            ("diagram_postprocess", raw, diagram_output),
            ("answer_planner", diagram_output, planner_output),
            ("must_preserve", planner_output, mp_output),
            ("conflict_guard", mp_output, conflict_guard_output),
        )
        stages = [
            {
                "name": name,
                "input_sha256": _text_sha256(before),
                "output_text": after,
                "output_sha256": _text_sha256(after),
            }
            for name, before, after in stage_values
        ]
        visual_enabled = effective["generation"]["visual_assets_registry"]
        visual_append = capture.get("visual_append")
        visual_preexisting = (
            visual_append["before"]
            if isinstance(visual_append, Mapping)
            else _json_copy(
                generation.get("diagrams") or [],
                field="preexisting visual assets",
            )
        )
        visual_selected = (
            visual_append["selected"] if isinstance(visual_append, Mapping) else []
        )
        eligible = p1.visual_lookup_keys(answer, served)
        run_identity = {
            key: boundary.run_genesis[key]
            for key in (
                "authorization_id",
                "authorization_receipt_sha256",
                "run_id",
                "run_genesis_sha256",
                "runtime_layout_sha256",
                "release_config_sha256",
                "prereg_sha256",
                "tested_commit_sha",
                "tested_tree_sha",
            )
        }
        intents = {intent.operation: intent.request for intent in router.intents}
        return {
            "schema": p1.REPLICA_RECEIPT_SCHEMA,
            "replica_key": replica.key,
            "qid": replica.qid,
            "replica_id": replica.replica_id,
            "input": _json_copy(input_row, field="receipt input"),
            "run_identity": run_identity,
            "effective_config": {
                "profile": p1.PROFILE,
                "semantic_config": effective,
                "semantic_config_sha256": effective_sha,
                "must_preserve_contract": True,
            },
            "retrieval": {
                "embedding_receipt": embedding,
                "embedding_request_sha256": p1.sha256_json(intents["embedding"]),
                "embedding_response_sha256": p1.sha256_json(embedding),
                "pool": capture["pool"],
                "pool_sha256": p1.sha256_json(capture["pool"]),
                "pool_parent_embedding_response_sha256": p1.sha256_json(embedding),
            },
            "rerank": {
                "receipt": rerank_response,
                "request_sha256": p1.sha256_json(intents["rerank"]),
                "response_sha256": p1.sha256_json(rerank_response),
                "input_pool_sha256": p1.sha256_json(capture["pool"]),
                "prefix": capture["prefix"],
                "prefix_sha256": p1.sha256_json(capture["prefix"]),
                "prefix_parent_rerank_response_sha256": p1.sha256_json(
                    rerank_response
                ),
                "fallback_used": False,
            },
            "served_context": served,
            "structural_fetch": {
                "input_prefix_sha256": p1.sha256_json(capture["prefix"]),
                "output": capture["prefix"],
                "output_sha256": p1.sha256_json(capture["prefix"]),
            },
            "coverage": {
                "status": "evaluated",
                "profile": p1.PROFILE,
                "effective_config_sha256": effective_sha,
                "input_context_sha256": p1.sha256_json(capture["prefix"]),
                "output_context": served,
                "output_context_sha256": p1.sha256_json(served),
            },
            "must_preserve": {
                "status": "evaluated",
                "profile": p1.PROFILE,
                "effective_config_sha256": effective_sha,
                "input_answer_sha256": _text_sha256(planner_output),
                "output_answer_sha256": _text_sha256(mp_output),
            },
            "provider": {
                "requested_model": intents["synthesis"]["model"],
                "reported_model": synthesis["model"],
                "stop_reason": synthesis["stop_reason"],
                "usage": synthesis["usage"],
                "response_id": synthesis["id"],
                "raw_payload": synthesis,
            },
            "answer": answer,
            "answer_sha256": answer_sha,
            "generation_chain": {
                "raw_payload_sha256": p1.sha256_json(synthesis),
                "raw_text": raw,
                "raw_text_sha256": _text_sha256(raw),
                "stages": stages,
                "final_answer_sha256": answer_sha,
            },
            "visual_assets": {
                "enabled": visual_enabled,
                "status": "evaluated" if visual_enabled else "not_executed",
                "effective_config_sha256": effective_sha,
                "input_answer_sha256": answer_sha,
                "input_context_sha256": p1.sha256_json(served),
                "rest_get_surface": [p1.VISUAL_REST_GET_SURFACE]
                if visual_enabled
                else [],
                "eligible_pages": eligible,
                "eligible_pages_sha256": p1.sha256_json(eligible),
                "lookup_receipts": capture["visual_lookups"],
                "preexisting_assets": visual_preexisting,
                "preexisting_assets_sha256": p1.sha256_json(
                    visual_preexisting
                ),
                "selected_assets": visual_selected,
                "selected_assets_sha256": p1.sha256_json(visual_selected),
            },
            "render": {
                "parts": render_parts,
                "parts_sha256": p1.sha256_json(render_parts),
                "render_status": "ok",
                "source_answer_sha256": answer_sha,
                "complete_source_rendered": True,
                "message_parts": len(render_parts),
            },
            "call_keys": [
                f"{replica.key}:{operation}" for operation in p1.CALL_OPERATIONS
            ],
            "call_requests": intents,
        }


def _transport_receipt(
    *,
    provider: str,
    call_key: str,
    request_sha256: str,
    payload: Mapping[str, Any],
    provider_request_id: str,
    raw_response_body: bytes | None = None,
    sdk_version: str = "offline-test",
    sdk_retries_taken: int = 0,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Build the exact safe receipt shape expected from the runner hook.

    This helper performs no I/O.  The hook must source ``provider_request_id``,
    body and usage from the actual HTTP response and keep the authoritative
    budget at the preregistered maximum until a separate operator reconciles
    the provider usage/cost report.
    """

    observed = observed_at or datetime.now(timezone.utc)
    response_body = raw_response_body or p1.canonical_json_bytes(payload)
    return {
        "schema": TRANSPORT_RECEIPT_SCHEMA,
        "provider": provider,
        "call_key": call_key,
        "request_sha256": request_sha256,
        "provider_request_id": provider_request_id,
        "http_status": 200,
        "response_body_sha256": hashlib.sha256(response_body).hexdigest(),
        "normalized_payload_sha256": p1.sha256_json(payload),
        "usage": _json_copy(payload.get("usage"), field="provider usage"),
        "usage_source": "provider_http_response",
        "cost_accounting": (
            "preregistered_max_reservation_until_external_reconciliation"
        ),
        "sdk_version": sdk_version,
        "sdk_retries_taken": sdk_retries_taken,
        "observed_at": observed.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def build_transport_receipt(
    *,
    intent: ProductProviderIntent,
    payload: Mapping[str, Any],
    provider_request_id: str,
    raw_response_body: bytes | None = None,
    sdk_version: str = "offline-test",
    sdk_retries_taken: int = 0,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a transport receipt for an injected/offline boundary."""

    return _transport_receipt(
        provider=intent.provider,
        call_key=intent.call_key,
        request_sha256=intent.request_sha256,
        payload=payload,
        provider_request_id=provider_request_id,
        raw_response_body=raw_response_body,
        sdk_version=sdk_version,
        sdk_retries_taken=sdk_retries_taken,
        observed_at=observed_at,
    )
