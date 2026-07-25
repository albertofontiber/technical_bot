#!/usr/bin/env python3
"""s103_seam_probe.py — fork DEC-097 disparado: replay de la composición fallida de cat021
(v3.1: el rerank-60 sirve el user-guide del 40/40R y la generación ASUME la variante) con el
seam de selección s102 aplicado (`GENERATOR_SELECTION_BLOCK=on`).

Mide K=3 (juez canónico) sobre:
  · cat021 — diana: con el seam, la generación debe volver a ENUMERAR (regla s79/s80).
  · hp009  — efecto-lado conocido del seam (s102: clarify intermitente 1/2 donde se espera
    answer family-genérico) — la conducta debe seguir siendo answer.
Ambos con pools v3.1 live (HYQ on). Pre-requisito: `git apply evals/s102_selection_seam.patch`.

Uso: python scripts/s103_seam_probe.py
Salida: evals/s103_seam_probe.json
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
DEMO = {"CHUNKS_TABLE": "chunks_v2", "HYDE_ENABLED": "false", "ENUNCIADOS_MULTIVECTOR": "on",
        "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "add",
        "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off", "LLM_MAX_TOKENS": "3500",
        "RERANK_TOP_K": "10", "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps",
        "RERANK_PREVIEW_CHARS": "800", "GENERATOR_PROMPT_VARIANT": "fidelity",
        "GENERATOR_SELECTION_BLOCK": "on"}
for k, v in DEMO.items():
    os.environ[k] = v
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)
for k, v in DEMO.items():
    os.environ[k] = v
import json  # noqa: E402
import subprocess  # noqa: E402
import yaml  # noqa: E402
import src.rag.generator as GEN  # noqa: E402
from src.rag import retriever as R  # noqa: E402
from src.rag.retriever import extract_product_models, retrieve_chunks  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402
from bvg_kmajority import _judge_one  # noqa: E402

K = 3


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    assert GEN._selection_block_on(), "seam no aplicado — `git apply evals/s102_selection_seam.patch`"
    golds = {g["qid"]: g for g in yaml.safe_load(open(ROOT / "evals" / "gold_answers_v1.yaml",
             encoding="utf-8"))}
    out = {"stamp": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                               capture_output=True).stdout.decode().strip(),
                     "flags": {**DEMO, "HYQ_TABLE": "on (call-time)"},
                     "seam": "evals/s102_selection_seam.patch aplicado"}, "rows": []}
    for qid in ("cat021", "hp009"):
        g = golds[qid]
        R.HYQ_TABLE_ON = True
        try:
            pool = retrieve_chunks(g["question"], top_k=50)
        finally:
            R.HYQ_TABLE_ON = False
        tm = extract_product_models(g["question"]) or None
        served = rerank_chunks(g["question"], pool, top_k=10, target_models=tm)
        gens, votes = [], []
        for i in range(K):
            r = GEN.generate_answer(g["question"], served, available_models=None)
            ans = r.get("answer") or ""
            gens.append(ans)
            _, _, row = _judge_one(((qid, "seam", i), 0, g["question"],
                                    g.get("conducta_esperada", "answer"),
                                    g.get("gold_answer", ""), ans))
            votes.append(row.get("veredicto", "?"))
        out["rows"].append({"qid": qid, "votes": votes, "pool_n": len(pool),
                            "answers": [a[:800] for a in gens]})
        print(f"  {qid:8s} votes={votes}", flush=True)
        print(f"    A0: {gens[0][:220]}", flush=True)
    json.dump(out, open(ROOT / "evals" / "s103_seam_probe.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("→ evals/s103_seam_probe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
