-- ============================================================================
-- s285 · H0-T3 FINAL — PROPUESTA DE ELIMINACIÓN (adjudicaciones #21 y #26)
-- ============================================================================
-- ESTADO: PROPUESTA. NADA de este fichero ha sido ejecutado. La lane que lo
--         generó operó SELECT-only. Es el ÚNICO borrado destructivo del lote H0
--         → requiere el visto explícito de Alberto antes de correr.
--
-- Adjudicación (Alberto):
--   #21 `Docs Morley-IAS Lite&Plus - QR` → ELIMINAR del corpus
--       (chunks + embeddings + imagen + documents) + del Excel.
--   #26 `Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica`
--       → SIN modelo, genérico → ELIMINAR igual que #21.
--   Ambos son "documentos" que no documentan producto: una tarjeta con un código
--   QR a la web de Honeywell y un formulario de solicitud de asistencia en web.
--
-- ── ESQUEMA REAL INSPECCIONADO (PostgREST + migrations/) ────────────────────
--   · `chunks_v2.embedding`  es una COLUMNA vector(1024) de la propia fila:
--      NO hay tabla de embeddings aparte → borrar el chunk borra su embedding.
--   · `chunks_v2_enunciados.parent_id` → chunks_v2(id) **ON DELETE CASCADE**
--      (migrations/011). Filas para estos 2 docs: 0 y 0 (verificado).
--   · `chunks_v2_hyq.chunk_id`        → chunks_v2(id) **ON DELETE CASCADE**
--      (migrations/013). Filas: 2 y 3 (verificado) → se van solas.
--   · `document_visual_assets.document_id` → documents(id) **SIN ON DELETE**
--      (migrations/014) ⇒ NO ACTION/RESTRICT: hay que borrarlas ANTES del
--      documento o el DELETE de `documents` FALLA. Filas: 1 y 1 (verificado).
--   · `chunks_v2.document_id` → documents(id) SIN ON DELETE ⇒ idem.
--   · `chunks.document_id`    → documents(id) SIN ON DELETE (migrations/001:135)
--      — corpus LEGACY OpenAI-1536, no servido en prod (CHUNKS_TABLE=chunks_v2),
--      pero bloquea el DELETE de `documents`. Filas: 1 y 1 (verificado).
--   · `document_group_members.document_id` → ON DELETE CASCADE. Filas: 0 y 0
--      (la tabla está vacía en todo el corpus).
--   · `documents.supersedes_id` / `.superseded_by_id` apuntando a estos docs: 0 y 0.
--   · `documents.revision_lineage_id` de ambos: NULL.
--
-- ── LO QUE EL SQL **NO** BORRA (paso manual, declarado) ─────────────────────
--   El JPG vive en Supabase **Storage** (bucket público `manual-images`), no en
--   Postgres. Borrar la fila de `document_visual_assets` deja el objeto huérfano.
--   Objetos a borrar a mano (dashboard o Storage API), DESPUÉS de descargarlos
--   para el respaldo:
--     · manual-images/Morley Lite/Plus/Morley_Lite_Plus_Docs_Morley-IAS_Lite_Plus_-_QR_p001.jpg
--       (sha256 c1dc3dd0f6243515358eb13682d8d0e0bacb04b7a8a7c0515c7568b7df71360a)
--     · manual-images/morley/morley_Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica_p001.jpg
--       (sha256 be183eafab7697d8046da2054e80192d07b8d7af99034a533c5a177d246c3931)
--
-- ── PASO EXCEL (obligatorio, fuera de la DB) ────────────────────────────────
--   `data/Inventario_Manuales.xlsx`, hoja **Morley** (373 filas, cabecera
--   Producto | Tipo documento | Idioma | Subcarpeta | Archivo | Tamaño (KB)).
--   Filas a eliminar (localizadas y verificadas):
--     · fila  14 → "Docs Morley-IAS Lite&Plus - QR | Otro | ES | publico  | …pdf | 80"
--     · fila 103 → "Docs Morley-IAS Lite&Plus - QR | Otro | ES | privado  | …pdf | 80"
--          ⚠ son DOS entradas del mismo documento (publico/privado) — borrar AMBAS.
--     · fila 329 → "Solicitud-asistencia-curso-de-formacion-puesta-en- | Guía
--                   troubleshooting | ES | guias | Solicitud-asistencia-…-tecnica.pdf | 3"
--   Recalcular la hoja `Resumen` (conteos por marca) tras el borrado.
--   El PDF de origen en disco/OneDrive, si se conserva, también debe retirarse
--   para que un futuro re-ingest no lo vuelva a meter.
--
-- ── ORDEN DE EJECUCIÓN ──────────────────────────────────────────────────────
--   §0 respaldo COMPLETO (5 tablas) → §1 gate de conteos → §2 DELETEs en orden
--   de dependencia → §3 verificación → (§4 restauración si hiciera falta)
-- ============================================================================

\set docA '3912b42a-26c9-46ea-b055-b24309083608'
\set docB 'b769abb0-6d2f-4003-be9b-e62099b5a03a'
-- (si el cliente SQL no soporta \set, sustituir los UUID a mano — aparecen
--  literalmente en cada sentencia de abajo para que sean copy-paste-ables)


-- ════════════════════════════════════════════════════════════════════════════
-- §0 · RESPALDO COMPLETO (filas enteras, incluidos embeddings) — UNA vez
-- ════════════════════════════════════════════════════════════════════════════
-- `SELECT *` conserva las columnas `embedding` (vector) y `search_vector`
-- (tsvector) tal cual → la restauración de §4 es byte-fiel sin re-embeber.

CREATE TABLE IF NOT EXISTS _s285_t3_del_documents AS
SELECT * FROM documents
 WHERE id IN ('3912b42a-26c9-46ea-b055-b24309083608',
              'b769abb0-6d2f-4003-be9b-e62099b5a03a');

CREATE TABLE IF NOT EXISTS _s285_t3_del_chunks_v2 AS
SELECT * FROM chunks_v2
 WHERE document_id IN ('3912b42a-26c9-46ea-b055-b24309083608',
                       'b769abb0-6d2f-4003-be9b-e62099b5a03a');

CREATE TABLE IF NOT EXISTS _s285_t3_del_chunks_legacy AS
SELECT * FROM chunks
 WHERE source_file IN ('Docs Morley-IAS Lite&Plus - QR',
                       'Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica');

CREATE TABLE IF NOT EXISTS _s285_t3_del_hyq AS
SELECT h.* FROM chunks_v2_hyq h
 JOIN chunks_v2 c ON c.id = h.chunk_id
 WHERE c.document_id IN ('3912b42a-26c9-46ea-b055-b24309083608',
                         'b769abb0-6d2f-4003-be9b-e62099b5a03a');

CREATE TABLE IF NOT EXISTS _s285_t3_del_enunciados AS
SELECT e.* FROM chunks_v2_enunciados e
 JOIN chunks_v2 c ON c.id = e.parent_id
 WHERE c.document_id IN ('3912b42a-26c9-46ea-b055-b24309083608',
                         'b769abb0-6d2f-4003-be9b-e62099b5a03a');

CREATE TABLE IF NOT EXISTS _s285_t3_del_visual_assets AS
SELECT * FROM document_visual_assets
 WHERE document_id IN ('3912b42a-26c9-46ea-b055-b24309083608',
                       'b769abb0-6d2f-4003-be9b-e62099b5a03a');


-- ════════════════════════════════════════════════════════════════════════════
-- §1 · GATE DE CONTEOS — el respaldo debe cuadrar EXACTO con lo verificado
-- ════════════════════════════════════════════════════════════════════════════
SELECT 'documents'      AS tabla, count(*) AS filas FROM _s285_t3_del_documents      -- esperado: 2
UNION ALL SELECT 'chunks_v2',     count(*) FROM _s285_t3_del_chunks_v2                -- esperado: 2
UNION ALL SELECT 'chunks_legacy', count(*) FROM _s285_t3_del_chunks_legacy            -- esperado: 2
UNION ALL SELECT 'hyq',           count(*) FROM _s285_t3_del_hyq                      -- esperado: 5  (2 + 3)
UNION ALL SELECT 'enunciados',    count(*) FROM _s285_t3_del_enunciados               -- esperado: 0
UNION ALL SELECT 'visual_assets', count(*) FROM _s285_t3_del_visual_assets;           -- esperado: 2

-- Referencias entrantes que bloquearían el DELETE (deben ser 0 las tres):
SELECT (SELECT count(*) FROM documents
         WHERE supersedes_id    IN ('3912b42a-26c9-46ea-b055-b24309083608',
                                    'b769abb0-6d2f-4003-be9b-e62099b5a03a')) AS ref_supersedes,
       (SELECT count(*) FROM documents
         WHERE superseded_by_id IN ('3912b42a-26c9-46ea-b055-b24309083608',
                                    'b769abb0-6d2f-4003-be9b-e62099b5a03a')) AS ref_superseded_by,
       (SELECT count(*) FROM document_group_members
         WHERE document_id      IN ('3912b42a-26c9-46ea-b055-b24309083608',
                                    'b769abb0-6d2f-4003-be9b-e62099b5a03a')) AS ref_group_members;

-- Identidad exacta de lo que se va (para el acta):
--   docA 3912b42a-… `Docs Morley-IAS Lite&Plus - QR`
--        chunk 4847ec7c-992f-4359-aaf0-23c111f57e17 · pm='unknown' · mfr='Morley'
--        doc-level pm='Morley Lite/Plus' · ingested 2026-04-16
--   docB b769abb0-… `Solicitud-asistencia-curso-de-formacion-…-tecnica`
--        chunk db1f6c8b-6512-4945-96c5-6efa113b485b · pm='unknown' · mfr='Morley'
--        doc-level pm='unknown' · language='en' · ingested 2026-04-23


-- ════════════════════════════════════════════════════════════════════════════
-- §2 · DELETE — en orden de dependencia (NO ejecutar sin el visto de Alberto)
-- ════════════════════════════════════════════════════════════════════════════
-- Envolver en transacción; si algún conteo no cuadra → ROLLBACK.

-- BEGIN;

-- 2.1 · chunks_v2 (arrastra en CASCADE sus hyq [5] y enunciados [0], y con la
--       fila se va la columna `embedding`):
-- DELETE FROM chunks_v2
--  WHERE document_id IN ('3912b42a-26c9-46ea-b055-b24309083608',
--                        'b769abb0-6d2f-4003-be9b-e62099b5a03a')
--  RETURNING id, source_file;   -- esperado: 2 filas

-- 2.2 · chunks LEGACY (bloquean el DELETE de documents; corpus OpenAI-1536 no
--       servido en prod). Si se prefiere conservar el legacy intacto, en su
--       lugar hacer `UPDATE chunks SET document_id = NULL WHERE …` — pero
--       entonces el legacy queda con contenido que Alberto mandó eliminar.
--       Recomendación de la lane: borrar (la adjudicación dice "del corpus").
-- DELETE FROM chunks
--  WHERE source_file IN ('Docs Morley-IAS Lite&Plus - QR',
--                        'Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica')
--  RETURNING id, source_file;   -- esperado: 2 filas

-- 2.3 · imagen (fila de metadatos; el objeto de Storage se borra a mano — ver
--       cabecera):
-- DELETE FROM document_visual_assets
--  WHERE document_id IN ('3912b42a-26c9-46ea-b055-b24309083608',
--                        'b769abb0-6d2f-4003-be9b-e62099b5a03a')
--  RETURNING id, storage_url;   -- esperado: 2 filas

-- 2.4 · documento:
-- DELETE FROM documents
--  WHERE id IN ('3912b42a-26c9-46ea-b055-b24309083608',
--               'b769abb0-6d2f-4003-be9b-e62099b5a03a')
--  RETURNING id, source_pdf_filename;   -- esperado: 2 filas

-- COMMIT;


-- ════════════════════════════════════════════════════════════════════════════
-- §3 · VERIFICACIÓN POST-BORRADO
-- ════════════════════════════════════════════════════════════════════════════
-- SELECT count(*) FROM chunks_v2  WHERE source_file IN ('Docs Morley-IAS Lite&Plus - QR',
--        'Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica'); -- 0
-- SELECT count(*) FROM chunks     WHERE source_file IN (…mismos…);                       -- 0
-- SELECT count(*) FROM documents  WHERE id IN ('3912b42a-…','b769abb0-…');               -- 0
-- SELECT count(*) FROM document_visual_assets WHERE document_id IN ('3912b42a-…','b769abb0-…'); -- 0
-- SELECT count(*) FROM chunks_v2_hyq h LEFT JOIN chunks_v2 c ON c.id=h.chunk_id
--  WHERE c.id IS NULL;                                                                   -- 0 (huérfanos)
--
-- Fingerprint del corpus tras el borrado (para el acta y el freeze-contract):
--   chunks_v2 : 25090 → 25088
--   documents :  1171 →  1169
--   unknown   :    227 → 225 (y 1 tras aplicar §1+§4 de s285_t3_final_apply_v1.sql)


-- ════════════════════════════════════════════════════════════════════════════
-- §4 · RESTAURACIÓN (si hubiera que revertir)
-- ════════════════════════════════════════════════════════════════════════════
-- Orden inverso al borrado (padres antes que hijos). Requiere que las tablas de
-- §0 sigan existiendo y que el JPG se haya guardado antes de vaciar Storage.
--
-- INSERT INTO documents              SELECT * FROM _s285_t3_del_documents;
-- INSERT INTO chunks_v2              SELECT * FROM _s285_t3_del_chunks_v2;
-- INSERT INTO chunks                 SELECT * FROM _s285_t3_del_chunks_legacy;
-- INSERT INTO chunks_v2_hyq          SELECT * FROM _s285_t3_del_hyq;
-- INSERT INTO chunks_v2_enunciados   SELECT * FROM _s285_t3_del_enunciados;  -- 0 filas
-- INSERT INTO document_visual_assets SELECT * FROM _s285_t3_del_visual_assets;
-- (+ re-subir los 2 JPG a `manual-images` con la MISMA ruta, o el storage_url
--    restaurado apuntará a un objeto inexistente)
--
-- Limpieza de los respaldos (SOLO cuando Alberto dé el borrado por definitivo):
-- DROP TABLE _s285_t3_del_documents, _s285_t3_del_chunks_v2, _s285_t3_del_chunks_legacy,
--            _s285_t3_del_hyq, _s285_t3_del_enunciados, _s285_t3_del_visual_assets;
