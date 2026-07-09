-- ============================================================================
-- 013 — Ship hyq/HyPE (D2 Alberto; piloto GO DEC-095; diseño evals/s102_plan_autonomo.md):
-- tabla SEPARADA para las preguntas-hipotéticas (question-side surrogates) con su PROPIO
-- índice HNSW — mismo patrón que 011 enunciados (DEC-088/089: compartir el HNSW de
-- chunks_v2 diluye el recall de los chunks reales; el surrogate vive en su índice y el
-- padre se resuelve por ID).
--
-- La tabla/índice de chunks reales NO se toca. Nada se sirve con flag-off (el RPC solo
-- lo llama vector_search cuando HYQ_TABLE=on; default off = prod inerte).
--
-- ROLLBACK (completo, no toca chunks_v2):
--   DROP FUNCTION IF EXISTS match_hyq(vector, double precision, integer);
--   DROP TABLE IF EXISTS chunks_v2_hyq;
-- ============================================================================

CREATE TABLE IF NOT EXISTS chunks_v2_hyq (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- FK CON índice de soporte (lección migración 009 vía 011-D6: FK sin índice =
    -- seqscan por-fila en cada DELETE de chunks_v2). El CASCADE acopla al pipeline de
    -- re-ingesta vivo a propósito: huérfanos imposibles.
    chunk_id      UUID NOT NULL REFERENCES chunks_v2(id) ON DELETE CASCADE,
    question      TEXT NOT NULL,
    embedding     vector(1024),
    source_file   TEXT,
    page_number   INTEGER,
    product_model TEXT,
    origin        TEXT,
    -- vintage AUDITABLE EN SQL (fix cross-model s102): qué universo npz/parse produjo la
    -- fila (patrón ingest_batch de 011). El loader estampa `hyq-v1-<sha16-del-npz>`, ABORTA
    -- si la tabla contiene otro batch (anti-mezcla: ignore-duplicates no actualiza filas
    -- stale) y --wipe borra por batch.
    ingest_batch  TEXT NOT NULL,
    -- idempotencia del loader: re-correr con on_conflict=ignore-duplicates solo inserta
    -- lo que falte (el npz es el checkpoint de embeddings; la DB, el de filas).
    UNIQUE (chunk_id, question)
);

CREATE INDEX IF NOT EXISTS idx_c2hyq_chunk_id ON chunks_v2_hyq (chunk_id);
CREATE INDEX IF NOT EXISTS idx_c2hyq_ingest_batch ON chunks_v2_hyq (ingest_batch);
CREATE INDEX IF NOT EXISTS idx_c2hyq_embedding ON chunks_v2_hyq
    USING hnsw (embedding vector_cosine_ops);

-- RPC del canal question-side. Retorno MÍNIMO (chunk_id, question, similarity): el
-- retriever colapsa keep-max por padre e hidrata el padre desde chunks_v2 — la fila
-- servida es SIEMPRE el chunk real (paridad exacta con el seam npz del piloto s101).
-- ef_search=120 (mismo vintage que 007/011). La barra del espacio-pregunta (0.45,
-- hiperparámetro MEDIDO del piloto) la pasa el cliente en match_threshold.
CREATE OR REPLACE FUNCTION public.match_hyq(
    query_embedding vector,
    match_threshold double precision DEFAULT 0.45,
    match_count integer DEFAULT 200
)
RETURNS TABLE(chunk_id uuid, question text, similarity double precision)
LANGUAGE plpgsql
AS $function$
BEGIN
    -- (fix dúo s102 #1) ef_search DEBE cubrir match_count: un index-scan HNSW devuelve
    -- como máximo ~ef_search filas → con 120 fijo (vintage 007/011) el LIMIT 200 del seam
    -- devolvería ~120 = fetch-K efectivo DISTINTO del npz del piloto (falsa paridad).
    -- (011 conserva su 120: su GO se midió CON la tabla — el número embebe el defecto.)
    PERFORM set_config('hnsw.ef_search', GREATEST(match_count, 120)::text, true);
    RETURN QUERY
    SELECT
        h.chunk_id, h.question,
        1 - (h.embedding <=> query_embedding) AS similarity
    FROM chunks_v2_hyq h
    WHERE
        h.embedding IS NOT NULL
        AND 1 - (h.embedding <=> query_embedding) > match_threshold
    ORDER BY h.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;
