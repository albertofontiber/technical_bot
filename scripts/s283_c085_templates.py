#!/usr/bin/env python3
"""s283_c085_templates.py — plantillas de chunks_v2_enunciados + verificación hp012 + contexto padres.

$0 SELECT-only. (1) SELECT filas reales de la tabla enunciados como plantilla de formato.
(2) hp012: contenido de b162a7eb (p151) + confirmar ausencia del pool. (3) contexto (blurb-B7)
y metadata de los padres candidatos (cat022: 74cc9f95/c94d2270/36ca37d0; hp012: b162a7eb).
(4) ¿ya existen enunciados para esos padres?
"""
from __future__ import annotations
import os, sys, json
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(os.getcwd()).resolve()
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
import httpx
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

def rest_get(table, params):
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_H, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def rest_post_rpc(fn, payload):
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/rpc/{fn}", headers={**_H, "Content-Type": "application/json"},
                   json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

CAND_PARENTS = {
    "cat022_p8_L":  "74cc9f95-6bbf-43cc-84bd-3cae03c48371",
    "cat022_p11_table_L4BIT": "c94d2270-f525-400d-af18-eb7c400aa4a1",
    "cat022_p12_L":  "36ca37d0-280f-497f-90da-c6f34fc8e81a",
    "cat022_p49_spec": "a6eae6a1-8be9-46db-bd16-c3e6891357d0",
    "hp012_p151_total": "b162a7eb",  # prefijo — resolvemos abajo
}

def main():
    print("=" * 90)
    print("PARTE 1 — PLANTILLA: filas reales de la tabla chunks_v2_enunciados")
    print("=" * 90)
    tmpl = rest_get("chunks_v2_enunciados", {
        "select": "id,content,context,parent_id,ingest_batch,extraction_sha256,product_model,"
                  "manufacturer,source_file,page_number,section_title,doc_type,content_type,"
                  "chunk_index,language",
        "order": "ingest_batch.desc", "limit": "8"})
    print(f"filas de chunks_v2_enunciados (muestra {len(tmpl)}):")
    for r in tmpl:
        print(json.dumps({k: (str(v)[:110] if isinstance(v, str) else v) for k, v in r.items()},
                         ensure_ascii=False, indent=1))
        print("-" * 40)
    cnt = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2_enunciados",
                    headers={**_H, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
                    params={"select": "id"}, timeout=60)
    print("total filas chunks_v2_enunciados:", cnt.headers.get("content-range"))

    print("\n" + "=" * 90)
    print("PARTE 2 — hp012: chunk 15088SP p151 (b162a7eb) contenido + p14")
    print("=" * 90)
    hp = rest_get("chunks_v2", {
        "select": "id,source_file,page_number,chunk_index,product_model,manufacturer,content_type,"
                  "context,content",
        "source_file": "eq.15088SP", "page_number": "in.(151,14)", "parent_id": "is.null",
        "order": "page_number.asc,chunk_index.asc", "limit": "10"})
    for r in hp:
        print(f"id={r['id']} src={r['source_file']} p{r['page_number']} ci={r['chunk_index']} "
              f"pm={r['product_model']} ct={r['content_type']}")
        print("  context:", (r.get("context") or "")[:300])
        print("  content:", (r.get("content") or "")[:600])

    print("\n" + "=" * 90)
    print("PARTE 3 — contexto (blurb-B7) + metadata de padres candidatos cat022")
    print("=" * 90)
    ids = [v for k, v in CAND_PARENTS.items() if k.startswith("cat022")]
    q = ",".join(f'"{x}"' for x in ids)
    parents = rest_get("chunks_v2", {
        "select": "id,source_file,page_number,chunk_index,product_model,manufacturer,content_type,"
                  "doc_type,section_title,language,document_id,extraction_sha256,context,content",
        "id": f"in.({q})"})
    pmap = {p["id"]: p for p in parents}
    for name, pid in CAND_PARENTS.items():
        if not name.startswith("cat022"):
            continue
        p = pmap.get(pid)
        if not p:
            print(f"{name}: NO ENCONTRADO ({pid})"); continue
        print(f"\n### {name}  id={p['id'][:8]} p{p['page_number']} ci={p['chunk_index']} "
              f"ct={p['content_type']} pm={p['product_model']} lang={p['language']}")
        print(f"  section_title: {p.get('section_title')}")
        print(f"  extraction_sha256: {p.get('extraction_sha256')}")
        print(f"  context (blurb-B7): {(p.get('context') or '')[:400]}")
        print(f"  content[:400]: {(p.get('content') or '')[:400]}")

    print("\n" + "=" * 90)
    print("PARTE 4 — ¿ya existen enunciados (parent_id) para estos padres?")
    print("=" * 90)
    allpids = ["74cc9f95-6bbf-43cc-84bd-3cae03c48371", "c94d2270-f525-400d-af18-eb7c400aa4a1",
               "36ca37d0-280f-497f-90da-c6f34fc8e81a", "a6eae6a1-8be9-46db-bd16-c3e6891357d0"]
    # hp012 full ids (p151/p14 de 15088SP):
    for r in hp:
        allpids.append(r["id"])
    q2 = ",".join(f'"{x}"' for x in allpids)
    existing = rest_get("chunks_v2", {
        "select": "id,parent_id,content,ingest_batch", "parent_id": f"in.({q2})", "limit": "50"})
    print(f"enunciados existentes apuntando a los padres candidatos: {len(existing)}")
    for e in existing:
        print(f"  enun {e['id'][:8]} -> parent {e['parent_id'][:8]} [{e.get('ingest_batch')}]: "
              f"{(e.get('content') or '')[:120]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
