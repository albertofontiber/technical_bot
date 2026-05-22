#!/usr/bin/env python3
"""Etapa A1 del pipeline de re-ingesta — inventario del corpus + dedup nivel 1.

Recorre todos los PDF del corpus, calcula el SHA-256 de cada archivo y agrupa
los byte-idénticos. Produce logs/reingest_manifest.json: la lista de archivos
ÚNICOS que la Etapa A2 (extracción LlamaParse) debe procesar — así no se paga
LlamaParse por las copias redundantes (el diagnóstico estimó ~188).

Coste cero (sin API). Determinista y re-ejecutable.

Uso:  python src/reingest/inventory.py
"""
import sys
import os
import glob
import json
import hashlib
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")

import fitz  # PyMuPDF — solo para contar páginas de PDFs no vistos por el diagnóstico

OUT = "logs/reingest_manifest.json"
DIAGNOSIS = "logs/corpus_diagnosis.json"
# Carpetas que no forman parte del corpus de manuales.
EXCLUDE = (".git", "extracted_images", "logs", ".venv", "venv", "node_modules")


def find_corpus_pdfs() -> list[str]:
    """Todos los PDF del corpus, excluyendo carpetas que no son manuales."""
    pdfs = []
    for p in glob.glob("**/*.pdf", recursive=True):
        norm = p.replace("\\", "/")
        if any(f"/{x}/" in f"/{norm}/" for x in EXCLUDE):
            continue
        pdfs.append(p)
    return sorted(pdfs)


def manufacturer(path: str) -> str:
    """Carpeta de fabricante a la que pertenece el PDF (heurística de ruta)."""
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        if part.startswith("Manuales"):
            return part
    return parts[0] if len(parts) > 1 else "(raíz)"


def sha256_file(path: str) -> str:
    """SHA-256 del contenido en bytes — estable ante renombrados."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load_pages_map() -> dict[str, int | None]:
    """{path: páginas} desde logs/corpus_diagnosis.json si existe (evita reabrir PDFs)."""
    if not os.path.exists(DIAGNOSIS):
        return {}
    with open(DIAGNOSIS, encoding="utf-8") as f:
        rows = json.load(f)
    return {r["path"]: r.get("pages") for r in rows if "path" in r}


def page_count(path: str) -> int | None:
    try:
        doc = fitz.open(path)
        n = len(doc)
        doc.close()
        return n
    except Exception:
        return None


def main():
    pdfs = find_corpus_pdfs()
    print(f"Corpus: {len(pdfs)} PDFs encontrados.\n", flush=True)
    pages_map = load_pages_map()

    by_hash: dict[str, list[str]] = collections.defaultdict(list)
    sizes: dict[str, int] = {}
    pages: dict[str, int | None] = {}

    for i, p in enumerate(pdfs):
        try:
            digest = sha256_file(p)
        except Exception as e:
            print(f"  ERROR leyendo {p}: {type(e).__name__}: {e}")
            continue
        by_hash[digest].append(p)
        sizes[p] = os.path.getsize(p)
        pages[p] = pages_map.get(p)
        if (i + 1) % 200 == 0:
            print(f"  ...{i + 1}/{len(pdfs)} hasheados", flush=True)

    # Páginas que el diagnóstico no cubrió: contarlas ahora.
    for p in pdfs:
        if p in sizes and pages.get(p) is None:
            pages[p] = page_count(p)

    manifest = []
    for digest, paths in by_hash.items():
        paths_sorted = sorted(paths)
        canonical = paths_sorted[0]
        mfrs = sorted({manufacturer(p) for p in paths_sorted})
        manifest.append({
            "sha256": digest,
            "canonical_path": canonical,
            "duplicate_paths": paths_sorted[1:],
            "n_copies": len(paths_sorted),
            "manufacturer": manufacturer(canonical),
            "pages": pages.get(canonical),
            "size_bytes": sizes.get(canonical),
            "cross_manufacturer": len(mfrs) > 1,
            "manufacturers_seen": mfrs if len(mfrs) > 1 else None,
        })
    manifest.sort(key=lambda r: r["canonical_path"])

    n_total = len(sizes)
    n_unique = len(manifest)
    n_dups = n_total - n_unique
    total_pages = sum(pages.get(p) or 0 for p in sizes)
    unique_pages = sum(r["pages"] or 0 for r in manifest)
    cross = [r for r in manifest if r["cross_manufacturer"]]

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_pdfs": n_total,
                "unique_files": n_unique,
                "duplicate_files": n_dups,
                "total_pages": total_pages,
                "unique_pages": unique_pages,
                "cross_manufacturer_dups": len(cross),
            },
            "files": manifest,
        }, f, ensure_ascii=False, indent=1)

    print("\n" + "=" * 60)
    print("INVENTARIO + DEDUP NIVEL 1")
    print(f"  PDFs totales:                       {n_total}")
    print(f"  Archivos unicos:                    {n_unique}")
    print(f"  Copias byte-identicas descartadas:  {n_dups}")
    print(f"  Paginas totales:                    {total_pages}")
    print(f"  Paginas unicas (a extraer en A2):   {unique_pages}")
    if cross:
        print(f"\n  AVISO: {len(cross)} duplicados cruzan carpeta de fabricante "
              f"(revisar atribucion):")
        for r in cross[:10]:
            print(f"    {r['canonical_path']}  [{', '.join(r['manufacturers_seen'])}]")
    print(f"\nManifiesto -> {OUT}")
    print("La Etapa A2 (extraccion LlamaParse) procesa solo los archivos unicos.")


if __name__ == "__main__":
    main()
