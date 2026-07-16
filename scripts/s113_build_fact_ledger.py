#!/usr/bin/env python3
"""Build the 129-row partial S113 ledger and an explicit rest decomposition."""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
S112_TRANSITIONS = ROOT / "evals/s112_postchange_transition_contract_v1.yaml"
S112_MANUAL = ROOT / "evals/s112_guided_synthesis_manual_review_v1.yaml"
ROOT_CAUSE = ROOT / "evals/s112_synthesis_root_cause_audit_v1.yaml"
S113_OVERRIDES = ROOT / "evals/s113_reconciliation_overrides_v1.yaml"
S113_CANARY = ROOT / "evals/s113_canary_adversarial_review_v1.yaml"
ANSWERS = ROOT / "evals/s113_full_answer_regression_v1.json"
OUT = ROOT / "evals/s113_fact_ledger_v1.json"
REST_OUT = ROOT / "evals/s113_rest_decomposition_v1.yaml"

REST_CLASSES = {
    "corpus-gap",
    "meta-ref",
    "noncore-adjudicated",
    "invalid-relation-adjudicated",
    "document-conflict-hold",
    "document-extraction-hold",
    "product-or-parameter-identity-hold",
    "evidence-partial-hold",
}


def headline(classes: dict[str, str]) -> dict[str, int]:
    counts = Counter(classes.values())
    result = {
        "OK": counts["OK"],
        "synthesis-miss": counts["synthesis-miss"],
        "rerank-miss": counts["rerank-miss"],
        "retrieval-miss": counts["retrieval-miss"],
        "rest": sum(counts[name] for name in REST_CLASSES),
    }
    if sum(result.values()) != len(classes):
        unknown = sorted(set(classes.values()) - REST_CLASSES - {
            "OK", "synthesis-miss", "rerank-miss", "retrieval-miss"
        })
        raise RuntimeError(f"incomplete partition; unknown={unknown}, result={result}")
    return result


