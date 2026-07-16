-- S131 STATIC SHADOW CONTRACT ONLY.
-- NO_GO_FOR_DB / DO NOT APPLY outside the separately authorized M0b disposable gate.
-- Composes after 20260714102428_chunks_v3_provenance_shadow.sql.
-- Exact arms frozen by s131_shadow_binding_manifest_gate_v1.yaml, SHA-256
-- ceb88cab7db9caa889f3516fdffcb64d28521e056cae6a7c55c1719230f77614.
-- It never changes chunks_v2 and never exposes chunks_v3 to normal API roles.
--
-- M0b rollback, in reverse dependency order, must remove:
--   search_chunks_v3_shadow_text_v2, the eligible view, S131 policies/triggers,
--   binding FK/policy columns, chunk_document_bindings_v1, S131 registry columns,
--   and the three S131 NOLOGIN roles; it must then prove no residual grants.

BEGIN;

DO $preconditions$
BEGIN
    IF to_regclass('public.chunks_v3') IS NULL
       OR to_regclass('public.chunk_materializations_v1') IS NULL
       OR to_regclass('public.chunks_v2') IS NULL
       OR to_regclass('public.documents') IS NULL THEN
        RAISE EXCEPTION 'S131 requires the exact S117 shadow antecedent';
    END IF;
    IF to_regclass('public.chunk_document_bindings_v1') IS NOT NULL THEN
        RAISE EXCEPTION 'S131 binding table already exists';
    END IF;
    IF EXISTS (SELECT 1 FROM public.chunk_materializations_v1)
       OR EXISTS (SELECT 1 FROM public.chunks_v3) THEN
        RAISE EXCEPTION 'S131 requires an empty disposable S117 shadow antecedent';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname IN (
            'technical_bot_chunks_v3_shadow_loader',
            'technical_bot_chunks_v3_shadow_rpc_owner',
            'technical_bot_chunks_v3_shadow_runner'
        )
    ) THEN
        RAISE EXCEPTION 'S131 role drift';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'chunks_v3'
          AND column_name IN (
              'retrieval_policy_class',
              'retrieval_policy_receipt_sha256',
              'retrieval_eligible'
          )
    ) THEN
        RAISE EXCEPTION 'S131 retrieval policy columns already exist';
    END IF;
END
$preconditions$;

-- Remove every inherited route that could serve a generation selected by
-- state='active'. The antecedent functions are deliberately not retained.
REVOKE ALL ON TABLE public.chunk_materializations_v1 FROM service_role;
REVOKE ALL ON TABLE public.chunks_v3 FROM service_role;
REVOKE ALL ON FUNCTION public.validate_chunks_v3_materialization_v1(UUID, TEXT)
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.publish_chunks_v3_materialization_v1(UUID)
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.discard_chunks_v3_materialization_v1(UUID)
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.match_chunks_v3(
    extensions.vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT, UUID
) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.search_chunks_text_v3(
    TEXT, TEXT, TEXT, TEXT, INTEGER, UUID
) FROM PUBLIC, anon, authenticated, service_role;

DROP FUNCTION public.match_chunks_v3(
    extensions.vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT, UUID
);
DROP FUNCTION public.search_chunks_text_v3(
    TEXT, TEXT, TEXT, TEXT, INTEGER, UUID
);
DROP FUNCTION public.publish_chunks_v3_materialization_v1(UUID);
DROP FUNCTION public.validate_chunks_v3_materialization_v1(UUID, TEXT);
DROP FUNCTION public.discard_chunks_v3_materialization_v1(UUID);

CREATE ROLE technical_bot_chunks_v3_shadow_loader
    NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
CREATE ROLE technical_bot_chunks_v3_shadow_rpc_owner
    NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
CREATE ROLE technical_bot_chunks_v3_shadow_runner
    NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;

-- PostgreSQL requires a prospective function/view owner to hold CREATE on the
-- containing schema. The grants are transaction-local setup and are revoked
-- after ownership transfer; neither role retains object-creation authority.
GRANT CREATE ON SCHEMA public TO
    technical_bot_chunks_v3_publisher,
    technical_bot_chunks_v3_shadow_rpc_owner;

ALTER TABLE public.chunk_materializations_v1
    ADD COLUMN expected_bindings INTEGER NOT NULL,
    ADD COLUMN bindings_manifest_sha256 TEXT NOT NULL,
    ADD COLUMN expected_binding_counts JSONB NOT NULL,
    ADD COLUMN expected_partition_counts JSONB NOT NULL;

