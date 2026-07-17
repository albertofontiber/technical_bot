#!/usr/bin/env python3
"""Freeze target questions, source identity, obligations and conflicts for S201."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s141_source_bound_technical_obligations import (
    DEV_FREEZE,
    answer_map,
    attested,
    plan_for,
)
from scripts.s165_answer_archetype_ledger import stable_sha
from src.rag.answer_planner import build_answer_conflicts


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s201_target_evaluation_packet_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_packet() -> dict[str, Any]:
    freeze = json.loads(DEV_FREEZE.read_text(encoding="utf-8"))
    rows_by_qid = {str(row["qid"]): row for row in freeze["rows"]}
    answers = answer_map()
    items = []
    for qid in QIDS:
        row = rows_by_qid[qid]
        chunks = attested(row)
        obligations = plan_for(row)
        conflicts = build_answer_conflicts(row["question"], chunks)
        items.append(
            {
                "qid": qid,
                "question": row["question"],
                "chunks": chunks,
                "base_answer": answers[qid],
                "obligations": [item.to_dict() for item in obligations],
                "conflicts": [item.to_dict() for item in conflicts],
            }
        )
    body = {
        "instrument": "s201_target_evaluation_packet_v1",
        "status": "SEALED_TARGET_EVALUATOR_INPUTS",
        "inputs": {
            "evals/s113_full_contexts_freeze_v1.json": file_sha(DEV_FREEZE),
            "evals/s113_full_answer_regression_v1.json": file_sha(
                ROOT / "evals/s113_full_answer_regression_v1.json"
            ),
            "evals/s133_unmeasured_answer_probe_v1.json": file_sha(
                ROOT / "evals/s133_unmeasured_answer_probe_v1.json"
            ),
            "scripts/s141_source_bound_technical_obligations.py": file_sha(
                ROOT / "scripts/s141_source_bound_technical_obligations.py"
            ),
            "src/rag/answer_planner.py": file_sha(
                ROOT / "src/rag/answer_planner.py"
            ),
        },
        "population": {
            "questions": len(items),
            "qids": list(QIDS),
            "obligations": sum(len(item["obligations"]) for item in items),
            "conflicts": sum(len(item["conflicts"]) for item in items),
        },
        "items": items,
        "database_reads": 0,
        "database_writes": 0,
    }
    normalized = json.loads(json.dumps(body, ensure_ascii=False))
    return {**normalized, "packet_sha256": stable_sha(normalized)}


def main() -> int:
    payload = build_packet()
    DEFAULT_OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["population"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
