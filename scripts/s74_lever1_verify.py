#!/usr/bin/env python3
"""s74 — VERIFY-FIRST ($0, determinista, sin LLM) del batch Lever 1 (2a+2b).

Antes de pagar la fase rerank del gate-0: ¿el batch (flags ON) cambia el POOL?
2a (broad-fallback) y 2b (keyword-order/limit) son fixes de POOL → su mecanismo se
valida con un retrieve determinista (embeddings cacheados, HyDE off, lecturas DB).
Reporta por gold: tamaño del pool y composición por canal, flags OFF vs ON.

Si el batch NO añade chunks (VECTOR de 2a / MODEL de 2b) → parar, no gastar en rerank.

Uso: python scripts/s74_lever1_verify.py
"""
from __future__ import annotations

import os

os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")

import sys
from collections import Counter
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")
sys.path.insert(0, str(ROOT))

import src.rag.retriever as rt  # noqa: E402
from src.config import RETRIEVAL_TOP_K  # noqa: E402

# Golds de retrieval del diagnóstico s71_track2 (fixables)
RET_IDS = ["cat016", "hp013", "hp008", "hp009", "cat001", "hp018", "cat013", "hp006",
           "hp003", "cat017", "cat007", "hp002", "hp001", "hp011", "cat021"]

FLAGS = ("LEVER1_BROAD_FALLBACK", "LEVER1_KEYWORD_ORDER")


def set_flags(on: bool) -> None:
    for f in FLAGS:
        if on:
            os.environ[f] = "on"
        else:
            os.environ.pop(f, None)


def pool_for(question: str, on: bool):
    set_flags(on)
    return rt.retrieve_chunks(question, top_k=RETRIEVAL_TOP_K)


def channels(pool):
    return dict(Counter(c.get("_channel") or "?" for c in pool))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    data = yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in data if g.get("qid")}

    print(f"{'GOLD':8} {'POOL off->on':14} CANALES off -> on")
    print("-" * 95)
    any_change = 0
    for qid in RET_IDS:
        g = golds.get(qid)
        if not g:
            print(f"{qid:8} (no encontrado)")
            continue
        q = g["question"]
        off = pool_for(q, False)
        on = pool_for(q, True)
        delta = len(on) - len(off)
        any_change += (delta != 0 or channels(off) != channels(on))
        flag = "  <-- +" + str(delta) if delta else ""
        print(f"{qid:8} {f'{len(off)} -> {len(on)}':14} {channels(off)}  ->  {channels(on)}{flag}")
    print("-" * 95)
    print(f"golds con cambio de pool/canal: {any_change}/{len([q for q in RET_IDS if q in golds])}")
    print("(VECTOR sube = 2a activo; MODEL/keyword sube = 2b activo. $0: embeddings cacheados.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
