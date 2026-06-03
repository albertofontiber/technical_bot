#!/usr/bin/env python3
"""characterize_factual_variance.py — caracterización screen-then-focus del eje factual (#37, DEC-014 §3).

Corre el eje FACTUAL (+NO-FABRICACIÓN) del árbitro K veces sobre el MISMO input (golds verificados +
respuestas cacheadas del bot) para medir la ESTABILIDAD DE VEREDICTO run-a-run — la métrica de #37
(NO la varianza de conteo). Separa dos causas de inestabilidad:
  - cruce de CONTEO 0↔1 de contradicciones/fabricaciones = sampling IRREDUCIBLE (gpt-5.5 temp=1)
  - flip a REVISAR por ERROR transitorio (parse/red) — debería ser ~0 tras response_format (DEC-014 §2)

gpt-5.5 no tiene knob de determinismo (probe s42): esto NO controla el sampling, lo MIDE. Paraleliza
las llamadas (i.i.d.) para acotar el wall-clock. Dumpea artefactos auditables a JSON.

Uso:
  python scripts/characterize_factual_variance.py --k 5                        # screen / 19
  python scripts/characterize_factual_variance.py --k 12 --qids hp005,hp008    # focus
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/
import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402
import gold_store  # noqa: E402
from atomic_scorer import (  # noqa: E402
    DEFAULT_ANSWERS, FACTUAL_MODEL, factual_check, score_gold, undue_inference_check)


def _vclass(v: str) -> str:
    """clase categórica del veredicto (lo que importa para #37): FALLO|PARCIAL|PASS|REVISAR|?"""
    return v.split("(")[0].strip()


def _one_run(g, ans, present_facts, absent, client, model):
    """una corrida del eje sobre un gold (idéntica al wiring de atomic_scorer.main con --llm)."""
    contradictions, factual_error = factual_check(present_facts, ans, client, model)
    undue, inference_error = (None, None)
    if absent:
        undue, inference_error = undue_inference_check(absent, ans, client, model)
    res = score_gold(g, ans, contradictions, factual_error,
                     undue_inferences=undue, inference_error=inference_error)
    return {"verdict": res["verdict"], "vclass": _vclass(res["verdict"]),
            "n_contra": (len(contradictions) if contradictions is not None else None),
            "n_undue": (len(undue) if undue is not None else None),
            "factual_error": factual_error, "inference_error": inference_error,
            # contenido para ADJUDICAR spurious-vs-real (DEC-014 §4: estructura del error)
            "contradictions": contradictions or [], "undue": undue or []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5, help="corridas por gold")
    ap.add_argument("--qids", default="", help="limitar a qids (coma) — para el focus")
    ap.add_argument("--answers", default=str(DEFAULT_ANSWERS))
    ap.add_argument("--model", default=FACTUAL_MODEL)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    load_dotenv(ROOT / ".env", override=True)
    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] sin OPENAI_API_KEY (en .env o env). Abortado.")
        return 1
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    answers = {}
    with open(args.answers, encoding="utf-8") as fh:
        for r in yaml.safe_load(fh) or []:
            if r.get("qid"):
                answers[r["qid"]] = r.get("bot_answer", "")
    golds = [g for g in gold_store.verified() if g.get("atomic_facts")]
    if args.qids:
        want = {q.strip() for q in args.qids.split(",")}
        golds = [g for g in golds if g.get("qid") in want]
    golds = sorted([g for g in golds if g.get("qid") in answers], key=lambda x: x.get("qid"))

    meta = {}
    for g in golds:
        facts = g.get("atomic_facts") or []
        meta[g.get("qid")] = (
            [f for f in facts if f.get("estado") != "ausente-probado"],
            [f for f in facts if f.get("estado") == "ausente-probado"],
        )
    work = [(g, i) for g in golds for i in range(args.k)]
    print(f"Caracterización eje factual · K={args.k} · {len(golds)} golds · "
          f"{len(work)} llamadas · workers={args.workers} · modelo={args.model}\n")

    by_qid: dict = {g.get("qid"): [] for g in golds}
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {}
        for g, _i in work:
            qid = g.get("qid")
            present_facts, absent = meta[qid]
            fut[ex.submit(_one_run, g, answers[qid], present_facts, absent, client, args.model)] = qid
        for f in as_completed(fut):
            qid = fut[f]
            try:
                by_qid[qid].append(f.result())
            except Exception as e:
                by_qid[qid].append({"verdict": f"REVISAR (harness error: {e})", "vclass": "REVISAR",
                                    "n_contra": None, "n_undue": None,
                                    "factual_error": str(e), "inference_error": None})
            done += 1
            if done % 10 == 0 or done == len(work):
                print(f"  ... {done}/{len(work)} llamadas")

    results = []
    print()
    for g in golds:
        qid = g.get("qid")
        runs = by_qid[qid]
        vc = Counter(r["vclass"] for r in runs)
        stable = len(vc) == 1
        ncontras = [r["n_contra"] for r in runs if r["n_contra"] is not None]
        n_errors = sum(1 for r in runs if r["factual_error"] or r["inference_error"])
        count_flip = len(set(ncontras)) > 1 if ncontras else False
        crosses_01 = bool(ncontras) and (0 in ncontras) and any(n >= 1 for n in ncontras)
        cause = []
        if not stable:
            if crosses_01:
                cause.append("0↔1")
            elif count_flip:
                cause.append("conteo")
            if n_errors:
                cause.append(f"{n_errors}err→REVISAR")
        results.append({"qid": qid, "k": args.k, "stable": stable,
                        "verdict_classes": dict(vc), "modal_verdict": vc.most_common(1)[0][0],
                        "n_contra_runs": [r["n_contra"] for r in runs],
                        "n_undue_runs": [r["n_undue"] for r in runs],
                        "n_errors": n_errors, "count_flip": count_flip, "crosses_01": crosses_01,
                        "cause": "+".join(cause), "runs": runs})
        print(f"  {qid:<8} [{'STABLE ' if stable else 'UNSTABLE'}] {dict(vc)} "
              f"· n_contra={[r['n_contra'] for r in runs]}" + (f" · {'+'.join(cause)}" if cause else ""))

    n_unstable = sum(1 for r in results if not r["stable"])
    n_err = sum(1 for r in results if not r["stable"] and r["n_errors"] > 0)
    n_sampling = sum(1 for r in results if not r["stable"] and r["crosses_01"])
    print(f"\n{'=' * 62}")
    print(f"RESUMEN K={args.k}: {n_unstable}/{len(results)} golds con VEREDICTO inestable "
          f"· {n_sampling} por sampling 0↔1 · {n_err} con ≥1 error→REVISAR")
    print(f"Inestables: {[r['qid'] for r in results if not r['stable']]}")
    # BASELINE #37 = agregación: veredicto por MAYORÍA + flag de review (no-unánime → spot-check
    # humano; cierra CM1 — ningún FALLO minoritario se lava en silencio). response_format mata el
    # ruido de formato; la mayoría mata el de sampling; gpt-5.5 no tiene knob de determinismo.
    print("\n--- BASELINE #37 (mayoría + flag) ---")
    for r in results:
        print(f"  {r['qid']:<8} {'⚠ REVIEW ' if not r['stable'] else 'estable  '} → {r['modal_verdict']}")
    print(f"  ({len(results) - n_unstable}/{len(results)} estables · {n_unstable} a spot-check humano)")
    out = Path(args.out) if args.out else ROOT / "evals" / f"factual_variance_k{args.k}.json"
    if not out.is_absolute():
        out = ROOT / out
    out.write_text(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "k": args.k,
                               "model": args.model, "n_unstable": n_unstable, "results": results},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[artefacto] → {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
