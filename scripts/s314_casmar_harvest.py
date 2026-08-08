# -*- coding: utf-8 -*-
"""Cosecha Casmar/Kidde — Fase A: catalogo; Fase B: docs por SKU; volcado JSON.

Educado: 1.2s entre requests; aborta a la primera senal de WAF (403/429).
"""
import io
import json
import os
import re
import sys
import time

import httpx

SCRATCH = os.environ.get("S314_WORKDIR", os.getcwd())  # artefactos del harvest (JSONs/staging)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
BASE_DOC = "https://www.casmarglobal.com/es/asistencia-tecnica/documentacion"
BASE_SEARCH = "https://www.casmarglobal.com/es/catalogsearch/result/"
PAUSA = 1.2


def _get(c, url, **kw):
    r = c.get(url, **kw)
    if r.status_code in (403, 429):
        raise SystemExit(f"WAF/limite ({r.status_code}) en {url} — ABORTO educado")
    r.raise_for_status()
    time.sleep(PAUSA)
    return r


def fase_a_catalogo(c):
    """Catalogo Kidde via busqueda paginada. Devuelve {sku: url_producto}."""
    skus = {}
    p = 1
    while True:
        r = _get(c, BASE_SEARCH, params={"q": "kidde", "product_list_limit": "36", "p": str(p)})
        items = re.findall(
            r'<a[^>]*class="[^"]*product-item-link[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            r.text, re.S)
        nuevos = 0
        for url, nombre in items:
            sku = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", nombre)).strip()
            if sku and sku not in skus:
                skus[sku] = url
                nuevos += 1
        print(f"  catalogo p={p}: {len(items)} items, {nuevos} nuevos (total {len(skus)})")
        if len(items) < 36 or nuevos == 0:
            break
        p += 1
        if p > 60:  # tope de cordura
            print("  ! tope de 60 paginas alcanzado")
            break
    return skus


def fase_b_docs(c, skus, baseline):
    """Docs por SKU exacto. baseline = set de PDFs del listado global (fallback)."""
    resultado = {}
    for n, sku in enumerate(sorted(skus), 1):
        r = _get(c, BASE_DOC, params={"filters[sku]": sku, "sort": "sku", "dir": "DESC"})
        pdfs = set(re.findall(r'href="(https://www\.casmarglobal\.com/media/[^"]+?\.pdf)"', r.text, re.I))
        # guarda anti-fallback: sin match, el portal devuelve el listado global
        if pdfs and pdfs == baseline:
            pdfs = set()
        resultado[sku] = sorted(pdfs)
        print(f"  [{n}/{len(skus)}] {sku}: {len(pdfs)} PDFs")
    return resultado


def main():
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        print("== Fase A: catalogo Kidde ==")
        skus = fase_a_catalogo(c)

        # union con los SKUs Kidde del corpus (por si la busqueda no los devuelve)
        corpus_skus = [
            "AD68N-0100", "NC-PF2", "KE-AS3115R-WM", "KE-DP3120W", "9-30781-KID-EN",
            "KE-DBA-AUXW", "NC-PF4-SC", "KE-IO3122", "KE-IO3101", "NC-PF4",
            "KE-DM3010R-KIT", "KE-DM3010R", "NC-PF8", "KE-AS3115R-WMIP", "KE-DB3010W",
            "KE-DP3020W", "NC-PF8-SC", "KE-DT3001W-HAB", "KE-IO3144", "9-30783-KID-EN",
        ]
        for s in corpus_skus:
            skus.setdefault(s, None)
        print(f"catalogo+corpus: {len(skus)} SKUs")

        # baseline del listado global con los mismos parametros de sort
        r = _get(c, BASE_DOC, params={"sort": "sku", "dir": "DESC"})
        baseline = set(re.findall(r'href="(https://www\.casmarglobal\.com/media/[^"]+?\.pdf)"', r.text, re.I))
        print(f"baseline global: {len(baseline)} PDFs")

        print("== Fase B: docs por SKU ==")
        docs = fase_b_docs(c, skus, baseline)

    salida = {"skus": {k: v for k, v in skus.items()}, "docs": docs}
    ruta = os.path.join(SCRATCH, "casmar_kidde_harvest.json")
    io.open(ruta, "w", encoding="utf-8").write(json.dumps(salida, ensure_ascii=False, indent=1))
    con_docs = sum(1 for v in docs.values() if v)
    total_pdfs = len({u for v in docs.values() for u in v})
    print(f"\nRESUMEN: {len(skus)} SKUs, {con_docs} con docs, {total_pdfs} PDFs unicos -> {ruta}")


if __name__ == "__main__":
    main()
