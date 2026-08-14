# -*- coding: utf-8 -*-
"""s322 #76 — RESCATE de las §0 saltadas por atribución corta.

Clase de fallo (recibo writer 160408Z): 12 filas alta+citas-verificadas
(§0, mismo criterio adjudicado) quedaron sin escribir con motivo «cita de
categoria no atribuible a doc». Causa raíz: `_contenido` del writer leía los
6 PRIMEROS chunks de cada doc, pero la repesca v2 verificó citas muestreadas
de secciones profundas (ilike sobre la variante). Este rescate re-atribuye
contra el doc COMPLETO — mismo criterio, misma verificación, sin relajar
nada: cita no encontrada en el doc entero → sigue saltada.
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
PROV = ("s322-76 poblacion fable-5 (+repescas v1-v3), gate GT PASS; criterio "
        "§0 adjudicado por Alberto 14-ago (alta + citas verificadas full-text); "
        "atribucion contra doc completo")

pob = json.loads((ROOT / "evals" / "s322_76_poblacion_v1.json")
                 .read_text(encoding="utf-8"))
bloque = [f for f in pob["detalle"]
          if f["llm"].get("confianza") == "alta" and f.get("citas_verificadas")]

contenido: dict[str, str] = {}


def _doc_completo(client, sf: str) -> str:
    if sf not in contenido:
        trozos, offset = [], 0
        while True:
            r = client.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                           params={"select": "content", "source_file": f"eq.{sf}",
                                   "order": "chunk_index.asc",
                                   "offset": str(offset), "limit": "100"})
            r.raise_for_status()
            lote = r.json()
            trozos.extend((x.get("content") or "") for x in lote)
            if len(lote) < 100:
                break
            offset += 100
        contenido[sf] = "\n".join(trozos).lower()
    return contenido[sf]


def _doc_de(client, docs: list[str], cita: str) -> str | None:
    # (r28 Sol M3) Se verifica la cita COMPLETA que se va a almacenar
    # ([:200]), no un prefijo de 50 — la cola podría ser texto del LLM que no
    # está en el doc. Espacios normalizados (los chunks se re-juntan con \n).
    import re as _re

    frag = _re.sub(r"\s+", " ", (cita or "")[:200].lower()).strip()
    if not frag:
        return None
    for sf in docs:
        doc = _re.sub(r"\s+", " ", _doc_completo(client, sf))
        if frag in doc:
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
            continue                      # ya escrita en pases previos
        doc_cat = _doc_de(client, f["docs"], v.get("categoria_cita"))
        if not doc_cat:
            saltadas.append({"id": f["id"],
                             "motivo": "cita no está NI en el doc completo"})
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

write_jsonl("products", filas)
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / f"s322_76_writer_rescate_{utc}.json").write_text(
    json.dumps({"que_es": "Rescate §0: atribución contra doc COMPLETO (clase "
                          "«no atribuible» del recibo 160408Z). Reversible.",
                "utc": utc, "escritas": len(escritas),
                "detalle": escritas, "saltadas": saltadas},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"rescatadas {len(escritas)} · irrecuperables {len(saltadas)}")
for s in saltadas:
    print("  aún saltada:", s["id"])
