#!/usr/bin/env python3
"""s94_f1_requal.py — re-QA v2 de los candidatos F1 (SIN re-pagar LLM; regla-C sobre el
QA v1, que tumbaba el 93% de R1 por un bug sistemático).

Fixes v2 (declarados en evals/s94_pilot_run.md):
(a) WHITELIST de metadata inyectada: los tokens del producto/pm/manufacturer/source_file
    del padre NO son invención del LLM (vienen de metadata adjudicada y el spec EXIGE el
    discriminador en el enunciado) → no cuentan contra la región. El resto de tokens
    numéricos/código siguen estrictos (deben existir verbatim en la página fuente).
(b) fact-bearing v2 para hechos COMPUESTOS: contiguo | token-sin-espacios ('1a') |
    (todos los componentes con dígito + ≥1 componente alfabético por prefijo len>=3,
    p.ej. 'seg'→'segundos').
(c) fuente del QA = TODOS los items de la página anclada (nivel-página; v1 usaba el
    sub-conjunto fact-items — más laxo pero sigue siendo la frontera de fidelidad).

Re-corre también el delta-check H4 con los fact-bearing v2. Salida: sobreescribe
evals/s94_f1_candidates.json (v2) y guarda el v1 en .v1.bak.
"""
import json
import os
import re
import shutil
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

from s93_trackB_probe import TIE, fetch_chunks, norm
from s94_f1_generate import (TRACKC_FACTS, item_text, region_source_text, store_pages,
                             tokens_num, value_pat)
from src.ingestion.embedder import embed_query
from src.rag.retriever import _cos
from src.reingest.embed import embed

F1 = "evals/s94_f1_candidates.json"


def fact_bearing_v2(valor: str, text: str) -> bool:
    nt = norm(text)
    pat = value_pat(valor)
    if pat and pat.search(nt):
        return True
    nospace = norm(valor).replace(" ", "")
    if nospace and re.search(rf"(?<![a-z0-9]){re.escape(nospace)}(?![a-z0-9])", nt):
        return True
    comps = norm(valor).split()
    digits = [c for c in comps if any(ch.isdigit() for ch in c)]
    alphas = [c for c in comps if not any(ch.isdigit() for ch in c) and len(c) >= 3]
    if digits and all(re.search(rf"(?<![a-z0-9]){re.escape(d)}(?![a-z0-9])", nt) for d in digits):
        if not alphas or any(re.search(rf"(?<![a-z0-9]){re.escape(a[:3])}", nt) for a in alphas):
            return True
    return False


def main() -> int:
    d = json.load(open(F1, encoding="utf-8"))
    shutil.copy(F1, F1 + ".v1.bak")
    f0 = json.load(open("evals/s94_f0_testbed.json", encoding="utf-8"))
    parents = fetch_chunks(sorted({c["parent_id"] for c in d["candidatos"]}))
    page_src: dict = {}
    stats = {"R1": [0, 0], "R2": [0, 0], "R3": [0, 0]}
    for c in d["candidatos"]:
        key = (c["anchor"]["sha"], c["anchor"]["page_idx"])
        if key not in page_src:
            pages = store_pages(key[0])
            items = pages[key[1]].get("items", []) if key[1] < len(pages) and isinstance(pages[key[1]], dict) else []
            page_src[key] = (norm(region_source_text(items)), region_source_text(items))
        src_norm, src_raw = page_src[key]
        p = parents.get(c["parent_id"]) or {}
        wl = set()
        for metafield in (p.get("product_model"), p.get("manufacturer"), p.get("source_file")):
            wl |= tokens_num(str(metafield or ""))
        bad = [t for t in tokens_num(c["text"]) if t not in src_norm and t not in wl]
        fb = fact_bearing_v2(c["valor"], c["text"])
        ok, motivo = (False, f"token '{bad[0]}' no existe en la región (v2)") if bad else (True, "")
        if ok and fb:                       # QA-b co-ocurrencia (como v1, con fb v2)
            pat = value_pat(c["valor"])
            lines = [ln for ln in src_raw.splitlines()
                     if (pat and pat.search(norm(ln))) or fact_bearing_v2(c["valor"], ln)]
            if lines:
                disc = [w for w in re.findall(r"[a-z0-9][a-z0-9-]{2,}", norm(c["text"]))
                        if not w.isdigit() and w not in {"de", "la", "el", "en", "del", "con", "para"}]
                if not any(any(w in norm(ln) for w in disc) for ln in lines):
                    ok, motivo = False, "valor sin discriminador co-ocurrente (v2)"
        c["qa_pass"], c["qa_motivo"], c["fact_bearing"] = ok, motivo, fb
        stats[c["arm"]][0] += 1
        if not ok:
            stats[c["arm"]][1] += 1

    # delta-check H4 (v2)
    delta = []
    rows = {(r["qid"], r["valor"]): r for r in f0["rows"]}
    for (qid, valor) in sorted(TRACKC_FACTS):
        best = next((c for c in d["candidatos"] if c["qid"] == qid and c["valor"] == valor
                     and c["arm"] == "R2" and c["fact_bearing"] and c["qa_pass"]), None)
        if not best:
            delta.append({"qid": qid, "valor": valor, "delta": None, "motivo": "sin candidato fact-bearing (v2)"})
            continue
        ch = parents.get(best["parent_id"]) or {}
        q_emb = embed_query(rows[(qid, valor)]["question"])
        t_b7 = (f"{ch['context']}\n\n{best['text']}" if ch.get("context") else best["text"])
        t_store = f"{ch.get('source_file','doc')} · página {best['anchor'].get('page_idx',0)+1}\n\n{best['text']}"
        e = embed([t_b7, t_store], "document")
        dv = abs(_cos(q_emb, e[0]) - _cos(q_emb, e[1]))
        delta.append({"qid": qid, "valor": valor, "delta": round(dv, 4), "supera_tie": dv > TIE})

    d["stats"] = {k: {"generados": v[0], "qa_fail": v[1]} for k, v in stats.items()}
    d["delta_check_prefijo"] = delta
    d["_qa_version"] = "v2 (whitelist metadata + fact-bearing compuestos + fuente nivel-página)"
    json.dump(d, open(F1, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("stats v2:", d["stats"])
    print("delta-check v2:", delta)
    fb_ok = sum(1 for c in d["candidatos"] if c["fact_bearing"] and c["qa_pass"])
    hechos = len({(c["qid"], c["valor"]) for c in d["candidatos"] if c["fact_bearing"] and c["qa_pass"]})
    print(f"fact-bearing QA-OK = {fb_ok} en {hechos} hechos → {F1} (v1 en .v1.bak)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
