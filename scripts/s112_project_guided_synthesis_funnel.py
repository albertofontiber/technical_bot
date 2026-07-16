#!/usr/bin/env python3
"""Layer adversarially reviewed synthesis transitions onto the S112 funnel."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
UPSTREAM_CONTRACT = ROOT / "evals/s112_postchange_transition_contract_v1.yaml"
MANUAL_REVIEW = ROOT / "evals/s112_guided_synthesis_manual_review_v1.yaml"
ROOT_CAUSE_AUDIT = ROOT / "evals/s112_synthesis_root_cause_audit_v1.yaml"
OUT = ROOT / "evals/s112_guided_synthesis_funnel_projection_v1.json"


def _headline(classes: dict[str, str], *, diagnostic: bool) -> dict[str, int]:
    counts = Counter(classes.values())
    rest = {"corpus-gap", "meta-ref", "noncore-adjudicated", "invalid-relation-adjudicated"}
    if diagnostic:
        rest |= {
            "document-conflict-hold",
            "product-or-parameter-identity-hold",
            "evidence-partial-hold",
        }
    result = {
        "OK": counts["OK"],
        "synthesis-miss": counts["synthesis-miss"],
        "rerank-miss": counts["rerank-miss"],
        "retrieval-miss": counts["retrieval-miss"],
        "rest": sum(counts[name] for name in rest),
    }
    if sum(result.values()) != len(classes):
        raise RuntimeError(f"incomplete headline partition: {result}")
    return result


def project_guided_synthesis_funnel(
    baseline: dict, upstream_contract: dict, manual_review: dict, root_cause_audit: dict
) -> dict:
    facts = {
        fact["key"]: fact
        for gold in baseline["per_gold"]
        for fact in gold["facts"]
    }
    stage_classes = {key: fact["clase"] for key, fact in facts.items()}
    for key, transition in upstream_contract["transitions"].items():
        stage_classes[key] = transition["candidate"]

    pass_keys = {
        row["fact_key"] for row in manual_review["rows"] if row["verdict"] == "pass"
    }
    if len(pass_keys) != manual_review["summary"]["pass"]:
        raise RuntimeError("manual-review pass count does not match unique pass facts")
    invalid_passes = sorted(key for key in pass_keys if stage_classes.get(key) != "synthesis-miss")
    if invalid_passes:
        raise RuntimeError(f"reviewed passes are not synthesis misses: {invalid_passes}")
    for key in pass_keys:
        stage_classes[key] = "OK"

    diagnostic_classes = dict(stage_classes)
    hold_projection = {
        "hold_document_conflict": "document-conflict-hold",
        "hold_product_and_parameter_identity": "product-or-parameter-identity-hold",
        "hold_product_identity": "product-or-parameter-identity-hold",
        "hold_evidence_partial": "evidence-partial-hold",
    }
    audited_keys = set()
    for row in root_cause_audit["rows"]:
        key = row["fact_key"]
        audited_keys.add(key)
        if key in pass_keys:
            continue
        classification = row["classification"]
        if classification == "synthesis_candidate":
            diagnostic_classes[key] = "synthesis-miss"
        else:
            diagnostic_classes[key] = hold_projection[classification]

    synthesis_before_review = {
        key
        for key, value in {
            **{key: fact["clase"] for key, fact in facts.items()},
            **{
                key: transition["candidate"]
                for key, transition in upstream_contract["transitions"].items()
            },
        }.items()
        if value == "synthesis-miss"
    }
    if audited_keys != synthesis_before_review:
        raise RuntimeError("root-cause audit must partition every pre-review synthesis fact")

    stage_headline = _headline(stage_classes, diagnostic=False)
    diagnostic_headline = _headline(diagnostic_classes, diagnostic=True)
    denominator = len(facts) - baseline["aggregate_hist"]["meta-ref"]
    target_ok = math.ceil(0.95 * denominator)
    return {
        "instrument": "s112_guided_synthesis_funnel_projection_v1",
        "status": "candidate_projection_not_official_full_regression",
        "baseline_headline_histogram": {
            "OK": baseline["aggregate_hist"]["OK"],
            "synthesis-miss": baseline["aggregate_hist"]["synthesis-miss"],
            "rerank-miss": baseline["aggregate_hist"]["rerank-miss"],
            "retrieval-miss": baseline["aggregate_hist"]["retrieval-miss"],
            "rest": baseline["aggregate_hist"]["corpus-gap"] + baseline["aggregate_hist"]["meta-ref"],
        },
        "stage_compatible_headline_histogram": stage_headline,
        "root_cause_corrected_work_queue": diagnostic_headline,
        "validated_synthesis_delta_ok": len(pass_keys),
        "validated_synthesis_pass_facts": sorted(pass_keys),
        "total_fact_rows": len(facts),
        "scored_denominator_excluding_meta_ref": denominator,
        "candidate_ok_rate_percent": round(100 * stage_headline["OK"] / denominator, 2),
        "target_95_percent_ok_count": target_ok,
        "additional_ok_needed_for_95_percent": target_ok - stage_headline["OK"],
        "bounded_experiment_cost": {
            "paid_generator_or_editor_calls": 6,
            "input_tokens": 72754,
            "output_tokens": 6473,
            "paid_reranker_calls": 0,
            "llm_judge_calls": 0,
        },
        "diagnostic_note":
            "The corrected work queue reclassifies nine residual synthesis rows as "
            "upstream evidence, identity, or document-conflict holds. Reclassification "
            "is diagnostic and is not counted as an OK improvement.",
        "release_gate": {
            "local_deterministic_regression": "GO_23_OF_23_PROTECTED_FACTS",
            "exact_hash_adversarial_review": "COMPLETE_4_PASS_1_FAIL_1_HOLD",
            "cheap_draft_obligation_repair": "NO_GO_ZERO_SEMANTIC_FACT_GAIN",
            "full_frozen_model_regression": "pending",
            "held_out_precision_regression": "pending",
            "official_histogram": False,
        },
    }


def main() -> int:
    payload = project_guided_synthesis_funnel(
        yaml.safe_load(BASELINE.read_text(encoding="utf-8")),
        yaml.safe_load(UPSTREAM_CONTRACT.read_text(encoding="utf-8")),
        yaml.safe_load(MANUAL_REVIEW.read_text(encoding="utf-8")),
        yaml.safe_load(ROOT_CAUSE_AUDIT.read_text(encoding="utf-8")),
    )
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["stage_compatible_headline_histogram"], indent=2))
    print(f"OK rate: {payload['candidate_ok_rate_percent']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
