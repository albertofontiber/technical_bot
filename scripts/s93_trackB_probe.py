#!/usr/bin/env python3
"""s93_trackB_probe.py — TRACK B del bake-off (plan v3.2): probe de multi-granularidad.

¿Un sub-chunk (span determinista que contiene el hecho) rankearía en coseno donde su
chunk-padre no rankea? SIN re-ingesta, SIN re-retrieval (sub-agente F1):
- 1 llamada `embed_query(pregunta cruda)` por gold (HyDE=off = config pin/prod),
  compartida entre ambos lados;
- cosenos LOCALES: embeddings ALMACENADOS del pool pineado (`_fetch_embeddings_by_id`)
  + embedding ad hoc del sub-chunk (Voyage input_type=document, receta fiel B7:
  `context-almacenado-del-padre + "\\n\\n" + span`, `src/reingest/embed.py:52-59`);
- evento v2 (regla-C sobre mi propio v1): la frontera min-cos del pool FINAL era
  demasiado optimista — el canal vectorial compite CORPUS-WIDE (top-50 por <=> sobre
  25k con duplicate_of IS NULL) y los filtros decapitan el pool después. La barra real
  = similarity del #50 (y #100 para queries 2-modelos) del RPC `match_chunks_v2` con
  MI query-embedding (mismo espacio, orden de producción). Se reporta también la
  frontera-pool v1 como referencia. Tie-band ±0.003 (DEC-042d).

Extracción DETERMINISTA (F6): línea(s) VERBATIM del content que contienen el `valor`
normalizado como token (unaccent/lower/no-punct, word-boundary); si la línea es fila
de tabla markdown ('|'), se antepone la cabecera del bloque contiguo. Sin match literal
→ FLAG (hecho parafraseado, sin span — declarado, no se inventa).

Testbed: post-PASO-0 (hp012 '99 + 99' EXCLUIDO: muere en diversify, no fine-grained).
Freeze: EMBED_MODEL=voyage-4-large · input_type doc/query · HYDE_ENABLED=false ·
pin=evals/s92_retrieval_miss_ON_add.yaml. NADA se escribe en DB.
"""
import json
import os
import re
import sys
import unicodedata

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
import httpx
import yaml

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from src.ingestion.embedder import embed_query
from src.rag.retriever import _cos, _fetch_embeddings_by_id
from src.reingest.embed import EMBED_MODEL, embed

PIN = "evals/s92_retrieval_miss_ON_add.yaml"
TIE = 0.003
EXCLUDED = [("hp012", "99 + 99")]          # paso 0: muere en diversify, no fine-grained
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = re.sub(r"[^a-z0-9ñ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def span_for(valor: str, content: str) -> str | None:
    """Línea(s) verbatim que contienen el valor como secuencia de tokens; + cabecera
    del bloque-tabla si la línea es fila markdown. Determinista, sin parafraseo."""
    nv = norm(valor)
    if not nv:
        return None
    pat = re.compile(rf"(?<![a-z0-9]){re.escape(nv)}(?![a-z0-9])")
    lines = content.splitlines()
    hits = [i for i, ln in enumerate(lines) if pat.search(norm(ln))]
    if not hits:
        return None
    out: list[str] = []
    for i in hits:
        if "|" in lines[i]:                       # fila de tabla → cabecera del bloque
            j = i
            while j > 0 and "|" in lines[j - 1]:
                j -= 1
            if j < i and lines[j] not in out:
                out.append(lines[j])
        if lines[i] not in out:
            out.append(lines[i])
    return "\n".join(out)


def rpc_frontier(q_emb: list[float]) -> dict:
    """Top-100 del canal vectorial REAL (RPC match_chunks_v2, threshold 0 para ver la
    frontera) con MI embedding → sim del #50 y #100. Es el orden de producción."""
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/rpc/match_chunks_v2",
                   headers={**_H, "Content-Type": "application/json"},
                   json={"query_embedding": q_emb, "match_threshold": 0.0,
                         "match_count": 100}, timeout=60)
    r.raise_for_status()
    sims = [row["similarity"] for row in r.json()]
    return {"sim1": sims[0], "sim50": sims[49] if len(sims) > 49 else None,
            "sim100": sims[99] if len(sims) > 99 else None,
            "ids100": [row["id"] for row in r.json()]}


