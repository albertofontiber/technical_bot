#!/usr/bin/env python3
"""Map immutable S147 exact-quote gold to deterministic evidence-unit IDs."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s165_answer_archetype_ledger import stable_sha
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s147_fresh_source_packet_v1.json"
COHORT = ROOT / "evals/s147_fresh_obligation_cohort_v1.json"
DEFAULT_OUT = ROOT / "evals/s171_s147_source_unit_gold_v1.json"


def build(source: dict[str, Any], cohort: dict[str, Any]) -> dict[str, Any]:
    source_by = {row["item_id"]: row for row in source["items"]}
    mapped_items = []
    original_points = mapped_points = 0
    drops = []
    for item in cohort["items"]:
        if not item["eligible"]:
            continue
        row = source_by[item["item_id"]]
        units = build_header_aware_evidence_units(
            row["excerpt"], fragment_number=1, candidate_id=item["item_id"]
        )
        points = []
        for point_index, point in enumerate(item["answer_points"], start=1):
            original_points += 1
            candidates = [unit for unit in units if point["exact_quote"] in unit.content]
            if not candidates:
                drops.append({
                    "item_id": item["item_id"], "point_index": point_index,
                    "claim_sha256": stable_sha(point["claim"]), "reason": "quote_not_contained_in_any_v2_unit",
                })
                continue
            candidates.sort(
                key=lambda unit: (
                    0 if item["stratum"] == "table" and unit.unit_kind == "table_row_with_header" else 1,
                    len(unit.content), unit.unit_id,
                )
            )
            unit = candidates[0]
            mapped_points += 1
            points.append({
                "claim": point["claim"], "exact_quote": point["exact_quote"],
                "facet": "unassigned_exact_quote_gold",
                "support_unit_ids": [unit.unit_id],
                "support_unit_receipts": [{
                    "unit_id": unit.unit_id, "unit_kind": unit.unit_kind,
                    "source_spans": [list(span) for span in unit.source_spans],
                    "content_sha256": unit.content_sha256,
                }],
            })
        mapped_items.append({
            "item_id": item["item_id"], "eligible": bool(points), "question": item["question"],
            "answer_points": points,
            **{key: row[key] for key in ("stratum", "manufacturer", "product_model", "document_id", "chunk_id", "excerpt_sha256")},
        })
    body: dict[str, Any] = {
        "instrument": "s171_s147_source_unit_gold_v1",
        "status": "SEALED_DETERMINISTIC_DEVELOPMENT_REUSE",
        "population": {
            "items": len(mapped_items),
            "eligible_items": sum(item["eligible"] for item in mapped_items),
            "manufacturers": len({item["manufacturer"] for item in mapped_items if item["eligible"]}),
            "original_answer_points": original_points,
            "mapped_answer_points": mapped_points,
            "unmapped_answer_points": len(drops),
            "model_calls": 0,
        },
        "drops": drops,
        "items": mapped_items,
    }
    return {**body, "cohort_sha256": stable_sha(body)}


def main() -> int:
    result = build(
        json.loads(SOURCE.read_text(encoding="utf-8")),
        json.loads(COHORT.read_text(encoding="utf-8")),
    )
    DEFAULT_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], **result["population"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
