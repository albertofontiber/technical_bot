#!/usr/bin/env python3
"""Freeze real combined serving contexts with no model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
POOLS = ROOT / "evals/s102_toc_pools.json"
LOCAL_REPLAY = ROOT / "evals/s110_rerank_pool_replay_v1.json"
COHORT = ROOT / "evals/s110_atomic_rerank_cohort_v1.yaml"
OUT = ROOT / "evals/s110_combined_contexts_v1.json"
IMPLEMENTATION_INPUTS = (
    ROOT / "src/rag/post_rerank_coverage.py",
    ROOT / "src/rag/structural_neighbor_coverage.py",
    ROOT / "src/rag/doc_scoped_hyq_coverage.py",
    ROOT / "config/structural_cascade_coverage_v1.yaml",
    ROOT / "config/evidence_coverage_facets_cascade_v1.yaml",
)


def _stable_sha(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    ).hexdigest()


def _bundle_reaches(selected: set[str], alternatives: list[list[str]]) -> bool:
    return any(set(bundle).issubset(selected) for bundle in alternatives)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--instrument", default="s110_combined_contexts_v1")
    parser.add_argument("--cascade", action="store_true")
    parser.add_argument("--logical-record", action="store_true")
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))

    from s109_bounded_synthesis_runtime_pilot import _hydrate_missing
    from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
    from src.rag.post_rerank_coverage import (
        apply_post_rerank_coverage_with_trace,
        coverage_context_content,
        has_exact_served_coverage_receipt,
    )

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    rows = {row["qid"]: row for row in baseline["per_gold"]}
    pools = json.loads(POOLS.read_text(encoding="utf-8"))
    local = json.loads(LOCAL_REPLAY.read_text(encoding="utf-8"))
    qids = [row["qid"] for row in local["receipts"] if row["selected"]]

    frozen = []
    for qid in qids:
        question = rows[qid]
        by_id = {str(row["id"]): dict(row) for row in pools[qid]}
        prefix_ids = [str(value) for value in question["served_ids"]]
        missing = [value for value in prefix_ids if value not in by_id]
        by_id.update(_hydrate_missing(missing, SUPABASE_URL, SUPABASE_SERVICE_KEY))
        prefix = [by_id[value] for value in prefix_ids]
        prefix_snapshot = deepcopy(prefix)
        context, trace = apply_post_rerank_coverage_with_trace(
            question["question"],
            prefix,
            retrieval_pool=pools[qid],
            enabled=True,
            structural_enabled=True,
            hyq_enabled=True,
            pool_enabled=True,
            cascade_enabled=args.cascade,
        )
        appended = context[len(prefix):]
        frozen.append(
            {
                "qid": qid,
                "question": question["question"],
                "protected_ok_facts": [
                    {
                        "key": fact["key"],
                        "valor": fact.get("valor"),
                        "texto": fact.get("texto"),
                    }
                    for fact in question["facts"]
                    if fact["clase"] == "OK"
                ],
                "baseline_answer": question["answer"],
                "prefix_ids": prefix_ids,
                "missing_prefix_rows_hydrated": len(missing),
                "protected_prefix_equal": context[: len(prefix)] == prefix_snapshot,
                "appended_ids": [str(row["id"]) for row in appended],
                "appended_lanes": [row.get("retrieval_lane") for row in appended],
                "appended_source_chars": sum(
                    len(row.get("content") or "") for row in appended
                ),
                "appended_served_chars": sum(
                    len(coverage_context_content(
                        row, logical_record_expansion=args.logical_record
                    ))
                    for row in appended
                ),
                "prompt_context_chars": sum(
                    len(coverage_context_content(
                        row, logical_record_expansion=args.logical_record
                    ))
                    for row in context
                ),
                "all_appended_have_exact_served_receipts": all(
                    has_exact_served_coverage_receipt(row) for row in appended
                ),
                "context_sha256": _stable_sha(context),
                "context": context,
                "trace": trace,
            }
        )

    # Targets are joined after every context has been selected and frozen.
    cohort = yaml.safe_load(COHORT.read_text(encoding="utf-8"))
    selected_by_qid = {
        row["qid"]: set(row["appended_ids"])
        for row in frozen
    }
    claim_results = []
    for claim in cohort["residual_rerank_claims"]:
        selected = selected_by_qid.get(claim["qid"], set())
        claim_results.append(
            {
                "claim_id": claim["claim_id"],
                "qid": claim["qid"],
                "reaches_generator": _bundle_reaches(selected, claim["support_any"]),
            }
        )
    protected_ok_count = sum(len(row["protected_ok_facts"]) for row in frozen)
    gate = {
        "affected_questions": len(frozen),
        "combined_runtime_residual_claims": len(claim_results),
        "combined_runtime_reaches_generator": sum(
            row["reaches_generator"] for row in claim_results
        ),
        "protected_ok_facts_requiring_answer_regression": protected_ok_count,
        "protected_ok_facts_bit_inert": baseline["aggregate_hist"]["OK"] - protected_ok_count,
        "all_protected_prefixes_equal": all(
            row["protected_prefix_equal"] for row in frozen
        ),
        "all_appended_have_exact_served_receipts": all(
            row["all_appended_have_exact_served_receipts"] for row in frozen
        ),
        "max_combined_appends": max(len(row["appended_ids"]) for row in frozen),
        "total_appended_source_chars": sum(
            row["appended_source_chars"] for row in frozen
        ),
        "total_appended_served_chars": sum(
            row["appended_served_chars"] for row in frozen
        ),
        "model_calls": 0,
        "prefix_hydration_get_requests": sum(
            bool(row["missing_prefix_rows_hydrated"]) for row in frozen
        ),
        "coverage_lane_get_requests": sum(
            int(lane.get("http_requests") or 0)
            for row in frozen
            for lane in row["trace"].get("lanes") or []
        ),
        "database_writes": 0,
    }
    gate["database_get_requests"] = (
        gate["prefix_hydration_get_requests"]
        + gate["coverage_lane_get_requests"]
    )
    source_chars = gate["total_appended_source_chars"]
    gate["served_context_fraction"] = round(
        gate["total_appended_served_chars"] / source_chars, 4
    ) if source_chars else 0.0
    gate["interpretation"] = (
        "GO_COMBINED_CONTEXT_FREEZE_PENDING_11_ANSWER_REGRESSIONS"
        if gate["combined_runtime_reaches_generator"] == len(claim_results)
        and gate["all_protected_prefixes_equal"]
        and gate["all_appended_have_exact_served_receipts"]
        and gate["max_combined_appends"] <= 4
        else "REVISE_COMBINED_CONTEXT"
    )
    payload = {
        "instrument": args.instrument,
        "logical_record_expansion": args.logical_record,
        "implementation_inputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in IMPLEMENTATION_INPUTS
        ],
        "selection_completed_before_claim_packet_load": True,
        "frozen_contexts_sha256": _stable_sha(
            {row["qid"]: row["context_sha256"] for row in frozen}
        ),
        "gate": gate,
        "claim_results": claim_results,
        "rows": frozen,
        "limitations": [
            "This freeze performs bounded GET-only hydration/navigation and no model calls.",
            "Only the 11 questions whose context changes require paid answer regression; the other protected OK facts are bit-inert at the generator input.",
            "The known development cohort is not held-out deployment evidence.",
        ],
    }
    output_path = args.out if args.out.is_absolute() else ROOT / args.out
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate["interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
