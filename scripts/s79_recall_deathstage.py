#!/usr/bin/env python3
"""s79 Paso 0 — death-STAGE del recall-cap de los within-doc golds (judge-free, $0, LIVE post-backfill).

El death-point de s78 dijo DÓNDE muere la cita en el funnel (pool / top-5). Este probe
descompone el RECALL-cap: de las citas que NO entran al pool-50, ¿en QUÉ stage de
`retrieve_chunks` mueren?  Decide si el cuello es arreglable barato o es recall vectorial profundo:

  - nunca aparece en vector_results NI keyword_results -> RECALL-VECTORIAL (rank>pool; lever s59)
  - aparece en search pero cae en _merge_channels (truncado)      -> MERGE-TRUNCATE
  - cae en 4b lifecycle (_filter_by_document_status)              -> LIFECYCLE (doc no-activo)
  - cae en 5a-pre _filter_to_query_models                         -> MODEL-FILTER (metadata; arreglable)
  - cae en 5a _diversify_by_source_file (cap round-robin)         -> DIVERSIFY-EXPELS (pool-stage; arreglable)
  - cae en 5c _filter_by_language                                 -> LANGUAGE

Método: monkeypatch OBSERVACIONAL — envuelve cada stage real (lo llama tal cual) y registra,
de las citas-objetivo, cuántas están cubiertas en la ENTRADA vs la SALIDA de ese stage.
Fiel al pipeline de prod (lección #40: el probe debe entrar por el pipeline real, no replicarlo).

Tambien re-mide n_in_pool LIVE (post-backfill) y el rank vectorial crudo de cada cita.
Read-only. Uso: python scripts/s79_recall_deathstage.py
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")

import json
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import src.rag.retriever as rt  # noqa: E402
from src.config import RETRIEVAL_TOP_K  # noqa: E402
from strict_match import chunk_has_quote_strict  # noqa: E402

# within-doc golds (death-point s78) + cat007 (referencia recall puro)
TARGETS = ["cat016", "hp001", "hp017", "hp011", "cat007"]


def set_prod_flags():
    for f in ("LEVER1_BROAD_FALLBACK", "LEVER1_KEYWORD_ORDER", "LEVER2_IDENTITY", "LEVER2_PM_RESCUE"):
        os.environ.pop(f, None)


def covered(chunks, quotes):
    """set de indices de quotes cubiertas (>=1 chunk contiene la cita) en `chunks`."""
    s = set()
    for qi, q in enumerate(quotes):
        for c in chunks:
            if chunk_has_quote_strict(c.get("content") or "", q):
                s.add(qi)
                break
    return s


# estado global para los wrappers (la query activa)
_CUR = {"quotes": [], "trace": [], "vec": [], "kw": []}


def _wrap_filter(name, fn):
    def wrapped(chunks, *a, **k):
        before = covered(chunks, _CUR["quotes"])
        out = fn(chunks, *a, **k)
        after = covered(out, _CUR["quotes"])
        dropped = before - after
        if dropped:
            _CUR["trace"].append((name, sorted(before), sorted(after), sorted(dropped)))
        return out
    return wrapped


def _wrap_merge(fn):
    def wrapped(keyword_results, vector_results, *a, **k):
        _CUR["kw"] = covered(keyword_results, _CUR["quotes"])
        _CUR["vec"] = covered(vector_results, _CUR["quotes"])
        # rank vectorial crudo de cada cita
        _CUR["vec_rank"] = {}
        for qi, q in enumerate(_CUR["quotes"]):
            for i, c in enumerate(vector_results):
                if chunk_has_quote_strict(c.get("content") or "", q):
                    _CUR["vec_rank"][qi] = i
                    break
        before = _CUR["kw"] | _CUR["vec"]
        out = fn(keyword_results, vector_results, *a, **k)
        after = covered(out, _CUR["quotes"])
        dropped = before - after
        if dropped:
            _CUR["trace"].append(("merge_truncate", sorted(before), sorted(after), sorted(dropped)))
        return out
    return wrapped


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    set_prod_flags()

    # instalar wrappers observacionales sobre el pipeline REAL
    rt._merge_channels = _wrap_merge(rt._merge_channels)
    rt._filter_by_document_status = _wrap_filter("lifecycle_4b", rt._filter_by_document_status)
    rt._filter_to_query_models = _wrap_filter("model_filter_5apre", rt._filter_to_query_models)
    rt._diversify_by_source_file = _wrap_filter("diversify_5a", rt._diversify_by_source_file)
    rt._diversify_by_manufacturer = _wrap_filter("diversify_mfr_5b", rt._diversify_by_manufacturer)
    rt._filter_by_language = _wrap_filter("language_5c", rt._filter_by_language)

    data = yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in data if g.get("qid")}

    report = []
    print("=== s79 death-STAGE del recall-cap (LIVE post-backfill, $0, flags OFF) ===\n")
    for qid in TARGETS:
        g = golds.get(qid)
        if not g:
            print(f"{qid}: NO ENCONTRADO"); continue
        quotes = [c["quote"] for c in (g.get("citations") or []) if c.get("quote")]
        _CUR.update({"quotes": quotes, "trace": [], "vec": set(), "kw": set(), "vec_rank": {}})

        models = rt.extract_product_models(g["question"])
        pool = rt.retrieve_chunks(g["question"], top_k=RETRIEVAL_TOP_K)
        in_pool = covered(pool, quotes)
        missing = set(range(len(quotes))) - in_pool

        # ¿las citas faltantes se retrievearon (search) o son miss vectorial puro?
        retrieved = _CUR["kw"] | _CUR["vec"]
        recall_vector_miss = missing - retrieved  # ni kw ni vec -> nunca recuperada
        died_in_filters = missing & retrieved      # recuperada pero filtrada/expulsada

        rec = {
            "qid": qid, "models_detected": models,
            "n_quotes": len(quotes), "n_in_pool": len(in_pool),
            "missing_quote_idx": sorted(missing),
            "retrieved_in_search": sorted(retrieved),
            "vec_rank_of_quotes": _CUR["vec_rank"],
            "recall_VECTORIAL_miss_idx": sorted(recall_vector_miss),
            "died_in_FILTERS_idx": sorted(died_in_filters),
            "stage_trace": [{"stage": t[0], "before": t[1], "after": t[2], "dropped": t[3]}
                            for t in _CUR["trace"]],
        }
        report.append(rec)

        print(f"{qid:7} modelos_detectados={models}")
        print(f"        citas={len(quotes)} en_pool={len(in_pool)} faltan={sorted(missing)}")
        print(f"        rank_vectorial_crudo_por_cita={_CUR['vec_rank']}")
        if recall_vector_miss:
            print(f"        >> RECALL-VECTORIAL puro (ni kw ni vec): citas {sorted(recall_vector_miss)}")
        if died_in_filters:
            print(f"        >> recuperadas pero MUERTAS en filtros: citas {sorted(died_in_filters)}")
        for t in _CUR["trace"]:
            print(f"           - stage {t[0]}: dropped citas {t[3]}  ({len(t[1])}->{len(t[2])} cubiertas)")
        print()

    p = ROOT / "evals" / "s79_recall_deathstage.json"
    p.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Reporte -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
