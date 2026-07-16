-- S117 M0a: immutable chunks_v3 generations. NO_GO_FOR_DB until M0b executes
-- apply, catalogue assertions, transitions, grants, RLS and rollback against a
-- disposable PostgreSQL + pgvector instance.
--
-- This migration never copies, alters, renames or deletes chunks_v2.
-- HNSW is deliberately deferred until a complete shadow generation is loaded
-- and validated. The future index must cover canonical embedded rows only.
--
-- Rollback order (only before any external consumer is enabled):
--   DROP FUNCTION public.publish_chunks_v3_materialization_v1(uuid);
--   DROP FUNCTION public.validate_chunks_v3_materialization_v1(uuid,text);
--   DROP FUNCTION public.discard_chunks_v3_materialization_v1(uuid);
--   DROP FUNCTION public.search_chunks_text_v3(text,text,text,text,int,uuid);
--   DROP FUNCTION public.match_chunks_v3(extensions.vector,double precision,integer,text,text,text,uuid);
--   DROP TABLE public.chunks_v3;
--   DROP TABLE public.chunk_materializations_v1;
--   DROP FUNCTION public.update_chunks_v3_search_vector_v1();
--   DROP FUNCTION public.protect_chunks_v3_rows_v1();
--   REVOKE SELECT (id, source_pdf_sha256) ON public.documents
--       FROM technical_bot_chunks_v3_publisher;
--   REVOKE USAGE ON SCHEMA public FROM technical_bot_chunks_v3_publisher;
--   DROP ROLE technical_bot_chunks_v3_publisher;

BEGIN;

DO $preconditions$
BEGIN
    IF to_regclass('public.chunks_v2') IS NULL
       OR to_regclass('public.documents') IS NULL THEN
        RAISE EXCEPTION 'chunks_v2 and documents prerequisites are required';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_extension AS ext
        JOIN pg_catalog.pg_namespace AS ns ON ns.oid = ext.extnamespace
        WHERE ext.extname = 'vector'
          AND ns.nspname = 'extensions'
    ) THEN
        RAISE EXCEPTION 'pgvector extension in schema extensions is required';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_ts_config AS cfg
        JOIN pg_catalog.pg_namespace AS ns ON ns.oid = cfg.cfgnamespace
        WHERE ns.nspname = 'public'
          AND cfg.cfgname = 'spanish_unaccent'
    ) THEN
        RAISE EXCEPTION 'public.spanish_unaccent text-search configuration is required';
    END IF;
    IF to_regclass('public.chunks_v3') IS NOT NULL
       OR to_regclass('public.chunk_materializations_v1') IS NOT NULL THEN
        RAISE EXCEPTION 'chunks_v3 objects already exist; refusing schema drift';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'technical_bot_chunks_v3_publisher'
    ) THEN
        RAISE EXCEPTION 'publisher role already exists; refusing privilege drift';
    END IF;
END
$preconditions$;

CREATE ROLE technical_bot_chunks_v3_publisher
    NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;

