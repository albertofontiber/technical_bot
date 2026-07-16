-- S117 M2.7 STATIC SQL SPECIFICATION ONLY.
-- NO_GO_FOR_DB / NO MIGRATION / DO NOT APPLY.
-- Executability requires a later disposable-Postgres + Supabase gate.

-- Policy and canonicality are independent.  Backfill/validation sequencing is
-- intentionally outside this static contract.
ALTER TABLE public.chunks_v3
    ADD COLUMN retrieval_policy_class TEXT,
    ADD COLUMN retrieval_eligible BOOLEAN
        GENERATED ALWAYS AS (
            retrieval_policy_class = 'eligible' AND duplicate_of IS NULL
        ) STORED;

ALTER TABLE public.chunks_v3
    ADD CONSTRAINT chunks_v3_retrieval_policy_class_chk CHECK (
        retrieval_policy_class IN (
            'eligible', 'register_only', 'unsupported_language', 'duplicate'
        )
    ) NOT VALID,
    ADD CONSTRAINT chunks_v3_retrieval_policy_canonicality_chk CHECK (
        (retrieval_policy_class <> 'eligible' OR duplicate_of IS NULL)
        AND (retrieval_policy_class <> 'duplicate' OR duplicate_of IS NOT NULL)
    ) NOT VALID;

-- The view is a logical single source, not a privilege barrier.
CREATE OR REPLACE VIEW public.chunks_v3_retrieval_eligible_v1
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
    c.raw_artifact_sha256,
    c.source_block_start,
    c.source_block_end,
    c.duplicate_of,
    c.retrieval_policy_class,
    c.retrieval_eligible,
    c.search_vector,
    c.embedding,
    c.context_origin,
    c.context_sha256,
    c.context_input_sha256,
    c.contextualizer_sha256,
    c.context_prompt_sha256,
    c.context_model,
    c.context_limits,
    c.embedding_origin,
    c.embedding_input_sha256,
    c.embedding_provider,
    c.embedding_model,
    c.embedding_input_type,
    c.embedding_dimensions,
    c.embedding_sha256
FROM public.chunks_v3 AS c
JOIN public.chunk_materializations_v1 AS m
  ON m.id = c.materialization_id
 AND m.state = 'active'
JOIN public.documents AS d
  ON d.id = c.document_id
 AND d.source_pdf_sha256 = c.extraction_sha256
 AND d.status = 'active'
WHERE c.retrieval_eligible
  AND c.duplicate_of IS NULL;

-- No generation override is accepted by either retrieval channel.
DROP FUNCTION IF EXISTS public.match_chunks_v3(
    vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT, UUID
);

