#!/usr/bin/env python3
"""s71 — bundle de un gold para auditoria (read-only). Imprime TODO lo que un auditor
necesita: gold (pregunta/conducta/expected/facts) + veredicto s67base + diagnosticos del
juez (K=5) + chunks SERVIDOS (top-5, content completo) + respuestas del bot (K=5) +
pool50_light + chequeo de corpus de los hechos. Uso: python scripts/s71_bundle.py <qid>"""
import os, sys, json
os.environ["CHUNKS_TABLE"] = "chunks_v2"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
import yaml
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import gold_store
EV = ROOT / "evals"
qid = sys.argv[1]
gold = {g["qid"]: g for g in gold_store.dev()}.get(qid, {})
rep = {x["qid"]: x for x in yaml.safe_load((EV/"s67base_gate_report.yaml").read_text(encoding="utf-8"))["golds"]}
ctx = json.loads((EV/"s67base_frozen_contexts.json").read_text(encoding="utf-8"))
bg = json.loads((EV/"s67base_generations.json").read_text(encoding="utf-8"))
bj = json.loads((EV/"s67base_judgments.json").read_text(encoding="utf-8"))
r = rep.get(qid, {})
print(f"===== GOLD {qid} =====")
print("PREGUNTA:", gold.get("question"))
print("CONDUCTA_ESPERADA:", gold.get("conducta_esperada"))
print("EXPECTED_ANSWER:", (gold.get("expected_answer") or gold.get("gold_answer") or "")[:1800])
if gold.get("atomic_facts"): print("ATOMIC_FACTS:", json.dumps(gold["atomic_facts"], ensure_ascii=False)[:1200])
if gold.get("notes"): print("NOTES:", str(gold.get("notes"))[:600])
print(f"\n===== VEREDICTO s67base: {r.get('veredicto')} {r.get('votes')} | bucket={r.get('bucket')} | atrib={r.get('atribucion')} | conducta_bot={r.get('conducta_bot_modal')} =====")
print("DIAGNOSTICOS del juez (K=5):")
for k in sorted(bj.get(qid, {})):
    d = bj[qid][k].get("diagnostico")
    if d: print(f"  [run{k} {bj[qid][k].get('veredicto')}] {d[:400]}")
print(f"\n===== CHUNKS SERVIDOS (top-5) =====")
for i, c in enumerate(ctx[qid]["top5"]):
    print(f"--- [F{i+1}] {c.get('source_file')} p{c.get('page_number')} sim={c.get('similarity')} ---")
    print((c.get("content") or "")[:1400])
print(f"\n===== RESPUESTAS DEL BOT (K=5) =====")
for k in sorted(bg.get(qid, {})):
    a = bg[qid][k].get("answer")
    if a: print(f"--- run{k} ---\n{a[:1400]}")
print(f"\n===== POOL-50 servido (sources) =====")
from collections import Counter
print(dict(Counter((c.get("source_file") or "?")[:40] for c in ctx[qid]["pool50_light"])))
