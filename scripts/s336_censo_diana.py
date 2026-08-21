# -*- coding: utf-8 -*-
"""s336 B1 — Censo de la DIANA de clasificación: la vista Notifier REAL.

La población se define POR EL JOIN DEL CÓDIGO (v3 §0, cierre de Sol2-3/Fable2-1:
mis cifras a mano mezclaban ids crudos con el join redirect-normalizado): se usa
`_productos_marca` — la MISMA función que sirve el inventario — y el lookup de
docs va SIEMPRE vía `follow_redirect` (el censo s322 usaba pid crudo; con
Detnov/Kidde no mordía, aquí sí). Solo lectura.

Además el recibo PRE-REGISTRA el suelo del gate de efecto (v3 §1.8, Fable2-3):
proxy de centrales-APARENTES por nombre/pista —declarado como APUESTA, el nombre
engaña por principio rector— y suelo = min(15, ceil(proxy·0,5)), fijado AQUÍ,
antes de la pasada, jamás ajustado después.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.bot.telegram_bot import _productos_marca  # noqa: E402 — EL join de la vista
from src.rag.catalog_store import load  # noqa: E402

cat = load()
con_docs: dict[str, list[str]] = {}
for dm in cat.doc_map:
    for e in dm.get("entries") or ():
        con_docs.setdefault(cat.follow_redirect(e["id"]), []).append(
            dm.get("source_file") or "")

vista = _productos_marca(cat, "notifier")
sin_clas = [p for p in vista if not p.get("clasificacion")]

_RX_CENTRAL_APARENTE = re.compile(
    r"\b(central|panel)\b", re.IGNORECASE)
_RX_FAMILIA_PANEL = re.compile(
    r"^(NFS|ID\d|AFP|NCA|AM\d|ONYX)", re.IGNORECASE)

diana = []
for p in sorted(sin_clas, key=lambda x: x["id"]):
    pid = p["id"]
    docs = con_docs.get(cat.follow_redirect(pid), [])
    assert docs, f"la vista garantiza docs y {pid} no tiene — join roto"
    pista = p.get("categoria") or ""
    canonical = p.get("canonical_model") or ""
    proxy_central = bool(_RX_CENTRAL_APARENTE.search(str(pista))
                         or _RX_FAMILIA_PANEL.match(canonical))
    diana.append({"id": pid, "canonical_model": canonical,
                  "marca": pid.split(":")[0], "docs": docs[:6],
                  "n_docs": len(docs), "pista_legacy": pista or None,
                  "proxy_central_aparente": proxy_central})

proxy = [d["id"] for d in diana if d["proxy_central_aparente"]]
suelo = min(15, math.ceil(len(proxy) * 0.5)) if proxy else 1
namespaces = Counter(d["marca"] for d in diana)
n_docs_dist = Counter(min(d["n_docs"], 6) for d in diana)

out = {
    "que_es": ("s336 B1 — diana de clasificación = vista Notifier "
               "(_productos_marca, join redirect-normalizado) sin clasificacion."),
    "derivacion": ("len(_productos_marca(cat,'notifier'))="
                   f"{len(vista)}; sin clasificacion={len(sin_clas)}; "
                   "docs por follow_redirect(pid) — todos con docs por construcción"),
    "total": len(diana),
    "namespaces": dict(namespaces),
    "n_docs_dist": {str(k): v for k, v in sorted(n_docs_dist.items())},
    "proxy_centrales_aparentes": {
        "declarado_como": "APUESTA por nombre/pista (el nombre engaña — principio "
                          "rector); solo fija el suelo del gate de efecto",
        "n": len(proxy), "ids": proxy},
    "suelo_gate_efecto": {"formula": "min(15, ceil(proxy*0.5))", "valor": suelo,
                          "pre_registrado": "B1, antes de GT y de la pasada"},
    "detalle": diana,
}
destino = ROOT / "evals" / "s336_censo_diana_v1.json"
destino.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"vista {len(vista)} · diana {len(diana)} · namespaces {dict(namespaces)}")
print(f"proxy centrales-aparentes {len(proxy)} → suelo gate efecto = {suelo}")
print(f"recibo -> {destino}")
