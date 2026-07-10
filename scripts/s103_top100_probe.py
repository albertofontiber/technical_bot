#!/usr/bin/env python3
"""s103_top100_probe.py — gate-0 judge-free del lever «pool a top-100» (pregunta de Alberto s103).

Pregunta medible: de los facts clase=retrieval-miss del scoreboard v2.2 (12), ¿cuántos ANCLAN
en el pool si retrieve_chunks corre a top_k=100 en vez de 50 (ruta e2e real, demo flags + hyq)?
Y de los que anclan a 100: ¿en qué banda cae el chunk-ancla (1-50 = ya estaba / 51-100 = ganancia
del ancho)? Constraint declarada: ef_search=120 en match_chunks_v2 (s59) → multi-modelo
(effective_top_k=200) excede la ventana HNSW; se reporta n_models por gold para leerlo.

Coste: ~12 golds × 2 retrieves (Voyage + DB), 0 LLM.
Uso: python scripts/s103_top100_probe.py
Salida: evals/s103_top100_probe.json
"""
import os

BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "GENERATOR_PROMPT_VARIANT": "fidelity",
        "GENERATOR_SELECTION_BLOCK": "off", "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off", "NEIGHBOR_WINDOW": "0"}
for k, v in BASE.items():
    os.environ[k] = v
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import unicodedata  # noqa: E402
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
import yaml  # noqa: E402
from src.rag import retriever as R  # noqa: E402
from scripts.gold_store import dev  # noqa: E402

assert R.HYQ_TABLE_ON is False


def _anchor_norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def _pool(q: str, k: int) -> list[dict]:
    R.HYQ_TABLE_ON = True
    try:
        return R.retrieve_chunks(q, top_k=k)
    finally:
        R.HYQ_TABLE_ON = False


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    fl = yaml.safe_load(open(os.path.join(os.getcwd(), "evals", "s100_factlevel_full.yaml"),
                             encoding="utf-8"))
    targets: dict[str, list[dict]] = {}
    for g in fl["per_gold"]:
        misses = [f for f in g.get("facts", [])
                  if f.get("clase") == "retrieval-miss" and f.get("lexically_anchorable")]
        if misses:
            targets[g["qid"]] = misses
    n_total_rm = sum(1 for g in fl["per_gold"] for f in g.get("facts", [])
                     if f.get("clase") == "retrieval-miss")
    golds = {g["qid"]: g for g in dev()}
    rows = []
    for qid, facts in sorted(targets.items()):
        q = golds[qid]["question"]
        models = R.extract_product_models(q)
        p50 = _pool(q, 50)
        p100 = _pool(q, 100)
        b50 = [_anchor_norm(c.get("content") or "") for c in p50]
        b100 = [_anchor_norm(c.get("content") or "") for c in p100]
        for f in facts:
            a = _anchor_norm(f.get("valor") or "")
            if len(a) < 2:
                continue
            in50 = any(a in t for t in b50)
            rank100 = next((i + 1 for i, t in enumerate(b100) if a in t), None)
            rows.append({"key": f["key"], "qid": qid, "n_models": len(models or []),
                         "pool50_n": len(p50), "pool100_n": len(p100),
                         "in_pool50": in50, "rank_at_100": rank100})
            band = ("YA-EN-50" if in50 else
                    (f"GANA@{rank100}" if rank100 else "NI-A-100"))
            print(f"  {f['key'][:42]:44s} models={len(models or [])} "
                  f"pool100={len(p100):3d}  {band}", flush=True)

    gains = [r for r in rows if not r["in_pool50"] and r["rank_at_100"]]
    ni = [r for r in rows if not r["in_pool50"] and not r["rank_at_100"]]
    stamp = {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True)
             .stdout.decode().strip(),
             "flags": {**BASE, "HYQ_TABLE": "on (call-time flip)"},
             "ef_search_constraint": "match_chunks_v2 ef=120 (s59); multi-modelo eff_k=200>120",
             "n_retrieval_miss_total_v22": n_total_rm,
             "n_anchorable_probed": len(rows)}
    out = {"stamp": stamp, "rows": rows,
           "verdict_raw": {"gains_51_100": [r["key"] for r in gains],
                           "ni_a_100": [r["key"] for r in ni]}}
    path = os.path.join(os.getcwd(), "evals", "s103_top100_probe.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nretrieval-miss v2.2: {n_total_rm} · anchorables probados: {len(rows)}")
    print(f"GANAN en banda 51-100: {len(gains)} · NI a 100: {len(ni)} · ya-en-50 (drift): "
          f"{sum(1 for r in rows if r['in_pool50'])}")
    print(f"→ {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
