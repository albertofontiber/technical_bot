from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import s277_c1_p1 as p1
from scripts import s277_c1_p1_execute as execute
from scripts import s277_c1_p1_live_manifest as live_manifest


NOW = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
PROJECT_REF = "izooestgffgscdirkfia"
FUNCTION_SHA = "1" * 64
MANIFEST_SHA = "2" * 64
RESULT_SHA = "3" * 64


class FakeGuard:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state
        self.receipts = (
            {
                "schema": "safe-postgrest-request",
                "method": "POST",
                "path": "/rest/v1/rpc/match_chunks_v2",
            },
        )

    def __enter__(self):
        self.state["guard_active"] = True
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.state["guard_active"] = False


class FakeFenceClient:
    def __init__(
        self,
        *,
        state: dict[str, object],
        pre_capture: dict[str, object],
        post_capture: dict[str, object],
        post_path: Path,
    ) -> None:
        self.state = state
        self.pre_capture = pre_capture
        self.post_capture = post_capture
        self.post_path = post_path
        self.contract_sha: str | None = None

    def open(self, *, release_config_sha256, live_manifest_contract_sha256):
        self.state["open_calls"] = int(self.state.get("open_calls", 0)) + 1
        self.state["opened_release_sha"] = release_config_sha256
        self.contract_sha = live_manifest_contract_sha256
        return {
            "fingerprint_receipt": {"schema": "safe-fingerprint"},
            "fence_open_receipt": {
                "schema": "safe-open",
                "live_manifest_contract_sha256": live_manifest_contract_sha256,
            },
            "live_manifest_pre_capture": copy.deepcopy(self.pre_capture),
        }

    def close(self):
        assert self.post_path.is_file()
        self.state["close_calls"] = int(self.state.get("close_calls", 0)) + 1
        return {
            "fence_close_receipt": {
                "schema": "safe-close",
                "live_manifest_contract_sha256": self.contract_sha,
                "live_manifest_post_capture_sha256": p1.sha256_json(
                    self.post_capture
                ),
            },
            "live_manifest_post_capture": copy.deepcopy(self.post_capture),
        }

    def abort(self, *, reason_code):
        self.state["abort_calls"] = int(self.state.get("abort_calls", 0)) + 1
        self.state["abort_reason"] = reason_code
        return {
            "fence_abort_receipt": {
                "schema": "safe-abort",
                "status": "ABORTED_CONFIRMED",
                "rollback_confirmed": True,
                "reason_code": reason_code,
            }
        }

    def abort_pending_open(self, *, reason_code):
        self.state["pending_abort_calls"] = int(
            self.state.get("pending_abort_calls", 0)
        ) + 1
        self.state["abort_reason"] = reason_code
        return {
            "fence_abort_receipt": {
                "schema": "safe-abort",
                "status": "ABORTED_CONFIRMED",
                "rollback_confirmed": True,
                "reason_code": reason_code,
            }
        }


