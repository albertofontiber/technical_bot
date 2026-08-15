# -*- coding: utf-8 -*-
"""s322c — Packet E3 v2: la sentada de las 47 parejas, encogida.

Ensambla atestación + recomendaciones v2 (repesca s322c) + carril de
evidencia ONLINE (primer uso del diseño s322b) → tres secciones:
- §0     = alta + cita ✓ (full-text) + sin hermanas → un solo sí en bloque.
- §0-bis = alta + cita ✓ + hermanas presentes PERO resueltas a máquina
           (hermanas_sujeto=unico con SU cita verificada) → un segundo sí.
- §1     = el residuo real, una a una, con la evidencia online adjunta.
SUPERSEDE al packet v1 (que mezclaba 12 parse-fails del bug max_tokens=400
con 17 altas castigadas solo por hermanas). NADA se aplica desde aquí.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

atest = json.loads((ROOT / "evals" / "s321_e3_atestacion_v1.json")
                   .read_text(encoding="utf-8"))
llm = json.loads((ROOT / "evals" / "s321_e3_llm_recomendaciones_v2.json")
                 .read_text(encoding="utf-8"))
online = json.loads((ROOT / "evals" / "s322_e3_online_evidencia_v1.json")
                    .read_text(encoding="utf-8"))["filas"]
por_clave = {(f["document_id"], f["pm_prev"]): f for f in llm["detalle"]}

secciones: dict[str, list[str]] = {"bloque": [], "bis": [], "resto": []}
for clase in ("pm_prev_producto_real", "ambigua_hermanas", "no_dominante",
              "no_atestada"):
    for f in atest["detalle"][clase]:
        rec = por_clave.get((f["document_id"], f["pm_prev"]), {})
        v = rec.get("llm", {})
        alta_cita = v.get("confianza") == "alta" and rec.get("cita_verificada")
        if alta_cita and not f.get("hermanas"):
            destino = "bloque"
        elif alta_cita and rec.get("hermanas_resueltas"):
            destino = "bis"
        else:
            destino = "resto"
        oe = online.get(f"{f['pm_prev']}|{f['source_file'][:55]}")
        linea = (
            f"- [ ] `{f['pm_prev']}` → `{f['canonico']}` · {f['chunks']} chunks "
            f"· {f['source_file'][:55]}\n"
            f"  - clase: {clase} · LLM: **{v.get('veredicto')}** "
            f"({v.get('confianza')}{', cita ✓' if rec.get('cita_verificada') else ''}"
            f"{', hermanas ✓' if f.get('hermanas') and rec.get('hermanas_resueltas') else ''})"
            f"{' · repesca v2' if rec.get('repesca') else ''}"
            f"{' · multi: `' + v['multi_valor'] + '`' if v.get('multi_valor') else ''}\n"
            f"  - razón LLM: {v.get('razon')}\n"
            f"  - cita: «{(v.get('cita') or '—')[:160]}»\n")
        if f.get("hermanas") and v.get("hermanas_cita"):
            linea += (f"  - hermanas ({v.get('hermanas_sujeto')}): "
                      f"«{v['hermanas_cita'][:140]}»\n")
        linea += (f"  - hermanas en content: {list(f.get('hermanas') or {}) or '—'} · "
                  f"canon-hits {f.get('hits_canon')} · otros {f.get('otros_top')}\n")
        if oe:
            linea += (f"  - 🌐 EVIDENCIA ONLINE ({online and '2026-08-14'}): "
                      f"{oe['hallazgo']}\n"
                      f"    → recomendación: {oe['recomendacion']}\n")
            for e in oe["evidencia"]:
                linea += f"    · «{e['quote']}» — {e['url']}\n"
        secciones[destino].append(linea)

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
md = f"""# s321 E3 — Packet de adjudicación v2 (generado {utc} · SUPERSEDE al v1)

Los 55 docs AUTO ya están aplicados. Repesca v2 (s322c): los 12 «parse-fail»
del v1 eran el bug max_tokens=400 (mismo del censo #76), y las hermanas ahora
se resuelven a máquina (`hermanas_sujeto` con cita verificada FULL-TEXT).
Carril de evidencia ONLINE (primer uso) en las filas donde el corpus no llega.
NADA se aplica sin tu sí.

## §0 — Aplicables EN BLOQUE si asientes ({len(secciones['bloque'])})

Alta + cita verificada full-text + sin variantes hermanas. Un «sí al §0» y
los aplico con el writer (CAS + findability), fila a fila.

{''.join(secciones['bloque'])}

## §0-bis — Hermanas RESUELTAS con cita ({len(secciones['bis'])})

Alta + cita ✓ + hermanas presentes, PERO el doc muestra sujeto ÚNICO (las
hermanas son accesorios/referencias) con cita verificada de ese papel. Un
«sí al §0-bis» los aplica igual; si dudas de alguna, sácala a §1.

{''.join(secciones['bis'])}

## §1 — Una a una ({len(secciones['resto'])})

El residuo real — con la evidencia online adjunta (🌐: informa TU decisión;
no se escribe nada de ella sin tu sí).

{''.join(secciones['resto'])}

---
*Recibos: `s321_e3_atestacion_v1.json` · `s321_e3_llm_recomendaciones_v2.json`
(repesca s322c sobre v1 intacto) · `s322_e3_online_evidencia_v1.json` ·
writer aplicado `s321_e3_writer_aplicar_20260813T222611Z.json`.*
"""
destino = ROOT / "evals" / "s321_e3_packet_adjudicacion_v2.md"
destino.write_text(md, encoding="utf-8")
print(f"packet v2 -> {destino}")
print(f"§0 {len(secciones['bloque'])} · §0-bis {len(secciones['bis'])} · "
      f"§1 {len(secciones['resto'])}")
