#!/usr/bin/env python3
"""s287_p05_probe_pool.py — probe $0 del gate P0.5 (quarantine 'zxe', hotfix s287).

Corre retrieve_chunks (que aplica resolver + _filter_to_query_models POR DENTRO) para la
pregunta del gold hp018 en DOS brazos, sin tocar el reranker (LLM = $0 aquí; el probe es
sobre el POOL FILTRADO pre-rerank):

  before = quarantine VACÍA simulada (estado pre-hotfix): bajo replace el drop de 'zxe'
           deja 0 supervivientes → fail-open (retriever.py:2152) = filtro DESARMADO,
           entran los primos ZXSe/ZX50/DXc (~8/10 en cabeza, diagnóstico s287).
  after  = quarantine REAL del YAML ({'zxe'}, s287 P0.5): el token se conserva → el
           filtro vive; predicción del diseño: ZXSe/ZX50/DXc caen del pool filtrado,
           quedan ZXe + ZXAE/ZXEE (~6/10 en cabeza — comportamiento-ADD, DEC-084).

Read-only sobre DB (retrieve necesita .env). Salida: evals/s287_p05_probe_pool_v1.json
(composición por source_file/product_model, cabeza-10 y pool completo, ambos brazos).

Uso:  python scripts/s287_p05_probe_pool.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir() and (ROOT / "evals").is_dir(), f"cwd no es la raíz: {ROOT}"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# ── flags de la RUTA HARNESS relevantes a RETRIEVAL (subset literal de DEMO_FLAGS,
# scripts/factlevel_assessment.py — el resto gobierna coverage/generación, aquí inertes).
# Los módulos hacen load_dotenv(override=True) en import-time → se fijan ANTES de importar
# y se RE-AFIRMAN después (mismo patrón _assert_demo_flags del instrumento).
RETRIEVAL_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2",
    "ENUNCIADOS_MULTIVECTOR": "on",
    "IDENTITY_RESOLVE": "on",
    "IDENTITY_RESOLVE_POLICY": "replace",
    "HYQ_TABLE": "on",
    "HYDE_ENABLED": "false",
    "DIVERSIFY_TIEBREAK": "off",
    "HYQ_PILOT_FILE": "",
    "LEVER2_PM_RESCUE": "",
}


def _assert_flags() -> None:
    for k, v in RETRIEVAL_FLAGS.items():
        os.environ[k] = v


_assert_flags()

import yaml  # noqa: E402

from src.rag.retriever import retrieve_chunks  # noqa: E402
from src.rag import catalog_resolver  # noqa: E402
from src.config import RETRIEVAL_TOP_K  # noqa: E402
from retrieval_miss_famtie import fam_norm  # noqa: E402

_assert_flags()   # re-afirmar tras los imports (load_dotenv override=True en la cadena)

QID = "hp018"
GOLDS_PATH = ROOT / "evals" / "gold_answers_v1.yaml"
OUT_PATH = ROOT / "evals" / "s287_p05_probe_pool_v1.json"
# la fila que acredita hp018#1 en el gate P0 (ZXe p.22, «RFL (6800Ω)»)
ACCREDITING_ID = "d4de9ba9-9206-49cf-9782-ba141168a0c2"

PRIMO_FAMS = {"ZXSE", "ZX50", "DXC"}          # los primos del diagnóstico (Grupo B)
FAMILY_FAMS = {"ZXE", "ZXAE/ZXEE", "ZX2E/ZX5E"}  # ZXe + legacy re-admitidos (DEC-084)


def hp018_question() -> str:
    golds = yaml.safe_load(GOLDS_PATH.read_text(encoding="utf-8"))
    rows = golds if isinstance(golds, list) else golds.get("golds") or []
    gold = next(g for g in rows if g.get("qid") == QID)
    return gold["question"]


def describe_pool(pool: list[dict]) -> dict:
    def rowinfo(c: dict) -> dict:
        return {"id": c.get("id"), "product_model": c.get("product_model"),
                "source_file": c.get("source_file"), "page_number": c.get("page_number")}

    head = pool[:10]
    fams_head = [fam_norm(c.get("product_model")) for c in head]
    fams_pool = [fam_norm(c.get("product_model")) for c in pool]
    return {
        "pool_n": len(pool),
        "head10": [rowinfo(c) for c in head],
        "head10_by_family": dict(Counter(fams_head)),
        "pool_by_family": dict(Counter(fams_pool)),
        "pool_by_source_file": dict(Counter(str(c.get("source_file")) for c in pool)),
        "head10_primos": sum(1 for f in fams_head if f in PRIMO_FAMS),
        "head10_familia": sum(1 for f in fams_head if f in FAMILY_FAMS),
        "pool_primos": sum(1 for f in fams_pool if f in PRIMO_FAMS),
        "accrediting_chunk_in_pool": any(c.get("id") == ACCREDITING_ID for c in pool),
        "accrediting_chunk_pool_rank": next(
            (i for i, c in enumerate(pool) if c.get("id") == ACCREDITING_ID), None),
    }


def run_arm(label: str, question: str) -> dict:
    pool = retrieve_chunks(question, top_k=RETRIEVAL_TOP_K)
    out = {"arm": label, **describe_pool(pool)}
    print(f"  [{label}] pool={out['pool_n']} head10_familia={out['head10_familia']} "
          f"head10_primos={out['head10_primos']} "
          f"accrediting_rank={out['accrediting_chunk_pool_rank']}")
    return out


def main() -> None:
    question = hp018_question()
    print(f"probe P0.5 · {QID}: {question}")

    # before: quarantine VACÍA simulada (pre-hotfix) — inyección directa del cache lazy
    catalog_resolver._quarantine = frozenset()
    before = run_arm("before_quarantine_vacia", question)

    # after: quarantine REAL del YAML ({'zxe'}, s287 P0.5) — fuerza re-lectura
    catalog_resolver._quarantine = None
    quarantine_real = sorted(catalog_resolver._quarantine_tokens())
    after = run_arm("after_quarantine_zxe", question)

    prediction_ok = (
        after["head10_primos"] == 0
        and after["head10_familia"] >= 4          # ~6/10 esperado; >=4 = margen de jitter
        and before["head10_primos"] > after["head10_primos"]
    )
    result = {
        "gate": "s287 P0.5 — quarantine 'zxe' re-arma el filtro de familia (hp018)",
        "question": question,
        "flags": dict(RETRIEVAL_FLAGS),
        "retrieval_top_k": RETRIEVAL_TOP_K,
        "quarantine_yaml": quarantine_real,
        "prediction": "ZXSe/ZX50/DXc caen del pool filtrado; quedan ZXe+ZXAE/ZXEE "
                      "(~6/10 en cabeza — DEC-084/comportamiento-ADD)",
        "before": before,
        "after": after,
        "prediction_ok": prediction_ok,
        "nota": "probe sobre el POOL FILTRADO pre-rerank (el rerank es LLM y NO se llama); "
                "dos retrieves = dos embeddings de la misma query, jitter de composición "
                "posible pero el delta lo gobierna el filtro",
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"escrito {OUT_PATH}")
    print(f"  prediction_ok={prediction_ok}")


if __name__ == "__main__":
    main()