CREATE OR REPLACE FUNCTION public.match_chunks_v3(
    query_embedding vector(1024),
    match_threshold DOUBLE PRECISION DEFAULT 0.5,
    match_count INTEGER DEFAULT 10,
    filter_product TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL,
    filter_manufacturer TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID, content TEXT, context TEXT, product_model TEXT, category TEXT,
    section_title TEXT, section_path TEXT, content_type TEXT, manufacturer TEXT,
    distributor TEXT, protocol TEXT, doc_type TEXT, language TEXT,
    is_flow_diagram BOOLEAN, confidence REAL, has_diagram BOOLEAN,
    diagram_url TEXT, source_file TEXT, page_number INTEGER, document_id UUID,
    materialization_id UUID, raw_artifact_sha256 TEXT,
    source_block_start INTEGER, source_block_end INTEGER,
    similarity DOUBLE PRECISION
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
    normalized_product TEXT;
    normalized_category TEXT;
    normalized_manufacturer TEXT;
BEGIN
    IF query_embedding IS NULL THEN
        RAISE EXCEPTION 'M27_INVALID_QUERY' USING ERRCODE = '22023';
    END IF;
    IF match_threshold IS NULL
       OR match_threshold = 'NaN'::DOUBLE PRECISION
       OR match_threshold < -1.0
       OR match_threshold > 1.0 THEN
        RAISE EXCEPTION 'M27_INVALID_THRESHOLD' USING ERRCODE = '22023';
    END IF;
    IF match_count IS NULL OR match_count < 1 OR match_count > 200 THEN
        RAISE EXCEPTION 'M27_INVALID_LIMIT' USING ERRCODE = '22023';
    END IF;
    IF (filter_product IS NOT NULL AND btrim(filter_product) = '')
       OR (filter_category IS NOT NULL AND btrim(filter_category) = '')
       OR (filter_manufacturer IS NOT NULL AND btrim(filter_manufacturer) = '') THEN
        RAISE EXCEPTION 'M27_INVALID_FILTER' USING ERRCODE = '22023';
    END IF;
    normalized_product := btrim(filter_product);
    normalized_category := btrim(filter_category);
    normalized_manufacturer := btrim(filter_manufacturer);

    RETURN QUERY
    WITH scored AS (
        SELECT
            v.*,
            (1 - (v.embedding <=> query_embedding))::DOUBLE PRECISION AS score
        FROM public.chunks_v3_retrieval_eligible_v1 AS v
        WHERE v.embedding IS NOT NULL
          AND v.context_origin = 'generated_v3'
          AND v.context_sha256 IS NOT NULL
          AND v.context_input_sha256 IS NOT NULL
          AND v.contextualizer_sha256 IS NOT NULL
          AND v.context_prompt_sha256 IS NOT NULL
          AND v.context_model = 'claude-haiku-4-5'
          AND v.embedding_origin = 'generated_v3'
          AND v.embedding_input_sha256 IS NOT NULL
          AND v.embedding_provider = 'voyage'
          AND v.embedding_model = 'voyage-4-large'
          AND v.embedding_input_type = 'document'
          AND v.embedding_dimensions = 1024
          AND v.embedding_sha256 IS NOT NULL
          AND (normalized_product IS NULL OR v.product_model = normalized_product)
          AND (normalized_category IS NULL OR v.category = normalized_category)
          AND (normalized_manufacturer IS NULL OR v.manufacturer = normalized_manufacturer)
    )
    SELECT
        s.id, s.content, s.context, s.product_model, s.category,
        s.section_title, s.section_path, s.content_type, s.manufacturer,
        s.distributor, s.protocol, s.doc_type, s.language, s.is_flow_diagram,
        s.confidence, s.has_diagram, s.diagram_url, s.source_file, s.page_number,
        s.document_id, s.materialization_id, s.raw_artifact_sha256,
        s.source_block_start, s.source_block_end, s.score
    FROM scored AS s
    WHERE s.score > match_threshold
    ORDER BY s.score DESC, s.id
    LIMIT match_count;
END
$function$;

DROP FUNCTION IF EXISTS public.search_chunks_text_v3(
    TEXT, TEXT, TEXT, TEXT, INTEGER, UUID
);

CREATE OR REPLACE FUNCTION public.search_chunks_text_v3(
    search_query TEXT,
    filter_product TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL,
    filter_manufacturer TEXT DEFAULT NULL,
    match_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID, content TEXT, context TEXT, product_model TEXT, category TEXT,
    section_title TEXT, section_path TEXT, content_type TEXT, manufacturer TEXT,
    distributor TEXT, protocol TEXT, doc_type TEXT, language TEXT,
    is_flow_diagram BOOLEAN, confidence REAL, has_diagram BOOLEAN,
    diagram_url TEXT, source_file TEXT, page_number INTEGER, document_id UUID,
    materialization_id UUID, raw_artifact_sha256 TEXT,
    source_block_start INTEGER, source_block_end INTEGER,
    rank DOUBLE PRECISION
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
    normalized_product TEXT;
    normalized_category TEXT;
    normalized_manufacturer TEXT;
    normalized_query TEXT;
    parsed_query TSQUERY;
BEGIN
    IF search_query IS NULL OR btrim(search_query) = '' THEN
        RAISE EXCEPTION 'M27_INVALID_QUERY' USING ERRCODE = '22023';
    END IF;
    IF match_limit IS NULL OR match_limit < 1 OR match_limit > 200 THEN
        RAISE EXCEPTION 'M27_INVALID_LIMIT' USING ERRCODE = '22023';
    END IF;
    IF (filter_product IS NOT NULL AND btrim(filter_product) = '')
       OR (filter_category IS NOT NULL AND btrim(filter_category) = '')
       OR (filter_manufacturer IS NOT NULL AND btrim(filter_manufacturer) = '') THEN
        RAISE EXCEPTION 'M27_INVALID_FILTER' USING ERRCODE = '22023';
    END IF;
    normalized_product := btrim(filter_product);
    normalized_category := btrim(filter_category);
    normalized_manufacturer := btrim(filter_manufacturer);
    normalized_query := btrim(search_query);
    parsed_query := plainto_tsquery('public.spanish_unaccent', normalized_query);
    IF numnode(parsed_query) = 0 THEN
        RAISE EXCEPTION 'M27_INVALID_QUERY' USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    SELECT
        v.id, v.content, v.context, v.product_model, v.category,
        v.section_title, v.section_path, v.content_type, v.manufacturer,
        v.distributor, v.protocol, v.doc_type, v.language, v.is_flow_diagram,
        v.confidence, v.has_diagram, v.diagram_url, v.source_file, v.page_number,
        v.document_id, v.materialization_id, v.raw_artifact_sha256,
        v.source_block_start, v.source_block_end,
        ts_rank(v.search_vector, parsed_query)::DOUBLE PRECISION AS score
    FROM public.chunks_v3_retrieval_eligible_v1 AS v
    WHERE v.search_vector @@ parsed_query
      AND (normalized_product IS NULL OR v.product_model = normalized_product)
      AND (normalized_category IS NULL OR v.category = normalized_category)
      AND (normalized_manufacturer IS NULL OR v.manufacturer = normalized_manufacturer)
    ORDER BY score DESC, v.id
    LIMIT match_limit;
END
$function$;

-- Static same-table predicate only.  Approximate vector indexes are explicitly
-- deferred until a generation-scoped recall + EXPLAIN gate.
CREATE INDEX chunks_v3_retrieval_eligible_fts_idx
    ON public.chunks_v3 USING gin (search_vector)
    WHERE retrieval_eligible AND duplicate_of IS NULL;

-- Future apply precondition: security-invoker execution relies on Supabase's
-- service_role BYPASSRLS contract.  M2.7 does not execute this guard.
DO $guard$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_roles
        WHERE rolname = 'service_role' AND rolbypassrls
    ) THEN
        RAISE EXCEPTION 'M27_SERVICE_ROLE_RLS_CONTRACT' USING ERRCODE = '42501';
    END IF;
END
$guard$;

REVOKE ALL ON TABLE public.chunks_v3_retrieval_eligible_v1
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.match_chunks_v3(
    vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT
) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.search_chunks_text_v3(
    TEXT, TEXT, TEXT, TEXT, INTEGER
) FROM PUBLIC, anon, authenticated, service_role;

-- Remove broad SELECT left by the frozen shadow migration, but retain INSERT.
REVOKE SELECT ON TABLE public.chunks_v3 FROM service_role;
REVOKE SELECT ON TABLE public.chunk_materializations_v1 FROM service_role;

GRANT SELECT (
    id, content, context, product_model, category, section_title, section_path,
    content_type, manufacturer, distributor, protocol, doc_type, language,
    is_flow_diagram, confidence, has_diagram, diagram_url, source_file,
    page_number, document_id, materialization_id, extraction_sha256,
    raw_artifact_sha256, source_block_start, source_block_end, duplicate_of,
    retrieval_policy_class, retrieval_eligible, search_vector, embedding,
    context_origin, context_sha256, context_input_sha256, contextualizer_sha256,
    context_prompt_sha256, context_model, context_limits, embedding_origin,
    embedding_input_sha256, embedding_provider, embedding_model,
    embedding_input_type, embedding_dimensions, embedding_sha256
) ON TABLE public.chunks_v3 TO service_role;
GRANT SELECT (id, state)
    ON TABLE public.chunk_materializations_v1 TO service_role;

-- documents is a shared production table.  M2.7 grants the required columns
-- but does not revoke unrelated pre-existing service_role access to it.
GRANT SELECT (id, source_pdf_sha256, status)
    ON TABLE public.documents TO service_role;

GRANT SELECT ON TABLE public.chunks_v3_retrieval_eligible_v1 TO service_role;
GRANT EXECUTE ON FUNCTION public.match_chunks_v3(
    vector, DOUBLE PRECISION, INTEGER, TEXT, TEXT, TEXT
) TO service_role;
GRANT EXECUTE ON FUNCTION public.search_chunks_text_v3(
    TEXT, TEXT, TEXT, TEXT, INTEGER
) TO service_role;
