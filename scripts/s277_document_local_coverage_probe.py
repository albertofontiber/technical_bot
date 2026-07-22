"""GET-only release-integrity probe for document-local coverage.

This probe replays the thirteen preregistered P1 questions from the sealed S113
prefixes.  It deliberately stops before retrieval, reranking and generation:
the purpose is to prove the new second hop's authority, boundedness, exact
serving view and fail-closed controls without consuming a model call or writing
to Supabase.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
FREEZE_SHA256_LF = "556490dd74056603b6b8f8c8d885c55820957761bbd6407bb1dcf8f533434498"
PREREG = ROOT / "evals/s277_c1_p1_prereg_v1.yaml"
DEFAULT_OUTPUT = ROOT / "evals/s277_document_local_coverage_probe_v2.json"
TARGET_QID = "hp011"
TARGET_ID = "475a8f18-7c69-4c7a-8111-45bd67334c96"
MAX_GETS_PER_QID = 12
ALLOWED_PATHS = frozenset(
    {
        "/rest/v1/documents",
        "/rest/v1/chunks_v2",
        "/rest/v1/rpc/document_local_snapshot_v2",
    }
)
INTEGRATION_SURFACE_FILES = tuple(
    ROOT / relative
    for relative in (
        "src/rag/coverage_runtime.py",
        "src/rag/serving_pipeline.py",
    )
)
RUNTIME_CONFIG_FILES = tuple(
    ROOT / relative
    for relative in (
        "config/structural_neighbor_coverage_v1.yaml",
        "config/retrieval_facets_v3.yaml",
        "config/evidence_coverage_facets_v4.yaml",
        "config/evidence_coverage_facets_v2.yaml",
        "config/structured_numeric_claims_v2.yaml",
        "config/retrieval_facets_v4.yaml",
        "config/evidence_coverage_facets_v5.yaml",
    )
)
RPC_MIGRATION_FILES = (
    ROOT
    / "supabase/migrations/20260721210847_s277_document_local_snapshot_rpc.sql",
    ROOT
    / "supabase/migrations/20260721220110_s277_document_local_exact_blob_authority.sql",
    ROOT
    / "supabase/migrations/20260722013000_s277_document_revision_lineage_snapshot_v2.sql",
)
P1_ACL_MIGRATION = (
    ROOT
    / "supabase/migrations/20260722014500_s277_p1_document_local_snapshot_v2_acl.sql"
)
MIGRATION_RECONCILIATION_RECEIPT = (
    ROOT / "evals/s277_document_local_migration_reconciliation_receipt_v2.json"
)
MODEL_PROVIDER_IMPORTS = frozenset(
    {
        "anthropic",
        "cohere",
        "google.generativeai",
        "google.genai",
        "mistralai",
        "openai",
        "voyageai",
    }
)


def _sha256_lf(path: Path) -> str:
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


class RecordingGetOnlyClient:
    """Expose only GET while retaining redacted request and lifecycle evidence."""

    def __init__(self, client: httpx.Client):
        self._client = client
        self.requests: list[dict[str, Any]] = []
        self.snapshot_payloads: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        path = urlparse(url).path
        self.requests.append(
            {
                "path": path,
                "params": copy.deepcopy(kwargs.get("params") or {}),
                "method": "GET",
            }
        )
        response = self._client.get(url, **kwargs)
        if (
            path == "/rest/v1/rpc/document_local_snapshot_v2"
            and response.status_code == 200
        ):
            payload = response.json()
            if isinstance(payload, dict):
                self.snapshot_payloads.append(copy.deepcopy(payload))
        return response


class HttpMutationGuard:
    """Fail closed if exercised code attempts a mutating HTTP verb."""

    _METHODS = ("post", "put", "patch", "delete")

    def __init__(self) -> None:
        self.attempts: list[dict[str, str]] = []
        self._originals: list[tuple[type, str, Any]] = []

    def __enter__(self) -> "HttpMutationGuard":
        for owner in (httpx.Client, httpx.AsyncClient):
            for method in self._METHODS:
                original = getattr(owner, method)
                self._originals.append((owner, method, original))
                if owner is httpx.AsyncClient:

                    async def blocked_async(
                        _client: Any,
                        *args: Any,
                        __method: str = method,
                        **_kwargs: Any,
                    ) -> Any:
                        self._record(__method, args)
                        raise RuntimeError("mutating HTTP request blocked by probe")

                    setattr(owner, method, blocked_async)
                else:

                    def blocked(
                        _client: Any,
                        *args: Any,
                        __method: str = method,
                        **_kwargs: Any,
                    ) -> Any:
                        self._record(__method, args)
                        raise RuntimeError("mutating HTTP request blocked by probe")

                    setattr(owner, method, blocked)
        return self

    def _record(self, method: str, args: tuple[Any, ...]) -> None:
        raw_url = str(args[0]) if args else ""
        parsed = urlparse(raw_url)
        self.attempts.append({"method": method.upper(), "path": parsed.path})

    def __exit__(self, *_exc: Any) -> None:
        for owner, method, original in reversed(self._originals):
            setattr(owner, method, original)
        self._originals.clear()


def _sha256_manifest(paths: tuple[Path, ...]) -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in paths
    }


def _loaded_project_python_files() -> tuple[Path, ...]:
    """Derive the exercised project-module set from Python's import registry."""
    files: set[Path] = set()
    instrument = Path(__file__).resolve()
    for module in tuple(sys.modules.values()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        path = Path(raw_path).resolve()
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            continue
        if (
            path != instrument
            and path.suffix == ".py"
            and relative.parts
            and relative.parts[0] in {"src", "scripts"}
        ):
            files.add(path)
    return tuple(sorted(files, key=lambda path: path.as_posix()))


def _unique_paths(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    return tuple(dict.fromkeys(path.resolve() for path in paths))


def _loaded_model_provider_modules() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if any(
            name == provider or name.startswith(provider + ".")
            for provider in MODEL_PROVIDER_IMPORTS
        )
    )


def _model_provider_import_findings(paths: tuple[Path, ...]) -> list[str]:
    findings: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                if any(
                    name == provider or name.startswith(provider + ".")
                    for provider in MODEL_PROVIDER_IMPORTS
                ):
                    findings.add(
                        f"{str(path.relative_to(ROOT)).replace(chr(92), '/')}:{name}"
                    )
    return sorted(findings)


def _rpc_body_read_only_contract(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    parts = source.split("$function$")
    if len(parts) < 3:
        return False
    body = parts[1]
    forbidden = re.compile(
        r"\b(insert|update|delete|merge|truncate|copy|call|perform|execute|"
        r"create|alter|drop|grant|revoke)\b",
        re.IGNORECASE,
    )
    return (
        "LANGUAGE sql" in source
        and "STABLE" in source
        and "SECURITY INVOKER" in source
        and "SET search_path = ''" in source
        and forbidden.search(body) is None
    )


def _load_inputs() -> tuple[list[str], dict[str, dict[str, Any]]]:
    if _sha256_lf(FREEZE) != FREEZE_SHA256_LF:
        raise RuntimeError("sealed S113 context freeze drifted")
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    qids = list(prereg["population"]["qids"])
    if len(qids) != 13 or len(set(qids)) != 13 or TARGET_QID not in qids:
        raise RuntimeError("P1 control cohort drifted")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    rows = {row["qid"]: row for row in freeze["rows"] if row["qid"] in qids}
    if set(rows) != set(qids):
        raise RuntimeError("sealed S113 rows incomplete")
    return qids, rows


def _prefix(row: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {str(item.get("id") or ""): item for item in row["context"]}
    try:
        return [copy.deepcopy(by_id[chunk_id]) for chunk_id in row["prefix_ids"]]
    except KeyError as exc:
        raise RuntimeError("sealed prefix identity missing from context") from exc


def _lifecycle_checks(
    snapshot_payloads: list[dict[str, Any]],
    target: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    from src.rag.document_local_coverage import resolve_authoritative_documents

    document_id = str(target["document_id"])
    matching: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for payload in snapshot_payloads:
        for authority in payload.get("authorities") or []:
            if str(authority.get("document_id") or "") == document_id:
                matching.append((payload, authority))
    if len(matching) != 1:
        raise RuntimeError("target authority absent or duplicated in atomic snapshot")
    payload, raw_authority = matching[0]
    scope_rank = raw_authority.get("scope_rank")
    component = []
    for source_row in payload.get("document_rows") or []:
        if source_row.get("scope_rank") != scope_rank:
            continue
        row = copy.deepcopy(source_row)
        row.pop("scope_rank", None)
        component.append(row)
    by_id = {str(row.get("id") or ""): row for row in component}
    active = by_id.get(document_id)
    if not active:
        raise RuntimeError("target active document absent from lifecycle receipt")
    predecessor_id = str(active.get("supersedes_id") or "")
    predecessor = by_id.get(predecessor_id)
    if not predecessor:
        raise RuntimeError("target predecessor absent from lifecycle receipt")
    scope = {
        "document_id": document_id,
        "extraction_sha256": str(target["extraction_sha256"]),
        "source_file": str(target["source_file"]),
        "manufacturer": str(target.get("manufacturer") or ""),
        "product_model": str(target.get("product_model") or ""),
    }
    authorities, reason = resolve_authoritative_documents(component, [scope])
    positive = (
        reason == "ok"
        and len(authorities) == 1
        and active.get("status") == "active"
        and active.get("superseded_by_id") is None
        and predecessor.get("status") == "superseded"
        and predecessor.get("superseded_by_id") == document_id
        and active.get("source_pdf_sha256") == target.get("extraction_sha256")
        and payload.get("schema") == "document_local_snapshot_v2"
        and active.get("revision_lineage_id")
        == raw_authority.get("revision_lineage_id")
        and raw_authority.get("family_rows") == len(component)
    )
    return {
        "passed": positive,
        "active_document_id": document_id,
        "active_revision": active.get("revision"),
        "predecessor_document_id": predecessor_id,
        "predecessor_revision": predecessor.get("revision"),
        "reciprocal": predecessor.get("superseded_by_id") == document_id,
        "blob_bound": active.get("source_pdf_sha256")
        == target.get("extraction_sha256"),
        "atomic_snapshot": payload.get("schema") == "document_local_snapshot_v2",
        "revision_lineage_id": raw_authority.get("revision_lineage_id"),
        "family_rows": len(component),
        "snapshot_sha256": target.get("document_local_snapshot_sha256"),
    }, component, scope


def _runtime_negative_controls(
    component: list[dict[str, Any]],
    scope: dict[str, str],
    target: dict[str, Any],
) -> dict[str, bool]:
    from src.rag.document_local_coverage import (
        TOTAL_CANDIDATE_LIMIT,
        resolve_authoritative_documents,
        select_document_local_coverage,
    )
    from src.rag.post_rerank_coverage import append_validated_coverage

    active_id = scope["document_id"]
    active_row = next(row for row in component if str(row.get("id")) == active_id)
    predecessor_id = str(active_row.get("supersedes_id") or "")
    predecessor_index = next(
        index
        for index, row in enumerate(component)
        if str(row.get("id") or "") == predecessor_id
    )

    two_active = copy.deepcopy(component)
    two_active[predecessor_index]["status"] = "active"
    result, reason_two_active = resolve_authoritative_documents(two_active, [scope])

    disconnected = copy.deepcopy(component)
    disconnected_active = copy.deepcopy(component[-1])
    disconnected_active.update(
        {
            "id": "00000000-0000-4000-8000-000000000001",
            "source_pdf_sha256": "d" * 64,
            "supersedes_id": None,
        }
    )
    disconnected.append(disconnected_active)
    disconnected_result, reason_disconnected = resolve_authoritative_documents(
        disconnected, [scope]
    )

    broken_pointer = copy.deepcopy(component)
    broken_pointer[predecessor_index]["superseded_by_id"] = None
    broken, reason_broken = resolve_authoritative_documents(broken_pointer, [scope])

    bad_scope = dict(scope)
    bad_scope["extraction_sha256"] = "f" * 64
    mismatch, reason_mismatch = resolve_authoritative_documents(component, [bad_scope])

    unverified = copy.deepcopy(component)
    for row in unverified:
        row["revision_lineage_id"] = None
    unverified_result, reason_unverified = resolve_authoritative_documents(
        unverified, [scope]
    )

    prefix = [{"id": "control-prefix", "content": "immutable"}]
    duplicate = copy.deepcopy(target)
    duplicate["duplicate_of"] = "other-canonical-row"
    duplicate_output = append_validated_coverage(prefix, [duplicate])

    cross_blob = copy.deepcopy(target)
    cross_blob["document_local_authority_extraction_sha256"] = "e" * 64
    cross_blob_output = append_validated_coverage(prefix, [cross_blob])

    cross_lineage = copy.deepcopy(target)
    cross_lineage["document_local_authority_revision_lineage_id"] = (
        "00000000-0000-4000-8000-000000000002"
    )
    cross_lineage_output = append_validated_coverage(prefix, [cross_lineage])

    tampered = copy.deepcopy(target)
    tampered["coverage_cards"][0]["quote"] += " tampered"
    tampered_output = append_validated_coverage(prefix, [tampered])

    prose = copy.deepcopy(target)
    prose_content = "Registro en prosa cuyo valor final queda fuera del recorte."
    prose["content"] = prose_content
    prose["coverage_cards"] = [
        {
            "candidate_id": prose["id"],
            "candidate_rank": 1,
            "start": 0,
            "end": 18,
            "quote": prose_content[:18],
            "facet": "timing_state",
            "exact_source_span_validated": True,
        }
    ]
    prose_output = append_validated_coverage(prefix, [prose])

    authority = {
        "document_id": scope["document_id"],
        "revision_lineage_id": str(active_row.get("revision_lineage_id") or ""),
        "extraction_sha256": scope["extraction_sha256"],
        "source_file": scope["source_file"],
        "language": "es",
        "revision": str(component[-1].get("revision") or ""),
    }
    overflow_rows = [
        copy.deepcopy(target) for _ in range(TOTAL_CANDIDATE_LIMIT + 1)
    ]
    for index, row in enumerate(overflow_rows):
        row["id"] = f"overflow-{index}"
    overflow, overflow_trace = select_document_local_coverage(
        "consulta de control con condicion temporizador diagnostico",
        overflow_rows,
        [],
        [authority],
    )
    return {
        "two_active_rejected": not result
        and reason_two_active == "ambiguous_active_revision",
        "disconnected_active_rejected": not disconnected_result
        and reason_disconnected == "incomplete_revision_chain",
        "broken_pointer_rejected": not broken
        and reason_broken == "nonreciprocal_revision_chain",
        "sha_mismatch_rejected": not mismatch
        and reason_mismatch == "active_revision_not_bound_to_anchor_blob",
        "unverified_lineage_rejected": not unverified_result
        and reason_unverified == "unverified_document_lineage",
        "duplicate_rejected": duplicate_output is prefix,
        "cross_blob_rejected": cross_blob_output is prefix,
        "cross_lineage_rejected": cross_lineage_output is prefix,
        "tampered_receipt_rejected": tampered_output is prefix,
        "unprovable_prose_record_rejected": prose_output is prefix,
        "combined_candidate_overflow_rejected": not overflow
        and overflow_trace.get("status") == "combined_candidate_cap_exceeded",
    }


def _live_sql_negative_controls(
    headers: dict[str, str],
    target_rpc_params: dict[str, Any],
) -> dict[str, Any]:
    """Exercise authority and parser rejection in the deployed SQL function."""
    endpoint = f"{os.environ['SUPABASE_URL']}/rest/v1/rpc/document_local_snapshot_v2"
    scopes = json.loads(str(target_rpc_params["anchor_scopes"]))
    if not isinstance(scopes, list) or not 1 <= len(scopes) <= 2:
        raise RuntimeError("target RPC scope unavailable for live controls")

    mismatched_scopes = copy.deepcopy(scopes)
    for scope in mismatched_scopes:
        original_sha = str(scope["extraction_sha256"])
        scope["extraction_sha256"] = (
            ("0" if original_sha[0] != "0" else "1") + original_sha[1:]
        )
    mismatch_params = copy.deepcopy(target_rpc_params)
    mismatch_params["anchor_scopes"] = json.dumps(
        mismatched_scopes,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    malformed_params = copy.deepcopy(target_rpc_params)
    malformed_params["fts_query"] = "a&&b"

    with HttpMutationGuard() as mutation_guard, httpx.Client(
        headers=headers,
        timeout=2.0,
    ) as transport:
        recorder = RecordingGetOnlyClient(transport)
        mismatch_response = recorder.get(endpoint, params=mismatch_params, timeout=2.0)
        mismatch_response.raise_for_status()
        mismatch_payload = mismatch_response.json()
        malformed_response = recorder.get(endpoint, params=malformed_params, timeout=2.0)
        malformed_response.raise_for_status()
        malformed_payload = malformed_response.json()

    mismatch_reasons = {
        str(row.get("reason") or "")
        for row in mismatch_payload.get("rejections") or []
        if isinstance(row, dict)
    }
    checks = {
        "mismatched_blob_rejected_by_live_rpc": (
            mismatch_payload.get("input_status") == "ok"
            and not mismatch_payload.get("authorities")
            and not mismatch_payload.get("candidates")
            and "active_revision_not_bound_to_anchor_blob" in mismatch_reasons
        ),
        "malformed_tsquery_rejected_by_live_rpc": (
            malformed_payload.get("input_status") == "invalid_request"
            and not malformed_payload.get("authorities")
            and not malformed_payload.get("candidates")
        ),
        "controls_used_get_only_rpc": (
            len(recorder.requests) == 2
            and all(
                request["method"] == "GET"
                and request["path"] == "/rest/v1/rpc/document_local_snapshot_v2"
                for request in recorder.requests
            )
        ),
        "no_mutating_http_attempts": not mutation_guard.attempts,
    }
    return {
        "checks": checks,
        "get_requests": len(recorder.requests),
        "mutation_attempts": mutation_guard.attempts,
        "mismatched_blob_payload_sha256": hashlib.sha256(
            _canonical_bytes(mismatch_payload)
        ).hexdigest(),
        "malformed_tsquery_payload_sha256": hashlib.sha256(
            _canonical_bytes(malformed_payload)
        ).hexdigest(),
    }


def run(env_file: Path, output: Path) -> dict[str, Any]:
    load_dotenv(env_file, override=False)
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"):
        raise RuntimeError("Supabase credentials unavailable")

    # Import after loading the explicit environment: config is resolved once.
    from src.rag.document_local_coverage import (
        LANE as DOCUMENT_LOCAL_LANE,
        collect_document_local_coverage,
        fetch_document_local_candidates,
    )
    from src.rag.post_rerank_coverage import (
        DOCUMENT_LOCAL_RECORD_KIND,
        apply_post_rerank_coverage_with_trace,
        collect_structural_coverage,
        coverage_context_content,
        has_exact_served_coverage_receipt,
    )
    from src.rag.structural_neighbor_shadow import fetch_structural_neighbor_rows
    from src.rag.rerank_pool_coverage import QUERY_CONFIG
    from src.rag import catalog as model_catalog
    from src.rag import catalog_resolver

    qids, frozen_rows = _load_inputs()
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    target_row: dict[str, Any] | None = None
    target_recorder: RecordingGetOnlyClient | None = None
    catalogue_loaded_before = {
        "governed_catalog": bool(catalog_resolver._loaded),
        "model_catalog": bool(model_catalog._loaded),
    }

    headers = {
        "apikey": os.environ["SUPABASE_SERVICE_KEY"],
        "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
    }
    with HttpMutationGuard() as cohort_mutation_guard, httpx.Client(
        headers=headers,
        timeout=2.0,
    ) as transport:
        for qid in qids:
            frozen = frozen_rows[qid]
            prefix = _prefix(frozen)
            prefix_before = _canonical_bytes(prefix)
            recorder = RecordingGetOnlyClient(transport)

            def structural_collector(query: str, seeds: list[dict[str, Any]]):
                def fetcher(served: list[dict[str, Any]], **kwargs: Any):
                    return fetch_structural_neighbor_rows(
                        served, client=recorder, **kwargs
                    )

                return collect_structural_coverage(query, seeds, fetcher=fetcher)

            def document_local_collector(
                query: str,
                anchors: list[dict[str, Any]],
                covered: list[dict[str, Any]],
            ):
                def fetcher(query_text: str, anchor_rows: list[dict[str, Any]]):
                    return fetch_document_local_candidates(
                        query_text, anchor_rows, client=recorder
                    )

                return collect_document_local_coverage(
                    query, anchors, covered, fetcher=fetcher
                )

            served, trace = apply_post_rerank_coverage_with_trace(
                frozen["question"],
                prefix,
                enabled=True,
                structural_enabled=True,
                table_preamble_enabled=False,
                hyq_enabled=False,
                pool_enabled=False,
                document_local_enabled=True,
                cascade_enabled=False,
                compatibility_enabled=False,
                structural_collector=structural_collector,
                document_local_collector=document_local_collector,
            )
            appended = served[len(prefix) :]
            local_rows = [
                row
                for row in appended
                if row.get("retrieval_lane") == DOCUMENT_LOCAL_LANE
            ]
            local_trace = next(
                (
                    lane
                    for lane in trace.get("lanes", [])
                    if lane.get("lane") == DOCUMENT_LOCAL_LANE
                ),
                {},
            )
            request_blob = json.dumps(
                recorder.requests, ensure_ascii=False, sort_keys=True
            )
            row_result = {
                "qid": qid,
                "prefix_sha256": hashlib.sha256(prefix_before).hexdigest(),
                "prefix_byte_equal": _canonical_bytes(served[: len(prefix)])
                == prefix_before
                and _canonical_bytes(prefix) == prefix_before,
                "appended_ids": [str(row.get("id") or "") for row in appended],
                "appended_lanes": [
                    str(row.get("retrieval_lane") or "") for row in appended
                ],
                "document_local_appends": len(local_rows),
                "all_appended_exact_served_receipts": all(
                    has_exact_served_coverage_receipt(row) for row in appended
                ),
                "lane_errors": [
                    str(lane.get("lane") or "")
                    for lane in trace.get("lanes", [])
                    if lane.get("status") == "error"
                ],
                "document_local_status": local_trace.get("status"),
                "document_local_http_requests": local_trace.get("http_requests", 0),
                "document_local_rows_read": local_trace.get("rows_read", 0),
                "document_local_authoritative_documents": local_trace.get(
                    "authoritative_documents", 0
                ),
                "document_local_fts_candidate_rows": local_trace.get(
                    "fts_candidate_rows", 0
                ),
                "document_local_query_facets_sha256": local_trace.get(
                    "query_facets_sha256"
                ),
                "document_local_catalog_scope_applied": local_trace.get(
                    "catalog_scope_applied"
                ),
                "get_requests": len(recorder.requests),
                "only_allowed_get_paths": all(
                    request["method"] == "GET" and request["path"] in ALLOWED_PATHS
                    for request in recorder.requests
                ),
                "target_id_absent_from_requests": TARGET_ID not in request_blob,
            }
            results.append(row_result)
            if qid == TARGET_QID:
                if len(local_rows) != 1:
                    rpc_diagnostics = [
                        request["params"]
                        for request in recorder.requests
                        if request["path"]
                        == "/rest/v1/rpc/document_local_snapshot_v2"
                    ]
                    raise RuntimeError(
                        "target did not produce exactly one local append: "
                        + json.dumps(
                            {
                                "result": row_result,
                                "rpc": rpc_diagnostics,
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                target_row = local_rows[0]
                target_recorder = recorder

    if target_row is None or target_recorder is None:
        raise RuntimeError("target evidence unavailable")
    target_view = coverage_context_content(target_row)
    lifecycle, component, scope = _lifecycle_checks(
        target_recorder.snapshot_payloads, target_row
    )
    runtime_controls = _runtime_negative_controls(component, scope, target_row)
    target_rpc_requests = [
        request
        for request in target_recorder.requests
        if request["path"] == "/rest/v1/rpc/document_local_snapshot_v2"
    ]
    if len(target_rpc_requests) != 1:
        raise RuntimeError("target atomic RPC request absent or duplicated")
    live_sql_controls = _live_sql_negative_controls(
        headers,
        target_rpc_requests[0]["params"],
    )

    exercised_runtime_files = _loaded_project_python_files()
    reviewed_runtime_files = _unique_paths(
        exercised_runtime_files + INTEGRATION_SURFACE_FILES
    )
    runtime_surface_files = reviewed_runtime_files + RUNTIME_CONFIG_FILES
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8") for path in runtime_surface_files
    ).casefold()
    query_facets_sha256 = hashlib.sha256(QUERY_CONFIG.read_bytes()).hexdigest()
    provider_import_findings = _model_provider_import_findings(
        reviewed_runtime_files
    )
    loaded_provider_modules = _loaded_model_provider_modules()
    catalogue_loaded_after = {
        "governed_catalog": bool(catalog_resolver._loaded),
        "model_catalog": bool(model_catalog._loaded),
    }
    catalogue_data_not_loaded = not any(
        [*catalogue_loaded_before.values(), *catalogue_loaded_after.values()]
    )
    rpc_bodies_read_only = all(
        _rpc_body_read_only_contract(path) for path in RPC_MIGRATION_FILES
    )
    forbidden_runtime_markers = (
        TARGET_QID,
        TARGET_ID,
        "hlsi-mn-103",
        "page_number == 63",
        "p63",
    )
    target = {
        "qid": TARGET_QID,
        "selected_id": target_row.get("id"),
        "lane": target_row.get("retrieval_lane"),
        "exact_served_receipt": has_exact_served_coverage_receipt(target_row),
        "served_view_chars": len(target_view),
        "complete_record_receipt": all(
            card.get("complete_record_validated") is True
            and card.get("record_kind") == DOCUMENT_LOCAL_RECORD_KIND
            for card in target_row.get("served_coverage_cards") or []
        ),
        "authoritative_descriptive_identity": {
            field: target_row.get(field)
            for field in (
                "document_family",
                "language",
                "doc_type",
                "manufacturer",
                "product_model",
            )
        },
        "authoritative_identity_stamps_match": all(
            bool(str(target_row.get(field) or "").strip())
            and str(target_row.get(field) or "")
            == str(target_row.get(f"document_local_authority_{field}") or "")
            for field in (
                "document_family",
                "language",
                "doc_type",
                "manufacturer",
                "product_model",
            )
        )
        and bool(str(target_row.get("document_revision_lineage_id") or ""))
        and str(target_row.get("document_revision_lineage_id") or "")
        == str(
            target_row.get("document_local_authority_revision_lineage_id")
            or ""
        ),
        "served_view_contains": {
            "reset_inhibition_record": "Rearme inhibido tras extinción" in target_view,
            "discharge_timer_reference": "t.A" in target_view,
            "zero_option": "00" in target_view,
            "bounded_minutes_option": "01 a 30" in target_view,
        },
        "lifecycle": lifecycle,
        "target_id_absent_from_all_requests": all(
            result["target_id_absent_from_requests"] for result in results
        ),
        "runtime_has_no_target_markers": not any(
            marker.casefold() in runtime_source for marker in forbidden_runtime_markers
        ),
        "catalogue_data_not_loaded": catalogue_data_not_loaded,
        "catalogue_state": {
            "before": catalogue_loaded_before,
            "after": catalogue_loaded_after,
        },
        "model_provider_import_findings": provider_import_findings,
        "loaded_model_provider_modules": loaded_provider_modules,
        "rpc_bodies_read_only": rpc_bodies_read_only,
        "query_facets_sha256_verified": next(
            result["document_local_query_facets_sha256"]
            for result in results
            if result["qid"] == TARGET_QID
        )
        == query_facets_sha256,
        "exercised_runtime_module_sha256s": _sha256_manifest(
            exercised_runtime_files
        ),
        "integration_surface_sha256s": _sha256_manifest(
            INTEGRATION_SURFACE_FILES
        ),
        "runtime_config_sha256s": _sha256_manifest(RUNTIME_CONFIG_FILES),
    }

    selected_qids = [
        result["qid"] for result in results if result["document_local_appends"]
    ]
    selector_exercised_qids = [
        result["qid"]
        for result in results
        if result["document_local_fts_candidate_rows"] > 0
    ]
    migration_reconciliation = json.loads(
        MIGRATION_RECONCILIATION_RECEIPT.read_text(encoding="utf-8")
    )
    migration_reconciled = (
        migration_reconciliation.get("status") == "RECONCILED"
        and all(
            migration_reconciliation.get("terminal_state", {})
            .get("migration_history", {})
            .get(version)
            is True
            for version in (
                "20260721210847",
                "20260721220110",
                "20260722013000",
                "20260722014500",
            )
        )
    )
    catalog_scope_bypassed = (
        next(
            result["document_local_catalog_scope_applied"]
            for result in results
            if result["qid"] == TARGET_QID
        )
        is False
        and all(
            result["document_local_catalog_scope_applied"] in (None, False)
            for result in results
        )
    )
    no_mutating_http_attempts = (
        not cohort_mutation_guard.attempts
        and not live_sql_controls["mutation_attempts"]
    )
    checks = {
        "sealed_freeze": _sha256_lf(FREEZE) == FREEZE_SHA256_LF,
        "cohort_13": len(results) == 13,
        "all_prefixes_byte_equal": all(
            result["prefix_byte_equal"] for result in results
        ),
        "all_appends_have_exact_served_receipts": all(
            result["all_appended_exact_served_receipts"] for result in results
        ),
        "no_lane_errors": all(not result["lane_errors"] for result in results),
        "document_local_cap_one": all(
            result["document_local_appends"] <= 1 for result in results
        ),
        "only_target_selected_in_control_cohort": selected_qids == [TARGET_QID],
        "bounded_gets": all(
            result["get_requests"] <= MAX_GETS_PER_QID for result in results
        ),
        "get_only_allowed_paths": all(
            result["only_allowed_get_paths"] for result in results
        ),
        "target_selected": target["selected_id"] == TARGET_ID,
        "target_exact_bounded_markdown_row": (
            target["exact_served_receipt"]
            and target["complete_record_receipt"]
            and 0 < target["served_view_chars"] <= 1800
            and all(target["served_view_contains"].values())
        ),
        "target_lifecycle_authoritative": lifecycle["passed"],
        "target_lineage_and_identity_authoritative": target[
            "authoritative_identity_stamps_match"
        ],
        "target_absent_from_requests": target["target_id_absent_from_all_requests"],
        "catalog_scope_bypassed_inside_exact_document": catalog_scope_bypassed,
        "runtime_generic": (
            target["runtime_has_no_target_markers"]
            and target["query_facets_sha256_verified"]
            and target["catalogue_data_not_loaded"]
        ),
        "runtime_negative_controls": all(runtime_controls.values()),
        "live_sql_negative_controls": all(
            live_sql_controls["checks"].values()
        ),
        "no_model_dependency_in_exercised_runtime": (
            not provider_import_findings and not loaded_provider_modules
        ),
        "no_mutating_http_attempts": no_mutating_http_attempts,
        "rpc_function_bodies_read_only": rpc_bodies_read_only,
        "migration_history_reconciled": migration_reconciled,
    }
    verdict = "GO_MECHANISM" if all(checks.values()) else "NO_GO_MECHANISM"
    receipt = {
        "instrument": "s277_document_local_coverage_probe_v2",
        "verdict": verdict,
        "checks": checks,
        "target": target,
        "runtime_negative_controls": runtime_controls,
        "live_sql_negative_controls": live_sql_controls,
        "cohort": results,
        "applicability": {
            "selector_exercised_qids": selector_exercised_qids,
            "selector_exercised_count": len(selector_exercised_qids),
            "lifecycle_or_language_rejected_count": sum(
                result["document_local_status"]
                in {
                    "unverified_document_lineage",
                    "lineage_identity_drift",
                    "ambiguous_active_revision",
                    "incomplete_revision_chain",
                    "unsupported_document_language",
                    "no_authoritative_source_scope",
                }
                for result in results
            ),
        },
        "cost": {
            "model_calls": 0,
            "database_writes": 0,
            "database_get_requests": sum(
                result["get_requests"] for result in results
            )
            + live_sql_controls["get_requests"],
            "local_receipt_writes": 1,
            "evidence_basis": {
                "model": (
                    "no model-provider module loaded on the exercised path and "
                    "no provider import in the derived exercised module set or "
                    "the two separately enumerated integration surfaces; the "
                    "probe stops at the post-rerank coverage seam"
                ),
                "database": (
                    "all observed remote requests were GET; mutating HTTP verbs "
                    "were blocked and counted; all three sealed RPC bodies are STABLE "
                    "read-only SQL"
                ),
            },
            "elapsed_seconds": round(time.monotonic() - started, 3),
        },
        "inputs": {
            "freeze": str(FREEZE.relative_to(ROOT)).replace("\\", "/"),
            "freeze_sha256_lf": FREEZE_SHA256_LF,
            "prereg": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
            "implementation_sha256s": _sha256_manifest(
                reviewed_runtime_files
                + RUNTIME_CONFIG_FILES
                + RPC_MIGRATION_FILES
                + (
                    P1_ACL_MIGRATION,
                    Path(__file__).resolve(),
                    MIGRATION_RECONCILIATION_RECEIPT,
                )
            ),
            "migration_reconciliation_receipt": str(
                MIGRATION_RECONCILIATION_RECEIPT.relative_to(ROOT)
            ).replace("\\", "/"),
            "effective_non_secret_config": {
                "coverage_release_profile": os.getenv(
                    "COVERAGE_RELEASE_PROFILE", "off"
                ),
                "document_local_probe_override": True,
                "structural_probe_override": True,
                "supabase_project_ref": urlparse(
                    os.environ["SUPABASE_URL"]
                ).hostname.split(".")[0],
            },
            "catalogue_data": {
                "loaded": False,
                "reason": (
                    "catalogue scope is intentionally bypassed after exact "
                    "document/blob authority; eager code dependencies remain hashed"
                ),
            },
        },
        "limitations": [
            "Replays sealed reranker prefixes; it does not rerun live retrieval or reranking.",
            "Stops before generation and fact judging; it cannot change the 146/154 KPI.",
            "GO_MECHANISM is not a production release or P1 authorization.",
            "Only document scopes with complete authoritative lifecycle metadata are eligible.",
            "Snapshot v2 is ES-only because chunks_v2 uses spanish_unaccent FTS.",
            "Snapshot v2 serves only a validated complete bounded Markdown pipe row; other record formats fail closed.",
            "Control-cohort selector reach is reported separately from lifecycle-gate reach.",
            "The module manifest is derived from modules loaded by this exercised pre-generation path; two unexecuted integration surfaces are enumerated and hashed separately. It does not claim a whole-application closure.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run(args.env_file.resolve(), args.output.resolve())
    print(
        json.dumps(
            {
                "verdict": receipt["verdict"],
                "checks": receipt["checks"],
                "cost": receipt["cost"],
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if receipt["verdict"] == "GO_MECHANISM" else 2


if __name__ == "__main__":
    raise SystemExit(main())
