from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import s277_c1_p1_live_manifest as live


PROJECT_REF = "abcdefghijklmnopqrst"
NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


def _acl(grantee: str, privilege: str) -> dict:
    return {
        "grantee": grantee,
        "grantor": "postgres",
        "privilege": privilege,
        "grantable": False,
    }


def _function_rows() -> tuple[list[dict], dict[str, str]]:
    rows = []
    hashes = {}
    for name, args in live.REQUIRED_FUNCTIONS.items():
        schema, function_name = name.split(".", 1)
        definition = f"CREATE FUNCTION {name} fixture {function_name}\n"
        hashes[name] = live.sha256_text_lf(definition)
        retrieval = name in live.RETRIEVAL_FUNCTIONS
        rows.append(
            {
                "schema_name": schema,
                "function_name": function_name,
                "arg_types": list(args),
                "overload_count": 1,
                "result_type": "record",
                "volatility": "v" if retrieval else "s",
                "security_definer": not retrieval,
                "leakproof": False,
                "parallel_safety": "u",
                "function_kind": "f",
                "language": "plpgsql" if retrieval else "sql",
                "owner": "postgres",
                "function_config": [],
                "definition": definition,
                "acl": [_acl("p1_readonly", "EXECUTE")] if retrieval else [_acl("service_role", "EXECUTE")],
            }
        )
    identity_definition = (
        "CREATE FUNCTION public.p1_runtime_identity_v1() RETURNS jsonb "
        "LANGUAGE sql STABLE SECURITY INVOKER AS SELECT current_user, "
        "current_setting('transaction_read_only'), current_setting('statement_timeout')\n"
    )
    rows.append(
        {
            "schema_name": "public",
            "function_name": "p1_runtime_identity_v1",
            "arg_types": [],
            "overload_count": 1,
            "result_type": "jsonb",
            "volatility": "s",
            "security_definer": False,
            "leakproof": False,
            "parallel_safety": "u",
            "function_kind": "f",
            "language": "sql",
            "owner": "postgres",
            "function_config": ["search_path=pg_catalog"],
            "definition": identity_definition,
            "acl": [_acl("p1_readonly", "EXECUTE")],
        }
    )
    return rows, hashes


def _index_rows(visual: str) -> list[dict]:
    rows = []
    for relation in ("chunks_v2", "chunks_v2_enunciados", "chunks_v2_hyq"):
        rows.append(
            {
                "table_schema": "public",
                "table_name": relation,
                "index_schema": "public",
                "index_name": f"idx_{relation}_embedding",
                "access_method": "hnsw",
                "is_unique": False,
                "is_primary": False,
                "is_valid": True,
                "is_ready": True,
                "is_live": True,
                "key_attribute_count": 1,
                "attribute_count": 1,
                "reloptions": [],
                "predicate": None,
                "expressions": None,
                "definition": f"CREATE INDEX idx_{relation}_embedding USING hnsw\n",
                "keys": [{
                    "position": 1,
                    "attribute_number": 2,
                    "column_name": "embedding",
                    "formatted_type": "vector(1024)",
                    "type_schema": "public",
                    "type_name": "vector",
                    "opclass_schema": "public",
                    "opclass_name": "vector_cosine_ops",
                    "collation_schema": None,
                    "collation_name": None,
                    "options": 0,
                }],
            }
        )
    for relation in (["documents", "document_visual_assets"] if visual == "on" else ["documents"]):
        rows.append(
            {
                "table_schema": "public",
                "table_name": relation,
                "index_schema": "public",
                "index_name": f"{relation}_pkey",
                "access_method": "btree",
                "is_unique": True,
                "is_primary": True,
                "is_valid": True,
                "is_ready": True,
                "is_live": True,
                "key_attribute_count": 1,
                "attribute_count": 1,
                "reloptions": [],
                "predicate": None,
                "expressions": None,
                "definition": f"CREATE UNIQUE INDEX {relation}_pkey USING btree\n",
                "keys": [],
            }
        )
    return rows