CREATE TABLE public.chunk_materializations_v1 (
    id UUID PRIMARY KEY,
    manifest_sha256 TEXT NOT NULL UNIQUE,
    manifest JSONB NOT NULL,
    manifest_receipt_sha256 TEXT NOT NULL,
    rows_manifest_sha256 TEXT NOT NULL,
    expected_documents INTEGER NOT NULL,
    expected_chunks INTEGER NOT NULL,
    observed_documents INTEGER,
    observed_chunks INTEGER,
    state TEXT NOT NULL DEFAULT 'loading',
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    validated_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    CONSTRAINT chunk_materializations_v1_hashes_chk CHECK (
        manifest_sha256 ~ '^[0-9a-f]{64}$'
        AND manifest_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND rows_manifest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT chunk_materializations_v1_manifest_chk CHECK (
        jsonb_typeof(manifest) = 'object'
        AND manifest ->> 'schema' = 'chunk_materialization_manifest_v1'
        AND manifest ->> 'version' = '1'
        AND manifest ->> 'provenance_contract' = 's116_section_lineage_v1'
    ),
    CONSTRAINT chunk_materializations_v1_counts_chk CHECK (
        expected_documents > 0 AND expected_chunks > 0
        AND (observed_documents IS NULL OR observed_documents >= 0)
        AND (observed_chunks IS NULL OR observed_chunks >= 0)
    ),
    CONSTRAINT chunk_materializations_v1_state_chk CHECK (
        state IN ('loading', 'validated', 'active', 'retired', 'failed')
    ),
    CONSTRAINT chunk_materializations_v1_state_receipt_chk CHECK (
        state IN ('loading', 'failed')
        OR (
            observed_documents = expected_documents
            AND observed_chunks = expected_chunks
            AND validated_at IS NOT NULL
        )
    )
);

CREATE UNIQUE INDEX chunk_materializations_v1_one_active_idx
    ON public.chunk_materializations_v1 ((state))
    WHERE state = 'active';

CREATE TABLE public.chunks_v3 (
    LIKE public.chunks_v2
        INCLUDING DEFAULTS
        INCLUDING STORAGE
        INCLUDING COMPRESSION
        INCLUDING COMMENTS,
    materialization_id UUID NOT NULL,
    provenance_version SMALLINT NOT NULL,
    provenance_contract TEXT NOT NULL,
    raw_artifact_sha256 TEXT NOT NULL,
    chunker_sha256 TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    provenance_payload_sha256 TEXT NOT NULL,
    source_block_start INTEGER NOT NULL,
    source_block_end INTEGER NOT NULL,
    section_anchor JSONB,
    section_lineage JSONB NOT NULL,
    context_origin TEXT NOT NULL DEFAULT 'none',
    context_sha256 TEXT,
    context_input_sha256 TEXT,
    contextualizer_sha256 TEXT,
    context_prompt_sha256 TEXT,
    context_model TEXT,
    context_limits JSONB,
    embedding_origin TEXT NOT NULL DEFAULT 'none',
    embedding_input_sha256 TEXT,
    embedding_provider TEXT,
    embedding_model TEXT,
    embedding_input_type TEXT,
    embedding_dimensions SMALLINT,
    embedding_sha256 TEXT,
    donor_chunk_id UUID
);

ALTER TABLE public.chunks_v3 ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.chunks_v3 ALTER COLUMN chunk_index SET NOT NULL;
ALTER TABLE public.chunks_v3 ALTER COLUMN document_id SET NOT NULL;

ALTER TABLE public.chunks_v3
    ADD CONSTRAINT chunks_v3_pkey PRIMARY KEY (id),
    ADD CONSTRAINT chunks_v3_materialization_fkey
        FOREIGN KEY (materialization_id)
        REFERENCES public.chunk_materializations_v1(id)
        ON DELETE RESTRICT,
    ADD CONSTRAINT chunks_v3_document_fkey
        FOREIGN KEY (document_id) REFERENCES public.documents(id),
    ADD CONSTRAINT chunks_v3_generation_id_key UNIQUE (materialization_id, id),
    ADD CONSTRAINT chunks_v3_generation_ordinal_key
        UNIQUE (materialization_id, extraction_sha256, chunk_index),
    ADD CONSTRAINT chunks_v3_duplicate_same_generation_fkey
        FOREIGN KEY (materialization_id, duplicate_of)
        REFERENCES public.chunks_v3(materialization_id, id)
        DEFERRABLE INITIALLY DEFERRED,
    ADD CONSTRAINT chunks_v3_legacy_donor_fkey
        FOREIGN KEY (donor_chunk_id)
        REFERENCES public.chunks_v2(id)
        ON DELETE RESTRICT,
    ADD CONSTRAINT chunks_v3_version_chk CHECK (
        provenance_version = 1
        AND provenance_contract = 's116_section_lineage_v1'
    ),
    ADD CONSTRAINT chunks_v3_hashes_chk CHECK (
        extraction_sha256 ~ '^[0-9a-f]{64}$'
        AND raw_artifact_sha256 ~ '^[0-9a-f]{64}$'
        AND chunker_sha256 ~ '^[0-9a-f]{64}$'
        AND content_sha256 ~ '^[0-9a-f]{64}$'
        AND provenance_payload_sha256 ~ '^[0-9a-f]{64}$'
    ),
    ADD CONSTRAINT chunks_v3_ordinal_span_chk CHECK (
        chunk_index >= 0
        AND source_block_start >= 0
        AND source_block_end >= source_block_start
    ),
    ADD CONSTRAINT chunks_v3_lineage_json_chk CHECK (
        jsonb_typeof(section_lineage) = 'array'
        AND (section_anchor IS NULL OR jsonb_typeof(section_anchor) = 'object')
    ),
    ADD CONSTRAINT chunks_v3_lineage_state_chk CHECK (
        (
            jsonb_array_length(section_lineage) = 0
            AND section_anchor IS NULL
            AND section_title IS NULL
            AND section_path IS NULL
        )
        OR (
            jsonb_array_length(section_lineage) > 0
            AND section_anchor IS NOT NULL
            AND section_title IS NOT NULL
            AND section_path IS NOT NULL
        )
    ),
    ADD CONSTRAINT chunks_v3_no_self_duplicate_chk CHECK (
        duplicate_of IS NULL OR duplicate_of <> id
    ),
    ADD CONSTRAINT chunks_v3_context_origin_chk CHECK (
        context_origin IN ('generated_v3', 'legacy_v2_reuse', 'none')
        AND (
            (
                context_origin = 'none'
                AND context IS NULL
                AND context_sha256 IS NULL
                AND context_input_sha256 IS NULL
                AND contextualizer_sha256 IS NULL
                AND context_prompt_sha256 IS NULL
                AND context_model IS NULL
                AND context_limits IS NULL
            )
            OR (
                context_origin <> 'none'
                AND context IS NOT NULL
                AND context_sha256 ~ '^[0-9a-f]{64}$'
                AND context_input_sha256 ~ '^[0-9a-f]{64}$'
                AND context_model IS NOT NULL
                AND context_limits IS NOT NULL
                AND jsonb_typeof(context_limits) = 'object'
            )
        )
        AND (
            context_origin <> 'generated_v3'
            OR (
                contextualizer_sha256 ~ '^[0-9a-f]{64}$'
                AND context_prompt_sha256 ~ '^[0-9a-f]{64}$'
            )
        )
        AND (contextualizer_sha256 IS NULL OR contextualizer_sha256 ~ '^[0-9a-f]{64}$')
        AND (context_prompt_sha256 IS NULL OR context_prompt_sha256 ~ '^[0-9a-f]{64}$')
    ),
    ADD CONSTRAINT chunks_v3_embedding_origin_chk CHECK (
        embedding_origin IN ('generated_v3', 'legacy_v2_reuse', 'none')
        AND (
            (
                embedding_origin = 'none'
                AND embedding IS NULL
                AND embedding_input_sha256 IS NULL
                AND embedding_provider IS NULL
                AND embedding_model IS NULL
                AND embedding_input_type IS NULL
                AND embedding_dimensions IS NULL
                AND embedding_sha256 IS NULL
            )
            OR (
                embedding_origin <> 'none'
                AND embedding IS NOT NULL
                AND embedding_input_sha256 ~ '^[0-9a-f]{64}$'
                AND embedding_provider IS NOT NULL
                AND embedding_model IS NOT NULL
                AND embedding_input_type = 'document'
                AND embedding_dimensions = 1024
                AND embedding_sha256 ~ '^[0-9a-f]{64}$'
            )
        )
    ),
    ADD CONSTRAINT chunks_v3_donor_chk CHECK (
        (
            context_origin = 'legacy_v2_reuse'
            OR embedding_origin = 'legacy_v2_reuse'
        ) = (donor_chunk_id IS NOT NULL)
    );

CREATE INDEX chunks_v3_materialization_idx
    ON public.chunks_v3 (materialization_id);
CREATE INDEX chunks_v3_document_idx
    ON public.chunks_v3 (document_id);
CREATE INDEX chunks_v3_duplicate_idx
    ON public.chunks_v3 (materialization_id, duplicate_of)
    WHERE duplicate_of IS NOT NULL;
CREATE INDEX chunks_v3_product_idx
    ON public.chunks_v3 (materialization_id, product_model)
    WHERE duplicate_of IS NULL;
CREATE INDEX chunks_v3_manufacturer_idx
    ON public.chunks_v3 (materialization_id, manufacturer)
    WHERE duplicate_of IS NULL;
CREATE INDEX chunks_v3_content_type_idx
    ON public.chunks_v3 (materialization_id, content_type)
    WHERE duplicate_of IS NULL;
CREATE INDEX chunks_v3_source_file_idx
    ON public.chunks_v3 (materialization_id, source_file);
CREATE INDEX chunks_v3_language_idx
    ON public.chunks_v3 (materialization_id, language)
    WHERE duplicate_of IS NULL;
CREATE INDEX chunks_v3_search_vector_idx
    ON public.chunks_v3 USING gin (search_vector);

CREATE FUNCTION public.update_chunks_v3_search_vector_v1()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('public.spanish_unaccent',
            coalesce(NEW.section_path, NEW.section_title, '')), 'A') ||
        setweight(to_tsvector('public.spanish_unaccent', coalesce(NEW.content, '')), 'B') ||
        setweight(to_tsvector('public.spanish_unaccent', coalesce(NEW.context, '')), 'C');
    RETURN NEW;
