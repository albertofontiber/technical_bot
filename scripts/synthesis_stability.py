#!/usr/bin/env python3
"""synthesis_stability.py (s87) — acota la VARIANZA DE GENERACIÓN del cuello-síntesis.

Sonnet temp=0 es no-determinista (declarado en s67base) → el conteo SYNTH-MISS de 1 generación tiene
ruido (hp007 flipeó subset↔full). Cruza 2 reps (generaciones independientes) por-hecho:
  stable-MISS = SYNTH-MISS en AMBAS reps (omisión estructural, robusta a varianza)
  flip        = SYNTH-MISS en UNA (borde OK/MISS, sensible a la estocasticidad de la generación)
  stable-OK   = SYNTH-OK/NOT-IN-CTX en ambas

Uso: python scripts/synthesis_stability.py evals/s87_synthesis_full.yaml evals/s87_synthesis_rep1.yaml
"""
import sys
from pathlib import Path
from collections import Counter
import yaml

def load(p):
    d = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
    out = {}
    for r in d["results"]:
        for i, f in enumerate(r["facts"]):
            out[(r["qid"], i)] = {"valor": f["valor"], "clase": f["clase"], "yes": f["yes"]}
    return out

def main():
    a = load(sys.argv[1]); b = load(sys.argv[2])
    keys = sorted(set(a) & set(b))
    def is_miss(x): return x["clase"] == "SYNTH-MISS"
    stable_miss, flip, stable_ok = [], [], []
    for k in keys:
        m0, m1 = is_miss(a[k]), is_miss(b[k])
        if m0 and m1: stable_miss.append(k)
        elif m0 or m1: flip.append(k)
        else: stable_ok.append(k)
    print(f"pares de hechos comparables: {len(keys)}")
    print(f"  stable-MISS (omisión en AMBAS reps) = {len(stable_miss)}")
    print(f"  flip (MISS en 1 de 2)               = {len(flip)}")
    print(f"  stable-OK                            = {len(stable_ok)}")
    print(f"\n  rep0 SYNTH-MISS = {sum(1 for k in keys if is_miss(a[k]))} | "
          f"rep1 SYNTH-MISS = {sum(1 for k in keys if is_miss(b[k]))}")
    print("\n── stable-MISS (el cuello-síntesis ROBUSTO) ──")
    for k in stable_miss:
        print(f"  {k[0]:8s} yes0={a[k]['yes']} yes1={b[k]['yes']} {a[k]['valor']!r}")
    print("\n── flip (sensibles a varianza de generación) ──")
    for k in flip:
        print(f"  {k[0]:8s} r0={a[k]['clase']}(y{a[k]['yes']}) r1={b[k]['clase']}(y{b[k]['yes']}) {a[k]['valor']!r}")
    out = Path(sys.argv[1]).with_name("s87_synthesis_stability.yaml")
    out.write_text(yaml.safe_dump({
        "n_pairs": len(keys), "stable_miss": len(stable_miss), "flip": len(flip), "stable_ok": len(stable_ok),
        "stable_miss_facts": [{"qid": k[0], "idx": k[1], "valor": a[k]["valor"]} for k in stable_miss],
        "flip_facts": [{"qid": k[0], "idx": k[1], "valor": a[k]["valor"],
                        "r0": a[k]["clase"], "r1": b[k]["clase"]} for k in flip],
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"\n[written] {out}")

if __name__ == "__main__":
    main()
