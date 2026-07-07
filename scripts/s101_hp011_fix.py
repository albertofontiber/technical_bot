#!/usr/bin/env python3
"""s101_hp011_fix.py — fix puntual de OCR 7-segmentos en el corpus (hp011): 'r.5'→'r.S' (r.1 REVERTIDO s101: adjudicación corregida rI).

Ground-truth: adjudicación de Alberto s101 (CORRIGE la s30; `feedback_7segment_reading`, vía tabla
clara de MNDT102 — SIN unir familias de producto, solo el glifo). Esquema MNEMÓNICO de parámetros:
  - fila "Rearme inhibido tras extinción": **rI** (Rearme Inhibido) → el corpus 'r.i' era CORRECTO;
    el fix r.i→r.1 del primer apply fue REVERTIDO; el error era del GOLD hp011 (corregido a 'r.I').
  - fila "Retardo de sirenas / Sounders delay": **rS** (Retardo Sirenas; no '5', sesgo 5↔S) → r.S APLICADO.
3 chunks afectados (HLSI-MN-103 ES ×2 + HLSI-MN-103I EN ×1, todos p63, 1 ocurrencia de cada glifo).

Diseño (patrón s80 backfill): content-only (SIN re-embed — Δ2 chars/~2000 = coseno negligible;
re-embed arriesga mismatch de receta B7), snapshot pre-guardado, reversible. Enunciados A3
verificados limpios (0 filas con 'r.i'). NO toca 't.H vs t.A' (misma clase OCR, sin adjudicación).

Uso:
  python scripts/s101_hp011_fix.py apply      # aplica (verifica 1-ocurrencia antes, relee después)
  python scripts/s101_hp011_fix.py verify     # solo lee el estado actual de los 3 chunks
  python scripts/s101_hp011_fix.py rollback   # restaura el content EXACTO del snapshot
Snapshot: evals/s100_hp011_ocr_snapshot.json (content original íntegro de los 3 chunks).
"""
from __future__ import annotations
import os, sys, json, re
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

import httpx
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

SNAP = ROOT / "evals" / "s100_hp011_ocr_snapshot.json"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
     "Content-Type": "application/json"}


def _get(ids):
    q = ",".join(f'"{i}"' for i in ids)
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
                  params={"select": "id,source_file,page_number,content", "id": f"in.({q})"}, timeout=30)
    r.raise_for_status()
    return r.json()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    ids = [c["id"] for c in snap]

    # glifos adjudicados: (patrón_mal, texto_bien). El patrón exige el contexto 'showing "…"'
    # para no tocar NADA fuera del display transcrito (p.ej. rangos numéricos como '05 a 295').
    # s101-corrección: r.i es CORRECTO (rI mnemónico) → SOLO queda el fix de rS. Si un apply viejo
    # dejó 'r.1', se revierte a 'r.i' (idempotente en ambas direcciones de la corrección).
    FIXES = [(r'showing "r\.1"', 'showing "r.i"'),
             (r'showing "r\.5"', 'showing "r.S"')]

    if mode == "verify":
        for c in _get(ids):
            state = {pat: len(re.findall(pat, c["content"])) for pat, _ in FIXES}
            fixed = {rep: rep.split('"')[1] in c["content"] for _, rep in FIXES}
            print(f"{c['id'][:12]} [{c['source_file'][:28]} p{c['page_number']}]: mal={state} bien={fixed}")
        return 0

    if mode == "apply":
        live = {c["id"]: c for c in _get(ids)}
        for c in snap:
            cur = live[c["id"]]["content"]
            new = cur
            for pat, rep in FIXES:
                occ = len(re.findall(pat, new))
                if occ == 0:
                    continue                     # ya aplicado o ausente en esta copia
                assert occ == 1, f"{c['id']}: {pat} esperaba 1 ocurrencia, hay {occ} — ABORT"
                new = re.sub(pat, rep, new, count=1)
            if new == cur:
                print(f"{c['id'][:12]}: sin cambios (ya aplicado)")
                continue
            r = httpx.patch(f"{SUPABASE_URL}/rest/v1/chunks_v2?id=eq.{c['id']}", headers=H,
                            json={"content": new}, timeout=30)
            assert r.status_code in (200, 204), f"{c['id']}: PATCH {r.status_code}"
            print(f"{c['id'][:12]}: PATCH OK")
        print("--- verificación post-apply ---")
        ok = True
        for c in _get(ids):
            good = all(not re.search(pat, c["content"]) for pat, _ in FIXES)
            ok &= good
            print(f"{c['id'][:12]}: {'VERIFICADO' if good else 'PROBLEMA'}")
        print("RESULTADO:", "OK aplicado y verificado" if ok else "XX revisar")
        return 0 if ok else 1

    if mode == "rollback":
        for c in snap:
            r = httpx.patch(f"{SUPABASE_URL}/rest/v1/chunks_v2?id=eq.{c['id']}", headers=H,
                            json={"content": c["content"]}, timeout=30)
            assert r.status_code in (200, 204), f"{c['id']}: PATCH {r.status_code}"
            print(f"{c['id'][:12]}: RESTAURADO del snapshot")
        return 0

    print(f"modo desconocido: {mode} (apply|verify|rollback)")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
