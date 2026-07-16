from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "evals/s117_m27_common_retrieval_policy_contract_v1.sql"


def _sql() -> str:
    return SPEC.read_text(encoding="utf-8")


def _function(sql: str, name: str) -> str:
    match = re.search(
        rf"CREATE OR REPLACE FUNCTION public\.{name}\(.*?\$function\$(.*?)\$function\$;",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, name
    return match.group(0)


def test_spec_is_explicitly_static_and_has_no_approximate_vector_index():
    sql = _sql()
    assert "NO_GO_FOR_DB / NO MIGRATION / DO NOT APPLY" in sql
    assert "hnsw" not in sql.casefold()
    assert "target_materialization_id" not in sql


def test_policy_and_canonicality_contract_is_not_false_equivalence():
    sql = _sql()
    assert "retrieval_policy_class = 'eligible' AND duplicate_of IS NULL" in sql
    assert "retrieval_policy_class <> 'eligible' OR duplicate_of IS NULL" in sql
    assert "retrieval_policy_class <> 'duplicate' OR duplicate_of IS NOT NULL" in sql
    assert "register_only" in sql and "unsupported_language" in sql


def test_security_invoker_view_is_common_logical_source():
    sql = _sql()
    assert "WITH (security_invoker = true)" in sql
    assert "JOIN public.chunk_materializations_v1 AS m" in sql
    assert "m.state = 'active'" in sql
    assert "JOIN public.documents AS d" in sql
    assert "d.source_pdf_sha256 = c.extraction_sha256" in sql
    assert "d.status = 'active'" in sql
    for name in ("match_chunks_v3", "search_chunks_text_v3"):
        body = _function(sql, name)
        assert "public.chunks_v3_retrieval_eligible_v1" in body
        assert "FROM public.chunks_v3 AS" not in body
        assert "chunk_materializations_v1" not in body
        assert "public.documents" not in body


def test_both_channels_share_fail_closed_limits_filters_and_codes():
    sql = _sql()
    vector = _function(sql, "match_chunks_v3")
    fts = _function(sql, "search_chunks_text_v3")
    for body in (vector, fts):
        assert "M27_INVALID_LIMIT" in body
        assert "> 200" in body
        assert "M27_INVALID_FILTER" in body
        assert "btrim(filter_product)" in body
        assert "btrim(filter_category)" in body
        assert "btrim(filter_manufacturer)" in body
        assert "ERRCODE = '22023'" in body
        assert "normalized_product IS NULL OR" in body
        assert "normalized_category IS NULL OR" in body
        assert "normalized_manufacturer IS NULL OR" in body
    assert "M27_INVALID_THRESHOLD" in vector
    assert "match_threshold < -1.0" in vector
    assert "match_threshold > 1.0" in vector
    assert "match_threshold = 'NaN'" in vector
    assert "query_embedding IS NULL" in vector
    assert "search_query IS NULL OR btrim(search_query) = ''" in fts


def test_fts_parses_query_once_and_has_static_partial_gin():
    sql = _sql()
    fts = _function(sql, "search_chunks_text_v3")
    assert fts.count("plainto_tsquery") == 1
    assert "numnode(parsed_query) = 0" in fts
    assert "v.search_vector @@ parsed_query" in fts
    assert re.search(
        r"USING gin \(search_vector\)\s+WHERE retrieval_eligible AND duplicate_of IS NULL",
        sql,
    )


def test_grants_remove_shadow_table_broad_select_and_freeze_rls_assumption():
    sql = _sql()
    assert "REVOKE SELECT ON TABLE public.chunks_v3 FROM service_role" in sql
    assert "REVOKE SELECT ON TABLE public.chunk_materializations_v1 FROM service_role" in sql
    assert "GRANT SELECT (\n    id, content" in sql
    assert "GRANT SELECT (id, state)" in sql
    assert "rolname = 'service_role' AND rolbypassrls" in sql
    assert "M27_SERVICE_ROLE_RLS_CONTRACT" in sql
    assert "REVOKE ALL ON TABLE public.chunks_v3_retrieval_eligible_v1" in sql
    assert "FROM PUBLIC, anon, authenticated, service_role" in sql
