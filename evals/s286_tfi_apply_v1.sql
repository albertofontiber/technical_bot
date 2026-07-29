-- s286 micro-patch t.Fi→t.A (chunk 475a8f18, HLSI-MN-103 p63; píxel verificado:
-- evals/s286_renders/HLSI-MN-103_p063.png — el display dice t.A). Staging pre-cargada.
BEGIN;
INSERT INTO _s286_tachados_backup
SELECT c.id, c.content, c.section_title, c.section_path, c.context, c.embedding, c.duplicate_of, now()
FROM chunks_v2 c WHERE c.id = '475a8f18-7c69-4c7a-8111-45bd67334c96';
WITH upd AS (
  UPDATE chunks_v2 c SET content = s.new_content, embedding = s.new_embedding
  FROM _s286_tfi_staging s
  WHERE c.id = s.id AND md5(c.content) = s.md5_before
  RETURNING c.id)
SELECT count(*) AS updated INTO TEMP t_u FROM upd;
DO $$ DECLARE n int; BEGIN SELECT updated INTO n FROM t_u;
  IF n <> 1 THEN RAISE EXCEPTION 'updated % <> 1 (deriva) — ABORTA', n; END IF; END $$;
SELECT 1 AS updated_ok;
COMMIT;