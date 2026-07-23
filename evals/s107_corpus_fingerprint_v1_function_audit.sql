-- Strong, deterministic identity for every database object used by the fixed
-- chunks_v2 evaluation route. Safe on production: it requires the existing pgcrypto
-- dependency and installs the read-only STABLE fingerprint RPC; it does not change corpus
-- rows, roles or retrieval objects.
DO $dependency$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        RAISE EXCEPTION 'pgcrypto prerequisite is missing; fingerprint RPC not installed';
    END IF;
END
$dependency$;

CREATE OR REPLACE FUNCTION public.corpus_fingerprint_v1()
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, extensions, public
AS $$
WITH chunk_hashes AS (
    SELECT
        c.id,
        c.created_at,
        encode(digest(jsonb_build_array(
            c.id, c.document_id, c.extraction_sha256, c.chunk_index,
            c.duplicate_of, c.created_at
        )::text, 'sha256'), 'hex') AS identity_hash,
        encode(digest(jsonb_build_array(
            c.id, c.content, c.context, c.language, c.section_title, c.section_path,
            c.content_type, c.is_flow_diagram, c.confidence, c.product_model,
            c.manufacturer, c.distributor, c.protocol, c.doc_type, c.category,
            c.has_diagram, c.diagram_url, c.source_file, c.page_number,
            c.document_id, c.extraction_sha256, c.chunk_index, c.duplicate_of,
            c.search_vector::text
        )::text, 'sha256'), 'hex') AS content_hash,
        encode(digest(jsonb_build_array(c.id, c.embedding::text)::text,
                      'sha256'), 'hex') AS embedding_hash
    FROM public.chunks_v2 c
), chunk_aggregate AS (
    SELECT
        count(*)::bigint AS row_count,
        max(created_at) AS max_created_at,
        encode(digest(coalesce(string_agg(identity_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS identity_sha256,
        encode(digest(coalesce(string_agg(content_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS content_sha256,
        encode(digest(coalesce(string_agg(embedding_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS embedding_sha256
    FROM chunk_hashes
), enunciado_hashes AS (
    SELECT
        e.id,
        encode(digest(jsonb_build_array(
            e.id, e.parent_id, e.ingest_batch, e.document_id,
            e.extraction_sha256, e.chunk_index
        )::text, 'sha256'), 'hex') AS identity_hash,
        encode(digest(jsonb_build_array(
            e.id, e.parent_id, e.content, e.context, e.source_file, e.page_number,
            e.product_model, e.manufacturer, e.section_title, e.doc_type,
            e.content_type, e.chunk_index, e.document_id, e.language,
            e.extraction_sha256, e.ingest_batch
        )::text, 'sha256'), 'hex') AS content_hash,
        encode(digest(jsonb_build_array(e.id, e.embedding::text)::text,
                      'sha256'), 'hex') AS embedding_hash
    FROM public.chunks_v2_enunciados e
), enunciado_aggregate AS (
    SELECT
        count(*)::bigint AS row_count,
        encode(digest(coalesce(string_agg(identity_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS identity_sha256,
        encode(digest(coalesce(string_agg(content_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS content_sha256,
        encode(digest(coalesce(string_agg(embedding_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS embedding_sha256
    FROM enunciado_hashes
), hyq_hashes AS (
    SELECT
        h.id,
        encode(digest(jsonb_build_array(
            h.id, h.chunk_id, h.ingest_batch
        )::text, 'sha256'), 'hex') AS identity_hash,
        encode(digest(jsonb_build_array(
            h.id, h.chunk_id, h.question, h.source_file, h.page_number,
            h.product_model, h.origin, h.ingest_batch
        )::text, 'sha256'), 'hex') AS content_hash,
        encode(digest(jsonb_build_array(h.id, h.embedding::text)::text,
                      'sha256'), 'hex') AS embedding_hash
    FROM public.chunks_v2_hyq h
), hyq_aggregate AS (
    SELECT
        count(*)::bigint AS row_count,
        encode(digest(coalesce(string_agg(identity_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS identity_sha256,
        encode(digest(coalesce(string_agg(content_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS content_sha256,
        encode(digest(coalesce(string_agg(embedding_hash, '' ORDER BY id), ''),
                      'sha256'), 'hex') AS embedding_sha256
    FROM hyq_hashes
), document_hashes AS (
    SELECT d.id,
           encode(digest(jsonb_build_array(
               d.id, d.document_family, d.revision, d.revision_date, d.language,
               d.doc_type, d.manufacturer, d.product_model, d.source_pdf_filename,
               d.source_pdf_sha256, d.status, d.supersedes_id, d.superseded_by_id,
               d.ingested_at
           )::text, 'sha256'), 'hex') AS document_hash
    FROM public.documents d
), document_aggregate AS (
    SELECT count(*)::bigint AS row_count,
           encode(digest(coalesce(string_agg(document_hash, '' ORDER BY id), ''),
                         'sha256'), 'hex') AS documents_sha256
    FROM document_hashes
), contract_items AS (
    -- Function bodies are part of retrieval semantics, not merely deployment metadata.
    SELECT 'function:' || p.oid::regprocedure::text AS item_key,
           pg_get_functiondef(p.oid) AS item_value
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN ('match_chunks_v2', 'search_chunks_text_v2',
                        'match_chunks_v2_enunciados', 'match_hyq')
    UNION ALL
    -- Includes HNSW operator classes/options and all supporting indexes.
    SELECT 'index:' || schemaname || '.' || indexname,
           indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename IN ('chunks_v2', 'chunks_v2_enunciados', 'chunks_v2_hyq',
                        'documents')
    UNION ALL
    SELECT 'table_reloptions:' || n.nspname || '.' || c.relname,
           jsonb_build_array(c.reloptions, toast.reloptions)::text
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    LEFT JOIN pg_class toast ON toast.oid = c.reltoastrelid
    WHERE n.nspname = 'public'
      AND c.relname IN ('chunks_v2', 'chunks_v2_enunciados', 'chunks_v2_hyq',
                        'documents')
    UNION ALL
    SELECT 'trigger:' || n.nspname || '.' || c.relname || '.' || t.tgname,
           pg_get_triggerdef(t.oid, true)
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE NOT t.tgisinternal AND n.nspname = 'public'
      AND c.relname IN ('chunks_v2', 'chunks_v2_enunciados', 'chunks_v2_hyq',
                        'documents')
    UNION ALL
    SELECT 'column:' || table_schema || '.' || table_name || '.' ||
           lpad(ordinal_position::text, 4, '0') || ':' || column_name,
           jsonb_build_array(data_type, udt_schema, udt_name, is_nullable,
                             column_default, is_generated,
                             generation_expression)::text
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name IN ('chunks_v2', 'chunks_v2_enunciados', 'chunks_v2_hyq',
                         'documents')
    UNION ALL
    -- FTS ranking depends on the parser/dictionary mapping and dictionary options.
    SELECT 'ts_config:' || nc.nspname || '.' || cfg.cfgname || ':' ||
           m.maptokentype::text || ':' || m.mapseqno::text,
           jsonb_build_array(nd.nspname, d.dictname, d.dictinitoption,
                             nt.nspname, tmpl.tmplname)::text
    FROM pg_ts_config cfg
    JOIN pg_namespace nc ON nc.oid = cfg.cfgnamespace
    JOIN pg_ts_config_map m ON m.mapcfg = cfg.oid
    JOIN pg_ts_dict d ON d.oid = m.mapdict
    JOIN pg_namespace nd ON nd.oid = d.dictnamespace
    JOIN pg_ts_template tmpl ON tmpl.oid = d.dicttemplate
    JOIN pg_namespace nt ON nt.oid = tmpl.tmplnamespace
    WHERE nc.nspname = 'public' AND cfg.cfgname = 'spanish_unaccent'
    UNION ALL
    SELECT 'extension:' || extname, extversion
    FROM pg_extension
    WHERE extname IN ('vector', 'unaccent')
    UNION ALL
    SELECT 'setting:' || setting_name, current_setting(setting_name, true)
    FROM unnest(ARRAY[
        'server_version_num', 'lc_collate', 'lc_ctype',
        'default_text_search_config', 'hnsw.ef_search', 'hnsw.iterative_scan',
        'hnsw.max_scan_tuples', 'hnsw.scan_mem_multiplier'
    ]) AS settings(setting_name)
), contract_aggregate AS (
    SELECT count(*)::bigint AS component_count,
           encode(digest(coalesce(string_agg(
               encode(digest(jsonb_build_array(item_key, item_value)::text,
                             'sha256'), 'hex'), '' ORDER BY item_key), ''),
                         'sha256'), 'hex') AS retrieval_contract_sha256
    FROM contract_items
), physical_items AS (
    SELECT 'index_physical:' || ni.nspname || '.' || i.relname AS item_key,
           jsonb_build_array(i.relfilenode, pg_relation_size(i.oid))::text AS item_value
    FROM pg_index x
    JOIN pg_class i ON i.oid = x.indexrelid
    JOIN pg_class t ON t.oid = x.indrelid
    JOIN pg_namespace ni ON ni.oid = i.relnamespace
    JOIN pg_namespace nt ON nt.oid = t.relnamespace
    WHERE nt.nspname = 'public'
      AND t.relname IN ('chunks_v2', 'chunks_v2_enunciados', 'chunks_v2_hyq',
                        'documents')
), physical_aggregate AS (
    SELECT count(*)::bigint AS component_count,
           encode(digest(coalesce(string_agg(
               encode(digest(jsonb_build_array(item_key, item_value)::text,
                             'sha256'), 'hex'), '' ORDER BY item_key), ''),
                         'sha256'), 'hex') AS retrieval_physical_sha256
    FROM physical_items
), required_objects AS (
    SELECT jsonb_build_object(
        'match_chunks_v2', count(*) FILTER (
            WHERE p.proname = 'match_chunks_v2' AND p.pronargs = 7) > 0,
        'search_chunks_text_v2', count(*) FILTER (
            WHERE p.proname = 'search_chunks_text_v2' AND p.pronargs = 5) > 0,
        'match_chunks_v2_enunciados', count(*) FILTER (
            WHERE p.proname = 'match_chunks_v2_enunciados' AND p.pronargs = 5) > 0,
        'match_hyq', count(*) FILTER (
            WHERE p.proname = 'match_hyq' AND p.pronargs = 3) > 0,
        'spanish_unaccent', EXISTS (
            SELECT 1 FROM pg_ts_config cfg
            JOIN pg_namespace ncfg ON ncfg.oid = cfg.cfgnamespace
            WHERE ncfg.nspname = 'public' AND cfg.cfgname = 'spanish_unaccent'),
        'chunks_v2_hnsw', EXISTS (
            SELECT 1 FROM pg_indexes i WHERE i.schemaname = 'public'
            AND i.tablename = 'chunks_v2' AND i.indexdef ILIKE '% USING hnsw %'),
        'chunks_v2_enunciados_hnsw', EXISTS (
            SELECT 1 FROM pg_indexes i WHERE i.schemaname = 'public'
            AND i.tablename = 'chunks_v2_enunciados' AND i.indexdef ILIKE '% USING hnsw %'),
        'chunks_v2_hyq_hnsw', EXISTS (
            SELECT 1 FROM pg_indexes i WHERE i.schemaname = 'public'
            AND i.tablename = 'chunks_v2_hyq' AND i.indexdef ILIKE '% USING hnsw %')
    ) AS presence
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN ('match_chunks_v2', 'search_chunks_text_v2',
                        'match_chunks_v2_enunciados', 'match_hyq')
)
SELECT jsonb_build_object(
    'schema', 'corpus_fingerprint_v1',
    'table', 'chunks_v2',
    'count', ca.row_count,
    'max_created_at', ca.max_created_at,
    'row_identity_sha256', encode(digest(jsonb_build_array(
        ca.identity_sha256, ea.identity_sha256, ha.identity_sha256,
        da.documents_sha256
    )::text, 'sha256'), 'hex'),
    'content_sha256', encode(digest(jsonb_build_array(
        ca.content_sha256, ea.content_sha256, ha.content_sha256,
        da.documents_sha256
    )::text, 'sha256'), 'hex'),
    'embedding_sha256', encode(digest(jsonb_build_array(
        ca.embedding_sha256, ea.embedding_sha256, ha.embedding_sha256
    )::text, 'sha256'), 'hex'),
    'retrieval_contract_sha256', ra.retrieval_contract_sha256,
    'retrieval_physical_sha256', pa.retrieval_physical_sha256,
    'required_objects', required.presence,
    'components', jsonb_build_object(
        'chunks_v2', ca.row_count,
        'chunks_v2_enunciados', ea.row_count,
        'chunks_v2_hyq', ha.row_count,
        'documents', da.row_count,
        'retrieval_contract_items', ra.component_count,
        'retrieval_physical_items', pa.component_count
    )
)
FROM chunk_aggregate ca
CROSS JOIN enunciado_aggregate ea
CROSS JOIN hyq_aggregate ha
CROSS JOIN document_aggregate da
CROSS JOIN contract_aggregate ra
CROSS JOIN physical_aggregate pa
CROSS JOIN required_objects required;
$$;

REVOKE ALL ON FUNCTION public.corpus_fingerprint_v1() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.corpus_fingerprint_v1() FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.corpus_fingerprint_v1() TO service_role;

COMMENT ON FUNCTION public.corpus_fingerprint_v1() IS
'Strong corpus/retrieval identity for chunks_v2 plus enunciados/hyq, documents, FTS and DB contract.';