END
$function$;

CREATE TRIGGER chunks_v3_search_vector_trigger
BEFORE INSERT OR UPDATE OF content, context, section_title, section_path
ON public.chunks_v3
FOR EACH ROW EXECUTE FUNCTION public.update_chunks_v3_search_vector_v1();

CREATE FUNCTION public.protect_chunks_v3_rows_v1()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
    generation_state TEXT;
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Serialize loaders with validate/publish.  FOR SHARE prevents the
        -- validator's FOR UPDATE from sealing a generation while an INSERT
        -- transaction that observed state=loading is still in flight.
        SELECT state INTO generation_state
        FROM public.chunk_materializations_v1
        WHERE id = NEW.materialization_id
        FOR SHARE;
        IF generation_state IS DISTINCT FROM 'loading' THEN
            RAISE EXCEPTION 'chunks_v3 inserts require a loading generation';
        END IF;
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'chunks_v3 rows are append-only';
    END IF;
    SELECT state INTO generation_state
    FROM public.chunk_materializations_v1
    WHERE id = OLD.materialization_id;
    IF generation_state NOT IN ('loading', 'failed') THEN
        RAISE EXCEPTION 'cannot delete rows from immutable generation %', OLD.materialization_id;
    END IF;
    RETURN OLD;
END
$function$;

