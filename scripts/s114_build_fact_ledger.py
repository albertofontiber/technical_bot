#!/usr/bin/env python3
"""Apply the S114 five-fact audit to the provisional S113 ledger."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evals/s113_fact_ledger_v1.json"
ADJUDICATION = ROOT / "evals/s114_partial_evidence_adjudication_v1.yaml"
OUT = ROOT / "evals/s114_fact_ledger_v1.json"
REST_OUT = ROOT / "evals/s114_rest_decomposition_v1.yaml"

FUNNEL = {"OK", "synthesis-miss", "rerank-miss", "retrieval-miss"}


def headline(rows: list[dict]) -> dict[str, int]:
    counts = Counter(row["diagnostic_class"] for row in rows)
    return {
        "OK": counts["OK"],
        "synthesis-miss": counts["synthesis-miss"],
        "rerank-miss": counts["rerank-miss"],
        "retrieval-miss": counts["retrieval-miss"],
        "rest": sum(count for name, count in counts.items() if name not in FUNNEL),
    }


def main() -> int:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    audit = yaml.safe_load(ADJUDICATION.read_text(encoding="utf-8"))
    audited = {row["fact_key"]: row for row in audit["rows"]}
    rows = []
    for original in base["rows"]:
        row = dict(original)
        decision = audited.get(row["fact_key"])
        if decision:
            row["prior_diagnostic_class"] = row["diagnostic_class"]
            row["diagnostic_class"] = decision["adjudicated_class"]
            row["diagnostic_evidence"] = "s114_partial_evidence_adjudication_v1"
            row["diagnostic_reason"] = decision["reason"] if "reason" in decision else (
                decision.get("unsupported_subclaim") or decision.get("required_action")
            )
        rows.append(row)

    result = headline(rows)
    if result != {
        "OK": 106,
        "synthesis-miss": 4,
        "rerank-miss": 1,
        "retrieval-miss": 4,
        "rest": 14,
    }:
        raise RuntimeError(f"unexpected S114 diagnostic partition: {result}")

    stage = base["summary"]["stage_compatible_partial_headline"]
    payload = {
        "instrument": "s114_fact_ledger_v1",
        "status": "NO_GO_PARTIAL_REGRESSION_NOT_OFFICIAL",
        "source_ledger": "evals/s113_fact_ledger_v1.json",
        "rows": rows,
        "summary": {
            "fact_rows": len(rows),
            "stage_compatible_partial_headline": stage,
            "root_cause_corrected_partial_work_queue": result,
            "retrieval_misses_newly_identified": 3,
            "atomicity_or_absence_holds_newly_identified": 2,
            "historical_scored_denominator": 127,
            "optimization_denominator": None,
            "optimization_denominator_status": "pending_versioned_atomic_split",
        },
        "limitations": [
            "The S113 changed-answer regression remains partial after its semantic canary NO-GO.",
            "S114 changes root-cause assignment, not the stage-compatible partial headline or OK count.",
            "The 95 percent target must be recomputed after hp013 and hp015 atomic migration.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rest = [row for row in rows if row["diagnostic_class"] not in FUNNEL]
    grouped = Counter(row["diagnostic_class"] for row in rest)
    actionability = {
        "document-extraction-hold": {"stage": "document_extraction", "actionable": True},
        "corpus-gap": {"stage": "corpus_acquisition_or_ingestion", "actionable": True},
        "document-conflict-hold": {"stage": "document_revision_and_source_arbitration", "actionable": True},
        "product-or-parameter-identity-hold": {"stage": "metadata_and_identity", "actionable": True},
        "atomicity-and-absence-inference-hold": {"stage": "evaluation_contract", "actionable": False},
        "meta-ref": {"stage": "evaluation_contract", "actionable": False},
        "noncore-adjudicated": {"stage": "evaluation_contract", "actionable": False},
        "invalid-relation-adjudicated": {"stage": "evaluation_contract", "actionable": False},
    }
    missing = set(grouped) - set(actionability)
    if missing:
        raise RuntimeError(f"unclassified rest categories: {sorted(missing)}")
    rest_payload = {
        "instrument": "s114_rest_decomposition_v1",
        "status": "audited_partial_work_queue_not_official_histogram",
        "total": len(rest),
        "histogram": dict(sorted(grouped.items())),
        "actionability": actionability,
        "actionable_rows": sum(grouped[name] for name in grouped if actionability[name]["actionable"]),
        "evaluation_contract_rows": sum(
            grouped[name] for name in grouped if not actionability[name]["actionable"]
        ),
        "rows": [
            {
                "fact_key": row["fact_key"],
                "qid": row["qid"],
                "category": row["diagnostic_class"],
                "evidence": row["diagnostic_evidence"],
                "reason": row["diagnostic_reason"],
            }
            for row in rest
        ],
    }
    REST_OUT.write_text(
        yaml.safe_dump(rest_payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(yaml.safe_dump(rest_payload["histogram"], allow_unicode=True, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
