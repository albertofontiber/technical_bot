# -*- coding: utf-8 -*-
"""Fase B v2 — docs por SKU con form_id (el fix) + paginacion intra-SKU."""
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
FORM_ID = "af52b3cc9cd3608beb69017b101dedd9"
PAUSA = 1.2

sys.stdout.reconfigure(line_buffering=True)

prev = json.loads(io.open(os.path.join(SCRATCH, "casmar_kidde_harvest.json"), encoding="utf-8").read())
skus = prev["skus"]


def _get(c, params):
    r = c.get(BASE_DOC, params=params)
    if r.status_code in (403, 429):
        raise SystemExit(f"WAF/limite ({r.status_code}) — ABORTO educado")
    r.raise_for_status()
    time.sleep(PAUSA)
    return r.text


def pdfs_de(html):
    return set(re.findall(r'href="(https://www\.casmarglobal\.com/media/[^"]+?\.pdf)"', html, re.I))


with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
    # baseline global (fallback si el filtro no matchea nada)
    baseline = pdfs_de(_get(c, {"form_id": FORM_ID, "sort": "sku", "dir": "DESC"}))
    print(f"baseline global: {len(baseline)} PDFs")

    docs = {}
    for n, sku in enumerate(sorted(skus), 1):
        vistos = set()
        for p in range(1, 6):  # cap de cordura: 5 paginas por SKU
            params = {"form_id": FORM_ID, "filters[sku]": sku,
                      "sort": "sku", "dir": "DESC", "p": str(p)}
            html = _get(c, params)
            lote = pdfs_de(html)
            if lote == baseline:      # filtro ignorado / sin resultados
                lote = set()
            nuevos = lote - vistos
            vistos |= lote
            if not nuevos:
                break
        docs[sku] = sorted(vistos)
        print(f"[{n}/{len(skus)}] {sku}: {len(vistos)} PDFs")

salida = {"skus": skus, "docs": docs}
ruta = os.path.join(SCRATCH, "casmar_kidde_harvest.json")
io.open(ruta, "w", encoding="utf-8").write(json.dumps(salida, ensure_ascii=False, indent=1))
con_docs = sum(1 for v in docs.values() if v)
total = len({u for v in docs.values() for u in v})
print(f"\nRESUMEN v2: {len(skus)} SKUs, {con_docs} con docs, {total} PDFs unicos")