class FakeRunner:
    def __init__(self, state: dict[str, object], result: dict[str, object]) -> None:
        self.state = state
        self.result = result

    def run(self):
        assert self.state.get("guard_active") is True
        self.state["runner_calls"] = int(self.state.get("runner_calls", 0)) + 1
        return copy.deepcopy(self.result)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(tmp_path: Path, *, run_status: str = "HOLD"):
    artifact = tmp_path / "artifacts"
    ipc = tmp_path / "ipc"
    post_path = artifact / "operator-postgrest.json"
    snapshot = {"schema": "safe-postgrest", "project_ref": PROJECT_REF}
    semantic = {
        "project_ref": PROJECT_REF,
        "visual_assets_registry": "off",
        "postgrest": copy.deepcopy(snapshot),
        "functions": [
            {
                "name": live_manifest.IDENTITY_FUNCTION,
                "definition_sha256_lf": FUNCTION_SHA,
            }
        ],
    }
    pre_capture = {
        "schema": "safe-live-manifest",
        "phase": "pre",
        "captured_at": "2026-07-21T10:00:00Z",
        "manifest": semantic,
        "manifest_sha256": MANIFEST_SHA,
    }
    post_capture = {
        **copy.deepcopy(pre_capture),
        "phase": "post",
        "captured_at": "2026-07-21T10:01:00Z",
    }
    contract = {
        "schema": "safe-contract",
        "manifest": copy.deepcopy(semantic),
        "manifest_sha256": MANIFEST_SHA,
    }
    release = {
        "schema_version": "safe-release",
        "railway": {
            "read_only_snapshot_taken_at": "2026-07-21T09:59:00Z",
            "live_snapshot": {"VISUAL_ASSETS_REGISTRY": "off"},
            "railway_live_snapshot_sha256": "4" * 64,
        },
        "derived_config": {
            "target_semantic_config": {
                "generation": {"visual_assets_registry": False}
            }
        },
        "candidate": {"tested_commit_sha": "5" * 40},
    }
    fresh_release = copy.deepcopy(release)
    fresh_release["railway"]["read_only_snapshot_taken_at"] = (
        "2026-07-21T10:00:00Z"
    )
    prereg = {"schema": "safe-prereg"}
    authorization = {"run_id": "run-test-0001", "safe": True}
    pre_evidence = {
        "schema": "safe-http-evidence",
        "project_ref": PROJECT_REF,
        "postgrest_snapshot": copy.deepcopy(snapshot),
        "identity_guard_receipt": {"schema": "safe-identity"},
    }
    inputs = {
        "release_config": tmp_path / "release.json",
        "prereg": tmp_path / "prereg.json",
        "authorization_receipt": tmp_path / "authorization.json",
        "live_manifest_contract": tmp_path / "contract.json",
        "live_manifest_pre": tmp_path / "pre.json",
        "live_http_evidence": tmp_path / "pre-evidence.json",
    }
    for name, value in (
        ("release_config", release),
        ("prereg", prereg),
        ("authorization_receipt", authorization),
        ("live_manifest_contract", contract),
        ("live_manifest_pre", pre_capture),
        ("live_http_evidence", pre_evidence),
    ):
        _write(inputs[name], value)
    credentials = tmp_path / "credentials.env"
    # The injected loader owns parsing.  This file proves only that the handler
    # receives the requested path; its contents must never reach an artifact.
    credentials.write_text("not parsed by tests", encoding="utf-8")
    args = argparse.Namespace(
        execute=True,
        confirm_paid=True,
        credentials=str(credentials),
        artifact_dir=str(artifact),
        ipc_dir=str(ipc),
        postgrest_post_snapshot=str(post_path),
        **{name: str(path) for name, path in inputs.items()},
    )
    state: dict[str, object] = {}
    client = FakeFenceClient(
        state=state,
        pre_capture=pre_capture,
        post_capture=post_capture,
        post_path=post_path,
    )
    guard = FakeGuard(state)
    secrets = {
        "RAILWAY_TOKEN": "railway-secret-value",
        "ANTHROPIC_API_KEY": "anthropic-secret-value",
        "VOYAGE_API_KEY": "voyage-secret-value",
        "SUPABASE_URL": f"https://{PROJECT_REF}.supabase.co",
        "SUPABASE_ACCESS_TOKEN": "supabase-pat-secret-value",
        "P1_SUPABASE_JWT": "p1-jwt-secret-value",
        "SUPABASE_KEY": "sb_publishable_project-key-secret-value",
    }

    def capture_post(**kwargs):
        assert state.get("guard_active") is False
        assert kwargs["access_token"] == secrets["SUPABASE_ACCESS_TOKEN"]
        assert kwargs["p1_jwt"] == secrets["P1_SUPABASE_JWT"]
        assert kwargs["supabase_key"] == secrets["SUPABASE_KEY"]
        state["post_capture_calls"] = int(
            state.get("post_capture_calls", 0)
        ) + 1
        return {
            "schema": "safe-post-http-evidence",
            "project_ref": PROJECT_REF,
            "postgrest_snapshot": copy.deepcopy(snapshot),
        }

    result = {
        "status": run_status,
        "code": "NO_GO_TEST" if run_status.startswith("NO_GO") else "HOLD_TEST",
        "result_sha256": RESULT_SHA,
    }

    def load_credentials(path):
        state["credentials_path"] = path
        return secrets

    def materialize_release(**kwargs):
        state["railway_token"] = kwargs["token"]
        return copy.deepcopy(fresh_release)

    def verify_identity(**kwargs):
        assert kwargs["p1_jwt"] == secrets["P1_SUPABASE_JWT"]
        assert kwargs["supabase_key"] == secrets["SUPABASE_KEY"]
        state["identity_credentials_bound"] = True
        return SimpleNamespace(verified=True)

    def make_guard(**kwargs):
        assert kwargs["p1_jwt"] == secrets["P1_SUPABASE_JWT"]
        assert kwargs["supabase_key"] == secrets["SUPABASE_KEY"]
        state["guard_credentials_bound"] = True
        return guard

    deps = execute.ExecutionDependencies(
        clock=lambda: NOW,
        dotenv_loader=load_credentials,
        release_materializer=materialize_release,
        runtime_inspector=lambda: SimpleNamespace(runtime="safe"),
        release_verifier=lambda *args: None,
        prereg_verifier=lambda value: None,
        fact_contract_loader=lambda path: {"contract": "safe"},
        fact_contract_path_resolver=lambda value: tmp_path / "fact.json",
        input_contract_builder=lambda value: {"hp017": {"safe": True}},
        stored_control_scorer=lambda **kwargs: {"status": "REVIEW"},
        permit_verifier=lambda *args, **kwargs: authorization,
        manifest_verifier=lambda *args, **kwargs: None,
        manifest_window_verifier=lambda *args, **kwargs: state.setdefault(
            "manifest_window_verified", True
        ),
        identity_verifier=verify_identity,
        postgrest_snapshot_normalizer=lambda value, project_ref: copy.deepcopy(
            value
        ),
        fence_client_factory=lambda **kwargs: client,
        fence_watcher_factory=lambda value: ("watcher", value),
        paid_adapter_factory=lambda **kwargs: ("paid", sorted(kwargs)),
        replica_adapter_factory=lambda **kwargs: ("replica", kwargs),
        guard_factory=make_guard,
        preflight_builder=lambda **kwargs: SimpleNamespace(preflight=True),
        artifact_store_factory=lambda path: ("artifacts", path),
        journal_factory=lambda path, **kwargs: ("journal", path),
        authorization_claims_factory=lambda path: ("claims", path),
        runner_factory=lambda **kwargs: FakeRunner(state, result),
        postgrest_evidence_capture=capture_post,
        fence_close_verifier=lambda *args, **kwargs: {"status": "closed"},
    )
    return args, deps, state, secrets, artifact, client, fresh_release


