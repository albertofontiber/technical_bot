-- ============================================================================
-- 014 — Registro de activos visuales por REVISIÓN documental (contrato S190,
-- evals/s190_visual_asset_contract_design_v1.md §"Contrato propuesto").
--
-- Motivo: el canal de diagramas del bot está implementado pero muerto en datos
-- (chunks_v2.diagram_url = 0/25.090; las URLs viven solo en la tabla legacy
-- `chunks`). El activo visual pertenece a una revisión documental y una página,
-- NO a una segmentación concreta — copiar la URL legacy a cada chunk (backfill
-- ciego) es NO-GO medido (S190: 3/5 muestras eran portada/marketing y
-- has_diagram=true en el 100% de filas = flag sin significado).
--
-- Esta tabla es INDEPENDIENTE del chunker: sobrevive a chunks_v2, chunks_v3 o
-- un futuro chunks_v4. La asociación con el chunk servido es SOLO en lectura,
-- vía (document_id, page_index). Nada muta chunks / chunks_v2.
--
-- Contrato de servicio (S190 §Restricciones):
--   * Solo se sirven activos technical_utility='useful'. 'uncertain' (el
--     DEFAULT) JAMÁS se sirve — un activo sin clasificar no llega al técnico.
--   * Máximo 2 activos por respuesta; la respuesta de texto falla abierta.
--   * La página servida debe pertenecer a un fragmento citado como evidencia.
--
-- Serving flag-gated: VISUAL_ASSETS_REGISTRY (default off) en src/config.py;
-- lectura en src/rag/visual_assets.py. Con el flag off la tabla es inerte.
--
-- Carga: scripts/visual_assets_bridge_load.py --load (dump S269 verificado
-- contra el audit S190 con tolerancia 0). El INSERT requiere autorización
-- explícita del orquestador; la migración solo crea el contenedor vacío.
--
-- ROLLBACK (completo, no toca ninguna tabla existente): migrations/014_rollback.sql
--   DROP TABLE IF EXISTS document_visual_assets;
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_visual_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ---- Identidad documental (nunca solo nombre de fichero) ---------------
    document_id UUID NOT NULL REFERENCES documents(id),
        -- FK a la revisión documental EXACTA en `documents` (mismo patrón que
        -- chunks_v2.document_id en la migración 006: los documentos son
        -- idempotentes por hash → el id ES la revisión).
    page_index INTEGER NOT NULL,
        -- Índice de página nativo del extractor. En el bridge S190/S269 es el
        -- page_number 1-based de LlamaParse (= chunks_v2.page_number, fiable).
    page_label TEXT,
        -- Etiqueta impresa de la página si difiere del índice ("iv", "3-12").
        -- Separada a propósito del índice nativo (contrato S190).

    -- ---- Identidad del activo ----------------------------------------------
    asset_sha256 TEXT NOT NULL,
        -- Identidad inmutable del BINARIO. El bridge S269 estampa
        -- provisionalmente sha256(storage_url) hasta descargar el binario
        -- (campo asset_sha256_provenance del dump lo declara); el backfill del
        -- hash binario NO cambia la clave de unión (document_id, page_index).
    storage_url TEXT NOT NULL,
        -- Localizador (Supabase Storage). Su valor NO constituye la identidad.

    -- ---- Recibo de transporte ----------------------------------------------
    media_type TEXT,
    width INTEGER,
    height INTEGER,

    -- ---- Alcance y clasificación -------------------------------------------
    asset_scope TEXT NOT NULL DEFAULT 'page_render'
        CHECK (asset_scope IN ('page_render', 'crop')),
        -- No fingir que una página completa es un diagrama (contrato S190).
    visual_role TEXT
        CHECK (visual_role IN ('wiring', 'table', 'procedure', 'ui',
                               'product_photo', 'cover', 'marketing', 'other')),
        -- Vocabulario CERRADO. NULL = aún sin clasificar (el clasificador de
        -- utilidad S269-v3 lo puebla; no se abusa de 'other' como placeholder).
    technical_utility TEXT NOT NULL DEFAULT 'uncertain'
        CHECK (technical_utility IN ('useful', 'not_useful', 'uncertain')),
        -- 'uncertain' es el default Y no se sirve NUNCA (el lookup filtra
        -- technical_utility='useful'; la falta de adjunto es preferible a un
        -- adjunto incorrecto — gate S191/S269).

    -- ---- Trazabilidad de la clasificación ----------------------------------
    classifier_contract TEXT,
        -- Versión del contrato del clasificador que emitió el veredicto
        -- (p.ej. 's269_visual_utility_cohort_v3_prereg'). NULL = sin clasificar.
    classifier_receipt JSONB,
        -- Recibo completo (modelo, labels, coste, sha de la cohorte). NULL en
        -- la carga del bridge; lo estampa el clasificador.
    source_extraction_sha256 TEXT,
        -- Une el activo a una extracción inmutable (chunks_v2.extraction_sha256
        -- = SHA-256 del PDF fuente, migración 006).

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Idempotencia del loader (patrón ingest de 011/013): re-correr --load con
    -- on_conflict=ignore-duplicates solo inserta lo que falte.
    UNIQUE (document_id, page_index, asset_sha256)
);

COMMENT ON TABLE document_visual_assets IS
    'Activos visuales por revisión documental (contrato S190). Independiente '
    'del chunker; unión en lectura por (document_id, page_index). Solo se '
    'sirve technical_utility=useful bajo el flag VISUAL_ASSETS_REGISTRY '
    '(default off). uncertain jamás se sirve.';

-- Índice de la ruta de servicio (lookup exacto por página citada).
CREATE INDEX IF NOT EXISTS idx_dva_document_page
    ON document_visual_assets (document_id, page_index);

-- Índice parcial de la condición REAL de servicio (patrón idx_chunks_v2_not_duplicate
-- de 006): el lookup siempre filtra technical_utility='useful'.
CREATE INDEX IF NOT EXISTS idx_dva_document_page_useful
    ON document_visual_assets (document_id, page_index)
    WHERE technical_utility = 'useful';