def fetch_chunks(ids: list[str]) -> dict:
    out = {}
    for i in range(0, len(ids), 40):
        q = ",".join(f'"{x}"' for x in ids[i:i + 40])
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                      params={"select": "id,content,context,section_title,source_file",
                              "id": f"in.({q})"}, timeout=30)
        for x in r.json():
            out[x["id"]] = x
    return out


def main() -> int:
    tb = json.load(open("evals/s93_gate0_testbed.json", encoding="utf-8"))
    pin = {r["qid"]: r for r in yaml.safe_load(open(PIN, encoding="utf-8"))["reps"][0]["results"]}
    rows = [r for r in tb["rows"] if (r["qid"], r["valor"]) not in EXCLUDED]
    all_sup = sorted({s["id"] for r in rows for s in r["sup_family_ids"]})
    sup_data = fetch_chunks(all_sup)

    results, q_emb_cache = [], {}
    for r in rows:
        qid, valor = r["qid"], r["valor"]
        if qid not in q_emb_cache:
            qe = embed_query(r["question"])
            q_emb_cache[qid] = (qe, rpc_frontier(qe))
        q_emb, front = q_emb_cache[qid]
        pool_ids = [c["id"] for c in pin[qid]["pool_pin"]]
        pool_embs = _fetch_embeddings_by_id(pool_ids)
        pool_cos = sorted((_cos(q_emb, e) for e in pool_embs.values()), reverse=True)
        if not pool_cos:
            results.append({"qid": qid, "valor": valor, "verdict": "SIN-POOL"})
            continue
        frontier = pool_cos[-1]
        best = None
        for s in r["sup_family_ids"]:
            ch = sup_data.get(s["id"])
            if not ch:
                continue
            span = span_for(valor, ch.get("content") or "")
            if span is None:
                cand = {"sup": s["id"][:8], "flag": "SIN-MATCH-LITERAL", "cos_sub": None}
            else:
                text = (f"{ch['context']}\n\n{span}" if ch.get("context") else span)
                cos_sub = _cos(q_emb, embed([text], "document")[0])
                cand = {"sup": s["id"][:8], "span_chars": len(span), "cos_sub": round(cos_sub, 4),
                        "cos_padre": round(_cos(q_emb, _fetch_embeddings_by_id([s["id"]]).get(s["id"], [])), 4)
                        if _fetch_embeddings_by_id([s["id"]]).get(s["id"]) else None,
                        "span": span[:200]}
            if best is None or (cand.get("cos_sub") or -1) > (best.get("cos_sub") or -1):
                best = cand
        pos = sum(1 for c in pool_cos if c > (best.get("cos_sub") or -1)) + 1 if best and best.get("cos_sub") else None
        s50, s100 = front["sim50"], front["sim100"]
        cs = (best or {}).get("cos_sub")
        if cs is None:
            verdict = "FLAG-sin-span"
        elif s50 is not None and cs >= s50 + TIE:
            verdict = "WIN-canal50"
        elif s50 is not None and cs >= s50 - TIE:
            verdict = "TIE-canal50"
        elif s100 is not None and cs >= s100 - TIE:
            verdict = "solo-top100"
        elif cs >= frontier - TIE:
            verdict = "solo-vs-pool(v1)"
        else:
            verdict = "NO"
        results.append({"qid": qid, "valor": valor, "verdict": verdict,
                        "canal_sim50": round(s50, 4) if s50 else None,
                        "canal_sim100": round(s100, 4) if s100 else None,
                        "pos_pool_equiv": pos, "pool_n": len(pool_cos),
                        "frontier_pool_v1": round(frontier, 4),
                        "top1_pool": round(pool_cos[0], 4), "best": best})
        b = best or {}
        print(f"{qid:8} {valor[:22]!r:24} {verdict:16} sub={b.get('cos_sub')} "
              f"padre={b.get('cos_padre')} canal50={round(s50,4) if s50 else None} "
              f"pool_front={round(frontier,4)}")

    out = {"_freeze": {"embed_model": EMBED_MODEL, "hyde": "off", "tie_band": TIE,
                       "pin": PIN, "excluidos_paso0": EXCLUDED},
           "results": results}
    json.dump(out, open("evals/s93_trackB_results.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"\n{dict(Counter(x['verdict'] for x in results))} de {len(results)}"
          f" → evals/s93_trackB_results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