def test_paid_opt_ins_are_checked_before_credentials_or_paths() -> None:
    calls: list[str] = []
    deps = execute.ExecutionDependencies(
        dotenv_loader=lambda path: calls.append(str(path)) or {}
    )
    with pytest.raises(p1.P1Error) as missing_execute:
        execute.run_live(
            argparse.Namespace(execute=False, confirm_paid=True),
            dependencies=deps,
        )
    assert missing_execute.value.code == "HOLD_EXECUTE_OPT_IN_REQUIRED"
    assert calls == []

    with pytest.raises(p1.P1Error) as missing_paid:
        execute.run_live(
            argparse.Namespace(execute=True, confirm_paid=False),
            dependencies=deps,
        )
    assert missing_paid.value.code == "HOLD_PAID_OPT_IN_REQUIRED"
    assert calls == []


@pytest.mark.parametrize(
    ("run_status", "expected_window_status"),
    [
        ("NO_GO_PARTIAL", "NO_GO_FENCE_CLOSED"),
        ("HOLD", "HOLD_FENCE_CLOSED"),
        (
            "P1_REPLICAS_COMPLETE_PENDING_FENCE_CLOSE",
            "P1_REPLICAS_COMPLETE_FENCE_CLOSED_PENDING_SCORE",
        ),
    ],
)
def test_live_window_closes_for_every_runner_result_and_never_finalizes(
    tmp_path: Path, run_status: str, expected_window_status: str
) -> None:
    args, deps, state, secrets, artifact, _client, _fresh = _fixture(
        tmp_path, run_status=run_status
    )
    result = execute.run_live(args, dependencies=deps)

    assert result["status"] == expected_window_status
    assert result["authoritative_score_materialized"] is False
    assert result["finalized"] is False
    assert result["railway_mutations"] == 0
    assert result["supabase_mutations"] == 0
    assert state["runner_calls"] == 1
    assert state["post_capture_calls"] == 1
    assert state["close_calls"] == 1
    assert state.get("abort_calls", 0) == 0
    assert state["guard_active"] is False
    assert state["railway_token"] == secrets["RAILWAY_TOKEN"]
    assert state["identity_credentials_bound"] is True
    assert state["guard_credentials_bound"] is True
    assert (artifact / "live_control" / "fence_close_receipt.json").is_file()
    assert Path(args.postgrest_post_snapshot).is_file()

    serialized = b"\n".join(
        path.read_bytes() for path in artifact.rglob("*.json")
    )
    for secret in secrets.values():
        if secret != secrets["SUPABASE_URL"]:
            assert secret.encode("utf-8") not in serialized


def test_fresh_railway_snapshot_drift_fails_before_fence_open(tmp_path: Path) -> None:
    args, deps, state, _secrets, _artifact, _client, fresh = _fixture(tmp_path)
    drifted = copy.deepcopy(fresh)
    drifted["railway"]["live_snapshot"] = {
        "VISUAL_ASSETS_REGISTRY": "on"
    }
    deps = execute.ExecutionDependencies(
        **{
            **deps.__dict__,
            "release_materializer": lambda **kwargs: drifted,
        }
    )

    with pytest.raises(p1.P1Error) as caught:
        execute.run_live(args, dependencies=deps)
    assert caught.value.code == "HOLD_RAILWAY_LIVE_SNAPSHOT_DRIFT"
    assert state.get("open_calls", 0) == 0


