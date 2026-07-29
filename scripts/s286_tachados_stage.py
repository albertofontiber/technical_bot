"""s286 — STAGE de la limpieza de tachados (spec v1.1; post-censo b624494).

Fases (todas ejecutables por separado; DB-writes SOLO a tablas scratch _s286_*):
  1. Computa los valores nuevos de las 907 filas del manifest (tokenizador) + el patch de
     etiquetas de 18691365 (r.t→r.I, LA→t.A; auditando también su blurb) + el retiro del
     duplicado corrupto 2113ac69 (duplicate_of=18691365).
  2. Pre-computa los embeddings nuevos (reusa src/reingest/embed.py: mismo modelo, mismo
     input `context\n\ncontent`[:16000], input_type='document').
  3. Escribe la tabla scratch `_s286_tachados_staging` (id, nuevos valores, md5 de guardas
     del estado actual esperado, embedding nuevo) — NO toca serving.
  4. Genera `evals/s286_tachados_apply_v1.sql` — el paste PEQUEÑO de Alberto: backup completo
     (content+context+títulos+paths+embedding+duplicate_of) → UPDATE-join transaccional con
     guard anti-deriva md5 por columna → marca duplicate_of del corrupto → DELETE con backup
     de sus 3 hyq → guards de conteo exacto → rollback documentado (restaura texto+vector).
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import psycopg2  # noqa: E402
from psycopg2.extras import execute_values  # noqa: E402
from s286_tachados_lib import strip_content  # noqa: E402
from src.reingest.embed import embed  # noqa: E402

env = {}
with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
os.environ.setdefault("VOYAGE_API_KEY", env.get("VOYAGE_API_KEY", ""))

CORRUPTO = "2113ac69-52c0-4a7e-a34c-3da1336b4927"
FIEL = "18691365-b867-4c39-a75c-be0196ff4b81"
COLS = ("content", "section_title", "section_path", "context")

manifest = json.load(open(os.path.join(ROOT, "evals", "s286_tachados_manifest_v1.json"),
                          encoding="utf-8"))

conn = psycopg2.connect(env["DATABASE_URL"])
cur = conn.cursor()

ids = [r["id"] for r in manifest["rows"]]
if FIEL not in ids:
    ids.append(FIEL)
cur.execute(
    "SELECT id::text, content, section_title, section_path, context, duplicate_of::text "
    "FROM chunks_v2 WHERE id = ANY(%s::uuid[])", (ids,))
db = {r[0]: {"content": r[1], "section_title": r[2], "section_path": r[3],
             "context": r[4], "duplicate_of": r[5]} for r in cur.fetchall()}
assert len(db) == len(ids), f"{len(db)} != {len(ids)}"

def md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest() if s is not None else None

stage_rows = []
n_col = {c: 0 for c in COLS}
for row in manifest["rows"]:
    rid = row["id"]
    cur_vals = db[rid]
    new_vals = {}
    for col in COLS:
        v = cur_vals[col]
        if v and "~~" in v:
            r = strip_content(v)
            if r.changed:
                new_vals[col] = r.text
                n_col[col] += 1
    if rid == FIEL:
        pass  # el patch del fiel se añade abajo (no está en el manifest: no tiene ~~)
    if not new_vals:
        continue
    stage_rows.append((rid, new_vals, cur_vals))

# --- patch de etiquetas del chunk FIEL (spec v1.1; verbatim de HLSI-MN-103/render) ---
fiel = db[FIEL]
fc = fiel["content"]
assert fc.count("r.t - Rearme inhibido") == 1, "ancla r.t no única"
assert fc.count("parámetro LA (LA → 0 seg.)") == 1, "ancla LA no única"
fc_new = fc.replace("r.t - Rearme inhibido", "r.I - Rearme inhibido")
fc_new = fc_new.replace("parámetro LA (LA → 0 seg.)", "parámetro t.A (t.A → 0 seg.)")
blurb = fiel["context"] or ""
assert "r.t" not in blurb and "(LA" not in blurb, f"blurb del fiel contaminado: {blurb[:200]}"
stage_rows.append((FIEL, {"content": fc_new}, fiel))
n_col["content"] += 1

print(f"filas staging: {len(stage_rows)} · por columna: {n_col}")

# --- embeddings nuevos (solo filas cuyo input de embedding cambia: content o context) ---
emb_ids, emb_texts = [], []
for rid, new_vals, cur_vals in stage_rows:
    if "content" in new_vals or "context" in new_vals:
        content = new_vals.get("content", cur_vals["content"]) or ""
        context = new_vals.get("context", cur_vals["context"])
        text = f"{context}\n\n{content}" if context else content
        emb_ids.append(rid)
        emb_texts.append(text[:16_000])
print(f"embeddings a computar: {len(emb_ids)}")
vectors = embed(emb_texts, input_type="document")
assert len(vectors) == len(emb_ids) and all(len(v) == 1024 for v in vectors)
emb_by_id = dict(zip(emb_ids, vectors))

# --- staging table (scratch) ---
cur.execute("DROP TABLE IF EXISTS _s286_tachados_staging")
cur.execute("""
CREATE TABLE _s286_tachados_staging (
  id uuid PRIMARY KEY,
  new_content text, md5_content_before text,
  new_section_title text, md5_title_before text,
  new_section_path text, md5_path_before text,
  new_context text, md5_context_before text,
  new_embedding vector(1024)
)""")
rows_sql = []
for rid, new_vals, cur_vals in stage_rows:
    rows_sql.append((
        rid,
        new_vals.get("content"), md5(cur_vals["content"]) if "content" in new_vals else None,
        new_vals.get("section_title"), md5(cur_vals["section_title"]) if "section_title" in new_vals else None,
        new_vals.get("section_path"), md5(cur_vals["section_path"]) if "section_path" in new_vals else None,
        new_vals.get("context"), md5(cur_vals["context"]) if "context" in new_vals else None,
        str(emb_by_id[rid]) if rid in emb_by_id else None,
    ))
execute_values(cur, """
INSERT INTO _s286_tachados_staging
 (id, new_content, md5_content_before, new_section_title, md5_title_before,
  new_section_path, md5_path_before, new_context, md5_context_before, new_embedding)
