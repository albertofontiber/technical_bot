"""s286 — CENSO/manifest de la limpieza de tachados (fase dry, READ-ONLY; spec v1.1).

Aplica el tokenizador a TODAS las columnas del alcance (content, section_title, section_path,
context) de chunks_v2 y produce evals/s286_tachados_manifest_v1.json:
  - por fila: columnas que cambian, sha256 antes/después, nº pares, huérfanos, spans eyeball
  - global: cardinalidades exactas, censo de run-4, censo de huérfanos, top spans para revisión
No escribe NADA en DB.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import psycopg2  # noqa: E402
from s286_tachados_lib import strip_content  # noqa: E402

env = {}
with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v

COLS = ("content", "section_title", "section_path", "context")

conn = psycopg2.connect(env["DATABASE_URL"])
cur = conn.cursor()
cur.execute(
    "SELECT c.id::text, c.source_file, c.page_number, d.status, "
    "c.content, c.section_title, c.section_path, c.context "
    "FROM chunks_v2 c JOIN documents d ON d.id = c.document_id "
    "WHERE c.content LIKE '%~~%' OR c.section_title LIKE '%~~%' "
    "   OR c.section_path LIKE '%~~%' OR c.context LIKE '%~~%'"
)
rows = cur.fetchall()
conn.close()

def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

manifest_rows = []
tot = {c: 0 for c in COLS}
tot_pairs = tot_orphans = tot_run4 = 0
eyeball: list[dict] = []
run4_census: list[dict] = []
need_reembed = 0

for rid, sf, page, status, *vals in rows:
    entry = {"id": rid, "source_file": sf, "page": page, "doc_status": status, "cols": {}}
    embed_input_changes = False
    for col, val in zip(COLS, vals):
        if not val or "~~" not in val:
            continue
        r = strip_content(val)
        if not r.changed and r.orphans == 0 and r.run4_literal == 0:
            continue
        entry["cols"][col] = {
            "sha_before": sha(val), "sha_after": sha(r.text),
            "pares": len(r.pairs), "huerfanos": r.orphans,
            "run4_literales": r.run4_literal, "changed": r.changed,
        }
        if r.changed:
            tot[col] += 1
            if col in ("content", "context"):
                embed_input_changes = True
        tot_pairs += len(r.pairs)
        tot_orphans += r.orphans
        tot_run4 += r.run4_literal
        for s in r.eyeball_flags:
            eyeball.append({"id": rid, "col": col, "span": s[:200]})
        if r.run4_literal:
            run4_census.append({"id": rid, "col": col, "source_file": sf})
    if embed_input_changes:
        need_reembed += 1
    if entry["cols"]:
        manifest_rows.append(entry)

resumen = {
    "filas_tocadas": len(manifest_rows),
    "cambian_por_columna": tot,
    "pares_retirados": tot_pairs,
    "huerfanos_conservados": tot_orphans,
    "run4_literales_conservados": tot_run4,
    "re_embeds_necesarios(content|context)": need_reembed,
    "eyeball_flags": len(eyeball),
}
print(json.dumps(resumen, ensure_ascii=False, indent=1))
print("\nEYEBALL (spans a revisar):")
for e in eyeball:
    print(f"  {e['id'][:8]} [{e['col']}] «{e['span'][:120]}»")
print("\nRUN-4 LITERALES:")
for e in run4_census:
    print(f"  {e['id'][:8]} [{e['col']}] {e['source_file']}")

json.dump({"resumen": resumen, "eyeball": eyeball, "run4_census": run4_census,
           "rows": manifest_rows},
          open(os.path.join(ROOT, "evals", "s286_tachados_manifest_v1.json"), "w",
               encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nmanifest → evals/s286_tachados_manifest_v1.json")
