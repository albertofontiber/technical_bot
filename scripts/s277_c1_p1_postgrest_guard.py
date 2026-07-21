"""Fail-closed PostgREST transport guard for the S277 C1/P1 product path.

The product retriever was written for a service-role credential.  P1 must run
the same product code while proving that every Supabase request uses the
dedicated ``p1_readonly`` JWT and stays inside the preregistered read surface.
This module supplies that narrow runtime boundary without patching the global
``httpx`` package (and therefore without touching Anthropic or Voyage traffic).

JWT claims are decoded locally only as an early shape/expiry check.  They are
not treated as proof of authenticity.  Authenticity and database-role identity
are bound to an HTTP receipt for ``p1_runtime_identity_v1`` which must match a
capture accepted by :func:`scripts.s277_c1_p1_live_manifest.verify_manifest_capture`.
Only SHA-256 fingerprints of the JWT and project API key are retained in that
capability; credentials, headers and query values never enter receipts or
exception details.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import threading
import time
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

import httpx as _real_httpx

from scripts import s277_c1_p1_live_manifest as _live_manifest


IDENTITY_RECEIPT_SCHEMA = "s277_c1_p1_postgrest_identity_http_receipt_v1"
REQUEST_RECEIPT_SCHEMA = "s277_c1_p1_postgrest_request_receipt_v1"
P1_ROLE = "p1_readonly"
EXPECTED_AUDIENCE = "authenticated"
IDENTITY_PATH = "/rest/v1/rpc/p1_runtime_identity_v1"

_PROJECT_REF_RE = re.compile(r"^[a-z0-9]{20}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PUBLISHABLE_KEY_RE = re.compile(r"^sb_publishable_[A-Za-z0-9._-]+$")
_FORBIDDEN_ROLES = frozenset({"anon", "authenticated", "service_role"})
_ALLOWED_GET_PATHS_BASE = frozenset(
    {
        "/rest/v1/chunks_v2",
        "/rest/v1/documents",
    }
)
_VISUAL_PATH = "/rest/v1/document_visual_assets"
_ALLOWED_POST_PATHS = frozenset(
    {
        "/rest/v1/rpc/match_chunks_v2",
        "/rest/v1/rpc/search_chunks_text_v2",
        "/rest/v1/rpc/match_chunks_v2_enunciados",
        "/rest/v1/rpc/match_hyq",
    }
)
_PATCH_LOCK = threading.Lock()
_CAPABILITY_PROOF = object()


class PostgrestGuardHold(RuntimeError):
    """Stable P1 stop condition whose detail never contains credential data."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _hold(code: str, detail: str) -> None:
    raise PostgrestGuardHold(code, detail)


def _expect(condition: bool, code: str, detail: str) -> None:
    if not condition:
        _hold(code, detail)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _exact_keys(
    value: Mapping[str, Any], expected: set[str], *, code: str, path: str
) -> None:
    actual = set(value)
    _expect(
        actual == expected,
        code,
        f"{path} keys drift: missing_count={len(expected - actual)} "
        f"extra_count={len(actual - expected)}",
    )


def _utc_timestamp(value: Any, *, code: str) -> datetime:
    _expect(isinstance(value, str), code, "captured_at must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PostgrestGuardHold(code, "captured_at is invalid") from exc
    _expect(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        code,
        "captured_at must be timezone-aware",
    )
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, init=False)
class VerifiedPostgrestIdentity:
    """Opaque capability produced only after manifest and HTTP-receipt checks."""

    project_ref: str
    visual_assets_registry: str
    manifest_sha256: str
    principal_sha256: str
    api_key_sha256: str
    function_definition_sha256_lf: str
    identity_captured_at: str

    def __init__(
        self,
        *,
        project_ref: str,
        visual_assets_registry: str,
        manifest_sha256: str,
        principal_sha256: str,
        api_key_sha256: str,
        function_definition_sha256_lf: str,
        identity_captured_at: str,
        _proof: object,
    ) -> None:
        if _proof is not _CAPABILITY_PROOF:
            raise TypeError("use verify_and_bind_identity_receipt")
        object.__setattr__(self, "project_ref", project_ref)
        object.__setattr__(self, "visual_assets_registry", visual_assets_registry)
        object.__setattr__(self, "manifest_sha256", manifest_sha256)
        object.__setattr__(self, "principal_sha256", principal_sha256)
        object.__setattr__(self, "api_key_sha256", api_key_sha256)
        object.__setattr__(
            self,
            "function_definition_sha256_lf",
            function_definition_sha256_lf,
        )
        object.__setattr__(self, "identity_captured_at", identity_captured_at)


