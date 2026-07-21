"""Fail-closed orchestration primitives for the S277 C1 P1 release gate.

The core remains dependency-injected and offline-testable.  The reviewed live
CLI composes it with the production RAG seam, scoped Anthropic/Voyage transport,
read-only Railway capture, a least-privilege PostgREST guard, and a separate
persistent PostgreSQL fence operator.  Paid execution still requires two CLI
opt-ins plus sealed release, authorization, manifest, fingerprint, and fence
evidence.

The authoritative model calls are journalled before delegation.  A call key is
never sent twice: a completed call is replayed only from its fsynced response,
a proven local pre-send failure remains terminal, and an interrupted reservation
is conservatively converted to UNKNOWN_BILLED_POST_SEND on reopen.
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import Any, Protocol


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if __name__ == "__main__":
    # Live adapters import the canonical package name lazily.  Alias this CLI
    # module first so P1Error and every runtime singleton keep one identity
    # instead of being loaded a second time as scripts.s277_c1_p1.
    sys.modules["scripts.s277_c1_p1"] = sys.modules[__name__]

CANONICAL_PREREG_PATH = ROOT / "evals/s277_c1_p1_prereg_v1.yaml"

RELEASE_CONFIG_SCHEMA = "s277_c1_p1_release_config_v1"
PREREG_SCHEMA = "s277_c1_p1_prereg_v1"
AUTHORIZATION_SCHEMA = "s277_c1_p1_paid_authorization_v1"
AUTHORIZATION_CLAIM_SCHEMA = "s277_c1_p1_authorization_claim_v1"
RUN_LEASE_SCHEMA = "s277_c1_p1_run_lease_v1"
RUN_GENESIS_SCHEMA = "s277_c1_p1_run_genesis_v1"
RUN_VALIDATION_SNAPSHOT_SCHEMA = "s277_c1_p1_run_validation_snapshot_v1"
FENCE_WATCH_SCHEMA = "s277_c1_p1_fence_watch_receipt_v1"
RUNTIME_LAYOUT_SCHEMA = "s277_c1_p1_runtime_layout_v1"
FINGERPRINT_SCHEMA = "s277_c1_p1_fingerprint_calibration_receipt_v1"
FENCE_OPEN_SCHEMA = "s277_c1_p1_fence_open_receipt_v1"
FENCE_CLOSE_SCHEMA = "s277_c1_p1_fence_close_receipt_v1"
REPLICA_RECEIPT_SCHEMA = "s277_c1_p1_replica_receipt_v1"
WAL_SCHEMA = "s277_c1_p1_call_wal_v1"
RESULT_SCHEMA = "s277_c1_p1_run_result_v1"
FINAL_RESULT_SCHEMA = "s277_c1_p1_final_result_v1"

FENCE_WATCH_EXACT_KEYS = frozenset(
    {
        "schema",
        "status",
        "phase",
        "call_key",
        "replica_key",
        "checked_at",
        "run_genesis_sha256",
        "release_config_sha256",
        "fingerprint_sha256",
        "fence_open_receipt_sha256",
        "backend_pid",
        "txid",
        "fence_owner",
        "deadline_at",
        "last_heartbeat_at",
        "heartbeat_max_age_seconds",
        "relations",
        "locks",
        "incompatible_waiters",
        "rpc_manifest_sha256",
        "physical_manifest_sha256",
    }
)

PROFILE = "coverage_c1_v1"
BOOTSTRAP_PROFILE = "off"
SEMANTIC_PROJECTION_SCHEMA = "s277_c1_semantic_effective_config_v1"
P1_TTL = timedelta(hours=6)
MAX_FENCE_WINDOW = timedelta(minutes=45)
FINGERPRINT_CEILING_MS = 120_000
FENCE_CLOCK_SKEW = timedelta(seconds=2)
MAX_RAILWAY_SNAPSHOT_AGE = timedelta(minutes=30)
MAX_RAILWAY_SNAPSHOT_FUTURE_SKEW = timedelta(seconds=60)
HARD_CAP_USD = Decimal("30.00")
ZERO = Decimal("0")

PROFILE_OWNED_LEGACY_FLAGS = (
    "POST_RERANK_COVERAGE",
    "STRUCTURAL_NEIGHBOR_COVERAGE",
    "COVERAGE_MANDATORY_CALLOUT",
    "MP_MANDATORY_VERB_TRIGGER",
)

TARGET_OFF_FLAGS = (
    "TABLE_PREAMBLE_CLOSURE",
    "CANONICAL_HYQ_COVERAGE",
    "COMPATIBILITY_BUNDLE_COVERAGE",
    "RERANK_POOL_COVERAGE",
    "STRUCTURAL_CASCADE_COVERAGE",
    "LOGICAL_RECORD_COVERAGE",
    "EVIDENCE_DERIVATION_OVERLAY",
    "DEDUP_REFERENCE_NAVIGATION",
    "R2_REPAIR_NAVIGATION",
    "STRUCTURAL_NEIGHBOR_SHADOW",
    "MP_HYBRID_DETECT",
    "MP_SERVED_BINDING",
    "MP_DEFLINE_EQ",
    "MP_STEM_BINDING",
    "MP_DISTINCTIVE_TOKEN",
)

ORTHOGONAL_PRESERVED_FLAGS = (
    "VISUAL_ASSETS_REGISTRY",
)

REPLICA_ORDER = (
    "hp017:r1",
    "hp017:r2",
    "hp017:r3",
    "cat001:r1",
    "cat001:r2",
    "cat017:r1",
    "cat017:r2",
    "cat018:r1",
    "cat018:r2",
    "cat019:r1",
    "cat019:r2",
    "hp002:r1",
    "hp002:r2",
    "hp003:r1",
    "hp003:r2",
    "hp005:r1",
    "hp005:r2",
    "hp011:r1",
    "hp011:r2",
    "hp012:r1",
    "hp012:r2",
    "hp013:r1",
    "hp013:r2",
    "hp014:r1",
    "hp014:r2",
    "hp018:r1",
    "hp018:r2",
)
CALL_OPERATIONS = ("embedding", "rerank", "synthesis")

BASE_FENCE_RELATIONS = (
    "public.chunks_v2",
    "public.chunks_v2_enunciados",
    "public.chunks_v2_hyq",
    "public.documents",
)
VISUAL_FENCE_RELATION = "public.document_visual_assets"
BASE_RPC_ALLOWLIST = (
    "match_chunks_v2",
    "search_chunks_text_v2",
    "match_chunks_v2_enunciados",
    "match_hyq",
)
BASE_REST_GET_ALLOWLIST = ("public.chunks_v2", "public.documents")
VISUAL_REST_GET_SURFACE = "public.document_visual_assets"
RERANK_INSTRUCTION = (
    "Ordena el pool por relevancia para la pregunta sin inventar evidencia; "
    "devuelve solo los identificadores en orden."
)
SYNTHESIS_SYSTEM_PROMPT = (
    "Responde la pregunta tecnica usando exclusivamente el contexto servido y "
    "conserva los localizadores de evidencia."
)
PROVIDER_TOKEN_OVERHEAD_RESERVE = 512
CALL_JOURNAL_FILENAME = "calls.jsonl"
AUTHORIZATION_LEDGER_DIRNAME = ".s277_c1_p1_authorization_claims_v1"
RUN_LEASE_DIRNAME = "leases"

PRODUCT_ADAPTER_IMPLEMENTATION_PATH = "scripts/s277_c1_p1_product_adapter.py"
EXECUTION_IMPLEMENTATION_PATH = "scripts/s277_c1_p1_execute.py"
FENCE_OPERATOR_IMPLEMENTATION_PATH = "scripts/s277_c1_p1_fence_operator.py"
LIVE_MANIFEST_IMPLEMENTATION_PATH = "scripts/s277_c1_p1_live_manifest.py"
LIVE_RECEIPTS_IMPLEMENTATION_PATH = "scripts/s277_c1_p1_live_receipts.py"
POSTGREST_GUARD_IMPLEMENTATION_PATH = "scripts/s277_c1_p1_postgrest_guard.py"
RELEASE_CONFIG_IMPLEMENTATION_PATH = "scripts/s277_c1_p1_release_config.py"

# This is the exact local Python implementation surface imported by the P1
# runner/scorer and by the production RAG entrypoints.  Keep the list explicit:
# it is embedded in run genesis and old runs must fail closed if any member
# changes.  ``implementation_dependency_closure`` below independently derives
# the transitive top-level import closure and rejects omissions.
REQUIRED_IMPLEMENTATION_HASHES = (
    "scripts/catalog_store.py",
    "scripts/s270_etapa2_probe.py",
    "scripts/s277_c1_p1.py",
    EXECUTION_IMPLEMENTATION_PATH,
    FENCE_OPERATOR_IMPLEMENTATION_PATH,
    LIVE_MANIFEST_IMPLEMENTATION_PATH,
    LIVE_RECEIPTS_IMPLEMENTATION_PATH,
    POSTGREST_GUARD_IMPLEMENTATION_PATH,
    PRODUCT_ADAPTER_IMPLEMENTATION_PATH,
    RELEASE_CONFIG_IMPLEMENTATION_PATH,
    "scripts/s277_c1_p1_scorer.py",
    "src/__init__.py",
    "src/bot/__init__.py",
    "src/bot/response_formatter.py",
    "src/config.py",
    "src/ingestion/__init__.py",
    "src/ingestion/embedder.py",
    "src/rag/__init__.py",
    "src/rag/answer_obligation_contract.py",
    "src/rag/answer_planner.py",
    "src/rag/catalog.py",
    "src/rag/catalog_resolver.py",
    "src/rag/compatibility_bundle_coverage.py",
    "src/rag/coverage_runtime.py",
    "src/rag/doc_scoped_hyq_coverage.py",
    "src/rag/evidence_coverage.py",
    "src/rag/evidence_derivation.py",
    "src/rag/evidence_window.py",
    "src/rag/generator.py",
    "src/rag/hyde.py",
    "src/rag/mp_lexicon.py",
    "src/rag/must_preserve.py",
    "src/rag/post_rerank_coverage.py",
    "src/rag/query_facets.py",
    "src/rag/rerank_pool_coverage.py",
    "src/rag/reranker.py",
    "src/rag/retriever.py",
    "src/rag/runtime_trace.py",
    "src/rag/series_registry.py",
    "src/rag/serving_pipeline.py",
    "src/rag/source_identity_attestation.py",
    "src/rag/structural_neighbor_coverage.py",
    "src/rag/structural_neighbor_shadow.py",
    "src/rag/structured_claims.py",
    "src/rag/table_preamble_closure.py",
    "src/rag/technical_obligations.py",
    "src/rag/toc_detection.py",
    "src/rag/visual_assets.py",
    "src/reingest/__init__.py",
    "src/reingest/embed.py",
    "src/release_profiles.py",
)

# Roots model the three executable trust domains: orchestration, scoring and
# product behavior.  Imports inside function bodies are not executed at module
# import, so the few P1-reachable dynamic imports are declared separately.
IMPLEMENTATION_IMPORT_ROOTS = (
    "scripts/s277_c1_p1.py",
    EXECUTION_IMPLEMENTATION_PATH,
    FENCE_OPERATOR_IMPLEMENTATION_PATH,
    LIVE_MANIFEST_IMPLEMENTATION_PATH,
    LIVE_RECEIPTS_IMPLEMENTATION_PATH,
    POSTGREST_GUARD_IMPLEMENTATION_PATH,
    PRODUCT_ADAPTER_IMPLEMENTATION_PATH,
    RELEASE_CONFIG_IMPLEMENTATION_PATH,
    "scripts/s277_c1_p1_scorer.py",
    "src/bot/response_formatter.py",
    "src/config.py",
    "src/rag/generator.py",
    "src/rag/reranker.py",
    "src/rag/retriever.py",
    "src/rag/runtime_trace.py",
    "src/rag/serving_pipeline.py",
)
IMPLEMENTATION_DYNAMIC_IMPORTS = {
    "scripts/s277_c1_p1.py": (
        EXECUTION_IMPLEMENTATION_PATH,
        "scripts/s277_c1_p1_scorer.py",
        "src/bot/response_formatter.py",
        "src/rag/retriever.py",
    ),
    PRODUCT_ADAPTER_IMPLEMENTATION_PATH: (
        "src/bot/response_formatter.py",
        "src/rag/generator.py",
        "src/rag/reranker.py",
        "src/rag/retriever.py",
        "src/rag/serving_pipeline.py",
        "src/rag/structural_neighbor_shadow.py",
        "src/rag/visual_assets.py",
        "src/reingest/embed.py",
    ),
    "scripts/s277_c1_p1_scorer.py": (
        "scripts/s270_etapa2_probe.py",
        "src/rag/answer_planner.py",
        "src/rag/post_rerank_coverage.py",
    ),
    "scripts/s270_etapa2_probe.py": ("src/rag/must_preserve.py",),
    "src/ingestion/embedder.py": ("src/reingest/embed.py",),
    "src/rag/catalog_resolver.py": ("scripts/catalog_store.py",),
    "src/rag/must_preserve.py": (
        "src/config.py",
        "src/rag/catalog_resolver.py",
        "src/rag/post_rerank_coverage.py",
    ),
    "src/rag/retriever.py": ("src/rag/catalog_resolver.py",),
    "src/rag/runtime_trace.py": ("src/rag/post_rerank_coverage.py",),
}

EXPECTED_FUNCTION_AUDIT_SHA256_LF = (
    "285dd74a1463bb71a21ab9bfb5ea4053789d606ede9b90b640c14008c676dbda"
)
EXPECTED_FUNCTION_DEFINITION_SHA256 = (
    "1f280e0852158b63501aad2843a7e946ab9fac5a4c64a17851d6d63ed0e8ebca"
)

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SECRET_NAME = re.compile(
    r"(?:^|_)(?:API_?KEY|TOKEN|PASSWORD|SECRET|PRIVATE_?KEY|SERVICE_?KEY)(?:$|_)",
    re.IGNORECASE,
)
_SAFE_NON_SECRET_NAMES = {"MP_DISTINCTIVE_TOKEN", "LLM_MAX_TOKENS"}
_SAFE_SECRET_HASH_NAMES = {"api_key_sha256"}
_MODEL_EXTRACTION_CACHE: dict[str, list[dict[str, Any]]] = {}


class P1Error(RuntimeError):
    """A classified, fail-closed P1 stop."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class NoRetryError(P1Error):
    pass


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise P1Error(code, message)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def json_safe_deep_copy_mapping(
    value: Mapping[str, Any], *, field: str
) -> dict[str, Any]:
    """Detach a preflight input through its exact JSON representation."""

    try:
        copied = json.loads(canonical_json_bytes(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise P1Error("HOLD_PREFLIGHT_SNAPSHOT", field) from exc
    _require(
        isinstance(copied, dict) and copied == value,
        "HOLD_PREFLIGHT_SNAPSHOT",
        f"{field} is not exactly JSON-safe",
    )
    return copied


def expected_surface(
    target_semantic_config: Mapping[str, Any],
) -> dict[str, list[str]]:
    generation = target_semantic_config.get("generation")
    _require(isinstance(generation, Mapping), "HOLD_CONFIG_DRIFT", "generation surface")
    visual = generation.get("visual_assets_registry")
    _require(type(visual) is bool, "HOLD_CONFIG_DRIFT", "visual surface")
    relations = list(BASE_FENCE_RELATIONS)
    rest_get = list(BASE_REST_GET_ALLOWLIST)
    if visual:
        relations.append(VISUAL_FENCE_RELATION)
        rest_get.append(VISUAL_REST_GET_SURFACE)
    return {
        "relations": relations,
        "rpc_allowlist": list(BASE_RPC_ALLOWLIST),
        "rest_get_allowlist": rest_get,
    }


def expected_declared_rpc_surface_sha256(
    target_semantic_config: Mapping[str, Any],
) -> str:
    """Hash the declared RPC/REST names, not any observed live implementation."""

    surface = expected_surface(target_semantic_config)
    return sha256_json(
        {
            "schema": "s277_c1_p1_rpc_surface_v1",
            "rpc_allowlist": surface["rpc_allowlist"],
            "rest_get_allowlist": surface["rest_get_allowlist"],
            "corpus_fingerprint_function_definition_sha256": (
                EXPECTED_FUNCTION_DEFINITION_SHA256
            ),
        }
    )


def expected_declared_lock_surface_sha256(
    target_semantic_config: Mapping[str, Any],
) -> str:
    """Hash declared relations/lock mode, not live indexes or configuration."""

    surface = expected_surface(target_semantic_config)
    return sha256_json(
        {
            "schema": "s277_c1_p1_physical_surface_v1",
            "relations": surface["relations"],
            "lock_mode": "ShareLock",
        }
    )


def artifact_identity_sha256(run_id: str, artifact_root: Path) -> str:
    """Bind an authorization to one resolved physical artifact directory."""

    _require(
        isinstance(run_id, str) and bool(re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", run_id)),
        "HOLD_RUN_IDENTITY",
        "invalid run_id",
    )
    return sha256_json(
        {
            "run_id": run_id,
            "artifact_root": os.path.normcase(str(artifact_root.resolve())),
        }
    )


def _resolved_path_sha256(path: Path) -> str:
    return hashlib.sha256(
        os.path.normcase(str(path.resolve())).encode("utf-8")
    ).hexdigest()


def canonical_authorization_claim_root(artifact_root: Path) -> Path:
    return artifact_root.resolve().parent / AUTHORIZATION_LEDGER_DIRNAME


def canonical_run_lease_path(artifact_root: Path) -> Path:
    root = artifact_root.resolve()
    filename = f"{_resolved_path_sha256(root)}.json"
    return canonical_authorization_claim_root(root) / RUN_LEASE_DIRNAME / filename


def canonical_runtime_layout(artifact_root: Path) -> dict[str, Any]:
    root = artifact_root.resolve()
    journal = root / CALL_JOURNAL_FILENAME
    journal_genesis = root / f"{CALL_JOURNAL_FILENAME}.genesis.json"
    journal_claims = root / f"{CALL_JOURNAL_FILENAME}.claims"
    artifact_genesis = root / "run_genesis.json"
    authorization_ledger = canonical_authorization_claim_root(root)
    run_lease = canonical_run_lease_path(root)
    return {
        "schema": RUNTIME_LAYOUT_SCHEMA,
        "artifact_root_sha256": _resolved_path_sha256(root),
        "call_journal": {
            "relative_path": CALL_JOURNAL_FILENAME,
            "path_sha256": _resolved_path_sha256(journal),
        },
        "call_journal_genesis": {
            "relative_path": f"{CALL_JOURNAL_FILENAME}.genesis.json",
            "path_sha256": _resolved_path_sha256(journal_genesis),
        },
        "call_claims": {
            "relative_path": f"{CALL_JOURNAL_FILENAME}.claims",
            "path_sha256": _resolved_path_sha256(journal_claims),
        },
        "artifact_genesis": {
            "relative_path": "run_genesis.json",
            "path_sha256": _resolved_path_sha256(artifact_genesis),
        },
        "authorization_ledger": {
            "derivation": f"artifact_root.parent/{AUTHORIZATION_LEDGER_DIRNAME}",
            "path_sha256": _resolved_path_sha256(authorization_ledger),
        },
        "run_lease": {
            "derivation": (
                "authorization_ledger/leases/"
                "{sha256(normcase(resolved_artifact_root))}.json"
            ),
            "path_sha256": _resolved_path_sha256(run_lease),
        },
    }


def physical_input_token_upper_bound(payload: Mapping[str, Any]) -> int:
    """Conservative byte bound plus fixed provider Messages framing reserve."""

    return len(canonical_json_bytes(payload)) + PROVIDER_TOKEN_OVERHEAD_RESERVE


def build_operation_payload(
    *,
    operation: str,
    model: str,
    question: str,
    lineage_payload: Any,
    max_output_tokens: int,
) -> dict[str, Any]:
    """Build the canonical provider-intent payload sealed by the offline core.

    The eventual wire bytes remain an adapter/parity concern; this function
    deliberately makes no claim that its canonical JSON is the provider SDK's
    transport serialization.
    """

    _require(operation in CALL_OPERATIONS, "HOLD_UNREGISTERED_CALL", operation)
    _require(isinstance(question, str) and bool(question), "HOLD_ENVELOPE_DRIFT", "question")
    if operation == "embedding":
        return {"model": model, "input_type": "query", "texts": [question]}
    prompt = {
        "question": question,
        "pool" if operation == "rerank" else "served_context": lineage_payload,
    }
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_output_tokens,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": canonical_json_bytes(prompt).decode("utf-8"),
            }
        ],
    }
    if operation == "rerank":
        payload["system"] = RERANK_INSTRUCTION
    else:
        payload["system"] = SYNTHESIS_SYSTEM_PROMPT
    return payload


