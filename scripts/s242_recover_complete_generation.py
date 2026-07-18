#!/usr/bin/env python3
"""Deterministically complete S241 from its already-finished provider receipts."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s235_run_direct_clause_bound_ab import _units  # noqa: E402
from src.rag.clause_bound_synthesis import (  # noqa: E402
    assemble_claim_blocks,
    validate_claim_block,
)
from src.rag.decomposed_evidence_planner_v2 import validate_plan  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    parse_json,
    sealed_artifact,
    stable_sha,
    write_json,
)

PACKET = ROOT / "evals/s235_direct_clause_bound_generation_packet_v1.json"
S241_GENERATION = ROOT / "evals/s241_direct_clause_bound_generation_v1.json"
S241_LEDGER = ROOT / "evals/s241_direct_clause_bound_call_ledger_v1.json"
OUT = ROOT / "evals/s242_direct_clause_bound_generation_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _completed_by_label(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = [event for event in ledger["events"] if event.get("event") == "COMPLETED"]
    by_label = {str(row["label"]): row for row in rows}
    if len(by_label) != len(rows):
        raise ValueError("S242 duplicate completed call label")
    return by_label


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S242 recovered generation already exists")
    packet = _sealed(PACKET)
    generation = _sealed(S241_GENERATION)
    ledger = _sealed(S241_LEDGER)
    if (
        generation.get("status") != "HOLD_EXTERNAL_OR_INVALID_NO_SEMANTIC_RETRY"
        or generation.get("score_packet_opened") is not False
        or [item["qid"] for item in generation["items"]] != list(QIDS[:3])
        or any(len(item["replicas"]) != 2 for item in generation["items"])
        or ledger.get("status") != "HOLD"
    ):
        raise ValueError("S242 S241 recovery precondition drift")
    packet_by_qid = {str(item["qid"]): item for item in packet["items"]}
    completed = _completed_by_label(ledger)
    item = packet_by_qid["hp017"]
    units = _units(item)
    by_id = {unit.unit_id: unit for unit in units}
    replicas = []
    used_labels = []
    for replicate in (1, 2):
        planner_label = f"hp017:r{replicate}:planner"
        baseline_label = f"hp017:r{replicate}:baseline"
        planner_event = completed[planner_label]
        baseline_event = completed[baseline_label]
        if (
            planner_event["model"] != "claude-haiku-4-5-20251001"
            or baseline_event["model"] != "claude-sonnet-4-6"
            or planner_event["stop_reason"] != "end_turn"
            or baseline_event["stop_reason"] != "end_turn"
        ):
            raise ValueError("S242 planner or baseline receipt invalid")
        plan, selected_ids = validate_plan(
            parse_json(planner_event["raw_output"]), set(by_id)
        )
        blocks = []
        for index, obligation in enumerate(plan, 1):
            label = f"hp017:r{replicate}:writer:{index}"
            event = completed[label]
            if event["model"] != "claude-sonnet-4-6" or event["stop_reason"] != "end_turn":
                raise ValueError(f"S242 invalid writer receipt: {label}")
            value = parse_json(event["raw_output"])
            validate_claim_block(value, set(obligation["unit_ids"]))
            blocks.append({"obligation_index": index, "value": value})
            used_labels.append(label)
        answer, assembly = assemble_claim_blocks(item["question"], plan, blocks, units)
        replicas.append(
            {
                "replicate": replicate,
                "baseline_answer": baseline_event["raw_output"],
                "treatment_answer": answer,
                "plan": plan,
                "selected_unit_ids": selected_ids,
                "claim_blocks": blocks,
                "assembly": assembly,
                "fragment_count": len(item["context"]),
            }
        )
        used_labels.extend([planner_label, baseline_label])
    items = generation["items"] + [{"qid": "hp017", "replicas": replicas}]
    if [item["qid"] for item in items] != list(QIDS):
        raise ValueError("S242 recovered item ordering drift")
    write_json(
        OUT,
        sealed_artifact(
            "s235_direct_clause_bound_generation_v1",
            {
                "status": "COMPLETE_SCORE_NOT_OPENED",
                "items": items,
                "actual_cost_usd": ledger["actual_cost_usd"],
                "score_packet_opened": False,
                "semantic_retries": 0,
                "transport_retries_max_per_label": 1,
                "deterministic_recovery": {
                    "source": "s241_completed_provider_receipts",
                    "provider_calls_added": 0,
                    "revalidated_labels": sorted(used_labels),
                    "claim_characters_maximum": 280,
                },
            },
        ),
    )
    print(
        json.dumps(
            {
                "status": "COMPLETE_SCORE_NOT_OPENED",
                "questions": len(items),
                "replicates": sum(len(item["replicas"]) for item in items),
                "provider_calls_added": 0,
                "cost_usd": ledger["actual_cost_usd"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