def _relation_rows(visual: str) -> list[dict]:
    rows = []
    for qualified in live.required_relations(visual):
        name = qualified.split(".", 1)[1]
        rows.append(
            {
                "schema_name": "public",
                "relation_name": name,
                "relation_kind": "r",
                "owner": "postgres",
                "row_security": name == "chunks_v2",
                "force_row_security": False,
                "reloptions": [],
                "acl": [_acl("p1_readonly", "SELECT")],
                "policies": ([{
                    "name": "chunks_v2_p1_readonly_select",
                    "permissive": "PERMISSIVE",
                    "roles": ["p1_readonly"],
                    "command": "SELECT",
                    "using": "true",
                    "check": None,
                }] if name == "chunks_v2" else []),
            }
        )
    return rows


def _postgrest(identity_sha256: str) -> dict:
    return {
        "schema": live.POSTGREST_SCHEMA,
        "project_ref": PROJECT_REF,
        "source": "supabase_management_api_and_openapi",
        "openapi_status": 200,
        "openapi_profile": "public",
        "openapi_sha256": "a" * 64,
        "rpc_methods": {key: list(value) for key, value in live.REQUIRED_RPC_METHODS.items()},
        "identity_probe": {
            "path": "/rpc/p1_runtime_identity_v1",
            "method": "GET",
            "status": 200,
            "current_user": "p1_readonly",
            "transaction_read_only": "on",
            "statement_timeout": "30s",
            "transaction_mode_scope": "identity_get_only_not_rpc_post",
            "function_definition_sha256_lf": identity_sha256,
        },
        "runtime_config": {
            "data_api_enabled": True,
            "exposed_schemas": ["public"],
            "max_rows": 1000,
            "postgrest_version": "fixture",
        },
    }


def _capture(
    *,
    visual: str = "on",
    current_user: str = "p1_readonly",
    transport: dict | None = None,
) -> tuple[dict, dict[str, str]]:
    function_rows, hashes = _function_rows()
    identity_sha256 = live.sha256_text_lf(
        next(row["definition"] for row in function_rows if row["function_name"] == "p1_runtime_identity_v1")
    )
    capture = live.materialize_live_manifest(
        project_ref=PROJECT_REF,
        visual_assets_registry=visual,
        phase="pre",
        captured_at=NOW,
        transport=transport or {
            "mode": "direct",
            "host": f"db.{PROJECT_REF}.supabase.co",
            "port": 5432,
            "tls": True,
        },
        session_rows=[{
            "transaction_read_only": "on",
            "database_name": "postgres",
            "current_user": current_user,
            "server_version_num": "170006",
        }],
        function_rows=function_rows,
        index_rows=_index_rows(visual),
        relation_rows=_relation_rows(visual),
        role_rows=[{
            "role_name": "p1_readonly",
            "is_superuser": False,
            "inherits": False,
            "can_create_role": False,
            "can_create_db": False,
            "can_login": False,
            "can_replicate": False,
            "bypasses_rls": False,
            "members": [{
                "member": "authenticator",
                "admin_option": False,
                "inherit_option": False,
                "set_option": True,
            }],
            "member_of": [],
            "role_settings": ["statement_timeout=30s"],
            "schema_create": False,
            "accessible_security_definer_functions": [],
        }],
        setting_rows=[
            {"name": name, "value": value}
            for name, value in {
                "server_version_num": "170006",
                "lc_collate": "C.UTF-8",
                "lc_ctype": "C.UTF-8",
                "default_text_search_config": "public.spanish_unaccent",
                "hnsw.ef_search": "40",
                "hnsw.iterative_scan": "off",
                "hnsw.max_scan_tuples": "20000",
                "hnsw.scan_mem_multiplier": "1",
                "pgrst.db_schemas": None,
                "pgrst.db_anon_role": None,
                "pgrst.db_max_rows": None,
            }.items()
        ],
        extension_rows=[
            {"name": "vector", "version": "0.8.0", "schema_name": "public"},
            {"name": "unaccent", "version": "1.1", "schema_name": "public"},
            {"name": "pgcrypto", "version": "1.3", "schema_name": "extensions"},
        ],
        db_role_setting_rows=[],
        postgrest_snapshot=_postgrest(identity_sha256),
    )
    return capture, hashes


def _rehashed(capture: dict) -> dict:
    capture["manifest_sha256"] = live.sha256_json(capture["manifest"])
    return capture


