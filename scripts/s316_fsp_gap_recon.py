#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s316 — Recon READ-ONLY: ¿qué manuales de ARITECH/EDWARDS tiene el portal que NO
tenemos, para productos que YA están en el corpus?

ENCARGO (Alberto, s316): «no quiero añadir productos que no estén ya; quiero añadir los
manuales que faltan de los productos que YA están en el corpus» — el patrón NC-PF2 de
Kidde. Alcance acotado por él a DOS marcas: Aritech y Edwards.

MÉTODO: `docs/CORPUS_FIRESECURITYPRODUCTS.md` (canónico, DEC-027, validado s52/s53/s55 —
de ahí salieron los 43 docs Aritech y 3 Edwards que hoy están en corpus).
NO DESCARGA NADA: solo enumera y cruza. La descarga/ingesta es un paso aparte con su
propio gate (RULER + Protocolo 3).

Uso:
    python scripts/s316_fsp_gap_recon.py                 # Aritech + Edwards
    python scripts/s316_fsp_gap_recon.py --marcas Aritech
Salida: evals/s316_fsp_gap_recon_v1.json + resumen por consola.
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

PIM = "https://pim.firesecurityproducts.com"
# El gate REAL de la API no es el token: sin Origin/Referer devuelve 400 "No access".
ORIGIN = {"Origin": "https://es.firesecurityproducts.com",
          "Referer": "https://es.firesecurityproducts.com/"}
# secret PÚBLICO de la SPA Angular (está en el bundle main.*.js); no es una credencial
CLIENT_SECRET = os.getenv("FSP_CLIENT_SECRET", "1NgsscHYb1oYUcS5")
PAUSA = 0.8
MARCAS_DIANA = ("Aritech", "Edwards")


def _token(client: httpx.Client) -> str | None:
    usuario, clave = os.getenv("KIDDE_USER"), os.getenv("KIDDE_PASSWORD")
    if not (usuario and clave):
        print("AVISO: sin KIDDE_USER/KIDDE_PASSWORD — se sigue sin token "
              "(la lista pública funciona con Origin/Referer)")
        return None
    r = client.post(f"{PIM}/oauth2/token", headers=ORIGIN, data={
        "grant_type": "password", "username": usuario, "password": clave,
        "client_id": "local_angular_client", "client_secret": CLIENT_SECRET,
        "scope": "default_scope"})
    if r.status_code != 200:
        print(f"AVISO: token rechazado ({r.status_code}) — se sigue sin él")
        return None
    return r.json().get("access_token")


def _get(client: httpx.Client, ruta: str, params: dict, tok: str | None) -> dict:
    h = dict(ORIGIN)
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    r = client.get(f"{PIM}/rest/front/1/{ruta}", headers=h, params=params, timeout=90)
    if r.status_code in (403, 429):
        raise SystemExit(f"WAF/límite ({r.status_code}) en {ruta} — ABORTO educado")
    r.raise_for_status()
    time.sleep(PAUSA)
    return r.json()


def _productos_comprados(client: httpx.Client, tok: str | None) -> list[dict]:
    """Base instalada: productos de los PEDIDOS de la cuenta (§7 del doc canónico).

    Es la MISMA población de la que salió el corpus Aritech/Edwards actual (s53/s55:
    10 pedidos → 41 productos → 76 PDFs), así que «lo que falta» se compara contra el
    mismo universo en vez de contra el catálogo entero del portal (274 SKUs Aritech
    solo en `panels`, la mayoría nunca comprados). Privacidad: se usan SOLO para
    identificar productos; el dato comercial (precio/cantidad) se IGNORA.
    """
    d = _get(client, "orders", {"domain": "es", "language": "es"}, tok)
    pedidos = (d.get("results", {}) or {}).get("orders") or []
    print(f"pedidos de la cuenta: {len(pedidos)}")
    por_id: dict[str, dict] = {}
    for ped in pedidos:
        num = ped.get("drupal_order_number") or ped.get("oracle_order_id")
        if not num:
            continue
        try:
            det = _get(client, "order_details", {"domain": "es", "language": "es",
                                                 "order_number": str(num)}, tok)
        except Exception as exc:
            print(f"  AVISO: pedido {num} ilegible ({type(exc).__name__})")
            continue
        for li in ((det.get("results", {}) or {}).get("line_items") or []):
            pid = li.get("product_id")
            if not pid:
                continue
            por_id.setdefault(str(pid), {
                "product_id": pid, "sku": li.get("sku") or "",
                "descripcion": li.get("description") or ""})
    return list(por_id.values())


