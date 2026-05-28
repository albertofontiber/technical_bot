#!/usr/bin/env python3
"""Diagnóstico READ-ONLY del bucket sin fabricante en CHUNKS_TABLE (#6).

Antes de tocar datos, responde:
  A. Distribución real de manufacturer/distributor (¿el "unknown" es NULL?).
  B. Sizing del bucket sin marca; split A (modelo real) vs B (product_model junk).
  C. Raíz vs parche: ¿documents.manufacturer / .product_model RESCATA sin Haiku?
     (fix barato vía join) + concentración por documento.
  D. Señal: context (blurb B7) + portada/legal de una muestra de docs del bucket.

Uso (PowerShell):
    $env:CHUNKS_TABLE='chunks_v2'; python scripts/diagnose_unknown_bucket.py
"""
from __future__ import annotations

import io
import os
import re
import sys
from collections import Counter, defaultdict

import httpx
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
TABLE = os.environ.get("CHUNKS_TABLE", "chunks")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
PAGE = 1000

_MONTHS = {"ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO",
           "SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE","JANUARY","FEBRUARY",
           "MARCH","APRIL","MAY","JUNE","JULY","AUGUST","SEPTEMBER","OCTOBER",
           "NOVEMBER","DECEMBER","ENE","FEB","ABR","JUN","JUL","AGO","SEP","OCT","NOV","DIC"}


def is_junk(pm: str | None) -> bool:
    if not pm or pm.lower() == "unknown":
        return True
    first = re.split(r"[- /]", pm.upper(), maxsplit=1)[0]
    if first in _MONTHS:
        return True
    if re.match(r"^EN[- ]?\d", pm.upper()):
        return True
    if " " in pm.strip() and not any(c.isdigit() for c in pm):
        return True
    return False


def no_mfr(v) -> bool:
    return v is None or str(v).strip() == "" or str(v).strip().lower() == "unknown"


def get(table: str, params: dict) -> list[dict]:
    r = httpx.get(f"{URL}/rest/v1/{table}", headers=H, params=params, timeout=30.0)
    r.raise_for_status()
    return r.json()


def fetch_all_chunks() -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        batch = get(TABLE, {
            "select": "product_model,manufacturer,distributor,source_file,page_number,document_id",
            "order": "id", "limit": str(PAGE), "offset": str(offset),
        })
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return rows


def main() -> None:
    print(f"== Diagnóstico bucket sin-marca · tabla='{TABLE}' ==\n")
    rows = fetch_all_chunks()
    total = len(rows)

    # A. Distribución manufacturer / distributor
    mfr_dist = Counter(("NULL" if r.get("manufacturer") is None else (str(r.get("manufacturer")).strip() or "EMPTY")) for r in rows)
    dist_dist = Counter(("NULL" if r.get("distributor") is None else (str(r.get("distributor")).strip() or "EMPTY")) for r in rows)
    print("== A. DISTRIBUCIÓN (chunks) ==")
    print(f"  total chunks: {total}")
    print(f"  manufacturer: {dict(mfr_dist.most_common(15))}")
    print(f"  distributor : {dict(dist_dist.most_common(15))}")
    print()

    # B. Bucket sin marca
    bucket = [r for r in rows if no_mfr(r.get("manufacturer"))]
    by_src: dict[str, list[dict]] = defaultdict(list)
    models: Counter[str] = Counter()
    for r in bucket:
        by_src[r.get("source_file") or "NOSRC"].append(r)
        models[r.get("product_model") or "NULL"] += 1
    a_models = [m for m in models if not is_junk(m)]
    b_models = [m for m in models if is_junk(m)]
    print("== B. SIZING bucket sin marca ==")
    print(f"  chunks sin marca .......... {len(bucket)} ({len(bucket)/total:.1%})")
    print(f"  documentos (source_file) .. {len(by_src)}")
    print(f"  product_model distintos ... {len(models)}")
    print(f"  A (modelo real) ........... {len(a_models)} modelos / {sum(models[m] for m in a_models)} chunks")
    print(f"  B (product_model junk) .... {len(b_models)} modelos / {sum(models[m] for m in b_models)} chunks")
    print()

    if not bucket:
        print("Bucket vacío — nada que diagnosticar.")
        return

    # C. documents rescata? (join barato)
    doc_ids = sorted({r.get("document_id") for r in bucket if r.get("document_id")})
    print(f"== C. ¿documents RESCATA sin Haiku? ({len(doc_ids)} document_ids del bucket) ==")
    docs: dict[str, dict] = {}
    for i in range(0, len(doc_ids), 150):
        chunk_ids = doc_ids[i:i+150]
        id_list = ",".join(f'"{d}"' for d in chunk_ids)
        try:
            for d in get("documents", {"id": f"in.({id_list})", "select": "id,manufacturer,product_model,distributor", "limit": "150"}):
                docs[d["id"]] = d
        except Exception as e:
            print(f"  (error documents batch: {e})")
            break
    doc_mfr = Counter(("NULL" if (docs.get(d, {}).get("manufacturer") is None) else (str(docs[d].get("manufacturer")).strip() or "EMPTY")) for d in doc_ids)
    doc_has_mfr = sum(1 for d in doc_ids if not no_mfr(docs.get(d, {}).get("manufacturer")))
    print(f"  documents con manufacturer útil: {doc_has_mfr}/{len(doc_ids)} docs")
    print(f"  documents.manufacturer dist: {dict(doc_mfr.most_common(12))}")
    print()

    # C2. Concentración
    src_sizes = sorted(((len(v), s) for s, v in by_src.items()), reverse=True)
    print("== C2. Concentración / top docs del bucket ==")
    for cnt, s in src_sizes[:12]:
        pms = sorted({r.get('product_model') or 'NULL' for r in by_src[s]})
        did = next((r.get("document_id") for r in by_src[s]), None)
        dmfr = docs.get(did, {}).get("manufacturer") if did else None
        print(f"    {cnt:>4}  {s:<30} doc.mfr={dmfr!r:14} models={pms[:3]}")
    print()

    # D. Señal: context (blurb) + portada/legal
    print("== D. SEÑAL de marca (context/blurb + portada + legal) ==")
    sample = [s for _, s in src_sizes[:3]] + [s for s in by_src if any(is_junk(r.get('product_model')) for r in by_src[s])][:2]
    for s in dict.fromkeys(sample):
        try:
            first = get(TABLE, {"source_file": f"eq.{s}", "select": "content,context,page_number", "order": "page_number.asc", "limit": "1"})
            last = get(TABLE, {"source_file": f"eq.{s}", "select": "content,page_number", "order": "page_number.desc", "limit": "1"})
        except Exception as e:
            print(f"  {s}: error ({e})"); continue
        print(f"  --- {s} ---")
        if first:
            ctx = (first[0].get("context") or "").replace("\n", " ")
            con = (first[0].get("content") or "").replace("\n", " ")
            print(f"    blurb(context): {ctx[:200]}")
            print(f"    PORTADA p{first[0].get('page_number')}: {con[:200]}")
        if last:
            con = (last[0].get("content") or "").replace("\n", " ")
            print(f"    LEGAL   p{last[0].get('page_number')}: {con[:200]}")
        print()


if __name__ == "__main__":
    main()
