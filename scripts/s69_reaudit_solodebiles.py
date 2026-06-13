#!/usr/bin/env python3
"""s69 — RE-AUDIT de los 8 solo_debiles (read-only, $0; pedido por el dúo r1, F1/F8).

El enfoque v1 trató los 8 como diana de generación = bias #20 (auto-etiquetar GENERACION
sin verificar que el dato esté SERVIDO). Este re-audit clasifica cada uno con evidencia:

  Por gold (de s67base, ya congelado — sufficiency D3 + diagnóstico del juez K=5):
   - facts con in_top5/in_filtered (¿el material del gold está en la vista servida?)
   - n_core_presente vs n_core_fuerte (cuántos hechos-core llegaron, aunque débiles)
   - el diagnóstico modal del juez (QUÉ marcó omitido/mal)
   - sources del top-5 servido

REGLA DE CLASIFICACIÓN (pre-registrada aquí):
  - GENERACION-confirmada := la mayoría de los core-facts están in_top5/in_filtered
    (material servido) ∧ el juez marca OMISIÓN de algo servido → el modelo lo tenía y
    lo dejó fuera. Estos SÍ entran a la diana de generación.
  - RETRIEVAL/CORPUS := la mayoría de core-facts NO están in_top5 → el modelo no podía
    decirlo → no es generación (es retrieval/corpus mal etiquetado).
  - AMBIGUO := mezcla / probes demasiado débiles para concluir (se reporta como tal,
    NO se mete en la diana — conservador, anti-bias #20).

Salida: evals/s69_reaudit_solodebiles.yaml + tabla. La clasificación final la hace el
autor leyendo la evidencia (no se auto-decide): este script SURFACEA, no juzga.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
OCHO = ["cat016", "cat019", "cat024", "hp003", "hp006", "hp009", "hp013", "hp017"]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    report = yaml.safe_load((EVALS / "s67base_gate_report.yaml").read_text(encoding="utf-8"))
    jud = json.loads((EVALS / "s67base_judgments.json").read_text(encoding="utf-8"))
    ctx = json.loads((EVALS / "s67base_frozen_contexts.json").read_text(encoding="utf-8"))
    g = {x["qid"]: x for x in report["golds"]}

    out = {}
    for q in OCHO:
        row = g[q]
        suff = row.get("sufficiency") or {}
        facts = suff.get("facts") or []
        n_servidos = sum(1 for f in facts if f.get("in_filtered"))
        # diagnóstico modal (el más repetido entre los 5 runs, truncado)
        diags = [jud[q][k].get("diagnostico", "") for k in sorted(jud[q]) if jud[q][k].get("diagnostico")]
        diag = max(diags, key=len) if diags else ""
        servidos_sources = sorted({c.get("source_file") for c in ctx[q]["top5"]})
        out[q] = {
            "n_facts": len(facts),
            "n_in_filtered": n_servidos,
            "n_core_presente": suff.get("n_core_presente"),
            "n_core_fuerte": suff.get("n_core_fuerte"),
            "facts": [{"valor": f.get("valor"), "strength": f.get("strength"),
                       "in_top5": f.get("in_top5"), "in_filtered": f.get("in_filtered")}
                      for f in facts],
            "labels_sufficiency": (suff.get("sub") or {}).get("labels"),
            "diag_modal": diag,
            "top5_sources": servidos_sources,
        }
        # señal cruda para clasificar (la decisión la toma el autor)
        frac = n_servidos / len(facts) if facts else 0
        senal = ("material-SERVIDO (gen?)" if frac >= 0.6
                 else "material-NO-servido (retrieval?)" if frac <= 0.3
                 else "MIXTO")
        print(f"\n=== {q} | {n_servidos}/{len(facts)} facts in_filtered "
              f"| core {suff.get('n_core_presente')}/{len(facts)} | {senal} ===")
        for f in facts:
            print(f"   [{('S' if f.get('in_filtered') else '.')}] "
                  f"{f.get('strength','?'):6} {str(f.get('valor'))[:46]}")
        print(f"   sources servidos: {servidos_sources}")
        print(f"   juez: {diag[:300]}")

    (EVALS / "s69_reaudit_solodebiles.yaml").write_text(
        yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    print(f"\n→ s69_reaudit_solodebiles.yaml ({len(OCHO)} golds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
