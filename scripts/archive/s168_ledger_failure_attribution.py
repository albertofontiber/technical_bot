#!/usr/bin/env python3
"""Attribute the S168 semantic NO-GO without changing its frozen score."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s168_source_unit_gold_ledger_gate import score_selection
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s168_source_unit_gold_packet_v1.json"
COHORT = ROOT / "evals/s168_source_unit_gold_ledger_cohort_v1.json"
RECEIPTS = ROOT / "evals/s168_source_unit_gold_ledger_selector_receipts_v1.json"
RESULT = ROOT / "evals/s168_source_unit_gold_ledger_v1.json"
DEFAULT_OUT = ROOT / "evals/s168_ledger_failure_attribution_v1.json"


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / max(1, denominator), 8)


def build(
    source: dict[str, Any], cohort: dict[str, Any], receipts: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    source_by = {row["item_id"]: row for row in source["items"]}
    item_by = {row["item_id"]: row for row in cohort["items"] if row["eligible"]}
    receipt_by = {row["item_id"]: row for row in receipts["receipts"]}
    by_stratum: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_support: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_facet: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    selected_gold_total = gold_total = cross_facet_covered = 0
    counterfactual_rows = []
    for item_id, item in item_by.items():
        row = source_by[item_id]
        units = build_header_aware_evidence_units(
            row["excerpt"], fragment_number=1, candidate_id=item_id
        )
        receipt = receipt_by[item_id]
        ledger = receipt["ledger"]
        selected_ids = list(dict.fromkeys(unit_id for ids in ledger.values() for unit_id in ids))
        score = score_selection(item, units, ledger, selected_ids)
        gold_union = {
            unit_id for point in item["answer_points"] for unit_id in point["support_unit_ids"]
        }
        gold_total += len(gold_union)
        selected_gold_total += len(gold_union.intersection(selected_ids))
        stratum = by_stratum[item["stratum"]]
        stratum["questions"] += 1
        stratum["claims"] += score["claims"]
        stratum["claims_covered"] += score["claims_covered"]
        stratum["complete"] += int(score["complete"])
        stratum["selected_units"] += score["selected_units"]
        stratum["useful_units"] += score["useful_units"]
        for point in item["answer_points"]:
            support = set(point["support_unit_ids"])
            union_hit = support.issubset(set(selected_ids))
            facet_hit = support.issubset(set(ledger.get(point["facet"], [])))
            bucket = by_support[len(support)]
            bucket["claims"] += 1
            bucket["covered"] += int(union_hit)
            facet = by_facet[point["facet"]]
            facet["claims"] += 1
            facet["union_covered"] += int(union_hit)
            facet["aligned_covered"] += int(facet_hit)
            cross_facet_covered += int(union_hit and not facet_hit)
        if receipt["validation_error"]:
            raw = json.loads(receipt["raw_text"])
            raw_ledger = {entry["facet"]: entry["unit_ids"] for entry in raw["selections"]}
            raw_ids = list(
                dict.fromkeys(unit_id for ids in raw_ledger.values() for unit_id in ids)
            )
            raw_score = score_selection(item, units, raw_ledger, raw_ids)
            counterfactual_rows.append(
                {
                    "item_id": item_id,
                    "validation_error": receipt["validation_error"],
                    "raw_unique_units": len(raw_ids),
                    "gold_units": len(gold_union),
                    "claims": raw_score["claims"],
                    "claims_covered_if_cap_ignored": raw_score["claims_covered"],
                    "complete_if_cap_ignored": raw_score["complete"],
                    "selected_units_if_cap_ignored": raw_score["selected_units"],
                    "useful_units_if_cap_ignored": raw_score["useful_units"],
                }
            )
    formatted_strata = {
        key: {
            **value,
            "claim_recall": _ratio(value["claims_covered"], value["claims"]),
            "unit_precision": _ratio(value["useful_units"], value["selected_units"]),
            "complete_rate": _ratio(value["complete"], value["questions"]),
        }
        for key, value in sorted(by_stratum.items())
    }
    formatted_support = {
        str(key): {**value, "claim_recall": _ratio(value["covered"], value["claims"])}
        for key, value in sorted(by_support.items())
    }
    formatted_facets = {
        key: {
            **value,
            "union_recall": _ratio(value["union_covered"], value["claims"]),
            "aligned_recall": _ratio(value["aligned_covered"], value["claims"]),
        }
        for key, value in sorted(by_facet.items())
    }
    cf_added = sum(row["claims_covered_if_cap_ignored"] for row in counterfactual_rows)
    cf_claims = sum(row["claims"] for row in counterfactual_rows)
    official_noninvalid_claims = result["population"]["answer_points"] - cf_claims
    official_noninvalid_covered = result["metrics"]["claims_covered"]
    counterfactual_total_covered = official_noninvalid_covered + cf_added
    body: dict[str, Any] = {
        "instrument": "s168_ledger_failure_attribution_v1",
        "status": "SEMANTIC_NO_GO_NOT_EXPLAINED_BY_TRANSPORT",
        "official": {
            "claim_recall": result["metrics"]["claim_recall"],
            "unit_precision": result["metrics"]["unit_precision"],
            "question_complete_rate": result["metrics"]["question_complete_rate"],
        },
        "by_stratum": formatted_strata,
        "by_gold_support_cardinality": formatted_support,
        "by_gold_facet": formatted_facets,
        "evidence_unit_recall": _ratio(selected_gold_total, gold_total),
        "cross_facet_covered_claims": cross_facet_covered,
        "invalid_selector_counterfactual": {
            "rows": counterfactual_rows,
            "claim_recall_if_only_cardinality_cap_ignored": _ratio(
                counterfactual_total_covered, result["population"]["answer_points"]
            ),
            "question_complete_rate_upper_bound_if_only_invalid_row_recovered": _ratio(
                result["metrics"]["questions_complete"]
                + sum(row["complete_if_cap_ignored"] for row in counterfactual_rows),
                result["population"]["eligible_questions"],
            ),
        },
        "decision": {
            "s168_credit": False,
            "threshold_change": False,
            "same_cohort_retry": False,
            "generic_ledger_line_promoted": False,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
        },
        "cost": {"additional_model_calls": 0, "additional_usd": 0},
    }
    return {**body, "result_sha256": stable_sha(body)}


def main() -> int:
    result = build(
        json.loads(SOURCE.read_text(encoding="utf-8")),
        json.loads(COHORT.read_text(encoding="utf-8")),
        json.loads(RECEIPTS.read_text(encoding="utf-8")),
        json.loads(RESULT.read_text(encoding="utf-8")),
    )
    DEFAULT_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "official", "by_stratum", "by_gold_support_cardinality", "invalid_selector_counterfactual")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
