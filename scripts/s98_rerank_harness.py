"""s98 · Harness FIEL de experimentos del rerank (pre-registro v2 s98_rerank_matrix.md).

Aísla el rerank: congela el pool-50 real (retrieve_chunks, config shipped) CON similarity +
has_diagram + content + target_models + needles + manifest; cada método solo re-rankea el
pool congelado CON target_models (path productivo) → top-5 → filtro similarity>=RELEVANCE_
THRESHOLD (lo que hace el generador) → 'servido'. Métrica RERANK-MISS = aguja-en-pool que NO
sobrevive al servido. Dúo s98 (2 críticos de fidelidad): sin similarity/has_diagram el pool
NO era fiel; corregido aquí.

Uso:
  python scripts/s98_rerank_harness.py freeze            # congela pools + manifest (1 vez)
  python scripts/s98_rerank_harness.py run M0|M1|...     # rerankea + mide (barato)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
# config SHIPPED (fija ANTES de importar retriever)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ["ENUNCIADOS_MULTIVECTOR"] = "on"
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "add"
os.environ["DIVERSIFY_TIEBREAK"] = "off"

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)
for k, v in {"CHUNKS_TABLE": "chunks_v2", "HYDE_ENABLED": "false",
             "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
             "IDENTITY_RESOLVE_POLICY": "add", "DIVERSIFY_TIEBREAK": "off"}.items():
    os.environ[k] = v

import inspect  # noqa: E402

import yaml  # noqa: E402

F_POOLS = ROOT / "evals" / "s98_pools_v2.json"
F_MANIFEST = ROOT / "evals" / "s98_pools_v2_manifest.json"

# --- métodos ESTRUCTURALES (relevance_instruction; None = M0 baseline de prod) ---
METHODS = {
    "M0": None,
    "M1": ("Evalúa qué fragmentos CONTIENEN el dato, valor o procedimiento CONCRETO que "
           "responde la pregunta del técnico — NO basta con que hablen del mismo tema, "
           "producto o sección; prioriza el fragmento que INCLUYE la respuesta específica "
           "(el borne, el código, el valor numérico, el paso), aunque su vocabulario no "
           "coincida con las palabras de la pregunta."),
}


def _needles() -> dict:
    fam = yaml.safe_load(open(ROOT / "evals" / "s85_retrieval_miss_DEF.yaml", encoding="utf-8"))
    nd = {}
    for r in fam["reps"][0]["results"]:
        for f in r["facts"]:
            if f.get("tipo_core") or True:  # todas; el core lo filtramos por gold
                nd[(r["qid"], f["valor"])] = set(f.get("votes", {}).keys())
    return nd


def freeze() -> int:
    import src.rag.retriever as R
    from src.rag.retriever import extract_product_models
    golds = [g for g in yaml.safe_load(open(ROOT / "evals" / "gold_answers_v1.yaml",
             encoding="utf-8"))]
    # solo dev (embargo held-out)
    import gold_store
    dev_qids = {g["qid"] for g in gold_store.verified()}
    pools = {}
    for g in golds:
        qid = g["qid"]
        if qid not in dev_qids:
            continue
        pool = R.retrieve_chunks(g["question"], top_k=50)
        pools[qid] = {
            "question": g["question"],
            "target_models": extract_product_models(g["question"]),
            "pool": [{"id": c.get("id"), "content": c.get("content"),
                      "similarity": c.get("similarity"), "source_file": c.get("source_file"),
                      "page_number": c.get("page_number"), "product_model": c.get("product_model"),
                      "has_diagram": c.get("has_diagram"), "diagram_url": c.get("diagram_url"),
                      "section_title": c.get("section_title"), "content_type": c.get("content_type"),
                      "manufacturer": c.get("manufacturer")} for c in pool],
        }
        print(f"  {qid}: pool={len(pools[qid]['pool'])} models={pools[qid]['target_models']}")
    json.dump(pools, open(F_POOLS, "w", encoding="utf-8"), ensure_ascii=False)
    from src.config import CHUNKS_TABLE
    man = {"at_config": {k: os.environ.get(k) for k in
           ("CHUNKS_TABLE", "ENUNCIADOS_MULTIVECTOR", "IDENTITY_RESOLVE",
            "IDENTITY_RESOLVE_POLICY", "DIVERSIFY_TIEBREAK", "HYDE_ENABLED")},
           "n_golds": len(pools), "table": CHUNKS_TABLE,
           "git": os.popen("git rev-parse --short HEAD").read().strip(),
           "retrieve_fn_sha": __import__("hashlib").sha256(
               inspect.getsource(R.retrieve_chunks).encode()).hexdigest()[:12]}
    json.dump(man, open(F_MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"freeze OK → {F_POOLS.name} ({len(pools)} dev golds) · manifest estampado")
    return 0


def run(method: str) -> int:
    from src.rag.generator import RELEVANCE_THRESHOLD
    from src.rag.reranker import rerank_chunks
    if not F_POOLS.exists():
        sys.exit("falta el freeze — corre 'freeze' primero")
    pools = json.load(open(F_POOLS, encoding="utf-8"))
    golds = {g["qid"]: g for g in yaml.safe_load(open(ROOT / "evals" / "gold_answers_v1.yaml",
             encoding="utf-8"))}
    needles = _needles()
    rel = METHODS[method]

    miss, served_facts, detail = [], [], []
    for qid, d in pools.items():
        pool = d["pool"]
        # rerank FIEL: con target_models (path productivo) + strict (no fail-open contamina)
        top5 = rerank_chunks(d["question"], pool, top_k=5,
                             target_models=d["target_models"] or None, strict=True,
                             relevance_instruction=rel)
        # filtro de relevancia del generador (prod, generator.py)
        served = {c.get("id") for c in top5 if (c.get("similarity") or 0) >= RELEVANCE_THRESHOLD}
        pool_ids = {c.get("id") for c in pool}
        for f in (golds[qid].get("atomic_facts") or []):
            if f.get("tipo") != "core":
                continue
            nd = needles.get((qid, f.get("valor")), set())
            if not nd or not (nd & pool_ids):
                continue  # solo facts con aguja EN el pool (aísla el rerank)
            if nd & served:
                served_facts.append((qid, f.get("valor")))
            else:
                miss.append((qid, f.get("valor")))
            detail.append({"qid": qid, "valor": str(f.get("valor"))[:24],
                           "served": bool(nd & served)})
    out = {"method": method, "relevance_instruction": rel,
           "rerank_miss": len(miss), "served": len(served_facts),
           "miss_facts": sorted(f"{q}·{v}" for q, v in miss),
           "served_facts": sorted(f"{q}·{v}" for q, v in served_facts)}
    json.dump(out, open(ROOT / "evals" / f"s98_rerank_{method}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"[{method}] RERANK-MISS = {len(miss)} · servidos = {len(served_facts)} "
          f"(facts-con-aguja-en-pool = {len(miss)+len(served_facts)})")
    print(f"  miss: {out['miss_facts']}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "freeze"
    if cmd == "freeze":
        raise SystemExit(freeze())
    else:
        raise SystemExit(run(cmd))
