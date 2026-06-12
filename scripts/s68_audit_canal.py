#!/usr/bin/env python3
"""s68 — AUDIT de dimensionamiento del canal vectorial (DEC-049b, paso 0 del ciclo).

Responde las DOS preguntas pre-registradas ANTES de diseñar ningún lever:
  (a) ¿cuánto del residual s67base es alcanzable RÍO ARRIBA (canal: pool/orden,
      profundidad/corte, semántica)?
  (b) ¿cuánto es CALIDAD-DE-CHUNK (extracción/fragmentación — lever #10 post-hoc)?

Entrada (todo congelado, $0 de juez y $0 de embeddings):
  evals/s67base_gate_report.yaml      sufficiency per-hecho del residual answer
                                      (probes deterministas del D3 de bvg)
  evals/s67base_frozen_contexts.json  pool50_light + top5 servidos (el pool REAL)
  evals/s67_embed_cache.json          embeddings de las 39 queries (pin DEC-048c)

Método por hecho CORE-FUERTE faltante de la vista (in_top5=False):
  1. winners := chunks de fact_docs que matchean la probe (matcher del funnel:
     strict_match — MISMA semántica que sufficiency_for/s59_recall_diagnosis).
  2. ¿winner ∈ pool-50 servido?  →  EN-POOL-no-top5 (cuello: orden/top-5)
  3. si no: rank vectorial REAL del mejor winner (RPC match_chunks sin filtro,
     k=300, embedding del cache) →  RANK-51-110 (corte/profundidad) ·
     RANK-111-300 (canal-profundo) · SIN-RANK>300 (semántica/léxico)
     [rank≤50 sin estar en pool = lo comieron filtros/mezcla/diversify → señal fina]
  4. verdad geométrica: cos(query, winner) vs corte (#50 del canal) — si
     sim_winner ≥ corte y el RPC no lo sube, el cuello es índice (ef/HNSW).
  5. naturaleza del chunk winner (pregunta b): content_type, longitud,
     section_path, blurb → señal chunk-quality.
Hechos in_top5=True de golds que fallan → EN-TOP5-pero-falla (generación o
chunk-quality: se reporta la naturaleza del chunk servidor).
INDETERMINADO-solo-débiles (sin core fuerte) → no atribuible determinista;
se reporta la naturaleza del top-5 entero (señal b cualitativa).
fact-not-located mantiene la semántica del instrumento s58 (sospecha corpus-gap
en los docs objetivo; NO se re-verifica corpus-wide — declarado).
K-INESTABLES y CUALITATIVA quedan FUERA del scope (no-canal por naturaleza).

Read-only total. Salida: evals/s68_audit_canal.yaml + tabla por consola.
Uso: python scripts/s68_audit_canal.py [--qids cat001,...]
"""
from __future__ import annotations

import os

os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")

import argparse
import datetime
import json
import math
import subprocess
import sys
from collections import Counter
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, RPC_SUFFIX  # noqa: E402
from src.ingestion.embedder import embed_query  # noqa: E402
from strict_match import norm_ocr, anchor_present, chunk_has_quote_strict  # noqa: E402

F_REPORT = ROOT / "evals" / "s67base_gate_report.yaml"
F_CTX = ROOT / "evals" / "s67base_frozen_contexts.json"
OUT = ROOT / "evals" / "s68_audit_canal.yaml"

RANK_PROBE_K = 300
CUTOFF = 50
_HEADERS = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
_CHUNK_COLS = ("id,content,context,source_file,page_number,section_path,"
               "content_type,product_model,duplicate_of")


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


# --- matcher (MISMO que sufficiency_for/s59_recall_diagnosis: funnel estricto) --
def probe_kind(probe) -> tuple[str, object]:
    if isinstance(probe, list):
        return "anchors", [str(p) for p in probe]
    s = str(probe)
    return "quote", (s[1:] if s.startswith("~") else s)


def chunk_has(content: str, kind: str, probe) -> bool:
    if kind == "anchors":
        nc = norm_ocr(content or "")
        return all(anchor_present(a, nc) for a in probe)
    return chunk_has_quote_strict(content or "", str(probe))


# --- DB read-only ----------------------------------------------------------------
def fetch_doc_chunks(sources: list[str]) -> list[dict]:
    out, seen = [], set()
    for s in sources[:8]:
        try:
            with httpx.Client(timeout=30.0) as c:
                r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_HEADERS,
                          params={"select": _CHUNK_COLS,
                                  "source_file": f"ilike.*{s[:48]}*", "limit": "600"})
            if r.status_code in (200, 206):
                for row in r.json():
                    if row.get("id") not in seen and not row.get("duplicate_of"):
                        seen.add(row.get("id"))
                        out.append(row)
        except Exception:
            continue
    return out


