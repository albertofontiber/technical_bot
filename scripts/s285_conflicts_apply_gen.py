"""s285 — genera evals/s285_conflicts_apply_v1.sql desde el frame v2 adjudicado por Alberto.

Alcance (adjudicación 28-jul, packet s285_conflicts_packet_v2.md + hilo):
  - 72 filas recommendation='s83'  → corregir la DB al valor s83 en el/los eje(s) EN CONFLICTO.
  - VESDA VEP (ninguno_refutada)   → doc_type='instalacion' (decisión de Alberto).
  - Addendum consistencia (Alberto): VLF-250 y VLF-500 guia_usuario→'instalacion'
    (mismo género Product Guide; pisa el valor T2 con firma nueva).
Contrato T2 endurecido: OVERWRITE deliberado ⇒ guard estricto de before-image
(el valor actual DEBE ser el esperado del frame congelado; si la DB derivó → aborta todo).
"""
from __future__ import annotations

import json
import os

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME = os.path.join(ROOT, "evals", "s285_conflicts_frame_v2.json")
DEST = os.path.join(ROOT, "evals", "s285_conflicts_apply_v1.sql")

env = {}
with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v

rows = json.load(open(FRAME, encoding="utf-8"))["rows"]

# Adjudicaciones de Alberto en el hilo (28-jul) que MODIFICAN el eje doc_type del frame:
#  - RS232: título «Instalación y configuración» = MIXTO real → NO se pisa el valor defendible
#    de la DB ('instalacion'); el eje doc_type se RETIRA (solo se corrige language de→es).
#  - Puedo-anular-clave: 'otro' (s83) es cajón de sastre; contenido = operativa del panel
#    (acceso teclado, EN54-2, kit llave) → 'operacion'. DB 'usuario' además fuera de taxonomía.
ADJUDICACIONES_DOC_TYPE = {
    "DXC-Connexion-Instalacion-y-configuracion-del-modulo-de-comunicacion-RS232": None,
    "DXC-Puedo-anular-la-clave-de-usuario-y-acceder-directamente-al-teclado": "operacion",
}

VESDA = "33976_13_VESDA-E_VEP-A00-P_Product_Guide_A4_Spanish_lores"
out = []
problemas = []
for r in rows:
    rec = r["recomendacion"]
    if rec == "s83":
        new_dt = old_dt = new_lang = old_lang = None
        if r["conflicto_doc_type"]:
            new_dt, old_dt = r["s83_doc_type_real"], r["db_doc_type"]
            if r["source_file"] in ADJUDICACIONES_DOC_TYPE:
                adj = ADJUDICACIONES_DOC_TYPE[r["source_file"]]
                new_dt, old_dt = (adj, r["db_doc_type"]) if adj else (None, None)
            if new_dt is not None and (not new_dt or not isinstance(new_dt, str)):
                problemas.append((r["source_file"], "doc_type no escalar", new_dt))
        clear_lang = False
        if r["conflicto_language"]:
            new_lang, old_lang = r["s83_language_real"], r["db_language"]
            if isinstance(new_lang, list):
                # doc multi-idioma: el valor DB es falso pero NO existe convención escalar
                # (política T2) → se LIMPIA a NULL y el doc se une al pool advisory de 209.
                new_lang, clear_lang = None, True
            elif not new_lang or not isinstance(new_lang, str):
                problemas.append((r["source_file"], "s83_language_real no escalar", new_lang))
        out.append({"document_id": r["document_id"], "source_file": r["source_file"],
                    "new_doc_type": new_dt, "old_doc_type": old_dt,
                    "new_language": new_lang, "old_language": old_lang,
                    "clear_language": clear_lang})
    elif rec == "ninguno_refutada" and r["source_file"] == VESDA:
        out.append({"document_id": r["document_id"], "source_file": r["source_file"],
                    "new_doc_type": "instalacion", "old_doc_type": r["db_doc_type"],
                    "new_language": None, "old_language": None, "clear_language": False})

if problemas:
    raise SystemExit(f"ABORT — valores no escalares: {problemas}")

# addendum VLF (ids vivos por source_file; valor esperado = el que escribió T2)
conn = psycopg2.connect(env["DATABASE_URL"])
cur = conn.cursor()
for sf in ("11369_22_VESDA_VLF-250_Product_Guide_A4_Spanish_lores",
           "11370_17_VESDA_VLF-500_Product_Guide_A4_Spanish_lores"):
    cur.execute(
        "SELECT DISTINCT d.id::text, d.doc_type FROM chunks_v2 c "
        "JOIN documents d ON d.id=c.document_id WHERE c.source_file=%s AND d.status='active'",
        (sf,),
    )
    hits = cur.fetchall()
    assert len(hits) == 1, f"{sf}: {len(hits)} docs"
    did, cur_dt = hits[0]
    assert cur_dt == "guia_usuario", f"{sf}: doc_type actual {cur_dt!r} != 'guia_usuario' esperado"
    out.append({"document_id": did, "source_file": sf,
                "new_doc_type": "instalacion", "old_doc_type": "guia_usuario",
                "new_language": None, "old_language": None, "clear_language": False})
conn.close()

n = len(out)
n_dt = sum(1 for o in out if o["new_doc_type"])
n_lang = sum(1 for o in out if o["new_language"])
n_clear = sum(1 for o in out if o["clear_language"])
assert n == 75, f"filas {n} != 75"
ids = [o["document_id"] for o in out]
assert len(set(ids)) == n and all(ids), "ids duplicados o nulos"
print(f"filas {n} · doc_type sets {n_dt} · language sets {n_lang} · language clears {n_clear}")


