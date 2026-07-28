#!/usr/bin/env python3
"""Join the frozen independent scan to its complete human-readable adjudication."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ADJUDICATION = ROOT / "evals" / "s126_prerequisite_independent_adjudication_v1.yaml"
OUTPUT = ROOT / "evals" / "s126_prerequisite_independent_gate_v1.yaml"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_payload() -> dict:
    adjudication = yaml.safe_load(ADJUDICATION.read_text(encoding="utf-8"))
    scan_path = ROOT / adjudication["scan"]["path"]
    if _sha(scan_path) != adjudication["scan"]["sha256"]:
        raise ValueError("independent scan drift")
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    decisions = {
        row["quote_sha256"]: row for row in adjudication["decisions"]
    }
    scanned = {row["quote_sha256"] for row in scan["opportunities"]}
    if set(decisions) != scanned or len(decisions) != len(scan["opportunities"]):
        raise ValueError("adjudication coverage is not exact")
    positives = [
        row for row in scan["opportunities"]
        if decisions[row["quote_sha256"]]["semantic_opportunity"]
    ]
    false_positives = [
        row for row in scan["opportunities"]
        if not decisions[row["quote_sha256"]]["semantic_opportunity"]
    ]
    access_positives = [row for row in positives if row["facet"] == "access_prerequisite"]
    entitlement_positives = [row for row in positives if row["facet"] == "quantified_entitlement"]
    positive_manufacturers = sorted({row["manufacturer"] for row in positives})
    applicability = {
        "positive_opportunities": len(positives),
        "positive_manufacturers": positive_manufacturers,
        "access_positive_opportunities": len(access_positives),
        "quantified_entitlement_positive_opportunities": len(entitlement_positives),
        "scanner_false_positives": len(false_positives),
    }
    checks = {
        "positive_opportunities_at_least_two": len(positives) >= 2,
        "positive_manufacturers_at_least_two": len(positive_manufacturers) >= 2,
        "both_facets_exercised": bool(access_positives) and bool(entitlement_positives),
        "zero_scanner_false_positives": not false_positives,
    }
    gate = "GO_INDEPENDENT_PREREQUISITES" if all(checks.values()) else "INCONCLUSIVE_NOT_GO"
    return {
        "schema_version": "s126_prerequisite_independent_gate_v1",
        "gate": gate,
        "checks": checks,
        "applicability": applicability,
        "authorization": {
            "procedure_prerequisite_serving_integration": False,
            "known_cohort_retrieval_credit": 2,
            "facts_moved_to_ok": 0,
        },
        "required_next_evidence": [
            "independent access-prerequisite opportunity from another manufacturer",
            "independent quantified-entitlement opportunity",
            "operational-access guard rejecting administrative RMA authorization",
        ],
        "cost": {"model_calls": 0, "network_calls": 0, "database_writes": 0},
    }


def main() -> int:
    payload = build_payload()
    OUTPUT.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(json.dumps({"gate": payload["gate"], **payload["applicability"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
