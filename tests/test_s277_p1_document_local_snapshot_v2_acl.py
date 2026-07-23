from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260722014500_s277_p1_document_local_snapshot_v2_acl.sql"
)


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_acl_is_forward_only_and_targets_exact_v2_signature() -> None:
    sql = _sql()
    assert "document_local_snapshot_v2(jsonb,text,integer,integer)" in sql
    assert "document_local_snapshot_v1" not in sql
    assert "DROP FUNCTION" not in sql
    assert "DROP TABLE" not in sql
    assert not re.search(r"^\s*(?:BEGIN|COMMIT)\s*;", sql, re.MULTILINE)


def test_p1_gets_only_two_registry_columns_and_verified_rows() -> None:
    sql = " ".join(_sql().split())
    assert (
        "REVOKE ALL PRIVILEGES ON TABLE public.document_revision_lineages "
        "FROM p1_readonly;"
    ) in sql
    assert (
        "GRANT SELECT (id, authority_status) "
        "ON public.document_revision_lineages TO p1_readonly;"
    ) in sql
    assert (
        "CREATE POLICY document_revision_lineages_p1_verified_select "
        "ON public.document_revision_lineages AS PERMISSIVE FOR SELECT "
        "TO p1_readonly USING (authority_status = 'verified');"
    ) in sql
    for denied_column in (
        "authority_contract",
        "authority_evidence_sha256",
        "created_at",
        "notes",
    ):
        assert f"'{denied_column}', 'SELECT'" in sql
    for denied_privilege in (
        "'SELECT'",
        "'INSERT'",
        "'UPDATE'",
        "'DELETE'",
        "'TRUNCATE'",
        "'REFERENCES'",
        "'TRIGGER'",
    ):
        assert (
            "'p1_readonly', 'public.document_revision_lineages', "
            f"{denied_privilege}"
        ) in sql


def test_rpc_execute_is_p1_and_service_role_only() -> None:
    sql = " ".join(_sql().split())
    assert (
        "REVOKE ALL ON FUNCTION public.document_local_snapshot_v2( "
        "JSONB, TEXT, INTEGER, INTEGER ) "
        "FROM PUBLIC, anon, authenticated, p1_readonly;"
    ) in sql
    assert (
        "GRANT EXECUTE ON FUNCTION public.document_local_snapshot_v2( "
        "JSONB, TEXT, INTEGER, INTEGER ) TO service_role, p1_readonly;"
    ) in sql
    for role in ("p1_readonly", "service_role", "anon", "authenticated"):
        assert (
            f"'{role}', "
            "'public.document_local_snapshot_v2(jsonb,text,integer,integer)', "
            "'EXECUTE'"
        ) in sql


def test_migration_has_exact_fail_closed_pre_and_postconditions() -> None:
    sql = _sql()
    assert "pg_catalog.to_regrole('p1_readonly') IS NULL" in sql
    assert "pg_catalog.to_regprocedure(" in sql
    assert "pg_catalog.to_regclass(" in sql
    assert "policy already exists" in sql
    assert "polcmd = 'r'" in sql
    assert "policy.polpermissive" in sql
    assert "policy.polwithcheck IS NULL" in sql
    assert "NOTIFY pgrst, 'reload schema';" in sql
