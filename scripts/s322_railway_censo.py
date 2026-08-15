# -*- coding: utf-8 -*-
"""s322f — Censo SOLO-LECTURA de la configuración VIVA en Railway (worker).

Por qué existe: los flags de producción NO se infieren del código ni de la
memoria — se leen de Railway por API (patrón DEC-195). Esta herramienta deja el
censo en un recibo comparable entre sesiones, y comprueba de un vistazo:
  · que las vars RETIRADAS (DEC-210/211/219) siguen ausentes;
  · que las que MANDAN siguen puestas con el valor esperado;
  · el estado del último deployment.

SEGURIDAD: los VALORES solo se leen/serializan para la lista blanca de flags
conocidos (no secretos). De cualquier var con nombre sensible se registra
únicamente su PRESENCIA, jamás el valor.

Uso:  python scripts/s322_railway_censo.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402

RW = "https://backboard.railway.app/graphql/v2"
HR = {"Project-Access-Token": os.environ["RAILWAY_TOKEN"]}
SENSIBLES = ("TOKEN", "KEY", "SECRET", "PASSWORD", "DSN", "URL", "IDS")

# DEC-210/211/219: retiradas por Alberto — deben estar AUSENTES.
RETIRADAS = ["GENERATOR_PROMPT_VARIANT", "RERANK_TOP_K", "ENUNCIADOS_MULTIVECTOR",
             "HYQ_TABLE", "GENERATOR_FOLLOWUPS", "ANTI_DIAGRAM_INVENTION",
             "WIRING_TOPOLOGY_GUARD", "CONVERSATION_POLICY", "ORCHESTRATOR_PATH"]
# Las que MANDAN (valor esperado hoy; None = solo se comprueba presencia).
MANDAN = {"INTENT_LLM": "on", "GENERATOR_SELECTION_BLOCK": "on",
          "GENERATOR_DIRECT_FIRST": "on", "VISUAL_ASSETS_LISTING_GATE": "on",
          "CHUNKS_TABLE": "chunks_v2", "LLM_MAX_TOKENS": "8000",
          "EC_LEGAL_DISCLAIMER_SKIP": "on", "LLM_MODEL": None}


def gql(query: str, variables: dict | None = None) -> dict:
    r = httpx.post(RW, headers=HR,
                   json={"query": query, "variables": variables or {}},
                   timeout=30)
    r.raise_for_status()
    d = r.json()
    if "errors" in d:
        raise RuntimeError(json.dumps(d["errors"])[:400])
    return d["data"]


info = gql("query { projectToken { projectId environmentId } }")["projectToken"]
pid, eid = info["projectId"], info["environmentId"]
servicios = gql("""query($pid: String!) { project(id: $pid) {
  services { edges { node { id name
    deployments(first: 1) { edges { node { status createdAt } } } } } } } }""",
                {"pid": pid})["project"]["services"]["edges"]

recibo: dict = {
    "que_es": ("Censo vivo de Railway (worker): retiradas ausentes, las que "
               "mandan presentes, último deployment. Valores solo de flags "
               "no secretos."),
    "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    "servicios": {},
}
fallos: list[str] = []

for e in servicios:
    nombre, sid = e["node"]["name"], e["node"]["id"]
    vars_ = gql("""query($pid: String!, $eid: String!, $sid: String!) {
      variables(projectId: $pid, environmentId: $eid, serviceId: $sid) }""",
                {"pid": pid, "eid": eid, "sid": sid})["variables"]
    dep = [d["node"] for d in e["node"]["deployments"]["edges"]]
    ausentes = {k: (k not in vars_) for k in RETIRADAS}
    mandan = {}
    for k, esperado in MANDAN.items():
        vivo = vars_.get(k)
        mandan[k] = {"presente": k in vars_,
                     "valor": vivo if not any(s in k.upper() for s in SENSIBLES)
                     else "(no se registra)",
                     "coincide_esperado": (esperado is None or vivo == esperado)}
        if k not in vars_ or (esperado is not None and vivo != esperado):
            fallos.append(f"{nombre}:{k} esperado {esperado!r}, vivo {vivo!r}")
    for k, ok in ausentes.items():
        if not ok:
            fallos.append(f"{nombre}:{k} DEBERÍA estar retirada y sigue puesta")
    recibo["servicios"][nombre] = {
        "n_vars": len(vars_),
        "retiradas_ausentes": ausentes,
        "las_que_mandan": mandan,
        "otras_no_secretas": sorted(
            k for k in vars_
            if k not in RETIRADAS and k not in MANDAN
            and not any(s in k.upper() for s in SENSIBLES)),
        "n_con_nombre_sensible": sum(
            1 for k in vars_ if any(s in k.upper() for s in SENSIBLES)),
        "ultimo_deployment": dep[0] if dep else None,
    }
    print(f"== {nombre}: {len(vars_)} vars ==")
    print(f"   retiradas ausentes: {sum(ausentes.values())}/{len(RETIRADAS)}")
    print(f"   último deployment: "
          f"{dep[0]['status'] if dep else '—'} ({dep[0]['createdAt'] if dep else '—'})")

recibo["fallos"] = fallos
destino = ROOT / "evals" / "s322_railway_censo_v1.json"
destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                   encoding="utf-8")
print(f"\n{'OK — sin desviaciones' if not fallos else 'DESVIACIONES:'}")
for f in fallos:
    print("  ⚠", f)
print(f"recibo -> {destino}")
sys.exit(0 if not fallos else 1)