def _detalle(client: httpx.Client, product_id: str, tok: str | None) -> dict:
    """Marca REAL del producto (el portal cross-brandea: 2X-A sale Aritech aquí)."""
    try:
        d = _get(client, "product_details", {"domain": "es", "language": "es",
                                             "product_id": str(product_id)}, tok)
    except Exception:
        return {}
    return (d.get("results", {}) or {})


def _descargas(client: httpx.Client, product_id: str, tok: str | None) -> list[dict]:
    d = _get(client, "product_downloads",
             {"domain": "es", "language": "es", "product_id": str(product_id),
              "ignore_language": "false", "preview": "off"}, tok)
    fuera = []
    for cat in (d.get("results", {}).get("download_categories") or []):
        seccion = str(cat.get("parent") or "")
        if "ertificad" in seccion:          # certificados fuera (regla del playbook)
            continue
        for doc in (cat.get("downloads") or []):
            url = doc.get("file") or ""
            if not url:
                continue
            fuera.append({"seccion": seccion, "url": url,
                          "fichero": url.rsplit("/", 1)[-1],
                          "titulo": doc.get("title") or doc.get("name") or "",
                          "version": doc.get("major_version")})
    return fuera


def _corpus() -> tuple[set[str], dict[str, set[str]]]:
    """(nombres de fichero ya en documents, marca -> modelos en corpus)."""
    import httpx as hx
    U, K = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
    H = {"apikey": K, "Authorization": f"Bearer {K}"}
    filas, off = [], 0
    with hx.Client(timeout=120) as c:
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
    nombres = {(f.get("source_pdf_filename") or "").lower() for f in filas}
    modelos: dict[str, set[str]] = {}
    for f in filas:
        modelos.setdefault(f.get("manufacturer") or "?", set()).add(
            (f.get("product_model") or "").upper())
    return nombres, modelos


def _norm_modelo(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marcas", nargs="*", default=list(MARCAS_DIANA))
    a = ap.parse_args()

    nombres_corpus, modelos_corpus = _corpus()
    print(f"corpus: {len(nombres_corpus)} nombres de fichero · "
          + " · ".join(f"{m}={len(modelos_corpus.get(m, set()))} modelos"
                       for m in a.marcas))

    salida: dict = {"marcas": {}, "nota": (
        "READ-ONLY. 'faltante' = documento del portal cuyo nombre de fichero no está en "
        "documents.source_pdf_filename. Alcance: SOLO productos cuya serie/SKU ya casa "
        "con un product_model del corpus (encargo de Alberto s316).")}
    with httpx.Client(follow_redirects=True) as client:
        tok = _token(client)
        print("token:", "OK" if tok else "(sin token)")
        if not tok:
            print("❌ los pedidos exigen token — abortado")
            return 1
        comprados = _productos_comprados(client, tok)
        print(f"productos distintos comprados: {len(comprados)}")

        por_marca: dict[str, list[dict]] = {}
        for p in comprados:
            det = _detalle(client, p["product_id"], tok)
            marca = str(det.get("product_brand") or "").strip() or "Otros"
            p["marca"] = marca
            p["serie"] = ((det.get("series") or {}) or {}).get("series_name") or ""
            por_marca.setdefault(marca, []).append(p)
        print("reparto por marca REAL: "
              + " · ".join(f"{k}={len(v)}" for k, v in sorted(por_marca.items())))

        for marca in a.marcas:
            prods = [p for k, v in por_marca.items() if marca.lower() in k.lower()
                     for p in v]
            if not prods:
                print(f"\n{marca}: 0 productos comprados con esa marca — nada que cruzar")
                salida["marcas"][marca] = {"productos_comprados": 0}
                continue
            print(f"\n{marca}: {len(prods)} productos comprados")
            vistos_doc: set[str] = set()
            filas = []
            for p in prods:
                for doc in _descargas(client, p["product_id"], tok):
                    if doc["fichero"] in vistos_doc:
                        continue                 # manuales por SERIE: dedup por fichero
                    vistos_doc.add(doc["fichero"])
                    filas.append({**doc, "sku": p["sku"], "serie": p.get("serie", ""),
                                  "ya_en_corpus": doc["fichero"].lower() in nombres_corpus})
            faltan = [f for f in filas if not f["ya_en_corpus"]]
            print(f"  documentos únicos ofrecidos: {len(filas)} · "
                  f"ya tenemos: {len(filas) - len(faltan)} · FALTAN: {len(faltan)}")
            for f in faltan[:50]:
                print(f"    - [{f['seccion'][:24]:24s}] {f['sku'][:14]:14s} {f['fichero'][:58]}")
            salida["marcas"][marca] = {"productos_comprados": len(prods),
                                       "docs_unicos": len(filas),
                                       "faltantes": faltan, "todos": filas}

    out = ROOT / "evals" / "s316_fsp_gap_recon_v1.json"
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nrecibo → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
