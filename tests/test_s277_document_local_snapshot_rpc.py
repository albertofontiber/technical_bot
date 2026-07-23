from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INITIAL_MIGRATION = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260721210847_s277_document_local_snapshot_rpc.sql"
)
MIGRATION = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260721220110_s277_document_local_exact_blob_authority.sql"
)


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _function_body(sql: str) -> str:
    match = re.search(r"AS \$function\$(.*?)\$function\$;", sql, re.DOTALL)
    assert match is not None
    return match.group(1)


def test_snapshot_rpc_is_stable_invoker_only_and_get_safe() -> None:
    sql = _sql()
    assert "LANGUAGE sql\nSTABLE\nSECURITY INVOKER" in sql
    assert "SET search_path = ''" in sql
    assert "SET statement_timeout" not in sql
    assert "SECURITY DEFINER" not in sql
    assert (
        "REVOKE ALL ON FUNCTION public.document_local_snapshot_v1(\n"
        "    JSONB, TEXT, INTEGER, INTEGER\n"
        ") FROM PUBLIC;"
    ) in sql
    assert ") FROM anon, authenticated;" in sql
    assert ") TO service_role;" in sql

    body = _function_body(sql)
    for statement in ("INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE", "EXECUTE"):
        assert re.search(rf"\b{statement}\b", body, re.IGNORECASE) is None


def test_snapshot_rpc_reads_complete_family_and_chunks_in_one_statement() -> None:
    body = _function_body(_sql())
    assert "WITH RECURSIVE" in body
    assert "JOIN LATERAL (" in body
    assert "FROM public.documents AS candidate" in body
    assert body.count("JOIN LATERAL (") == 2
    assert "FROM public.chunks_v2 AS chunk" in body
    assert "candidate.document_family" in body
    assert "candidate.language IS NOT DISTINCT FROM seed.language" in body
    assert "candidate.manufacturer IS NOT DISTINCT FROM seed.manufacturer" in body
    assert "LIMIT family_limit + 1" in body
    assert "family.doc_type IS DISTINCT FROM seed.doc_type" in body
    assert "family.product_model IS DISTINCT FROM seed.product_model" in body
    assert "stats.active_count <> 1" in body
    assert "stats.root_count <> 1" in body
    assert "walked.walked_count" in body
    assert "nonreciprocal_revision_chain" in body
    assert "disconnected_revision_family" not in body


def test_snapshot_rpc_enforces_exact_blob_language_and_sentinels() -> None:
    body = _function_body(_sql())
    assert "pg_catalog.lower(seed.language) = 'es'" in body
    assert "pg_catalog.lower(chunk.extraction_sha256)" in body
    assert "chunk.source_file = authority.source_file" in body
    assert "chunk.duplicate_of IS NULL" in body
    for stale_denormalized_guard in (
        "chunk.language IS NOT DISTINCT FROM authority.language",
        "chunk.doc_type IS NOT DISTINCT FROM authority.doc_type",
        "chunk.manufacturer IS NOT DISTINCT FROM authority.manufacturer",
        "chunk.product_model IS NOT DISTINCT FROM authority.product_model",
    ):
        assert stale_denormalized_guard not in body
    assert "candidate_limit BETWEEN 1 AND 64" in body
    assert "family_limit BETWEEN 1 AND 32" in body
    assert "LIMIT candidate_limit + 1" in body
    assert "snapshot_candidate_rank <= candidate_limit + 1" in body
    assert "stats.family_count > family_limit" in body
    assert "fts_query ~ '^[a-z0-9()&|]+$'" in body
    assert "pg_catalog.pg_input_is_valid(" in body
    assert "'public.spanish_unaccent'::pg_catalog.regconfig" in body


def test_snapshot_rpc_returns_revalidatable_bounded_receipt() -> None:
    body = _function_body(_sql())
    for field in (
        "'schema', 'document_local_snapshot_v1'",
        "'authorities'",
        "'document_rows'",
        "'candidates'",
        "'rejections'",
        "'family_rows_read'",
        "'candidate_rows'",
        "'candidate_overflow_scopes'",
        "'scope_rank'",
        "'family_rows'",
    ):
        assert field in body
    assert (
        "DROP FUNCTION IF EXISTS public.document_local_snapshot_v1"
        in INITIAL_MIGRATION.read_text(encoding="utf-8")
    )
    assert "re-apply the CREATE OR REPLACE FUNCTION body" in _sql()
