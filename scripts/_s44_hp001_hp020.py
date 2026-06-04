#!/usr/bin/env python3
"""_s44_hp001_hp020.py — DEC-016 s44: atribuir el FALLO de hp001 y hp020 a uno de
tres mecanismos (SÍNTESIS-over-admit / BURIAL / RECALL-MISS).

EVAL-ONLY. No toca producción, no commitea, no upsert.

Reutiliza EXACTAMENTE el embudo (retrieve_chunks+rerank_chunks) y el matcher
(fact_probe/_chunk_has/present_in) del funnel + la búsqueda vectorial pura top-50
de _s44_dimension_burial.py. Para cada HECHO core fallido:

  - SÍNTESIS/over-admit (NO A2-addressable): el chunk con el dato llega al TOP-5
    del embudo → el bot lo tenía y aun así eligió mal/over-admitió → generación.
  - BURIAL (A2-addressable): el chunk está en vector-top-50 pero no en pool-15
    (enterrado por scores planos).
  - RECALL-MISS (A2 no ayuda): el chunk ni en vector-top-50.

A diferencia de _s44_dimension_burial.py (que solo mira hechos en bucket RETRIEVAL),
aquí dumpeamos TODOS los hechos core, porque la hipótesis de trabajo es que estos
dos casos son SÍNTESIS (chunk en top5) — el funnel manda, el vector-50 contextualiza.

Multi-doc (hp001): muestro el rango del chunk-con-2222 (admin/MC-380) frente al
chunk-con-1111 (usuario/MU-376) para ver si el bot tenía ambos y eligió el de usuario.

Uso:
  python scripts/_s44_hp001_hp020.py
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import sys
from pathlib import Path

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

from src.config import CHUNKS_IS_V2  # noqa: E402
from src.rag.retriever import retrieve_chunks, vector_search  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402
from src.rag.hyde import HYDE_ENABLED  # noqa: E402
from src.ingestion.embedder import embed_query  # noqa: E402

from scripts.audit_retrieval_funnel import (  # noqa: E402
    fact_probe, _chunk_has, present_in, target_servable, fetch_manual_chunks,
    source_matches_target, classify, RETRIEVE_K, RERANK_K,
)
from scripts.strict_match import norm_ocr  # noqa: E402

GOLD = ROOT / "evals" / "gold_answers_v1.yaml"
VEC_WIDE_K = 50
TOP15 = 15

QIDS = ["hp001", "hp020"]


def _rank_in(chunks: list[dict], kind, probe) -> int | None:
    """Índice (0-based) del PRIMER chunk de la lista que contiene el dato, o None."""
    for i, c in enumerate(chunks):
        if _chunk_has(c.get("content") or "", kind, probe):
            return i
    return None


def _short(content: str, n: int = 320) -> str:
    return " ".join((content or "").split())[:n]


def mechanism(in_top5: bool, in_pool15: bool, in_vec50: bool) -> str:
    """Mecanismo del FALLO para un hecho que el manual SÍ tiene."""
    if in_top5:
        return "SINTESIS/over-admit (chunk EN top-5 → el bot lo tenía)"
    if in_pool15 or in_vec50:
        return "BURIAL (en pool-15/vec-50 pero no top-5 → A2-addressable)"
    return "RECALL-MISS (ni en vector top-50 → A2 no ayuda)"


def analyze(qid: str, golds: dict) -> None:
    g = golds[qid]
    q = g["question"]
    print("\n" + "#" * 100)
    print(f"# {qid}: {q}")
    print("#" * 100)

    # --- Embudo idéntico al funnel / al A/B (sin target_models, HyDE-off) ---
    pool = retrieve_chunks(q, top_k=RETRIEVE_K)        # pool-15
    top5 = rerank_chunks(q, pool, top_k=RERANK_K, target_models=None)

    # --- Vector PURO top-50 (coseno real, HyDE-off) ---
    embq = embed_query(q)
    wide = vector_search(q, top_k=VEC_WIDE_K, precomputed_embedding=embq)

    # --- Manual objetivo (servabilidad a nivel de hecho) ---
    servable, srv = target_servable(g)
    targets = srv["target_tokens"]
    fetch_tokens = targets or sorted({c.get("source_file") for c in pool if c.get("source_file")})
    manual_chunks = fetch_manual_chunks(fetch_tokens)

    pool_src = sorted({c.get("source_file") for c in pool if c.get("source_file")})
    top_src = [c.get("source_file") for c in top5]
    print(f"\ntargets={targets}")
    print(f"top5_src     = {top_src}")
    print(f"pool15_src   = {pool_src}")
    print(f"manual_chunks (objetivo) fetched = {len(manual_chunks)}")

    # --- Por cada hecho core (presente): bucket del funnel + rango vectorial ---
    print("\n" + "=" * 100)
    print("HECHOS CORE (estado=presente) — bucket del embudo + rango vector-50")
    print("=" * 100)
    for f in g.get("atomic_facts") or []:
        if f.get("tipo") != "core" or f.get("estado") != "presente":
            continue
        kind, probe, strength = fact_probe(f.get("valor", ""), f.get("texto", ""))
        pr = sorted(probe) if kind == "anchors" else f"~{probe}"

        rank_top5 = _rank_in(top5, kind, probe)
        rank_pool = _rank_in(pool, kind, probe)
        in_top5 = rank_top5 is not None
        in_pool = rank_pool is not None
        in_manual = in_pool or present_in(manual_chunks, kind, probe)
        bucket = classify(in_top5, in_pool, in_manual)

        # rango en vector-50 (laxo = cualquier manual) + target-constrained
        vec_hits = [(i, c.get("source_file"), round(c.get("similarity", 0), 4), c.get("page_number"))
                    for i, c in enumerate(wide)
                    if _chunk_has(c.get("content") or "", kind, probe)]
        vec_hits_tgt = [h for h in vec_hits if source_matches_target(h[1] or "", targets)]
        rank_vec = vec_hits[0][0] if vec_hits else None
        rank_vec_tgt = vec_hits_tgt[0][0] if vec_hits_tgt else None
        in_vec50 = bool(vec_hits)
        in_vec50_tgt = bool(vec_hits_tgt)

        mech = mechanism(in_top5, in_pool, in_vec50_tgt)

        print(f"\n--- HECHO valor={f.get('valor')!r} [{strength}] probe={pr}")
        print(f"    cita_gold={f.get('cita')}")
        print(f"    BUCKET(funnel)={bucket} | rank_top5={rank_top5} rank_pool15={rank_pool}")
        print(f"    vec50: rank(laxo)={rank_vec} rank(TGT-manual-objetivo)={rank_vec_tgt}")
        print(f"    >>> MECANISMO: {mech}")
        if vec_hits_tgt:
            for rank, src, sim, pg in vec_hits_tgt[:2]:
                print(f"        [TGT] vec#{rank:02d} sim={sim} src={src} p{pg}")
                print(f"              {_short(wide[rank].get('content'))}")
        elif vec_hits:
            for rank, src, sim, pg in vec_hits[:2]:
                print(f"        [laxo, OTRO manual] vec#{rank:02d} sim={sim} src={src} p{pg}")
                print(f"              {_short(wide[rank].get('content'))}")
        else:
            print("        (ningún chunk en vector-50 contiene el dato)")

    # --- Validación Rule C: ¿dónde vive el dato CORRECTO en el manual objetivo? ---
    # (búsqueda directa en manual_chunks, independiente del retrieval, para confirmar
    #  que el hecho EXISTE en el corpus y dónde — cierra el critico 'el manual existe
    #  pero ¿el chunk tiene el dato?')
    print("\n" + "=" * 100)
    print("RULE C — ¿el dato CORRECTO existe en el manual objetivo? (búsqueda directa en manual_chunks)")
    print("=" * 100)
    if qid == "hp001":
        probes_c = [("2222 (ADMIN, correcto)", "anchors", {"2222"}),
                    ("1111 (USUARIO, lo que dio el bot)", "anchors", {"1111"}),
                    ("PANTALLA DE ADMINISTRADOR", "quote", "PANTALLA DE ADMINISTRADOR")]
    else:
        probes_c = [("Cambio del codigo de acceso", "quote", "Cambio del codigo de acceso"),
                    ("nivel de acceso 3 ... 2 o 3 (regla N3)", "quote", "nivel de acceso 2 o 3"),
                    ("satisfactorio (mensaje de exito)", "quote", "satisfactorio"),
                    ("4 y 8 (longitud)", "quote", "4 y 8")]
    for label, kind, probe in probes_c:
        hits = [c for c in manual_chunks if _chunk_has(c.get("content") or "", kind, probe)]
        print(f"\n  >> '{label}': {len(hits)} chunk(s) en el manual objetivo")
        for c in hits[:3]:
            print(f"     src={c.get('source_file')} p{c.get('page_number')} id={c.get('id')}")
            print(f"     {_short(c.get('content'), 360)}")
        # ¿alguno de esos chunks-con-dato está en el pool-15 / top-5 / vec-50?
        if hits:
            ids_with = {c.get("id") for c in hits}
            in_t5 = [i for i, c in enumerate(top5) if c.get("id") in ids_with]
            in_p15 = [i for i, c in enumerate(pool) if c.get("id") in ids_with]
            in_v50 = [i for i, c in enumerate(wide) if c.get("id") in ids_with]
            print(f"     -> ¿chunk-con-dato en TOP5?={in_t5}  POOL15?={in_p15}  VEC50?={in_v50}")


def main() -> int:
    assert CHUNKS_IS_V2, "CHUNKS_TABLE debe ser chunks_v2"
    assert not HYDE_ENABLED, "HyDE debe estar OFF"
    golds = {g["qid"]: g for g in yaml.safe_load(GOLD.read_text(encoding="utf-8"))}
    print(f"chunks_v2 | HyDE OFF | retrieve={RETRIEVE_K} rerank={RERANK_K} | vector puro top-{VEC_WIDE_K} (coseno real)")
    for qid in QIDS:
        analyze(qid, golds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
