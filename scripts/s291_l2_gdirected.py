#!/usr/bin/env python3
"""s291b L2 — G-directed: hp002#4 en la VENTANA-MALA con el vector completo.

Reproduce la composición de ventana-mala (prefijo HEAD de p1map rep1, donde el
portador 5b6a3a19 NO está servido y la reserva ordenada lo apendiza — probe
s289) y genera N=2 drafts con `OBLIGATION_WARNING_APPENDIX=on` en el path real
del generador (el contrato mp corre dentro). Juez del instrumento sobre
hp002#4 en cada draft + verificación determinista de que el aviso viaja
(cuerpo O apéndice). Éxito pre-declarado: hp002#4 conveyed-firme en N=2/2
(la clase deja de ser flip) y hp002#0-#3 sin degradar (spot: #1 «80 %»).

Coste: 1 embedding + 2 generaciones + juicios (~$1-2).
Salida: evals/s291_l2_gdirected_result_v1.json
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.factlevel_assessment as fla  # noqa: E402
from scripts.gold_store import verified  # noqa: E402
from scripts.s288c_gate_funnel_probe import _rebuild_prefix, _retrieve_pool  # noqa: E402
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage  # noqa: E402

OUT = ROOT / "evals" / "s291_l2_gdirected_result_v1.json"
P1MAP_REP1 = ROOT / "evals" / "s100_factlevel_smoke_v31_p1map_rep1.partial.jsonl"
N_REPS = 2
# regla-C s291b: los markers v1 fallaban contra el verbatim con markdown
# («es **imprescindible** bloquearlos») — se pliega [*_] antes de matchear.
WARNING_MARKERS = ("imprescindible bloquearlos", "bloquearlos o desconectarlos")


def _rep_conveyed(valor, texto, answer):
    primary = fla.judge_conveyed21(valor, texto, answer)
    if primary["yes"] >= fla.THRESH_FIRM:
        return {"conveyed": True, "primary_yes": primary["yes"], "dual": None}
    dual = fla.judge_conveyed_dual(valor, texto, answer)
    return {"conveyed": bool(dual.get("firm")), "primary_yes": primary["yes"],
            "dual": {"yes": dual.get("yes"), "firm": dual.get("firm")}}


def main() -> int:
    os.environ["OBLIGATION_WARNING_APPENDIX"] = "on"   # vector candidato de ship
    gold = next(g for g in verified() if g["qid"] == "hp002")
    rep1 = next(
        json.loads(line) for line in P1MAP_REP1.open(encoding="utf-8")
        if '"qid"' in line and json.loads(line).get("qid") == "hp002"
    )
    pool = _retrieve_pool(gold["question"], fla.RETRIEVAL_TOP_K)
    prefix, prefix_trace = _rebuild_prefix(list(rep1["topk_ids"]), pool)
    chunks, _trace = apply_profiled_post_rerank_coverage(
        gold["question"], copy.deepcopy(prefix), retrieval_pool=copy.deepcopy(pool)
    )
    reserve_carrier = any(
        str(c.get("id") or "").startswith("5b6a3a19") for c in chunks[len(prefix):]
    )
    facts = list(fla.core_facts(gold))
    v4, t4 = facts[4].get("valor", ""), (facts[4].get("texto") or "").strip()
    v1, t1 = facts[1].get("valor", ""), (facts[1].get("texto") or "").strip()
    reps = []
    for i in range(N_REPS):
        ans = fla.gen_answer_only(gold["question"], copy.deepcopy(chunks))
        folded = re.sub(r"[*_]", "", ans.lower())
        warning_travels = any(m in folded for m in WARNING_MARKERS)
        appendix_present = "Aviso obligatorio del manual" in ans
        r4 = _rep_conveyed(v4, t4, ans)
        r1_check = _rep_conveyed(v1, t1, ans)
        reps.append({"rep": i, "warning_travels": warning_travels,
                     "appendix_present": appendix_present,
                     "hp002_4": r4, "hp002_1_centinela": r1_check,
                     "answer_tail": ans[-350:]})
        print(f"rep{i}: travels={warning_travels} appendix={appendix_present} "
              f"#4conveyed={r4['conveyed']} #1ok={r1_check['conveyed']}")
    verdict = ("PASS" if all(r["hp002_4"]["conveyed"] and r["warning_travels"]
                             and r["hp002_1_centinela"]["conveyed"] for r in reps)
               else "FAIL")
    result = {"instrument": "s291_l2_gdirected_result_v1",
              "carrier_reserve_served": reserve_carrier,
              "prefix_trace": prefix_trace, "verdict": verdict, "reps": reps}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"carrier-en-reserva={reserve_carrier} · veredicto {verdict}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
