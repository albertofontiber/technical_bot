"""Read-only capture and fail-closed verification for the S277 P1 live manifest.

This module deliberately has no network client and no credential loading.  The
caller owns the persistent PostgreSQL connection (direct IPv6 or the approved
IPv4 Supavisor session endpoint) and the independently captured PostgREST receipt.
The only database statements here are catalog reads.

The P1 runner can use this module through three small hooks:

* :func:`capture_live_manifest` before, during and after the protected window;
* :func:`build_manifest_contract` once an operator-reviewed pre-capture exists;
* :func:`verify_manifest_window` before accepting the window.

No function in this file acquires locks, changes a role, writes a receipt or calls
PostgREST.  Those remain separate operator responsibilities.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence


MANIFEST_SCHEMA = "s277_c1_p1_live_manifest_v1"
CONTRACT_SCHEMA = "s277_c1_p1_live_manifest_contract_v1"
POSTGREST_SCHEMA = "s277_c1_p1_postgrest_snapshot_v1"

BASE_REQUIRED_RELATIONS = (
    "public.chunks_v2",
    "public.chunks_v2_enunciados",
    "public.chunks_v2_hyq",
    "public.documents",
)
VISUAL_ASSETS_RELATION = "public.document_visual_assets"


def required_relations(visual_assets_registry: str) -> tuple[str, ...]:
    _expect(
        visual_assets_registry in {"on", "off"},
        "HOLD_MANIFEST_VISUAL_CONFIG_INVALID",
        str(visual_assets_registry),
    )
    if visual_assets_registry == "on":
        return (*BASE_REQUIRED_RELATIONS, VISUAL_ASSETS_RELATION)
    return BASE_REQUIRED_RELATIONS

REQUIRED_FUNCTIONS: Mapping[str, tuple[str, ...]] = {
    "public.match_chunks_v2": (
        "public.vector",
        "pg_catalog.float8",
        "pg_catalog.int4",
        "pg_catalog.text",
        "pg_catalog.text",
        "pg_catalog.text",
        "pg_catalog.bool",
    ),
    "public.search_chunks_text_v2": (
        "pg_catalog.text",
        "pg_catalog.text",
        "pg_catalog.text",
        "pg_catalog.text",
        "pg_catalog.int4",
    ),
    "public.match_chunks_v2_enunciados": (
        "public.vector",
        "pg_catalog.float8",
        "pg_catalog.int4",
        "pg_catalog.text",
        "pg_catalog.text",
    ),
    "public.match_hyq": (
        "public.vector",
        "pg_catalog.float8",
        "pg_catalog.int4",
    ),
    "public.corpus_fingerprint_v1": (),
}

RETRIEVAL_FUNCTIONS = frozenset(REQUIRED_FUNCTIONS) - {
    "public.corpus_fingerprint_v1"
}
IDENTITY_FUNCTION = "public.p1_runtime_identity_v1"

# These are the operator-observed pg_get_functiondef hashes at the S277 design
# boundary.  They are not silently learned from the same capture they protect.
S277_EXPECTED_FUNCTION_SHA256: Mapping[str, str] = {
    "public.match_chunks_v2":
        "e6c940f2a7f606e0fd7199e1ac192abc09046a686d7c6562470a584858d1f55e",
    "public.search_chunks_text_v2":
        "0b3cd49a415c5f7192be05b268c23a29c81ba458a2621a75a3e70945a38e2f5f",
    "public.match_chunks_v2_enunciados":
        "ed986867c931c8d3a361a5f904449d995d4acee70c815922f31f25fc997cbae7",
    "public.match_hyq":
        "d7744e62bd1f09498bbc5702d69510dc83708e77ea113e34545cc806e4353d8b",
    "public.corpus_fingerprint_v1":
        "1f280e0852158b63501aad2843a7e946ab9fac5a4c64a17851d6d63ed0e8ebca",
}

REQUIRED_RPC_METHODS: Mapping[str, tuple[str, ...]] = {
    "/rpc/match_chunks_v2": ("POST",),
    "/rpc/search_chunks_text_v2": ("POST",),
    "/rpc/match_chunks_v2_enunciados": ("POST",),
    "/rpc/match_hyq": ("POST",),
}

_PHASES = frozenset({"pre", "watch", "post"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PROJECT_REF_RE = re.compile(r"^[a-z0-9]{20}$")
_SUPAVISOR_SESSION_HOST = "aws-1-eu-north-1.pooler.supabase.com"
_SECRET_KEY_RE = re.compile(
    r"(?i)(secret|password|credential|authorization|api[_-]?key|jwt|bearer|token)"
)


class ManifestHold(RuntimeError):
    """A stable, machine-readable P1 stop condition."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _hold(code: str, detail: str) -> None:
    raise ManifestHold(code, detail)


