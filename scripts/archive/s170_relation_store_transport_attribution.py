#!/usr/bin/env python3
"""Attribute S170 extraction construction failures without retrying them."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s165_answer_archetype_ledger import stable_sha


ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "evals/s170_per_chunk_relation_extraction_receipts_v1.json"
STORE = ROOT / "evals/s170_per_chunk_relation_store_v1.json"
RESULT = ROOT / "evals/s170_per_chunk_relation_store_gate_v1.json"
DEFAULT_OUT = ROOT / "evals/s170_relation_store_transport_attribution_v1.json"


def build(receipts: dict[str, Any], store: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    categories = {"valid": 0, "over_population": 0, "truncated_or_invalid_json": 0, "other": 0}
    over_counts = []
    rows = []
    for receipt in receipts["receipts"]:
        error = receipt["validation_error"]
        raw_count = None
        if error is None:
            category = "valid"
        elif error == "relation population out of bounds":
            category = "over_population"
            raw_count = len(json.loads(receipt["raw_text"])["relations"])
            over_counts.append(raw_count)
        elif "Unterminated string" in error or "Expecting property name" in error:
            category = "truncated_or_invalid_json"
        else:
            category = "other"
        categories[category] += 1
        rows.append({
            "item_id": receipt["item_id"], "category": category,
            "validation_error": error, "raw_relation_count": raw_count,
            "output_tokens": receipt["usage"].get("output_tokens", 0),
            "raw_characters": len(receipt["raw_text"]),
        })
    body: dict[str, Any] = {
        "instrument": "s170_relation_store_transport_attribution_v1",
        "status": "TRANSPORT_SUCCESSOR_ALLOWED_ON_DIFFERENT_DEVELOPMENT_COHORT",
        "population": {
            "chunks": len(rows), "categories": categories,
            "valid_relations": sum(len(row["relations"]) for row in store["items"] if row["valid"]),
            "over_population_relation_counts": over_counts,
            "selector_calls": 0,
        },
        "rows": rows,
        "decision": {
            "s170_credit": False, "same_cohort_retry": False,
            "different_existing_development_cohort": "S147",
            "allowed_transport_changes": [
                "declare and schema-bind relation maximum",
                "increase output budget to fit the declared bounded schema",
                "constrain relation field verbosity",
            ],
            "semantic_prompt_scope_change": False,
            "third_transport_iteration_if_successor_fails": False,
            "target_probe": False, "production": False, "facts_moved_to_ok": 0,
        },
        "cost": {"additional_model_calls": 0, "additional_usd": 0, "s170_paid_usd": result["cost"]["total_usd"]},
    }
    return {**body, "result_sha256": stable_sha(body)}


def main() -> int:
    result = build(
        json.loads(RECEIPTS.read_text(encoding="utf-8")),
        json.loads(STORE.read_text(encoding="utf-8")),
        json.loads(RESULT.read_text(encoding="utf-8")),
    )
    DEFAULT_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], **result["population"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