def test_safe_capture_seals_and_pre_watch_post_window_verifies() -> None:
    pre, hashes = _capture()
    contract = live.build_manifest_contract(pre, expected_function_sha256=hashes)
    watch = copy.deepcopy(pre)
    watch.update(phase="watch", captured_at=(NOW + timedelta(minutes=1)).isoformat())
    post = copy.deepcopy(pre)
    post.update(phase="post", captured_at=(NOW + timedelta(minutes=2)).isoformat())

    live.verify_manifest_window(contract, [pre, watch, post])
    assert set(live.REQUIRED_RPC_METHODS) == {
        "/rpc/match_chunks_v2",
        "/rpc/search_chunks_text_v2",
        "/rpc/match_chunks_v2_enunciados",
        "/rpc/match_hyq",
    }
    assert "public.document_visual_assets" in {
        row["name"] for row in pre["manifest"]["relations"]
    }


def test_definition_and_index_drift_fail_closed() -> None:
    pre, hashes = _capture()
    contract = live.build_manifest_contract(pre, expected_function_sha256=hashes)

    changed = copy.deepcopy(pre)
    changed["phase"] = "post"
    changed["manifest"]["functions"][0]["definition"] += "-- changed\n"
    changed["manifest"]["functions"][0]["definition_sha256_lf"] = live.sha256_text_lf(
        changed["manifest"]["functions"][0]["definition"]
    )
    _rehashed(changed)
    with pytest.raises(live.ManifestHold, match="HOLD_RPC_DEFINITION_DRIFT"):
        live.verify_manifest_capture(contract, changed)

    changed = copy.deepcopy(pre)
    changed["manifest"]["indexes"][0]["is_ready"] = False
    _rehashed(changed)
    with pytest.raises(live.ManifestHold, match="HOLD_INDEX_STATE_DRIFT"):
        live.verify_manifest_capture(contract, changed)


def test_role_identity_privileges_membership_and_settings_fail_closed() -> None:
    with pytest.raises(live.ManifestHold, match="HOLD_P1_RUNTIME_IDENTITY_DRIFT"):
        _capture(current_user="postgres")

    pre, hashes = _capture()
    for field, expected_code in (
        ("bypasses_rls", "HOLD_P1_ROLE_UNSAFE"),
        ("member_of", "HOLD_P1_ROLE_OVERPRIVILEGED"),
        ("role_settings", "HOLD_P1_ROLE_SETTING_DRIFT"),
    ):
        changed = copy.deepcopy(pre)
        role = changed["manifest"]["p1_readonly_role"]
        role[field] = (
            [{"role": "service_role", "set_option": True}]
            if field == "member_of"
            else ([] if field == "role_settings" else True)
        )
        _rehashed(changed)
        with pytest.raises(live.ManifestHold, match=expected_code):
            live.verify_intrinsic_safety(changed, expected_function_sha256=hashes)

    changed = copy.deepcopy(pre)
    relation = changed["manifest"]["relations"][0]
    relation["acl"].append(_acl("p1_readonly", "UPDATE"))
    _rehashed(changed)
    with pytest.raises(live.ManifestHold, match="HOLD_P1_ROLE_TABLE_PRIVILEGE_DRIFT"):
        live.verify_intrinsic_safety(changed, expected_function_sha256=hashes)

    changed = copy.deepcopy(pre)
    changed["manifest"]["p1_readonly_role"]["schema_create"] = True
    _rehashed(changed)
    with pytest.raises(live.ManifestHold, match="HOLD_P1_ROLE_SCHEMA_CREATE"):
        live.verify_intrinsic_safety(changed, expected_function_sha256=hashes)

    changed = copy.deepcopy(pre)
    changed["manifest"]["p1_readonly_role"][
        "accessible_security_definer_functions"
    ] = ["create_hnsw_index()"]
    _rehashed(changed)
    with pytest.raises(
        live.ManifestHold, match="HOLD_P1_ROLE_SECURITY_DEFINER_ESCAPE"
    ):
        live.verify_intrinsic_safety(changed, expected_function_sha256=hashes)


def test_visual_relation_is_conditional_but_on_is_fenced() -> None:
    off, hashes = _capture(visual="off")
    live.build_manifest_contract(off, expected_function_sha256=hashes)
    assert "public.document_visual_assets" not in {
        row["name"] for row in off["manifest"]["relations"]
    }

    broken, hashes = _capture(visual="on")
    broken["manifest"]["relations"] = [
        row for row in broken["manifest"]["relations"]
        if row["name"] != "public.document_visual_assets"
    ]
    _rehashed(broken)
    with pytest.raises(live.ManifestHold, match="HOLD_RELATION_SET_DRIFT"):
        live.verify_intrinsic_safety(broken, expected_function_sha256=hashes)


