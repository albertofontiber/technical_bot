\set ON_ERROR_STOP on

-- Disposable M0b rollback only.  This intentionally removes both the S131
-- binding layer and its S117 shadow antecedent, while preserving chunks_v2,
-- documents, text-search configuration, and the local extension fixture.
BEGIN;

DO $precondition$
BEGIN
    IF pg_catalog.current_database() <> 's131_m0b' THEN
        RAISE EXCEPTION 'S131 M0b rollback is restricted to s131_m0b';
    END IF;
END
$precondition$;

DROP FUNCTION public.search_chunks_v3_shadow_text_v2(
    UUID, TEXT, TEXT, TEXT, TEXT, TEXT, INTEGER
);
DROP VIEW public.chunks_v3_shadow_retrieval_eligible_v2;
DROP FUNCTION public.validate_chunks_v3_shadow_v2(UUID, TEXT, TEXT);
DROP FUNCTION public.discard_chunks_v3_shadow_v2(UUID);

DROP POLICY documents_s131_shadow_rpc_select ON public.documents;
DROP POLICY documents_s131_publisher_bound_select ON public.documents;

DROP TABLE public.chunks_v3;
DROP TABLE public.chunk_document_bindings_v1;
DROP TABLE public.chunk_materializations_v1;

DROP FUNCTION public.protect_chunk_document_bindings_v1();
DROP FUNCTION public.protect_chunks_v3_rows_v1();
DROP FUNCTION public.update_chunks_v3_search_vector_v1();

REVOKE ALL ON TABLE public.documents FROM
    technical_bot_chunks_v3_publisher,
    technical_bot_chunks_v3_shadow_rpc_owner;
REVOKE ALL ON SCHEMA public FROM
    technical_bot_chunks_v3_publisher,
    technical_bot_chunks_v3_shadow_loader,
    technical_bot_chunks_v3_shadow_rpc_owner,
    technical_bot_chunks_v3_shadow_runner;

DROP ROLE technical_bot_chunks_v3_shadow_runner;
DROP ROLE technical_bot_chunks_v3_shadow_rpc_owner;
DROP ROLE technical_bot_chunks_v3_shadow_loader;
DROP ROLE technical_bot_chunks_v3_publisher;

-- Every document in this disposable fixture was inserted by the M0b loader.
-- DELETE keeps the preserved chunks_v2 -> documents FK explicit; CASCADE is
-- deliberately forbidden in this rollback proof.
DELETE FROM public.documents;

DO $postcondition$
DECLARE
    residual_count INTEGER;
BEGIN
    IF to_regclass('public.chunks_v3') IS NOT NULL
       OR to_regclass('public.chunk_document_bindings_v1') IS NOT NULL
       OR to_regclass('public.chunk_materializations_v1') IS NOT NULL
       OR to_regclass('public.chunks_v3_shadow_retrieval_eligible_v2') IS NOT NULL THEN
        RAISE EXCEPTION 'S131/S117 relation residue after rollback';
    END IF;
    SELECT count(*) INTO residual_count
    FROM pg_catalog.pg_proc AS p
    JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN (
          'search_chunks_v3_shadow_text_v2',
          'validate_chunks_v3_shadow_v2',
          'discard_chunks_v3_shadow_v2',
          'protect_chunk_document_bindings_v1',
          'protect_chunks_v3_rows_v1',
          'update_chunks_v3_search_vector_v1',
          'match_chunks_v3',
          'search_chunks_text_v3',
          'publish_chunks_v3_materialization_v1',
          'validate_chunks_v3_materialization_v1',
          'discard_chunks_v3_materialization_v1'
      );
    IF residual_count <> 0 THEN
        RAISE EXCEPTION 'S131/S117 function residue after rollback';
    END IF;
    SELECT count(*) INTO residual_count
    FROM pg_catalog.pg_roles
    WHERE rolname IN (
        'technical_bot_chunks_v3_publisher',
        'technical_bot_chunks_v3_shadow_loader',
        'technical_bot_chunks_v3_shadow_rpc_owner',
        'technical_bot_chunks_v3_shadow_runner'
    );
    IF residual_count <> 0 THEN
        RAISE EXCEPTION 'S131/S117 role residue after rollback';
    END IF;
    SELECT count(*) INTO residual_count
    FROM pg_catalog.pg_policies
    WHERE policyname LIKE '%s131%'
       OR policyname LIKE '%chunks_v3%';
    IF residual_count <> 0 THEN
        RAISE EXCEPTION 'S131/S117 policy residue after rollback';
    END IF;
    IF to_regclass('public.chunks_v2') IS NULL
       OR to_regclass('public.documents') IS NULL THEN
        RAISE EXCEPTION 'rollback damaged the preserved antecedent tables';
    END IF;
    IF EXISTS (SELECT 1 FROM public.documents) THEN
        RAISE EXCEPTION 'disposable M0b document fixture residue after rollback';
    END IF;
END
$postcondition$;

COMMIT;
