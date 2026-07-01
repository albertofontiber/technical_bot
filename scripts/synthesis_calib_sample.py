#!/usr/bin/env python3
"""synthesis_calib_sample.py (s87) — muestra estratificada para certificación HAND-LABELED del juez_B.

El autor (Opus 4.8) etiqueta leyendo el answer real = cross-model check sobre el juez GPT-5.5 (finding-4
del cross-model: trampa+control-PASS no bastan). Estratos: TODOS los SYNTH-MISS + TODOS los borderline
+ TODOS los hechos-negación (punto blando del juez, trampa s87) + muestra determinista de SYNTH-OK.

Uso: python scripts/synthesis_calib_sample.py evals/s87_synthesis_full.yaml
Salida: evals/s87_calib_sample.md (para etiquetar a mano) — imprime (valor, texto, veredicto-juez, answer).
"""
import sys, re
from pathlib import Path
import yaml

NEG = re.compile(r"\b(no|sin|not|non)\b", re.I)

def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "evals/s87_synthesis_full.yaml")
    d = yaml.safe_load(src.read_text(encoding="utf-8"))
    ans = {r["qid"]: r["answer"] for r in d["results"]}
    rows = []
    for r in d["results"]:
        for f in r["facts"]:
            rows.append({**f, "qid": r["qid"]})
    miss = [x for x in rows if x["clase"] == "SYNTH-MISS"]
    border = [x for x in rows if x.get("borderline")]
    neg = [x for x in rows if NEG.search(x["valor"]) and x["clase"] == "SYNTH-OK" and not x.get("borderline")]
    ok = [x for x in rows if x["clase"] == "SYNTH-OK" and not x.get("borderline")]
    ok_sample = ok[::max(1, len(ok)//10)][:10]  # ~10 determinista
    sel, seen = [], set()
    for tag, group in [("SYNTH-MISS", miss), ("BORDERLINE", border), ("NEG-OK", neg), ("OK-SAMPLE", ok_sample)]:
        for x in group:
            key = (x["qid"], x["valor"], x["texto"])
            if key in seen: continue
            seen.add(key); sel.append((tag, x))
    out = ["# s87 — muestra de calibración del juez_B (etiquetar a mano leyendo el ANSWER)\n",
           f"Total filas: {len(rows)} | seleccionadas: {len(sel)} "
           f"(MISS={len(miss)} BORDER={len(border)} NEG-OK={len(neg)} OK-sample={len(ok_sample)})\n"]
    for tag, x in sel:
        a = ans[x["qid"]]
        out.append("\n" + "="*80)
        out.append(f"[{tag}] {x['qid']} | juez yes={x['yes']}/5 reaches_gen={x['reaches_gen']} clase={x['clase']}")
        out.append(f"  VALOR: {x['valor']!r}")
        out.append(f"  TEXTO: {x['texto']}")
        out.append(f"  ANSWER ({len(a)} ch):\n{a}")
    p = src.with_name("s87_calib_sample.md")
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"[written] {p} | {len(sel)} filas para etiquetar (MISS={len(miss)} BORDER={len(border)} "
          f"NEG-OK={len(neg)} OK={len(ok_sample)})")

if __name__ == "__main__":
    main()
