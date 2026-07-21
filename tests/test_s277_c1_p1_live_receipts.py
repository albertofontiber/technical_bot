from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import s277_c1_p1_postgrest_guard as guard
from scripts import s277_c1_p1_live_receipts as receipts
from tests import test_s277_c1_p1_live_manifest as manifest_fixtures


PROJECT_REF = "abcdefghijklmnopqrst"
OTHER_REF = "tsrqponmlkjihgfedcba"
SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"
PAT = "sbp_test_management_pat_never_serialize"
MANAGEMENT_SECRET = "management-jwt-secret-never-serialize"
IDENTITY_SHA = "d" * 64


def _jwt(payload: dict | None = None) -> str:
    def encoded(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{encoded({'alg': 'HS256', 'typ': 'JWT'})}.{encoded(payload or {'role': 'p1_readonly', 'sub': 'p1-gate'})}.signature"


P1_JWT = _jwt()
SUPABASE_KEY = "sb_publishable_test_project_key_never_serialize"


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _openapi(*, version: str | None = "14.1.0") -> dict:
    paths = {
        path: {method.lower(): {"responses": {"200": {"description": "OK"}}}}
        for path, (method,) in receipts.live.REQUIRED_RPC_METHODS.items()
    }
    paths["/rpc/p1_runtime_identity_v1"] = {
        "get": {"responses": {"200": {"description": "OK"}}}
    }
    result = {
        "swagger": "2.0",
        "host": f"{PROJECT_REF}.supabase.co:443",
        "basePath": "/",
        "schemes": ["https"],
        "paths": paths,
        "info": {"title": "public schema"},
    }
    if version is not None:
        result["info"]["version"] = version
    return result


class FakeResponse:
    def __init__(
        self,
        *,
        url: str,
        body: object,
        request_id: str,
        status: int = 200,
        final_url: str | None = None,
        content_type: str = "application/json",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._url = final_url or url
        self._body = body if isinstance(body, bytes) else _json_bytes(body)
        self.headers = {
            "Content-Type": content_type,
            "X-Request-Id": request_id,
            **(extra_headers or {}),
        }
        self.closed = False

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def close(self) -> None:
        self.closed = True


class FakeOpener:
    def __init__(
        self,
        *,
        management: object | None = None,
        openapi: object | None = None,
        identity: object | None = None,
        status_for: dict[str, int] | None = None,
        redirect_for: str | None = None,
        postgrest_header: str | None = "PostgREST/14.1.0",
    ) -> None:
        self.management = management or {
            "db_schema": "public, storage, graphql_public",
            "max_rows": 1000,
            "db_pool": 15,
            "jwt_secret": MANAGEMENT_SECRET,
            "future_nested": {"api_token": "another-secret"},
        }
        self.openapi = openapi or _openapi()
        self.identity = identity or {
            "current_user": "p1_readonly",
            "transaction_read_only": "on",
            "statement_timeout": "30s",
        }
        self.status_for = status_for or {}
        self.redirect_for = redirect_for
        self.postgrest_header = postgrest_header
        self.requests: list[tuple[object, float]] = []

    def open(self, request: object, *, timeout: float) -> FakeResponse:
        self.requests.append((request, timeout))
        url = request.full_url
        if url.endswith(f"/v1/projects/{PROJECT_REF}/postgrest"):
            endpoint, body, content_type = "management", self.management, "application/json"
        elif url.endswith(
            f"/v1/projects/{PROJECT_REF}/database/openapi?schema=public"
        ):
            endpoint, body, content_type = "openapi", self.openapi, "application/openapi+json"
        elif url.endswith("/rest/v1/rpc/p1_runtime_identity_v1"):
            endpoint, body, content_type = "identity", self.identity, "application/json"
        else:  # pragma: no cover - makes any accidental target obvious.
            raise AssertionError(f"unexpected target: {url}")
        headers = {}
        if endpoint == "openapi" and self.postgrest_header is not None:
            headers["Server"] = self.postgrest_header
        final_url = f"{url.rstrip('/')}/redirected" if endpoint == self.redirect_for else None
        return FakeResponse(
            url=url,
            final_url=final_url,
            body=body,
            request_id=f"request-{endpoint}",
            status=self.status_for.get(endpoint, 200),
            content_type=content_type,
            extra_headers=headers,
        )


def _capture(opener: FakeOpener, **kwargs: object) -> dict:
    return receipts.capture_postgrest_evidence(
        supabase_url=SUPABASE_URL,
        access_token=PAT,
        p1_jwt=P1_JWT,
        supabase_key=SUPABASE_KEY,
        expected_identity_function_sha256=IDENTITY_SHA,
        opener=opener,
        captured_at="2026-07-21T12:00:00Z",
        **kwargs,
    )


def test_happy_capture_builds_exact_snapshot_and_safe_http_receipts() -> None:
    opener = FakeOpener()
    evidence = _capture(opener)

    snapshot = evidence["postgrest_snapshot"]
    assert snapshot["schema"] == receipts.live.POSTGREST_SCHEMA
    assert snapshot["project_ref"] == PROJECT_REF
    assert snapshot["openapi_sha256"] == hashlib.sha256(
        _json_bytes(opener.openapi)
    ).hexdigest()
    assert snapshot["rpc_methods"] == {
        path: ["POST"] for path in receipts.live.REQUIRED_RPC_METHODS
    }
    assert snapshot["runtime_config"] == {
        "data_api_enabled": True,
        "exposed_schemas": ["graphql_public", "public", "storage"],
        "max_rows": 1000,
        "postgrest_version": "14.1.0",
    }
    assert snapshot["identity_probe"] == {
        "path": "/rpc/p1_runtime_identity_v1",
        "method": "GET",
        "status": 200,
        "current_user": "p1_readonly",
        "transaction_read_only": "on",
        "statement_timeout": "30s",
        "transaction_mode_scope": "identity_get_only_not_rpc_post",
        "function_definition_sha256_lf": IDENTITY_SHA,
    }

    serialized = json.dumps(evidence, sort_keys=True)
    assert PAT not in serialized
    assert P1_JWT not in serialized
    assert SUPABASE_KEY not in serialized
    assert MANAGEMENT_SECRET not in serialized
    assert "another-secret" not in serialized
    assert "headers" not in serialized.lower()
    assert set(evidence["http_receipts"]) == {
        "schema",
        "management_postgrest",
        "postgrest_openapi",
        "postgrest_identity",
    }
    for name, receipt in evidence["http_receipts"].items():
        if name == "schema":
            continue
        assert set(receipt) == {
            "method",
            "origin",
            "path",
            "status",
            "request_id",
            "body_sha256",
            "principal_sha256",
            "api_key_sha256",
        }
        assert "?" not in receipt["path"]
        assert len(receipt["body_sha256"]) == 64
        assert len(receipt["principal_sha256"]) == 64
        if name in {"management_postgrest", "postgrest_openapi"}:
            assert receipt["api_key_sha256"] is None
        else:
            assert len(receipt["api_key_sha256"]) == 64

    assert len(opener.requests) == 3
    assert all(timeout == receipts.HTTP_TIMEOUT_SECONDS for _, timeout in opener.requests)
    management_request = opener.requests[0][0]
    management_headers = {key.lower(): value for key, value in management_request.header_items()}
    assert management_request.get_method() == "GET"
    assert management_headers["authorization"] == f"Bearer {PAT}"
    openapi_headers = {
        key.lower(): value for key, value in opener.requests[1][0].header_items()
    }
    assert opener.requests[1][0].full_url == (
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/openapi"
        "?schema=public"
    )
    assert openapi_headers["authorization"] == f"Bearer {PAT}"
    assert "accept-profile" not in openapi_headers
    assert "apikey" not in openapi_headers
    assert P1_JWT not in openapi_headers.values()
    identity_headers = {
        key.lower(): value for key, value in opener.requests[2][0].header_items()
    }
    assert identity_headers["authorization"] == f"Bearer {P1_JWT}"
    assert identity_headers["apikey"] == SUPABASE_KEY


def test_management_secret_is_discarded_before_validation_errors() -> None:
    secret = "do-not-ever-echo-this-value"
    opener = FakeOpener(
        management={
            "db_schema": "public",
            "max_rows": "invalid",
            "jwt_secret": secret,
            "password": "also-secret",
        }
    )
    with pytest.raises(receipts.live.ManifestHold) as caught:
        _capture(opener)
    assert caught.value.code == "HOLD_POSTGREST_CONFIG_UNVERIFIED"
    assert secret not in str(caught.value)
    assert "also-secret" not in str(caught.value)


def test_wrong_project_ref_and_openapi_host_fail_before_trust() -> None:
    opener = FakeOpener()
    with pytest.raises(receipts.live.ManifestHold, match="HOLD_SUPABASE_PROJECT_MISMATCH"):
        _capture(opener, expected_project_ref=OTHER_REF)
    assert opener.requests == []

    changed = _openapi()
    changed["host"] = f"{OTHER_REF}.supabase.co"
    with pytest.raises(
        receipts.live.ManifestHold, match="HOLD_POSTGREST_OPENAPI_PROJECT_DRIFT"
    ):
        _capture(FakeOpener(openapi=changed))


@pytest.mark.parametrize("base_path", ["/rest/v1", "/rest/v1/", "/other", ""])
def test_management_openapi_rejects_legacy_or_other_base_paths(
    base_path: str,
) -> None:
    changed = _openapi()
    changed["basePath"] = base_path

    with pytest.raises(
        receipts.live.ManifestHold, match="HOLD_POSTGREST_OPENAPI_PROJECT_DRIFT"
    ):
        _capture(FakeOpener(openapi=changed))


@pytest.mark.parametrize(
    "url",
    [
        (
            f"https://example.invalid/v1/projects/{PROJECT_REF}/database/openapi"
            "?schema=public"
        ),
        (
            f"https://api.supabase.com/v1/projects/{OTHER_REF}/database/openapi"
            "?schema=public"
        ),
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/openapi",
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/openapi?schema=private",
        (
            f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/openapi"
            "?schema=public&schema=private"
        ),
        (
            f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/openapi"
            "?schema=public&extra=1"
        ),
    ],
)
def test_management_openapi_schema_query_is_exact_and_fails_before_transport(
    url: str,
) -> None:
    class NeverOpener:
        calls = 0

        def open(self, request: object, *, timeout: float) -> object:
            self.calls += 1
            raise AssertionError("transport must not run for a target-contract violation")

    opener = NeverOpener()
    with pytest.raises(receipts.live.ManifestHold) as caught:
        receipts._safe_get_json(  # noqa: SLF001
            url=url,
            headers={"Authorization": f"Bearer {PAT}"},
            credential_kind="supabase-management-pat",
            credential=PAT,
            expected_origin=receipts.MANAGEMENT_ORIGIN,
            expected_path=f"/v1/projects/{PROJECT_REF}/database/openapi",
            expected_query={"schema": ["public"]},
            endpoint="management-postgrest-openapi",
            opener=opener,  # type: ignore[arg-type]
        )

    assert caught.value.code == "HOLD_HTTP_TARGET_INVALID"
    assert PAT not in str(caught.value)
    assert opener.calls == 0


def test_rpc_methods_are_exact_and_fail_closed() -> None:
    changed = _openapi()
    changed["paths"]["/rpc/match_hyq"] = {
        "get": {"responses": {"200": {"description": "OK"}}},
        "post": {"responses": {"200": {"description": "OK"}}},
    }
    with pytest.raises(receipts.live.ManifestHold, match="HOLD_POSTGREST_RPC_SURFACE_DRIFT"):
        _capture(FakeOpener(openapi=changed))


@pytest.mark.parametrize(
    "identity",
    [
        {
            "current_user": "postgres",
            "transaction_read_only": "on",
            "statement_timeout": "30s",
        },
        {
            "current_user": "p1_readonly",
            "transaction_read_only": "off",
            "statement_timeout": "30s",
        },
        {
            "current_user": "p1_readonly",
            "transaction_read_only": "on",
            "statement_timeout": "30s",
            "unexpected": "field",
        },
    ],
)
def test_identity_probe_must_be_exact(identity: dict) -> None:
    with pytest.raises(receipts.live.ManifestHold, match="HOLD_POSTGREST_IDENTITY_UNVERIFIED"):
        _capture(FakeOpener(identity=identity))


def test_postgrest_version_is_required_and_sources_must_agree() -> None:
    with pytest.raises(receipts.live.ManifestHold, match="HOLD_POSTGREST_VERSION_UNVERIFIED"):
        _capture(FakeOpener(openapi=_openapi(version=None), postgrest_header=None))

    with pytest.raises(receipts.live.ManifestHold, match="HOLD_POSTGREST_VERSION_DRIFT"):
        _capture(
            FakeOpener(
                openapi=_openapi(version="14.2.0"),
                postgrest_header="PostgREST/14.1.0",
            )
        )


@pytest.mark.parametrize("endpoint", ["management", "openapi", "identity"])
def test_non_200_status_fails_closed(endpoint: str) -> None:
    with pytest.raises(receipts.live.ManifestHold, match="HOLD_HTTP_STATUS_INVALID"):
        _capture(FakeOpener(status_for={endpoint: 503}))


@pytest.mark.parametrize("endpoint", ["management", "openapi", "identity"])
def test_redirects_are_rejected(endpoint: str) -> None:
    with pytest.raises(receipts.live.ManifestHold, match="HOLD_HTTP_REDIRECT_FORBIDDEN"):
        _capture(FakeOpener(redirect_for=endpoint))


def test_timeout_is_single_attempt_and_fails_without_echoing_credentials() -> None:
    class TimeoutOpener:
        calls = 0

        def open(self, request: object, *, timeout: float) -> object:
            self.calls += 1
            assert timeout == receipts.HTTP_TIMEOUT_SECONDS
            raise TimeoutError(f"request carried {PAT}")

    opener = TimeoutOpener()
    with pytest.raises(receipts.live.ManifestHold) as caught:
        _capture(opener)  # type: ignore[arg-type]
    assert caught.value.code == "HOLD_HTTP_TIMEOUT"
    assert PAT not in str(caught.value)
    assert opener.calls == 1


class FakeCursor:
    def __init__(self, statements: list[str]) -> None:
        self.statements = statements
        self.closed = False

    def execute(self, sql: str) -> None:
        self.statements.append(sql)

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, *, host: str, port: int = 5432, ssl: bool = True) -> None:
        self.info = SimpleNamespace(
            host=host,
            port=port,
            user=f"postgres.{PROJECT_REF}",
            ssl_in_use=ssl,
        )
        self.autocommit = False
        self.statements: list[str] = []
        self.rollback_count = 0
        self.close_count = 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self.statements)

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.close_count += 1


