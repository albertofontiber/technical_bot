-- 009 — índice de soporte para la FK chunks_v2.duplicate_of → chunks_v2.id.
-- La FK existía SIN índice: cada DELETE/UPDATE dispara un seqscan por fila para el
-- check FOR KEY SHARE (cazado al borrar el batch T1 — statement timeout). Índice
-- parcial (solo filas con duplicate_of set, ~pocas).
CREATE INDEX IF NOT EXISTS idx_chunks_v2_duplicate_of
    ON chunks_v2 (duplicate_of) WHERE duplicate_of IS NOT NULL;
