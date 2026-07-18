#!/usr/bin/env python3
"""Freeze S260 generation and scoring bytes after generation, before scoring."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals/s260_evidence_claim_ir_prereg_v1.yaml"
EXECUTION_PERMIT = ROOT / "evals/s260_evidence_claim_ir_execution_permit_v1.yaml"
GENERATION = ROOT / "evals/s260_evidence_claim_ir_generation_v1.json"
LEDGER = ROOT / "evals/s260_evidence_claim_ir_call_ledger_v1.json"
OUT = ROOT / "evals/s260_evidence_claim_ir_score_execution_permit_v1.yaml"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sealed(path: Path) -> dict[str, Any]:
    from src.rag.visual_gold import stable_sha

    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S260 score permit already exists")
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    execution = yaml.safe_load(EXECUTION_PERMIT.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_AFTER_DUAL_FRONTIER_PASS":
        raise RuntimeError("S260 preregistration is not frozen")
    if execution.get("status") != "EXECUTION_GO_PAID_BOUNDED_NO_RETRY":
        raise RuntimeError("S260 execution permit is invalid")
    if file_sha(PREREG) != execution["frozen_artifacts"]["prereg"]["sha256"]:
        raise RuntimeError("S260 preregistration drift after execution permit")

    generation = _sealed(GENERATION)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    receipts = ledger.get("receipts") or []
    expected_pairs = {(qid, replica) for qid in QIDS for replica in (1, 2)}
    observed_pairs = {(row.get("qid"), row.get("replica")) for row in receipts}
    if (
        generation.get("status") != "COMPLETE_SCORE_NOT_OPENED"
        or generation.get("score_packet_opened") is not False
        or generation.get("call_ledger_sha256") != file_sha(LEDGER)
        or ledger.get("status") != "PAID_CHECKPOINT_COMPLETE"
        or observed_pairs != expected_pairs
        or len(receipts) != 8
        or any(row.get("status") != "completed" for row in receipts)
    ):
        raise RuntimeError("S260 generation or call ledger is incomplete")

    scoring = prereg["frozen_scoring_inputs"]
    for spec in scoring.values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S260 scoring input drift: {spec['path']}")
    permit = {
        "schema": "s260_evidence_claim_ir_score_execution_permit_v1",
        "status": "SCORE_EXECUTION_GO_FROZEN_AFTER_GENERATION",
        "generation": {
            "path": GENERATION.relative_to(ROOT).as_posix(),
            "sha256": file_sha(GENERATION),
        },
        "call_ledger": {
            "path": LEDGER.relative_to(ROOT).as_posix(),
            "sha256": file_sha(LEDGER),
        },
        "prereg": {
            "path": PREREG.relative_to(ROOT).as_posix(),
            "sha256": file_sha(PREREG),
        },
        "execution_permit": {
            "path": EXECUTION_PERMIT.relative_to(ROOT).as_posix(),
            "sha256": file_sha(EXECUTION_PERMIT),
        },
        "frozen_scoring_inputs": scoring,
        "facts_moved_to_ok": 0,
    }
    OUT.write_text(yaml.safe_dump(permit, sort_keys=False), encoding="utf-8")
    print("S260_SCORE_EXECUTION_PERMIT_CREATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
