-- 012 — Piloto A s95, corrección de PARIDAD DE CANAL (hallazgo del trace post-gates):
-- en s94 (DEC-086) los surrogates eran alcanzables por el canal model-filtered
-- (filter_product) — 3 de los 6 flips (PWR-R cos 0.446 < frontera 0.516 en el probe F2)
-- SOLO entran por ahí. El RPC de la tabla separada gana los mismos filtros que
-- match_chunks_v2. Firma vieja se elimina (2 firmas romperían la resolución PostgREST).
DROP FUNCTION IF EXISTS public.match_chunks_v2_enunciados(vector, double precision, integer);

CREATE OR REPLACE FUNCTION public.match_chunks_v2_enunciados(
    query_embedding vector,
    match_threshold double precision DEFAULT 0.5,
    match_count integer DEFAULT 10,
    filter_product text DEFAULT NULL::text,
    filter_manufacturer text DEFAULT NULL::text
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
        e.id, e.content, e.context, e.product_model,
        NULL::text AS category,
        e.section_title,
        NULL::text AS section_path,
        e.content_type, e.manufacturer,
        NULL::text AS distributor, NULL::text AS protocol,
        e.doc_type, e.language,
        NULL::boolean AS is_flow_diagram, NULL::real AS confidence,
        NULL::boolean AS has_diagram, NULL::text AS diagram_url,
        e.source_file, e.page_number, e.document_id, e.parent_id,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM chunks_v2_enunciados e
    WHERE
        e.embedding IS NOT NULL
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
        AND (filter_product IS NULL OR e.product_model = filter_product)
        AND (filter_manufacturer IS NULL OR e.manufacturer = filter_manufacturer)
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;
