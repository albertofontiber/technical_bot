# -*- coding: utf-8 -*-
"""Recon READ-ONLY del catalogo Casmar: ¿lleva Aritech / Edwards como marca?

s315: la sesion remota tenia casmarglobal.com bloqueado por politica de egress, asi
que la pregunta quedo abierta. Este script reusa el metodo s314 (search paginado de
Magento, cortesia 1.2s, aborta en 403/429) y se corre desde un entorno CON red:

    python scripts/s315_casmar_recon.py            # busca aritech y edwards
    python scripts/s315_casmar_recon.py FP1216 ATS EST3 EST4 iO1000

Salida: recon_search.json en el directorio actual (SKUs + URL por termino). Si sale
0 SKUs para ambas marcas, la fuente para Aritech/Edwards es firesecurityproducts.com
(portal del grupo; cf. docs/CORPUS_FIRESECURITYPRODUCTS.md), no Casmar.
Evidencia previa (harvest s314, q=kidde): la familia 2X es Aritech-OEM vendida como
Kidde y YA esta en corpus; de Edwards no hubo rastro.
"""
import json
import re
import sys
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
BASE_SEARCH = "https://www.casmarglobal.com/es/catalogsearch/result/"
PAUSA = 1.2

sys.stdout.reconfigure(line_buffering=True)


def _get(c, url, **kw):
    kw.setdefault("timeout", 60)
    r = c.get(url, **kw)
    if r.status_code in (403, 429):
        raise SystemExit(f"WAF/limite ({r.status_code}) en {url} — ABORTO educado")
    r.raise_for_status()
    time.sleep(PAUSA)
    return r


def buscar(c, term, max_pages=8):
    skus = {}
    p = 1
    total_declared = None
    while True:
        r = _get(c, BASE_SEARCH, params={"q": term, "product_list_limit": "36", "p": str(p)})
        if total_declared is None:
            m = re.search(r'toolbar-number">(\d+)</span>', r.text)
            # Magento suele mostrar "Artículos X-Y de Z" — coger el mayor numero
            nums = re.findall(r'class="toolbar-number">\s*(\d+)\s*</span>', r.text)
            if nums:
                total_declared = max(int(n) for n in nums)
        items = re.findall(
            r'<a[^>]*class="[^"]*product-item-link[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            r.text, re.S)
        nuevos = 0
        for url, nombre in items:
            sku = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", nombre)).strip()
            if sku and sku not in skus:
                skus[sku] = url
                nuevos += 1
        print(f"  [{term}] p={p}: {len(items)} items, {nuevos} nuevos (acum {len(skus)}, total_decl={total_declared})")
        if len(items) < 36 or nuevos == 0 or p >= max_pages:
            break
        p += 1
    return skus, total_declared


def main():
    terms = sys.argv[1:] or ["aritech", "edwards"]
    out = {}
    with requests.Session() as c:
        c.headers.update(UA)
        for t in terms:
            print(f"== busqueda: {t} ==")
            skus, total = buscar(c, t)
            out[t] = {"total_declared": total, "n_skus": len(skus), "skus": skus}
    path = "recon_search.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"-> {path}")


if __name__ == "__main__":
    main()
