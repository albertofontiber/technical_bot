# -*- coding: utf-8 -*-
"""s322b r28 — Retirada de la tecnología no anclada de kidde:2010-2-pak-rmsdk.

Hallazgo materializado de Sol M3 (verificación 50-chars vs almacenado 200):
la cita almacenada fusionaba dos bullets del datasheet y la palabra que
anclaría «analogica» («addressable») NO existe en el doc (0 hits de
addressable/direccionable/analog en 2010-2-pak-rmsdk-161721-es). El valor era
invención del LLM en la cola parafraseada → se RETIRA el atributo (la
clasificación `accesorio`, con cita verbatim verificada, se conserva).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402

filas = _read_jsonl(CATALOG_DIR / "products.jsonl")
retirado = None
for r in filas:
    if r["id"] != "kidde:2010-2-pak-rmsdk":
        continue
    at = r.get("atributos") or {}
    retirado = at.pop("tecnologia", None)
    if not at:
        r.pop("atributos", None)

assert retirado, "la fila objetivo no tenía tecnologia — ¿ya migrada?"
write_jsonl("products", filas)
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s322_76_fix_rmsdk_v1.json").write_text(
    json.dumps({"que_es": ("Retirada r28: tecnologia no anclada (cita "
                           "parafraseada por el LLM; el doc no contiene "
                           "addressable/direccionable/analog). Reversible."),
                "utc": utc, "retirado": retirado},
               ensure_ascii=False, indent=1), encoding="utf-8")
print("retirada tecnologia de kidde:2010-2-pak-rmsdk:",
      json.dumps(retirado, ensure_ascii=False)[:160])
