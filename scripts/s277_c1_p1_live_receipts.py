"""Live Supabase evidence and manifest materialization for the S277 C1 P1 gate.

This module is the I/O boundary around :mod:`s277_c1_p1_live_manifest`.
Every remote operation is a GET and every PostgreSQL capture runs inside an
explicit read-only transaction over the Supavisor session endpoint (port 5432).

Secrets are accepted only as runtime inputs.  Returned values and materialized
JSON contain safe projections and one-way, domain-separated principal hashes;
they never contain request headers, credentials, connection strings, response
queries, or the Management API ``jwt_secret`` field.
"""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

try:  # pragma: no cover - the package import is used by tests and ``python -m``.
    from scripts import s277_c1_p1_live_manifest as live
    from scripts import s277_c1_p1_postgrest_guard as postgrest_guard
except ImportError:  # pragma: no cover - direct ``python scripts/...py`` support.
    import s277_c1_p1_live_manifest as live  # type: ignore[no-redef]
    import s277_c1_p1_postgrest_guard as postgrest_guard  # type: ignore[no-redef]


HTTP_EVIDENCE_SCHEMA = "s277_c1_p1_supabase_http_evidence_v1"
HTTP_RECEIPT_SCHEMA = "s277_c1_p1_http_receipts_v1"
MANAGEMENT_ORIGIN = "https://api.supabase.com"
OPENAPI_PROFILE = "public"
HTTP_TIMEOUT_SECONDS = 15.0
MAX_HTTP_BODY_BYTES = 24 * 1024 * 1024

_PROJECT_REF_RE = re.compile(r"^[a-z0-9]{20}$")
_SESSION_POOLER_HOST_RE = re.compile(
    r"^aws-[0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*\.pooler\.supabase\.com$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:/+-]{1,256}$")
_VERSION_RE = re.compile(
    r"^(?:postgrest[/ -]?)?v?(?P<version>[0-9]+(?:\.[0-9]+){1,3}"
    r"(?:[-+][0-9A-Za-z.-]+)?)$",
    re.IGNORECASE,
)
_HTTP_METHODS = frozenset(
    {"get", "head", "post", "put", "patch", "delete", "options", "trace"}
)
_REQUEST_ID_HEADERS = (
    "x-request-id",
    "sb-request-id",
    "x-kong-request-id",
    "cf-ray",
)


def _hold(code: str, detail: str) -> None:
    raise live.ManifestHold(code, detail)


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


def _principal_sha256(kind: str, credential: str) -> str:
    return _sha256_bytes(f"s277:{kind}:v1\0{credential}".encode("utf-8"))


def _guard_principal_sha256(p1_jwt: str) -> str:
    """Use the guard's deliberately unprefixed credential fingerprint."""

    return _sha256_bytes(p1_jwt.encode("utf-8"))


