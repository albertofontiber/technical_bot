"""Capture a secret-free Railway snapshot and materialize the C1 P1 release config.

This is operator tooling.  It reads Railway through the documented GraphQL API,
projects the response onto the small set of variables that can affect P1, and
never writes or prints the unfiltered variables returned by Railway.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s277_c1_p1 as p1


RAILWAY_GRAPHQL_URL = "https://backboard.railway.com/graphql/v2"
RAILWAY_RECEIPT_SCHEMA = "s277_c1_p1_railway_snapshot_receipt_v2"
RAILWAY_OPERATION = "S277C1P1Variables"
SNAPSHOT_MAX_AGE = timedelta(minutes=30)

# The only production Railway target authorised for P1.  These are public
# resource identifiers, not credentials.  Keeping them in code prevents a
# valid query against a different project/service from authorising the run.
RAILWAY_PROJECT_ID = "129867c5-d1f3-44d8-b1e8-b33a06d83bb6"
RAILWAY_ENVIRONMENT_ID = "c607c36e-d842-4d60-a0a1-c8bfeff9c8ba"
RAILWAY_SERVICE_ID = "e049a76d-def5-4e51-a7b4-204161b85cd3"

REQUIRED_EXACT_VALUES = {
    "CHUNKS_TABLE": "chunks_v2",
    "ENUNCIADOS_MULTIVECTOR": "on",
    "HYQ_TABLE": "on",
    "IDENTITY_RESOLVE": "on",
    "IDENTITY_RESOLVE_POLICY": "add",
    "GENERATOR_SELECTION_BLOCK": "on",
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "RERANK_TOP_K": "10",
    "LLM_MAX_TOKENS": "3500",
    "MUST_PRESERVE_CONTRACT": "on",
}

# Missing values are resolved exactly as the production code resolves them.
# Keeping presence separately in the receipt prevents a default from being
# misrepresented as a variable physically present in Railway.
SAFE_DEFAULTS = {
    "HYQ_PILOT_FILE": "",
    "HYDE_ENABLED": "false",
    "RERANKER_BACKEND": "llm",
    "MERGE_STRATEGY": "stamps",
    "RERANK_PREVIEW_CHARS": "800",
    "DIVERSIFY_TIEBREAK": "off",
    # P1-reachable readers that were previously outside the release snapshot.
    "ANSWER_OBLIGATION_PLANNER": "off",
    "GENERATOR_INCLUDE_CONTEXT": "0",
    "IDENTITY_FETCH": "off",
    "ENUNCIADOS_QUOTA_FUSION": "off",
    "HYQ_PILOT_QUOTA": "10",
    "HYQ_PILOT_MIN_COS": "0.45",
    "NEIGHBOR_WINDOW": "0",
    "NEIGHBOR_MODELS_ONLY": "off",
    "IDENTITY_MAP": "off",
    "LEVER1_KEYWORD_ORDER": "off",
    "LEVER2_IDENTITY": "off",
    "LEVER2_PM_RESCUE": "off",
    "SERIES_REGISTRY_ENABLED": "true",
    "EMBED_PROVIDER": "voyage",
    "EMBED_MODEL": "voyage-4-large",
    "HYDE_MODEL": "claude-haiku-4-5",
    **{name: "off" for name in p1.TARGET_OFF_FLAGS},
}

# These variables are read by the transitive implementation closure but are
# credentials or operational paths, not safe semantic configuration.  They are
# inventoried so a new env read fails closed, but their values are never copied
# into a receipt.
NON_PROJECTED_ENV_NAMES = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "P1_FENCE_DATABASE_URL",
        "P1_IDENTITY_FUNCTION_SHA256",
        "P1_SUPABASE_JWT",
        "SUPABASE_ACCESS_TOKEN",
        "VOYAGE_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_KEY",
        "TELEGRAM_BOT_TOKEN",
        "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY",
        "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION",
        "MANUALS_DIR",
        "IMAGES_DIR",
        "EMBED_CACHE_PATH",
        "VOICE_TRANSCRIPTION_MODEL",
    }
)

# Values of these names are deliberately not persisted.  The planned patch
# deletes/overwrites them before product imports, so only physical presence is
# relevant and even a secret accidentally assigned to one cannot escape.
PRESENCE_ONLY_NAMES = frozenset(
    {*p1.PROFILE_OWNED_LEGACY_FLAGS, "COVERAGE_RELEASE_PROFILE"}
)

SAFE_VARIABLE_NAMES = frozenset(
    {
        *REQUIRED_EXACT_VALUES,
        *SAFE_DEFAULTS,
        *p1.PROFILE_OWNED_LEGACY_FLAGS,
        *p1.ORTHOGONAL_PRESERVED_FLAGS,
        "COVERAGE_RELEASE_PROFILE",
    }
)

ALLOWED_SAFE_VALUES = {
    **{name: frozenset({value}) for name, value in REQUIRED_EXACT_VALUES.items()},
    **{name: frozenset({value}) for name, value in SAFE_DEFAULTS.items()},
    "VISUAL_ASSETS_REGISTRY": frozenset({"on", "off"}),
}

# Dynamic getenv sites are bounded separately: their domains are the profile,
# target-off, must-preserve and legacy-identity names above.  Any new *literal*
# os.getenv/os.environ read in the hashed closure must be classified here or in
# ALLOWED_SAFE_VALUES before a receipt can be captured.
EXPECTED_DYNAMIC_ENV_SITES = frozenset(
    {
        ("scripts/s270_etapa2_probe.py", "_assert_pipeline_config", "key"),
        ("scripts/s277_c1_p1.py", "_offline_extract_models", "name"),
        (
            "scripts/s277_c1_p1.py",
            "sealed_target_runtime_environment",
            "name",
        ),
        (
            "scripts/s277_c1_p1_fence_operator.py",
            "_cli_serve",
            "args.database_url_env",
        ),
        (
            "scripts/s277_c1_p1_live_receipts.py",
            "_required_environment",
            "name",
        ),
        ("src/config.py", "_strict_on_off", "name"),
        ("src/rag/catalog_resolver.py", "mode", "f"),
        ("src/rag/series_registry.py", "_entry_flag_enabled", "str(flag)"),
    }
)


class RailwaySnapshotError(RuntimeError):
    """Fail-closed operator error that is safe to display."""


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise RailwaySnapshotError("Railway receipt timestamp is absent")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RailwaySnapshotError("Railway receipt timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise RailwaySnapshotError("Railway receipt timestamp lacks timezone")
    return parsed.astimezone(timezone.utc)


def _string_variables(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RailwaySnapshotError("Railway variables response is not an object")
    result: dict[str, str] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, (str, int, bool)):
            raise RailwaySnapshotError("Railway variables contain a non-scalar entry")
        result[key] = str(raw)
    return result


def _env_read_inventory() -> tuple[
    frozenset[str], frozenset[tuple[str, str, str]]
]:
    """Return literal and dynamic os.getenv/os.environ reads in the P1 closure."""

    literal: set[str] = set()
    dynamic: set[tuple[str, str, str]] = set()
    for relative in p1.IMPLEMENTATION_PYTHON_SOURCES:
        path = ROOT / relative
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=relative)
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise RailwaySnapshotError(
                f"cannot inventory P1 environment reads in {relative}"
            ) from exc
        owners: dict[int, str] = {}

        class _OwnerVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.stack = ["<module>"]

            def generic_visit(self, node: ast.AST) -> None:
                owners[id(node)] = self.stack[-1]
                super().generic_visit(node)

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                owners[id(node)] = self.stack[-1]
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

        _OwnerVisitor().visit(tree)
        for node in ast.walk(tree):
            key: ast.expr | None = None
            if isinstance(node, ast.Call) and node.args:
                function = node.func
                if (
                    isinstance(function, ast.Attribute)
                    and function.attr == "getenv"
                    and isinstance(function.value, ast.Name)
                    and function.value.id == "os"
                ):
                    key = node.args[0]
                elif (
                    isinstance(function, ast.Attribute)
                    and function.attr == "get"
                    and isinstance(function.value, ast.Attribute)
                    and function.value.attr == "environ"
                    and isinstance(function.value.value, ast.Name)
                    and function.value.value.id == "os"
                ):
                    key = node.args[0]
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.ctx, ast.Load)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "environ"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "os"
            ):
                key = node.slice
            if key is None:
                continue
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                literal.add(key.value)
            else:
                dynamic.add((relative, owners[id(node)], ast.unparse(key)))
    return frozenset(literal), frozenset(dynamic)


def assert_env_inventory_complete() -> None:
    literal, dynamic = _env_read_inventory()
    classified = set(ALLOWED_SAFE_VALUES) | set(PRESENCE_ONLY_NAMES)
    classified.update(NON_PROJECTED_ENV_NAMES)
    unknown = sorted(literal - classified)
    unexpected_dynamic = sorted(dynamic - EXPECTED_DYNAMIC_ENV_SITES)
    if unknown or unexpected_dynamic:
        details: list[str] = []
        if unknown:
            details.append("unclassified=" + ",".join(unknown))
        if unexpected_dynamic:
            details.append(
                "dynamic="
                + ",".join(
                    f"{path}:{owner}:{expression}"
                    for path, owner, expression in unexpected_dynamic
                )
            )
        raise RailwaySnapshotError(
            "P1 environment-read inventory drifted: " + "; ".join(details)
        )


def project_safe_snapshot(raw_variables: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve only P1-relevant values; never retain unrelated names or values."""

    assert_env_inventory_complete()
    raw = _string_variables(raw_variables)
    present = sorted(name for name in SAFE_VARIABLE_NAMES if name in raw)
    absent = sorted(SAFE_VARIABLE_NAMES - set(present))
    presence_only_present = sorted(PRESENCE_ONLY_NAMES & set(present))
    physical_snapshot = {
        name: raw[name] for name in present if name not in PRESENCE_ONLY_NAMES
    }
    for name, value in physical_snapshot.items():
        allowed = ALLOWED_SAFE_VALUES.get(name)
        if allowed is None or value not in allowed:
            raise RailwaySnapshotError(
                f"Railway variable {name} is outside its sealed allowlist"
            )
    snapshot = dict(physical_snapshot)
    for name, default in SAFE_DEFAULTS.items():
        snapshot.setdefault(name, default)

    missing_required = sorted(set(REQUIRED_EXACT_VALUES) - set(snapshot))
    if missing_required:
        raise RailwaySnapshotError(
            "required Railway variables are absent: " + ", ".join(missing_required)
        )
    for name, expected in REQUIRED_EXACT_VALUES.items():
        if snapshot[name] != expected:
            raise RailwaySnapshotError(
                f"Railway variable {name} differs from the P1 contract"
            )

    visual = snapshot.get("VISUAL_ASSETS_REGISTRY")
    if visual not in {"on", "off"}:
        raise RailwaySnapshotError(
            "VISUAL_ASSETS_REGISTRY must be physically present and equal on|off"
        )
    for name in p1.TARGET_OFF_FLAGS:
        if snapshot.get(name) != "off":
            raise RailwaySnapshotError(f"Railway target-off flag is enabled: {name}")

    # Derivation is part of the validation: a snapshot that cannot produce the
    # exact bootstrap and target profiles is not a usable receipt.
    patch = {
        "delete": list(p1.PROFILE_OWNED_LEGACY_FLAGS),
        "set": {"COVERAGE_RELEASE_PROFILE": p1.BOOTSTRAP_PROFILE},
    }
    p1.derive_release_states(snapshot, patch)
    return {
        "live_snapshot": snapshot,
        "physical_safe_snapshot": physical_snapshot,
        "presence_only_names_present": presence_only_present,
        "safe_names_present": present,
        "safe_names_absent": absent,
        "ignored_variable_count": len(set(raw) - SAFE_VARIABLE_NAMES),
    }


