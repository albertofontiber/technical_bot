#!/usr/bin/env python3
"""Local, zero-model replay of the default-off retrieval-pool complement.

Selection is executed for every available frozen question before the atomic
claim packet is loaded.  The packet can therefore measure stage movement but
cannot influence ranking.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
POOLS = ROOT / "evals/s102_toc_pools.json"
COHORT = ROOT / "evals/s110_atomic_rerank_cohort_v1.yaml"
OUT = ROOT / "evals/s110_rerank_pool_replay_v1.json"
IMPLEMENTATION_INPUTS = (
    ROOT / "src/rag/rerank_pool_coverage.py",
    ROOT / "src/rag/post_rerank_coverage.py",
    ROOT / "config/retrieval_facets_v4.yaml",
    ROOT / "config/evidence_coverage_facets_v5.yaml",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_reaches(selected: set[str], alternatives: list[list[str]]) -> bool:
    return any(set(bundle).issubset(selected) for bundle in alternatives)


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from src.rag.post_rerank_coverage import (
        apply_post_rerank_coverage_with_trace,
        coverage_context_content,
        has_exact_coverage_receipt,
        is_validated_coverage_chunk,
    )
    from src.rag.toc_detection import is_toc_page

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    pools = json.loads(POOLS.read_text(encoding="utf-8"))

    # Selection phase: deliberately no cohort/gold-support file in memory.
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
        frozen_prefix = deepcopy(reranked)
        output, trace = apply_post_rerank_coverage_with_trace(
            question["question"],
            reranked,
            retrieval_pool=pool,
            enabled=True,
            structural_enabled=False,
            hyq_enabled=False,
            pool_enabled=True,
        )
        appended = output[len(reranked):]
        receipts.append(
            {
                "qid": qid,
                "question_sha256": hashlib.sha256(
                    question["question"].encode("utf-8")
                ).hexdigest(),
                "protected_prefix_equal": output[: len(reranked)] == frozen_prefix,
                "selected": [
                    {
                        "id": str(row["id"]),
                        "source_file": row.get("source_file"),
                        "product_model": row.get("product_model"),
                        "page_number": row.get("page_number"),
                        "section_title": row.get("section_title"),
                        "alignment_terms": row.get("rerank_pool_alignment_hits") or [],
                        "need_scores": row.get("rerank_pool_need_scores") or [],
                        "facets": row.get("rerank_pool_facets") or [],
                        "exact_receipt": has_exact_coverage_receipt(row),
                        "generator_admitted": is_validated_coverage_chunk(row),
                        "toc_like": is_toc_page(
                            f"{row.get('section_title') or ''}\n\n{row.get('content') or ''}"
                        ),
                        "source_content_chars": len(row.get("content") or ""),
                        "served_excerpt_chars": len(coverage_context_content(row)),
                    }
                    for row in appended
                ],
                "trace": trace,
            }
        )

    # Evaluation phase: atomic targets enter only after every selection is frozen.
    cohort = yaml.safe_load(COHORT.read_text(encoding="utf-8"))
    selected_by_qid = {
        row["qid"]: {item["id"] for item in row["selected"]}
        for row in receipts
    }

    def evaluate_claims(key: str) -> list[dict]:
        results = []
        for claim in cohort.get(key) or []:
            selected = selected_by_qid.get(claim["qid"], set())
            reached = _bundle_reaches(selected, claim["support_any"])
            results.append(
                {
                    "claim_id": claim["claim_id"],
                    "qid": claim["qid"],
                    "stage_before": "rerank",
                    "stage_after": "generator" if reached else "rerank",
                    "reaches_generator": reached,
                    "selected_ids": sorted(selected),
                }
            )
        return results

    residual = evaluate_claims("residual_rerank_claims")
    provenance = evaluate_claims("separate_provenance_probe")
    target_qids = {row["qid"] for row in residual}
    selected_rows = [item for row in receipts for item in row["selected"]]
    target_selected = [
        item for row in receipts if row["qid"] in target_qids for item in row["selected"]
    ]
    non_target_selected = [
        item for row in receipts if row["qid"] not in target_qids for item in row["selected"]
    ]
    recovered = sum(row["reaches_generator"] for row in residual)
    gate = {
        "residual_rerank_claims": len(residual),
        "residual_reaches_generator": recovered,
        "residual_stage_recovery_rate": round(recovered / len(residual), 4),
        "separate_provenance_recovered": sum(
            row["reaches_generator"] for row in provenance
        ),
        "all_protected_prefixes_equal": all(
            row["protected_prefix_equal"] for row in receipts
        ),
        "all_selected_have_exact_receipts": all(
            row["exact_receipt"] for row in selected_rows
        ),
        "all_selected_admitted_by_generator_boundary": all(
            row["generator_admitted"] for row in selected_rows
        ),
        "toc_like_selected_rows": sum(row["toc_like"] for row in selected_rows),
        "max_appended_per_question": max(
            (len(row["selected"]) for row in receipts), default=0
        ),
        "questions_replayed": len(receipts),
        "questions_with_append": sum(bool(row["selected"]) for row in receipts),
        "target_selected_rows": len(target_selected),
        "non_target_selected_rows": len(non_target_selected),
        "selected_source_content_chars": sum(
            row["source_content_chars"] for row in selected_rows
        ),
        "selected_served_excerpt_chars": sum(
            row["served_excerpt_chars"] for row in selected_rows
        ),
        "model_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "official_ok_delta": 0,
    }
    source_chars = gate["selected_source_content_chars"]
    gate["served_context_fraction"] = round(
        gate["selected_served_excerpt_chars"] / source_chars, 4
    ) if source_chars else 0.0
    causal_go = (
        recovered == len(residual)
        and gate["all_protected_prefixes_equal"]
        and gate["all_selected_have_exact_receipts"]
        and gate["all_selected_admitted_by_generator_boundary"]
        and gate["toc_like_selected_rows"] == 0
        and gate["max_appended_per_question"] <= 2
    )
    gate["interpretation"] = (
        "GO_RERANK_STAGE_8_OF_8_RETROSPECTIVE_HOLD_RELEASE"
        if causal_go
        else "REVISE_RERANK_STAGE"
    )

    payload = {
        "instrument": "s110_rerank_pool_replay_v1",
        "read_only": True,
        "selection_completed_before_claim_packet_load": True,
        "frozen_inputs": {
            "baseline_path": str(BASELINE.relative_to(ROOT)),
            "baseline_sha256": _sha(BASELINE),
            "pool_path": str(POOLS.relative_to(ROOT)),
            "pool_sha256": _sha(POOLS),
            "cohort_path": str(COHORT.relative_to(ROOT)),
            "cohort_sha256": _sha(COHORT),
            "implementation_inputs": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": _sha(path),
                }
                for path in IMPLEMENTATION_INPUTS
            ],
            "git_head": os.popen("git rev-parse HEAD").read().strip(),
        },
        "gate": gate,
        "residual_claim_results": residual,
        "separate_provenance_results": provenance,
        "funnel_reconciliation": cohort["post_s109_funnel_reconciliation"],
        "receipts": receipts,
        "limitations": [
            cohort["known_data_warning"],
            "S102 pool membership is tracked and reproducible but is not byte-identical to every historical S100 paid reranker pool.",
            "Stage recovery proves evidence reaches synthesis; it does not claim the generated answer conveys the claim.",
            "Non-target appends require protected answer regression before this default-off lane can be released.",
            "The official 93/127 baseline remains unchanged.",
        ],
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if causal_go else 1


if __name__ == "__main__":
    raise SystemExit(main())