def verify_and_bind_identity_receipt(
    *,
    manifest_contract: Mapping[str, Any],
    manifest_capture: Mapping[str, Any],
    identity_http_receipt: Mapping[str, Any],
    p1_jwt: str,
    supabase_key: str,
) -> VerifiedPostgrestIdentity:
    """Bind the role probe to the exact P1 JWT and low-privilege API key.

    ``identity_http_receipt`` is the safe receipt emitted by the operator that
    performed the identity RPC.  ``principal_sha256`` proves which in-memory
    credentials were used without persisting either credential or its headers.
    """

    _expect(
        isinstance(p1_jwt, str) and bool(p1_jwt),
        "HOLD_P1_JWT_INVALID",
        "credential is missing",
    )
    _live_manifest.verify_manifest_capture(manifest_contract, manifest_capture)

    _expect(
        isinstance(identity_http_receipt, Mapping),
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "receipt is not an object",
    )
    _exact_keys(
        identity_http_receipt,
        {
            "schema",
            "project_ref",
            "manifest_sha256",
            "captured_at",
            "method",
            "path",
            "status",
            "redirect_count",
            "request_id",
            "body_sha256",
            "payload_sha256",
            "principal_sha256",
            "api_key_sha256",
            "payload",
        },
        code="HOLD_P1_IDENTITY_RECEIPT_INVALID",
        path="identity_http_receipt",
    )

    semantic = manifest_capture.get("manifest")
    _expect(
        isinstance(semantic, Mapping),
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "verified manifest payload is missing",
    )
    project_ref = semantic.get("project_ref")
    visual = semantic.get("visual_assets_registry")
    manifest_sha256 = manifest_capture.get("manifest_sha256")
    postgrest = semantic.get("postgrest")
    identity_probe = postgrest.get("identity_probe") if isinstance(postgrest, Mapping) else None
    _expect(
        isinstance(identity_probe, Mapping),
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "verified manifest identity probe is missing",
    )

    payload = identity_http_receipt["payload"]
    _expect(
        isinstance(payload, Mapping),
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "payload is not an object",
    )
    _exact_keys(
        payload,
        {"current_user", "transaction_read_only", "statement_timeout"},
        code="HOLD_P1_IDENTITY_RECEIPT_INVALID",
        path="identity_http_receipt.payload",
    )
    expected_payload = {
        "current_user": identity_probe.get("current_user"),
        "transaction_read_only": identity_probe.get("transaction_read_only"),
        "statement_timeout": identity_probe.get("statement_timeout"),
    }
    payload_sha256 = _sha256_bytes(_canonical_json_bytes(dict(payload)))
    principal_sha256 = _sha256_bytes(p1_jwt.encode("utf-8"))
    _validate_supabase_api_key(
        supabase_key,
        project_ref=str(project_ref),
        p1_jwt=p1_jwt,
    )
    api_key_sha256 = _sha256_bytes(supabase_key.encode("utf-8"))
    function_sha256 = identity_probe.get("function_definition_sha256_lf")

    _expect(
        identity_http_receipt["schema"] == IDENTITY_RECEIPT_SCHEMA,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "schema",
    )
    _expect(
        _PROJECT_REF_RE.fullmatch(str(project_ref)) is not None
        and identity_http_receipt["project_ref"] == project_ref,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "project_ref",
    )
    _expect(
        visual in {"on", "off"},
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "visual_assets_registry",
    )
    _expect(
        _SHA256_RE.fullmatch(str(manifest_sha256)) is not None
        and identity_http_receipt["manifest_sha256"] == manifest_sha256,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "manifest binding",
    )
    _expect(
        identity_http_receipt["method"] == "GET"
        and identity_http_receipt["path"] == IDENTITY_PATH
        and identity_http_receipt["status"] == 200
        and identity_http_receipt["redirect_count"] == 0,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "identity HTTP boundary",
    )
    _expect(
        identity_http_receipt["request_id"] is None
        or (
            isinstance(identity_http_receipt["request_id"], str)
            and 0 < len(identity_http_receipt["request_id"]) <= 256
            and identity_http_receipt["request_id"].isprintable()
        ),
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "request_id",
    )
    _expect(
        _SHA256_RE.fullmatch(str(identity_http_receipt["body_sha256"])) is not None,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "body_sha256",
    )
    _expect(
        identity_http_receipt["payload_sha256"] == payload_sha256,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "payload hash",
    )
    _expect(
        identity_http_receipt["principal_sha256"] == principal_sha256,
        "HOLD_P1_IDENTITY_PRINCIPAL_DRIFT",
        "credential fingerprint differs from identity probe",
    )
    _expect(
        identity_http_receipt["api_key_sha256"] == api_key_sha256,
        "HOLD_P1_IDENTITY_API_KEY_DRIFT",
        "API key fingerprint differs from identity probe",
    )
    _expect(
        dict(payload) == expected_payload
        and expected_payload
        == {
            "current_user": P1_ROLE,
            "transaction_read_only": "on",
            "statement_timeout": "30s",
        },
        "HOLD_P1_IDENTITY_DRIFT",
        "identity payload differs from verified manifest",
    )
    _expect(
        _SHA256_RE.fullmatch(str(function_sha256)) is not None,
        "HOLD_P1_IDENTITY_DRIFT",
        "identity function hash",
    )

    identity_time = _utc_timestamp(
        identity_http_receipt["captured_at"],
        code="HOLD_P1_IDENTITY_RECEIPT_INVALID",
    )
    manifest_time = _utc_timestamp(
        manifest_capture.get("captured_at"),
        code="HOLD_P1_IDENTITY_RECEIPT_INVALID",
    )
    _expect(
        identity_time <= manifest_time
        and (manifest_time - identity_time).total_seconds() <= 300,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "identity probe is not contemporaneous with manifest capture",
    )

    return VerifiedPostgrestIdentity(
        project_ref=str(project_ref),
        visual_assets_registry=str(visual),
        manifest_sha256=str(manifest_sha256),
        principal_sha256=principal_sha256,
        api_key_sha256=api_key_sha256,
        function_definition_sha256_lf=str(function_sha256),
        identity_captured_at=identity_time.isoformat().replace("+00:00", "Z"),
        _proof=_CAPABILITY_PROOF,
    )


