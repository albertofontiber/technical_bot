#!/usr/bin/env python3
"""s77 FALL-THROUGH MEASURE — qué responde el bot SI Option D deja pasar el corte (judge-free).

Pregunta decisiva (eval-driven, bias #38: "validado-por-dúo" != "validado-como-que-mejora"):
para los 6 catalog-miss, ¿el fall-through produce una respuesta MEJOR que el falso hard-refuse
actual ("no tengo info sobre CAD-150"), o PEOR (alucinación / inferencia cross-brand)? El cross-model
de s76 avisó que el gate-fix "cambia falsos-rechazos por falsos-aceptados". Esto lo MIDE leyendo.

FIDELIDAD (lección #40 — el eval bypasea el handler): una vez Option D hace fall-through, el path
es EXACTAMENTE `_process_query` (telegram_bot.py:416-466): extract -> retrieve(50) -> rerank(5,
target_models) -> generate_answer. Se replica paso a paso. El gate solo decide la ENTRADA, no
altera el pipeline, así que correr el pipeline == medir el outcome del fall-through.

CONFIG = baseline prod-inerte DECLARADO (no se hereda el .env local): LEVER2_* OFF, preview 800,
chunks_v2. Con target_models el reranker es SIEMPRE LLM (reranker.py:269), así que el backend no
es variable aquí.

reach != PASS: esto NO mide PASS de gold; mide CONDUCTA del fall-through (answer/admit/refuse/
cross-brand). Sondas de NO-REGRESIÓN incluidas: cat013 (refuse-inference, el canario de #41) +
modelo-ausente-bajo-marca-conocida (el fallo OPUESTO que Option D podría introducir).

Uso: python scripts/s77_fallthrough_measure.py
Salida: evals/s77_fallthrough_measure.yaml + respuestas completas por consola.
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"

import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
# Baseline prod-inerte EXPLÍCITO (no heredar lever-states del .env local).
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["LEVER2_IDENTITY"] = "off"
os.environ["LEVER2_PM_RESCUE"] = "off"
os.environ["RERANK_PREVIEW_CHARS"] = "800"
sys.path.insert(0, str(ROOT))

import scripts.gold_store as gold_store  # noqa: E402
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from src.rag.retriever import (  # noqa: E402
    extract_product_models, retrieve_chunks, lookup_model_manufacturer, manufacturer_in_db,
)
from src.rag.reranker import rerank  # noqa: E402
from src.rag.generator import generate_answer  # noqa: E402

# Los 6 catalog-miss (CUT_model_not_found, marca correcta — recuperables vía Option D).
SIX_QIDS = ["cat013", "cat016", "hp003", "hp009", "hp018", "cat021"]

# Sondas de NO-REGRESIÓN (el fallo OPUESTO): marca conocida + modelo INEXISTENTE → bajo Option D
# caería al RAG; el generador DEBE seguir haciendo admit-no-info, no rellenar.
ABSENT_PROBES = [
    {"qid": "probe_absent_notifier",
     "question": "En la central Notifier AFP-9990, ¿cómo se programa el retardo de salida de alarma principal?"},
    {"qid": "probe_absent_detnov",
     "question": "¿Cómo se configura el nivel de sensibilidad del detector Detnov XQD-880?"},
]

# Texto del falso hard-refuse ACTUAL (gate, telegram_bot.py:319-324) — la línea base a superar.
CURRENT_REFUSE = "[hard-refuse] 'No tengo información sobre el modelo X. Tengo manuales de: ...'"


def run_pipeline(query: str) -> dict:
    """Replica _process_query (telegram_bot.py:416-466) para una query fresca (sin sesión)."""
    target_models = extract_product_models(query)
    chunks = retrieve_chunks(query, top_k=RETRIEVAL_TOP_K)
    chunks = rerank(query, chunks, top_k=RERANK_TOP_K, target_models=target_models)
    # available_models=None: nuestras queries tienen target_models (rama not-target no aplica).
    result = generate_answer(query, chunks, available_models=None)
    top = [{"product_model": c.get("product_model"), "manufacturer": c.get("manufacturer"),
            "source_file": c.get("source_file"), "sim": round(c.get("similarity", 0), 3)}
           for c in chunks]
    return {"target_models": target_models, "top_chunks": top, "answer": result["answer"]}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    by_qid = {g.get("qid"): g for g in gold_store.load()}

    cases = []
    for qid in SIX_QIDS:
        g = by_qid.get(qid)
        cases.append({"qid": qid, "tipo": "catalog-miss",
                      "conducta_esperada": g.get("conducta_esperada"),
                      "question": (g.get("question") or "").strip()})
    for p in ABSENT_PROBES:
        cases.append({"qid": p["qid"], "tipo": "no-regresion(ausente)",
                      "conducta_esperada": "admit_no_info", "question": p["question"]})

    results = []
    for c in cases:
        q = c["question"]
        # Verificación de path: ¿este caso traversa la rama de Option D?
        extracted = extract_product_models(q)
        model0 = extracted[0] if extracted else None
        lookup = lookup_model_manufacturer(model0) if model0 else None
        out = run_pipeline(q)
        row = {
            **c,
            "model_extraido": model0,
            "lookup_model_manufacturer": lookup,
            "target_models": out["target_models"],
            "top_chunk_mfrs": [t["manufacturer"] for t in out["top_chunks"]],
            "top_chunk_models": [t["product_model"] for t in out["top_chunks"]],
            "answer": out["answer"],
        }
        results.append(row)
        print("=" * 100)
        print(f"{c['qid']}  [{c['tipo']}]  conducta_esperada={c['conducta_esperada']}")
        print(f"Q: {q}")
        print(f"extract={extracted}  lookup({model0})={lookup}")
        print(f"top-5 mfrs={row['top_chunk_mfrs']}")
        print(f"top-5 models={row['top_chunk_models']}")
        print(f"--- RESPUESTA (fall-through) ---\n{out['answer']}\n")

    report = {
        "meta": {
            "proposito": "Conducta del fall-through (Option D) vs falso hard-refuse actual. reach != PASS.",
            "metodo": "replica _process_query (extract->retrieve50->rerank5->generate). "
                      "Baseline prod-inerte: LEVER2_* OFF, preview 800, chunks_v2.",
            "baseline_actual_prod": CURRENT_REFUSE,
            "n_catalog_miss": len(SIX_QIDS), "n_sondas_ausente": len(ABSENT_PROBES),
            "clasificacion_pendiente": "humano/Claude lee 'answer' y marca: "
            "ANSWER_CORRECT_MFR | ADMIT_NO_INFO | REFUSE_INFERENCE | CLARIFY | HALLUCINATE/CROSS_BRAND",
        },
        "resultados": results,
    }
    out_path = ROOT / "evals" / "s77_fallthrough_measure.yaml"
    out_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False, width=100),
                        encoding="utf-8")
    print("=" * 100)
    print(f"Reporte -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
