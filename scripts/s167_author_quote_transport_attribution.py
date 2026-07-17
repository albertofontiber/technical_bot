#!/usr/bin/env python3
"""Attribute S167 cohort failure without changing or rescoring its gate."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s165_answer_archetype_ledger import stable_sha


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s167_independent_ledger_source_packet_v1.json"
RECEIPTS = ROOT / "evals/s167_independent_answer_ledger_author_receipts_v1.json"
RESULT = ROOT / "evals/s167_independent_answer_ledger_v1.json"
DEFAULT_OUT = ROOT / "evals/s167_author_quote_transport_attribution_v1.json"
TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def token_coverage(quote: str, source: str) -> float:
    source_tokens = set(TOKEN_RE.findall(source.casefold()))
    quote_tokens = TOKEN_RE.findall(quote.casefold())
    return sum(token in source_tokens for token in quote_tokens) / max(1, len(quote_tokens))


def classify_failed_quote(quote: str, stratum: str) -> str:
    if "[...]" in quote or "[…]" in quote:
        return "non_contiguous_ellipsis_serialization"
    if stratum == "table":
        return "table_or_markdown_serialization"
    return "prose_layout_serialization"


def build(source: dict[str, Any], receipts: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    source_by = {row["item_id"]: row for row in source["items"]}
    rows = []
    raw_points = exact_points = failed_points = raw_eligible = 0
    for receipt in receipts["receipts"]:
        item_id = receipt["item_id"]
        row = source_by[item_id]
        raw = json.loads(receipt["raw_text"])
        raw_eligible += int(raw["eligible"])
        failures = []
        for point in raw["answer_points"]:
            raw_points += 1
            if point["exact_quote"] in row["excerpt"]:
                exact_points += 1
                continue
            failed_points += 1
            failures.append(
                {
                    "classification": classify_failed_quote(
                        point["exact_quote"], row["stratum"]
                    ),
                    "lexical_token_coverage": round(
                        token_coverage(point["exact_quote"], row["excerpt"]), 8
                    ),
                    "quote_sha256": stable_sha(point["exact_quote"]),
                }
            )
        rows.append(
            {
                "item_id": item_id,
                "stratum": row["stratum"],
                "model_eligible": raw["eligible"],
                "raw_answer_points": len(raw["answer_points"]),
                "failed_exact_quotes": len(failures),
                "validation_error": receipt["validation_error"],
                "failures": failures,
            }
        )
    classifications: dict[str, int] = {}
    coverages = []
    for row in rows:
        for failure in row["failures"]:
            label = failure["classification"]
            classifications[label] = classifications.get(label, 0) + 1
            coverages.append(failure["lexical_token_coverage"])
    body: dict[str, Any] = {
        "instrument": "s167_author_quote_transport_attribution_v1",
        "status": "TRANSPORT_SUCCESSOR_JUSTIFIED_NO_POSTHOC_CREDIT",
        "gate_status": result["status"],
        "population": {
            "source_items": len(source["items"]),
            "model_authored_eligible_items": raw_eligible,
            "model_authored_answer_points": raw_points,
            "exact_quote_points": exact_points,
            "failed_exact_quote_points": failed_points,
            "items_with_failed_quotes": sum(bool(row["failures"]) for row in rows),
        },
        "attribution": {
            "classifications": classifications,
            "minimum_failed_quote_lexical_token_coverage": min(coverages, default=0),
            "selector_calls": 0,
            "additional_model_calls": 0,
        },
        "rows": rows,
        "decision": {
            "s167_credit": False,
            "same_cohort_retry": False,
            "threshold_change": False,
            "new_document_independent_source_packet_required": True,
            "source_unit_id_bound_gold_successor": True,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
        },
        "cost": {"additional_usd": 0, "s167_paid_usd": result["cost"]["total_usd"]},
    }
    return {**body, "result_sha256": stable_sha(body)}


def main() -> int:
    result = build(
        json.loads(SOURCE.read_text(encoding="utf-8")),
        json.loads(RECEIPTS.read_text(encoding="utf-8")),
        json.loads(RESULT.read_text(encoding="utf-8")),
    )
    DEFAULT_OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], **result["population"], **result["attribution"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
