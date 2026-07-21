from __future__ import annotations

import base64
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json

import httpx
import pytest

from scripts import s277_c1_p1_postgrest_guard as guard


PROJECT_REF = "abcdefghijklmnopqrst"
SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"
NOW_EPOCH = 2_000_000_000.0
CAPTURED_AT = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


def _b64(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _jwt(**claim_overrides) -> str:
    claims = {
        "iss": f"{SUPABASE_URL}/auth/v1",
        "aud": "authenticated",
        "exp": NOW_EPOCH + 3600,
        "iat": NOW_EPOCH - 60,
        "ref": PROJECT_REF,
        "role": "p1_readonly",
    }
    claims.update(claim_overrides)
    return f"{_b64({'alg': 'HS256', 'typ': 'JWT'})}.{_b64(claims)}.c2lnbmF0dXJl"


def _manifest(*, visual: str = "on") -> tuple[dict, dict]:
    identity = {
        "path": "/rpc/p1_runtime_identity_v1",
        "method": "GET",
        "status": 200,
        "current_user": "p1_readonly",
        "transaction_read_only": "on",
        "statement_timeout": "30s",
        "function_definition_sha256_lf": "b" * 64,
    }
    capture = {
        "schema": "s277_c1_p1_live_manifest_v1",
        "phase": "pre",
        "captured_at": CAPTURED_AT.isoformat().replace("+00:00", "Z"),
        "manifest_sha256": "a" * 64,
        "manifest": {
            "project_ref": PROJECT_REF,
            "visual_assets_registry": visual,
            "postgrest": {"identity_probe": identity},
        },
    }
    contract = {"schema": "fixture-contract"}
    return contract, capture


def _identity_receipt(token: str, capture: dict) -> dict:
    payload = {
        "current_user": "p1_readonly",
        "transaction_read_only": "on",
        "statement_timeout": "30s",
    }
    payload_raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return {
        "schema": guard.IDENTITY_RECEIPT_SCHEMA,
        "project_ref": PROJECT_REF,
        "manifest_sha256": capture["manifest_sha256"],
        "captured_at": (CAPTURED_AT - timedelta(seconds=2)).isoformat().replace(
            "+00:00", "Z"
        ),
        "method": "GET",
        "path": guard.IDENTITY_PATH,
        "status": 200,
        "redirect_count": 0,
        "request_id": "identity-request-1",
        "body_sha256": hashlib.sha256(payload_raw).hexdigest(),
        "payload_sha256": hashlib.sha256(payload_raw).hexdigest(),
        "principal_sha256": hashlib.sha256(token.encode()).hexdigest(),
        "payload": payload,
    }


def _capability(monkeypatch, token: str, *, visual: str = "on"):
    contract, capture = _manifest(visual=visual)
    calls = []

    def _verified(actual_contract, actual_capture):
        calls.append((actual_contract, actual_capture))

    monkeypatch.setattr(guard._live_manifest, "verify_manifest_capture", _verified)
    capability = guard.verify_and_bind_identity_receipt(
        manifest_contract=contract,
        manifest_capture=capture,
        identity_http_receipt=_identity_receipt(token, capture),
        p1_jwt=token,
    )
    assert calls == [(contract, capture)]
    return capability


class _Response:
    def __init__(
        self,
        status: int = 200,
        body: bytes = b"[]",
        *,
        request_id: str | None = "request-1",
        history=(),
    ) -> None:
        self.status_code = status
        self.content = body
        self.headers = {} if request_id is None else {"x-request-id": request_id}
        self.history = history

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        if not 200 <= self.status_code < 300:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeFactory:
    def __init__(self, responses=None) -> None:
        self.responses = list(responses or [])
        self.calls: list[dict] = []
        self.client_kwargs: list[dict] = []

    def __call__(self, *args, **kwargs):
        self.client_kwargs.append(dict(kwargs))
        return _FakeClient(self)


class _FakeClient:
    def __init__(self, factory: _FakeFactory) -> None:
        self.factory = factory

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def request(self, method, url, **kwargs):
        self.factory.calls.append({"method": method, "url": url, "kwargs": kwargs})
        if self.factory.responses:
            return self.factory.responses.pop(0)
        return _Response()


def _new_guard(monkeypatch, *, token=None, visual="on", factory=None):
    token = token or _jwt()
    factory = factory or _FakeFactory()
    capability = _capability(monkeypatch, token, visual=visual)
    instance = guard.P1PostgrestGuard(
        supabase_url=SUPABASE_URL,
        p1_jwt=token,
        project_ref=PROJECT_REF,
        visual_assets_registry=visual,
        verified_identity=capability,
        client_factory=factory,
        now_epoch=lambda: NOW_EPOCH,
    )
    return instance, factory, token


def _headers(token: str) -> dict[str, str]:
    return {"apikey": token, "Authorization": f"Bearer {token}"}


def test_happy_paths_patch_only_product_modules_and_emit_safe_receipts(monkeypatch) -> None:
    from src.rag import retriever, visual_assets

    responses = [
        _Response(body=b'[{"id":"chunk-1"}]', request_id="get-1"),
        _Response(body=b'[{"id":"chunk-2"}]', request_id="rpc-1"),
        _Response(body=b'[{"storage_url":"safe"}]', request_id=None),
    ]
    instance, factory, token = _new_guard(
        monkeypatch, factory=_FakeFactory(responses)
    )
    originals = {
        "retriever_httpx": retriever.httpx,
        "retriever_url": retriever.SUPABASE_URL,
        "retriever_key": retriever.SUPABASE_SERVICE_KEY,
        "visual_httpx": visual_assets.httpx,
        "visual_url": visual_assets.SUPABASE_URL,
        "visual_key": visual_assets.SUPABASE_SERVICE_KEY,
        "global_client": httpx.Client,
    }

    with instance:
        assert retriever.httpx is visual_assets.httpx
        assert retriever.httpx is not httpx
        assert httpx.Client is originals["global_client"]
        assert retriever.SUPABASE_URL == visual_assets.SUPABASE_URL == SUPABASE_URL
        assert retriever.SUPABASE_SERVICE_KEY == visual_assets.SUPABASE_SERVICE_KEY == token
        with retriever.httpx.Client(timeout=5.0) as client:
            client.get(
                f"{SUPABASE_URL}/rest/v1/chunks_v2?select=id&content=eq.secret-query",
                headers=_headers(token),
            )
            client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/match_chunks_v2",
                headers={**_headers(token), "Content-Type": "application/json"},
                json={"query_embedding": [0.1]},
            )
        with visual_assets.httpx.Client(timeout=3.0) as client:
            client.get(
                f"{SUPABASE_URL}/rest/v1/document_visual_assets",
                headers=_headers(token),
                params={"document_id": "eq.private-value"},
            )

        receipts = instance.receipts
        assert [(row["method"], row["path"]) for row in receipts] == [
            ("GET", "/rest/v1/chunks_v2"),
            ("POST", "/rest/v1/rpc/match_chunks_v2"),
            ("GET", "/rest/v1/document_visual_assets"),
        ]
        assert [row["ordinal"] for row in receipts] == [1, 2, 3]
        assert receipts[0]["request_id"] == "get-1"
        assert receipts[2]["request_id"] is None
        encoded = json.dumps(receipts, sort_keys=True)
        assert token not in encoded
        assert "secret-query" not in encoded
        assert "private-value" not in encoded
        assert "headers" not in encoded.lower()
        assert all(len(row["body_sha256"]) == 64 for row in receipts)

    assert retriever.httpx is originals["retriever_httpx"]
    assert retriever.SUPABASE_URL == originals["retriever_url"]
    assert retriever.SUPABASE_SERVICE_KEY == originals["retriever_key"]
    assert visual_assets.httpx is originals["visual_httpx"]
    assert visual_assets.SUPABASE_URL == originals["visual_url"]
    assert visual_assets.SUPABASE_SERVICE_KEY == originals["visual_key"]
    assert httpx.Client is originals["global_client"]
    assert all(row["follow_redirects"] is False for row in factory.client_kwargs)
    assert all(row["trust_env"] is False for row in factory.client_kwargs)


