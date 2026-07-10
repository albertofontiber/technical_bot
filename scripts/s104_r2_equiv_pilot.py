#!/usr/bin/env python3
"""s104_r2_equiv_pilot.py — G0: piloto de equivalencia Haiku-vs-Sonnet del pase R2.

Dos modos:
  --select N   elige N docs estratificados (marca × tabla/prosa × ES/EN) del store,
               EXCLUYENDO los 14 de T1 → evals/s104_g0_docs.txt (determinista, seed fija)
  --compare    computa las bandas G0 desde los dos dumps (G0S=Sonnet-p1, G0H=Haiku-h1)
               → evals/s104_g0_verdict.json

BANDAS (pre-declaradas en el diseño v2, AGREGADAS — los estratos n≈1-2 son ruido):
  QA-pass-rate H ≥ 90% del de S · cobertura/página H ≥ 95% de S ·
  enunciados-ÚTILES/item (sin chaff) H ≥ 85% de S · hechos-por-tabla (tokens-valor
  distintos cubiertos) H ≥ 90% de S.
Además emite el PANEL semántico: 40 pares muestreados (mismo item, S vs H) para lectura
manual (atribución + utilidad) — el QA determinista no ve atribución (F1 dúo).

Las generaciones las hace enunciados_pass.py (2 invocaciones, --to-dump):
  python scripts/enunciados_pass.py --tranche G0S --docs evals/s104_g0_docs.txt --to-dump
  python scripts/enunciados_pass.py --tranche G0H --docs evals/s104_g0_docs.txt --to-dump \\
         --model claude-haiku-4-5-20251001 --vintage h1
"""
import argparse
import glob
import json
import os
import random
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from enunciados_qa import tokens_valor  # noqa: E402
from s94_f1_generate import item_text  # noqa: E402

STORE = "data/extraction/agent_anthropic-sonnet-45"
DOCS_OUT = "evals/s104_g0_docs.txt"
BANDS = {"qa_pass_rate": 0.90, "cobertura": 0.95, "utiles_por_item": 0.85,
         "hechos_por_tabla": 0.90}


