from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "supabase/migrations/20260716120000_chunks_v3_shadow_binding_v2.sql"
SQL = SQL_PATH.read_text(encoding="utf-8")


def _function(name: str) -> str:
    match = re.search(
        rf"CREATE FUNCTION public\.{re.escape(name)}\s*\(.*?\)\s*RETURNS.*?AS \$function\$(.*?)\$function\$;",
        SQL,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, name
    return match.group(0)


def _view() -> str:
    start = SQL.index("CREATE VIEW public.chunks_v3_shadow_retrieval_eligible_v2")
    end = SQL.index("CREATE FUNCTION public.search_chunks_v3_shadow_text_v2", start)
    return SQL[start:end]


def test_contract_is_static_and_composes_exact_antecedent() -> None:
    assert "S131 STATIC SHADOW CONTRACT ONLY" in SQL
    assert "NO_GO_FOR_DB / DO NOT APPLY" in SQL
    assert "20260714102428_chunks_v3_provenance_shadow.sql" in SQL
    assert "ceb88cab7db9caa889f3516fdffcb64d28521e056cae6a7c55c1719230f77614" in SQL
    assert "S131 requires an empty disposable S117 shadow antecedent" in SQL
    assert SQL.strip().endswith("COMMIT;")


def test_inherited_active_serving_routes_are_removed() -> None:
    for name in (
        "match_chunks_v3",
        "search_chunks_text_v3",
        "publish_chunks_v3_materialization_v1",
        "validate_chunks_v3_materialization_v1",
        "discard_chunks_v3_materialization_v1",
    ):
        assert re.search(rf"DROP FUNCTION public\.{name}\s*\(", SQL)
    assert "REVOKE ALL ON TABLE public.chunk_materializations_v1 FROM service_role" in SQL
    assert "REVOKE ALL ON TABLE public.chunks_v3 FROM service_role" in SQL
    assert "extensions.vector, DOUBLE PRECISION" in SQL
    assert not re.search(r"m\.state\s*=\s*'active'", SQL)
    assert not re.search(r"WHERE\s+state\s*=\s*'active'", SQL)


def test_shadow_roles_are_nologin_and_runner_is_not_owner() -> None:
    for role in (
        "technical_bot_chunks_v3_shadow_loader",
        "technical_bot_chunks_v3_shadow_rpc_owner",
        "technical_bot_chunks_v3_shadow_runner",
    ):
        assert re.search(
            rf"CREATE ROLE {role}\s+NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE\s+NOREPLICATION NOBYPASSRLS;",
            SQL,
        )
    assert "OWNER TO technical_bot_chunks_v3_shadow_rpc_owner" in SQL
    assert "OWNER TO technical_bot_chunks_v3_shadow_runner" not in SQL
    assert re.search(
        r"GRANT CREATE ON SCHEMA public TO.*?shadow_rpc_owner;.*?REVOKE CREATE ON SCHEMA public FROM.*?shadow_rpc_owner;",
        SQL,
        re.DOTALL,
    )


def test_generation_registry_freezes_exact_arm_identities_and_binding_taxonomy() -> None:
    exact_values = (
        "eb426a33-91cb-543e-a0c9-fd615dbc36cb",
        "3040da3ace4e033f6bc52e3cf092e2427262d91729ecb67fe7a104a71cbd73a1",
        "68e87fd43702fcf53f14ff7fbdbe65e4faa346977a199ff7427333b8cab950f3",
        "951c6a7615045d770574404cf664385b741bd0097abeebed6a0b6bc1f410f2c1",
        "1852e61c-ac7f-5232-be1c-627ea54f29b5",
        "f702ddcf3d51a479fff90c95f1ccd6206680da4a262462f80a74b10c1b3c1089",
        "cdfcbae0cf476bf74cad9712b5a3f32433a9ea73662116e468ec27522c5cbb63",
        "aa870ab8a484700656252d0315808ee69076a57edfa5d4c0c128e2dd54a13746",
    )
    for value in exact_values:
        assert value in SQL
    for column in (
        "expected_bindings INTEGER NOT NULL",
        "bindings_manifest_sha256 TEXT NOT NULL",
        "expected_binding_counts JSONB NOT NULL",
        "expected_partition_counts JSONB NOT NULL",
    ):
        assert column in SQL
    assert "expected_documents = 1068" in SQL
    assert "expected_bindings = 1068" in SQL
    assert "expected_chunks = 31212" in SQL
    assert "expected_chunks = 31226" in SQL
    for status, count in (
        ("bound_active_physical_sha_verified", 405),
        ("bound_active_legacy_snapshot_only", 597),
        ("bound_nonactive_legacy_snapshot", 8),
        ("unbound_snapshot_empty_document", 8),
        ("unbound_absent_from_snapshot", 50),
    ):
        assert f"'{status}', {count}" in SQL
    for value in (998, 932, 70):
        assert str(value) in SQL


def test_binding_table_commits_all_identity_namespaces_and_truth_table() -> None:
    table = SQL[SQL.index("CREATE TABLE public.chunk_document_bindings_v1"):]
    for column in (
        "extraction_sha256",
        "raw_artifact_sha256",
        "document_id",
        "binding_status",
        "binding_authority",
        "document_status_at_snapshot",
        "source_pdf_identity",
        "source_pdf_identity_status",
        "evaluation_partition",
        "snapshot_binding_ledger_sha256",
        "heldout_manifest_sha256",
        "binding_receipt_sha256",
    ):
        assert column in table
    assert "source_pdf_identity = extraction_sha256" in table
    assert "document_id IS NULL" in table
    assert "document_id IS NOT NULL" in table
    assert "document_status_at_snapshot IN ('needs_review', 'superseded')" in table
    assert "chunk_document_bindings_v1_pdf_identity_shape_chk" in table
    assert "source_pdf_identity ~ '^[0-9a-f]{64}$'" in table
    assert "source_pdf_identity ~ '^backfill:[0-9a-f]{64}$'" in table
    assert "retrieval_binding_eligible BOOLEAN GENERATED ALWAYS AS" in table


def test_chunks_require_binding_and_keep_policy_separate() -> None:
    assert "ALTER TABLE public.chunks_v3 ALTER COLUMN document_id DROP NOT NULL" in SQL
    assert "ADD CONSTRAINT chunks_v3_s131_binding_fkey" in SQL
    assert "REFERENCES public.chunk_document_bindings_v1" in SQL
    assert "retrieval_policy_class TEXT NOT NULL" in SQL
    assert "retrieval_policy_receipt_sha256 TEXT NOT NULL" in SQL
    assert "retrieval_eligible BOOLEAN GENERATED ALWAYS AS" in SQL


def test_validator_is_definer_closed_and_checks_every_relational_bridge() -> None:
    body = _function("validate_chunks_v3_shadow_v2")
    assert "SECURITY DEFINER" in body
    assert "SET search_path = ''" in body
    for fragment in (
        "target.expected_bindings <> 1068",
        "target.expected_chunks NOT IN (31212, 31226)",
        "asserted_rows_manifest_sha256 IS DISTINCT FROM target.rows_manifest_sha256",
        "asserted_bindings_manifest_sha256 IS DISTINCT FROM target.bindings_manifest_sha256",
        "observed_binding_counts IS DISTINCT FROM target.expected_binding_counts",
        "observed_partition_counts IS DISTINCT FROM target.expected_partition_counts",
        "c.document_id IS DISTINCT FROM b.document_id",
        "c.raw_artifact_sha256 IS DISTINCT FROM b.raw_artifact_sha256",
        "d.status IS DISTINCT FROM b.document_status_at_snapshot",
        "d.source_pdf_sha256 IS DISTINCT FROM b.source_pdf_identity",
        "NOT b.retrieval_binding_eligible",
        "c.retrieval_policy_class = 'eligible'",
        "S131 ineligible binding marked for retrieval",
    ):
        assert fragment in body
    assert "d.source_pdf_sha256 IS DISTINCT FROM c.extraction_sha256" not in body


def test_view_has_exact_binding_document_and_policy_conjunction() -> None:
    view = _view()
    assert "WITH (security_invoker = true)" in view
    for fragment in (
        "m.state = 'validated'",
        "b.document_status_at_snapshot = 'active'",
        "d.status = 'active'",
        "d.source_pdf_sha256 IS NOT DISTINCT FROM b.source_pdf_identity",
        "c.document_id IS NOT DISTINCT FROM b.document_id",
        "c.raw_artifact_sha256 = b.raw_artifact_sha256",
        "c.retrieval_policy_class = 'eligible'",
        "c.retrieval_policy_receipt_sha256 IS NOT NULL",
        "c.duplicate_of IS NULL",
    ):
        assert fragment in view


def test_shadow_rpc_has_no_defaults_fallback_or_dynamic_sql() -> None:
    body = _function("search_chunks_v3_shadow_text_v2")
    signature = body[: body.index("RETURNS TABLE")]
    assert "DEFAULT" not in signature
    assert "SECURITY DEFINER" in body
    assert "SET search_path = ''" in body
    assert "target_materialization_id IS NULL" in body
    assert "target_evaluation_partition NOT IN ('development', 'heldout_s130')" in body
    assert "m.state = 'validated'" in body
    for frozen_hash in (
        "3040da3ace4e033f6bc52e3cf092e2427262d91729ecb67fe7a104a71cbd73a1",
        "951c6a7615045d770574404cf664385b741bd0097abeebed6a0b6bc1f410f2c1",
        "f702ddcf3d51a479fff90c95f1ccd6206680da4a262462f80a74b10c1b3c1089",
        "aa870ab8a484700656252d0315808ee69076a57edfa5d4c0c128e2dd54a13746",
    ):
        assert frozen_hash in body
    assert "v.materialization_id = target_materialization_id" in body
    assert "v.evaluation_partition = target_evaluation_partition" in body
    assert "ORDER BY pg_catalog.ts_rank(" in body
    assert ") DESC, v.id ASC" in body
    assert "ORDER BY rank" not in body
    assert "EXECUTE format" not in body
    assert "active'" not in signature


def test_runner_has_only_schema_usage_and_rpc_execute() -> None:
    runner = "technical_bot_chunks_v3_shadow_runner"
    assert re.search(rf"GRANT USAGE ON SCHEMA public TO.*?{runner};", SQL, re.DOTALL)
    assert re.search(
        rf"GRANT EXECUTE ON FUNCTION public\.search_chunks_v3_shadow_text_v2\(.*?\) TO {runner};",
        SQL,
        re.DOTALL,
    )
    grant_statements = re.findall(r"(?ims)^\s*GRANT\b.*?;", SQL)
    runner_grants = [statement for statement in grant_statements if runner in statement]
    assert len(runner_grants) == 2
    assert not any(re.search(r"\b(?:SELECT|INSERT|UPDATE|DELETE)\b", statement) for statement in runner_grants)
    assert not any(re.search(r"\bON\s+TABLE\b", statement) for statement in runner_grants)


def test_api_roles_are_denied_every_s131_object_and_rpc() -> None:
    for role in ("PUBLIC", "anon", "authenticated", "service_role"):
        assert re.search(
            rf"REVOKE ALL ON TABLE public\.chunk_document_bindings_v1.*?{role}",
            SQL,
            re.DOTALL,
        )
        assert re.search(
            rf"REVOKE ALL ON TABLE public\.chunks_v3_shadow_retrieval_eligible_v2.*?{role}",
            SQL,
            re.DOTALL,
        )
        assert re.search(
            rf"REVOKE ALL ON FUNCTION public\.search_chunks_v3_shadow_text_v2\(.*?\).*?{role}",
            SQL,
            re.DOTALL,
        )
    assert not re.search(r"GRANT .* TO service_role", SQL)


def test_rls_covers_loader_internal_owner_and_central_document_join() -> None:
    assert "ALTER TABLE public.chunk_document_bindings_v1 ENABLE ROW LEVEL SECURITY" in SQL
    for policy in (
        "chunk_materializations_v1_s131_loader_insert",
        "chunks_v3_s131_loader_insert",
        "chunk_document_bindings_v1_s131_loader_insert",
        "chunk_document_bindings_v1_s131_publisher_select",
        "chunk_document_bindings_v1_s131_publisher_delete",
        "documents_s131_publisher_bound_select",
        "chunk_materializations_v1_s131_rpc_select",
        "chunks_v3_s131_rpc_select",
        "chunk_document_bindings_v1_s131_rpc_select",
        "documents_s131_shadow_rpc_select",
    ):
        assert f"CREATE POLICY {policy}" in SQL
    assert "FOR SELECT TO technical_bot_chunks_v3_publisher" in SQL
    assert "FOR DELETE TO technical_bot_chunks_v3_publisher" in SQL
    assert re.search(
        r"CREATE POLICY documents_s131_publisher_bound_select.*?"
        r"FROM public\.chunk_document_bindings_v1 AS b.*?b\.document_id = id",
        SQL,
        re.DOTALL,
    )


def test_no_vector_index_or_serving_publish_is_created() -> None:
    assert "USING hnsw" not in SQL.lower()
    assert "CREATE FUNCTION public.match_chunks_v3" not in SQL
    assert "CREATE FUNCTION public.publish_chunks_v3" not in SQL
    assert "NOTIFY pgrst" not in SQL
