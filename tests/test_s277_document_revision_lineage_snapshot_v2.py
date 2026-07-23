from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260722013000_s277_document_revision_lineage_snapshot_v2.sql"
)


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _normalised_sql() -> str:
    return " ".join(_sql().split())


def _function_body() -> str:
    match = re.search(
        r"CREATE OR REPLACE FUNCTION public\.document_local_snapshot_v2\(.*?"
        r"AS \$function\$(.*?)\$function\$;",
        _sql(),
        re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def _cte(body: str, name: str, next_name: str) -> str:
    match = re.search(
        rf"\b{name}\s+AS\s*\((.*?)\n\),\n{next_name}\s+AS\s*\(",
        body,
        re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def test_migration_is_additive_and_preserves_deployed_v1() -> None:
    sql = _sql()
    assert "CREATE OR REPLACE FUNCTION public.document_local_snapshot_v2(" in sql
    assert "CREATE OR REPLACE FUNCTION public.document_local_snapshot_v1(" not in sql
    assert "DROP FUNCTION" not in sql
    assert "DROP TABLE" not in sql
    assert "DROP COLUMN" not in sql
    assert "ALTER TABLE public.documents\n    ADD COLUMN revision_lineage_id UUID NULL;" in sql


def test_lineage_registry_is_explicit_governed_and_not_publicly_readable() -> None:
    sql = _sql()
    normalised = _normalised_sql()
    assert "CREATE TABLE public.document_revision_lineages" in sql
    assert "id UUID PRIMARY KEY" in sql
    assert "authority_status IN ('verified', 'needs_review')" in sql
    assert "authority_evidence_sha256 ~ '^[0-9a-f]{64}$'" in sql
    assert (
        "ALTER TABLE public.document_revision_lineages ENABLE ROW LEVEL SECURITY;"
        in sql
    )
    assert "REVOKE ALL ON TABLE public.document_revision_lineages FROM PUBLIC;" in sql
    assert (
        "REVOKE ALL ON TABLE public.document_revision_lineages "
        "FROM anon, authenticated;"
    ) in normalised
    assert "GRANT SELECT ON TABLE public.document_revision_lineages TO service_role;" in sql
    assert "REFERENCES public.document_revision_lineages(id) ON DELETE RESTRICT" in normalised


def test_only_exact_preconditioned_hp011_documents_are_bound() -> None:
    sql = _sql()
    for exact_value in (
        "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429",
        "e98e05ff-ee1d-5341-869a-65768855dae9",
        "494e71be-873b-48c1-adb3-a21a122da111",
        "ccabe3df906990c9b95d0d180d811e0444278089d4ce30678d86948cb197e93e",
        "914ceacf8395729f73876cb9e397a8cb3154d70ba67903b6e055f2b4398be573",
        "HLSI-MN-103_RP1r-Supra_lr",
        "DATE '2013-11-01'",
        "DATE '2018-05-01'",
    ):
        assert exact_value in sql
    assert "document.status = 'superseded'" in sql
    assert "document.status = 'active'" in sql
    assert "document.superseded_by_id = active_document" in sql
    assert "document.supersedes_id = old_document" in sql
    assert sql.count("document.revision_lineage_id IS NULL") >= 3
    assert "IF changed <> 2" in sql
    assert "HP011 lineage bind postcondition failed" in sql


def test_database_prevents_two_active_rows_in_one_explicit_lineage() -> None:
    normalised = _normalised_sql()
    assert (
        "CREATE UNIQUE INDEX uq_documents_one_active_per_revision_lineage "
        "ON public.documents(revision_lineage_id) "
        "WHERE revision_lineage_id IS NOT NULL AND status = 'active';"
    ) in normalised
    assert (
        "CREATE INDEX idx_documents_revision_lineage_id "
        "ON public.documents(revision_lineage_id);"
    ) in normalised


def test_v2_positive_membership_uses_only_exact_lineage_uuid() -> None:
    family = _cte(_function_body(), "family_rows", "family_stats")
    normalised = " ".join(family.split())
    assert "candidate.revision_lineage_id = seed.revision_lineage_id" in normalised
    assert "seed.lineage_authority_status = 'verified'" in normalised
    assert "seed.revision_lineage_id IS NOT NULL" in normalised

    # Descriptive legacy labels may reject a bound lineage later as a negative
    # consistency check, but they must never add or omit members.
    for forbidden_membership in (
        "candidate.document_family IS NOT DISTINCT FROM seed.document_family",
        "candidate.language IS NOT DISTINCT FROM seed.language",
        "candidate.manufacturer IS NOT DISTINCT FROM seed.manufacturer",
        "lower(candidate.document_family)",
        "unaccent(candidate.document_family)",
        "similarity(candidate.document_family",
    ):
        assert forbidden_membership.casefold() not in normalised.casefold()


def test_v2_fails_closed_for_null_unverified_or_drifted_lineage() -> None:
    body = _function_body()
    assert "seed.revision_lineage_id IS NULL" in body
    assert "seed.lineage_authority_status IS DISTINCT FROM 'verified'" in body
    assert "THEN 'unverified_document_lineage'" in body
    assert "THEN 'lineage_identity_drift'" in body
    assert "family.revision_lineage_id\n                    IS DISTINCT FROM seed.revision_lineage_id" in body


def test_v2_revalidates_the_complete_bounded_lifecycle_graph() -> None:
    body = _function_body()
    for contract in (
        "LIMIT family_limit + 1",
        "stats.family_count > family_limit",
        "stats.active_count <> 1",
        "stats.root_count <> 1",
        "family.status NOT IN ('active', 'superseded')",
        "older.superseded_by_id = family.id",
        "newer.supersedes_id = family.id",
        "NOT newer.id = ANY(walk.path)",
        "walked.walked_count",
        "'ambiguous_active_revision'",
        "'branched_or_cyclic_revision_chain'",
        "'nonreciprocal_revision_chain'",
        "'incomplete_revision_chain'",
    ):
        assert contract in body


def test_v2_keeps_exact_active_blob_and_candidate_authority() -> None:
    body = _function_body()
    for contract in (
        "seed.status <> 'active'",
        "seed.superseded_by_id IS NOT NULL",
        "seed.anchor_extraction_sha256",
        "seed.anchor_source_file",
        "'active_revision_not_bound_to_anchor_blob'",
        "chunk.document_id = authority.document_id",
        "pg_catalog.lower(chunk.extraction_sha256)",
        "chunk.source_file = authority.source_file",
        "chunk.duplicate_of IS NULL",
        "'public.spanish_unaccent'::pg_catalog.regconfig",
        "LIMIT candidate_limit + 1",
        "snapshot_candidate_rank <= candidate_limit + 1",
    ):
        assert contract in body


def test_v2_request_bounds_and_payload_are_revalidatable() -> None:
    body = _function_body()
    for contract in (
        "jsonb_array_length(anchor_scopes) BETWEEN 1 AND 2",
        "family_limit BETWEEN 1 AND 32",
        "candidate_limit BETWEEN 1 AND 64",
        "pg_catalog.length(fts_query) BETWEEN 1 AND 480",
        "fts_query ~ '^[a-z0-9()&|]+$'",
        "pg_catalog.pg_input_is_valid(",
        "'schema', 'document_local_snapshot_v2'",
        "'revision_lineage_id', authority.revision_lineage_id",
        "'document_rows'",
        "'candidates'",
        "'rejections'",
        "'family_rows_read'",
        "'candidate_rows'",
        "'candidate_overflow_scopes'",
        "authority.revision_lineage_id AS document_revision_lineage_id",
    ):
        assert contract in body


def test_v2_rpc_is_read_only_stable_invoker_and_service_role_only() -> None:
    sql = _sql()
    body = _function_body()
    assert "LANGUAGE sql\nSTABLE\nSECURITY INVOKER" in sql
    assert "SET search_path = ''" in sql
    assert "SECURITY DEFINER" not in sql
    assert (
        "REVOKE ALL ON FUNCTION public.document_local_snapshot_v2(\n"
        "    JSONB, TEXT, INTEGER, INTEGER\n"
        ") FROM PUBLIC;"
    ) in sql
    assert ") FROM anon, authenticated;" in sql
    assert ") TO service_role;" in sql
    for statement in ("INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE", "EXECUTE"):
        assert re.search(rf"\b{statement}\b", body, re.IGNORECASE) is None
    assert "NOTIFY pgrst, 'reload schema';" in sql
