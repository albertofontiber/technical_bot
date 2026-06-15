#!/usr/bin/env python3
"""s74 — GATE-0 rerank del batch Lever 1 (JUDGE-FREE, modal). Diseño _s74_lever1_batch_design.md.

Métrica: factcov-sobre-top5 = fracción de las CITAS del gold (texto literal del manual)
presentes (strict_match) en los 5 chunks que el reranker ELIGE. Es el cuello que importa:
"¿el chunk con el dato llega al top-5?" — judge-free (esquiva el ±2 del juez).

Por el DADO del reranker LLM (DEC-041 d-bis): top-5 MODAL de n=3 réplicas, y el BASELINE
(flags off) se re-corre EN ESTA MISMA SESIÓN (no contra un top-5 frozen viejo).

Configs (atribución): base_off_800 → batch_800 (efecto 2a+2b, pool) → batch_2400/4000 (efecto 2c, ventana).
Scope: 15 target (retrieval s71) + 10 PASS-control (shadow de regresión).
Coste: solo rerank LLM (~$9-12). Retrieve $0 (embed-cache). Resumable.

Uso: python scripts/s74_lever1_gate0.py [run|report]
"""
from __future__ import annotations

import os

os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")

import hashlib
import json
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
sys.path.insert(0, str(ROOT / "scripts"))

import src.rag.retriever as rt  # noqa: E402
import src.rag.reranker as rk  # noqa: E402
from src.rag.reranker import rerank  # noqa: E402
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from strict_match import chunk_has_quote_strict  # noqa: E402

TARGET = ["cat016", "hp013", "hp008", "hp009", "cat001", "hp018", "cat013", "hp006",
          "hp003", "cat017", "cat007", "hp002", "hp001", "hp011", "cat021"]
PASS_CONTROL = ["cat005", "cat010", "cat014", "cat015", "cat018", "cat022",
                "cat023", "hp015", "hp019", "hp020"]
N = 3
CONFIGS = [("base_off_800", False, 800), ("batch_800", True, 800),
           ("batch_2400", True, 2400), ("batch_4000", True, 4000)]
F_OUT = ROOT / "evals" / "s74_lever1_gate0.json"

_pools: dict = {}


def set_flags(on: bool) -> None:
    for f in ("LEVER1_BROAD_FALLBACK", "LEVER1_KEYWORD_ORDER"):
        if on:
            os.environ[f] = "on"
        else:
            os.environ.pop(f, None)


def get_pool(qid: str, question: str, on: bool) -> list[dict]:
    key = (qid, on)
    if key not in _pools:
        set_flags(on)
        _pools[key] = rt.retrieve_chunks(question, top_k=RETRIEVAL_TOP_K)
    return _pools[key]


def chash(c: dict) -> str:
    return hashlib.sha1((c.get("content") or "").encode("utf-8")).hexdigest()[:12]


def factcov(top5: list[dict], quotes: list[str]):
    if not quotes:
        return None
    hit = sum(1 for q in quotes
              if any(chunk_has_quote_strict(c.get("content") or "", q) for c in top5))
    return [hit, len(quotes)]


def _load() -> dict:
    return json.loads(F_OUT.read_text(encoding="utf-8")) if F_OUT.exists() else {}


def _save(d: dict) -> None:
    F_OUT.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


def run() -> int:
    data = yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in data if g.get("qid")}
    out = _load()
    for qid in TARGET + PASS_CONTROL:
        g = golds.get(qid)
        if not g:
            print(f"  {qid}: NO ENCONTRADO"); continue
        quotes = [c["quote"] for c in (g.get("citations") or []) if c.get("quote")]
        for name, on, prev in CONFIGS:
            if qid in out.get(name, {}):
                continue
            pool = get_pool(qid, g["question"], on)
            rk.RERANK_PREVIEW_CHARS = prev
            if len(pool) <= RERANK_TOP_K:
                top5_modal, stable = pool, True
            else:
                tiradas, vistas = [], []
                for _ in range(N):
                    t5 = rerank(g["question"], list(pool), top_k=RERANK_TOP_K, strict=True)
                    tiradas.append(tuple(chash(c) for c in t5)); vistas.append(t5)
                modal = Counter(tiradas).most_common(1)[0][0]
                top5_modal = next(v for v, t in zip(vistas, tiradas) if t == modal)
                stable = len(set(tiradas)) == 1
            out.setdefault(name, {})[qid] = {
                "factcov": factcov(top5_modal, quotes), "stable": stable,
                "pool": len(pool), "n_quotes": len(quotes)}
            _save(out)
            fc = out[name][qid]["factcov"]
            print(f"  {name}/{qid}: factcov={fc} pool={len(pool)} {'stable' if stable else 'DADO'}")
    print(f"run OK → {F_OUT.name}")
    return 0


def report() -> int:
    out = _load()

    def agg(ids):
        res = {}
        for name, _, _ in CONFIGS:
            hit = tot = 0
            for qid in ids:
                fc = out.get(name, {}).get(qid, {}).get("factcov")
                if fc:
                    hit += fc[0]; tot += fc[1]
            res[name] = f"{hit}/{tot}"
        return res

    print("=== factcov-sobre-top5 AGREGADO (citas del gold presentes en el top-5 modal) ===")
    print("TARGET (15 retrieval golds):", agg(TARGET))
    print("PASS-CONTROL (10 golds):    ", agg(PASS_CONTROL))
    print()
    print("=== por gold TARGET (base_off_800 -> batch_800 -> batch_2400 -> batch_4000) ===")
    for qid in TARGET:
        row = [str(out.get(n, {}).get(qid, {}).get("factcov")) for n, _, _ in CONFIGS]
        dado = [n for n, _, _ in CONFIGS if out.get(n, {}).get(qid, {}).get("stable") is False]
        print(f"  {qid:8} {' -> '.join(row):40} {'DADO:' + ','.join(dado) if dado else ''}")
    print()
    print("=== PASS-CONTROL (vigilar caídas = regresión) ===")
    for qid in PASS_CONTROL:
        row = [str(out.get(n, {}).get(qid, {}).get("factcov")) for n, _, _ in CONFIGS]
        print(f"  {qid:8} {' -> '.join(row)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    fase = sys.argv[1] if len(sys.argv) > 1 else "run"
    # firm-up n=7 (DEC-016b: firmar el gate antes del A/B; el dado n=3 fue pesado): base vs
    # batch@2400 (valor elegido por dato) sobre los golds DECISIVOS (gainers + dado-sensibles +
    # losers) + los PASS-control que se movieron (cat022/cat010). Salida separada.
    if fase.startswith("firmup"):
        N = 7
        CONFIGS = [("base_off_800", False, 800), ("batch_2400", True, 2400)]
        F_OUT = ROOT / "evals" / "s74_lever1_firmup.json"
        TARGET = ["hp008", "hp002", "hp003", "hp018", "cat001", "cat017", "hp013",
                  "hp001", "hp011", "cat016", "hp009"]
        PASS_CONTROL = ["cat022", "cat010"]
    sys.exit(run() if fase in ("run", "firmup") else report())
