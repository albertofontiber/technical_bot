#!/usr/bin/env python3
"""Build S216's score-free single- and multi-chunk generation packet."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SINGLE = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
MULTI = ROOT / "evals/s113_full_contexts_freeze_v1.json"
OUT = ROOT / "evals/s216_synthesis_screen_packet_v1.json"
TARGETS = {"cat018", "hp002", "hp011", "hp017"}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def single_context(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": item["chunk_id"],
            "content": item["excerpt"],
            "context": "",
            "product_model": item["product_model"],
            "manufacturer": item["manufacturer"],
            "source_file": item["source_file"],
            "page_number": item["page_number"],
            "section_title": item["section_title"],
            "content_type": (
                "specification" if item["stratum"] == "table" else "general"
            ),
            "document_id": item["document_id"],
            "similarity": 1.0,
            "has_diagram": False,
            "diagram_url": None,
        }
    ]


def main() -> int:
    single = json.loads(SINGLE.read_text(encoding="utf-8"))
    multi = json.loads(MULTI.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in single["items"]:
        rows.append(
            {
                "item_id": item["item_id"],
                "role": "single_source_development",
                "stratum": item["stratum"],
                "question": item["question"],
                "context": single_context(item),
                "context_sha256": stable_sha(single_context(item)),
            }
        )
    for source in multi["rows"]:
        qid = str(source["qid"])
        if qid in TARGETS:
            continue
        context = source["context"]
        rows.append(
            {
                "item_id": qid,
                "role": "protected_multichunk",
                "stratum": "multi_chunk",
                "question": source["question"],
                "context": context,
                "context_sha256": stable_sha(context),
                "serving_context_sha256": source["serving_context_sha256"],
            }
        )
    if len(rows) != 49 or len({row["item_id"] for row in rows}) != 49:
        raise RuntimeError("S216 screen population drift")
    if any(row["item_id"] in TARGETS for row in rows):
        raise RuntimeError("S216 target leaked into screen packet")
    if any(
        key in row
        for row in rows
        for key in ("facts", "answer_points", "gold", "baseline_answer", "answer")
    ):
        raise RuntimeError("S216 screen packet contains scoring or answer data")
    multi_rows = [row for row in rows if row["role"] == "protected_multichunk"]
    if len(multi_rows) != 35 or any(len(row["context"]) < 2 for row in multi_rows):
        raise RuntimeError("S216 multi-chunk guardrail population drift")
    body = {
        "schema": "s216_synthesis_screen_packet_v1",
        "status": "FROZEN_SCORE_FREE_GENERATION_PACKET",
        "source_inputs": {
            "single": {"path": str(SINGLE.relative_to(ROOT)), "sha256": file_sha(SINGLE)},
            "multi": {"path": str(MULTI.relative_to(ROOT)), "sha256": file_sha(MULTI)},
        },
        "population": {
            "questions": 49,
            "single_source_development": 14,
            "protected_multichunk": 35,
            "target_questions": 0,
            "multi_context_rows": sum(len(row["context"]) for row in multi_rows),
        },
        "forbidden_fields_absent": True,
        "rows": rows,
    }
    payload = {**body, "payload_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"path": str(OUT.relative_to(ROOT)), **payload["population"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