ALTER TABLE public.chunk_materializations_v1
    ADD CONSTRAINT chunk_materializations_v1_s131_shadow_manifest_chk CHECK (
        expected_documents = 1068
        AND expected_bindings = 1068
        AND bindings_manifest_sha256 ~ '^[0-9a-f]{64}$'
        AND (
            (
                id = 'eb426a33-91cb-543e-a0c9-fd615dbc36cb'::UUID
                AND manifest_sha256 =
                    '3040da3ace4e033f6bc52e3cf092e2427262d91729ecb67fe7a104a71cbd73a1'
                AND rows_manifest_sha256 =
                    '68e87fd43702fcf53f14ff7fbdbe65e4faa346977a199ff7427333b8cab950f3'
                AND bindings_manifest_sha256 =
                    '951c6a7615045d770574404cf664385b741bd0097abeebed6a0b6bc1f410f2c1'
                AND expected_chunks = 31212
            )
            OR (
                id = '1852e61c-ac7f-5232-be1c-627ea54f29b5'::UUID
                AND manifest_sha256 =
                    'f702ddcf3d51a479fff90c95f1ccd6206680da4a262462f80a74b10c1b3c1089'
                AND rows_manifest_sha256 =
                    'cdfcbae0cf476bf74cad9712b5a3f32433a9ea73662116e468ec27522c5cbb63'
                AND bindings_manifest_sha256 =
                    'aa870ab8a484700656252d0315808ee69076a57edfa5d4c0c128e2dd54a13746'
                AND expected_chunks = 31226
            )
        )
        AND expected_binding_counts = jsonb_build_object(
            'bound_active_physical_sha_verified', 405,
            'bound_active_legacy_snapshot_only', 597,
            'bound_nonactive_legacy_snapshot', 8,
            'unbound_snapshot_empty_document', 8,
            'unbound_absent_from_snapshot', 50
        )
        AND expected_partition_counts = jsonb_build_object(
            'development', jsonb_build_object(
                'extractions_total', 998,
                'bound_active_extractions', 932
            ),
            'heldout_s130', jsonb_build_object(
                'extractions_total', 70,
                'bound_active_extractions', 70
            )
        )
    );

