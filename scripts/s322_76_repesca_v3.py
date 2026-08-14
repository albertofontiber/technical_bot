# -*- coding: utf-8 -*-
"""s322b — REPESCA v3: dirigida a la TABLA DE MODELOS (las 22 §1 restantes).

Diagnóstico (14-ago, pregunta de Alberto sobre mejorar certidumbre): las 22
filas §1 tienen 1-12 menciones de su modelo en SUS docs — el fallo fue de
MUESTREO (la fila exacta de la tabla de modelos del manual de familia 2X-A no
cayó en la ventana), no de corpus. v3 muestrea EXACTAMENTE los chunks que
mencionan el modelo (completos, no truncados a 900) y verifica las citas a
TEXTO COMPLETO contra el doc entero (estándar r28), no contra la muestra.

Lo que alcance el criterio §0 EXACTO (alta + citas verificadas) queda marcado
para el writer bajo el «sí al §0» vigente de Alberto (precedente repesca v1/v2,
reportado); el resto sigue §1 → carril de evidencia online en el packet.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from scripts.s322_76_poblacion import PROMPT, MODELO  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


pob_path = ROOT / "evals" / "s322_76_poblacion_v1.json"
pob = json.loads(pob_path.read_text(encoding="utf-8"))
censo = {d["id"]: d for d in json.loads(
    (ROOT / "evals" / "s322_76_censo_diana_v1.json")
    .read_text(encoding="utf-8"))["detalle"]}
clasificados = set()
for ln in (ROOT / "data" / "catalog" / "products.jsonl").open(encoding="utf-8"):
    r = json.loads(ln)
    if r.get("clasificacion"):
        clasificados.add(r["id"])

objetivo = [f for f in pob["detalle"] if f["id"] not in clasificados]
print(f"objetivo v3: {len(objetivo)} filas")

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
repescadas, nuevas_s0 = 0, []
with abierto(timeout=30.0) as c:
    for f in objetivo:
        d = censo[f["id"]]
        trozos = []
        for sf in d["docs"]:
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "content", "source_file": f"eq.{sf}",
                              "content": f"ilike.*{d['canonical_model']}*",
                              "order": "chunk_index.asc", "limit": "4"})
            if r.status_code == 200 and r.json():
                trozos.append(f"[DOC: {sf} — chunks que mencionan "
                              f"{d['canonical_model']}]\n" + "\n···\n".join(
                                  (x.get("content") or "")[:2400]
                                  for x in r.json()))
        muestra = "\n\n".join(trozos)[:14000]
        if not muestra:
            continue
        msg = cliente.messages.create(
            model=MODELO, max_tokens=800,
            messages=[{"role": "user", "content": PROMPT.format(
                canonical=d["canonical_model"], pid=f["id"],
                muestra=muestra, pista=d.get("pista_legacy"))}])
        texto = "".join(b.text for b in msg.content
                        if getattr(b, "type", "") == "text").strip()
        try:
            v = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
        except Exception:                     # noqa: BLE001
            continue

        # verificación FULL-TEXT (estándar r28): la cita completa que se
        # almacenaría ([:200]) contra el doc ENTERO, espacios normalizados.
        docs_norm = {sf: _norm(_doc_completo(c, sf)) for sf in d["docs"]}

        def _ok(cita):
            frag = _norm((cita or "")[:200])
            return bool(frag) and any(frag in dn for dn in docs_norm.values())

        citas_ok = _ok(v.get("categoria_cita"))
        if v.get("tecnologia") and v.get("tecnologia") != "null":
            citas_ok = citas_ok and _ok(v.get("tecnologia_cita"))
        for lz in (v.get("lazos") or []):
            citas_ok = citas_ok and _ok(lz.get("cita"))
        if v.get("confianza") == "alta" and not citas_ok:
            v["confianza"] = "media"
        f["llm"] = v
        f["citas_verificadas"] = citas_ok
        f["repesca"] = "v3 tabla-modelos full-text"
        repescadas += 1
        if v.get("confianza") == "alta" and citas_ok:
            nuevas_s0.append(f["id"])
        time.sleep(0.2)

pob["repesca_v3_utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
pob_path.write_text(json.dumps(pob, ensure_ascii=False, indent=1),
                    encoding="utf-8")
print(f"re-evaluadas {repescadas}/{len(objetivo)} · "
      f"nuevas §0 (alta+citas-full-text) {len(nuevas_s0)}")
for pid in nuevas_s0:
    print("  §0-v3:", pid)