def _decode_segment(
    segment: str, *, code: str = "HOLD_P1_JWT_INVALID"
) -> Mapping[str, Any]:
    _expect(bool(segment), code, "empty JWT segment")
    try:
        raw = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PostgrestGuardHold(code, "malformed JWT") from exc
    _expect(
        isinstance(value, Mapping),
        code,
        "JWT segment is not an object",
    )
    return value


def _validate_jwt_claims(
    p1_jwt: str,
    *,
    project_ref: str,
    principal_sha256: str,
    now_epoch: float,
) -> None:
    parts = p1_jwt.split(".") if isinstance(p1_jwt, str) else []
    _expect(
        len(parts) == 3 and all(parts),
        "HOLD_P1_JWT_INVALID",
        "JWT must have three signed segments",
    )
    header = _decode_segment(parts[0])
    claims = _decode_segment(parts[1])
    _expect(
        header.get("alg") in {"HS256", "RS256", "ES256"}
        and header.get("typ", "JWT") == "JWT",
        "HOLD_P1_JWT_INVALID",
        "JWT header",
    )
    role = claims.get("role")
    _expect(
        role == P1_ROLE and role not in _FORBIDDEN_ROLES,
        "HOLD_P1_JWT_ROLE_INVALID",
        "JWT role is not p1_readonly",
    )
    expected_issuer = f"https://{project_ref}.supabase.co/auth/v1"
    _expect(
        claims.get("iss") == expected_issuer,
        "HOLD_P1_JWT_PROJECT_INVALID",
        "JWT issuer does not match the canonical project",
    )
    if "ref" in claims:
        _expect(
            claims["ref"] == project_ref,
            "HOLD_P1_JWT_PROJECT_INVALID",
            "JWT project ref differs",
        )
    audience = claims.get("aud")
    audience_ok = audience == EXPECTED_AUDIENCE or audience == [EXPECTED_AUDIENCE]
    _expect(
        audience_ok,
        "HOLD_P1_JWT_AUDIENCE_INVALID",
        "JWT audience",
    )
    expires = claims.get("exp")
    _expect(
        isinstance(expires, (int, float))
        and not isinstance(expires, bool)
        and float(expires) > now_epoch,
        "HOLD_P1_JWT_EXPIRED",
        "JWT is expired or has no numeric exp",
    )
    not_before = claims.get("nbf")
    if not_before is not None:
        _expect(
            isinstance(not_before, (int, float))
            and not isinstance(not_before, bool)
            and float(not_before) <= now_epoch,
            "HOLD_P1_JWT_NOT_YET_VALID",
            "JWT nbf is in the future",
        )
    _expect(
        _sha256_bytes(p1_jwt.encode("utf-8")) == principal_sha256,
        "HOLD_P1_IDENTITY_PRINCIPAL_DRIFT",
        "credential fingerprint differs from verified identity",
    )