CREATE TABLE public.chunk_document_bindings_v1 (
    materialization_id UUID NOT NULL,
    extraction_sha256 TEXT NOT NULL,
    raw_artifact_sha256 TEXT NOT NULL,
    document_id UUID,
    binding_status TEXT NOT NULL,
    binding_authority TEXT NOT NULL,
    document_status_at_snapshot TEXT,
    source_pdf_identity TEXT,
    source_pdf_identity_status TEXT NOT NULL,
    evaluation_partition TEXT NOT NULL,
    snapshot_binding_ledger_sha256 TEXT NOT NULL,
    heldout_manifest_sha256 TEXT NOT NULL,
    binding_receipt_sha256 TEXT NOT NULL,
    retrieval_binding_eligible BOOLEAN GENERATED ALWAYS AS (
        binding_status IN (
            'bound_active_physical_sha_verified',
            'bound_active_legacy_snapshot_only'
        )
    ) STORED,
    PRIMARY KEY (materialization_id, extraction_sha256),
    CONSTRAINT chunk_document_bindings_v1_materialization_fkey
        FOREIGN KEY (materialization_id)
        REFERENCES public.chunk_materializations_v1(id)
        ON DELETE RESTRICT,
    CONSTRAINT chunk_document_bindings_v1_document_fkey
        FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT chunk_document_bindings_v1_hashes_chk CHECK (
        extraction_sha256 ~ '^[0-9a-f]{64}$'
        AND raw_artifact_sha256 ~ '^[0-9a-f]{64}$'
        AND snapshot_binding_ledger_sha256 =
            '1eec4001dfee4eb2228e92bb8f71018e02dc84e738b1973bce2aaabf5b97eaeb'
        AND heldout_manifest_sha256 =
            '654ee7c211b2d908912e5600513fbc293ba9cda9bb6a9482e1266e378fd099b8'
        AND binding_receipt_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT chunk_document_bindings_v1_partition_chk CHECK (
        evaluation_partition IN ('development', 'heldout_s130')
    ),
    CONSTRAINT chunk_document_bindings_v1_pdf_identity_shape_chk CHECK (
        (
            source_pdf_identity IS NULL
            AND source_pdf_identity_status = 'unknown'
        )
        OR (
            source_pdf_identity ~ '^[0-9a-f]{64}$'
            AND source_pdf_identity_status = 'known_physical'
        )
        OR (
            source_pdf_identity ~ '^backfill:[0-9a-f]{64}$'
            AND source_pdf_identity_status = 'synthetic_backfill'
        )
    ),
    CONSTRAINT chunk_document_bindings_v1_truth_table_chk CHECK (
        (
            binding_status = 'bound_active_physical_sha_verified'
            AND document_id IS NOT NULL
            AND document_status_at_snapshot = 'active'
            AND source_pdf_identity = extraction_sha256
            AND source_pdf_identity_status = 'known_physical'
            AND binding_authority = 'm25_exact_active_and_snapshot_reciprocal'
        )
        OR (
            binding_status = 'bound_active_legacy_snapshot_only'
            AND document_id IS NOT NULL
            AND document_status_at_snapshot = 'active'
            AND source_pdf_identity IS NOT NULL
            AND source_pdf_identity_status IN (
                'known_physical', 'synthetic_backfill', 'unknown'
            )
            AND binding_authority = 'legacy_snapshot_reciprocal_shadow_only'
        )
        OR (
            binding_status = 'bound_nonactive_legacy_snapshot'
            AND document_id IS NOT NULL
            AND document_status_at_snapshot IN ('needs_review', 'superseded')
            AND source_pdf_identity IS NOT NULL
            AND source_pdf_identity_status IN (
                'known_physical', 'synthetic_backfill', 'unknown'
            )
            AND binding_authority = 'legacy_snapshot_reciprocal_shadow_only'
        )
        OR (
            binding_status = 'unbound_snapshot_empty_document'
            AND document_id IS NULL
            AND document_status_at_snapshot IS NULL
            AND source_pdf_identity IS NULL
            AND source_pdf_identity_status = 'unknown'
            AND binding_authority = 'snapshot_empty_document_shadow_only'
        )
        OR (
            binding_status = 'unbound_absent_from_snapshot'
            AND document_id IS NULL
            AND document_status_at_snapshot IS NULL
            AND source_pdf_identity IS NULL
            AND source_pdf_identity_status = 'unknown'
            AND binding_authority = 'absent_from_snapshot_shadow_only'
        )
    )
);

ALTER TABLE public.chunk_document_bindings_v1 ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.chunks_v3 ALTER COLUMN document_id DROP NOT NULL;
ALTER TABLE public.chunks_v3
    ADD COLUMN retrieval_policy_class TEXT NOT NULL,
    ADD COLUMN retrieval_policy_receipt_sha256 TEXT NOT NULL,
    ADD COLUMN retrieval_eligible BOOLEAN GENERATED ALWAYS AS (
        retrieval_policy_class = 'eligible' AND duplicate_of IS NULL
    ) STORED,
    ADD CONSTRAINT chunks_v3_s131_binding_fkey
        FOREIGN KEY (materialization_id, extraction_sha256)
        REFERENCES public.chunk_document_bindings_v1(
            materialization_id, extraction_sha256
        )
        ON DELETE RESTRICT,
    ADD CONSTRAINT chunks_v3_s131_retrieval_policy_chk CHECK (
        retrieval_policy_class IN (
            'eligible', 'register_only', 'unsupported_language', 'duplicate'
        )
        AND retrieval_policy_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND (retrieval_policy_class <> 'eligible' OR duplicate_of IS NULL)
        AND (retrieval_policy_class <> 'duplicate' OR duplicate_of IS NOT NULL)
    );

CREATE INDEX chunk_document_bindings_v1_document_idx
    ON public.chunk_document_bindings_v1 (document_id)
    WHERE document_id IS NOT NULL;
CREATE INDEX chunk_document_bindings_v1_partition_idx
    ON public.chunk_document_bindings_v1 (
        materialization_id, evaluation_partition, binding_status
    );
CREATE INDEX chunks_v3_s131_fts_eligible_idx
    ON public.chunks_v3 USING gin (search_vector)
    WHERE retrieval_eligible AND duplicate_of IS NULL;

CREATE FUNCTION public.protect_chunk_document_bindings_v1()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
    generation_state TEXT;
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT m.state INTO generation_state
        FROM public.chunk_materializations_v1 AS m
        WHERE m.id = NEW.materialization_id
        FOR SHARE;
        IF generation_state IS DISTINCT FROM 'loading' THEN
            RAISE EXCEPTION 'S131 bindings require a loading generation';
        END IF;
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'S131 bindings are append-only';
    END IF;
    SELECT m.state INTO generation_state
    FROM public.chunk_materializations_v1 AS m
    WHERE m.id = OLD.materialization_id;
    IF generation_state NOT IN ('loading', 'failed') THEN
        RAISE EXCEPTION 'cannot delete binding from sealed generation';
    END IF;
    RETURN OLD;
END
$function$;

ALTER FUNCTION public.protect_chunk_document_bindings_v1()
    OWNER TO technical_bot_chunks_v3_publisher;
CREATE TRIGGER chunk_document_bindings_v1_immutable_trigger
BEFORE INSERT OR UPDATE OR DELETE ON public.chunk_document_bindings_v1
FOR EACH ROW EXECUTE FUNCTION public.protect_chunk_document_bindings_v1();

ALTER FUNCTION public.protect_chunks_v3_rows_v1() SECURITY DEFINER;
ALTER FUNCTION public.protect_chunks_v3_rows_v1()
    OWNER TO technical_bot_chunks_v3_publisher;

CREATE FUNCTION public.validate_chunks_v3_shadow_v2(
    target_id UUID,
    asserted_rows_manifest_sha256 TEXT,
    asserted_bindings_manifest_sha256 TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
    target public.chunk_materializations_v1%ROWTYPE;
    binding_count INTEGER;
    chunk_count INTEGER;
    observed_binding_counts JSONB;
    observed_partition_counts JSONB;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('technical_bot_chunks_v3_shadow_transition_v2', 0)
    );
    SELECT m.* INTO target
    FROM public.chunk_materializations_v1 AS m
    WHERE m.id = target_id
    FOR UPDATE;
    IF NOT FOUND OR target.state <> 'loading' THEN
        RAISE EXCEPTION 'S131 materialization is absent or not loading';
    END IF;
    IF target.expected_bindings <> 1068
       OR target.expected_chunks NOT IN (31212, 31226)
       OR asserted_rows_manifest_sha256 IS DISTINCT FROM target.rows_manifest_sha256
       OR asserted_bindings_manifest_sha256 IS DISTINCT FROM target.bindings_manifest_sha256 THEN
        RAISE EXCEPTION 'S131 frozen manifest assertion mismatch';
    END IF;

    SELECT count(*) INTO binding_count
    FROM public.chunk_document_bindings_v1 AS b
    WHERE b.materialization_id = target_id;
    SELECT count(*) INTO chunk_count
    FROM public.chunks_v3 AS c
    WHERE c.materialization_id = target_id;
    IF binding_count <> target.expected_bindings
       OR chunk_count <> target.expected_chunks THEN
        RAISE EXCEPTION 'S131 materialization count mismatch';
    END IF;

    SELECT jsonb_build_object(
        'bound_active_physical_sha_verified', count(*) FILTER (
            WHERE b.binding_status = 'bound_active_physical_sha_verified'
        ),
        'bound_active_legacy_snapshot_only', count(*) FILTER (
            WHERE b.binding_status = 'bound_active_legacy_snapshot_only'
        ),
        'bound_nonactive_legacy_snapshot', count(*) FILTER (
            WHERE b.binding_status = 'bound_nonactive_legacy_snapshot'
        ),
        'unbound_snapshot_empty_document', count(*) FILTER (
            WHERE b.binding_status = 'unbound_snapshot_empty_document'
        ),
        'unbound_absent_from_snapshot', count(*) FILTER (
            WHERE b.binding_status = 'unbound_absent_from_snapshot'
        )
    ) INTO observed_binding_counts
    FROM public.chunk_document_bindings_v1 AS b
    WHERE b.materialization_id = target_id;

    SELECT jsonb_build_object(
        'development', jsonb_build_object(
            'extractions_total', count(*) FILTER (
                WHERE b.evaluation_partition = 'development'
            ),
            'bound_active_extractions', count(*) FILTER (
                WHERE b.evaluation_partition = 'development'
                  AND b.retrieval_binding_eligible
            )
        ),
        'heldout_s130', jsonb_build_object(
            'extractions_total', count(*) FILTER (
                WHERE b.evaluation_partition = 'heldout_s130'
            ),
            'bound_active_extractions', count(*) FILTER (
                WHERE b.evaluation_partition = 'heldout_s130'
                  AND b.retrieval_binding_eligible
            )
        )
    ) INTO observed_partition_counts
    FROM public.chunk_document_bindings_v1 AS b
    WHERE b.materialization_id = target_id;

    IF observed_binding_counts IS DISTINCT FROM target.expected_binding_counts
       OR observed_partition_counts IS DISTINCT FROM target.expected_partition_counts THEN
        RAISE EXCEPTION 'S131 binding or partition counts diverge';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.chunk_document_bindings_v1 AS b
        LEFT JOIN public.chunks_v3 AS c
          ON c.materialization_id = b.materialization_id
         AND c.extraction_sha256 = b.extraction_sha256
        WHERE b.materialization_id = target_id
        GROUP BY b.materialization_id, b.extraction_sha256
        HAVING count(c.id) = 0
    ) THEN
        RAISE EXCEPTION 'S131 binding without chunks';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.chunks_v3 AS c
        JOIN public.chunk_document_bindings_v1 AS b
          ON b.materialization_id = c.materialization_id
         AND b.extraction_sha256 = c.extraction_sha256
        WHERE c.materialization_id = target_id
          AND (
              c.document_id IS DISTINCT FROM b.document_id
              OR c.raw_artifact_sha256 IS DISTINCT FROM b.raw_artifact_sha256
          )
    ) THEN
        RAISE EXCEPTION 'S131 chunk/binding identity mismatch';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.chunks_v3 AS c
        JOIN public.chunk_document_bindings_v1 AS b
          ON b.materialization_id = c.materialization_id
         AND b.extraction_sha256 = c.extraction_sha256
        WHERE c.materialization_id = target_id
          AND NOT b.retrieval_binding_eligible
          AND c.retrieval_policy_class = 'eligible'
    ) THEN
        RAISE EXCEPTION 'S131 ineligible binding marked for retrieval';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.chunk_document_bindings_v1 AS b
        LEFT JOIN public.documents AS d ON d.id = b.document_id
        WHERE b.materialization_id = target_id
          AND b.document_id IS NOT NULL
          AND (
              d.id IS NULL
              OR d.status IS DISTINCT FROM b.document_status_at_snapshot
              OR d.source_pdf_sha256 IS DISTINCT FROM b.source_pdf_identity
          )
    ) THEN
        RAISE EXCEPTION 'S131 document identity or status drift';
    END IF;

    UPDATE public.chunk_materializations_v1
    SET state = 'validated',
        observed_documents = binding_count,
        observed_chunks = chunk_count,
        validated_at = pg_catalog.now(),
        failure_reason = NULL
    WHERE id = target_id;

    RETURN jsonb_build_object(
        'materialization_id', target_id,
        'state', 'validated',
        'bindings', binding_count,
        'chunks', chunk_count
    );