def _store_docs() -> list[dict]:
    out = []
    for p in sorted(glob.glob(f"{STORE}/*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        head = open(p, encoding="utf-8").read(600)
        m = re.search(r'"source_path":\s*"([^"]+)"', head)
        if not m:
            continue
        base = re.sub(r"\.(pdf|json)$", "", os.path.basename(m.group(1)), flags=re.I)
        r = d.get("result") or {}
        pages = r.get("pages", []) if isinstance(r, dict) else (r if isinstance(r, list) else [])
        n_items = n_tables = 0
        for pg in pages:
            if not isinstance(pg, dict):
                continue
            for it in (pg.get("items") or []):
                if not isinstance(it, dict):
                    continue
                if it.get("rows") or len(tokens_valor(item_text(it))) >= 3:
                    n_items += 1
                    n_tables += bool(it.get("rows"))
        if n_items:
            out.append({"doc": base, "items": n_items, "tables": n_tables, "path": p})
    return out


def select(n: int) -> int:
    t1_docs = set()
    for line in open("evals/t1_surrogates_dump.jsonl", encoding="utf-8"):
        t1_docs.add(json.loads(line)["source_file"])
    cands = [d for d in _store_docs() if d["doc"] not in t1_docs
             and 5 <= d["items"] <= 120]          # ni triviales ni carísimos (G0 ≈ $5)
    # estratos: marca aproximada por prefijo del doc + tabla/prosa
    rng = random.Random(104)
    by_strat: dict = defaultdict(list)
    for d in cands:
        pref = re.match(r"[A-Za-z]+", d["doc"])
        marca = (pref.group(0)[:3].upper() if pref else "???")
        by_strat[(marca, d["tables"] > 0)].append(d)
    strats = sorted(by_strat, key=lambda k: -len(by_strat[k]))
    picked, i = [], 0
    while len(picked) < n and any(by_strat.values()):
        k = strats[i % len(strats)]
        if by_strat[k]:
            picked.append(by_strat[k].pop(rng.randrange(len(by_strat[k]))))
        i += 1
    with open(DOCS_OUT, "w", encoding="utf-8") as fh:
        for d in picked:
            fh.write(d["doc"] + "\n")
    est_items = sum(d["items"] for d in picked)
    print(f"G0: {len(picked)} docs · {est_items} items · estratos {len(strats)} → {DOCS_OUT}")
    print(f"   coste estimado 2 brazos ≈ ${est_items * 2 * 0.9 * 0.004:.2f}")
    return 0


def _metrics(manifest_path: str, dump_path: str) -> dict:
    man = json.load(open(manifest_path, encoding="utf-8"))
    gen = qa_fail = items = chaff = ins = 0
    covs = []
    for r in man["results"]:
        if r.get("skipped") or r.get("error"):
            continue
        gen += r.get("gen", 0); qa_fail += r.get("qa_fail", 0)
        items += r.get("items", 0); chaff += r.get("chaff", 0)
        ins += r.get("insertables", 0)
        if r.get("cobertura") is not None:
            covs.append(r["cobertura"])
    # hechos-por-tabla: tokens-valor distintos cubiertos en enunciados de items con tabla
    facts_tab: dict = defaultdict(set)
    by_item: dict = defaultdict(list)
    for line in open(dump_path, encoding="utf-8"):
        row = json.loads(line)
        key = (row["source_file"], row["page_number"])
        by_item[key].append(row)
        if not row.get("chaff"):
            facts_tab[key] |= tokens_valor(row["content"])
    return {"docs": sum(1 for r in man["results"] if not r.get("skipped") and not r.get("error")),
            "items": items, "gen": gen, "qa_pass_rate": (gen - qa_fail) / gen if gen else 0,
            "cobertura": sum(covs) / len(covs) if covs else 0,
            "insertables": ins, "chaff": chaff,
            "utiles_por_item": (ins - chaff) / items if items else 0,
            "hechos_tokens_total": sum(len(v) for v in facts_tab.values()),
            "cost_usd": man.get("spent_after")}


def compare() -> int:
    s = _metrics("evals/enunciados_pass_G0S.json", "evals/enunciados_dump_G0S.jsonl")
    h = _metrics("evals/enunciados_pass_G0H.json", "evals/enunciados_dump_G0H.jsonl")
    verdict, detail = "PASA", {}
    for k, band in BANDS.items():
        sv = s.get(k) or (s.get("hechos_tokens_total") if k == "hechos_por_tabla" else 0)
        hv = h.get(k) or (h.get("hechos_tokens_total") if k == "hechos_por_tabla" else 0)
        if k == "hechos_por_tabla":
            sv, hv = s["hechos_tokens_total"], h["hechos_tokens_total"]
        ratio = hv / sv if sv else 1.0
        detail[k] = {"sonnet": round(sv, 4), "haiku": round(hv, 4),
                     "ratio": round(ratio, 3), "band": band, "ok": ratio >= band}
        if ratio < band:
            verdict = "NO PASA"
    # panel semántico: 40 pares (mismo doc/página, S vs H) muestreados determinista
    rng = random.Random(104)
    s_rows = [json.loads(x) for x in open("evals/enunciados_dump_G0S.jsonl", encoding="utf-8")]
    h_rows = [json.loads(x) for x in open("evals/enunciados_dump_G0H.jsonl", encoding="utf-8")]
    h_by_pg = defaultdict(list)
    for r in h_rows:
        h_by_pg[(r["source_file"], r["page_number"])].append(r["content"])
    pool = [r for r in s_rows if not r.get("chaff") and h_by_pg.get((r["source_file"], r["page_number"]))]
    panel = []
    for r in rng.sample(pool, min(40, len(pool))):
        panel.append({"doc": r["source_file"], "p": r["page_number"], "pm": r.get("product_model"),
                      "sonnet": r["content"][:220],
                      "haiku_mismapagina": [t[:220] for t in
                                            h_by_pg[(r["source_file"], r["page_number"])][:3]]})
    out = {"verdict_bandas": verdict, "detail": detail, "sonnet": s, "haiku": h,
           "panel_semantico": panel,
           "nota": "verdict final = bandas ∧ lectura del panel (atribución/utilidad, F1 dúo)"}
    json.dump(out, open("evals/s104_g0_verdict.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"── G0 bandas: {verdict} ──")
    for k, v in detail.items():
        print(f"  {k:18s} S={v['sonnet']} H={v['haiku']} ratio={v['ratio']} "
              f"(banda ≥{v['band']}) {'✅' if v['ok'] else '❌'}")
    print(f"  coste: S=${s['cost_usd']} H=${h['cost_usd']}")
    print("→ evals/s104_g0_verdict.json (panel de 40 pares para lectura)")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", type=int)
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args()
    if a.select:
        raise SystemExit(select(a.select))
    if a.compare:
        raise SystemExit(compare())
    ap.print_help()
