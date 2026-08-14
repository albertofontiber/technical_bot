# -*- coding: utf-8 -*-
"""s322 #76 — GATE de precisión vs mini-GT + PACKET de adjudicación.

Gate (r27 Sol M3, pre-registrado): precisión de la ALTA-confianza contra el GT
sin-duda ≥95% en categoría (y sin contradicción en tecnologia/lazos donde el GT
los tiene) — o la población NO sale del recibo. Cobertura = informativa.

Packet: §0 = alta+citas-verificadas (aplicable EN BLOQUE con el sí de Alberto)
· §1 = media/baja una-a-una · nota de enum-semántica (analogica≈direccionable).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

pob = json.loads((ROOT / "evals" / "s322_76_poblacion_v1.json")
                 .read_text(encoding="utf-8"))
gt = yaml.safe_load((ROOT / "evals" / "s322_76_gt_v1.yaml")
                    .read_text(encoding="utf-8"))
gt_por_id = {g["id"]: g for g in gt}
por_id = {f["id"]: f for f in pob["detalle"]}

# ---- GATE ----
aciertos = fallos = 0
detalle_gate = []
for g in gt:
    if g.get("duda"):
        continue
    f = por_id.get(g["id"])
    if not f or f["llm"].get("confianza") != "alta":
        continue                     # el gate mide PRECISIÓN de la alta, no cobertura
    v = f["llm"]
    ok = v.get("categoria") == g["categoria"]
    if ok and g.get("tecnologia"):
        tec = v.get("tecnologia")
        ok = tec in (None, "null") or tec == g["tecnologia"]
    if ok and g.get("lazos") and not g.get("duda_lazos") and v.get("lazos"):
        ok = any(lz.get("base") == g["lazos"]["base"]
                 and lz.get("max", lz.get("base")) == g["lazos"]["max"]
                 for lz in v["lazos"])
    aciertos += ok
    fallos += (not ok)
    detalle_gate.append({"id": g["id"], "ok": ok,
                         "gt": {k: g.get(k) for k in
                                ("categoria", "tecnologia", "lazos")},
                         "llm": {k: v.get(k) for k in
                                 ("categoria", "tecnologia", "lazos")}})
n = aciertos + fallos
precision = aciertos / n if n else 0.0
gate_pass = n >= 10 and precision >= 0.95

# ---- PACKET ----
bloque, resto = [], []
for f in pob["detalle"]:
    v = f["llm"]
    linea = (f"- [ ] `{f['id']}` ({f['canonical']}) → "
             f"**{v.get('categoria')}**"
             f"{' · ' + v['tecnologia'] if v.get('tecnologia') not in (None, 'null') else ''}"
             f"{' · lazos ' + '/'.join(str(l.get('base')) for l in v['lazos']) if v.get('lazos') else ''}"
             f" ({v.get('confianza')}{', citas ✓' if f.get('citas_verificadas') else ''})\n"
             f"  - cita: «{(v.get('categoria_cita') or '—')[:120]}»\n")
    if v.get("confianza") == "alta" and f.get("citas_verificadas"):
        bloque.append(linea)
    else:
        resto.append(linea)

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
md = f"""# s322 #76 — Packet de POBLACIÓN del catálogo (generado {utc})

**GATE de precisión (pre-registrado)**: alta-confianza vs mini-GT sin-duda →
**{aciertos}/{n} = {precision:.0%}** → **{'PASS' if gate_pass else 'FAIL — la población NO sale de este recibo'}**.
(GT: 30 etiquetados a mano leyendo docs ANTES de la pasada; recibo del gate abajo.)

**Nota de enum-semántica para tu adjudicación**: `analogica` ≈ direccionable/
inteligente/addressable (uso PCI-ES estándar; Detnov escribe «analógica», Kidde
«addressable»). Si prefieres separarlas, dilo y re-etiqueto.

## §0 — Aplicables EN BLOQUE con tu sí ({len(bloque)})

Alta confianza + citas verificadas contra el contenido. Un «sí al §0» y las
escribo vía la puerta (validación completa + recibo).

{''.join(bloque)}

## §1 — Una a una ({len(resto)})

{''.join(resto)}

---
*Recibos: `s322_76_poblacion_v1.json` · `s322_76_gt_v1.yaml` ·
gate: {json.dumps({'aciertos': aciertos, 'n': n, 'precision': round(precision, 3), 'pass': gate_pass})}*
"""
(ROOT / "evals" / "s322_76_packet_adjudicacion_v1.md").write_text(
    md, encoding="utf-8")
recibo_gate = {"utc": utc, "aciertos": aciertos, "n": n,
               "precision": round(precision, 4), "gate_pass": gate_pass,
               "umbral": 0.95, "detalle": detalle_gate,
               "resumen_poblacion": pob["resumen"]}
(ROOT / "evals" / "s322_76_gate_gt_v1.json").write_text(
    json.dumps(recibo_gate, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"gate: {aciertos}/{n} = {precision:.0%} -> "
      f"{'PASS' if gate_pass else 'FAIL'} · §0 {len(bloque)} · §1 {len(resto)}")
