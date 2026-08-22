# -*- coding: utf-8 -*-
"""B1 — Censo de la DIANA de clasificación: la vista de UNA marca, la REAL.

La población se define POR EL JOIN DEL CÓDIGO (v3 §0, cierre de Sol2-3/Fable2-1:
mis cifras a mano mezclaban ids crudos con el join redirect-normalizado): se usa
`_productos_marca` — la MISMA función que sirve el inventario — y el lookup de
docs va SIEMPRE vía `follow_redirect` (el censo s322 usaba pid crudo; con
Detnov/Kidde no mordía, aquí sí). Solo lectura.

Además el recibo PRE-REGISTRA el suelo del gate de efecto (v3 §1.8, Fable2-3):
proxy de centrales-APARENTES por nombre/pista —declarado como APUESTA, el nombre
engaña por principio rector— y suelo = min(15, ceil(proxy·0,5)), fijado AQUÍ,
antes de la pasada, jamás ajustado después.

Parametrizado por marca al cerrar s336-lote. El patrón de familias-panel es
CONOCIMIENTO DE MARCA (`^(NFS|ID\\d|AFP|...)` es Notifier puro): una marca sin
patrón declarado obtiene un proxy menor y por tanto un suelo menor — es decir,
un gate de efecto MÁS LAXO. No se esconde: el recibo estampa qué patrón se usó
y avisa por stdout cuando va vacío. La visibilidad ES el control.

Uso: python scripts/s336_censo_diana.py [--marca morley] [--familias-panel REGEX]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import lib_lote_marca as L  # noqa: E402
from src.rag.catalog_store import load  # noqa: E402

_RX_CENTRAL_APARENTE = re.compile(r"\b(central|panel)\b", re.IGNORECASE)
# Histórico de la vista que fijó el método; se conserva para que su censo sea
# reproducible byte a byte. Para otra marca hay que declararlo con --familias-panel.
FAMILIAS_PANEL_HISTORICAS = {
    "notifier": r"^(NFS|ID\d|AFP|NCA|AM\d|ONYX)",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marca", default=L.MARCA_HISTORICA)
    ap.add_argument("--force", action="store_true",
                    help="re-escribe el recibo aunque ya exista (ver guarda)")
    ap.add_argument("--familias-panel", default=None,
                    help="regex de familias que APARENTAN central en esta marca "
                         "(alimenta el proxy que fija el suelo del gate de "
                         "efecto). Sin él, el suelo baja y se avisa.")
    args = ap.parse_args()
    marca = L.normaliza_marca(args.marca)

    patron = args.familias_panel
    if patron is None:
        patron = FAMILIAS_PANEL_HISTORICAS.get(marca, "")
    rx_familia = re.compile(patron, re.IGNORECASE) if patron else None

    destino = L.ruta("censo", marca)
    motivo = L.guarda_de_pisado(destino, marca, args.force)
    if motivo:
        print(motivo)
        return 3

    cat = load()
    con_docs: dict[str, list[str]] = {}
    for dm in cat.doc_map:
        for e in dm.get("entries") or ():
            con_docs.setdefault(cat.follow_redirect(e["id"]), []).append(
                dm.get("source_file") or "")

    vista = list(L.vista_de(cat, marca).values())
    if not vista:
        print(f"la vista de «{marca}» está VACÍA — ¿namespace mal escrito?")
        return 2
    sin_clas = [p for p in vista if not p.get("clasificacion")]

    diana = []
    for p in sorted(sin_clas, key=lambda x: x["id"]):
        pid = p["id"]
        docs = con_docs.get(cat.follow_redirect(pid), [])
        assert docs, f"la vista garantiza docs y {pid} no tiene — join roto"
        pista = p.get("categoria") or ""
        canonical = p.get("canonical_model") or ""
        proxy_central = bool(_RX_CENTRAL_APARENTE.search(str(pista))
                             or (rx_familia and rx_familia.match(canonical)))
        diana.append({"id": pid, "canonical_model": canonical,
                      "marca": pid.split(":")[0], "docs": docs[:6],
                      "n_docs": len(docs), "pista_legacy": pista or None,
                      "proxy_central_aparente": proxy_central})

    proxy = [d["id"] for d in diana if d["proxy_central_aparente"]]
    suelo = min(15, math.ceil(len(proxy) * 0.5)) if proxy else 1
    namespaces = Counter(d["marca"] for d in diana)
    n_docs_dist = Counter(min(d["n_docs"], 6) for d in diana)

    out = {
        "que_es": (f"B1 — diana de clasificación = vista {marca} "
                   "(_productos_marca, join redirect-normalizado) sin clasificacion."),
        "marca": marca,
        "derivacion": (f"len(_productos_marca(cat,'{marca}'))="
                       f"{len(vista)}; sin clasificacion={len(sin_clas)}; "
                       "docs por follow_redirect(pid) — todos con docs por construcción"),
        "total": len(diana),
        "namespaces": dict(namespaces),
        "n_docs_dist": {str(k): v for k, v in sorted(n_docs_dist.items())},
        "proxy_centrales_aparentes": {
            "declarado_como": "APUESTA por nombre/pista (el nombre engaña — principio "
                              "rector); solo fija el suelo del gate de efecto",
            "patron_familias_panel": patron or None,
            "patron_declarado": bool(patron),
            "n": len(proxy), "ids": proxy},
        "suelo_gate_efecto": {"formula": "min(15, ceil(proxy*0.5))", "valor": suelo,
                              "pre_registrado": "B1, antes de GT y de la pasada"},
        "detalle": diana,
    }
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{marca}] vista {len(vista)} · diana {len(diana)} · namespaces {dict(namespaces)}")
    if not patron:
        print("  AVISO: sin patrón de familias-panel declarado para esta marca — "
              "el proxy sólo lo alimenta la pista legacy y el SUELO del gate de "
              "efecto queda MÁS BAJO (gate más laxo). Declárelo con --familias-panel.")
    print(f"proxy centrales-aparentes {len(proxy)} → suelo gate efecto = {suelo}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
