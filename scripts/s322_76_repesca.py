# -*- coding: utf-8 -*-
"""s322 #76 — REPESCA de los 46 §1: el tope max_tokens=400 truncaba JSONs a
mitad (parse-fail → baja artificial; la CAD-150-4 de la query dorada entre
ellos). Re-llamada con 800, mismo prompt, misma verificación de citas. Las que
alcancen el CRITERIO EXACTO del §0 adjudicado (alta + citas verificadas) se
marcan §0-bis — reportadas a Alberto como extensión bajo su mismo criterio."""
from __future__ import annotations

import json
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

pob_path = ROOT / "evals" / "s322_76_poblacion_v1.json"
pob = json.loads(pob_path.read_text(encoding="utf-8"))
censo = {d["id"]: d for d in json.loads(
    (ROOT / "evals" / "s322_76_censo_diana_v1.json")
    .read_text(encoding="utf-8"))["detalle"]}

objetivo = [f for f in pob["detalle"]
            if not (f["llm"].get("confianza") == "alta"
                    and f.get("citas_verificadas"))]
cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                              timeout=120.0, max_retries=1)
repescadas = 0
with abierto(timeout=30.0) as c:
    for i, f in enumerate(objetivo):
        d = censo[f["id"]]
        trozos = []
        for sf in d["docs"][:3]:
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "content", "source_file": f"eq.{sf}",
                              "order": "chunk_index.asc", "limit": "3"})
            r.raise_for_status()
            trozos.append(f"[DOC: {sf}]\n" + "\n···\n".join(
                (x.get("content") or "")[:900] for x in r.json()))
            # v2: muestreo DIRIGIDO — los chunks que MENCIONAN la variante
            # (la CAD-150-4 no aparece en los primeros chunks del manual de
            # familia; su sección «de 4 y 8 lazos» vive más adentro).
            rv = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                       params={"select": "content",
                               "source_file": f"eq.{sf}",
                               "content": f"ilike.*{d['canonical_model']}*",
                               "order": "chunk_index.asc", "limit": "3"})
            if rv.status_code == 200 and rv.json():
                trozos.append(f"[DOC: {sf} — secciones que mencionan "
                              f"{d['canonical_model']}]\n" + "\n···\n".join(
                                  (x.get("content") or "")[:900]
                                  for x in rv.json()))
        muestra = "\n\n".join(trozos)[:9000]
        msg = cliente.messages.create(
            model=MODELO, max_tokens=800,   # el fix: 400 truncaba
            messages=[{"role": "user", "content": PROMPT.format(
                canonical=d["canonical_model"], pid=d["id"],
                muestra=muestra, pista=d.get("pista_legacy"))}])
        texto = "".join(b.text for b in msg.content
                        if getattr(b, "type", "") == "text").strip()
        try:
            v = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
        except Exception:                     # noqa: BLE001
            continue                          # sigue como estaba (§1)
        ml = muestra.lower()

        def _ok(cita):
            return bool(cita) and cita[:50].lower() in ml

        citas_ok = _ok(v.get("categoria_cita"))
        if v.get("tecnologia") and v.get("tecnologia") != "null":
            citas_ok = citas_ok and _ok(v.get("tecnologia_cita"))
        for lz in (v.get("lazos") or []):
            citas_ok = citas_ok and _ok(lz.get("cita"))
        if v.get("confianza") == "alta" and not citas_ok:
            v["confianza"] = "media"
        f["llm"] = v
        f["citas_verificadas"] = citas_ok
        f["repesca"] = "max_tokens 400->800"
        repescadas += 1
        if (i + 1) % 15 == 0:
            print(f"  {i+1}/{len(objetivo)}…", flush=True)
        time.sleep(0.2)

pob["repesca_utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
pob_path.write_text(json.dumps(pob, ensure_ascii=False, indent=1),
                    encoding="utf-8")
nuevos_altas = sum(1 for f in pob["detalle"]
                   if f.get("repesca") and f["llm"].get("confianza") == "alta"
                   and f.get("citas_verificadas"))
print(f"objetivo {len(objetivo)} · re-parseadas {repescadas} · "
      f"nuevas §0-bis (alta+citas) {nuevos_altas}")
