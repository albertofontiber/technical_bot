# -*- coding: utf-8 -*-
"""s322b — CENSO-EXTRA: los 2 kits Firebeam vendidos bajo Detnov.

El censo v1 filtró por prefijo de marca (detnov:/kidde:) y dejó fuera
firebeam:140kit160 y firebeam:70kit140, que SÍ aparecen en la vista de
inventario de Detnov (vendido_bajo) con 3 docs mapeados. Mismo pipeline y
mismo criterio §0 vigente (alta + citas verificadas FULL-TEXT); recibo
propio — el recibo del censo v1 no se muta (los recibos no se tocan).
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

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl  # noqa: E402
from scripts.s322_76_poblacion import PROMPT, MODELO  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
IDS = ["firebeam:140kit160", "firebeam:70kit140"]
PROV = ("s322-76 censo-extra firebeam (vendido_bajo Detnov; fuera del censo v1 "
        "por prefijo de marca); criterio §0 adjudicado por Alberto 14-ago "
        "(alta + citas verificadas full-text)")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


filas = _read_jsonl(CATALOG_DIR / "products.jsonl")
por_id = {r["id"]: r for r in filas}
doc_map = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")
docs_de: dict[str, list[str]] = {}
for dm in doc_map:
    for e in dm.get("entries") or ():
        docs_de.setdefault(e["id"], []).append(dm.get("source_file"))

doc_cache: dict[str, str] = {}


def _doc_completo(client, sf: str) -> str:
    if sf not in doc_cache:
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
        doc_cache[sf] = "\n".join(trozos)
    return doc_cache[sf]


cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                              timeout=120.0, max_retries=1)
resultado = []
with abierto(timeout=30.0) as c:
    for pid in IDS:
        fila = por_id[pid]
        if fila.get("clasificacion"):
            resultado.append({"id": pid, "estado": "ya clasificada"})
            continue
        canonical = fila.get("canonical_model") or pid
        docs = docs_de.get(pid, [])
        trozos = []
        for sf in docs:
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "content", "source_file": f"eq.{sf}",
                              "content": f"ilike.*{canonical}*",
                              "order": "chunk_index.asc", "limit": "4"})
            if r.status_code == 200 and r.json():
                trozos.append(f"[DOC: {sf} — chunks que mencionan {canonical}]\n"
                              + "\n···\n".join((x.get("content") or "")[:2400]
                                               for x in r.json()))
        if not trozos:            # fallback: inicio de cada doc
            for sf in docs:
                r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                          params={"select": "content",
                                  "source_file": f"eq.{sf}",
                                  "order": "chunk_index.asc", "limit": "3"})
                if r.status_code == 200:
                    trozos.append(f"[DOC: {sf}]\n" + "\n···\n".join(
                        (x.get("content") or "")[:1500] for x in r.json()))
        muestra = "\n\n".join(trozos)[:14000]
        msg = cliente.messages.create(
            model=MODELO, max_tokens=800,
            messages=[{"role": "user", "content": PROMPT.format(
                canonical=canonical, pid=pid, muestra=muestra,
                pista=fila.get("categoria"))}])
        texto = "".join(b.text for b in msg.content
                        if getattr(b, "type", "") == "text").strip()
        try:
            v = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
        except Exception:                     # noqa: BLE001
            resultado.append({"id": pid, "estado": "parse-fail"})
            continue
        docs_norm = {sf: _norm(_doc_completo(c, sf)) for sf in docs}

        def _doc_de(cita):
            frag = _norm((cita or "")[:200])
            if not frag:
                return None
            for sf, dn in docs_norm.items():
                if frag in dn:
                    return sf
            return None

        doc_cat = _doc_de(v.get("categoria_cita"))
        if v.get("confianza") != "alta" or not doc_cat:
            resultado.append({"id": pid, "estado": "NO alcanza §0 (queda §1)",
                              "llm": v})
            continue
        fila["clasificacion"] = {"categoria": v["categoria"],
                                 "cita": v["categoria_cita"][:200],
                                 "provenance": PROV}
        atributos = {}
        if v.get("tecnologia") not in (None, "null"):
            doc_t = _doc_de(v.get("tecnologia_cita"))
            if doc_t:
                atributos["tecnologia"] = [{"valor": v["tecnologia"],
                                            "doc": doc_t,
                                            "cita": v["tecnologia_cita"][:200]}]
        if atributos:
            fila["atributos"] = atributos
        resultado.append({"id": pid, "estado": "escrita",
                          "clasificacion": fila["clasificacion"],
                          "atributos": fila.get("atributos")})

write_jsonl("products", filas)
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s322_76_censo_extra_firebeam_v1.json").write_text(
    json.dumps({"que_es": __doc__.strip().splitlines()[0], "utc": utc,
                "resultado": resultado}, ensure_ascii=False, indent=1),
    encoding="utf-8")
for r in resultado:
    print(r["id"], "→", r["estado"],
          "·", (r.get("clasificacion") or {}).get("categoria", ""))
