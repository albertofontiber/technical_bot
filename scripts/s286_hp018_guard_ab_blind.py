"""s286 — paquete de adjudicación CIEGA-A-METADATOS del A/B del guard (brief v3.1 §A/B).

Baraja las 128 respuestas con seed fija y emite:
  - evals/s286_hp018_ab_blind_v1.jsonl : {blind_id, qkey, question, answer} — SIN celda, flags,
    k, wiring_guard ni orden original. (qkey se mantiene: la adjudicación necesita saber QUÉ se
    preguntó; la ceguera es a la CELDA.)
  - evals/s286_hp018_ab_mapping_v1.json : blind_id → job_id (para desenmascarar DESPUÉS de
    hashear los veredictos; su sha256 se imprime y debe registrarse ANTES de adjudicar).
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RUNS = "evals/s286_hp018_ab_runs_v1.jsonl"
BLIND = "evals/s286_hp018_ab_blind_v1.jsonl"
MAPPING = "evals/s286_hp018_ab_mapping_v1.json"
SEED = 2286

rows = []
bateria = None
for line in open(RUNS, encoding="utf-8"):
    r = json.loads(line)
    if "freeze" in r:
        bateria = r["freeze"]["bateria"]
    elif r.get("job_id"):
        assert "error" not in r, r["job_id"]
        rows.append(r)
assert len(rows) == 128, len(rows)

rnd = random.Random(SEED)
rnd.shuffle(rows)

mapping = {}
with open(BLIND, "w", encoding="utf-8", newline="\n") as f:
    for i, r in enumerate(rows):
        bid = f"B{i:03d}"
        mapping[bid] = r["job_id"]
        f.write(json.dumps({
            "blind_id": bid,
            "qkey": r["qkey"],
            "question": bateria[r["qkey"]],
            "answer": r["answer"],
        }, ensure_ascii=False) + "\n")

mp = json.dumps(mapping, ensure_ascii=False, sort_keys=True, indent=1)
open(MAPPING, "w", encoding="utf-8", newline="\n").write(mp)
print("blind:", BLIND, "· mapping sha256:", hashlib.sha256(mp.encode()).hexdigest())
print("REGLA: los veredictos (s286_hp018_ab_verdicts_v1.jsonl) se hashean ANTES de abrir el mapping.")
