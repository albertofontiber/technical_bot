# -*- coding: utf-8 -*-
"""s321 E4 — Migra el seed FAMILY_REGISTRY al campo `clarify` de las umbrellas
ZXe/ZXSe, vía la puerta (write_jsonl valida el conjunto).

PROVENANCE SEPARADA por componente (dúo r26, Sol M1 — «datos T3» era falso):
- membresía/divergent: INTACTOS (ya adjudicados: gt-s78-morley + s90-alberto-qa).
- eje_terminos: GT s78/s79/s80 (memoria reference_morley_zx_rp1r) servido como
  seed en código desde s281; migrado s321-E4; adjudicación FORMAL del léxico
  pendiente (declarado — es el vocabulario que #76 tipará).
- variantes: NO se escriben — se derivan de los miembros en runtime.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402

EJE_LAZOS = [
    "cuántos lazos", "cuantos lazos", "número de lazos", "numero de lazos",
    "cuántos bucles", "cuantos bucles", "lazos y zonas",
    "cuántas zonas", "cuantas zonas", "número de zonas", "numero de zonas",
]
PROV = ("eje: GT s78/s79/s80 (memoria reference_morley_zx_rp1r), seed en "
        "código desde s281 (FAMILY_REGISTRY), migrado s321-E4; adjudicación "
        "formal del léxico PENDIENTE")

filas = _read_jsonl(CATALOG_DIR / "umbrellas.jsonl")
hechas = 0
for u in filas:
    if u.get("termino") in ("ZXe", "ZXSe") and u.get("tipo") == "familia":
        assert "clarify" not in u, f"ya migrada: {u['termino']}"
        u["clarify"] = {"eje_terminos": EJE_LAZOS, "provenance": PROV}
        hechas += 1
assert hechas == 2, f"esperaba 2 umbrellas familia ZXe/ZXSe, toqué {hechas}"
write_jsonl("umbrellas", filas)   # valida el conjunto entero
print(f"migradas {hechas} umbrellas (ZXe, ZXSe) — catálogo validado")