@pytest.mark.parametrize(
    ("method", "url", "visual", "code"),
    [
        ("PATCH", f"{SUPABASE_URL}/rest/v1/chunks_v2", "on", "HOLD_P1_POSTGREST_SURFACE_BLOCKED"),
        ("GET", f"{SUPABASE_URL}/rest/v1/chunks_v2_hyq", "on", "HOLD_P1_POSTGREST_SURFACE_BLOCKED"),
        ("POST", f"{SUPABASE_URL}/rest/v1/rpc/corpus_fingerprint_v1", "on", "HOLD_P1_POSTGREST_SURFACE_BLOCKED"),
        ("GET", "https://evil.example/rest/v1/chunks_v2", "on", "HOLD_P1_POSTGREST_URL_BLOCKED"),
        ("GET", f"http://{PROJECT_REF}.supabase.co/rest/v1/chunks_v2", "on", "HOLD_P1_POSTGREST_URL_BLOCKED"),
        ("GET", f"{SUPABASE_URL}/rest/v1/document_visual_assets", "off", "HOLD_P1_POSTGREST_SURFACE_BLOCKED"),
    ],
)
def test_method_path_host_scheme_and_visual_off_block_before_transport(
    monkeypatch, method, url, visual, code
) -> None:
    from src.rag import retriever

    instance, factory, token = _new_guard(monkeypatch, visual=visual)
    with instance:
        with pytest.raises(guard.PostgrestGuardHold) as caught:
            with retriever.httpx.Client(timeout=1.0) as client:
                client.request(method, url, headers=_headers(token))
    assert caught.value.code == code
    assert factory.calls == []


