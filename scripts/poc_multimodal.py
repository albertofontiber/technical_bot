#!/usr/bin/env python3
"""PoC de extracción LlamaParse — comparación de modos sobre un excerpt de un PDF.

Extrae un rango de páginas de un PDF con LlamaParse y guarda el markdown + la
confianza por página. Sirve para comparar modos sobre las mismas páginas.

Uso:
    python scripts/poc_multimodal.py --pages 60-68 --mode parse_page_with_agent
    python scripts/poc_multimodal.py --src "**/33976*VEP*.pdf" --label VESDA_VEP \
        --pages 84-88 --mode parse_page_with_llm
"""
import sys
import os
import time
import glob
import re
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")

import fitz
import httpx

OUT = "logs/poc_extraction"
PDF_DIR = os.path.join(OUT, "_pdfs")
API = "https://api.cloud.llamaindex.ai/api/v1/parsing"


def load_key():
    for line in open(".env", encoding="utf-8"):
        if line.strip().startswith("LLAMAPARSE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def make_excerpt(src_pdf, p_from, p_to, dst):
    doc = fitz.open(src_pdf)
    out = fitz.open()
    out.insert_pdf(doc, from_page=p_from - 1, to_page=min(p_to, len(doc)) - 1)
    out.save(dst)
    out.close()
    doc.close()


def llamaparse(pdf, key, mode, model):
    """Ejecuta LlamaParse. Devuelve (markdown, job_metadata, pages)."""
    headers = {"Authorization": f"Bearer {key}"}
    if mode == "auto":
        data = {
            "auto_mode": "true",
            "auto_mode_trigger_on_image_in_page": "true",
            "auto_mode_trigger_on_table_in_page": "true",
        }
    else:
        data = {"parse_mode": mode}
        if mode in ("parse_page_with_lvm", "parse_page_with_agent"):
            data["vendor_multimodal_model_name"] = model
    with open(pdf, "rb") as f:
        files = {"file": (os.path.basename(pdf), f, "application/pdf")}
        r = httpx.post(f"{API}/upload", headers=headers, data=data,
                       files=files, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"upload HTTP {r.status_code}: {r.text[:600]}")
    job_id = r.json()["id"]
    tag = f"mode={mode}" + (f", model={model}"
                            if mode in ("parse_page_with_lvm", "parse_page_with_agent")
                            else "")
    print(f"  job {job_id}  ({tag})")
    for _ in range(300):
        time.sleep(3)
        st = httpx.get(f"{API}/job/{job_id}", headers=headers,
                       timeout=30).json().get("status")
        if st == "SUCCESS":
            break
        if st in ("ERROR", "FAILED"):
            raise RuntimeError(f"job {st}")
    else:
        raise RuntimeError("timeout esperando el job")
    md = httpx.get(f"{API}/job/{job_id}/result/markdown", headers=headers,
                   timeout=60).json().get("markdown", "")
    rj = {}
    try:
        rj = httpx.get(f"{API}/job/{job_id}/result/json", headers=headers,
                       timeout=60).json()
    except Exception:
        pass
    return md, rj.get("job_metadata", {}), rj.get("pages", [])


def metrics(text):
    table_rows = len(re.findall(r"^\s*\|.+\|\s*$", text, re.MULTILINE))
    return len(text), table_rows


def main():
    ap = argparse.ArgumentParser(description="PoC extracción LlamaParse")
    ap.add_argument("--src", default="**/MPDT190.pdf",
                    help="patrón glob del PDF fuente")
    ap.add_argument("--label", default="MPDT190",
                    help="etiqueta para los nombres de archivo de salida")
    ap.add_argument("--pages", default="60-68",
                    help="rango de páginas PDF, 1-based inclusive")
    ap.add_argument("--mode", default="parse_page_with_lvm",
                    help="parse_page_with_llm | _lvm | _agent | auto")
    ap.add_argument("--model", default="anthropic-sonnet-4.5",
                    help="modelo VLM (aplica a lvm y agent)")
    args = ap.parse_args()
    p_from, p_to = (int(x) for x in args.pages.split("-"))

    key = load_key()
    if not key:
        print("LLAMAPARSE_API_KEY no encontrada en .env")
        return
    hits = glob.glob(args.src, recursive=True)
    if not hits:
        print(f"PDF no encontrado: {args.src}")
        return
    src = hits[0]
    os.makedirs(PDF_DIR, exist_ok=True)
    excerpt = os.path.join(PDF_DIR, f"visual_{args.label}_p{p_from}-{p_to}.pdf")
    make_excerpt(src, p_from, p_to, excerpt)
    n_pages = p_to - p_from + 1
    print(f"Excerpt: {os.path.basename(src)} págs PDF {p_from}-{p_to} ({n_pages} págs)\n")

    t0 = time.time()
    try:
        md, meta, pages = llamaparse(excerpt, key, args.mode, args.model)
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return
    dt = time.time() - t0
    chars, rows = metrics(md)

    slug = args.mode.replace("parse_page_with_", "").replace("parse_document_with_", "doc_")
    if args.mode in ("parse_page_with_lvm", "parse_page_with_agent"):
        slug += "_" + args.model.replace(".", "").replace("/", "-")
    path = os.path.join(OUT, f"visual_{args.label}_p{p_from}-{p_to}__llamaparse_{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\n  modo={args.mode}")
    print(f"  {chars:7d} chars  {rows:4d} filas-tabla  {dt:6.1f}s")
    triggered = meta.get("job_auto_mode_triggered_pages")
    if triggered is not None:
        print(f"  páginas escaladas por auto mode: {triggered} / {meta.get('job_pages')}")
    print(f"  job_metadata: {json.dumps(meta, ensure_ascii=False)}")
    if pages:
        print(f"  confianza por página:")
        for p in pages:
            ep = p.get("page")
            print(f"    PDF {p_from + ep - 1}:  conf={p.get('confidence')}  "
                  f"noText={p.get('noTextContent')}")
    print(f"  salida -> {path}")


if __name__ == "__main__":
    main()