def test_supavisor_session_is_accepted_and_transaction_pooler_is_rejected() -> None:
    session_transport = {
        "mode": "supavisor_session",
        "host": "aws-1-eu-north-1.pooler.supabase.com",
        "port": 5432,
        "tls": True,
        "authenticated_project_ref": PROJECT_REF,
    }
    capture, hashes = _capture(transport=session_transport)
    live.build_manifest_contract(capture, expected_function_sha256=hashes)

    connection = SimpleNamespace(
        info=SimpleNamespace(
            host="aws-1-eu-north-1.pooler.supabase.com",
            port=5432,
            user=f"postgres.{PROJECT_REF}",
        )
    )
    assert live._validated_transport(connection, project_ref=PROJECT_REF) == session_transport

    connection.info.port = 6543
    with pytest.raises(live.ManifestHold, match="HOLD_FENCE_PERSISTENT_SESSION_REQUIRED"):
        live._validated_transport(connection, project_ref=PROJECT_REF)


def test_postgrest_requires_management_config_and_rejects_secret_shaped_keys() -> None:
    function_rows, _ = _function_rows()
    identity_sha256 = live.sha256_text_lf(
        next(row["definition"] for row in function_rows if row["function_name"] == "p1_runtime_identity_v1")
    )
    snapshot = _postgrest(identity_sha256)
    snapshot["runtime_config"]["api_token"] = "not-even-a-real-secret"
    with pytest.raises(live.ManifestHold, match="HOLD_MANIFEST_SECRET_MATERIAL"):
        live.materialize_live_manifest(
            project_ref=PROJECT_REF,
            visual_assets_registry="off",
            phase="pre",
            captured_at=NOW,
            transport={"mode": "direct", "host": f"db.{PROJECT_REF}.supabase.co", "port": 5432, "tls": True},
            session_rows=[{"transaction_read_only": "on", "database_name": "postgres", "current_user": "p1_readonly", "server_version_num": "170006"}],
            function_rows=function_rows,
            index_rows=_index_rows("off"),
            relation_rows=_relation_rows("off"),
            role_rows=[], setting_rows=[], extension_rows=[], db_role_setting_rows=[],
            postgrest_snapshot=snapshot,
        )


def test_migration_is_additive_read_only_and_contains_visual_and_role_defenses() -> None:
    sql = (
        Path(__file__).resolve().parent.parent
        / "supabase/migrations/20260721120000_add_p1_readonly_role.sql"
    ).read_text(encoding="utf-8")
    upper = sql.upper()
    assert "CREATE ROLE P1_READONLY" in upper
    assert "NOLOGIN NOINHERIT" in upper
    assert "NOBYPASSRLS" in upper
    assert "ALTER ROLE P1_READONLY RESET DEFAULT_TRANSACTION_READ_ONLY" in upper
    assert "ALTER ROLE P1_READONLY SET STATEMENT_TIMEOUT = '30S'" in upper
    assert "GRANT P1_READONLY TO AUTHENTICATOR WITH INHERIT FALSE" in upper
    assert "GRANT P1_READONLY TO AUTHENTICATOR WITH SET TRUE" in upper
    assert "GRANT P1_READONLY TO AUTHENTICATOR WITH ADMIN FALSE" in upper
    assert "REVOKE EXECUTE ON FUNCTION PUBLIC.CREATE_HNSW_INDEX() FROM PUBLIC" in upper
    assert "HAS_SCHEMA_PRIVILEGE('P1_READONLY', 'PUBLIC', 'CREATE')" in upper
    assert "PROC.PROSECDEF" in upper
    assert "PUBLIC.DOCUMENT_VISUAL_ASSETS" in upper
    assert "CREATE FUNCTION PUBLIC.P1_RUNTIME_IDENTITY_V1()" in upper
    assert "NOTIFY PGRST, 'RELOAD CONFIG'" in upper
    assert "GRANT SELECT ON TABLE" in upper
    assert "GRANT EXECUTE ON FUNCTION PUBLIC.CORPUS_FINGERPRINT_V1" not in upper
    for forbidden in ("GRANT INSERT", "GRANT UPDATE", "GRANT DELETE", "GRANT TRUNCATE"):
        assert forbidden not in upper
