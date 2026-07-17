#!/usr/bin/env python3
"""Attribute S186 misses to relation extraction or query-time selection."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
STORE = ROOT / "evals/s186_relation_store_v1.json"
RESULT = ROOT / "evals/s186_provider_compatible_relation_store_gate_v1.json"
OUT = ROOT / "evals/s187_relation_store_failure_attribution_v1.json"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _metrics(rows: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    claims = sum(row["claims"] for row in rows)
    covered = sum(row[f"{prefix}_claims_covered"] for row in rows)
    complete = sum(row[f"{prefix}_complete"] for row in rows)
    return {
        "questions": len(rows),
        "claims": claims,
        "claims_covered": covered,
        "claim_recall": round(covered / claims, 8),
        "questions_complete": complete,
        "question_complete_rate": round(complete / len(rows), 8),
    }


def build() -> dict[str, Any]:
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    store = json.loads(STORE.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    store_by = {row["item_id"]: row for row in store["items"]}
    result_by = {row["item_id"]: row for row in result["rows"]}
    rows: list[dict[str, Any]] = []
    extraction_limited = selector_limited = 0
    available_total = available_useful = 0
    for item in gold["items"]:
        item_id = item["item_id"]
        relations = store_by[item_id]["relations"]
        available = {
            unit_id
            for relation in relations
            for unit_id in relation["source_unit_ids"]
        }
        gold_sets = [set(point["support_unit_ids"]) for point in item["answer_points"]]
        gold_union = set().union(*gold_sets) if gold_sets else set()
        oracle_hits = [support.issubset(available) for support in gold_sets]
        actual_covered = int(result_by[item_id]["claims_covered"])
        oracle_covered = sum(oracle_hits)
        extraction_limited += len(oracle_hits) - oracle_covered
        selector_limited += oracle_covered - actual_covered
        available_total += len(available)
        available_useful += len(available.intersection(gold_union))
        rows.append(
            {
                "item_id": item_id,
                "stratum": item["stratum"],
                "claims": len(gold_sets),
                "relations": len(relations),
                "available_source_units": len(available),
                "gold_source_units_available": len(available.intersection(gold_union)),
                "extraction_oracle_claims_covered": oracle_covered,
                "extraction_oracle_complete": bool(oracle_hits) and all(oracle_hits),
                "selector_claims_covered": actual_covered,
                "selector_complete": bool(result_by[item_id]["complete"]),
                "extraction_limited_claims": len(oracle_hits) - oracle_covered,
                "selector_limited_claims": oracle_covered - actual_covered,
            }
        )

    by_stratum: dict[str, Any] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["stratum"]].append(row)
    for stratum, members in sorted(grouped.items()):
        by_stratum[stratum] = {
            "extraction_oracle": _metrics(members, "extraction_oracle"),
            "selector": _metrics(members, "selector"),
        }

    oracle = _metrics(rows, "extraction_oracle")
    selector = _metrics(rows, "selector")
    body = {
        "instrument": "s187_relation_store_failure_attribution_v1",
        "status": "LOCAL_ATTRIBUTION_COMPLETE_RELATION_STORE_NO_GO",
        "population": {
            "questions": len(rows),
            "manufacturers": len({row["manufacturer"] for row in result["rows"]}),
            "claims": oracle["claims"],
            "relations": result["population"]["relations"],
        },
        "extraction_oracle": {
            **oracle,
            "available_source_units": available_total,
            "gold_source_units_available": available_useful,
            "available_unit_precision_against_question_gold": round(
                available_useful / available_total, 8
            ),
        },
        "frozen_selector": {
            **selector,
            "selected_units": result["metrics"]["selected_units"],
            "useful_units": result["metrics"]["useful_units"],
            "unit_precision": result["metrics"]["unit_precision"],
        },
        "miss_attribution": {
            "extraction_limited_claims": extraction_limited,
            "selector_limited_claims": selector_limited,
            "total_missed_claims": oracle["claims"] - selector["claims_covered"],
        },
        "by_stratum": by_stratum,
        "rows": rows,
        "decision": {
            "s186": "CLOSED_NO_GO",
            "relation_extraction_transport": "VALID_BUT_NOT_SUFFICIENT",
            "haiku_relation_selector": "CLOSED_NO_GO",
            "threshold_change": False,
            "same_cohort_selector_retry": False,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
            "next": "RETURN_TO_FOUR_RETRIEVAL_RESIDUALS; REOPEN_SYNTHESIS_ONLY_WITH_FRESH_EXTERNAL_SELECTION_EVIDENCE",
        },
        "cost": {"additional_model_calls": 0, "additional_usd": 0},
    }
    return {**body, "result_sha256": _sha(_canonical(body))}


def main() -> int:
    result = build()
    OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "extraction_oracle": result["extraction_oracle"],
                "selector": result["frozen_selector"],
                "attribution": result["miss_attribution"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
