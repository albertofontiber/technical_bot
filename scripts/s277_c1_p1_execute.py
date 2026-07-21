"""Live, fail-closed assembly for the S277 C1 P1 paid window.

This module is intentionally only an execution-window orchestrator.  It
recaptures Railway through the read-only adapter, delegates the persistent
PostgreSQL fence to its credential-separated IPC process, runs the production
RAG seam under the scoped PostgREST guard, and closes (or explicitly aborts)
the fence.  It never mutates Railway or Supabase and it never scores or
finalizes a P1 result.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from scripts import s277_c1_p1 as p1
from scripts import s277_c1_p1_fence_operator as fence_operator
from scripts import s277_c1_p1_live_manifest as live_manifest
from scripts import s277_c1_p1_live_receipts as live_receipts
from scripts import s277_c1_p1_postgrest_guard as postgrest_guard
from scripts import s277_c1_p1_product_adapter as product_adapter
from scripts import s277_c1_p1_release_config as release_config
from scripts import s277_c1_p1_scorer as scorer


EXECUTION_WINDOW_SCHEMA = "s277_c1_p1_live_execution_window_v1"
RAILWAY_REVALIDATION_SCHEMA = "s277_c1_p1_railway_revalidation_v1"
_SAFE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{2,95}$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dotenv_values(path: Path) -> Mapping[str, Any]:
    try:
        from dotenv import dotenv_values

        return dotenv_values(path)
    except Exception as exc:
        raise p1.P1Error(
            "HOLD_CREDENTIALS_REQUIRED",
            f"credentials file could not be read ({type(exc).__name__})",
        ) from exc


def _verify_prereg(prereg: Mapping[str, Any]) -> None:
    p1.verify_prereg_sealed_inputs(prereg)
    p1.verify_prereg_release_identity(prereg)
    p1.verify_prereg_runtime_contract(prereg)
    p1.verify_model_extraction_contract(prereg)


def _fact_contract_path(prereg: Mapping[str, Any]) -> Path:
    sealed = prereg.get("sealed_inputs")
    fact = sealed.get("fact_contract") if isinstance(sealed, Mapping) else None
    path = fact.get("path") if isinstance(fact, Mapping) else None
    _require(
        isinstance(path, str) and bool(path),
        "HOLD_PREREG_SCHEMA",
        "sealed fact contract path is absent",
    )
    return p1._sealed_path(path)  # noqa: SLF001


def _verify_release(
    candidate: Mapping[str, Any], runtime: p1.RuntimeIdentity, now: datetime
) -> None:
    p1.verify_release_config(candidate, runtime, now=now)


def _verify_fence_close(
    opened: Mapping[str, Any],
    closed: Mapping[str, Any],
    now: datetime,
    *,
    post_manifest_capture: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    return p1.verify_fence_close_receipt(
        opened,
        closed,
        now=now,
        post_manifest_capture=post_manifest_capture,
    )


def _normalize_postgrest_snapshot(
    snapshot: Mapping[str, Any], project_ref: str
) -> Mapping[str, Any]:
    # This is the same strict normalizer used when the live manifest is built.
    # Keeping the publication byte-equivalent prevents the operator from
    # accepting a broader HTTP surface between its catalog pre/post captures.
    return live_manifest._normalize_postgrest_snapshot(  # noqa: SLF001
        snapshot, project_ref=project_ref
    )


@dataclass(frozen=True, repr=False)
class RuntimeSecrets:
    railway_token: str
    anthropic_api_key: str
    voyage_api_key: str
    supabase_url: str
    supabase_access_token: str
    p1_supabase_jwt: str
    supabase_key: str

    def __repr__(self) -> str:
        return "RuntimeSecrets(<redacted>)"

    def forbidden_values(self) -> tuple[str, ...]:
        return (
            self.railway_token,
            self.anthropic_api_key,
            self.voyage_api_key,
            self.supabase_access_token,
            self.p1_supabase_jwt,
            self.supabase_key,
        )


@dataclass(frozen=True)
class ExecutionDependencies:
    """Injectable seams; defaults are the reviewed production implementations."""

    clock: Callable[[], datetime] = _now
    dotenv_loader: Callable[[Path], Mapping[str, Any]] = _dotenv_values
    release_materializer: Callable[..., Mapping[str, Any]] = (
        release_config.materialize_release_config
    )
    runtime_inspector: Callable[[], p1.RuntimeIdentity] = p1.inspect_runtime_identity
    release_verifier: Callable[..., None] = _verify_release
    prereg_verifier: Callable[[Mapping[str, Any]], None] = _verify_prereg
    fact_contract_loader: Callable[[str | Path], Mapping[str, Any]] = (
        scorer.load_fact_contract
    )
    fact_contract_path_resolver: Callable[[Mapping[str, Any]], Path] = (
        _fact_contract_path
    )
    input_contract_builder: Callable[[Mapping[str, Any]], Mapping[str, Any]] = (
        p1.prereg_input_contract
    )
    stored_control_scorer: Callable[..., Mapping[str, Any]] = (
        scorer.score_stored_controls
    )
    replica_scorer: Callable[..., Mapping[str, Any]] = scorer.score_replica
    permit_verifier: Callable[..., Mapping[str, Any]] = p1.verify_execution_permit
    manifest_verifier: Callable[..., None] = live_manifest.verify_manifest_capture
    manifest_window_verifier: Callable[..., None] = (
        live_manifest.verify_manifest_window
    )
    identity_verifier: Callable[..., Any] = (
        postgrest_guard.verify_and_bind_identity_receipt
    )
    postgrest_snapshot_normalizer: Callable[..., Mapping[str, Any]] = (
        _normalize_postgrest_snapshot
    )
    fence_client_factory: Callable[..., Any] = fence_operator.FenceIpcClient
    fence_watcher_factory: Callable[..., Any] = fence_operator.IpcFenceWatcher
    paid_adapter_factory: Callable[..., Any] = product_adapter.ProductSDKPaidAdapter
    replica_adapter_factory: Callable[..., Any] = product_adapter.ProductReplicaAdapter
    guard_factory: Callable[..., Any] = postgrest_guard.P1PostgrestGuard
    preflight_builder: Callable[..., Any] = p1.build_preflight_bundle
    artifact_store_factory: Callable[..., Any] = p1.ArtifactStore
    journal_factory: Callable[..., Any] = p1.CallJournal
    authorization_claims_factory: Callable[..., Any] = p1.AuthorizationClaimStore
    runner_factory: Callable[..., Any] = p1.P1Runner
    postgrest_evidence_capture: Callable[..., Mapping[str, Any]] = (
        live_receipts.capture_postgrest_evidence
    )
    fence_close_verifier: Callable[..., Mapping[str, Any]] = _verify_fence_close
    exclusive_writer: Callable[[Path, Mapping[str, Any]], Any] = (
        fence_operator.write_json_atomic_exclusive
    )


@dataclass(frozen=True)
class _SafeArtifactPaths:
    root: Path
    receipt_dir: Path
    postgrest_post_snapshot: Path
    railway_revalidation: Path
    manifest_contract: Path
    supplied_pre_capture: Path
    fence_pre_capture: Path
    pre_http_evidence: Path
    fingerprint_receipt: Path
    fence_open_receipt: Path
    post_http_evidence: Path
    fence_post_capture: Path
    fence_close_receipt: Path
    fence_abort_receipt: Path

    def all_outputs(self) -> tuple[Path, ...]:
        return (
            self.postgrest_post_snapshot,
            self.railway_revalidation,
            self.manifest_contract,
            self.supplied_pre_capture,
            self.fence_pre_capture,
            self.pre_http_evidence,
            self.fingerprint_receipt,
            self.fence_open_receipt,
            self.post_http_evidence,
            self.fence_post_capture,
            self.fence_close_receipt,
            self.fence_abort_receipt,
        )


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise p1.P1Error(code, detail)


def _inside(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    base = root.resolve()
    return resolved == base or base in resolved.parents


def _paths(args: argparse.Namespace) -> tuple[_SafeArtifactPaths, Path]:
    artifact_root = Path(args.artifact_dir).resolve()
    ipc_root = Path(args.ipc_dir).resolve()
    post_path = Path(args.postgrest_post_snapshot).resolve()
    checkout = p1.ROOT.resolve()

    for label, path in (
        ("artifact_dir", artifact_root),
        ("ipc_dir", ipc_root),
        ("postgrest_post_snapshot", post_path),
    ):
        _require(
            not _inside(path, checkout),
            "HOLD_RUNTIME_PATH_INSIDE_CHECKOUT",
            f"{label} must be outside the detached Git checkout",
        )
    _require(
        _inside(post_path, artifact_root),
        "HOLD_POSTGREST_PUBLICATION_PATH",
        "postgrest_post_snapshot must be inside artifact_dir",
    )
    _require(
        not _inside(artifact_root, ipc_root)
        and not _inside(ipc_root, artifact_root),
        "HOLD_RUNTIME_PATH_OVERLAP",
        "artifact_dir and ipc_dir must be disjoint",
    )
    if artifact_root.exists():
        _require(
            artifact_root.is_dir()
            and not artifact_root.is_symlink()
            and next(artifact_root.iterdir(), None) is None,
            "HOLD_ARTIFACT_ROOT_NOT_EMPTY",
            "artifact_dir must be absent or empty before a new live window",
        )
    credentials_path = Path(args.credentials)
    _require(
        not credentials_path.is_symlink()
        and not _inside(credentials_path.resolve(), artifact_root)
        and not _inside(credentials_path.resolve(), ipc_root),
        "HOLD_CREDENTIALS_PATH_OVERLAP",
        "credentials must be a non-symlink file outside artifacts and IPC",
    )

    receipt_dir = artifact_root / "live_control"
    result = _SafeArtifactPaths(
        root=artifact_root,
        receipt_dir=receipt_dir,
        postgrest_post_snapshot=post_path,
        railway_revalidation=receipt_dir / "railway_revalidation.json",
        manifest_contract=receipt_dir / "live_manifest_contract.json",
        supplied_pre_capture=receipt_dir / "supplied_live_manifest_pre.json",
        fence_pre_capture=receipt_dir / "fence_live_manifest_pre.json",
        pre_http_evidence=receipt_dir / "postgrest_pre_http_evidence.json",
        fingerprint_receipt=receipt_dir / "fingerprint_receipt.json",
        fence_open_receipt=receipt_dir / "fence_open_receipt.json",
        post_http_evidence=receipt_dir / "postgrest_post_http_evidence.json",
        fence_post_capture=receipt_dir / "fence_live_manifest_post.json",
        fence_close_receipt=receipt_dir / "fence_close_receipt.json",
        fence_abort_receipt=receipt_dir / "fence_abort_receipt.json",
    )
    outputs = result.all_outputs()
    _require(
        len({path.resolve() for path in outputs}) == len(outputs),
        "HOLD_SAFE_ARTIFACT_PATH_COLLISION",
        "safe receipt paths collide",
    )
    for path in outputs:
        _require(
            _inside(path, artifact_root),
            "HOLD_SAFE_ARTIFACT_PATH",
            "safe receipt escaped artifact_dir",
        )
        _require(
            not path.exists(),
            "HOLD_SAFE_ARTIFACT_EXISTS",
            f"refusing to overwrite {path.name}",
        )
    return result, ipc_root


def _load_runtime_secrets(
    path: Path, *, loader: Callable[[Path], Mapping[str, Any]]
) -> RuntimeSecrets:
    try:
        values = loader(path)
    except p1.P1Error:
        raise
    except Exception as exc:
        raise p1.P1Error(
            "HOLD_CREDENTIALS_REQUIRED",
            f"credentials file could not be read ({type(exc).__name__})",
        ) from exc
    _require(
        isinstance(values, Mapping),
        "HOLD_CREDENTIALS_REQUIRED",
        "credentials loader did not return a mapping",
    )
    names = (
        "RAILWAY_TOKEN",
        "ANTHROPIC_API_KEY",
        "VOYAGE_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_ACCESS_TOKEN",
        "P1_SUPABASE_JWT",
        "SUPABASE_KEY",
    )
    loaded: dict[str, str] = {}
    for name in names:
        value = values.get(name)
        _require(
            isinstance(value, str) and bool(value.strip()),
            "HOLD_CREDENTIALS_REQUIRED",
            f"credential {name} is absent",
        )
        loaded[name] = value
    return RuntimeSecrets(
        railway_token=loaded["RAILWAY_TOKEN"],
        anthropic_api_key=loaded["ANTHROPIC_API_KEY"],
        voyage_api_key=loaded["VOYAGE_API_KEY"],
        supabase_url=loaded["SUPABASE_URL"],
        supabase_access_token=loaded["SUPABASE_ACCESS_TOKEN"],
        p1_supabase_jwt=loaded["P1_SUPABASE_JWT"],
        supabase_key=loaded["SUPABASE_KEY"],
    )


def _stable_release_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    railway = value.get("railway")
    _require(
        isinstance(railway, Mapping),
        "HOLD_RAILWAY_LIVE_SNAPSHOT_DRIFT",
        "release Railway projection is absent",
    )
    excluded = {"read_only_snapshot_taken_at"}
    return {
        key: (
            {name: item for name, item in railway.items() if name not in excluded}
            if key == "railway"
            else item
        )
        for key, item in value.items()
    }


def _verify_fresh_railway_release(
    sealed: Mapping[str, Any], fresh: Mapping[str, Any]
) -> dict[str, Any]:
    sealed_railway = sealed.get("railway")
    fresh_railway = fresh.get("railway")
    _require(
        isinstance(sealed_railway, Mapping)
        and isinstance(fresh_railway, Mapping)
        and fresh_railway.get("live_snapshot")
        == sealed_railway.get("live_snapshot"),
        "HOLD_RAILWAY_LIVE_SNAPSHOT_DRIFT",
        "fresh Railway live_snapshot differs from the sealed release",
    )
    _require(
        _stable_release_projection(fresh) == _stable_release_projection(sealed),
        "HOLD_RAILWAY_LIVE_SNAPSHOT_DRIFT",
        "fresh read-only materialization differs from the sealed release identity",
    )
    snapshot = fresh_railway["live_snapshot"]
    return {
        "schema": RAILWAY_REVALIDATION_SCHEMA,
        "status": "PASS_READ_ONLY_LIVE_SNAPSHOT_IDENTICAL",
        "sealed_release_sha256": p1.sha256_json(sealed),
        "fresh_release_sha256": p1.sha256_json(fresh),
        "live_snapshot_sha256": p1.sha256_json(snapshot),
        "fresh_snapshot_taken_at": fresh_railway.get(
            "read_only_snapshot_taken_at"
        ),
        "railway_mutations": 0,
    }


def _identity_function_sha256(contract: Mapping[str, Any]) -> str:
    manifest = contract.get("manifest")
    functions = manifest.get("functions") if isinstance(manifest, Mapping) else None
    candidates = [
        row.get("definition_sha256_lf")
        for row in functions or []
        if isinstance(row, Mapping)
        and row.get("name") == live_manifest.IDENTITY_FUNCTION
    ]
    _require(
        len(candidates) == 1
        and isinstance(candidates[0], str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", candidates[0])),
        "HOLD_EXPECTED_MANIFEST_INVALID",
        "identity function hash missing from live manifest contract",
    )
    return str(candidates[0])


def _safe_write(
    path: Path,
    value: Mapping[str, Any],
    *,
    secrets: RuntimeSecrets,
    writer: Callable[[Path, Mapping[str, Any]], Any],
) -> None:
    _require(
        isinstance(value, Mapping),
        "HOLD_SAFE_ARTIFACT_INVALID",
        path.name,
    )
    try:
        raw = p1.canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise p1.P1Error("HOLD_SAFE_ARTIFACT_INVALID", path.name) from exc
    p1._assert_no_secret_material(value)  # noqa: SLF001
    for secret in secrets.forbidden_values():
        _require(
            secret.encode("utf-8") not in raw,
            "HOLD_SECRET_SERIALIZATION",
            f"credential reached {path.name}",
        )
    try:
        writer(path, value)
    except Exception as exc:
        if isinstance(exc, p1.P1Error):
            raise
        code = getattr(exc, "code", "HOLD_SAFE_ARTIFACT_PERSISTENCE")
        if not isinstance(code, str) or _SAFE_CODE.fullmatch(code) is None:
            code = "HOLD_SAFE_ARTIFACT_PERSISTENCE"
        raise p1.P1Error(code, f"could not create {path.name}") from exc


def _load_input_objects(args: argparse.Namespace) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    release = p1.load_json_object(Path(args.release_config))
    prereg = p1.load_data_object(Path(args.prereg))
    authorization = p1.load_json_object(Path(args.authorization_receipt))
    manifest_contract = p1.load_json_object(Path(args.live_manifest_contract))
    supplied_pre = p1.load_json_object(Path(args.live_manifest_pre))
    pre_evidence = p1.load_json_object(Path(args.live_http_evidence))
    return (
        release,
        prereg,
        authorization,
        manifest_contract,
        supplied_pre,
        pre_evidence,
    )


def _safe_reason(exc: BaseException) -> str:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and _SAFE_CODE.fullmatch(code):
        return code
    return "HOLD_RUNNER_EXCEPTION"


def _as_p1_error(exc: BaseException, *, default_code: str) -> p1.P1Error:
    if isinstance(exc, p1.P1Error):
        return exc
    code = getattr(exc, "code", default_code)
    if not isinstance(code, str) or _SAFE_CODE.fullmatch(code) is None:
        code = default_code
    return p1.P1Error(code, f"{type(exc).__name__} at live execution boundary")


def _abort_open_fence(
    *,
    client: Any,
    cause: BaseException,
    paths: _SafeArtifactPaths,
    secrets: RuntimeSecrets,
    dependencies: ExecutionDependencies,
    pending_open: bool = False,
) -> None:
    try:
        abort_method = (
            client.abort_pending_open if pending_open else client.abort
        )
        payload = abort_method(reason_code=_safe_reason(cause))
        receipt = payload.get("fence_abort_receipt")
        _require(
            isinstance(receipt, Mapping)
            and receipt.get("status") == "ABORTED_CONFIRMED"
            and receipt.get("rollback_confirmed") is True,
            "HOLD_FENCE_ABORT_UNCONFIRMED",
            "operator did not return a confirmed rollback receipt",
        )
        _safe_write(
            paths.fence_abort_receipt,
            receipt,
            secrets=secrets,
            writer=dependencies.exclusive_writer,
        )
    except Exception as abort_exc:
        raise p1.P1Error(
            "HOLD_FENCE_ABORT_UNCONFIRMED",
            f"fence cleanup was not confirmed ({type(abort_exc).__name__})",
        ) from abort_exc


def _window_result(
    *,
    run_result: Mapping[str, Any],
    close_receipt: Mapping[str, Any],
    pre_capture: Mapping[str, Any],
    post_capture: Mapping[str, Any],
    post_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    run_status = str(run_result.get("status") or "")
    if run_status == "P1_REPLICAS_COMPLETE_PENDING_FENCE_CLOSE":
        status = "P1_REPLICAS_COMPLETE_FENCE_CLOSED_PENDING_SCORE"
        code = "HOLD_PENDING_AUTHORITATIVE_SCORE_AND_FINALIZE"
    elif run_status.startswith("NO_GO"):
        status = "NO_GO_FENCE_CLOSED"
        code = str(run_result.get("code") or "NO_GO_PARTIAL")
    else:
        status = "HOLD_FENCE_CLOSED"
        code = str(run_result.get("code") or "HOLD_RUN_INCOMPLETE")
    if _SAFE_CODE.fullmatch(code) is None:
        code = "HOLD_RUN_RESULT_CODE_INVALID"
    return {
        "schema": EXECUTION_WINDOW_SCHEMA,
        "status": status,
        "code": code,
        "run_status": run_status,
        "run_result_sha256": run_result.get("result_sha256"),
        "fence_close_receipt_sha256": p1.sha256_json(close_receipt),
        "live_manifest_pre_sha256": pre_capture.get("manifest_sha256"),
        "live_manifest_post_sha256": post_capture.get("manifest_sha256"),
        "postgrest_post_evidence_sha256": p1.sha256_json(post_evidence),
        "authoritative_score_materialized": False,
        "finalized": False,
        "release_deployed": False,
        "railway_mutations": 0,
        "supabase_mutations": 0,
    }


def _run_live_impl(
    args: argparse.Namespace, *, dependencies: ExecutionDependencies | None = None
) -> dict[str, Any]:
    """Execute and close one P1 window without scoring or finalization.

    Both paid opt-ins are checked before the credentials path is inspected or
    the dotenv loader is called.
    """

    _require(
        getattr(args, "execute", False) is True,
        "HOLD_EXECUTE_OPT_IN_REQUIRED",
        "--execute missing",
    )
    _require(
        getattr(args, "confirm_paid", False) is True,
        "HOLD_PAID_OPT_IN_REQUIRED",
        "--confirm-paid missing",
    )

    deps = dependencies or ExecutionDependencies()
    paths, ipc_root = _paths(args)
    (
        sealed_release,
        prereg,
        authorization,
        manifest_contract,
        supplied_pre,
        pre_evidence,
    ) = _load_input_objects(args)
    secrets = _load_runtime_secrets(
        Path(args.credentials), loader=deps.dotenv_loader
    )

    observed_now = deps.clock()
    fresh_release = deps.release_materializer(
        token=secrets.railway_token, now=observed_now
    )
    railway_revalidation = _verify_fresh_railway_release(
        sealed_release, fresh_release
    )
    runtime = deps.runtime_inspector()
    deps.release_verifier(sealed_release, runtime, observed_now)
    deps.prereg_verifier(prereg)

    fact_path = deps.fact_contract_path_resolver(prereg)
    fact_contract = deps.fact_contract_loader(fact_path)
    stored_control = deps.stored_control_scorer(contract=fact_contract)
    permit = p1.ExecutionPermit(
        execute=True,
        confirm_paid=True,
        credentials_present=True,
        authorization=authorization,
    )
    run_id = authorization.get("run_id")
    expected_artifact_identity = p1.artifact_identity_sha256(
        str(run_id), paths.root
    )
    deps.permit_verifier(
        permit,
        release_config_sha256=p1.sha256_json(sealed_release),
        prereg_sha256=p1.sha256_json(prereg),
        expected_artifact_identity_sha256=expected_artifact_identity,
        stored_control_score_sha256=p1.sha256_json(stored_control),
        now=observed_now,
    )

    deps.manifest_verifier(manifest_contract, supplied_pre)
    identity_receipt = pre_evidence.get("identity_guard_receipt")
    _require(
        isinstance(identity_receipt, Mapping),
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "pre HTTP evidence lacks identity_guard_receipt",
    )
    pre_semantic = supplied_pre.get("manifest")
    _require(
        isinstance(pre_semantic, Mapping),
        "HOLD_EXPECTED_MANIFEST_INVALID",
        "pre manifest payload missing",
    )
    project_ref = str(pre_semantic.get("project_ref") or "")
    visual_mode = str(pre_semantic.get("visual_assets_registry") or "")
    target_visual = sealed_release.get("derived_config", {}).get(
        "target_semantic_config", {}
    ).get("generation", {}).get("visual_assets_registry")
    _require(
        visual_mode in {"on", "off"}
        and target_visual is (visual_mode == "on"),
        "HOLD_FENCE_MANIFEST_DRIFT",
        "live manifest visual surface differs from the sealed release",
    )
    pre_snapshot = pre_evidence.get("postgrest_snapshot")
    _require(
        isinstance(pre_snapshot, Mapping),
        "HOLD_POSTGREST_SNAPSHOT_INVALID",
        "pre HTTP evidence lacks postgrest_snapshot",
    )
    normalized_pre_snapshot = deps.postgrest_snapshot_normalizer(
        pre_snapshot, project_ref
    )
    _require(
        pre_semantic.get("postgrest") == normalized_pre_snapshot,
        "HOLD_POSTGREST_SNAPSHOT_BINDING",
        "pre HTTP snapshot differs from the sealed live manifest",
    )

    manifest_contract_sha256 = p1.sha256_json(manifest_contract)
    client = deps.fence_client_factory(ipc_dir=ipc_root, clock=deps.clock)
    open_attempted = False
    open_confirmed = False
    terminal = False
    try:
        open_attempted = True
        open_payload = client.open(
            release_config_sha256=p1.sha256_json(sealed_release),
            live_manifest_contract_sha256=manifest_contract_sha256,
        )
        open_confirmed = True
        fingerprint_receipt = open_payload.get("fingerprint_receipt")
        fence_open_receipt = open_payload.get("fence_open_receipt")
        fence_pre_capture = open_payload.get("live_manifest_pre_capture")
        _require(
            isinstance(fingerprint_receipt, Mapping)
            and isinstance(fence_open_receipt, Mapping)
            and isinstance(fence_pre_capture, Mapping),
            "HOLD_FENCE_IPC_BINDING",
            "open payload is incomplete",
        )
        _require(
            fence_open_receipt.get("live_manifest_contract_sha256")
            == manifest_contract_sha256,
            "HOLD_FENCE_IPC_BINDING",
            "open receipt manifest contract binding",
        )
        deps.manifest_verifier(manifest_contract, fence_pre_capture)
        _require(
            fence_pre_capture.get("manifest_sha256")
            == supplied_pre.get("manifest_sha256")
            and fence_pre_capture.get("manifest") == supplied_pre.get("manifest"),
            "HOLD_FENCE_MANIFEST_DRIFT",
            "operator pre capture differs from the supplied sealed pre",
        )
        verified_identity = deps.identity_verifier(
            manifest_contract=manifest_contract,
            manifest_capture=fence_pre_capture,
            identity_http_receipt=identity_receipt,
            p1_jwt=secrets.p1_supabase_jwt,
            supabase_key=secrets.supabase_key,
        )

        for path, payload in (
            (paths.railway_revalidation, railway_revalidation),
            (paths.manifest_contract, manifest_contract),
            (paths.supplied_pre_capture, supplied_pre),
            (paths.fence_pre_capture, fence_pre_capture),
            (paths.pre_http_evidence, pre_evidence),
            (paths.fingerprint_receipt, fingerprint_receipt),
            (paths.fence_open_receipt, fence_open_receipt),
        ):
            _safe_write(
                path,
                payload,
                secrets=secrets,
                writer=deps.exclusive_writer,
            )

        bundle = deps.preflight_builder(
            release_config=sealed_release,
            prereg=prereg,
            fingerprint_receipt=fingerprint_receipt,
            fence_open_receipt=fence_open_receipt,
            runtime=runtime,
            now=deps.clock(),
        )
        guard = deps.guard_factory(
            supabase_url=secrets.supabase_url,
            p1_jwt=secrets.p1_supabase_jwt,
            supabase_key=secrets.supabase_key,
            project_ref=project_ref,
            visual_assets_registry=visual_mode,
            verified_identity=verified_identity,
        )
        paid_adapter = deps.paid_adapter_factory(
            anthropic_api_key=secrets.anthropic_api_key,
            voyage_api_key=secrets.voyage_api_key,
        )
        replica_adapter = deps.replica_adapter_factory(
            input_contract=deps.input_contract_builder(prereg),
            postgrest_receipt_source=lambda: guard.receipts,
            postgrest_manifest_sha256=str(fence_pre_capture["manifest_sha256"]),
            visual_assets_registry=visual_mode,
        )
        artifacts = deps.artifact_store_factory(paths.root)
        journal = deps.journal_factory(
            paths.root / p1.CALL_JOURNAL_FILENAME, now=deps.clock
        )
        runner = deps.runner_factory(
            bundle=bundle,
            permit=permit,
            artifacts=artifacts,
            journal=journal,
            provider_adapter=paid_adapter,
            replica_adapter=replica_adapter,
            fence_watcher=deps.fence_watcher_factory(client),
            authorization_claims=deps.authorization_claims_factory(paths.root),
            scorer=lambda receipt: deps.replica_scorer(
                dict(receipt), fact_contract
            ),
            runtime_inspector=deps.runtime_inspector,
            now=deps.clock,
        )
        with guard:
            run_result = runner.run()
        _require(
            isinstance(run_result, Mapping),
            "HOLD_RUN_RESULT_INVALID",
            "P1Runner did not return a result mapping",
        )

        post_evidence = deps.postgrest_evidence_capture(
            supabase_url=secrets.supabase_url,
            access_token=secrets.supabase_access_token,
            p1_jwt=secrets.p1_supabase_jwt,
            supabase_key=secrets.supabase_key,
            expected_identity_function_sha256=_identity_function_sha256(
                manifest_contract
            ),
            expected_project_ref=project_ref,
        )
        _require(
            isinstance(post_evidence, Mapping)
            and post_evidence.get("project_ref") == project_ref,
            "HOLD_POSTGREST_SNAPSHOT_INVALID",
            "post HTTP evidence project binding",
        )
        raw_post_snapshot = post_evidence.get("postgrest_snapshot")
        _require(
            isinstance(raw_post_snapshot, Mapping),
            "HOLD_POSTGREST_SNAPSHOT_INVALID",
            "post HTTP evidence lacks postgrest_snapshot",
        )
        post_snapshot = deps.postgrest_snapshot_normalizer(
            raw_post_snapshot, project_ref
        )
        _safe_write(
            paths.post_http_evidence,
            post_evidence,
            secrets=secrets,
            writer=deps.exclusive_writer,
        )
        # Publication is last: the operator can only observe a complete,
        # validated snapshot, never a partially written JSON document.
        _safe_write(
            paths.postgrest_post_snapshot,
            post_snapshot,
            secrets=secrets,
            writer=deps.exclusive_writer,
        )

        close_payload = client.close()
        terminal = True
        close_receipt = close_payload.get("fence_close_receipt")
        fence_post_capture = close_payload.get("live_manifest_post_capture")
        _require(
            isinstance(close_receipt, Mapping)
            and isinstance(fence_post_capture, Mapping),
            "HOLD_FENCE_CLOSE",
            "close payload is incomplete",
        )
        _require(
            close_receipt.get("live_manifest_contract_sha256")
            == manifest_contract_sha256,
            "HOLD_FENCE_CLOSE",
            "close receipt manifest contract binding",
        )
        _require(
            close_receipt.get("live_manifest_post_capture_sha256")
            == p1.sha256_json(fence_post_capture),
            "HOLD_FENCE_CLOSE",
            "close receipt post-manifest binding",
        )
        deps.manifest_verifier(manifest_contract, fence_post_capture)
        deps.manifest_window_verifier(
            manifest_contract, [fence_pre_capture, fence_post_capture]
        )
        deps.fence_close_verifier(
            fence_open_receipt,
            close_receipt,
            deps.clock(),
            post_manifest_capture=fence_post_capture,
        )
        for path, payload in (
            (paths.fence_post_capture, fence_post_capture),
            (paths.fence_close_receipt, close_receipt),
        ):
            _safe_write(
                path,
                payload,
                secrets=secrets,
                writer=deps.exclusive_writer,
            )
        return _window_result(
            run_result=run_result,
            close_receipt=close_receipt,
            pre_capture=fence_pre_capture,
            post_capture=fence_post_capture,
            post_evidence=post_evidence,
        )
    except BaseException as exc:
        if open_attempted and not terminal:
            _abort_open_fence(
                client=client,
                cause=exc,
                paths=paths,
                secrets=secrets,
                dependencies=deps,
                pending_open=not open_confirmed,
            )
        raise _as_p1_error(exc, default_code="HOLD_LIVE_EXECUTION_FAILED") from exc


def run_live(
    args: argparse.Namespace, *, dependencies: ExecutionDependencies | None = None
) -> dict[str, Any]:
    """Public CLI handler with one safe error vocabulary."""

    # Keep these checks here as well as in the implementation so even malformed
    # dependency objects or path namespaces cannot cause a credential read.
    _require(
        getattr(args, "execute", False) is True,
        "HOLD_EXECUTE_OPT_IN_REQUIRED",
        "--execute missing",
    )
    _require(
        getattr(args, "confirm_paid", False) is True,
        "HOLD_PAID_OPT_IN_REQUIRED",
        "--confirm-paid missing",
    )
    try:
        return _run_live_impl(args, dependencies=dependencies)
    except p1.P1Error:
        raise
    except BaseException as exc:
        raise _as_p1_error(exc, default_code="HOLD_LIVE_EXECUTION_FAILED") from exc


__all__ = ["ExecutionDependencies", "RuntimeSecrets", "run_live"]
