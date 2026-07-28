#!/usr/bin/env python3
"""Verificación lote 3: contexto exacto de chunks F (hp010, hp011) + cm003 humedad."""
import sys
import json
import glob
import os
import re
import fitz

sys.stdout.reconfigure(encoding="utf-8")

with open("logs/eval_20260502T152857Z.json", encoding="utf-8") as f:
    data = json.load(f)
results = {r["question"]["id"]: r for r in data["results"]}


def chunk_context(qid, fnum, terms, window=220):
    """Muestra el contexto alrededor de cada término en el chunk F<fnum>."""
    r = results[qid]
    chunks = r["result"].get("chunks_full") or []
    if fnum > len(chunks):
        print(f"   {qid} F{fnum}: no existe")
        return
    c = chunks[fnum-1]
    content = c.get("content", "")
    print(f"\n[{qid} · F{fnum}] producto={c.get('product_model')} | fuente={c.get('source_file')}")
    print(f"   section_title={c.get('section_title')!r}")
    for term in terms:
        idx = content.lower().find(term.lower())
        if idx < 0:
            print(f"   '{term}': NO aparece en F{fnum}")
            continue
        a = max(0, idx-window)
        b = min(len(content), idx+len(term)+window)
        snippet = content[a:b].replace("\n", " ")
        print(f"   '{term}' (pos {idx}): ...{snippet}...")


print("="*70)
print("hp010 — ¿F5 contiene realmente 'EN54-2 13.7 = 512'? (Cowork dijo que NO)")
print("="*70)
chunk_context("hp010", 5, ["512", "13.7", "EN54-2"])
# también revisar el resto de F de hp010
for fn in [1, 3, 4]:
    chunk_context("hp010", fn, ["512", "13.7"])

print("\n" + "="*70)
print("hp011 — ¿F1/F2/F5 contienen 'SW3-6'/'SW3-7'? (Cowork dijo que solo SW1-7)")
print("="*70)
for fn in [1, 2, 5]:
    chunk_context("hp011", fn, ["SW3-6", "SW3-7", "SW1-7"])

print("\n" + "="*70)
print("cm003 — humedad ASD531 (final p.91 + p.92)")
print("="*70)
pdfs = [p for p in glob.glob("**/*.pdf", recursive=True) if "asd531_om" in os.path.basename(p).lower()]
if pdfs:
    doc = fitz.open(pdfs[0])
    for pg in [91, 92]:
        if pg <= len(doc):
            txt = doc[pg-1].get_text()
            # mostrar desde "Condiciones ambientales" o "humedad"
            low = txt.lower()
            idx = low.find("condiciones ambientales")
            if idx < 0:
                idx = low.find("humedad")
            seg = txt[max(0,idx-50):idx+700] if idx >= 0 else txt[-700:]
            print(f"\n--- ASD531 pág {pg} (fragmento relevante) ---\n{seg}")
    doc.close()
