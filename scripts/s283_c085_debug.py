#!/usr/bin/env python3
"""s283_c085_debug.py — RAÍZ del FLIP=no: cosine del enunciado + traza por-etapa.

$0-retrieval. Reusa el monkeypatch de inyección; añade: (1) captura del query_embedding
del payload → cosine candidato↔query impreso; (2) retrieve_chunks(_trace=...) para ver en
QUÉ etapa entra/muere el padre (channels/post_merge/post_neighbor/post_superseded/
post_model_filter/post_diversify/post_lang/final); (3) el suelo de coseno del pool vectorial.
"""
from __future__ import annotations
import os, sys, json, uuid
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["HYDE_ENABLED"] = "false"
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(os.getcwd()).resolve()
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ.update({
    "COVERAGE_RELEASE_PROFILE": "coverage_c1_v4", "IDENTITY_RESOLVE": "on",
    "IDENTITY_RESOLVE_POLICY": "replace", "MUST_PRESERVE_CONTRACT": "on",
    "ENUNCIADOS_MULTIVECTOR": "on", "HYQ_TABLE": "on", "VISUAL_ASSETS_REGISTRY": "on",
    "RERANK_TOP_K": "10", "LLM_MAX_TOKENS": "3500",
    "GENERATOR_SELECTION_BLOCK": "on", "GENERATOR_PROMPT_VARIANT": "fidelity"})
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import httpx
import numpy as np
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL, RETRIEVAL_TOP_K
from src.reingest.embed import embed
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

QUERIES = {
    "cat022": ("En los detectores de llama Spectrex SharpEye 40/40, ¿qué diferencia hay "
               "entre el modelo 40/40L y el 40/40L4, y qué significa el sufijo «B» (p. ej. 40/40LB)?"),
    "hp012": ("¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y "
              "cuántos dispositivos por lazo?"),
}
HINT_LOC = {"c94d2270": ("MNDT722_40-40L", 11), "a6eae6a1": ("MNDT722_40-40L", 49),
            "74cc9f95": ("MNDT722_40-40L", 8), "b162a7eb": ("15088SP", 151),
            "f03d3ae4": ("15088SP", 14)}

def rest_get(table, params):
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_H, params=params, timeout=60)
    r.raise_for_status(); return r.json()

def resolve(hint):
    src, pg = HINT_LOC[hint]
    rows = rest_get("chunks_v2", {"select": "id,context,content,product_model,manufacturer,"
        "source_file,page_number,section_title,doc_type,content_type,chunk_index,document_id,language",
        "source_file": f"eq.{src}", "page_number": f"eq.{pg}", "parent_id": "is.null", "limit": "20"})
    return [r for r in rows if str(r["id"]).startswith(hint)][0]

_INJECT = []
_QEMB = {"v": None}
_FORCE_SIM = {"v": None}   # None = cosine real; float = fuerza la similarity del enunciado
_ORIG = httpx.Client.post
def _patched(self, url, *a, **k):
    resp = _ORIG(self, url, *a, **k)
    if "match_chunks_v2_enunciados" in str(url) and _INJECT:
        payload = k.get("json") or {}
        qe = payload.get("query_embedding"); thr = payload.get("match_threshold", 0.3)
        _QEMB["v"] = qe
        try: base = resp.json()
        except Exception: base = []
        qv = np.asarray(qe, float); qn = qv/(np.linalg.norm(qv)+1e-12)
        extra = []
        for row in _INJECT:
            cn = np.asarray(row["_emb"], float); cn = cn/(np.linalg.norm(cn)+1e-12)
            sim = float(np.dot(qn, cn))
            row["_sim"] = sim
            if _FORCE_SIM["v"] is not None:
                sim = _FORCE_SIM["v"]
            if sim <= thr: continue
            r2 = {kk: vv for kk, vv in row.items() if not kk.startswith("_")}
            r2["similarity"] = sim; extra.append(r2)
        merged = base + extra
        class _S:
            def raise_for_status(self_): return None
            def json(self_): return merged
        return _S()
    return resp

def build(cands, parents):
    texts, meta = [], []
    for c in cands:
        p = parents[c["parent_hint"]]; ctx = p.get("context") or ""
        texts.append(f"{ctx}\n\n{c['content']}" if ctx else c["content"]); meta.append((c, p))
    embs = embed(texts, "document")
    rows = []
    for (c, p), e in zip(meta, embs):
        rows.append({"id": str(uuid.uuid4()), "parent_id": p["id"], "content": c["content"],
            "context": p.get("context"), "product_model": p.get("product_model"),
            "manufacturer": p.get("manufacturer"), "source_file": p.get("source_file"),
            "page_number": p.get("page_number"), "section_title": p.get("section_title"),
            "doc_type": p.get("doc_type"), "content_type": p.get("content_type"),
            "document_id": p.get("document_id"), "language": p.get("language"),
            "_emb": e, "_name": c["name"]})
    return rows

def _rank_in(pid, pool):
    for i, c in enumerate(pool):
        if c.get("id") == pid:
            return i
    return None

def main():
    global _INJECT
    cfg = json.load(open(ROOT/"evals"/"s283_c085_candidates.json", encoding="utf-8"))
    hints = sorted({c["parent_hint"] for c in cfg["candidates"]})
    parents = {h: resolve(h) for h in hints}
    httpx.Client.post = _patched
    from src.rag.retriever import retrieve_chunks
    STAGES = ["channels","post_merge","post_neighbor","post_superseded","post_model_filter",
              "post_diversify","post_lang","final"]
    for qid, query in QUERIES.items():
        cands = [c for c in cfg["candidates"] if c["qid"] == qid]
        rows = build(cands, parents)
        tgt = {c["parent_hint"]: parents[c["parent_hint"]]["id"] for c in cands}
        print("\n" + "="*90); print(f"QID {qid}"); print("="*90)
        _INJECT = rows
        for label, force in [("cosine-REAL", None), ("FORZADO sim=0.95", 0.95)]:
            _FORCE_SIM["v"] = force
            tr = {}
            pool = retrieve_chunks(query, top_k=RETRIEVAL_TOP_K, _trace=tr)
            tr["final"] = {c.get("id") for c in pool}
            if force is None:
                print("cosine candidato↔query (input_type document vs query):")
                for r in rows:
                    print(f"  {r['_name']:34} sim={r.get('_sim'):.4f}  -> parent {r['parent_id'][:8]}")
                sims = sorted([c.get("similarity") or 0 for c in pool])
                print(f"pool_size={len(pool)}  similarity: min={sims[0]:.3f} "
                      f"p25={sims[len(sims)//4]:.3f} med={sims[len(sims)//2]:.3f} max={sims[-1]:.3f}")
            print(f"  [{label}]")
            for h, pid in tgt.items():
                where = [s for s in STAGES if pid in tr.get(s, set())]
                fr = _rank_in(pid, pool)
                print(f"    padre {h} ({parents[h]['source_file']} p{parents[h]['page_number']}): "
                      f"etapas={where or 'NUNCA'} | pool_rank={fr}")
        _FORCE_SIM["v"] = None
    httpx.Client.post = _ORIG
    return 0

if __name__ == "__main__":
    sys.exit(main())