def _guard_api_key_sha256(supabase_key: str) -> str:
    """Use the guard's deliberately unprefixed API-key fingerprint."""

    return _sha256_bytes(supabase_key.encode("utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp(value: str | None) -> str:
    if value is None:
        return _utc_now()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise live.ManifestHold(
            "HOLD_MANIFEST_TIME_INVALID", "capture time is not ISO-8601"
        ) from exc
    _expect(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        "HOLD_MANIFEST_TIME_INVALID",
        "capture time must be timezone-aware",
    )
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_project_ref(project_ref: str) -> str:
    _expect(
        _PROJECT_REF_RE.fullmatch(project_ref) is not None,
        "HOLD_SUPABASE_PROJECT_INVALID",
        "project ref must be exactly 20 lowercase alphanumeric characters",
    )
    return project_ref


def project_ref_from_supabase_url(
    supabase_url: str, *, expected_project_ref: str | None = None
) -> str:
    """Return the project ref only for the canonical hosted Supabase origin."""

    try:
        parsed = urlparse.urlsplit(supabase_url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise live.ManifestHold(
            "HOLD_SUPABASE_URL_INVALID", "SUPABASE_URL is not a valid URL"
        ) from exc
    _expect(
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
        and parsed.path in ("", "/")
        and not parsed.query
        and not parsed.fragment,
        "HOLD_SUPABASE_URL_INVALID",
        "requires the canonical HTTPS project origin without path or query",
    )
    hostname = (parsed.hostname or "").lower()
    suffix = ".supabase.co"
    _expect(
        hostname.endswith(suffix),
        "HOLD_SUPABASE_URL_INVALID",
        "requires <project-ref>.supabase.co",
    )
    project_ref = _validate_project_ref(hostname[: -len(suffix)])
    _expect(
        hostname == f"{project_ref}{suffix}",
        "HOLD_SUPABASE_URL_INVALID",
        "custom domains and subdomains are not accepted",
    )
    if expected_project_ref is not None:
        _expect(
            project_ref == _validate_project_ref(expected_project_ref),
            "HOLD_SUPABASE_PROJECT_MISMATCH",
            "SUPABASE_URL does not identify the expected project",
        )
    return project_ref


def _decode_jwt_payload(jwt: str) -> Mapping[str, Any]:
    parts = jwt.split(".")
    _expect(
        len(parts) == 3 and all(parts),
        "HOLD_P1_JWT_INVALID",
        "P1_SUPABASE_JWT is not a compact JWT",
    )
    try:
        payload_bytes = base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise live.ManifestHold(
            "HOLD_P1_JWT_INVALID", "P1_SUPABASE_JWT payload is invalid"
        ) from exc
    _expect(
        isinstance(payload, Mapping) and payload.get("role") == "p1_readonly",
        "HOLD_P1_JWT_ROLE_INVALID",
        "JWT role must be p1_readonly",
    )
    return payload


class _NoRedirectHandler(urlrequest.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _default_opener() -> Any:
    return urlrequest.build_opener(_NoRedirectHandler())


def _header_map(response: Any) -> dict[str, str]:
    headers = getattr(response, "headers", {}) or {}
    try:
        items = headers.items()
    except AttributeError:
        items = ()
    return {str(key).lower(): str(value).strip() for key, value in items}


def _request_id(headers: Mapping[str, str]) -> str:
    for name in _REQUEST_ID_HEADERS:
        value = headers.get(name, "")
        if value:
            _expect(
                _REQUEST_ID_RE.fullmatch(value) is not None,
                "HOLD_HTTP_REQUEST_ID_INVALID",
                f"invalid {name} response header",
            )
            return value
    _hold("HOLD_HTTP_REQUEST_ID_MISSING", "response has no allowlisted request id")


def _response_status(response: Any) -> int:
    value = getattr(response, "status", None)
    if value is None:
        value = response.getcode()
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise live.ManifestHold("HOLD_HTTP_STATUS_INVALID", "non-integer status") from exc


def _read_limited(response: Any) -> bytes:
    body = response.read(MAX_HTTP_BODY_BYTES + 1)
    _expect(
        isinstance(body, bytes),
        "HOLD_HTTP_BODY_INVALID",
        "response body must be bytes",
    )
    _expect(
        len(body) <= MAX_HTTP_BODY_BYTES,
        "HOLD_HTTP_BODY_TOO_LARGE",
        "response exceeded the fixed byte limit",
    )
    return body


def _parse_json(body: bytes, *, endpoint: str) -> Any:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise live.ManifestHold(
            "HOLD_HTTP_JSON_INVALID", f"{endpoint} did not return valid UTF-8 JSON"
        ) from exc


def _invoke_opener(opener: Any, request: urlrequest.Request) -> Any:
    target = opener or _default_opener()
    call: Callable[..., Any]
    call = target.open if hasattr(target, "open") else target
    try:
        return call(request, timeout=HTTP_TIMEOUT_SECONDS)
    except urlerror.HTTPError as exc:
        if 300 <= int(exc.code) < 400:
            _hold("HOLD_HTTP_REDIRECT_FORBIDDEN", "redirect response rejected")
        _hold("HOLD_HTTP_STATUS_INVALID", f"HTTP status {int(exc.code)}")
    except (TimeoutError, socket.timeout):
        _hold("HOLD_HTTP_TIMEOUT", "fixed request timeout reached")
    except urlerror.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            _hold("HOLD_HTTP_TIMEOUT", "fixed request timeout reached")
        _hold("HOLD_HTTP_UNAVAILABLE", "remote request failed")
    except live.ManifestHold:
        raise
    except Exception as exc:
        # Exception text can include a Request repr with Authorization headers.
        # Preserve only the type, never the message.
        raise live.ManifestHold(
            "HOLD_HTTP_UNAVAILABLE", f"request failed ({type(exc).__name__})"
        ) from None


def _safe_get_json(
    *,
    url: str,
    headers: Mapping[str, str],
    credential_kind: str,
    credential: str,
    expected_origin: str,
    expected_path: str,
    api_key: str | None = None,
    expected_query: Mapping[str, Sequence[str]] | None = None,
    endpoint: str,
    opener: Any,
) -> tuple[Any, bytes, dict[str, str], dict[str, Any]]:
    parsed = urlparse.urlsplit(url)
    try:
        parsed_query = urlparse.parse_qs(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError as exc:
        raise live.ManifestHold(
            "HOLD_HTTP_TARGET_INVALID", f"{endpoint} query is malformed"
        ) from exc
    wanted_query = {
        str(key): [str(item) for item in values]
        for key, values in (expected_query or {}).items()
    }
    origin = f"{parsed.scheme}://{parsed.netloc}"
    _expect(
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and origin == expected_origin
        and parsed.path == expected_path
        and parsed_query == wanted_query
        and not parsed.fragment,
        "HOLD_HTTP_TARGET_INVALID",
        f"{endpoint} target/query contract differs",
    )
    request = urlrequest.Request(url, headers=dict(headers), method="GET")
    response = _invoke_opener(opener, request)
    try:
        status = _response_status(response)
        final_url = str(response.geturl())
        if 300 <= status < 400 or final_url != url:
            _hold("HOLD_HTTP_REDIRECT_FORBIDDEN", f"{endpoint} redirected")
        _expect(
            status == 200,
            "HOLD_HTTP_STATUS_INVALID",
            f"{endpoint} returned HTTP {status}",
        )
        response_headers = _header_map(response)
        content_type = response_headers.get("content-type", "").lower()
        _expect(
            "json" in content_type,
            "HOLD_HTTP_CONTENT_TYPE_INVALID",
            f"{endpoint} did not return JSON",
        )
        request_id = _request_id(response_headers)
        body = _read_limited(response)
        payload = _parse_json(body, endpoint=endpoint)
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    receipt = {
        "method": "GET",
        "origin": origin,
        "path": parsed.path,
        "status": 200,
        "request_id": request_id,
        "body_sha256": _sha256_bytes(body),
        "principal_sha256": _principal_sha256(credential_kind, credential),
        "api_key_sha256": (
            _principal_sha256("supabase-project-api-key", api_key)
            if api_key is not None
            else None
        ),
    }
    return payload, body, response_headers, receipt


def _management_projection(payload: Any) -> dict[str, Any]:
    """Whitelist safe Management fields; all secret/unknown fields disappear."""

    _expect(
        isinstance(payload, Mapping),
        "HOLD_POSTGREST_CONFIG_UNVERIFIED",
        "Management API payload must be an object",
    )
    raw_schemas = payload.get("db_schema")
    if isinstance(raw_schemas, str):
        schemas = sorted({item.strip() for item in raw_schemas.split(",") if item.strip()})
    elif isinstance(raw_schemas, Sequence) and not isinstance(raw_schemas, (bytes, bytearray)):
        schemas = sorted({str(item).strip() for item in raw_schemas if str(item).strip()})
    else:
        schemas = []
    max_rows = payload.get("max_rows")
    _expect(
        "public" in schemas,
        "HOLD_POSTGREST_CONFIG_UNVERIFIED",
        "Management API did not confirm the public schema",
    )
    _expect(
        isinstance(max_rows, int)
        and not isinstance(max_rows, bool)
        and max_rows > 0,
        "HOLD_POSTGREST_CONFIG_UNVERIFIED",
        "Management API max_rows must be a positive integer",
    )
    return {"exposed_schemas": schemas, "max_rows": max_rows}


def _normalize_version(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _VERSION_RE.fullmatch(value.strip())
    return match.group("version") if match else None


def _postgrest_version(openapi: Mapping[str, Any], headers: Mapping[str, str]) -> str:
    candidates: list[str] = []
    explicit = _normalize_version(headers.get("x-postgrest-version"))
    if explicit:
        candidates.append(explicit)
    server = _normalize_version(headers.get("server"))
    if server and "postgrest" in headers.get("server", "").lower():
        candidates.append(server)
    info = openapi.get("info")
    if isinstance(info, Mapping):
        spec_version = _normalize_version(info.get("version"))
        if spec_version:
            candidates.append(spec_version)
    _expect(
        bool(candidates),
        "HOLD_POSTGREST_VERSION_UNVERIFIED",
        "no parseable PostgREST version in response header or OpenAPI info",
    )
    _expect(
        len(set(candidates)) == 1,
        "HOLD_POSTGREST_VERSION_DRIFT",
        "header and OpenAPI versions disagree",
    )
    return candidates[0]


def _validate_openapi_origin(openapi: Mapping[str, Any], *, project_ref: str) -> None:
    expected_host = f"{project_ref}.supabase.co"
    if "host" in openapi:
        raw_host = str(openapi["host"]).lower()
        _expect(
            raw_host in {expected_host, f"{expected_host}:443"},
            "HOLD_POSTGREST_OPENAPI_PROJECT_DRIFT",
            "OpenAPI host does not match SUPABASE_URL",
        )
    if "schemes" in openapi:
        _expect(
            openapi["schemes"] == ["https"],
            "HOLD_POSTGREST_OPENAPI_PROJECT_DRIFT",
            "OpenAPI schemes must be exactly HTTPS",
        )
    if "basePath" in openapi:
        _expect(
            openapi["basePath"] == "/",
            "HOLD_POSTGREST_OPENAPI_PROJECT_DRIFT",
            "Management OpenAPI basePath must be exactly project root",
        )
    servers = openapi.get("servers")
    if servers is not None:
        _expect(
            isinstance(servers, list) and bool(servers),
            "HOLD_POSTGREST_OPENAPI_PROJECT_DRIFT",
            "OpenAPI servers must be a non-empty list",
        )
        for item in servers:
            _expect(
                isinstance(item, Mapping) and isinstance(item.get("url"), str),
                "HOLD_POSTGREST_OPENAPI_PROJECT_DRIFT",
                "invalid OpenAPI server",
            )
            parsed = urlparse.urlsplit(str(item["url"]))
            _expect(
                parsed.scheme == "https"
                and parsed.hostname == expected_host
                and parsed.port in (None, 443)
                and parsed.path in {"/rest/v1", "/rest/v1/"}
                and not parsed.query
                and not parsed.fragment,
                "HOLD_POSTGREST_OPENAPI_PROJECT_DRIFT",
                "OpenAPI server does not match the exact project REST origin",
            )


def _required_rpc_methods(openapi: Mapping[str, Any]) -> dict[str, list[str]]:
    paths = openapi.get("paths")
    _expect(
        isinstance(paths, Mapping),
        "HOLD_POSTGREST_OPENAPI_INVALID",
        "OpenAPI paths missing",
    )
    result: dict[str, list[str]] = {}
    for path, expected in live.REQUIRED_RPC_METHODS.items():
        item = paths.get(path)
        _expect(
            isinstance(item, Mapping),
            "HOLD_POSTGREST_RPC_SURFACE_DRIFT",
            f"required RPC path missing: {path}",
        )
        methods = sorted(
            str(key).upper() for key in item if str(key).lower() in _HTTP_METHODS
        )
        wanted = sorted(str(method).upper() for method in expected)
        _expect(
            methods == wanted,
            "HOLD_POSTGREST_RPC_SURFACE_DRIFT",
            f"{path} methods differ",
        )
        result[path] = methods
    return result


def _identity_payload(payload: Any) -> dict[str, str]:
    _expect(
        isinstance(payload, Mapping),
        "HOLD_POSTGREST_IDENTITY_UNVERIFIED",
        "identity RPC payload must be an object",
    )
    wanted = {"current_user", "transaction_read_only", "statement_timeout"}
    _expect(
        set(payload) == wanted,
        "HOLD_POSTGREST_IDENTITY_UNVERIFIED",
        "identity RPC keys differ",
    )
    safe = {key: str(payload[key]) for key in sorted(wanted)}
    _expect(
        safe["current_user"] == "p1_readonly"
        and safe["transaction_read_only"] == "on"
        and safe["statement_timeout"] == "30s",
        "HOLD_POSTGREST_IDENTITY_UNVERIFIED",
        "identity RPC did not prove the P1 role, timeout and GET transaction mode",
    )
    return safe


def capture_postgrest_evidence(
    *,
    supabase_url: str,
    access_token: str,
    p1_jwt: str,
    supabase_key: str,
    expected_identity_function_sha256: str,
    expected_project_ref: str | None = None,
    opener: Any = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Capture a safe Management/OpenAPI/identity snapshot with HTTP receipts."""

    _expect(bool(access_token), "HOLD_SUPABASE_PAT_MISSING", "SUPABASE_ACCESS_TOKEN missing")
    _expect(bool(p1_jwt), "HOLD_P1_JWT_MISSING", "P1_SUPABASE_JWT missing")
    _decode_jwt_payload(p1_jwt)
    _expect(
        _SHA256_RE.fullmatch(expected_identity_function_sha256) is not None,
        "HOLD_IDENTITY_FUNCTION_HASH_INVALID",
        "expected identity function SHA-256 must be lowercase hex",
    )
    project_ref = project_ref_from_supabase_url(
        supabase_url, expected_project_ref=expected_project_ref
    )
    postgrest_guard._validate_supabase_api_key(  # noqa: SLF001
        supabase_key,
        project_ref=project_ref,
        p1_jwt=p1_jwt,
    )
    project_origin = f"https://{project_ref}.supabase.co"

    management_url = f"{MANAGEMENT_ORIGIN}/v1/projects/{project_ref}/postgrest"
    management, _management_body, _management_headers, management_receipt = _safe_get_json(
        url=management_url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "technical-bot-s277-c1-p1/1",
        },
        credential_kind="supabase-management-pat",
        credential=access_token,
        expected_origin=MANAGEMENT_ORIGIN,
        expected_path=f"/v1/projects/{project_ref}/postgrest",
        endpoint="management-postgrest",
        opener=opener,
    )
    # This allowlist projection is created immediately.  In particular,
    # jwt_secret and any future secret/unknown Management fields are discarded
    # before validation errors or persisted hashes can observe them.
    management_safe = _management_projection(management)
    management_receipt["body_sha256"] = _sha256_bytes(
        _canonical_json_bytes(management_safe)
    )

    data_headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {p1_jwt}",
        "apikey": supabase_key,
        "User-Agent": "technical-bot-s277-c1-p1/1",
    }
    # Supabase removed low-privilege access to the Data API root in 2026.
    # Its official read-only replacement is this PAT-authenticated Management
    # endpoint.  The exact query contract prevents silently capturing a schema
    # other than the preregistered public surface.
    openapi_url = (
        f"{MANAGEMENT_ORIGIN}/v1/projects/{project_ref}/database/openapi"
        f"?schema={OPENAPI_PROFILE}"
    )
    openapi, openapi_body, openapi_headers, openapi_receipt = _safe_get_json(
        url=openapi_url,
        headers={
            "Accept": "application/openapi+json, application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "technical-bot-s277-c1-p1/1",
        },
        credential_kind="supabase-management-pat",
        credential=access_token,
        expected_origin=MANAGEMENT_ORIGIN,
        expected_path=f"/v1/projects/{project_ref}/database/openapi",
        expected_query={"schema": [OPENAPI_PROFILE]},
        endpoint="management-postgrest-openapi",
        opener=opener,
    )
    _expect(
        isinstance(openapi, Mapping),
        "HOLD_POSTGREST_OPENAPI_INVALID",
        "OpenAPI root must be an object",
    )
    _validate_openapi_origin(openapi, project_ref=project_ref)
    rpc_methods = _required_rpc_methods(openapi)
    version = _postgrest_version(openapi, openapi_headers)

    identity_url = f"{project_origin}/rest/v1/rpc/p1_runtime_identity_v1"
    identity, _identity_body, _identity_headers, identity_receipt = _safe_get_json(
        url=identity_url,
        headers={**data_headers, "Accept": "application/json"},
        credential_kind="supabase-p1-jwt",
        credential=p1_jwt,
        expected_origin=project_origin,
        expected_path="/rest/v1/rpc/p1_runtime_identity_v1",
        api_key=supabase_key,
        endpoint="postgrest-identity",
        opener=opener,
    )
    identity_safe = _identity_payload(identity)

    snapshot = {
        "schema": live.POSTGREST_SCHEMA,
        "project_ref": project_ref,
        "source": "supabase_management_api_and_openapi",
        "openapi_status": 200,
        "openapi_profile": OPENAPI_PROFILE,
        "openapi_sha256": _sha256_bytes(openapi_body),
        "rpc_methods": rpc_methods,
        "identity_probe": {
            "path": "/rpc/p1_runtime_identity_v1",
            "method": "GET",
            "status": 200,
            **identity_safe,
            "transaction_mode_scope": "identity_get_only_not_rpc_post",
            "function_definition_sha256_lf": expected_identity_function_sha256,
        },
        "runtime_config": {
            "data_api_enabled": True,
            "exposed_schemas": management_safe["exposed_schemas"],
            "max_rows": management_safe["max_rows"],
            "postgrest_version": version,
        },
    }
    evidence = {
        "schema": HTTP_EVIDENCE_SCHEMA,
        "project_ref": project_ref,
        "captured_at": _timestamp(captured_at),
        "postgrest_snapshot": snapshot,
        "http_receipts": {
            "schema": HTTP_RECEIPT_SCHEMA,
            "management_postgrest": management_receipt,
            "postgrest_openapi": openapi_receipt,
            "postgrest_identity": identity_receipt,
        },
    }
    serialized = _canonical_json_bytes(evidence)
    for forbidden in (access_token, p1_jwt, supabase_key):
        _expect(
            forbidden.encode("utf-8") not in serialized,
            "HOLD_SECRET_SERIALIZATION",
            "credential reached the safe evidence projection",
        )
    return evidence


def build_identity_guard_receipt(
    *,
    evidence: Mapping[str, Any],
    manifest_capture: Mapping[str, Any],
    p1_jwt: str,
    supabase_key: str,
) -> dict[str, Any]:
    """Bind the identity GET to a manifest using the guard's exact contract."""

    _expect(
        isinstance(p1_jwt, str) and bool(p1_jwt),
        "HOLD_P1_JWT_INVALID",
        "P1_SUPABASE_JWT missing",
    )
    project_ref = evidence.get("project_ref")
    captured_at = evidence.get("captured_at")
    snapshot = evidence.get("postgrest_snapshot")
    receipts = evidence.get("http_receipts")
    semantic = manifest_capture.get("manifest")
    manifest_sha256 = manifest_capture.get("manifest_sha256")
    _expect(
        isinstance(snapshot, Mapping)
        and isinstance(receipts, Mapping)
        and isinstance(semantic, Mapping),
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "evidence or manifest shape",
    )
    snapshot_identity = snapshot.get("identity_probe")
    manifest_postgrest = semantic.get("postgrest")
    manifest_identity = (
        manifest_postgrest.get("identity_probe")
        if isinstance(manifest_postgrest, Mapping)
        else None
    )
    http_receipt = receipts.get("postgrest_identity")
    _expect(
        isinstance(snapshot_identity, Mapping)
        and isinstance(manifest_identity, Mapping)
        and isinstance(http_receipt, Mapping),
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "identity evidence shape",
    )
    payload = {
        "current_user": snapshot_identity.get("current_user"),
        "transaction_read_only": snapshot_identity.get("transaction_read_only"),
        "statement_timeout": snapshot_identity.get("statement_timeout"),
    }
    manifest_payload = {
        "current_user": manifest_identity.get("current_user"),
        "transaction_read_only": manifest_identity.get("transaction_read_only"),
        "statement_timeout": manifest_identity.get("statement_timeout"),
    }
    _expect(
        payload == manifest_payload
        == {
            "current_user": "p1_readonly",
            "transaction_read_only": "on",
            "statement_timeout": "30s",
        }
        and snapshot_identity.get("function_definition_sha256_lf")
        == manifest_identity.get("function_definition_sha256_lf"),
        "HOLD_P1_IDENTITY_DRIFT",
        "HTTP identity evidence differs from the manifest",
    )
    _expect(
        project_ref == semantic.get("project_ref")
        and _PROJECT_REF_RE.fullmatch(str(project_ref)) is not None,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "project_ref",
    )
    _expect(
        isinstance(manifest_sha256, str)
        and _SHA256_RE.fullmatch(manifest_sha256) is not None,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "manifest_sha256",
    )
    _expect(
        http_receipt.get("method") == "GET"
        and http_receipt.get("path") == postgrest_guard.IDENTITY_PATH
        and http_receipt.get("status") == 200
        and isinstance(http_receipt.get("body_sha256"), str)
        and _SHA256_RE.fullmatch(str(http_receipt.get("body_sha256"))) is not None,
        "HOLD_P1_IDENTITY_RECEIPT_INVALID",
        "identity HTTP boundary",
    )
    normalized_time = _timestamp(str(captured_at))
    return {
        "schema": postgrest_guard.IDENTITY_RECEIPT_SCHEMA,
        "project_ref": project_ref,
        "manifest_sha256": manifest_sha256,
        "captured_at": normalized_time,
        "method": "GET",
        "path": postgrest_guard.IDENTITY_PATH,
        "status": 200,
        "redirect_count": 0,
        "request_id": http_receipt.get("request_id"),
        "body_sha256": http_receipt["body_sha256"],
        "payload_sha256": _sha256_bytes(_canonical_json_bytes(payload)),
        "principal_sha256": _guard_principal_sha256(p1_jwt),
        "api_key_sha256": _guard_api_key_sha256(supabase_key),
        "payload": payload,
    }


def _validated_database_url(database_url: str, *, project_ref: str) -> dict[str, Any]:
    try:
        parsed = urlparse.urlsplit(database_url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise live.ManifestHold(
            "HOLD_DATABASE_URL_INVALID", "DATABASE_URL is not a valid URL"
        ) from exc
    username = urlparse.unquote(parsed.username or "")
    host = (parsed.hostname or "").lower()
    query = urlparse.parse_qs(parsed.query, keep_blank_values=True)
    query_ok = not query or query == {"sslmode": ["require"]}
    _expect(
        parsed.scheme in {"postgres", "postgresql"}
        and parsed.password is not None
        and bool(parsed.password)
        and port == 5432
        and _SESSION_POOLER_HOST_RE.fullmatch(host) is not None
        and username == f"postgres.{project_ref}"
        and parsed.path == "/postgres"
        and query_ok
        and not parsed.fragment,
        "HOLD_FENCE_PERSISTENT_SESSION_REQUIRED",
        "DATABASE_URL must be the exact Supavisor session endpoint on port 5432",
    )
    return {"host": host, "port": 5432, "user": username}


def _default_connector(database_url: str, **kwargs: Any) -> Any:
    try:
        import psycopg2
    except ImportError as exc:  # pragma: no cover - installed in the runtime image.
        raise live.ManifestHold(
            "HOLD_DATABASE_DRIVER_MISSING", "psycopg2 is required"
        ) from exc
    try:
        return psycopg2.connect(database_url, **kwargs)
    except Exception as exc:
        # libpq errors can echo DSNs, usernames or hosts.  Do not include them.
        raise live.ManifestHold(
            "HOLD_DATABASE_CONNECT_FAILED", f"connection failed ({type(exc).__name__})"
        ) from None


@contextmanager
def open_readonly_database(
    database_url: str,
    *,
    project_ref: str,
    connector: Callable[..., Any] | None = None,
) -> Iterator[Any]:
    """Open TLS Supavisor session mode and start an explicit read-only tx."""

    expected = _validated_database_url(database_url, project_ref=project_ref)
    connect = connector or _default_connector
    try:
        connection = connect(
            database_url,
            sslmode="require",
            connect_timeout=10,
            application_name="s277-c1-p1-live-receipts",
        )
    except live.ManifestHold:
        raise
    except Exception as exc:
        raise live.ManifestHold(
            "HOLD_DATABASE_CONNECT_FAILED", f"connection failed ({type(exc).__name__})"
        ) from None
    try:
        info = getattr(connection, "info", None)
        actual = {
            "host": str(getattr(info, "host", "") or "").lower(),
            "port": int(getattr(info, "port", 0) or 0),
            "user": str(getattr(info, "user", "") or ""),
        }
        _expect(
            actual == expected,
            "HOLD_DATABASE_CONNECTION_IDENTITY_DRIFT",
            "libpq connection identity differs from DATABASE_URL",
        )
        _expect(
            getattr(info, "ssl_in_use", None) is True,
            "HOLD_DATABASE_TLS_REQUIRED",
            "libpq did not confirm TLS",
        )
        try:
            connection.autocommit = True
            cursor = connection.cursor()
            try:
                cursor.execute("BEGIN")
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET LOCAL ROLE p1_readonly")
            finally:
                cursor.close()
        except Exception as exc:
            raise live.ManifestHold(
                "HOLD_DATABASE_READ_ONLY_SETUP_FAILED",
                f"read-only transaction setup failed ({type(exc).__name__})",
            ) from None
        yield connection
    finally:
        try:
            connection.rollback()
        except Exception:
            pass
        try:
            connection.close()
        except Exception:
            pass


def capture_live_phase(
    *,
    phase: str,
    visual_assets_registry: str,
    supabase_url: str,
    access_token: str,
    p1_jwt: str,
    supabase_key: str,
    database_url: str,
    expected_identity_function_sha256: str,
    expected_project_ref: str | None = None,
    opener: Any = None,
    connector: Callable[..., Any] | None = None,
    captured_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Capture one pre/watch/post manifest plus its separate safe HTTP evidence."""

    _expect(phase in {"pre", "watch", "post"}, "HOLD_MANIFEST_PHASE_INVALID", phase)
    # Bind the HTTP and catalog receipts to one timestamp instead of allowing
    # two independent ``now()`` calls to create an ambiguous evidence pair.
    capture_time = _timestamp(captured_at)
    evidence = capture_postgrest_evidence(
        supabase_url=supabase_url,
        access_token=access_token,
        p1_jwt=p1_jwt,
        supabase_key=supabase_key,
        expected_identity_function_sha256=expected_identity_function_sha256,
        expected_project_ref=expected_project_ref,
        opener=opener,
        captured_at=capture_time,
    )
    project_ref = str(evidence["project_ref"])
    with open_readonly_database(
        database_url, project_ref=project_ref, connector=connector
    ) as connection:
        capture = live.capture_live_manifest(
            connection,
            project_ref=project_ref,
            visual_assets_registry=visual_assets_registry,
            phase=phase,
            postgrest_snapshot=evidence["postgrest_snapshot"],
            captured_at=capture_time,
        )
    evidence["identity_guard_receipt"] = build_identity_guard_receipt(
        evidence=evidence,
        manifest_capture=capture,
        p1_jwt=p1_jwt,
        supabase_key=supabase_key,
    )
    return capture, evidence


def _json_document(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_exclusive(
    path: str | Path, value: Any, *, forbidden_values: Sequence[str] = ()
) -> None:
    target = Path(path)
    body = _json_document(value)
    for forbidden in forbidden_values:
        if forbidden:
            _expect(
                forbidden.encode("utf-8") not in body,
                "HOLD_SECRET_SERIALIZATION",
                "secret reached a materialized artifact",
            )
    try:
        with target.open("xb") as handle:
            handle.write(body)
    except FileExistsError as exc:
        raise live.ManifestHold(
            "HOLD_RECEIPT_PATH_EXISTS", f"refusing to overwrite {target.name}"
        ) from exc


def _forbidden_runtime_values(
    *, access_token: str, p1_jwt: str, supabase_key: str, database_url: str
) -> tuple[str, ...]:
    try:
        database_password = urlparse.unquote(
            urlparse.urlsplit(database_url).password or ""
        )
    except (TypeError, ValueError):
        database_password = ""
    return access_token, p1_jwt, supabase_key, database_url, database_password


def _preflight_output_paths(paths: Sequence[str | Path]) -> None:
    resolved = [Path(path).resolve() for path in paths]
    _expect(
        len(resolved) == len(set(resolved)),
        "HOLD_RECEIPT_PATH_INVALID",
        "output paths must be distinct",
    )
    for path in resolved:
        _expect(
            not path.exists(),
            "HOLD_RECEIPT_PATH_EXISTS",
            f"refusing to overwrite {path.name}",
        )
        _expect(
            path.parent.is_dir(),
            "HOLD_RECEIPT_PATH_INVALID",
            f"parent directory missing for {path.name}",
        )


def materialize_pre_contract(
    *,
    pre_path: str | Path,
    contract_path: str | Path,
    http_evidence_path: str | Path,
    visual_assets_registry: str,
    supabase_url: str,
    access_token: str,
    p1_jwt: str,
    supabase_key: str,
    database_url: str,
    expected_identity_function_sha256: str,
    expected_project_ref: str | None = None,
    opener: Any = None,
    connector: Callable[..., Any] | None = None,
    captured_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Capture a safe pre image, seal its contract, and create artifacts once."""

    paths = (pre_path, contract_path, http_evidence_path)
    _preflight_output_paths(paths)
    pre, evidence = capture_live_phase(
        phase="pre",
        visual_assets_registry=visual_assets_registry,
        supabase_url=supabase_url,
        access_token=access_token,
        p1_jwt=p1_jwt,
        supabase_key=supabase_key,
        database_url=database_url,
        expected_identity_function_sha256=expected_identity_function_sha256,
        expected_project_ref=expected_project_ref,
        opener=opener,
        connector=connector,
        captured_at=captured_at,
    )
    contract = live.build_manifest_contract(pre)
    forbidden = _forbidden_runtime_values(
        access_token=access_token,
        p1_jwt=p1_jwt,
        supabase_key=supabase_key,
        database_url=database_url,
    )
    _write_exclusive(pre_path, pre, forbidden_values=forbidden)
    _write_exclusive(contract_path, contract, forbidden_values=forbidden)
    _write_exclusive(http_evidence_path, evidence, forbidden_values=forbidden)
    return pre, contract, evidence


def _identity_hash_from_contract(contract: Mapping[str, Any]) -> str:
    manifest = contract.get("manifest")
    _expect(
        isinstance(manifest, Mapping),
        "HOLD_EXPECTED_MANIFEST_INVALID",
        "contract manifest missing",
    )
    functions = manifest.get("functions")
    _expect(
        isinstance(functions, list),
        "HOLD_EXPECTED_MANIFEST_INVALID",
        "contract function list missing",
    )
    candidates = [
        row.get("definition_sha256_lf")
        for row in functions
        if isinstance(row, Mapping) and row.get("name") == live.IDENTITY_FUNCTION
    ]
    _expect(
        len(candidates) == 1
        and isinstance(candidates[0], str)
        and _SHA256_RE.fullmatch(candidates[0]) is not None,
        "HOLD_EXPECTED_MANIFEST_INVALID",
        "contract identity function hash missing",
    )
    return str(candidates[0])


def materialize_verified_phase(
    *,
    phase: str,
    contract: Mapping[str, Any],
    capture_path: str | Path,
    http_evidence_path: str | Path,
    visual_assets_registry: str,
    supabase_url: str,
    access_token: str,
    p1_jwt: str,
    supabase_key: str,
    database_url: str,
    expected_project_ref: str | None = None,
    opener: Any = None,
    connector: Callable[..., Any] | None = None,
    captured_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Capture a watch/post image, verify it, then create its artifacts once."""

    _expect(phase in {"watch", "post"}, "HOLD_MANIFEST_PHASE_INVALID", phase)
    _preflight_output_paths((capture_path, http_evidence_path))
    capture, evidence = capture_live_phase(
        phase=phase,
        visual_assets_registry=visual_assets_registry,
        supabase_url=supabase_url,
        access_token=access_token,
        p1_jwt=p1_jwt,
        supabase_key=supabase_key,
        database_url=database_url,
        expected_identity_function_sha256=_identity_hash_from_contract(contract),
        expected_project_ref=expected_project_ref,
        opener=opener,
        connector=connector,
        captured_at=captured_at,
    )
    live.verify_manifest_capture(contract, capture)
    forbidden = _forbidden_runtime_values(
        access_token=access_token,
        p1_jwt=p1_jwt,
        supabase_key=supabase_key,
        database_url=database_url,
    )
    _write_exclusive(capture_path, capture, forbidden_values=forbidden)
    _write_exclusive(http_evidence_path, evidence, forbidden_values=forbidden)
    return capture, evidence


def _load_json(path: str | Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise live.ManifestHold(
            "HOLD_RECEIPT_FILE_INVALID", f"cannot read {Path(path).name}"
        ) from exc


def verify_materialized_window(
    *,
    contract_path: str | Path,
    pre_path: str | Path,
    watch_paths: Sequence[str | Path],
    post_path: str | Path,
) -> None:
    contract = _load_json(contract_path)
    captures = [
        _load_json(pre_path),
        *(_load_json(path) for path in watch_paths),
        _load_json(post_path),
    ]
    live.verify_manifest_window(contract, captures)


def _required_environment() -> dict[str, str]:
    names = (
        "SUPABASE_ACCESS_TOKEN",
        "SUPABASE_URL",
        "P1_SUPABASE_JWT",
        "SUPABASE_KEY",
        "DATABASE_URL",
    )
    result: dict[str, str] = {}
    for name in names:
        value = os.environ.get(name, "")
        _expect(bool(value), "HOLD_RUNTIME_ENV_MISSING", f"{name} missing")
        result[name] = value
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture and verify S277 P1 live Supabase manifests"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pre = subparsers.add_parser("pre")
    pre.add_argument("--pre-out", required=True)
    pre.add_argument("--contract-out", required=True)
    pre.add_argument("--http-evidence-out", required=True)
    pre.add_argument("--identity-function-sha256")
    pre.add_argument("--project-ref")
    pre.add_argument("--visual-assets-registry", choices=("on", "off"), required=True)

    phase = subparsers.add_parser("capture")
    phase.add_argument("--phase", choices=("watch", "post"), required=True)
    phase.add_argument("--contract", required=True)
    phase.add_argument("--capture-out", required=True)
    phase.add_argument("--http-evidence-out", required=True)
    phase.add_argument("--project-ref")
    phase.add_argument("--visual-assets-registry", choices=("on", "off"), required=True)

    verify = subparsers.add_parser("verify-window")
    verify.add_argument("--contract", required=True)
    verify.add_argument("--pre", required=True)
    verify.add_argument("--watch", action="append", default=[])
    verify.add_argument("--post", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify-window":
            verify_materialized_window(
                contract_path=args.contract,
                pre_path=args.pre,
                watch_paths=args.watch,
                post_path=args.post,
            )
            print(json.dumps({"status": "PASS", "window": "verified"}, sort_keys=True))
            return 0

        env = _required_environment()
        if args.command == "pre":
            identity_hash = (
                args.identity_function_sha256
                or os.environ.get("P1_IDENTITY_FUNCTION_SHA256", "")
            )
            _expect(
                bool(identity_hash),
                "HOLD_IDENTITY_FUNCTION_HASH_INVALID",
                "--identity-function-sha256 or P1_IDENTITY_FUNCTION_SHA256 required",
            )
            materialize_pre_contract(
                pre_path=args.pre_out,
                contract_path=args.contract_out,
                http_evidence_path=args.http_evidence_out,
                visual_assets_registry=args.visual_assets_registry,
                supabase_url=env["SUPABASE_URL"],
                access_token=env["SUPABASE_ACCESS_TOKEN"],
                p1_jwt=env["P1_SUPABASE_JWT"],
                supabase_key=env["SUPABASE_KEY"],
                database_url=env["DATABASE_URL"],
                expected_identity_function_sha256=identity_hash,
                expected_project_ref=args.project_ref,
            )
            print(json.dumps({"status": "PASS", "phase": "pre"}, sort_keys=True))
            return 0

        contract = _load_json(args.contract)
        materialize_verified_phase(
            phase=args.phase,
            contract=contract,
            capture_path=args.capture_out,
            http_evidence_path=args.http_evidence_out,
            visual_assets_registry=args.visual_assets_registry,
            supabase_url=env["SUPABASE_URL"],
            access_token=env["SUPABASE_ACCESS_TOKEN"],
            p1_jwt=env["P1_SUPABASE_JWT"],
            supabase_key=env["SUPABASE_KEY"],
            database_url=env["DATABASE_URL"],
            expected_project_ref=args.project_ref,
        )
        print(json.dumps({"status": "PASS", "phase": args.phase}, sort_keys=True))
        return 0
    except live.ManifestHold as exc:
        print(json.dumps({"status": "HOLD", "code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
