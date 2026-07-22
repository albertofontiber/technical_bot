-- 008 — fix de dilución HNSW post-filtro (T1 s94b): iterative_scan.
-- Al insertar 21.995 surrogates (parent_id set) el índice HNSW pasó de 25k a 47k
-- vectores; con include_surrogates=false el filtro parent_id IS NULL descarta ~47% del
-- pool ef_search DESPUÉS del traversal → recall de chunks reales cae (famtie 12→19).
-- pgvector 0.8 iterative_scan=relaxed_order sigue escaneando hasta llenar el match_count
-- con filas que pasan el filtro. USERSET vía set_config (mismo patrón que ef_search).
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
    PERFORM set_config('hnsw.iterative_scan', 'relaxed_order', true);
    PERFORM set_config('hnsw.max_scan_tuples', '40000', true);
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
