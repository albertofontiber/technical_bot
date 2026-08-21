# -*- coding: utf-8 -*-
"""s336 B4c — GATE de precisión vs mini-GT + PACKET §0/§1 (v3 §0.1).

Gate (pre-registrado, barra heredada del cierre s322b): precisión de la
ALTA-confianza contra las filas SIN-duda del GT congelado ≥95% en categoría
(y sin contradicción en tecnología donde el GT la tiene), n≥10 — o la
población NO sale del recibo. Cobertura = INFORMATIVA aquí; el veredicto
PASS/PARCIAL del LOTE lo estampa el writer con el criterio del 60% (v3 §0.3).

Uso: python scripts/s336_gate_y_packet.py [--poblacion ...] [--elegibles ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--poblacion", default=str(ROOT / "evals" / "s336_poblacion_v1.json"))
    ap.add_argument("--elegibles", default=str(ROOT / "evals" / "s336_elegibles_v1.json"))
    args = ap.parse_args()

    crudo_gt = (ROOT / "evals" / "s336_gt_v1.yaml").read_text(encoding="utf-8")
    gt = yaml.safe_load(crudo_gt)["filas"]
    pob = json.loads(Path(args.poblacion).read_text(encoding="utf-8"))
    ele = json.loads(Path(args.elegibles).read_text(encoding="utf-8"))
    por_id = {f["id"]: f for f in pob["detalle"]}
    ele_por_id = {f["id"]: f for f in ele["detalle"]}

    aciertos = fallos = 0
    detalle = []
    for g in gt:
        if g.get("duda"):
            continue
        f = por_id.get(g["id"])
        if not f or f["llm"].get("confianza") != "alta":
            continue                    # el gate mide PRECISIÓN de la alta
        v = f["llm"]
        ok = v.get("categoria") == g["categoria"]
        if ok and g.get("tecnologia"):
            tec = v.get("tecnologia")
            ok = tec in (None, "null") or tec == g["tecnologia"]
        aciertos += ok
        fallos += (not ok)
        detalle.append({"id": g["id"], "ok": ok, "gt": g.get("categoria"),
                        "llm": v.get("categoria"), "etapa": v.get("etapa")})
    n = aciertos + fallos
    precision = aciertos / n if n else 0.0
    gate_pass = n >= 10 and precision >= 0.95

    # ── packet ────────────────────────────────────────────────────────────────
    elegibles = [f for f in ele["detalle"] if f.get("elegible")]
    resto = defaultdict(list)
    for f in pob["detalle"]:
        v = f["llm"]
        if v.get("confianza") == "alta":
            e = ele_por_id.get(f["id"])
            if e and not e.get("elegible"):
                resto["alta_sin_fulltext"].append(f["id"])
            continue
        clase = v.get("confianza") or "baja"
        if v.get("razon") == "sin chunks en ningún doc":
            clase = "sin_evidencia_chunks"
        resto[clase].append(f["id"])
    cap_packet = [f["id"] for f in ele["detalle"] if f.get("capacidad_packet")]
    cats = Counter(f.get("categoria") for f in elegibles)

    recibo = {
        "gate": {"n": n, "aciertos": aciertos, "precision": round(precision, 4),
                 "umbral": 0.95, "pass": gate_pass, "detalle": detalle},
        "freeze": {"gt_sha256": hashlib.sha256(crudo_gt.encode()).hexdigest()[:16],
                   "prompt_sha256": pob.get("prompt_sha256")},
        "packet": {
            "s0_elegibles_en_bloque": {"n": len(elegibles),
                                       "categorias": dict(cats)},
            "s1_resto": {k: {"n": len(v), "ids": v} for k, v in sorted(resto.items())},
            "s1_capacidad_a_adjudicar": {"n": len(cap_packet), "ids": cap_packet},
            "docs_sin_chunks": pob.get("docs_sin_chunks", []),
        },
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out = ROOT / "evals" / "s336_gate_result_v1.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"GATE: {'PASS' if gate_pass else 'FAIL'} · precisión {precision:.1%} "
          f"(n={n}) · §0 elegibles={len(elegibles)} {dict(cats)} · "
          f"capacidad-a-packet={len(cap_packet)} · recibo → {out}")
    for d in detalle:
        if not d["ok"]:
            print(f"  [X] {d['id']}: GT={d['gt']} vs LLM={d['llm']} ({d['etapa']})")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
