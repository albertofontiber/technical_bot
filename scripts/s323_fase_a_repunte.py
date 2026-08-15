# -*- coding: utf-8 -*-
"""s323 FASE A — repunte de las 49 entradas fantasma del doc_map (defecto VIVO #80).

Plan v2 + adenda r32 (`evals/s323_plan_80_81_v2.md`). Alcance ACOTADO a la clase que el
censo verificó con 13 controles negativos: `doc_map.document_id` apunta a una fila
`retired` con CERO chunks, mientras los chunks servidos cuelgan del id ACTIVO. Efecto
medido: `must_preserve.attest_identity` atesta False con el id realmente servido, así que
el anexo de obligaciones nunca actúa en esos manuales.

Acción: repuntar UN campo (`document_id` fantasma → activo), dejando `source_file` y las
entries intactos. NO se toca `documents` (la retirada ya está aplicada desde s65) y NO se
tocan las otras 11 no-activas (tienen filas rivales; repuntar duplicaría el id y el
validador lo rechaza).

Mecánica T3: baseline POR-ENTRY ejecutado → backup → escritura por la puerta gobernada →
baseline de nuevo → ABORT si alguna entry sigue sin atestar.

Uso:  python scripts/s323_fase_a_repunte.py [--aplicar]
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
import os
from src.http_pool import abierto
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl, load as cargar
from src.rag.must_preserve import attest_identity

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

ap = argparse.ArgumentParser(); ap.add_argument("--aplicar", action="store_true")
args = ap.parse_args(); modo = "aplicar" if args.aplicar else "dry-run"

las49 = {f["source_file"].lower(): f for f in json.loads(
    (ROOT / "evals" / "s322f_e1_colisiones_adjudicacion_v1.json")
    .read_text(encoding="utf-8"))["seccion_0_bloque"]}
doc_map = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")


def baseline(cat) -> dict:
    """attest_identity POR ENTRY con el id REALMENTE SERVIDO (el de los chunks).
    El v1 decía '191 medidos' cuando la sonda corría 49 atestaciones: aquí se
    ejecuta de verdad, una por entry."""
    ok = fail = 0
    detalle = []
    with abierto(timeout=30.0) as c:
        for dm in doc_map:
            if dm["source_file"].lower() not in las49:
                continue
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "document_id",
                              "source_file": f"eq.{dm['source_file']}", "limit": "1"})
            servido = (r.json() or [{}])[0].get("document_id") if r.status_code == 200 else None
            for e in dm.get("entries") or []:
                v = attest_identity(servido, [e["id"]], catalog=cat) if servido else False
                ok += bool(v); fail += (not v)
                detalle.append({"source_file": dm["source_file"], "entry": e["id"],
                                "id_servido": servido, "atesta": bool(v)})
    return {"entries": ok + fail, "atestan": ok, "fallan": fail, "detalle": detalle}


cat0 = cargar(CATALOG_DIR)
antes = baseline(cat0)
print(f"BASELINE por-entry ANTES: {antes['atestan']}/{antes['entries']} atestan "
      f"· fallan {antes['fallan']}")

backup, plan = [], []
with abierto(timeout=30.0) as c:
    for dm in doc_map:
        sf = dm["source_file"]
        if sf.lower() not in las49:
            continue
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "document_id", "source_file": f"eq.{sf}", "limit": "1"})
        activo = (r.json() or [{}])[0].get("document_id") if r.status_code == 200 else None
        if not activo or activo == dm["document_id"]:
            continue
        backup.append({"source_file": sf, "document_id_prev": dm["document_id"]})
        plan.append({"source_file": sf, "de": dm["document_id"], "a": activo,
                     "entries": len(dm.get("entries") or [])})
        if args.aplicar:
            dm["document_id"] = activo

print(f"{modo}: {len(plan)} entradas a repuntar · "
      f"{sum(p['entries'] for p in plan)} entries del catálogo afectadas")

despues = None
if args.aplicar and plan:
    write_jsonl("doc_map", doc_map)          # valida el conjunto (document_id único)
    despues = baseline(cargar(CATALOG_DIR))
    print(f"BASELINE por-entry DESPUÉS: {despues['atestan']}/{despues['entries']}")

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
recibo = {"que_es": __doc__.strip().splitlines()[0], "modo": modo, "utc": utc,
          "baseline_antes": {k: v for k, v in antes.items() if k != "detalle"},
          "baseline_despues": ({k: v for k, v in despues.items() if k != "detalle"}
                               if despues else None),
          "repuntadas": plan, "backup": backup,
          "detalle_antes": antes["detalle"],
          "detalle_despues": despues["detalle"] if despues else None}
(ROOT / "evals" / f"s323_fase_a_repunte_{modo}_{utc}.json").write_text(
    json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
if despues and despues["fallan"]:
    print(f"⚠ ABORT-WORTHY: {despues['fallan']} entries siguen sin atestar")
    sys.exit(1)
print("recibo escrito")