def test_service_role_wrong_audience_project_and_expiry_are_rejected(monkeypatch) -> None:
    cases = [
        (_jwt(role="service_role"), "HOLD_P1_JWT_ROLE_INVALID"),
        (_jwt(aud="anon"), "HOLD_P1_JWT_AUDIENCE_INVALID"),
        (_jwt(iss="https://other.supabase.co/auth/v1"), "HOLD_P1_JWT_PROJECT_INVALID"),
        (_jwt(exp=NOW_EPOCH), "HOLD_P1_JWT_EXPIRED"),
    ]
    for token, expected_code in cases:
        capability = _capability(monkeypatch, token)
        factory = _FakeFactory()
        with pytest.raises(guard.PostgrestGuardHold) as caught:
            guard.P1PostgrestGuard(
                supabase_url=SUPABASE_URL,
                p1_jwt=token,
                project_ref=PROJECT_REF,
                visual_assets_registry="on",
                verified_identity=capability,
                client_factory=factory,
                now_epoch=lambda: NOW_EPOCH,
            )
        assert caught.value.code == expected_code
        assert factory.calls == []
        assert token not in str(caught.value)


def test_header_override_and_redirect_option_block_before_transport(monkeypatch) -> None:
    instance, factory, token = _new_guard(monkeypatch)
    from src.rag import retriever

    with instance:
        with retriever.httpx.Client(timeout=1.0) as client:
            with pytest.raises(guard.PostgrestGuardHold) as wrong_header:
                client.get(
                    f"{SUPABASE_URL}/rest/v1/chunks_v2",
                    headers={"apikey": "other", "Authorization": f"Bearer {token}"},
                )
            with pytest.raises(guard.PostgrestGuardHold) as redirect:
                client.get(
                    f"{SUPABASE_URL}/rest/v1/chunks_v2",
                    headers=_headers(token),
                    follow_redirects=True,
                )
    assert wrong_header.value.code == "HOLD_P1_POSTGREST_AUTH_INVALID"
    assert redirect.value.code == "HOLD_P1_POSTGREST_REDIRECT_BLOCKED"
    assert factory.calls == []