def test_failure_after_open_aborts_and_persists_confirmed_receipt(
    tmp_path: Path,
) -> None:
    args, deps, state, _secrets, artifact, _client, _fresh = _fixture(tmp_path)

    class IdentityFailure(RuntimeError):
        code = "HOLD_IDENTITY_TEST"

    def fail_identity(**kwargs):
        raise IdentityFailure("must not be serialized")

    deps = execute.ExecutionDependencies(
        **{**deps.__dict__, "identity_verifier": fail_identity}
    )
    with pytest.raises(p1.P1Error) as caught:
        execute.run_live(args, dependencies=deps)
    assert caught.value.code == "HOLD_IDENTITY_TEST"
    assert state["open_calls"] == 1
    assert state["abort_calls"] == 1
    assert state.get("close_calls", 0) == 0
    abort_path = artifact / "live_control" / "fence_abort_receipt.json"
    assert json.loads(abort_path.read_text(encoding="utf-8"))[
        "rollback_confirmed"
    ] is True


def test_post_capture_failure_after_hold_aborts_instead_of_leaving_fence_open(
    tmp_path: Path,
) -> None:
    args, deps, state, _secrets, artifact, _client, _fresh = _fixture(
        tmp_path, run_status="HOLD"
    )

    class PostFailure(RuntimeError):
        code = "HOLD_POST_CAPTURE_TEST"

    deps = execute.ExecutionDependencies(
        **{
            **deps.__dict__,
            "postgrest_evidence_capture": lambda **kwargs: (_ for _ in ()).throw(
                PostFailure("safe")
            ),
        }
    )
    with pytest.raises(p1.P1Error) as caught:
        execute.run_live(args, dependencies=deps)
    assert caught.value.code == "HOLD_POST_CAPTURE_TEST"
    assert state["runner_calls"] == 1
    assert state["abort_calls"] == 1
    assert state.get("close_calls", 0) == 0
    assert (artifact / "live_control" / "fence_abort_receipt.json").is_file()


def test_runtime_output_paths_inside_checkout_are_rejected_before_secret_load(
    tmp_path: Path,
) -> None:
    calls: list[Path] = []
    args = argparse.Namespace(
        execute=True,
        confirm_paid=True,
        artifact_dir=str(p1.ROOT / "forbidden-artifacts"),
        ipc_dir=str(tmp_path / "ipc"),
        postgrest_post_snapshot=str(
            p1.ROOT / "forbidden-artifacts" / "post.json"
        ),
    )
    deps = execute.ExecutionDependencies(
        dotenv_loader=lambda path: calls.append(path) or {}
    )
    with pytest.raises(p1.P1Error) as caught:
        execute.run_live(args, dependencies=deps)
    assert caught.value.code == "HOLD_RUNTIME_PATH_INSIDE_CHECKOUT"
    assert calls == []


def test_credentials_must_be_outside_artifacts_and_ipc_before_secret_load(
    tmp_path: Path,
) -> None:
    calls: list[Path] = []
    artifact = tmp_path / "artifacts"
    args = argparse.Namespace(
        execute=True,
        confirm_paid=True,
        artifact_dir=str(artifact),
        ipc_dir=str(tmp_path / "ipc"),
        postgrest_post_snapshot=str(artifact / "post.json"),
        credentials=str(artifact / "credentials.env"),
    )
    deps = execute.ExecutionDependencies(
        dotenv_loader=lambda path: calls.append(path) or {}
    )
    with pytest.raises(p1.P1Error) as caught:
        execute.run_live(args, dependencies=deps)
    assert caught.value.code == "HOLD_CREDENTIALS_PATH_OVERLAP"
    assert calls == []


def test_ambiguous_open_uses_preallocated_pending_abort(tmp_path: Path) -> None:
    args, deps, state, _secrets, artifact, client, _fresh = _fixture(tmp_path)

    def ambiguous_open(**kwargs):
        state["open_calls"] = 1
        raise RuntimeError("response lost after operator opened")

    client.open = ambiguous_open
    with pytest.raises(p1.P1Error) as caught:
        execute.run_live(args, dependencies=deps)
    assert caught.value.code == "HOLD_LIVE_EXECUTION_FAILED"
    assert state["pending_abort_calls"] == 1
    assert state.get("abort_calls", 0) == 0
    assert (
        artifact / "live_control" / "fence_abort_receipt.json"
    ).is_file()
