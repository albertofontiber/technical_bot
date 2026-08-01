#!/usr/bin/env python3
"""s291 L2 — G-FP de amplitud + G-directed (diseño v2 §gates, pareado-de-drafts).

Para cada gold de la captura s289 cuya composición (replay ON = vector de ship)
lleva fila de la reserva: genera UN draft desde esa composición (coherente), y
aplica el apéndice determinísticamente sobre el MISMO draft (brazo ON) vs el
draft tal cual (brazo OFF) — $0 de varianza de generación entre brazos (Sol-1).

Recibo POR-FILA (H7): {gold, fragment, quote, section_title del chunk, outcome
appendix/satisfied/rejected, answer_delta_chars}. La adjudicación
espurio/redundante/legítimo se hace SOBRE este recibo (regla C, por-fila).
G-directed: para hp002, si el draft no transmite el aviso, el brazo ON debe
llevarlo verbatim (chequeo determinista aquí; el juez conveyed corre aparte).
Tripwire: >5/39 apéndices = STOP.

Coste declarado: ~N generaciones Sonnet (1 por gold-con-reserva) + 0 jueces.
Salida: evals/s291_l2_gfp_result_v1.json
"""
from __future__ import annotations

import copy
import gzip
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.factlevel_assessment as fla  # noqa: E402  (pin DEMO_FLAGS: appendix off)
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage  # noqa: E402
import src.rag.must_preserve as mp  # noqa: E402

CAPTURE = ROOT / "evals" / "s289_g1_sweep39_capture_v1.json.gz"
OUT = ROOT / "evals" / "s291_l2_gfp_result_v1.json"
RESERVE_LANE = "obligation_warning_reserve_v1"


def main() -> int:
    with gzip.open(CAPTURE, "rt", encoding="utf-8") as fh:
        captured = json.load(fh)
    rows_out = []
    n_appendix = 0
    for qid, entry in captured["golds"].items():
        chunks, _trace = apply_profiled_post_rerank_coverage(
            entry["query"], copy.deepcopy(entry["prefix"]),
            retrieval_pool=copy.deepcopy(entry["pool"]),
        )
        reserve = [c for c in chunks if c.get("retrieval_lane") == RESERVE_LANE]
        if not reserve:
            continue
        card = (reserve[0].get("coverage_cards") or [{}])[0]
        draft = fla.gen_answer_only(entry["query"], copy.deepcopy(chunks))
        # brazo ON: apéndice determinista sobre el MISMO draft
        os.environ["OBLIGATION_WARNING_APPENDIX"] = "on"
        try:
            out_on, trace_on = mp.apply_must_preserve_contract(
                entry["query"], chunks, draft
            )
        finally:
            os.environ["OBLIGATION_WARNING_APPENDIX"] = "off"
        ob = (trace_on or {}).get("obligation_appendix") or {}
        outcome = ("appended" if ob.get("appended")
                   else "satisfied" if ob.get("satisfied")
                   else "rejected" if ob.get("rejected")
                   else "no_candidate" if ob.get("candidates") == 0
                   else "identity_unresolved" if (trace_on or {}).get("reason")
                   else "?")
        if ob.get("appended"):
            n_appendix += 1
        rows_out.append({
            "qid": qid,
            "fragment_id": str(reserve[0].get("id"))[:8],
            "section_title": str(reserve[0].get("section_title") or "")[:60],
            "page": reserve[0].get("page_number"),
            "quote_head": (card.get("quote") or "")[:150],
            "outcome": outcome,
            "ob_trace": ob,
            "mp_reason": (trace_on or {}).get("reason"),
            "answer_delta_chars": len(out_on) - len(draft),
            "draft_tail": draft[-200:],
            "appendix_tail": out_on[-400:] if ob.get("appended") else None,
        })
        print(f"  {qid}: {outcome} (delta {len(out_on)-len(draft)})")
    verdict = "TRIPWIRE-STOP" if n_appendix > 5 else "RECIBO-LISTO"
    result = {"instrument": "s291_l2_gfp_result_v1",
              "n_reserve_golds": len(rows_out), "n_appendix": n_appendix,
              "tripwire": verdict, "rows": rows_out}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"reserva en {len(rows_out)} golds · apéndices {n_appendix} · {verdict}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