VALUES %s""", rows_sql)
conn.commit()
print(f"staging cargada: {len(rows_sql)} filas")

# --- las 3 hyq del corrupto (ids exactos para el DELETE del paste) ---
cur.execute("SELECT id::text, question FROM chunks_v2_hyq WHERE chunk_id = %s", (CORRUPTO,))
hyq = cur.fetchall()
print(f"hyq del corrupto: {len(hyq)}")
for h in hyq:
    print("  ", h[0][:8], "·", h[1][:90])
assert len(hyq) == 3
hyq_ids = ", ".join(f"'{h[0]}'" for h in hyq)

# guard del duplicado: md5 actual del corrupto
md5_corrupto = md5(db[CORRUPTO]["content"]) if CORRUPTO in db else None
if md5_corrupto is None:
    cur.execute("SELECT content, duplicate_of::text FROM chunks_v2 WHERE id=%s", (CORRUPTO,))
    c_row = cur.fetchone()
    md5_corrupto = md5(c_row[0])
    assert c_row[1] is None, "el corrupto ya tiene duplicate_of"
conn.close()

N = len(rows_sql)
N_EMB = len(emb_ids)
sql = f"""-- s286 tachados-apply — limpieza de énfasis mal renderizado (~~) + retiro del duplicado P2.
-- GENERADO por scripts/s286_tachados_stage.py. Spec: evals/s286_tachados_design_v1_1.md.
-- Adjudicación: packet s285 (marcas de Alberto) + arrastre clase-3 (LQAS sellado).
-- Los datos pesados viajan en _s286_tachados_staging (cargada, con embeddings pre-computados);
-- este paste hace el intercambio ATÓMICO. Esperado: {N} filas UPDATE ({N_EMB} con embedding),
-- 1 duplicate_of marcado, 3 hyq borradas (con backup).
-- Dry-run: cambia COMMIT por ROLLBACK.

BEGIN;

-- 1. BACKUP completo (texto + vector + duplicate_of) — persistente para rollback
CREATE TABLE IF NOT EXISTS _s286_tachados_backup AS
SELECT c.id, c.content, c.section_title, c.section_path, c.context, c.embedding,
       c.duplicate_of, now() AS backed_at
FROM chunks_v2 c
WHERE c.id IN (SELECT id FROM _s286_tachados_staging)
   OR c.id = '{CORRUPTO}';

CREATE TABLE IF NOT EXISTS _s286_tachados_del_hyq AS
SELECT h.*, now() AS backed_at FROM chunks_v2_hyq h WHERE h.id IN ({hyq_ids});

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM _s286_tachados_staging;
  IF n <> {N} THEN RAISE EXCEPTION 'staging % <> {N}', n; END IF;
  SELECT count(*) INTO n FROM _s286_tachados_backup;
  IF n <> {N + 1} THEN RAISE EXCEPTION 'backup % <> {N + 1}', n; END IF;
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
  IF n <> {N} THEN RAISE EXCEPTION 'updated % <> {N} (deriva detectada) — ABORTA TODO', n; END IF;
END $$;

-- 3. Retiro del duplicado corrupto P2 (guard: md5 actual + sin duplicate_of previo)
UPDATE chunks_v2 SET duplicate_of = '{FIEL}'
WHERE id = '{CORRUPTO}' AND duplicate_of IS NULL AND md5(content) = '{md5_corrupto}';

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM chunks_v2 WHERE id = '{CORRUPTO}' AND duplicate_of = '{FIEL}';
  IF n <> 1 THEN RAISE EXCEPTION 'retiro del duplicado no aplicado — ABORTA'; END IF;
END $$;

-- 4. Las 3 hyq del corrupto (ya respaldadas arriba)
DELETE FROM chunks_v2_hyq WHERE id IN ({hyq_ids});

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM chunks_v2_hyq WHERE chunk_id = '{CORRUPTO}';
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
"""
dest = os.path.join(ROOT, "evals", "s286_tachados_apply_v1.sql")
open(dest, "w", encoding="utf-8", newline="\n").write(sql)
print("paste →", dest, f"· esperado: {N} updates / {N_EMB} embeddings / 1 retiro / 3 hyq")
