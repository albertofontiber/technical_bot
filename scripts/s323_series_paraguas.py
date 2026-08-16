# -*- coding: utf-8 -*-
"""s323 — PROPUESTA de paraguas de SERIE + re-mapeo de los documentos de serie.

Hallazgo de Alberto (15-ago) revisando el §0.B: la «Guía de funcionamiento rápido de
la serie 2X-A» se asignaba a 2 productos de los 40 que tenemos de esa serie. Medido:
el documento NO nombra ni un modelo — solo «2X-A». Los 2 salían de la etiqueta de los
chunks, no del contenido.

Un documento de SERIE no pertenece a dos miembros elegidos al azar: pertenece a la
serie. El catálogo ya soporta ese concepto (`umbrellas.jsonl`, 21 vivos) pero no
existen `2X-A` ni `NC`.

NO APLICA NADA: emite la propuesta (paraguas + miembros + re-mapeo) para que Alberto
la firme, porque la pertenencia de 40 productos a un paraguas es exactamente lo que
debe ver antes de que esté vivo.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl

# series detectadas en los documentos del §0.B (prefijo -> regex de miembro)
SERIES = {
    "2X-A": re.compile(r"^2X-A", re.I),
    "NC": re.compile(r"^NC-", re.I),
}
products = _read_jsonl(CATALOG_DIR / "products.jsonl")
umbrellas = {u["termino"].upper() for u in _read_jsonl(CATALOG_DIR / "umbrellas.jsonl")}

propuesta = {"que_es": __doc__.strip().splitlines()[0], "paraguas": [], "notas": []}
for serie, rx in SERIES.items():
    if serie.upper() in umbrellas:
        propuesta["notas"].append(f"{serie}: YA existe como paraguas, no se propone")
        continue
    miembros = [r for r in products
                if rx.match(r.get("canonical_model") or "")
                and r.get("estado") == "activo" and not r.get("candidate")]
    # subfamilias: el sufijo distingue conducta (táctil AT, repetidor FR, teclado F)
    def _sub(m: str) -> str:
        u = m.upper()
        if u.startswith("2X-AT"):
            return "tactil (2X-AT)"
        if u.startswith("2X-AFR"):
            return "repetidor (2X-AFR)"
        if u.startswith("2X-AE"):
            return "evacuacion (2X-AE)"
        if u.startswith("2X-AF"):
            return "teclado (2X-AF)"
        return "otros"
    grupos: dict[str, list] = {}
    for r in miembros:
        grupos.setdefault(_sub(r["canonical_model"]), []).append(r["canonical_model"])
    propuesta["paraguas"].append({
        "termino": serie,
        "n_miembros": len(miembros),
        "ids": sorted(r["id"] for r in miembros),
        "subfamilias": {k: sorted(v) for k, v in sorted(grupos.items())},
        "aviso": ("OJO: las subfamilias NO son homogeneas para un documento de "
                  "OPERACION — el tactil, el repetidor y el de teclado tienen "
                  "interfaces distintas. Un documento de serie que describa UNA "
                  "interfaz no deberia expandirse a todas."),
    })
(ROOT / "evals" / "s323_series_paraguas_propuesta_v1.json").write_text(
    json.dumps(propuesta, ensure_ascii=False, indent=1), encoding="utf-8")
for p in propuesta["paraguas"]:
    print(f"{p['termino']}: {p['n_miembros']} miembros activos")
    for k, v in p["subfamilias"].items():
        print(f"   {k:<22} {len(v):>2} -> {', '.join(v[:5])}{' ...' if len(v) > 5 else ''}")
for n in propuesta["notas"]:
    print(" ", n)