def _canonical_supabase_url(project_ref: str, supplied: str) -> str:
    _expect(
        _PROJECT_REF_RE.fullmatch(project_ref) is not None,
        "HOLD_P1_SUPABASE_PROJECT_INVALID",
        "project_ref",
    )
    expected = f"https://{project_ref}.supabase.co"
    _expect(
        supplied == expected,
        "HOLD_P1_SUPABASE_URL_INVALID",
        "URL must be the canonical project origin",
    )
    return expected


def _validate_supabase_api_key(
    supabase_key: str,
    *,
    project_ref: str,
    p1_jwt: str,
) -> None:
    """Accept only a distinct publishable key or legacy ``anon`` JWT."""

    _expect(
        isinstance(supabase_key, str)
        and bool(supabase_key)
        and supabase_key == supabase_key.strip()
        and supabase_key != p1_jwt,
        "HOLD_P1_SUPABASE_API_KEY_INVALID",
        "SUPABASE_KEY must be a distinct non-empty credential",
    )
    if _PUBLISHABLE_KEY_RE.fullmatch(supabase_key) is not None:
        return
    parts = supabase_key.split(".")
    _expect(
        len(parts) == 3 and all(parts),
        "HOLD_P1_SUPABASE_API_KEY_INVALID",
        "SUPABASE_KEY is neither publishable nor a legacy anon JWT",
    )
    claims = _decode_segment(
        parts[1], code="HOLD_P1_SUPABASE_API_KEY_INVALID"
    )
    _expect(
        claims.get("role") == "anon"
        and ("ref" not in claims or claims.get("ref") == project_ref),
        "HOLD_P1_SUPABASE_API_KEY_INVALID",
        "legacy SUPABASE_KEY is not the project's anon key",
    )


def _header_pairs(headers: Any) -> list[tuple[str, str]]:
    _expect(headers is not None, "HOLD_P1_POSTGREST_AUTH_INVALID", "headers missing")
    if hasattr(headers, "multi_items"):
        raw_items = list(headers.multi_items())
    elif isinstance(headers, Mapping):
        raw_items = list(headers.items())
    elif isinstance(headers, Sequence) and not isinstance(headers, (str, bytes, bytearray)):
        raw_items = list(headers)
    else:
        _hold("HOLD_P1_POSTGREST_AUTH_INVALID", "headers shape")
    pairs: list[tuple[str, str]] = []
    for item in raw_items:
        _expect(
            isinstance(item, Sequence)
            and not isinstance(item, (str, bytes, bytearray))
            and len(item) == 2,
            "HOLD_P1_POSTGREST_AUTH_INVALID",
            "header entry shape",
        )
        key, value = item
        try:
            if isinstance(key, bytes):
                key = key.decode("ascii", errors="strict")
            if isinstance(value, bytes):
                value = value.decode("ascii", errors="strict")
        except UnicodeDecodeError:
            _hold("HOLD_P1_POSTGREST_AUTH_INVALID", "non-ASCII header entry")
        _expect(
            isinstance(key, str) and isinstance(value, str),
            "HOLD_P1_POSTGREST_AUTH_INVALID",
            "header entry type",
        )
        pairs.append((key.lower(), value))
    return pairs