def capture_railway_snapshot(
    *,
    token: str,
    project_id: str = RAILWAY_PROJECT_ID,
    environment_id: str = RAILWAY_ENVIRONMENT_ID,
    service_id: str = RAILWAY_SERVICE_ID,
    now: datetime | None = None,
    opener=urlopen,
) -> dict[str, Any]:
    """Perform one read-only Railway GraphQL query and return a safe receipt."""

    if not all(isinstance(value, str) and value for value in (
        token,
        project_id,
        environment_id,
        service_id,
    )):
        raise RailwaySnapshotError("Railway identity or token is absent")
    if (
        project_id,
        environment_id,
        service_id,
    ) != (
        RAILWAY_PROJECT_ID,
        RAILWAY_ENVIRONMENT_ID,
        RAILWAY_SERVICE_ID,
    ):
        raise RailwaySnapshotError("Railway identity is not the canonical P1 target")
    query = (
        f"query {RAILWAY_OPERATION}($projectId: String!, $environmentId: String!, "
        "$serviceId: String!) { variables(projectId: $projectId, "
        "environmentId: $environmentId, serviceId: $serviceId) }"
    )
    request_body = json.dumps(
        {
            "operationName": RAILWAY_OPERATION,
            "query": query,
            "variables": {
                "projectId": project_id,
                "environmentId": environment_id,
                "serviceId": service_id,
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = Request(
        RAILWAY_GRAPHQL_URL,
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "Project-Access-Token": token,
            "User-Agent": "technical-bot-s277-c1-p1/1",
        },
        method="POST",
    )
    try:
        response = opener(request, timeout=20)
        status = getattr(response, "status", None)
        status_code = int(status if status is not None else response.getcode())
        response_body = response.read()
        headers = response.headers
    except HTTPError as exc:
        # Never include the response body: it could echo a credential or value.
        raise RailwaySnapshotError(f"Railway HTTP error {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RailwaySnapshotError(
            f"Railway transport failed: {type(exc).__name__}"
        ) from exc
    if status_code != 200:
        raise RailwaySnapshotError(f"Railway returned HTTP {status_code}")
    try:
        payload = json.loads(response_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RailwaySnapshotError("Railway returned invalid JSON") from exc
    if not isinstance(payload, Mapping) or payload.get("errors"):
        raise RailwaySnapshotError("Railway GraphQL response contains errors")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise RailwaySnapshotError("Railway GraphQL data is absent")
    projection = project_safe_snapshot(data.get("variables"))
    captured_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    external_request_id = (
        headers.get("x-request-id")
        or headers.get("request-id")
        or headers.get("cf-ray")
    )
    if not isinstance(external_request_id, str) or not external_request_id.strip():
        raise RailwaySnapshotError("Railway response lacks a request identifier")
    receipt = {
        "schema": RAILWAY_RECEIPT_SCHEMA,
        "status": "PASS_READ_ONLY_SAFE_PROJECTION",
        "captured_at": _iso(captured_at),
        "project_id": project_id,
        "environment_id": environment_id,
        "service_id": service_id,
        "operation": RAILWAY_OPERATION,
        "http_status": status_code,
        "external_request_id": external_request_id.strip(),
        **projection,
    }
    receipt["live_snapshot_sha256"] = p1.sha256_json(receipt["live_snapshot"])
    receipt["receipt_sha256"] = p1.sha256_json(receipt)
    p1._assert_no_secret_material(receipt)
    return receipt


def verify_railway_snapshot_receipt(
    receipt: Mapping[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    p1._assert_no_secret_material(receipt)
    expected_keys = {
        "schema",
        "status",
        "captured_at",
        "project_id",
        "environment_id",
        "service_id",
        "operation",
        "http_status",
        "external_request_id",
        "live_snapshot",
        "physical_safe_snapshot",
        "presence_only_names_present",
        "safe_names_present",
        "safe_names_absent",
        "ignored_variable_count",
        "live_snapshot_sha256",
        "receipt_sha256",
    }
    if set(receipt) != expected_keys:
        raise RailwaySnapshotError("Railway receipt shape drifted")
    if (
        receipt.get("schema") != RAILWAY_RECEIPT_SCHEMA
        or receipt.get("status") != "PASS_READ_ONLY_SAFE_PROJECTION"
        or receipt.get("operation") != RAILWAY_OPERATION
        or receipt.get("http_status") != 200
    ):
        raise RailwaySnapshotError("Railway receipt identity is invalid")
    if (
        receipt.get("project_id"),
        receipt.get("environment_id"),
        receipt.get("service_id"),
    ) != (
        RAILWAY_PROJECT_ID,
        RAILWAY_ENVIRONMENT_ID,
        RAILWAY_SERVICE_ID,
    ):
        raise RailwaySnapshotError("Railway receipt targets a non-canonical service")
    request_id = receipt.get("external_request_id")
    if (
        not isinstance(request_id, str)
        or not request_id.strip()
        or request_id == "not-provided"
    ):
        raise RailwaySnapshotError("Railway receipt lacks request provenance")
    captured_at = _parse_time(receipt.get("captured_at"))
    observed_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if captured_at > observed_now + timedelta(seconds=60):
        raise RailwaySnapshotError("Railway receipt is from the future")
    if observed_now - captured_at > SNAPSHOT_MAX_AGE:
        raise RailwaySnapshotError("Railway receipt is stale")
    physical = receipt.get("physical_safe_snapshot")
    presence_only = receipt.get("presence_only_names_present")
    if not isinstance(physical, Mapping) or not isinstance(presence_only, list):
        raise RailwaySnapshotError("Railway physical projection is invalid")
    if (
        sorted(presence_only) != presence_only
        or not set(presence_only).issubset(PRESENCE_ONLY_NAMES)
        or set(physical) & PRESENCE_ONLY_NAMES
    ):
        raise RailwaySnapshotError("Railway redacted presence projection is invalid")
    reconstruction = dict(physical)
    reconstruction.update({name: "<redacted>" for name in presence_only})
    projection = project_safe_snapshot(reconstruction)
    for field in (
        "live_snapshot",
        "physical_safe_snapshot",
        "presence_only_names_present",
        "safe_names_present",
        "safe_names_absent",
    ):
        if projection[field] != receipt.get(field):
            raise RailwaySnapshotError(f"Railway {field} provenance drifted")
    if receipt.get("live_snapshot_sha256") != p1.sha256_json(
        receipt["live_snapshot"]
    ):
        raise RailwaySnapshotError("Railway snapshot hash drifted")
    unsigned = dict(receipt)
    claimed = unsigned.pop("receipt_sha256", None)
    if claimed != p1.sha256_json(unsigned):
        raise RailwaySnapshotError("Railway receipt hash drifted")
    if not isinstance(receipt.get("ignored_variable_count"), int):
        raise RailwaySnapshotError("Railway ignored-variable count is invalid")
    present = receipt.get("safe_names_present", [])
    absent = receipt.get("safe_names_absent", [])
    if (
        receipt["ignored_variable_count"] < 0
        or not isinstance(present, list)
        or not isinstance(absent, list)
        or sorted(present) != present
        or sorted(absent) != absent
        or set(present).isdisjoint(absent) is False
        or set(present) | set(absent) != SAFE_VARIABLE_NAMES
    ):
        raise RailwaySnapshotError("Railway presence projection is invalid")
    return dict(receipt)


def _git(*args: str, allow_not_found: bool = False) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 and not (
        allow_not_found and completed.returncode == 1
    ):
        raise RailwaySnapshotError(f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def _materialize_verified_release_config(
    railway_receipt: Mapping[str, Any],
    *,
    now: datetime | None = None,
    identity_inspector=p1.inspect_runtime_identity,
) -> dict[str, Any]:
    """Build from an in-process live receipt; not an operator entry point."""

    verified = verify_railway_snapshot_receipt(railway_receipt, now=now)
    initial_runtime = identity_inspector()
    if not isinstance(initial_runtime, p1.RuntimeIdentity):
        raise RailwaySnapshotError("runtime identity inspector returned invalid data")
    if not initial_runtime.detached or not initial_runtime.clean:
        raise RailwaySnapshotError("runtime identity is not clean and detached")
    commit = initial_runtime.commit_sha
    tree = initial_runtime.tree_sha

    snapshot = dict(verified["live_snapshot"])
    patch = {
        "delete": list(p1.PROFILE_OWNED_LEGACY_FLAGS),
        "set": {"COVERAGE_RELEASE_PROFILE": p1.BOOTSTRAP_PROFILE},
    }
    release = {
        "schema_version": p1.RELEASE_CONFIG_SCHEMA,
        "status": "MATERIALIZED_SAFE_NO_SECRETS",
        "secret_fields_present": False,
        "candidate": {
            "tested_commit_sha": commit,
            "tested_tree_sha": tree,
            "detached_worktree": True,
            "git_status_empty": True,
            "untracked_files": [],
            "bot_version": commit,
        },
        "railway": {
            "read_only_snapshot_taken_at": verified["captured_at"],
            "snapshot_max_age_seconds": 1800,
            "snapshot_future_skew_seconds": 60,
            "live_snapshot": snapshot,
            "railway_live_snapshot_sha256": p1.sha256_json(snapshot),
            "planned_bootstrap_patch": patch,
        },
        "derived_config": p1.derive_release_states(snapshot, patch),
        "models": {
            "embedding": "voyage-4-large",
            "reranker": "claude-sonnet-4-6",
            "generator": "claude-sonnet-4-6",
            "temperature": 0,
            "max_tokens": 3500,
            "prompt_cache": False,
            "inference_geo": "global",
            "service_tier": "standard_sync",
        },
        "retrieval": {
            "chunks_table": "chunks_v2",
            "retrieval_top_k": 50,
            "rerank_top_k": 10,
            "reranker_backend": "llm",
            "hyde_enabled": False,
        },
        "runtime": {
            "python_version": sys.version.split()[0],
            "anthropic_sdk_version": p1.package_version("anthropic"),
            "voyage_sdk_version": p1.package_version("voyageai"),
            "effective_lock_sha256": p1.sha256_file(
                ROOT / "requirements.txt", lf_normalized=True
            ),
        },
        "implementation_hashes": {
            relative: p1.sha256_file(ROOT / relative, lf_normalized=True)
            for relative in p1.REQUIRED_IMPLEMENTATION_HASHES
        },
        "rpc_allowlist": p1.derive_rpc_allowlist(snapshot),
        "authorizations": {
            "paid_run": False,
            "railway_mutation": False,
            "supabase_write": False,
        },
    }
    # A second exact identity is captured only after every implementation byte
    # has been read and hashed.  This closes the clean-check/read TOCTOU window.
    post_hash_runtime = identity_inspector()
    if post_hash_runtime != initial_runtime:
        raise RailwaySnapshotError("runtime identity changed while materializing")
    if not post_hash_runtime.detached or not post_hash_runtime.clean:
        raise RailwaySnapshotError("runtime identity became unsafe while materializing")
    p1.verify_release_config(release, post_hash_runtime, now=now)
    # Verification re-reads implementation files, so also fence that interval.
    final_runtime = identity_inspector()
    if final_runtime != post_hash_runtime:
        raise RailwaySnapshotError("runtime identity changed during final verification")
    return release


def materialize_release_config(
    *,
    token: str,
    now: datetime | None = None,
    opener=urlopen,
    identity_inspector=p1.inspect_runtime_identity,
) -> dict[str, Any]:
    """Capture canonical Railway live and materialize in one process."""

    receipt = capture_railway_snapshot(token=token, now=now, opener=opener)
    return _materialize_verified_release_config(
        receipt,
        now=now,
        identity_inspector=identity_inspector,
    )


def _load_credentials(path: Path, token_name: str) -> str:
    try:
        from dotenv import dotenv_values

        values = dotenv_values(path)
    except Exception as exc:
        raise RailwaySnapshotError(
            f"cannot read credentials file: {type(exc).__name__}"
        ) from exc
    token = values.get(token_name)
    if not isinstance(token, str) or not token:
        raise RailwaySnapshotError(f"credential {token_name} is absent")
    return token


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    p1.write_json_exclusive(path, value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--credentials", required=True)
    capture.add_argument("--token-name", default="RAILWAY_TOKEN")
    capture.add_argument("--output", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--credentials", required=True)
    build.add_argument("--token-name", default="RAILWAY_TOKEN")
    build.add_argument("--output", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--railway-receipt", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "capture":
            token = _load_credentials(Path(args.credentials), args.token_name)
            receipt = capture_railway_snapshot(
                token=token,
            )
            _write_exclusive(Path(args.output), receipt)
            output = {
                "status": receipt["status"],
                "receipt_sha256": receipt["receipt_sha256"],
                "output": str(Path(args.output).resolve()),
                "railway_mutations": 0,
            }
        elif args.command == "build":
            token = _load_credentials(Path(args.credentials), args.token_name)
            release = materialize_release_config(token=token)
            _write_exclusive(Path(args.output), release)
            output = {
                "status": "PASS_RELEASE_CONFIG_MATERIALIZED",
                "release_config_sha256": p1.sha256_json(release),
                "output": str(Path(args.output).resolve()),
                "railway_mutations": 0,
            }
        else:
            receipt = p1.load_json_object(Path(args.railway_receipt))
            verified = verify_railway_snapshot_receipt(receipt)
            output = {
                "status": "PASS_RAILWAY_RECEIPT",
                "receipt_sha256": verified["receipt_sha256"],
                "railway_mutations": 0,
            }
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (RailwaySnapshotError, p1.P1Error) as exc:
        print(
            json.dumps(
                {
                    "status": "HOLD",
                    "code": type(exc).__name__,
                    "message": str(exc),
                    "railway_mutations": 0,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
