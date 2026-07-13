#!/usr/bin/env python3
"""Reconcile the frozen 36 non-OK rows with reproducible S108 evidence.

This is deliberately conservative: it records candidate preconditions and
cached outcomes without changing the official 93/127 baseline or silently
promoting a fact that has not passed its downstream gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
CAT007 = ROOT / "evals/s108_cat007_measurement_probe_v1.json"
STRUCTURAL = ROOT / "evals/s108_structural_retrieval_replay_v1.json"
DOC_SCOPED_HYQ = ROOT / "evals/s108_doc_scoped_hyq_replay_v1.json"
SYNTHESIS = ROOT / "evals/s107_bounded_synthesis_pilot_v1.json"
OUT = ROOT / "evals/s108_failure_stage_reconciliation_v1.json"
MD_OUT = ROOT / "evals/s108_failure_stage_reconciliation_v1.md"

TERMINAL_CLASSES = {
    "corpus-gap",
    "retrieval-miss",
    "rerank-miss",
    "synthesis-miss",
    "meta-ref",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconcile() -> dict[str, Any]:
    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    cat007 = json.loads(CAT007.read_text(encoding="utf-8"))
    structural = json.loads(STRUCTURAL.read_text(encoding="utf-8"))
    doc_scoped_hyq = json.loads(DOC_SCOPED_HYQ.read_text(encoding="utf-8"))
    synthesis = json.loads(SYNTHESIS.read_text(encoding="utf-8"))

    cat007_by_key = {row["key"]: row for row in cat007["facts"]}
    structural_by_key = {
        row["key"]: row
        for row in structural["retrieval_facts_after_selection"]
    }
    confirmatory_structural_keys = set(
        structural["gate"]["confirmatory_supported_keys"]
    )
    hyq_by_key = {
        row["key"]: row
        for row in doc_scoped_hyq["retrieval_facts_after_selection"]
    }
    synthesis_by_qid = {row["qid"]: row for row in synthesis["rows"]}
    rows = []
    for question in baseline["per_gold"]:
        for fact in question["facts"]:
            baseline_class = fact["clase"]
            if baseline_class not in TERMINAL_CLASSES:
                continue
            evidence = []
            status = "unchanged"
            next_lane = {
                "corpus-gap": "document_extraction",
                "retrieval-miss": "retrieval_root_cause",
                "rerank-miss": "evidence_selection",
                "synthesis-miss": "answer_coverage",
                "meta-ref": "excluded",
            }[baseline_class]

            measurement = cat007_by_key.get(fact["key"])
            if measurement:
                evidence.append(
                    {
                        "kind": "measurement_representation_bridge",
                        "same_family_recovered_ids": measurement[
                            "recovered_same_family_ids"
                        ],
                        "recovered_served_ids": measurement["recovered_served_ids"],
                        "answer_value_present": measurement["answer_value_present"],
                        "cross_family_admitted_ids": measurement[
                            "cross_family_admitted_ids"
                        ],
                    }
                )
                status = "measurement_replay_ready"
                next_lane = "bounded_frozen_judge_replay"

            target = structural_by_key.get(fact["key"])
            if target and target["structural_retrieval_precondition"]:
                confirmatory = fact["key"] in confirmatory_structural_keys
                evidence.append(
                    {
                        "kind": "reproducible_same_blob_structural_neighbor",
                        "confirmatory": confirmatory,
                        "same_family_supporting_ids": target[
                            "same_family_supporting_ids"
                        ],
                        "selected_before_fact_evaluation": True,
                        "serving_integration": False,
                    }
                )
                status = (
                    "structural_retrieval_precondition_ready"
                    if confirmatory
                    else "exploratory_structural_retrieval_precondition"
                )
                next_lane = (
                    "bounded_synthesis_repair"
                    if confirmatory
                    else "freeze_discovery_then_bounded_synthesis"
                )
                cached = synthesis_by_qid.get(question["qid"])
                if cached:
                    evidence.append(
                        {
                            "kind": "cached_paid_synthesis",
                            "model": cached["model"],
                            "stop_reason": cached["stop_reason"],
                            "fact_present": cached["fact_present"],
                            "fact_cited_by_target_fragment": cached[
                                "fact_cited_by_target_fragment"
                            ],
                            "synthesis_success": cached["synthesis_success"],
                        }
                    )
                    if cached["synthesis_success"]:
                        status = "cached_synthesis_success_pending_protected_regression"
                        next_lane = "protected_regression_and_atomic_judge"
                    else:
                        status = "r2_precondition_ready_cached_synthesis_miss"
                        next_lane = "synthesis_repair_with_cached_context"

            hyq_target = hyq_by_key.get(fact["key"])
            if hyq_target and hyq_target["structural_retrieval_precondition"]:
                evidence.append(
                    {
                        "kind": "document_scoped_hyq_source_retrieval",
                        "same_family_supporting_ids": hyq_target[
                            "same_family_supporting_ids"
                        ],
                        "generated_hyq_prose_served": False,
                        "selected_before_fact_evaluation": True,
                        "serving_integration": False,
                    }
                )
                if status == "unchanged":
                    status = "doc_scoped_hyq_retrieval_precondition"
                    next_lane = "rerank_and_provenance_gate"

            rows.append(
                {
                    "key": fact["key"],
                    "qid": question["qid"],
                    "baseline_class": baseline_class,
                    "candidate_status": status,
                    "next_lane": next_lane,
                    "evidence": evidence,
                }
            )

    if len(rows) != 36:
        raise RuntimeError(f"expected 36 frozen non-OK rows, observed {len(rows)}")
    baseline_counts = Counter(row["baseline_class"] for row in rows)
    status_counts = Counter(row["candidate_status"] for row in rows)
    retrieval_rows = [row for row in rows if row["baseline_class"] == "retrieval-miss"]
    retrieval_queue = {
        "measurement_replay_ready": [
            row["key"]
            for row in retrieval_rows
            if row["candidate_status"] == "measurement_replay_ready"
        ],
        "structural_r2_precondition_ready": [
            row["key"]
            for row in retrieval_rows
            if any(
                evidence.get("kind")
                == "reproducible_same_blob_structural_neighbor"
                and evidence.get("confirmatory") is True
                for evidence in row["evidence"]
            )
        ],
        "structural_exploratory_discovery": [
            row["key"]
            for row in retrieval_rows
            if any(
                evidence.get("kind")
                == "reproducible_same_blob_structural_neighbor"
                and evidence.get("confirmatory") is False
                for evidence in row["evidence"]
            )
        ],
        "doc_scoped_hyq_unique_resolution": [
            row["key"]
            for row in retrieval_rows
            if row["candidate_status"]
            == "doc_scoped_hyq_retrieval_precondition"
        ],
        "doc_scoped_hyq_all_support": [
            row["key"]
            for row in retrieval_rows
            if any(
                evidence.get("kind")
                == "document_scoped_hyq_source_retrieval"
                for evidence in row["evidence"]
            )
        ],
        "still_unresolved_in_merged_evidence": [
            row["key"]
            for row in retrieval_rows
            if row["candidate_status"] == "unchanged"
        ],
    }
    gate = {
        "frozen_non_ok_rows": len(rows),
        "baseline_counts": dict(sorted(baseline_counts.items())),
        "candidate_status_counts": dict(sorted(status_counts.items())),
        "retrieval_facts": len(retrieval_rows),
        "retrieval_measurement_replay_ready": len(
            retrieval_queue["measurement_replay_ready"]
        ),
        "retrieval_structural_r2_precondition_ready": len(
            retrieval_queue["structural_r2_precondition_ready"]
        ),
        "retrieval_structural_exploratory_discoveries": len(
            retrieval_queue["structural_exploratory_discovery"]
        ),
        "retrieval_doc_scoped_hyq_unique_resolutions": len(
            retrieval_queue["doc_scoped_hyq_unique_resolution"]
        ),
        "retrieval_doc_scoped_hyq_supported_facts": len(
            retrieval_queue["doc_scoped_hyq_all_support"]
        ),
        "retrieval_still_unresolved": len(
            retrieval_queue["still_unresolved_in_merged_evidence"]
        ),
        "cached_synthesis_successes": sum(
            row["candidate_status"].startswith("cached_synthesis_success")
            for row in rows
        ),
        "model_calls": 0,
        "database_writes": 0,
        "official_ok_baseline": "93/127 unchanged",
        "official_ok_uplift": 0,
    }
    gate["retrieval_stage_accounted_facts"] = (
        gate["retrieval_measurement_replay_ready"]
        + gate["retrieval_structural_r2_precondition_ready"]
        + gate["retrieval_structural_exploratory_discoveries"]
        + gate["retrieval_doc_scoped_hyq_unique_resolutions"]
    )
    gate["interpretation"] = (
        "GO_RETRIEVAL_7_OF_7_PRECONDITIONS_TO_DOWNSTREAM_GATES"
        if gate["retrieval_measurement_replay_ready"] == 2
        and gate["retrieval_structural_r2_precondition_ready"] == 3
        and gate["retrieval_structural_exploratory_discoveries"] == 1
        and gate["retrieval_doc_scoped_hyq_unique_resolutions"] == 1
        and gate["retrieval_still_unresolved"] == 0
        and gate["retrieval_stage_accounted_facts"] == 7
        and gate["cached_synthesis_successes"] == 1
        else "NO_GO_STAGE_RECONCILIATION"
    )
    return {
        "instrument": "s108_failure_stage_reconciliation_v1",
        "read_only": True,
        "frozen_inputs": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in (BASELINE, CAT007, STRUCTURAL, DOC_SCOPED_HYQ, SYNTHESIS)
        },
        "gate": gate,
        "retrieval_queue": retrieval_queue,
        "rows": rows,
        "limitations": [
            "Candidate statuses are stage evidence, not official reclassification.",
            "The structural observer is not a serving integration.",
            "The cached synthesis success has not passed the 93-OK protected regression.",
            "The hp013 structural match is exploratory and must be frozen independently before promotion.",
            "The HYQ lane navigates with precomputed questions but serves only exact source chunks.",
            "Only tracked inputs plus deterministic, read-only S108 probes are used.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    gate = payload["gate"]
    lines = [
        "# S108 failure-stage reconciliation",
        "",
        "Conservative reconciliation of the 36 frozen non-OK rows. Candidate status is not official OK credit.",
        "",
        f"- Official baseline: **{gate['official_ok_baseline']}**",
        f"- Retrieval facts: **{gate['retrieval_facts']}**",
        f"- Measurement replay ready: **{gate['retrieval_measurement_replay_ready']}**",
        f"- Structural R2 precondition ready: **{gate['retrieval_structural_r2_precondition_ready']}**",
        f"- Structural exploratory discoveries: **{gate['retrieval_structural_exploratory_discoveries']}**",
        f"- Doc-scoped HYQ unique resolutions: **{gate['retrieval_doc_scoped_hyq_unique_resolutions']}**",
        f"- Retrieval unresolved in merged evidence: **{gate['retrieval_still_unresolved']}**",
        f"- Retrieval stage accounted: **{gate['retrieval_stage_accounted_facts']}/{gate['retrieval_facts']}**",
        f"- Cached synthesis successes: **{gate['cached_synthesis_successes']}**",
        "",
        "| Key | Baseline | Candidate status | Next lane |",
        "|---|---|---|---|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| `{row['key']}` | `{row['baseline_class']}` | "
            f"`{row['candidate_status']}` | `{row['next_lane']}` |"
        )
    lines.extend(["", f"Gate: **{gate['interpretation']}**", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--md-out", type=Path, default=MD_OUT)
    args = parser.parse_args()
    payload = reconcile()
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.md_out.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload["gate"], ensure_ascii=False, indent=2))
    return 0 if payload["gate"]["interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
