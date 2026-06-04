#!/usr/bin/env python3
"""_s44_dimension_burial.py — DEC-016 s44: dimensionar el "burial" a nivel de CHUNK/HECHO.

EVAL-ONLY. No toca producción, no commitea, no upsert. Mide, sobre los hechos en
bucket RETRIEVAL del funnel (audit_retrieval_funnel), cuántos son:

  BURIAL (A2-addressable): el chunk del corpus que CONTIENE el valor del hecho
     aparece en una búsqueda VECTORIAL PURA (coseno real, top-50, HyDE-off) con
     buen rango → el dato SÍ se recupera por vector, pero el merge plano
     (similitudes estampadas 0.65/0.80/0.82/0.85 + merged.sort) lo entierra fuera
     del pool-15. A2 (fusión por sim real / RRF) lo rescataría.
  RECALL-MISS (A2 NO ayuda): esos chunks NO aparecen en vector top-50 → recall
     genuino (embedding/chunking/term-exacto). A2 no lo arregla.

Reutiliza EXACTAMENTE el matcher del funnel (fact_probe / _chunk_has) y su
clasificación de bucket (re-corre el funnel inline por qid para no hardcodear).
Para cada hecho en RETRIEVAL, busca el rango vectorial real del/los chunk(s) que
contienen el valor.

Complementario (--restamp): re-estampa la sim REAL (coseno query·embedding, col
`embedding` de chunks_v2) sobre TODOS los candidatos del pool reconstruido ANTES
del sort, conservando las guardas (lifecycle/idioma/modelo/diversify), re-corre la
clasificación y reporta cuántos hechos pasan de RETRIEVAL→pool15/top5.

Uso:
  python scripts/_s44_dimension_burial.py
  python scripts/_s44_dimension_burial.py --dump hp019   # validación Rule C de un caso
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import json
import math
import sys
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.config import CHUNKS_IS_V2, SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag.retriever import (retrieve_chunks, extract_product_models,  # noqa: E402
                               vector_search)
from src.rag.reranker import rerank_chunks  # noqa: E402
from src.rag.hyde import HYDE_ENABLED  # noqa: E402
from src.ingestion.embedder import embed_query  # noqa: E402

# Reusar el matcher y los helpers EXACTOS del funnel (no duplicar lógica).
from scripts.audit_retrieval_funnel import (  # noqa: E402
    fact_probe, _chunk_has, present_in, target_servable, fetch_manual_chunks,
    source_matches_target, classify, RETRIEVE_K, RERANK_K,
)
from scripts.strict_match import norm_ocr  # noqa: E402

GOLD = ROOT / "evals" / "gold_answers_v1.yaml"
OUT = ROOT / "evals" / "_s44_burial_dimensioned.yaml"

QIDS = ["hp005", "hp006", "hp008", "hp009", "hp011", "hp013", "hp019"]

_HDR = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

VEC_WIDE_K = 50
TOP15 = 15  # "vector-top-15" = burial fuerte; 16-50 = burial marginal


def _parse_emb(v) -> list[float] | None:
    if v is None:
        return None
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return None


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return float("nan")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return float("nan")
    return dot / (na * nb)


def fetch_embeddings_by_ids(ids: list[str]) -> dict[str, list[float]]:
    """Trae la columna `embedding` para un conjunto de chunk ids (el SELECT del
    funnel/vector_search NO la trae). Batch via in.()."""
    out: dict[str, list[float]] = {}
    ids = [i for i in ids if i]
    for i in range(0, len(ids), 80):
        batch = ids[i:i + 80]
        id_list = ",".join(f'"{x}"' for x in batch)
        try:
            with httpx.Client(timeout=30.0) as c:
                r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_HDR,
                          params={"id": f"in.({id_list})", "select": "id,embedding"})
            if r.status_code in (200, 206):
                for row in r.json():
                    emb = _parse_emb(row.get("embedding"))
                    if emb:
                        out[row["id"]] = emb
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------------
# Núcleo: para un qid, recomputa el funnel (buckets) + mide rango vectorial real.
# ---------------------------------------------------------------------------
def analyze_qid(qid: str, golds: dict, vec_emb_query: list[float],
                wide_vec: list[dict]) -> list[dict]:
    g = golds[qid]
    q = g["question"]

    # --- 1. Reproducir el embudo del funnel (idéntico) ---
    pool = retrieve_chunks(q, top_k=RETRIEVE_K)
    top5 = rerank_chunks(q, pool, top_k=RERANK_K, target_models=None)  # como el A/B (sin target_models)

    pool_src = [c.get("source_file") for c in pool]
    servable, srv = target_servable(g)
    targets = srv["target_tokens"]
    fetch_tokens = targets or sorted({s for s in pool_src if s})
    manual_chunks = fetch_manual_chunks(fetch_tokens)

    # --- 2. Vector PURO top-50 (coseno real, HyDE-off): rangos por chunk-con-valor ---
    # wide_vec ya viene calculado (vector_search(q, top_k=50)).
    out_facts = []
    for f in g.get("atomic_facts") or []:
        if f.get("tipo") != "core" or f.get("estado") != "presente":
            continue
        kind, probe, strength = fact_probe(f.get("valor", ""), f.get("texto", ""))
        in_top5 = present_in(top5, kind, probe)
        in_pool = present_in(pool, kind, probe)
        in_corpus = in_pool or present_in(manual_chunks, kind, probe)
        bucket = classify(in_top5, in_pool, in_corpus)
        if bucket != "RETRIEVAL":
            continue  # solo nos interesa el bucket RETRIEVAL

        # rangos vectoriales de los chunks que CONTIENEN el valor (matcher idéntico)
        vec_hits = [(i, c.get("source_file"), round(c.get("similarity", 0), 4), c.get("id"))
                    for i, c in enumerate(wide_vec)
                    if _chunk_has(c.get("content") or "", kind, probe)]
        best_rank = vec_hits[0][0] if vec_hits else None
        in_vec_top15 = any(i < TOP15 for i, *_ in vec_hits)
        in_vec_top50 = bool(vec_hits)

        # --- TARGET-CONSTRAINED (anti-artefacto Rule C): un hit solo cuenta si el
        # chunk-con-valor pertenece al MANUAL OBJETIVO del gold (mismas target_tokens
        # que usa el funnel para servabilidad). Sin esto, un quote débil ("Fallo de
        # Tierra", "Retorno", "enclavadas") matchea por substring en CUALQUIER manual
        # que contenga la palabra común → inflaba BURIAL. Los hechos FUERTES (anchors
        # de modelo/num) son inmunes; los débiles necesitan esta atadura.
        vec_hits_tgt = [h for h in vec_hits if source_matches_target(h[1] or "", targets)]
        best_rank_tgt = vec_hits_tgt[0][0] if vec_hits_tgt else None
        in_vec_top15_tgt = any(i < TOP15 for i, *_ in vec_hits_tgt)
        in_vec_top50_tgt = bool(vec_hits_tgt)

        def _verdict(t15, t50):
            if t15:
                return "BURIAL-fuerte"
            if t50:
                return "BURIAL-marginal"
            return "RECALL-MISS"

        verdict = _verdict(in_vec_top15, in_vec_top50)            # cualquier manual (laxo)
        verdict_tgt = _verdict(in_vec_top15_tgt, in_vec_top50_tgt)  # solo manual objetivo (estricto)

        out_facts.append({
            "qid": qid,
            "valor": f.get("valor"),
            "probe": sorted(probe) if kind == "anchors" else f"~{probe}",
            "strength": strength,
            "in_vec_top15": in_vec_top15,
            "in_vec_top50": in_vec_top50,
            "best_vec_rank": best_rank,
            "vec_hits": vec_hits[:3],
            "verdict": verdict,
            # target-constrained
            "in_vec_top15_tgt": in_vec_top15_tgt,
            "in_vec_top50_tgt": in_vec_top50_tgt,
            "best_vec_rank_tgt": best_rank_tgt,
            "vec_hits_tgt": vec_hits_tgt[:3],
            "verdict_tgt": verdict_tgt,
            "targets": targets,
        })
    return out_facts


# ---------------------------------------------------------------------------
# Complementario: re-estampar coseno REAL sobre el pool y re-clasificar.
# ---------------------------------------------------------------------------
def restamp_qid(qid: str, golds: dict, vec_emb_query: list[float]) -> dict:
    """Re-estampa sim REAL sobre los candidatos del pool-15 que devuelve
    retrieve_chunks (los que sobrevivieron guardas/diversify), re-ordena por
    coseno real, y re-clasifica los hechos RETRIEVAL.

    CAVEAT honesto: retrieve_chunks ya devuelve merged[:15], así que esto re-ordena
    SOLO dentro del pool-15 superviviente (no re-rescata candidatos que el sort
    plano expulsó del top-15 antes de las guardas). Por eso el rango vectorial
    top-50 (analyze_qid) es la señal PRIMARIA; el re-stamp es confirmación parcial
    del mecanismo 'el orden plano es el que entierra' DENTRO del pool observable.
    """
    g = golds[qid]
    q = g["question"]
    pool = retrieve_chunks(q, top_k=RETRIE_K_FULL)
    # fetch embeddings reales de los chunks del pool
    ids = [c.get("id") for c in pool]
    embmap = fetch_embeddings_by_ids(ids)
    restamped = []
    for c in pool:
        e = embmap.get(c.get("id"))
        cos = cosine(vec_emb_query, e) if e else float("nan")
        cc = dict(c)
        cc["_flat_sim"] = c.get("similarity")
        cc["_real_cos"] = cos
        restamped.append(cc)
    # re-ordenar por coseno real (los NaN — sin embedding — al fondo)
    restamped.sort(key=lambda c: (c["_real_cos"] if not math.isnan(c["_real_cos"]) else -1),
                   reverse=True)
    new_top5 = restamped[:RERANK_K]
    new_pool = restamped[:RETRIE_K_FULL]

    servable, srv = target_servable(g)
    targets = srv["target_tokens"]
    fetch_tokens = targets or sorted({c.get("source_file") for c in pool if c.get("source_file")})
    manual_chunks = fetch_manual_chunks(fetch_tokens)

    moved = []
    for f in g.get("atomic_facts") or []:
        if f.get("tipo") != "core" or f.get("estado") != "presente":
            continue
        kind, probe, strength = fact_probe(f.get("valor", ""), f.get("texto", ""))
        # bucket original (orden plano)
        in_pool_flat = present_in(pool, kind, probe)
        in_corpus = in_pool_flat or present_in(manual_chunks, kind, probe)
        # NB: top5 plano = rerank; aquí aproximamos bucket plano por el funnel (analyze_qid lo da exacto)
        # re-estampado
        in_pool_real = present_in(new_pool, kind, probe)
        in_top5_real = present_in(new_top5, kind, probe)
        if not in_corpus:
            continue
        moved.append({
            "valor": f.get("valor"), "strength": strength,
            "in_pool15_flat": in_pool_flat,
            "in_pool15_realcos": in_pool_real,
            "in_top5_realcos": in_top5_real,
        })
    return {"qid": qid, "facts": moved, "n_with_emb": len(embmap), "n_pool": len(pool)}


RETRIE_K_FULL = 15


def do_dump(qid: str, golds: dict, vec_emb_query: list[float], wide_vec: list[dict]) -> None:
    """Validación Rule C: para cada hecho RETRIEVAL del qid, vuelca el/los chunk(s)
    que contienen el valor + su rango vectorial real. Confirma que la clasificación
    no es artefacto del matcher."""
    g = golds[qid]
    q = g["question"]
    print(f"\n########## DUMP {qid}: {q} ##########\n")
    facts = analyze_qid(qid, golds, vec_emb_query, wide_vec)
    for fr in facts:
        print(f"--- HECHO: {fr['valor']!r}  [{fr['strength']}]  probe={fr['probe']}  -> {fr['verdict']}")
        print(f"    best_vec_rank={fr['best_vec_rank']}  in_top15={fr['in_vec_top15']}  in_top50={fr['in_vec_top50']}")
        if fr["vec_hits"]:
            for rank, src, sim, cid in fr["vec_hits"]:
                # volcar el contenido del chunk que matchea (validación del matcher)
                chunk = wide_vec[rank]
                content = " ".join((chunk.get("content") or "").split())
                # resaltar el anchor
                print(f"      vec#{rank:02d} sim={sim} src={src} p{chunk.get('page_number')}")
                print(f"        content[:350]: {content[:350]}")
        else:
            print("      (ningún chunk en vector top-50 contiene el valor → RECALL-MISS)")
        print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default="", help="qid: volcar chunks-con-valor + rango vectorial (Rule C)")
    ap.add_argument("--restamp", action="store_true", help="además, re-estampar coseno real sobre el pool")
    args = ap.parse_args()

    assert CHUNKS_IS_V2, "CHUNKS_TABLE debe ser chunks_v2"
    assert not HYDE_ENABLED, "HyDE debe estar OFF"

    golds = {g["qid"]: g for g in yaml.safe_load(GOLD.read_text(encoding="utf-8"))}

    print(f"chunks_v2 | HyDE OFF | vector PURO top-{VEC_WIDE_K} (coseno real) | "
          f"BURIAL si chunk-con-valor en vector top-50\n")

    # precomputar embedding de query (Voyage input_type=query) y vector top-50 por qid
    qid_list = [args.dump] if args.dump else QIDS
    wide_by_qid = {}
    embq_by_qid = {}
    for qid in qid_list:
        q = golds[qid]["question"]
        embq = embed_query(q)  # HyDE-off → embedding de la query cruda (igual que el vector path de prod)
        embq_by_qid[qid] = embq
        wide_by_qid[qid] = vector_search(q, top_k=VEC_WIDE_K, precomputed_embedding=embq)

    if args.dump:
        do_dump(args.dump, golds, embq_by_qid[args.dump], wide_by_qid[args.dump])
        return 0

    all_facts = []
    for qid in QIDS:
        facts = analyze_qid(qid, golds, embq_by_qid[qid], wide_by_qid[qid])
        all_facts.extend(facts)

    # --- Tabla por-hecho (dos veredictos: laxo=cualquier manual, tgt=solo manual objetivo) ---
    print("=" * 110)
    print("TABLA POR-HECHO (bucket RETRIEVAL del funnel) — vecRank=cualquier manual | vecRankTGT=solo manual objetivo")
    print("=" * 110)
    print(f"{'qid':6} {'F':1} {'valor':22} {'vRank':6} {'vRankTGT':9} {'verdicto(laxo)':16} {'verdicto(TGT)':16}")
    print("-" * 110)
    for fr in all_facts:
        F = "F" if fr["strength"] == "fuerte" else "·"
        rank = str(fr["best_vec_rank"]) if fr["best_vec_rank"] is not None else "-"
        rankt = str(fr["best_vec_rank_tgt"]) if fr["best_vec_rank_tgt"] is not None else "-"
        print(f"{fr['qid']:6} {F:1} {str(fr['valor'])[:22]:22} {rank:6} {rankt:9} "
              f"{fr['verdict']:16} {fr['verdict_tgt']:16}")

    # --- Agregado: doble (laxo y target-constrained) ---
    def _tally(key):
        burial = [f for f in all_facts if f[key].startswith("BURIAL")]
        recall = [f for f in all_facts if f[key] == "RECALL-MISS"]
        return {
            "burial": len(burial),
            "burial_F": len([f for f in burial if f["strength"] == "fuerte"]),
            "burial_top15": len([f for f in all_facts if f[key] == "BURIAL-fuerte"]),
            "burial_marg": len([f for f in all_facts if f[key] == "BURIAL-marginal"]),
            "recall": len(recall),
            "recall_F": len([f for f in recall if f["strength"] == "fuerte"]),
        }

    n_total = len(all_facts)
    n_fuerte = sum(1 for f in all_facts if f["strength"] == "fuerte")
    lax = _tally("verdict")
    tgt = _tally("verdict_tgt")

    print("\n" + "=" * 110)
    print(f"AGREGADO — RETRIEVAL bucket: {n_total} hechos ({n_fuerte} fuertes)\n")
    print("                                BURIAL (A2-addressable)         RECALL-MISS (A2 no ayuda)")
    print(f"  LAXO (cualquier manual):      {lax['burial']:2} ({lax['burial_F']} fuertes) "
          f"[top15={lax['burial_top15']}, 16-50={lax['burial_marg']}]      "
          f"{lax['recall']:2} ({lax['recall_F']} fuertes)")
    print(f"  TGT  (solo manual objetivo):  {tgt['burial']:2} ({tgt['burial_F']} fuertes) "
          f"[top15={tgt['burial_top15']}, 16-50={tgt['burial_marg']}]      "
          f"{tgt['recall']:2} ({tgt['recall_F']} fuertes)")
    print("\n  >>> TECHO DE A2: el LAXO sobreestima (matchea palabras comunes en OTROS manuales);")
    print("      el TGT es defendible. Los hechos FUERTES son inmunes al artefacto (anchors de modelo/num).")
    burial = [f for f in all_facts if f["verdict"].startswith("BURIAL")]
    burial_strong = [f for f in all_facts if f["verdict"] == "BURIAL-fuerte"]
    burial_marg = [f for f in all_facts if f["verdict"] == "BURIAL-marginal"]
    recall_miss = [f for f in all_facts if f["verdict"] == "RECALL-MISS"]
    burial_F = [f for f in burial if f["strength"] == "fuerte"]
    recall_F = [f for f in recall_miss if f["strength"] == "fuerte"]

    out = {
        "config": "chunks_v2 | HyDE-off | vector puro top-50 coseno real",
        "n_retrieval_facts": n_total,
        "n_retrieval_fuertes": n_fuerte,
        "tally_laxo_cualquier_manual": lax,
        "tally_tgt_solo_manual_objetivo": tgt,
        "facts": all_facts,
    }

    if args.restamp:
        print("\n" + "=" * 100)
        print("COMPLEMENTARIO — re-estampar coseno real sobre el pool-15 superviviente:")
        restamp_out = []
        for qid in QIDS:
            r = restamp_qid(qid, golds, embq_by_qid[qid])
            restamp_out.append(r)
            for fr in r["facts"]:
                tag = ""
                if fr["in_pool15_realcos"] and not fr["in_pool15_flat"]:
                    tag = "  <<RESCATADO al pool por coseno real"
                print(f"  {qid} {fr['valor'][:30]:30} flat_pool={fr['in_pool15_flat']} "
                      f"real_pool={fr['in_pool15_realcos']} real_top5={fr['in_top5_realcos']}{tag}")
        out["restamp"] = restamp_out

    OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"\nDetalle: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
