#!/usr/bin/env python3
"""Run the eval set in evals/baseline_v1.yaml against the live RAG stack.

Pipeline per question (mirrors what telegram_bot.py does, minus UI):
  1. retrieve_chunks(query) — vector + keyword search
  2. rerank_chunks(query, chunks) — Claude relevance reranking
  3. generate_answer(query, reranked) — Claude final answer + diagrams

Scoring (heuristic v1 — a human pass is still needed for trust):
  - expected_behavior:
      answer              → answer doesn't predominantly ask back / admit ignorance
      ask_clarification   → answer contains a clarifying question
      admit_no_info       → answer says "no tengo / no dispongo / no encuentro"
  - expected_keywords    → every keyword must appear (substring, lowercased)
  - forbidden_keywords   → none may appear
  - expected_has_diagram → len(diagrams) > 0 must match
  - expected_sources     → (loose) at least one source_file in citations

Usage:
  python scripts/run_eval.py                       # full eval, default YAML
  python scripts/run_eval.py --input path/to.yaml
  python scripts/run_eval.py --only hp001,am003    # run a subset
  python scripts/run_eval.py --categories happy_path,not_in_db
  python scripts/run_eval.py --dry-run             # skip LLM calls; only print plan

Output:
  logs/eval_<timestamp>.json — full results per question + aggregate scores
  stdout                     — human-readable summary grouped by category
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

try:
    import yaml  # noqa: E402
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Scoring heuristics
# ---------------------------------------------------------------------------
# Phrases that signal the bot is asking back (clarification)
_CLARIFY_PATTERNS = re.compile(
    r"(¿[^?]*(modelo|fabricante|cuál|qué|cual|que)[^?]*\?|"
    r"¿puedes (confirmar|indicar|especificar|aclarar|dar)|"
    r"necesito saber|dime el modelo|cuál (de los|de las)|"
    r"¿te refieres a|¿cuál de ([^?]+)\?)",
    re.IGNORECASE,
)

# Phrases that signal "I don't have that manual"
_NO_INFO_PATTERNS = re.compile(
    r"(no tengo (este|ese|el) manual|"
    r"no dispongo de (información|manual|datos)|"
    r"no (encuentro|localizo) (información|manual|datos)|"
    r"no (está|aparece) en (mi|la) (base|biblioteca|bd)|"
    r"no figura en los manuales|"
    r"no (puedo|tengo) (información|datos) sobre (este|ese) (producto|modelo)|"
    r"registrar(é|emos)? (este|el) (producto|modelo|fabricante))",
    re.IGNORECASE,
)


def classify_behavior(answer: str) -> str:
    """Classify the bot's response style from text.

    Returns one of: 'answer', 'ask_clarification', 'admit_no_info'.
    Priority: admit_no_info > ask_clarification > answer.
    """
    if _NO_INFO_PATTERNS.search(answer):
        return "admit_no_info"
    if _CLARIFY_PATTERNS.search(answer):
        return "ask_clarification"
    return "answer"


def score_keywords(answer: str, expected: list[str]) -> tuple[int, int, list[str]]:
    """Return (hits, total, missing). Substring match, lowercased."""
    if not expected:
        return 0, 0, []
    a = answer.lower()
    missing = [kw for kw in expected if kw.lower() not in a]
    return len(expected) - len(missing), len(expected), missing


def score_forbidden(answer: str, forbidden: list[str]) -> list[str]:
    """Return list of forbidden keywords that DID appear (violations)."""
    if not forbidden:
        return []
    a = answer.lower()
    return [kw for kw in forbidden if kw.lower() in a]


def score_sources(citations_text: str, expected: list[str]) -> int:
    """Number of expected source substrings that appear in citations. 0 if none expected."""
    if not expected or not citations_text:
        return 0
    c = citations_text.lower()
    return sum(1 for s in expected if s.lower() in c)


def score_question(q: dict, result: dict) -> dict:
    """Compute per-criterion scores for a single question. Returns dict with
    per-criterion booleans + an overall pass/fail."""
    answer = result.get("answer", "")
    diagrams = result.get("diagrams", [])

    # Behavior
    observed_behavior = classify_behavior(answer)
    behavior_ok = observed_behavior == q.get("expected_behavior", "answer")

    # Keywords
    kw_hits, kw_total, kw_missing = score_keywords(answer, q.get("expected_keywords") or [])
    keywords_ok = kw_total == 0 or kw_missing == []

    # Forbidden
    violations = score_forbidden(answer, q.get("forbidden_keywords") or [])
    forbidden_ok = violations == []

    # Diagram presence
    expected_has_diag = q.get("expected_has_diagram")
    has_diag = len(diagrams) > 0
    if expected_has_diag is None:
        diagram_ok = True  # don't care
    else:
        diagram_ok = bool(expected_has_diag) == has_diag

    # Sources (loose, for info)
    citations_text = "\n".join(c.get("source_file", "") for c in result.get("chunks_used", []))
    src_hits = score_sources(citations_text, q.get("expected_sources") or [])

    # Overall pass: behavior + keywords + forbidden (diagram is informational)
    overall_pass = behavior_ok and keywords_ok and forbidden_ok

    return {
        "observed_behavior": observed_behavior,
        "behavior_ok": behavior_ok,
        "keywords": {"hits": kw_hits, "total": kw_total, "missing": kw_missing, "ok": keywords_ok},
        "forbidden_violations": violations,
        "forbidden_ok": forbidden_ok,
        "has_diagram": has_diag,
        "diagram_ok": diagram_ok,
        "source_hits": src_hits,
        "pass": overall_pass,
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_single(q: dict, dry_run: bool = False) -> dict:
    """Execute the full retrieve → rerank → generate pipeline for one question."""
    if dry_run:
        return {
            "answer": "[dry-run — no LLM call]",
            "diagrams": [],
            "chunks_used": [],
            "timing": {"retrieve": 0, "rerank": 0, "generate": 0, "total": 0},
            "dry_run": True,
        }

    # Import lazily so --dry-run doesn't require full env vars
    from src.rag.retriever import (
        retrieve_chunks, extract_product_models, get_category_models,
    )
    from src.rag.reranker import rerank_chunks
    from src.rag.generator import generate_answer

    query = q["question"]
    t0 = time.time()
    chunks = retrieve_chunks(query)
    t_ret = time.time() - t0

    t0 = time.time()
    target_models = extract_product_models(query)
    reranked = rerank_chunks(query, chunks, target_models=target_models or None)
    t_rer = time.time() - t0

    t0 = time.time()
    # Best-effort: pass available_models for the detected category if any model hit
    available_models = None
    if target_models:
        # heuristic — category from first chunk if any, else skip
        cat = chunks[0].get("category") if chunks else None
        if cat:
            try:
                available_models = get_category_models(cat)
            except Exception:
                available_models = None
    gen = generate_answer(query, reranked, available_models=available_models)
    t_gen = time.time() - t0

    return {
        "answer": gen.get("answer", ""),
        "diagrams": gen.get("diagrams", []),
        "chunks_used": [
            {"source_file": c.get("source_file"), "page": c.get("page_number"),
             "product_model": c.get("product_model"),
             "similarity": c.get("similarity")}
            for c in reranked[:6]
        ],
        "target_models_detected": target_models,
        "timing": {
            "retrieve": round(t_ret, 2),
            "rerank": round(t_rer, 2),
            "generate": round(t_gen, 2),
            "total": round(t_ret + t_rer + t_gen, 2),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="evals/baseline_v1.yaml",
                    help="Path to the eval YAML")
    ap.add_argument("--only", default=None,
                    help="Comma-separated list of question ids to run (e.g. hp001,am003)")
    ap.add_argument("--categories", default=None,
                    help="Comma-separated list of categories to run")
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip LLM calls; only print the plan")
    ap.add_argument("--output-dir", default="logs",
                    help="Where to write the JSON report")
    args = ap.parse_args()

    yaml_path = ROOT / args.input
    if not yaml_path.exists():
        print(f"ERROR: eval file not found: {yaml_path}")
        return 1
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    questions = data.get("questions", [])

    # Filter
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        questions = [q for q in questions if q["id"] in wanted]
    if args.categories:
        cats = {s.strip() for s in args.categories.split(",") if s.strip()}
        questions = [q for q in questions if q.get("category") in cats]

    print(f"Loaded {len(questions)} question(s) from {yaml_path.name}")
    print(f"Mode: {'DRY-RUN (no LLM)' if args.dry_run else 'LIVE'}")
    print()

    results: list[dict] = []
    t_start = time.time()
    for i, q in enumerate(questions, 1):
        qid = q.get("id", f"q{i}")
        cat = q.get("category", "?")
        qtext = q.get("question", "")[:70]
        print(f"[{i}/{len(questions)}] {qid} ({cat})  {qtext}...")

        try:
            exec_result = run_single(q, dry_run=args.dry_run)
            if not args.dry_run:
                score = score_question(q, exec_result)
            else:
                score = {"pass": None, "dry_run": True}
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")
            traceback.print_exc(limit=2)
            exec_result = {"error": str(e), "type": type(e).__name__}
            score = {"pass": False, "error": True}

        status = (
            "DRY" if args.dry_run else
            ("PASS" if score.get("pass") else "FAIL")
        )
        print(f"    {status}  "
              f"(behavior_expected={q.get('expected_behavior')} "
              f"observed={score.get('observed_behavior','?')} | "
              f"keywords={score.get('keywords',{}).get('hits','?')}/"
              f"{score.get('keywords',{}).get('total','?')} | "
              f"diag_ok={score.get('diagram_ok','?')} | "
              f"time={exec_result.get('timing',{}).get('total','?')}s)")

        if not args.dry_run and not score.get("pass") and not score.get("error"):
            kw_missing = score.get("keywords", {}).get("missing", [])
            if kw_missing:
                print(f"    missing keywords: {kw_missing}")
            vios = score.get("forbidden_violations", [])
            if vios:
                print(f"    forbidden hit:    {vios}")

        results.append({"question": q, "result": exec_result, "score": score})

    elapsed = time.time() - t_start

    # Aggregate scores
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total elapsed: {elapsed:.1f}s")
    if args.dry_run:
        print("(dry run — no pass/fail scoring)")
    else:
        by_cat: dict[str, dict[str, int]] = {}
        for r in results:
            c = r["question"].get("category", "?")
            bucket = by_cat.setdefault(c, {"pass": 0, "fail": 0, "error": 0})
            if r["score"].get("error"):
                bucket["error"] += 1
            elif r["score"].get("pass"):
                bucket["pass"] += 1
            else:
                bucket["fail"] += 1
        print()
        print(f"{'category':<22s} {'pass':>6s} {'fail':>6s} {'err':>6s}  rate")
        print("-" * 50)
        total_p = total_f = total_e = 0
        for cat in sorted(by_cat):
            p, f, e = by_cat[cat]["pass"], by_cat[cat]["fail"], by_cat[cat]["error"]
            total_p, total_f, total_e = total_p + p, total_f + f, total_e + e
            t = p + f + e
            rate = f"{100*p/t:.0f}%" if t else "-"
            print(f"{cat:<22s} {p:>6d} {f:>6d} {e:>6d}  {rate:>4s}")
        print("-" * 50)
        t = total_p + total_f + total_e
        rate = f"{100*total_p/t:.0f}%" if t else "-"
        print(f"{'TOTAL':<22s} {total_p:>6d} {total_f:>6d} {total_e:>6d}  {rate:>4s}")

    # Write JSON
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"eval_{ts}.json"
    out_path.write_text(
        json.dumps({
            "timestamp_utc": ts, "input": str(args.input),
            "dry_run": args.dry_run, "elapsed_s": round(elapsed, 1),
            "results": results,
        }, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print()
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
