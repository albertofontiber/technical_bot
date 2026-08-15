# -*- coding: utf-8 -*-
"""s322i — Arregla los 2 defectos MEDIOS que cazó el verificador adversarial.

(1) TITULAR vs CASILLAS: los tres packets prometían menos decisiones de las
    casillas que ellos mismos imprimen (E1 98 vs 241, E1b 146 vs 432, E2 20 vs
    94). El dato no estaba falseado — la prosa lo estaba. Añade una línea de
    reconciliación explícita: cuántas casillas hay de verdad y qué significan.
(2) ATRIBUCIÓN DE CITA: 5 filas imprimen «prov X» pegado a «cita OK <<...>>» y
    esa cita no está en X (prov es la procedencia del ID, no la fuente de la
    cita). Renombra la etiqueta para que nadie lea una atribución falsa.
Solo toca los .md de los packets. Nada de catálogo, DB ni snapshot.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKETS = {
    "E1": ROOT / "evals" / "s320_e1_packet_adjudicacion_v2.md",
    "E1b": ROOT / "evals" / "s320_e1b_packet_adjudicacion_v2.md",
    "E2": ROOT / "evals" / "s320_e2_packet_adjudicacion_v2.md",
}
recibo = {"que_es": __doc__.strip().splitlines()[0], "arreglos": []}

for nombre, p in PACKETS.items():
    t = p.read_text(encoding="utf-8")
    # --- (1) reconciliación titular vs casillas reales, por sección
    secciones, actual = {}, "(cabecera)"
    for linea in t.splitlines():
        m = re.match(r"^#{2,3}\s+(.*)", linea)
        if m:
            actual = m.group(1).strip()
            secciones.setdefault(actual, 0)
        elif linea.lstrip().startswith("- [ ]"):
            secciones[actual] = secciones.get(actual, 0) + 1
    total = sum(secciones.values())
    detalle = " · ".join(f"{k.split('—')[0].strip()[:34]}: {v}"
                         for k, v in secciones.items() if v)
    nota = (
        f"\n> **Cuenta honesta de casillas** (la escribe el verificador "
        f"adversarial, no el optimismo del autor): este fichero imprime "
        f"**{total} casillas `- [ ]`** en total — {detalle}. Las de §0 están "
        f"ahí para que PUEDAS bajar a grano fino y desmarcar lo que quieras, "
        f"no porque haya que marcarlas una a una: el «sí en bloque» las cubre "
        f"todas de golpe. Si solo asientes a los bloques, tu trabajo real son "
        f"las decisiones del titular.\n")
    # se inserta justo tras el bloque de cita del titular (primera línea vacía
    # después del último '> ' inicial)
    lineas = t.splitlines(keepends=True)
    idx = next((i for i, l in enumerate(lineas)
                if l.startswith(">") and i > 3
                and not lineas[i + 1].startswith(">")), None)
    if idx is not None and "Cuenta honesta de casillas" not in t:
        lineas.insert(idx + 1, nota)
        t = "".join(lineas)
        recibo["arreglos"].append({"packet": nombre, "fix": "titular-vs-casillas",
                                   "casillas_reales": total,
                                   "por_seccion": secciones})
    # --- (2) etiqueta de procedencia que se leía como fuente de la cita
    n_prov = len(re.findall(r"prov `", t))
    if n_prov:
        t = t.replace("prov `", "id-provenance (NO es la fuente de la cita) `")
        recibo["arreglos"].append({"packet": nombre, "fix": "etiqueta-prov",
                                   "ocurrencias": n_prov})
    p.write_text(t, encoding="utf-8")
    print(f"{nombre}: {total} casillas reales · prov renombrado x{n_prov}")

(ROOT / "evals" / "s322i_fix_packets_v2.json").write_text(
    json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
print("recibo -> evals/s322i_fix_packets_v2.json")
