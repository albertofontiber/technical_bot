#!/usr/bin/env python3
"""Build content-isolated generation and score packets for S219."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.visual_gold import sealed_artifact, stable_sha, write_json  # noqa: E402


S113 = ROOT / "evals/s113_full_contexts_freeze_v1.json"
S214_PACKET = ROOT / "evals/s214_kidde_multisource_gold_packet_v1.json"
S214_SOL = ROOT / "evals/s214_kidde_sol_generations_v1.json"
S215_RESULT = ROOT / "evals/s215_kidde_multisource_continuation_result_v1.json"
S215_ANALYSIS = ROOT / "evals/s215_kidde_multisource_failure_analysis_v1.json"
GENERATION_PACKET = ROOT / "evals/s219_omission_generation_packet_v1.json"
SCORE_PACKET = ROOT / "evals/s219_omission_score_packet_v1.json"

TARGETS = {"cat018", "hp002", "hp011", "hp017"}
KIDDE_ITEMS = (
    "kidde_2xa_interface_tradeoffs",
    "kidde_modulaser_role_selection",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed(path: Path) -> dict[str, Any]:
    value = _load(path)
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _packet(path: Path) -> dict[str, Any]:
    value = _load(path)
    body = dict(value)
    expected = body.pop("packet_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"packet identity drift: {path.name}")
    return value


def _page_chunks(item: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in item["evidence_units"]:
        if unit["unit_kind"] == "gap_free_partition_v1":
            grouped[str(unit["candidate_id"])].append(unit)
    chunks = []
    for candidate_id, units in grouped.items():
        units.sort(key=lambda row: tuple(row["source_spans"][0]))
        if units[0]["source_spans"][0][0] != 0:
            raise ValueError(f"page partition does not start at zero: {candidate_id}")
        for previous, current in zip(units, units[1:]):
            if previous["source_spans"][0][1] != current["source_spans"][0][0]:
                raise ValueError(f"page partition is not gap-free: {candidate_id}")
        first = units[0]
        chunks.append(
            {
                "id": candidate_id,
                "content": "".join(str(unit["content"]) for unit in units),
                "product_model": item["product"],
                "source_file": first["source_pdf"],
                "section_title": f"Página {first['page']}",
                "content_type": "specification",
                "similarity": 1.0,
                "page_number": first["page"],
                "document_revision": None,
                "document_revision_date": None,
                "has_diagram": False,
                "diagram_url": None,
            }
        )
    chunks.sort(key=lambda row: (str(row["source_file"]), int(row["page_number"])))
    if len(chunks) != len(item["rendered_pages"]):
        raise ValueError(f"page reconstruction geometry drift: {item['canary_id']}")
    return chunks


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    s113 = _load(S113)
    dev_rows = []
    dev_scores = []
    for row in s113["rows"]:
        qid = str(row["qid"])
        misses = [
            fact for fact in row["facts"]
            if fact.get("baseline_class") == "synthesis-miss"
        ]
        if qid in TARGETS or not misses:
            continue
        dev_rows.append(
            {
                "item_id": qid,
                "role": "historical_multichunk_development",
                "question": row["question"],
                "context": row["context"],
                "baseline_answer": row["baseline_answer"],
            }
        )
        dev_scores.append(
            {
                "item_id": qid,
                "role": "historical_multichunk_development",
                "synthesis_miss_facts": misses,
                "historical_ok_facts": [
                    fact for fact in row["facts"]
                    if fact.get("baseline_class") == "OK"
                ],
            }
        )
    if len(dev_rows) != 7 or sum(
        len(row["synthesis_miss_facts"]) for row in dev_scores
    ) != 7:
        raise ValueError("S113 non-target synthesis development geometry drift")

    s215 = _sealed(S215_RESULT)
    analysis = _sealed(S215_ANALYSIS)
    if (
        s215.get("status") != "NO_GO_S215_PIXEL_REVIEW"
        or tuple(s215.get("published_items") or ()) != KIDDE_ITEMS
        or tuple(analysis["cause"]["published_item_ids"]) != KIDDE_ITEMS
        or analysis["decision"]["next"]
        != "RETURN_TO_GENERIC_MECHANISM_DEVELOPMENT_ON_EXISTING_FROZEN_NON_TARGET_POPULATIONS"
    ):
        raise ValueError("S215 approved-principal-candidate boundary drift")
    packet = _packet(S214_PACKET)
    packet_by = {item["canary_id"]: item for item in packet["items"]}
    sol = _sealed(S214_SOL)
    sol_by = {row["canary_id"]: row for row in sol["items"]}
    kidde_rows = []
    kidde_scores = []
    for item_id in KIDDE_ITEMS:
        authored = sol_by[item_id]
        if authored.get("validation_status") != "VALID":
            raise ValueError(f"invalid inherited principal candidate: {item_id}")
        candidate = authored["candidate"]
        kidde_rows.append(
            {
                "item_id": item_id,
                "role": "kidde_multisource_guardrail",
                "question": candidate["question"],
                "context": _page_chunks(packet_by[item_id]),
                "baseline_answer": None,
            }
        )
        kidde_scores.append(
            {
                "item_id": item_id,
                "role": "kidde_multisource_guardrail",
                "atomic_facts": candidate["atomic_facts"],
                "gold_answer_sha256": stable_sha(candidate["gold_answer"]),
            }
        )

    generation = sealed_artifact(
        "s219_omission_generation_packet_v1",
        {
            "status": "SEALED_NO_SCORE_FACTS",
            "population": {
                "items": 9,
                "historical_multichunk_development": 7,
                "kidde_multisource_guardrail": 2,
                "canonical_targets": 0,
            },
            "items": dev_rows + kidde_rows,
        },
    )
    score = sealed_artifact(
        "s219_omission_score_packet_v1",
        {
            "status": "SEALED_SCORE_ONLY",
            "population": {
                "development_synthesis_facts": 7,
                "development_historical_ok_facts": sum(
                    len(row["historical_ok_facts"]) for row in dev_scores
                ),
                "kidde_atomic_facts": sum(
                    len(row["atomic_facts"]) for row in kidde_scores
                ),
                "canonical_targets": 0,
            },
            "items": dev_scores + kidde_scores,
        },
    )
    return generation, score


def main() -> int:
    generation, score = build()
    write_json(GENERATION_PACKET, generation)
    write_json(SCORE_PACKET, score)
    print(
        json.dumps(
            {
                "status": "BUILT",
                "generation_items": len(generation["items"]),
                "score_items": len(score["items"]),
                "targets": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