def lit(s: str | None) -> str:
    return "NULL" if s is None else "'" + s.replace("'", "''") + "'"


values = ",\n".join(
    f"  ('{o['document_id']}', {lit(o['source_file'])}, {lit(o['new_doc_type'])}, "
    f"{lit(o['old_doc_type'])}, {lit(o['new_language'])}, {lit(o['old_language'])}, "
    f"{'true' if o['clear_language'] else 'false'})"
    for o in sorted(out, key=lambda o: o["source_file"])
)

sql = f"""-- s285 conflicts-apply — corrección adjudicada de doc_type/language sobre `documents`.
-- GENERADO por scripts/s285_conflicts_apply_gen.py desde s285_conflicts_frame_v2.json.
-- Adjudicación: packet s285_conflicts_packet_v2.md, «OK» de Alberto 28-jul-2026 + decisión
-- VESDA='instalacion' con addendum de consistencia VLF-250/VLF-500 (pisa T2 con firma nueva).
-- CONTRATO: OVERWRITE deliberado con guard ESTRICTO de before-image — cada valor actual debe
-- ser EXACTAMENTE el esperado del frame congelado; cualquier deriva ⇒ aborta TODO.
-- Esperado: {n} filas UPDATE · {n_dt} doc_type set · {n_lang} language set · {n_clear} language
-- LIMPIADO a NULL (doc multi-idioma con valor DB falso; sin convención escalar → pool advisory).
-- Dry-run: cambia el COMMIT final por ROLLBACK.

BEGIN;

CREATE TEMP TABLE conf_staging (
  document_id  uuid PRIMARY KEY,
  source_file  text NOT NULL,
  new_doc_type text,
  old_doc_type_expected text,
  new_language text,
  old_language_expected text,
  clear_language boolean NOT NULL
) ON COMMIT DROP;

INSERT INTO conf_staging VALUES
{values};

DO $$
DECLARE n_stage int; n_missing int; n_drift int;
BEGIN
  SELECT count(*) INTO n_stage FROM conf_staging;
  IF n_stage <> {n} THEN RAISE EXCEPTION 'staging % <> {n}', n_stage; END IF;

  SELECT count(*) INTO n_missing FROM conf_staging s
    LEFT JOIN documents d ON d.id = s.document_id
    WHERE d.id IS NULL OR d.status <> 'active';
  IF n_missing <> 0 THEN RAISE EXCEPTION '% document_id inexistentes o no-active', n_missing; END IF;

  -- guard ESTRICTO anti-deriva: el valor vigente debe ser el que adjudicamos como erróneo
  SELECT count(*) INTO n_drift FROM conf_staging s JOIN documents d ON d.id = s.document_id
    WHERE (s.new_doc_type IS NOT NULL AND d.doc_type IS DISTINCT FROM s.old_doc_type_expected)
       OR ((s.new_language IS NOT NULL OR s.clear_language)
           AND d.language IS DISTINCT FROM s.old_language_expected);
  IF n_drift <> 0 THEN RAISE EXCEPTION 'DERIVA: % filas con valor actual != esperado — NO se aplica nada', n_drift; END IF;
END $$;

CREATE TEMP TABLE conf_audit (
  document_id uuid, source_file text,
  old_doc_type text, new_doc_type text,
  old_language text, new_language text, cleared_language boolean
) ON COMMIT DROP;

WITH upd AS (
  UPDATE documents d SET
    doc_type = COALESCE(s.new_doc_type, d.doc_type),
    language = CASE WHEN s.clear_language THEN NULL
                    ELSE COALESCE(s.new_language, d.language) END
  FROM conf_staging s
  WHERE d.id = s.document_id
  RETURNING d.id, s.source_file, s.old_doc_type_expected, s.new_doc_type,
            s.old_language_expected, s.new_language, s.clear_language
)
INSERT INTO conf_audit SELECT * FROM upd;

DO $$
DECLARE n_upd int; n_dt int; n_lang int; n_clear int;
BEGIN
  SELECT count(*) INTO n_upd FROM conf_audit;
  SELECT count(*) INTO n_dt    FROM conf_audit WHERE new_doc_type IS NOT NULL;
  SELECT count(*) INTO n_lang  FROM conf_audit WHERE new_language IS NOT NULL;
  SELECT count(*) INTO n_clear FROM conf_audit WHERE cleared_language;
  RAISE NOTICE 'conflicts-apply: updated=% doc_type_set=% language_set=% language_cleared=%',
    n_upd, n_dt, n_lang, n_clear;
  IF n_upd   <> {n} THEN RAISE EXCEPTION 'updated % <> {n}', n_upd; END IF;
  IF n_dt    <> {n_dt} THEN RAISE EXCEPTION 'doc_type_set % <> {n_dt}', n_dt; END IF;
  IF n_lang  <> {n_lang} THEN RAISE EXCEPTION 'language_set % <> {n_lang}', n_lang; END IF;
  IF n_clear <> {n_clear} THEN RAISE EXCEPTION 'language_cleared % <> {n_clear}', n_clear; END IF;
END $$;

-- Before-image (informativo; el rollback NO la necesita: los valores viejos están en el frame v2 en git)
SELECT document_id, source_file, old_doc_type, new_doc_type, old_language, new_language, cleared_language
FROM conf_audit ORDER BY source_file;

-- ROLLBACK post-COMMIT (si hiciera falta): re-ejecuta este mismo fichero cambiando en el INSERT
-- new_*<->old_*_expected (o pídeme el fichero inverso: el frame v2 en git tiene todos los valores).

COMMIT;   -- <-- para dry-run: cambiar por ROLLBACK
"""

open(DEST, "w", encoding="utf-8", newline="\n").write(sql)
print("escrito", DEST)
