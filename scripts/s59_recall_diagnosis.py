#!/usr/bin/env python3
"""s59_recall_diagnosis.py — s59(a): POR QUE los 14 hechos RECALL no llegan al pool-50.

Lee el funnel CONGELADO de s58b (evals/dec003_retrieval_funnel_noTgt_llm.yaml) y,
para cada hecho FUERTE con bucket=RETRIEVAL (los 14 de DEC-039g), localiza los
chunks de chunks_v2 que SI contienen el hecho ("winners", mismo matcher estricto
del funnel) y mide canal a canal por que el retriever no los sube:

  senal 1 — canal vectorial (replica): rank del winner en match_chunks_v2 SIN
            filtro y CON filter_category=detected (la que aplica el bot). Es el
            RPC + indice HNSW de prod, no una simulacion.
  senal 2 — verdad geometrica: cos-sim local query<->winner usando el embedding
            ALMACENADO del chunk, comparado con el corte (#50 del canal sin
            filtro). Si sim_winner >= corte y el RPC no lo devuelve, el cuello
            es el INDICE (ef_search/HNSW), no la semantica del embedding.
  senal 3 — canales lexicos: ¿alguna keyword de la query (extract_search_keywords,
            las mismas <=3 del bot) esta en el content del winner (ilike)?
            ¿el product_model del winner pasa el imatch (canales model-scoped)
            y el filtro #11e (_filter_to_query_models)? ¿el FTS
            (search_chunks_text_v2) lo devuelve con la query completa?
  senal 4 — naturaleza del chunk: section_path, content_type, longitud, blurb
            (context) y preview -> senal de chunking/tabla-sin-contexto.

NO re-corre el pool-50 (la referencia congelada es el YAML de s58b) y NO toca el
corpus (freeze s58 vigente): todo es read-only.

Uso:    python scripts/s59_recall_diagnosis.py [--qids cat001,hp008]
Salida: evals/s59_recall_diagnosis.yaml + tabla por consola.
"""
from __future__ import annotations

import os
# chunks_v2 + HyDE OFF ANTES de importar config/retriever (leen el env al cargar).
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import json
import math
import re
import subprocess
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

from src.config import (CHUNKS_IS_V2, SUPABASE_URL, SUPABASE_SERVICE_KEY,  # noqa: E402
                        RPC_SUFFIX)
from src.ingestion.embedder import embed_query  # noqa: E402
from src.rag.retriever import (extract_product_models, extract_search_keywords,  # noqa: E402
                               _CATEGORY_PHRASES, CATEGORY_TERMS, QUERY_SYNONYMS,
                               SPEC_INTENT, TROUBLESHOOT_INTENT, WIRING_INTENT)
from scripts.strict_match import norm_ocr, anchor_present, chunk_has_quote_strict  # noqa: E402

FUNNEL = ROOT / "evals" / "dec003_retrieval_funnel_noTgt_llm.yaml"
GOLD = ROOT / "evals" / "gold_answers_v1.yaml"
OUT = ROOT / "evals" / "s59_recall_diagnosis.yaml"

RANK_PROBE_K = 300   # cuanto canal vectorial mirar mas alla del 50 (diagnostico)
CUTOFF_RANK = 50     # el pool de prod (RETRIEVAL_TOP_K)

_HEADERS = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def _git_commit() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


# --- probes (reconstruidos del YAML congelado — mismo matcher del funnel) -----
def probe_from_yaml(probe) -> tuple[str, object]:
    """El funnel serializa anchors como lista y quotes como '~texto'."""
    if isinstance(probe, list):
        return "anchors", set(str(p) for p in probe)
    s = str(probe)
    return "quote", (s[1:] if s.startswith("~") else s)


def chunk_has(content: str, kind: str, probe) -> bool:
    if kind == "anchors":
        nc = norm_ocr(content or "")
        return all(anchor_present(a, nc) for a in probe)
    return chunk_has_quote_strict(content or "", str(probe))


