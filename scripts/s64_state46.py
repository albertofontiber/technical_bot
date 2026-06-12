#!/usr/bin/env python3
"""s64_state46.py — Estado read-only de los docs implicados en TECH_DEBT #46.

Antes de diseñar el procedimiento (Protocolo 4: verificar el estado real PRIMERO):
  1. Filas en `documents` de los 6 docs implicados (3 viejos a superseder + sus
     sucesores): id, sha, status, supersedes_id/superseded_by_id, modelo, revisión.
  2. Chunks en `chunks_v2` por source_file: n, document_id (¿enlazado o NULL?),
     extraction_sha256 (para casar con el sha de los PDF en disco).
  3. Sanidad del esquema: distribución de `documents.status` + nº con supersedes
     poblado (esperado 0 — el contrato existe sin poblar, audit s62).
  4. SHA-256 de los PDF locales implicados (Manuales_Detnov / Manuales_ES).

Solo lecturas. Uso: python scripts/s64_state46.py
"""
from __future__ import annotations

import hashlib
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

URL = os.environ["SUPABASE_URL"]
H = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
     "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

# Patrones de los docs del #46 (substring sobre filename/source_file).
PATTERNS = ["MAD-472", "MC-380", "MS-416"]

# PDFs en disco implicados (viejos abril + lote Detnov jun).
LOCAL_PDFS = [
    ROOT / "Manuales_ES" / "Detección analógica" / "CAD-250-MS-416-es.pdf",
    ROOT / "Manuales_ES" / "Detección analógica" / "CAD-250-MC-380-es.pdf",
    ROOT / "Manuales_Detnov" / "CAD-250_Manual-software-configuracion-MS-416-es-2026-b.pdf",
    ROOT / "Manuales_Detnov" / "CAD-250_Manual-Configuracion-MC-380-es-2026-c.pdf",
]


def get(table: str, params: dict) -> list[dict]:
    r = httpx.get(f"{URL}/rest/v1/{table}", headers=H, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("=" * 76)
    print("1) documents — filas que matchean los patrones del #46")
    print("=" * 76)
    doc_rows: list[dict] = []
    for pat in PATTERNS:
        rows = get("documents", {
            "select": ("id,source_pdf_filename,source_pdf_sha256,status,"
                       "supersedes_id,superseded_by_id,product_model,"
                       "manufacturer,revision,revision_date"),
            "source_pdf_filename": f"ilike.*{pat}*",
        })
        doc_rows.extend(rows)
        print(f"\n  [{pat}] {len(rows)} fila(s) en documents:")
        for d in rows:
            print(f"    - {d['source_pdf_filename']}")
            print(f"        id={d['id']}  status={d['status']!r}  "
                  f"model={d['product_model']!r}  rev={d['revision']!r} "
                  f"({d['revision_date']!r})")
            print(f"        sha={d['source_pdf_sha256']}")
            print(f"        supersedes_id={d['supersedes_id']}  "
                  f"superseded_by_id={d['superseded_by_id']}")

    print()
    print("=" * 76)
    print("2) chunks_v2 — chunks por source_file que matchea los patrones")
    print("=" * 76)
    for pat in PATTERNS:
        rows = get("chunks_v2", {
            "select": "source_file,document_id,extraction_sha256",
            "source_file": f"ilike.*{pat}*",
            "limit": "5000",
        })
        agg: dict[tuple, int] = Counter()
        for c in rows:
            agg[(c["source_file"], c["document_id"], c["extraction_sha256"])] += 1
        print(f"\n  [{pat}] {len(rows)} chunks en {len(agg)} grupo(s):")
        for (src, doc_id, esha), n in sorted(agg.items()):
            print(f"    - {src}")
            print(f"        n={n}  document_id={doc_id}")
            print(f"        extraction_sha256={esha}")

    print()
    print("=" * 76)
    print("3) sanidad del esquema documents (status / supersedes)")
    print("=" * 76)
    all_docs = []
    offset = 0
    while True:
        page = get("documents", {
            "select": "id,status,supersedes_id,superseded_by_id",
            "limit": "1000", "offset": str(offset)})
        all_docs.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    st = Counter(d["status"] for d in all_docs)
    n_sup = sum(1 for d in all_docs
                if d["supersedes_id"] or d["superseded_by_id"])
    print(f"  documents totales: {len(all_docs)}")
    print(f"  status: {dict(st)}")
    print(f"  con supersedes_id/superseded_by_id poblado: {n_sup}")

    print()
    print("=" * 76)
    print("4) SHA-256 de los PDF locales")
    print("=" * 76)
    for p in LOCAL_PDFS:
        if p.exists():
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            print(f"  {p.name}\n      {sha}  ({p.stat().st_size:,} bytes)")
        else:
            print(f"  {p.name}  — NO EXISTE en disco")
    return 0


if __name__ == "__main__":
    sys.exit(main())
