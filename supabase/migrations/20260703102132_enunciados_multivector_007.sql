ALTER TABLE chunks_v2
    ADD COLUMN IF NOT EXISTS parent_id UUID NULL REFERENCES chunks_v2(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS ingest_batch TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_chunks_v2_parent
    ON chunks_v2 (parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chunks_v2_batch
    ON chunks_v2 (ingest_batch) WHERE ingest_batch IS NOT NULL;

DROP FUNCTION IF EXISTS match_chunks_v2(vector, double precision, integer, text, text, text);

CREATE OR REPLACE FUNCTION public.match_chunks_v2(
    query_embedding vector,
    match_threshold double precision DEFAULT 0.5,
    match_count integer DEFAULT 10,
    filter_product text DEFAULT NULL::text,
    filter_category text DEFAULT NULL::text,
    filter_manufacturer text DEFAULT NULL::text,
    include_surrogates boolean DEFAULT false
)
RETURNS TABLE(id uuid, content text, context text, product_model text, category text,
              section_title text, section_path text, content_type text, manufacturer text,
              distributor text, protocol text, doc_type text, language text,
              is_flow_diagram boolean, confidence real, has_diagram boolean,
              diagram_url text, source_file text, page_number integer, document_id uuid,
              parent_id uuid, similarity double precision)
LANGUAGE plpgsql
AS $function$
BEGIN
    PERFORM set_config('hnsw.ef_search', '120', true);
    RETURN QUERY
    SELECT
        c.id, c.content, c.context, c.product_model, c.category,
        c.section_title, c.section_path, c.content_type, c.manufacturer,
        c.distributor, c.protocol, c.doc_type, c.language, c.is_flow_diagram,
        c.confidence, c.has_diagram, c.diagram_url, c.source_file, c.page_number,
        c.document_id, c.parent_id,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks_v2 c
    WHERE
        c.duplicate_of IS NULL
        AND c.embedding IS NOT NULL
        AND (include_surrogates OR c.parent_id IS NULL)
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
        AND (filter_product IS NULL OR c.product_model = filter_product)
        AND (filter_category IS NULL OR c.category = filter_category)
        AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.search_chunks_text_v2(
    search_query text,
    filter_product text DEFAULT NULL::text,
    filter_manufacturer text DEFAULT NULL::text,
    filter_category text DEFAULT NULL::text,
    match_limit integer DEFAULT 10
)
RETURNS TABLE(id uuid, content text, context text, product_model text, category text,
              section_title text, section_path text, content_type text, manufacturer text,
              distributor text, protocol text, doc_type text, language text,
              is_flow_diagram boolean, confidence real, has_diagram boolean,
              diagram_url text, source_file text, page_number integer, document_id uuid,
              rank double precision)
LANGUAGE plpgsql
AS $function$
DECLARE
    ts_query tsquery := plainto_tsquery('public.spanish_unaccent', search_query);
BEGIN
    RETURN QUERY
    SELECT
        c.id, c.content, c.context, c.product_model, c.category,
        c.section_title, c.section_path, c.content_type, c.manufacturer,
        c.distributor, c.protocol, c.doc_type, c.language, c.is_flow_diagram,
        c.confidence, c.has_diagram, c.diagram_url, c.source_file, c.page_number,
        c.document_id,
        ts_rank(c.search_vector, ts_query)::FLOAT AS rank
    FROM chunks_v2 c
    WHERE
        c.duplicate_of IS NULL
        AND c.parent_id IS NULL
        AND c.search_vector @@ ts_query
        AND (filter_product IS NULL OR c.product_model = filter_product)
        AND (filter_category IS NULL OR c.category = filter_category)
        AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY ts_rank(c.search_vector, ts_query) DESC
    LIMIT match_limit;
END;
$function$;
