#!/usr/bin/env python3
"""s283_c085_trace.py — TRAZA cat022 (clase DEC-085 within-doc miss).

$0 (SELECT-only). Localiza el/los chunk(s) con las bandas IR (2,5-3,0 vs 4,5 μm)
del Spectrex 40/40 en chunks_v2 (source_file MNDT722_40-40L), verifica presencia
en el POOL de cat022 y su rank. Confirma/refuta misma-clase que hp012 (pool-absent).

Uso:  python scripts/s283_c085_trace.py
"""
from __future__ import annotations
import os, sys, re
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["HYDE_ENABLED"] = "false"
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(os.getcwd()).resolve()
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import httpx
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

CAT022_Q = ("En los detectores de llama Spectrex SharpEye 40/40, ¿qué diferencia hay "
            "entre el modelo 40/40L y el 40/40L4, y qué significa el sufijo «B» (p. ej. 40/40LB)?")

def rest_get(table, params):
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_H, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def main():
    print("=" * 90)
    print("PARTE A — ¿existe el chunk con las bandas IR (2,5-3,0 / 4,5 μm) en chunks_v2?")
    print("=" * 90)
    # 1) Todos los chunks reales (parent_id null) de MNDT722_40-40L
    rows = rest_get("chunks_v2", {
        "select": "id,source_file,page_number,chunk_index,product_model,manufacturer,"
                  "content_type,doc_type,section_title,language,content",
        "source_file": "eq.MNDT722_40-40L", "parent_id": "is.null",
        "duplicate_of": "is.null", "order": "page_number.asc,chunk_index.asc",
        "limit": "3000"})
    print(f"chunks reales (parent_id null) en MNDT722_40-40L: {len(rows)}")
    # 2) ¿cuáles mencionan 2,5 / 3,0 / 4,5 μm o la banda IR?
    band_re = re.compile(r"2[.,]5|3[.,]0|4[.,]5|longitud de onda|µm|μm|wavelength", re.I)
    l4_re = re.compile(r"4[.,]5\s*[µμ]?m|hidrocarburo", re.I)
    l_re = re.compile(r"2[.,]5.{0,6}3[.,]0|entre 2[.,]5", re.I)
    hits = []
    for c in rows:
        txt = c.get("content") or ""
        if band_re.search(txt):
            hits.append(c)
    print(f"chunks que mencionan banda/longitud de onda: {len(hits)}")
    band_ids = set()
    for c in hits:
        txt = c.get("content") or ""
        has_l = bool(l_re.search(txt)); has_l4 = bool(l4_re.search(txt))
        flag = ("  <<< L(2,5-3,0)" if has_l else "") + ("  <<< L4(4,5μm)" if has_l4 else "")
        if has_l or has_l4:
            band_ids.add(c["id"])
        print(f"  id={c['id'][:8]} p{c.get('page_number')} ci={c.get('chunk_index')} "
              f"ct={c.get('content_type')} pm={c.get('product_model')}{flag}")
        # dump snippet around the band
        m = re.search(r".{0,80}(2[.,]5|4[.,]5|longitud de onda).{0,160}", txt, re.I)
        if m:
            print(f"      «...{m.group(0).strip()[:230]}...»")
    print(f"\nchunk(s) con la banda IR discriminante = {sorted(band_ids)}")

    print("\n" + "=" * 90)
    print("PARTE B — POOL de cat022 (retrieve_chunks top_k=50, env paridad): ¿está el band-chunk? rank?")
    print("=" * 90)
    # env de paridad s283 (mismo que baseline v2)
    os.environ.update({
        "COVERAGE_RELEASE_PROFILE": "coverage_c1_v4", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "replace", "MUST_PRESERVE_CONTRACT": "on",
        "ENUNCIADOS_MULTIVECTOR": "on", "HYQ_TABLE": "on", "VISUAL_ASSETS_REGISTRY": "on",
        "RERANK_TOP_K": "10", "LLM_MAX_TOKENS": "3500",
        "GENERATOR_SELECTION_BLOCK": "on", "GENERATOR_PROMPT_VARIANT": "fidelity"})
    from src.rag.retriever import retrieve_chunks
    pool = retrieve_chunks(CAT022_Q, top_k=50)
    print(f"pool size = {len(pool)}")
    band_in_pool = []
    for rank, c in enumerate(pool):
        cid = c.get("id")
        tag = ""
        if cid in band_ids:
            tag = "  <<<< BAND-CHUNK (discriminante IR)"
            band_in_pool.append((rank, cid))
        if c.get("source_file") == "MNDT722_40-40L":
            print(f"  rank {rank:2} id={str(cid)[:8]} p{c.get('page_number')} "
                  f"ci={c.get('chunk_index')} sim={c.get('similarity'):.4f} "
                  f"ct={c.get('content_type')}{tag}")
    if not band_in_pool:
        print("\n>>> BAND-CHUNK AUSENTE del pool entero (0/50) — CONFIRMA clase DEC-085 (pool-absent within-doc)")
    else:
        print(f"\n>>> BAND-CHUNK presente en pool: {band_in_pool}")

    # top-10 global (para ver qué gana)
    print("\n--- top-10 global del pool (autoridad) ---")
    for rank, c in enumerate(pool[:10]):
        print(f"  {rank:2} id={str(c.get('id'))[:8]} {c.get('source_file'):28} "
              f"p{c.get('page_number')} sim={c.get('similarity'):.4f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
