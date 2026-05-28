#!/usr/bin/env python3
"""PoC de stacks de extracción — compara 3 extractores sobre 6 manuales.

Stacks:
  - baseline : extractor actual del proyecto (PyMuPDF + pdfplumber)
  - llamaparse : LlamaParse vía API REST (SDK roto en Python 3.14)
  - docling : Docling SDK (layout-aware, local)

Para que sea rápido y barato, procesa un RANGO de páginas relevante de cada
manual (donde vive el contenido difícil), no el manual entero. Guarda cada
salida en logs/poc_extraction/ para inspección + métricas comparativas.
"""
import sys
import os
import time
import glob
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import fitz
import httpx

OUT = "logs/poc_extraction"
PDF_DIR = os.path.join(OUT, "_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

# (clave, patrón de búsqueda, rango de páginas 1-based con contenido difícil)
MANUALS = [
    ("escaneado_15584",   "**/15584.pdf",                                              (1, 12)),
    ("visual_MPDT190",    "**/MPDT190.pdf",                                            (62, 78)),
    ("tabla_VESDA_VEP",   "**/33976_13_VESDA-E_VEP-A00*.pdf",                          (40, 55)),
    ("multi_CAD150-8",    "**/55315013 Manual Centrales Analogicas CAD-150-8 Inst*.pdf", (1, 16)),
    ("ui_CAD250-MC380",   "**/CAD-250-MC-380-es.pdf",                                  (28, 38)),
    ("limpio_MFDT180",    "**/MFDT180.pdf",                                            (1, 12)),
]


def load_key():
    for line in open(".env", encoding="utf-8"):
        if line.strip().startswith("LLAMAPARSE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def make_excerpt(src_pdf, p_from, p_to, dst):
    """Crea un PDF recortado al rango [p_from, p_to] (1-based, inclusive)."""
    doc = fitz.open(src_pdf)
    out = fitz.open()
    out.insert_pdf(doc, from_page=p_from - 1, to_page=min(p_to, len(doc)) - 1)
    out.save(dst)
    out.close()
    doc.close()


# --- Extractor 1: baseline (proyecto) ---
def extract_baseline(pdf):
    from src.ingestion.pdf_parser import parse_pdf, enrich_with_tables, get_document_text
    parsed = parse_pdf(pdf)
    try:
        enrich_with_tables(parsed)
    except Exception:
        pass
    return get_document_text(parsed)


# --- Extractor 2: LlamaParse (REST) ---
def extract_llamaparse(pdf, key):
    headers = {"Authorization": f"Bearer {key}"}
    base = "https://api.cloud.llamaindex.ai/api/v1/parsing"
    with open(pdf, "rb") as f:
        files = {"file": (os.path.basename(pdf), f, "application/pdf")}
        r = httpx.post(f"{base}/upload", headers=headers, files=files, timeout=120)
    r.raise_for_status()
    job_id = r.json()["id"]
    for _ in range(120):
        time.sleep(3)
        st = httpx.get(f"{base}/job/{job_id}", headers=headers, timeout=30).json().get("status")
        if st == "SUCCESS":
            break
        if st in ("ERROR", "FAILED"):
            raise RuntimeError(f"job {st}")
    res = httpx.get(f"{base}/job/{job_id}/result/markdown", headers=headers, timeout=30).json()
    return res.get("markdown", "")


# --- Extractor 3: Docling ---
_DOCLING = None
def extract_docling(pdf):
    global _DOCLING
    if _DOCLING is None:
        from docling.document_converter import DocumentConverter
        _DOCLING = DocumentConverter()
    return _DOCLING.convert(pdf).document.export_to_markdown()


def metrics(text):
    table_rows = len(re.findall(r"^\s*\|.+\|\s*$", text, re.MULTILINE))
    return {"chars": len(text), "table_rows": table_rows}


def main():
    key = load_key()
    extractors = [
        ("baseline", lambda p: extract_baseline(p)),
        ("llamaparse", lambda p: extract_llamaparse(p, key)),
        ("docling", lambda p: extract_docling(p)),
    ]
    summary = []
    for name, pattern, (p_from, p_to) in MANUALS:
        hits = glob.glob(pattern, recursive=True)
        if not hits:
            print(f"[{name}] PDF no encontrado: {pattern}")
            continue
        excerpt = os.path.join(PDF_DIR, f"{name}.pdf")
        make_excerpt(hits[0], p_from, p_to, excerpt)
        print(f"\n[{name}] págs {p_from}-{p_to} de {os.path.basename(hits[0])}")
        for stack, fn in extractors:
            t0 = time.time()
            try:
                text = fn(excerpt)
                m = metrics(text)
                dt = time.time() - t0
                path = os.path.join(OUT, f"{name}__{stack}.md")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"   {stack:11s} {m['chars']:7d} chars  {m['table_rows']:4d} filas-tabla  {dt:6.1f}s")
                summary.append((name, stack, m["chars"], m["table_rows"], round(dt, 1), ""))
            except Exception as e:
                print(f"   {stack:11s} ERROR: {type(e).__name__}: {e}")
                summary.append((name, stack, 0, 0, 0, f"{type(e).__name__}: {e}"))

    print("\n" + "=" * 70)
    print("RESUMEN (manual · stack · chars · filas-tabla · seg)")
    for row in summary:
        err = f"  ERROR: {row[5]}" if row[5] else ""
        print(f"  {row[0]:18s} {row[1]:11s} {row[2]:7d} {row[3]:4d} {row[4]:7.1f}{err}")
    print(f"\nSalidas en {OUT}/  — un .md por (manual, stack) para inspección.")


if __name__ == "__main__":
    main()
