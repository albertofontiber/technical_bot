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
from src.rag.reranker import rerank_chunks, rerank_chunks_voyage  # noqa: E402

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


# --- Matcher ESTRICTO (specific-fact presence) ---------------------------------
# El fuzzy de arriba (substring O overlap>=0.6) SOBREESTIMA recall en preguntas de
# spec: cuenta números/términos compartidos como "fact presente" (hp019 daba 4/4
# fuzzy pero la tabla de valores no estaba recuperada). El estricto exige que los
# VALORES distintivos del quote (números de >=2 dígitos, códigos de modelo)
# aparezcan TODOS en el chunk (OCR-normalizado: guiones –/—/− → -, "+ 60"→"+60").
# Quotes de prosa pura (sin valores) → overlap alto (0.8) + ancla contigua.
_DASHES = {0x2013: "-", 0x2014: "-", 0x2212: "-", 0x2010: "-", 0x2011: "-"}


def norm_ocr(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.translate(_DASHES).replace("º", "°")
    s = re.sub(r"(?<=[+\-\d])\s+(?=\d)", "", s)  # "+ 60"->"+60", "1 000"->"1000"
    return " ".join(s.split())


_NUM = re.compile(r"[+\-]?\d[\d.,]*")
_MODEL = re.compile(r"\b[a-z]{2,}-?\d{2,}[a-z]*\b")


def _distinctive(quote: str) -> set[str]:
    """Valores que identifican el fact: números de >=2 dígitos + códigos de modelo."""
    q = norm_ocr(quote)
    nums = {n.strip(".,") for n in _NUM.findall(q) if len(re.findall(r"\d", n)) >= 2}
    return nums | set(_MODEL.findall(q))


def chunk_has_quote_strict(content: str, quote: str) -> bool:
    nc = norm_ocr(content)
    anchors = _distinctive(quote)
    if anchors:
        return all(a in nc for a in anchors)
    nq = norm_ocr(quote)
    if len(nq) > WINDOW and any(nq[i:i + WINDOW] in nc
                                for i in range(0, len(nq) - WINDOW + 1, 5)):
        return True
    return quote_overlap(quote, content) >= 0.8


STRICT = True  # fijado desde --match en main()


def _match(content: str, quote: str) -> bool:
    return chunk_has_quote_strict(content, quote) if STRICT else chunk_has_quote(content, quote)


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
                             if _match(ch.get('content', ''), q)), None)
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
            if _match(ch.get("content", ""), q):
                found_ranks.append(rank)
                break
    return (min(found_ranks) if found_ranks else None, len(found_ranks))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=15)
    ap.add_argument("--match", choices=["strict", "fuzzy"], default="strict",
                    help="strict=presencia de fact específico (default) | "
                         "fuzzy=overlap 0.6 (antiguo, sobreestima recall en specs)")
    ap.add_argument("--rerank", action="store_true",
                    help="aplica el reranker sobre los topk candidatos y mide recall "
                         "POST-RERANK (= lo que ve el generator)")
    ap.add_argument("--reranker", choices=["llm", "voyage"], default="llm",
                    help="llm=scorer Claude (producción actual) | voyage=cross-encoder rerank-2.5")
    ap.add_argument("--rerank-k", type=int, default=5,
                    help="cuántos chunks deja el reranker para el generator (prod actual=5)")
    ap.add_argument("--detail", default="", help="qids separados por coma para volcado detallado")
    args = ap.parse_args()

    global STRICT
    STRICT = (args.match == "strict")

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
        if args.rerank:
            _rr = rerank_chunks_voyage if args.reranker == "voyage" else rerank_chunks
            chunks = _rr(g["question"], chunks, top_k=args.rerank_k)
        rank, n_found = best_rank(chunks, quotes)
        if args.rerank:
            # solo quedan <=5 chunks: rank None = el reranker (o el retrieval) dejó
            # el dato fuera de la ventana del generator; rank<=5 = el generator lo vio.
            gap = (f"fuera de top-{args.rerank_k} (reranker/retrieval)" if rank is None
                   else f"visto por generator (top-{args.rerank_k})")
        elif rank is None:
            gap = "RETRIEVAL (no en top-%d)" % args.topk
        elif rank <= 5:
            gap = "generación (top-5)"
        else:
            gap = "TOP-K/RERANKER (6-%d)" % args.topk
        rows.append({"qid": qid, "verdict": verdicts.get(qid, "?"), "best_rank": rank,
                     "n_found": n_found, "n_total": len(quotes),
                     "quotes": f"{n_found}/{len(quotes)}", "gap": gap})

    rows.sort(key=lambda r: (r["best_rank"] is not None, r["best_rank"] or 999))
    mode = f"top_k={args.topk}→rerank[{args.reranker}]@{args.rerank_k} (POST-RERANK = lo que ve el generator)" \
        if args.rerank else f"top_k={args.topk} (retrieval crudo)"
    print(f"== Retrieval eval · chunks_v2 · {mode} · match={args.match} · {len(rows)} answer-questions ==\n")
    hit5 = sum(1 for r in rows if r["best_rank"] and r["best_rank"] <= 5)
    hitk = sum(1 for r in rows if r["best_rank"] is not None)
    # recall por-PREGUNTA (al menos 1 quote presente) — best_rank usa el MÍNIMO, así
    # que enmascara facts ausentes; por eso reportamos también recall por-FACT abajo.
    print(f"recall@5 (por-pregunta)  = {hit5}/{len(rows)} = {hit5/len(rows):.0%}")
    if not args.rerank:
        print(f"recall@{args.topk} (por-pregunta) = {hitk}/{len(rows)} = {hitk/len(rows):.0%}")
    facts_found = sum(r["n_found"] for r in rows)
    facts_total = sum(r["n_total"] for r in rows)
    label = f"post-rerank@{args.rerank_k}" if args.rerank else f"top-{args.topk}"
    print(f"recall POR-FACT ({label}) = {facts_found}/{facts_total} = {facts_found/facts_total:.0%}  "
          f"← métrica honesta\n")

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
