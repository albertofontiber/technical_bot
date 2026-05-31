#!/usr/bin/env python3
"""factual_gate_eval.py — caracteriza el RECALL del eje FACTUAL del scorer.

Corre el fixture evals/factual_gate_fixture.yaml (alucinaciones CONOCIDAS +
no-alucinaciones) a través de factual_check (atomic_scorer) y mide:
  - recall        = positivos cazados / positivos   (¿caza las contradicciones?)
  - especificidad = negativos no marcados / negativos (¿evita falsos positivos, s13?)

Motivo: el review adversarial (s32) señaló que el gate factual se había demostrado
con n=1 positivo → su miss-rate estaba SIN caracterizar (peligroso en un gate de
seguridad). Esto lo cuantifica con casos etiquetados.

Uso: python scripts/factual_gate_eval.py [--fixture FILE] [--model gpt-5.5]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/
from atomic_scorer import FACTUAL_MODEL, factual_check  # noqa: E402

FIXTURE = ROOT / "evals" / "factual_gate_fixture.yaml"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default=str(FIXTURE))
    ap.add_argument("--model", default=FACTUAL_MODEL)
    args = ap.parse_args()

    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv(ROOT / ".env", override=True)
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("[ERROR] falta OPENAI_API_KEY (en .env o env).")
        return 1
    client = OpenAI(api_key=key)

    cases = yaml.safe_load(open(args.fixture, encoding="utf-8")) or []
    print(f"Fixture: {Path(args.fixture).name} · {len(cases)} casos · modelo {args.model}\n")

    tp = fp = tn = fn = errors = 0
    fails = []
    for c in cases:
        contradictions, err = factual_check(c["facts"], c["answer"], client, args.model)
        flagged = bool(contradictions) and not err
        want = (c["expect"] == "flag")
        ok = (not err) and (flagged == want)
        if err:
            errors += 1
        elif want and flagged:
            tp += 1
        elif want and not flagged:
            fn += 1
        elif (not want) and flagged:
            fp += 1
        else:
            tn += 1
        mark = "ERROR" if err else ("PASS" if ok else "FAIL")
        if not ok:
            fails.append(c["name"])
        print(f"[{mark}] {c['name']}  (expect={c['expect']}, flagged={flagged})")
        if err:
            print(f"        error: {err}")
        elif flagged:
            for x in contradictions:
                print(f"        ⚠ {str(x.get('por_que'))[:110]}")
        if (not ok) and (not err):
            print("        ← FALSO NEGATIVO (no cazó la contradicción)" if want
                  else "        ← FALSO POSITIVO (marcó algo que no era contradicción)")

    pos, neg = tp + fn, tn + fp
    print("\n" + "=" * 60)
    print(f"RECALL (alucinaciones cazadas)   = {tp}/{pos}" + (f" = {tp/pos:.0%}" if pos else ""))
    print(f"ESPECIFICIDAD (limpios no marcados) = {tn}/{neg}" + (f" = {tn/neg:.0%}" if neg else ""))
    if errors:
        print(f"errores de evaluación: {errors}")
    print("CASOS FALLIDOS: " + (", ".join(fails) if fails else "ninguno — todos OK"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