CREATE TRIGGER chunks_v3_immutable_trigger
BEFORE INSERT OR UPDATE OR DELETE ON public.chunks_v3
FOR EACH ROW EXECUTE FUNCTION public.protect_chunks_v3_rows_v1();

CREATE FUNCTION public.validate_chunks_v3_materialization_v1(
    target_id UUID,
    asserted_rows_manifest_sha256 TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
    target public.chunk_materializations_v1%ROWTYPE;
    document_count INTEGER;
    chunk_count INTEGER;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('technical_bot_chunks_v3_publication_v1', 0)
    );
    SELECT * INTO target
    FROM public.chunk_materializations_v1
    WHERE id = target_id
    FOR UPDATE;
    IF NOT FOUND OR target.state <> 'loading' THEN
        RAISE EXCEPTION 'materialization is absent or not loading';
    END IF;
    IF asserted_rows_manifest_sha256 <> target.rows_manifest_sha256 THEN
        RAISE EXCEPTION 'rows manifest assertion mismatch';
    END IF;
    SELECT count(DISTINCT extraction_sha256), count(*)
      INTO document_count, chunk_count
    FROM public.chunks_v3
    WHERE materialization_id = target_id;
    IF document_count <> target.expected_documents
       OR chunk_count <> target.expected_chunks THEN
        RAISE EXCEPTION 'materialization count mismatch';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM public.chunks_v3 AS c
        LEFT JOIN public.documents AS d ON d.id = c.document_id
        WHERE c.materialization_id = target_id
          AND (
              d.id IS NULL
              OR d.source_pdf_sha256 !~ '^[0-9a-f]{64}$'
              OR d.source_pdf_sha256 IS DISTINCT FROM c.extraction_sha256
          )
    ) THEN
        RAISE EXCEPTION 'chunk/document exact source identity mismatch';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM (
            SELECT c.extraction_sha256
            FROM public.chunks_v3 AS c
            JOIN public.documents AS d
              ON d.source_pdf_sha256 = c.extraction_sha256
            WHERE c.materialization_id = target_id
            GROUP BY c.extraction_sha256
            HAVING count(DISTINCT d.id) <> 1
        ) AS ambiguous_document
    ) THEN
        RAISE EXCEPTION 'source SHA-256 does not resolve to exactly one document';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM public.chunks_v3 child
        JOIN public.chunks_v3 parent
          ON parent.materialization_id = child.materialization_id
         AND parent.id = child.duplicate_of
        WHERE child.materialization_id = target_id
          AND (
              child.id = child.duplicate_of
              OR parent.duplicate_of IS NOT NULL
          )
    ) THEN
        RAISE EXCEPTION 'invalid duplicate self-reference or chain';
    END IF;
    UPDATE public.chunk_materializations_v1
    SET state = 'validated',
        observed_documents = document_count,
        observed_chunks = chunk_count,
        validated_at = now(),
        failure_reason = NULL
    WHERE id = target_id;
    RETURN jsonb_build_object(
        'materialization_id', target_id,
        'state', 'validated',
        'documents', document_count,
        'chunks', chunk_count
    );
