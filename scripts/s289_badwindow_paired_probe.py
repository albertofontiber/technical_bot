#!/usr/bin/env python3
"""s289 r4 — cierre empírico de los 2 hallazgos causales del cross-model r4.

R4-1 (crítico): la captura G-1 no reproduce el miss de hp002#4 (el rerank fresco
sirvió el aviso en el prefijo) ⇒ el PASS de G-3 no valida la CONVERSIÓN de Fix B
en la ventana-mala. Este probe la mide donde murió: prefijo reconstruido de los
`topk_ids` HEAD (p1map rep1, portador NO servido) + pool fresco (1 embedding) →
brazos OFF/ON del seam → N=2 generaciones por brazo → juez de hp002#4 con la
regla exacta del instrumento (primario K=5 → dual en miss).

R4-3 (medio): la conversión de cat017#4 en G-3 corrió con AMBOS flags ⇒ no
atribuible por flag. Aquí se regenera bajo el brazo A-only (captura G-1, misma
composición que el sweep a_only) y se juzga cat017#4: si convierte, la
conversión es de Fix A (el portador `b7633e98` es su fila).

Coste declarado: 1 embedding + hidrataciones GET + 6 generaciones Sonnet +
juicios de 2 facts (primario K=5 ×reps ×brazos + dual en miss).
Salida: evals/s289_badwindow_paired_result_v1.json
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

import scripts.factlevel_assessment as fla  # noqa: E402  (pin DEMO_FLAGS)
from scripts.gold_store import verified  # noqa: E402
from scripts.s288c_gate_funnel_probe import _rebuild_prefix, _retrieve_pool  # noqa: E402
from scripts.s289_order_fixes_sweep import (  # noqa: E402
    CAPTURE_PATH,
    TREATMENT_FLAGS,
    freeze_binding,
)
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage  # noqa: E402

RESULT_PATH = ROOT / "evals" / "s289_badwindow_paired_result_v1.json"
P1MAP_REP1 = ROOT / "evals" / "s100_factlevel_smoke_v31_p1map_rep1.partial.jsonl"
N_REPS = 2


def _set_flags(flag_map: dict[str, str]) -> None:
    for name in TREATMENT_FLAGS:
        os.environ[name] = flag_map.get(name, "off")


def _rep_conveyed(valor, texto: str, answer: str) -> dict:
    primary = fla.judge_conveyed21(valor, texto, answer)
    if primary["yes"] >= fla.THRESH_FIRM:
        return {"conveyed": True, "primary_yes": primary["yes"], "dual": None}
    dual = fla.judge_conveyed_dual(valor, texto, answer)
    return {"conveyed": bool(dual.get("firm")), "primary_yes": primary["yes"],
            "dual": {"yes": dual.get("yes"), "n_valid": dual.get("n_valid"),
                     "firm": dual.get("firm")}}


def _fact(gold: dict, idx: int) -> tuple:
    f = list(fla.core_facts(gold))[idx]
    return f.get("valor", ""), (f.get("texto") or "").strip()


def _gen_and_judge(question: str, chunks: list[dict], valor, texto) -> dict:
    answers = [
        fla.gen_answer_only(question, copy.deepcopy(chunks)) for _ in range(N_REPS)
    ]
    reps = [_rep_conveyed(valor, texto, a) for a in answers]
    conveyed = [r["conveyed"] for r in reps]
    return {
        "verdict": ("conveyed-stable" if all(conveyed)
                    else "miss-stable" if not any(conveyed) else "flip"),
        "reps": reps,
        "answers": answers,
        "served_ids": [str(c.get("id") or "") for c in chunks],
    }


def main() -> int:
    golds = {g["qid"]: g for g in verified() if g["qid"] in ("hp002", "cat017")}
    out: dict = {"instrument": "s289_badwindow_paired_result_v1",
                 "freeze_binding": freeze_binding(),
                 "judges": {"primary": fla.JUDGE_MODEL, "dual": fla.JUDGE2_MODEL,
                            "K": fla.K, "thresh_firm": fla.THRESH_FIRM}}

    # ── R4-1: hp002 ventana-mala (prefijo HEAD, portador NO servido) ──────────
    gold = golds["hp002"]
    rep1 = next(
        json.loads(line) for line in P1MAP_REP1.open(encoding="utf-8")
        if '"qid"' in line and json.loads(line).get("qid") == "hp002"
    )
    pool = _retrieve_pool(gold["question"], fla.RETRIEVAL_TOP_K)
    prefix, prefix_trace = _rebuild_prefix(list(rep1["topk_ids"]), pool)
    carrier_served = any(
        str(r.get("id") or "").startswith("5b6a3a19") for r in prefix
    )
    valor, texto = _fact(gold, 4)
    arms: dict = {}
    for arm, flag_map in (
        ("off", {}),
        ("on", {n: "on" for n in TREATMENT_FLAGS}),
    ):
        _set_flags(flag_map)
        chunks, trace = apply_profiled_post_rerank_coverage(
            gold["question"], copy.deepcopy(prefix), retrieval_pool=copy.deepcopy(pool)
        )
        arms[arm] = _gen_and_judge(gold["question"], chunks, valor, texto)
        arms[arm]["appended_ids"] = [
            str(c.get("id") or "") for c in chunks[len(prefix):]
        ]
    _set_flags({})
    out["hp002_badwindow"] = {
        "prefix_trace": prefix_trace,
        "carrier_in_prefix": carrier_served,
        "carrier_appended_on": any(
            x.startswith("5b6a3a19") for x in arms["on"]["appended_ids"]
        ),
        "fact": "hp002#4",
        "arms": arms,
    }
    print(f"hp002#4 ventana-mala: carrier_in_prefix={carrier_served} "
          f"carrier_appended_on={out['hp002_badwindow']['carrier_appended_on']} "
          f"off={arms['off']['verdict']} on={arms['on']['verdict']}")

    # ── R4-3: cat017 bajo A-only (captura G-1) ────────────────────────────────
    with gzip.open(CAPTURE_PATH, "rt", encoding="utf-8") as fh:
        captured = json.load(fh)
    entry = captured["golds"]["cat017"]
    gold = golds["cat017"]
    valor, texto = _fact(gold, 4)
    _set_flags({"FACET_COMPLEMENT_FALLBACK": "on"})
    chunks, _trace = apply_profiled_post_rerank_coverage(
        entry["query"], copy.deepcopy(entry["prefix"]),
        retrieval_pool=copy.deepcopy(entry["pool"]),
    )
    _set_flags({})
    res = _gen_and_judge(entry["query"], chunks, valor, texto)
    out["cat017_a_only"] = {"fact": "cat017#4", **res}
    print(f"cat017#4 A-only: {res['verdict']}")

    RESULT_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"-> {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