END
$function$;

ALTER FUNCTION public.validate_chunks_v3_shadow_v2(UUID, TEXT, TEXT)
    OWNER TO technical_bot_chunks_v3_publisher;

CREATE FUNCTION public.discard_chunks_v3_shadow_v2(target_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
    target_state TEXT;
    removed_chunks INTEGER;
    removed_bindings INTEGER;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('technical_bot_chunks_v3_shadow_transition_v2', 0)
    );
    SELECT m.state INTO target_state
    FROM public.chunk_materializations_v1 AS m
    WHERE m.id = target_id
    FOR UPDATE;
    IF NOT FOUND OR target_state NOT IN ('loading', 'failed') THEN
        RAISE EXCEPTION 'S131 discard requires loading or failed';
    END IF;
    DELETE FROM public.chunks_v3 WHERE materialization_id = target_id;
    GET DIAGNOSTICS removed_chunks = ROW_COUNT;
    DELETE FROM public.chunk_document_bindings_v1 WHERE materialization_id = target_id;
    GET DIAGNOSTICS removed_bindings = ROW_COUNT;
    DELETE FROM public.chunk_materializations_v1 WHERE id = target_id;
    RETURN jsonb_build_object(
        'materialization_id', target_id,
        'state', 'discarded',
        'removed_chunks', removed_chunks,
        'removed_bindings', removed_bindings
    );