def _bind_auth_headers(
    headers: Any, p1_jwt: str, supabase_key: str
) -> list[tuple[str, str]]:
    pairs = _header_pairs(headers)
    api_values = [value for key, value in pairs if key == "apikey"]
    authorization_values = [value for key, value in pairs if key == "authorization"]
    _expect(
        api_values in ([p1_jwt], [supabase_key])
        and authorization_values == [f"Bearer {p1_jwt}"]
        and all(
            p1_jwt not in value and supabase_key not in value
            for key, value in pairs
            if key not in {"apikey", "authorization"}
        ),
        "HOLD_P1_POSTGREST_AUTH_INVALID",
        "Authorization/apikey credential binding",
    )
    bound = [
        (key, supabase_key if key == "apikey" else value)
        for key, value in pairs
    ]
    _expect(
        [value for key, value in bound if key == "apikey"] == [supabase_key]
        and [value for key, value in bound if key == "authorization"]
        == [f"Bearer {p1_jwt}"],
        "HOLD_P1_POSTGREST_AUTH_INVALID",
        "transport credential binding",
    )
    return bound


def _safe_request_id(headers: Any) -> str | None:
    if headers is None:
        return None
    for name in ("x-request-id", "request-id", "sb-request-id"):
        try:
            value = headers.get(name)
        except AttributeError:
            value = None
        if value is not None:
            text = str(value)
            return text if 0 < len(text) <= 256 and text.isprintable() else None
    return None


def _response_bytes(response: Any) -> bytes:
    try:
        value = response.content
    except (AttributeError, RuntimeError):
        value = str(getattr(response, "text", "")).encode("utf-8")
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    return str(value).encode("utf-8")


class _GuardedClient:
    def __init__(self, guard: "P1PostgrestGuard", *args: Any, **kwargs: Any) -> None:
        self._guard = guard
        forbidden = {
            "auth",
            "headers",
            "cookies",
            "base_url",
            "proxy",
            "proxies",
            "mounts",
            "transport",
        }
        present = sorted(key for key in forbidden if kwargs.get(key) not in (None, "", {}, ()))
        _expect(
            not present,
            "HOLD_P1_POSTGREST_CLIENT_CONFIG_INVALID",
            f"forbidden client options={present}",
        )
        _expect(
            kwargs.get("follow_redirects", False) is False,
            "HOLD_P1_POSTGREST_REDIRECT_BLOCKED",
            "follow_redirects",
        )
        _expect(
            kwargs.get("trust_env", False) is False,
            "HOLD_P1_POSTGREST_CLIENT_CONFIG_INVALID",
            "trust_env",
        )
        _expect(
            kwargs.get("verify", True) is not False,
            "HOLD_P1_POSTGREST_CLIENT_CONFIG_INVALID",
            "TLS verification",
        )
        kwargs["follow_redirects"] = False
        kwargs["trust_env"] = False
        self._client = guard._client_factory(*args, **kwargs)
        self._entered_client: Any = None

    def __enter__(self) -> "_GuardedClient":
        entered = self._client.__enter__() if hasattr(self._client, "__enter__") else self._client
        self._entered_client = entered
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> Any:
        if hasattr(self._client, "__exit__"):
            return self._client.__exit__(exc_type, exc, traceback)
        close = getattr(self._client, "close", None)
        if callable(close):
            close()
        return None

    @property
    def _transport_client(self) -> Any:
        return self._entered_client if self._entered_client is not None else self._client

    def request(self, method: str, url: Any, **kwargs: Any) -> Any:
        return self._guard._request(self._transport_client, method, url, kwargs)

    def get(self, url: Any, **kwargs: Any) -> Any:
        return self.request("GET", url, **kwargs)

    def post(self, url: Any, **kwargs: Any) -> Any:
        return self.request("POST", url, **kwargs)

    def head(self, url: Any, **kwargs: Any) -> Any:
        return self.request("HEAD", url, **kwargs)

    def put(self, url: Any, **kwargs: Any) -> Any:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: Any, **kwargs: Any) -> Any:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: Any, **kwargs: Any) -> Any:
        return self.request("DELETE", url, **kwargs)

    def options(self, url: Any, **kwargs: Any) -> Any:
        return self.request("OPTIONS", url, **kwargs)


