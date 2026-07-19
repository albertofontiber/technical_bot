-- ============================================================================
-- ROLLBACK EJECUTABLE de 014 (patrón 007_rollback / nota de rollback de 011/013).
-- document_visual_assets es una tabla NUEVA sin dependientes: ningún objeto de
-- producción (chunks, chunks_v2, RPCs, triggers) la referencia. El DROP es
-- completo y no toca ninguna tabla existente. Los índices idx_dva_* caen con
-- la tabla. El serving queda inerte igualmente porque VISUAL_ASSETS_REGISTRY
-- es default off y el lookup falla abierto (404 → sin diagramas, warning).
-- ============================================================================

DROP TABLE IF EXISTS document_visual_assets;
