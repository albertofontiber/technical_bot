"""s285 — genera el par apply/rollback de los conflictos adjudicados (frame v2 + hilo Alberto).

100% DETERMINISTA desde git (sin DB): frame v2 + constantes del manifest T2. Post-dúo r1 (Sol):
  - F1 guard anti-deriva ATÓMICO (predicados de before-image en el WHERE del UPDATE + conteo);
  - F2 UCIP-Tabla: language='es' adjudicado (prosa española, chunk_lang=es; el ['en','es'] del
    s83 son token-languages [lección MADT609], no idioma de redacción) → sin mecanismo clear;
  - F3 rollback EXPLÍCITO generado (s285_conflicts_rollback_v1.sql), no anunciado;
  - F4 VLF desde constantes del manifest T2 en git (reproducible post-apply);
  - F5 guard de correspondencia source_file↔document_id vía chunks_v2;
  - F6 conteos esperados como LITERALES adjudicados (75/19/65), no derivados del resultado.

Adjudicaciones de Alberto (28-jul, hilo): VESDA VEP + VLF-250/500 → 'instalacion' (consistencia
género Product Guide, pisa T2 con firma nueva); RS232 mixto → eje doc_type RETIRADO;
Puedo-anular-clave → 'operacion'; UCIP-Tabla → language='es' (ver arriba).
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME = os.path.join(ROOT, "evals", "s285_conflicts_frame_v2.json")

N_ESPERADO, N_DT_ESPERADO, N_LANG_ESPERADO = 75, 19, 65

ADJUDICACIONES_DOC_TYPE = {
    "DXC-Connexion-Instalacion-y-configuracion-del-modulo-de-comunicacion-RS232": None,
    "DXC-Puedo-anular-la-clave-de-usuario-y-acceder-directamente-al-teclado": "operacion",
}
ADJUDICACIONES_LANGUAGE = {
    "UCIP-Tabla-de-compatibilidad-con-receptoras-y-centrales": "es",
}
VESDA = "33976_13_VESDA-E_VEP-A00-P_Product_Guide_A4_Spanish_lores"
# ids + before-image del manifest T2 (evals/s282_t2_apply_v1.sql, en git — T2 escribió guia_usuario)
VLF = [
    ("144d759a-400f-44e7-8496-e5ffd706ec5e", "11369_22_VESDA_VLF-250_Product_Guide_A4_Spanish_lores"),
    ("e2c7c875-aa95-4b3c-9ce2-3a2988f94ca8", "11370_17_VESDA_VLF-500_Product_Guide_A4_Spanish_lores"),
]

rows = json.load(open(FRAME, encoding="utf-8"))["rows"]

out = []
for r in rows:
    rec = r["recomendacion"]
    if rec == "s83":
        new_dt = old_dt = new_lang = old_lang = None
        if r["conflicto_doc_type"]:
            new_dt, old_dt = r["s83_doc_type_real"], r["db_doc_type"]
            if r["source_file"] in ADJUDICACIONES_DOC_TYPE:
                adj = ADJUDICACIONES_DOC_TYPE[r["source_file"]]
                new_dt, old_dt = (adj, r["db_doc_type"]) if adj else (None, None)
            elif not isinstance(new_dt, str) or not new_dt:
                # anti fail-open (dúo r1, sub-agente MENOR-2): un eje EN CONFLICTO sin valor
                # escalar y sin adjudicación explícita NUNCA se dropea en silencio
                raise SystemExit(f"eje doc_type en conflicto sin valor escalar: {r['source_file']} {new_dt!r}")
        if r["conflicto_language"]:
            new_lang, old_lang = r["s83_language_real"], r["db_language"]
            if r["source_file"] in ADJUDICACIONES_LANGUAGE:
                new_lang = ADJUDICACIONES_LANGUAGE[r["source_file"]]
            elif not isinstance(new_lang, str) or not new_lang:
                raise SystemExit(f"eje language en conflicto sin valor escalar: {r['source_file']} {new_lang!r}")
        out.append({"document_id": r["document_id"], "source_file": r["source_file"],
                    "new_doc_type": new_dt, "old_doc_type": old_dt,
                    "new_language": new_lang, "old_language": old_lang})
    elif rec == "ninguno_refutada" and r["source_file"] == VESDA:
        out.append({"document_id": r["document_id"], "source_file": r["source_file"],
                    "new_doc_type": "instalacion", "old_doc_type": r["db_doc_type"],
                    "new_language": None, "old_language": None})

for did, sf in VLF:
    out.append({"document_id": did, "source_file": sf,
                "new_doc_type": "instalacion", "old_doc_type": "guia_usuario",
                "new_language": None, "old_language": None})

n = len(out)
n_dt = sum(1 for o in out if o["new_doc_type"])
n_lang = sum(1 for o in out if o["new_language"])
assert n == N_ESPERADO, f"filas {n} != {N_ESPERADO}"
assert n_dt == N_DT_ESPERADO, f"doc_type {n_dt} != {N_DT_ESPERADO}"
assert n_lang == N_LANG_ESPERADO, f"language {n_lang} != {N_LANG_ESPERADO}"
ids = [o["document_id"] for o in out]
assert len(set(ids)) == n and all(ids), "ids duplicados o nulos"
print(f"filas {n} · doc_type {n_dt} · language {n_lang} — contratos literales OK")


def lit(s: str | None) -> str:
    return "NULL" if s is None else "'" + s.replace("'", "''") + "'"


def render(dest: str, titulo: str, inverso: bool) -> None:
    """inverso=False → apply (escribe new, exige old). inverso=True → rollback (escribe old, exige new)."""
    filas = []
    for o in sorted(out, key=lambda o: o["source_file"]):
        set_dt, exp_dt = (o["old_doc_type"], o["new_doc_type"]) if inverso else (o["new_doc_type"], o["old_doc_type"])
        set_lang, exp_lang = (o["old_language"], o["new_language"]) if inverso else (o["new_language"], o["old_language"])
        # eje no tocado: sin set NI expectativa; eje tocado: set puede ser NULL explícito (restaurar NULL)
        touch_dt = o["new_doc_type"] is not None
        touch_lang = o["new_language"] is not None
        filas.append(
            f"  ('{o['document_id']}', {lit(o['source_file'])}, "
            f"{'true' if touch_dt else 'false'}, {lit(set_dt)}, {lit(exp_dt)}, "
            f"{'true' if touch_lang else 'false'}, {lit(set_lang)}, {lit(exp_lang)})"
        )
    values = ",\n".join(filas)
    sql = f"""-- {titulo}
