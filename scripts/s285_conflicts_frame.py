"""s285 — extrae el frame de CONFLICTOS del QA s83 (v3) para el packet de adjudicación.

Conflicto = el s83 propone un valor y la DB YA tiene otro distinto (fill-only lo saltó):
  - doc_type_flag == 'differ'
  - language_flag == 'contradict'
Read-only sobre DB (join source_file -> documents para el valor vigente).
Salida: evals/s285_conflicts_frame_v1.json
"""
from __future__ import annotations

import json
import os

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = {}
with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v

data = json.load(open(os.path.join(ROOT, "evals", "s282_qa_s83_result_v3.json"), encoding="utf-8"))
recs = data["records"]

conflicts = [
    r
    for r in recs
    if r.get("doc_type_flag") == "differ" or r.get("language_flag") == "contradict"
]
print(f"filas en conflicto: {len(conflicts)} "
      f"(doc_type differ: {sum(1 for r in conflicts if r.get('doc_type_flag') == 'differ')}, "
      f"language contradict: {sum(1 for r in conflicts if r.get('language_flag') == 'contradict')}, "
      f"ambos: {sum(1 for r in conflicts if r.get('doc_type_flag') == 'differ' and r.get('language_flag') == 'contradict')})")

conn = psycopg2.connect(env["DATABASE_URL"])
cur = conn.cursor()
sfs = [r["source_file"] for r in conflicts]
cur.execute(
    """
    SELECT DISTINCT c.source_file, d.id::text, d.doc_type, d.language, d.product_model,
           d.manufacturer, d.status
    FROM chunks_v2 c JOIN documents d ON d.id = c.document_id
    WHERE c.source_file = ANY(%s)
    """,
    (sfs,),
)
db = {row[0]: row[1:] for row in cur.fetchall()}
conn.close()

out = []
for r in conflicts:
    hit = db.get(r["source_file"])
    fill = r.get("fill_plan") or {}
    out.append(
        {
            "source_file": r["source_file"],
            "brand": r.get("brand"),
            "document_id": hit[0] if hit else None,
            "db_status": hit[5] if hit else "NO_ENCONTRADO",
            "conflicto_doc_type": r.get("doc_type_flag") == "differ",
            "db_doc_type": hit[1] if hit else None,
            "s83_doc_type": fill.get("doc_type"),
            "conflicto_language": r.get("language_flag") == "contradict",
            "db_language": hit[2] if hit else None,
            "s83_language": fill.get("language"),
            "s83_confidence": r.get("s83_confidence"),
            "write_op": r.get("write_op"),
            "nota": r.get("write_op_note"),
        }
    )

dest = os.path.join(ROOT, "evals", "s285_conflicts_frame_v1.json")
json.dump({"n": len(out), "criterio": "doc_type differ OR language contradict (frame v3 congelado)",
           "rows": out}, open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"escrito {dest} · en DB: {sum(1 for o in out if o['document_id'])} / {len(out)}")
