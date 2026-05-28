#!/usr/bin/env python3
"""Diagnóstico del corpus — inventario por tipo de documento.

Para cada PDF: páginas, texto extraíble, densidad de imágenes, idioma estimado.
Clasifica cada documento para dimensionar el sprint de re-ingesta:
  - escaneado      → texto casi nulo, necesita OCR/Vision sí o sí
  - imagen-heavy   → tiene texto pero muchas imágenes grandes (contenido visual clave)
  - texto-limpio   → buen ratio texto/página, pocas imágenes
  - mixto          → caso intermedio

Solo PyMuPDF (rápido). La detección fina de tablas se deja para el PoC.
"""
import sys
import glob
import os
import json
import collections
import fitz

sys.stdout.reconfigure(encoding="utf-8")

# Palabras función por idioma (heurística de detección)
LANG_WORDS = {
    "es": {"el", "la", "los", "las", "de", "que", "con", "para", "una", "del", "se", "por"},
    "en": {"the", "of", "and", "to", "in", "is", "for", "with", "this", "be", "on"},
    "it": {"il", "di", "che", "non", "per", "una", "con", "del", "sono", "della", "gli"},
    "pt": {"o", "de", "que", "não", "uma", "para", "com", "se", "do", "da", "os"},
    "fr": {"le", "de", "et", "la", "les", "des", "un", "une", "pour", "est", "dans"},
}


def detect_lang(text):
    words = text.lower().split()
    if len(words) < 30:
        return "?"
    sample = collections.Counter(w.strip(".,;:()[]") for w in words[:600])
    scores = {lang: sum(sample[w] for w in ws) for lang, ws in LANG_WORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "?"


def manufacturer(path):
    parts = path.replace("\\", "/").split("/")
    for p in parts:
        if p.startswith("Manuales"):
            return p
    return parts[0] if parts else "?"


def diagnose(path):
    doc = fitz.open(path)
    npages = len(doc)
    total_chars = 0
    big_images = 0
    all_text_parts = []
    for page in doc:
        txt = page.get_text()
        total_chars += len(txt.strip())
        if len(all_text_parts) < 8:
            all_text_parts.append(txt)
        for img in page.get_images(full=True):
            try:
                base = doc.extract_image(img[0])
                if base.get("width", 0) > 200 and base.get("height", 0) > 200:
                    big_images += 1
            except Exception:
                pass
    doc.close()

    cpp = total_chars / max(npages, 1)          # chars por página
    ipp = big_images / max(npages, 1)            # imágenes grandes por página
    lang = detect_lang(" ".join(all_text_parts))

    if cpp < 80:
        kind = "escaneado"
    elif cpp < 600 and ipp >= 0.6:
        kind = "imagen-heavy"
    elif cpp >= 1200 and ipp < 0.3:
        kind = "texto-limpio"
    else:
        kind = "mixto"

    return {
        "pages": npages, "chars_per_page": round(cpp), "big_img_per_page": round(ipp, 2),
        "kind": kind, "lang": lang,
    }


def main():
    pdfs = [p for p in glob.glob("**/*.pdf", recursive=True)
            if ".git" not in p and "extracted_images" not in p]
    print(f"Diagnosticando {len(pdfs)} PDFs...\n", flush=True)

    rows = []
    for i, p in enumerate(pdfs):
        try:
            d = diagnose(p)
            d["path"] = p
            d["manufacturer"] = manufacturer(p)
            rows.append(d)
        except Exception as e:
            rows.append({"path": p, "manufacturer": manufacturer(p),
                         "kind": "ERROR", "error": f"{type(e).__name__}: {e}",
                         "pages": 0, "lang": "?", "chars_per_page": 0, "big_img_per_page": 0})
        if (i + 1) % 150 == 0:
            print(f"  ...{i+1}/{len(pdfs)}", flush=True)

    with open("logs/corpus_diagnosis.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    # --- Resumen ---
    by_kind = collections.Counter(r["kind"] for r in rows)
    by_lang = collections.Counter(r["lang"] for r in rows)
    by_mfr = collections.Counter(r["manufacturer"] for r in rows)
    pages_by_kind = collections.defaultdict(int)
    for r in rows:
        pages_by_kind[r["kind"]] += r.get("pages", 0)

    print("\n" + "=" * 60)
    print(f"TOTAL: {len(rows)} PDFs, {sum(r.get('pages',0) for r in rows)} páginas\n")
    print("Por TIPO de documento:")
    for k, n in by_kind.most_common():
        print(f"  {k:14s} {n:4d} docs  ({pages_by_kind[k]:6d} págs)")
    print("\nPor IDIOMA (primario detectado):")
    for l, n in by_lang.most_common():
        print(f"  {l:4s} {n:4d} docs")
    print("\nPor CARPETA (fabricante):")
    for m, n in by_mfr.most_common():
        print(f"  {m:32s} {n:4d} docs")

    errs = [r for r in rows if r["kind"] == "ERROR"]
    if errs:
        print(f"\n{len(errs)} PDFs con error de apertura:")
        for r in errs[:10]:
            print(f"  {r['path']}: {r.get('error')}")

    print("\nDetalle completo en logs/corpus_diagnosis.json")


if __name__ == "__main__":
    main()
