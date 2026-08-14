# -*- coding: utf-8 -*-
"""s321 — Ejecuta las 2 adjudicaciones de Alberto (packet s318/s320, FYI 13-ago):

1. DP312x: 202503 → superseded con cadena a 202512 (packet §1, «SÍ, ejecuta»).
   Reversible; recibo con ambas filas ANTES/DESPUÉS (la promesa literal).
2. #71: EC_LEGAL_DISCLAIMER_SKIP=on en Railway worker (packet §3, adjudicado;
   DEC-208 — aparato protegido, el ON exigía exactamente esta adjudicación).

La verificación previa (recibo del scratchpad) mostró que las adjudicaciones
no habían llegado a los sistemas: los checkboxes eran la DECISIÓN; esto es la
ejecución con recibo.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=False)

from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
      "Content-Type": "application/json"}
RW = "https://backboard.railway.app/graphql/v2"
HR = {"Project-Access-Token": os.environ["RAILWAY_TOKEN"]}

recibo: dict = {"utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}

# ---- 1) DP312x ---------------------------------------------------------------
with abierto(timeout=15.0) as c:
    r = c.get(f"{SB}/rest/v1/documents", headers=HS,
              params={"select": "id,source_pdf_filename,status,"
                                "supersedes_id,superseded_by_id",
                      "source_pdf_filename": "ilike.*DP312x*"})
    r.raise_for_status()
    filas = {("202503" if "202503" in f["source_pdf_filename"] else "202512"): f
             for f in r.json()}
    assert set(filas) == {"202503", "202512"}, filas
    recibo["dp312x_antes"] = filas
    vieja, nueva = filas["202503"], filas["202512"]

    r = c.patch(f"{SB}/rest/v1/documents",
                headers={**HS, "Prefer": "return=representation"},
                params={"id": f"eq.{vieja['id']}"},
                json={"status": "superseded",
                      "superseded_by_id": nueva["id"]})
    r.raise_for_status()
    r = c.patch(f"{SB}/rest/v1/documents",
                headers={**HS, "Prefer": "return=representation"},
                params={"id": f"eq.{nueva['id']}"},
                json={"supersedes_id": vieja["id"]})
    r.raise_for_status()

    r = c.get(f"{SB}/rest/v1/documents", headers=HS,
              params={"select": "id,source_pdf_filename,status,"
                                "supersedes_id,superseded_by_id",
                      "source_pdf_filename": "ilike.*DP312x*"})
    r.raise_for_status()
    recibo["dp312x_despues"] = r.json()
print("DP312x: cadena aplicada")

# ---- 2) Railway EC_LEGAL_DISCLAIMER_SKIP=on ---------------------------------


def gql(query, variables=None):
    r = httpx.post(RW, headers=HR, json={"query": query,
                                         "variables": variables or {}},
                   timeout=30)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"])[:400])
    return data["data"]


info = gql("query { projectToken { projectId environmentId } }")["projectToken"]
servicios = gql("""query($pid: String!) {
  project(id: $pid) { services { edges { node { id name } } } } }""",
                {"pid": info["projectId"]})["project"]["services"]["edges"]
worker = next(e["node"]["id"] for e in servicios if e["node"]["name"] == "worker")
gql("""mutation($input: VariableUpsertInput!) { variableUpsert(input: $input) }""",
    {"input": {"projectId": info["projectId"],
               "environmentId": info["environmentId"],
               "serviceId": worker,
               "name": "EC_LEGAL_DISCLAIMER_SKIP", "value": "on"}})
vars_ = gql("""query($pid: String!, $eid: String!, $sid: String!) {
  variables(projectId: $pid, environmentId: $eid, serviceId: $sid) }""",
            {"pid": info["projectId"], "eid": info["environmentId"],
             "sid": worker})["variables"]
recibo["railway_ec_legal_disclaimer_skip"] = vars_.get("EC_LEGAL_DISCLAIMER_SKIP")
print("Railway: EC_LEGAL_DISCLAIMER_SKIP =",
      repr(recibo["railway_ec_legal_disclaimer_skip"]))

destino = ROOT / "evals" / f"s321_adjudicaciones_apply_{recibo['utc']}.json"
destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                   encoding="utf-8")
print(f"recibo -> {destino}")