# --- replica de la deteccion de categoria del bot (retrieve_chunks Step 1b) ---
def detect_category(query: str) -> str | None:
    ql = query.lower()
    for phrase, cat in _CATEGORY_PHRASES:
        if phrase in ql:
            return cat
    for term, cat in CATEGORY_TERMS.items():
        if term in ql:
            return cat
    return None


# --- replica de model_to_imatch_pattern en regex Python -----------------------
def pm_imatch(model: str, product_model: str) -> bool:
    """¿product_model (almacenado) matchea el patron imatch que el bot genera
    para `model`? Replica model_to_imatch_pattern: separadores opcionales,
    boundary inicial, sin extension por digito."""
    parts = [p for p in re.split(r"[- ]+", model.strip()) if p]
    if not parts or not product_model:
        return False
    core = r"[- ]*".join(re.escape(p) for p in parts)
    return re.search(rf"(?<![A-Za-z0-9]){core}(?!\d)", product_model, re.IGNORECASE) is not None


def filter11e_pass(models: list[str], product_model: str) -> bool:
    """Replica _filter_to_query_models: normaliza quitando [- ] y pide substring."""
    def norm(s: str) -> str:
        return re.sub(r"[- ]", "", s or "").lower()
    pm = norm(product_model or "")
    return any(norm(m) in pm for m in models if m)


# --- Supabase ------------------------------------------------------------------
def rpc_match_chunks(query_embedding: list[float], match_count: int,
                     threshold: float, category: str | None) -> list[dict]:
    payload = {
        "query_embedding": query_embedding,
        "match_threshold": threshold,
        "match_count": match_count,
        "filter_product": None,
        "filter_category": category,
        "filter_manufacturer": None,
    }
    with httpx.Client(timeout=60.0) as c:
        r = c.post(f"{SUPABASE_URL}/rest/v1/rpc/match_chunks{RPC_SUFFIX}",
                   headers={**_HEADERS, "Content-Type": "application/json"}, json=payload)
        r.raise_for_status()
    return r.json()


def rpc_fts(search_query: str, match_limit: int = 50) -> list[dict]:
    payload = {"search_query": search_query, "filter_product": None,
               "filter_manufacturer": None, "filter_category": None,
               "match_limit": match_limit}
    try:
        with httpx.Client(timeout=30.0) as c:
            r = c.post(f"{SUPABASE_URL}/rest/v1/rpc/search_chunks_text{RPC_SUFFIX}",
                       headers={**_HEADERS, "Content-Type": "application/json"}, json=payload)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return []


def fetch_manual_chunks(tokens: list[str], limit: int = 600) -> list[dict]:
    """Chunks del manual objetivo (mismos tokens del funnel congelado), con los
    campos que el diagnostico necesita. Excluye duplicate_of (como los canales)."""
    cols = ("id,content,context,source_file,page_number,section_title,section_path,"
            "content_type,product_model,category,manufacturer,language,duplicate_of")
    out, seen = [], set()
    for t in tokens[:6]:
        try:
            with httpx.Client(timeout=30.0) as c:
                r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_HEADERS,
                          params={"select": cols, "source_file": f"ilike.*{t}*",
                                  "limit": str(limit)})
            if r.status_code in (200, 206):
                for row in r.json():
                    if row.get("id") not in seen and not row.get("duplicate_of"):
                        seen.add(row.get("id"))
                        out.append(row)
        except Exception:
            continue
    return out


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


def cos_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