END
$function$;

CREATE FUNCTION public.publish_chunks_v3_materialization_v1(target_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
    target_state TEXT;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('technical_bot_chunks_v3_publication_v1', 0)
    );
    SELECT state INTO target_state
    FROM public.chunk_materializations_v1
    WHERE id = target_id
    FOR UPDATE;
    IF target_state IS DISTINCT FROM 'validated' THEN
        RAISE EXCEPTION 'materialization is absent or not validated';
    END IF;
    UPDATE public.chunk_materializations_v1
    SET state = 'retired', retired_at = now()
    WHERE state = 'active';
    UPDATE public.chunk_materializations_v1
    SET state = 'active', activated_at = now()
    WHERE id = target_id;
    RETURN jsonb_build_object('materialization_id', target_id, 'state', 'active');
END
$function$;

CREATE FUNCTION public.discard_chunks_v3_materialization_v1(target_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
    target_state TEXT;
    removed_chunks INTEGER;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('technical_bot_chunks_v3_publication_v1', 0)
    );
    SELECT state INTO target_state
    FROM public.chunk_materializations_v1
    WHERE id = target_id
    FOR UPDATE;
    IF NOT FOUND OR target_state NOT IN ('loading', 'failed') THEN
        RAISE EXCEPTION 'only loading or failed materializations can be discarded';
    END IF;
    DELETE FROM public.chunks_v3 WHERE materialization_id = target_id;
    GET DIAGNOSTICS removed_chunks = ROW_COUNT;
    DELETE FROM public.chunk_materializations_v1 WHERE id = target_id;
    RETURN jsonb_build_object(
        'materialization_id', target_id,
        'state', 'discarded',
        'removed_chunks', removed_chunks
    );
