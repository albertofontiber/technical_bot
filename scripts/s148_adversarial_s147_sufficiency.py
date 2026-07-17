#!/usr/bin/env python3
"""Build and execute one bounded semantic sufficiency review of S147."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s145_adversarial_sufficiency_review import (
    execute as execute_judges,
    file_sha,
    stable_sha,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s147_fresh_source_packet_v1.json"
COHORT = ROOT / "evals/s147_fresh_obligation_cohort_v1.json"
RESULT = ROOT / "evals/s147_per_item_header_aware_v1.json"
DEFAULT_PACKET = ROOT / "evals/s148_adversarial_s147_packet_v1.json"
DEFAULT_PREREG = ROOT / "evals/s148_adversarial_s147_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s148_adversarial_s147_execution_permit_v1.yaml"
DEFAULT_SOL = ROOT / "evals/s148_sol56_xhigh_s147_sufficiency_v1.json"
DEFAULT_FABLE = ROOT / "evals/s148_fable5_xhigh_s147_sufficiency_v1.json"
DEFAULT_OUT = ROOT / "evals/s148_adversarial_s147_sufficiency_v1.json"
DEFAULT_ENV = Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env")


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_packet() -> dict[str, Any]:
    sources = json.loads(SOURCE.read_text(encoding="utf-8"))
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    source_by = {row["item_id"]: row for row in sources["items"]}
    cohort_by = {row["item_id"]: row for row in cohort["items"]}
    questions = []
    for index, row in enumerate(result["rows"], 1):
        item_id = row["item_id"]
        source = source_by[item_id]["excerpt"]
        units = build_header_aware_evidence_units(
            source, fragment_number=1, candidate_id=item_id
        )
        by_id = {unit.unit_id: unit for unit in units}
        selected = []
        for receipt in row["selected_unit_receipts"]:
            unit = by_id[receipt["unit_id"]]
            if unit.content_sha256 != receipt["content_sha256"]:
                raise RuntimeError("S148 selected evidence drift")
            selected.append(
                {
                    "evidence_id": unit.unit_id,
                    "content": unit.content,
                }
            )
        questions.append(
            {
                "question_id": f"Q{index:02d}",
                "question": cohort_by[item_id]["question"],
                "full_source": source,
                "selected_evidence": selected,
            }
        )
    body = {
        "instrument": "s148_adversarial_s147_packet_v1",
        "blind": {
            "authored_answer_points_included": False,
            "s147_metrics_included": False,
            "judge_identities_included": False,
        },
        "questions": questions,
    }
    return {**body, "packet_sha256": stable_sha(body)}


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S148 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_FINAL":
        raise RuntimeError("S148 execution is not permitted")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S148 frozen input drift: {label}")
    for label, spec in permit["frozen_artifacts"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S148 permitted artifact drift: {label}")
    return prereg


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-packet", action="store_true")
    parser.add_argument("--execute-paid", action="store_true")
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--sol", type=Path, default=DEFAULT_SOL)
    parser.add_argument("--fable", type=Path, default=DEFAULT_FABLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if args.build_packet:
        packet = build_packet()
        _write(args.packet, packet)
        print(json.dumps({"status": "PACKET_BUILT", "questions": len(packet["questions"]), "packet_sha256": packet["packet_sha256"]}))
        return 0
    if not args.execute_paid:
        raise RuntimeError("choose --build-packet or --execute-paid")
    prereg = validate_authorization(args.prereg, args.permit)
    judged = execute_judges(prereg, args.env_file, args.sol, args.fable)
    go = judged["status"] == "GO_TO_S145_FRESH_INDEPENDENT"
    body = {
        **judged,
        "instrument": "s148_adversarial_s147_sufficiency_v1",
        "status": "GO_TO_IMPLEMENTATION_PROBE" if go else "NO_GO",
        "decision": {
            "implementation_probe": "GO" if go else "NO_GO",
            "production": "NO_GO",
            "facts_moved_to_ok": 0,
        },
    }
    body.pop("result_sha256", None)
    result = {**body, "result_sha256": stable_sha(body)}
    _write(args.out, result)
    print(json.dumps({"status": result["status"], **result["result"], **result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
