#!/usr/bin/env python3
"""Busca un patrón (regex) en el texto extraído de un PDF (PyMuPDF), por página.

Herramienta de NAVEGACIÓN, no de verificación: LOCALIZA dónde está un claim para
luego confirmarlo. NUNCA es la verificación de un gold por sí sola — el texto
extraído de un PDF escaneado/OCR es el MISMO texto corrupto que tiene el corpus
(ver lección 7-segmentos: "r.i" en vez de "r.1"), así que "verificar" con esto
reproduciría el error. La verificación de un gold es SIEMPRE contra la fuente
primaria confirmada legible: render del píxel (render_pdf_page.py) + confirmar que
el PDF es digital-native y la lectura es fiel.

Uso:
  python scripts/pdf_grep.py "<ruta_o_nombre.pdf>" "retardo.*alarma" [--ctx 200]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent


def resolve_pdf(arg: str) -> Path:
    p = Path(arg)
    if p.is_file():
        return p
    m = list(ROOT.rglob(p.name))
    if not m:
        sys.exit(f"PDF no encontrado: {arg!r}")
    if len(m) > 1:
        print(f"AVISO: {len(m)} coincidencias; uso 1ª: {m[0].relative_to(ROOT)}")
    return m[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf")
    ap.add_argument("pattern")
    ap.add_argument("--ctx", type=int, default=160, help="caracteres de contexto")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    pdf = resolve_pdf(args.pdf)
    doc = fitz.open(pdf)
    npages = doc.page_count
    rx = re.compile(args.pattern, re.IGNORECASE)
    hits = 0
    for i in range(npages):
        txt = doc.load_page(i).get_text()
        for m in rx.finditer(txt):
            hits += 1
            s = max(0, m.start() - args.ctx)
            e = min(len(txt), m.end() + args.ctx)
            frag = " ".join(txt[s:e].split())
            print(f"[p{i + 1}] ...{frag}...")
    doc.close()
    print(f"\n{hits} coincidencia(s) de /{args.pattern}/ en {pdf.name} ({npages} págs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
