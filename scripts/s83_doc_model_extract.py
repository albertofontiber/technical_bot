#!/usr/bin/env python3
"""s83_doc_model_extract.py — extrae el conjunto MULTI-LABEL de modelos que cada documento CUBRE,
desde el CONTENIDO (no del product_model tag, que es single-label e INCOMPLETO).

Motivación (Alberto s83): el doc FAAST FLEX Product Guide cubre FLX-010 Y FLX-020, pero el corpus lo
tagueó solo 'FLX-010' → FLX-020 es invisible a la recuperación por modelo. Construir familias desde
los tags MISSEA estos modelos. Señal: frecuencia de tokens-modelo en el contenido (los CUBIERTOS
aparecen muchas veces; las menciones de paso, una). El refinamiento LLM (cubre-vs-menciona) viene después.

Read-only. Output: evals/s83_doc_model_candidates.json (doc -> {manufacturer, current_tag, candidates}).
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

os.environ["CHUNKS_TABLE"] = "chunks_v2"
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
CH = f"{SUPABASE_URL}/rest/v1/chunks_v2"
# token-modelo: prefijo de letras + dígitos (FLX-020, CAD-150-8, ID3000, NFXI-ASD11, AM-8200G)
TOK = re.compile(r"\b([A-Z]{1,6}(?:[- ]?[A-Z0-9]+)*\d[A-Z0-9-]*)\b")


def is_model(t: str) -> bool:
    al = sum(c.isalpha() for c in t)
    dg = sum(c.isdigit() for c in t)
    return al >= 1 and dg >= 2 and 3 <= len(t) <= 18 and not t.isdigit()


def get(off: int):
    for a in range(5):
        try:
            r = httpx.get(CH, headers=H, params={
                "select": "source_file,manufacturer,product_model,content",
                "limit": "1000", "offset": str(off)}, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception:
            if a == 4:
                raise
            time.sleep(2 * (a + 1))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    doc: dict = defaultdict(lambda: {"mfr": Counter(), "tag": Counter(), "tok": Counter()})
    off = 0
    while True:
        rows = get(off)
        if not rows:
            break
        for row in rows:
            sf = row.get("source_file")
            if not sf:
                continue
            d = doc[sf]
            if row.get("manufacturer"):
                d["mfr"][row["manufacturer"]] += 1
            if row.get("product_model"):
                d["tag"][row["product_model"]] += 1
            for m in TOK.findall(row.get("content") or ""):
                if is_model(m):
                    d["tok"][m] += 1
        off += 1000
        print(f"  ...{off} chunks ({len(doc)} docs)", flush=True)
        if len(rows) < 1000:
            break
    out = {}
    for sf, d in doc.items():
        cands = {t: c for t, c in d["tok"].most_common(40) if c >= 2}
        out[sf] = {
            "manufacturer": (d["mfr"].most_common(1)[0][0] if d["mfr"] else None),
            "current_tag": (d["tag"].most_common(1)[0][0] if d["tag"] else None),
            "candidates": cands,
        }
    OUTP = ROOT / "evals" / "s83_doc_model_candidates.json"
    OUTP.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"\ndocs procesados: {len(out)} → {OUTP}")
    # validación FAAST
    for sf, d in out.items():
        if "FAAST_FLEX_Product_Guide" in sf and "7020" in sf:
            print(f"\nVALIDACION doc FAAST: {sf[:55]}")
            print(f"  tag actual (single-label): {d['current_tag']}")
            print(f"  candidatos multi-label desde CONTENIDO: {d['candidates']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
