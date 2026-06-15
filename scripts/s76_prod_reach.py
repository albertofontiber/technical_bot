#!/usr/bin/env python3
"""s76 PROD-REACH — mide el gap eval<->prod del bias #40 (observabilidad, judge-free).

El harness del eval (test_bot_vs_gold.py:37) llama retrieve_chunks() DIRECTO: bypasea los
gates pre-retrieval de handle_message() (telegram_bot.py:261-344). En prod, una query puede
cortarse ANTES del RAG (manufacturer-check) y nunca llegar al retrieval — el error mas caro del
proyecto (LEVER2_IDENTITY NO-OP en prod, s73/bias #40). Este script hace VISIBLE ese corte.

ANTI-BIAS-#40 (clave): NO re-implementa la logica de datos del gate. Importa los REGEX y
FUNCIONES REALES del handler (telegram_bot._MANUFACTURER_NAMES/_CATALOG_PATTERNS/...,
retriever.extract_product_models/lookup_model_manufacturer/manufacturer_in_db) y replica el
ORDEN EXACTO de ramas de handle_message (telegram_bot.py:261-344). Lo unico replicado es el
if/else (deterministico, citado). Flags en DEFAULT (OFF = prod). CHUNKS_TABLE=chunks_v2 (prod).

ALCANCE: mide REACH (la query llega al retrieval si/no), NO outcome (el gold pasa). reach != PASS
es load-bearing — no re-leer "N golds recuperables". Es deuda de MEDICION, no un lever.

Uso: python scripts/s76_prod_reach.py
Salida: evals/s76_prod_reach.yaml + resumen por consola.
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # prod, ANTES de importar config/retriever

import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # re-asegurar tras load_dotenv
sys.path.insert(0, str(ROOT))

import scripts.gold_store as gold_store  # noqa: E402
# Funciones/regex REALES del handler (no se re-implementan).
from src.bot.telegram_bot import (  # noqa: E402
    _MANUFACTURER_NAMES, _CATALOG_PATTERNS,
    _GREETING_PATTERNS, _THANKS_PATTERNS, _BYE_PATTERNS, _FEEDBACK_PATTERNS,
)
from src.rag.retriever import (  # noqa: E402
    extract_product_models, lookup_model_manufacturer, manufacturer_in_db,
)

# Los 29 NO-PASS (evals/s71_classification_v2.yaml). Mapa de clases para el cruce.
NOPASS_29 = [
    "cat007", "cat013", "cat021", "hp006", "hp009", "hp013", "cat016", "hp003",
    "cat017", "hp002", "hp008", "hp001", "hp017", "cat001", "hp011", "hp018",
    "cat008", "cat009", "hp005", "hp014", "hp004", "hp007", "cat011", "cat012",
    "cat019", "cat020", "cat024", "hp010", "hp012",
]


def classify_pre_rag(query: str) -> dict:
    """Replica FIEL el orden de ramas de handle_message (telegram_bot.py:261-344).

    Devuelve {outcome, detail, mentioned_manufacturer, model, actual_manufacturer}.
    outcome in {REACHES_RAG, CUT_greeting/thanks/bye, CUT_catalog, CUT_A_mismatch,
    CUT_model_not_found, CUT_manufacturer_not_in_db, CUT_feedback}.
    """
    out = {"mentioned_manufacturer": None, "model": None, "actual_manufacturer": None}

    # Pasos 1-3 (telegram_bot.py:262-284): saludo/gracias/despedida (anclados ^...$).
    if _GREETING_PATTERNS.match(query):
        return {**out, "outcome": "CUT_greeting", "detail": "greeting"}
    if _THANKS_PATTERNS.match(query):
        return {**out, "outcome": "CUT_thanks", "detail": "thanks"}
    if _BYE_PATTERNS.match(query):
        return {**out, "outcome": "CUT_bye", "detail": "bye"}

    # Paso 4 (telegram_bot.py:287): catalogo.
    if _CATALOG_PATTERNS.search(query):
        return {**out, "outcome": "CUT_catalog", "detail": "catalog shortcut"}

    # Paso 5 (telegram_bot.py:293-339): manufacturer-check pre-retrieval.
    m = _MANUFACTURER_NAMES.search(query)
    if m:
        mentioned = m.group(0)
        out["mentioned_manufacturer"] = mentioned
        models = extract_product_models(query)
        if models:
            model = models[0]
            out["model"] = model
            actual = lookup_model_manufacturer(model)
            out["actual_manufacturer"] = actual
            if actual:
                if actual.lower() != mentioned.lower():
                    # :304-313 — modelo bajo OTRA marca → corta (CUT-A).
                    return {**out, "outcome": "CUT_A_mismatch",
                            "detail": f"{model}={actual} != mencion {mentioned}"}
                # :314 — marca correcta → fall-through al RAG.
            else:
                # :315-325 — modelo no en DB → corta.
                return {**out, "outcome": "CUT_model_not_found",
                        "detail": f"lookup_model_manufacturer({model})=None"}
        else:
            # :326-339 — solo marca, sin modelo.
            if not manufacturer_in_db(mentioned):
                return {**out, "outcome": "CUT_manufacturer_not_in_db",
                        "detail": f"manufacturer_in_db({mentioned})=False"}
            # marca en DB → fall-through.

    # Paso 6 (telegram_bot.py:342): feedback.
    if _FEEDBACK_PATTERNS.search(query):
        return {**out, "outcome": "CUT_feedback", "detail": "feedback handler"}

    # --- llega al RAG (telegram_bot.py:346-348) ---
    return {**out, "outcome": "REACHES_RAG", "detail": "fall-through to RAG"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    all_golds = gold_store.load()
    by_qid = {g.get("qid"): g for g in all_golds}

    # Embargo: ninguno de los 29 debe ser held-out (son dev por construccion). Assert duro.
    heldout_qids = {g.get("qid") for g in gold_store.heldout()}
    leaked = [q for q in NOPASS_29 if q in heldout_qids]
    if leaked:
        sys.exit(f"EMBARGO: qids held-out en la lista de 29: {leaked} — abortado")

    rows = []
    for qid in NOPASS_29:
        g = by_qid.get(qid)
        if not g:
            rows.append({"qid": qid, "outcome": "MISSING_GOLD", "detail": "qid no en el ruler"})
            continue
        q = (g.get("question") or "").strip()
        r = classify_pre_rag(q)
        rows.append({
            "qid": qid,
            "conducta": g.get("conducta_esperada"),
            "question": q[:140],
            "outcome": r["outcome"],
            "detail": r["detail"],
            "mentioned_manufacturer": r["mentioned_manufacturer"],
            "model": r["model"],
            "actual_manufacturer": r["actual_manufacturer"],
        })

    # Base rate sobre TODO el dev verificado (incl. PASS-control) — contexto.
    dev = gold_store.dev()
    dev_counts: dict[str, int] = {}
    dev_cut_qids: list[str] = []
    for g in dev:
        q = (g.get("question") or "").strip()
        oc = classify_pre_rag(q)["outcome"]
        dev_counts[oc] = dev_counts.get(oc, 0) + 1
        if oc != "REACHES_RAG":
            dev_cut_qids.append(g.get("qid"))

    # Resumen de los 29.
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    cut_qids = [r["qid"] for r in rows if r["outcome"] != "REACHES_RAG"
                and r["outcome"] != "MISSING_GOLD"]

    report = {
        "meta": {
            "proposito": "Observabilidad del gap eval<->prod (bias #40). REACH != PASS.",
            "metodo": "classify_pre_rag replica handle_message telegram_bot.py:261-344, "
                      "funciones/regex reales, flags default (OFF=prod), chunks_v2.",
            "n_29": len(NOPASS_29), "n_dev_total": len(dev),
        },
        "resumen_29": {
            "counts": counts,
            "cut_total": len(cut_qids),
            "cut_qids": cut_qids,
        },
        "base_rate_dev": {
            "counts": dev_counts,
            "cut_total": len(dev_cut_qids),
            "cut_qids": sorted(dev_cut_qids),
        },
        "detalle_29": rows,
    }
    out_path = ROOT / "evals" / "s76_prod_reach.yaml"
    out_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False, width=100),
                        encoding="utf-8")

    print("=== PROD-REACH de los 29 NO-PASS (REACH != PASS) ===")
    for r in rows:
        mark = "  REACH" if r["outcome"] == "REACHES_RAG" else ">>CUT "
        print(f"{mark} {r['qid']:7} {r['outcome']:26} {r.get('detail','')}")
    print(f"\nResumen 29: {counts}")
    print(f"Cortados antes del RAG: {len(cut_qids)}/29 -> {cut_qids}")
    print(f"\nBase rate dev ({len(dev)} golds): {dev_counts}")
    print(f"Dev cortados: {len(dev_cut_qids)} -> {sorted(dev_cut_qids)}")
    print(f"\nReporte -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
