#!/usr/bin/env python3
"""s94_f2_probe.py — F2 del piloto (spec v2): probe cos-vs-frontera. SOLO PRIORIZA.

Por hecho × brazo: embed de los candidatos QA-OK fact-bearing (receta blurb-B7-del-padre,
la del 2/4) + cos vs query cruda; frontera = sim#50 del canal vectorial REAL (RPC, mismo
espacio del run). DECLARADO (dúo H1/MENOR-7): la frontera post-merge real es MÁS dura
(sim#(50−n_keyword)) → esto es proxy de PRIORIZACIÓN, no mata brazos salvo margen extremo
y consistente; el veredicto lo da F3 (famtie).

Salida: evals/s94_f2_probe.json. Read-only.
"""
import json
import os
import sys
from collections import defaultdict

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

from s93_trackB_probe import TIE, fetch_chunks, rpc_frontier
from src.ingestion.embedder import embed_query
from src.rag.retriever import _cos
from src.reingest.embed import embed


def main() -> int:
    f0 = json.load(open("evals/s94_f0_testbed.json", encoding="utf-8"))
    f1 = json.load(open("evals/s94_f1_candidates.json", encoding="utf-8"))
    # v2 (regla-C sobre F2 v1): se prueban TODOS los QA-OK, no solo fact-bearing — en el
    # diseño SWAP el flip lo produce CUALQUIER surrogate del padre que rankee (el hecho
    # juzgado vive en el PADRE); fact-bearing se reporta como nivel aparte (evento 2).
    by_fact = defaultdict(list)
    for c in f1["candidatos"]:
        if c["qa_pass"]:
            by_fact[(c["qid"], c["valor"])].append(c)
    parents = fetch_chunks(sorted({c["parent_id"] for cs in by_fact.values() for c in cs}))

    results = []
    for r in f0["rows"]:
        key = (r["qid"], r["valor"])
        cs = by_fact.get(key, [])
        q_emb = embed_query(r["question"])
        s50 = rpc_frontier(q_emb)["sim50"]
        per_arm = {}
        # batch de embeddings por hecho (coste)
        texts, refs = [], []
        for c in cs:
            ch = parents.get(c["parent_id"]) or {}
            texts.append(f"{ch['context']}\n\n{c['text']}" if ch.get("context") else c["text"])
            refs.append(c)
        embs = embed(texts, "document") if texts else []
        for c, e in zip(refs, embs):
            cos = _cos(q_emb, e)
            cur = per_arm.get(c["arm"])
            if cur is None or cos > cur["cos"]:
                per_arm[c["arm"]] = {"cos": round(cos, 4), "text": c["text"][:150],
                                     "parent": c["parent_id"][:8],
                                     "fb": bool(c["fact_bearing"])}
            if c["fact_bearing"]:
                k = c["arm"] + "_fb"
                cur = per_arm.get(k)
                if cur is None or cos > cur["cos"]:
                    per_arm[k] = {"cos": round(cos, 4), "text": c["text"][:150],
                                  "parent": c["parent_id"][:8]}
        row = {"qid": r["qid"], "valor": r["valor"], "clase": r["clase"],
               "canal_sim50": round(s50, 4) if s50 else None, "n_cands": len(cs),
               "por_brazo": {a: {**v, "cruza_proxy": (v["cos"] >= (s50 or 9) - TIE)}
                             for a, v in per_arm.items()}}
        results.append(row)
        resumen = " ".join(f"{a}:{v['cos']}{'✓' if v['cos'] >= (s50 or 9) - TIE else '✗'}"
                           for a, v in sorted(per_arm.items()))
        print(f"{r['qid']:8} {r['valor'][:20]!r:22} [{r['clase'][:5]}] s50={round(s50,4) if s50 else '?'} "
              f"n={len(cs):2} {resumen or 'SIN-CANDIDATOS'}")

    json.dump({"results": results}, open("evals/s94_f2_probe.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for arm in ("R1", "R2", "R3"):
        n = sum(1 for x in results if x["por_brazo"].get(arm, {}).get("cruza_proxy"))
        print(f"{arm}: cruza-proxy {n}/{len(results)}")
    print("→ evals/s94_f2_probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
