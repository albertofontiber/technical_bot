# -*- coding: utf-8 -*-
"""s322b r28 — RE-VERIFICACIÓN a texto COMPLETO de toda cita almacenada.

Dúo r28 (Sol M3): el writer original atribuía verificando los primeros 50
chars de la cita pero almacenaba hasta 200 — la cola podía ser texto del LLM
no presente en el doc. Este script verifica CADA cita almacenada en el
catálogo (clasificacion.cita contra cualquiera de los docs del producto;
atributos[*].cita contra SU doc atribuido) usando el texto completo
almacenado, con espacios normalizados (los chunks se re-juntan con \\n).
Las derivaciones de regla DECLARADAS (cita que anuncia «DERIVACION DE REGLA»)
se listan aparte — no son verbatim por diseño y así lo dicen.

Solo LEE y emite recibo; cualquier fallo se reporta para corrección explícita
(jamás se recorta/reescribe una cita en silencio).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


contenido: dict[str, str] = {}


def _doc_norm(client, sf: str) -> str:
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
        contenido[sf] = _norm("\n".join(trozos))
    return contenido[sf]


filas = _read_jsonl(CATALOG_DIR / "products.jsonl")

# docs por producto vía doc_map (la fuente gobernada, no el censo)
doc_map = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")
redirects = {r["id"]: r.get("redirect_to") for r in filas if r.get("redirect_to")}


def _resuelve(pid: str) -> str:
    visto = set()
    while pid in redirects and pid not in visto:
        visto.add(pid)
        pid = redirects[pid]
    return pid


docs_de: dict[str, set[str]] = {}
for dm in doc_map:
    sf = dm.get("source_file")
    for e in dm.get("entries") or ():
        docs_de.setdefault(_resuelve(e["id"]), set()).add(sf)

ok, derivadas, fallos = 0, [], []
with abierto(timeout=30.0) as client:
    for r in filas:
        pid = r["id"]
        cl = r.get("clasificacion")
        if cl:
            cita = _norm(cl.get("cita"))
            if "derivacion de regla" in cita:
                derivadas.append({"id": pid, "campo": "clasificacion"})
            elif any(cita in _doc_norm(client, sf)
                     for sf in sorted(docs_de.get(pid, ()))):
                ok += 1
            else:
                fallos.append({"id": pid, "campo": "clasificacion",
                               "cita": cl.get("cita")})
        for clave, valores in (r.get("atributos") or {}).items():
            for v in valores if isinstance(valores, list) else ():
                cita = _norm(v.get("cita"))
                if "derivacion de regla" in cita:
                    derivadas.append({"id": pid, "campo": clave})
                    continue
                sf = v.get("doc")
                if sf and cita and cita in _doc_norm(client, sf):
                    ok += 1
                else:
                    fallos.append({"id": pid, "campo": clave, "doc": sf,
                                   "cita": v.get("cita")})

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s322_76_verifica_citas_v1.json").write_text(
    json.dumps({"que_es": ("Re-verificación r28 a texto completo de toda cita "
                           "almacenada (Sol M3: el writer verificaba 50 chars "
                           "y almacenaba 200)."),
                "utc": utc, "verificadas_ok": ok,
                "derivadas_declaradas": derivadas, "fallos": fallos},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"citas OK {ok} · derivadas-declaradas {len(derivadas)} · "
      f"FALLOS {len(fallos)}")
for f in fallos[:20]:
    print("  FALLO:", f["id"], f["campo"], "→", (f.get("cita") or "")[:70])