def sha256_file(path: Path, *, lf_normalized: bool = False) -> str:
    raw = path.read_bytes()
    if lf_normalized:
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _decimal(value: Any, *, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise P1Error("HOLD_INVALID_COST", f"{field} is not decimal") from exc
    _require(result.is_finite() and result >= ZERO, "HOLD_INVALID_COST", field)
    return result


def _money(value: Decimal) -> str:
    return format(value, "f")


def _parse_time(value: Any, *, field: str) -> datetime:
    _require(isinstance(value, str) and value, "HOLD_INVALID_TIME", field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise P1Error("HOLD_INVALID_TIME", field) from exc
    _require(parsed.tzinfo is not None, "HOLD_INVALID_TIME", f"{field} lacks timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _fsync_parent(_path: Path) -> None:
    """Best-effort directory fsync; Windows does not expose portable dir fsync."""

    if os.name == "nt":
        return
    descriptor = os.open(_path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_json_exclusive(path: Path, value: Any) -> str:
    """Write a canonical JSON artifact once and make the file durable."""

    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value) + b"\n"
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_parent(path.parent)
    return hashlib.sha256(raw).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P1Error("HOLD_INVALID_ARTIFACT", str(path)) from exc
    _require(isinstance(value, dict), "HOLD_INVALID_ARTIFACT", str(path))
    return value


def load_data_object(path: Path) -> dict[str, Any]:
    """Load JSON or YAML without evaluating constructors."""

    if path.suffix.casefold() in {".yaml", ".yml"}:
        try:
            import yaml

            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise P1Error("HOLD_INVALID_ARTIFACT", str(path)) from exc
        _require(isinstance(value, dict), "HOLD_INVALID_ARTIFACT", str(path))
        return value
    return load_json_object(path)


@dataclass(frozen=True)
class Replica:
    qid: str
    replica_id: str

    @property
    def key(self) -> str:
        return f"{self.qid}:{self.replica_id}"


REPLICAS = tuple(Replica(*item.split(":")) for item in REPLICA_ORDER)
REPLICA_PLAN_SHA256 = sha256_json(list(REPLICA_ORDER))


def expected_call_keys() -> tuple[str, ...]:
    return tuple(
        f"{replica.key}:{operation}"
        for replica in REPLICAS
        for operation in CALL_OPERATIONS
    )


CALL_PLAN_SHA256 = sha256_json(list(expected_call_keys()))


def _assert_no_secret_material(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            name = str(key)
            if name == "secret_fields_present":
                _require(
                    child is False,
                    "HOLD_SECRET_IN_SAFE_ARTIFACT",
                    f"{path}.{name} must be false",
                )
                continue
            if name in _SAFE_SECRET_HASH_NAMES:
                _require(
                    child is None
                    or (
                        isinstance(child, str)
                        and _HEX64.fullmatch(child) is not None
                    ),
                    "HOLD_SECRET_IN_SAFE_ARTIFACT",
                    f"{path}.{name} must be null or a lowercase SHA-256",
                )
                continue
            _require(
                name in _SAFE_NON_SECRET_NAMES or not _SECRET_NAME.search(name),
                "HOLD_SECRET_IN_SAFE_ARTIFACT",
                f"secret-like field at {path}.{name}",
            )
            _assert_no_secret_material(child, f"{path}.{name}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_secret_material(child, f"{path}[{index}]")


def apply_planned_bootstrap_patch(
    live_snapshot: Mapping[str, str], patch: Mapping[str, Any]
) -> dict[str, str]:
    """Apply the one permitted Railway bootstrap transformation in memory only."""

    _require(
        set(patch) == {"delete", "set"},
        "HOLD_PATCH_DRIFT",
        "planned patch must contain only delete and set",
    )
    unset = patch.get("delete")
    set_values = patch.get("set")
    _require(isinstance(unset, list), "HOLD_PATCH_DRIFT", "unset must be a list")
    _require(
        len(unset) == len(set(unset)) and set(unset) == set(PROFILE_OWNED_LEGACY_FLAGS),
        "HOLD_PATCH_DRIFT",
        "patch must remove exactly the four profile-owned legacy flags",
    )
    _require(
        set_values == {"COVERAGE_RELEASE_PROFILE": BOOTSTRAP_PROFILE},
        "HOLD_PATCH_DRIFT",
        "patch may only set the bootstrap release profile",
    )
    output = {str(key): str(value) for key, value in live_snapshot.items()}
    for name in unset:
        output.pop(name, None)
    output.update(set_values)
    return output


def _exact_env(
    raw_env: Mapping[str, Any],
    name: str,
    *,
    expected: str | None = None,
    default: str | None = None,
) -> str:
    raw = raw_env.get(name, default)
    _require(isinstance(raw, str), "HOLD_CONFIG_DRIFT", f"{name} must be a string")
    if expected is not None:
        _require(raw == expected, "HOLD_CONFIG_DRIFT", f"{name} must equal {expected!r}")
    return raw


def derive_semantic_config(
    raw_env: Mapping[str, Any], *, release_profile: str
) -> dict[str, Any]:
    """Resolve the exact effective behavior P1 measures from the safe env."""

    _require(
        release_profile in {BOOTSTRAP_PROFILE, PROFILE},
        "HOLD_CONFIG_DRIFT",
        "semantic release profile",
    )
    visual = _exact_env(raw_env, "VISUAL_ASSETS_REGISTRY")
    _require(visual in {"on", "off"}, "HOLD_CONFIG_DRIFT", "visual assets")
    rerank_top_k = _exact_env(raw_env, "RERANK_TOP_K", expected="10")
    llm_max_tokens = _exact_env(raw_env, "LLM_MAX_TOKENS", expected="3500")
    preview_chars = _exact_env(
        raw_env, "RERANK_PREVIEW_CHARS", expected="800", default="800"
    )
    merge_strategy = _exact_env(
        raw_env, "MERGE_STRATEGY", expected="stamps", default="stamps"
    )
    reranker_backend = _exact_env(
        raw_env, "RERANKER_BACKEND", expected="llm", default="llm"
    )
    _exact_env(raw_env, "CHUNKS_TABLE", expected="chunks_v2")
    _exact_env(raw_env, "HYDE_ENABLED", expected="false")
    _exact_env(raw_env, "ENUNCIADOS_MULTIVECTOR", expected="on")
    _exact_env(raw_env, "HYQ_TABLE", expected="on")
    hyq_pilot = _exact_env(raw_env, "HYQ_PILOT_FILE", expected="", default="")
    identity_resolve = _exact_env(raw_env, "IDENTITY_RESOLVE", expected="on")
    identity_policy = _exact_env(
        raw_env, "IDENTITY_RESOLVE_POLICY", expected="add"
    )
    prompt_variant = _exact_env(
        raw_env, "GENERATOR_PROMPT_VARIANT", expected="fidelity"
    )
    _exact_env(raw_env, "GENERATOR_SELECTION_BLOCK", expected="on")
    _exact_env(raw_env, "MUST_PRESERVE_CONTRACT", expected="on")
    enabled = release_profile == PROFILE
    return {
        "schema": SEMANTIC_PROJECTION_SCHEMA,
        "corpus": {"chunks_table": "chunks_v2"},
        "retrieval": {
            "retrieval_top_k": 50,
            "rerank_top_k": int(rerank_top_k),
            "reranker_backend": reranker_backend,
            "reranker_model": "claude-sonnet-4-6",
            "rerank_preview_chars": int(preview_chars),
            "merge_strategy": merge_strategy,
            "hyde_enabled": False,
            "enunciados_multivector": True,
            "hyq_table": True,
            "hyq_pilot_file": hyq_pilot,
            "identity_resolve": identity_resolve == "on",
            "identity_resolve_policy": identity_policy,
        },
        "generation": {
            "model": "claude-sonnet-4-6",
            "max_tokens": int(llm_max_tokens),
            "temperature": 0,
            "prompt_cache": False,
            "prompt_variant": prompt_variant,
            "selection_block": True,
            "must_preserve_contract": True,
            "visual_assets_registry": visual == "on",
        },
        "embedding": {"model": "voyage-4-large"},
        "coverage": {
            "release_profile": release_profile,
            "post_rerank_coverage": enabled,
            "structural_neighbor_coverage": enabled,
            "mandatory_callout": enabled,
            "mandatory_verb_trigger": enabled,
        },
    }


def derive_release_states(
    live_snapshot: Mapping[str, str], patch: Mapping[str, Any]
) -> dict[str, Any]:
    bootstrap = apply_planned_bootstrap_patch(live_snapshot, patch)
    target = dict(bootstrap)
    target["COVERAGE_RELEASE_PROFILE"] = PROFILE
    for name in ORTHOGONAL_PRESERVED_FLAGS:
        live_value = live_snapshot.get(name)
        _require(
            isinstance(live_value, str) and live_value in {"on", "off"},
            "HOLD_CONFIG_DRIFT",
            f"{name} must be the exact literal on or off",
        )
        _require(
            bootstrap.get(name) == live_value and target.get(name) == live_value,
            "HOLD_CONFIG_DRIFT",
            f"{name} was not preserved byte-exact",
        )
    for state in (bootstrap, target):
        _require(
            not any(name in state for name in PROFILE_OWNED_LEGACY_FLAGS),
            "HOLD_CONFIG_DRIFT",
            "profile-owned legacy flags remain after patch",
        )
    common = {
        key: value
        for key, value in bootstrap.items()
        if key != "COVERAGE_RELEASE_PROFILE"
    }
    bootstrap_effective = dict(bootstrap)
    bootstrap_effective.update({name: "off" for name in PROFILE_OWNED_LEGACY_FLAGS})
    target_effective = dict(target)
    target_effective.update({name: "on" for name in PROFILE_OWNED_LEGACY_FLAGS})
    bootstrap_semantic = derive_semantic_config(
        bootstrap, release_profile=BOOTSTRAP_PROFILE
    )
    target_semantic = derive_semantic_config(target, release_profile=PROFILE)
    return {
        "bootstrap_profile": BOOTSTRAP_PROFILE,
        "p1_target_profile": PROFILE,
        "common_config_sha256": sha256_json(common),
        "bootstrap_effective_config_sha256": sha256_json(bootstrap_effective),
        "target_effective_config_sha256": sha256_json(target_effective),
        "semantic_projection_schema": SEMANTIC_PROJECTION_SCHEMA,
        "bootstrap_semantic_config": bootstrap_semantic,
        "target_semantic_config": target_semantic,
        "bootstrap_semantic_config_sha256": sha256_json(bootstrap_semantic),
        "target_semantic_config_sha256": sha256_json(target_semantic),
        "raw_allowlisted_env": bootstrap,
    }


@dataclass(frozen=True)
class RuntimeIdentity:
    commit_sha: str
    tree_sha: str
    detached: bool
    clean: bool


def inspect_runtime_identity(repo: Path = ROOT) -> RuntimeIdentity:
    def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=repo,
            check=check,
            capture_output=True,
            text=True,
        )

    commit = git("rev-parse", "HEAD").stdout.strip()
    tree = git("rev-parse", "HEAD^{tree}").stdout.strip()
    symbolic = git("symbolic-ref", "-q", "HEAD", check=False)
    status = git("status", "--porcelain=v1", "--untracked-files=all").stdout
    return RuntimeIdentity(
        commit_sha=commit,
        tree_sha=tree,
        detached=symbolic.returncode != 0,
        clean=not bool(status.strip()),
    )


def runtime_identity_payload(runtime: RuntimeIdentity) -> dict[str, Any]:
    _require(
        isinstance(runtime, RuntimeIdentity),
        "HOLD_RUNTIME_IDENTITY_DRIFT",
        "runtime inspector returned an invalid identity",
    )
    return {
        "commit_sha": runtime.commit_sha,
        "tree_sha": runtime.tree_sha,
        "detached": runtime.detached,
        "clean": runtime.clean,
    }


def inspect_and_assert_runtime_identity(
    inspector: Callable[[], RuntimeIdentity],
    expected: RuntimeIdentity,
) -> RuntimeIdentity:
    try:
        observed = inspector()
    except Exception as exc:
        raise P1Error(
            "HOLD_RUNTIME_INSPECTION_FAILED",
            f"runtime inspection failed: {type(exc).__name__}",
        ) from exc
    _require(
        runtime_identity_payload(observed) == runtime_identity_payload(expected),
        "HOLD_RUNTIME_IDENTITY_DRIFT",
        "runtime identity differs from the sealed preflight identity",
    )
    return observed


def _strict_on(raw: Any, *, field: str) -> bool:
    value = str(raw if raw is not None else "off").strip().casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"", "0", "false", "no", "off"}:
        return False
    raise P1Error("HOLD_CONFIG_DRIFT", f"invalid on/off value for {field}")


def derive_rpc_allowlist(raw_env: Mapping[str, Any]) -> list[str]:
    """Derive the exact PostgREST RPC surface from the sealed retriever flags."""

    expected = ["match_chunks_v2", "search_chunks_text_v2"]
    if _strict_on(raw_env.get("ENUNCIADOS_MULTIVECTOR"), field="ENUNCIADOS_MULTIVECTOR"):
        expected.append("match_chunks_v2_enunciados")
    if _strict_on(raw_env.get("HYQ_TABLE"), field="HYQ_TABLE"):
        expected.append("match_hyq")
    _require(
        not bool(str(raw_env.get("HYQ_PILOT_FILE", "")).strip()),
        "HOLD_CONFIG_DRIFT",
        "HYQ_PILOT_FILE is not an allowed release backend",
    )
    return expected


class _TopLevelImportVisitor(ast.NodeVisitor):
    """Collect imports whose statements execute while a module is imported."""

    def __init__(self) -> None:
        self.imports: list[ast.Import | ast.ImportFrom] = []

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        self.imports.append(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        self.imports.append(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        # Function bodies are covered by IMPLEMENTATION_DYNAMIC_IMPORTS only
        # when the P1 path actually invokes them.
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        return None

    def visit_Lambda(self, node: ast.Lambda) -> None:  # noqa: N802
        return None


def _implementation_module_name(relative: str) -> str:
    parts = relative.replace("\\", "/").split("/")
    _require(
        len(parts) >= 2 and parts[0] in {"scripts", "src"},
        "HOLD_IMPLEMENTATION_DRIFT",
        f"non-local implementation path: {relative}",
    )
    filename = parts[-1]
    _require(
        filename.endswith(".py"),
        "HOLD_IMPLEMENTATION_DRIFT",
        f"non-Python implementation path: {relative}",
    )
    if filename == "__init__.py":
        return ".".join(parts[:-1])
    return ".".join((*parts[:-1], filename[:-3]))


def _implementation_module_index(root: Path) -> dict[str, str]:
    """Index local modules without importing product code or consulting git."""

    index: dict[str, str] = {}
    for dirname in ("scripts", "src"):
        base = root / dirname
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            module = _implementation_module_name(relative)
            index[module] = relative
            # catalog_resolver deliberately imports catalog_store after adding
            # scripts/ to sys.path, so mirror that legitimate top-level alias.
            if dirname == "scripts" and path.parent == base:
                index.setdefault(path.stem, relative)
    return index


def _implementation_package_initializers(root: Path, relative: str) -> set[str]:
    output: set[str] = set()
    current = (root / relative).parent
    while current != root and root in current.parents:
        init_path = current / "__init__.py"
        if init_path.is_file():
            output.add(init_path.relative_to(root).as_posix())
        current = current.parent
    return output


def _resolve_static_local_imports(
    relative: str,
    node: ast.Import | ast.ImportFrom,
    module_index: Mapping[str, str],
) -> set[str]:
    candidates: list[str] = []
    if isinstance(node, ast.Import):
        candidates.extend(alias.name for alias in node.names)
    else:
        current_module = _implementation_module_name(relative)
        if relative.endswith("/__init__.py"):
            current_package = current_module
        else:
            current_package = current_module.rpartition(".")[0]
        if node.level:
            package_parts = current_package.split(".") if current_package else []
            ascend = node.level - 1
            if ascend > len(package_parts):
                return set()
            if ascend:
                package_parts = package_parts[:-ascend]
            base = ".".join(
                (*package_parts, *((node.module or "").split(".") if node.module else ()))
            )
        else:
            base = node.module or ""
        if base:
            candidates.append(base)
        candidates.extend(
            ".".join(part for part in (base, alias.name) if part)
            for alias in node.names
            if alias.name != "*"
        )
    return {
        module_index[candidate]
        for candidate in candidates
        if candidate in module_index
    }


def implementation_dependency_closure(root: Path | None = None) -> tuple[str, ...]:
    """Derive the exact local import closure required by the P1 product path.

    Top-level imports are read from AST without executing them.  Reachable
    function-local imports are a short reviewed allowlist above.  Any new local
    import therefore changes this closure and blocks an old or incomplete
    implementation manifest.
    """

    resolved_root = (root or ROOT).resolve()
    module_index = _implementation_module_index(resolved_root)
    pending = list(IMPLEMENTATION_IMPORT_ROOTS)
    closure: set[str] = set()
    while pending:
        relative = pending.pop()
        if relative in closure:
            continue
        path = (resolved_root / relative).resolve()
        _require(
            resolved_root in path.parents and path.is_file(),
            "HOLD_IMPLEMENTATION_DRIFT",
            f"missing implementation dependency: {relative}",
        )
        closure.add(relative)
        pending.extend(
            dependency
            for dependency in _implementation_package_initializers(
                resolved_root, relative
            )
            if dependency not in closure
        )
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=relative)
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise P1Error(
                "HOLD_IMPLEMENTATION_DRIFT",
                f"cannot parse implementation dependency {relative}: {type(exc).__name__}",
            ) from exc
        visitor = _TopLevelImportVisitor()
        visitor.visit(tree)
        for import_node in visitor.imports:
            pending.extend(
                dependency
                for dependency in _resolve_static_local_imports(
                    relative, import_node, module_index
                )
                if dependency not in closure
            )
        pending.extend(
            dependency
            for dependency in IMPLEMENTATION_DYNAMIC_IMPORTS.get(relative, ())
            if dependency not in closure
        )
    return tuple(sorted(closure))


def loaded_local_implementation_paths(root: Path | None = None) -> tuple[str, ...]:
    """Return local Python source files loaded in the current interpreter.

    Product entrypoint tests call this from a fresh subprocess, avoiding test
    process contamination while checking real import resolution in addition to
    the static AST closure.
    """

    resolved_root = (root or ROOT).resolve()
    loaded: set[str] = set()
    for module in tuple(sys.modules.values()):
        raw_path = getattr(module, "__file__", None)
        if not isinstance(raw_path, str) or not raw_path:
            continue
        path = Path(raw_path)
        if path.suffix in {".pyc", ".pyo"} and path.parent.name == "__pycache__":
            stem = path.name.split(".", 1)[0]
            path = path.parent.parent / f"{stem}.py"
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved_root not in resolved.parents or resolved.suffix != ".py":
            continue
        relative = resolved.relative_to(resolved_root).as_posix()
        if relative.startswith(("scripts/", "src/")):
            loaded.add(relative)
    return tuple(sorted(loaded))


def verify_loaded_implementation_closure(
    manifest: Mapping[str, Any],
    *,
    loaded_paths: Sequence[str] | None = None,
) -> None:
    """Reject a clean-process product import that escaped the sealed manifest."""

    observed = set(
        loaded_local_implementation_paths()
        if loaded_paths is None
        else loaded_paths
    )
    escaped = sorted(observed - set(manifest))
    _require(
        not escaped,
        "HOLD_IMPLEMENTATION_DRIFT",
        f"loaded local implementation outside manifest: {escaped}",
    )


def verify_implementation_hashes(manifest: Mapping[str, Any]) -> None:
    _require(isinstance(manifest, Mapping), "HOLD_IMPLEMENTATION_DRIFT", "manifest")
    required = set(REQUIRED_IMPLEMENTATION_HASHES)
    _require(
        set(manifest) == required,
        "HOLD_IMPLEMENTATION_DRIFT",
        "implementation manifest path set",
    )
    closure = set(implementation_dependency_closure())
    _require(
        closure == required,
        "HOLD_IMPLEMENTATION_DRIFT",
        "implementation dependency closure mismatch: "
        f"unsealed={sorted(closure - required)}, unreachable={sorted(required - closure)}",
    )
    for relative, expected in manifest.items():
        _require(isinstance(relative, str) and relative, "HOLD_IMPLEMENTATION_DRIFT", "path")
        _require(isinstance(expected, str) and bool(_HEX64.fullmatch(expected)), "HOLD_IMPLEMENTATION_DRIFT", relative)
        path = (ROOT / relative).resolve()
        _require(ROOT in path.parents and path.is_file(), "HOLD_IMPLEMENTATION_DRIFT", relative)
        _require(
            sha256_file(path, lf_normalized=True) == expected,
            "HOLD_IMPLEMENTATION_DRIFT",
            f"hash mismatch: {relative}",
        )


def verify_release_config(
    config: Mapping[str, Any],
    runtime: RuntimeIdentity,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    _assert_no_secret_material(config)
    _require(config.get("schema_version") == RELEASE_CONFIG_SCHEMA, "HOLD_CONFIG_SCHEMA", "schema")
    schema_path = ROOT / "evals/s277_c1_p1_release_config_schema_v1.json"
    _require(schema_path.is_file(), "HOLD_CONFIG_SCHEMA", "release config schema missing")
    try:
        import jsonschema

        jsonschema.validate(dict(config), load_json_object(schema_path))
    except jsonschema.ValidationError as exc:
        raise P1Error("HOLD_CONFIG_SCHEMA", exc.message) from exc
    candidate = config.get("candidate")
    _require(isinstance(candidate, Mapping), "HOLD_CONFIG_SCHEMA", "candidate")
    expected_commit = candidate.get("tested_commit_sha")
    expected_tree = candidate.get("tested_tree_sha")
    _require(
        isinstance(expected_commit, str) and bool(_HEX40.fullmatch(expected_commit)),
        "HOLD_CODE_IDENTITY",
        "tested_commit_sha",
    )
    _require(
        isinstance(expected_tree, str) and bool(_HEX40.fullmatch(expected_tree)),
        "HOLD_CODE_IDENTITY",
        "tested_tree_sha",
    )
    _require(runtime.detached, "HOLD_WORKTREE_NOT_DETACHED", "P1 requires detached HEAD")
    _require(runtime.clean, "HOLD_WORKTREE_DIRTY", "P1 requires a clean worktree")
    _require(runtime.commit_sha == expected_commit, "HOLD_CODE_IDENTITY", "commit drift")
    _require(runtime.tree_sha == expected_tree, "HOLD_CODE_IDENTITY", "tree drift")
    _require(candidate.get("bot_version") == expected_commit, "HOLD_CODE_IDENTITY", "bot_version drift")

    railway = config.get("railway")
    _require(isinstance(railway, Mapping), "HOLD_CONFIG_SCHEMA", "railway")
    observed_now = now or datetime.now(timezone.utc)
    verify_railway_snapshot_freshness(railway, now=observed_now)
    snapshot = railway.get("live_snapshot")
    patch = railway.get("planned_bootstrap_patch")
    _require(isinstance(snapshot, Mapping), "HOLD_CONFIG_SCHEMA", "live_snapshot")
    _require(isinstance(patch, Mapping), "HOLD_CONFIG_SCHEMA", "planned_bootstrap_patch")
    snapshot_hash = railway.get("railway_live_snapshot_sha256")
    _require(
        snapshot_hash == sha256_json(snapshot),
        "HOLD_CONFIG_DRIFT",
        "Railway snapshot hash mismatch",
    )
    derived = derive_release_states(snapshot, patch)
    expected_derived = config.get("derived_config")
    _require(isinstance(expected_derived, Mapping), "HOLD_CONFIG_SCHEMA", "derived_config")
    for key, value in derived.items():
        _require(expected_derived.get(key) == value, "HOLD_CONFIG_DRIFT", key)

    bootstrap = derived["raw_allowlisted_env"]
    target = dict(bootstrap)
    target["COVERAGE_RELEASE_PROFILE"] = PROFILE
    _require(target.get("MUST_PRESERVE_CONTRACT") == "on", "HOLD_CONFIG_DRIFT", "MUST_PRESERVE_CONTRACT")
    retrieval = config.get("retrieval")
    _require(isinstance(retrieval, Mapping), "HOLD_CONFIG_SCHEMA", "retrieval")
    _require(retrieval.get("hyde_enabled") is False, "HOLD_CONFIG_DRIFT", "HYDE_ENABLED")
    target_semantic = derived["target_semantic_config"]
    semantic_retrieval = target_semantic["retrieval"]
    _require(
        retrieval.get("chunks_table") == target_semantic["corpus"]["chunks_table"]
        and retrieval.get("retrieval_top_k")
        == semantic_retrieval["retrieval_top_k"]
        and retrieval.get("rerank_top_k") == semantic_retrieval["rerank_top_k"]
        and retrieval.get("reranker_backend")
        == semantic_retrieval["reranker_backend"]
        and retrieval.get("hyde_enabled") == semantic_retrieval["hyde_enabled"],
        "HOLD_CONFIG_DRIFT",
        "retrieval semantic projection differs from effective Railway config",
    )
    _require(target.get("COVERAGE_RELEASE_PROFILE") == PROFILE, "HOLD_CONFIG_DRIFT", "profile")
    for name in TARGET_OFF_FLAGS:
        _require(target.get(name) == "off", "HOLD_CONFIG_DRIFT", f"{name} must be off")

    runtime_config = config.get("runtime")
    _require(isinstance(runtime_config, Mapping), "HOLD_RUNTIME_DRIFT", "runtime")
    for name in (
        "python_version",
        "anthropic_sdk_version",
        "voyage_sdk_version",
        "effective_lock_sha256",
    ):
        _require(bool(runtime_config.get(name)), "HOLD_RUNTIME_DRIFT", name)
    _require(
        runtime_config.get("python_version") == sys.version.split()[0],
        "HOLD_RUNTIME_DRIFT",
        "Python version drift",
    )
    try:
        observed_anthropic = package_version("anthropic")
        observed_voyage = package_version("voyageai")
    except PackageNotFoundError as exc:
        raise P1Error("HOLD_RUNTIME_DRIFT", f"SDK missing: {exc.name}") from exc
    _require(
        runtime_config.get("anthropic_sdk_version") == observed_anthropic,
        "HOLD_RUNTIME_DRIFT",
        "Anthropic SDK version drift",
    )
    _require(
        runtime_config.get("voyage_sdk_version") == observed_voyage,
        "HOLD_RUNTIME_DRIFT",
        "Voyage SDK version drift",
    )
    _require(
        runtime_config.get("effective_lock_sha256")
        == sha256_file(ROOT / "requirements.txt", lf_normalized=True),
        "HOLD_RUNTIME_DRIFT",
        "effective dependency input hash drift",
    )
    models = config.get("models")
    _require(isinstance(models, Mapping), "HOLD_CONFIG_SCHEMA", "models")
    for name in ("embedding", "reranker", "generator"):
        _require(bool(models.get(name)), "HOLD_CONFIG_SCHEMA", f"models.{name}")
    _require(models.get("prompt_cache") is False, "HOLD_CACHE_POLICY_DRIFT", "prompt_cache")
    _require(models.get("temperature") == 0, "HOLD_MODEL_PREREG_DRIFT", "temperature")
    _require(
        models.get("max_tokens")
        == int(
            # Per-operation budget is checked against this again in the
            # preflight bundle once the prereg is available.
            models.get("max_tokens")
        )
        and models.get("max_tokens") > 0,
        "HOLD_MODEL_PREREG_DRIFT",
        "max_tokens",
    )
    _require(
        models.get("inference_geo") in {"global", "default"},
        "HOLD_PRICING_DRIFT",
        "US-only inference_geo needs the 1.1x tariff and is not preregistered",
    )
    _require(
        models.get("service_tier") == "standard_sync",
        "HOLD_PRICING_DRIFT",
        "batch/priority pricing is not preregistered",
    )
    semantic_generation = target_semantic["generation"]
    _require(
        models.get("generator") == semantic_generation["model"]
        and models.get("reranker") == semantic_retrieval["reranker_model"]
        and models.get("embedding") == target_semantic["embedding"]["model"]
        and models.get("max_tokens") == semantic_generation["max_tokens"]
        and models.get("temperature") == semantic_generation["temperature"]
        and models.get("prompt_cache") == semantic_generation["prompt_cache"],
        "HOLD_CONFIG_DRIFT",
        "model semantic projection differs from effective runtime",
    )
    verify_implementation_hashes(config.get("implementation_hashes"))
    actual_rpc = config.get("rpc_allowlist")
    expected_rpc = derive_rpc_allowlist(bootstrap)
    _require(
        actual_rpc == expected_rpc,
        "HOLD_RPC_ALLOWLIST_DRIFT",
        f"expected {expected_rpc}, got {actual_rpc}",
    )
    _require(config.get("authorizations") == {
        "paid_run": False,
        "railway_mutation": False,
        "supabase_write": False,
    }, "HOLD_CONFIG_SCHEMA", "release config must not authorize side effects")
    return derived


def verify_railway_snapshot_freshness(
    railway: Mapping[str, Any], *, now: datetime
) -> None:
    _require(
        railway.get("snapshot_max_age_seconds")
        == int(MAX_RAILWAY_SNAPSHOT_AGE.total_seconds())
        and railway.get("snapshot_future_skew_seconds")
        == int(MAX_RAILWAY_SNAPSHOT_FUTURE_SKEW.total_seconds()),
        "HOLD_CONFIG_SCHEMA",
        "Railway snapshot freshness policy drift",
    )
    snapshot_taken_at = _parse_time(
        railway.get("read_only_snapshot_taken_at"),
        field="read_only_snapshot_taken_at",
    )
    _require(
        snapshot_taken_at <= now + MAX_RAILWAY_SNAPSHOT_FUTURE_SKEW
        and now - snapshot_taken_at <= MAX_RAILWAY_SNAPSHOT_AGE,
        "HOLD_RAILWAY_SNAPSHOT_STALE",
        "Railway snapshot is beyond its sealed freshness window",
    )


def operation_models(release_config: Mapping[str, Any]) -> dict[str, str]:
    models = release_config["models"]
    return {
        "embedding": str(models["embedding"]),
        "rerank": str(models["reranker"]),
        "synthesis": str(models["generator"]),
    }


def _sealed_path(relative: Any) -> Path:
    _require(isinstance(relative, str) and relative, "HOLD_PREREG_DRIFT", "sealed path")
    path = (ROOT / relative).resolve()
    _require(ROOT in path.parents and path.is_file(), "HOLD_PREREG_DRIFT", relative)
    return path


def verify_prereg_sealed_inputs(prereg: Mapping[str, Any]) -> None:
    sealed = prereg.get("sealed_inputs")
    _require(isinstance(sealed, Mapping), "HOLD_PREREG_DRIFT", "sealed_inputs")
    for role in ("fact_contract", "model_extraction_receipt", "release_config_schema"):
        spec = sealed.get(role)
        _require(isinstance(spec, Mapping), "HOLD_PREREG_DRIFT", role)
        path = _sealed_path(spec.get("path"))
        expected_lf = spec.get("sha256_lf")
        _require(
            isinstance(expected_lf, str)
            and sha256_file(path, lf_normalized=True) == expected_lf,
            "HOLD_PREREG_DRIFT",
            f"{role} LF hash",
        )
        if role == "fact_contract":
            contract = load_json_object(path)
            _require(
                contract.get("payload_sha256") == spec.get("payload_sha256")
                and sha256_json(
                    {
                        key: value
                        for key, value in contract.items()
                        if key != "payload_sha256"
                    }
                )
                == spec.get("payload_sha256"),
                "HOLD_PREREG_DRIFT",
                "fact contract payload hash",
            )
        if role == "release_config_schema":
            _require(
                sha256_json(load_json_object(path)) == spec.get("schema_object_sha256"),
                "HOLD_PREREG_DRIFT",
                "release schema object hash",
            )
    release = sealed.get("release_config")
    _require(isinstance(release, Mapping), "HOLD_PREREG_DRIFT", "release config slot")
    _require(
        release.get("required_path") == "evals/s277_c1_p1_release_config_v1.json",
        "HOLD_PREREG_DRIFT",
        "release config path",
    )


def verify_prereg_release_identity(prereg: Mapping[str, Any]) -> None:
    """Bind P1 to preserving orthogonal runtime flags across activation."""

    identity = prereg.get("release_identity")
    _require(isinstance(identity, Mapping), "HOLD_PREREG_DRIFT", "release_identity")
    preserved = identity.get("preserved_orthogonal_flags")
    expected = {
        "VISUAL_ASSETS_REGISTRY": {
            "allowed_values": ["on", "off"],
            "source_path": "railway.live_snapshot.VISUAL_ASSETS_REGISTRY",
            "bootstrap_policy": "preserve_exact",
            "target_policy": "preserve_exact",
            "profile_owned": False,
        }
    }
    _require(
        preserved == expected,
        "HOLD_PREREG_DRIFT",
        "orthogonal flag preservation contract",
    )


def verify_prereg_runtime_contract(prereg: Mapping[str, Any]) -> None:
    """Reject a prereg that weakens the runtime/receipt bindings enforced here."""

    semantic = prereg.get("semantic_runtime_contract")
    _require(isinstance(semantic, Mapping), "HOLD_PREREG_DRIFT", "semantic runtime contract")
    expected_raw = {
        "CHUNKS_TABLE": "chunks_v2",
        "ENUNCIADOS_MULTIVECTOR": "on",
        "HYQ_TABLE": "on",
        "HYQ_PILOT_FILE": "",
        "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "add",
        "GENERATOR_SELECTION_BLOCK": "on",
        "GENERATOR_PROMPT_VARIANT": "fidelity",
        "HYDE_ENABLED": "false",
        "RERANK_TOP_K": "10",
        "LLM_MAX_TOKENS": "3500",
        "MUST_PRESERVE_CONTRACT": "on",
    }
    _require(
        semantic.get("schema_version") == "s277_c1_semantic_runtime_contract_v1"
        and semantic.get("semantic_projection_schema") == SEMANTIC_PROJECTION_SCHEMA
        and semantic.get("snapshot_freshness")
        == {
            "max_age_seconds": int(MAX_RAILWAY_SNAPSHOT_AGE.total_seconds()),
            "future_skew_seconds": int(MAX_RAILWAY_SNAPSHOT_FUTURE_SKEW.total_seconds()),
            "validated_at": "every_preflight_and_immediately_before_first_paid_call",
        }
        and semantic.get("required_raw_env") == expected_raw
        and semantic.get("required_target_off_env")
        == {name: "off" for name in TARGET_OFF_FLAGS},
        "HOLD_PREREG_DRIFT",
        "semantic runtime invariants",
    )
    _require(
        semantic.get("semantic_projection_exact_top_level_keys")
        == ["schema", "corpus", "retrieval", "generation", "embedding", "coverage"]
        and semantic.get("semantic_hashes_required")
        == ["bootstrap_semantic_config_sha256", "target_semantic_config_sha256"]
        and semantic.get("raw_effective_hashes_preserved") is True,
        "HOLD_PREREG_DRIFT",
        "semantic projection/hash contract",
    )

    authorization = prereg.get("authorization")
    input_preflight = prereg.get("input_preflight")
    wal = prereg.get("wal")
    fence = prereg.get("corpus_fence")
    _require(
        isinstance(authorization, Mapping)
        and authorization.get("paid_permit_required_fields")
        == [
            "authorization_id",
            "run_id",
            "artifact_identity_sha256",
            "release_config_sha256",
            "prereg_sha256",
            "replica_plan_sha256",
        ]
        and authorization.get("global_atomic_claim_outside_artifact_dir") is True
        and authorization.get("authorization_ledger_derivation")
        == f"artifact_root.parent/{AUTHORIZATION_LEDGER_DIRNAME}"
        and authorization.get("authorization_ledger_root_injection_allowed")
        is False
        and authorization.get("execution_lease_derivation")
        == (
            "authorization_ledger/leases/"
            "{sha256(normcase(resolved_artifact_root))}.json"
        )
        and authorization.get("execution_lease_acquire")
        == "O_EXCL_before_claim_bind_and_recovery"
        and authorization.get("execution_lease_release")
        == "only_after_result_persisted"
        and authorization.get("execution_lease_existing")
        == "HOLD_MANUAL_RECOVERY_NO_AUTO_RECLAIM"
        and authorization.get("execution_lease_scope")
        == "single_host_filesystem_only"
        and authorization.get("execution_lease_multi_host")
        == "STOP_LINE_EXTERNAL_TRANSACTIONAL_LOCK_REQUIRED"
        and authorization.get("execution_lease_recovery_command")
        == "NOT_IMPLEMENTED_FUTURE_REVIEW"
        and authorization.get(
            "authorization_receipt_json_safe_deep_copy_and_seal"
        )
        is True
        and authorization.get("existing_claim_requires_canonical_resume_state")
        == [
            CALL_JOURNAL_FILENAME,
            f"{CALL_JOURNAL_FILENAME}.genesis.json",
            f"{CALL_JOURNAL_FILENAME}.claims",
            "run_genesis.json",
        ]
        and authorization.get("claim_resume_policy")
        == "same_authorization_id_run_id_artifact_identity_and_genesis_only"
        and isinstance(wal, Mapping)
        and wal.get("canonical_runtime_layout")
        == {
            "call_journal": f"artifact_root/{CALL_JOURNAL_FILENAME}",
            "call_journal_genesis": (
                f"artifact_root/{CALL_JOURNAL_FILENAME}.genesis.json"
            ),
            "call_claims": f"artifact_root/{CALL_JOURNAL_FILENAME}.claims",
            "artifact_genesis": "artifact_root/run_genesis.json",
            "authorization_ledger": (
                f"artifact_root.parent/{AUTHORIZATION_LEDGER_DIRNAME}"
            ),
            "run_lease": (
                "authorization_ledger/leases/"
                "{sha256(normcase(resolved_artifact_root))}.json"
            ),
        }
        and wal.get("runtime_layout_schema") == RUNTIME_LAYOUT_SCHEMA
        and wal.get("runtime_layout_sha256_in_run_genesis") is True
        and wal.get("run_genesis_exact_identity")
        == [
            "authorization_id",
            "authorization_receipt_sha256",
            "run_id",
            "artifact_identity_sha256",
            "runtime_layout",
            "runtime_layout_sha256",
            "release_config_sha256",
            "prereg_sha256",
            "tested_commit_sha",
            "tested_tree_sha",
            "target_semantic_config_sha256",
            "fingerprint_receipt_sha256",
            "fingerprint_sha256",
            "fence_open_receipt_sha256",
            "fence_identity",
            "replica_plan_sha256",
            "call_plan_sha256",
            "validation_snapshot",
            "validation_snapshot_sha256",
        ]
        and wal.get("run_genesis_sha256_on_every_event_and_atomic_call_claim")
        is True
        and wal.get("opened_journal_change_before_bind_or_recovery")
        == "HOLD_WAL_STALE_OPEN"
        and wal.get("global_terminal_stop_before_any_new_call")
        == ["FAILED_PRE_SEND_NO_RETRY", "UNKNOWN_BILLED_POST_SEND"]
        and wal.get("new_call_order")
        == "exact_first_preregistered_call_key_absent_from_WAL"
        and wal.get("provider_boundary_invoke_serialized_in_process") is True,
        "HOLD_PREREG_DRIFT",
        "authorization/run-genesis contract",
    )
    _require(
        isinstance(input_preflight, Mapping)
        and input_preflight.get("json_safe_deep_copy_exact")
        == [
            "release_config",
            "prereg",
            "fingerprint_receipt",
            "fence_open_receipt",
        ]
        and input_preflight.get("preserve_runtime_identity") is True
        and input_preflight.get(
            "execution_start_rebuild_with_fresh_runtime_identity"
        )
        is True
        and input_preflight.get(
            "runtime_rechecked_immediately_before_lease_and_every_send"
        )
        is True
        and input_preflight.get("execution_start_exact_seals")
        == [
            "release_config_sha256",
            "prereg_sha256",
            "fingerprint_receipt_sha256",
            "fence_open_receipt_sha256",
            "runtime_identity_sha256",
            "stored_control_score_sha256",
            "budget_sha256",
            "input_contract_sha256",
        ],
        "HOLD_PREREG_DRIFT",
        "execution-start preflight revalidation contract",
    )
    _require(
        isinstance(fence, Mapping)
        and fence.get("declared_surface_hashes_are_live_attestation") is False
        and fence.get(
            "live_rpc_signature_index_config_manifest_materialized"
        )
        is True
        and fence.get("product_cli_stop_line") is None
        and "HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED"
        not in prereg.get("current_stop_lines", [])
        and "HOLD_LIVE_MANIFEST_NOT_CAPTURED"
        in prereg.get("current_stop_lines", [])
        and fence.get("persistent_session_postgres_not_transaction_pooler")
        is True
        and fence.get("operator_ipc_boundary")
        == "credential_free_append_only_single_use_with_hashed_terminal_journal"
        and fence.get("abort_protocol")
        == "exact_terminal_response_recovery_or_confirmed_rollback_or_ambiguous"
        and fence.get("postgrest_guard")
        == {
            "principal": "p1_readonly",
            "identity_rpc_bound_to_exact_jwt_sha256": True,
            "exact_get_rpc_allowlist": True,
            "write_methods_forbidden": True,
            "redirects_forbidden": True,
            "request_receipts_bound_per_replica": True,
        }
        and fence.get("protocol")
        == [
            "BEGIN_READ_COMMITTED_READ_ONLY",
            "SHARE_LOCKS_CANONICAL_ORDER_NOWAIT",
            "INITIAL_FINGERPRINT",
            "POST_INITIAL_FINGERPRINT_SESSION_RECHECK",
            "LIVE_MANIFEST_PRE",
            "POST_PRE_MANIFEST_SESSION_RECHECK",
            "27_REPLICAS_WITH_LIVE_MANIFEST_WATCH",
            "LIVE_MANIFEST_POST",
            "FRESH_HEARTBEAT_RECHECK_BEFORE_FINAL_FINGERPRINT",
            "FINAL_FINGERPRINT_UNDER_LOCK",
            "POST_FINAL_FINGERPRINT_SESSION_LOCK_WAITER_RECHECK",
            "COMMIT",
        ]
        and fence.get("clock_skew_tolerance_seconds") == 2
        and fence.get("fingerprint_ceiling_ms") == 120000
        and fence.get("fingerprint_statement_timeout_ms") == 130000
        and fence.get("open_close_timing_bounds")
        == {
            "server_operation_ceiling_seconds": 1200,
            "max_unchecked_block_seconds": 450,
            "response_allowance_seconds": 60,
            "client_timeout_seconds": 1740,
            "request_ttl_seconds": 1800,
            "strict_order": "server_ceiling+max_unchecked_block+response_allowance<client_timeout<request_ttl",
        }
        and fence.get("terminal_journal")
        == {
            "schema": "s277_c1_p1_fence_terminal_journal_v1",
            "request_id_hash_action_sequence_session_bound": True,
            "exact_response_and_hash_persisted_before_response_file": True,
            "expired_exact_replay_allowed_without_redispatch": True,
            "closed_aborted_conflict_rejected": True,
            "abort_reason_preserved": True,
            "abort_after_observed_closed_forbidden": True,
        }
        and isinstance(fence.get("close_invariants"), Mapping)
        and fence["close_invariants"].get(
            "fresh_heartbeat_required_before_final_fingerprint"
        )
        is True
        and fence["close_invariants"].get(
            "fingerprint_is_only_heartbeat_age_exemption_and_is_bounded"
        )
        is True
        and fence["close_invariants"].get(
            "fresh_session_identity_locks_and_waiters_recheck_after_final_fingerprint"
        )
        is True
        and fence["close_invariants"].get("postcheck_heartbeat_fresh_at_close")
        is True
        and fence.get("base_relations_exact") == list(BASE_FENCE_RELATIONS)
        and fence.get("base_rpc_allowlist_exact") == list(BASE_RPC_ALLOWLIST)
        and fence.get("base_rest_get_allowlist_exact")
        == list(BASE_REST_GET_ALLOWLIST)
        and fence.get("visual_on_surface_extension")
        == {
            "relation": VISUAL_FENCE_RELATION,
            "rest_get": VISUAL_REST_GET_SURFACE,
        }
        and fence.get(
            "watch_immediately_inside_provider_boundary_before_prepare_and_send"
        )
        is True
        and fence.get("watch_absolute_heartbeat_age_required")
        == "now-last_heartbeat_at<=heartbeat_max_age_seconds"
        and fence.get(
            "persisted_watch_historical_validation_at_score_finalize"
        )
        is True
        and fence.get("fingerprint_expiry_rechecked_before_each_provider_prepare")
        is True,
        "HOLD_PREREG_DRIFT",
        "canonical fence surface contract",
    )

    pipeline = prereg.get("receipt_pipeline")
    _require(isinstance(pipeline, Mapping), "HOLD_PREREG_DRIFT", "receipt pipeline")
    physical = pipeline.get("physical_call_envelope")
    generation = pipeline.get("generation_chain")
    _require(
        pipeline.get("schema_version") == "s277_c1_p1_receipt_pipeline_v1"
        and isinstance(physical, Mapping)
        and physical.get("common_request_exact_keys")
        == [
            "replica_key",
            "operation",
            "model",
            "run_genesis_sha256",
            "lineage_input_sha256",
            "physical_payload",
            "physical_payload_sha256",
            "input_tokens_upper_bound",
            "max_output_tokens",
        ]
        and physical.get("input_bound_derivation")
        == "len(canonical_json_bytes(physical_payload))+512"
        and physical.get("provider_token_overhead_reserve")
        == PROVIDER_TOKEN_OVERHEAD_RESERVE
        and pipeline.get("render", {}).get("recompute_exactly_with")
        == "src.bot.response_formatter.format_telegram_messages(answer)"
        and pipeline.get("visual_assets", {}).get("on_relation")
        == VISUAL_FENCE_RELATION
        and pipeline.get("visual_assets", {}).get("on_rest_method") == "GET"
        and physical.get("max_retries") == 0
        and physical.get("prompt_cache") is False
        and physical.get("inference_geo") == "global"
        and physical.get("service_tier") == "standard_sync"
        and physical.get("post_prepare_pre_send_guards_exact")
        == [
            "fresh_runtime_identity",
            "canonical_lease_ownership",
            "reserved_request_sha256_unchanged",
        ]
        and physical.get(
            "fingerprint_and_fence_boundary_inputs_json_safe_deep_copied"
        )
        is True
        and physical.get("offline_gate_reopens_all_wal_physical_artifacts")
        is True
        and physical.get("canonical_provider_response_path")
        == "provider_responses/{sha256(call_key)}.json"
        and physical.get("canonical_fence_watch_path")
        == "fence_watches/{sha256(call_key)}.json"
        and physical.get("physical_directories_exact_no_missing_or_extra")
        is True
        and physical.get("offline_cross_binding")
        == (
            "replica.call_requests_and_observed_responses_to_"
            "WAL_and_physical_files"
        )
        and physical.get("offline_gate_revalidates_all_27_replica_receipts")
        is True
        and physical.get("run_validation_snapshot")
        == {
            "materialization": "embedded_in_canonical_run_genesis_json",
            "exact_components": [
                "models",
                "input_contract",
                "budget_plan",
                "implementation_hashes",
            ],
            "component_hashes_and_snapshot_hash_required": True,
            "bound_in_result": [
                "validation_snapshot_sha256",
                "implementation_hashes_sha256",
            ],
        }
        and physical.get(
            "score_finalize_current_implementation_must_equal_run_snapshot"
        )
        is True
        and isinstance(generation, Mapping)
        and generation.get("stage_order")
        == ["diagram_postprocess", "answer_planner", "must_preserve"],
        "HOLD_PREREG_DRIFT",
        "physical receipt/envelope contract",
    )


def _offline_extract_models(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Run product extraction in an isolated, socket-denied child process."""

    cache_key = sha256_json(list(rows))
    if cache_key in _MODEL_EXTRACTION_CACHE:
        return json.loads(json.dumps(_MODEL_EXTRACTION_CACHE[cache_key]))

    child = r'''
import json, os, socket, sys
sys.path.insert(0, os.getcwd())
def deny(event, _args):
    if event in {"socket.connect", "socket.connect_ex"}:
        raise RuntimeError("offline model extraction attempted network")
sys.addaudithook(deny)
from src.rag.retriever import extract_product_models
rows = json.load(sys.stdin)
print(json.dumps([
    {"qid": row["qid"], "models": extract_product_models(row["question"])}
    for row in rows
], ensure_ascii=False))
'''
    keep_names = ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP")
    environment = {
        name: os.environ[name] for name in keep_names if name in os.environ
    }
    environment.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "PYTHONIOENCODING": "utf-8",
            "COVERAGE_RELEASE_PROFILE": "off",
            "CHUNKS_TABLE": "chunks_v2",
            "HYDE_ENABLED": "false",
            "ENUNCIADOS_MULTIVECTOR": "off",
            "HYQ_TABLE": "off",
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", child],
        cwd=ROOT,
        env=environment,
        input=json.dumps(list(rows), ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    _require(
        completed.returncode == 0,
        "HOLD_EXPECTATION_DRIFT",
        "isolated model extraction failed "
        f"({completed.returncode}): {completed.stderr[-1000:].strip()}",
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise P1Error("HOLD_EXPECTATION_DRIFT", "invalid extraction receipt") from exc
    _require(isinstance(result, list), "HOLD_EXPECTATION_DRIFT", "extraction result")
    _MODEL_EXTRACTION_CACHE[cache_key] = result
    return result


def verify_model_extraction_contract(prereg: Mapping[str, Any]) -> None:
    population = prereg.get("population")
    _require(isinstance(population, Mapping), "HOLD_PREREG_DRIFT", "population")
    rows = population.get("rows")
    _require(isinstance(rows, list) and len(rows) == 13, "HOLD_PREREG_DRIFT", "population rows")
    receipt_spec = prereg["sealed_inputs"]["model_extraction_receipt"]
    receipt = load_json_object(_sealed_path(receipt_spec["path"]))
    _require(
        receipt.get("status") == "PASS_MODEL_EXTRACTION_OFFLINE"
        and receipt.get("network_calls") == 0
        and receipt.get("paid_model_calls") == 0,
        "HOLD_EXPECTATION_DRIFT",
        "model extraction receipt status",
    )
    source_hashes = receipt.get("inputs_sha256_lf")
    _require(isinstance(source_hashes, Mapping) and source_hashes, "HOLD_EXPECTATION_DRIFT", "extraction inputs")
    for relative, expected_hash in source_hashes.items():
        path = _sealed_path(relative)
        _require(
            sha256_file(path, lf_normalized=True) == expected_hash,
            "HOLD_EXPECTATION_DRIFT",
            f"extraction source drift: {relative}",
        )
    _require(
        receipt.get("environment_contract", {}).get("PYTHON_DOTENV_DISABLED") == "1"
        and receipt.get("environment_contract", {}).get("LEVER2_IDENTITY") == "absent",
        "HOLD_EXPECTATION_DRIFT",
        "extraction environment contract",
    )
    receipt_by_qid = {
        row.get("qid"): row for row in receipt.get("rows", []) if isinstance(row, Mapping)
    }
    expected: list[dict[str, Any]] = []
    for row in rows:
        _require(isinstance(row, Mapping), "HOLD_PREREG_DRIFT", "population row")
        question = row.get("question")
        qid = row.get("qid")
        expected_models = row.get("expected_target_models")
        _require(isinstance(question, str) and isinstance(qid, str), "HOLD_PREREG_DRIFT", "question")
        _require(
            hashlib.sha256(question.encode("utf-8")).hexdigest()
            == row.get("question_sha256"),
            "HOLD_EXPECTATION_DRIFT",
            f"question hash {qid}",
        )
        _require(isinstance(expected_models, list) and expected_models, "HOLD_EXPECTATION_DRIFT", qid)
        _require(row.get("query_for_retrieval") == "exact_question", "HOLD_INPUT_DRIFT", qid)
        _require(row.get("available_models") is None, "HOLD_INPUT_DRIFT", qid)
        frozen = receipt_by_qid.get(qid)
        _require(
            isinstance(frozen, Mapping)
            and frozen.get("question_sha256") == row.get("question_sha256")
            and frozen.get("models") == expected_models,
            "HOLD_EXPECTATION_DRIFT",
            f"frozen extraction {qid}",
        )
        expected.append({"qid": qid, "question": question})
    observed = _offline_extract_models(expected)
    _require(
        observed
        == [
            {"qid": row["qid"], "models": row["expected_target_models"]}
            for row in rows
        ],
        "HOLD_EXPECTATION_DRIFT",
        "extract_product_models output drift",
    )


@dataclass(frozen=True)
class CallCostSpec:
    call_key: str
    provider: str
    model: str
    max_input_tokens: int
    max_output_tokens: int
    input_usd_per_mtok: Decimal
    output_usd_per_mtok: Decimal
    max_cost_usd: Decimal

    @classmethod
    def from_mapping(cls, call_key: str, value: Mapping[str, Any]) -> "CallCostSpec":
        max_input = value.get("max_input_tokens")
        max_output = value.get("max_output_tokens", 0)
        _require(isinstance(max_input, int) and max_input >= 0, "HOLD_INVALID_COST", call_key)
        _require(isinstance(max_output, int) and max_output >= 0, "HOLD_INVALID_COST", call_key)
        input_rate = _decimal(value.get("input_usd_per_mtok"), field="input rate")
        output_rate = _decimal(value.get("output_usd_per_mtok", "0"), field="output rate")
        declared = _decimal(value.get("max_cost_usd"), field="max cost")
        calculated = (
            Decimal(max_input) * input_rate + Decimal(max_output) * output_rate
        ) / Decimal(1_000_000)
        _require(
            declared >= calculated,
            "HOLD_UNDERBOUNDED_COST",
            f"{call_key}: declared {declared} < token-derived {calculated}",
        )
        provider = value.get("provider")
        model = value.get("model")
        _require(isinstance(provider, str) and provider, "HOLD_INVALID_COST", call_key)
        _require(isinstance(model, str) and model, "HOLD_INVALID_COST", call_key)
        return cls(
            call_key=call_key,
            provider=provider,
            model=model,
            max_input_tokens=max_input,
            max_output_tokens=max_output,
            input_usd_per_mtok=input_rate,
            output_usd_per_mtok=output_rate,
            max_cost_usd=declared,
        )

    def observed_cost(self, usage: Mapping[str, Any]) -> Decimal:
        for key, value in usage.items():
            if (
                "cache" in str(key).casefold()
                and not _cache_usage_value_is_explicit_zero(value)
            ):
                raise P1Error("NO_GO_CACHE_USAGE_DRIFT", f"cache usage in {self.call_key}")
        raw_input = usage.get("input_tokens", usage.get("total_tokens"))
        raw_output = usage.get("output_tokens", 0)
        _require(
            isinstance(raw_input, int) and raw_input >= 0,
            "NO_GO_USAGE_MISSING",
            self.call_key,
        )
        _require(
            isinstance(raw_output, int) and raw_output >= 0,
            "NO_GO_USAGE_MISSING",
            self.call_key,
        )
        return (
            Decimal(raw_input) * self.input_usd_per_mtok
            + Decimal(raw_output) * self.output_usd_per_mtok
        ) / Decimal(1_000_000)


def _cache_usage_value_is_explicit_zero(value: Any) -> bool:
    """Accept provider cache counters only when every reported leaf is zero.

    Anthropic SDK 0.97 exposes both the legacy scalar counters and a nested
    ``cache_creation`` breakdown, even when prompt caching is unused.  The
    nested object itself is truthy, so it must be evaluated by its leaves;
    unknown non-scalar leaf shapes remain fail-closed.
    """

    if value is None:
        return True
    if isinstance(value, bool):
        return value is False
    if isinstance(value, int):
        return value == 0
    if isinstance(value, str):
        return value == "0"
    if isinstance(value, Mapping):
        return all(
            _cache_usage_value_is_explicit_zero(nested)
            for nested in value.values()
        )
    return False


class BudgetPlan:
    def __init__(self, specs: Sequence[CallCostSpec], cap_usd: Decimal = HARD_CAP_USD):
        self.cap_usd = _decimal(cap_usd, field="cap_usd")
        _require(self.cap_usd == HARD_CAP_USD, "HOLD_BUDGET_DRIFT", "cap must be exactly 30 USD")
        self.specs = {spec.call_key: spec for spec in specs}
        expected = expected_call_keys()
        _require(
            tuple(spec.call_key for spec in specs) == expected,
            "HOLD_CALL_PLAN_DRIFT",
            "budget calls must match the 81-call preregistered order",
        )
        self.static_worst_case_usd = sum(
            (spec.max_cost_usd for spec in specs), start=ZERO
        )
        _require(
            self.static_worst_case_usd <= self.cap_usd,
            "HOLD_STATIC_BUDGET_EXCEEDED",
            "static 81-call bound exceeds 30 USD",
        )

    @classmethod
    def from_prereg(cls, prereg: Mapping[str, Any]) -> "BudgetPlan":
        _require(prereg.get("schema_version") == PREREG_SCHEMA, "HOLD_PREREG_SCHEMA", "schema")
        population = prereg.get("population")
        _require(isinstance(population, Mapping), "HOLD_PREREG_SCHEMA", "population")
        _require(population.get("replica_order") == list(REPLICA_ORDER), "HOLD_CALL_PLAN_DRIFT", "replica order")
        _require(population.get("replica_count") == 27, "HOLD_CALL_PLAN_DRIFT", "replica count")
        budget = prereg.get("cost")
        _require(isinstance(budget, Mapping), "HOLD_PREREG_SCHEMA", "budget")
        _require(_decimal(budget.get("list_price_cap"), field="cap") == HARD_CAP_USD, "HOLD_BUDGET_DRIFT", "cap")
        operation_specs = budget.get("operations")
        _require(isinstance(operation_specs, Mapping), "HOLD_PREREG_SCHEMA", "operations")
        specs: list[CallCostSpec] = []
        for call_key in expected_call_keys():
            operation = call_key.rsplit(":", 1)[1]
            raw = operation_specs.get(operation)
            _require(isinstance(raw, Mapping), "HOLD_PREREG_SCHEMA", operation)
            specs.append(CallCostSpec.from_mapping(call_key, raw))
        return cls(specs, HARD_CAP_USD)

    @classmethod
    def from_identity(cls, identity: Mapping[str, Any]) -> "BudgetPlan":
        _require(
            isinstance(identity, Mapping)
            and set(identity) == {"cap_usd", "static_worst_case_usd", "specs"},
            "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
            "budget identity shape",
        )
        raw_specs = identity.get("specs")
        _require(
            isinstance(raw_specs, list) and len(raw_specs) == len(expected_call_keys()),
            "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
            "budget identity call count",
        )
        exact_spec_keys = {
            "call_key",
            "provider",
            "model",
            "max_input_tokens",
            "max_output_tokens",
            "input_usd_per_mtok",
            "output_usd_per_mtok",
            "max_cost_usd",
        }
        specs: list[CallCostSpec] = []
        for expected_call_key, raw in zip(
            expected_call_keys(), raw_specs, strict=True
        ):
            _require(
                isinstance(raw, Mapping)
                and set(raw) == exact_spec_keys
                and raw.get("call_key") == expected_call_key,
                "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
                f"budget identity spec {expected_call_key}",
            )
            specs.append(CallCostSpec.from_mapping(expected_call_key, raw))
        plan = cls(
            specs,
            _decimal(identity.get("cap_usd"), field="snapshot cap_usd"),
        )
        _require(
            budget_plan_identity(plan) == dict(identity),
            "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
            "budget identity canonical form",
        )
        return plan

    def projected_total(self, journal: "CallJournal") -> Decimal:
        total = ZERO
        records = journal.records
        for key, spec in self.specs.items():
            record = records.get(key)
            if record is None or record["state"] == "RESERVED_FSYNCED":
                total += spec.max_cost_usd
            elif record["state"] == "COMPLETED":
                total += _decimal(record.get("actual_cost_usd"), field=key)
            elif record["state"] == "UNKNOWN_BILLED_POST_SEND":
                total += spec.max_cost_usd
            elif record["state"] == "FAILED_PRE_SEND_NO_RETRY":
                continue
        return total

    def assert_call_allowed(self, call_key: str, journal: "CallJournal") -> None:
        _require(call_key in self.specs, "HOLD_UNREGISTERED_CALL", call_key)
        projected = self.projected_total(journal)
        _require(
            projected <= self.cap_usd,
            "NO_GO_BUDGET_BOUND_EXCEEDED",
            f"projected list-price {projected} exceeds {self.cap_usd}",
        )


def budget_plan_identity(budget: BudgetPlan) -> dict[str, Any]:
    return {
        "cap_usd": _money(budget.cap_usd),
        "static_worst_case_usd": _money(budget.static_worst_case_usd),
        "specs": [
            {
                "call_key": spec.call_key,
                "provider": spec.provider,
                "model": spec.model,
                "max_input_tokens": spec.max_input_tokens,
                "max_output_tokens": spec.max_output_tokens,
                "input_usd_per_mtok": str(spec.input_usd_per_mtok),
                "output_usd_per_mtok": str(spec.output_usd_per_mtok),
                "max_cost_usd": _money(spec.max_cost_usd),
            }
            for spec in budget.specs.values()
        ],
    }


_RUN_GENESIS_KEYS = {
    "schema",
    "authorization_id",
    "run_id",
    "artifact_identity_sha256",
    "runtime_layout",
    "runtime_layout_sha256",
    "authorization_receipt_sha256",
    "release_config_sha256",
    "prereg_sha256",
    "tested_commit_sha",
    "tested_tree_sha",
    "target_semantic_config",
    "target_semantic_config_sha256",
    "fingerprint_receipt_sha256",
    "fingerprint_sha256",
    "fence_open_receipt_sha256",
    "fence_identity",
    "replica_plan_sha256",
    "call_plan_sha256",
    "validation_snapshot",
    "validation_snapshot_sha256",
    "run_genesis_sha256",
}


def verify_run_genesis(genesis: Mapping[str, Any]) -> dict[str, Any]:
    _require(set(genesis) == _RUN_GENESIS_KEYS, "HOLD_RUN_IDENTITY", "genesis shape")
    _require(genesis.get("schema") == RUN_GENESIS_SCHEMA, "HOLD_RUN_IDENTITY", "genesis schema")
    for key in (
        "artifact_identity_sha256",
        "runtime_layout_sha256",
        "authorization_receipt_sha256",
        "release_config_sha256",
        "prereg_sha256",
        "target_semantic_config_sha256",
        "fingerprint_receipt_sha256",
        "fingerprint_sha256",
        "fence_open_receipt_sha256",
        "replica_plan_sha256",
        "call_plan_sha256",
        "validation_snapshot_sha256",
        "run_genesis_sha256",
    ):
        _require(
            isinstance(genesis.get(key), str) and bool(_HEX64.fullmatch(genesis[key])),
            "HOLD_RUN_IDENTITY",
            key,
        )
    for key in ("authorization_id", "run_id"):
        _require(
            isinstance(genesis.get(key), str)
            and bool(re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", genesis[key])),
            "HOLD_RUN_IDENTITY",
            key,
        )
    _require(
        isinstance(genesis.get("tested_commit_sha"), str)
        and bool(_HEX40.fullmatch(genesis["tested_commit_sha"]))
        and isinstance(genesis.get("tested_tree_sha"), str)
        and bool(_HEX40.fullmatch(genesis["tested_tree_sha"])),
        "HOLD_RUN_IDENTITY",
        "git identity",
    )
    semantic = genesis.get("target_semantic_config")
    fence = genesis.get("fence_identity")
    runtime_layout = genesis.get("runtime_layout")
    _require(isinstance(semantic, Mapping), "HOLD_RUN_IDENTITY", "semantic config")
    _require(
        genesis.get("target_semantic_config_sha256") == sha256_json(semantic),
        "HOLD_RUN_IDENTITY",
        "semantic config hash",
    )
    _require(isinstance(fence, Mapping), "HOLD_RUN_IDENTITY", "fence identity")
    _require(
        isinstance(runtime_layout, Mapping)
        and runtime_layout.get("schema") == RUNTIME_LAYOUT_SCHEMA
        and genesis.get("runtime_layout_sha256") == sha256_json(runtime_layout),
        "HOLD_RUN_IDENTITY",
        "runtime layout",
    )
    snapshot = genesis.get("validation_snapshot")
    _require(
        isinstance(snapshot, Mapping)
        and genesis.get("validation_snapshot_sha256") == sha256_json(snapshot),
        "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
        "validation snapshot seal",
    )
    verify_run_validation_snapshot(snapshot, genesis=genesis)
    body = {key: value for key, value in genesis.items() if key != "run_genesis_sha256"}
    _require(
        genesis.get("run_genesis_sha256") == sha256_json(body),
        "HOLD_RUN_IDENTITY",
        "genesis seal",
    )
    return dict(genesis)


class CallJournal:
    """Append-only, hash-chained, fsynced physical-call journal."""

    TERMINAL = {
        "COMPLETED",
        "FAILED_PRE_SEND_NO_RETRY",
        "UNKNOWN_BILLED_POST_SEND",
    }

    def __init__(self, path: Path, *, now: Callable[[], datetime] | None = None):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.claims_dir = self.path.with_name(self.path.name + ".claims")
        self.genesis_path = self.path.with_name(self.path.name + ".genesis.json")
        self._wal_observed_at_open = self.path.is_file()
        self._claims_observed_at_open = self.claims_dir.is_dir()
        self._genesis_observed_at_open = self.genesis_path.is_file()
        self._durable_topology_observed = (
            self._wal_observed_at_open
            and self._claims_observed_at_open
            and self._genesis_observed_at_open
        )
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._run_genesis: dict[str, Any] | None = None
        self._loaded_genesis_sha256: str | None = None
        self._recovered = False
        self.events: list[dict[str, Any]] = []
        self.records: dict[str, dict[str, Any]] = {}
        self._load()
        self._opened_disk_state = self._capture_disk_state()

    @property
    def run_genesis_sha256(self) -> str:
        _require(self._run_genesis is not None, "HOLD_RUN_IDENTITY", "WAL genesis not bound")
        return str(self._run_genesis["run_genesis_sha256"])

    def bind_genesis(self, genesis: Mapping[str, Any]) -> None:
        self.assert_unchanged_since_open()
        verified = verify_run_genesis(genesis)
        self.assert_topology(self.path.parent, genesis=verified)
        digest = verified["run_genesis_sha256"]
        self.claims_dir.mkdir(parents=True, exist_ok=True)
        _fsync_parent(self.claims_dir.parent)
        if self.genesis_path.exists():
            stored = load_json_object(self.genesis_path)
            _require(stored == verified, "HOLD_RUN_IDENTITY", "WAL genesis drift")
        else:
            write_json_exclusive(self.genesis_path, verified)
        if not self.path.exists():
            with self.path.open("xb") as handle:
                handle.flush()
                os.fsync(handle.fileno())
            _fsync_parent(self.path.parent)
        _require(
            self._loaded_genesis_sha256 in {None, digest},
            "HOLD_RUN_IDENTITY",
            "WAL belongs to another genesis",
        )
        if self._run_genesis is not None:
            _require(self._run_genesis == verified, "HOLD_RUN_IDENTITY", "WAL rebound")
            self._opened_disk_state = self._capture_disk_state()
            return
        self._run_genesis = verified
        self._opened_disk_state = self._capture_disk_state()
        self._verify_no_orphan_claims()
        self._recover_incomplete_reservations()
        self._recovered = True
        self._wal_observed_at_open = True
        self._claims_observed_at_open = True
        self._genesis_observed_at_open = True
        self._durable_topology_observed = True
        self._opened_disk_state = self._capture_disk_state()

    @staticmethod
    def _file_disk_identity(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise P1Error("HOLD_WAL_UNREADABLE", str(path)) from exc
        return {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    def _capture_disk_state(self) -> dict[str, Any]:
        try:
            claims = {
                path.name: self._file_disk_identity(path)
                for path in sorted(self.claims_dir.glob("*.json"))
            }
        except OSError as exc:
            raise P1Error("HOLD_WAL_UNREADABLE", str(self.claims_dir)) from exc
        return {
            "journal": self._file_disk_identity(self.path),
            "genesis": self._file_disk_identity(self.genesis_path),
            "claims_dir_exists": self.claims_dir.is_dir(),
            "claims": claims,
        }

    def assert_unchanged_since_open(self) -> None:
        _require(
            self._capture_disk_state() == self._opened_disk_state,
            "HOLD_WAL_STALE_OPEN",
            "journal or sidecars changed after this journal was opened",
        )

    def assert_topology(
        self,
        artifact_root: Path,
        *,
        genesis: Mapping[str, Any] | None = None,
    ) -> None:
        root = artifact_root.resolve()
        expected = canonical_runtime_layout(root)
        _require(
            self.path == root / CALL_JOURNAL_FILENAME
            and self.genesis_path
            == root / f"{CALL_JOURNAL_FILENAME}.genesis.json"
            and self.claims_dir == root / f"{CALL_JOURNAL_FILENAME}.claims",
            "HOLD_RUNTIME_TOPOLOGY",
            "journal and sidecars must use the canonical artifact-root layout",
        )
        candidate = genesis if genesis is not None else self._run_genesis
        if candidate is not None:
            _require(
                dict(candidate.get("runtime_layout", {})) == expected,
                "HOLD_RUNTIME_TOPOLOGY",
                "journal runtime layout differs from run genesis",
            )

    def require_existing_resume_state(
        self, artifact_root: Path, genesis: Mapping[str, Any]
    ) -> None:
        self.assert_topology(artifact_root, genesis=genesis)
        _require(
            self._durable_topology_observed
            and self.path.is_file()
            and self.claims_dir.is_dir()
            and self.genesis_path.is_file(),
            "HOLD_AUTHORIZATION_RESUME_STATE",
            "existing authorization requires its canonical WAL and sidecars",
        )
        _require(
            load_json_object(self.genesis_path) == dict(genesis),
            "HOLD_AUTHORIZATION_RESUME_STATE",
            "existing authorization WAL genesis is absent or drifted",
        )

    def require_new_claim_state(self, artifact_root: Path) -> None:
        self.assert_topology(artifact_root)
        _require(
            not self._wal_observed_at_open
            and not self._claims_observed_at_open
            and not self._genesis_observed_at_open
            and not self.path.exists()
            and not self.claims_dir.exists()
            and not self.genesis_path.exists()
            and not self.events,
            "HOLD_AUTHORIZATION_RESUME_STATE",
            "new authorization cannot adopt pre-existing WAL state",
        )

    @property
    def head_sha256(self) -> str | None:
        return self.events[-1]["event_sha256"] if self.events else None

    def _claim_path(self, call_key: str) -> Path:
        return self.claims_dir / f"{hashlib.sha256(call_key.encode()).hexdigest()}.json"

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            lines = self.path.read_bytes().splitlines()
        except OSError as exc:
            raise P1Error("HOLD_WAL_UNREADABLE", str(self.path)) from exc
        previous: str | None = None
        for index, raw in enumerate(lines):
            _require(bool(raw.strip()), "HOLD_WAL_CORRUPT", f"blank WAL line {index + 1}")
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise P1Error("HOLD_WAL_CORRUPT", f"line {index + 1}") from exc
            _require(isinstance(event, dict), "HOLD_WAL_CORRUPT", f"line {index + 1}")
            digest = event.get("event_sha256")
            body = {key: value for key, value in event.items() if key != "event_sha256"}
            _require(
                digest == sha256_json(body),
                "HOLD_WAL_CORRUPT",
                f"event hash line {index + 1}",
            )
            _require(
                body.get("previous_event_sha256") == previous,
                "HOLD_WAL_CORRUPT",
                f"chain line {index + 1}",
            )
            _require(body.get("schema") == WAL_SCHEMA, "HOLD_WAL_CORRUPT", "schema")
            _require(body.get("sequence") == index + 1, "HOLD_WAL_CORRUPT", "sequence")
            genesis_sha = body.get("run_genesis_sha256")
            _require(
                isinstance(genesis_sha, str) and bool(_HEX64.fullmatch(genesis_sha)),
                "HOLD_WAL_CORRUPT",
                "run genesis",
            )
            if self._loaded_genesis_sha256 is None:
                self._loaded_genesis_sha256 = genesis_sha
            _require(
                self._loaded_genesis_sha256 == genesis_sha,
                "HOLD_WAL_CORRUPT",
                "mixed run genesis",
            )
            self._apply_event(event, loading=True)
            self.events.append(event)
            previous = digest

    def _apply_event(self, event: Mapping[str, Any], *, loading: bool) -> None:
        call_key = event.get("call_key")
        state = event.get("state")
        _require(isinstance(call_key, str) and call_key, "HOLD_WAL_CORRUPT", "call_key")
        _require(
            state == "RESERVED_FSYNCED" or state in self.TERMINAL,
            "HOLD_WAL_CORRUPT",
            "state",
        )
        current = self.records.get(call_key)
        _require(
            isinstance(event.get("request_sha256"), str)
            and bool(_HEX64.fullmatch(event["request_sha256"])),
            "HOLD_WAL_CORRUPT",
            f"request hash {call_key}",
        )
        _decimal(event.get("max_cost_usd"), field=f"WAL max {call_key}")
        if self._run_genesis is not None:
            _require(
                event.get("run_genesis_sha256") == self.run_genesis_sha256,
                "HOLD_RUN_IDENTITY",
                f"WAL genesis {call_key}",
            )
        if state == "RESERVED_FSYNCED":
            _require(current is None, "HOLD_WAL_CORRUPT", f"duplicate reserve {call_key}")
        else:
            _require(
                current is not None and current["state"] == "RESERVED_FSYNCED",
                "HOLD_WAL_CORRUPT",
                f"illegal terminal transition {call_key}",
            )
            _require(
                event.get("request_sha256") == current.get("request_sha256"),
                "HOLD_WAL_CORRUPT",
                f"request drift {call_key}",
            )
            _require(
                event.get("max_cost_usd") == current.get("max_cost_usd"),
                "HOLD_WAL_CORRUPT",
                f"max-cost drift {call_key}",
            )
            _require(isinstance(event.get("reason"), str) and event.get("reason"), "HOLD_WAL_CORRUPT", "reason")
            if state == "COMPLETED":
                _decimal(event.get("actual_cost_usd"), field=f"WAL actual {call_key}")
                _require(
                    isinstance(event.get("response_path"), str)
                    and isinstance(event.get("response_sha256"), str)
                    and bool(_HEX64.fullmatch(event["response_sha256"])),
                    "HOLD_WAL_CORRUPT",
                    f"response receipt {call_key}",
                )
                _require(
                    isinstance(event.get("fence_watch_path"), str)
                    and isinstance(event.get("fence_watch_sha256"), str)
                    and bool(_HEX64.fullmatch(event["fence_watch_sha256"])),
                    "HOLD_WAL_CORRUPT",
                    f"fence watch receipt {call_key}",
                )
        self.records[call_key] = dict(event)

    def _append(self, event: dict[str, Any]) -> dict[str, Any]:
        _require(self._run_genesis is not None, "HOLD_RUN_IDENTITY", "WAL genesis not bound")
        self.assert_unchanged_since_open()
        body = {
            "schema": WAL_SCHEMA,
            "sequence": len(self.events) + 1,
            "timestamp": _iso(self._now()),
            "previous_event_sha256": self.head_sha256,
            "run_genesis_sha256": self.run_genesis_sha256,
            **event,
        }
        full = {**body, "event_sha256": sha256_json(body)}
        self._apply_event(full, loading=False)
        raw = canonical_json_bytes(full) + b"\n"
        with self.path.open("ab") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        self.events.append(full)
        self._opened_disk_state = self._capture_disk_state()
        return full

    def _recover_incomplete_reservations(self) -> None:
        pending = [
            dict(record)
            for record in self.records.values()
            if record["state"] == "RESERVED_FSYNCED"
        ]
        for reservation in sorted(pending, key=lambda row: row["sequence"]):
            self.terminal(
                reservation["call_key"],
                "UNKNOWN_BILLED_POST_SEND",
                reason="reopened_with_nonterminal_reservation",
            )

    def _verify_no_orphan_claims(self) -> None:
        known = {self._claim_path(key).name for key in self.records}
        observed = {path.name for path in self.claims_dir.glob("*.json")}
        _require(
            observed <= known,
            "HOLD_WAL_ORPHAN_CLAIM",
            "claim exists without durable WAL reservation",
        )
        for call_key, record in self.records.items():
            claim_path = self._claim_path(call_key)
            if not claim_path.exists():
                # Compatibility is intentionally denied for a new paid run: the
                # atomic claim is part of the reviewed no-double-send boundary.
                raise P1Error("HOLD_WAL_CLAIM_MISSING", call_key)
            claim = load_json_object(claim_path)
            _require(
                claim
                == {
                    "call_key": call_key,
                    "request_sha256": record["request_sha256"],
                    "max_cost_usd": record["max_cost_usd"],
                    "run_genesis_sha256": self.run_genesis_sha256,
                },
                "HOLD_WAL_CLAIM_DRIFT",
                call_key,
            )

    def reserve(
        self,
        *,
        call_key: str,
        request_sha256: str,
        max_cost_usd: Decimal,
        accumulated_prior_usd: Decimal,
    ) -> dict[str, Any]:
        self.assert_unchanged_since_open()
        _require(call_key not in self.records, "HOLD_CALL_ALREADY_CONSUMED", call_key)
        claim = {
            "call_key": call_key,
            "request_sha256": request_sha256,
            "max_cost_usd": _money(max_cost_usd),
            "run_genesis_sha256": self.run_genesis_sha256,
        }
        write_json_exclusive(self._claim_path(call_key), claim)
        self._opened_disk_state = self._capture_disk_state()
        return self._append(
            {
                **claim,
                "state": "RESERVED_FSYNCED",
                "accumulated_prior_usd": _money(accumulated_prior_usd),
            }
        )

    def terminal(
        self,
        call_key: str,
        state: str,
        *,
        reason: str,
        actual_cost_usd: Decimal | None = None,
        response_path: str | None = None,
        response_sha256: str | None = None,
        fence_watch_path: str | None = None,
        fence_watch_sha256: str | None = None,
    ) -> dict[str, Any]:
        current = self.records.get(call_key)
        _require(
            current is not None and current["state"] == "RESERVED_FSYNCED",
            "HOLD_ILLEGAL_WAL_TRANSITION",
            call_key,
        )
        event: dict[str, Any] = {
            "call_key": call_key,
            "request_sha256": current["request_sha256"],
            "max_cost_usd": current["max_cost_usd"],
            "state": state,
            "reason": reason,
        }
        if actual_cost_usd is not None:
            event["actual_cost_usd"] = _money(actual_cost_usd)
        if response_path is not None:
            event["response_path"] = response_path
        if response_sha256 is not None:
            event["response_sha256"] = response_sha256
        if fence_watch_path is not None:
            event["fence_watch_path"] = fence_watch_path
        if fence_watch_sha256 is not None:
            event["fence_watch_sha256"] = fence_watch_sha256
        return self._append(event)


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._durable_genesis_observed = (self.root / "run_genesis.json").is_file()
        self._run_genesis: dict[str, Any] | None = None

    @property
    def run_genesis_sha256(self) -> str:
        _require(self._run_genesis is not None, "HOLD_RUN_IDENTITY", "artifact genesis not bound")
        return str(self._run_genesis["run_genesis_sha256"])

    def bind_genesis(self, genesis: Mapping[str, Any]) -> None:
        verified = verify_run_genesis(genesis)
        self.assert_topology(genesis=verified)
        path = self._path("run_genesis.json")
        if path.exists():
            _require(
                load_json_object(path) == verified,
                "HOLD_RUN_IDENTITY",
                "artifact genesis drift",
            )
        else:
            write_json_exclusive(path, verified)
        if self._run_genesis is not None:
            _require(self._run_genesis == verified, "HOLD_RUN_IDENTITY", "artifact rebound")
        self._run_genesis = verified
        self._durable_genesis_observed = True

    def assert_topology(self, *, genesis: Mapping[str, Any] | None = None) -> None:
        candidate = genesis if genesis is not None else self._run_genesis
        if candidate is not None:
            _require(
                dict(candidate.get("runtime_layout", {}))
                == canonical_runtime_layout(self.root),
                "HOLD_RUNTIME_TOPOLOGY",
                "artifact store runtime layout differs from run genesis",
            )

    def require_existing_resume_state(self, genesis: Mapping[str, Any]) -> None:
        self.assert_topology(genesis=genesis)
        path = self._path("run_genesis.json")
        _require(
            self._durable_genesis_observed and path.is_file(),
            "HOLD_AUTHORIZATION_RESUME_STATE",
            "existing authorization requires its canonical artifact genesis",
        )
        _require(
            load_json_object(path) == dict(genesis),
            "HOLD_AUTHORIZATION_RESUME_STATE",
            "existing authorization artifact genesis is absent or drifted",
        )

    def require_new_claim_state(self) -> None:
        _require(
            not self._durable_genesis_observed
            and not self._path("run_genesis.json").exists(),
            "HOLD_AUTHORIZATION_RESUME_STATE",
            "new authorization cannot adopt pre-existing artifact genesis",
        )

    def _require_bound(self) -> None:
        _require(self._run_genesis is not None, "HOLD_RUN_IDENTITY", "artifact genesis not bound")

    def _path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        _require(
            path == self.root or self.root in path.parents,
            "HOLD_ARTIFACT_PATH",
            relative,
        )
        return path

    def persist_provider_response(self, call_key: str, payload: Mapping[str, Any]) -> tuple[str, str]:
        self._require_bound()
        filename = hashlib.sha256(call_key.encode()).hexdigest() + ".json"
        path = self._path(f"provider_responses/{filename}")
        digest = write_json_exclusive(path, payload)
        return path.relative_to(self.root).as_posix(), digest

    def load_provider_response(self, relative: str, expected_sha256: str) -> dict[str, Any]:
        self._require_bound()
        path = self._path(relative)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise P1Error("HOLD_RESPONSE_RECEIPT_DRIFT", relative) from exc
        _require(hashlib.sha256(raw).hexdigest() == expected_sha256, "HOLD_RESPONSE_RECEIPT_DRIFT", relative)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise P1Error("HOLD_RESPONSE_RECEIPT_DRIFT", relative) from exc
        _require(
            isinstance(value, dict)
            and raw == canonical_json_bytes(value) + b"\n",
            "HOLD_RESPONSE_RECEIPT_DRIFT",
            relative,
        )
        return value

    def load_completed_call_artifacts(
        self, call_key: str, record: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        self._require_bound()
        filename = hashlib.sha256(call_key.encode("utf-8")).hexdigest() + ".json"
        response_relative = f"provider_responses/{filename}"
        watch_relative = f"fence_watches/{filename}"
        _require(
            record.get("state") == "COMPLETED"
            and record.get("response_path") == response_relative
            and record.get("fence_watch_path") == watch_relative,
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"noncanonical physical paths for {call_key}",
        )
        try:
            response = self.load_provider_response(
                response_relative, str(record.get("response_sha256"))
            )
            watch = self.load_fence_watch(
                watch_relative, str(record.get("fence_watch_sha256"))
            )
        except P1Error as exc:
            raise P1Error(
                "HOLD_RUN_ARTIFACT_DRIFT",
                f"physical call artifact drift for {call_key}: {exc.code}",
            ) from exc
        return response, watch

    def persist_replica(self, replica: Replica, receipt: Mapping[str, Any]) -> tuple[str, str]:
        self._require_bound()
        path = self._path(f"replicas/{replica.key.replace(':', '_')}.json")
        digest = write_json_exclusive(path, receipt)
        return path.relative_to(self.root).as_posix(), digest

    def load_replica(self, replica: Replica) -> tuple[dict[str, Any], str, str] | None:
        self._require_bound()
        path = self._path(f"replicas/{replica.key.replace(':', '_')}.json")
        if not path.exists():
            return None
        raw = path.read_bytes()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise P1Error("HOLD_REPLICA_RECEIPT_DRIFT", replica.key) from exc
        _require(isinstance(value, dict), "HOLD_REPLICA_RECEIPT_DRIFT", replica.key)
        return (
            value,
            path.relative_to(self.root).as_posix(),
            hashlib.sha256(raw).hexdigest(),
        )

    def persist_result(self, payload: Mapping[str, Any]) -> Path:
        self._require_bound()
        path = self._path("result.json")
        write_json_exclusive(path, payload)
        return path

    def load_result(self) -> dict[str, Any] | None:
        self._require_bound()
        path = self._path("result.json")
        if not path.exists():
            return None
        result = load_json_object(path)
        seal = result.get("result_sha256")
        body = {key: value for key, value in result.items() if key != "result_sha256"}
        _require(seal == sha256_json(body), "HOLD_RUN_ARTIFACT_DRIFT", "result seal")
        return result

    def persist_fence_watch(
        self, call_key: str, receipt: Mapping[str, Any]
    ) -> tuple[str, str]:
        self._require_bound()
        filename = hashlib.sha256(call_key.encode()).hexdigest() + ".json"
        path = self._path(f"fence_watches/{filename}")
        digest = write_json_exclusive(path, receipt)
        return path.relative_to(self.root).as_posix(), digest

    def load_fence_watch(self, relative: str, expected_sha256: str) -> dict[str, Any]:
        return self.load_provider_response(relative, expected_sha256)


@dataclass(frozen=True)
class ProviderCall:
    call_key: str
    provider: str
    model: str
    request: Mapping[str, Any]
    run_genesis_sha256: str
    lineage_input_sha256: str
    input_tokens_upper_bound: int
    max_output_tokens: int
    max_retries: int = 0
    prompt_cache: bool = False
    inference_geo: str = "global"
    service_tier: str = "standard_sync"

    @property
    def sealed_envelope(self) -> dict[str, Any]:
        return {
            "call_key": self.call_key,
            "provider": self.provider,
            "model": self.model,
            "request": dict(self.request),
            "run_genesis_sha256": self.run_genesis_sha256,
            "lineage_input_sha256": self.lineage_input_sha256,
            "input_tokens_upper_bound": self.input_tokens_upper_bound,
            "max_output_tokens": self.max_output_tokens,
            "max_retries": self.max_retries,
            "prompt_cache": self.prompt_cache,
            "inference_geo": self.inference_geo,
            "service_tier": self.service_tier,
        }

    @property
    def request_sha256(self) -> str:
        return sha256_json(self.sealed_envelope)


_PROVIDER_CALL_ENVELOPE_KEYS = {
    "call_key",
    "provider",
    "model",
    "request",
    "run_genesis_sha256",
    "lineage_input_sha256",
    "input_tokens_upper_bound",
    "max_output_tokens",
    "max_retries",
    "prompt_cache",
    "inference_geo",
    "service_tier",
}


def provider_call_from_sealed_envelope(
    envelope: Mapping[str, Any],
    *,
    expected_call_key: str,
    spec: CallCostSpec,
    run_genesis: Mapping[str, Any],
) -> ProviderCall:
    """Rebuild and validate one persisted provider intent without delegation."""

    _require(
        isinstance(envelope, Mapping)
        and set(envelope) == _PROVIDER_CALL_ENVELOPE_KEYS
        and isinstance(envelope.get("request"), Mapping),
        "HOLD_RUN_ARTIFACT_DRIFT",
        f"provider envelope shape {expected_call_key}",
    )
    call = ProviderCall(
        call_key=envelope.get("call_key"),
        provider=envelope.get("provider"),
        model=envelope.get("model"),
        request=envelope["request"],
        run_genesis_sha256=envelope.get("run_genesis_sha256"),
        lineage_input_sha256=envelope.get("lineage_input_sha256"),
        input_tokens_upper_bound=envelope.get("input_tokens_upper_bound"),
        max_output_tokens=envelope.get("max_output_tokens"),
        max_retries=envelope.get("max_retries"),
        prompt_cache=envelope.get("prompt_cache"),
        inference_geo=envelope.get("inference_geo"),
        service_tier=envelope.get("service_tier"),
    )
    genesis = verify_run_genesis(run_genesis)
    _require(
        call.sealed_envelope == dict(envelope)
        and call.call_key == expected_call_key == spec.call_key
        and call.provider == spec.provider
        and call.model == spec.model
        and call.max_retries == 0
        and call.prompt_cache is False
        and call.run_genesis_sha256 == genesis["run_genesis_sha256"],
        "HOLD_RUN_ARTIFACT_DRIFT",
        f"provider envelope/spec/genesis binding {expected_call_key}",
    )
    ProviderBoundary._validate_request_envelope(call, spec)
    return call


class PreparedCall(Protocol):
    def send(self) -> Mapping[str, Any]: ...


class PaidCallAdapter(Protocol):
    def prepare(self, call: ProviderCall) -> PreparedCall: ...


class ProviderBoundary:
    def __init__(
        self,
        budget: BudgetPlan,
        journal: CallJournal,
        artifacts: ArtifactStore,
        adapter: PaidCallAdapter,
        *,
        fence_watcher: "FenceWatcher",
        fence_open_receipt: Mapping[str, Any],
        fingerprint_receipt: Mapping[str, Any],
        run_genesis: Mapping[str, Any],
        run_lease: "RunLease",
        runtime_inspector: Callable[[], RuntimeIdentity],
        expected_runtime_identity: RuntimeIdentity,
        now: Callable[[], datetime] | None = None,
    ):
        self.budget = budget
        self.journal = journal
        self.artifacts = artifacts
        self.adapter = adapter
        self.fence_watcher = fence_watcher
        self.fence_open_receipt = json_safe_deep_copy_mapping(
            fence_open_receipt, field="provider_boundary.fence_open_receipt"
        )
        self.fingerprint_receipt = json_safe_deep_copy_mapping(
            fingerprint_receipt,
            field="provider_boundary.fingerprint_receipt",
        )
        self.run_genesis = verify_run_genesis(
            json_safe_deep_copy_mapping(
                run_genesis, field="provider_boundary.run_genesis"
            )
        )
        self.run_lease = run_lease
        self.runtime_inspector = runtime_inspector
        self.expected_runtime_identity = expected_runtime_identity
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.touched_call_keys: list[str] = []
        self._invoke_lock = threading.RLock()

    @staticmethod
    def _request_contains_cache_directive(value: Any) -> bool:
        if isinstance(value, Mapping):
            return any(
                "cache" in str(key).casefold()
                or ProviderBoundary._request_contains_cache_directive(child)
                for key, child in value.items()
            )
        if isinstance(value, list):
            return any(
                ProviderBoundary._request_contains_cache_directive(child)
                for child in value
            )
        return False

    @staticmethod
    def _validate_request_envelope(call: ProviderCall, spec: CallCostSpec) -> None:
        operation = call.call_key.rsplit(":", 1)[-1]
        replica_key = call.call_key.rsplit(":", 1)[0]
        _require(isinstance(call.request, Mapping), "HOLD_ENVELOPE_DRIFT", call.call_key)
        if call.request.get("schema") == "s277_c1_p1_product_provider_intent_v1":
            expected_product_keys = {
                "schema",
                "replica_key",
                "operation",
                "call_key",
                "provider",
                "model",
                "physical_payload",
                "physical_payload_sha256",
                "lineage_input_sha256",
                "run_genesis_sha256",
                "max_output_tokens",
            }
            payload = call.request.get("physical_payload")
            _require(
                set(call.request) == expected_product_keys
                and call.request.get("replica_key") == replica_key
                and call.request.get("operation") == operation
                and call.request.get("call_key") == call.call_key
                and call.request.get("provider") == call.provider == spec.provider
                and call.request.get("model") == call.model == spec.model
                and call.request.get("run_genesis_sha256")
                == call.run_genesis_sha256
                and call.request.get("lineage_input_sha256")
                == call.lineage_input_sha256
                and call.request.get("max_output_tokens")
                == call.max_output_tokens
                and call.max_retries == 0
                and call.prompt_cache is False
                and isinstance(payload, Mapping)
                and call.request.get("physical_payload_sha256")
                == sha256_json(payload),
                "HOLD_ENVELOPE_DRIFT",
                f"product request identity for {call.call_key}",
            )
            derived_bound = physical_input_token_upper_bound(payload)
            _require(
                type(call.input_tokens_upper_bound) is int
                and call.input_tokens_upper_bound == derived_bound
                and call.input_tokens_upper_bound <= spec.max_input_tokens,
                "HOLD_INPUT_TOKEN_BOUND",
                call.call_key,
            )
            _require(
                type(call.max_output_tokens) is int
                and 0 <= call.max_output_tokens <= spec.max_output_tokens
                and (operation == "embedding") == (call.max_output_tokens == 0),
                "HOLD_OUTPUT_TOKEN_BOUND",
                call.call_key,
            )
            if operation == "embedding":
                _require(
                    set(payload)
                    == {"model", "input_type", "texts", "truncation"}
                    and payload.get("model") == call.model
                    and payload.get("input_type") == "query"
                    and payload.get("truncation") is True
                    and isinstance(payload.get("texts"), list)
                    and len(payload["texts"]) == 1
                    and isinstance(payload["texts"][0], str)
                    and bool(payload["texts"][0]),
                    "HOLD_ENVELOPE_DRIFT",
                    f"product embedding payload for {call.call_key}",
                )
            else:
                expected_payload_keys = {
                    "model",
                    "max_tokens",
                    "temperature",
                    "messages",
                }
                if operation == "synthesis":
                    expected_payload_keys.add("system")
                messages = payload.get("messages")
                _require(
                    set(payload) == expected_payload_keys
                    and payload.get("model") == call.model
                    and payload.get("temperature") == 0
                    and payload.get("max_tokens") == call.max_output_tokens
                    and (
                        operation != "synthesis"
                        or (
                            isinstance(payload.get("system"), str)
                            and bool(payload["system"])
                        )
                    )
                    and isinstance(messages, list)
                    and len(messages) == 1
                    and isinstance(messages[0], Mapping)
                    and set(messages[0]) == {"role", "content"}
                    and messages[0].get("role") == "user"
                    and isinstance(messages[0].get("content"), str)
                    and bool(messages[0]["content"]),
                    "HOLD_ENVELOPE_DRIFT",
                    f"product Anthropic controls for {call.call_key}",
                )
            _require(
                not ProviderBoundary._request_contains_cache_directive(call.request)
                and call.inference_geo == "global"
                and call.service_tier == "standard_sync",
                "HOLD_PRICING_DRIFT",
                call.call_key,
            )
            return
        common_keys = {
            "replica_key",
            "operation",
            "model",
            "run_genesis_sha256",
            "lineage_input_sha256",
            "physical_payload",
            "physical_payload_sha256",
            "input_tokens_upper_bound",
            "max_output_tokens",
        }
        expected_keys = common_keys
        _require(
            set(call.request) == expected_keys,
            "HOLD_ENVELOPE_DRIFT",
            f"request shape for {call.call_key}",
        )
        _require(
            call.request.get("operation") == operation
            and call.request.get("replica_key") == replica_key
            and call.request.get("model") == call.model
            and call.request.get("run_genesis_sha256")
            == call.run_genesis_sha256
            and call.request.get("lineage_input_sha256")
            == call.lineage_input_sha256
            and isinstance(call.lineage_input_sha256, str)
            and bool(_HEX64.fullmatch(call.lineage_input_sha256)),
            "HOLD_ENVELOPE_DRIFT",
            f"identity/model fields for {call.call_key}",
        )
        _require(
            isinstance(call.request.get("physical_payload"), Mapping)
            and call.request.get("physical_payload_sha256")
            == sha256_json(call.request["physical_payload"]),
            "HOLD_ENVELOPE_DRIFT",
            f"physical payload seal for {call.call_key}",
        )
        payload = call.request["physical_payload"]
        derived_bound = physical_input_token_upper_bound(payload)
        _require(
            type(call.input_tokens_upper_bound) is int
            and call.input_tokens_upper_bound == derived_bound
            and call.input_tokens_upper_bound <= spec.max_input_tokens,
            "HOLD_INPUT_TOKEN_BOUND",
            call.call_key,
        )
        _require(
            type(call.max_output_tokens) is int
            and call.max_output_tokens == spec.max_output_tokens,
            "HOLD_OUTPUT_TOKEN_BOUND",
            call.call_key,
        )
        _require(
            call.request.get("input_tokens_upper_bound")
            == call.input_tokens_upper_bound
            and call.request.get("max_output_tokens") == call.max_output_tokens,
            "HOLD_ENVELOPE_DRIFT",
            f"token declarations for {call.call_key}",
        )
        if operation == "embedding":
            _require(
                set(payload) == {"model", "input_type", "texts"}
                and payload.get("model") == call.model
                and payload.get("input_type") == "query"
                and isinstance(payload.get("texts"), list)
                and len(payload["texts"]) == 1
                and isinstance(payload["texts"][0], str)
                and bool(payload["texts"][0]),
                "HOLD_ENVELOPE_DRIFT",
                f"embedding payload for {call.call_key}",
            )
        else:
            expected_system = (
                RERANK_INSTRUCTION if operation == "rerank" else SYNTHESIS_SYSTEM_PROMPT
            )
            messages = payload.get("messages")
            _require(
                set(payload)
                == {"model", "max_tokens", "temperature", "messages", "system"}
                and payload.get("model") == call.model
                and payload.get("temperature") == 0
                and payload.get("max_tokens") == call.max_output_tokens
                and payload.get("system") == expected_system
                and isinstance(messages, list)
                and len(messages) == 1
                and isinstance(messages[0], Mapping)
                and set(messages[0]) == {"role", "content"}
                and messages[0].get("role") == "user"
                and isinstance(messages[0].get("content"), str),
                "HOLD_ENVELOPE_DRIFT",
                f"Anthropic controls for {call.call_key}",
            )
        _require(
            not ProviderBoundary._request_contains_cache_directive(call.request),
            "HOLD_CACHE_POLICY_DRIFT",
            call.call_key,
        )
        _require(
            call.inference_geo == "global"
            and call.service_tier == "standard_sync",
            "HOLD_PRICING_DRIFT",
            call.call_key,
        )

    def _validate_frozen_question_before_send(self, call: ProviderCall) -> None:
        """Bind every paid request to the preregistered question before delegation."""

        replica_key, operation = call.call_key.rsplit(":", 1)
        qid = replica_key.split(":", 1)[0]
        input_contract = self.run_genesis["validation_snapshot"]["input_contract"]
        expected_input = input_contract.get(qid)
        _require(
            isinstance(expected_input, Mapping),
            "HOLD_INPUT_REQUEST_BINDING",
            f"missing frozen input for {call.call_key}",
        )
        expected_question = expected_input.get("question")
        payload = call.request.get("physical_payload")
        _require(
            isinstance(expected_question, str)
            and bool(expected_question)
            and isinstance(payload, Mapping),
            "HOLD_INPUT_REQUEST_BINDING",
            call.call_key,
        )
        if operation == "embedding":
            observed_question = payload.get("texts", [None])[0]
            _require(
                observed_question == expected_question
                and call.lineage_input_sha256 == sha256_json(expected_input),
                "HOLD_INPUT_REQUEST_BINDING",
                f"embedding input differs from prereg for {call.call_key}",
            )
            return
        if call.request.get("schema") == "s277_c1_p1_product_provider_intent_v1":
            messages = payload.get("messages")
            content = (
                messages[0].get("content")
                if isinstance(messages, list)
                and len(messages) == 1
                and isinstance(messages[0], Mapping)
                else None
            )
            prefix = (
                "Pregunta del técnico PCI: "
                if operation == "rerank"
                else "Pregunta del técnico: "
            )
            _require(
                isinstance(content, str)
                and content.startswith(f"{prefix}{expected_question}\n"),
                "HOLD_INPUT_REQUEST_BINDING",
                f"product question differs from prereg for {call.call_key}",
            )
            return
        try:
            messages = payload["messages"]
            prompt = json.loads(messages[0]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise P1Error(
                "HOLD_INPUT_REQUEST_BINDING",
                f"provider prompt is not canonical JSON for {call.call_key}",
            ) from exc
        _require(
            isinstance(prompt, Mapping)
            and set(prompt)
            == {"question", "pool" if operation == "rerank" else "served_context"}
            and prompt.get("question") == expected_question,
            "HOLD_INPUT_REQUEST_BINDING",
            f"question differs from prereg for {call.call_key}",
        )

    @staticmethod
    def _validate_completed_response(
        spec: CallCostSpec,
        response: Mapping[str, Any],
        *,
        recorded_actual: Decimal | None = None,
        declared_input_bound: int | None = None,
        declared_output_bound: int | None = None,
    ) -> Decimal:
        usage = response.get("usage")
        _require(isinstance(usage, Mapping), "NO_GO_USAGE_MISSING", spec.call_key)
        input_tokens = usage.get("input_tokens", usage.get("total_tokens"))
        output_tokens = usage.get("output_tokens", 0)
        _require(
            type(input_tokens) is int
            and 0 <= input_tokens <= spec.max_input_tokens,
            "NO_GO_INPUT_TOKEN_BOUND_BREACH",
            spec.call_key,
        )
        _require(
            type(output_tokens) is int
            and 0 <= output_tokens <= spec.max_output_tokens,
            "NO_GO_OUTPUT_TOKEN_BOUND_BREACH",
            spec.call_key,
        )
        if declared_input_bound is not None:
            _require(
                input_tokens <= declared_input_bound,
                "NO_GO_DECLARED_INPUT_BOUND_BREACH",
                spec.call_key,
            )
        if declared_output_bound is not None:
            _require(
                output_tokens <= declared_output_bound,
                "NO_GO_DECLARED_OUTPUT_BOUND_BREACH",
                spec.call_key,
            )
        actual = spec.observed_cost(usage)
        if recorded_actual is not None:
            _require(
                actual == recorded_actual,
                "HOLD_RESPONSE_RECEIPT_DRIFT",
                f"cost drift for {spec.call_key}",
            )
        _require(response.get("model") == spec.model, "NO_GO_MODEL_DRIFT", spec.call_key)
        _require(actual <= spec.max_cost_usd, "NO_GO_COST_BOUND_BREACH", spec.call_key)
        return actual

    def invoke(self, call: ProviderCall) -> dict[str, Any]:
        with self._invoke_lock:
            return self._invoke_serialized(call)

    def invoke_product(self, intent: Any) -> Any:
        """Execute an exact product SDK intent through the canonical WAL/fence.

        The import is intentionally lazy: the product adapter imports this
        module, while the central boundary must also remain usable by the
        offline synthetic tests.
        """

        envelope = getattr(intent, "request", None)
        call_key = getattr(intent, "call_key", None)
        _require(
            isinstance(envelope, Mapping) and isinstance(call_key, str),
            "HOLD_PRODUCT_INTENT_DRIFT",
            "invalid ProductProviderIntent",
        )
        spec = self.budget.specs.get(call_key)
        _require(spec is not None, "HOLD_UNREGISTERED_CALL", call_key)
        call = provider_call_from_sealed_envelope(
            envelope,
            expected_call_key=call_key,
            spec=spec,
            run_genesis=self.run_genesis,
        )
        raw = dict(self.invoke(call))
        raw.pop("_p1_resumed_from_receipt", None)
        transport = raw.pop("_p1_transport_receipt", None)
        _require(
            isinstance(transport, Mapping),
            "NO_GO_PRODUCT_TRANSPORT_RECEIPT",
            call_key,
        )
        from scripts.s277_c1_p1_product_adapter import ProductProviderResult

        return ProductProviderResult(payload=raw, transport_receipt=transport)

    def _invoke_serialized(self, call: ProviderCall) -> dict[str, Any]:
        _require(
            _parse_time(
                self.fingerprint_receipt.get("expires_at"),
                field="fingerprint expires_at",
            )
            > self._now(),
            "HOLD_FINGERPRINT_EXPIRED",
            call.call_key,
        )
        spec = self.budget.specs.get(call.call_key)
        _require(spec is not None, "HOLD_UNREGISTERED_CALL", call.call_key)
        _require(call.provider == spec.provider, "NO_GO_PROVIDER_DRIFT", call.call_key)
        _require(call.model == spec.model, "NO_GO_MODEL_DRIFT", call.call_key)
        _require(call.max_retries == 0, "HOLD_RETRY_POLICY_DRIFT", call.call_key)
        _require(call.prompt_cache is False, "HOLD_CACHE_POLICY_DRIFT", call.call_key)
        _require(
            call.run_genesis_sha256 == self.run_genesis["run_genesis_sha256"]
            == self.journal.run_genesis_sha256
            == self.artifacts.run_genesis_sha256,
            "HOLD_RUN_IDENTITY",
            call.call_key,
        )
        _require(
            call.call_key.rsplit(":", 1)[-1] in CALL_OPERATIONS,
            "HOLD_UNREGISTERED_CALL",
            call.call_key,
        )
        self._validate_request_envelope(call, spec)
        self.touched_call_keys.append(call.call_key)
        existing = self.journal.records.get(call.call_key)
        if existing is not None:
            state = existing["state"]
            if state == "COMPLETED":
                _require(
                    existing.get("request_sha256") == call.request_sha256,
                    "HOLD_REQUEST_REPLAY_DRIFT",
                    call.call_key,
                )
                response, fence_watch = self.artifacts.load_completed_call_artifacts(
                    call.call_key, existing
                )
                verify_persisted_fence_watch_receipt(
                    fence_watch,
                    run_genesis=self.run_genesis,
                    call_key=call.call_key,
                )
                self._validate_completed_response(
                    spec,
                    response,
                    recorded_actual=_decimal(
                        existing.get("actual_cost_usd"), field=call.call_key
                    ),
                    declared_input_bound=call.input_tokens_upper_bound,
                    declared_output_bound=call.max_output_tokens,
                )
                return {**response, "_p1_resumed_from_receipt": True}
            raise NoRetryError("HOLD_CALL_ALREADY_CONSUMED", f"{call.call_key}: {state}")

        self._validate_frozen_question_before_send(call)
        blocked = {
            key: record["state"]
            for key, record in self.journal.records.items()
            if record["state"]
            in {"FAILED_PRE_SEND_NO_RETRY", "UNKNOWN_BILLED_POST_SEND"}
        }
        _require(
            not blocked,
            "HOLD_PRIOR_TERMINAL_CALL",
            json.dumps(blocked, sort_keys=True),
        )
        reserved = {
            key: record["state"]
            for key, record in self.journal.records.items()
            if record["state"] == "RESERVED_FSYNCED"
        }
        _require(
            not reserved,
            "HOLD_PRIOR_NONTERMINAL_CALL",
            json.dumps(reserved, sort_keys=True),
        )
        next_call_key = next(
            (
                key
                for key in expected_call_keys()
                if key not in self.journal.records
            ),
            None,
        )
        _require(
            call.call_key == next_call_key,
            "HOLD_CALL_ORDER_DRIFT",
            f"expected {next_call_key}, got {call.call_key}",
        )
        self.budget.assert_call_allowed(call.call_key, self.journal)
        prior = ZERO
        for key, record in self.journal.records.items():
            if record["state"] == "COMPLETED":
                prior += _decimal(record["actual_cost_usd"], field=key)
            elif record["state"] == "UNKNOWN_BILLED_POST_SEND":
                prior += self.budget.specs[key].max_cost_usd
        self.journal.reserve(
            call_key=call.call_key,
            request_sha256=call.request_sha256,
            max_cost_usd=spec.max_cost_usd,
            accumulated_prior_usd=prior,
        )
        delegated = False
        fence_watch_path: str | None = None
        fence_watch_sha256: str | None = None
        try:
            raw_watch = self.fence_watcher.verify(
                phase="before_provider_send",
                replica=Replica(*call.call_key.rsplit(":", 1)[0].split(":")),
                call_key=call.call_key,
                run_genesis=self.run_genesis,
                fence_open_receipt=self.fence_open_receipt,
            )
            _require(isinstance(raw_watch, Mapping), "HOLD_CORPUS_FENCE_LOST", call.call_key)
            watch = verify_fence_watch_receipt(
                raw_watch,
                open_receipt=self.fence_open_receipt,
                run_genesis=self.run_genesis,
                call_key=call.call_key,
                now=self._now(),
            )
            fence_watch_path, fence_watch_sha256 = self.artifacts.persist_fence_watch(
                call.call_key, watch
            )
            # The strong receipt is the last external-state check before even
            # preparing provider delegation; prepare is required to be local.
            prepared = self.adapter.prepare(call)
            _require(hasattr(prepared, "send"), "FAILED_PRE_SEND", call.call_key)
        except Exception as exc:
            self.journal.terminal(
                call.call_key,
                "FAILED_PRE_SEND_NO_RETRY",
                reason=f"local_pre_send_exception:{type(exc).__name__}",
            )
            if isinstance(exc, P1Error):
                raise
            raise NoRetryError("NO_GO_PRE_SEND_FAILURE", call.call_key) from exc

        try:
            # This assignment is the local delegation boundary.  Every exception
            # from send onward is billed/unknown and terminal; there is no retry.
            verify_fence_watch_receipt(
                watch,
                open_receipt=self.fence_open_receipt,
                run_genesis=self.run_genesis,
                call_key=call.call_key,
                now=self._now(),
            )
            _require(
                _parse_time(
                    self.fingerprint_receipt.get("expires_at"),
                    field="fingerprint expires_at",
                )
                > self._now(),
                "HOLD_FINGERPRINT_EXPIRED",
                call.call_key,
            )
            inspect_and_assert_runtime_identity(
                self.runtime_inspector, self.expected_runtime_identity
            )
            self.run_lease.assert_owned(self.run_genesis)
            current = self.journal.records.get(call.call_key)
            _require(
                current is not None
                and current.get("state") == "RESERVED_FSYNCED"
                and current.get("request_sha256") == call.request_sha256,
                "HOLD_REQUEST_PREPARE_DRIFT",
                f"request changed after reservation for {call.call_key}",
            )
            delegated = True
            raw_response = prepared.send()
            _require(isinstance(raw_response, Mapping), "NO_GO_PROVIDER_RESPONSE", call.call_key)
            response = dict(raw_response)
            relative, response_sha = self.artifacts.persist_provider_response(call.call_key, response)
            usage = response.get("usage")
            _require(isinstance(usage, Mapping), "NO_GO_USAGE_MISSING", call.call_key)
            actual = spec.observed_cost(usage)
            self.journal.terminal(
                call.call_key,
                "COMPLETED",
                reason="response_fsynced",
                actual_cost_usd=actual,
                response_path=relative,
                response_sha256=response_sha,
                fence_watch_path=fence_watch_path,
                fence_watch_sha256=fence_watch_sha256,
            )
            self._validate_completed_response(
                spec,
                response,
                recorded_actual=actual,
                declared_input_bound=call.input_tokens_upper_bound,
                declared_output_bound=call.max_output_tokens,
            )
            observed_total = ZERO
            for key, record in self.journal.records.items():
                if record["state"] == "COMPLETED":
                    observed_total += _decimal(record["actual_cost_usd"], field=key)
                elif record["state"] == "UNKNOWN_BILLED_POST_SEND":
                    observed_total += self.budget.specs[key].max_cost_usd
            _require(
                observed_total <= self.budget.cap_usd,
                "NO_GO_HARD_CAP_EXCEEDED",
                "observed plus unknown cost exceeds the 30 USD cap",
            )
            return response
        except Exception as exc:
            current = self.journal.records[call.call_key]
            if current["state"] == "RESERVED_FSYNCED":
                self.journal.terminal(
                    call.call_key,
                    "UNKNOWN_BILLED_POST_SEND" if delegated else "FAILED_PRE_SEND_NO_RETRY",
                    reason=(
                        "post_delegation_exception:"
                        if delegated
                        else "local_pre_send_exception:"
                    )
                    + type(exc).__name__,
                    fence_watch_path=fence_watch_path,
                    fence_watch_sha256=fence_watch_sha256,
                )
            if isinstance(exc, P1Error):
                raise
            raise NoRetryError("NO_GO_UNKNOWN_BILLED_POST_SEND", call.call_key) from exc


def _artifact_hash(value: Mapping[str, Any]) -> str:
    return sha256_json(value)


def verify_fingerprint_receipt(
    receipt: Mapping[str, Any],
    *,
    release_config_sha256: str,
    now: datetime,
) -> dict[str, Any]:
    _assert_no_secret_material(receipt)
    _require(receipt.get("schema") == FINGERPRINT_SCHEMA, "HOLD_FINGERPRINT_RECEIPT", "schema")
    _require(receipt.get("status") == "PASS", "HOLD_FINGERPRINT_RECEIPT", "status")
    _require(receipt.get("release_config_sha256") == release_config_sha256, "HOLD_FINGERPRINT_RECEIPT", "config")
    _require(receipt.get("function_audit_sha256_lf") == EXPECTED_FUNCTION_AUDIT_SHA256_LF, "HOLD_FINGERPRINT_RECEIPT", "audit hash")
    _require(receipt.get("function_definition_sha256") == EXPECTED_FUNCTION_DEFINITION_SHA256, "HOLD_FINGERPRINT_RECEIPT", "function hash")
    elapsed = receipt.get("elapsed_ms")
    ceiling = receipt.get("ceiling_ms")
    _require(
        isinstance(elapsed, int)
        and ceiling == FINGERPRINT_CEILING_MS
        and 0 <= elapsed <= ceiling,
        "HOLD_FINGERPRINT_CEILING",
        "elapsed/ceiling",
    )
    _require(bool(receipt.get("fingerprint")), "HOLD_FINGERPRINT_RECEIPT", "fingerprint")
    _require(_parse_time(receipt.get("expires_at"), field="expires_at") > now, "HOLD_FINGERPRINT_EXPIRED", "expired")
    return dict(receipt)


def verify_fence_open_receipt(
    receipt: Mapping[str, Any],
    *,
    release_config_sha256: str,
    fingerprint: Any,
    target_semantic_config: Mapping[str, Any],
    now: datetime,
) -> dict[str, Any]:
    _assert_no_secret_material(receipt)
    _require(receipt.get("schema") == FENCE_OPEN_SCHEMA, "HOLD_FENCE_RECEIPT", "schema")
    _require(receipt.get("status") == "OPEN_VERIFIED", "HOLD_FENCE_RECEIPT", "status")
    _require(receipt.get("release_config_sha256") == release_config_sha256, "HOLD_FENCE_RECEIPT", "config")
    _require(receipt.get("initial_fingerprint") == fingerprint, "HOLD_FENCE_RECEIPT", "fingerprint")
    _require(
        receipt.get("persistent_session") is True,
        "HOLD_FENCE_RECEIPT",
        "persistent PostgreSQL session",
    )
    _require(receipt.get("transaction_pooler") is False, "HOLD_FENCE_RECEIPT", "pooler")
    _require(isinstance(receipt.get("backend_pid"), int), "HOLD_FENCE_RECEIPT", "backend pid")
    _require(bool(receipt.get("txid")) and bool(receipt.get("fence_owner")), "HOLD_FENCE_RECEIPT", "owner/txid")
    opened = _parse_time(receipt.get("opened_at"), field="opened_at")
    deadline = _parse_time(receipt.get("deadline_at"), field="deadline_at")
    heartbeat = _parse_time(receipt.get("last_heartbeat_at"), field="last_heartbeat_at")
    _require(
        opened <= heartbeat + FENCE_CLOCK_SKEW
        and heartbeat <= now + FENCE_CLOCK_SKEW
        and now < deadline,
        "HOLD_CORPUS_FENCE_LOST",
        "fence time",
    )
    _require(deadline - opened <= MAX_FENCE_WINDOW, "HOLD_FENCE_RECEIPT", "deadline >45m")
    heartbeat_max_age = receipt.get("heartbeat_max_age_seconds")
    _require(
        isinstance(heartbeat_max_age, int) and 0 < heartbeat_max_age <= 300,
        "HOLD_FENCE_RECEIPT",
        "heartbeat_max_age_seconds",
    )
    _require(
        now - heartbeat <= timedelta(seconds=heartbeat_max_age),
        "HOLD_CORPUS_FENCE_LOST",
        "stale heartbeat",
    )
    relations = receipt.get("relations")
    locks = receipt.get("locks")
    surface = expected_surface(target_semantic_config)
    _require(
        relations == surface["relations"],
        "HOLD_FENCE_RECEIPT",
        "relations must equal the canonical retrieval surface in order",
    )
    _require(isinstance(locks, list) and len(locks) == len(relations), "HOLD_FENCE_RECEIPT", "locks")
    for expected_relation, lock in zip(relations, locks, strict=True):
        _require(isinstance(lock, Mapping), "HOLD_FENCE_RECEIPT", "lock")
        _require(
            set(lock) == {"relation", "mode", "granted"}
            and lock.get("relation") == expected_relation
            and lock.get("mode") == "ShareLock"
            and lock.get("granted") is True,
            "HOLD_CORPUS_FENCE_LOST",
            "canonical lock",
        )
    _require(receipt.get("incompatible_waiters") == [], "HOLD_CORPUS_FENCE_LOST", "waiters")
    _require(
        receipt.get("rpc_manifest_sha256")
        == expected_declared_rpc_surface_sha256(target_semantic_config)
        and receipt.get("physical_manifest_sha256")
        == expected_declared_lock_surface_sha256(target_semantic_config),
        "HOLD_FENCE_RECEIPT",
        "declared synthetic surface hashes",
    )
    return dict(receipt)


def verify_fence_watch_receipt(
    receipt: Mapping[str, Any],
    *,
    open_receipt: Mapping[str, Any],
    run_genesis: Mapping[str, Any],
    call_key: str,
    now: datetime,
) -> dict[str, Any]:
    """Verify a fresh, canonical lock receipt immediately before one send."""

    _assert_no_secret_material(receipt)
    _require(
        set(receipt) == FENCE_WATCH_EXACT_KEYS,
        "HOLD_CORPUS_FENCE_LOST",
        "watch shape",
    )
    _require(
        receipt.get("schema") == FENCE_WATCH_SCHEMA
        and receipt.get("status") == "OPEN_VERIFIED"
        and receipt.get("phase") == "before_provider_send"
        and receipt.get("call_key") == call_key
        and receipt.get("replica_key") == call_key.rsplit(":", 1)[0],
        "HOLD_CORPUS_FENCE_LOST",
        "watch identity",
    )
    verified_genesis = verify_run_genesis(run_genesis)
    _require(
        receipt.get("run_genesis_sha256")
        == verified_genesis["run_genesis_sha256"]
        and receipt.get("release_config_sha256")
        == open_receipt.get("release_config_sha256")
        and receipt.get("fingerprint_sha256")
        == sha256_json(open_receipt.get("initial_fingerprint"))
        and receipt.get("fence_open_receipt_sha256")
        == sha256_json(open_receipt),
        "HOLD_CORPUS_FENCE_LOST",
        "watch run/fingerprint binding",
    )
    for key in (
        "backend_pid",
        "txid",
        "fence_owner",
        "deadline_at",
        "heartbeat_max_age_seconds",
        "relations",
        "locks",
        "rpc_manifest_sha256",
        "physical_manifest_sha256",
    ):
        _require(
            receipt.get(key) == open_receipt.get(key),
            "HOLD_CORPUS_FENCE_LOST",
            f"watch {key}",
        )
    _require(
        receipt.get("relations")
        == expected_surface(run_genesis["target_semantic_config"])["relations"]
        and receipt.get("rpc_manifest_sha256")
        == expected_declared_rpc_surface_sha256(
            run_genesis["target_semantic_config"]
        )
        and receipt.get("physical_manifest_sha256")
        == expected_declared_lock_surface_sha256(
            run_genesis["target_semantic_config"]
        )
        and receipt.get("incompatible_waiters") == [],
        "HOLD_CORPUS_FENCE_LOST",
        "watch canonical surface",
    )
    checked = _parse_time(receipt.get("checked_at"), field="checked_at")
    heartbeat = _parse_time(
        receipt.get("last_heartbeat_at"), field="last_heartbeat_at"
    )
    deadline = _parse_time(receipt.get("deadline_at"), field="deadline_at")
    max_age = receipt.get("heartbeat_max_age_seconds")
    _require(
        isinstance(max_age, int)
        and 0 < max_age <= 300
        and heartbeat <= checked
        and checked <= now + FENCE_CLOCK_SKEW
        and now - checked <= timedelta(seconds=2)
        and checked - heartbeat <= timedelta(seconds=max_age)
        and now - heartbeat <= timedelta(seconds=max_age)
        and now < deadline,
        "HOLD_CORPUS_FENCE_LOST",
        "watch freshness",
    )
    return dict(receipt)


def verify_persisted_fence_watch_receipt(
    receipt: Mapping[str, Any],
    *,
    run_genesis: Mapping[str, Any],
    call_key: str,
) -> dict[str, Any]:
    """Verify historical watch evidence without applying scoring-time freshness."""

    _assert_no_secret_material(receipt)
    _require(
        set(receipt) == FENCE_WATCH_EXACT_KEYS,
        "HOLD_RUN_ARTIFACT_DRIFT",
        f"fence watch shape {call_key}",
    )
    genesis = verify_run_genesis(run_genesis)
    fence = genesis["fence_identity"]
    _require(
        receipt.get("schema") == FENCE_WATCH_SCHEMA
        and receipt.get("status") == "OPEN_VERIFIED"
        and receipt.get("phase") == "before_provider_send"
        and receipt.get("call_key") == call_key
        and receipt.get("replica_key") == call_key.rsplit(":", 1)[0]
        and receipt.get("run_genesis_sha256")
        == genesis["run_genesis_sha256"]
        and receipt.get("release_config_sha256")
        == genesis["release_config_sha256"]
        and receipt.get("fingerprint_sha256") == genesis["fingerprint_sha256"]
        and receipt.get("fence_open_receipt_sha256")
        == genesis["fence_open_receipt_sha256"],
        "HOLD_RUN_ARTIFACT_DRIFT",
        f"fence watch identity {call_key}",
    )
    for key in (
        "backend_pid",
        "txid",
        "fence_owner",
        "deadline_at",
        "heartbeat_max_age_seconds",
        "relations",
        "locks",
        "rpc_manifest_sha256",
        "physical_manifest_sha256",
    ):
        _require(
            receipt.get(key) == fence.get(key),
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"fence watch {key} {call_key}",
        )
    semantic = genesis["target_semantic_config"]
    _require(
        receipt.get("relations") == expected_surface(semantic)["relations"]
        and receipt.get("rpc_manifest_sha256")
        == expected_declared_rpc_surface_sha256(semantic)
        and receipt.get("physical_manifest_sha256")
        == expected_declared_lock_surface_sha256(semantic)
        and receipt.get("incompatible_waiters") == [],
        "HOLD_RUN_ARTIFACT_DRIFT",
        f"fence watch surface {call_key}",
    )
    checked = _parse_time(receipt.get("checked_at"), field="checked_at")
    heartbeat = _parse_time(
        receipt.get("last_heartbeat_at"), field="last_heartbeat_at"
    )
    deadline = _parse_time(receipt.get("deadline_at"), field="deadline_at")
    max_age = receipt.get("heartbeat_max_age_seconds")
    _require(
        isinstance(max_age, int)
        and 0 < max_age <= 300
        and heartbeat <= checked < deadline
        and checked - heartbeat <= timedelta(seconds=max_age),
        "HOLD_RUN_ARTIFACT_DRIFT",
        f"fence watch historical time {call_key}",
    )
    return dict(receipt)


def verify_fence_close_receipt(
    open_receipt: Mapping[str, Any],
    close_receipt: Mapping[str, Any],
    *,
    now: datetime,
    post_manifest_capture: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _assert_no_secret_material(close_receipt)
    _require(close_receipt.get("schema") == FENCE_CLOSE_SCHEMA, "HOLD_FENCE_CLOSE", "schema")
    _require(close_receipt.get("status") == "CLOSED_VERIFIED", "HOLD_FENCE_CLOSE", "status")
    post_manifest_sha256 = close_receipt.get(
        "live_manifest_post_capture_sha256"
    )
    _require(
        isinstance(post_manifest_sha256, str)
        and _HEX64.fullmatch(post_manifest_sha256) is not None,
        "HOLD_FENCE_CLOSE",
        "post live-manifest hash",
    )
    if post_manifest_capture is not None:
        _require(
            post_manifest_sha256 == sha256_json(post_manifest_capture),
            "HOLD_FENCE_CLOSE",
            "post live-manifest binding",
        )
    for key in ("release_config_sha256", "backend_pid", "txid", "fence_owner", "rpc_manifest_sha256", "physical_manifest_sha256"):
        _require(close_receipt.get(key) == open_receipt.get(key), "HOLD_FENCE_CLOSE", key)
    _require(close_receipt.get("initial_fingerprint") == open_receipt.get("initial_fingerprint"), "HOLD_CORPUS_DRIFT", "initial fingerprint")
    _require(close_receipt.get("final_fingerprint") == open_receipt.get("initial_fingerprint"), "HOLD_CORPUS_DRIFT", "final fingerprint")
    _require(
        close_receipt.get("verified_under_lock") is True,
        "HOLD_FENCE_CLOSE",
        "final checks were not verified under lock",
    )
    _require(
        close_receipt.get("relations") == open_receipt.get("relations"),
        "HOLD_FENCE_CLOSE",
        "final relation manifest drift",
    )
    relations = close_receipt.get("relations")
    locks = close_receipt.get("locks")
    _require(
        isinstance(relations, list)
        and relations
        and isinstance(locks, list)
        and len(locks) == len(relations),
        "HOLD_FENCE_CLOSE",
        "final locks missing",
    )
    for expected_relation, lock in zip(relations, locks, strict=True):
        _require(
            isinstance(lock, Mapping)
            and set(lock) == {"relation", "mode", "granted"}
            and lock.get("relation") == expected_relation
            and lock.get("mode") == "ShareLock"
            and lock.get("granted") is True,
            "HOLD_FENCE_CLOSE",
            "final ShareLock lost",
        )
    _require(
        relations
        in (
            list(BASE_FENCE_RELATIONS),
            [*BASE_FENCE_RELATIONS, VISUAL_FENCE_RELATION],
        )
        and close_receipt.get("incompatible_waiters") == [],
        "HOLD_FENCE_CLOSE",
        "final lock coverage/waiters drift",
    )
    visual_surface = relations == [*BASE_FENCE_RELATIONS, VISUAL_FENCE_RELATION]
    surface_semantic = {
        "generation": {"visual_assets_registry": visual_surface}
    }
    _require(
        open_receipt.get("rpc_manifest_sha256")
        == expected_declared_rpc_surface_sha256(surface_semantic)
        and open_receipt.get("physical_manifest_sha256")
        == expected_declared_lock_surface_sha256(surface_semantic),
        "HOLD_FENCE_CLOSE",
        "declared synthetic surface hashes",
    )
    opened_at = _parse_time(open_receipt.get("opened_at"), field="opened_at")
    deadline_at = _parse_time(open_receipt.get("deadline_at"), field="deadline_at")
    closed_at = _parse_time(close_receipt.get("closed_at"), field="closed_at")
    heartbeat_at = _parse_time(
        close_receipt.get("last_heartbeat_at"), field="last_heartbeat_at"
    )
    fingerprint_at = _parse_time(
        close_receipt.get("final_fingerprint_taken_at"),
        field="final_fingerprint_taken_at",
    )
    heartbeat_max_age = open_receipt.get("heartbeat_max_age_seconds")
    _require(
        isinstance(heartbeat_max_age, int) and heartbeat_max_age > 0,
        "HOLD_FENCE_CLOSE",
        "heartbeat policy missing",
    )
    _require(
        opened_at <= fingerprint_at + FENCE_CLOCK_SKEW
        and fingerprint_at <= heartbeat_at
        and heartbeat_at <= closed_at + FENCE_CLOCK_SKEW
        and closed_at <= deadline_at
        and closed_at <= now,
        "HOLD_FENCE_CLOSE",
        "final checks are outside the open fence window",
    )
    _require(
        closed_at - heartbeat_at <= timedelta(seconds=heartbeat_max_age),
        "HOLD_CORPUS_FENCE_LOST",
        "final heartbeat stale before close",
    )
    expires_at = closed_at + P1_TTL
    return {
        "status": "P1_WINDOW_CLOSED_VERIFIED",
        "p1_completed_at": _iso(closed_at),
        "p1_expires_at": _iso(expires_at),
        "expired": now >= expires_at,
        "close_receipt_sha256": _artifact_hash(close_receipt),
    }


@dataclass(frozen=True)
class ExecutionPermit:
    execute: bool
    confirm_paid: bool
    credentials_present: bool
    authorization: Mapping[str, Any]
    authorization_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        snapshot = json_safe_deep_copy_mapping(
            self.authorization, field="execution_permit.authorization"
        )
        object.__setattr__(self, "authorization", snapshot)
        object.__setattr__(self, "authorization_sha256", sha256_json(snapshot))


def verify_execution_permit(
    permit: ExecutionPermit,
    *,
    release_config_sha256: str,
    prereg_sha256: str,
    expected_artifact_identity_sha256: str | None = None,
    stored_control_score_sha256: str | None = None,
    now: datetime,
) -> dict[str, Any]:
    _require(permit.execute, "HOLD_EXECUTE_OPT_IN_REQUIRED", "--execute missing")
    _require(permit.confirm_paid, "HOLD_PAID_OPT_IN_REQUIRED", "--confirm-paid missing")
    _require(permit.credentials_present, "HOLD_CREDENTIALS_REQUIRED", "credentials missing")
    _require(
        sha256_json(permit.authorization) == permit.authorization_sha256,
        "HOLD_PAID_AUTHORIZATION_DRIFT",
        "execution permit authorization changed after construction",
    )
    receipt = json_safe_deep_copy_mapping(
        permit.authorization, field="execution_permit.authorization"
    )
    _assert_no_secret_material(receipt)
    _require(receipt.get("schema") == AUTHORIZATION_SCHEMA, "HOLD_PAID_AUTHORIZATION", "schema")
    _require(receipt.get("status") == "AUTHORIZED", "HOLD_PAID_AUTHORIZATION", "status")
    _require(receipt.get("scope") == "P1_E_27_REPLICAS", "HOLD_PAID_AUTHORIZATION", "scope")
    _require(receipt.get("release_config_sha256") == release_config_sha256, "HOLD_PAID_AUTHORIZATION", "config")
    _require(receipt.get("prereg_sha256") == prereg_sha256, "HOLD_PAID_AUTHORIZATION", "prereg")
    _require(receipt.get("replica_plan_sha256") == REPLICA_PLAN_SHA256, "HOLD_PAID_AUTHORIZATION", "replicas")
    for key in ("authorization_id", "run_id"):
        _require(
            isinstance(receipt.get(key), str)
            and bool(re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", receipt[key])),
            "HOLD_PAID_AUTHORIZATION",
            key,
        )
    _require(
        isinstance(receipt.get("artifact_identity_sha256"), str)
        and bool(_HEX64.fullmatch(receipt["artifact_identity_sha256"])),
        "HOLD_PAID_AUTHORIZATION",
        "artifact identity",
    )
    if expected_artifact_identity_sha256 is not None:
        _require(
            receipt.get("artifact_identity_sha256")
            == expected_artifact_identity_sha256,
            "HOLD_PAID_AUTHORIZATION",
            "authorization is not bound to this artifact root",
        )
    _require(_decimal(receipt.get("max_usd"), field="authorization max") == HARD_CAP_USD, "HOLD_PAID_AUTHORIZATION", "max")
    _require(bool(receipt.get("authorized_by")), "HOLD_PAID_AUTHORIZATION", "authorizer")
    _require(_parse_time(receipt.get("issued_at"), field="issued_at") <= now, "HOLD_PAID_AUTHORIZATION", "issued_at")
    _require(_parse_time(receipt.get("expires_at"), field="expires_at") > now, "HOLD_PAID_AUTHORIZATION", "expired")
    conflict = receipt.get("prepaid_known_conflict")
    _require(isinstance(conflict, Mapping), "HOLD_PREPAID_KNOWN_CONFLICT_RISK", "missing conflict disposition")
    _require(conflict.get("conflict_id") == "conf_26f63590494f", "HOLD_PREPAID_KNOWN_CONFLICT_RISK", "conflict id")
    _require(
        conflict.get("status") in {"RESOLVED_BEFORE_P1", "EXPLICIT_MEASUREMENT_PERMIT"},
        "HOLD_PREPAID_KNOWN_CONFLICT_RISK",
        "stored hp017 conflict is neither fixed nor explicitly permitted",
    )
    _require(bool(conflict.get("rationale")), "HOLD_PREPAID_KNOWN_CONFLICT_RISK", "rationale")
    if stored_control_score_sha256 is not None:
        _require(
            conflict.get("stored_control_score_sha256")
            == stored_control_score_sha256,
            "HOLD_PREPAID_KNOWN_CONFLICT_RISK",
            "permit does not bind the measured stored-control prior",
        )
    return receipt


@dataclass(frozen=True)
class AuthorizationClaimResult:
    claim: Mapping[str, Any]
    created: bool


class AuthorizationClaimStore:
    """Global, atomic one-authorization/one-run claim store."""

    def __init__(self, artifact_root: Path):
        self.artifact_root = artifact_root.resolve()
        self.root = canonical_authorization_claim_root(self.artifact_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def assert_topology(
        self,
        artifact_root: Path,
        *,
        genesis: Mapping[str, Any] | None = None,
    ) -> None:
        resolved_artifact_root = artifact_root.resolve()
        expected_root = canonical_authorization_claim_root(resolved_artifact_root)
        _require(
            self.artifact_root == resolved_artifact_root
            and self.root.resolve() == expected_root
            and self.root != resolved_artifact_root
            and resolved_artifact_root not in self.root.parents,
            "HOLD_RUNTIME_TOPOLOGY",
            "authorization ledger must be derived from artifact_root.parent",
        )
        if genesis is not None:
            _require(
                dict(genesis.get("runtime_layout", {}))
                == canonical_runtime_layout(resolved_artifact_root),
                "HOLD_RUNTIME_TOPOLOGY",
                "authorization ledger runtime layout differs from run genesis",
            )

    def _path(self, authorization_id: str) -> Path:
        filename = hashlib.sha256(authorization_id.encode("utf-8")).hexdigest()
        return self.root / f"{filename}.json"

    def claim(
        self,
        *,
        authorization: Mapping[str, Any],
        genesis: Mapping[str, Any],
        artifact_root: Path,
    ) -> AuthorizationClaimResult:
        verified = verify_run_genesis(genesis)
        resolved_artifact_root = artifact_root.resolve()
        self.assert_topology(resolved_artifact_root, genesis=verified)
        claim = {
            "schema": AUTHORIZATION_CLAIM_SCHEMA,
            "authorization_id": authorization.get("authorization_id"),
            "run_id": authorization.get("run_id"),
            "artifact_identity_sha256": authorization.get(
                "artifact_identity_sha256"
            ),
            "run_genesis_sha256": verified["run_genesis_sha256"],
        }
        _require(
            claim["authorization_id"] == verified["authorization_id"]
            and claim["run_id"] == verified["run_id"]
            and claim["artifact_identity_sha256"]
            == verified["artifact_identity_sha256"]
            and verified["authorization_receipt_sha256"]
            == sha256_json(authorization),
            "HOLD_RUN_IDENTITY",
            "authorization/genesis claim binding",
        )
        path = self._path(str(claim["authorization_id"]))
        created = True
        try:
            write_json_exclusive(path, claim)
        except FileExistsError:
            created = False
            existing = load_json_object(path)
            _require(
                existing == claim,
                "HOLD_AUTHORIZATION_ALREADY_CONSUMED",
                "authorization may resume only the same run and artifact identity",
            )
        return AuthorizationClaimResult(claim=dict(claim), created=created)


class RunLease:
    """Exclusive fail-closed execution lease; existing leases are never reclaimed."""

    def __init__(self, artifact_root: Path):
        self.artifact_root = artifact_root.resolve()
        self.path = canonical_run_lease_path(self.artifact_root)
        self._owned_receipt: dict[str, Any] | None = None

    def assert_topology(self, genesis: Mapping[str, Any]) -> None:
        verified = verify_run_genesis(genesis)
        _require(
            self.path.resolve() == canonical_run_lease_path(self.artifact_root)
            and dict(verified.get("runtime_layout", {}))
            == canonical_runtime_layout(self.artifact_root),
            "HOLD_RUNTIME_TOPOLOGY",
            "run lease differs from the canonical sealed layout",
        )

    def acquire(
        self, genesis: Mapping[str, Any], *, acquired_at: datetime
    ) -> dict[str, Any]:
        verified = verify_run_genesis(genesis)
        self.assert_topology(verified)
        _require(
            self._owned_receipt is None,
            "HOLD_RUN_LEASE_ACTIVE",
            "this runner already owns an execution lease",
        )
        receipt = {
            "schema": RUN_LEASE_SCHEMA,
            "lease_id": os.urandom(32).hex(),
            "authorization_id": verified["authorization_id"],
            "run_id": verified["run_id"],
            "artifact_identity_sha256": verified["artifact_identity_sha256"],
            "run_genesis_sha256": verified["run_genesis_sha256"],
            "runtime_layout_sha256": verified["runtime_layout_sha256"],
            "acquired_at": _iso(acquired_at),
        }
        try:
            write_json_exclusive(self.path, receipt)
        except FileExistsError as exc:
            raise P1Error(
                "HOLD_RUN_LEASE_ACTIVE",
                "canonical execution lease exists; manual recovery is required",
            ) from exc
        self._owned_receipt = receipt
        return dict(receipt)

    def assert_owned(self, genesis: Mapping[str, Any]) -> None:
        self.assert_topology(genesis)
        receipt = self._owned_receipt
        _require(
            receipt is not None
            and self.path.is_file()
            and load_json_object(self.path) == receipt
            and receipt.get("run_genesis_sha256")
            == genesis.get("run_genesis_sha256")
            and receipt.get("runtime_layout_sha256")
            == genesis.get("runtime_layout_sha256"),
            "HOLD_RUN_LEASE_DRIFT",
            "runner no longer owns the canonical execution lease",
        )

    def release_after_result_persisted(self) -> None:
        receipt = self._owned_receipt
        _require(
            receipt is not None,
            "HOLD_RUN_LEASE_DRIFT",
            "runner does not own a releasable lease",
        )
        _require(
            self.path.resolve() == canonical_run_lease_path(self.artifact_root)
            and self.path.is_file()
            and load_json_object(self.path) == receipt,
            "HOLD_RUN_LEASE_DRIFT",
            "canonical execution lease is absent or drifted",
        )
        self.path.unlink()
        _fsync_parent(self.path.parent)
        self._owned_receipt = None


class FenceWatcher(Protocol):
    def verify(
        self,
        *,
        phase: str,
        replica: Replica | None,
        call_key: str,
        run_genesis: Mapping[str, Any],
        fence_open_receipt: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


class ReplicaAdapter(Protocol):
    def execute_replica(
        self, replica: Replica, boundary: ProviderBoundary
    ) -> Mapping[str, Any]: ...


def prereg_input_contract(prereg: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    population = prereg.get("population")
    _require(isinstance(population, Mapping), "HOLD_PREREG_DRIFT", "population")
    rows = population.get("rows")
    _require(isinstance(rows, list), "HOLD_PREREG_DRIFT", "population rows")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, Mapping), "HOLD_PREREG_DRIFT", "population row")
        qid = row.get("qid")
        question = row.get("question")
        target_models = row.get("expected_target_models")
        _require(
            isinstance(qid, str)
            and qid not in result
            and isinstance(question, str)
            and bool(question)
            and isinstance(target_models, list)
            and bool(target_models),
            "HOLD_PREREG_DRIFT",
            "input row identity",
        )
        _require(
            row.get("question_sha256")
            == hashlib.sha256(question.encode("utf-8")).hexdigest()
            and row.get("query_for_retrieval") == "exact_question"
            and row.get("available_models") is None
            and row.get("fresh_single_turn") is True,
            "HOLD_PREREG_DRIFT",
            f"input row contract {qid}",
        )
        result[qid] = {
            "question": question,
            "target_models": list(target_models),
            "query_for_retrieval": question,
            "available_models": None,
        }
    _require(
        set(result) == {replica.qid for replica in REPLICAS},
        "HOLD_PREREG_DRIFT",
        "input QID population",
    )
    return result


_RUN_VALIDATION_SNAPSHOT_KEYS = {
    "schema",
    "release_config_sha256",
    "prereg_sha256",
    "target_semantic_config_sha256",
    "models",
    "models_sha256",
    "input_contract",
    "input_contract_sha256",
    "budget_plan",
    "budget_plan_sha256",
    "implementation_hashes",
    "implementation_hashes_sha256",
}


def _verify_snapshot_input_contract(value: Mapping[str, Any]) -> None:
    expected_qids = {replica.qid for replica in REPLICAS}
    _require(
        isinstance(value, Mapping) and set(value) == expected_qids,
        "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
        "input contract QID set",
    )
    exact_row_keys = {
        "question",
        "target_models",
        "query_for_retrieval",
        "available_models",
    }
    for qid, row in value.items():
        _require(
            isinstance(row, Mapping)
            and set(row) == exact_row_keys
            and isinstance(row.get("question"), str)
            and bool(str(row.get("question")))
            and isinstance(row.get("target_models"), list)
            and bool(row.get("target_models"))
            and all(
                isinstance(model, str) and bool(model)
                for model in row.get("target_models", [])
            )
            and row.get("query_for_retrieval") == row.get("question")
            and row.get("available_models") is None,
            "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
            f"input contract row {qid}",
        )


def build_run_validation_snapshot(bundle: "PreflightBundle") -> dict[str, Any]:
    models = json_safe_deep_copy_mapping(
        bundle.release_config["models"], field="validation_snapshot.models"
    )
    input_contract = prereg_input_contract(bundle.prereg)
    budget_plan = budget_plan_identity(bundle.budget)
    implementation_hashes = json_safe_deep_copy_mapping(
        bundle.release_config["implementation_hashes"],
        field="validation_snapshot.implementation_hashes",
    )
    snapshot = {
        "schema": RUN_VALIDATION_SNAPSHOT_SCHEMA,
        "release_config_sha256": bundle.release_config_sha256,
        "prereg_sha256": bundle.prereg_sha256,
        "target_semantic_config_sha256": sha256_json(
            bundle.release_config["derived_config"]["target_semantic_config"]
        ),
        "models": models,
        "models_sha256": sha256_json(models),
        "input_contract": input_contract,
        "input_contract_sha256": sha256_json(input_contract),
        "budget_plan": budget_plan,
        "budget_plan_sha256": sha256_json(budget_plan),
        "implementation_hashes": implementation_hashes,
        "implementation_hashes_sha256": sha256_json(implementation_hashes),
    }
    _require(
        snapshot["input_contract_sha256"] == bundle.input_contract_sha256
        and snapshot["budget_plan_sha256"] == bundle.budget_sha256,
        "HOLD_PREFLIGHT_SNAPSHOT_DRIFT",
        "run validation snapshot differs from preflight seals",
    )
    return verify_run_validation_snapshot(snapshot)


def verify_run_validation_snapshot(
    snapshot: Mapping[str, Any],
    *,
    genesis: Mapping[str, Any] | None = None,
    verify_current_implementation: bool = False,
) -> dict[str, Any]:
    _require(
        isinstance(snapshot, Mapping)
        and set(snapshot) == _RUN_VALIDATION_SNAPSHOT_KEYS
        and snapshot.get("schema") == RUN_VALIDATION_SNAPSHOT_SCHEMA,
        "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
        "validation snapshot shape",
    )
    for name in (
        "release_config_sha256",
        "prereg_sha256",
        "target_semantic_config_sha256",
        "models_sha256",
        "input_contract_sha256",
        "budget_plan_sha256",
        "implementation_hashes_sha256",
    ):
        _require(
            isinstance(snapshot.get(name), str)
            and bool(_HEX64.fullmatch(str(snapshot[name]))),
            "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
            name,
        )
    models = snapshot.get("models")
    exact_model_keys = {
        "embedding",
        "reranker",
        "generator",
        "temperature",
        "max_tokens",
        "prompt_cache",
        "inference_geo",
        "service_tier",
    }
    _require(
        isinstance(models, Mapping)
        and set(models) == exact_model_keys
        and all(
            isinstance(models.get(name), str) and bool(models.get(name))
            for name in ("embedding", "reranker", "generator")
        )
        and models.get("temperature") == 0
        and type(models.get("max_tokens")) is int
        and models.get("max_tokens", 0) > 0
        and models.get("prompt_cache") is False
        and models.get("inference_geo") in {"global", "default"}
        and models.get("service_tier") == "standard_sync"
        and snapshot.get("models_sha256") == sha256_json(models),
        "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
        "model snapshot",
    )
    input_contract = snapshot.get("input_contract")
    _verify_snapshot_input_contract(input_contract)
    _require(
        snapshot.get("input_contract_sha256") == sha256_json(input_contract),
        "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
        "input contract seal",
    )
    budget_identity = snapshot.get("budget_plan")
    _require(
        isinstance(budget_identity, Mapping)
        and snapshot.get("budget_plan_sha256") == sha256_json(budget_identity),
        "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
        "budget plan seal",
    )
    budget = BudgetPlan.from_identity(budget_identity)
    expected_models = {
        "embedding": models["embedding"],
        "rerank": models["reranker"],
        "synthesis": models["generator"],
    }
    for call_key, spec in budget.specs.items():
        operation = call_key.rsplit(":", 1)[1]
        _require(
            spec.model == expected_models[operation]
            and (
                operation != "synthesis"
                or spec.max_output_tokens == models["max_tokens"]
            ),
            "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
            f"model/budget binding {call_key}",
        )
    implementation_hashes = snapshot.get("implementation_hashes")
    _require(
        isinstance(implementation_hashes, Mapping)
        and set(implementation_hashes) == set(REQUIRED_IMPLEMENTATION_HASHES)
        and snapshot.get("implementation_hashes_sha256")
        == sha256_json(implementation_hashes)
        and all(
            isinstance(value, str) and bool(_HEX64.fullmatch(value))
            for value in implementation_hashes.values()
        ),
        "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
        "implementation manifest snapshot",
    )
    if genesis is not None:
        _require(
            snapshot.get("release_config_sha256")
            == genesis.get("release_config_sha256")
            and snapshot.get("prereg_sha256") == genesis.get("prereg_sha256")
            and snapshot.get("target_semantic_config_sha256")
            == genesis.get("target_semantic_config_sha256"),
            "HOLD_RUN_VALIDATION_SNAPSHOT_DRIFT",
            "snapshot/genesis binding",
        )
    if verify_current_implementation:
        verify_implementation_hashes(implementation_hashes)
    return dict(snapshot)


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def visual_lookup_keys(answer: str, served_context: Sequence[Any]) -> list[dict[str, Any]]:
    """Exact cited (document,page) keys which activate the visual GET side path."""

    result: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for raw_number in re.findall(r"\[F(\d+)\]", answer):
        index = int(raw_number) - 1
        if index < 0 or index >= len(served_context):
            continue
        row = served_context[index]
        if not isinstance(row, Mapping):
            continue
        document_id = row.get("document_id")
        page_index = row.get("page_number")
        if not isinstance(document_id, str) or not document_id or type(page_index) is not int:
            continue
        key = (document_id, page_index)
        if key not in seen:
            seen.add(key)
            result.append({"document_id": document_id, "page_index": page_index})
    return result


def _provider_raw_text(payload: Mapping[str, Any]) -> str:
    content = payload.get("content")
    if isinstance(content, str):
        return content
    if (
        isinstance(content, list)
        and content
        and isinstance(content[0], Mapping)
        and isinstance(content[0].get("text"), str)
    ):
        return str(content[0]["text"])
    raise P1Error("NO_GO_PROVIDER_RESPONSE", "synthesis raw text is absent")


def validate_replica_receipt(
    receipt: Mapping[str, Any],
    replica: Replica,
    models: Mapping[str, Any],
    *,
    expected_input: Mapping[str, Any],
    synthesis_spec: CallCostSpec,
    expected_run_genesis: Mapping[str, Any],
    expected_effective_config: Mapping[str, Any],
) -> None:
    base_receipt_keys = {
        "schema", "replica_key", "qid", "replica_id", "input",
        "run_identity", "effective_config",
        "retrieval", "rerank", "served_context", "structural_fetch",
        "coverage", "must_preserve", "provider", "answer",
        "answer_sha256", "generation_chain", "visual_assets", "render",
        "call_keys", "call_requests",
    }
    _require(
        frozenset(receipt) in {
            frozenset(base_receipt_keys),
            frozenset(base_receipt_keys | {"product_adapter_attestation"}),
        },
        "NO_GO_REPLICA_RECEIPT",
        f"top-level shape {replica.key}",
    )
    _require(receipt.get("schema") == REPLICA_RECEIPT_SCHEMA, "NO_GO_REPLICA_RECEIPT", "schema")
    _require(receipt.get("replica_key") == replica.key, "NO_GO_REPLICA_RECEIPT", "replica key")
    _require(receipt.get("qid") == replica.qid and receipt.get("replica_id") == replica.replica_id, "NO_GO_REPLICA_RECEIPT", "identity")
    genesis = verify_run_genesis(expected_run_genesis)
    expected_run_identity = {
        key: genesis[key]
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
    _require(
        receipt.get("run_identity") == expected_run_identity,
        "NO_GO_RUN_IDENTITY_DRIFT",
        replica.key,
    )
    effective_sha = sha256_json(expected_effective_config)
    expected_effective_receipt = {
        "profile": PROFILE,
        "semantic_config": dict(expected_effective_config),
        "semantic_config_sha256": effective_sha,
        "must_preserve_contract": True,
    }
    _require(
        receipt.get("effective_config") == expected_effective_receipt
        and expected_effective_config.get("coverage", {}).get("release_profile")
        == PROFILE
        and expected_effective_config.get("generation", {}).get(
            "must_preserve_contract"
        )
        is True,
        "NO_GO_EFFECTIVE_CONFIG_DRIFT",
        replica.key,
    )
    input_row = receipt.get("input")
    _require(isinstance(input_row, Mapping), "NO_GO_REPLICA_RECEIPT", "input")
    _require(
        dict(input_row) == dict(expected_input),
        "NO_GO_INPUT_DRIFT",
        f"receipt input does not equal prereg row for {replica.key}",
    )
    retrieval = receipt.get("retrieval")
    rerank = receipt.get("rerank")
    _require(
        isinstance(retrieval, Mapping)
        and set(retrieval)
        == {
            "embedding_receipt",
            "embedding_request_sha256",
            "embedding_response_sha256",
            "pool",
            "pool_sha256",
            "pool_parent_embedding_response_sha256",
        },
        "NO_GO_RETRIEVAL",
        replica.key,
    )
    embedding_receipt = retrieval.get("embedding_receipt")
    _require(isinstance(embedding_receipt, Mapping), "NO_GO_RETRIEVAL", replica.key)
    clean_embedding = dict(embedding_receipt)
    clean_embedding.pop("_p1_resumed_from_receipt", None)
    pool = retrieval.get("pool")
    _require(
        isinstance(pool, list)
        and bool(pool)
        and retrieval.get("embedding_response_sha256")
        == sha256_json(clean_embedding)
        and retrieval.get("pool_sha256") == sha256_json(pool)
        and retrieval.get("pool_parent_embedding_response_sha256")
        == retrieval.get("embedding_response_sha256"),
        "NO_GO_RETRIEVAL_LINEAGE",
        replica.key,
    )
    _require(
        isinstance(rerank, Mapping)
        and set(rerank)
        == {
            "receipt",
            "request_sha256",
            "response_sha256",
            "input_pool_sha256",
            "prefix",
            "prefix_sha256",
            "prefix_parent_rerank_response_sha256",
            "fallback_used",
        },
        "NO_GO_RERANK",
        replica.key,
    )
    rerank_receipt = rerank.get("receipt")
    clean_rerank = dict(rerank_receipt) if isinstance(rerank_receipt, Mapping) else {}
    clean_rerank.pop("_p1_resumed_from_receipt", None)
    prefix = rerank.get("prefix")
    _require(
        isinstance(prefix, list)
        and bool(prefix)
        and rerank.get("input_pool_sha256") == retrieval.get("pool_sha256")
        and rerank.get("response_sha256") == sha256_json(clean_rerank)
        and rerank.get("prefix_sha256") == sha256_json(prefix)
        and rerank.get("prefix_parent_rerank_response_sha256")
        == rerank.get("response_sha256"),
        "NO_GO_RERANK_LINEAGE",
        replica.key,
    )
    _require(rerank.get("fallback_used") is False, "NO_GO_RERANK_FALLBACK", replica.key)
    served_context = receipt.get("served_context")
    _require(isinstance(served_context, list) and served_context, "NO_GO_EMPTY_CONTEXT", replica.key)
    structural = receipt.get("structural_fetch")
    _require(
        isinstance(structural, Mapping)
        and set(structural)
        == {"input_prefix_sha256", "output", "output_sha256"}
        and structural.get("input_prefix_sha256") == rerank.get("prefix_sha256")
        and isinstance(structural.get("output"), list)
        and bool(structural.get("output"))
        and structural.get("output_sha256") == sha256_json(structural["output"]),
        "NO_GO_STRUCTURAL_LINEAGE",
        replica.key,
    )
    coverage = receipt.get("coverage")
    must_preserve = receipt.get("must_preserve")
    _require(
        isinstance(coverage, Mapping)
        and set(coverage)
        == {
            "status",
            "profile",
            "effective_config_sha256",
            "input_context_sha256",
            "output_context",
            "output_context_sha256",
        }
        and coverage.get("status") == "evaluated"
        and coverage.get("profile") == PROFILE
        and coverage.get("effective_config_sha256") == effective_sha
        and coverage.get("input_context_sha256")
        == structural.get("output_sha256")
        and coverage.get("output_context") == served_context
        and coverage.get("output_context_sha256") == sha256_json(served_context),
        "NO_GO_COVERAGE",
        replica.key,
    )
    _require(
        isinstance(must_preserve, Mapping)
        and set(must_preserve)
        == {
            "status",
            "profile",
            "effective_config_sha256",
            "input_answer_sha256",
            "output_answer_sha256",
        }
        and must_preserve.get("status") == "evaluated"
        and must_preserve.get("profile") == PROFILE
        and must_preserve.get("effective_config_sha256") == effective_sha,
        "NO_GO_MUST_PRESERVE",
        replica.key,
    )
    provider = receipt.get("provider")
    _require(isinstance(provider, Mapping), "NO_GO_PROVIDER_RESPONSE", replica.key)
    _require(
        set(provider)
        == {
            "requested_model", "reported_model", "stop_reason", "usage",
            "response_id", "raw_payload",
        },
        "NO_GO_PROVIDER_RESPONSE",
        f"provider shape {replica.key}",
    )
    _require(provider.get("requested_model") == models.get("generator"), "NO_GO_MODEL_DRIFT", replica.key)
    _require(provider.get("reported_model") == models.get("generator"), "NO_GO_MODEL_DRIFT", replica.key)
    _require(provider.get("stop_reason") == "end_turn", "NO_GO_STOP_REASON", replica.key)
    _require(isinstance(provider.get("usage"), Mapping), "NO_GO_USAGE_MISSING", replica.key)
    raw_payload = provider.get("raw_payload")
    _require(isinstance(raw_payload, Mapping), "NO_GO_PROVIDER_RESPONSE", replica.key)
    _require(
        bool(provider.get("response_id"))
        and provider.get("response_id") == raw_payload.get("id")
        and provider.get("reported_model") == raw_payload.get("model")
        and provider.get("stop_reason") == raw_payload.get("stop_reason")
        and dict(provider["usage"]) == raw_payload.get("usage"),
        "NO_GO_PROVIDER_RECEIPT_DRIFT",
        f"top-level provider fields do not equal raw payload for {replica.key}",
    )
    raw_usage = raw_payload.get("usage")
    _require(isinstance(raw_usage, Mapping), "NO_GO_USAGE_MISSING", replica.key)
    _require(
        type(raw_usage.get("input_tokens")) is int
        and 0 <= raw_usage["input_tokens"] <= synthesis_spec.max_input_tokens
        and type(raw_usage.get("output_tokens")) is int
        and 0 <= raw_usage["output_tokens"] < synthesis_spec.max_output_tokens,
        "NO_GO_SYNTHESIS_TOKEN_BOUND",
        f"raw synthesis usage for {replica.key}",
    )
    answer = receipt.get("answer")
    _require(isinstance(answer, str) and bool(answer.strip()), "NO_GO_EMPTY_RESPONSE", replica.key)
    _require(receipt.get("answer_sha256") == _text_sha256(answer), "NO_GO_RESPONSE_HASH", replica.key)
    chain = receipt.get("generation_chain")
    _require(isinstance(chain, Mapping), "NO_GO_GENERATION_CHAIN", replica.key)
    _require(
        set(chain)
        == {
            "raw_payload_sha256",
            "raw_text",
            "raw_text_sha256",
            "stages",
            "final_answer_sha256",
        },
        "NO_GO_GENERATION_CHAIN",
        f"chain shape {replica.key}",
    )
    raw_text = _provider_raw_text(raw_payload)
    raw_text_sha = _text_sha256(raw_text)
    _require(
        chain.get("raw_payload_sha256") == sha256_json(raw_payload)
        and chain.get("raw_text") == raw_text
        and chain.get("raw_text_sha256") == raw_text_sha,
        "NO_GO_GENERATION_CHAIN",
        f"raw response binding {replica.key}",
    )
    stages = chain.get("stages")
    _require(
        isinstance(stages, list) and len(stages) == 3,
        "NO_GO_GENERATION_CHAIN",
        f"stage count {replica.key}",
    )
    previous_sha = raw_text_sha
    previous_text = raw_text
    for expected_name, stage in zip(
        ("diagram_postprocess", "answer_planner", "must_preserve"),
        stages,
        strict=True,
    ):
        _require(
            isinstance(stage, Mapping)
            and set(stage) == {"name", "input_sha256", "output_text", "output_sha256"}
            and stage.get("name") == expected_name
            and stage.get("input_sha256") == previous_sha
            and isinstance(stage.get("output_text"), str)
            and stage.get("output_sha256") == _text_sha256(stage["output_text"]),
            "NO_GO_GENERATION_CHAIN",
            f"{expected_name} binding {replica.key}",
        )
        previous_text = str(stage["output_text"])
        previous_sha = str(stage["output_sha256"])
    _require(
        previous_text == answer
        and previous_sha == receipt.get("answer_sha256")
        and chain.get("final_answer_sha256") == receipt.get("answer_sha256"),
        "NO_GO_GENERATION_CHAIN",
        f"final answer binding {replica.key}",
    )
    _require(
        must_preserve.get("input_answer_sha256")
        == stages[1].get("output_sha256")
        and must_preserve.get("output_answer_sha256")
        == stages[2].get("output_sha256")
        == receipt.get("answer_sha256"),
        "NO_GO_MUST_PRESERVE",
        f"answer lineage {replica.key}",
    )
    visual = receipt.get("visual_assets")
    visual_enabled = expected_effective_config["generation"][
        "visual_assets_registry"
    ]
    eligible_pages = visual_lookup_keys(answer, served_context)
    expected_visual_keys = {
        "enabled",
        "status",
        "effective_config_sha256",
        "input_answer_sha256",
        "input_context_sha256",
        "rest_get_surface",
        "eligible_pages",
        "eligible_pages_sha256",
        "lookup_receipts",
        "selected_assets",
        "selected_assets_sha256",
    }
    _require(
        isinstance(visual, Mapping)
        and set(visual) == expected_visual_keys
        and visual.get("enabled") is visual_enabled
        and visual.get("effective_config_sha256") == effective_sha
        and visual.get("input_answer_sha256") == receipt.get("answer_sha256")
        and visual.get("input_context_sha256") == sha256_json(served_context)
        and visual.get("eligible_pages") == eligible_pages
        and visual.get("eligible_pages_sha256") == sha256_json(eligible_pages)
        and isinstance(visual.get("lookup_receipts"), list)
        and isinstance(visual.get("selected_assets"), list)
        and visual.get("selected_assets_sha256")
        == sha256_json(visual["selected_assets"]),
        "NO_GO_VISUAL_LINEAGE",
        replica.key,
    )
    if not visual_enabled:
        _require(
            visual.get("status") == "not_executed"
            and visual.get("rest_get_surface") == []
            and visual.get("lookup_receipts") == []
            and visual.get("selected_assets") == [],
            "NO_GO_VISUAL_SIDE_PATH_EXECUTED",
            replica.key,
        )
    else:
        _require(
            visual.get("status") == "evaluated"
            and visual.get("rest_get_surface") == [VISUAL_REST_GET_SURFACE]
            and len(visual["lookup_receipts"]) == len(eligible_pages),
            "NO_GO_VISUAL_LINEAGE",
            replica.key,
        )
        response_assets: list[Any] = []
        for page, lookup in zip(
            eligible_pages, visual["lookup_receipts"], strict=True
        ):
            _require(
                isinstance(lookup, Mapping)
                and set(lookup)
                == {"request", "request_sha256", "response", "response_sha256"}
                and lookup.get("request")
                == {
                    "method": "GET",
                    "relation": VISUAL_REST_GET_SURFACE,
                    **page,
                    "technical_utility": "useful",
                    "visual_roles": ["wiring", "table", "procedure", "ui"],
                }
                and lookup.get("request_sha256") == sha256_json(lookup["request"])
                and isinstance(lookup.get("response"), list)
                and lookup.get("response_sha256")
                == sha256_json(lookup["response"]),
                "NO_GO_VISUAL_LINEAGE",
                f"lookup {replica.key}",
            )
            response_assets.extend(lookup["response"])
        _require(
            len(visual["selected_assets"]) <= 4
            and all(asset in response_assets for asset in visual["selected_assets"])
            and all(
                isinstance(asset, Mapping)
                and asset.get("technical_utility") == "useful"
                and asset.get("visual_role")
                in {"wiring", "table", "procedure", "ui"}
                for asset in visual["selected_assets"]
            ),
            "NO_GO_VISUAL_SELECTION",
            replica.key,
        )
    render = receipt.get("render")
    _require(isinstance(render, Mapping) and render.get("render_status") == "ok", "NO_GO_RENDER", replica.key)
    parts = render.get("parts")
    _require(isinstance(parts, list) and parts and all(isinstance(part, str) and part for part in parts), "NO_GO_RENDER", replica.key)
    _require(all(len(part) <= 4096 for part in parts), "NO_GO_RENDER_TRUNCATION", replica.key)
    _require(render.get("source_answer_sha256") == receipt.get("answer_sha256"), "NO_GO_RENDER_DRIFT", replica.key)
    _require(
        render.get("parts_sha256") == sha256_json(parts),
        "NO_GO_RENDER_DRIFT",
        f"render parts hash {replica.key}",
    )
    _require(render.get("complete_source_rendered") is True, "NO_GO_RENDER_TRUNCATION", replica.key)
    _require(render.get("message_parts") == len(parts), "NO_GO_RENDER_DRIFT", replica.key)
    from src.bot.response_formatter import format_telegram_messages

    recomputed_parts = format_telegram_messages(answer)
    _require(
        parts == recomputed_parts,
        "NO_GO_RENDER_DRIFT",
        f"renderer output {replica.key}",
    )
    _require(receipt.get("call_keys") == [f"{replica.key}:{op}" for op in CALL_OPERATIONS], "NO_GO_CALL_RECEIPT", replica.key)
    requests = receipt.get("call_requests")
    _require(
        isinstance(requests, Mapping) and set(requests) == set(CALL_OPERATIONS),
        "NO_GO_CALL_RECEIPT",
        f"missing physical request envelopes for {replica.key}",
    )
    input_sha = sha256_json(expected_input)
    expected_lineages = {
        "embedding": input_sha,
        "rerank": str(retrieval["pool_sha256"]),
        "synthesis": sha256_json(served_context),
    }
    lineage_payloads = {
        "embedding": expected_input,
        "rerank": pool,
        "synthesis": served_context,
    }
    product_mode = all(
        isinstance(requests[operation], Mapping)
        and isinstance(requests[operation].get("request"), Mapping)
        and requests[operation]["request"].get("schema")
        == "s277_c1_p1_product_provider_intent_v1"
        for operation in CALL_OPERATIONS
    )
    for operation in CALL_OPERATIONS:
        envelope = requests[operation]
        _require(isinstance(envelope, Mapping), "NO_GO_CALL_RECEIPT", operation)
        request = envelope.get("request")
        _require(isinstance(request, Mapping), "NO_GO_CALL_RECEIPT", operation)
        if product_mode:
            physical = request.get("physical_payload")
            expected_model = models[
                {
                    "embedding": "embedding",
                    "rerank": "reranker",
                    "synthesis": "generator",
                }[operation]
            ]
            _require(
                set(envelope) == _PROVIDER_CALL_ENVELOPE_KEYS
                and envelope.get("call_key") == f"{replica.key}:{operation}"
                and envelope.get("model") == expected_model
                and envelope.get("run_genesis_sha256")
                == genesis["run_genesis_sha256"]
                and envelope.get("lineage_input_sha256")
                == expected_lineages[operation]
                and request.get("run_genesis_sha256")
                == genesis["run_genesis_sha256"]
                and request.get("lineage_input_sha256")
                == expected_lineages[operation]
                and isinstance(physical, Mapping)
                and request.get("physical_payload_sha256")
                == sha256_json(physical)
                and envelope.get("input_tokens_upper_bound")
                == physical_input_token_upper_bound(physical)
                and request.get("max_output_tokens")
                == envelope.get("max_output_tokens")
                and envelope.get("max_retries") == 0
                and envelope.get("prompt_cache") is False,
                "NO_GO_INPUT_REQUEST_BINDING",
                f"product envelope {replica.key}:{operation}",
            )
            if operation == "embedding":
                _require(
                    physical.get("texts") == [expected_input["question"]],
                    "NO_GO_INPUT_REQUEST_BINDING",
                    f"product embedding {replica.key}",
                )
            else:
                content = physical.get("messages", [{}])[0].get("content")
                question_prefix = (
                    "Pregunta del técnico PCI: "
                    if operation == "rerank"
                    else "Pregunta del técnico: "
                )
                _require(
                    isinstance(content, str)
                    and content.startswith(
                        f"{question_prefix}{expected_input['question']}\n"
                    ),
                    "NO_GO_INPUT_REQUEST_BINDING",
                    f"product prompt {replica.key}:{operation}",
                )
            continue
        expected_payload = build_operation_payload(
            operation=operation,
            model=str(envelope.get("model")),
            question=str(expected_input["question"]),
            lineage_payload=lineage_payloads[operation],
            max_output_tokens=int(envelope.get("max_output_tokens")),
        )
        _require(
            envelope.get("run_genesis_sha256")
            == genesis["run_genesis_sha256"]
            and envelope.get("lineage_input_sha256")
            == expected_lineages[operation]
            and request.get("run_genesis_sha256")
            == genesis["run_genesis_sha256"]
            and request.get("lineage_input_sha256")
            == expected_lineages[operation]
            and request.get("physical_payload") == expected_payload
            and request.get("physical_payload_sha256")
            == sha256_json(expected_payload)
            and envelope.get("input_tokens_upper_bound")
            == physical_input_token_upper_bound(expected_payload)
            and request.get("input_tokens_upper_bound")
            == envelope.get("input_tokens_upper_bound"),
            "NO_GO_INPUT_REQUEST_BINDING",
            f"{replica.key}:{operation}",
        )
    attestation = receipt.get("product_adapter_attestation")
    if product_mode:
        _require(
            isinstance(attestation, Mapping)
            and attestation.get("schema")
            == "s277_c1_p1_product_adapter_attestation_v1"
            and attestation.get("replica_key") == replica.key
            and attestation.get("entrypoint")
            == "src.rag.serving_pipeline.execute_rag_turn"
            and attestation.get("entrypoint_calls") == 1
            and attestation.get("provider_operations") == list(CALL_OPERATIONS)
            and attestation.get("provider_transport_attestation")
            == "RAW_HTTP_RECEIPTS_PERSISTED"
            and attestation.get("postgrest_transport_attestation")
            == "GUARDED_HTTP_RECEIPTS_PERSISTED"
            and isinstance(attestation.get("postgrest_manifest_sha256"), str)
            and bool(
                _HEX64.fullmatch(attestation["postgrest_manifest_sha256"])
            )
            and isinstance(attestation.get("postgrest_request_receipts"), list)
            and bool(attestation["postgrest_request_receipts"])
            and attestation.get("postgrest_request_receipts_sha256")
            == sha256_json(attestation["postgrest_request_receipts"])
            and isinstance(attestation.get("attestation_sha256"), str)
            and attestation.get("attestation_sha256")
            == sha256_json(
                {
                    key: value
                    for key, value in attestation.items()
                    if key != "attestation_sha256"
                }
            ),
            "NO_GO_PRODUCT_ATTESTATION",
            replica.key,
        )
    else:
        _require(
            attestation is None,
            "NO_GO_PRODUCT_ATTESTATION",
            f"unexpected attestation {replica.key}",
        )
    _require(
        retrieval.get("embedding_request_sha256")
        == sha256_json(requests["embedding"])
        and rerank.get("request_sha256") == sha256_json(requests["rerank"]),
        "NO_GO_LINEAGE_REQUEST_BINDING",
        replica.key,
    )


@dataclass(frozen=True)
class PreflightBundle:
    release_config: Mapping[str, Any]
    prereg: Mapping[str, Any]
    fingerprint_receipt: Mapping[str, Any]
    fence_open_receipt: Mapping[str, Any]
    runtime_identity: RuntimeIdentity
    release_config_sha256: str
    prereg_sha256: str
    fingerprint_receipt_sha256: str
    fence_open_receipt_sha256: str
    runtime_identity_sha256: str
    stored_control_score_sha256: str
    budget_sha256: str
    input_contract_sha256: str
    budget: BudgetPlan


def build_run_genesis(
    bundle: PreflightBundle,
    authorization: Mapping[str, Any],
    artifact_root: Path,
) -> dict[str, Any]:
    target_semantic = bundle.release_config["derived_config"][
        "target_semantic_config"
    ]
    fence = bundle.fence_open_receipt
    runtime_layout = canonical_runtime_layout(artifact_root)
    validation_snapshot = build_run_validation_snapshot(bundle)
    body = {
        "schema": RUN_GENESIS_SCHEMA,
        "authorization_id": authorization.get("authorization_id"),
        "run_id": authorization.get("run_id"),
        "artifact_identity_sha256": artifact_identity_sha256(
            str(authorization.get("run_id")), artifact_root
        ),
        "runtime_layout": runtime_layout,
        "runtime_layout_sha256": sha256_json(runtime_layout),
        "authorization_receipt_sha256": sha256_json(authorization),
        "release_config_sha256": bundle.release_config_sha256,
        "prereg_sha256": bundle.prereg_sha256,
        "tested_commit_sha": bundle.release_config["candidate"]["tested_commit_sha"],
        "tested_tree_sha": bundle.release_config["candidate"]["tested_tree_sha"],
        "target_semantic_config": target_semantic,
        "target_semantic_config_sha256": sha256_json(target_semantic),
        "fingerprint_receipt_sha256": sha256_json(bundle.fingerprint_receipt),
        "fingerprint_sha256": sha256_json(
            bundle.fingerprint_receipt["fingerprint"]
        ),
        "fence_open_receipt_sha256": sha256_json(bundle.fence_open_receipt),
        "fence_identity": {
            key: fence[key]
            for key in (
                "backend_pid",
                "txid",
                "fence_owner",
                "deadline_at",
                "heartbeat_max_age_seconds",
                "relations",
                "locks",
                "rpc_manifest_sha256",
                "physical_manifest_sha256",
            )
        },
        "replica_plan_sha256": REPLICA_PLAN_SHA256,
        "call_plan_sha256": CALL_PLAN_SHA256,
        "validation_snapshot": validation_snapshot,
        "validation_snapshot_sha256": sha256_json(validation_snapshot),
    }
    genesis = {**body, "run_genesis_sha256": sha256_json(body)}
    return verify_run_genesis(genesis)


def build_preflight_bundle(
    *,
    release_config: Mapping[str, Any],
    prereg: Mapping[str, Any],
    fingerprint_receipt: Mapping[str, Any],
    fence_open_receipt: Mapping[str, Any],
    runtime: RuntimeIdentity,
    now: datetime,
) -> PreflightBundle:
    release_config = json_safe_deep_copy_mapping(
        release_config, field="release_config"
    )
    prereg = json_safe_deep_copy_mapping(prereg, field="prereg")
    fingerprint_receipt = json_safe_deep_copy_mapping(
        fingerprint_receipt, field="fingerprint_receipt"
    )
    fence_open_receipt = json_safe_deep_copy_mapping(
        fence_open_receipt, field="fence_open_receipt"
    )
    runtime_payload = runtime_identity_payload(runtime)
    verify_release_config(release_config, runtime, now=now)
    verify_prereg_sealed_inputs(prereg)
    verify_prereg_release_identity(prereg)
    verify_prereg_runtime_contract(prereg)
    verify_model_extraction_contract(prereg)
    release_hash = _artifact_hash(release_config)
    prereg_hash = _artifact_hash(prereg)
    budget = BudgetPlan.from_prereg(prereg)
    expected_models = operation_models(release_config)
    for operation, model in expected_models.items():
        _require(
            budget.specs[f"{REPLICA_ORDER[0]}:{operation}"].model == model,
            "HOLD_MODEL_PREREG_DRIFT",
            operation,
        )
    _require(
        budget.specs[f"{REPLICA_ORDER[0]}:synthesis"].max_output_tokens
        == release_config["models"]["max_tokens"],
        "HOLD_MODEL_PREREG_DRIFT",
        "generator max_tokens differs from cost envelope",
    )
    price_contract = {
        "embedding": ("voyage", Decimal("0.12"), Decimal("0")),
        "rerank": ("anthropic", Decimal("3"), Decimal("15")),
        "synthesis": ("anthropic", Decimal("3"), Decimal("15")),
    }
    for operation, (provider, input_rate, output_rate) in price_contract.items():
        spec = budget.specs[f"{REPLICA_ORDER[0]}:{operation}"]
        _require(
            (spec.provider, spec.input_usd_per_mtok, spec.output_usd_per_mtok)
            == (provider, input_rate, output_rate),
            "HOLD_PRICING_DRIFT",
            operation,
        )
    fingerprint = verify_fingerprint_receipt(
        fingerprint_receipt, release_config_sha256=release_hash, now=now
    )
    verify_fence_open_receipt(
        fence_open_receipt,
        release_config_sha256=release_hash,
        fingerprint=fingerprint["fingerprint"],
        target_semantic_config=release_config["derived_config"][
            "target_semantic_config"
        ],
        now=now,
    )
    calls = prereg.get("model_calls")
    _require(isinstance(calls, Mapping), "HOLD_PREREG_SCHEMA", "model_calls")
    _require(calls.get("expected") == {
        "voyage_embedding": 27,
        "sonnet_rerank": 27,
        "sonnet_synthesis": 27,
        "total": 81,
    }, "HOLD_CALL_PLAN_DRIFT", "model call counts")
    _require(prereg.get("authorization", {}).get("paid_execution") is False, "HOLD_PREREG_DRIFT", "prereg cannot authorize spend")
    from scripts.s277_c1_p1_scorer import load_fact_contract, score_stored_controls

    contract_path = _sealed_path(
        prereg["sealed_inputs"]["fact_contract"]["path"]
    )
    stored_control = score_stored_controls(
        contract=load_fact_contract(contract_path)
    )
    _require(
        stored_control.get("status") == "REVIEW"
        and stored_control.get("decision") == "HOLD_PREPAID_KNOWN_CONFLICT_RISK"
        and stored_control.get("confirmed_3_of_3") is True
        and stored_control.get("candidate_runtime_measured") is False
        and stored_control.get("paid_model_calls") == 0,
        "HOLD_PREPAID_KNOWN_CONFLICT_RISK",
        "stored-control prior drifted",
    )
    input_contract = prereg_input_contract(prereg)
    budget_identity = budget_plan_identity(budget)
    return PreflightBundle(
        release_config=release_config,
        prereg=prereg,
        fingerprint_receipt=fingerprint_receipt,
        fence_open_receipt=fence_open_receipt,
        runtime_identity=runtime,
        release_config_sha256=release_hash,
        prereg_sha256=prereg_hash,
        fingerprint_receipt_sha256=sha256_json(fingerprint_receipt),
        fence_open_receipt_sha256=sha256_json(fence_open_receipt),
        runtime_identity_sha256=sha256_json(runtime_payload),
        stored_control_score_sha256=sha256_json(stored_control),
        budget_sha256=sha256_json(budget_identity),
        input_contract_sha256=sha256_json(input_contract),
        budget=budget,
    )


class P1Runner:
    """Execute the sealed plan only through injected provider/fence adapters."""

    def __init__(
        self,
        *,
        bundle: PreflightBundle,
        permit: ExecutionPermit,
        artifacts: ArtifactStore,
        journal: CallJournal,
        provider_adapter: PaidCallAdapter,
        replica_adapter: ReplicaAdapter,
        fence_watcher: FenceWatcher,
        authorization_claims: AuthorizationClaimStore,
        scorer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        runtime_inspector: Callable[[], RuntimeIdentity] | None = None,
        now: Callable[[], datetime] | None = None,
    ):
        self.bundle = bundle
        self.permit = permit
        self.artifacts = artifacts
        self.journal = journal
        self.provider_adapter = provider_adapter
        self.replica_adapter = replica_adapter
        self.fence_watcher = fence_watcher
        self.authorization_claims = authorization_claims
        self.scorer = scorer
        self.runtime_inspector = runtime_inspector or inspect_runtime_identity
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.boundary: ProviderBoundary | None = None
        self.run_genesis: dict[str, Any] | None = None
        self.expected_inputs = prereg_input_contract(bundle.prereg)

    def _revalidate_preflight_at_execution_start(
        self, *, now: datetime
    ) -> None:
        bundle = self.bundle
        current_inputs = prereg_input_contract(bundle.prereg)
        _require(
            sha256_json(bundle.release_config) == bundle.release_config_sha256
            and sha256_json(bundle.prereg) == bundle.prereg_sha256
            and sha256_json(bundle.fingerprint_receipt)
            == bundle.fingerprint_receipt_sha256
            and sha256_json(bundle.fence_open_receipt)
            == bundle.fence_open_receipt_sha256
            and sha256_json(runtime_identity_payload(bundle.runtime_identity))
            == bundle.runtime_identity_sha256
            and sha256_json(budget_plan_identity(bundle.budget))
            == bundle.budget_sha256
            and sha256_json(current_inputs) == bundle.input_contract_sha256
            and current_inputs == self.expected_inputs,
            "HOLD_PREFLIGHT_SNAPSHOT_DRIFT",
            "sealed preflight bundle changed after construction",
        )
        fresh_runtime = inspect_and_assert_runtime_identity(
            self.runtime_inspector, bundle.runtime_identity
        )
        rebuilt = build_preflight_bundle(
            release_config=bundle.release_config,
            prereg=bundle.prereg,
            fingerprint_receipt=bundle.fingerprint_receipt,
            fence_open_receipt=bundle.fence_open_receipt,
            runtime=fresh_runtime,
            now=now,
        )
        rebuilt_inputs = prereg_input_contract(rebuilt.prereg)
        _require(
            rebuilt.release_config == bundle.release_config
            and rebuilt.prereg == bundle.prereg
            and rebuilt.fingerprint_receipt == bundle.fingerprint_receipt
            and rebuilt.fence_open_receipt == bundle.fence_open_receipt
            and rebuilt.runtime_identity == bundle.runtime_identity
            and rebuilt.release_config_sha256 == bundle.release_config_sha256
            and rebuilt.prereg_sha256 == bundle.prereg_sha256
            and rebuilt.fingerprint_receipt_sha256
            == bundle.fingerprint_receipt_sha256
            and rebuilt.fence_open_receipt_sha256
            == bundle.fence_open_receipt_sha256
            and rebuilt.runtime_identity_sha256 == bundle.runtime_identity_sha256
            and rebuilt.stored_control_score_sha256
            == bundle.stored_control_score_sha256
            and rebuilt.budget_sha256 == bundle.budget_sha256
            and rebuilt.input_contract_sha256 == bundle.input_contract_sha256
            and rebuilt_inputs == self.expected_inputs,
            "HOLD_PREFLIGHT_REVALIDATION_DRIFT",
            "execution-start preflight differs from the sealed preflight",
        )
        self.bundle = rebuilt
        self.expected_inputs = rebuilt_inputs

    def _verify_physical_bindings(
        self, receipt: Mapping[str, Any], replica: Replica
    ) -> None:
        observed_responses = {
            "embedding": receipt["retrieval"]["embedding_receipt"],
            "rerank": receipt["rerank"]["receipt"],
            "synthesis": receipt["provider"]["raw_payload"],
        }
        requests = receipt["call_requests"]
        for operation in CALL_OPERATIONS:
            call_key = f"{replica.key}:{operation}"
            record = self.journal.records.get(call_key)
            _require(
                record is not None and record["state"] == "COMPLETED",
                "NO_GO_CALL_RECEIPT",
                call_key,
            )
            _require(
                sha256_json(requests[operation]) == record["request_sha256"],
                "NO_GO_ENVELOPE_DRIFT",
                call_key,
            )
            physical, fence_watch = self.artifacts.load_completed_call_artifacts(
                call_key, record
            )
            physical = dict(physical)
            transport = physical.pop("_p1_transport_receipt", None)
            observed = dict(observed_responses[operation])
            observed.pop("_p1_resumed_from_receipt", None)
            attestation = receipt.get("product_adapter_attestation")
            if attestation is not None:
                _require(
                    isinstance(transport, Mapping)
                    and isinstance(attestation, Mapping)
                    and attestation.get("transport_receipt_sha256s", {}).get(
                        operation
                    )
                    == sha256_json(transport),
                    "NO_GO_PRODUCT_TRANSPORT_RECEIPT",
                    call_key,
                )
            _require(
                sha256_json(observed) == sha256_json(physical),
                "NO_GO_PROVIDER_RECEIPT_DRIFT",
                call_key,
            )
            verify_persisted_fence_watch_receipt(
                fence_watch,
                run_genesis=self.run_genesis,
                call_key=call_key,
            )

    def _budget_summary(self) -> dict[str, Any]:
        actual = ZERO
        unknown = ZERO
        for key, record in self.journal.records.items():
            if record["state"] == "COMPLETED":
                actual += _decimal(record["actual_cost_usd"], field=key)
            elif record["state"] == "UNKNOWN_BILLED_POST_SEND":
                unknown += self.bundle.budget.specs[key].max_cost_usd
        return {
            "cap_usd": _money(self.bundle.budget.cap_usd),
            "observed_list_price_usd": _money(actual),
            "unknown_reserved_usd": _money(unknown),
            "projected_total_usd": _money(self.bundle.budget.projected_total(self.journal)),
        }

    def _result(
        self,
        *,
        status: str,
        code: str,
        started_at: datetime,
        replica_receipts: list[dict[str, Any]],
        early_abort_checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        completed_at = self._now()
        body = {
            "schema": RESULT_SCHEMA,
            "status": status,
            "code": code,
            "started_at": _iso(started_at),
            "replicas_completed_at": _iso(completed_at),
            "p1_completed_at": None,
            "p1_expires_at": None,
            "release_config_sha256": self.bundle.release_config_sha256,
            "prereg_sha256": self.bundle.prereg_sha256,
            "authorization_id": self.run_genesis["authorization_id"],
            "run_id": self.run_genesis["run_id"],
            "artifact_identity_sha256": self.run_genesis[
                "artifact_identity_sha256"
            ],
            "authorization_receipt_sha256": self.run_genesis[
                "authorization_receipt_sha256"
            ],
            "run_genesis_sha256": self.run_genesis["run_genesis_sha256"],
            "runtime_layout_sha256": self.run_genesis[
                "runtime_layout_sha256"
            ],
            "target_semantic_config_sha256": self.run_genesis[
                "target_semantic_config_sha256"
            ],
            "validation_snapshot_sha256": self.run_genesis[
                "validation_snapshot_sha256"
            ],
            "implementation_hashes_sha256": self.run_genesis[
                "validation_snapshot"
            ]["implementation_hashes_sha256"],
            "fingerprint_receipt_sha256": sha256_json(
                self.bundle.fingerprint_receipt
            ),
            "fence_open_receipt_sha256": sha256_json(
                self.bundle.fence_open_receipt
            ),
            "tested_commit_sha": self.bundle.release_config["candidate"]["tested_commit_sha"],
            "tested_tree_sha": self.bundle.release_config["candidate"]["tested_tree_sha"],
            "replica_plan_sha256": REPLICA_PLAN_SHA256,
            "call_plan_sha256": CALL_PLAN_SHA256,
            "replicas_expected": len(REPLICAS),
            "replicas_persisted": len(replica_receipts),
            "replica_receipts": replica_receipts,
            "non_authoritative_early_abort_checks": early_abort_checks,
            "wal_head_sha256": self.journal.head_sha256,
            "budget": self._budget_summary(),
            "paid_adapter_is_injected": True,
            "railway_mutations": 0,
            "supabase_mutations": 0,
        }
        return {**body, "result_sha256": sha256_json(body)}

    def run(self) -> dict[str, Any]:
        started_at = self._now()
        self._revalidate_preflight_at_execution_start(now=started_at)
        self.artifacts.assert_topology()
        self.journal.assert_topology(self.artifacts.root)
        self.authorization_claims.assert_topology(self.artifacts.root)
        authorization = self.permit.authorization
        run_id = authorization.get("run_id")
        expected_artifact_identity = artifact_identity_sha256(
            str(run_id), self.artifacts.root
        )
        verified_authorization = verify_execution_permit(
            self.permit,
            release_config_sha256=self.bundle.release_config_sha256,
            prereg_sha256=self.bundle.prereg_sha256,
            expected_artifact_identity_sha256=expected_artifact_identity,
            stored_control_score_sha256=self.bundle.stored_control_score_sha256,
            now=started_at,
        )
        verify_railway_snapshot_freshness(
            self.bundle.release_config["railway"], now=started_at
        )
        verified_fingerprint = verify_fingerprint_receipt(
            self.bundle.fingerprint_receipt,
            release_config_sha256=self.bundle.release_config_sha256,
            now=started_at,
        )
        verify_fence_open_receipt(
            self.bundle.fence_open_receipt,
            release_config_sha256=self.bundle.release_config_sha256,
            fingerprint=verified_fingerprint["fingerprint"],
            target_semantic_config=self.bundle.release_config["derived_config"][
                "target_semantic_config"
            ],
            now=started_at,
        )
        _require(
            _parse_time(
                verified_authorization.get("expires_at"),
                field="authorization expires_at",
            )
            >= _parse_time(
                self.bundle.fence_open_receipt.get("deadline_at"),
                field="fence deadline_at",
            ),
            "HOLD_PAID_AUTHORIZATION",
            "authorization must cover the complete fence window",
        )
        genesis = build_run_genesis(
            self.bundle, verified_authorization, self.artifacts.root
        )
        _require(
            genesis["artifact_identity_sha256"]
            == verified_authorization["artifact_identity_sha256"],
            "HOLD_PAID_AUTHORIZATION",
            "artifact identity",
        )
        self.artifacts.assert_topology(genesis=genesis)
        self.journal.assert_topology(self.artifacts.root, genesis=genesis)
        self.authorization_claims.assert_topology(
            self.artifacts.root, genesis=genesis
        )
        inspect_and_assert_runtime_identity(
            self.runtime_inspector, self.bundle.runtime_identity
        )
        lease = RunLease(self.artifacts.root)
        lease.acquire(genesis, acquired_at=started_at)
        self.journal.assert_unchanged_since_open()
        claim_result = self.authorization_claims.claim(
            authorization=verified_authorization,
            genesis=genesis,
            artifact_root=self.artifacts.root,
        )
        if claim_result.created:
            self.artifacts.require_new_claim_state()
            self.journal.require_new_claim_state(self.artifacts.root)
        else:
            self.artifacts.require_existing_resume_state(genesis)
            self.journal.require_existing_resume_state(
                self.artifacts.root, genesis
            )
        self.artifacts.bind_genesis(genesis)
        self.journal.bind_genesis(genesis)
        self.run_genesis = genesis
        self.boundary = ProviderBoundary(
            self.bundle.budget,
            self.journal,
            self.artifacts,
            self.provider_adapter,
            fence_watcher=self.fence_watcher,
            fence_open_receipt=self.bundle.fence_open_receipt,
            fingerprint_receipt=self.bundle.fingerprint_receipt,
            run_genesis=genesis,
            run_lease=lease,
            runtime_inspector=self.runtime_inspector,
            expected_runtime_identity=self.bundle.runtime_identity,
            now=self._now,
        )
        existing_result = self.artifacts.load_result()
        if existing_result is not None:
            _require(
                existing_result.get("release_config_sha256")
                == self.bundle.release_config_sha256
                and existing_result.get("prereg_sha256") == self.bundle.prereg_sha256
                and existing_result.get("run_genesis_sha256")
                == genesis["run_genesis_sha256"]
                and existing_result.get("validation_snapshot_sha256")
                == genesis["validation_snapshot_sha256"]
                and existing_result.get("implementation_hashes_sha256")
                == genesis["validation_snapshot"][
                    "implementation_hashes_sha256"
                ],
                "HOLD_RUN_ARTIFACT_DRIFT",
                "existing result belongs to another run identity",
            )
            if (
                existing_result.get("status")
                == "P1_REPLICAS_COMPLETE_PENDING_FENCE_CLOSE"
            ):
                reopened_result, _reopened_replicas = load_run_replicas(
                    self.artifacts.root
                )
                _require(
                    reopened_result == existing_result,
                    "HOLD_RUN_ARTIFACT_DRIFT",
                    "reopened completed result differs from the bound result",
                )
            lease.release_after_result_persisted()
            return existing_result
        replica_receipts: list[dict[str, Any]] = []
        early_abort_checks: list[dict[str, Any]] = []
        try:
            blocked = {
                key: row["state"]
                for key, row in self.journal.records.items()
                if row["state"] in {
                    "FAILED_PRE_SEND_NO_RETRY",
                    "UNKNOWN_BILLED_POST_SEND",
                }
            }
            _require(not blocked, "HOLD_PRIOR_TERMINAL_CALL", json.dumps(blocked, sort_keys=True))
            for replica in REPLICAS:
                stored_receipt = self.artifacts.load_replica(replica)
                if stored_receipt is not None:
                    receipt, relative, digest = stored_receipt
                else:
                    _require(self.boundary is not None, "HOLD_RUN_IDENTITY", "boundary")
                    call_start = len(self.boundary.touched_call_keys)
                    raw_receipt = self.replica_adapter.execute_replica(replica, self.boundary)
                    if isinstance(raw_receipt, Mapping):
                        receipt = dict(raw_receipt)
                    else:
                        product_receipt = getattr(raw_receipt, "receipt", None)
                        product_attestation = getattr(
                            raw_receipt, "adapter_attestation", None
                        )
                        _require(
                            isinstance(product_receipt, Mapping)
                            and isinstance(product_attestation, Mapping),
                            "NO_GO_REPLICA_RECEIPT",
                            replica.key,
                        )
                        receipt = dict(product_receipt)
                        receipt["product_adapter_attestation"] = dict(
                            product_attestation
                        )
                    expected_keys = [f"{replica.key}:{op}" for op in CALL_OPERATIONS]
                    touched = self.boundary.touched_call_keys[call_start:]
                    _require(touched == expected_keys, "NO_GO_CALL_PLAN_DRIFT", replica.key)
                    receipt.setdefault("call_keys", expected_keys)
                    relative, digest = self.artifacts.persist_replica(replica, receipt)
                stored = {"replica_key": replica.key, "path": relative, "sha256": digest}
                replica_receipts.append(stored)
                # High-level checks happen only after the complete receipt is durable.
                validate_replica_receipt(
                    receipt,
                    replica,
                    self.bundle.release_config["models"],
                    expected_input=self.expected_inputs[replica.qid],
                    synthesis_spec=self.bundle.budget.specs[
                        f"{replica.key}:synthesis"
                    ],
                    expected_run_genesis=genesis,
                    expected_effective_config=self.bundle.release_config[
                        "derived_config"
                    ]["target_semantic_config"],
                )
                self._verify_physical_bindings(receipt, replica)
                score = dict(self.scorer(receipt))
                early_abort_checks.append(
                    {
                        "replica_key": replica.key,
                        **score,
                        "authority": "NON_AUTHORITATIVE_EARLY_ABORT_ONLY",
                    }
                )
                if score.get("status") in {"FAIL", "INSTRUMENT_ERROR", "ADJUDICATED_FAIL"}:
                    raise P1Error("NO_GO_PROTECTED_CONTRACT", replica.key)
            _require(len(replica_receipts) == 27, "NO_GO_REPLICA_COUNT", "not 27")
            _require(len(self.journal.records) == 81, "NO_GO_CALL_COUNT", "not 81")
            result = self._result(
                status="P1_REPLICAS_COMPLETE_PENDING_FENCE_CLOSE",
                code="HOLD_PENDING_FINAL_FINGERPRINT_AND_FENCE_CLOSE",
                started_at=started_at,
                replica_receipts=replica_receipts,
                early_abort_checks=early_abort_checks,
            )
        except Exception as exc:
            code = exc.code if isinstance(exc, P1Error) else "NO_GO_UNCLASSIFIED_EXCEPTION"
            result = self._result(
                status="NO_GO_PARTIAL" if self.journal.records else "HOLD",
                code=code,
                started_at=started_at,
                replica_receipts=replica_receipts,
                early_abort_checks=early_abort_checks,
            )
            result["error_type"] = type(exc).__name__
            result.pop("result_sha256", None)
            result["result_sha256"] = sha256_json(result)
        self.artifacts.persist_result(result)
        lease.release_after_result_persisted()
        return result


def _json_output(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _offline_cli_preflight(args: argparse.Namespace) -> dict[str, Any]:
    release = load_json_object(Path(args.release_config))
    prereg = load_data_object(Path(args.prereg))
    fingerprint = load_json_object(Path(args.fingerprint_receipt))
    fence = load_json_object(Path(args.fence_open_receipt))
    bundle = build_preflight_bundle(
        release_config=release,
        prereg=prereg,
        fingerprint_receipt=fingerprint,
        fence_open_receipt=fence,
        runtime=inspect_runtime_identity(),
        now=datetime.now(timezone.utc),
    )
    return {
        "status": "PASS_P1_OFFLINE_PREFLIGHT",
        "replicas": len(REPLICAS),
        "model_calls": len(expected_call_keys()),
        "replica_plan_sha256": REPLICA_PLAN_SHA256,
        "call_plan_sha256": CALL_PLAN_SHA256,
        "release_config_sha256": bundle.release_config_sha256,
        "prereg_sha256": bundle.prereg_sha256,
        "stored_control_score_sha256": bundle.stored_control_score_sha256,
        "static_worst_case_usd": _money(bundle.budget.static_worst_case_usd),
        "hard_cap_usd": _money(bundle.budget.cap_usd),
        "external_calls": 0,
        "mutations": 0,
    }


def _verify_complete_wal_and_result_budget(
    journal: CallJournal,
    budget: BudgetPlan,
    result: Mapping[str, Any],
) -> Decimal:
    """Recompute the exact successful-run WAL sequence and list-price ledger."""

    call_keys = expected_call_keys()
    _require(
        len(journal.events) == 2 * len(call_keys),
        "HOLD_RUN_ARTIFACT_DRIFT",
        "WAL must contain exactly reserve/completed for every call",
    )
    reserve_keys = {
        "schema",
        "sequence",
        "timestamp",
        "previous_event_sha256",
        "run_genesis_sha256",
        "call_key",
        "request_sha256",
        "max_cost_usd",
        "state",
        "accumulated_prior_usd",
        "event_sha256",
    }
    completed_keys = {
        "schema",
        "sequence",
        "timestamp",
        "previous_event_sha256",
        "run_genesis_sha256",
        "call_key",
        "request_sha256",
        "max_cost_usd",
        "state",
        "reason",
        "actual_cost_usd",
        "response_path",
        "response_sha256",
        "fence_watch_path",
        "fence_watch_sha256",
        "event_sha256",
    }
    accumulated = ZERO
    previous_timestamp: datetime | None = None
    for index, call_key in enumerate(call_keys):
        reserved = journal.events[2 * index]
        completed = journal.events[2 * index + 1]
        spec = budget.specs[call_key]
        reserved_at = _parse_time(
            reserved.get("timestamp"), field=f"WAL reserve timestamp {call_key}"
        )
        completed_at = _parse_time(
            completed.get("timestamp"), field=f"WAL completed timestamp {call_key}"
        )
        _require(
            set(reserved) == reserve_keys
            and set(completed) == completed_keys
            and reserved.get("state") == "RESERVED_FSYNCED"
            and completed.get("state") == "COMPLETED"
            and reserved.get("call_key") == completed.get("call_key") == call_key
            and reserved.get("request_sha256")
            == completed.get("request_sha256")
            and reserved.get("max_cost_usd")
            == completed.get("max_cost_usd")
            == _money(spec.max_cost_usd)
            and reserved.get("accumulated_prior_usd") == _money(accumulated)
            and completed.get("reason") == "response_fsynced"
            and (previous_timestamp is None or previous_timestamp <= reserved_at)
            and reserved_at <= completed_at,
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"WAL reserve/completed contract {call_key}",
        )
        actual = _decimal(
            completed.get("actual_cost_usd"), field=f"WAL actual {call_key}"
        )
        _require(
            completed.get("actual_cost_usd") == _money(actual)
            and actual <= spec.max_cost_usd,
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"WAL actual/max cost {call_key}",
        )
        accumulated += actual
        previous_timestamp = completed_at
    _require(
        accumulated <= budget.cap_usd
        and budget.projected_total(journal) == accumulated,
        "HOLD_RUN_ARTIFACT_DRIFT",
        "recomputed WAL total/cap",
    )
    expected_summary = {
        "cap_usd": _money(budget.cap_usd),
        "observed_list_price_usd": _money(accumulated),
        "unknown_reserved_usd": _money(ZERO),
        "projected_total_usd": _money(accumulated),
    }
    _require(
        result.get("budget") == expected_summary,
        "HOLD_RUN_ARTIFACT_DRIFT",
        "result budget differs from recomputed complete WAL",
    )
    return accumulated


def load_run_replicas(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = run_dir.resolve()
    genesis = verify_run_genesis(load_json_object(root / "run_genesis.json"))
    validation_snapshot = verify_run_validation_snapshot(
        genesis["validation_snapshot"],
        genesis=genesis,
        verify_current_implementation=True,
    )
    validation_budget = BudgetPlan.from_identity(
        validation_snapshot["budget_plan"]
    )
    result = load_json_object(root / "result.json")
    _require(result.get("schema") == RESULT_SCHEMA, "HOLD_RUN_ARTIFACT_DRIFT", "schema")
    seal = result.get("result_sha256")
    body = {key: value for key, value in result.items() if key != "result_sha256"}
    _require(seal == sha256_json(body), "HOLD_RUN_ARTIFACT_DRIFT", "result seal")
    _require(
        result.get("run_genesis_sha256") == genesis["run_genesis_sha256"]
        and result.get("release_config_sha256")
        == genesis["release_config_sha256"]
        and result.get("prereg_sha256") == genesis["prereg_sha256"]
        and result.get("target_semantic_config_sha256")
        == genesis["target_semantic_config_sha256"]
        and result.get("validation_snapshot_sha256")
        == genesis["validation_snapshot_sha256"]
        and result.get("implementation_hashes_sha256")
        == validation_snapshot["implementation_hashes_sha256"],
        "HOLD_RUN_ARTIFACT_DRIFT",
        "result genesis/validation snapshot binding",
    )
    _require(
        result.get("status") == "P1_REPLICAS_COMPLETE_PENDING_FENCE_CLOSE",
        "HOLD_RUN_INCOMPLETE",
        str(result.get("status")),
    )
    _require(
        result.get("replica_plan_sha256") == REPLICA_PLAN_SHA256
        and result.get("call_plan_sha256") == CALL_PLAN_SHA256
        and result.get("replicas_expected") == len(REPLICAS)
        and result.get("replicas_persisted") == len(REPLICAS),
        "HOLD_RUN_ARTIFACT_DRIFT",
        "run plan/count binding",
    )
    journal = CallJournal(root / "calls.jsonl")
    journal.bind_genesis(genesis)
    _require(
        list(journal.records) == list(expected_call_keys())
        and all(row["state"] == "COMPLETED" for row in journal.records.values()),
        "HOLD_RUN_ARTIFACT_DRIFT",
        "WAL is not exactly 81 completed calls",
    )
    _require(
        journal.head_sha256 == result.get("wal_head_sha256"),
        "HOLD_RUN_ARTIFACT_DRIFT",
        "WAL head does not bind result",
    )
    _verify_complete_wal_and_result_budget(journal, validation_budget, result)
    artifacts = ArtifactStore(root)
    artifacts.bind_genesis(genesis)
    physical_responses: dict[str, dict[str, Any]] = {}
    expected_response_paths: set[str] = set()
    expected_watch_paths: set[str] = set()
    for call_key in expected_call_keys():
        record = journal.records[call_key]
        response, watch = artifacts.load_completed_call_artifacts(
            call_key, record
        )
        verify_persisted_fence_watch_receipt(
            watch,
            run_genesis=genesis,
            call_key=call_key,
        )
        physical_responses[call_key] = response
        expected_response_paths.add(str(record["response_path"]))
        expected_watch_paths.add(str(record["fence_watch_path"]))

    def exact_physical_manifest(dirname: str) -> set[str]:
        directory = (root / dirname).resolve()
        _require(
            directory.parent == root and directory.is_dir(),
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"missing physical artifact directory {dirname}",
        )
        paths = {
            path.relative_to(root).as_posix()
            for path in directory.rglob("*")
            if path.is_file()
        }
        _require(
            all(not (root / relative).is_symlink() for relative in paths),
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"symlink in physical artifact directory {dirname}",
        )
        return paths

    _require(
        exact_physical_manifest("provider_responses")
        == expected_response_paths
        and exact_physical_manifest("fence_watches") == expected_watch_paths,
        "HOLD_RUN_ARTIFACT_DRIFT",
        "missing or extra WAL-referenced physical call artifact",
    )
    manifests = result.get("replica_receipts")
    _require(isinstance(manifests, list) and len(manifests) == 27, "HOLD_RUN_ARTIFACT_DRIFT", "replicas")
    replicas: list[dict[str, Any]] = []
    expected_receipt_paths: set[str] = set()
    validated_call_keys: list[str] = []
    for expected_replica, expected, manifest in zip(
        REPLICAS, REPLICA_ORDER, manifests, strict=True
    ):
        _require(isinstance(manifest, Mapping), "HOLD_RUN_ARTIFACT_DRIFT", expected)
        _require(
            set(manifest) == {"replica_key", "path", "sha256"},
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"manifest shape {expected}",
        )
        _require(manifest.get("replica_key") == expected, "HOLD_RUN_ARTIFACT_DRIFT", expected)
        relative = manifest.get("path")
        expected_relative = f"replicas/{expected.replace(':', '_')}.json"
        _require(
            relative == expected_relative,
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"receipt path {expected}",
        )
        expected_receipt_paths.add(expected_relative)
        path = (root / relative).resolve()
        _require(root in path.parents and path.is_file(), "HOLD_RUN_ARTIFACT_DRIFT", relative)
        raw = path.read_bytes()
        _require(hashlib.sha256(raw).hexdigest() == manifest.get("sha256"), "HOLD_RUN_ARTIFACT_DRIFT", relative)
        try:
            replica = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise P1Error("HOLD_RUN_ARTIFACT_DRIFT", relative) from exc
        _require(isinstance(replica, dict) and replica.get("replica_key") == expected, "HOLD_RUN_ARTIFACT_DRIFT", expected)
        calls = replica.get("call_requests")
        _require(
            isinstance(calls, Mapping)
            and set(calls) == set(CALL_OPERATIONS)
            and replica.get("call_keys")
            == [f"{expected}:{operation}" for operation in CALL_OPERATIONS],
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"physical call manifest {expected}",
        )
        retrieval = replica.get("retrieval")
        rerank = replica.get("rerank")
        provider = replica.get("provider")
        _require(
            isinstance(retrieval, Mapping)
            and isinstance(rerank, Mapping)
            and isinstance(provider, Mapping),
            "HOLD_RUN_ARTIFACT_DRIFT",
            f"physical response binding shape {expected}",
        )
        observed_by_operation = {
            "embedding": retrieval.get("embedding_receipt"),
            "rerank": rerank.get("receipt"),
            "synthesis": provider.get("raw_payload"),
        }
        for operation in CALL_OPERATIONS:
            call_key = f"{expected}:{operation}"
            envelope = calls.get(operation)
            observed = observed_by_operation[operation]
            spec = validation_budget.specs[call_key]
            _require(
                isinstance(envelope, Mapping)
                and isinstance(observed, Mapping)
                and sha256_json(envelope)
                == journal.records[call_key]["request_sha256"],
                "HOLD_RUN_ARTIFACT_DRIFT",
                f"WAL request binding {call_key}",
            )
            call = provider_call_from_sealed_envelope(
                envelope,
                expected_call_key=call_key,
                spec=spec,
                run_genesis=genesis,
            )
            _require(
                call.request_sha256 == journal.records[call_key]["request_sha256"],
                "HOLD_RUN_ARTIFACT_DRIFT",
                f"reconstructed request binding {call_key}",
            )
            clean_observed = dict(observed)
            clean_observed.pop("_p1_resumed_from_receipt", None)
            clean_physical = dict(physical_responses[call_key])
            transport = clean_physical.pop("_p1_transport_receipt", None)
            product_attestation = replica.get("product_adapter_attestation")
            if product_attestation is not None:
                _require(
                    isinstance(transport, Mapping)
                    and isinstance(product_attestation, Mapping)
                    and product_attestation.get(
                        "transport_receipt_sha256s", {}
                    ).get(operation)
                    == sha256_json(transport),
                    "HOLD_RUN_ARTIFACT_DRIFT",
                    f"product transport binding {call_key}",
                )
            _require(
                sha256_json(clean_observed)
                == sha256_json(clean_physical),
                "HOLD_RUN_ARTIFACT_DRIFT",
                f"provider response binding {call_key}",
            )
            ProviderBoundary._validate_completed_response(
                spec,
                physical_responses[call_key],
                recorded_actual=_decimal(
                    journal.records[call_key].get("actual_cost_usd"),
                    field=f"WAL actual {call_key}",
                ),
                declared_input_bound=call.input_tokens_upper_bound,
                declared_output_bound=call.max_output_tokens,
            )
            validated_call_keys.append(call_key)
        validate_replica_receipt(
            replica,
            expected_replica,
            validation_snapshot["models"],
            expected_input=validation_snapshot["input_contract"][
                expected_replica.qid
            ],
            synthesis_spec=validation_budget.specs[f"{expected}:synthesis"],
            expected_run_genesis=genesis,
            expected_effective_config=genesis["target_semantic_config"],
        )
        replicas.append(replica)
    replica_root = (root / "replicas").resolve()
    actual_receipt_paths = {
        path.relative_to(root).as_posix()
        for path in replica_root.rglob("*")
        if path.is_file()
    }
    _require(
        actual_receipt_paths == expected_receipt_paths,
        "HOLD_RUN_ARTIFACT_DRIFT",
        "missing or extra physical replica receipt",
    )
    _require(
        validated_call_keys == list(expected_call_keys()),
        "HOLD_RUN_ARTIFACT_DRIFT",
        "not every physical provider call was revalidated exactly once",
    )
    return result, replicas


def _authoritative_scoring_inputs(
    run_result: Mapping[str, Any],
    *,
    prereg_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Load the repository-canonical prereg and its sealed fact contract."""

    from scripts.s277_c1_p1_scorer import load_fact_contract

    canonical_prereg = load_data_object(CANONICAL_PREREG_PATH)
    selected_prereg = (
        canonical_prereg
        if prereg_path is None
        else load_data_object(prereg_path)
    )
    canonical_prereg_sha256 = sha256_json(canonical_prereg)
    _require(
        sha256_json(selected_prereg) == canonical_prereg_sha256,
        "HOLD_PREREG_DRIFT",
        "scoring prereg is not the repository-canonical prereg",
    )
    _require(
        run_result.get("prereg_sha256") == canonical_prereg_sha256,
        "HOLD_SCORE_RUN_BINDING_DRIFT",
        "run was not produced from the canonical prereg",
    )
    verify_prereg_sealed_inputs(selected_prereg)
    verify_prereg_release_identity(selected_prereg)
    verify_prereg_runtime_contract(selected_prereg)
    fact_spec = selected_prereg["sealed_inputs"]["fact_contract"]
    fact_path = _sealed_path(fact_spec["path"])
    try:
        contract = load_fact_contract(fact_path)
    except Exception as exc:
        raise P1Error(
            "HOLD_FACT_CONTRACT_DRIFT",
            f"sealed fact contract rejected: {type(exc).__name__}",
        ) from exc
    bindings = {
        "run_result_sha256": str(run_result.get("result_sha256") or ""),
        "prereg_sha256": canonical_prereg_sha256,
        "fact_contract_sha256_lf": str(fact_spec.get("sha256_lf") or ""),
        "fact_contract_payload_sha256": str(fact_spec.get("payload_sha256") or ""),
        "replica_manifest_sha256": sha256_json(run_result.get("replica_receipts")),
    }
    _require(
        all(bool(_HEX64.fullmatch(value)) for value in bindings.values()),
        "HOLD_SCORE_RUN_BINDING_DRIFT",
        "authoritative score binding is incomplete",
    )
    return selected_prereg, contract, bindings


def _cli_score(args: argparse.Namespace) -> dict[str, Any]:
    from scripts.s277_c1_p1_scorer import score_run

    run_result, replicas = load_run_replicas(Path(args.run_dir))
    _prereg, contract, bindings = _authoritative_scoring_inputs(
        run_result,
        prereg_path=(Path(args.prereg) if getattr(args, "prereg", None) else None),
    )
    score = score_run(replicas, contract, bindings=bindings)
    output = Path(args.output) if args.output else Path(args.run_dir) / "score.json"
    write_json_exclusive(output, score)
    return {
        "status": "P1_SCORE_MATERIALIZED_NOT_RELEASE_GO",
        "score_status": score.get("status"),
        "score_decision": score.get("decision"),
        "score_sha256": sha256_json(score),
        "run_result_sha256": run_result["result_sha256"],
        "output": str(output),
        "paid_model_calls": 0,
    }


def _cli_score_stored_controls(args: argparse.Namespace) -> dict[str, Any]:
    from scripts.s277_c1_p1_scorer import (
        load_fact_contract,
        score_stored_controls,
    )

    contract = load_fact_contract(Path(args.contract))
    result = score_stored_controls(contract=contract)
    if args.output:
        write_json_exclusive(Path(args.output), result)
    return {
        **result,
        "scope": "stored_control_only_not_candidate_runtime",
        "paid_model_calls": 0,
        "network_calls": 0,
    }


def _finalize_after_verified_live_manifest(args: argparse.Namespace) -> dict[str, Any]:
    """Finalize only after the product CLI has verified the live manifest."""

    from scripts.s277_c1_p1_scorer import finalize_score, score_run

    now = datetime.now(timezone.utc)
    run_result, replicas = load_run_replicas(Path(args.run_dir))
    _prereg, contract, bindings = _authoritative_scoring_inputs(
        run_result,
        prereg_path=(Path(args.prereg) if getattr(args, "prereg", None) else None),
    )
    supplied_score = load_json_object(Path(args.score))
    authoritative_score = score_run(replicas, contract, bindings=bindings)
    _require(
        sha256_json(supplied_score) == sha256_json(authoritative_score),
        "HOLD_SCORE_ARTIFACT_DRIFT",
        "supplied score differs from the authoritative offline rescore",
    )
    adjudication = (
        load_data_object(Path(args.adjudication)) if args.adjudication else None
    )
    final_score = finalize_score(
        authoritative_score,
        adjudication,
        replicas=replicas,
        contract=contract,
        bindings=bindings,
    )
    decision = final_score.get("decision")
    if decision == "NO_GO":
        status = "P1_NO_GO"
        code = "NO_GO_PROTECTED_CONTRACT"
        window = None
    elif decision != "PASS":
        status = "HOLD"
        code = str(decision or "HOLD_SCORING_INCOMPLETE")
        window = None
    else:
        opened = load_json_object(Path(args.fence_open_receipt))
        closed = load_json_object(Path(args.fence_close_receipt))
        _require(
            sha256_json(opened) == run_result.get("fence_open_receipt_sha256"),
            "HOLD_FENCE_CLOSE",
            "open receipt is not the run input",
        )
        window = verify_fence_close_receipt(opened, closed, now=now)
        completed = _parse_time(
            run_result.get("replicas_completed_at"), field="replicas_completed_at"
        )
        closed_at = _parse_time(window["p1_completed_at"], field="p1_completed_at")
        _require(closed_at >= completed, "HOLD_FENCE_CLOSE", "fence closed before replicas completed")
        _require(window["expired"] is False, "HOLD_P1_EXPIRED", "six-hour TTL elapsed")
        status = "P1_PASS"
        code = "NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS"
    body = {
        "schema": FINAL_RESULT_SCHEMA,
        "status": status,
        "code": code,
        "run_result_sha256": run_result["result_sha256"],
        "score_sha256": sha256_json(authoritative_score),
        "final_score": final_score,
        "window": window,
        "p1_completed_at": window["p1_completed_at"] if window else None,
        "p1_expires_at": window["p1_expires_at"] if window else None,
        "release_deployed": False,
        "post_activation_canary_complete": False,
        "official_atomic_kpi_changed": False,
        "paid_model_calls_during_finalize": 0,
    }
    result = {**body, "result_sha256": sha256_json(body)}
    output = Path(args.output) if args.output else Path(args.run_dir) / "final.json"
    write_json_exclusive(output, result)
    return result


def _cli_finalize(args: argparse.Namespace) -> dict[str, Any]:
    _verify_materialized_live_manifest_window(
        contract_path=Path(args.live_manifest_contract),
        pre_path=Path(args.live_manifest_pre),
        post_path=Path(args.live_manifest_post),
        fence_open_path=Path(args.fence_open_receipt),
        fence_close_path=Path(args.fence_close_receipt),
    )
    return _finalize_after_verified_live_manifest(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="print the immutable zero-cost call plan")
    plan.set_defaults(handler=lambda _args: {
        "status": "P1_PLAN_OFFLINE",
        "replica_order": list(REPLICA_ORDER),
        "replica_plan_sha256": REPLICA_PLAN_SHA256,
        "call_count": len(expected_call_keys()),
        "call_plan_sha256": CALL_PLAN_SHA256,
        "paid_model_calls": 0,
    })

    sealed = argparse.ArgumentParser(add_help=False)
    sealed.add_argument("--release-config", required=True)
    sealed.add_argument("--prereg", required=True)
    offline_common = argparse.ArgumentParser(add_help=False, parents=[sealed])
    offline_common.add_argument("--fingerprint-receipt", required=True)
    offline_common.add_argument("--fence-open-receipt", required=True)
    preflight = subparsers.add_parser("preflight", parents=[offline_common])
    preflight.set_defaults(handler=_offline_cli_preflight)

    fingerprint = subparsers.add_parser("fingerprint-calibrate")
    fingerprint.add_argument("--operator-receipt", required=True)
    fingerprint.add_argument("--release-config", required=True)
    fingerprint.set_defaults(handler=_cli_fingerprint)

    fence_open = subparsers.add_parser("fence-open-verify")
    fence_open.add_argument("--operator-receipt", required=True)
    fence_open.add_argument("--fingerprint-receipt", required=True)
    fence_open.add_argument("--release-config", required=True)
    fence_open.add_argument("--live-manifest-contract", required=True)
    fence_open.add_argument("--live-manifest-pre", required=True)
    fence_open.set_defaults(handler=_cli_fence_open)

    fence_close = subparsers.add_parser("fence-close-verify")
    fence_close.add_argument("--fence-open-receipt", required=True)
    fence_close.add_argument("--operator-receipt", required=True)
    fence_close.add_argument("--live-manifest-contract", required=True)
    fence_close.add_argument("--live-manifest-pre", required=True)
    fence_close.add_argument("--live-manifest-post", required=True)
    fence_close.set_defaults(handler=_cli_fence_close)

    score = subparsers.add_parser("score")
    score.add_argument("--run-dir", required=True)
    score.add_argument("--prereg", default=str(CANONICAL_PREREG_PATH))
    score.add_argument("--output")
    score.set_defaults(handler=_cli_score)

    stored = subparsers.add_parser("score-stored-controls")
    stored.add_argument(
        "--contract",
        default=str(ROOT / "evals/s277_c1_p1_fact_contract_v1.json"),
    )
    stored.add_argument("--output")
    stored.set_defaults(handler=_cli_score_stored_controls)

    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--run-dir", required=True)
    finalize.add_argument("--score", required=True)
    finalize.add_argument("--prereg", default=str(CANONICAL_PREREG_PATH))
    finalize.add_argument("--fence-open-receipt", required=True)
    finalize.add_argument("--fence-close-receipt", required=True)
    finalize.add_argument("--live-manifest-contract", required=True)
    finalize.add_argument("--live-manifest-pre", required=True)
    finalize.add_argument("--live-manifest-post", required=True)
    finalize.add_argument("--adjudication")
    finalize.add_argument("--output")
    finalize.set_defaults(handler=_cli_finalize)

    run = subparsers.add_parser("run", parents=[sealed])
    run.add_argument("--execute", action="store_true")
    run.add_argument("--confirm-paid", action="store_true")
    run.add_argument("--authorization-receipt", required=True)
    run.add_argument("--credentials", required=True)
    run.add_argument("--artifact-dir", required=True)
    run.add_argument("--ipc-dir", required=True)
    run.add_argument("--live-manifest-contract", required=True)
    run.add_argument("--live-manifest-pre", required=True)
    run.add_argument("--live-http-evidence", required=True)
    run.add_argument("--postgrest-post-snapshot", required=True)
    run.set_defaults(handler=_cli_run_product)
    return parser


def _cli_fingerprint(args: argparse.Namespace) -> dict[str, Any]:
    release = load_json_object(Path(args.release_config))
    receipt = load_json_object(Path(args.operator_receipt))
    verified = verify_fingerprint_receipt(
        receipt,
        release_config_sha256=sha256_json(release),
        now=datetime.now(timezone.utc),
    )
    return {"status": "PASS_FINGERPRINT_CALIBRATION_RECEIPT_OFFLINE", "receipt_sha256": sha256_json(verified), "external_calls": 0}


def _verify_materialized_live_manifest_window(
    *,
    contract_path: Path,
    pre_path: Path,
    post_path: Path | None = None,
    fence_open_path: Path | None = None,
    fence_close_path: Path | None = None,
) -> dict[str, Any]:
    """Verify safe materialized manifest evidence and its fence bindings."""

    from scripts.s277_c1_p1_live_manifest import (
        verify_manifest_capture,
        verify_manifest_window,
    )

    contract = load_json_object(contract_path)
    pre = load_json_object(pre_path)
    try:
        verify_manifest_capture(contract, pre)
        captures = [pre]
        post = None
        if post_path is not None:
            post = load_json_object(post_path)
            captures.append(post)
            verify_manifest_window(contract, captures)
    except Exception as exc:
        code = getattr(exc, "code", "HOLD_FENCE_MANIFEST_DRIFT")
        raise P1Error(str(code), "live manifest verification failed") from exc
    contract_sha256 = sha256_json(contract)
    if fence_open_path is not None:
        opened = load_json_object(fence_open_path)
        _require(
            opened.get("live_manifest_contract_sha256") == contract_sha256,
            "HOLD_FENCE_MANIFEST_DRIFT",
            "open receipt is not bound to the supplied live manifest contract",
        )
    if fence_close_path is not None:
        closed = load_json_object(fence_close_path)
        _require(
            closed.get("live_manifest_contract_sha256") == contract_sha256,
            "HOLD_FENCE_MANIFEST_DRIFT",
            "close receipt is not bound to the supplied live manifest contract",
        )
        _require(
            post is not None
            and closed.get("live_manifest_post_capture_sha256")
            == sha256_json(post),
            "HOLD_FENCE_MANIFEST_DRIFT",
            "close receipt is not bound to the supplied post manifest",
        )
    return {
        "contract": contract,
        "pre": pre,
        "post": post,
        "live_manifest_contract_sha256": contract_sha256,
    }


def _cli_fence_open(args: argparse.Namespace) -> dict[str, Any]:
    release = load_json_object(Path(args.release_config))
    fingerprint = load_json_object(Path(args.fingerprint_receipt))
    receipt = load_json_object(Path(args.operator_receipt))
    live_window = _verify_materialized_live_manifest_window(
        contract_path=Path(args.live_manifest_contract),
        pre_path=Path(args.live_manifest_pre),
        fence_open_path=Path(args.operator_receipt),
    )
    verified = verify_fence_open_receipt(
        receipt,
        release_config_sha256=sha256_json(release),
        fingerprint=fingerprint.get("fingerprint"),
        target_semantic_config=release["derived_config"]["target_semantic_config"],
        now=datetime.now(timezone.utc),
    )
    return {
        "status": "PASS_FENCE_OPEN_RECEIPT_OFFLINE",
        "receipt_sha256": sha256_json(verified),
        "live_manifest_contract_sha256": live_window[
            "live_manifest_contract_sha256"
        ],
        "external_calls": 0,
    }


def _cli_fence_close(args: argparse.Namespace) -> dict[str, Any]:
    opened = load_json_object(Path(args.fence_open_receipt))
    closed = load_json_object(Path(args.operator_receipt))
    _verify_materialized_live_manifest_window(
        contract_path=Path(args.live_manifest_contract),
        pre_path=Path(args.live_manifest_pre),
        post_path=Path(args.live_manifest_post),
        fence_open_path=Path(args.fence_open_receipt),
        fence_close_path=Path(args.operator_receipt),
    )
    return verify_fence_close_receipt(opened, closed, now=datetime.now(timezone.utc))


def _cli_run_product(args: argparse.Namespace) -> dict[str, Any]:
    from scripts.s277_c1_p1_execute import run_live

    return dict(run_live(args))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.handler(args)
        _json_output(result)
        return 0
    except P1Error as exc:
        paid_model_calls: int | None = 0
        paid_model_calls_evidence = "NO_NONEMPTY_WAL_OBSERVED"
        artifact_dir = getattr(args, "artifact_dir", None)
        if args.command == "run" and artifact_dir:
            wal_path = Path(artifact_dir).resolve() / CALL_JOURNAL_FILENAME
            try:
                if wal_path.is_file() and wal_path.stat().st_size > 0:
                    paid_model_calls = None
                    paid_model_calls_evidence = (
                        "NONEMPTY_WAL_REQUIRES_ARTIFACT_RECONCILIATION"
                    )
            except OSError:
                paid_model_calls = None
                paid_model_calls_evidence = "WAL_STATE_UNREADABLE"
        _json_output(
            {
                "status": "HOLD",
                "code": exc.code,
                "message": str(exc),
                "paid_model_calls": paid_model_calls,
                "paid_model_calls_evidence": paid_model_calls_evidence,
                "railway_mutations": 0,
                "supabase_mutations": 0,
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