def rpc_rank(query_embedding: list[float], k: int = RANK_PROBE_K) -> list[dict]:
    payload = {"query_embedding": query_embedding, "match_threshold": 0.0,
               "match_count": k, "filter_product": None,
               "filter_category": None, "filter_manufacturer": None}
    with httpx.Client(timeout=90.0) as c:
        r = c.post(f"{SUPABASE_URL}/rest/v1/rpc/match_chunks{RPC_SUFFIX}",
                   headers={**_HEADERS, "Content-Type": "application/json"}, json=payload)
        r.raise_for_status()
    return r.json()


def fetch_embeddings(ids: list[str]) -> dict[str, list[float]]:
    if not ids:
        return {}
    id_list = ",".join(f'"{i}"' for i in ids)
    with httpx.Client(timeout=60.0) as c:
        r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_HEADERS,
                  params={"select": "id,embedding", "id": f"in.({id_list})"})
        r.raise_for_status()
    out = {}
    for row in r.json():
        emb = row.get("embedding")
        if isinstance(emb, str):
            emb = json.loads(emb)
        if emb:
            out[row["id"]] = emb
    return out


def cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def naturaleza(c: dict) -> dict:
    content = c.get("content") or ""
    return {"id": c.get("id"), "source": c.get("source_file"),
            "page": c.get("page_number"), "section_path": c.get("section_path"),
            "content_type": c.get("content_type"), "len": len(content),
            "has_blurb": bool(c.get("context")),
            "frag_sospechosa": len(content) < 200,
            "preview": content[:140].replace("\n", " ")}


