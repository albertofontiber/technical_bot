# -*- coding: utf-8 -*-
"""s323 — Actualiza EL FICHERO que Alberto abre: `s320_e1_packet_adjudicacion_v2.md`.

Tres cambios pedidos por el:
 1. §0.A (49 colisiones) -> marcada APLICADA (fue la fase A: must_preserve 0/191 -> 191/191).
    Estaba desfasada y le hacia perder tiempo.
 2. §0.B -> REHECHA con la regla serie x categoria, partida en LIMPIAS y PIDEN-TU-OJO.
 3. Hueco «-> TU DECISION:» bajo cada fila que exija criterio suyo.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
v3 = json.loads((ROOT / "evals" / "s323_tierb_v3_serie_x_categoria.json").read_text(encoding="utf-8"))
p = ROOT / "evals" / "s320_e1_packet_adjudicacion_v2.md"
t = p.read_text(encoding="utf-8")

ini = t.index("### §0.A —")
fin = t.index("### §0.C —")

nuevo = ["### §0.A — Colisiones de identidad (49) · ✅ **YA APLICADO, no firmes nada**", "",
         "Era la avería del anexo `must_preserve`: el mapa apuntaba a fichas vacías. Se",
         "reparó en la fase A del mismo día y está **medido**: de **0/191 a 191/191**",
         "entradas atestando. Recibo: `evals/s323_fase_a_repunte_aplicar_*.json`.", "",
         f"### §0.B — `doc_map` tier B, REHECHO con la regla **serie × categoría** "
         f"({len(v3['limpias'])} limpias + {len(v3['piden_tu_ojo'])} a tu criterio)", "",
         "**Por qué se rehizo** (lo viste tú): la guía de la serie 2X-A se asignaba a 2",
         "productos de los 40 de esa serie. El documento no nombra ni un modelo. La regla",
         "buena no es «la serie» (mezcla interfaces distintas) sino **serie × categoría**:",
         "«centrales de la serie NC», no «la serie NC».", "",
         "#### §0.B.1 — LIMPIAS: un solo «sí» las cubre todas", ""]

for f in v3["limpias"]:
    ids = f.get("ids_por_serie_x_categoria") or f["ids_originales"]
    marca = ""
    if f.get("ids_por_serie_x_categoria"):
        marca = (f" · **serie {f['serie']} × {f['categoria_declarada']}** "
                 f"({len(ids)} ids; la pasada original proponía {len(f['ids_originales'])})")
    nuevo += [f"- [ ] `{f['documento'][:58]}`{marca}",
              f"      → {', '.join(f'`{i}`' for i in ids) if ids else '(sin ids)'}",
              f"      cita: «{f['cita'][:100]}»", ""]

nuevo += ["", "#### §0.B.2 — PIDEN TU OJO: la máquina se para y te lo pasa", ""]
for f in v3["piden_tu_ojo"]:
    nuevo += [f"- [ ] `{f['documento'][:58]}`",
              f"      motivo: **{f['motivo']}**",
              f"      cita: «{f['cita'][:100]}»",
              f"      asignación de la pasada original: "
              f"{', '.join(f'`{i}`' for i in f['ids_originales']) or '(ninguna)'}",
              "      → TU DECISIÓN: ", ""]

t = t[:ini] + "\n".join(nuevo) + "\n" + t[fin:]
p.write_text(t, encoding="utf-8")
print(f"packet actualizado: §0.A marcada aplicada · §0.B {len(v3['limpias'])}+{len(v3['piden_tu_ojo'])} con hueco de decisión")
