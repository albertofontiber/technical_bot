#!/usr/bin/env python3
"""Renderiza páginas de un PDF a PNG (PyMuPDF) para verificación visual de golds.

Habilitador de las capas de verificación del ruler (TECH_DEBT #33): matrices,
tablas y páginas con OCR degradado NO se pueden verificar desde el texto extraído
del corpus; hay que LEER la página real. Reemplaza la dependencia de `pdftoppm`
que bloqueó el audit de la sesión 30 (PyMuPDF ya está en el stack de ingesta).

Las páginas se indican 1-indexed (como las cita el gold). Internamente PyMuPDF
es 0-indexed; el script convierte.

Uso:
  python scripts/render_pdf_page.py "<ruta_o_nombre.pdf>" 81
  python scripts/render_pdf_page.py "<ruta_o_nombre.pdf>" 80-82 --dpi 220
  python scripts/render_pdf_page.py "Manual...pdf" 81 --out logs/render

Si se pasa un nombre (no una ruta existente), se busca recursivamente bajo la
raíz del proyecto.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent


def resolve_pdf(arg: str) -> Path:
    p = Path(arg)
    if p.is_file():
        return p
    # Buscar por nombre bajo la raíz del proyecto (manuales viven en Manuales_*/).
    matches = list(ROOT.rglob(p.name))
    if not matches:
        sys.exit(f"PDF no encontrado: {arg!r} (ni como ruta ni bajo {ROOT})")
    if len(matches) > 1:
        print(f"AVISO: {len(matches)} coincidencias para {p.name!r}; uso la 1ª:")
        for m in matches[:5]:
            print(f"  - {m.relative_to(ROOT)}")
    return matches[0]


def parse_pages(spec: str) -> list[int]:
    """'81' -> [81]; '80-82' -> [80, 81, 82] (1-indexed)."""
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(spec)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", help="Ruta al PDF o nombre de archivo a buscar")
    ap.add_argument("pages", help="Página 1-indexed o rango 'a-b'")
    ap.add_argument("--dpi", type=int, default=200, help="Resolución (default 200)")
    ap.add_argument("--out", default="logs/render", help="Directorio de salida")
    ap.add_argument("--clip", help="Recorte normalizado 'l,t,r,b' en fracciones 0-1 "
                    "(p.ej. '0,0,0.35,1' = columna izquierda) para ampliar displays")
    args = ap.parse_args()

    pdf_path = resolve_pdf(args.pdf)
    out_dir = (ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    n = doc.page_count
    stem = pdf_path.stem[:50]
    written: list[Path] = []

    for pg in parse_pages(args.pages):
        if not (1 <= pg <= n):
            print(f"  saltada p{pg}: fuera de rango (1-{n})")
            continue
        page = doc.load_page(pg - 1)  # 0-indexed
        clip = None
        suffix = f"{args.dpi}dpi"
        if args.clip:
            l, t, r, b = (float(x) for x in args.clip.split(","))
            rc = page.rect
            clip = fitz.Rect(rc.x0 + l * rc.width, rc.y0 + t * rc.height,
                             rc.x0 + r * rc.width, rc.y0 + b * rc.height)
            suffix += "_clip"
        pix = page.get_pixmap(dpi=args.dpi, clip=clip)
        dst = out_dir / f"{stem}_p{pg}_{suffix}.png"
        pix.save(dst)
        written.append(dst)
        print(f"  p{pg} -> {dst.relative_to(ROOT)}  ({pix.width}x{pix.height})")

    doc.close()
    print(f"\n{len(written)} página(s) renderizada(s) de {pdf_path.name} ({n} págs total).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