-- GENERADO por scripts/s285_conflicts_apply_gen.py (determinista desde git; ver docstring).
-- Adjudicación: packet s285_conflicts_packet_v2.md + hilo 28-jul (OK Alberto; VESDA/VLF;
-- RS232 retirado; Puedo-anular='operacion'; UCIP-Tabla language='es').
-- Esperado: {n} filas UPDATE · {n_dt} doc_type · {n_lang} language.
-- GUARD ATÓMICO: los predicados de before-image viven en el WHERE del UPDATE; si CUALQUIER
-- fila no coincide, el conteo falla y la transacción entera aborta (all-or-nothing).
-- Dry-run: cambia el COMMIT final por ROLLBACK.

BEGIN;

CREATE TEMP TABLE conf_staging (
  document_id  uuid PRIMARY KEY,
  source_file  text NOT NULL,
  touch_doc_type boolean NOT NULL,
  set_doc_type text,
  expect_doc_type text,
  touch_language boolean NOT NULL,
  set_language text,
  expect_language text
) ON COMMIT DROP;

INSERT INTO conf_staging VALUES
{values};

DO $$
DECLARE n_stage int; n_missing int; n_map int; n_drift int;
BEGIN
  SELECT count(*) INTO n_stage FROM conf_staging;
  IF n_stage <> {n} THEN RAISE EXCEPTION 'staging % <> {n}', n_stage; END IF;

  SELECT count(*) INTO n_missing FROM conf_staging s
    LEFT JOIN documents d ON d.id = s.document_id
    WHERE d.id IS NULL OR d.status <> 'active';
  IF n_missing <> 0 THEN RAISE EXCEPTION '% document_id inexistentes o no-active', n_missing; END IF;

  -- correspondencia source_file <-> document_id (anti id-equivocado)
  SELECT count(*) INTO n_map FROM conf_staging s
    WHERE NOT EXISTS (SELECT 1 FROM chunks_v2 c
                      WHERE c.document_id = s.document_id AND c.source_file = s.source_file);
  IF n_map <> 0 THEN RAISE EXCEPTION '% filas sin chunk que ligue source_file<->document_id', n_map; END IF;

  -- pre-check informativo de deriva (el guard REAL es el WHERE del UPDATE)
  SELECT count(*) INTO n_drift FROM conf_staging s JOIN documents d ON d.id = s.document_id
    WHERE (s.touch_doc_type AND d.doc_type IS DISTINCT FROM s.expect_doc_type)
       OR (s.touch_language AND d.language IS DISTINCT FROM s.expect_language);
  IF n_drift <> 0 THEN RAISE EXCEPTION 'DERIVA: % filas con valor actual != esperado — NO se aplica nada', n_drift; END IF;
