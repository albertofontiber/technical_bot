#!/usr/bin/env python3
"""Split the frozen four-question target into leakage-safe generation and score packets."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.visual_gold import sealed_artifact, write_json  # noqa: E402

TARGET = ROOT / "evals/s201_target_evaluation_packet_v1.json"
RESIDUAL = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
GENERATION = ROOT / "evals/s235_direct_clause_bound_generation_packet_v1.json"
SCORE = ROOT / "evals/s235_direct_clause_bound_score_packet_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_packets() -> tuple[dict[str, Any], dict[str, Any]]:
    target = _load(TARGET)
    audit = _load(RESIDUAL)
    if target.get("status") != "SEALED_TARGET_EVALUATOR_INPUTS":
        raise ValueError("S201 target packet is not sealed evaluator input")
    if target.get("population") != {
        "questions": 4,
        "qids": list(QIDS),
        "obligations": 20,
        "conflicts": 1,
    }:
        raise ValueError("S201 target population drift")
    if audit.get("population", {}).get("genuine_synthesis_residuals") != 12:
        raise ValueError("S163 residual population drift")

    residual_by_qid: dict[str, list[str]] = {qid: [] for qid in QIDS}
    for row in audit["rows"]:
        qid = str(row["qid"])
        if qid not in residual_by_qid:
            raise ValueError(f"unexpected S163 qid: {qid}")
        if not row["covered"]:
            residual_by_qid[qid].append(str(row["obligation_id"]))
    if sum(map(len, residual_by_qid.values())) != 12:
        raise ValueError("S163 residual IDs do not total twelve")

    by_qid = {str(item["qid"]): item for item in target["items"]}
    if tuple(by_qid) != QIDS:
        raise ValueError("S201 target ordering drift")

    generation_items = []
    score_items = []
    for qid in QIDS:
        item = by_qid[qid]
        obligation_ids = {
            str(obligation["obligation_id"]) for obligation in item["obligations"]
        }
        residual_ids = residual_by_qid[qid]
        if not set(residual_ids).issubset(obligation_ids):
            raise ValueError(f"residual obligation missing from target packet: {qid}")
        generation_items.append(
            {
                "qid": qid,
                "question": item["question"],
                "context": item["chunks"],
            }
        )
        score_items.append(
            {
                "qid": qid,
                "canonical_answer": item["base_answer"],
                "fragment_count": len(item["chunks"]),
                "obligations": item["obligations"],
                "conflicts": item["conflicts"],
                "residual_obligation_ids": residual_ids,
            }
        )

    generation = sealed_artifact(
        "s235_direct_clause_bound_generation_packet_v1",
        {
            "status": "SEALED_GENERATION_ONLY_NO_SCORE_FIELDS",
            "population": {"questions": 4, "qids": list(QIDS), "chunks": 51},
            "items": generation_items,
            "forbidden_score_fields_absent": True,
            "database_reads": 0,
            "database_writes": 0,
        },
    )
    score = sealed_artifact(
        "s235_direct_clause_bound_score_packet_v1",
        {
            "status": "SEALED_SCORE_ONLY_OPEN_AFTER_GENERATION",
            "population": {
                "questions": 4,
                "qids": list(QIDS),
                "obligations": 20,
                "genuine_synthesis_residuals": 12,
                "conflicts": 1,
            },
            "items": score_items,
            "generation_content_absent": True,
            "database_reads": 0,
            "database_writes": 0,
        },
    )
    return generation, score


def main() -> int:
    generation, score = build_packets()
    write_json(GENERATION, generation)
    write_json(SCORE, score)
    print(
        json.dumps(
            {
                "status": "S235_PACKETS_SEALED",
                "questions": len(generation["items"]),
                "chunks": generation["population"]["chunks"],
                "obligations": score["population"]["obligations"],
                "residuals": score["population"]["genuine_synthesis_residuals"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
