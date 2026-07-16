#!/usr/bin/env python3
"""Project the S133 fact adjudication onto the canonical S126 funnel."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
S126 = ROOT / "evals/s126_upstream_residual_audit_v1.json"
S133 = ROOT / "evals/s133_unmeasured_fact_adjudication_v1.yaml"
OUT = ROOT / "evals/s133_reconciled_funnel_v1.json"

EXPECTED_RECEIPTS = {
    "s126_upstream_residual_audit": (
        S126,
        "43a5776926879f0420287d1ededb9de05e6e512b3a95a17d9ce9be8a8f8a24d4",
    ),
    "s133_unmeasured_fact_adjudication": (
        S133,
        "4f3e72e35bf17276a1ef35ce10b1c181051feeb0500ec05ea4dd12c01ecdcb78",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_funnel(s126: dict, adjudication: dict) -> dict:
    prior = Counter(s126["provisional_reconciled_diagnostic"]["stage_histogram"])
    adjudicated = Counter(row["stage_bucket"] for row in adjudication["rows"])
    if prior != Counter(
        {
            "OK": 111,
            "retrieval-miss": 4,
            "source-contract-hold": 1,
            "synthesis-miss": 14,
            "synthesis-not-measured": 27,
        }
    ):
        raise RuntimeError("canonical S126 funnel drift")
    if adjudicated != Counter({"OK": 23, "synthesis-miss": 4}):
        raise RuntimeError("S133 adjudication histogram drift")
    if len(adjudication["rows"]) != prior["synthesis-not-measured"]:
        raise RuntimeError("S133 does not close the exact unmeasured bucket")

    projected = prior.copy()
    projected["synthesis-not-measured"] -= len(adjudication["rows"])
    projected.update(adjudicated)
    projected = +projected
    denominator = sum(projected.values())
    if denominator != sum(prior.values()):
        raise RuntimeError("funnel denominator changed during measurement reconciliation")
    target = math.ceil(0.95 * denominator)
    return {
        "schema_version": "s133_reconciled_funnel_v1",
        "instrument": "s133_project_reconciled_funnel",
        "status": "PROVISIONAL_HYBRID_FUNNEL_RECONCILED_ALL_FACTS_CLASSIFIED",
        "authority": {
            name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha}
            for name, (path, sha) in EXPECTED_RECEIPTS.items()
        },
        "bridge": {
            "prior_stage_histogram": dict(sorted(prior.items())),
            "removed_stage_histogram": {"synthesis-not-measured": 27},
            "added_stage_histogram": dict(sorted(adjudicated.items())),
            "facts_reclassified": 27,
            "confirmed_ok_exposed_by_measurement": 23,
            "facts_moved_to_ok_due_to_bot_change": 0,
        },
        "reconciled_diagnostic": {
            "content_denominator": denominator,
            "stage_histogram": dict(sorted(projected.items())),
            "ok_count": projected["OK"],
            "ok_rate": projected["OK"] / denominator,
            "ok_rate_percent": round(100 * projected["OK"] / denominator, 2),
            "target_ok_for_95_percent": target,
            "gap_to_95_percent": target - projected["OK"],
            "largest_non_ok_bucket": "synthesis-miss",
            "all_facts_stage_classified": True,
            "official_atomic_kpi": None,
        },
        "credit_and_limitations": {
            "bot_improvement_credit": 0,
            "measurement_reconciliation_credit": 23,
            "reason_official_kpi_is_null": (
                "The S125 bridge remains a provisional hybrid denominator because 77 "
                "legacy carries have not completed atomic requiredness adjudication."
            ),
            "chunks_version": "chunks_v2_exact_S113_context",
            "chunks_v3_effect_measured": False,
        },
        "cost": {
            "projection_model_calls": 0,
            "projection_network_calls": 0,
            "projection_database_reads": 0,
            "projection_database_writes": 0,
        },
    }


def main() -> int:
    for name, (path, expected) in EXPECTED_RECEIPTS.items():
        actual = _sha256(path)
        if actual != expected:
            raise RuntimeError(f"{name} receipt drift: {expected} != {actual}")
    s126 = json.loads(S126.read_text(encoding="utf-8"))
    adjudication = yaml.safe_load(S133.read_text(encoding="utf-8"))
    payload = project_funnel(s126, adjudication)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["reconciled_diagnostic"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
