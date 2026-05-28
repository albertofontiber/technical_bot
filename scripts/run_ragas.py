#!/usr/bin/env python3
"""Score a RAG eval log with RAGAS metrics (post-hoc, no bot re-execution).

Pipeline:
  1. Load logs/eval_<ts>.json (must include `chunks_full` per case — re-run with
     `python scripts/run_eval.py --include-full-chunks` if missing).
  2. Optionally load evals/baseline_v1.yaml for `reference_answer` fields per
     case (enables LLMContextRecall).
  3. Build a RAGAS EvaluationDataset with (user_input, retrieved_contexts,
     response, reference) per case.
  4. Run RAGAS metrics with Anthropic Claude (Sonnet) as evaluator LLM and
     OpenAI as embeddings provider:
       - Faithfulness                          (no reference needed)
       - ResponseRelevancy                     (no reference needed)
       - LLMContextPrecisionWithoutReference   (no reference needed)
       - LLMContextRecall                      (only for cases with reference)
  5. Write logs/ragas_<ts>.json with per-case + aggregate scores.

Usage:
  python scripts/run_ragas.py                       # most recent eval_*.json
  python scripts/run_ragas.py --input logs/eval_20260502T120000Z.json
  python scripts/run_ragas.py --only hp012,hp016
  python scripts/run_ragas.py --metrics faithfulness,response_relevancy
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Silence the "Pydantic V1 not compatible with Python 3.14" warning from
# langchain_core; we don't use V1 features and the V2 path is exercised.
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="ragas")

# Bootstrap .env for ANTHROPIC_API_KEY / OPENAI_API_KEY.
# Use utf-8-sig to be tolerant of BOM and Windows-edited files; load_dotenv with
# the default encoding silently drops some keys on this machine's .env.
try:
    from dotenv import dotenv_values
    for k, v in dotenv_values(ROOT / ".env", encoding="utf-8-sig").items():
        if v is not None and not os.environ.get(k):
            os.environ[k] = v
except ImportError:
    pass

JUDGE_MODEL = "claude-sonnet-4-6"
EMBED_MODEL = "text-embedding-3-small"

# Map of metric name (CLI / output) → (factory class in ragas.metrics.collections, requires_reference)
# The new collections API renamed several classes vs the legacy ragas.metrics module.
METRIC_REGISTRY: dict[str, tuple[str, bool]] = {
    "faithfulness": ("Faithfulness", False),
    "response_relevancy": ("AnswerRelevancy", False),
    "context_precision": ("ContextPrecisionWithoutReference", False),
    "context_recall": ("ContextRecall", True),
}


def _format_chunk_for_context(c: dict) -> str:
    """Render a chunk for RAGAS retrieved_contexts list — content only.

    No source/page header: empirically (smoke 2026-05-02) the bracketed header
    didn't move scores. The bigger trap is the bot's own [F1][F2] citation
    markers in the response — those are stripped separately in _strip_markers.
    """
    return (c.get("content") or "").strip()


_MARKER_RE = __import__("re").compile(r"\s*\[F\d+\](?:\s*\[F\d+\])*")

def _strip_citation_markers(text: str) -> str:
    """Remove [F1], [F1][F2], [F12], etc. from the bot's response.

    RAGAS Faithfulness decomposes the response into atomic claims and checks
    each against retrieved_contexts. The markers are not natural-language
    claims, but the LLM sees [F1] as an extra unsupported claim. Empirically
    (smoke 2026-05-02 on hp016) this fix moves faithfulness from 0.0 to 0.55.
    Pass --keep-markers on the CLI to disable this.
    """
    return _MARKER_RE.sub("", text or "").strip()


def _most_recent_eval_log(logs_dir: Path) -> Path | None:
    candidates = sorted(logs_dir.glob("eval_*.json"))
    return candidates[-1] if candidates else None


def _load_eval_log(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_baseline(path: Path) -> dict[str, dict]:
    """Read baseline_v1.yaml and index questions by id for fast lookup."""
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {q["id"]: q for q in data.get("questions", []) if "id" in q}


def _build_samples(eval_results: list[dict],
                   baseline_by_id: dict[str, dict],
                   only: set[str] | None,
                   keep_markers: bool = False) -> tuple[list[dict], list[str], list[str]]:
    """Return (samples, with_ref_ids, without_ref_ids).

    samples is a list of dicts with the SingleTurnSample fields RAGAS expects.
    with_ref_ids vs without_ref_ids tracks which cases can run LLMContextRecall.
    Cases with errors or empty chunks are skipped (logged to stderr).
    """
    samples: list[dict] = []
    with_ref: list[str] = []
    without_ref: list[str] = []
    skipped: list[tuple[str, str]] = []

    for r in eval_results:
        q = r.get("question") or {}
        qid = q.get("id", "?")
        if only and qid not in only:
            continue

        result = r.get("result") or {}
        if result.get("error"):
            skipped.append((qid, f"runner error: {result.get('error')}"))
            continue

        answer = result.get("answer") or ""
        if not answer.strip():
            skipped.append((qid, "empty answer"))
            continue

        chunks_full = result.get("chunks_full") or []
        if not chunks_full:
            skipped.append((qid, "no chunks_full — re-run eval with --include-full-chunks"))
            continue

        retrieved_contexts = [_format_chunk_for_context(c) for c in chunks_full]
        clean_response = answer if keep_markers else _strip_citation_markers(answer)

        sample = {
            "user_input": q.get("question", ""),
            "retrieved_contexts": retrieved_contexts,
            "response": clean_response,
        }

        # Optional ground_truth from baseline YAML
        ref = (baseline_by_id.get(qid) or {}).get("reference_answer")
        if ref:
            sample["reference"] = ref
            with_ref.append(qid)
        else:
            without_ref.append(qid)

        sample["_qid"] = qid  # tag for post-hoc lookup; stripped before EvaluationDataset
        samples.append(sample)

    if skipped:
        print(f"[skipped {len(skipped)} cases]")
        for qid, why in skipped[:10]:
            print(f"  {qid}: {why}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")

    return samples, with_ref, without_ref


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None,
                    help="Path to eval_<ts>.json (default: most recent in logs/)")
    ap.add_argument("--baseline", default="evals/baseline_v1.yaml",
                    help="YAML with `reference_answer` per question (enables context_recall)")
    ap.add_argument("--only", default=None,
                    help="Comma-separated question ids to score (e.g. hp012,hp016)")
    ap.add_argument("--metrics", default="faithfulness,response_relevancy,context_precision,context_recall",
                    help="Comma-separated metrics. Choices: " + ",".join(METRIC_REGISTRY))
    ap.add_argument("--output-dir", default="logs",
                    help="Where to write the RAGAS report JSON")
    ap.add_argument("--judge-model", default=JUDGE_MODEL,
                    help=f"Claude model name for evaluator LLM (default: {JUDGE_MODEL})")
    args = ap.parse_args()

    # Resolve input path
    logs_dir = ROOT / "logs"
    if args.input:
        in_path = Path(args.input)
        if not in_path.is_absolute():
            in_path = ROOT / in_path
    else:
        in_path = _most_recent_eval_log(logs_dir)
        if in_path is None:
            print(f"ERROR: no eval_*.json found in {logs_dir}")
            return 1
        print(f"Using most recent eval log: {in_path.name}")

    if not in_path.exists():
        print(f"ERROR: eval log not found: {in_path}")
        return 1

    # API keys sanity check
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set (needed for evaluator LLM)")
        return 1
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set (needed for embeddings)")
        return 1

    # Validate requested metrics
    requested = [m.strip() for m in args.metrics.split(",") if m.strip()]
    unknown = [m for m in requested if m not in METRIC_REGISTRY]
    if unknown:
        print(f"ERROR: unknown metrics {unknown}. Available: {list(METRIC_REGISTRY)}")
        return 1

    only_ids = {s.strip() for s in args.only.split(",")} if args.only else None

    # Load inputs
    eval_log = _load_eval_log(in_path)
    eval_results = eval_log.get("results", [])
    print(f"Loaded {len(eval_results)} cases from {in_path.name}")

    baseline_path = ROOT / args.baseline
    baseline_by_id: dict[str, dict] = {}
    if baseline_path.exists():
        baseline_by_id = _load_baseline(baseline_path)
        print(f"Loaded {len(baseline_by_id)} baseline entries from {baseline_path.name}")
    else:
        print(f"(no baseline at {baseline_path}; context_recall will be skipped)")

    # Build samples
    samples, with_ref, without_ref = _build_samples(
        eval_results, baseline_by_id, only_ids
    )
    if not samples:
        print("ERROR: no scoreable samples (all skipped)")
        return 1
    print(f"Scoreable: {len(samples)} (with reference: {len(with_ref)}, without: {len(without_ref)})")

    # Lazy imports — modern ragas.metrics.collections API: each metric is its
    # own object constructed with its own llm/embeddings, scored per-sample with
    # `metric.score(**kwargs)`. No EvaluationDataset / evaluate() — that path
    # only accepts the deprecated metric module and silently filters the new
    # collection metrics out.
    print("Importing RAGAS + Anthropic + OpenAI...")
    from ragas.llms import llm_factory
    from ragas.embeddings import OpenAIEmbeddings as RagasOpenAIEmbeddings
    from ragas.metrics.collections import (
        Faithfulness, AnswerRelevancy,
        ContextRecall, ContextPrecisionWithoutReference,
    )
    import anthropic
    from openai import OpenAI

    metric_classes = {
        "Faithfulness": Faithfulness,
        "AnswerRelevancy": AnswerRelevancy,
        "ContextPrecisionWithoutReference": ContextPrecisionWithoutReference,
        "ContextRecall": ContextRecall,
    }

    # Each metric.score() takes a different kwarg subset. Centralised here so
    # the scoring loop stays generic.
    def _kwargs_for(cls_name: str, sample: dict) -> dict:
        if cls_name == "Faithfulness":
            return {"user_input": sample["user_input"], "response": sample["response"],
                    "retrieved_contexts": sample["retrieved_contexts"]}
        if cls_name == "AnswerRelevancy":
            return {"user_input": sample["user_input"], "response": sample["response"]}
        if cls_name == "ContextPrecisionWithoutReference":
            return {"user_input": sample["user_input"], "response": sample["response"],
                    "retrieved_contexts": sample["retrieved_contexts"]}
        if cls_name == "ContextRecall":
            return {"user_input": sample["user_input"],
                    "retrieved_contexts": sample["retrieved_contexts"],
                    "reference": sample["reference"]}
        raise ValueError(f"unknown metric class {cls_name}")

    # Configure clients + evaluator stack. RAGAS metrics .score() internally
    # calls agenerate(), which requires async clients (AsyncAnthropic / AsyncOpenAI).
    print(f"Configuring evaluator: judge={args.judge_model}, embeddings={EMBED_MODEL}")
    from openai import AsyncOpenAI
    anthropic_client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    evaluator_llm = llm_factory(args.judge_model, provider="anthropic", client=anthropic_client)
    # RAGAS' Instructor adapter sets BOTH temperature and top_p by default, but
    # Anthropic Sonnet 4.6+ rejects sending both — pick one.
    # max_tokens needs to be high — Faithfulness on dense answers can produce
    # JSON with 30+ claim verdicts; 1024 (the RAGAS default) truncates.
    evaluator_llm.model_args = {"temperature": 0.01, "max_tokens": 4096}
    evaluator_embeddings = RagasOpenAIEmbeddings(client=openai_client, model=EMBED_MODEL)

    def _build_metric(cls_name: str):
        cls = metric_classes[cls_name]
        if cls is AnswerRelevancy:
            return cls(llm=evaluator_llm, embeddings=evaluator_embeddings)
        return cls(llm=evaluator_llm)

    # Build metric instances and remember which need a reference
    metric_objs: list[tuple[str, str, object, bool]] = []  # (name, cls_name, instance, requires_ref)
    for name in requested:
        cls_name, requires_ref = METRIC_REGISTRY[name]
        metric_objs.append((name, cls_name, _build_metric(cls_name), requires_ref))

    qids = [s.pop("_qid") for s in samples]
    with_ref_set = set(with_ref)
    per_case: dict[str, dict] = {qid: {} for qid in qids}

    print(f"\nScoring {len(samples)} samples × {len(metric_objs)} metrics "
          f"(reference-only metrics skipped on {len(without_ref)} samples)...")
    for i, (sample, qid) in enumerate(zip(samples, qids), 1):
        scores_str = []
        for name, cls_name, metric, requires_ref in metric_objs:
            if requires_ref and qid not in with_ref_set:
                per_case[qid][name] = None
                scores_str.append(f"{name}=skip")
                continue
            try:
                kwargs = _kwargs_for(cls_name, sample)
                result = metric.score(**kwargs)
                # MetricResult exposes .value (float in [0,1])
                val = float(result.value) if result.value is not None else None
                per_case[qid][name] = val
                scores_str.append(f"{name}={val:.2f}" if val is not None else f"{name}=—")
            except Exception as e:
                per_case[qid][name] = None
                scores_str.append(f"{name}=ERR")
                print(f"  [{i}/{len(samples)}] {qid} {name}: {type(e).__name__}: {e}")
        print(f"  [{i}/{len(samples)}] {qid}  " + " ".join(scores_str))

    # Aggregate
    print()
    print("=" * 70)
    print("RAGAS SUMMARY")
    print("=" * 70)
    aggregate: dict[str, dict] = {}
    for name in requested:
        vals = [per_case[qid].get(name) for qid in qids if per_case[qid].get(name) is not None]
        if not vals:
            aggregate[name] = {"mean": None, "n": 0}
            continue
        aggregate[name] = {
            "mean": round(sum(vals) / len(vals), 3),
            "n": len(vals),
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
        }

    print(f"{'metric':<28s} {'mean':>8s} {'n':>5s} {'min':>8s} {'max':>8s}")
    print("-" * 60)
    for name, agg in aggregate.items():
        mean = f"{agg['mean']:.3f}" if agg.get("mean") is not None else "—"
        n = agg["n"]
        if n:
            print(f"{name:<28s} {mean:>8s} {n:>5d} {agg['min']:>8.3f} {agg['max']:>8.3f}")
        else:
            print(f"{name:<28s} {'—':>8s} {0:>5d}      —      —")

    # Per-case dump (worst 10 by faithfulness, lo más relevante para alucinaciones)
    fpc = [(qid, per_case[qid].get("faithfulness")) for qid in qids
           if per_case[qid].get("faithfulness") is not None]
    fpc.sort(key=lambda x: x[1])
    if fpc:
        print()
        print(f"Worst 10 by faithfulness:")
        for qid, val in fpc[:10]:
            scores = per_case[qid]
            tags = " ".join(f"{k}={v:.2f}" if v is not None else f"{k}=—"
                            for k, v in scores.items())
            print(f"  {qid:<10s} {tags}")

    # Persist
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"ragas_{ts}.json"
    out_path.write_text(json.dumps({
        "source_eval_log": in_path.name,
        "judge_model": args.judge_model,
        "embed_model": EMBED_MODEL,
        "metrics_requested": requested,
        "n_samples": len(qids),
        "n_with_reference": len(with_ref),
        "aggregate": aggregate,
        "per_case": per_case,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
