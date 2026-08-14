# -*- coding: utf-8 -*-
"""s322 #76 — Lazos por SUFIJO para la familia CAD-150 (regla de dominio
adjudicada por Alberto 14-ago: «en el caso de 8 lazos, siempre es hasta 8»).

Alcance ACOTADO: solo variantes CAD-150-N cuyo manual de familia está mapeado
y que NO tienen lazos anclados por cita verbatim (la -1/-2 ya los tienen del
contenido y se conservan). La «cita» declara EXPLÍCITAMENTE que es derivación
de regla, no verbatim — transparencia sobre el nivel de evidencia. Extender a
otras familias (2X-A F1/F2…) = por-familia con la misma regla, no un barrido.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402

RX = re.compile(r"^CAD-150-(\d+)(-PLUS)?$", re.IGNORECASE)
DOC = "55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT"
CITA = ("sufijo del modelo CAD-150-{n}: hasta {n} lazos (DERIVACION DE REGLA, "
        "no cita verbatim — regla de dominio adjudicada por Alberto 14-ago-2026: "
        "«N lazos» = «hasta N»)")

filas = _read_jsonl(CATALOG_DIR / "products.jsonl")
tocadas = []
for r in filas:
    if not r["id"].startswith("detnov:"):
        continue
    m = RX.match(r.get("canonical_model") or "")
    if not m or not r.get("clasificacion"):
        continue
    at = r.setdefault("atributos", {})
    if at.get("lazos"):
        continue                    # verbatim ya anclado: se conserva
    n = int(m.group(1))
    # sin `base`: el doc no declara dotación de serie — un base=1 inventado
    # sería un hecho falso indistinguible a máquina (dúo r28 Sol M2).
    at["lazos"] = [{"max": n, "doc": DOC, "cita": CITA.format(n=n)}]
    tocadas.append({"id": r["id"], "max": n})

write_jsonl("products", filas)
print(f"lazos-por-sufijo aplicados: {len(tocadas)} → "
      f"{[t['id'] for t in tocadas]}")
(ROOT / "evals" / "s322_76_sufijo_cad150_v1.json").write_text(
    json.dumps({"regla": "Alberto 14-ago: N lazos = hasta N",
                "tocadas": tocadas}, ensure_ascii=False, indent=1),
    encoding="utf-8")
