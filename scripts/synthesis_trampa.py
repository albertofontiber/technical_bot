#!/usr/bin/env python3
"""synthesis_trampa.py (s87) — certificación NEGATIVA del juez_B de synthesis_miss_judge.

Sesgo peligroso = sobre-acreditar "conveyed" (juez dice afirmado=true cuando el hecho NO está en la
respuesta) → DESINFLA synthesis-miss → hace el cuello parecer menor de lo que es. Justo el resultado
que mi sesgo de convergencia querría (feedback_my_bias) → guardarraíl innegociable antes de creer el full.

Método: por cada hecho SÍNTESIS ya juzgado (lee el yaml de synthesis_miss_judge, que trae answer+facts),
juzgar un VALOR PERTURBADO (falso) contra la MISMA respuesta real. El juez DEBE devolver afirmado=false.
FP = afirmado=true a un valor inexistente. Perturbaciones:
  · numérico: cada dígito +3 mod 10 (reusa retrieval_miss_judge._perturb)
  · no-numérico: negación/antónimo curado (no enclavado→enclavado, failsafe→no-failsafe, NC→NO)
Un +3 puede COINCIDIR con otro valor real del gold (p.ej. 3→6 meses si 6 meses existe) → se marca
`coincidencia_posible` y NO cuenta como FP (se revisa a mano).

Uso: python scripts/synthesis_trampa.py evals/s87_synthesis_subset.yaml
"""
from __future__ import annotations
import os
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
import sys, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

ROOT = Path(os.getcwd()).resolve()
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import yaml
from synthesis_miss_judge import _judge_once, K, THRESH_FIRM

NONNUM = {  # antónimos/negaciones curados para valores no-numéricos
    "no enclavado": "enclavado", "enclavado": "no enclavado",
    "NC-C-NA": "solo NA (sin NC ni C)", "failsafe": "no failsafe (se energiza para señalar)",
}

def perturb_num(valor: str) -> str:
    return "".join(str((int(ch) + 3) % 10) if ch.isdigit() else ch for ch in valor)

def make_fake(valor: str) -> tuple[str, str] | None:
    if any(ch.isdigit() for ch in valor):
        fake = perturb_num(valor)
        return (fake, "num") if fake != valor else None
    if valor in NONNUM:
        return (NONNUM[valor], "nonnum")
    return None  # sin perturbación fiable → se salta (cuenta aparte)

def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "evals/s87_synthesis_subset.yaml")
    d = yaml.safe_load(src.read_text(encoding="utf-8"))
    cases, skipped = [], 0
    for r in d["results"]:
        qid, answer = r["qid"], r["answer"]
        real_vals = {f["valor"] for f in r["facts"]}
        for f in r["facts"]:
            mk = make_fake(f["valor"])
            if not mk:
                skipped += 1; continue
            fake, kind = mk
            coincide = fake in real_vals  # el fake ES otro valor real del gold
            with ThreadPoolExecutor(max_workers=6) as pool:
                votes = [x.result() for x in [pool.submit(_judge_once, fake, f["texto"], answer) for _ in range(K)]]
            yes = sum(1 for v in votes if v == 1)
            fp = (yes >= THRESH_FIRM) and not coincide
            cases.append({"qid": qid, "valor_real": f["valor"], "valor_fake": fake, "kind": kind,
                          "yes_fake": yes, "coincide": coincide, "FP": fp})
    n = len(cases); fp = sum(1 for c in cases if c["FP"]); coinc = sum(1 for c in cases if c["coincide"])
    print(f"TRAMPA synthesis_judge: {fp}/{n} FP (afirmado≥{THRESH_FIRM}/5 a valor falso) = "
          f"{fp/n*100:.1f}%  | {coinc} coincidencias-posibles (excluidas) | {skipped} sin-perturbación")
    print("  umbral de aceptación ≤10%\n")
    for c in sorted(cases, key=lambda x: -x["yes_fake"]):
        flag = "  <<< FP!" if c["FP"] else (" (coincide)" if c["coincide"] else "")
        print(f"  {c['qid']:8s} {c['kind']:6s} real={c['valor_real']!r:20s} fake={c['valor_fake']!r:24s} "
              f"yes_fake={c['yes_fake']}/5{flag}")
    out = src.with_name(src.stem + "_trampa.yaml")
    out.write_text(yaml.safe_dump({"n": n, "n_fp": fp, "fp_rate": round(fp/n, 3),
                                   "n_coincidencia": coinc, "cases": cases},
                                  allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"\n[written] {out}")

if __name__ == "__main__":
    main()