END $$;

CREATE TEMP TABLE conf_audit (
  document_id uuid, source_file text,
  set_doc_type text, expect_doc_type text, touch_doc_type boolean,
  set_language text, expect_language text, touch_language boolean
) ON COMMIT DROP;

WITH upd AS (
  UPDATE documents d SET
    doc_type = CASE WHEN s.touch_doc_type THEN s.set_doc_type ELSE d.doc_type END,
    language = CASE WHEN s.touch_language THEN s.set_language ELSE d.language END
  FROM conf_staging s
  WHERE d.id = s.document_id
    AND (NOT s.touch_doc_type OR d.doc_type IS NOT DISTINCT FROM s.expect_doc_type)
    AND (NOT s.touch_language OR d.language IS NOT DISTINCT FROM s.expect_language)
  RETURNING d.id, s.source_file, s.set_doc_type, s.expect_doc_type, s.touch_doc_type,
            s.set_language, s.expect_language, s.touch_language
)
INSERT INTO conf_audit SELECT * FROM upd;

DO $$
DECLARE n_upd int; n_dt int; n_lang int;
BEGIN
  SELECT count(*) INTO n_upd FROM conf_audit;
  SELECT count(*) INTO n_dt   FROM conf_audit WHERE touch_doc_type;
  SELECT count(*) INTO n_lang FROM conf_audit WHERE touch_language;
  RAISE NOTICE '{titulo.split(" — ")[0]}: updated=% doc_type=% language=%', n_upd, n_dt, n_lang;
  IF n_upd  <> {n} THEN RAISE EXCEPTION 'updated % <> {n} (deriva concurrente o id perdido) — la transaccion aborta entera', n_upd; END IF;
  IF n_dt   <> {n_dt} THEN RAISE EXCEPTION 'doc_type % <> {n_dt}', n_dt; END IF;
  IF n_lang <> {n_lang} THEN RAISE EXCEPTION 'language % <> {n_lang}', n_lang; END IF;
END $$;

SELECT document_id, source_file, set_doc_type, expect_doc_type, set_language, expect_language
FROM conf_audit ORDER BY source_file;

COMMIT;   -- <-- para dry-run: cambiar por ROLLBACK
"""
    open(dest, "w", encoding="utf-8", newline="\n").write(sql)
    print("escrito", dest)


render(os.path.join(ROOT, "evals", "s285_conflicts_apply_v1.sql"),
       "s285 conflicts-apply — corrección adjudicada de doc_type/language sobre `documents`", False)
render(os.path.join(ROOT, "evals", "s285_conflicts_rollback_v1.sql"),
       "s285 conflicts-ROLLBACK — restaura los valores previos (inverso exacto del apply)", True)
