-- s286 tachados-apply — limpieza de énfasis mal renderizado (~~) + retiro del duplicado P2.
-- GENERADO por scripts/s286_tachados_stage.py. Spec: evals/s286_tachados_design_v1_1.md.
-- Adjudicación: packet s285 (marcas de Alberto) + arrastre clase-3 (LQAS sellado).
-- Los datos pesados viajan en _s286_tachados_staging (cargada, con embeddings pre-computados);
-- este paste hace el intercambio ATÓMICO. Esperado: 907 filas UPDATE (837 con embedding),
-- 1 duplicate_of marcado, 3 hyq borradas (con backup).
-- Dry-run: cambia COMMIT por ROLLBACK.

BEGIN;

-- 1. BACKUP completo (texto + vector + duplicate_of) — persistente para rollback
CREATE TABLE IF NOT EXISTS _s286_tachados_backup AS
SELECT c.id, c.content, c.section_title, c.section_path, c.context, c.embedding,
       c.duplicate_of, now() AS backed_at
FROM chunks_v2 c
WHERE c.id IN (SELECT id FROM _s286_tachados_staging)
   OR c.id = '2113ac69-52c0-4a7e-a34c-3da1336b4927';

CREATE TABLE IF NOT EXISTS _s286_tachados_del_hyq AS
SELECT h.*, now() AS backed_at FROM chunks_v2_hyq h WHERE h.id IN ('2700aec4-2eac-4f95-971a-83e027c65091', 'e7274df9-5400-4a45-8873-5d5fd3e1f8be', '0b0fed95-fee8-4aab-9bc7-6c166f418e89');

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM _s286_tachados_staging;
  IF n <> 907 THEN RAISE EXCEPTION 'staging % <> 907', n; END IF;
  SELECT count(*) INTO n FROM _s286_tachados_backup;
  IF n <> 908 THEN RAISE EXCEPTION 'backup % <> 908', n; END IF;
END $$;

-- 2. UPDATE-join atómico con guard anti-deriva md5 POR COLUMNA tocada
WITH upd AS (
  UPDATE chunks_v2 c SET
    content       = COALESCE(s.new_content, c.content),
    section_title = COALESCE(s.new_section_title, c.section_title),
    section_path  = COALESCE(s.new_section_path, c.section_path),
    context       = COALESCE(s.new_context, c.context),
    embedding     = COALESCE(s.new_embedding, c.embedding)
  FROM _s286_tachados_staging s
  WHERE c.id = s.id
    AND (s.new_content IS NULL OR md5(c.content) = s.md5_content_before)
    AND (s.new_section_title IS NULL OR md5(c.section_title) = s.md5_title_before)
    AND (s.new_section_path IS NULL OR md5(c.section_path) = s.md5_path_before)
    AND (s.new_context IS NULL OR md5(c.context) = s.md5_context_before)
  RETURNING c.id
)
SELECT count(*) AS updated INTO TEMP tmp_updated FROM upd;

DO $$
DECLARE n int;
BEGIN
  SELECT updated INTO n FROM tmp_updated;
  IF n <> 907 THEN RAISE EXCEPTION 'updated % <> 907 (deriva detectada) — ABORTA TODO', n; END IF;
END $$;

-- 3. Retiro del duplicado corrupto P2 (guard: md5 actual + sin duplicate_of previo)
UPDATE chunks_v2 SET duplicate_of = '18691365-b867-4c39-a75c-be0196ff4b81'
WHERE id = '2113ac69-52c0-4a7e-a34c-3da1336b4927' AND duplicate_of IS NULL AND md5(content) = 'd702247a7be8ddeed2757109c24dec2c';

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM chunks_v2 WHERE id = '2113ac69-52c0-4a7e-a34c-3da1336b4927' AND duplicate_of = '18691365-b867-4c39-a75c-be0196ff4b81';
  IF n <> 1 THEN RAISE EXCEPTION 'retiro del duplicado no aplicado — ABORTA'; END IF;
END $$;

-- 4. Las 3 hyq del corrupto (ya respaldadas arriba)
DELETE FROM chunks_v2_hyq WHERE id IN ('2700aec4-2eac-4f95-971a-83e027c65091', 'e7274df9-5400-4a45-8873-5d5fd3e1f8be', '0b0fed95-fee8-4aab-9bc7-6c166f418e89');

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM chunks_v2_hyq WHERE chunk_id = '2113ac69-52c0-4a7e-a34c-3da1336b4927';
  IF n <> 0 THEN RAISE EXCEPTION 'quedan hyq del corrupto'; END IF;
END $$;

SELECT (SELECT count(*) FROM _s286_tachados_backup)  AS backup_rows,
       (SELECT updated FROM tmp_updated)             AS updated_rows,
       3                                             AS hyq_borradas;

-- ROLLBACK post-COMMIT (si hiciera falta): UPDATE chunks_v2 c SET content=b.content,
--   section_title=b.section_title, section_path=b.section_path, context=b.context,
--   embedding=b.embedding, duplicate_of=b.duplicate_of
--   FROM _s286_tachados_backup b WHERE c.id=b.id;
--   INSERT INTO chunks_v2_hyq SELECT (columnas) FROM _s286_tachados_del_hyq;

COMMIT;   -- <-- para dry-run: ROLLBACK
