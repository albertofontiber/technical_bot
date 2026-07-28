#!/usr/bin/env python3
"""Freeze the integrated candidate serving context for all 39 S100 questions.

The production post-rerank selector runs with every candidate lane enabled over
the immutable S100 reranker prefix and frozen retrieval pool. Selection receives
only question text and source rows; fact packets are joined afterwards. This is
GET-only and makes no embedding, reranker, generator, judge, or database write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
POOLS = ROOT / "evals/s102_toc_pools.json"
OUT = ROOT / "evals/s113_full_contexts_freeze_v1.json"
IMPLEMENTATION_INPUTS = (
    ROOT / "src/rag/post_rerank_coverage.py",
    ROOT / "src/rag/structural_neighbor_coverage.py",
    ROOT / "src/rag/doc_scoped_hyq_coverage.py",
    ROOT / "src/rag/rerank_pool_coverage.py",
    ROOT / "config/structural_cascade_coverage_v1.yaml",
    ROOT / "config/evidence_coverage_facets_cascade_v1.yaml",
)


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    os.environ.update(
        {
            "CHUNKS_TABLE": "chunks_v2",
            "POST_RERANK_COVERAGE": "on",
            "STRUCTURAL_NEIGHBOR_COVERAGE": "on",
            "CANONICAL_HYQ_COVERAGE": "on",
            "RERANK_POOL_COVERAGE": "on",
            "STRUCTURAL_CASCADE_COVERAGE": "on",
            "LOGICAL_RECORD_COVERAGE": "on",
        }
    )
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
    pools = json.loads(POOLS.read_text(encoding="utf-8"))
    # Selection projection deliberately excludes facts and answers.
    questions = [
        {
            "qid": row["qid"],
            "question": row["question"],
            "served_ids": [str(value) for value in row["served_ids"]],
        }
        for row in baseline["per_gold"]
    ]
    if set(pools) != {row["qid"] for row in questions}:
        raise RuntimeError("frozen pool and S100 question sets differ")

    selected_rows = []
    hydration_batches = 0
    for question in questions:
        qid = question["qid"]
        retrieval_pool = [dict(row) for row in pools[qid]]
        by_id = {str(row["id"]): row for row in retrieval_pool}
        missing = [value for value in question["served_ids"] if value not in by_id]
        if missing:
            by_id.update(_hydrate_missing(missing, SUPABASE_URL, SUPABASE_SERVICE_KEY))
            hydration_batches += 1
        absent = [value for value in question["served_ids"] if value not in by_id]
        if absent:
            raise RuntimeError(f"{qid}: missing frozen prefix rows {absent}")
        prefix = [by_id[value] for value in question["served_ids"]]
        prefix_snapshot = deepcopy(prefix)
        context, trace = apply_post_rerank_coverage_with_trace(
            question["question"],
            prefix,
            retrieval_pool=retrieval_pool,
            enabled=True,
            structural_enabled=True,
            hyq_enabled=True,
            pool_enabled=True,
            cascade_enabled=True,
        )
        appended = context[len(prefix):]
        served_content = [coverage_context_content(row) for row in context]
        selected_rows.append(
            {
                "qid": qid,
                "question": question["question"],
                "prefix_ids": question["served_ids"],
                "protected_prefix_equal": context[: len(prefix)] == prefix_snapshot,
                "appended_ids": [str(row.get("id") or "") for row in appended],
                "appended_lanes": [row.get("retrieval_lane") for row in appended],
                "all_appended_have_exact_served_receipts": all(
                    has_exact_served_coverage_receipt(row) for row in appended
                ),
                "context_rows": len(context),
                "serving_context_sha256": stable_sha(served_content),
                "context": context,
                "trace": trace,
            }
        )

    # Gold information is joined only after every selection is frozen.
    gold_by_qid = {row["qid"]: row for row in baseline["per_gold"]}
    for row in selected_rows:
        gold = gold_by_qid[row["qid"]]
        row["baseline_answer"] = gold["answer"]
        row["facts"] = [
            {
                "key": fact["key"],
                "valor": fact.get("valor"),
                "texto": fact.get("texto"),
                "baseline_class": fact["clase"],
            }
            for fact in gold["facts"]
        ]

    lane_errors = [
        {"qid": row["qid"], "lane": lane.get("lane"), "error_type": lane.get("error_type")}
        for row in selected_rows
        for lane in row["trace"].get("lanes", [])
        if lane.get("status") == "error"
    ]
    appended = [item for row in selected_rows for item in row["appended_ids"]]
    gate = {
        "questions": len(selected_rows),
        "fact_rows": sum(len(row["facts"]) for row in selected_rows),
        "questions_with_appends": sum(bool(row["appended_ids"]) for row in selected_rows),
        "appended_rows": len(appended),
        "max_appended_rows_per_question": max(len(row["appended_ids"]) for row in selected_rows),
        "all_protected_prefixes_equal": all(row["protected_prefix_equal"] for row in selected_rows),
        "all_appended_have_exact_served_receipts": all(
            row["all_appended_have_exact_served_receipts"] for row in selected_rows
        ),
        "lane_errors": lane_errors,
        "baseline_hydration_get_batches": hydration_batches,
        "coverage_lane_get_requests": sum(
            int(lane.get("http_requests") or 0)
            for row in selected_rows
            for lane in row["trace"].get("lanes", [])
        ),
        "embedding_calls": 0,
        "reranker_calls": 0,
        "generator_calls": 0,
        "judge_calls": 0,
        "database_writes": 0,
    }
    gate["database_get_requests"] = (
        gate["baseline_hydration_get_batches"] + gate["coverage_lane_get_requests"]
    )
    gate["interpretation"] = (
        "GO_FULL_CONTEXT_FREEZE"
        if gate["questions"] == 39
        and gate["fact_rows"] == 129
        and gate["max_appended_rows_per_question"] <= 4
        and gate["all_protected_prefixes_equal"]
        and gate["all_appended_have_exact_served_receipts"]
        and not lane_errors
        else "NO_GO_FULL_CONTEXT_FREEZE"
    )
    payload = {
        "instrument": "s113_full_contexts_freeze_v1",
        "selection_completed_before_fact_packet_load": True,
        "candidate_flags": {
            key: os.environ[key]
            for key in (
                "POST_RERANK_COVERAGE",
                "STRUCTURAL_NEIGHBOR_COVERAGE",
                "CANONICAL_HYQ_COVERAGE",
                "RERANK_POOL_COVERAGE",
                "STRUCTURAL_CASCADE_COVERAGE",
                "LOGICAL_RECORD_COVERAGE",
            )
        },
        "implementation_inputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in IMPLEMENTATION_INPUTS
        ],
        "corpus_snapshot": baseline["manifest"]["corpus"],
        "frozen_contexts_sha256": stable_sha(
            {row["qid"]: row["serving_context_sha256"] for row in selected_rows}
        ),
        "gate": gate,
        "rows": selected_rows,
        "limitations": [
            "The immutable S100 reranker prefix and retrieval-pool artifact are reused; no live retrieval or reranking is performed.",
            "This known cohort measures integrated behavior but is not held-out deployment evidence.",
            "No fact, expected value, support ID, or QID is available to the production selector.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate["interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
