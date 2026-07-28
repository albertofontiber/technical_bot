"""s285 — ensambla el packet de adjudicación de los 80 conflictos QA s83 vs DB.

Entrada: frame v1 (evals/s285_conflicts_frame_v1.json) + salida del workflow (recomendaciones
verificadas por escépticos). Dedup por (source_file, eje-normalizado); las filas refutadas por
un escéptico se marcan para revisión explícita. Salida: evals/s285_conflicts_packet_v1.md
formato excepción-only.
"""
from __future__ import annotations

import json
import sys
from collections import Counter

FRAME = r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot-s281\evals\s285_conflicts_frame_v1.json"
WF_OUT = sys.argv[1]
DEST = r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot-s281\evals\s285_conflicts_packet_v1.md"

frame = {r["source_file"]: r for r in json.load(open(FRAME, encoding="utf-8"))["rows"]}
wf = json.load(open(WF_OUT, encoding="utf-8"))["result"]

recs: dict[str, dict] = {}
for r in wf["recomendaciones"]:
    sf = r["source_file"]
    if sf not in recs:  # primer lote gana; los duplicados entre lotes coinciden en dirección
        recs[sf] = r

refuted = {v["source_file"]: v for v in wf.get("refutadas", [])}

missing = [sf for sf in frame if sf not in recs]
extra = [sf for sf in recs if sf not in frame]
dist = Counter(r["recomendacion"] for r in recs.values())
conf = Counter(r["confianza"] for r in recs.values())
print(f"frame {len(frame)} · recomendadas únicas {len(recs)} · sin recomendación {len(missing)}"
      f" · fuera de frame {len(extra)} · refutadas {len(refuted)}")
print("distribución:", dict(dist), "· confianza:", dict(conf))
for sf in missing:
    print("  FALTA:", sf)

L: list[str] = []
L.append("# s285 — Packet de adjudicación: los 80 conflictos QA (s83 propone X, la DB tiene Y)\n")
L.append("> **Formato excepción-only:** cada fila lleva recomendación + evidencia leída del corpus")
L.append("> real (14 agentes, escépticos incluidos). **Solo contesta las filas donde DISCREPES**;")
L.append("> con tu «OK» (o «OK salvo #n, #m») genero el SQL de aplicación con el mismo aparato del")
L.append("> T2 (conteos exactos, before-image, rollback) y lo pegas tú. Nada se escribe sin eso.")
L.append(">")
L.append("> Origen: fill-only del T2 SALTÓ estas filas porque la DB ya tenía valor — aquí el s83")
L.append("> CONTRADICE ese valor y hay que decidir cuál es verdad. (DEC-156 citaba «121»: el frame")
L.append("> v3 congelado real son 80 filas.)\n")
L.append("## Resumen\n")
L.append(f"| recomendación | n | significado |")
L.append(f"|---|---|---|")
L.append(f"| **s83** | {dist.get('s83', 0)} | el valor de la DB está MAL; se corrige al del s83 |")
L.append(f"| **db** | {dist.get('db', 0)} | la DB ya está bien; el s83 se equivoca — no se toca nada |")
L.append(f"| **ninguno** | {dist.get('ninguno', 0)} | ambos mal; el valor correcto va en la evidencia |")
L.append(f"| **no_aplica_borrado** | {dist.get('no_aplica_borrado', 0)} | documento borrado en T3 — fila muerta |")
L.append(f"\nConfianza: {dict(conf)}. Refutadas por escéptico (revisión explícita abajo): {len(refuted)}.\n")

if refuted:
    L.append("## ⚠️ Filas donde el escéptico REFUTÓ la recomendación — decide tú estas SÍ o SÍ\n")
    for i, (sf, v) in enumerate(sorted(refuted.items()), 1):
        r = recs.get(sf, {})
        L.append(f"**R{i} · `{sf}`** — recomendación original: `{r.get('recomendacion', '?')}`")
        L.append(f"- Evidencia original: {r.get('evidencia', '—')}")
        L.append(f"- Refutación: {v.get('motivo', '—')}")
        L.append(f"- **TU MARCA:** `[ ] original` · `[ ] refutación` · `[ ] otro: ____`\n")

def bloque(titulo: str, keys: list[str]) -> None:
    if not keys:
        return
    L.append(f"## {titulo} ({len(keys)})\n")
    for i, sf in enumerate(keys, 1):
        r = recs[sf]
        f = frame[sf]
        ejes = []
        if f["conflicto_doc_type"]:
            ejes.append(f"doc_type: DB=`{f['db_doc_type']}` vs s83=`{f['s83_doc_type']}`")
        if f["conflicto_language"]:
            ejes.append(f"language: DB=`{f['db_language']}` vs s83=`{f['s83_language']}`")
        marca_ref = " ⚠️REFUTADA" if sf in refuted else ""
        L.append(f"**#{i} · `{sf}`** ({f['brand']}) — {' · '.join(ejes)}")
        L.append(f"- → **{r['recomendacion']}** (confianza {r['confianza']}){marca_ref}: {r['evidencia']}\n")

orden = sorted(recs, key=lambda s: (recs[s]["recomendacion"], s))
bloque("Corregir la DB al valor s83", [s for s in orden if recs[s]["recomendacion"] == "s83" and s not in refuted])
bloque("La DB ya está bien (s83 se equivoca) — sin cambio", [s for s in orden if recs[s]["recomendacion"] == "db" and s not in refuted])
bloque("Ambos mal — valor correcto en la evidencia", [s for s in orden if recs[s]["recomendacion"] == "ninguno" and s not in refuted])
bloque("Filas muertas (documento borrado en T3)", [s for s in orden if recs[s]["recomendacion"] == "no_aplica_borrado"])

if missing:
    L.append(f"## Sin recomendación automática ({len(missing)}) — las reviso a mano antes del SQL\n")
    for sf in missing:
        L.append(f"- `{sf}`")

L.append("\n## Qué pasa tras tu OK\n")
L.append("Genero `s285_conflicts_apply_v1.sql` (mismo contrato del T2: staging + conteos exactos +")
L.append("before-image + rollback; esta vez es OVERWRITE deliberado de los valores adjudicados como")
L.append("erróneos) → lo pegas → verifico en vivo 1:1.")

open(DEST, "w", encoding="utf-8").write("\n".join(L))
print("escrito", DEST)
