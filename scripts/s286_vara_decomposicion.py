"""s286 — descomposición del salto de FALLOs (pregunta de Alberto 29-jul).

Re-juzga las 39 respuestas ALMACENADAS del baseline v4 (ship config) bajo la
letra v3. Mismas respuestas + mismos golds vigentes en ambos brazos → el delta
v3→v4 sobre estas filas es EXCLUSIVAMENTE efecto de la vara. El residuo contra
el baseline v3 histórico (16/20/3, s284: otras respuestas, golds pre-r1/r2,
corpus pre-tachados) = generación+golds+corpus, y se atribuye por-qid aparte.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402
from openai import OpenAI  # noqa: E402
import gold_store  # noqa: E402

BASELINE_V4 = ROOT / "evals" / "bot_vs_gold_39_baseline_shipconfig_v4judge_s286.yaml"
OUT = ROOT / "evals" / "s286_vara_decomposicion_v1.json"

env = dict(l.strip().split("=", 1) for l in open(ROOT / ".env", encoding="utf-8")
           if l.strip() and not l.startswith("#") and "=" in l)
os.environ.setdefault("OPENAI_API_KEY", env.get("OPENAI_API_KEY", ""))

rows = yaml.safe_load(open(BASELINE_V4, encoding="utf-8"))
golds = {g["qid"]: g for g in gold_store.load()}
oai = OpenAI()

os.environ["JUDGE_VARA"] = "v3"
spec = importlib.util.spec_from_file_location("tbg_v3", ROOT / "scripts" / "test_bot_vs_gold.py")
tbg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tbg)
assert tbg.JUDGE_VARA == "v3"

out = {}
for r in rows:
    qid = r["qid"]
    g = golds[qid]
    v = tbg.judge(oai, g["question"], g.get("conducta_esperada", "answer"),
                  g.get("gold_answer", ""), r["bot_answer"], gold_row=g)
    out[qid] = {
        "v4": r["veredicto"],
        "v3_mismas_respuestas": v.get("veredicto"),
        "diag_v3": str(v.get("diagnostico"))[:250],
    }
    flag = " ★" if out[qid]["v3_mismas_respuestas"] != r["veredicto"] else ""
    print(f"{qid}: v4={r['veredicto']} | v3={out[qid]['v3_mismas_respuestas']}{flag}")

c_v4 = Counter(x["v4"] for x in out.values())
c_v3 = Counter(x["v3_mismas_respuestas"] for x in out.values())
print("\nMISMAS respuestas, MISMOS golds:")
print(f"  vara v4: {dict(c_v4)}")
print(f"  vara v3: {dict(c_v3)}")
print("  → el delta de arriba es SOLO vara; el resto del salto vs 16/20/3 (s284)")
print("    es generación+golds+corpus (atribución por-qid en el JSON).")
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"→ {OUT.relative_to(ROOT)}")
