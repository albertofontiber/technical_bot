#!/usr/bin/env python3
"""s283_c085_flipcheck.py — FLIP-CHECK in-process ($0 retrieval-only, SIN DB-WRITE).

Simula el INSERT de los enunciados candidatos a chunks_v2_enunciados SIN escribir en DB:
monkeypatch de httpx.Client.post → cuando el RPC es match_chunks_v2_enunciados, se APENDEN
las filas candidatas con similarity = 1 - cos_dist(cand_emb, query_embedding-del-payload)
(idéntico a lo que calcularía el RPC server-side). El resto del pipeline (colapso por
parent, _enunciados_swap, fusión sort-mixta [cuota OFF], model-filter, diversify, lang,
rerank strict K=10, coverage) corre INTACTO sobre el padre REAL hidratado desde DB.

Mide, por qid, BASELINE (sin inyección = prod) vs INYECTADO:
  - rank del padre-target en el POOL (retrieve_chunks top_k=50)
  - presencia/rank del padre en el SERVIDO (execute_rag_turn, rerank strict K=10 + coverage)

Uso:  python scripts/s283_c085_flipcheck.py
"""
from __future__ import annotations
import os, sys, json, uuid, copy
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["HYDE_ENABLED"] = "false"
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(os.getcwd()).resolve()
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
# env de PARIDAD s283 (== baseline v2) — set ANTES de importar retriever
os.environ.update({
    "COVERAGE_RELEASE_PROFILE": "coverage_c1_v4", "IDENTITY_RESOLVE": "on",
    "IDENTITY_RESOLVE_POLICY": "replace", "MUST_PRESERVE_CONTRACT": "on",
    "ENUNCIADOS_MULTIVECTOR": "on", "HYQ_TABLE": "on", "VISUAL_ASSETS_REGISTRY": "on",
    "RERANK_TOP_K": "10", "LLM_MAX_TOKENS": "3500",
    "GENERATOR_SELECTION_BLOCK": "on", "GENERATOR_PROMPT_VARIANT": "fidelity"})
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import httpx
import numpy as np
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL, RETRIEVAL_TOP_K, RERANK_TOP_K
from src.reingest.embed import embed
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

QUERIES = {
    "cat022": ("En los detectores de llama Spectrex SharpEye 40/40, ¿qué diferencia hay "
               "entre el modelo 40/40L y el 40/40L4, y qué significa el sufijo «B» (p. ej. 40/40LB)?"),
    "hp012": ("¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y "
              "cuántos dispositivos por lazo?"),
}
# padres-target (full ids) por prefijo
FULL = {
    "c94d2270": "c94d2270-f525-40f8-",  # resolver
}

def rest_get(table, params):
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_H, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

# hint(prefijo) -> (source_file, page_number) para resolución robusta (like sobre uuid = 404)
HINT_LOC = {
    "c94d2270": ("MNDT722_40-40L", 11),
    "a6eae6a1": ("MNDT722_40-40L", 49),
    "74cc9f95": ("MNDT722_40-40L", 8),
    "36ca37d0": ("MNDT722_40-40L", 12),
    "b162a7eb": ("15088SP", 151),
    "f03d3ae4": ("15088SP", 14),
}

def resolve_full_ids(hints):
    """resuelve prefijo → uuid completo + context/metadata del padre (por source_file+page)."""
    out = {}
    sel = ("id,context,content,product_model,manufacturer,source_file,page_number,"
           "section_title,doc_type,content_type,chunk_index,document_id,language,"
           "extraction_sha256")
    for h in hints:
        src, pg = HINT_LOC[h]
        rows = rest_get("chunks_v2", {
            "select": sel, "source_file": f"eq.{src}", "page_number": f"eq.{pg}",
            "parent_id": "is.null", "limit": "20"})
        match = [r for r in rows if str(r["id"]).startswith(h)]
        assert match, f"padre {h} no resuelto en {src} p{pg}"
        out[h] = match[0]
    return out

# ---- estado global del monkeypatch ----
_INJECT: list[dict] = []          # filas e_row candidatas a apendizar
_ORIG_POST = httpx.Client.post

def _patched_post(self, url, *args, **kwargs):
    resp = _ORIG_POST(self, url, *args, **kwargs)
    if "match_chunks_v2_enunciados" in str(url) and _INJECT:
        payload = kwargs.get("json") or {}
        qe = payload.get("query_embedding")
        thr = payload.get("match_threshold", 0.3)
        try:
            base = resp.json()
        except Exception:
            base = []
        qv = np.asarray(qe, dtype=np.float64)
        qn = qv / (np.linalg.norm(qv) + 1e-12)
        extra = []
        for row in _INJECT:
            cv = np.asarray(row["_emb"], dtype=np.float64)
            cn = cv / (np.linalg.norm(cv) + 1e-12)
            sim = float(np.dot(qn, cn))
            if sim <= thr:      # el RPC real no lo devolvería
                continue
            r2 = {k: v for k, v in row.items() if k != "_emb"}
            r2["similarity"] = sim
            extra.append(r2)
        merged = base + extra

        class _Shim:
            def raise_for_status(self_): return None
            def json(self_): return merged
        return _Shim()
    return resp

