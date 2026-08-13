# -*- coding: utf-8 -*-
"""s320 E2 — Packet de adjudicación: backlog de altas del gobernado (1.235,
por lotes con atestación), 23 bajas-candidatas (1 probada load-bearing por el
gate: VESDA-E-VEP) y gaps del catálogo (feedback a E1)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
pleno = json.loads((ROOT / "evals" / "s320_e2_snapshot_diff_v1.json")
                   .read_text(encoding="utf-8"))
cons = json.loads((ROOT / "evals" / "s320_e2_snapshot_diff_conservador_v1.json")
                  .read_text(encoding="utf-8"))

lineas = ["# s320 E2 — Packet de adjudicación del snapshot del detector", ""]
lineas.append("**Contexto**: el snapshot vivo queda CONDUCTA-IDÉNTICO (gates "
              "PASS); todo cambio de datos viaja aquí. Marca ✓/✗ por lote o "
              "por fila; yo aplico con recibo.")
lineas.append("")
lineas.append(f"## §1 — Backlog de ALTAS del catálogo gobernado "
              f"({len(pleno['altas'])}, en lotes de 50)")
lineas.append("Términos del catálogo gobernado ATESTADOS en corpus activo que "
              "el detector de hoy NO conoce. Entrar = el detector/voz los "
              "reconoce. Ordenados por chunk_count (impacto).")
lineas.append("")
altas = sorted(pleno["altas"], key=lambda a: -(a.get("chunk_count") or 0))
for i, a in enumerate(altas):
    if i % 50 == 0:
        lineas.append(f"### Lote {i // 50 + 1}")
    lineas.append(f"- [ ] `{a['model']}` (via {a.get('via')}, "
                  f"chunks {a.get('chunk_count')})")
lineas.append("")
lineas.append(f"## §2 — BAJAS candidatas ({len(cons['bajas'])} — NINGUNA "
              "auto-aplicada)")
lineas.append("Modelos del snapshot vivo SIN atestación activa exacta. ⚠️ El "
              "gate probó que `VESDA-E-VEP` lo usa una query GOLD (el pm "
              "re-tagueado rompe la atestación exacta) — revisar UNA a UNA:")
lineas.append("")
for b in cons["bajas"]:
    marca = " ⚠️ GOLD" if "vesda-e-vep" in b["model"].lower() else ""
    lineas.append(f"- [ ] retirar `{b['model']}`{marca} — {b['motivo']}")
lineas.append("")
lineas.append("## §3 — GAPS del catálogo (feedback a E1, informativo)")
lineas.append("Modelos vivos atestados en corpus SIN término gobernado — "
              "candidatos a alta en products/aliases (van al flujo E1):")
lineas.append("")
detalle_bajas_pleno = [b for b in pleno["bajas"]
                       if b.get("causa") == "no-en-terminos-gobernados"]
for b in detalle_bajas_pleno[:60]:
    lineas.append(f"- `{b['model']}` (chunks {b.get('chunk_count')})")
if len(detalle_bajas_pleno) > 60:
    lineas.append(f"- … y {len(detalle_bajas_pleno) - 60} más (diff pleno)")

destino = ROOT / "evals" / "s320_e2_packet_adjudicacion_v1.md"
destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
print(f"packet -> {destino} · altas {len(altas)} · bajas {len(cons['bajas'])} "
      f"· gaps {len(detalle_bajas_pleno)}")
