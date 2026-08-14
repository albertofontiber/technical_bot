# -*- coding: utf-8 -*-
"""s322d — Cirugía FD2705 adjudicada por Alberto (14-ago, con el datasheet
FD2705R y el addendum en la mano): «la realidad es que son dos modelos:
FD2705R y FD2710R… y ambos son "Detector analógico lineal de humos por
barrera de rayos infrarrojos"». El «FD2705-10R» del doc_map/catálogo es un
ARTEFACTO del nombre de fichero.

Hace (gobernado, write_jsonl valida el conjunto, recibo reversible):
1. doc_map: la guía 22318.18.08 pasa de [aritech:fd2705-10r] a
   [aritech:fd2705r, aritech:fd2710r] (como YA está el addendum).
2. products: aritech:fd2705-10r → estado «retirado» con proveniencia.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402

PROV = ("adjudicado por Alberto 14-ago-2026 (s322d): FD2705-10R no existe como "
        "modelo — artefacto del nombre de fichero; la realidad son FD2705R y "
        "FD2710R (detector analógico lineal por barrera IR, 50 m / 100 m)")
DOC = "22318.18.08_-_aritech_ra_-_fd2705-10r_english_std_reflective_user_guide_-_en"

docs = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")
cambiado_docmap = False
for r in docs:
    if r.get("source_file") == DOC:
        assert [e["id"] for e in r["entries"]] == ["aritech:fd2705-10r"], r
        r["entries"] = [
            {"id": "aritech:fd2705r", "role": "primary", "scope": "doc",
             "provenance": PROV},
            {"id": "aritech:fd2710r", "role": "primary", "scope": "doc",
             "provenance": PROV},
        ]
        cambiado_docmap = True
assert cambiado_docmap, "doc 22318 no encontrado en doc_map"

products = _read_jsonl(CATALOG_DIR / "products.jsonl")
retirado = False
for r in products:
    if r["id"] == "aritech:fd2705-10r":
        assert r.get("estado") == "activo", r
        r["estado"] = "retirado"
        r["provenance"] = (r.get("provenance") or "") + " | " + PROV
        retirado = True
assert retirado, "aritech:fd2705-10r no encontrado"

write_jsonl("doc_map", docs)
write_jsonl("products", products)
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s322_e3_fd2705_catalogo_v1.json").write_text(
    json.dumps({"que_es": PROV, "utc": utc,
                "docmap": {DOC: ["aritech:fd2705r", "aritech:fd2710r"]},
                "retirado": "aritech:fd2705-10r",
                "reversible": "restaurar entry fd2705-10r y estado activo"},
               ensure_ascii=False, indent=1), encoding="utf-8")
print("doc_map 22318 → [fd2705r, fd2710r] · aritech:fd2705-10r → retirado · validado")
