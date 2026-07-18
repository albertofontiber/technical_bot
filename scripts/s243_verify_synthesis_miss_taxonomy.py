#!/usr/bin/env python3
"""Verify that S243 classifies every frozen synthesis residual exactly once."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
TAXONOMY = ROOT / "evals/s243_synthesis_miss_causal_taxonomy_v1.yaml"


def main() -> int:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    taxonomy = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    residuals = {
        (str(row["qid"]), str(row["obligation_id"])): row
        for row in audit["rows"]
        if not row["covered"]
    }
    rows = taxonomy["rows"]
    keys = [(str(row["qid"]), str(row["obligation_id"])) for row in rows]
    if len(keys) != len(set(keys)) or set(keys) != set(residuals):
        raise ValueError("S243 taxonomy does not cover each residual exactly once")
    for row in rows:
        source = residuals[(row["qid"], row["obligation_id"])]
        expected = {
            "kind": source["kind"],
            "fragment_number": source["fragment_number"],
            "source_fragment_cited": source["source_fragment_cited"],
            "symptom": source["diagnostic_category"],
        }
        if any(row[field] != value for field, value in expected.items()):
            raise ValueError(f"S243 provenance drift: {row['obligation_id']}")
    measured = {
        "stage_attribution": Counter(row["stage"] for row in rows),
        "symptom_histogram": Counter(row["symptom"] for row in rows),
        "lost_detail_family_histogram": Counter(row["family"] for row in rows),
    }
    for field, counter in measured.items():
        if dict(counter) != taxonomy[field]:
            raise ValueError(f"S243 histogram drift: {field}")
    if taxonomy["population"]["synthesis_misses"] != len(residuals) or len(residuals) != 12:
        raise ValueError("S243 residual population drift")
    cited = sum(row["source_fragment_cited"] for row in rows)
    if cited != taxonomy["population"]["residuals_whose_source_fragment_was_cited"]:
        raise ValueError("S243 cited-fragment count drift")
    print(
        json.dumps(
            {
                "status": "S243_TAXONOMY_VERIFIED",
                "residuals": len(rows),
                "within_cited_fragment": measured["stage_attribution"][
                    "within_cited_fragment_detail_loss"
                ],
                "families": dict(measured["lost_detail_family_histogram"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
