#!/usr/bin/env python3
"""s289 G-3 — gate dirigido PAREADO per-fact de los 2 fixes (dúo r3, S1+S2).

Corre DESPUÉS de `s289_order_fixes_sweep.py arms` (G-1). Población = los golds
cuya vista servida CAMBIA entre brazos (lista G-1) ∪ {cat017, hp002} (dianas).
Todos los brazos parten de la MISMA captura congelada (S1): la composición por
brazo se re-materializa con el replay determinista (validado por réplica-OFF) y
la generación (Sonnet temp=0, N=2 reps por brazo) corre sobre ESA composición
(`gen_answer_only`, cláusula 6 del instrumento).

Adjudicación per-fact = LA DEL INSTRUMENTO v3.1 (paridad exacta, fix dúo
dual-judge #4): primario `judge_conveyed21` (GPT-5.5 K=5, conveyed si
yes>=THRESH_FIRM); si miss → `judge_conveyed_dual` (Opus, regla proporcional
C2). Veredicto por brazo: conveyed-stable (N=2 reps conveyed) / miss-stable /
flip.

VEREDICTO DEL GATE (pre-registrado en el diseño §Plan):
  - ÉXITO: cat017#4 y hp002#4 conveyed en el brazo ON (al menos 1 rep; stable
    = resultado fuerte).
  - NO-REGRESIÓN: ningún fact conveyed-stable en OFF cae a miss-stable en ON.
  - G-2 embebido: hp002#0..#3 (hoy OK) no degradan al desplazar 339f06e0.

Uso: python scripts/s289_order_fixes_directed.py [--dry]  (--dry = solo
     población y coste, sin gasto)
Salidas: evals/s289_g3_directed_result_v1.json + _report_v1.md
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
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage  # noqa: E402

CAPTURE_PATH = ROOT / "evals" / "s289_g1_sweep39_capture_v1.json.gz"
G1_RESULT_PATH = ROOT / "evals" / "s289_g1_sweep39_result_v1.json"
RESULT_PATH = ROOT / "evals" / "s289_g3_directed_result_v1.json"
REPORT_PATH = ROOT / "evals" / "s289_g3_directed_report_v1.md"

TREATMENT_FLAGS = ("FACET_COMPLEMENT_FALLBACK", "OBLIGATION_RESERVE_ORDERED")
TARGET_QIDS = ("cat017", "hp002")
TARGET_FACTS = {"cat017#4", "hp002#4"}
N_REPS = 2


def _set_treatment(value: str) -> None:
    for name in TREATMENT_FLAGS:
        os.environ[name] = value


def _replay_chunks(entry: dict) -> list[dict]:
    served, _trace = apply_profiled_post_rerank_coverage(
        entry["query"],
        copy.deepcopy(entry["prefix"]),
        retrieval_pool=copy.deepcopy(entry["pool"]),
    )
    return served


def _rep_conveyed(valor, texto: str, answer: str) -> dict:
    """Regla EXACTA de `measure_gold._rep_is_miss` (paridad del instrumento)."""
    primary = fla.judge_conveyed21(valor, texto, answer)
    if primary["yes"] >= fla.THRESH_FIRM:
        return {"conveyed": True, "primary_yes": primary["yes"], "dual": None}
    dual = fla.judge_conveyed_dual(valor, texto, answer)
    return {
        "conveyed": bool(dual.get("firm")),
        "primary_yes": primary["yes"],
        "dual": {"yes": dual.get("yes"), "n_valid": dual.get("n_valid"),
                 "firm": dual.get("firm")},
    }


def main() -> int:
    dry = "--dry" in sys.argv
    if not CAPTURE_PATH.exists() or not G1_RESULT_PATH.exists():
        raise SystemExit("faltan captura/result de G-1 — corre el sweep primero")
    with gzip.open(CAPTURE_PATH, "rt", encoding="utf-8") as fh:
        captured = json.load(fh)
    g1 = json.loads(G1_RESULT_PATH.read_text(encoding="utf-8"))
    if g1.get("verdict") != "PASS":
        raise SystemExit(f"G-1 verdict={g1.get('verdict')} — no se corre G-3")

    qids = sorted(set(g1["changed_golds"]) | set(TARGET_QIDS))
    golds = {g["qid"]: g for g in verified() if g["qid"] in qids}
    n_facts = sum(len(fla.core_facts(golds[q])) for q in qids)
    print(f"G-3 población: {qids} ({len(qids)} golds, {n_facts} facts)")
    print(f"coste declarado: {len(qids)*2*N_REPS} generaciones Sonnet + "
          f"~{n_facts*2*N_REPS} juicios primarios K={fla.K} (+dual en miss)")
    if dry:
        return 0

    out: dict[str, dict] = {}
    for qid in qids:
        gold = golds[qid]
        entry = captured["golds"][qid]
        arms: dict[str, dict] = {}
        for arm, treatment in (("off", "off"), ("on", "on")):
            _set_treatment(treatment)
            chunks = _replay_chunks(entry)
            answers = [
                fla.gen_answer_only(gold["question"], copy.deepcopy(chunks))
                for _ in range(N_REPS)
            ]
            arms[arm] = {
                "served_ids": [str(c.get("id") or "") for c in chunks],
                "answers": answers,
            }
        _set_treatment("off")
        facts = []
        for idx, f in enumerate(fla.core_facts(gold)):
            valor = f.get("valor", "")
            texto = (f.get("texto") or "").strip()
            key = f"{qid}#{idx}"
            fact_row: dict = {"key": key, "valor": valor}
            for arm in ("off", "on"):
                reps = [
                    _rep_conveyed(valor, texto, ans)
                    for ans in arms[arm]["answers"]
                ]
                conveyed = [r["conveyed"] for r in reps]
                fact_row[arm] = {
                    "reps": reps,
                    "verdict": ("conveyed-stable" if all(conveyed)
                                else "miss-stable" if not any(conveyed)
                                else "flip"),
                }
            facts.append(fact_row)
            print(f"  {key}: off={fact_row['off']['verdict']} "
                  f"on={fact_row['on']['verdict']}")
        out[qid] = {
            "arms": {a: {"served_ids": arms[a]["served_ids"]} for a in arms},
            "answers": {a: arms[a]["answers"] for a in arms},
            "facts": facts,
        }

    regressions, conversions, target_status = [], [], {}
    for qid, entry in out.items():
        for fact in entry["facts"]:
            off_v, on_v = fact["off"]["verdict"], fact["on"]["verdict"]
            if off_v == "conveyed-stable" and on_v == "miss-stable":
                regressions.append(fact["key"])
            if off_v == "miss-stable" and on_v in ("conveyed-stable", "flip"):
                conversions.append((fact["key"], on_v))
            if fact["key"] in TARGET_FACTS:
                target_status[fact["key"]] = {"off": off_v, "on": on_v}

    verdict = "PASS" if not regressions and all(
        v["on"] in ("conveyed-stable", "flip") for v in target_status.values()
    ) else ("NO-REGRESSION-FAIL" if regressions else "TARGETS-NOT-CONVERTED")

    result = {
        "instrument": "s289_g3_directed_result_v1",
        "population": qids,
        "n_reps": N_REPS,
        "verdict": verdict,
        "targets": target_status,
        "conversions": conversions,
        "regressions": regressions,
        "golds": out,
    }
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    lines = [
        "# s289 G-3 — dirigido pareado per-fact (OFF vs ON sobre captura única)",
        "",
        f"- Veredicto: **{verdict}**",
        f"- Dianas: {json.dumps(target_status, ensure_ascii=False)}",
        f"- Conversiones: {conversions}",
        f"- Regresiones (conveyed-stable→miss-stable): {regressions or 'ninguna'}",
        "",
    ]
    for qid, entry in out.items():
        lines.append(f"## {qid}")
        for fact in entry["facts"]:
            lines.append(
                f"- {fact['key']}: off={fact['off']['verdict']} → "
                f"on={fact['on']['verdict']}"
            )
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"veredicto {verdict}")
    print(f"-> {RESULT_PATH}\n-> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
