"""s97 GATE-0 (artefacto, dúo H4) — replay del _diversify_by_source_file REAL con y sin
tie-break sobre los pools capturados de hp012/'99+99' y hp018/'1 A'.

El probe inline (rank-en-grupo 2/16 y 2/19) NO probaba la SELECCIÓN: depende de los
0.82/0.85 por encima, del cap por-fuente y del orden de fuentes. Este replay corre el
código real dos veces sobre EL MISMO pool → ¿la aguja entra al top-50 con flag on?
Si no entra → NO construir el brazo famtie (ahorra la medición).

Salida: evals/s97_gate0.json. Config: demo (multivector on, identity on/add).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ["ENUNCIADOS_MULTIVECTOR"] = "on"
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "add"

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["ENUNCIADOS_MULTIVECTOR"] = "on"
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "add"

import yaml  # noqa: E402

import src.rag.retriever as R  # noqa: E402

TARGETS = [("hp012", "99 + 99"), ("hp018", "1 A")]


def main() -> int:
    d = yaml.safe_load(open(ROOT / "evals" / "s85_retrieval_miss_DEF.yaml", encoding="utf-8"))
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(ROOT / "evals" / "gold_answers_v1.yaml", encoding="utf-8"))}
    out = {"config": {"multivector": "on", "identity": "on/add", "top_k": 50}, "targets": {}}
    orig = R._diversify_by_source_file

    for qid, valor in TARGETS:
        fact = [f for r in d["reps"][0]["results"] if r["qid"] == qid
                for f in r["facts"] if f["valor"] == valor][0]
        sup = set(fact["votes"].keys())

        cap: dict = {}

        def spy(chunks, top_k, models, *a, **k):
            if "pool" not in cap:
                cap["pool"] = [dict(c) for c in chunks]     # copia: el replay muta orden
                cap["args"] = (top_k, models)
                cap["kwargs"] = {kk: vv for kk, vv in k.items()}
            return orig(chunks, top_k, models, *a, **k)

        R._diversify_by_source_file = spy
        try:
            R.retrieve_chunks(golds[qid]["question"], top_k=50)
        finally:
            R._diversify_by_source_file = orig
        if "pool" not in cap:
            out["targets"][f"{qid}·{valor}"] = {"error": "diversify no corrió"}
            continue

        res = {}
        for mode in ("off", "cosine"):
            os.environ["DIVERSIFY_TIEBREAK"] = mode
            pool = [dict(c) for c in cap["pool"]]
            top_k, models = cap["args"]
            kw = dict(cap["kwargs"])
            kw.pop("query_embedding", None)
            selected = orig(pool, top_k, models, golds[qid]["question"],
                            query_embedding=R.embed_query(golds[qid]["question"]), **kw)
            res[mode] = {
                "needle_in": sum(1 for c in selected if c.get("id") in sup),
                "pool_out": len(selected),
                "sim_intacta": all(isinstance(c.get("similarity"), (int, float))
                                   for c in selected),
            }
        os.environ["DIVERSIFY_TIEBREAK"] = "off"
        out["targets"][f"{qid}·{valor}"] = res
        print(f"{qid} '{valor}': off→aguja {res['off']['needle_in']} · "
              f"cosine→aguja {res['cosine']['needle_in']}")

    ok = all(t.get("cosine", {}).get("needle_in", 0) >= 1
             for t in out["targets"].values() if "error" not in t)
    out["gate0"] = "PASA" if ok else "FALLA"
    json.dump(out, open(ROOT / "evals" / "s97_gate0.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"GATE-0: {out['gate0']} → evals/s97_gate0.json")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