END
$function$;

ALTER FUNCTION public.discard_chunks_v3_shadow_v2(UUID)
    OWNER TO technical_bot_chunks_v3_publisher;

CREATE VIEW public.chunks_v3_shadow_retrieval_eligible_v2
WITH (security_invoker = true)
AS
SELECT
    c.id,
    c.content,
    c.context,
    c.product_model,
    c.category,
    c.section_title,
    c.section_path,
    c.content_type,
    c.manufacturer,
    c.distributor,
    c.protocol,
    c.doc_type,
    c.language,
    c.is_flow_diagram,
    c.confidence,
    c.has_diagram,
    c.diagram_url,
    c.source_file,
    c.page_number,
    c.document_id,
    c.materialization_id,
    c.extraction_sha256,
    c.raw_artifact_sha256,
    c.source_block_start,
    c.source_block_end,
    c.search_vector,
    b.binding_status,
    b.binding_receipt_sha256,
    b.evaluation_partition,
    b.source_pdf_identity,
    c.retrieval_policy_class,
    c.retrieval_policy_receipt_sha256
FROM public.chunks_v3 AS c
JOIN public.chunk_document_bindings_v1 AS b
  ON b.materialization_id = c.materialization_id
 AND b.extraction_sha256 = c.extraction_sha256
JOIN public.chunk_materializations_v1 AS m
  ON m.id = c.materialization_id