def main() -> int:
    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    transition = yaml.safe_load(S112_TRANSITIONS.read_text(encoding="utf-8"))
    manual = yaml.safe_load(S112_MANUAL.read_text(encoding="utf-8"))
    root_cause = yaml.safe_load(ROOT_CAUSE.read_text(encoding="utf-8"))
    overrides = yaml.safe_load(S113_OVERRIDES.read_text(encoding="utf-8"))["overrides"]
    canary = yaml.safe_load(S113_CANARY.read_text(encoding="utf-8"))
    answers = json.loads(ANSWERS.read_text(encoding="utf-8"))
    answer_by_qid = {row["qid"]: row for row in answers["rows"]}

    facts = {
        fact["key"]: {**fact, "qid": gold["qid"]}
        for gold in baseline["per_gold"]
        for fact in gold["facts"]
    }
    classes = {key: fact["clase"] for key, fact in facts.items()}
    evidence = {key: "s100_factlevel_full" for key in facts}
    attribution = {key: "baseline_unchanged" for key in facts}
    for key, row in transition["transitions"].items():
        classes[key] = row["candidate"]
        evidence[key] = row["evidence"]
        attribution[key] = "s112_candidate_transition"
    for row in manual["rows"]:
        if row["verdict"] == "pass":
            classes[row["fact_key"]] = "OK"
            evidence[row["fact_key"]] = "s112_guided_synthesis_manual_review_v1"
            attribution[row["fact_key"]] = "verified_synthesis_gain"
    for key, row in overrides.items():
        classes[key] = row["candidate"]
        evidence[key] = row["evidence"]
        attribution[key] = row["attribution"]

    diagnostic = dict(classes)
    diagnostic_evidence = dict(evidence)
    diagnostic_reason: dict[str, str] = {}
    root_projection = {
        "hold_document_conflict": "document-conflict-hold",
        "hold_product_and_parameter_identity": "product-or-parameter-identity-hold",
        "hold_product_identity": "product-or-parameter-identity-hold",
        "hold_evidence_partial": "evidence-partial-hold",
    }
    for row in root_cause["rows"]:
        key = row["fact_key"]
        if diagnostic[key] == "OK":
            continue
        if row["classification"] in root_projection:
            diagnostic[key] = root_projection[row["classification"]]
            diagnostic_evidence[key] = "s112_synthesis_root_cause_audit_v1"
            diagnostic_reason[key] = row["reason"]

    for qid_row in canary["rows"]:
        for row in qid_row["facts"]:
            if row.get("reason"):
                diagnostic_reason[row["fact_key"]] = row["reason"]
    static_reasons = {
        "corpus-gap": "No servable same-product evidence was found in the frozen corpus.",
        "meta-ref": "Evaluation pointer or document reference, not an atomic technical fact.",
        "noncore-adjudicated": "Removed from the scored core by the atomicity adjudication.",
        "invalid-relation-adjudicated": "The evaluated relation was rejected by the atomicity adjudication.",
    }

    ledger = []
    for key, fact in facts.items():
        answer = answer_by_qid[fact["qid"]]
        ledger.append(
            {
                "fact_key": key,
                "qid": fact["qid"],
                "baseline_class": fact["clase"],
                "stage_compatible_class": classes[key],
                "diagnostic_class": diagnostic[key],
                "stage_evidence": evidence[key],
                "diagnostic_evidence": diagnostic_evidence[key],
                "diagnostic_reason": diagnostic_reason.get(
                    key, static_reasons.get(diagnostic[key])
                ),
                "attribution": attribution[key],
                "answer_status": answer["answer_source"] or "pending_generation",
                "answer_sha256": answer["answer_sha256"],
            }
        )

    stage_headline = headline(classes)
    diagnostic_headline = headline(diagnostic)
    denominator = len(facts) - sum(value == "meta-ref" for value in classes.values())
    target = math.ceil(0.95 * denominator)
    payload = {
        "instrument": "s113_fact_ledger_v1",
        "status": "NO_GO_PARTIAL_REGRESSION_NOT_OFFICIAL",
        "rows": ledger,
        "summary": {
            "fact_rows": len(ledger),
            "answers_available": answers["gate"]["answers_available"],
            "answers_pending": answers["gate"]["remaining_generator_calls"],
            "stage_compatible_partial_headline": stage_headline,
            "root_cause_corrected_partial_work_queue": diagnostic_headline,
            "scored_denominator_excluding_meta_ref": denominator,
            "partial_candidate_ok_rate_percent": round(100 * stage_headline["OK"] / denominator, 2),
            "target_95_ok_count": target,
            "additional_ok_needed_from_partial_snapshot": target - stage_headline["OK"],
        },
        "limitations": [
            "Twelve changed-answer prompts remain intentionally unexecuted after the semantic canary NO-GO.",
            "Candidate transitions not covered by exact S113 canary review remain provisional.",
            "Diagnostic reclassification is not an OK gain.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rest_rows = [row for row in ledger if row["diagnostic_class"] in REST_CLASSES]
    grouped = Counter(row["diagnostic_class"] for row in rest_rows)
    rest_payload = {
        "instrument": "s113_rest_decomposition_v1",
        "status": "audited_partial_work_queue_not_official_histogram",
        "total": len(rest_rows),
        "histogram": dict(sorted(grouped.items())),
        "actionability": {
            "document-extraction-hold": {"stage": "document_extraction", "actionable": True},
            "corpus-gap": {"stage": "corpus_acquisition_or_ingestion", "actionable": True},
            "document-conflict-hold": {"stage": "document_revision_and_source_arbitration", "actionable": True},
            "product-or-parameter-identity-hold": {"stage": "metadata_and_identity", "actionable": True},
            "evidence-partial-hold": {"stage": "extraction_retrieval_or_gold_adjudication", "actionable": True},
            "meta-ref": {"stage": "evaluation_contract", "actionable": False},
            "noncore-adjudicated": {"stage": "evaluation_contract", "actionable": False},
            "invalid-relation-adjudicated": {"stage": "evaluation_contract", "actionable": False},
        },
        "rows": [
            {
                "fact_key": row["fact_key"],
                "qid": row["qid"],
                "category": row["diagnostic_class"],
                "evidence": row["diagnostic_evidence"],
                "reason": row["diagnostic_reason"],
            }
            for row in rest_rows
        ],
    }
    REST_OUT.write_text(yaml.safe_dump(rest_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(yaml.safe_dump(rest_payload["histogram"], allow_unicode=True, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
