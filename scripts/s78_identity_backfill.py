#!/usr/bin/env python3
"""s78 — Runner del backfill de identidad CAPA 1 (s64-style, guardarraíl-eado). Spec: _s78_identity_backfill_spec.md (v2 post-dúo).

Fases:
  inventory  — cuenta las filas afectadas por cada fix; DEBE == el conteo exacto del spec (count-match
               determinista = verificación de los WHERE). Read-only. ABORTA si algún count != esperado.
  before     — snapshot por-fila (id + valores actuales) de chunks_v2 Y documents afectados → JSON.
               Read-only (DB) + escribe el snapshot local. Es el rollback.
  apply      — APLICA los UPDATE (PATCH PostgREST). DESTRUCTIVO → requiere `apply --confirmed` Y GO de Alberto.
  after      — re-cuenta: to-value == esperado y from-value == 0 por fix.
  rollback   — re-aplica el snapshot (restaura valores previos). `rollback <snapshot.json> --confirmed`.

reach != PASS. El eval (test_bot_vs_gold) debe dar IDÉNTICO antes/después (correr aparte) — guardarraíl negativo.
Uso: python scripts/s78_identity_backfill.py [inventory|before|apply --confirmed|after|rollback <f> --confirmed]
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
SNAP = ROOT / "evals" / "s78_backfill_snapshot.json"

RP1R_SUPRA_DOCS = ["HLSI-MN-103_RP1r-Supra_lr", "HLSI-MN-103I_RP1r-Supra_lr",
                   "HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr", "HLSI-MA-103-I_GuiaRapida_RP1r-Supra_EN_lr"]
NFXI_ASD_DOCS = ["I56-3947-202_FAAST LT_MULTI", "I56-6577-006_ES FAAST Notifier LT-200 QIG",
                 "I56-6577-006_EN Notifier FAAST LT-200 QIG"]

# Cada fix: lista de SELECTORES (params PostgREST que incluyen el filtro from-value = idempotente),
# campo a cambiar, valor destino, conteo esperado (del spec verificado), y si toca documents.
FIXES = [
    {"id": "FIX1", "field": "manufacturer", "to": "Notifier", "expect": 312, "documents": True,
     "selectors": [{"source_file": f"eq.{d}", "manufacturer": "eq.Morley"} for d in RP1R_SUPRA_DOCS]},
    {"id": "FIX2", "field": "manufacturer", "to": "Notifier", "expect": 135, "documents": True,
     "selectors": [{"source_file": f"eq.{d}", "manufacturer": "eq.Securiton"} for d in NFXI_ASD_DOCS]},
    # FIX3 (MIE-MI-600 unknown->ZX1Se/ZX2Se/ZX5Se/ZX10Se, 88) y FIX6 (ZX2e/ZX5e->ZX1e/ZX2e/ZX5e, 207)
    # DIFERIDOS al ciclo de FINDABILITY: el tag combinado es dato correcto pero NO da findability sin
    # un split de etiquetas combinadas en build_model_catalog.py + regen (no eval-inerte). Ver el spec.
    {"id": "FIX4", "field": "product_model", "to": "NFXI-FLX", "expect": 83, "documents": False,
     "selectors": [{"source_file": "eq.A05-7030-000_B_ES_Notifier FAAST FLEX Addressable", "product_model": "eq.unknown"}]},
    {"id": "FIX5a", "field": "product_model", "to": "ZX50", "expect": 126, "documents": False,
     "selectors": [{"product_model": "eq.ZX-50"}]},
    {"id": "FIX5b", "field": "product_model", "to": "ZXR50A/ZXR50P", "expect": 18, "documents": False,
     "selectors": [{"product_model": "eq.ZXr-A/ZXr-P"}]},
    # (FIX6 ZX2e/ZX5e->ZX1e/ZX2e/ZX5e → ciclo findability, ver nota arriba)
    {"id": "FIX5d", "field": "product_model", "to": "RP1r", "expect": 65, "documents": False,
     "selectors": [{"product_model": "eq.RP1R"}]},
]


def count(url, params):
    r = httpx.get(url, headers={**H, "Prefer": "count=exact"}, params={**params, "select": "id", "limit": "1"}, timeout=40)
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
    """PATCH en lotes pequeños por id. chunks_v2 tiene índice vectorial HNSW: un UPDATE masivo
    re-inserta cada fila en el grafo -> 'statement timeout' (cazado en el 1er intento, 190 filas).
    Lotes de 10 quedan bajo el timeout. Idempotente: el selector lleva el from-value, así que
    re-correr salta lo ya cambiado."""
    ids = [r["id"] for r in fetch(url, selector, "id")]
    for i in range(0, len(ids), batch):
        grp = ",".join(ids[i:i + batch])
        httpx.patch(url, headers={**H, "Prefer": "return=minimal"},
                    params={"id": f"in.({grp})"}, json={field: to}, timeout=120).raise_for_status()
    return len(ids)


def doc_selectors(fix):
    # documents: match por source_pdf_filename ilike *doc* + manufacturer from-value
    frm = fix["selectors"][0]["manufacturer"].split(".")[1]  # 'Morley'/'Securiton'
    docs = RP1R_SUPRA_DOCS if fix["id"] == "FIX1" else NFXI_ASD_DOCS
    return [{"source_pdf_filename": f"ilike.*{d}*", "manufacturer": f"eq.{frm}"} for d in docs]


def inventory():
    print("=== INVENTORY (count-match: real vs spec) ===")
    ok = True
    for f in FIXES:
        n = sum(count(CH, s) for s in f["selectors"])
        mark = "OK " if n == f["expect"] else "XX "
        ok = ok and n == f["expect"]
        print(f"  {mark}{f['id']:6} {f['field']:13} ->{f['to']:16} chunks={n} (esperado {f['expect']})")
        if f["documents"]:
            dn = sum(count(DOC, s) for s in doc_selectors(f))
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
        if f["documents"]:
            drows = []
            for s in doc_selectors(f):
                drows += fetch(DOC, s, "id,source_pdf_filename,product_model,manufacturer")
            snap["documents"][f["id"]] = drows
        print(f"  {f['id']}: snapshot {len(snap['chunks'][f['id']])} chunks"
              + (f" + {len(snap['documents'].get(f['id'],[]))} documents" if f["documents"] else ""))
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
        if f["documents"]:
            for s in doc_selectors(f):  # documents: tabla pequeña sin índice vectorial, sin riesgo
                httpx.patch(DOC, headers={**H, "Prefer": "return=minimal"}, params=s,
                            json={f["field"]: f["to"]}, timeout=60).raise_for_status()
        print(f"  {f['id']} aplicado ({n} chunks en lotes de 10).")
    return after()


def after():
    # Señal FIABLE = from-value restante == 0 (todos cambiados). El to-value NO sirve como check
    # cuando el destino ya existía (canonicalizaciones: ZX50/ZXR50A-P/RP1r ya tenían chunks) -> contaminado.
    print("=== AFTER (from-value restante == 0 = todos cambiados) ===")
    ok = True
    for f in FIXES:
        n_from = sum(count(CH, s) for s in f["selectors"])
        mark = "OK " if n_from == 0 else "XX "
        ok = ok and n_from == 0
        print(f"  {mark}{f['id']:6} from-restante={n_from} (esperado 0; debía cambiar {f['expect']})")
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
                        json={"manufacturer": row["manufacturer"]}, timeout=60).raise_for_status()
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