JOIN public.documents AS d ON d.id = b.document_id
WHERE m.state = 'validated'
  AND b.binding_status IN (
      'bound_active_physical_sha_verified',
      'bound_active_legacy_snapshot_only'
  )
  AND b.document_status_at_snapshot = 'active'
  AND d.status = 'active'
  AND d.source_pdf_sha256 IS NOT DISTINCT FROM b.source_pdf_identity
  AND c.document_id IS NOT DISTINCT FROM b.document_id
  AND c.raw_artifact_sha256 = b.raw_artifact_sha256
  AND c.retrieval_policy_class = 'eligible'
  AND c.retrieval_policy_receipt_sha256 IS NOT NULL
  AND c.duplicate_of IS NULL;

CREATE FUNCTION public.search_chunks_v3_shadow_text_v2(
    target_materialization_id UUID,
    target_evaluation_partition TEXT,
    search_query TEXT,
    filter_product TEXT,
    filter_manufacturer TEXT,
    filter_category TEXT,
    match_limit INTEGER
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    context TEXT,
    product_model TEXT,
    category TEXT,
    section_title TEXT,
    section_path TEXT,
    content_type TEXT,
    manufacturer TEXT,
    language TEXT,
    source_file TEXT,
    page_number INTEGER,
    document_id UUID,
    materialization_id UUID,
    extraction_sha256 TEXT,
    evaluation_partition TEXT,
    rank DOUBLE PRECISION
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $function$
BEGIN
    IF target_materialization_id IS NULL
       OR target_evaluation_partition NOT IN ('development', 'heldout_s130')
       OR search_query IS NULL
       OR pg_catalog.btrim(search_query) = ''
       OR match_limit IS NULL
       OR match_limit < 1
       OR match_limit > 200
       OR (filter_product IS NOT NULL AND pg_catalog.btrim(filter_product) = '')
       OR (filter_manufacturer IS NOT NULL AND pg_catalog.btrim(filter_manufacturer) = '')
       OR (filter_category IS NOT NULL AND pg_catalog.btrim(filter_category) = '') THEN
        RAISE EXCEPTION 'S131 invalid shadow query' USING ERRCODE = '22023';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM public.chunk_materializations_v1 AS m
        WHERE m.id = target_materialization_id
          AND m.state = 'validated'
          AND (
              (
                  m.id = 'eb426a33-91cb-543e-a0c9-fd615dbc36cb'::UUID
                  AND m.manifest_sha256 =
                      '3040da3ace4e033f6bc52e3cf092e2427262d91729ecb67fe7a104a71cbd73a1'
                  AND m.rows_manifest_sha256 =
                      '68e87fd43702fcf53f14ff7fbdbe65e4faa346977a199ff7427333b8cab950f3'
                  AND m.bindings_manifest_sha256 =
                      '951c6a7615045d770574404cf664385b741bd0097abeebed6a0b6bc1f410f2c1'
                  AND m.expected_chunks = 31212
              )
              OR (
                  m.id = '1852e61c-ac7f-5232-be1c-627ea54f29b5'::UUID
                  AND m.manifest_sha256 =
                      'f702ddcf3d51a479fff90c95f1ccd6206680da4a262462f80a74b10c1b3c1089'
                  AND m.rows_manifest_sha256 =
                      'cdfcbae0cf476bf74cad9712b5a3f32433a9ea73662116e468ec27522c5cbb63'
                  AND m.bindings_manifest_sha256 =
                      'aa870ab8a484700656252d0315808ee69076a57edfa5d4c0c128e2dd54a13746'
                  AND m.expected_chunks = 31226
              )
          )
    ) THEN
        RAISE EXCEPTION 'S131 shadow materialization is not validated';
    END IF;

    RETURN QUERY
    SELECT
        v.id,
        v.content,
        v.context,
        v.product_model,
        v.category,
        v.section_title,
        v.section_path,
        v.content_type,
        v.manufacturer,
        v.language,
        v.source_file,
        v.page_number,
        v.document_id,
        v.materialization_id,
        v.extraction_sha256,
        v.evaluation_partition,
        pg_catalog.ts_rank(
            v.search_vector,
            pg_catalog.plainto_tsquery('public.spanish_unaccent', search_query)
        )::DOUBLE PRECISION AS rank
    FROM public.chunks_v3_shadow_retrieval_eligible_v2 AS v
    WHERE v.materialization_id = target_materialization_id
      AND v.evaluation_partition = target_evaluation_partition
      AND v.search_vector @@ pg_catalog.plainto_tsquery(
          'public.spanish_unaccent', search_query
      )
      AND (filter_product IS NULL OR v.product_model = pg_catalog.btrim(filter_product))
      AND (filter_manufacturer IS NULL OR v.manufacturer = pg_catalog.btrim(filter_manufacturer))
      AND (filter_category IS NULL OR v.category = pg_catalog.btrim(filter_category))
    ORDER BY pg_catalog.ts_rank(
        v.search_vector,
        pg_catalog.plainto_tsquery('public.spanish_unaccent', search_query)
    ) DESC, v.id ASC
    LIMIT match_limit;
