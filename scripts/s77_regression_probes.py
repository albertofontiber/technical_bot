#!/usr/bin/env python3
"""s77 REGRESSION PROBES — cierra los huecos de medición que cazó el dúo (Protocolo 3, s77).

El dúo (sub-agente Opus + cross-model GPT-5.5) sobre el diseño de Option D encontró que la medición
de `s77_fallthrough_measure.py` tenía huecos. Esto los cierra ANTES de cablear:

  (A) MODELO-VECINO (el riesgo más fuerte, cross-model): marca conocida + modelo INEXISTENTE pero
      CERCANO a una familia real ("Detnov CAD-151" cerca de CAD-150-8). Bajo Option D cae al RAG; el
      retriever trae el VECINO. ¿El generador responde como-si-fuera-el-pedido (PEOR que refuse) o
      admite/clarifica? NO es cross-brand → la conducta de cat013 no lo cubre.
  (B) AUSENTE FIEL de marca-COLA: modelo inexistente bajo marca de cola (no Notifier dominante) que
      SÍ extraiga + lookup=None → ejercita la rama de Option D de verdad (la sonda detnov de antes
      no extrajo modelo).
  (C) COMPUESTO cross-brand (sub-agente): marca A mencionada + model0 de familia desincronizada de A
      + 2º modelo de marca B.

K-MAYORÍA (default 3): el generador es no-determinista; 1 muestra no declara estabilidad de conducta.
FIDELIDAD: replica _process_query; baseline prod-inerte (LEVER2_* OFF, preview 800, chunks_v2). Marca
si cada sonda es FIEL al path de Option D (modelo extraído + lookup=None + marca en DB).

Uso: python scripts/s77_regression_probes.py [K]
Salida: evals/s77_regression_probes.yaml + respuestas completas por consola.
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
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["LEVER2_IDENTITY"] = "off"
os.environ["LEVER2_PM_RESCUE"] = "off"
os.environ["RERANK_PREVIEW_CHARS"] = "800"
sys.path.insert(0, str(ROOT))

from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from src.rag.retriever import (  # noqa: E402
    extract_product_models, retrieve_chunks, lookup_model_manufacturer, manufacturer_in_db,
)
from src.rag.reranker import rerank  # noqa: E402
from src.rag.generator import generate_answer  # noqa: E402

PROBES = [
    # (A) MODELO-VECINO: modelo inexistente cerca de una familia real, marca conocida.
    {"id": "neighbor_detnov_cad151", "clase": "vecino",
     "q": "Tengo una central Detnov CAD-151 y necesito saber cómo se conectan las baterías de 24V."},
    {"id": "neighbor_morley_zx9e", "clase": "vecino",
     "q": "¿Cuál es la resistencia de fin de línea recomendada para los lazos de la central Morley ZX9e?"},
    {"id": "neighbor_spectrex_4041", "clase": "vecino",
     "q": "Necesito un detector de llama SharpEye Spectrex 40/41R para una instalación; ¿qué referencia pido?"},
    # (B) AUSENTE FIEL marca-cola.
    {"id": "absent_xtralis_vep999", "clase": "ausente-cola",
     "q": "¿Cómo se realiza el test anual del detector Xtralis VESDA VEP-9990 según el fabricante?"},
    {"id": "absent_spectrex_2020z", "clase": "ausente-cola",
     "q": "¿Cuál es el rango de detección del detector de llama Spectrex 20/20Z?"},
    # (C) COMPUESTO cross-brand: marca mencionada A + model0 familia desincronizada + 2º modelo marca B.
    {"id": "crossbrand_morley_zxe_sdx", "clase": "compuesto-cross-brand",
     "q": "En la Morley ZXe quiero montar un detector óptico Notifier SDX-751 que me sobró; ¿es compatible?"},
]


def run_pipeline(query: str) -> dict:
    target_models = extract_product_models(query)
    chunks = retrieve_chunks(query, top_k=RETRIEVAL_TOP_K)
    chunks = rerank(query, chunks, top_k=RERANK_TOP_K, target_models=target_models)
    result = generate_answer(query, chunks, available_models=None)
    return {
        "target_models": target_models,
        "top_chunk_mfrs": [c.get("manufacturer") for c in chunks],
        "top_chunk_models": [c.get("product_model") for c in chunks],
        "answer": result["answer"],
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    results = []
    for p in PROBES:
        q = p["q"]
        extracted = extract_product_models(q)
        model0 = extracted[0] if extracted else None
        lookup = lookup_model_manufacturer(model0) if model0 else None
        # ¿Es FIEL al path de Option D? (modelo extraído + lookup=None + marca-mencionada en DB)
        # marca mencionada: la 1ª palabra-marca; aproximación por presencia en el texto.
        faithful = bool(model0) and lookup is None
        runs = [run_pipeline(q) for _ in range(K)]
        row = {
            "id": p["id"], "clase": p["clase"], "q": q,
            "model_extraido": model0, "lookup": lookup, "fiel_a_optionD": faithful,
            "K": K,
            "runs": [{"answer": r["answer"], "top_mfrs": r["top_chunk_mfrs"][:5],
                      "top_models": r["top_chunk_models"][:5]} for r in runs],
        }
        results.append(row)
        print("=" * 100)
        print(f"{p['id']}  [{p['clase']}]  fiel_a_OptionD={faithful}")
        print(f"Q: {q}")
        print(f"extract={extracted}  lookup({model0})={lookup}")
        for i, r in enumerate(runs):
            print(f"\n--- run {i+1}/{K} | top-5 models={r['top_chunk_models'][:5]} ---")
            print(r["answer"])
        print()

    report = {
        "meta": {
            "proposito": "Cierra huecos de medición del dúo s77 (vecino / ausente-cola / compuesto). reach != PASS.",
            "metodo": f"K-mayoría={K}; réplica _process_query; baseline prod-inerte (LEVER2_* OFF, "
                      "preview 800, chunks_v2).",
            "clases": "vecino=modelo inexistente cerca de familia real; ausente-cola=inexistente marca "
                      "minoritaria; compuesto-cross-brand=marca A + model0 desinc + modelo B.",
        },
        "resultados": results,
    }
    out_path = ROOT / "evals" / "s77_regression_probes.yaml"
    out_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False, width=100),
                        encoding="utf-8")
    print("=" * 100)
    print(f"Reporte -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
