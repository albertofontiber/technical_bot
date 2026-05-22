#!/usr/bin/env python3
"""Etapa A2/A3 del pipeline de re-ingesta — extracción LlamaParse + store duradero.

Procesa los archivos únicos del manifiesto (A1, logs/reingest_manifest.json) con
LlamaParse en modo agéntico y guarda el resultado JSON crudo en un store local
duradero, indexado por SHA-256 del archivo + config de extracción.

El store (data/extraction/<config>/) es la frontera de la arquitectura de dos
etapas: la Etapa B (indexación) lee de aquí. LlamaParse se paga una sola vez —
re-ejecutar este script salta los archivos ya extraídos (resumable).

Modos de uso:
    python src/reingest/extract.py --probe          # muestra ~150 págs (probe)
    python src/reingest/extract.py --probe --model anthropic-sonnet-4.0
    python src/reingest/extract.py                  # corpus completo (tras OK)

El store se indexa por config (modo+modelo), así que correr el probe con varios
modelos no colisiona — cada uno en su subcarpeta.
"""
import sys
import os
import json
import time
import argparse
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")

import httpx

MANIFEST = "logs/reingest_manifest.json"
DIAGNOSIS = "logs/corpus_diagnosis.json"
STORE_ROOT = "data/extraction"
API = "https://api.cloud.llamaindex.ai/api/v1/parsing"

# Créditos/página medidos en el dashboard de LlamaParse (22 may 2026).
CREDITS_PER_PAGE = {"parse_page_with_agent": 45, "parse_page_with_lvm": 60,
                    "parse_page_with_llm": 3}


def load_key():
    for line in open(".env", encoding="utf-8"):
        if line.strip().startswith("LLAMAPARSE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)["files"]


def select_probe_sample(files, target_pages):
    """Muestra estratificada por 'kind' del diagnóstico — ~target_pages páginas."""
    kinds = {}
    if os.path.exists(DIAGNOSIS):
        with open(DIAGNOSIS, encoding="utf-8") as f:
            for r in json.load(f):
                if "path" in r:
                    kinds[r["path"]] = r.get("kind", "?")
    by_kind = collections.defaultdict(list)
    for rec in files:
        by_kind[kinds.get(rec["canonical_path"], "?")].append(rec)

    present = sorted(by_kind)
    per_kind = target_pages / max(1, len(present))
    sample = []
    for k in present:
        acc = 0
        for rec in sorted(by_kind[k], key=lambda r: r["canonical_path"]):
            if acc >= per_kind:
                break
            sample.append(rec)
            acc += rec.get("pages") or 0
    return sample


def config_slug(mode, model):
    s = mode.replace("parse_page_with_", "").replace("parse_document_with_", "doc_")
    if mode in ("parse_page_with_lvm", "parse_page_with_agent"):
        s += "_" + model.replace(".", "").replace("/", "-")
    return s


def llamaparse_extract(pdf_path, key, mode, model):
    """Sube el PDF, espera el job y devuelve (job_id, resultado JSON completo)."""
    headers = {"Authorization": f"Bearer {key}"}
    data = {"parse_mode": mode}
    if mode in ("parse_page_with_lvm", "parse_page_with_agent"):
        data["vendor_multimodal_model_name"] = model
    with open(pdf_path, "rb") as f:
        files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
        r = httpx.post(f"{API}/upload", headers=headers, data=data,
                       files=files, timeout=300)
    if r.status_code != 200:
        raise RuntimeError(f"upload HTTP {r.status_code}: {r.text[:300]}")
    job_id = r.json()["id"]
    for _ in range(400):  # ~20 min de techo por archivo
        time.sleep(3)
        st = httpx.get(f"{API}/job/{job_id}", headers=headers,
                       timeout=30).json().get("status")
        if st == "SUCCESS":
            break
        if st in ("ERROR", "FAILED"):
            raise RuntimeError(f"job {st}")
    else:
        raise RuntimeError("timeout esperando el job")
    result = httpx.get(f"{API}/job/{job_id}/result/json", headers=headers,
                       timeout=120).json()
    return job_id, result


def main():
    ap = argparse.ArgumentParser(description="Etapa A2/A3 — extracción LlamaParse")
    ap.add_argument("--mode", default="parse_page_with_agent")
    ap.add_argument("--model", default="anthropic-sonnet-4.5")
    ap.add_argument("--probe", action="store_true",
                    help="procesa solo una muestra estratificada (probe de modelo/coste)")
    ap.add_argument("--probe-pages", type=int, default=150)
    ap.add_argument("--limit", type=int, default=0,
                    help="procesa como máximo N archivos (0 = sin límite)")
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("LLAMAPARSE_API_KEY no encontrada en .env")
        return
    if not os.path.exists(MANIFEST):
        print(f"Falta {MANIFEST} — corre antes src/reingest/inventory.py (A1)")
        return

    files = load_manifest()
    if args.probe:
        files = select_probe_sample(files, args.probe_pages)
    if args.limit:
        files = files[:args.limit]

    slug = config_slug(args.mode, args.model)
    store = os.path.join(STORE_ROOT, slug)
    os.makedirs(store, exist_ok=True)

    total_pages = sum(r.get("pages") or 0 for r in files)
    est = total_pages * CREDITS_PER_PAGE.get(args.mode, 45)
    print(f"Config: {slug}")
    print(f"Archivos: {len(files)}  (~{total_pages} páginas)")
    print(f"Coste estimado: ~{est} créditos (~${est * 1.25 / 1000:.0f})")
    print(f"Store: {store}/\n")

    done = skipped = failed = 0
    failures = []
    for i, rec in enumerate(files):
        out = os.path.join(store, rec["sha256"] + ".json")
        if os.path.exists(out):
            skipped += 1
            continue
        path = rec["canonical_path"]
        try:
            t0 = time.time()
            job_id, result = llamaparse_extract(path, key, args.mode, args.model)
            record = {
                "sha256": rec["sha256"],
                "source_path": path,
                "manufacturer": rec.get("manufacturer"),
                "pages": rec.get("pages"),
                "mode": args.mode,
                "model": args.model,
                "job_id": job_id,
                "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "result": result,
            }
            tmp = out + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False)
            os.replace(tmp, out)  # escritura atómica → resumability robusta
            done += 1
            print(f"  [{i+1}/{len(files)}] OK     {os.path.basename(path)[:55]}  "
                  f"({time.time()-t0:.0f}s)")
        except Exception as e:
            failed += 1
            failures.append({"path": path, "sha256": rec["sha256"],
                             "error": f"{type(e).__name__}: {e}"})
            print(f"  [{i+1}/{len(files)}] FALLO  {os.path.basename(path)[:55]}  "
                  f"{type(e).__name__}: {e}")

    if failures:
        with open(os.path.join(store, "_failures.json"), "w", encoding="utf-8") as f:
            json.dump(failures, f, ensure_ascii=False, indent=1)

    print(f"\n{'='*60}")
    print(f"EXTRACCIÓN — {slug}")
    print(f"  procesados: {done}   ya estaban: {skipped}   fallos: {failed}")
    print(f"  store: {store}/")
    if failed:
        print(f"  fallos en {store}/_failures.json — re-ejecuta para reintentar")


if __name__ == "__main__":
    main()
