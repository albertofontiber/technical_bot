"""Static, fail-closed checks for the S117 shadow-schema migration.

These tests deliberately do not claim SQL executability.  M0b still has to
apply and roll back the migration on disposable PostgreSQL with pgvector.
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260714102428_chunks_v3_provenance_shadow.sql"
)


def _sql() -> str:
    return SQL_PATH.read_text(encoding="utf-8")


def _without_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def _function(sql: str, name: str) -> str:
    pattern = rf"CREATE FUNCTION public\.{re.escape(name)}\b(?P<body>.*?)\n\$function\$;"
    match = re.search(pattern, sql, flags=re.IGNORECASE | re.DOTALL)
    assert match is not None, f"missing function {name}"
    return match.group(0)


def test_migration_is_explicitly_no_go_for_database() -> None:
    sql = _sql()
    assert "NO_GO_FOR_DB until M0b" in sql
    assert sql.rstrip().endswith("COMMIT;")


def test_text_search_precondition_uses_real_postgres_catalogs() -> None:
    sql = _sql()
    assert "to_regconfig(" not in sql
    assert "FROM pg_catalog.pg_ts_config AS cfg" in sql
    assert "JOIN pg_catalog.pg_namespace AS ns" in sql
    assert "cfg.cfgname = 'spanish_unaccent'" in sql


def test_pgvector_schema_and_operator_are_explicitly_trusted() -> None:
    sql = _sql()
    assert "ext.extname = 'vector'" in sql
    assert "ns.nspname = 'extensions'" in sql
    assert "query_embedding extensions.vector(1024)" in sql
    assert sql.count("OPERATOR(extensions.<=>)") == 3
    assert "c.embedding <=> query_embedding" not in sql


def test_lexical_rpc_uses_resolvable_deterministic_ordering() -> None:
    body = _function(_sql(), "search_chunks_text_v3")
    assert "ORDER BY rank" not in body
    assert "ORDER BY ts_rank(" in body
    assert ") DESC, c.id ASC" in body


def test_chunks_v2_is_source_shape_and_donor_only_never_mutated() -> None:
    code = _without_comments(_sql())
    forbidden = (
        r"\bINSERT\s+INTO\s+(?:public\.)?chunks_v2\b",
        r"\bUPDATE\s+(?:public\.)?chunks_v2\b",
        r"\bDELETE\s+FROM\s+(?:public\.)?chunks_v2\b",
        r"\bALTER\s+TABLE\s+(?:public\.)?chunks_v2\b",
        r"\bDROP\s+TABLE\s+(?:public\.)?chunks_v2\b",
        r"\bTRUNCATE\s+(?:TABLE\s+)?(?:public\.)?chunks_v2\b",
        r"\bCREATE\s+TABLE\s+(?:public\.)?chunks_v3\s+AS\b",
    )
    for pattern in forbidden:
        assert re.search(pattern, code, re.IGNORECASE) is None
    assert "LIKE public.chunks_v2" in code
    assert "REFERENCES public.chunks_v2(id)" in code


def test_hnsw_is_deferred() -> None:
    code = _without_comments(_sql())
    assert re.search(r"\bUSING\s+hnsw\b", code, re.IGNORECASE) is None
    assert "chunks_v3_search_vector_idx" in code


def test_generation_and_row_identity_constraints_are_present() -> None:
    sql = _sql()
    required = (
        "chunk_materializations_v1_one_active_idx",
        "WHERE state = 'active'",
        "UNIQUE (materialization_id, id)",
        "UNIQUE (materialization_id, extraction_sha256, chunk_index)",
        "FOREIGN KEY (materialization_id, duplicate_of)",
        "DEFERRABLE INITIALLY DEFERRED",
        "duplicate_of IS NULL OR duplicate_of <> id",
        "provenance_contract = 's116_section_lineage_v1'",
        "source_block_end >= source_block_start",
    )
    for fragment in required:
        assert fragment in sql


def test_document_identity_is_exact_unique_and_required() -> None:
    sql = _sql()
    assert "ALTER COLUMN document_id SET NOT NULL" in sql
    assert "d.source_pdf_sha256 !~ '^[0-9a-f]{64}$'" in sql
    assert "d.source_pdf_sha256 IS DISTINCT FROM c.extraction_sha256" in sql
    assert "HAVING count(DISTINCT d.id) <> 1" in sql
    assert "source SHA-256 does not resolve to exactly one document" in sql


def test_enrichment_origin_is_closed_and_legacy_donor_is_bound() -> None:
    sql = _sql()
    assert "context_origin IN ('generated_v3', 'legacy_v2_reuse', 'none')" in sql
    assert "embedding_origin IN ('generated_v3', 'legacy_v2_reuse', 'none')" in sql
    assert "embedding_dimensions = 1024" in sql
    assert "embedding_input_type = 'document'" in sql
    assert "chunks_v3_legacy_donor_fkey" in sql
    assert "FOREIGN KEY (donor_chunk_id)" in sql
    assert "REFERENCES public.chunks_v2(id)" in sql


def test_rows_are_append_only_and_cleanup_is_state_guarded() -> None:
    sql = _sql()
    guard = _function(sql, "protect_chunks_v3_rows_v1")
    assert "IF TG_OP = 'INSERT'" in guard
    assert "WHERE id = NEW.materialization_id" in guard
    assert "FOR SHARE" in guard
    assert "generation_state IS DISTINCT FROM 'loading'" in guard
    assert "chunks_v3 inserts require a loading generation" in guard
    assert "IF TG_OP = 'UPDATE'" in guard
    assert "chunks_v3 rows are append-only" in guard
    assert "generation_state NOT IN ('loading', 'failed')" in guard
    assert "BEFORE INSERT OR UPDATE OR DELETE ON public.chunks_v3" in sql


def test_validate_rpc_checks_counts_documents_and_duplicate_chains() -> None:
    body = _function(_sql(), "validate_chunks_v3_materialization_v1")
    assert "SECURITY DEFINER" in body
    assert "SET search_path = ''" in body
    assert "asserted_rows_manifest_sha256 <> target.rows_manifest_sha256" in body
    assert "document_count <> target.expected_documents" in body
    assert "chunk_count <> target.expected_chunks" in body
    assert "chunk/document exact source identity mismatch" in body
    assert "parent.duplicate_of IS NOT NULL" in body
    assert "SET state = 'validated'" in body


def test_publication_and_discard_are_narrow_serialized_transitions() -> None:
    sql = _sql()
    publish = _function(sql, "publish_chunks_v3_materialization_v1")
    discard = _function(sql, "discard_chunks_v3_materialization_v1")
    for body in (publish, discard):
        assert "SECURITY DEFINER" in body
        assert "SET search_path = ''" in body
        assert "pg_catalog.pg_advisory_xact_lock" in body
    assert "target_state IS DISTINCT FROM 'validated'" in publish
    assert "SET state = 'retired'" in publish
    assert "SET state = 'active'" in publish
    assert "IF NOT FOUND OR target_state NOT IN ('loading', 'failed')" in discard
    assert "DELETE FROM public.chunks_v3" in discard


def test_publisher_role_is_non_login_and_cannot_bypass_rls() -> None:
    sql = _sql()
    declaration = re.search(
        r"CREATE ROLE technical_bot_chunks_v3_publisher(?P<body>.*?);",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert declaration is not None
    body = declaration.group("body")
    for attribute in (
        "NOLOGIN",
        "NOINHERIT",
        "NOSUPERUSER",
        "NOCREATEDB",
        "NOCREATEROLE",
        "NOREPLICATION",
        "NOBYPASSRLS",
    ):
        assert attribute in body


def test_rls_and_explicit_default_grant_revocation_cover_both_tables() -> None:
    sql = _sql()
    for table in ("chunk_materializations_v1", "chunks_v3"):
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in sql
        revoke = re.search(
            rf"REVOKE ALL ON TABLE public\.{table} FROM (?P<roles>.*?);",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        assert revoke is not None
        roles = revoke.group("roles")
        for role in ("PUBLIC", "anon", "authenticated", "service_role"):
            assert role in roles


def test_transition_functions_are_owned_by_publisher_and_not_public() -> None:
    sql = _sql()
    signatures = (
        "validate_chunks_v3_materialization_v1(UUID, TEXT)",
        "publish_chunks_v3_materialization_v1(UUID)",
        "discard_chunks_v3_materialization_v1(UUID)",
    )
    for signature in signatures:
        assert (
            f"ALTER FUNCTION public.{signature}\n"
            "    OWNER TO technical_bot_chunks_v3_publisher;"
        ) in sql
        revoke = re.search(
            rf"REVOKE ALL ON FUNCTION public\.{re.escape(signature)} FROM (?P<roles>.*?);",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        assert revoke is not None
        for role in ("PUBLIC", "anon", "authenticated", "service_role"):
            assert role in revoke.group("roles")
        assert f"GRANT EXECUTE ON FUNCTION public.{signature} TO service_role;" in sql


def test_publisher_has_only_required_document_read_and_temporary_schema_create() -> None:
    sql = _sql()
    assert (
        "GRANT SELECT (id, source_pdf_sha256) ON TABLE public.documents\n"
        "    TO technical_bot_chunks_v3_publisher;"
    ) in sql
    grant_position = sql.index(
        "GRANT CREATE ON SCHEMA public TO technical_bot_chunks_v3_publisher;"
    )
    ownership_position = sql.index(
        "ALTER FUNCTION public.validate_chunks_v3_materialization_v1(UUID, TEXT)"
    )
    revoke_position = sql.index(
        "REVOKE CREATE ON SCHEMA public FROM technical_bot_chunks_v3_publisher;"
    )
    assert grant_position < ownership_position < revoke_position


def test_service_role_has_insert_select_but_no_direct_update_or_delete() -> None:
    code = _without_comments(_sql())
    assert "GRANT SELECT ON TABLE public.chunk_materializations_v1 TO service_role" in code
    assert re.search(
        r"GRANT INSERT\s*\(.*?\)\s*ON TABLE public\.chunk_materializations_v1 TO service_role;",
        code,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert "GRANT SELECT, INSERT ON TABLE public.chunks_v3 TO service_role" in code
    direct_mutation = re.search(
        r"GRANT\s+[^;]*(?:UPDATE|DELETE)[^;]*\bON\s+TABLE\b[^;]*\bTO\s+service_role\s*;",
        code,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert direct_mutation is None


def test_retrieval_functions_are_security_invoker_and_active_by_default() -> None:
    sql = _sql()
    for name in ("match_chunks_v3", "search_chunks_text_v3"):
        body = _function(sql, name)
        assert "SECURITY INVOKER" in body
        assert "SET search_path = ''" in body
        assert "WHERE m.state = 'active'" in body
        assert "c.duplicate_of IS NULL" in body


def test_rollback_header_only_names_v3_objects_and_publisher_role() -> None:
    header = _sql().split("BEGIN;", 1)[0]
    assert "DROP TABLE public.chunks_v2" not in header
    assert "ALTER TABLE public.chunks_v2" not in header
    assert "REVOKE SELECT (id, source_pdf_sha256) ON public.documents" in header
    assert "REVOKE USAGE ON SCHEMA public FROM technical_bot_chunks_v3_publisher" in header
    assert header.index("REVOKE USAGE ON SCHEMA") < header.index(
        "DROP ROLE technical_bot_chunks_v3_publisher"
    )
    for object_name in (
        "chunks_v3",
        "chunk_materializations_v1",
        "technical_bot_chunks_v3_publisher",
    ):
        assert object_name in header