END
$function$;

ALTER VIEW public.chunks_v3_shadow_retrieval_eligible_v2
    OWNER TO technical_bot_chunks_v3_shadow_rpc_owner;
ALTER FUNCTION public.search_chunks_v3_shadow_text_v2(
    UUID, TEXT, TEXT, TEXT, TEXT, TEXT, INTEGER
) OWNER TO technical_bot_chunks_v3_shadow_rpc_owner;

REVOKE CREATE ON SCHEMA public FROM
    technical_bot_chunks_v3_publisher,
    technical_bot_chunks_v3_shadow_rpc_owner;

-- Existing internal publisher gains only the metadata required by the two
-- transition RPCs. It remains NOLOGIN and no API role receives membership.
GRANT SELECT, UPDATE, DELETE ON TABLE public.chunk_materializations_v1
    TO technical_bot_chunks_v3_publisher;
GRANT SELECT, DELETE ON TABLE public.chunks_v3
    TO technical_bot_chunks_v3_publisher;
GRANT SELECT, UPDATE, DELETE ON TABLE public.chunk_document_bindings_v1
    TO technical_bot_chunks_v3_publisher;
GRANT SELECT (id, source_pdf_sha256, status) ON TABLE public.documents
    TO technical_bot_chunks_v3_publisher;

CREATE POLICY chunk_materializations_v1_s131_loader_insert
ON public.chunk_materializations_v1
FOR INSERT TO technical_bot_chunks_v3_shadow_loader
WITH CHECK (state = 'loading');
CREATE POLICY chunks_v3_s131_loader_insert
ON public.chunks_v3
FOR INSERT TO technical_bot_chunks_v3_shadow_loader
WITH CHECK (true);
CREATE POLICY chunk_document_bindings_v1_s131_loader_insert
ON public.chunk_document_bindings_v1
FOR INSERT TO technical_bot_chunks_v3_shadow_loader
WITH CHECK (true);
-- The two SECURITY DEFINER transition RPCs are owned by the publisher.  RLS
-- therefore needs explicit internal read/delete paths; table grants alone are
-- insufficient and API roles receive neither policy nor membership.
CREATE POLICY chunk_document_bindings_v1_s131_publisher_select
ON public.chunk_document_bindings_v1
FOR SELECT TO technical_bot_chunks_v3_publisher
USING (true);
CREATE POLICY chunk_document_bindings_v1_s131_publisher_delete
ON public.chunk_document_bindings_v1
FOR DELETE TO technical_bot_chunks_v3_publisher
USING (true);
CREATE POLICY documents_s131_publisher_bound_select
ON public.documents
FOR SELECT TO technical_bot_chunks_v3_publisher
USING (
    EXISTS (
        SELECT 1
        FROM public.chunk_document_bindings_v1 AS b
        WHERE b.document_id = id
    )
);

CREATE POLICY chunk_materializations_v1_s131_rpc_select
ON public.chunk_materializations_v1
FOR SELECT TO technical_bot_chunks_v3_shadow_rpc_owner
USING (state = 'validated');
CREATE POLICY chunks_v3_s131_rpc_select
ON public.chunks_v3
FOR SELECT TO technical_bot_chunks_v3_shadow_rpc_owner
USING (
    EXISTS (
        SELECT 1
        FROM public.chunk_materializations_v1 AS m
        WHERE m.id = materialization_id AND m.state = 'validated'
    )
);
CREATE POLICY chunk_document_bindings_v1_s131_rpc_select
ON public.chunk_document_bindings_v1
FOR SELECT TO technical_bot_chunks_v3_shadow_rpc_owner
USING (
    retrieval_binding_eligible
    AND EXISTS (
        SELECT 1
        FROM public.chunk_materializations_v1 AS m
        WHERE m.id = materialization_id AND m.state = 'validated'
    )
);
CREATE POLICY documents_s131_shadow_rpc_select
ON public.documents
FOR SELECT TO technical_bot_chunks_v3_shadow_rpc_owner
USING (status = 'active');

REVOKE ALL ON TABLE public.chunk_materializations_v1
    FROM PUBLIC, anon, authenticated, service_role,
         technical_bot_chunks_v3_shadow_loader,
         technical_bot_chunks_v3_shadow_rpc_owner,
         technical_bot_chunks_v3_shadow_runner;
