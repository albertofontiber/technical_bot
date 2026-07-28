#!/usr/bin/env python3
"""t1_select_docs.py — selección DETERMINISTA de docs para T1 + coste pre-vuelo.

Reglas (plan s94b v2 + dúo: T1 debe reproducir el piloto Y estresar layouts no vistos):
1. Los 12 docs-soporte del PILOTO (gate de reproducción) — SIEMPRE dentro.
2. Docs de las MARCAS-DE-GOLDS (Notifier, Morley, Detnov, Honeywell Life Safety),
   priorizados por densidad de datos (nº de items-tabla en el store, desc), hasta el
   presupuesto.
3. 2-3 marcas NO-VISTAS con isPerfectTable BAJO (estrés de layout): las 3 marcas con
   peor ratio isPerfect (mín. 5 docs con tablas), ~5 docs cada una.

Coste pre-vuelo: llamadas ≈ Σ(data_items + items_tabla) × $/call medido en el smoke
(MIDT180: 155 calls ≈ $2.5 → ~$0.016/call). GATE: si la proyección supera el techo
($100), se recorta la cola de (2) determinísticamente hasta caber.

Salida: evals/t1_docs.txt + evals/t1_selection.json (manifest con proyección).
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

STORE = "data/extraction/agent_anthropic-sonnet-45"
GOLD_BRANDS = {"notifier", "morley", "detnov", "honeywell life safety"}
TECHO_USD = 100.0
USD_POR_CALL = 0.016
N_UNSEEN_BRANDS = 3
DOCS_POR_UNSEEN = 5

PILOT_DOCS = ["MIDT170", "50253SP", "15088SP", "ADW535_TD_T140358es_e",
              "55315013 Manual Centrales Analogicas C", "HLSI-MN-103",
              "CAD-250-MC-380-es", "CAD-250_Manual-Configuracion-MC-380-es",
              "Manual instalacion CAD-250", "MPDT280", "MFDT280",
              "MIE-MI-530rv001", "MIDT190", "MIDT180"]


def scan_store() -> list[dict]:
    from enunciados_qa import tokens_valor
    from s94_f1_generate import item_text
    docs = []
    for p in sorted(glob.glob(f"{STORE}/*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        src = str(d.get("source_path", ""))
        base = os.path.splitext(os.path.basename(src.replace("\\", "/")))[0]
        marca_dir = src.replace("\\", "/").split("/")[0].replace("Manuales_", "")
        r = d.get("result") or {}
        pages = r.get("pages", []) if isinstance(r, dict) else []
        tablas = perf = data_items = 0
        for pg in pages:
            if not isinstance(pg, dict):
                continue
            for it in pg.get("items", []):
                if not isinstance(it, dict):
                    continue
                if it.get("rows"):
                    tablas += 1
                    perf += bool(it.get("isPerfectTable"))
                    data_items += 1
                elif len(tokens_valor(item_text(it))) >= 3:
                    data_items += 1
        docs.append({"doc": base, "marca_dir": marca_dir, "tablas": tablas,
                     "isPerfect": perf, "data_items": data_items,
                     "calls_est": data_items + tablas})
    return docs


def main() -> int:
    docs = scan_store()
    by_doc = {d["doc"]: d for d in docs}

    def is_gold_brand(d):
        m = d["marca_dir"].lower().replace("_privado", "").replace("_", " ").strip()
        return any(b in m for b in GOLD_BRANDS)

    sel, motivo = [], {}
    # 1. piloto (match por prefijo normalizado)
    def normk(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())
    for pd in PILOT_DOCS:
        k = normk(pd)
        hit = next((d for d in docs if k in normk(d["doc"]) or normk(d["doc"]) in k), None)
        if hit and hit["doc"] not in motivo:
            sel.append(hit)
            motivo[hit["doc"]] = "piloto"
    # 3. marcas no-vistas con peor ratio isPerfect (mín 5 docs con tablas)
    per_marca = defaultdict(list)
    for d in docs:
        if d["tablas"] > 0:
            per_marca[d["marca_dir"]].append(d)
    unseen = [(m, sum(x["isPerfect"] for x in v) / max(sum(x["tablas"] for x in v), 1), v)
              for m, v in per_marca.items()
              if len(v) >= 5 and not is_gold_brand({"marca_dir": m})
              and m.lower() not in ("otros",)]   # 'Otros' = cajón de sastre, no una marca
    unseen.sort(key=lambda t: (t[1], t[0]))
    for m, ratio, v in unseen[:N_UNSEEN_BRANDS]:
        # densidad MEDIANA (estresa el layout sin pagar los docs más caros de la marca)
        vv = sorted(v, key=lambda x: (x["tablas"], x["doc"]))
        mid = len(vv) // 2
        for d in vv[max(0, mid - DOCS_POR_UNSEEN // 2):][:DOCS_POR_UNSEEN]:
            if d["doc"] not in motivo:
                sel.append(d)
                motivo[d["doc"]] = f"unseen:{m} (isPerfect={ratio:.2f})"
    # 2. marcas-de-golds por densidad hasta el techo
    # marca-gold: densidad MODERADA primero (más docs por dólar → mejor calibración
    # por-marca del gate QA), luego el resto
    resto = sorted((d for d in docs if is_gold_brand(d) and d["doc"] not in motivo
                    and d["data_items"] > 0),
                   key=lambda x: (not (3 <= x["tablas"] <= 25), -x["data_items"], x["doc"]))
    coste = sum(d["calls_est"] for d in sel) * USD_POR_CALL
    for d in resto:
        c = d["calls_est"] * USD_POR_CALL
        if coste + c > TECHO_USD:
            continue
        sel.append(d)
        motivo[d["doc"]] = "marca-gold"
        coste += c
    open("evals/t1_docs.txt", "w", encoding="utf-8").write(
        "\n".join(d["doc"] for d in sel) + "\n")
    manifest = {"n_docs": len(sel), "coste_proyectado_usd": round(coste, 2),
                "usd_por_call": USD_POR_CALL, "techo": TECHO_USD,
                "por_motivo": {m: sum(1 for x in sel if motivo[x["doc"]].startswith(m.split(":")[0]))
                               for m in ("piloto", "unseen", "marca-gold")},
                "unseen_brands": [f"{m} (isPerfect={r:.2f})" for m, r, _ in unseen[:N_UNSEEN_BRANDS]],
                "docs": [{**d, "motivo": motivo[d["doc"]]} for d in sel]}
    json.dump(manifest, open("evals/t1_selection.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"seleccionados: {len(sel)} docs · coste proyectado ${coste:.0f} (techo ${TECHO_USD:.0f})")
    print(f"  piloto={manifest['por_motivo']['piloto']} · unseen={manifest['por_motivo']['unseen']} "
          f"({', '.join(manifest['unseen_brands'])}) · marca-gold={manifest['por_motivo']['marca-gold']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
