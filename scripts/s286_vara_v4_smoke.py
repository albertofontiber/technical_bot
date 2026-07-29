"""s286 — humo de la vara v4: re-juzga respuestas EXISTENTES del baseline v3 bajo v3 y v4.

Mismas respuestas + mismos golds (vigentes) en ambos brazos → el delta es SOLO de vara.
Subset: los 4 clase-B del packet r2 (PARCIAL-por-supplementary: cat008, hp003, hp008, hp020)
+ 2 controles PASS (cat012, hp007). Esperado: clase-B se resuelve (→PASS bajo v4 si los cores
están cubiertos), controles PASS no se caen (anti checklist-bias).
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402
from openai import OpenAI  # noqa: E402
import gold_store  # noqa: E402

QIDS = ["cat008", "hp003", "hp008", "hp020", "cat012", "hp007"]
BASELINE = ROOT / "evals" / "bot_vs_gold_39_baseline_c1v4_v3judgefull_s284.yaml"

env = dict(l.strip().split("=", 1) for l in open(ROOT / ".env", encoding="utf-8")
           if l.strip() and not l.startswith("#") and "=" in l)
os.environ.setdefault("OPENAI_API_KEY", env.get("OPENAI_API_KEY", ""))

rows = {r["qid"]: r for r in yaml.safe_load(open(BASELINE, encoding="utf-8"))}
golds = {g["qid"]: g for g in gold_store.load()}
oai = OpenAI()

out = {}
for vara in ("v3", "v4"):
    os.environ["JUDGE_VARA"] = vara
    spec = importlib.util.spec_from_file_location(f"tbg_{vara}", ROOT / "scripts" / "test_bot_vs_gold.py")
    tbg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tbg)
    assert tbg.JUDGE_VARA == vara
    for qid in QIDS:
        r, g = rows[qid], golds[qid]
        v = tbg.judge(oai, g["question"], g.get("conducta_esperada", "answer"),
                      g.get("gold_answer", ""), r["bot_answer"], gold_row=g)
        out.setdefault(qid, {})[vara] = {"veredicto": v.get("veredicto"),
                                          "diag": str(v.get("diagnostico"))[:200]}
        print(f"{vara} {qid}: {v.get('veredicto')}")

print("\nRESUMEN (v3 → v4):")
for qid in QIDS:
    a, b = out[qid]["v3"]["veredicto"], out[qid]["v4"]["veredicto"]
    print(f"  {qid}: {a} → {b}" + ("  ★" if a != b else ""))
json.dump(out, open(ROOT / "evals" / "s286_vara_v4_smoke_v1.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("→ evals/s286_vara_v4_smoke_v1.json")
