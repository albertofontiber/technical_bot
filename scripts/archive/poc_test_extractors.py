#!/usr/bin/env python3
"""Prueba mínima de los extractores antes del PoC completo.

LlamaParse vía API REST (el SDK Python falla con Python 3.14 + Pydantic V1).
Docling vía SDK. Prueba sobre un PDF de 2 páginas para confirmar APIs.
"""
import sys
import os
import time
import glob

sys.stdout.reconfigure(encoding="utf-8")

# Windows: HuggingFace Hub usa symlinks que requieren permisos de admin.
# Desactivarlos hace que copie los archivos (funcional, sin privilegios).
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# PDF de prueba: 2 páginas
TEST_PDF = glob.glob("**/55360004 Manual Detector Gas DGD-600*.pdf", recursive=True)[0]
print(f"PDF de prueba: {os.path.basename(TEST_PDF)}\n")


def load_key():
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if line.startswith("LLAMAPARSE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def test_llamaparse():
    print("=== LlamaParse (API REST) ===")
    import httpx
    key = load_key()
    headers = {"Authorization": f"Bearer {key}"}
    base = "https://api.cloud.llamaindex.ai/api/v1/parsing"
    try:
        with open(TEST_PDF, "rb") as f:
            files = {"file": (os.path.basename(TEST_PDF), f, "application/pdf")}
            r = httpx.post(f"{base}/upload", headers=headers, files=files, timeout=90)
        if r.status_code != 200:
            print(f"  upload HTTP {r.status_code}: {r.text[:300]}")
            return
        job_id = r.json()["id"]
        print(f"  upload OK, job {job_id}")
        for _ in range(60):
            time.sleep(3)
            s = httpx.get(f"{base}/job/{job_id}", headers=headers, timeout=30).json()
            st = s.get("status")
            if st == "SUCCESS":
                break
            if st in ("ERROR", "FAILED"):
                print(f"  job falló: {s}")
                return
        res = httpx.get(f"{base}/job/{job_id}/result/markdown", headers=headers, timeout=30).json()
        md = res.get("markdown", "")
        print(f"  ✓ OK — {len(md)} chars de markdown")
        print(f"  --- primeros 400 chars ---\n{md[:400]}\n")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")


def test_docling():
    print("=== Docling (SDK local) ===")
    try:
        t0 = time.time()
        from docling.document_converter import DocumentConverter
        conv = DocumentConverter()
        print("  (convirtiendo — la 1ª vez descarga modelos, puede tardar)")
        result = conv.convert(TEST_PDF)
        md = result.document.export_to_markdown()
        print(f"  ✓ OK — {len(md)} chars de markdown en {time.time()-t0:.0f}s")
        print(f"  --- primeros 400 chars ---\n{md[:400]}\n")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    # test_llamaparse() ya confirmado OK — no re-quemar páginas de la cuenta
    test_docling()
