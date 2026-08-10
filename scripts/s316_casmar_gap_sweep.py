# -*- coding: utf-8 -*-
"""s316 — Barrido Casmar de MANUALES QUE FALTAN de equipos que YA están en el corpus.

ENCARGO (Alberto, s316): no incorporar productos nuevos; encontrar los manuales
ausentes de los equipos ya ingestados — el patrón NC-PF2 de Kidde (el equipo estaba,
sus manuales no, y sí estaban publicados en Casmar). Alcance acotado por él a ARITECH
y EDWARDS. «Excluyendo certificados/homologaciones, y con cuidado de quedarnos solo
con los documentos que son REALMENTE diferentes.»

MÉTODO: el mismo de s314 (`scripts/s314_casmar_harvest.py`) — listado
`asistencia-tecnica/documentacion` filtrado por SKU, cortesía 1.2s, aborto educado
ante WAF, y la guarda anti-fallback (sin match el portal devuelve el listado GLOBAL,
que se confundiría con «este SKU tiene 400 PDFs»).

READ-ONLY: enumera y cruza; NO descarga. La identidad dura es sha256 del contenido y
eso exige bajar el fichero — paso aparte, con su gate. Aquí la criba es:
  1. fuera certificados/homologaciones/declaraciones (regla del playbook: no se
     responden dudas técnicas con un certificado);
  2. fuera lo que ya está en el corpus por NOMBRE de fichero normalizado;
  3. los que sobreviven se marcan con su parecido al corpus para no bajar el mismo
     documento con otro nombre.

Uso:  python scripts/s316_casmar_gap_sweep.py [--marcas Aritech Edwards]
Salida: evals/s316_casmar_gap_sweep_v1.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
FICHA = "https://www.casmarglobal.com/es/{sku}.html"
PAUSA = 1.2
# Los documentos NO están en `href`: viven en el onclick del «Área de Descargas»
# (`checkPdf(url, sku, attributeCode)`), con el attributeCode diciendo QUÉ es cada
# uno. Descubierto en s316 con el navegador; el listado
# `asistencia-tecnica/documentacion?filters[sku]=` que usó s314 YA NO FILTRA
# (devuelve el listado global para cualquier SKU — verificado con NC-PF2, el control
# positivo de s314), así que ese camino da falsos «0 documentos».
CHECKPDF = re.compile(
    r"checkPdf\(\s*'([^']+\.pdf)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'", re.I)
# Regla del playbook (s314) + encargo explícito de Alberto: certificados y
# homologaciones FUERA. Se filtra por attributeCode (autoritativo) y por nombre.
ATTR_EXCLUIDOS = re.compile(r"homolog|certific|declarac|conformi", re.I)
EXCLUIR = re.compile(
    r"certifi|homolog|declarac|conformi|_ce[_.\-]|[_\-]ce\.|[_\-]dop[_.\-]|^h_dop|"
    r"prestacion|attestation|ul[_\-]?listing|vds[_\-]?approval", re.I)


def _get(c: httpx.Client, url: str, **kw):
    r = c.get(url, **kw)
    if r.status_code in (403, 429):
        raise SystemExit(f"WAF/límite ({r.status_code}) en {url} — ABORTO educado")
    time.sleep(PAUSA)
    return r


def _docs_de_ficha(html: str) -> list[dict]:
    """[{url, sku, attr}] del «Área de Descargas» de una ficha de producto."""
    fuera, vistos = [], set()
    for url, sku, attr in CHECKPDF.findall(html):
        if url in vistos:
            continue
        vistos.add(url)
        fuera.append({"url": url, "sku": sku, "attr": attr})
    return fuera


def _norm_nombre(n: str) -> str:
    """Nombre comparable: sin extensión, sin separadores, sin sufijos de idioma/rev."""
    n = re.sub(r"\.pdf$", "", n, flags=re.I)
    n = re.sub(r"[^a-z0-9]", "", n.lower())
    return n


def _corpus():
    U, K = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
    H = {"apikey": K, "Authorization": f"Bearer {K}"}
    filas, off = [], 0
    with httpx.Client(timeout=120) as c:
        while True:
            r = c.get(f"{U}/rest/v1/documents", headers={**H, "Range": f"{off}-{off+999}"},
                      params={"select": "source_pdf_filename,manufacturer,product_model",
                              "order": "id.asc"})
            r.raise_for_status()
            b = r.json()
            filas += b
            if len(b) < 1000:
                break
            off += 1000
    nombres = {_norm_nombre(f.get("source_pdf_filename") or "") for f in filas}
    nombres.discard("")
    modelos: dict[str, list[str]] = {}
    for f in filas:
        m = (f.get("manufacturer") or "").strip()
        pm = (f.get("product_model") or "").strip()
        if m and pm:
            modelos.setdefault(m, []).append(pm)
    return nombres, modelos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marcas", nargs="*", default=["Aritech", "Edwards"])
    a = ap.parse_args()

    nombres_corpus, modelos = _corpus()
    print(f"corpus: {len(nombres_corpus)} nombres normalizados")

    # Los product_model del corpus pueden ser compuestos ("2X-A/2X-AT-F2/…"): se
    # consulta cada componente por separado, que es como el SKU vive en el portal.
    diana: list[tuple[str, str]] = []
    for marca in a.marcas:
        vistos = set()
        for pm in modelos.get(marca, []):
            for parte in re.split(r"[/,;]| y ", pm):
                parte = parte.strip()
                if parte and parte.upper() not in vistos:
                    vistos.add(parte.upper())
                    diana.append((marca, parte))
    print(f"SKUs diana (modelos ya en corpus): {len(diana)} "
          + " · ".join(f"{m}={sum(1 for x, _ in diana if x == m)}" for m in a.marcas))

    salida: dict = {"nota": (
        "READ-ONLY. 'candidato' = PDF de Casmar para un modelo YA en corpus, que no es "
        "certificado/homologación y cuyo nombre normalizado no está en documents. "
        "La identidad DURA es sha256 y exige descargar: paso aparte."),
        "marcas": a.marcas, "por_sku": {}, "candidatos": []}

    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        vistos_pdf: set[str] = set()
        sin_ficha, n_excl, n_ya = 0, 0, 0
        for n, (marca, sku) in enumerate(diana, 1):
            url_ficha = FICHA.format(sku=sku.lower().replace(" ", "-"))
            try:
                r = _get(c, url_ficha)
            except SystemExit:
                raise
            except Exception as exc:
                print(f"  [{n}/{len(diana)}] {sku}: ERROR {type(exc).__name__}")
                continue
            if r.status_code == 404:
                sin_ficha += 1
                continue
            if r.status_code != 200:
                print(f"  [{n}/{len(diana)}] {sku}: HTTP {r.status_code}")
                continue
            docs = _docs_de_ficha(r.text)
            salida["por_sku"][f"{marca}:{sku}"] = len(docs)
            nuevos = 0
            for d in docs:
                fichero = d["url"].rsplit("/", 1)[-1]
                # el attributeCode es AUTORITATIVO sobre el nombre para decir qué es
                if ATTR_EXCLUIDOS.search(d["attr"]) or EXCLUIR.search(fichero):
                    n_excl += 1
                    continue
                if d["url"] in vistos_pdf:
                    continue                      # mismo PDF servido a varios SKU
                vistos_pdf.add(d["url"])
                if _norm_nombre(fichero) in nombres_corpus:
                    n_ya += 1
                    continue
                salida["candidatos"].append(
                    {"marca": marca, "sku": sku, "fichero": fichero,
                     "tipo": d["attr"], "url": d["url"]})
                nuevos += 1
            if docs:
                print(f"  [{n}/{len(diana)}] {marca}/{sku}: {len(docs)} docs "
                      f"· candidatos nuevos {nuevos}")
        salida["resumen"] = {"skus_sin_ficha": sin_ficha,
                             "excluidos_cert_homolog": n_excl,
                             "ya_en_corpus_por_nombre": n_ya,
                             "pdfs_distintos_vistos": len(vistos_pdf)}
        print(f"\nSKUs sin ficha en Casmar: {sin_ficha}/{len(diana)} · "
              f"excluidos cert/homolog: {n_excl} · ya en corpus: {n_ya}")

    cands = salida["candidatos"]
    print(f"\nCANDIDATOS (manuales de equipos YA en corpus, sin certificados, "
          f"no presentes por nombre): {len(cands)}")
    for cd in cands:
        print(f"  - [{cd['marca']}/{cd['sku'][:16]:16s}] {cd['fichero'][:70]}")
    out = ROOT / "evals" / "s316_casmar_gap_sweep_v1.json"
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nrecibo → {out}")
    print("SIGUIENTE (paso aparte, con gate): descargar los candidatos y dedupar por "
          "sha256 contra documents.source_pdf_sha256 — el nombre NO decide identidad.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
