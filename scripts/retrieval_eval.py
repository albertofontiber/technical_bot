#!/usr/bin/env python3
"""Eval de RETRIEVAL (recall@k) + diagnóstico retrieval-vs-generación.

Determinista, sin generación ni judge. Para cada pregunta del gold (answer-type),
recupera top-K y localiza en qué RANGO aparece un chunk que contiene cada `quote`
de las citations del gold (= el contenido que el chunk relevante debe tener).

Clasifica el gap por pregunta (best rank entre sus quotes):
  - top-5    → gap de GENERACIÓN (el dato estaba en la ventana del generator y no
               se usó) → un reranker NO lo arregla.
  - 6..K     → gap de TOP-K/RERANKER (recuperado pero fuera del top-5 que ve el
               generator) → reranker/top-K split SÍ ayuda.
  - no en K  → gap de RETRIEVAL profundo (el chunk no sube) → ni reranker.

Sirve de (a) diagnóstico raíz (¿es el reranker la palanca?) y (b) instrumento
determinista para tunear top-K/reranker. Content-based (sliding-window substring
normalizado) para no depender del mapeo PDF→source_file.

Uso: python scripts/retrieval_eval.py [--topk 15]
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import unicodedata
from pathlib import Path

os.environ["CHUNKS_TABLE"] = "chunks_v2"  # forzar ANTES de importar config/retriever
import yaml
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
sys.path.insert(0, str(ROOT))
from src.rag.retriever import retrieve_chunks  # noqa: E402

GOLD = ROOT / "evals" / "gold_answers_v1.yaml"
RESULTS = ROOT / "evals" / "bot_vs_gold_results.yaml"
WINDOW = 25  # longitud mínima de substring distintivo del quote


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


OVERLAP_THRESHOLD = 0.6  # token-overlap mínimo para considerar el quote presente


def chunk_has_quote(content: str, quote: str) -> bool:
    """Substring exacto (barato/preciso) O token-overlap >= umbral (tolera la
    reescritura/OCR entre el gold-quote de Opus y el chunk de LlamaParse — el
    substring estricto daba falsos 'no recuperado', p.ej. hp020 a 76-87% overlap)."""
    nc, nq = norm(content), norm(quote)
    if not nq:
        return False
    if len(nq) <= WINDOW:
        if nq in nc:
            return True
    else:
        for i in range(0, len(nq) - WINDOW + 1, 5):
            if nq[i:i + WINDOW] in nc:
                return True
    return quote_overlap(quote, content) >= OVERLAP_THRESHOLD


def _toks(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", norm(s)))


def quote_overlap(quote: str, content: str) -> float:
    """Fracción de tokens del quote presentes en el content (match fuzzy)."""
    qt = _toks(quote)
    return len(qt & _toks(content)) / len(qt) if qt else 0.0


def detail(gold: list[dict], qids: list[str], topk: int) -> None:
    """Vuelca, por qid: query + cada quote del gold con (substring-hit rank,
    mejor token-overlap y en qué chunk) + dump de los chunks recuperados.
    Para decidir si un '0 facts' es artefacto de matching o miss real."""
    by_qid = {g.get("qid"): g for g in gold}
    for qid in qids:
        g = by_qid.get(qid)
        if not g:
            print(f"[{qid}] no encontrado en gold\n")
            continue
        quotes = [c.get("quote", "") for c in (g.get("citations") or []) if c.get("quote")]
        chunks = retrieve_chunks(g["question"], top_k=topk)
        print(f"==== {qid} · {g.get('conducta_esperada')} ====")
        print(f"Q: {g['question']}\n")
        for i, q in enumerate(quotes, 1):
            sub_rank = next((r for r, ch in enumerate(chunks, 1)
                             if chunk_has_quote(ch.get('content', ''), q)), None)
            best_ov, best_r = 0.0, None
            for r, ch in enumerate(chunks, 1):
                ov = quote_overlap(q, ch.get('content', ''))
                if ov > best_ov:
                    best_ov, best_r = ov, r
            print(f"  quote{i} substr_rank={sub_rank} | best_overlap={best_ov:.0%}@rank{best_r}")
            print(f"    «{q[:120]}»")
        print(f"\n  chunks recuperados (top {len(chunks)}):")
        for r, ch in enumerate(chunks, 1):
            c = " ".join((ch.get('content') or '').split())
            print(f"    [{r}] {ch.get('source_file','?')[:28]:<28} | {c[:130]}")
        print()


def best_rank(chunks: list[dict], quotes: list[str]) -> tuple[int | None, int]:
    """(mejor rank 1-indexed donde aparece algún quote, nº de quotes hallados)."""
    found_ranks = []
    for q in quotes:
        for rank, ch in enumerate(chunks, 1):
            if chunk_has_quote(ch.get("content", ""), q):
                found_ranks.append(rank)
                break
    return (min(found_ranks) if found_ranks else None, len(found_ranks))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=15)
    ap.add_argument("--detail", default="", help="qids separados por coma para volcado detallado")
    args = ap.parse_args()

    gold = yaml.safe_load(open(GOLD, encoding="utf-8"))
    if args.detail:
        detail(gold, [q.strip() for q in args.detail.split(",") if q.strip()], args.topk)
        return
    verdicts = {}
    if RESULTS.is_file():
        for r in yaml.safe_load(open(RESULTS, encoding="utf-8")) or []:
            verdicts[r.get("qid")] = r.get("veredicto")

    rows = []
    for g in gold:
        if g.get("conducta_esperada") != "answer":
            continue  # recall solo aplica a las que deben responder
        quotes = [c.get("quote", "") for c in (g.get("citations") or []) if c.get("quote")]
        if not quotes:
            continue
        qid = g.get("qid")
        chunks = retrieve_chunks(g["question"], top_k=args.topk)
        rank, n_found = best_rank(chunks, quotes)
        if rank is None:
            gap = "RETRIEVAL (no en top-%d)" % args.topk
        elif rank <= 5:
            gap = "generación (top-5)"
        else:
            gap = "TOP-K/RERANKER (6-%d)" % args.topk
        rows.append({"qid": qid, "verdict": verdicts.get(qid, "?"),
                     "best_rank": rank, "quotes": f"{n_found}/{len(quotes)}", "gap": gap})

    rows.sort(key=lambda r: (r["best_rank"] is not None, r["best_rank"] or 999))
    print(f"== Retrieval eval · chunks_v2 · top_k={args.topk} · {len(rows)} answer-questions ==\n")
    hit5 = sum(1 for r in rows if r["best_rank"] and r["best_rank"] <= 5)
    hitk = sum(1 for r in rows if r["best_rank"] is not None)
    print(f"recall@5  = {hit5}/{len(rows)} = {hit5/len(rows):.0%}")
    print(f"recall@{args.topk} = {hitk}/{len(rows)} = {hitk/len(rows):.0%}\n")

    from collections import Counter
    print("Diagnóstico de gap (clasificación raíz):")
    for g, n in Counter(r["gap"] for r in rows).most_common():
        print(f"  {g:<26} {n}")
    print()
    print(f"{'qid':<8}{'verdict':<10}{'rank':<6}{'quotes':<8}gap")
    for r in rows:
        print(f"{r['qid']:<8}{r['verdict']:<10}{str(r['best_rank']):<6}{r['quotes']:<8}{r['gap']}")


if __name__ == "__main__":
    main()
