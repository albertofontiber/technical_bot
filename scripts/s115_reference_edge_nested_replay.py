#!/usr/bin/env python3
"""Run the one-shot S115 nested smoke after implementation hash freeze."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Callable

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.reference_edge_coverage import (
    select_reference_edge_coverage,
    verify_reference_edge_receipt,
)

NESTED = ROOT / "evals/s115_reference_edge_nested_holdout_freeze_v1.json"
BASE = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
PREREG = ROOT / "evals/s115_reference_edge_nested_holdout_prereg_v8.yaml"
IMPLEMENTATION_FREEZE = ROOT / "evals/s115_reference_edge_implementation_freeze_v1.yaml"
OUT = ROOT / "evals/s115_reference_edge_nested_replay_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_inputs() -> dict:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    receipt = yaml.safe_load(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    expected = {
        prereg["frozen_design"]["path"]: prereg["frozen_design"]["sha256"],
        prereg["frozen_design"]["config_path"]: prereg["frozen_design"]["config_sha256"],
        prereg["nested_holdout"]["path"]: prereg["nested_holdout"]["sha256"],
    }
    expected.update(receipt["frozen_files"])
    mismatches = {}
    for relative, digest in expected.items():
        path = ROOT / relative
        actual = _sha256(path) if path.is_file() else None
        if actual != digest:
            mismatches[relative] = {"expected": digest, "actual": actual}
    if mismatches:
        raise RuntimeError(f"S115 frozen-input mismatch: {mismatches}")
    return {
        "prereg_sha256": _sha256(PREREG),
        "implementation_freeze_sha256": _sha256(IMPLEMENTATION_FREEZE),
        "nested_holdout_sha256": _sha256(NESTED),
        "base_scope_sha256": _sha256(BASE),
    }


def build_payload(
    nested: dict,
    base: dict,
    *,
    selector: Callable = select_reference_edge_coverage,
    frozen_receipts: dict | None = None,
) -> dict:
    scopes = base["candidate_scopes"]
    rows_by_id = {
        str(row["id"]): row for rows in scopes.values() for row in rows
    }
    replay = []
    for index, item in enumerate(nested["sample"], start=1):
        source = rows_by_id[str(item["chunk_id"])]
        candidates = scopes[item["scope_key"]]
        started = time.perf_counter()
        selected, trace = selector(item["question"], [source], candidates)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        receipts = []
        for row in selected:
            anchor = rows_by_id[str(row["section_anchor_receipt"]["candidate_id"])]
            receipts.append(
                {
                    "candidate_id": str(row["id"]),
                    "section_title": row.get("section_title"),
                    "reference_edge": row["reference_edge"],
                    "section_anchor_receipt": row["section_anchor_receipt"],
                    "coverage_cards": row["coverage_cards"],
                    "receipts_verified": verify_reference_edge_receipt(
                        anchor, row["section_anchor_receipt"]
                    )
                    and all(
                        verify_reference_edge_receipt(row, card)
                        for card in row["coverage_cards"]
                    ),
                }
            )
        replay.append(
            {
                "nested_id": f"s115n{index:03d}",
                "manufacturer": item["manufacturer"],
                "product_model": item["product_model"],
                "question": item["question"],
                "served_id": str(item["chunk_id"]),
                "served_content": source.get("content"),
                "scope_key": item["scope_key"],
                "selected_ids": [str(row["id"]) for row in selected],
                "selected_receipts": receipts,
                "trace": trace,
                "selector_runtime_ms": elapsed_ms,
            }
        )
    all_receipts = [receipt for row in replay for receipt in row["selected_receipts"]]
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
        "receipt_count": len(all_receipts),
        "all_receipts_verified": (
            all(receipt["receipts_verified"] for receipt in all_receipts)
            if all_receipts
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
        "adjudication_status": "PENDING_BLINDED_RELEVANCE_AND_FALSE_NEGATIVE_AUDIT",
    }
    return {
        "instrument": "s115_reference_edge_nested_replay_v1",
        "status": "single_unseal_pending_blinded_adjudication",
        "frozen_receipts": frozen_receipts or {},
        "gate": gate,
        "rows": replay,
        "limitations": [
            "This 12-question, two-manufacturer cohort is a smoke test, not +30-manufacturer release evidence.",
            "Selector output is not a correctness label; selected cards and visible false negatives require blinded adjudication.",
            "Any post-unseal selector or config change invalidates this result.",
        ],
    }


def main() -> int:
    if OUT.exists():
        raise RuntimeError(f"one-shot S115 output already exists: {OUT}")
    frozen = verify_frozen_inputs()
    nested = json.loads(NESTED.read_text(encoding="utf-8"))
    base = json.loads(BASE.read_text(encoding="utf-8"))
    payload = build_payload(nested, base, frozen_receipts=frozen)
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["gate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