END
$function$;

CREATE FUNCTION public.match_chunks_v3(
    query_embedding extensions.vector(1024),
    match_threshold DOUBLE PRECISION DEFAULT 0.5,
    match_count INTEGER DEFAULT 10,
    filter_product TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL,
    filter_manufacturer TEXT DEFAULT NULL,
    target_materialization_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID, content TEXT, context TEXT, product_model TEXT, category TEXT,
    section_title TEXT, section_path TEXT, content_type TEXT, manufacturer TEXT,
    distributor TEXT, protocol TEXT, doc_type TEXT, language TEXT,
    is_flow_diagram BOOLEAN, confidence REAL, has_diagram BOOLEAN,
    diagram_url TEXT, source_file TEXT, page_number INTEGER, document_id UUID,
    materialization_id UUID, raw_artifact_sha256 TEXT,
    source_block_start INTEGER, source_block_end INTEGER, similarity DOUBLE PRECISION
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $function$
    SELECT
        c.id, c.content, c.context, c.product_model, c.category,
        c.section_title, c.section_path, c.content_type, c.manufacturer,
        c.distributor, c.protocol, c.doc_type, c.language, c.is_flow_diagram,
        c.confidence, c.has_diagram, c.diagram_url, c.source_file, c.page_number,
        c.document_id, c.materialization_id, c.raw_artifact_sha256,
        c.source_block_start, c.source_block_end,
        (1 - (c.embedding OPERATOR(extensions.<=>) query_embedding))::DOUBLE PRECISION
    FROM public.chunks_v3 AS c
    WHERE c.materialization_id = COALESCE(
            target_materialization_id,
            (SELECT m.id FROM public.chunk_materializations_v1 AS m WHERE m.state = 'active')
        )
      AND c.duplicate_of IS NULL
      AND c.embedding IS NOT NULL
      AND 1 - (c.embedding OPERATOR(extensions.<=>) query_embedding) > match_threshold
      AND (filter_product IS NULL OR c.product_model = filter_product)
      AND (filter_category IS NULL OR c.category = filter_category)
      AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY c.embedding OPERATOR(extensions.<=>) query_embedding
    LIMIT match_count
$function$;

CREATE FUNCTION public.search_chunks_text_v3(
    search_query TEXT,
    filter_product TEXT DEFAULT NULL,
    filter_manufacturer TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL,
    match_limit INTEGER DEFAULT 10,
    target_materialization_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID, content TEXT, context TEXT, product_model TEXT, category TEXT,
    section_title TEXT, section_path TEXT, content_type TEXT, manufacturer TEXT,
    distributor TEXT, protocol TEXT, doc_type TEXT, language TEXT,
    is_flow_diagram BOOLEAN, confidence REAL, has_diagram BOOLEAN,
    diagram_url TEXT, source_file TEXT, page_number INTEGER, document_id UUID,
    materialization_id UUID, raw_artifact_sha256 TEXT,
    source_block_start INTEGER, source_block_end INTEGER, rank DOUBLE PRECISION
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $function$
    SELECT
        c.id, c.content, c.context, c.product_model, c.category,
        c.section_title, c.section_path, c.content_type, c.manufacturer,
        c.distributor, c.protocol, c.doc_type, c.language, c.is_flow_diagram,
        c.confidence, c.has_diagram, c.diagram_url, c.source_file, c.page_number,
        c.document_id, c.materialization_id, c.raw_artifact_sha256,
        c.source_block_start, c.source_block_end,
        ts_rank(
            c.search_vector,
            plainto_tsquery('public.spanish_unaccent', search_query)
        )::DOUBLE PRECISION
    FROM public.chunks_v3 AS c
    WHERE c.materialization_id = COALESCE(
            target_materialization_id,
            (SELECT m.id FROM public.chunk_materializations_v1 AS m WHERE m.state = 'active')
        )
      AND c.duplicate_of IS NULL
      AND c.search_vector @@ plainto_tsquery('public.spanish_unaccent', search_query)
      AND (filter_product IS NULL OR c.product_model = filter_product)
      AND (filter_category IS NULL OR c.category = filter_category)
      AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY ts_rank(
        c.search_vector,
        plainto_tsquery('public.spanish_unaccent', search_query)
    ) DESC, c.id ASC
    LIMIT match_limit
$function$;

ALTER TABLE public.chunk_materializations_v1 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chunks_v3 ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.chunk_materializations_v1 FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.chunks_v3 FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.update_chunks_v3_search_vector_v1() FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.protect_chunks_v3_rows_v1() FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.validate_chunks_v3_materialization_v1(UUID, TEXT) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.publish_chunks_v3_materialization_v1(UUID) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.discard_chunks_v3_materialization_v1(UUID) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.match_chunks_v3(extensions.vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT, UUID) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.search_chunks_text_v3(TEXT, TEXT, TEXT, TEXT, INTEGER, UUID) FROM PUBLIC, anon, authenticated, service_role;

GRANT USAGE ON SCHEMA public TO technical_bot_chunks_v3_publisher;
GRANT CREATE ON SCHEMA public TO technical_bot_chunks_v3_publisher;
GRANT SELECT, UPDATE, DELETE ON TABLE public.chunk_materializations_v1
    TO technical_bot_chunks_v3_publisher;
GRANT SELECT, DELETE ON TABLE public.chunks_v3
    TO technical_bot_chunks_v3_publisher;
GRANT SELECT (id, source_pdf_sha256) ON TABLE public.documents
    TO technical_bot_chunks_v3_publisher;

CREATE POLICY chunk_materializations_v1_publisher_policy
ON public.chunk_materializations_v1
FOR ALL TO technical_bot_chunks_v3_publisher
USING (true) WITH CHECK (true);

CREATE POLICY chunks_v3_publisher_policy
ON public.chunks_v3
FOR SELECT TO technical_bot_chunks_v3_publisher
USING (true);

CREATE POLICY chunks_v3_publisher_delete_policy
ON public.chunks_v3
FOR DELETE TO technical_bot_chunks_v3_publisher
USING (true);

ALTER FUNCTION public.validate_chunks_v3_materialization_v1(UUID, TEXT)
    OWNER TO technical_bot_chunks_v3_publisher;
ALTER FUNCTION public.publish_chunks_v3_materialization_v1(UUID)
    OWNER TO technical_bot_chunks_v3_publisher;
ALTER FUNCTION public.discard_chunks_v3_materialization_v1(UUID)
    OWNER TO technical_bot_chunks_v3_publisher;

REVOKE CREATE ON SCHEMA public FROM technical_bot_chunks_v3_publisher;

GRANT SELECT ON TABLE public.chunk_materializations_v1 TO service_role;
GRANT INSERT (
    id, manifest_sha256, manifest, manifest_receipt_sha256,
    rows_manifest_sha256, expected_documents, expected_chunks
) ON TABLE public.chunk_materializations_v1 TO service_role;
GRANT SELECT, INSERT ON TABLE public.chunks_v3 TO service_role;
GRANT EXECUTE ON FUNCTION public.update_chunks_v3_search_vector_v1() TO service_role;
GRANT EXECUTE ON FUNCTION public.validate_chunks_v3_materialization_v1(UUID, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.publish_chunks_v3_materialization_v1(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.discard_chunks_v3_materialization_v1(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.match_chunks_v3(extensions.vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT, UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.search_chunks_text_v3(TEXT, TEXT, TEXT, TEXT, INTEGER, UUID) TO service_role;

COMMENT ON TABLE public.chunk_materializations_v1 IS
    'Immutable chunks_v3 generation registry. State transitions use narrow RPCs.';
COMMENT ON TABLE public.chunks_v3 IS
    'Shadow multigeneration corpus with S116 structural provenance. Not served by default.';

NOTIFY pgrst, 'reload schema';

COMMIT;
