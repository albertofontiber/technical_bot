#!/usr/bin/env python3
"""s103_gold_arm_probe.py — A/B outcome de UN gold: ctrl (pool old del dump) vs treat (v3.1
live), K=3 + juez canónico. Para atribuir una conducta observada (¿v3.1 o baseline?).

Uso: python scripts/s103_gold_arm_probe.py <qid>
Salida: evals/s103_gold_arm_<qid>.json
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
DEMO = {"CHUNKS_TABLE": "chunks_v2", "HYDE_ENABLED": "false", "ENUNCIADOS_MULTIVECTOR": "on",
        "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "add",
        "GENERATOR_SELECTION_BLOCK": "off", "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off",
        "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10", "RERANKER_BACKEND": "llm",
        "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "GENERATOR_PROMPT_VARIANT": "fidelity"}
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


def main(qid: str):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    g = next(x for x in yaml.safe_load(open(ROOT / "evals" / "gold_answers_v1.yaml",
                                            encoding="utf-8")) if x["qid"] == qid)
    old = None
    for line in open(ROOT / "evals" / "s103_pools_old.jsonl", encoding="utf-8"):
        row = json.loads(line)
        if row.get("qid") == qid:
            old = row["chunks"]
            break
    assert old, f"{qid} no está en el dump old"
    R.HYQ_TABLE_ON = True
    try:
        v3 = retrieve_chunks(g["question"], top_k=50)
    finally:
        R.HYQ_TABLE_ON = False
    tm = extract_product_models(g["question"]) or None
    out = {"stamp": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                               capture_output=True).stdout.decode().strip(),
                     "flags": {**DEMO, "HYQ_TABLE": "on (call-time)"}}, "qid": qid, "arms": {}}
    for arm, pool in (("ctrl_old", old), ("treat_v3", v3)):
        served = rerank_chunks(g["question"], [dict(c) for c in pool], top_k=10,
                               target_models=tm, strict=True)
        votes, answers = [], []
        for i in range(K):
            r = GEN.generate_answer(g["question"], served, available_models=None)
            ans = r.get("answer") or ""
            answers.append(ans[:800])
            _, _, row = _judge_one(((qid, arm, i), 0, g["question"],
                                    g.get("conducta_esperada", "answer"),
                                    g.get("gold_answer", ""), ans))
            votes.append(row.get("veredicto", "?"))
        out["arms"][arm] = {"votes": votes, "answers": answers,
                            "served_srcs": [c.get("source_file", "")[:24] for c in served]}
        print(f"  {qid} {arm:9s} votes={votes}", flush=True)
    path = ROOT / "evals" / f"s103_gold_arm_{qid}.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "hp009"))
