# -*- coding: utf-8 -*-
"""s321 E3 — Packet de adjudicación del residuo (47 parejas · 878 chunks).

Ensambla: atestación (clase + dominancia + hermanas + extracto) + recomendación
LLM (veredicto + confianza + cita verificada) → un MD por secciones con
checkbox. Sección 0 = «aplicables en bloque si asientes» (alta+cita-verificada
+ sin hermanas); el resto por clase. NADA se aplica desde aquí.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

atest = json.loads((ROOT / "evals" / "s321_e3_atestacion_v1.json")
                   .read_text(encoding="utf-8"))
llm = json.loads((ROOT / "evals" / "s321_e3_llm_recomendaciones_v1.json")
                 .read_text(encoding="utf-8"))
por_clave = {(f["document_id"], f["pm_prev"]): f for f in llm["detalle"]}

secciones: dict[str, list[str]] = {"bloque": [], "resto": []}
for clase in ("pm_prev_producto_real", "ambigua_hermanas", "no_dominante",
              "no_atestada"):
    for f in atest["detalle"][clase]:
        rec = por_clave.get((f["document_id"], f["pm_prev"]), {})
        v = rec.get("llm", {})
        bloque = (v.get("confianza") == "alta" and rec.get("cita_verificada")
                  and not f.get("hermanas"))
        linea = (
            f"- [ ] `{f['pm_prev']}` → `{f['canonico']}` · {f['chunks']} chunks "
            f"· {f['source_file'][:55]}\n"
            f"  - clase: {clase} · LLM: **{v.get('veredicto')}** "
            f"({v.get('confianza')}{', cita ✓' if rec.get('cita_verificada') else ''})"
            f"{' · multi: `' + v['multi_valor'] + '`' if v.get('multi_valor') else ''}\n"
            f"  - razón LLM: {v.get('razon')}\n"
            f"  - cita: «{(v.get('cita') or '—')[:160]}»\n"
            f"  - hermanas en content: {list(f.get('hermanas') or {}) or '—'} · "
            f"canon-hits {f.get('hits_canon')} · otros {f.get('otros_top')}\n")
        secciones["bloque" if bloque else "resto"].append(linea)

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
md = f"""# s321 E3 — Packet de adjudicación del residuo del re-tag (generado {utc})

Los 55 docs AUTO ya están aplicados (579 chunks, findability PASS, backup
versionado). Esto es el RESIDUO que exige tus ojos, enriquecido con la pasada
LLM que pediste (claude-fable-5, contenido real, cita verificada).

## §0 — Aplicables EN BLOQUE si asientes ({len(secciones['bloque'])})

Alta confianza + cita verificada en contenido + sin variantes hermanas. Un solo
«sí al §0» tuyo y los aplico con el writer (CAS + findability), fila a fila.

{''.join(secciones['bloque'])}

## §1 — Recomendaciones una a una ({len(secciones['resto'])})

Multi-valor probable, hermanas presentes, o confianza insuficiente — decide
por fila (RETAG / MULTI_VALOR con qué lista / MANTENER / OTRO).

{''.join(secciones['resto'])}

---
*Recibos: `s321_e3_atestacion_v1.json` · `s321_e3_llm_recomendaciones_v1.json`
· writer aplicado `s321_e3_writer_aplicar_20260813T222611Z.json`.*
"""
destino = ROOT / "evals" / "s321_e3_packet_adjudicacion_v1.md"
destino.write_text(md, encoding="utf-8")
print(f"packet -> {destino} · bloque {len(secciones['bloque'])} · "
      f"resto {len(secciones['resto'])}")