# --- clasificacion PROPUESTA (heuristica; la lectura final es del duo) ---------
def propose_cause(w: dict, detected_cat: str | None) -> str:
    """Etiqueta candidata para el mejor winner de un hecho. Solo orienta."""
    rank = w.get("rank_vector_nofilter")
    sim = w.get("sim_local")
    cut = w.get("cutoff50_sim")
    in50 = rank is not None and rank <= CUTOFF_RANK
    geom_in = (sim is not None and cut is not None and sim >= cut)
    if in50 or geom_in:
        # la geometria SI lo pone en el top-50 del canal sin filtro:
        if detected_cat and w.get("category") != detected_cat:
            return "CATEGORY-FILTER"      # el filtro de categoria del canal lo excluye
        if not w.get("filter11e_pass"):
            return "MODEL-LABEL-FILTER"   # #11e lo expulsa del merge
        if not in50 and geom_in:
            return "INDEX-RECALL"         # geometria ok, el HNSW no lo devuelve
        return "MERGE/DIVERSITY"          # entra al canal pero el merge lo pierde
    # la geometria NO lo pone en el top-50:
    if w.get("kw_hits"):
        if not w.get("pm_imatch_any"):
            return "MODEL-LABEL+SEMANTIC"  # el canal lexico lo veria, la etiqueta lo esconde
        return "ILIKE-LOTTERY+SEMANTIC"    # el ilike model-scoped lo ve (limit sin ranking)
    return "LEXICAL+SEMANTIC"              # ni vocabulario compartido ni cercania vectorial


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--qids", default="", help="csv de qids (default: los 7 con hechos RECALL)")
    args = ap.parse_args()

    assert CHUNKS_IS_V2, "CHUNKS_TABLE debe ser chunks_v2"

    funnel = yaml.safe_load(FUNNEL.read_text(encoding="utf-8"))
    from scripts.gold_store import exclude_heldout  # noqa: E402
    golds = {g["qid"]: g for g in exclude_heldout(yaml.safe_load(GOLD.read_text(encoding="utf-8")))}

    # Los 14 hechos: fuertes, bucket RETRIEVAL, del funnel CONGELADO.
    targets: list[tuple[str, dict, dict]] = []   # (qid, funnel_row, fact)
    for row in funnel["results"]:
        for f in row.get("facts") or []:
            if f.get("strength") == "fuerte" and f.get("bucket") == "RETRIEVAL":
                targets.append((row["qid"], row, f))
    if args.qids:
        keep = {q.strip() for q in args.qids.split(",") if q.strip()}
        targets = [t for t in targets if t[0] in keep]
    else:
        assert len(targets) == 14, f"esperaba 14 hechos RECALL, hay {len(targets)}"

    by_qid: dict[str, list[tuple[dict, dict]]] = {}
    for qid, row, f in targets:
        by_qid.setdefault(qid, []).append((row, f))

    print(f"chunks_v2 | HyDE OFF | RPC match_chunks{RPC_SUFFIX} | "
          f"{len(targets)} hechos RECALL en {len(by_qid)} qids\n")

    results = []
    for qid, pairs in by_qid.items():
        row = pairs[0][0]
        g = golds[qid]
        q = g["question"]
        models = extract_product_models(q)
        detected_cat = detect_category(q)
        keywords = extract_search_keywords(q)
        ql = q.lower()
        synonyms = [syn for phrase, syn in QUERY_SYNONYMS.items() if phrase in ql]
        intents = [n for n, p in (("spec", SPEC_INTENT), ("troubleshoot", TROUBLESHOOT_INTENT),
                                  ("wiring", WIRING_INTENT)) if p.search(q)]

        emb = embed_query(q)
        run_nofilter = rpc_match_chunks(emb, RANK_PROBE_K, 0.0, None)
        rank_nofilter = {r["id"]: i + 1 for i, r in enumerate(run_nofilter)}
        cutoff50 = (run_nofilter[CUTOFF_RANK - 1]["similarity"]
                    if len(run_nofilter) >= CUTOFF_RANK else None)
        run_cat = (rpc_match_chunks(emb, CUTOFF_RANK, 0.3, detected_cat)
                   if detected_cat else [])
        rank_cat = {r["id"]: i + 1 for i, r in enumerate(run_cat)}
        fts_rows = rpc_fts(q, 50)
        fts_rank = {r["id"]: i + 1 for i, r in enumerate(fts_rows)}

        manual_chunks = fetch_manual_chunks(row.get("target_tokens") or [])

        qrec = {
            "qid": qid, "question": q,
            "models_detected": models,
            "detected_category": detected_cat,
            "keywords": keywords, "synonyms": synonyms, "intents": intents,
            "vector_nofilter_returned": len(run_nofilter),
            "cutoff50_sim": round(cutoff50, 4) if cutoff50 is not None else None,
            "vector_cat_returned": len(run_cat),
            "fts_returned": len(fts_rows),
            "manual_chunks_fetched": len(manual_chunks),
            "facts": [],
        }

        for _, f in pairs:
            kind, probe = probe_from_yaml(f.get("probe"))
            winners = [c for c in manual_chunks if chunk_has(c.get("content") or "", kind, probe)]
            wrecs = []
            embs = fetch_embeddings([w["id"] for w in winners[:6]])
            for w in winners[:6]:
                wemb = embs.get(w["id"])
                sim = cos_sim(emb, wemb) if wemb else None
                content = w.get("content") or ""
                kw_hits = [k for k in keywords if k in content.lower()]
                syn_hits = [s for s in synonyms if s in content.lower()]
                pm = w.get("product_model") or ""
                wrec = {
                    "chunk_id": w["id"],
                    "source_file": w.get("source_file"),
                    "page": w.get("page_number"),
                    "section_path": w.get("section_path") or w.get("section_title"),
                    "content_type": w.get("content_type"),
                    "product_model": pm,
                    "category": w.get("category"),
                    "language": w.get("language"),
                    "content_len": len(content),
                    "has_blurb": bool(w.get("context")),
                    "blurb": (w.get("context") or "")[:200],
                    "preview": " ".join(content.split())[:240],
                    "sim_local": round(sim, 4) if sim is not None else None,
                    "cutoff50_sim": qrec["cutoff50_sim"],
                    "rank_vector_nofilter": rank_nofilter.get(w["id"]),
                    "rank_vector_cat": rank_cat.get(w["id"]),
                    "rank_fts_query": fts_rank.get(w["id"]),
                    "kw_hits": kw_hits,
                    "syn_hits": syn_hits,
                    "pm_imatch_any": any(pm_imatch(m, pm) for m in models),
                    "filter11e_pass": filter11e_pass(models, pm),
                    "cat_match": (w.get("category") == detected_cat) if detected_cat else None,
                }
                wrecs.append(wrec)

            best = max(wrecs, key=lambda r: (r["sim_local"] or 0.0), default=None)
            frec = {
                "valor": f.get("valor"),
                "probe": f.get("probe"),
                "n_winners": len(winners),
                "winners": wrecs,
                "proposed_cause": propose_cause(best, detected_cat) if best else "NO-WINNER-FOUND",
            }
            qrec["facts"].append(frec)

            b = best or {}
            print(f"  {qid} | {str(f.get('valor'))[:28]:28s} | winners={len(winners):2d} "
                  f"| sim={b.get('sim_local')} cut50={qrec['cutoff50_sim']} "
                  f"rankV={b.get('rank_vector_nofilter')} fts={b.get('rank_fts_query')} "
                  f"kw={','.join(b.get('kw_hits', [])) or '-'} pm11e={b.get('filter11e_pass')} "
                  f"cat={b.get('cat_match')} -> {frec['proposed_cause']}")

        results.append(qrec)
        print()

    meta = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "chunks_table": os.environ.get("CHUNKS_TABLE"),
        "funnel_file": FUNNEL.name,
        "rank_probe_k": RANK_PROBE_K,
        "n_facts": len(targets),
        "qids": sorted(by_qid),
    }
    OUT.write_text(yaml.safe_dump({"meta": meta, "results": results},
                                  allow_unicode=True, sort_keys=False), encoding="utf-8")

    print("=" * 70)
    from collections import Counter
    causes = Counter(f["proposed_cause"] for r in results for f in r["facts"])
    print("CAUSAS PROPUESTAS (hechos):", dict(causes))
    print(f"Detalle: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
