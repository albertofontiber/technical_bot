#!/usr/bin/env python3
"""s80 — Runner del backfill de identidad de la SERIE FAAST LT-200 (3 QIGs core). Spec: evals/_s80_faast_backfill_spec.md.

NO es eval-inerte (a diferencia de s78): cambia product_model, que es GENERATOR-VISIBLE (generator.py:452) y
mueve la SELECCIÓN de retrieval (_filter_to_query_models). Por eso el guardarraíl NO es "eval idéntico" sino:
  (1) findability POSITIVO por el HANDLER real (lección #40), incluyendo los paths que PODRÍAN regresar
      (Morley/System Sensor FAAST LT-200, NFXI-ASD11, ES+EN), y
  (2) no-regresión NEGATIVO = re-run full test_bot_vs_gold (set-PASS superset-o-igual al baseline) bajo
      freeze-contract (DEC-021§F), + test LT-200/Xtralis (la familia ancha no debe empeorar).
GUARDARRAÍL OBLIGATORIO aparte (no en este script): regen de data/model_catalog.json + reload tras el apply
(DEFECTO-4: catálogo stale ASD11→Securiton). El regen es un cambio de CÓDIGO (PR→main→Railway), no de DB.

Fases (idénticas a s78, doc_selectors ahora EXPLÍCITO por fix — bite del dúo):
  inventory  — count-match real vs spec. Read-only. ABORTA si algún count != esperado.
  before     — snapshot por-fila (chunks + documents afectados) → JSON. Read-only(DB)+escribe snapshot. Es el rollback.
  apply      — APLICA los UPDATE (PATCH). DESTRUCTIVO → requiere `apply --confirmed` Y GO de Alberto.
  after      — from-value restante == 0 por fix (el to-value 'FAAST LT-200' YA existe en 6574 → contaminado, lección s78).
  rollback   — re-aplica el snapshot. `rollback <snapshot.json> --confirmed`.

Uso: python scripts/s80_faast_backfill.py [inventory|before|apply --confirmed|after|rollback <f> --confirmed]
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
CH = f"{SUPABASE_URL}/rest/v1/chunks_v2"
DOC = f"{SUPABASE_URL}/rest/v1/documents"
SNAP = ROOT / "evals" / "s80_faast_backfill_snapshot.json"

F6575_EN = "I56-6575-005_EN-FAAST-LT-200-Loop-QIG"
F6575_ES = "I56-6575-005_ES FAAST LT-200 Loop QIG"
F6577_EN = "I56-6577-006_EN Notifier FAAST LT-200 QIG"
F6577_ES = "I56-6577-006_ES FAAST Notifier LT-200 QIG"

# Cada fix: selectores chunks (con from-value = idempotente), campo, valor destino, conteo esperado (verificado vs DB
# s80), y doc_selectors EXPLÍCITO (None si no toca documents — patrón s78: documents solo para manufacturer).
FIXES = [
    {"id": "FX1", "field": "product_model", "to": "FAAST LT-200", "expect": 78,
     "selectors": [{"source_file": f"eq.{F6575_EN}", "product_model": "eq.LT-200"},
                   {"source_file": f"eq.{F6575_ES}", "product_model": "eq.LT-200"}],
     "doc_selectors": None},
    {"id": "FX2", "field": "manufacturer", "to": "Notifier", "expect": 41,
     "selectors": [{"source_file": f"eq.{F6575_ES}", "manufacturer": "eq.System Sensor"}],
     "doc_selectors": [{"source_pdf_filename": "ilike.*6575-005_ES*", "manufacturer": "eq.System Sensor"}]},
    {"id": "FX3", "field": "product_model", "to": "FAAST LT-200", "expect": 73,
     "selectors": [{"source_file": f"eq.{F6577_EN}", "product_model": "eq.ASD11"},
                   {"source_file": f"eq.{F6577_ES}", "product_model": "eq.ASD11"}],
     "doc_selectors": None},
]


def count(url, params):
    r = httpx.get(url, headers={**H, "Prefer": "count=exact"},
                  params={**params, "select": "id", "limit": "1"}, timeout=40)
    r.raise_for_status()
    return int(r.headers.get("content-range", "*/0").split("/")[-1])


def fetch(url, params, select):
    rows, off = [], 0
    while True:
        r = httpx.get(url, headers=H, params={**params, "select": select, "limit": "1000", "offset": str(off)}, timeout=60)
        r.raise_for_status(); b = r.json(); rows += b
        if len(b) < 1000: break
        off += 1000
    return rows


def patch_batched(url, selector, field, to, batch=10):
    """PATCH en lotes de 10 por id (timeout HNSW en chunks_v2; lección s78). Idempotente: el selector
    lleva el from-value, así que re-correr salta lo ya cambiado."""
    ids = [r["id"] for r in fetch(url, selector, "id")]
    for i in range(0, len(ids), batch):
        grp = ",".join(ids[i:i + batch])
        httpx.patch(url, headers={**H, "Prefer": "return=minimal"},
                    params={"id": f"in.({grp})"}, json={field: to}, timeout=120).raise_for_status()
    return len(ids)


def inventory():
    print("=== INVENTORY (count-match: real vs spec) ===")
    ok = True
    for f in FIXES:
        n = sum(count(CH, s) for s in f["selectors"])
        mark = "OK " if n == f["expect"] else "XX "
        ok = ok and n == f["expect"]
        print(f"  {mark}{f['id']:5} {f['field']:13} ->{f['to']:14} chunks={n} (esperado {f['expect']})")
        if f["doc_selectors"]:
            dn = sum(count(DOC, s) for s in f["doc_selectors"])
            print(f"        documents afectados: {dn}")
    print(f"\n{'TODOS los counts CUADRAN con el spec.' if ok else '!!! MISMATCH — abortar, revisar.'}")
    return 0 if ok else 1


def before():
    snap = {"ts": datetime.now(timezone.utc).isoformat(), "chunks": {}, "documents": {}}
    for f in FIXES:
        rows = []
        for s in f["selectors"]:
            rows += fetch(CH, s, "id,source_file,product_model,manufacturer")
        snap["chunks"][f["id"]] = rows
        if f["doc_selectors"]:
            drows = []
            for s in f["doc_selectors"]:
                drows += fetch(DOC, s, "id,source_pdf_filename,product_model,manufacturer")
            snap["documents"][f["id"]] = drows
        print(f"  {f['id']}: snapshot {len(snap['chunks'][f['id']])} chunks"
              + (f" + {len(snap['documents'].get(f['id'], []))} documents" if f["doc_selectors"] else ""))
    SNAP.write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nSnapshot -> {SNAP.relative_to(ROOT)}  (rollback = re-aplicar este JSON)")
    return 0


def apply(confirmed):
    if not confirmed:
        print("APPLY destructivo — requiere `apply --confirmed` Y GO explícito de Alberto. Abortado."); return 1
    if inventory() != 0:
        print("Inventory NO cuadra — apply abortado."); return 1
    if not SNAP.exists():
        print("Falta el before-snapshot — corre `before` primero. Abortado."); return 1
    for f in FIXES:
        n = 0
        for s in f["selectors"]:
            n += patch_batched(CH, s, f["field"], f["to"])
        if f["doc_selectors"]:
            for s in f["doc_selectors"]:  # documents: tabla pequeña sin índice vectorial, sin riesgo de timeout
                httpx.patch(DOC, headers={**H, "Prefer": "return=minimal"}, params=s,
                            json={f["field"]: f["to"]}, timeout=60).raise_for_status()
        print(f"  {f['id']} aplicado ({n} chunks en lotes de 10).")
    print("\nRECORDATORIO guardarraíl: regen de data/model_catalog.json + reload (PR→main→Railway), "
          "luego A/B (freeze-contract) + smoke por handler real de los paths COULD-regress.")
    return after()


def after():
    print("=== AFTER (from-value restante == 0 = todos cambiados) ===")
    ok = True
    for f in FIXES:
        n_from = sum(count(CH, s) for s in f["selectors"])
        mark = "OK " if n_from == 0 else "XX "
        ok = ok and n_from == 0
        print(f"  {mark}{f['id']:5} from-restante={n_from} (esperado 0; debía cambiar {f['expect']})")
    print("OK — todos los from-value a 0" if ok else "!!! quedan from-value sin cambiar")
    return 0 if ok else 1


def rollback(path, confirmed):
    if not confirmed:
        print("rollback requiere --confirmed. Abortado."); return 1
    snap = json.loads(Path(path).read_text(encoding="utf-8"))
    for fid, rows in snap["chunks"].items():
        for row in rows:
            httpx.patch(CH, headers={**H, "Prefer": "return=minimal"}, params={"id": f"eq.{row['id']}"},
                        json={"product_model": row["product_model"], "manufacturer": row["manufacturer"]}, timeout=60).raise_for_status()
    for fid, rows in snap.get("documents", {}).items():
        for row in rows:
            httpx.patch(DOC, headers={**H, "Prefer": "return=minimal"}, params={"id": f"eq.{row['id']}"},
                        json={"product_model": row["product_model"], "manufacturer": row["manufacturer"]}, timeout=60).raise_for_status()
    print(f"rollback aplicado desde {path}")
    return 0


def main():
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
    phase = sys.argv[1] if len(sys.argv) > 1 else "inventory"
    confirmed = "--confirmed" in sys.argv
    if phase == "inventory": return inventory()
    if phase == "before": return before()
    if phase == "apply": return apply(confirmed)
    if phase == "after": return after()
    if phase == "rollback": return rollback(sys.argv[2], confirmed)
    print(f"fase desconocida: {phase}"); return 1


if __name__ == "__main__":
    sys.exit(main())
