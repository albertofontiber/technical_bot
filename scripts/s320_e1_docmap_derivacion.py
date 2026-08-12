# -*- coding: utf-8 -*-
"""s320 E1a — Derivación de doc_map para los activos SIN entrada (censo E0 v2
por document_id: 279).

v3 (dúo r22): split-parcial → tier B con trazas (jamás candidato compuesto);
coherencia de marca por PREFIJO de normkey + check vendido_bajo (OEM→B);
el cubo no_producto es REVISIÓN HUMANA, no basura (un pm-norma sucio puede
tapar un producto real — caso EMA1224B4R con pm «EN-54-3»).

REGLA (DEC-074, plan v2 §E1): el matching REUSA la maquinaria adjudicada —
`Catalog.resolve()` (homónimo-primero, candidate-gating, redirects) sobre los
tokens del `product_model` del documento — JAMÁS fuzzy, JAMÁS un matcher nuevo.

TIERS (la propuesta separa lo derivable de lo adjudicable):
- **A (auto-propuesta)**: TODOS los tokens del pm resuelven con expand=True por
  exact|alias, y todos los ids comparten UNA marca cuyo prefijo está contenido
  en el manufacturer del documento (coherencia de marca). Entrada propuesta:
  role=primary, scope=doc, provenance con este script y el token→id.
- **B (packet)**: resuelve por paraguas/homónimo, o multi-marca, o parcial
  (algunos tokens sí, otros no) — la traza completa va al packet.
- **C (packet)**: ningún token resuelve — contexto (pm/marca/tipo) al packet.

Este script NO escribe el catálogo: emite propuesta + recibo + packet. La
escritura de la tier A va tras el dúo r21, vía catalog_store (valida TODO).
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import load as cargar_catalogo  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
CAT_DIR = ROOT / "data" / "catalog"


def _normkey(s: str) -> str:
    plano = unicodedata.normalize("NFKD", s or "")
    plano = "".join(c for c in plano if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", plano)


def main() -> int:
    censo = json.loads((ROOT / "evals" / "s320_e0_censo_v1.json")
                       .read_text(encoding="utf-8"))
    sin_entrada = censo["doc_map"]["sin_entrada_lista"]
    cat = cargar_catalogo(CAT_DIR)

    with abierto(timeout=30.0) as client:
        filas, off = [], 0
        while True:
            r = client.get(f"{SUPABASE_URL}/rest/v1/documents", headers=H,
                           params={"select": "id,source_pdf_filename,"
                                             "product_model,manufacturer,doc_type",
                                   "status": "eq.active", "order": "id.asc",
                                   "offset": str(off), "limit": "1000"})
            r.raise_for_status()
            lote = r.json()
            filas.extend(lote)
            if len(lote) < 1000:
                break
            off += 1000

    # r21 C1: selección por document_id (la clave estable), no por filename
    objetivo_ids = set(censo["doc_map"]["sin_entrada_ids"])
    docs = [d for d in filas if d["id"] in objetivo_ids]

    # r21 C2: la "/" del pm es AMBIGUA (separador-lista vs barra interna del
    # modelo: 20/20I, PUL-D/EXT). Tokenización RESOLUTION-FIRST: el pm ENTERO
    # primero; el split solo vale si TODAS las partes resuelven por sí mismas
    # — si no, el pm queda ENTERO para el packet (jamás fragmentos).
    _RE_NO_PRODUCTO = re.compile(
        r"^(unknown|n/?a)$|^(19|20)\d{2}$|^[a-z]+-(19|20)\d{2}$"
        r"|^(en|une|iso|ul|nfpa)[-\s]?\d", re.IGNORECASE)

    def _resolver_pm(pm: str) -> tuple[str, list[dict]]:
        entero = cat.resolve(pm)
        if entero is not None:
            return "entero", [{"token": pm, "via": entero.get("via"),
                               "ids": entero.get("ids", []),
                               "expand": entero.get("expand")}]
        partes = [t.strip() for t in pm.split("/") if t.strip()]
        if len(partes) > 1:
            trazas = []
            for tok in partes:
                res = cat.resolve(tok)
                trazas.append({"token": tok, "via": (res or {}).get("via"),
                               "ids": (res or {}).get("ids", []),
                               "expand": (res or {}).get("expand")})
            if all(t["via"] is not None for t in trazas):
                return "split-completo", trazas
            if any(t["via"] is not None for t in trazas):
                # (r22 Sol C1) resolución PARCIAL: algunas partes YA existen en
                # el catálogo (2X-A/2X-AT-F2/...) — al packet CON las trazas,
                # jamás a tier C como candidato compuesto falso.
                return "split-parcial", trazas
        return "sin-resolver", [{"token": pm, "via": None, "ids": [],
                                 "expand": None}]

    tier_a, tier_b, tier_c, no_producto = [], [], [], []
    for d in sorted(docs, key=lambda x: x.get("source_pdf_filename") or ""):
        pm = (d.get("product_model") or "").strip()
        marca_doc = _normkey(d.get("manufacturer") or "")
        modo, trazas = _resolver_pm(pm)
        base = {"document_id": d["id"],
                "source_file": re.sub(r"\.pdf$", "",
                                      (d.get("source_pdf_filename") or "")
                                      .strip().lower()),
                "pm": pm, "manufacturer": d.get("manufacturer"),
                "doc_type": d.get("doc_type"), "modo": modo, "trazas": trazas}
        if modo == "sin-resolver":
            if not pm or _RE_NO_PRODUCTO.match(pm):
                # r21 M3: fechas/normas/unknown NO son candidatos a producto
                no_producto.append(base)
            else:
                tier_c.append(base)
            continue
        if modo == "split-parcial":
            tier_b.append(base)
            continue
        exactas = [t for t in trazas
                   if t["via"] in ("exact", "alias") and t["expand"]
                   and len(t["ids"]) == 1]
        marcas = {i.split(":")[0] for t in exactas for i in t["ids"]}
        # (r22 Fable F2) coherencia = PREFIJO real del normkey del manufacturer,
        # no substring-en-cualquier-posición; y si el producto lleva
        # vendido_bajo distinto de la marca del doc → tier B (OEM legal≠marca)
        productos_por_id = cat.products  # ya es dict id->row (catalog_store:74)
        def _vendido_ok(pid: str) -> bool:
            vb = (productos_por_id.get(pid) or {}).get("vendido_bajo") or []
            if isinstance(vb, str):
                vb = [vb]
            # sin vendido_bajo = sin señal OEM → ok; con él, la marca del doc
            # debe estar entre las marcas bajo las que se vende
            return not vb or any(marca_doc.startswith(_normkey(v)) for v in vb)

        vendido_ok = all(_vendido_ok(t["ids"][0]) for t in exactas)
        coherente = (len(exactas) == len(trazas) and len(marcas) == 1
                     and marca_doc.startswith(next(iter(marcas)))
                     and vendido_ok)
        if coherente:
            ids_unicos = sorted({t["ids"][0] for t in exactas})
            tier_a.append({**base, "propuesta": {
                "document_id": d["id"],
                "source_file": base["source_file"],
                "entries": [{"id": pid, "role": "primary", "scope": "doc",
                             "provenance": "s320-e1 derivacion "
                                           "resolve(exact|alias)+marca-coherente"}
                            for pid in ids_unicos]}})
        else:
            tier_b.append(base)

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def _muestra(tier: list[dict], n: int = 8) -> list[dict]:
        return tier[:n]

    # Recibo COMPACTO (para revisión y repo) + detalle COMPLETO en fichero
    # aparte (r21: el recibo v1 de 5.000 líneas reventó el presupuesto del
    # segundo revisor — el subject de un dúo debe caber en el dúo).
    compacto = {
        "que_es": ("E1a v2 (r21 aplicado): derivación doc_map por "
                   "Catalog.resolve, cruce por document_id, tokenización "
                   "resolution-first (pm entero primero; split solo si TODAS "
                   "las partes resuelven; jamás fragmentos). NADA escrito: "
                   "tier A = propuesta de escritura post-dúo; B/C/no-producto "
                   "= packet."),
        "utc": utc,
        "objetivo_censo": len(objetivo_ids),
        "encontrados_activos": len(docs),
        "tiers": {"a": len(tier_a), "b": len(tier_b), "c": len(tier_c),
                  "no_producto": len(no_producto)},
        "muestras": {"a": _muestra(tier_a), "b": _muestra(tier_b),
                     "c": _muestra(tier_c), "no_producto": _muestra(no_producto)},
        "detalle_completo": "evals/s320_e1_docmap_derivacion_v2_detalle.json",
    }
    detalle = {"tier_a": tier_a, "tier_b": tier_b, "tier_c": tier_c,
               "no_producto": no_producto}
    (ROOT / "evals" / "s320_e1_docmap_derivacion_v2_detalle.json").write_text(
        json.dumps(detalle, ensure_ascii=False, indent=1), encoding="utf-8")
    destino = ROOT / "evals" / "s320_e1_docmap_derivacion_v2.json"
    destino.write_text(json.dumps(compacto, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"objetivo {len(objetivo_ids)} · localizados {len(docs)} · "
          f"A {len(tier_a)} · B {len(tier_b)} · C {len(tier_c)} · "
          f"no-producto {len(no_producto)}")
    print(f"recibo compacto -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