# --- audit por gold ----------------------------------------------------------------
def audit_gold(row: dict, ctx: dict) -> dict:
    qid = row["qid"]
    suff = row.get("sufficiency") or {}
    facts = suff.get("facts") or []
    pool_ids = [c.get("id") for c in ctx["pool50_light"]]
    top5 = ctx["top5"]
    q_emb = embed_query(ctx["question"])      # cache s67 → $0 API; miss = embebe y persiste

    # ranking vectorial real una vez por gold (k=300, sin filtro)
    ranked = rpc_rank(q_emb)
    rank_by_id = {r.get("id"): i + 1 for i, r in enumerate(ranked)}
    sim_corte = (ranked[CUTOFF - 1].get("similarity")
                 if len(ranked) >= CUTOFF else None)

    # winners por doc objetivo (los fact_docs de TODOS los per_fact + top5 sources)
    fact_docs = sorted({d for pf in ((suff.get("sub") or {}).get("per_fact") or [])
                        for d in (pf.get("fact_docs") or [])})
    doc_chunks = fetch_doc_chunks(fact_docs) if fact_docs else []

    hechos = []
    for f in facts:
        if f.get("strength") != "fuerte":
            continue
        kind, probe = probe_kind(f.get("probe"))
        if f.get("in_top5"):
            # el hecho ESTÁ servido y el gold aun así no es PASS → generación o chunk-quality
            serv = [c for c in top5 if chunk_has(c.get("content") or "", kind, probe)]
            hechos.append({"valor": f.get("valor"), "bucket": "EN-TOP5-pero-falla",
                           "chunk_servidor": naturaleza(serv[0]) if serv else None})
            continue
        winners = [c for c in doc_chunks if chunk_has(c.get("content") or "", kind, probe)]
        if not winners:
            hechos.append({"valor": f.get("valor"), "bucket": "NO-LOCALIZADO (sospecha gap)",
                           "fact_docs": fact_docs})
            continue
        w_ids = [w["id"] for w in winners]
        en_pool = [i for i in w_ids if i in pool_ids]
        if en_pool:
            pos = min(pool_ids.index(i) + 1 for i in en_pool)
            hechos.append({"valor": f.get("valor"), "bucket": "EN-POOL-no-top5",
                           "pos_en_pool": pos, "n_winners": len(winners),
                           "winner": naturaleza(next(w for w in winners
                                                     if w["id"] in en_pool))})
            continue
        ranks = sorted(rank_by_id.get(i) for i in w_ids if rank_by_id.get(i))
        best_rank = ranks[0] if ranks else None
        if best_rank and best_rank <= CUTOFF:
            bucket = "RANK<=50-fuera-de-pool (filtros/mezcla/diversify)"
        elif best_rank and best_rank <= 110:
            bucket = "RANK-51-110 (corte/profundidad)"
        elif best_rank:
            bucket = f"RANK-111-{RANK_PROBE_K} (canal-profundo)"
        else:
            bucket = f"SIN-RANK>{RANK_PROBE_K} (semantica/lexico)"
        embs = fetch_embeddings(w_ids[:5])
        best_sim = max((cos(q_emb, e) for e in embs.values()), default=None)
        indice_culpable = (best_sim is not None and sim_corte is not None
                           and best_sim >= sim_corte and (best_rank or 999) > CUTOFF)
        hechos.append({"valor": f.get("valor"), "bucket": bucket,
                       "best_rank_vectorial": best_rank,
                       "cos_winner": round(best_sim, 4) if best_sim is not None else None,
                       "cos_corte_50": round(sim_corte, 4) if sim_corte is not None else None,
                       "indice_culpable": indice_culpable,
                       "n_winners": len(winners),
                       "winner": naturaleza(winners[0])})

    solo_debiles = bool(facts) and not any(f.get("strength") == "fuerte" for f in facts)
    out = {"qid": qid, "atribucion_s67base": row.get("atribucion") or row.get("bucket"),
           "modal": row.get("veredicto"), "hechos_fuertes": hechos,
           "solo_debiles": solo_debiles}
    if solo_debiles or row.get("atribucion") == "INDETERMINADO-solo-debiles":
        out["naturaleza_top5"] = [naturaleza(c) for c in top5]
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--qids", default="")
    args = ap.parse_args()
    only = {q.strip() for q in args.qids.split(",") if q.strip()}

    report = yaml.safe_load(F_REPORT.read_text(encoding="utf-8"))
    ctxs = json.loads(F_CTX.read_text(encoding="utf-8"))

    scope, fuera = [], []
    for row in report["golds"]:
        b = row.get("bucket")
        if b == "PASS-control":
            continue
        if b == "K-INESTABLE" or "CUALITATIVA" in str(row.get("atribucion") or ""):
            fuera.append({"qid": row["qid"], "motivo": row.get("atribucion") or b})
            continue
        scope.append(row)
    if only:
        scope = [r for r in scope if r["qid"] in only]

    print(f"audit | scope={len(scope)} residual-answer | fuera={len(fuera)} (KI/cualitativa)")
    golds_out = []
    for row in sorted(scope, key=lambda r: r["qid"]):
        g = audit_gold(row, ctxs[row["qid"]])
        golds_out.append(g)
        resumen = Counter(h["bucket"].split(" ")[0] for h in g["hechos_fuertes"])
        print(f"  {g['qid']:8} [{g['atribucion_s67base']:<28}] "
              f"{dict(resumen) if resumen else '(sin core fuerte → señal b)'}")

    # --- agregación: techo por lever (a nivel GOLD: por su peor-hecho dominante) ---
    bucket_hechos = Counter(h["bucket"] for g in golds_out for h in g["hechos_fuertes"])
    techo = Counter()
    for g in golds_out:
        bs = {h["bucket"] for h in g["hechos_fuertes"]}
        if not bs:
            techo["solo-debiles (señal chunk-quality, no atribuible)"] += 1
        elif all(b == "EN-TOP5-pero-falla" for b in bs):
            techo["generacion-o-chunk-quality (todo servido)"] += 1
        elif any("NO-LOCALIZADO" in b for b in bs):
            techo["con-sospecha-gap"] += 1
        elif all(b.startswith(("EN-POOL", "EN-TOP5", "RANK<=50")) for b in bs):
            techo["alcanzable-en-pool (orden/top5)"] += 1
        elif all(b.startswith(("EN-POOL", "EN-TOP5", "RANK")) for b in bs):
            techo["alcanzable-con-profundidad (canal río arriba)"] += 1
        else:
            techo["mixto-con-semantica"] += 1

    out = {"meta": {"at": _now(), "git": _git(),
                    "fuente": "s67base (sufficiency D3) + pool50 congelado + embed-cache s67",
                    "preguntas": "DEC-049b (a) canal vs (b) chunk-quality",
                    "fuera_de_scope": fuera,
                    "nota": ("read-only; rank vectorial real RPC k=300 sin filtro; "
                             "NO-LOCALIZADO mantiene la semántica s58 (docs objetivo, "
                             "no corpus-wide)")},
           "techo_por_lever_GOLDS": dict(techo),
           "buckets_HECHOS": dict(bucket_hechos),
           "golds": golds_out}
    OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=110),
                   encoding="utf-8")
    print("\n=== TECHO POR LEVER (golds) ===")
    for k, v in techo.most_common():
        print(f"  {v:2d}  {k}")
    print(f"=== buckets por HECHO ===\n  {dict(bucket_hechos)}")
    print(f"\n→ {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
