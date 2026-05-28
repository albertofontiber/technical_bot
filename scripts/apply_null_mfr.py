#!/usr/bin/env python3
"""Aplica las atribuciones de #6 a CHUNKS_TABLE desde el artefacto REFINADO
(scripts/refine_null_mfr_review.py) + las 15 resoluciones manuales de Alberto.

Escribe SOLO:
  - manufacturer (nivel documento, filas con manufacturer IS NULL)
  - product_model (solo si la corrección procede: current_model_ok=false o NULL,
    un único valor actual, modelo propuesto real) — acotado al valor viejo
  - documents.manufacturer (consistencia)

Dry-run por defecto (muestra el plan, NO escribe). --apply escribe, con un
snapshot de rollback del bucket entero (id, manufacturer, product_model) antes.

Idempotente: el filtro manufacturer=is.null / product_model=eq.<viejo> no
re-matchea lo ya aplicado.

Uso:
    $env:CHUNKS_TABLE='chunks_v2'; python scripts/apply_null_mfr.py            # dry-run
    $env:CHUNKS_TABLE='chunks_v2'; python scripts/apply_null_mfr.py --apply
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"), override=True)
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
TABLE = os.environ.get("CHUNKS_TABLE", "chunks")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
H_WRITE = {**H, "Content-Type": "application/json", "Prefer": "return=minimal"}

# Resoluciones humanas de los 15 desacuerdos Haiku/docX (Alberto, sesión #6).
MANUAL_RESOLUTIONS = {
    "D716 issue 1 - M700KAC-KACI_Eng": "Notifier",
    "F5K-2H-UserGuide-SPANISH_Manual F5000": "Morley",
    "FAAST-LT-Como-obtener-el-historico-del-equipo": "Notifier",
    "HLSI-MI-580I": "Morley",
    "Manual_DXD-2X0A (55321013 MI 606 m 2024 b)": "Detnov",
    "PUL-DEXT_Instrucciones multi": "Notifier",
    "PUL-PEXT_Instrucciones multi": "Notifier",
    "ASD Cold Environments_SP": "Notifier",
    "FAAST-LT-Como-comunicar-con-el-equipo": "Notifier",
    "I56-6574-005_EN-HS-Stand-Alone-FAAST-LT-200-QIG": "Notifier",
    "I56-6574-005_ES -HS Stand Alone FAAST LT-200 QIG": "Notifier",
    "I56-6575-005_EN-FAAST-LT-200-Loop-QIG": "Notifier",
    "NFS-SUPRA-VSN2-PLUS-Entrada-Digital": "Notifier",
    "UCIP-Conectar-con-equipo-via-IP": "Morley",
    "VSN4-PLUS_ITA": "Morley",
}


def final_for(e: dict) -> str | None:
    if e["action"] == "manual":
        return MANUAL_RESOLUTIONS.get(e["source_file"])
    return e.get("final_manufacturer")


def is_clean_model(pm: str | None) -> bool:
    """¿Parece un CÓDIGO de modelo (no una frase/descripción/lista multi-modelo)?
    El dry-run reveló que Haiku a veces propone frases ('Centrales de Incendios
    Convencionales de 1,2 y 4 Zonas') o listas ('NFS Supra / VSN-Plus2 / ...').
    Esas NO deben escribirse como product_model (contaminarían el catálogo)."""
    if not pm or pm.strip().lower() == "unknown":
        return False
    pm = pm.strip()
    if len(pm) > 25:
        return False
    if pm.count("/") > 1 or " / " in pm:   # lista multi-modelo
        return False
    if "," in pm:                          # frase
        return False
    if len(pm.split()) > 4:                # descripción
        return False
    return True


def pm_correction(e: dict) -> tuple[str, str] | None:
    """(old_pm, new_pm) si procede corregir product_model, o None.
    Código limpio → se usa; basura/frase/multi-modelo → 'unknown' (excluido del
    catálogo). No-op si el target coincide con el valor actual."""
    cur = e.get("current_product_models") or []
    new = e.get("proposed_product_model")
    needs = e.get("current_model_ok") is False or (len(cur) == 1 and cur[0] == "NULL")
    if not (needs and len(cur) == 1):
        return None
    target = new if is_clean_model(new) else "unknown"
    if target == cur[0]:
        return None
    return cur[0], target


def snapshot_bucket(ts: str) -> str:
    rows: list[dict] = []
    offset = 0
    while True:
        r = httpx.get(f"{URL}/rest/v1/{TABLE}", headers=H, params={
            "manufacturer": "is.null",
            "select": "id,manufacturer,product_model,source_file",
            "order": "id", "limit": "1000", "offset": str(offset)}, timeout=30.0)
        r.raise_for_status()
        b = r.json()
        rows.extend(b)
        if len(b) < 1000:
            break
        offset += 1000
    path = os.path.join(ROOT, "logs", f"null_mfr_rollback_{ts}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(rows, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return path, len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("artifact", nargs="?")
    args = ap.parse_args()

    path = args.artifact or max(
        glob.glob(os.path.join(ROOT, "logs", "null_mfr_refined_*.json")), key=os.path.getmtime)
    refined = json.load(open(path, encoding="utf-8"))
    print(f"== apply_null_mfr · tabla='{TABLE}' · {'APPLY' if args.apply else 'DRY-RUN'} ==")
    print(f"   artefacto: {os.path.basename(path)}\n")

    plan: list[dict] = []
    skipped: list[str] = []
    for e in refined:
        mfr = final_for(e)
        if not mfr:
            skipped.append(e["source_file"])
            continue
        plan.append({"source_file": e["source_file"], "document_id": e.get("document_id"),
                     "mfr": mfr, "pm": pm_correction(e)})

    by_mfr = Counter(p["mfr"] for p in plan)
    pm_real = [p for p in plan if p["pm"] and p["pm"][1] != "unknown"]
    pm_unk = [p for p in plan if p["pm"] and p["pm"][1] == "unknown"]
    print(f"docs a actualizar: {len(plan)}  | sin marca (skip): {len(skipped)}")
    print(f"manufacturer a escribir: {dict(by_mfr.most_common())}")
    print(f"product_model: {len(pm_real)} → modelo limpio · {len(pm_unk)} → unknown (basura, excluida del catálogo)")
    if skipped:
        print(f"SKIP (sin marca resuelta): {skipped[:10]}")
    print("\nMuestra correcciones a MODELO LIMPIO (15):")
    for p in pm_real[:15]:
        print(f"  {p['source_file'][:38]:<38} [{p['mfr']}] {p['pm'][0]} -> {p['pm'][1]}")
    print("\nMuestra a UNKNOWN (basura detectada, 12):")
    for p in pm_unk[:12]:
        print(f"  {p['source_file'][:38]:<38} {p['pm'][0]!r} -> unknown")

    if not args.apply:
        print("\n(dry-run — nada escrito. Re-ejecuta con --apply)")
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap_path, n_snap = snapshot_bucket(ts)
    print(f"\nRollback snapshot: {n_snap} chunks -> {snap_path}\n")

    ok, fail = 0, 0
    failures: list[tuple[str, str]] = []
    for i, p in enumerate(plan, 1):
        s = p["source_file"]
        try:
            httpx.patch(f"{URL}/rest/v1/{TABLE}", headers=H_WRITE,
                        params={"source_file": f"eq.{s}", "manufacturer": "is.null"},
                        json={"manufacturer": p["mfr"]}, timeout=30.0).raise_for_status()
            if p["pm"]:
                old_pm, new_pm = p["pm"]
                pmf = {"product_model": "is.null"} if old_pm == "NULL" else {"product_model": f"eq.{old_pm}"}
                httpx.patch(f"{URL}/rest/v1/{TABLE}", headers=H_WRITE,
                            params={"source_file": f"eq.{s}", **pmf},
                            json={"product_model": new_pm}, timeout=30.0).raise_for_status()
            if p["document_id"]:
                httpx.patch(f"{URL}/rest/v1/documents", headers=H_WRITE,
                            params={"id": f"eq.{p['document_id']}"},
                            json={"manufacturer": p["mfr"]}, timeout=30.0)
            ok += 1
        except Exception as ex:
            fail += 1
            failures.append((s, str(ex)[:120]))
        if i % 50 == 0:
            print(f"  ...{i}/{len(plan)} (ok={ok} fail={fail})")

    print(f"\nAplicadas: {ok}  | fallos: {fail}")
    for s, err in failures:
        print(f"  FAIL {s}: {err}")
    print(f"Rollback disponible en {snap_path}")


if __name__ == "__main__":
    main()
