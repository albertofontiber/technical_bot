import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "supabase"
    / "migration_proposals"
    / "20260720095702_add_query_logs_rag_trace.sql"
)
BOOTSTRAP = ROOT / "supabase_schema.sql"


def _sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_migration_recreates_the_exact_constraint_atomically_and_validates_it():
    sql = _sql(MIGRATION)
    assert re.search(r"\bbegin\s*;", sql)
    assert re.search(r"\bcommit\s*;\s*$", sql)
    assert "drop constraint if exists query_logs_rag_trace_object_size_v1" in sql
    assert "add constraint query_logs_rag_trace_object_size_v1" in sql
    assert "jsonb_typeof(rag_trace) = 'object'" in sql
    assert "octet_length(rag_trace::text) <= 8192" in sql
    assert "not valid" in sql
    assert "validate constraint query_logs_rag_trace_object_size_v1" in sql
    assert "and contype = 'c'" in sql


def test_migration_preserves_the_live_privilege_and_rls_contract():
    sql = _sql(MIGRATION)
    assert sql.count("rolbypassrls") >= 2
    assert sql.count("relrowsecurity") >= 2
    assert sql.count("relforcerowsecurity") >= 2
    assert "array['anon', 'authenticated']" in sql
    assert "has_table_privilege('service_role', 'public.query_logs', 'insert')" in sql
    assert sql.count("'maintain'") >= 4
    assert sql.count("has_any_column_privilege") >= 8
    for privilege in ("update", "delete", "truncate", "references", "trigger", "maintain"):
        assert sql.count(
            f"has_table_privilege('service_role', 'public.query_logs', '{privilege}')"
        ) >= 2
    assert not re.search(r"create\s+index[^;]*rag_trace", sql, re.DOTALL)
    assert "column_default is null" in sql
    assert "is_identity = 'no'" in sql
    assert "is_generated = 'never'" in sql


def test_full_schema_bootstrap_has_atomic_trace_limit_and_personal_data_boundary():
    sql = _sql(BOOTSTRAP)
    block = re.search(
        r"do \$rag_trace_constraint\$(.*?)\$rag_trace_constraint\$;",
        sql,
        re.DOTALL,
    )
    assert block is not None
    assert "drop constraint if exists query_logs_rag_trace_object_size_v1" in block.group(1)
    assert "add constraint query_logs_rag_trace_object_size_v1" in block.group(1)
    boundary = re.search(
        r"do \$personal_data_boundary\$(.*?)\$personal_data_boundary\$;",
        sql,
        re.DOTALL,
    )
    assert boundary is not None
    boundary_sql = boundary.group(1)
    personal_section = sql[sql.index("-- keep creation and hardening"):]
    assert re.search(r"\bbegin\s*;", personal_section)
    assert re.search(r"\bcommit\s*;", personal_section)
    for table in ("query_logs", "feedback", "user_consent"):
        assert table in boundary_sql
    assert "enable row level security" in boundary_sql
    assert "force row level security" in boundary_sql
    assert "revoke all privileges on table public.%i" in boundary_sql
    assert "grant select, insert on table public.query_logs to service_role" in sql
    assert "grant select, insert on table public.feedback to service_role" in sql
    assert (
        "grant select, insert, update on table public.user_consent to service_role"
        in sql
    )
    assert "'maintain'" in boundary_sql
    assert "has_any_column_privilege" in boundary_sql
    assert "relrowsecurity" in boundary_sql
    assert "relforcerowsecurity" in boundary_sql
    assert "column_default is null" in block.group(1)
    assert "is_identity = 'no'" in block.group(1)
    assert "is_generated = 'never'" in block.group(1)
