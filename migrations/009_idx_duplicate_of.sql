-- ============================================================================
-- 009 — índice de soporte para la FK chunks_v2.duplicate_of → chunks_v2.id
-- (T1 s94b, cazado al borrar el batch de enunciados: la FK existía SIN índice, así
--  que cada DELETE/UPDATE disparaba un seqscan por-fila en el check FOR KEY SHARE →
--  statement timeout al borrar 22k filas). Índice parcial (solo filas con duplicate_of
--  set). Mejora permanente de todo DELETE/UPDATE sobre chunks_v2. APLICADA a la DB viva.
--
-- ROLLBACK: DROP INDEX IF EXISTS idx_chunks_v2_duplicate_of;
--
-- Nota operativa (T1): borrar filas de una tabla con índice HNSW NO restaura el recall
-- por sí solo — pgvector deja los vectores borrados como tuplas-fantasma en el grafo
-- hasta un VACUUM. Tras cualquier rollback masivo de surrogates: VACUUM chunks_v2.
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_chunks_v2_duplicate_of
    ON chunks_v2 (duplicate_of) WHERE duplicate_of IS NOT NULL;
