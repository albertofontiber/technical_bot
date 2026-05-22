#!/usr/bin/env python3
"""Verificación lote 2: citación (chunks del eval log) + contexto de páginas concretas."""
import sys
import json
import glob
import os
import re
import fitz

sys.stdout.reconfigure(encoding="utf-8")

# --- Cargar eval log ---
LOG = "logs/eval_20260502T152857Z.json"
with open(LOG, encoding="utf-8") as f:
    data = json.load(f)
results = {r["question"]["id"]: r for r in data["results"]}


def show_citation_check(qid, terms):
    """Para qid, muestra qué chunks F contienen cada término (verificación de citación)."""
    print(f"\n{'='*70}\n[{qid}] VERIFICACIÓN DE CITACIÓN")
    r = results.get(qid)
    if not r:
        print(f"   qid no encontrado en el log")
        return
    chunks = r["result"].get("chunks_full") or r["result"].get("chunks_used") or []
    answer = r["result"].get("answer", "")
    print(f"   {len(chunks)} chunks F. Respuesta del bot ({len(answer)} chars).")
    # Qué [F<n>] cita el bot
    cited = sorted(set(re.findall(r'\[?F(\d+)\]?', answer)))
    print(f"   El bot cita: F{', F'.join(cited) if cited else '(ninguno)'}")
    for term in terms:
        in_answer = term.lower() in answer.lower()
        chunk_hits = []
        for i, c in enumerate(chunks):
            if term.lower() in (c.get("content", "")).lower():
                chunk_hits.append(f"F{i+1}")
        print(f"   '{term}': en respuesta={in_answer} | en chunks={chunk_hits or 'NINGUNO'}")


def show_behavior(qid):
    """Muestra la respuesta del bot para analizar observed_behavior."""
    print(f"\n{'='*70}\n[{qid}] ANÁLISIS DE BEHAVIOR")
    r = results.get(qid)
    if not r:
        print("   no encontrado")
        return
    answer = r["result"].get("answer", "")
    sc = r.get("score", {})
    print(f"   observed_behavior (clasificador): {sc.get('observed_behavior')}")
    print(f"   expected: {r['question'].get('expected_behavior')}")
    nums = re.findall(r'\b\d+[.,]?\d*\s*(?:km|Ω|µF|μF|mm²|mm2|V|mA|m\b)', answer)
    print(f"   datos numéricos técnicos en la respuesta: {nums[:12]}")
    print(f"   ¿termina con '?': {answer.rstrip().endswith('?')}")
    print(f"   --- primeros 400 chars ---\n   {answer[:400]}")
    print(f"   --- últimos 250 chars ---\n   {answer[-250:]}")


def show_page_context(pdf_pat, pages, label):
    """Extrae texto de páginas concretas para lectura de contexto."""
    print(f"\n{'='*70}\n[{label}] CONTEXTO DE PÁGINAS")
    pdfs = [p for p in glob.glob("**/*.pdf", recursive=True)
            if pdf_pat.lower() in os.path.basename(p).lower()]
    if not pdfs:
        print(f"   PDF '{pdf_pat}' no encontrado")
        return
    doc = fitz.open(pdfs[0])
    print(f"   {os.path.basename(pdfs[0])}")
    for pg in pages:
        if pg <= len(doc):
            txt = doc[pg-1].get_text()
            print(f"\n   --- pág {pg} ---\n{txt[:1100]}")
    doc.close()


# hp010 — ¿el dato 512/EN54-2 está en algún chunk F que el bot vio?
show_citation_check("hp010", ["512", "EN54-2", "EN 54-2", "13.7", "sensores", "autoaprend", "auto-aprend", "auto-configuración"])

# hp011 — ¿SW3-6/SW3-7 están en los chunks F? Cowork dice F1 solo tiene SW1-7
show_citation_check("hp011", ["SW3", "SW1", "SW3-6", "SW3-7", "SW1-7", "abort", "EOL"])

# mc006 — análisis del clasificador de behavior
show_behavior("mc006")

# hp004 — ¿el DGD-600 especifica AC/DC para la variante 220V?
show_page_context("DGD-600", [1, 2], "hp004 — DGD-600 tensión 220V")

# cm003 — humedad ASD531 p.91
show_page_context("ASD531_OM", [91], "cm003 — ASD531 datos técnicos")
