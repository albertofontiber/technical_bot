#!/usr/bin/env python3
"""Sonda corpus CAD-150 — verifica (regla-C) la estructura de familia que describió Alberto.

Alberto (16 jun, desde la web/manuales Detnov): la familia CAD-150 = {CAD-150-1, CAD-150-2,
CAD-150-2-MB, CAD-150-4, CAD-150-8, CAD-150-8-PLUS}; los manuales 55315013 (Instalación) y 55315008
(Usuario) cubren TODA la familia, con páginas/secciones específicas por nº de lazos. Esto es
ground-truth de IDENTIDAD que el corpus no expresa solo → confirmar cómo está el dato realmente
(¿todo bajo product_model=CAD-150-8? ¿qué es CAD-150R, que NO está en su lista?) para que la
curación futura (#4 / identidad #49) sea exacta. Read-only.
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, CHUNKS_TABLE  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def fetch(params):
    rows, off = [], 0
    with httpx.Client(timeout=30.0) as c:
        while True:
            r = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=H,
                      params={**params, "limit": "1000", "offset": str(off)})
            r.raise_for_status()
            b = r.json(); rows.extend(b)
            if len(b) < 1000 or off >= 9000:
                break
            off += 1000
    return rows


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # 1) Todos los chunks cuyo source_file menciona CAD-150 — por (source_file, product_model).
    rows = fetch({"source_file": "ilike.*CAD-150*", "select": "source_file,product_model,page_number,manufacturer"})
    print(f"=== chunks con source_file ~CAD-150: {len(rows)} ===\n")
    agg = {}
    for r in rows:
        k = (r.get("source_file"), r.get("product_model"), r.get("manufacturer"))
        d = agg.setdefault(k, {"n": 0, "pages": set()})
        d["n"] += 1
        if r.get("page_number") is not None:
            d["pages"].add(r["page_number"])
    for (sf, pm, mfr), d in sorted(agg.items(), key=lambda kv: -kv[1]["n"]):
        pr = f"{min(d['pages'])}-{max(d['pages'])}" if d["pages"] else "—"
        print(f"  {d['n']:4} chunks | pm={pm} | mfr={mfr}\n        source={sf}\n        páginas {pr} ({len(d['pages'])} distintas)")

    # 2) ¿Qué es CAD-150R? (no está en la lista de familia de Alberto)
    print("\n=== product_model = 'CAD-150R' (anomalía: no en la lista de Alberto) ===")
    r2 = fetch({"product_model": "eq.CAD-150R", "select": "source_file,page_number"})
    sf2 = {}
    for r in r2:
        sf2.setdefault(r.get("source_file"), set()).add(r.get("page_number"))
    for sf, pgs in sf2.items():
        pgs = {p for p in pgs if p is not None}
        pr = f"{min(pgs)}-{max(pgs)}" if pgs else "—"
        print(f"  {sf}: {len([1 for r in r2 if r.get('source_file')==sf])} chunks, páginas {pr}")

    # 3) ¿Existe ALGÚN chunk etiquetado con las variantes que Alberto lista (1/2/4/2-MB/8-PLUS)?
    print("\n=== ¿hay product_model por-variante en el corpus? ===")
    for variant in ["CAD-150-1", "CAD-150-2", "CAD-150-2-MB", "CAD-150-4", "CAD-150-8-PLUS"]:
        rr = fetch({"product_model": f"eq.{variant}", "select": "id"})
        print(f"  {variant:16} → {len(rr)} chunks")

    # 4) Página-por-página de los dos manuales clave (para ver si las páginas 2/4/5/6/7 están).
    for sf_key in ["55315013", "55315008"]:
        rr = fetch({"source_file": f"ilike.*{sf_key}*", "select": "page_number,product_model"})
        pages = sorted({r["page_number"] for r in rr if r.get("page_number") is not None})
        pmset = sorted({r.get("product_model") for r in rr})
        print(f"\n=== {sf_key}: {len(rr)} chunks, pm={pmset}, páginas presentes: {pages[:40]}{' …' if len(pages)>40 else ''}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