def test_redirect_response_and_non_2xx_are_receipted_then_rejected(monkeypatch) -> None:
    responses = [_Response(302, b"redirect"), _Response(500, b"failure")]
    instance, factory, token = _new_guard(
        monkeypatch,
        factory=_FakeFactory(responses),
    )
    from src.rag import retriever

    with instance:
        for expected_code in (
            "HOLD_P1_POSTGREST_REDIRECT_BLOCKED",
            "HOLD_P1_POSTGREST_STATUS_INVALID",
        ):
            with retriever.httpx.Client(timeout=1.0) as client:
                with pytest.raises(guard.PostgrestGuardHold) as caught:
                    client.get(
                        f"{SUPABASE_URL}/rest/v1/chunks_v2",
                        headers=_headers(token),
                    )
            assert caught.value.code == expected_code
    assert len(factory.calls) == 2
    assert [row["status"] for row in instance.receipts] == [302, 500]


def test_globals_restore_on_product_exception_and_lock_is_non_reentrant(monkeypatch) -> None:
    from src.rag import retriever, visual_assets

    original_retriever = (retriever.httpx, retriever.SUPABASE_URL, retriever.SUPABASE_SERVICE_KEY)
    original_visual = (visual_assets.httpx, visual_assets.SUPABASE_URL, visual_assets.SUPABASE_SERVICE_KEY)
    first, _, _ = _new_guard(monkeypatch)
    second, _, _ = _new_guard(monkeypatch)

    with pytest.raises(RuntimeError, match="product failed"):
        with first:
            with pytest.raises(guard.PostgrestGuardHold) as nested:
                second.__enter__()
            assert nested.value.code == "HOLD_P1_POSTGREST_GUARD_REENTRANT"
            raise RuntimeError("product failed")

    assert (retriever.httpx, retriever.SUPABASE_URL, retriever.SUPABASE_SERVICE_KEY) == original_retriever
    assert (visual_assets.httpx, visual_assets.SUPABASE_URL, visual_assets.SUPABASE_SERVICE_KEY) == original_visual
    with second:
        assert second.active


def test_identity_receipt_forgery_principal_and_manifest_probe_drift_fail_closed(monkeypatch) -> None:
    token = _jwt()
    contract, capture = _manifest()
    monkeypatch.setattr(guard._live_manifest, "verify_manifest_capture", lambda *_: None)

    forged = _identity_receipt(token, capture)
    forged["principal_sha256"] = "0" * 64
    with pytest.raises(guard.PostgrestGuardHold) as principal:
        guard.verify_and_bind_identity_receipt(
            manifest_contract=contract,
            manifest_capture=capture,
            identity_http_receipt=forged,
            p1_jwt=token,
        )
    assert principal.value.code == "HOLD_P1_IDENTITY_PRINCIPAL_DRIFT"

    drifted = _identity_receipt(token, capture)
    drifted["payload"]["current_user"] = "service_role"
    drifted["payload_sha256"] = hashlib.sha256(
        json.dumps(
            drifted["payload"], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    with pytest.raises(guard.PostgrestGuardHold) as identity:
        guard.verify_and_bind_identity_receipt(
            manifest_contract=contract,
            manifest_capture=capture,
            identity_http_receipt=drifted,
            p1_jwt=token,
        )
    assert identity.value.code == "HOLD_P1_IDENTITY_DRIFT"

    def _reject_manifest(*_):
        raise RuntimeError("manifest verifier rejected capture")

    monkeypatch.setattr(guard._live_manifest, "verify_manifest_capture", _reject_manifest)
    with pytest.raises(RuntimeError, match="manifest verifier"):
        guard.verify_and_bind_identity_receipt(
            manifest_contract=contract,
            manifest_capture=capture,
            identity_http_receipt=_identity_receipt(token, capture),
            p1_jwt=token,
        )


def test_capability_cannot_be_constructed_directly() -> None:
    with pytest.raises(TypeError, match="verify_and_bind_identity_receipt"):
        guard.VerifiedPostgrestIdentity(
            project_ref=PROJECT_REF,
            visual_assets_registry="on",
            manifest_sha256="a" * 64,
            principal_sha256="b" * 64,
            function_definition_sha256_lf="c" * 64,
            identity_captured_at="2026-07-21T12:00:00Z",
            _proof=object(),
        )