def build_inject_rows(cands, parents):
    """embed cada candidato (receta context+content) y arma la fila e_row surrogate."""
    rows = []
    texts, meta = [], []
    for c in cands:
        p = parents[c["parent_hint"]]
        ctx = p.get("context") or ""
        etext = f"{ctx}\n\n{c['content']}" if ctx else c["content"]
        texts.append(etext); meta.append((c, p))
    embs = embed(texts, "document")
    for (c, p), e in zip(meta, embs):
        rows.append({
            "id": str(uuid.uuid4()), "parent_id": p["id"], "content": c["content"],
            "context": p.get("context"), "product_model": p.get("product_model"),
            "manufacturer": p.get("manufacturer"), "source_file": p.get("source_file"),
            "page_number": p.get("page_number"), "section_title": p.get("section_title"),
            "doc_type": p.get("doc_type"), "content_type": p.get("content_type"),
            "document_id": p.get("document_id"), "language": p.get("language"),
            "_emb": e, "_name": c["name"],
        })
    return rows

def _rank_of(pid, chunks):
    for i, c in enumerate(chunks):
        if c.get("id") == pid:
            return i
    return None

def measure(qid, query, target_pids):
    from src.rag.retriever import retrieve_chunks
    from src.rag.reranker import rerank
    from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn
    from src.rag.structural_neighbor_shadow import observe_structural_neighbor_shadow

    def _stub_gen(q, served, **kw):
        return {"answer": "<stub-no-llm>"}

    def _strict_rerank(q, chunks, **kw):
        return rerank(q, chunks, strict=True, **kw)

    adapters = RagServingAdapters(
        retrieve=retrieve_chunks, rerank=_strict_rerank,
        observe_structural_shadow=observe_structural_neighbor_shadow, generate=_stub_gen)

    pool = retrieve_chunks(query, top_k=RETRIEVAL_TOP_K)
    pipe = execute_rag_turn(query=query, query_for_retrieval=query, target_models=None,
                            available_models=None, retrieval_top_k=RETRIEVAL_TOP_K,
                            rerank_top_k=RERANK_TOP_K, adapters=adapters)
    served = pipe["chunks"]
    res = {"pool_size": len(pool), "served_size": len(served),
           "coverage_status": pipe["coverage_trace"].get("status")}
    for name, pid in target_pids.items():
        res[f"pool_rank[{name}]"] = _rank_of(pid, pool)
        res[f"served_rank[{name}]"] = _rank_of(pid, served)
    res["served_ids"] = [(str(c.get("id"))[:8], c.get("source_file"), c.get("page_number"))
                         for c in served]
    return res

def main():
    global _INJECT
    cfg = json.load(open(ROOT / "evals" / "s283_c085_candidates.json", encoding="utf-8"))
    hints = sorted({c["parent_hint"] for c in cfg["candidates"]})
    parents = resolve_full_ids(hints)
    print("Padres resueltos:")
    for h, p in parents.items():
        print(f"  {h} -> {p['id']} | {p['source_file']} p{p['page_number']} ci={p['chunk_index']} pm={p['product_model']}")

    httpx.Client.post = _patched_post   # activar patch (inerte con _INJECT vacío)

    report = {}
    for qid, query in QUERIES.items():
        cands = [c for c in cfg["candidates"] if c["qid"] == qid]
        # padres-target por nombre corto
        tp = {}
        for c in cands:
            tp.setdefault(c["parent_hint"], parents[c["parent_hint"]]["id"])
        target_pids = {h: pid for h, pid in tp.items()}

        print("\n" + "=" * 90)
        print(f"QID {qid} — query: {query}")
        print("=" * 90)

        _INJECT = []
        base = measure(qid, query, target_pids)
        print("\n[BASELINE — sin inyección (= prod)]")
        for k, v in base.items():
            if k != "served_ids":
                print(f"  {k} = {v}")

        rows = build_inject_rows(cands, parents)
        print(f"\n[candidatos embebidos: {len(rows)}]")
        _INJECT = rows
        inj = measure(qid, query, target_pids)
        print("\n[INYECTADO — enunciados candidatos activos]")
        for k, v in inj.items():
            if k != "served_ids":
                print(f"  {k} = {v}")
        print("\n  servido top-10 (inyectado):")
        for i, (cid, src, pg) in enumerate(inj["served_ids"]):
            flag = ""
            for h, pid in target_pids.items():
                if str(pid).startswith(cid):
                    flag = f"  <<<< TARGET {h}"
            print(f"    {i:2} {cid} {str(src)[:34]:36} p{pg}{flag}")

        # veredicto flip
        flips = {}
        for h in target_pids:
            b = base.get(f"served_rank[{h}]"); a = inj.get(f"served_rank[{h}]")
            flips[h] = {"served_baseline": b, "served_injected": a,
                        "pool_baseline": base.get(f"pool_rank[{h}]"),
                        "pool_injected": inj.get(f"pool_rank[{h}]"),
                        "FLIP_to_served": (b is None and a is not None)}
        report[qid] = {"baseline": base, "injected": inj, "flips": flips}
        print("\n  VEREDICTO FLIP:")
        for h, f in flips.items():
            print(f"    {h}: served {f['served_baseline']} -> {f['served_injected']} | "
                  f"pool {f['pool_baseline']} -> {f['pool_injected']} | "
                  f"FLIP={'SÍ' if f['FLIP_to_served'] else 'no'}")

    httpx.Client.post = _ORIG_POST
    out = ROOT / "evals" / "s283_c085_flipcheck_result.json"
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n-> {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
