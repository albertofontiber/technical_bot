"""Capture a read-only live receipt for the S277 lineage/RPC v2 boundary."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg2
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "evals/s277_document_local_migration_reconciliation_receipt_v2.json"
)
MIGRATIONS = {
    "20260721210847": ROOT
    / "supabase/migrations/20260721210847_s277_document_local_snapshot_rpc.sql",
    "20260721220110": ROOT
    / "supabase/migrations/20260721220110_s277_document_local_exact_blob_authority.sql",
    "20260722013000": ROOT
    / "supabase/migrations/20260722013000_s277_document_revision_lineage_snapshot_v2.sql",
    "20260722014500": ROOT
    / "supabase/migrations/20260722014500_s277_p1_document_local_snapshot_v2_acl.sql",
}
FUNCTION_SIGNATURE = (
    "public.document_local_snapshot_v2(jsonb,text,integer,integer)"
)
LINEAGE_ID = "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429"
OLD_DOCUMENT_ID = "e98e05ff-ee1d-5341-869a-65768855dae9"
ACTIVE_DOCUMENT_ID = "494e71be-873b-48c1-adb3-a21a122da111"


def _sha256_lf_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload.replace(b"\r\n", b"\n")).hexdigest()


def _rows(cursor: Any) -> list[dict[str, Any]]:
    columns = [str(item[0]) for item in cursor.description or ()]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def capture(env_file: Path, output: Path) -> dict[str, Any]:
    values = dotenv_values(env_file)
    database_url = str(values.get("DATABASE_URL") or "")
    supabase_url = str(values.get("SUPABASE_URL") or "")
    if not database_url or not supabase_url:
        raise RuntimeError("DATABASE_URL and SUPABASE_URL are required")
    project_ref = (urlparse(supabase_url).hostname or "").split(".")[0]
    if not project_ref:
        raise RuntimeError("SUPABASE_URL project ref is invalid")

    connection = psycopg2.connect(
        database_url,
        connect_timeout=15,
        sslmode="require",
    )
    try:
        connection.set_session(readonly=True, autocommit=False)
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    pg_catalog.current_setting('server_version') AS server_version,
                    language.lanname AS language,
                    function.provolatile AS volatility,
                    function.prosecdef AS security_definer,
                    function.proconfig AS function_config,
                    pg_catalog.pg_get_functiondef(function.oid) AS definition,
                    pg_catalog.has_function_privilege(
                        'service_role', function.oid, 'EXECUTE'
                    ) AS service_role_execute,
                    pg_catalog.has_function_privilege(
                        'p1_readonly', function.oid, 'EXECUTE'
                    ) AS p1_readonly_execute,
                    pg_catalog.has_function_privilege(
                        'anon', function.oid, 'EXECUTE'
                    ) AS anon_execute,
                    pg_catalog.has_function_privilege(
                        'authenticated', function.oid, 'EXECUTE'
                    ) AS authenticated_execute,
                    EXISTS (
                        SELECT 1
                        FROM pg_catalog.aclexplode(
                            COALESCE(
                                function.proacl,
                                pg_catalog.acldefault('f', function.proowner)
                            )
                        ) AS acl
                        WHERE acl.grantee = 0
                          AND acl.privilege_type = 'EXECUTE'
                    ) AS public_execute
                FROM pg_catalog.pg_proc AS function
                JOIN pg_catalog.pg_language AS language
                  ON language.oid = function.prolang
                WHERE function.oid = %s::pg_catalog.regprocedure
                """,
                (FUNCTION_SIGNATURE,),
            )
            function_rows = _rows(cursor)
            if len(function_rows) != 1:
                raise RuntimeError("document_local_snapshot_v2 is absent or ambiguous")
            function = function_rows[0]
            definition = str(function.pop("definition"))
            function["definition_sha256_lf"] = _sha256_lf_bytes(
                definition.encode("utf-8")
            )
            function["function_config"] = list(function["function_config"] or [])

            cursor.execute(
                """
                SELECT version
                FROM supabase_migrations.schema_migrations
                WHERE version = ANY(%s)
                ORDER BY version
                """,
                (list(MIGRATIONS),),
            )
            observed_versions = {str(row[0]) for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT
                    id::text,
                    authority_status,
                    authority_contract,
                    authority_evidence_sha256
                FROM public.document_revision_lineages
                WHERE id = %s::uuid
                """,
                (LINEAGE_ID,),
            )
            lineage_rows = _rows(cursor)

            cursor.execute(
                """
                SELECT
                    id::text,
                    revision_lineage_id::text,
                    status,
                    supersedes_id::text,
                    superseded_by_id::text,
                    source_pdf_sha256,
                    source_pdf_filename
                FROM public.documents
                WHERE id = ANY(%s::uuid[])
                ORDER BY id
                """,
                ([OLD_DOCUMENT_ID, ACTIVE_DOCUMENT_ID],),
            )
            document_rows = _rows(cursor)

            cursor.execute(
                """
                SELECT
                    relation.relrowsecurity AS row_security,
                    policy.polcmd AS command,
                    policy.polpermissive AS permissive,
                    pg_catalog.pg_get_expr(
                        policy.polqual, policy.polrelid
                    ) AS using_expression,
                    pg_catalog.pg_get_expr(
                        policy.polwithcheck, policy.polrelid
                    ) AS check_expression,
                    ARRAY(
                        SELECT role.rolname
                        FROM pg_catalog.unnest(policy.polroles) AS member(role_oid)
                        JOIN pg_catalog.pg_roles AS role
                          ON role.oid = member.role_oid
                        ORDER BY role.rolname
                    ) AS roles
                FROM pg_catalog.pg_class AS relation
                JOIN pg_catalog.pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                LEFT JOIN pg_catalog.pg_policy AS policy
                  ON policy.polrelid = relation.oid
                 AND policy.polname =
                     'document_revision_lineages_p1_verified_select'
                WHERE namespace.nspname = 'public'
                  AND relation.relname = 'document_revision_lineages'
                """
            )
            policy_rows = _rows(cursor)

            cursor.execute(
                """
                SELECT
                    pg_catalog.has_table_privilege(
                        'p1_readonly',
                        'public.document_revision_lineages',
                        'SELECT'
                    ) AS table_select,
                    pg_catalog.has_table_privilege(
                        'p1_readonly',
                        'public.document_revision_lineages',
                        'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'
                    ) AS any_table_write,
                    pg_catalog.has_column_privilege(
                        'p1_readonly',
                        'public.document_revision_lineages',
                        'id',
                        'SELECT'
                    ) AS id_select,
                    pg_catalog.has_column_privilege(
                        'p1_readonly',
                        'public.document_revision_lineages',
                        'authority_status',
                        'SELECT'
                    ) AS authority_status_select,
                    pg_catalog.has_column_privilege(
                        'p1_readonly',
                        'public.document_revision_lineages',
                        'authority_contract',
                        'SELECT'
                    ) AS authority_contract_select,
                    pg_catalog.has_column_privilege(
                        'p1_readonly',
                        'public.document_revision_lineages',
                        'authority_evidence_sha256',
                        'SELECT'
                    ) AS authority_evidence_select,
                    pg_catalog.has_column_privilege(
                        'p1_readonly',
                        'public.document_revision_lineages',
                        'notes',
                        'SELECT'
                    ) AS notes_select
                """
            )
            acl_rows = _rows(cursor)
        finally:
            cursor.close()
        connection.rollback()
    finally:
        connection.close()

    migration_history = {
        version: version in observed_versions for version in MIGRATIONS
    }
    lineage = lineage_rows[0] if len(lineage_rows) == 1 else {}
    documents = {str(row["id"]): row for row in document_rows}
    old = documents.get(OLD_DOCUMENT_ID, {})
    active = documents.get(ACTIVE_DOCUMENT_ID, {})
    policy = policy_rows[0] if len(policy_rows) == 1 else {}
    acl = acl_rows[0] if len(acl_rows) == 1 else {}
    checks = {
        "migration_history_complete": all(migration_history.values()),
        "function_sql_stable_invoker_empty_search_path": (
            function["language"] == "sql"
            and function["volatility"] == "s"
            and function["security_definer"] is False
            and function["function_config"] == ['search_path=""']
        ),
        "function_execute_acl_exact": (
            function["service_role_execute"] is True
            and function["p1_readonly_execute"] is True
            and function["anon_execute"] is False
            and function["authenticated_execute"] is False
            and function["public_execute"] is False
        ),
        "lineage_registry_exact": (
            lineage.get("id") == LINEAGE_ID
            and lineage.get("authority_status") == "verified"
            and lineage.get("authority_contract") == "explicit_document_ids_v1"
            and lineage.get("authority_evidence_sha256")
            == "ba83f754e864caa98c7ad7dd86c434e599e13c1acc81f24eb654e0ad5bec1576"
        ),
        "hp011_documents_exactly_bound": (
            len(documents) == 2
            and old.get("revision_lineage_id") == LINEAGE_ID
            and old.get("status") == "superseded"
            and old.get("supersedes_id") is None
            and old.get("superseded_by_id") == ACTIVE_DOCUMENT_ID
            and active.get("revision_lineage_id") == LINEAGE_ID
            and active.get("status") == "active"
            and active.get("supersedes_id") == OLD_DOCUMENT_ID
            and active.get("superseded_by_id") is None
        ),
        "p1_lineage_rls_exact": (
            policy.get("row_security") is True
            and policy.get("command") == "r"
            and policy.get("permissive") is True
            and policy.get("roles") == ["p1_readonly"]
            and str(policy.get("using_expression") or "")
            == "(authority_status = 'verified'::text)"
            and policy.get("check_expression") is None
        ),
        "p1_lineage_column_acl_minimal": (
            acl.get("table_select") is False
            and acl.get("any_table_write") is False
            and acl.get("id_select") is True
            and acl.get("authority_status_select") is True
            and acl.get("authority_contract_select") is False
            and acl.get("authority_evidence_select") is False
            and acl.get("notes_select") is False
        ),
    }
    receipt = {
        "schema": "s277_document_local_migration_reconciliation_receipt_v2",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "status": "RECONCILED" if all(checks.values()) else "HOLD",
        "project": {
            "ref": project_ref,
            "postgres_version": function["server_version"],
        },
        "checks": checks,
        "terminal_state": {
            "migration_history": migration_history,
            "function": {
                key: value
                for key, value in function.items()
                if key != "server_version"
            },
            "lineage": lineage,
            "documents": document_rows,
            "policy": policy,
            "p1_acl": acl,
        },
        "local_migration_sha256_lf": {
            version: _sha256_lf_bytes(path.read_bytes())
            for version, path in MIGRATIONS.items()
        },
        "invariants": {
            "database_writes": 0,
            "model_calls": 0,
            "migration_repair_used": False,
            "include_all_used": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = capture(args.env_file.resolve(), args.output.resolve())
    print(json.dumps({"status": receipt["status"], "checks": receipt["checks"]}))
    return 0 if receipt["status"] == "RECONCILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
