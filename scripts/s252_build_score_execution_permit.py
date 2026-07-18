#!/usr/bin/env python3
"""Bind the completed S252 generation to the preregistered scoring bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from src.rag.visual_gold import sealed_artifact, stable_sha, write_json

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals/s252_adaptive_reasoning_writer_ab_prereg_v1.yaml"
GENERATION = ROOT / "evals/s252_adaptive_reasoning_writer_generation_v1.json"
OUT = ROOT / "evals/s252_adaptive_reasoning_writer_score_execution_permit_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S252 score permit already exists")
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_AFTER_DUAL_FRONTIER_PASS":
        raise ValueError("S252 preregistration is not execution-frozen")
    for label, spec in prereg["frozen_scoring_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S252 preregistered scoring input drift: {label}")
    generation = _sealed(GENERATION)
    if (
        generation.get("status") != "COMPLETE_SCORE_NOT_OPENED"
        or generation.get("score_packet_opened") is not False
        or tuple(row.get("qid") for row in generation.get("items") or []) != QIDS
    ):
        raise ValueError("S252 completed generation invariant failed")
    write_json(
        OUT,
        sealed_artifact(
            "s252_adaptive_reasoning_writer_score_execution_permit_v1",
            {
                "status": "SCORE_EXECUTION_GO_POST_GENERATION_BOUND",
                "generation": {
                    "path": GENERATION.relative_to(ROOT).as_posix(),
                    "sha256": _sha(GENERATION),
                },
                "frozen_scoring_inputs": prereg["frozen_scoring_inputs"],
                "score_packet_opened": False,
                "created_after_generation_complete": True,
            },
        ),
    )
    print(json.dumps({"status": "S252_SCORE_EXECUTION_PERMIT_CREATED"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

