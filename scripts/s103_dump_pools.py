#!/usr/bin/env python3
"""s103_dump_pools.py — vuelca los pools completos (chunks con content) de los 39 dev con el
código VIGENTE del checkout donde se corre (uso: worktree@HEAD = carve-out s102 → brazo OLD).
Insumo del served-churn gate v2 (contraste correcto old-vs-v3, no presencia-del-canal).

Uso: python scripts/s103_dump_pools.py <etiqueta>   → evals/s103_pools_<etiqueta>.jsonl
"""
import os

BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "GENERATOR_SELECTION_BLOCK": "off", "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off",
        "NEIGHBOR_WINDOW": "0"}
for k, v in BASE.items():
    os.environ[k] = v
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
from src.rag import retriever as R  # noqa: E402
from scripts.gold_store import dev  # noqa: E402


def main(label: str):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True).stdout.decode().strip()
    path = os.path.join(os.getcwd(), "evals", f"s103_pools_{label}.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_stamp": {"label": label, "git_sha": sha,
                                        "flags": {**BASE, "HYQ_TABLE": "on (flip)"}}},
                            ensure_ascii=False) + "\n")
        for g in dev():
            R.HYQ_TABLE_ON = True
            try:
                pool = R.retrieve_chunks(g["question"], top_k=50)
            finally:
                R.HYQ_TABLE_ON = False
            keep = [{k: c.get(k) for k in
                     ("id", "content", "context", "product_model", "section_title",
                      "content_type", "manufacturer", "source_file", "page_number",
                      "similarity", "has_diagram", "language", "_channel",
                      "_hyq_surrogate", "_hyq_boosted", "_hyq_question")} for c in pool]
            fh.write(json.dumps({"qid": g["qid"], "question": g["question"],
                                 "chunks": keep}, ensure_ascii=False) + "\n")
            print(f"  {g['qid']:8s} pool={len(pool)}", flush=True)
    print(f"→ {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "old"))