REVOKE ALL ON TABLE public.chunks_v3
    FROM PUBLIC, anon, authenticated, service_role,
         technical_bot_chunks_v3_shadow_loader,
         technical_bot_chunks_v3_shadow_rpc_owner,
         technical_bot_chunks_v3_shadow_runner;
REVOKE ALL ON TABLE public.chunk_document_bindings_v1
    FROM PUBLIC, anon, authenticated, service_role,
         technical_bot_chunks_v3_shadow_loader,
         technical_bot_chunks_v3_shadow_rpc_owner,
         technical_bot_chunks_v3_shadow_runner;
REVOKE ALL ON TABLE public.chunks_v3_shadow_retrieval_eligible_v2
    FROM PUBLIC, anon, authenticated, service_role,
         technical_bot_chunks_v3_shadow_loader,
         technical_bot_chunks_v3_shadow_rpc_owner,
         technical_bot_chunks_v3_shadow_runner;
REVOKE ALL ON FUNCTION public.validate_chunks_v3_shadow_v2(UUID, TEXT, TEXT)
    FROM PUBLIC, anon, authenticated, service_role,
         technical_bot_chunks_v3_shadow_loader,
         technical_bot_chunks_v3_shadow_rpc_owner,
         technical_bot_chunks_v3_shadow_runner;
REVOKE ALL ON FUNCTION public.discard_chunks_v3_shadow_v2(UUID)
    FROM PUBLIC, anon, authenticated, service_role,
         technical_bot_chunks_v3_shadow_loader,
         technical_bot_chunks_v3_shadow_rpc_owner,
         technical_bot_chunks_v3_shadow_runner;
REVOKE ALL ON FUNCTION public.search_chunks_v3_shadow_text_v2(
    UUID, TEXT, TEXT, TEXT, TEXT, TEXT, INTEGER
) FROM PUBLIC, anon, authenticated, service_role,
       technical_bot_chunks_v3_shadow_loader,
       technical_bot_chunks_v3_shadow_rpc_owner,
       technical_bot_chunks_v3_shadow_runner;

GRANT USAGE ON SCHEMA public TO
    technical_bot_chunks_v3_shadow_loader,
    technical_bot_chunks_v3_shadow_rpc_owner,
    technical_bot_chunks_v3_shadow_runner;

GRANT INSERT (
    id, manifest_sha256, manifest, manifest_receipt_sha256,
    rows_manifest_sha256, expected_documents, expected_chunks,
    expected_bindings, bindings_manifest_sha256,
    expected_binding_counts, expected_partition_counts
) ON TABLE public.chunk_materializations_v1
TO technical_bot_chunks_v3_shadow_loader;
GRANT INSERT ON TABLE public.chunk_document_bindings_v1
    TO technical_bot_chunks_v3_shadow_loader;
GRANT INSERT ON TABLE public.chunks_v3
    TO technical_bot_chunks_v3_shadow_loader;
GRANT EXECUTE ON FUNCTION public.validate_chunks_v3_shadow_v2(UUID, TEXT, TEXT)
    TO technical_bot_chunks_v3_shadow_loader;
GRANT EXECUTE ON FUNCTION public.discard_chunks_v3_shadow_v2(UUID)
    TO technical_bot_chunks_v3_shadow_loader;

GRANT SELECT ON TABLE public.chunk_materializations_v1,
    public.chunks_v3, public.chunk_document_bindings_v1
    TO technical_bot_chunks_v3_shadow_rpc_owner;
GRANT SELECT (id, source_pdf_sha256, status) ON TABLE public.documents
    TO technical_bot_chunks_v3_shadow_rpc_owner;
GRANT SELECT ON TABLE public.chunks_v3_shadow_retrieval_eligible_v2
    TO technical_bot_chunks_v3_shadow_rpc_owner;

GRANT EXECUTE ON FUNCTION public.search_chunks_v3_shadow_text_v2(
    UUID, TEXT, TEXT, TEXT, TEXT, TEXT, INTEGER
) TO technical_bot_chunks_v3_shadow_runner;

COMMENT ON TABLE public.chunk_document_bindings_v1 IS
'S131 shadow-only extraction-to-document receipts; legacy binding is not PDF identity proof.';
COMMENT ON VIEW public.chunks_v3_shadow_retrieval_eligible_v2 IS
'S131 internal security-invoker view; callers use only the narrow shadow RPC.';
COMMENT ON FUNCTION public.search_chunks_v3_shadow_text_v2(
    UUID, TEXT, TEXT, TEXT, TEXT, TEXT, INTEGER
) IS 'S131 lexical shadow RPC; explicit validated materialization and partition only.';

COMMIT;
