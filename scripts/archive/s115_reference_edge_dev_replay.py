#!/usr/bin/env python3
"""Replay S115 on the labelled S114 development challenge (not release evidence)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.reference_edge_coverage import (
    select_reference_edge_coverage,
    verify_reference_edge_receipt,
)

CHALLENGE = ROOT / "evals/s114_procedure_bundle_section_challenge_v1.json"
FREEZE = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
OUT = ROOT / "evals/s115_reference_edge_dev_replay_v1.json"


def build_payload() -> dict:
    challenge = json.loads(CHALLENGE.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    rows_by_id = {
        str(row["id"]): row
        for rows in freeze["candidate_scopes"].values()
        for row in rows
    }
    scopes = freeze["candidate_scopes"]
    replay = []
    for old in challenge["rows"]:
        source = rows_by_id[old["chunk_id"]]
        candidates = scopes[old["scope_key"]]
        started = time.perf_counter()
        selected, trace = select_reference_edge_coverage(
            old["question"], [source], candidates
        )
        replay.append(
            {
                "challenge_id": old["challenge_id"],
                "manufacturer": old["manufacturer"],
                "product_model": old["product_model"],
                "question": old["question"],
                "served_id": old["chunk_id"],
                "selected_ids": [str(row["id"]) for row in selected],
                "selected_receipts": [
                    {
                        "candidate_id": str(row["id"]),
                        "section_title": row.get("section_title"),
                        "reference_edge": row["reference_edge"],
                        "section_anchor_receipt": row["section_anchor_receipt"],
                        "coverage_cards": row["coverage_cards"],
                        "receipts_verified": verify_reference_edge_receipt(
                            rows_by_id[row["section_anchor_receipt"]["candidate_id"]],
                            row["section_anchor_receipt"],
                        )
                        and all(
                            verify_reference_edge_receipt(row, card)
                            for card in row["coverage_cards"]
                        ),
                    }
                    for row in selected
                ],
                "trace": trace,
                "selector_runtime_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
    receipts = [receipt for row in replay for receipt in row["selected_receipts"]]
    gate = {
        "questions": len(replay),
        "manufacturers": len({row["manufacturer"] for row in replay}),
        "questions_with_reference_edges": sum(
            row["trace"]["reference_edges"] > 0 for row in replay
        ),
        "questions_with_eligible_clusters": sum(
            row["trace"]["eligible_clusters"] > 0 for row in replay
        ),
        "questions_with_selections": sum(bool(row["selected_ids"]) for row in replay),
        "selected_challenge_ids": [
            row["challenge_id"] for row in replay if row["selected_ids"]
        ],
        "receipt_count": len(receipts),
        "all_receipts_verified": (
            all(receipt["receipts_verified"] for receipt in receipts)
            if receipts
            else "not_applicable"
        ),
        "potential_reference_edges": sum(
            row["trace"]["potential_reference_edges"] for row in replay
        ),
        "potential_not_selected_edges": sum(
            len(row["trace"]["potential_not_selected_edge_indexes"])
            for row in replay
        ),
        "max_selector_runtime_ms": max(
            (row["selector_runtime_ms"] for row in replay), default=0
        ),
        "database_get_requests": 0,
        "database_writes": 0,
        "model_calls": 0,
        "interpretation": "PENDING_BLINDED_S115_CARD_REVIEW",
    }
    return {
        "instrument": "s115_reference_edge_dev_replay_v1",
        "status": "labelled_development_set_not_release_evidence",
        "gate": gate,
        "rows": replay,
        "limitations": [
            "S114 labels influenced S115 design, so this replay cannot prove generalization.",
            "A newly selected row/card must be adjudicated on its own evidence, not inherit the old selector label.",
            "The sealed nested holdout remains unopened.",
        ],
    }


def main() -> int:
    payload = build_payload()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["gate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