def _database_url(*, port: int = 5432) -> str:
    return (
        f"postgresql://postgres.{PROJECT_REF}:database-password@"
        f"aws-0-eu-north-1.pooler.supabase.com:{port}/postgres"
    )


def test_database_opens_tls_and_sets_read_only_before_yield() -> None:
    connection = FakeConnection(host="aws-0-eu-north-1.pooler.supabase.com")
    calls: list[tuple[str, dict]] = []

    def connector(database_url: str, **kwargs: object) -> FakeConnection:
        calls.append((database_url, kwargs))
        return connection

    with receipts.open_readonly_database(
        _database_url(), project_ref=PROJECT_REF, connector=connector
    ) as opened:
        assert opened is connection
        assert connection.statements == [
            "BEGIN",
            "SET TRANSACTION READ ONLY",
            "SET LOCAL ROLE p1_readonly",
        ]
        assert connection.autocommit is True
    assert calls[0][1]["sslmode"] == "require"
    assert connection.rollback_count == 1
    assert connection.close_count == 1


def test_transaction_pooler_is_rejected_before_connect() -> None:
    called = False

    def connector(*args: object, **kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("must not connect")

    with pytest.raises(
        receipts.live.ManifestHold, match="HOLD_FENCE_PERSISTENT_SESSION_REQUIRED"
    ):
        with receipts.open_readonly_database(
            _database_url(port=6543), project_ref=PROJECT_REF, connector=connector
        ):
            pass
    assert called is False


def test_capture_phase_calls_manifest_only_after_read_only_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection(host="aws-0-eu-north-1.pooler.supabase.com")
    snapshot = {"schema": receipts.live.POSTGREST_SCHEMA}
    evidence = {
        "project_ref": PROJECT_REF,
        "postgrest_snapshot": snapshot,
    }
    monkeypatch.setattr(receipts, "capture_postgrest_evidence", lambda **kwargs: evidence)

    observed: dict[str, object] = {}

    def fake_manifest(conn: FakeConnection, **kwargs: object) -> dict:
        observed["statements"] = list(conn.statements)
        observed["kwargs"] = kwargs
        return {"schema": "fixture", "phase": kwargs["phase"]}

    monkeypatch.setattr(receipts.live, "capture_live_manifest", fake_manifest)
    monkeypatch.setattr(
        receipts,
        "build_identity_guard_receipt",
        lambda **kwargs: {"schema": guard.IDENTITY_RECEIPT_SCHEMA},
    )
    capture, returned_evidence = receipts.capture_live_phase(
        phase="pre",
        visual_assets_registry="on",
        supabase_url=SUPABASE_URL,
        access_token=PAT,
        p1_jwt=P1_JWT,
        supabase_key=SUPABASE_KEY,
        database_url=_database_url(),
        expected_identity_function_sha256=IDENTITY_SHA,
        connector=lambda *args, **kwargs: connection,
    )
    assert observed["statements"] == [
        "BEGIN",
        "SET TRANSACTION READ ONLY",
        "SET LOCAL ROLE p1_readonly",
    ]
    assert observed["kwargs"]["postgrest_snapshot"] is snapshot
    assert capture["phase"] == "pre"
    assert returned_evidence is evidence
    assert returned_evidence["identity_guard_receipt"] == {
        "schema": guard.IDENTITY_RECEIPT_SCHEMA
    }


def test_identity_receipt_interoperates_with_real_postgrest_guard() -> None:
    manifest_capture, function_hashes = manifest_fixtures._capture()
    manifest_contract = receipts.live.build_manifest_contract(
        manifest_capture,
        expected_function_sha256=function_hashes,
    )
    identity_function_sha = next(
        row["definition_sha256_lf"]
        for row in manifest_capture["manifest"]["functions"]
        if row["name"] == receipts.live.IDENTITY_FUNCTION
    )
    evidence = receipts.capture_postgrest_evidence(
        supabase_url=SUPABASE_URL,
        access_token=PAT,
        p1_jwt=P1_JWT,
        supabase_key=SUPABASE_KEY,
        expected_identity_function_sha256=identity_function_sha,
        opener=FakeOpener(),
        captured_at=manifest_capture["captured_at"],
    )
    identity_receipt = receipts.build_identity_guard_receipt(
        evidence=evidence,
        manifest_capture=manifest_capture,
        p1_jwt=P1_JWT,
        supabase_key=SUPABASE_KEY,
    )

    capability = guard.verify_and_bind_identity_receipt(
        manifest_contract=manifest_contract,
        manifest_capture=manifest_capture,
        identity_http_receipt=identity_receipt,
        p1_jwt=P1_JWT,
        supabase_key=SUPABASE_KEY,
    )
    assert identity_receipt["schema"] == guard.IDENTITY_RECEIPT_SCHEMA
    assert identity_receipt["principal_sha256"] == hashlib.sha256(
        P1_JWT.encode("utf-8")
    ).hexdigest()
    assert capability.principal_sha256 == identity_receipt["principal_sha256"]
    assert identity_receipt["api_key_sha256"] == hashlib.sha256(
        SUPABASE_KEY.encode("utf-8")
    ).hexdigest()
    assert capability.api_key_sha256 == identity_receipt["api_key_sha256"]
    serialized = json.dumps(identity_receipt, sort_keys=True)
    assert P1_JWT not in serialized
    assert PAT not in serialized
    assert SUPABASE_KEY not in serialized


def test_pre_materialization_is_exclusive_and_never_serializes_inputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pre = {"schema": "pre-fixture", "phase": "pre"}
    evidence = {"schema": receipts.HTTP_EVIDENCE_SCHEMA, "safe": True}
    contract = {"schema": "contract-fixture"}
    monkeypatch.setattr(
        receipts,
        "capture_live_phase",
        lambda **kwargs: (copy.deepcopy(pre), copy.deepcopy(evidence)),
    )
    monkeypatch.setattr(
        receipts.live,
        "build_manifest_contract",
        lambda capture: copy.deepcopy(contract),
    )
    paths = {
        "pre_path": tmp_path / "pre.json",
        "contract_path": tmp_path / "contract.json",
        "http_evidence_path": tmp_path / "http.json",
    }
    receipts.materialize_pre_contract(
        **paths,
        visual_assets_registry="on",
        supabase_url=SUPABASE_URL,
        access_token=PAT,
        p1_jwt=P1_JWT,
        supabase_key=SUPABASE_KEY,
        database_url=_database_url(),
        expected_identity_function_sha256=IDENTITY_SHA,
    )
    combined = "".join(path.read_text(encoding="utf-8") for path in paths.values())
    assert PAT not in combined
    assert P1_JWT not in combined
    assert SUPABASE_KEY not in combined
    assert "database-password" not in combined
    with pytest.raises(receipts.live.ManifestHold, match="HOLD_RECEIPT_PATH_EXISTS"):
        receipts.materialize_pre_contract(
            **paths,
            visual_assets_registry="on",
            supabase_url=SUPABASE_URL,
            access_token=PAT,
            p1_jwt=P1_JWT,
            supabase_key=SUPABASE_KEY,
            database_url=_database_url(),
            expected_identity_function_sha256=IDENTITY_SHA,
        )


def test_materialized_window_delegates_exact_pre_watch_post(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    values = {
        "contract.json": {"kind": "contract"},
        "pre.json": {"phase": "pre"},
        "watch.json": {"phase": "watch"},
        "post.json": {"phase": "post"},
    }
    for name, value in values.items():
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    observed: dict[str, object] = {}
    monkeypatch.setattr(
        receipts.live,
        "verify_manifest_window",
        lambda contract, captures: observed.update(
            contract=contract, captures=captures
        ),
    )
    receipts.verify_materialized_window(
        contract_path=tmp_path / "contract.json",
        pre_path=tmp_path / "pre.json",
        watch_paths=[tmp_path / "watch.json"],
        post_path=tmp_path / "post.json",
    )
    assert observed["contract"] == values["contract.json"]
    assert [row["phase"] for row in observed["captures"]] == [
        "pre",
        "watch",
        "post",
    ]
