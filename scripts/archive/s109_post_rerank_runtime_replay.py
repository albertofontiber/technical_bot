#!/usr/bin/env python3
"""Exercise the real default-off post-rerank serving seam without model calls.

Inputs are the frozen paid reranker top-10 IDs in S100.  Both coverage lanes use
their production GET-only collectors.  Gold facts are joined only after all
selection is complete, so they can evaluate movement but cannot influence it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
OUT = ROOT / "evals/s109_post_rerank_runtime_replay_v1.json"
TARGET_QIDS = ("hp011", "hp012", "hp013", "hp014", "hp017")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))

    # Import only after loading the explicitly selected environment.  No
    # generator, reranker or embedding client is imported or invoked.
    from s108_structural_retrieval_replay import evaluate_retrieval_facts
    from src.rag.post_rerank_coverage import (
        apply_post_rerank_coverage_with_trace,
        is_validated_coverage_chunk,
    )

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    questions = [
        row for row in baseline["per_gold"] if row["qid"] in TARGET_QIDS
    ]
    started = time.perf_counter()
    receipts = []
    evaluation_selections = []
    for question in questions:
        frozen_prefix = [{"id": str(value)} for value in question["served_ids"]]
        output, trace = apply_post_rerank_coverage_with_trace(
            question["question"],
            frozen_prefix,
            enabled=True,
            structural_enabled=True,
            hyq_enabled=True,
        )
        appended = output[len(frozen_prefix):]
        receipts.append(
            {
                "qid": question["qid"],
                "question_sha256": _sha256_bytes(
                    question["question"].encode("utf-8")
                ),
                "frozen_prefix_ids": [row["id"] for row in frozen_prefix],
                "protected_prefix_equal": output[: len(frozen_prefix)] == frozen_prefix,
                "appended": [
                    {
                        "id": str(row["id"]),
                        "source_file": row.get("source_file"),
                        "product_model": row.get("product_model"),
                        "page_number": row.get("page_number"),
                        "retrieval_lane": row.get("retrieval_lane"),
                        "content_sha256": _sha256_bytes(
                            (row.get("content") or "").encode("utf-8")
                        ),
                        "coverage_card_facets": row.get("coverage_card_facets") or [],
                        "coverage_quotes": [
                            card["quote"] for card in row.get("coverage_cards") or []
                        ],
                        "generator_admitted": is_validated_coverage_chunk(row),
                    }
                    for row in appended
                ],
                "trace": trace,
            }
        )
        evaluation_selections.append(
            {
                "qid": question["qid"],
                "selected": [
                    {
                        "id": str(row["id"]),
                        "rank": index,
                        "product_model": row.get("product_model"),
                        "content": row.get("content") or "",
                        "content_sha256": _sha256_bytes(
                            (row.get("content") or "").encode("utf-8")
                        ),
                    }
                    for index, row in enumerate(appended, 1)
                ],
            }
        )

    retrieval_facts = evaluate_retrieval_facts(questions, evaluation_selections)
    recovered = [
        row["key"] for row in retrieval_facts
        if row["structural_retrieval_precondition"]
    ]
    gate = {
        "queries": len(questions),
        "retrieval_facts": len(retrieval_facts),
        "runtime_appended_rows": sum(len(row["appended"]) for row in receipts),
        "generator_admitted_rows": sum(
            sum(bool(item["generator_admitted"]) for item in row["appended"])
            for row in receipts
        ),
        "protected_prefixes_equal": all(
            row["protected_prefix_equal"] for row in receipts
        ),
        "model_calls": 0,
        "database_writes": 0,
        "recovered_retrieval_keys": sorted(recovered),
    }
    expected = {
        "hp011#2:05 a 295 seg",
        "hp012#3:4 lazos / 792",
        "hp013#1:PWR-R",
        "hp014#3:35",
        "hp017#1:instruccion de entrada",
    }
    gate["interpretation"] = (
        "GO_REAL_RUNTIME_5_OF_5_TO_DOWNSTREAM"
        if set(recovered) == expected
        and gate["protected_prefixes_equal"]
        and gate["runtime_appended_rows"] == gate["generator_admitted_rows"]
        else "REVISE_REAL_RUNTIME_COVERAGE"
    )
    payload = {
        "instrument": "s109_post_rerank_runtime_replay_v1",
        "read_only": True,
        "actual_bot_module": "src.rag.post_rerank_coverage",
        "selection_contract": {
            "target_facts_available_during_selection": False,
            "frozen_paid_reranker_prefix": True,
            "generated_hyq_prose_served": False,
            "real_source_span_required": True,
            "protected_prefix_required": True,
            "railway_changed": False,
        },
        "frozen_inputs": {
            "baseline_sha256": _sha256_bytes(BASELINE.read_bytes()),
            "git_head": os.popen("git rev-parse HEAD").read().strip(),
        },
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "gate": gate,
        "retrieval_facts_after_runtime": retrieval_facts,
        "receipts": receipts,
        "limitations": [
            "This reuses a known evaluation cohort and cannot prove held-out generalisation.",
            "It proves evidence reaches the generator boundary, not that synthesis conveys every fact.",
            "CAT007 is excluded because S108 established it was a measurement defect, not a runtime retrieval miss.",
            "Official OK remains unchanged until downstream synthesis and regression gates pass.",
        ],
    }
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate["interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