class _ScopedHttpxProxy:
    """The only httpx surface made visible to the two patched product modules."""

    def __init__(self, guard: "P1PostgrestGuard") -> None:
        self._guard = guard

    def Client(self, *args: Any, **kwargs: Any) -> _GuardedClient:  # noqa: N802
        _expect(
            self._guard.active,
            "HOLD_P1_POSTGREST_GUARD_INACTIVE",
            "client created outside guard",
        )
        return _GuardedClient(self._guard, *args, **kwargs)


class P1PostgrestGuard:
    """Patch only product PostgREST globals for one non-reentrant P1 window."""

    def __init__(
        self,
        *,
        supabase_url: str,
        p1_jwt: str,
        supabase_key: str,
        project_ref: str,
        visual_assets_registry: str,
        verified_identity: VerifiedPostgrestIdentity,
        client_factory: Callable[..., Any] = _real_httpx.Client,
        now_epoch: Callable[[], float] = time.time,
    ) -> None:
        _expect(
            isinstance(verified_identity, VerifiedPostgrestIdentity),
            "HOLD_P1_IDENTITY_UNVERIFIED",
            "verified identity capability required",
        )
        self._supabase_url = _canonical_supabase_url(project_ref, supabase_url)
        _expect(
            visual_assets_registry in {"on", "off"}
            and verified_identity.project_ref == project_ref
            and verified_identity.visual_assets_registry == visual_assets_registry,
            "HOLD_P1_IDENTITY_DRIFT",
            "guard configuration differs from verified manifest",
        )
        _expect(
            callable(client_factory) and callable(now_epoch),
            "HOLD_P1_POSTGREST_CLIENT_CONFIG_INVALID",
            "client_factory/clock",
        )
        self._jwt = p1_jwt
        self._supabase_key = supabase_key
        self._project_ref = project_ref
        self._visual = visual_assets_registry
        self._identity = verified_identity
        self._client_factory = client_factory
        self._now_epoch = now_epoch
        self._active = False
        self._lock_owned = False
        self._saved: list[tuple[ModuleType, str, Any]] = []
        self._receipts: list[dict[str, Any]] = []
        self._receipt_lock = threading.Lock()
        _validate_supabase_api_key(
            self._supabase_key,
            project_ref=self._project_ref,
            p1_jwt=self._jwt,
        )
        self._validate_live_credential()

    @property
    def active(self) -> bool:
        return self._active

    @property
    def receipts(self) -> tuple[dict[str, Any], ...]:
        with self._receipt_lock:
            return tuple(dict(receipt) for receipt in self._receipts)

    def _validate_live_credential(self) -> None:
        _validate_jwt_claims(
            self._jwt,
            project_ref=self._project_ref,
            principal_sha256=self._identity.principal_sha256,
            now_epoch=float(self._now_epoch()),
        )
        _expect(
            _sha256_bytes(self._supabase_key.encode("utf-8"))
            == self._identity.api_key_sha256,
            "HOLD_P1_IDENTITY_API_KEY_DRIFT",
            "API key fingerprint differs from verified identity",
        )

    def __enter__(self) -> "P1PostgrestGuard":
        _expect(
            not self._active,
            "HOLD_P1_POSTGREST_GUARD_REENTRANT",
            "guard instance already active",
        )
        acquired = _PATCH_LOCK.acquire(blocking=False)
        _expect(
            acquired,
            "HOLD_P1_POSTGREST_GUARD_REENTRANT",
            "another product PostgREST guard is active",
        )
        self._lock_owned = True
        try:
            self._validate_live_credential()
            from src.rag import retriever, visual_assets

            proxy = _ScopedHttpxProxy(self)
            patches = (
                (retriever, "httpx", proxy),
                (retriever, "SUPABASE_URL", self._supabase_url),
                (retriever, "SUPABASE_SERVICE_KEY", self._jwt),
                (visual_assets, "httpx", proxy),
                (visual_assets, "SUPABASE_URL", self._supabase_url),
                (visual_assets, "SUPABASE_SERVICE_KEY", self._jwt),
            )
            for module, name, replacement in patches:
                self._saved.append((module, name, getattr(module, name)))
                setattr(module, name, replacement)
            self._active = True
            return self
        except BaseException:
            self._restore()
            raise

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self._restore()

    def _restore(self) -> None:
        self._active = False
        for module, name, original in reversed(self._saved):
            setattr(module, name, original)
        self._saved.clear()
        if self._lock_owned:
            self._lock_owned = False
            _PATCH_LOCK.release()

    def _allowed_path(self, method: str, path: str) -> bool:
        if method == "GET":
            allowed = set(_ALLOWED_GET_PATHS_BASE)
            if self._visual == "on":
                allowed.add(_VISUAL_PATH)
            return path in allowed
        if method == "POST":
            return path in _ALLOWED_POST_PATHS
        return False

    def _validate_url(self, method: str, url: Any) -> str:
        try:
            parsed = urlsplit(str(url))
            port = parsed.port
        except (TypeError, ValueError) as exc:
            del exc
            raise PostgrestGuardHold(
                "HOLD_P1_POSTGREST_URL_BLOCKED", "malformed URL"
            ) from None
        _expect(
            parsed.scheme == "https"
            and parsed.hostname == f"{self._project_ref}.supabase.co"
            and port is None
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment,
            "HOLD_P1_POSTGREST_URL_BLOCKED",
            "request origin is not the canonical Supabase project",
        )
        _expect(
            self._allowed_path(method, parsed.path),
            "HOLD_P1_POSTGREST_SURFACE_BLOCKED",
            f"method={method}; path is outside the exact P1 allowlist",
        )
        return parsed.path

    def _record_response(self, *, method: str, path: str, response: Any) -> None:
        status = getattr(response, "status_code", None)
        _expect(
            isinstance(status, int) and not isinstance(status, bool),
            "HOLD_P1_POSTGREST_RESPONSE_INVALID",
            "response status missing",
        )
        receipt = {
            "schema": REQUEST_RECEIPT_SCHEMA,
            "ordinal": 0,
            "method": method,
            "path": path,
            "status": status,
            "request_id": _safe_request_id(getattr(response, "headers", None)),
            "body_sha256": _sha256_bytes(_response_bytes(response)),
        }
        with self._receipt_lock:
            receipt["ordinal"] = len(self._receipts) + 1
            self._receipts.append(receipt)

    def _request(
        self,
        transport_client: Any,
        method: str,
        url: Any,
        kwargs: Mapping[str, Any],
    ) -> Any:
        _expect(
            self._active,
            "HOLD_P1_POSTGREST_GUARD_INACTIVE",
            "request outside guard",
        )
        self._validate_live_credential()
        normalized_method = str(method).upper()
        path = self._validate_url(normalized_method, url)
        request_kwargs = dict(kwargs)
        _expect(
            request_kwargs.get("follow_redirects", False) is False,
            "HOLD_P1_POSTGREST_REDIRECT_BLOCKED",
            "follow_redirects",
        )
        request_kwargs.pop("follow_redirects", None)
        request_kwargs["headers"] = _bind_auth_headers(
            request_kwargs.get("headers"), self._jwt, self._supabase_key
        )

        try:
            response = transport_client.request(
                normalized_method,
                str(url),
                **request_kwargs,
            )
        except Exception:
            raise PostgrestGuardHold(
                "HOLD_P1_POSTGREST_TRANSPORT_FAILED",
                f"method/path={normalized_method} {path}",
            ) from None
        self._record_response(method=normalized_method, path=path, response=response)
        history = getattr(response, "history", ()) or ()
        status = response.status_code
        _expect(
            not history and not (300 <= status < 400),
            "HOLD_P1_POSTGREST_REDIRECT_BLOCKED",
            f"method/path={normalized_method} {path}",
        )
        _expect(
            200 <= status < 300,
            "HOLD_P1_POSTGREST_STATUS_INVALID",
            f"method/path/status={normalized_method} {path} {status}",
        )
        return response


__all__ = [
    "EXPECTED_AUDIENCE",
    "IDENTITY_PATH",
    "IDENTITY_RECEIPT_SCHEMA",
    "P1PostgrestGuard",
    "P1_ROLE",
    "PostgrestGuardHold",
    "REQUEST_RECEIPT_SCHEMA",
    "VerifiedPostgrestIdentity",
    "verify_and_bind_identity_receipt",
]
