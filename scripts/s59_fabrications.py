#!/usr/bin/env python3
"""s59_fabrications.py — eje no-fabricación (C2/R3) sobre generaciones K del runner.

Materializa la cláusula C2 del PREREG (+ R3 para K=5) para el A/B del lever s59:
  - unidad: GOLD con "fabricación K-estable" = en >=3 de los K runs el bot AFIRMA
    >=1 hecho marcado `ausente-probado` (eje no-fabricación del atomic_scorer —
    undue_inference_check, cross-model GPT-5.5, conservador).
  - alcance: golds dev con >=1 hecho ausente-probado (en los demás el eje es N/A).
  - R3 (ceguera): el brazo BASE (s58_generations.json) se computa ANTES de generar
    el brazo LEVER. Este script se niega a correr el brazo post si el base no
    existe aún (orden pin del diseño).

Uso:
  python scripts/s59_fabrications.py base   # sobre evals/s58_generations.json
  python scripts/s59_fabrications.py post   # sobre evals/s59_generations.json
Salida: evals/s59_fabrications_{base|post}.yaml
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import gold_store  # noqa: E402
from atomic_scorer import undue_inference_check, FACTUAL_MODEL  # noqa: E402

EVALS = ROOT / "evals"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("arm", choices=["base", "post"])
    ap.add_argument("--k-stable", type=int, default=3, help="umbral K-estable (>=N de K)")
    args = ap.parse_args()

    gen_file = EVALS / ("s58_generations.json" if args.arm == "base" else "s59_generations.json")
    out_file = EVALS / f"s59_fabrications_{args.arm}.yaml"
    if args.arm == "post":
        assert (EVALS / "s59_fabrications_base.yaml").exists(), \
            "R3: el brazo BASE debe computarse ANTES (ciego al lever) — corre `base` primero"
    gens = json.loads(gen_file.read_text(encoding="utf-8"))

    golds = {g["qid"]: g for g in gold_store.dev()}
    scoped = {qid: g for qid, g in golds.items()
              if any(f.get("estado") == "ausente-probado" for f in g.get("atomic_facts") or [])}
    print(f"{args.arm} | golds con hechos ausente-probado: {len(scoped)}/{len(golds)} "
          f"| modelo={FACTUAL_MODEL}")

    from openai import OpenAI
    import os
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    rows, k_stable_golds = [], []
    for qid in sorted(scoped):
        g = scoped[qid]
        absent = [f for f in g["atomic_facts"] if f.get("estado") == "ausente-probado"]
        runs = gens.get(qid) or {}
        per_run = []
        for rk in sorted(runs):
            row = runs[rk]
            if row.get("error") or not row.get("answer"):
                per_run.append({"run": rk, "fabricated": None, "note": "gen-error"})
                continue
            fabs, err = undue_inference_check(absent, row["answer"], client, FACTUAL_MODEL)
            per_run.append({"run": rk,
                            "fabricated": (len(fabs) > 0) if err is None else None,
                            "n_fabs": len(fabs) if err is None else None,
                            "fabs": fabs[:3] if fabs else [],
                            "error": err})
        n_fab = sum(1 for r in per_run if r["fabricated"] is True)
        n_eval = sum(1 for r in per_run if r["fabricated"] is not None)
        k_stable = n_fab >= args.k_stable
        if k_stable:
            k_stable_golds.append(qid)
        rows.append({"qid": qid, "n_absent_facts": len(absent), "n_runs_eval": n_eval,
                     "n_runs_fabricated": n_fab, "k_stable_fabrication": k_stable,
                     "runs": per_run})
        print(f"  {qid}: fabricó en {n_fab}/{n_eval} runs"
              f"{'  ** K-ESTABLE **' if k_stable else ''}")

    out = {"meta": {"arm": args.arm, "gen_file": gen_file.name,
                    "at": datetime.datetime.now().isoformat(timespec="seconds"),
                    "model": FACTUAL_MODEL, "k_stable_threshold": args.k_stable,
                    "scope": f"{len(scoped)} golds con ausente-probado"},
           "F": len(k_stable_golds),
           "k_stable_golds": k_stable_golds,
           "golds": rows}
    out_file.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    print(f"\nF_{args.arm} = {len(k_stable_golds)} golds con fabricación K-estable "
          f"{k_stable_golds} → {out_file.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
