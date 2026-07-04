-- ============================================================================
-- ROLLBACK EJECUTABLE de 007 (MENOR del cross-model T0: "pre-escrito" exigía las
-- definiciones pre-007 EJECUTABLES, no una referencia). Definiciones VIVAS
-- capturadas con pg_get_functiondef el 3-jul-2026 ANTES de aplicar 007.
-- Nota: el SET "hnsw.ef_search"='120' original exige un rol con permiso sobre el
-- GUC (se aplicó en s59b vía SQL Editor); si el rol de rollback no lo tiene,
-- sustituir por PERFORM set_config('hnsw.ef_search','120',true) en el body.
-- ============================================================================

DELETE FROM chunks_v2 WHERE ingest_batch LIKE 'enunciados-%';

DROP FUNCTION IF EXISTS match_chunks_v2(vector, double precision, integer, text, text, text, boolean);
DROP INDEX IF EXISTS idx_chunks_v2_parent;
DROP INDEX IF EXISTS idx_chunks_v2_batch;
ALTER TABLE chunks_v2 DROP COLUMN IF EXISTS parent_id, DROP COLUMN IF EXISTS ingest_batch;

CREATE OR REPLACE FUNCTION public.match_chunks_v2(query_embedding vector, match_threshold double precision DEFAULT 0.5, match_count integer DEFAULT 10, filter_product text DEFAULT NULL::text, filter_category text DEFAULT NULL::text, filter_manufacturer text DEFAULT NULL::text)
 RETURNS TABLE(id uuid, content text, context text, product_model text, category text, section_title text, section_path text, content_type text, manufacturer text, distributor text, protocol text, doc_type text, language text, is_flow_diagram boolean, confidence real, has_diagram boolean, diagram_url text, source_file text, page_number integer, document_id uuid, similarity double precision)
 LANGUAGE plpgsql
 SET "hnsw.ef_search" TO '120'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        c.id, c.content, c.context, c.product_model, c.category,
        c.section_title, c.section_path, c.content_type, c.manufacturer,
        c.distributor, c.protocol, c.doc_type, c.language, c.is_flow_diagram,
        c.confidence, c.has_diagram, c.diagram_url, c.source_file, c.page_number,
        c.document_id,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks_v2 c
    WHERE
        c.duplicate_of IS NULL
        AND c.embedding IS NOT NULL
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
        AND (filter_product IS NULL OR c.product_model = filter_product)
        AND (filter_category IS NULL OR c.category = filter_category)
        AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.search_chunks_text_v2(search_query text, filter_product text DEFAULT NULL::text, filter_manufacturer text DEFAULT NULL::text, filter_category text DEFAULT NULL::text, match_limit integer DEFAULT 10)
 RETURNS TABLE(id uuid, content text, context text, product_model text, category text, section_title text, section_path text, content_type text, manufacturer text, distributor text, protocol text, doc_type text, language text, is_flow_diagram boolean, confidence real, has_diagram boolean, diagram_url text, source_file text, page_number integer, document_id uuid, rank double precision)
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
        AND c.search_vector @@ ts_query
        AND (filter_product IS NULL OR c.product_model = filter_product)
        AND (filter_category IS NULL OR c.category = filter_category)
        AND (filter_manufacturer IS NULL OR c.manufacturer = filter_manufacturer)
    ORDER BY ts_rank(c.search_vector, ts_query) DESC
    LIMIT match_limit;
END;
$function$;
