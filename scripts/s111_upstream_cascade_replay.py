#!/usr/bin/env python3
"""Zero-model replay of pool -> same-blob structural cascade and prompt support."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import unicodedata
from copy import deepcopy
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
POOLS = ROOT / "evals/s102_toc_pools.json"
COHORT = ROOT / "evals/s111_served_support_cohort_v1.yaml"
OUT = ROOT / "evals/s111_upstream_cascade_replay_v1.json"
IMPLEMENTATION_INPUTS = (
    ROOT / "src/rag/post_rerank_coverage.py",
    ROOT / "src/config.py",
    ROOT / "src/rag/rerank_pool_coverage.py",
    ROOT / "src/rag/structural_neighbor_coverage.py",
    ROOT / "config/structural_cascade_coverage_v1.yaml",
    ROOT / "config/retrieval_facets_v4.yaml",
    ROOT / "config/evidence_coverage_facets_cascade_v1.yaml",
    ROOT / "config/evidence_coverage_facets_v5.yaml",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(without_marks.casefold().split())


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from src.rag.post_rerank_coverage import (
        apply_post_rerank_coverage_with_trace,
        coverage_context_content,
        has_exact_coverage_receipt,
        has_exact_served_coverage_receipt,
        is_validated_coverage_chunk,
    )
    from src.rag.structural_neighbor_coverage import CASCADED_LANE

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    pools = json.loads(POOLS.read_text(encoding="utf-8"))

    # Selection is completed for every available question before the
    # adjudicated needle packet is loaded into memory.
    receipts = []
    for question in baseline["per_gold"]:
        qid = question["qid"]
        if qid not in pools:
            continue
        pool = pools[qid]
        by_id = {str(row.get("id") or ""): row for row in pool}
        reranked = [
            deepcopy(by_id.get(str(row_id), {"id": str(row_id)}))
            for row_id in question["served_ids"]
        ]
        prefix = deepcopy(reranked)
        output, trace = apply_post_rerank_coverage_with_trace(
            question["question"],
            reranked,
            retrieval_pool=pool,
            enabled=True,
            structural_enabled=False,
            hyq_enabled=False,
            pool_enabled=True,
            cascade_enabled=True,
        )
        appended = output[len(reranked):]
        receipts.append(
            {
                "qid": qid,
                "protected_prefix_equal": output[: len(reranked)] == prefix,
                "selected": [
                    {
                        "id": str(row.get("id") or ""),
                        "lane": row.get("retrieval_lane"),
                        "source_file": row.get("source_file"),
                        "page_number": row.get("page_number"),
                        "exact_receipt": has_exact_coverage_receipt(row),
                        "served_exact_receipt": (
                            has_exact_served_coverage_receipt(row)
                        ),
                        "generator_admitted": is_validated_coverage_chunk(row),
                        "served_excerpt": coverage_context_content(
                            row, logical_record_expansion=True
                        ),
                    }
                    for row in appended
                ],
                "trace": trace,
            }
        )

    cohort = yaml.safe_load(COHORT.read_text(encoding="utf-8"))
    selected_by_qid = {
        row["qid"]: {item["id"]: item for item in row["selected"]}
        for row in receipts
    }
    claim_results = []
    for claim in cohort["claims"]:
        selected = selected_by_qid.get(claim["qid"], {})
        matched_bundle = None
        for bundle in claim["support_any"]:
            if not set(bundle["ids"]).issubset(selected):
                continue
            prompt_text = "\n".join(
                selected[row_id]["served_excerpt"] for row_id in bundle["ids"]
            )
            if all(_fold(needle) in _fold(prompt_text) for needle in bundle["needles"]):
                matched_bundle = bundle
                break
        claim_results.append(
            {
                "claim_id": claim["claim_id"],
                "qid": claim["qid"],
                "literal_support_reaches_prompt": matched_bundle is not None,
                "matched_ids": (matched_bundle or {}).get("ids", []),
            }
        )

    selected_rows = [item for row in receipts for item in row["selected"]]
    cascade_rows = [
        item for item in selected_rows if item["lane"] == CASCADED_LANE
    ]
    http_requests = sum(
        int(lane.get("http_requests") or 0)
        for row in receipts
        for lane in row["trace"].get("lanes") or []
    )
    recovered = sum(
        row["literal_support_reaches_prompt"] for row in claim_results
    )
    gate = {
        "claims_reconciled": len(claim_results),
        "literal_support_reaches_prompt": recovered,
        "support_recovery_rate": round(recovered / len(claim_results), 4),
        "questions_replayed": len(receipts),
        "questions_with_cascade_append": sum(
            any(item["lane"] == CASCADED_LANE for item in row["selected"])
            for row in receipts
        ),
        "cascade_rows_appended": len(cascade_rows),
        "max_total_appended_per_question": max(
            (len(row["selected"]) for row in receipts), default=0
        ),
        "all_protected_prefixes_equal": all(
            row["protected_prefix_equal"] for row in receipts
        ),
        "all_selected_have_exact_receipts": all(
            row["exact_receipt"] for row in selected_rows
        ),
        "all_served_excerpts_have_exact_receipts": all(
            row["served_exact_receipt"] for row in selected_rows
        ),
        "all_selected_admitted_by_generator_boundary": all(
            row["generator_admitted"] for row in selected_rows
        ),
        "model_calls": 0,
        "database_get_requests": http_requests,
        "database_writes": 0,
        "official_ok_delta": 0,
    }
    causal_go = (
        recovered == len(claim_results)
        and gate["all_protected_prefixes_equal"]
        and gate["all_selected_have_exact_receipts"]
        and gate["all_served_excerpts_have_exact_receipts"]
        and gate["all_selected_admitted_by_generator_boundary"]
        and gate["max_total_appended_per_question"] <= 4
    )
    gate["interpretation"] = (
        "GO_UPSTREAM_3_OF_3_PROMPT_SUPPORT_HOLD_SYNTHESIS"
        if causal_go else "REVISE_UPSTREAM_SUPPORT_BOUNDARY"
    )

    payload = {
        "instrument": "s111_upstream_cascade_replay_v1",
        "read_only": True,
        "selection_completed_before_claim_packet_load": True,
        "inputs": {
            "baseline_sha256": _sha(BASELINE),
            "pool_sha256": _sha(POOLS),
            "cohort_sha256": _sha(COHORT),
            "implementation_inputs": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": _sha(path),
                }
                for path in IMPLEMENTATION_INPUTS
            ],
            "git_head": _git_head(),
        },
        "gate": gate,
        "claim_results": claim_results,
        "receipts": receipts,
        "limitations": cohort["limitations"],
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if causal_go else 1


if __name__ == "__main__":
    raise SystemExit(main())
