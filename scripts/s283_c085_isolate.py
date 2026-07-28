#!/usr/bin/env python3
"""s283_c085_isolate.py — confirmar el muro diversify de cat022 AISLANDO 1 inyección.

Inyecta SOLO 1 enunciado (c94d2270 e2) forzado a sim alto y comprueba si el padre
sobrevive al diversify (etapas + pool_rank). Aísla el ruido multi-inyección MNDT722.
Compara con 15088SP/b162a7eb (control que SÍ sobrevivió a 0.95).
"""
from __future__ import annotations
import os, sys, uuid
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
    "RERANK_TOP_K": "10"})
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import httpx
import numpy as np
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL, RETRIEVAL_TOP_K
from src.reingest.embed import embed
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
STAGES = ["channels","post_merge","post_neighbor","post_superseded","post_model_filter",
          "post_diversify","post_lang","final"]

def resolve(src, pg, hint):
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H, params={
        "select": "id,context,content,product_model,manufacturer,source_file,page_number,"
                  "section_title,doc_type,content_type,chunk_index,document_id,language",
        "source_file": f"eq.{src}", "page_number": f"eq.{pg}", "parent_id": "is.null",
        "limit": "20"}, timeout=60)
    r.raise_for_status()
    return [x for x in r.json() if str(x["id"]).startswith(hint)][0]

_INJECT = None; _FORCE = None
_ORIG = httpx.Client.post
def _patched(self, url, *a, **k):
    resp = _ORIG(self, url, *a, **k)
    if "match_chunks_v2_enunciados" in str(url) and _INJECT is not None:
        payload = k.get("json") or {}
        qe = payload.get("query_embedding"); thr = payload.get("match_threshold", 0.3)
        try: base = resp.json()
        except Exception: base = []
        qv = np.asarray(qe, float); qn = qv/(np.linalg.norm(qv)+1e-12)
        cn = np.asarray(_INJECT["_emb"], float); cn = cn/(np.linalg.norm(cn)+1e-12)
        sim = _FORCE if _FORCE is not None else float(np.dot(qn, cn))
        if sim > thr:
            r2 = {kk: vv for kk, vv in _INJECT.items() if not kk.startswith("_")}
            r2["similarity"] = sim
            base = base + [r2]
        class _S:
            def raise_for_status(self_): return None
            def json(self_): return base
        return _S()
    return resp

def mkrow(p, content):
    e = embed([f"{p.get('context') or ''}\n\n{content}"], "document")[0]
    return {"id": str(uuid.uuid4()), "parent_id": p["id"], "content": content,
            "context": p.get("context"), "product_model": p.get("product_model"),
            "manufacturer": p.get("manufacturer"), "source_file": p.get("source_file"),
            "page_number": p.get("page_number"), "section_title": p.get("section_title"),
            "doc_type": p.get("doc_type"), "content_type": p.get("content_type"),
            "document_id": p.get("document_id"), "language": p.get("language"), "_emb": e}

def run(query, p, content, force):
    global _INJECT, _FORCE
    from src.rag.retriever import retrieve_chunks
    _INJECT = mkrow(p, content); _FORCE = force
    tr = {}
    pool = retrieve_chunks(query, top_k=RETRIEVAL_TOP_K, _trace=tr)
    tr["final"] = {c.get("id") for c in pool}
    where = [s for s in STAGES if p["id"] in tr.get(s, set())]
    rank = next((i for i, c in enumerate(pool) if c.get("id") == p["id"]), None)
    lbl = "cosine-real" if force is None else f"forzado={force}"
    print(f"  [{lbl:14}] padre {p['id'][:8]} ({p['source_file']} p{p['page_number']}): "
          f"etapas={where or 'NUNCA'} | pool_rank={rank}")

def main():
    httpx.Client.post = _patched
    QC = ("En los detectores de llama Spectrex SharpEye 40/40, ¿qué diferencia hay "
          "entre el modelo 40/40L y el 40/40L4, y qué significa el sufijo «B» (p. ej. 40/40LB)?")
    QH = ("¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y "
          "cuántos dispositivos por lazo?")
    c94 = resolve("MNDT722_40-40L", 11, "c94d2270")
    b16 = resolve("15088SP", 151, "b162a7eb")
    cont_c = ("La diferencia entre el detector Spectrex SharpEye 40/40L y el 40/40L4 está en la "
              "longitud de onda del sensor IR: 2,8 µm en el 40/40L frente a 4,5 µm en el 40/40L4.")
    cont_b = ("El sistema Notifier AFP1010 admite un máximo de cuatro LIBs, con un total de 792 "
              "dispositivos direccionables en todo el sistema; el AM2020 admite diez LIBs (1980).")
    print("### cat022 — c94d2270 (MNDT722_40-40L p11) AISLADO:")
    run(QC, c94, cont_c, None)
    run(QC, c94, cont_c, 0.95)
    run(QC, c94, cont_c, 0.99)
    print("### hp012 — b162a7eb (15088SP p151) AISLADO (control):")
    run(QH, b16, cont_b, None)
    run(QH, b16, cont_b, 0.95)
    httpx.Client.post = _ORIG
    return 0

if __name__ == "__main__":
    sys.exit(main())
