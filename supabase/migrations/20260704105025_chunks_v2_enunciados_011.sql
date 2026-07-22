-- 011 — Piloto A s95: tabla separada para enunciados-surrogate + HNSW propio + RPC.
-- (contenido idéntico a migrations/011_chunks_v2_enunciados.sql del repo)
CREATE TABLE IF NOT EXISTS chunks_v2_enunciados (
    id                UUID PRIMARY KEY,
    content           TEXT NOT NULL,
    context           TEXT,
    embedding         vector(1024),
    parent_id         UUID NOT NULL REFERENCES chunks_v2(id) ON DELETE CASCADE,
    ingest_batch      TEXT NOT NULL,
    source_file       TEXT,
    page_number       INTEGER,
    product_model     TEXT,
    manufacturer      TEXT,
    section_title     TEXT,
    doc_type          TEXT,
    content_type      TEXT,
    chunk_index       INTEGER,
    document_id       UUID,
    language          TEXT,
    extraction_sha256 TEXT
);

CREATE INDEX IF NOT EXISTS idx_c2e_parent_id ON chunks_v2_enunciados (parent_id);
CREATE INDEX IF NOT EXISTS idx_c2e_ingest_batch ON chunks_v2_enunciados (ingest_batch);
CREATE INDEX IF NOT EXISTS idx_c2e_embedding ON chunks_v2_enunciados
    USING hnsw (embedding vector_cosine_ops);

CREATE OR REPLACE FUNCTION public.match_chunks_v2_enunciados(
    query_embedding vector,
    match_threshold double precision DEFAULT 0.5,
    match_count integer DEFAULT 10
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
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;
