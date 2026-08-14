# -*- coding: utf-8 -*-
"""s322 #76 — WRITER del §0 (adjudicado por Alberto: «sí al §0», 14-ago).

Escribe clasificacion+atributos de las 114 filas alta+citas-verificadas al
catálogo, vía write_jsonl (valida el conjunto). Cada valor de atributo lleva
su {doc, cita}: la atribución POR-DOC se resuelve verificando la cita contra
el contenido real de cada doc del producto (el punto del esquema multi-fuente
r27). Cita no atribuible a ningún doc → la fila SE SALTA a recibo (jamás se
escribe con atribución inventada). Recibo completo + reversible (las filas
previas no tenían clasificacion: rollback = quitarla).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
PROV = ("s322-76 poblacion fable-5, gate GT 19/19 PASS "
        "(evals/s322_76_gate_gt_v1.json); §0 adjudicado por Alberto 14-ago")

pob = json.loads((ROOT / "evals" / "s322_76_poblacion_v1.json")
                 .read_text(encoding="utf-8"))
bloque = [f for f in pob["detalle"]
          if f["llm"].get("confianza") == "alta" and f.get("citas_verificadas")]

contenido_doc: dict[str, str] = {}


def _contenido(client, sf: str) -> str:
    if sf not in contenido_doc:
        r = client.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                       params={"select": "content", "source_file": f"eq.{sf}",
                               "order": "chunk_index.asc", "limit": "6"})
        r.raise_for_status()
        contenido_doc[sf] = "\n".join((x.get("content") or "")
                                      for x in r.json()).lower()
    return contenido_doc[sf]


def _doc_de(client, docs: list[str], cita: str) -> str | None:
    frag = (cita or "")[:50].lower()
    if not frag:
        return None
    for sf in docs:
        if frag in _contenido(client, sf):
            return sf
    return None


filas = _read_jsonl(CATALOG_DIR / "products.jsonl")
por_id = {r["id"]: r for r in filas}
escritas, saltadas = [], []

with abierto(timeout=30.0) as client:
    for f in bloque:
        v = f["llm"]
        fila = por_id.get(f["id"])
        if fila is None or fila.get("clasificacion"):
            saltadas.append({"id": f["id"], "motivo": "ausente o ya clasificada"})
            continue
        doc_cat = _doc_de(client, f["docs"], v.get("categoria_cita"))
        if not doc_cat:
            saltadas.append({"id": f["id"],
                             "motivo": "cita de categoria no atribuible a doc"})
            continue
        fila["clasificacion"] = {"categoria": v["categoria"],
                                 "cita": v["categoria_cita"][:200],
                                 "provenance": PROV}
        atributos = {}
        if v.get("tecnologia") not in (None, "null"):
            doc_t = _doc_de(client, f["docs"], v.get("tecnologia_cita"))
            if doc_t:
                atributos["tecnologia"] = [{"valor": v["tecnologia"],
                                            "doc": doc_t,
                                            "cita": v["tecnologia_cita"][:200]}]
        lazos = []
        for lz in (v.get("lazos") or []):
            doc_l = _doc_de(client, f["docs"], lz.get("cita"))
            if doc_l and isinstance(lz.get("base"), int):
                lazos.append({"base": lz["base"],
                              "max": lz.get("max", lz["base"]),
                              "doc": doc_l, "cita": lz["cita"][:200]})
        if lazos:
            atributos["lazos"] = lazos
        if atributos:
            fila["atributos"] = atributos
        escritas.append({"id": f["id"],
                         "clasificacion": fila["clasificacion"],
                         "atributos": fila.get("atributos")})

write_jsonl("products", filas)   # valida el conjunto ENTERO
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
recibo = {"que_es": "Writer §0 #76 (adjudicado). Reversible: rollback = quitar clasificacion/atributos de los ids listados.",
          "utc": utc, "bloque": len(bloque), "escritas": len(escritas),
          "saltadas": saltadas, "detalle": escritas}
(ROOT / "evals" / f"s322_76_writer_{utc}.json").write_text(
    json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"bloque {len(bloque)} · escritas {len(escritas)} · "
      f"saltadas {len(saltadas)} — catálogo validado")
