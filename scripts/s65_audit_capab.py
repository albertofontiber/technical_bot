#!/usr/bin/env python3
"""s65_audit_capab.py — Audit dirigido de la CAPA B de TECH_DEBT #43 (read-only).

Protocolo 4 (gate/audit primero): el audit s62 inventarió la capa B como hallazgo
COLATERAL del análisis de near-dups; antes de diseñar el ciclo de higiene, este
script cuantifica cada bucket con números exactos y frescos (post-s64):

  B1. manufacturer mal asignado (terceros bajo Detnov; cualquier otro cruce).
  B2. product_model='unknown' — en documents Y en chunks_v2 (el filtro de
      retrieval opera sobre chunks).
  B3. revision con basura de parser ("Rev isar/ise/io/iamente/iaturas").
  B4. revision_date / language NULL en documents.
  B5. document_family poblada pero = filename (inservible como familia).
  B6. documents sin chunks en chunks_v2 (¿tienen chunks solo en la tabla vieja?).
  B7. chunks_v2 sin document_id (lotes s55/s58 sin fila en documents) — por
      manufacturer y source_file; ¿existe fila en documents por filename?

Solo lecturas. Artefacto: evals/s65_audit_capab.yaml
Uso: python scripts/s65_audit_capab.py
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

URL = os.environ["SUPABASE_URL"]
H = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
     "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

OUT = ROOT / "evals" / "s65_audit_capab.yaml"

# Marcas de terceros detectadas en el audit s62 bajo manufacturer=Detnov
# (PA5/PA20/DS10 = Pfannenberg; SharpEye/Spectrex; SGMCB/Sensitron). Substrings
# sobre filename lowercased — el audit LISTA candidatos, la curación decide.
THIRD_PARTY_KEYWORDS = {
    "pfannenberg": ["pfannenberg", "pa 5", "pa5", "pa 20", "pa20", "ds 10", "ds10"],
    "spectrex": ["spectrex", "sharpeye", "sharp eye", "20/20"],
    "sensitron": ["sensitron", "sgmcb", "smart3", "smart 3", "py x", "pyx"],
}

REV_GARBAGE = re.compile(r"^rev\s?i", re.IGNORECASE)  # Rev isar/ise/io/iamente/...


def get_paged(table: str, select: str, extra: dict | None = None,
              page: int = 1000) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        params = {"select": select, "limit": str(page), "offset": str(offset)}
        if extra:
            params.update(extra)
        r = httpx.get(f"{URL}/rest/v1/{table}", headers=H, params=params,
                      timeout=120)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page:
            return rows
        offset += page


def count_exact(table: str, filters: dict) -> int:
    params = {"select": "id", "limit": "1"}
    params.update(filters)
    r = httpx.get(f"{URL}/rest/v1/{table}",
                  headers={**H, "Prefer": "count=exact", "Range-Unit": "items",
                           "Range": "0-0"},
                  params=params, timeout=60)
    r.raise_for_status()
    cr = r.headers.get("content-range", "")
    return int(cr.split("/")[-1]) if "/" in cr else -1


def norm_fname(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    if s.endswith(".pdf"):
        s = s[:-4]
    return s


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    report: dict = {"audit": "s65_capaB", "read_only": True}

    # ------------------------------------------------------------------ docs
    print("[1/4] documents (dump completo paginado)...")
    docs = get_paged(
        "documents",
        "id,source_pdf_filename,source_pdf_sha256,manufacturer,product_model,"
        "revision,revision_date,language,document_family,doc_type,status,"
        "ingested_at")
    print(f"      {len(docs)} filas")
    report["documents_total"] = len(docs)
    report["documents_status"] = dict(Counter(d["status"] for d in docs))
    report["documents_by_manufacturer"] = dict(
        Counter(d["manufacturer"] or "NULL" for d in docs).most_common())

    # B1 — terceros bajo manufacturer equivocado (candidatos por keyword)
    b1: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        fn = (d["source_pdf_filename"] or "").lower()
        for brand, kws in THIRD_PARTY_KEYWORDS.items():
            if any(k in fn for k in kws) and (d["manufacturer"] or "").lower() != brand:
                b1[brand].append({
                    "id": d["id"], "filename": d["source_pdf_filename"],
                    "manufacturer": d["manufacturer"],
                    "product_model": d["product_model"], "status": d["status"],
                    "matched": [k for k in kws if k in fn]})
                break
    report["B1_third_party_candidates"] = {
        b: rows for b, rows in sorted(b1.items())}
    report["B1_total"] = sum(len(v) for v in b1.values())

    # B2 — product_model unknown/NULL en documents
    unk_docs = [d for d in docs
                if (d["product_model"] or "").lower() in ("unknown", "")]
    report["B2_documents_model_unknown_total"] = len(unk_docs)
    report["B2_documents_model_unknown_by_manufacturer"] = dict(
        Counter(d["manufacturer"] or "NULL" for d in unk_docs).most_common())

    # B3 — revision basura
    rev_counter = Counter((d["revision"] or "NULL") for d in docs)
    garbage = {v: n for v, n in rev_counter.items()
               if v != "NULL" and REV_GARBAGE.match(v)}
    report["B3_revision_values_total_distinct"] = len(rev_counter)
    report["B3_revision_garbage"] = dict(sorted(garbage.items()))
    report["B3_revision_garbage_total"] = sum(garbage.values())
    report["B3_revision_top20"] = dict(rev_counter.most_common(20))

    # B4 — revision_date / language
    report["B4_revision_date_null"] = sum(
        1 for d in docs if not d["revision_date"])
    report["B4_language_null"] = sum(1 for d in docs if not d["language"])
    report["B4_language_dist"] = dict(
        Counter(d["language"] or "NULL" for d in docs).most_common())

    # B5 — document_family
    fams = Counter(d["document_family"] for d in docs if d["document_family"])
    multi = {f: n for f, n in fams.items() if n >= 2}
    report["B5_family_populated"] = sum(fams.values())
    report["B5_family_distinct"] = len(fams)
    report["B5_families_with_2plus_docs"] = len(multi)
    report["B5_examples_multi"] = dict(Counter(multi).most_common(10))

    # ---------------------------------------------------------------- chunks
    print("[2/4] chunks_v2 (dump agregado paginado)...")
    chunks = get_paged(
        "chunks_v2", "id,source_file,document_id,manufacturer,product_model")
    print(f"      {len(chunks)} filas")
    report["chunks_v2_total"] = len(chunks)
    report["chunks_by_manufacturer"] = dict(
        Counter(c["manufacturer"] or "NULL" for c in chunks).most_common())

    # B2 en chunks (donde muerde el filtro de retrieval)
    unk_chunks = [c for c in chunks
                  if (c["product_model"] or "").lower() in ("unknown", "")]
    report["B2_chunks_model_unknown_total"] = len(unk_chunks)
    report["B2_chunks_model_unknown_by_manufacturer"] = dict(
        Counter(c["manufacturer"] or "NULL" for c in unk_chunks).most_common())
    report["B2_chunks_model_unknown_sources"] = len(
        {c["source_file"] for c in unk_chunks})

    # B7 — chunks sin document_id
    orphan = [c for c in chunks if not c["document_id"]]
    report["B7_chunks_no_document_id_total"] = len(orphan)
    report["B7_by_manufacturer"] = dict(
        Counter(c["manufacturer"] or "NULL" for c in orphan).most_common())
    orphan_sources = sorted({c["source_file"] for c in orphan})
    report["B7_distinct_source_files"] = len(orphan_sources)

    # ¿esos source_files tienen fila en documents por filename (norm)?
    doc_by_fname = {norm_fname(d["source_pdf_filename"]): d for d in docs}
    linked_possible, no_row = [], []
    for src in orphan_sources:
        if norm_fname(src) in doc_by_fname:
            linked_possible.append(src)
        else:
            no_row.append(src)
    report["B7_sources_with_documents_row_by_filename"] = len(linked_possible)
    report["B7_sources_without_documents_row"] = len(no_row)
    report["B7_sources_sample"] = no_row[:25]
    n_chunks_by_src = Counter(c["source_file"] for c in orphan)
    report["B7_top_sources_by_chunks"] = dict(n_chunks_by_src.most_common(15))

    # ------------------------------------------------------------- cruce B6
    print("[3/4] documents sin chunks en chunks_v2...")
    linked_ids = {c["document_id"] for c in chunks if c["document_id"]}
    no_chunks = [d for d in docs if d["id"] not in linked_ids]
    report["B6_documents_without_chunks_v2"] = len(no_chunks)
    report["B6_by_manufacturer"] = dict(
        Counter(d["manufacturer"] or "NULL" for d in no_chunks).most_common())
    report["B6_by_status"] = dict(
        Counter(d["status"] for d in no_chunks).most_common())

    print(f"[4/4] cross-check de {len(no_chunks)} docs contra tabla vieja "
          f"'chunks' (count exacto por doc)...")
    in_old, nowhere = [], []
    for i, d in enumerate(no_chunks):
        n = count_exact("chunks", {"document_id": f"eq.{d['id']}"})
        rec = {"id": d["id"], "filename": d["source_pdf_filename"],
               "manufacturer": d["manufacturer"], "status": d["status"],
               "chunks_in_old_table": n}
        (in_old if n > 0 else nowhere).append(rec)
        if (i + 1) % 25 == 0:
            print(f"      {i + 1}/{len(no_chunks)}")
    report["B6_with_chunks_in_old_table"] = len(in_old)
    report["B6_with_no_chunks_anywhere"] = len(nowhere)
    report["B6_nowhere_sample"] = nowhere[:25]
    report["B6_in_old_sample"] = in_old[:25]

    OUT.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False,
                                  width=100), encoding="utf-8")

    # ------------------------------------------------------------- resumen
    print("\n" + "=" * 72)
    print("RESUMEN CAPA B (detalle completo en evals/s65_audit_capab.yaml)")
    print("=" * 72)
    print(f"documents: {report['documents_total']}  "
          f"status={report['documents_status']}")
    print(f"chunks_v2: {report['chunks_v2_total']}")
    print(f"\nB1 manufacturer mal asignado (candidatos): {report['B1_total']}")
    for b, rows in report["B1_third_party_candidates"].items():
        print(f"    {b}: {len(rows)} docs")
    print(f"B2 model=unknown: docs={report['B2_documents_model_unknown_total']} "
          f"{report['B2_documents_model_unknown_by_manufacturer']}")
    print(f"   model=unknown en CHUNKS: "
          f"{report['B2_chunks_model_unknown_total']} chunks / "
          f"{report['B2_chunks_model_unknown_sources']} sources "
          f"{report['B2_chunks_model_unknown_by_manufacturer']}")
    print(f"B3 revision basura: {report['B3_revision_garbage_total']} docs "
          f"en {len(report['B3_revision_garbage'])} valores")
    print(f"B4 revision_date NULL: {report['B4_revision_date_null']}  "
          f"language NULL: {report['B4_language_null']}")
    print(f"B5 document_family: {report['B5_family_distinct']} únicos / "
          f"{report['B5_family_populated']} pobladas; "
          f"familias>=2 docs: {report['B5_families_with_2plus_docs']}")
    print(f"B6 docs sin chunks_v2: {report['B6_documents_without_chunks_v2']} "
          f"(en tabla vieja: {report['B6_with_chunks_in_old_table']}; "
          f"en ninguna: {report['B6_with_no_chunks_anywhere']})")
    print(f"B7 chunks sin document_id: "
          f"{report['B7_chunks_no_document_id_total']} chunks / "
          f"{report['B7_distinct_source_files']} sources  "
          f"{report['B7_by_manufacturer']}")
    print(f"   con fila en documents por filename: "
          f"{report['B7_sources_with_documents_row_by_filename']}  "
          f"sin fila: {report['B7_sources_without_documents_row']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
