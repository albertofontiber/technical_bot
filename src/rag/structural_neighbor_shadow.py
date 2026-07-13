"""Default-off, fail-open observer for post-rerank structural neighbors.

The observer never returns chunks and never imports the generator.  Its only
output is redacted telemetry.  Network access is GET-only, bounded, and used
solely to hydrate immutable seed identities and nearby rows.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable

import httpx
import yaml

from ..config import (
    STRUCTURAL_NEIGHBOR_SHADOW,
    STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY,
    STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION,
    SUPABASE_SERVICE_KEY,
    SUPABASE_URL,
)
from .structural_neighbor_coverage import (
    DEFAULT_CONFIG,
    select_structural_neighbors,
)

logger = logging.getLogger(__name__)
EVENT_SCHEMA = "structural_neighbor_shadow_event_v1"
TELEMETRY_ALLOWED_FIELDS = frozenset(
    {
        "schema",
        "event_id",
        "query_hmac_sha256",
        "served_ids_sha256",
        "config_sha256",
        "sampling_hmac_key_version",
        "sample_bucket",
        "served_rows",
        "selected_ids",
        "selected_rows",
        "candidate_rows",
        "toc_rejected_rows",
        "http_requests",
        "rows_read",
        "elapsed_ms",
        "status",
        "error_type",
        "sink_status",
        "sink_error_type",
        "served_identity_equal",
        "generator_calls",
        "database_writes",
        "coverage_attestations",
        "overflow",
        "emitted",
    }
)
_SELECT = (
    "id,document_id,extraction_sha256,chunk_index,content,section_title,"
    "product_model,language,source_file,page_number,duplicate_of"
)


def _runtime_contract() -> dict[str, Any]:
    payload = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    runtime = payload.get("shadow_runtime") or {}
    expected = {
        "default_enabled": False,
        "raw_query_allowed": False,
        "raw_content_allowed": False,
        "fail_open": True,
        "hmac_key_version_required": True,
        "retention_days_max": 14,
        "access": "operations_and_named_evaluators_only",
    }
    if any(
        type(runtime.get(key)) is not type(value) or runtime.get(key) != value
        for key, value in expected.items()
    ):
        raise RuntimeError("unsafe structural-neighbor shadow contract")
    for key, low, high in (
        ("timeout_ms", 50, 2000),
        ("sample_basis_points", 1, 10000),
        ("max_http_requests", 2, 12),
    ):
        value = runtime.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            raise RuntimeError(f"invalid structural-neighbor shadow {key}")
    return runtime


def _stable_json_sha(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _keyed_digest(secret: str, value: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _merged_intervals(indexes: list[int], gap: int) -> list[tuple[int, int]]:
    intervals = sorted((max(0, index - gap), index + gap) for index in indexes)
    merged: list[list[int]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def fetch_structural_neighbor_rows(
    served_chunks: list[dict[str, Any]],
    *,
    max_gap: int,
    max_candidates: int,
    max_http_requests: int,
    timeout_seconds: float,
    client: httpx.Client | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Hydrate seeds and neighbors with bounded, GET-only PostgREST reads."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable for shadow read")
    ids = [str(row.get("id") or "") for row in served_chunks if row.get("id")]
    if not ids:
        return [], [], {"http_requests": 0, "rows_read": 0}
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    started = time.monotonic()
    request_count = 0

    def get_rows(request_client: httpx.Client, params: dict[str, str]) -> list[dict]:
        nonlocal request_count
        request_count += 1
        if request_count > max_http_requests:
            raise RuntimeError("structural neighbor HTTP request cap exceeded")
        remaining = timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("structural neighbor read deadline exceeded")
        response = request_client.get(
            f"{SUPABASE_URL.rstrip('/')}/rest/v1/chunks_v2",
            headers=headers,
            params=params,
            timeout=remaining,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("structural neighbor read returned non-list payload")
        return payload

    context = (
        httpx.Client(timeout=timeout_seconds) if client is None else nullcontext(client)
    )
    with context as request_client:
        hydrated_rows = get_rows(
            request_client,
            {
                "select": _SELECT,
                "id": f"in.({','.join(ids)})",
                "limit": str(len(ids)),
            },
        )
        by_id = {str(row.get("id") or ""): row for row in hydrated_rows}
        missing = sorted(set(ids) - set(by_id))
        if missing:
            raise RuntimeError("structural neighbor seed hydration incomplete")
        hydrated = [by_id[chunk_id] for chunk_id in ids]

        groups: dict[tuple[str, str], list[int]] = defaultdict(list)
        for row in hydrated:
            document_id = str(row.get("document_id") or "")
            extraction_sha256 = str(row.get("extraction_sha256") or "")
            index = row.get("chunk_index")
            if document_id and len(extraction_sha256) == 64 and isinstance(index, int):
                groups[(document_id, extraction_sha256)].append(index)

        neighbors: dict[str, dict[str, Any]] = {}
        for (document_id, extraction_sha256), indexes in sorted(groups.items()):
            for lower, upper in _merged_intervals(indexes, max_gap):
                page = get_rows(
                    request_client,
                    {
                        "select": _SELECT,
                        "document_id": f"eq.{document_id}",
                        "extraction_sha256": f"eq.{extraction_sha256}",
                        "chunk_index": f"gte.{lower}",
                        "and": f"(chunk_index.lte.{upper})",
                        "order": "chunk_index.asc,id.asc",
                        "limit": str(max_candidates + 1),
                    },
                )
                for row in page:
                    row_id = str(row.get("id") or "")
                    if row_id:
                        neighbors[row_id] = row
                if len(neighbors) > max_candidates:
                    raise RuntimeError("structural neighbor candidate cap exceeded")
    return hydrated, list(neighbors.values()), {
        "http_requests": request_count,
        "rows_read": len(hydrated) + len(neighbors),
    }


def _log_sink(event: dict[str, Any]) -> None:
    unknown = set(event) - TELEMETRY_ALLOWED_FIELDS
    if unknown:
        raise RuntimeError(f"structural neighbor telemetry field not allowed: {sorted(unknown)}")
    logger.info("structural_neighbor_shadow %s", json.dumps(event, sort_keys=True))


def observe_structural_neighbor_shadow(
    query: str,
    served_chunks: list[dict[str, Any]],
    *,
    enabled: bool | None = None,
    hmac_key: str | None = None,
    hmac_key_version: str | None = None,
    fetcher: Callable[..., tuple[list[dict], list[dict], dict]] = fetch_structural_neighbor_rows,
    sink: Callable[[dict[str, Any]], None] | None = _log_sink,
    sample_basis_points: int | None = None,
    timeout_ms: int | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Observe candidates without mutating or returning the served context."""
    runtime = _runtime_contract()
    active = STRUCTURAL_NEIGHBOR_SHADOW if enabled is None else enabled
    if not active:
        return {"schema": EVENT_SCHEMA, "status": "disabled", "emitted": False}

    secret = STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY if hmac_key is None else hmac_key
    key_version = (
        STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION
        if hmac_key_version is None
        else hmac_key_version
    )
    if len(secret) < 32:
        return {
            "schema": EVENT_SCHEMA,
            "status": "configuration_error",
            "error_type": "MissingTelemetryHmacKey",
            "emitted": False,
        }
    if (
        not isinstance(key_version, str)
        or not key_version.startswith("v")
        or not key_version[1:].isdigit()
        or not 1 <= int(key_version[1:]) <= 999999
    ):
        return {
            "schema": EVENT_SCHEMA,
            "status": "configuration_error",
            "error_type": "MissingTelemetryHmacKeyVersion",
            "emitted": False,
        }
    sample_bps = runtime["sample_basis_points"] if sample_basis_points is None else sample_basis_points
    budget_ms = runtime["timeout_ms"] if timeout_ms is None else timeout_ms
    if not 1 <= sample_bps <= 10000 or not 50 <= budget_ms <= 2000:
        return {
            "schema": EVENT_SCHEMA,
            "status": "configuration_error",
            "error_type": "InvalidRuntimeBound",
            "emitted": False,
        }

    query_digest = _keyed_digest(secret, query)
    sample_bucket = int(query_digest[:8], 16) % 10000
    if sample_bucket >= sample_bps:
        return {
            "schema": EVENT_SCHEMA,
            "status": "sampled_out",
            "sample_bucket": sample_bucket,
            "emitted": False,
        }

    original_digest = _stable_json_sha(served_chunks)
    served_copy = copy.deepcopy(served_chunks)
    served_ids = [str(row.get("id") or "") for row in served_copy]
    config_sha256 = hashlib.sha256(DEFAULT_CONFIG.read_bytes()).hexdigest()
    event = {
        "schema": EVENT_SCHEMA,
        "event_id": _stable_json_sha([query_digest, served_ids, config_sha256]),
        "query_hmac_sha256": query_digest,
        "served_ids_sha256": _stable_json_sha(served_ids),
        "config_sha256": config_sha256,
        "sampling_hmac_key_version": key_version,
        "sample_bucket": sample_bucket,
        "served_rows": len(served_copy),
        "generator_calls": 0,
        "database_writes": 0,
        "coverage_attestations": 0,
        "emitted": True,
    }
    started = monotonic()
    try:
        coverage_config = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        hydrated, candidates, read_trace = fetcher(
            served_copy[: coverage_config["max_seeds"]],
            max_gap=coverage_config["max_gap"],
            max_candidates=coverage_config["max_candidates"],
            max_http_requests=runtime["max_http_requests"],
            timeout_seconds=budget_ms / 1000.0,
        )
        selected, selection_trace = select_structural_neighbors(
            query, hydrated, candidates
        )
        elapsed_ms = round((monotonic() - started) * 1000, 3)
        event.update(
            {
                "status": "timeout" if elapsed_ms > budget_ms else "observed",
                "elapsed_ms": elapsed_ms,
                "http_requests": read_trace.get("http_requests", 0),
                "rows_read": read_trace.get("rows_read", 0),
                "candidate_rows": len(candidates),
                "selected_ids": [str(row["id"]) for row in selected],
                "selected_rows": len(selected),
                "toc_rejected_rows": len(selection_trace.get("toc_rejected_ids") or []),
                "overflow": selection_trace.get("overflow", False),
            }
        )
    except Exception as exc:  # fail-open is the core contract
        event.update(
            {
                "status": "error",
                "error_type": type(exc).__name__,
                "elapsed_ms": round((monotonic() - started) * 1000, 3),
                "selected_ids": [],
                "selected_rows": 0,
            }
        )

    event["served_identity_equal"] = _stable_json_sha(served_chunks) == original_digest
    if sink is not None:
        try:
            sink(copy.deepcopy(event))
            event["sink_status"] = "ok"
        except Exception as exc:  # telemetry can never break the answer path
            event["sink_status"] = "error"
            event["sink_error_type"] = type(exc).__name__
    else:
        event["sink_status"] = "discarded"
    return event