def _expect(condition: bool, code: str, detail: str) -> None:
    if not condition:
        _hold(code, detail)


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def sha256_text_lf(text: str) -> str:
    return hashlib.sha256(_lf(text).encode("utf-8")).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _timestamp(value: str | datetime) -> str:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ManifestHold("HOLD_MANIFEST_TIME_INVALID", str(value)) from exc
    _expect(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        "HOLD_MANIFEST_TIME_INVALID",
        "timestamp must be timezone-aware",
    )
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_value(value: Any) -> Any:
    """Normalize driver JSON/text values to plain deterministic Python values."""

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _reject_secret_keys(value: Any, path: str = "postgrest") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            _expect(
                _SECRET_KEY_RE.search(key_text) is None,
                "HOLD_MANIFEST_SECRET_MATERIAL",
                f"forbidden key at {path}.{key_text}",
            )
            _reject_secret_keys(item, f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_secret_keys(item, f"{path}[{index}]")


def _exact_keys(
    value: Mapping[str, Any], expected: Iterable[str], *, code: str, path: str
) -> None:
    actual = set(value)
    wanted = set(expected)
    _expect(
        actual == wanted,
        code,
        f"{path} keys drift: missing={sorted(wanted - actual)} "
        f"extra={sorted(actual - wanted)}",
    )


def _normalize_acl(value: Any) -> list[dict[str, Any]]:
    rows = _json_value(value) or []
    _expect(isinstance(rows, list), "HOLD_MANIFEST_SHAPE", "ACL must be a list")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        _expect(isinstance(row, Mapping), "HOLD_MANIFEST_SHAPE", "ACL row")
        item = {
            "grantee": str(row.get("grantee")),
            "grantor": str(row.get("grantor")),
            "privilege": str(row.get("privilege")).upper(),
            "grantable": bool(row.get("grantable")),
        }
        normalized.append(item)
    return sorted(
        normalized,
        key=lambda row: (
            row["grantee"], row["privilege"], row["grantor"], row["grantable"]
        ),
    )


def _normalize_postgrest_snapshot(
    snapshot: Mapping[str, Any], *, project_ref: str
) -> dict[str, Any]:
    _reject_secret_keys(snapshot)
    _exact_keys(
        snapshot,
        {
            "schema",
            "project_ref",
            "source",
            "openapi_status",
            "openapi_profile",
            "openapi_sha256",
            "rpc_methods",
            "identity_probe",
            "runtime_config",
        },
        code="HOLD_POSTGREST_SNAPSHOT_INVALID",
        path="postgrest",
    )
    _expect(
        snapshot["schema"] == POSTGREST_SCHEMA,
        "HOLD_POSTGREST_SNAPSHOT_INVALID",
        "schema",
    )
    _expect(
        snapshot["project_ref"] == project_ref,
        "HOLD_POSTGREST_SNAPSHOT_INVALID",
        "project_ref",
    )
    _expect(
        snapshot["source"] == "supabase_management_api_and_openapi",
        "HOLD_POSTGREST_CONFIG_UNVERIFIED",
        "snapshot must combine Management API and OpenAPI evidence",
    )
    _expect(
        snapshot["openapi_status"] == 200,
        "HOLD_POSTGREST_SNAPSHOT_INVALID",
        "OpenAPI root was not HTTP 200",
    )
    _expect(
        snapshot["openapi_profile"] == "public",
        "HOLD_POSTGREST_SNAPSHOT_INVALID",
        "unexpected OpenAPI profile",
    )
    openapi_sha = str(snapshot["openapi_sha256"])
    _expect(
        _SHA256_RE.fullmatch(openapi_sha) is not None,
        "HOLD_POSTGREST_SNAPSHOT_INVALID",
        "openapi_sha256",
    )

    methods = snapshot["rpc_methods"]
    _expect(
        isinstance(methods, Mapping),
        "HOLD_POSTGREST_SNAPSHOT_INVALID",
        "rpc_methods",
    )
    normalized_methods = {
        str(path): sorted(str(method).upper() for method in value)
        for path, value in methods.items()
    }
    expected_methods = {
        path: sorted(value) for path, value in REQUIRED_RPC_METHODS.items()
    }
    _expect(
        normalized_methods == expected_methods,
        "HOLD_POSTGREST_RPC_SURFACE_DRIFT",
        "required RPC methods differ",
    )

    identity = snapshot["identity_probe"]
    _expect(
        isinstance(identity, Mapping),
        "HOLD_POSTGREST_IDENTITY_UNVERIFIED",
        "identity_probe",
    )
    _exact_keys(
        identity,
        {
            "path", "method", "status", "current_user",
            "transaction_read_only", "statement_timeout",
            "transaction_mode_scope",
            "function_definition_sha256_lf",
        },
        code="HOLD_POSTGREST_IDENTITY_UNVERIFIED",
        path="postgrest.identity_probe",
    )
    _expect(
        identity["path"] == "/rpc/p1_runtime_identity_v1"
        and identity["method"] == "GET"
        and identity["status"] == 200
        and identity["current_user"] == "p1_readonly"
        and identity["transaction_read_only"] == "on"
        and identity["statement_timeout"] == "30s"
        and identity["transaction_mode_scope"]
        == "identity_get_only_not_rpc_post"
        and _SHA256_RE.fullmatch(str(identity["function_definition_sha256_lf"]))
        is not None,
        "HOLD_POSTGREST_IDENTITY_UNVERIFIED",
        "live PostgREST role and identity-GET transaction probe",
    )

    runtime = snapshot["runtime_config"]
    _expect(
        isinstance(runtime, Mapping),
        "HOLD_POSTGREST_CONFIG_UNVERIFIED",
        "runtime_config",
    )
    _exact_keys(
        runtime,
        {
            "data_api_enabled",
            "exposed_schemas",
            "max_rows",
            "postgrest_version",
        },
        code="HOLD_POSTGREST_CONFIG_UNVERIFIED",
        path="postgrest.runtime_config",
    )
    exposed = sorted(str(item) for item in runtime["exposed_schemas"])
    _expect(
        runtime["data_api_enabled"] is True and "public" in exposed,
        "HOLD_POSTGREST_CONFIG_UNVERIFIED",
        "Data API/public schema not confirmed",
    )
    _expect(
        isinstance(runtime["max_rows"], int)
        and not isinstance(runtime["max_rows"], bool)
        and runtime["max_rows"] > 0,
        "HOLD_POSTGREST_CONFIG_UNVERIFIED",
        "max_rows must be a positive integer",
    )
    _expect(
        isinstance(runtime["postgrest_version"], str)
        and bool(runtime["postgrest_version"].strip()),
        "HOLD_POSTGREST_CONFIG_UNVERIFIED",
        "PostgREST version missing",
    )
    return {
        "schema": POSTGREST_SCHEMA,
        "project_ref": project_ref,
        "source": snapshot["source"],
        "openapi_status": 200,
        "openapi_profile": "public",
        "openapi_sha256": openapi_sha,
        "rpc_methods": normalized_methods,
        "identity_probe": dict(identity),
        "runtime_config": {
            "data_api_enabled": True,
            "exposed_schemas": exposed,
            "max_rows": runtime["max_rows"],
            "postgrest_version": runtime["postgrest_version"].strip(),
        },
    }


SESSION_SQL = """/* s277:session */
SELECT
    current_setting('transaction_read_only') AS transaction_read_only,
    current_database() AS database_name,
    current_user AS current_user,
    current_setting('server_version_num') AS server_version_num;
"""

FUNCTIONS_SQL = """/* s277:functions */
SELECT
    n.nspname AS schema_name,
    p.proname AS function_name,
    ARRAY(
        SELECT format('%%I.%%I', tn.nspname, t.typname)
        FROM unnest(p.proargtypes::oid[]) WITH ORDINALITY AS u(type_oid, ordinality)
        JOIN pg_type AS t ON t.oid = u.type_oid
        JOIN pg_namespace AS tn ON tn.oid = t.typnamespace
        ORDER BY u.ordinality
    ) AS arg_types,
    count(*) OVER (PARTITION BY n.nspname, p.proname) AS overload_count,
    pg_get_function_result(p.oid) AS result_type,
    p.provolatile AS volatility,
    p.prosecdef AS security_definer,
    p.proleakproof AS leakproof,
    p.proparallel AS parallel_safety,
    p.prokind AS function_kind,
    l.lanname AS language,
    pg_get_userbyid(p.proowner) AS owner,
    p.proconfig AS function_config,
    pg_get_functiondef(p.oid) AS definition,
    COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'grantee', CASE WHEN x.grantee = 0 THEN 'PUBLIC'
                            ELSE pg_get_userbyid(x.grantee) END,
            'grantor', pg_get_userbyid(x.grantor),
            'privilege', x.privilege_type,
            'grantable', x.is_grantable
        ) ORDER BY
            CASE WHEN x.grantee = 0 THEN 'PUBLIC'
                 ELSE pg_get_userbyid(x.grantee) END,
            x.privilege_type,
            pg_get_userbyid(x.grantor),
            x.is_grantable)
        FROM aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) AS x
    ), '[]'::jsonb) AS acl
FROM pg_proc AS p
JOIN pg_namespace AS n ON n.oid = p.pronamespace
JOIN pg_language AS l ON l.oid = p.prolang
WHERE n.nspname = 'public'
  AND p.proname = ANY(%s)
ORDER BY n.nspname, p.proname, p.oid;
"""

INDEXES_SQL = """/* s277:indexes */
SELECT
    tn.nspname AS table_schema,
    t.relname AS table_name,
    ni.nspname AS index_schema,
    i.relname AS index_name,
    am.amname AS access_method,
    x.indisunique AS is_unique,
    x.indisprimary AS is_primary,
    x.indisvalid AS is_valid,
    x.indisready AS is_ready,
    x.indislive AS is_live,
    x.indnkeyatts AS key_attribute_count,
    x.indnatts AS attribute_count,
    i.reloptions AS reloptions,
    pg_get_expr(x.indpred, x.indrelid, true) AS predicate,
    pg_get_expr(x.indexprs, x.indrelid, true) AS expressions,
    pg_get_indexdef(i.oid) AS definition,
    COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'position', k.ordinality,
            'attribute_number', k.attnum,
            'column_name', a.attname,
            'formatted_type', CASE WHEN a.attnum IS NULL THEN NULL
                                   ELSE format_type(a.atttypid, a.atttypmod) END,
            'type_schema', atn.nspname,
            'type_name', at.typname,
            'opclass_schema', ocn.nspname,
            'opclass_name', oc.opcname,
            'collation_schema', cn.nspname,
            'collation_name', coll.collname,
            'options', k.indoption
        ) ORDER BY k.ordinality)
        FROM unnest(
            x.indkey::smallint[], x.indclass::oid[],
            x.indcollation::oid[], x.indoption::smallint[]
        ) WITH ORDINALITY AS k(attnum, opclass_oid, collation_oid, indoption, ordinality)
        LEFT JOIN pg_attribute AS a
          ON a.attrelid = t.oid AND a.attnum = k.attnum AND k.attnum > 0
        LEFT JOIN pg_type AS at ON at.oid = a.atttypid
        LEFT JOIN pg_namespace AS atn ON atn.oid = at.typnamespace
        JOIN pg_opclass AS oc ON oc.oid = k.opclass_oid
        JOIN pg_namespace AS ocn ON ocn.oid = oc.opcnamespace
        LEFT JOIN pg_collation AS coll
          ON coll.oid = NULLIF(k.collation_oid, 0)
        LEFT JOIN pg_namespace AS cn ON cn.oid = coll.collnamespace
    ), '[]'::jsonb) AS keys
FROM pg_index AS x
JOIN pg_class AS i ON i.oid = x.indexrelid
JOIN pg_namespace AS ni ON ni.oid = i.relnamespace
JOIN pg_class AS t ON t.oid = x.indrelid
JOIN pg_namespace AS tn ON tn.oid = t.relnamespace
JOIN pg_am AS am ON am.oid = i.relam
WHERE tn.nspname = 'public'
  AND t.relname = ANY(%s)
ORDER BY tn.nspname, t.relname, ni.nspname, i.relname;
"""

RELATIONS_SQL = """/* s277:relations */
SELECT
    n.nspname AS schema_name,
    c.relname AS relation_name,
    c.relkind AS relation_kind,
    pg_get_userbyid(c.relowner) AS owner,
    c.relrowsecurity AS row_security,
    c.relforcerowsecurity AS force_row_security,
    c.reloptions AS reloptions,
    COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'grantee', CASE WHEN x.grantee = 0 THEN 'PUBLIC'
                            ELSE pg_get_userbyid(x.grantee) END,
            'grantor', pg_get_userbyid(x.grantor),
            'privilege', x.privilege_type,
            'grantable', x.is_grantable
        ) ORDER BY
            CASE WHEN x.grantee = 0 THEN 'PUBLIC'
                 ELSE pg_get_userbyid(x.grantee) END,
            x.privilege_type,
            pg_get_userbyid(x.grantor),
            x.is_grantable)
        FROM aclexplode(COALESCE(c.relacl, acldefault('r', c.relowner))) AS x
    ), '[]'::jsonb) AS acl,
    COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'name', pol.policyname,
            'permissive', pol.permissive,
            'roles', pol.roles,
            'command', pol.cmd,
            'using', pol.qual,
            'check', pol.with_check
        ) ORDER BY pol.policyname)
        FROM pg_policies AS pol
        WHERE pol.schemaname = n.nspname AND pol.tablename = c.relname
    ), '[]'::jsonb) AS policies
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = ANY(%s)
  AND c.relkind IN ('r', 'p')
ORDER BY n.nspname, c.relname;
"""

ROLE_SQL = """/* s277:role */
SELECT
    r.rolname AS role_name,
    r.rolsuper AS is_superuser,
    r.rolinherit AS inherits,
    r.rolcreaterole AS can_create_role,
    r.rolcreatedb AS can_create_db,
    r.rolcanlogin AS can_login,
    r.rolreplication AS can_replicate,
    r.rolbypassrls AS bypasses_rls,
    COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'member', pg_get_userbyid(m.member),
            'admin_option', m.admin_option,
            'inherit_option', m.inherit_option,
            'set_option', m.set_option
        ) ORDER BY pg_get_userbyid(m.member))
        FROM pg_auth_members AS m
        WHERE m.roleid = r.oid
    ), '[]'::jsonb) AS members,
    COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'role', pg_get_userbyid(m.roleid),
            'admin_option', m.admin_option,
            'inherit_option', m.inherit_option,
            'set_option', m.set_option
        ) ORDER BY pg_get_userbyid(m.roleid))
        FROM pg_auth_members AS m
        WHERE m.member = r.oid
    ), '[]'::jsonb) AS member_of,
    COALESCE((
        SELECT jsonb_agg(cfg.value ORDER BY cfg.value)
        FROM pg_db_role_setting AS s
        CROSS JOIN LATERAL unnest(s.setconfig) AS cfg(value)
        WHERE s.setrole = r.oid AND s.setdatabase = 0
    ), '[]'::jsonb) AS role_settings,
    has_schema_privilege(r.rolname, 'public', 'CREATE') AS schema_create,
    COALESCE((
        SELECT jsonb_agg(
            p.oid::regprocedure::text ORDER BY p.oid::regprocedure::text
        )
        FROM pg_proc AS p
        JOIN pg_namespace AS n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.prosecdef
          AND has_function_privilege(r.rolname, p.oid, 'EXECUTE')
    ), '[]'::jsonb) AS accessible_security_definer_functions
FROM pg_roles AS r
WHERE r.rolname = 'p1_readonly';
"""

SETTINGS_SQL = """/* s277:settings */
WITH wanted(name) AS (
    VALUES
        ('server_version_num'), ('lc_collate'), ('lc_ctype'),
        ('default_text_search_config'), ('hnsw.ef_search'),
        ('hnsw.iterative_scan'), ('hnsw.max_scan_tuples'),
        ('hnsw.scan_mem_multiplier'), ('pgrst.db_schemas'),
        ('pgrst.db_anon_role'), ('pgrst.db_max_rows')
)
SELECT name, current_setting(name, true) AS value
FROM wanted
ORDER BY name;
"""

EXTENSIONS_SQL = """/* s277:extensions */
SELECT e.extname AS name, e.extversion AS version, n.nspname AS schema_name
FROM pg_extension AS e
JOIN pg_namespace AS n ON n.oid = e.extnamespace
WHERE e.extname IN ('vector', 'unaccent', 'pgcrypto')
ORDER BY e.extname;
"""

DB_ROLE_SETTINGS_SQL = """/* s277:db-role-settings */
SELECT
    s.setdatabase,
    CASE WHEN s.setrole = 0 THEN 'ALL' ELSE pg_get_userbyid(s.setrole) END AS role_name,
    cfg.value AS setting
FROM pg_db_role_setting AS s
CROSS JOIN LATERAL unnest(s.setconfig) AS cfg(value)
WHERE cfg.value LIKE 'pgrst.%%'
ORDER BY s.setdatabase, role_name, cfg.value;
"""


def _cursor_rows(connection: Any, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    cursor = connection.cursor()
    try:
        cursor.execute(sql, tuple(params))
        description = cursor.description or ()
        columns = [str(item[0]) for item in description]
        return [
            {column: _json_value(value) for column, value in zip(columns, row)}
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()


def _validated_transport(connection: Any, *, project_ref: str) -> dict[str, Any]:
    info = getattr(connection, "info", None)
    host = str(getattr(info, "host", "") or "").lower()
    port = int(getattr(info, "port", 0) or 0)
    database_user = str(getattr(info, "user", "") or "")
    expected_host = f"db.{project_ref}.supabase.co"
    if host == expected_host and port == 5432:
        return {"mode": "direct", "host": host, "port": port, "tls": True}
    if (
        host == _SUPAVISOR_SESSION_HOST
        and port == 5432
        and database_user == f"postgres.{project_ref}"
    ):
        return {
            "mode": "supavisor_session",
            "host": host,
            "port": port,
            "tls": True,
            "authenticated_project_ref": project_ref,
        }
    _hold(
        "HOLD_FENCE_PERSISTENT_SESSION_REQUIRED",
        f"expected {expected_host}:5432 or {_SUPAVISOR_SESSION_HOST}:5432; "
        f"got {host or '<unknown>'}:{port}",
    )


def _validate_transport_receipt(
    transport: Mapping[str, Any], *, project_ref: str
) -> None:
    direct = {
        "mode": "direct",
        "host": f"db.{project_ref}.supabase.co",
        "port": 5432,
        "tls": True,
    }
    session = {
        "mode": "supavisor_session",
        "host": _SUPAVISOR_SESSION_HOST,
        "port": 5432,
        "tls": True,
        "authenticated_project_ref": project_ref,
    }
    _expect(
        dict(transport) in (direct, session),
        "HOLD_FENCE_PERSISTENT_SESSION_REQUIRED",
        "requires direct or allowlisted Supavisor :5432 session mode",
    )


def _normalize_function_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        definition = _lf(str(row["definition"]))
        arg_types = [str(item) for item in (_json_value(row["arg_types"]) or [])]
        name = f"{row['schema_name']}.{row['function_name']}"
        signature = f"{name}({','.join(arg_types)})"
        result.append(
            {
                "name": name,
                "signature": signature,
                "arg_types": arg_types,
                "overload_count": int(row["overload_count"]),
                "result_type": str(row["result_type"]),
                "volatility": str(row["volatility"]),
                "security_definer": bool(row["security_definer"]),
                "leakproof": bool(row["leakproof"]),
                "parallel_safety": str(row["parallel_safety"]),
                "function_kind": str(row["function_kind"]),
                "language": str(row["language"]),
                "owner": str(row["owner"]),
                "function_config": sorted(str(item) for item in (row.get("function_config") or [])),
                "acl": _normalize_acl(row["acl"]),
                "definition": definition,
                "definition_sha256_lf": sha256_text_lf(definition),
            }
        )
    return sorted(result, key=lambda item: item["signature"])


def _normalize_index_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        definition = _lf(str(row["definition"]))
        keys = _json_value(row["keys"]) or []
        _expect(isinstance(keys, list), "HOLD_MANIFEST_SHAPE", "index keys")
        result.append(
            {
                "relation": f"{row['table_schema']}.{row['table_name']}",
                "name": f"{row['index_schema']}.{row['index_name']}",
                "access_method": str(row["access_method"]),
                "is_unique": bool(row["is_unique"]),
                "is_primary": bool(row["is_primary"]),
                "is_valid": bool(row["is_valid"]),
                "is_ready": bool(row["is_ready"]),
                "is_live": bool(row["is_live"]),
                "key_attribute_count": int(row["key_attribute_count"]),
                "attribute_count": int(row["attribute_count"]),
                "reloptions": sorted(str(item) for item in (row.get("reloptions") or [])),
                "predicate": row.get("predicate"),
                "expressions": row.get("expressions"),
                "keys": keys,
                "definition": definition,
                "definition_sha256_lf": sha256_text_lf(definition),
            }
        )
    return sorted(result, key=lambda item: item["name"])


def _normalize_relation_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        policies = _json_value(row["policies"]) or []
        _expect(isinstance(policies, list), "HOLD_MANIFEST_SHAPE", "policies")
        normalized_policies = []
        for policy in policies:
            normalized_policies.append(
                {
                    "name": str(policy["name"]),
                    "permissive": str(policy["permissive"]),
                    "roles": sorted(str(role) for role in (policy.get("roles") or [])),
                    "command": str(policy["command"]),
                    "using": policy.get("using"),
                    "check": policy.get("check"),
                }
            )
        result.append(
            {
                "name": f"{row['schema_name']}.{row['relation_name']}",
                "relation_kind": str(row["relation_kind"]),
                "owner": str(row["owner"]),
                "row_security": bool(row["row_security"]),
                "force_row_security": bool(row["force_row_security"]),
                "reloptions": sorted(str(item) for item in (row.get("reloptions") or [])),
                "acl": _normalize_acl(row["acl"]),
                "policies": sorted(normalized_policies, key=lambda item: item["name"]),
            }
        )
    return sorted(result, key=lambda item: item["name"])


def _normalize_role_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    _expect(len(rows) <= 1, "HOLD_P1_ROLE_DRIFT", "duplicate p1_readonly role")
    if not rows:
        return None
    row = rows[0]
    members = _json_value(row["members"]) or []
    member_of = _json_value(row["member_of"]) or []
    role_settings = _json_value(row["role_settings"]) or []
    accessible_security_definer = (
        _json_value(row["accessible_security_definer_functions"]) or []
    )
    return {
        "role_name": str(row["role_name"]),
        "is_superuser": bool(row["is_superuser"]),
        "inherits": bool(row["inherits"]),
        "can_create_role": bool(row["can_create_role"]),
        "can_create_db": bool(row["can_create_db"]),
        "can_login": bool(row["can_login"]),
        "can_replicate": bool(row["can_replicate"]),
        "bypasses_rls": bool(row["bypasses_rls"]),
        "members": sorted(members, key=lambda item: str(item.get("member"))),
        "member_of": sorted(member_of, key=lambda item: str(item.get("role"))),
        "role_settings": sorted(str(item) for item in role_settings),
        "schema_create": bool(row["schema_create"]),
        "accessible_security_definer_functions": sorted(
            str(item) for item in accessible_security_definer
        ),
    }


def materialize_live_manifest(
    *,
    project_ref: str,
    visual_assets_registry: str,
    phase: str,
    captured_at: str | datetime,
    transport: Mapping[str, Any],
    session_rows: Sequence[Mapping[str, Any]],
    function_rows: Sequence[Mapping[str, Any]],
    index_rows: Sequence[Mapping[str, Any]],
    relation_rows: Sequence[Mapping[str, Any]],
    role_rows: Sequence[Mapping[str, Any]],
    setting_rows: Sequence[Mapping[str, Any]],
    extension_rows: Sequence[Mapping[str, Any]],
    db_role_setting_rows: Sequence[Mapping[str, Any]],
    postgrest_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a deterministic capture from already-read catalog rows."""

    _expect(
        _PROJECT_REF_RE.fullmatch(project_ref) is not None,
        "HOLD_MANIFEST_PROJECT_INVALID",
        project_ref,
    )
    _expect(phase in _PHASES, "HOLD_MANIFEST_PHASE_INVALID", phase)
    expected_relations = required_relations(visual_assets_registry)
    _expect(len(session_rows) == 1, "HOLD_MANIFEST_SHAPE", "session row")
    session = session_rows[0]
    _expect(
        session.get("transaction_read_only") == "on",
        "HOLD_MANIFEST_CONNECTION_NOT_READ_ONLY",
        "transaction_read_only must be on",
    )
    _expect(
        session.get("current_user") == "p1_readonly",
        "HOLD_P1_RUNTIME_IDENTITY_DRIFT",
        f"current_user={session.get('current_user')}",
    )
    _validate_transport_receipt(transport, project_ref=project_ref)

    functions = _normalize_function_rows(function_rows)
    indexes = _normalize_index_rows(index_rows)
    relations = _normalize_relation_rows(relation_rows)
    role = _normalize_role_rows(role_rows)
    settings = {
        str(row["name"]): None if row.get("value") is None else str(row["value"])
        for row in setting_rows
    }
    extensions = sorted(
        [
            {
                "name": str(row["name"]),
                "version": str(row["version"]),
                "schema": str(row["schema_name"]),
            }
            for row in extension_rows
        ],
        key=lambda item: item["name"],
    )
    db_role_settings = sorted(
        [
            {
                "database_oid": int(row["setdatabase"]),
                "role_name": str(row["role_name"]),
                "setting": str(row["setting"]),
            }
            for row in db_role_setting_rows
        ],
        key=lambda item: (item["database_oid"], item["role_name"], item["setting"]),
    )
    postgrest = _normalize_postgrest_snapshot(postgrest_snapshot, project_ref=project_ref)

    semantic = {
        "project_ref": project_ref,
        "visual_assets_registry": visual_assets_registry,
        "transport": dict(transport),
        "database": {
            "database_name": str(session["database_name"]),
            "server_version_num": str(session["server_version_num"]),
            "transaction_read_only": "on",
            "current_user": str(session["current_user"]),
        },
        "functions": functions,
        "indexes": indexes,
        "relations": relations,
        "p1_readonly_role": role,
        "settings": dict(sorted(settings.items())),
        "extensions": extensions,
        "db_role_settings": db_role_settings,
        "postgrest": postgrest,
    }
    return {
        "schema": MANIFEST_SCHEMA,
        "phase": phase,
        "captured_at": _timestamp(captured_at),
        "manifest": semantic,
        "manifest_sha256": sha256_json(semantic),
    }


def capture_live_manifest(
    connection: Any,
    *,
    project_ref: str,
    visual_assets_registry: str,
    phase: str,
    postgrest_snapshot: Mapping[str, Any],
    captured_at: str | datetime | None = None,
) -> dict[str, Any]:
    """Capture via catalog SELECTs on an approved persistent read-only session."""

    transport = _validated_transport(connection, project_ref=project_ref)
    session_rows = _cursor_rows(connection, SESSION_SQL)
    _expect(
        len(session_rows) == 1
        and session_rows[0].get("transaction_read_only") == "on",
        "HOLD_MANIFEST_CONNECTION_NOT_READ_ONLY",
        "catalog capture refused before any non-session query",
    )
    relation_names = [
        name.split(".", 1)[1]
        for name in required_relations(visual_assets_registry)
    ]
    function_names = [name.split(".", 1)[1] for name in REQUIRED_FUNCTIONS]
    function_names.append(IDENTITY_FUNCTION.split(".", 1)[1])
    return materialize_live_manifest(
        project_ref=project_ref,
        visual_assets_registry=visual_assets_registry,
        phase=phase,
        captured_at=captured_at or datetime.now(timezone.utc),
        transport=transport,
        session_rows=session_rows,
        function_rows=_cursor_rows(connection, FUNCTIONS_SQL, (function_names,)),
        index_rows=_cursor_rows(connection, INDEXES_SQL, (relation_names,)),
        relation_rows=_cursor_rows(connection, RELATIONS_SQL, (relation_names,)),
        role_rows=_cursor_rows(connection, ROLE_SQL),
        setting_rows=_cursor_rows(connection, SETTINGS_SQL),
        extension_rows=_cursor_rows(connection, EXTENSIONS_SQL),
        db_role_setting_rows=_cursor_rows(connection, DB_ROLE_SETTINGS_SQL),
        postgrest_snapshot=postgrest_snapshot,
    )


def _acl_privileges(acl: Sequence[Mapping[str, Any]], grantee: str) -> set[str]:
    return {
        str(row["privilege"]).upper()
        for row in acl
        if row.get("grantee") == grantee
    }


def verify_intrinsic_safety(
    capture: Mapping[str, Any],
    *,
    expected_function_sha256: Mapping[str, str] = S277_EXPECTED_FUNCTION_SHA256,
) -> None:
    """Reject a capture that cannot safely represent the P1 retrieval boundary."""

    _exact_keys(
        capture,
        {"schema", "phase", "captured_at", "manifest", "manifest_sha256"},
        code="HOLD_MANIFEST_SHAPE",
        path="capture",
    )
    _expect(capture["schema"] == MANIFEST_SCHEMA, "HOLD_MANIFEST_SHAPE", "schema")
    semantic = capture["manifest"]
    _expect(isinstance(semantic, Mapping), "HOLD_MANIFEST_SHAPE", "manifest")
    _expect(
        capture["manifest_sha256"] == sha256_json(semantic),
        "HOLD_MANIFEST_SELF_HASH_DRIFT",
        "manifest_sha256",
    )
    _timestamp(str(capture["captured_at"]))
    _expect(
        semantic.get("database", {}).get("transaction_read_only") == "on"
        and semantic.get("database", {}).get("current_user") == "p1_readonly",
        "HOLD_P1_RUNTIME_IDENTITY_DRIFT",
        "manifest was not captured as p1_readonly in a read-only transaction",
    )

    functions = semantic.get("functions")
    _expect(isinstance(functions, list), "HOLD_MANIFEST_SHAPE", "functions")
    by_name: dict[str, list[Mapping[str, Any]]] = {}
    for function in functions:
        by_name.setdefault(str(function["name"]), []).append(function)
    _expect(
        set(by_name) == set(REQUIRED_FUNCTIONS) | {IDENTITY_FUNCTION},
        "HOLD_RPC_SET_DRIFT",
        f"functions={sorted(by_name)}",
    )
    _expect(
        set(expected_function_sha256) == set(REQUIRED_FUNCTIONS),
        "HOLD_EXPECTED_MANIFEST_INVALID",
        "function hash keys",
    )
    for name, arg_types in REQUIRED_FUNCTIONS.items():
        rows = by_name[name]
        _expect(len(rows) == 1, "HOLD_RPC_OVERLOAD_DRIFT", name)
        function = rows[0]
        expected_signature = f"{name}({','.join(arg_types)})"
        _expect(
            function["signature"] == expected_signature
            and function["overload_count"] == 1,
            "HOLD_RPC_SIGNATURE_DRIFT",
            name,
        )
        _expect(
            function["definition_sha256_lf"] == expected_function_sha256[name],
            "HOLD_RPC_DEFINITION_DRIFT",
            name,
        )
        _expect(
            function["function_kind"] == "f" and not function["leakproof"],
            "HOLD_RPC_EXECUTION_CLASS_DRIFT",
            name,
        )
        if name in RETRIEVAL_FUNCTIONS:
            _expect(
                function["volatility"] == "v" and not function["security_definer"],
                "HOLD_RPC_EXECUTION_CLASS_DRIFT",
                name,
            )
            _expect(
                "EXECUTE" in _acl_privileges(function["acl"], "p1_readonly"),
                "HOLD_P1_ROLE_GRANT_MISSING",
                f"EXECUTE {name}",
            )
        else:
            _expect(
                function["volatility"] == "s" and function["security_definer"],
                "HOLD_FINGERPRINT_FUNCTION_DRIFT",
                name,
            )
            _expect(
                "EXECUTE" not in _acl_privileges(function["acl"], "p1_readonly"),
                "HOLD_P1_ROLE_OVERPRIVILEGED",
                "p1_readonly must not execute corpus_fingerprint_v1",
            )

    identity_rows = by_name[IDENTITY_FUNCTION]
    _expect(len(identity_rows) == 1, "HOLD_RPC_OVERLOAD_DRIFT", IDENTITY_FUNCTION)
    identity_function = identity_rows[0]
    _expect(
        identity_function["signature"] == f"{IDENTITY_FUNCTION}()"
        and identity_function["overload_count"] == 1
        and identity_function["volatility"] == "s"
        and identity_function["security_definer"] is False
        and identity_function["function_kind"] == "f"
        and identity_function["language"] == "sql",
        "HOLD_POSTGREST_IDENTITY_FUNCTION_DRIFT",
        "identity RPC execution class",
    )
    identity_acl = identity_function["acl"]
    _expect(
        _acl_privileges(identity_acl, "p1_readonly") == {"EXECUTE"}
        and not any(
            _acl_privileges(identity_acl, grantee)
            for grantee in ("PUBLIC", "anon", "authenticated", "service_role")
        ),
        "HOLD_POSTGREST_IDENTITY_FUNCTION_DRIFT",
        "identity RPC ACL",
    )
    identity_definition = identity_function["definition"].lower()
    _expect(
        "current_user" in identity_definition
        and "transaction_read_only" in identity_definition
        and "statement_timeout" in identity_definition,
        "HOLD_POSTGREST_IDENTITY_FUNCTION_DRIFT",
        "identity RPC body",
    )

    role = semantic.get("p1_readonly_role")
    _expect(isinstance(role, Mapping), "HOLD_P1_ROLE_MISSING", "p1_readonly")
    unsafe_role_flags = {
        "is_superuser",
        "inherits",
        "can_create_role",
        "can_create_db",
        "can_login",
        "can_replicate",
        "bypasses_rls",
    }
    _expect(
        role.get("role_name") == "p1_readonly"
        and not any(bool(role.get(flag)) for flag in unsafe_role_flags),
        "HOLD_P1_ROLE_UNSAFE",
        "p1_readonly role attributes",
    )
    members = role.get("members") or []
    authenticator = [member for member in members if member.get("member") == "authenticator"]
    operator = [member for member in members if member.get("member") == "postgres"]
    _expect(
        len(members) == 2
        and len(authenticator) == 1
        and authenticator[0].get("set_option") is True
        and authenticator[0].get("inherit_option") is False
        and authenticator[0].get("admin_option") is False
        and len(operator) == 1
        and operator[0].get("set_option") is True
        and operator[0].get("inherit_option") is False
        and operator[0].get("admin_option") is True,
        "HOLD_P1_ROLE_MEMBERSHIP_DRIFT",
        "authenticator and postgres operator SET ROLE memberships",
    )
    _expect(
        role.get("member_of") == [],
        "HOLD_P1_ROLE_OVERPRIVILEGED",
        "p1_readonly must not be a member of another role",
    )
    _expect(
        role.get("role_settings") == ["statement_timeout=30s"],
        "HOLD_P1_ROLE_SETTING_DRIFT",
        "statement_timeout",
    )
    _expect(
        role.get("schema_create") is False,
        "HOLD_P1_ROLE_SCHEMA_CREATE",
        "p1_readonly must not CREATE in public",
    )
    _expect(
        role.get("accessible_security_definer_functions") == [],
        "HOLD_P1_ROLE_SECURITY_DEFINER_ESCAPE",
        "p1_readonly can execute a public SECURITY DEFINER function",
    )

    relations = semantic.get("relations")
    _expect(isinstance(relations, list), "HOLD_MANIFEST_SHAPE", "relations")
    relation_by_name = {str(row["name"]): row for row in relations}
    expected_relations = required_relations(str(semantic.get("visual_assets_registry")))
    _expect(
        set(relation_by_name) == set(expected_relations),
        "HOLD_RELATION_SET_DRIFT",
        f"relations={sorted(relation_by_name)}",
    )
    for name, relation in relation_by_name.items():
        privileges = _acl_privileges(relation["acl"], "p1_readonly")
        _expect(
            privileges == {"SELECT"},
            "HOLD_P1_ROLE_TABLE_PRIVILEGE_DRIFT",
            f"{name}: {sorted(privileges)}",
        )
    chunks = relation_by_name["public.chunks_v2"]
    policies = chunks["policies"]
    p1_select = [
        policy
        for policy in policies
        if policy["name"] == "chunks_v2_p1_readonly_select"
    ]
    _expect(
        chunks["row_security"] is True
        and len(p1_select) == 1
        and p1_select[0]["command"] == "SELECT"
        and "p1_readonly" in p1_select[0]["roles"]
        and str(p1_select[0]["using"]).strip("() ").lower() == "true"
        and p1_select[0]["check"] is None,
        "HOLD_P1_ROLE_RLS_POLICY_DRIFT",
        "chunks_v2 SELECT policy",
    )

    indexes = semantic.get("indexes")
    _expect(isinstance(indexes, list) and indexes, "HOLD_INDEX_SET_DRIFT", "indexes")
    _expect(
        all(row["is_valid"] and row["is_ready"] and row["is_live"] for row in indexes),
        "HOLD_INDEX_STATE_DRIFT",
        "an index is invalid, unready or not live",
    )
    hnsw_by_relation: dict[str, list[Mapping[str, Any]]] = {}
    for index in indexes:
        if index["access_method"] == "hnsw":
            hnsw_by_relation.setdefault(str(index["relation"]), []).append(index)
    for relation in (
        "public.chunks_v2",
        "public.chunks_v2_enunciados",
        "public.chunks_v2_hyq",
    ):
        candidates = hnsw_by_relation.get(relation, [])
        _expect(len(candidates) == 1, "HOLD_HNSW_INDEX_DRIFT", relation)
        keys = candidates[0]["keys"]
        _expect(
            any(
                key.get("formatted_type") == "vector(1024)"
                and key.get("opclass_name") == "vector_cosine_ops"
                for key in keys
            ),
            "HOLD_HNSW_INDEX_DRIFT",
            f"{relation}: vector(1024)/vector_cosine_ops",
        )

    extensions = {row["name"]: row for row in semantic.get("extensions", [])}
    _expect(
        set(extensions) == {"vector", "unaccent", "pgcrypto"},
        "HOLD_EXTENSION_DRIFT",
        f"extensions={sorted(extensions)}",
    )
    settings = semantic.get("settings") or {}
    required_settings = {
        "server_version_num",
        "lc_collate",
        "lc_ctype",
        "default_text_search_config",
        "hnsw.ef_search",
        "hnsw.iterative_scan",
        "hnsw.max_scan_tuples",
        "hnsw.scan_mem_multiplier",
        "pgrst.db_schemas",
        "pgrst.db_anon_role",
        "pgrst.db_max_rows",
    }
    _expect(
        set(settings) == required_settings,
        "HOLD_DATABASE_CONFIG_DRIFT",
        "setting set",
    )
    _expect(
        settings["default_text_search_config"] == "public.spanish_unaccent",
        "HOLD_DATABASE_CONFIG_DRIFT",
        "default_text_search_config",
    )

    # Re-run the strict PostgREST validator over the semantic snapshot so a
    # hand-edited capture cannot bypass the boundary validation.
    postgrest = semantic.get("postgrest")
    _expect(isinstance(postgrest, Mapping), "HOLD_POSTGREST_SNAPSHOT_INVALID", "missing")
    reconstructed = {
        "schema": POSTGREST_SCHEMA,
        "project_ref": postgrest.get("project_ref"),
        "source": postgrest.get("source"),
        "openapi_status": postgrest.get("openapi_status"),
        "openapi_profile": postgrest.get("openapi_profile"),
        "openapi_sha256": postgrest.get("openapi_sha256"),
        "rpc_methods": postgrest.get("rpc_methods"),
        "identity_probe": postgrest.get("identity_probe"),
        "runtime_config": postgrest.get("runtime_config"),
    }
    _normalize_postgrest_snapshot(reconstructed, project_ref=semantic["project_ref"])
    _expect(
        postgrest["identity_probe"]["function_definition_sha256_lf"]
        == identity_function["definition_sha256_lf"],
        "HOLD_POSTGREST_IDENTITY_FUNCTION_DRIFT",
        "PostgREST probe is not bound to the captured identity function",
    )


def build_manifest_contract(
    capture: Mapping[str, Any],
    *,
    expected_function_sha256: Mapping[str, str] = S277_EXPECTED_FUNCTION_SHA256,
) -> dict[str, Any]:
    """Seal an operator-reviewed safe capture as the exact P1 expectation."""

    _expect(capture.get("phase") == "pre", "HOLD_MANIFEST_PHASE_INVALID", "contract needs pre")
    verify_intrinsic_safety(
        capture, expected_function_sha256=expected_function_sha256
    )
    semantic = capture["manifest"]
    return {
        "schema": CONTRACT_SCHEMA,
        "manifest_schema": MANIFEST_SCHEMA,
        "manifest_sha256": capture["manifest_sha256"],
        "expected_function_sha256": dict(sorted(expected_function_sha256.items())),
        "manifest": semantic,
    }


def verify_manifest_capture(
    contract: Mapping[str, Any], capture: Mapping[str, Any]
) -> None:
    _exact_keys(
        contract,
        {
            "schema",
            "manifest_schema",
            "manifest_sha256",
            "expected_function_sha256",
            "manifest",
        },
        code="HOLD_EXPECTED_MANIFEST_INVALID",
        path="contract",
    )
    _expect(
        contract["schema"] == CONTRACT_SCHEMA
        and contract["manifest_schema"] == MANIFEST_SCHEMA,
        "HOLD_EXPECTED_MANIFEST_INVALID",
        "schema",
    )
    _expect(
        contract["manifest_sha256"] == sha256_json(contract["manifest"]),
        "HOLD_EXPECTED_MANIFEST_INVALID",
        "self hash",
    )
    verify_intrinsic_safety(
        capture,
        expected_function_sha256=contract["expected_function_sha256"],
    )
    _expect(
        capture["manifest_sha256"] == contract["manifest_sha256"]
        and capture["manifest"] == contract["manifest"],
        "HOLD_FENCE_MANIFEST_DRIFT",
        f"phase={capture.get('phase')}",
    )


def verify_manifest_window(
    contract: Mapping[str, Any], captures: Sequence[Mapping[str, Any]]
) -> None:
    """Require exact pre/watch/post identity and monotonic receipt times."""

    _expect(len(captures) >= 2, "HOLD_FENCE_MANIFEST_SEQUENCE", "pre/post required")
    phases = [capture.get("phase") for capture in captures]
    _expect(
        phases[0] == "pre"
        and phases[-1] == "post"
        and all(phase == "watch" for phase in phases[1:-1]),
        "HOLD_FENCE_MANIFEST_SEQUENCE",
        f"phases={phases}",
    )
    timestamps = [
        datetime.fromisoformat(_timestamp(str(capture["captured_at"])).replace("Z", "+00:00"))
        for capture in captures
    ]
    _expect(
        timestamps == sorted(timestamps),
        "HOLD_FENCE_MANIFEST_SEQUENCE",
        "capture timestamps are not monotonic",
    )
    for capture in captures:
        verify_manifest_capture(contract, capture)
