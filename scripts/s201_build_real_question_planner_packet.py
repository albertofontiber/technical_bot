#!/usr/bin/env python3
"""Freeze a deterministic holdout of pre-existing real benchmark questions."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s165_answer_archetype_ledger import stable_sha
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
CONTEXTS = ROOT / "evals/s113_full_contexts_freeze_v1.json"
DEFAULT_OUT = ROOT / "evals/s201_real_question_planner_packet_v1.json"
SEED = "s201-real-question-holdout-v1"
TARGET_QIDS = frozenset({"cat018", "hp002", "hp011", "hp017"})
DEFAULT_OFF_CANDIDATE_QIDS = frozenset({"cat007", "cat013"})
COHORT_SIZE = 12


def file_sha(path: Path) -> str:
    # Evaluation artifacts are text.  Seal their logical LF representation so
    # a Windows checkout and Linux CI validate the same bytes.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _rank(label: str) -> str:
    return hashlib.sha256(f"{SEED}|{label}".encode("utf-8")).hexdigest()


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _manifest(content: str, fragment_number: int, candidate_id: str) -> list[dict[str, Any]]:
    return [
        {
            "unit_id": unit.unit_id,
            "unit_kind": unit.unit_kind,
            "source_spans": [list(span) for span in unit.source_spans],
            "content_sha256": unit.content_sha256,
        }
        for unit in build_header_aware_evidence_units(
            content,
            fragment_number=fragment_number,
            candidate_id=candidate_id,
        )
    ]


def build_packet() -> dict[str, Any]:
    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    contexts_artifact = json.loads(CONTEXTS.read_text(encoding="utf-8"))
    contexts_by_qid = {
        str(row["qid"]): row for row in contexts_artifact["rows"]
    }
    excluded = TARGET_QIDS | DEFAULT_OFF_CANDIDATE_QIDS
    eligible: list[dict[str, Any]] = []
    for row in baseline["per_gold"]:
        qid = str(row["qid"])
        context_row = contexts_by_qid.get(qid)
        if context_row is None or qid in excluded:
            continue
        answer_points = list(row["facts"])
        contexts = context_row["context"]
        if len(answer_points) < 2 or not contexts:
            continue
        primary = contexts[0]
        manufacturer = str(primary.get("manufacturer") or "").strip()
        product_model = str(primary.get("product_model") or "").strip()
        if not manufacturer or not product_model:
            continue
        eligible.append(
            {
                "qid": qid,
                "question": str(row["question"]),
                "answer_points": len(answer_points),
                "baseline_reaching_generation_points": sum(
                    bool(fact.get("reaches_gen")) for fact in answer_points
                ),
                "manufacturer": manufacturer,
                "product_model": product_model,
                "product_key": f"{_norm(manufacturer)}:{_norm(product_model)}",
                "context_row": context_row,
            }
        )

    # First take one seeded item per manufacturer, then fill by the same seeded
    # order without repeating normalized manufacturer/product pairs.  No answer,
    # class, reaches_gen outcome, planner output or target label participates.
    chosen: list[dict[str, Any]] = []
    product_keys: set[str] = set()
    manufacturers = sorted(
        {row["manufacturer"] for row in eligible},
        key=lambda value: _rank(f"manufacturer|{value}"),
    )
    for manufacturer in manufacturers:
        rows = sorted(
            (row for row in eligible if row["manufacturer"] == manufacturer),
            key=lambda row: _rank(row["qid"]),
        )
        row = next(
            (item for item in rows if item["product_key"] not in product_keys),
            None,
        )
        if row is not None:
            chosen.append(row)
            product_keys.add(row["product_key"])
    for row in sorted(eligible, key=lambda item: _rank(item["qid"])):
        if len(chosen) >= COHORT_SIZE:
            break
        if row not in chosen and row["product_key"] not in product_keys:
            chosen.append(row)
            product_keys.add(row["product_key"])
    if len(chosen) != COHORT_SIZE:
        raise RuntimeError("S201 could not construct the frozen cohort")

    items: list[dict[str, Any]] = []
    for row in chosen:
        evidence_sources = []
        seen_candidate_ids: set[str] = set()
        for fragment_number, source in enumerate(row["context_row"]["context"], 1):
            candidate_id = str(source.get("id") or "")
            content = str(source.get("content") or "")
            if not candidate_id or not content or candidate_id in seen_candidate_ids:
                raise RuntimeError(f"S201 invalid context identity for {row['qid']}")
            seen_candidate_ids.add(candidate_id)
            evidence_sources.append(
                {
                    "fragment_number": fragment_number,
                    "candidate_id": candidate_id,
                    "document_id": str(source.get("document_id") or ""),
                    "manufacturer": str(source.get("manufacturer") or ""),
                    "product_model": str(source.get("product_model") or ""),
                    "source_file": str(source.get("source_file") or ""),
                    "page_number": source.get("page_number"),
                    "content": content,
                    "content_sha256": hashlib.sha256(
                        content.encode("utf-8")
                    ).hexdigest(),
                    "evidence_unit_manifest": _manifest(
                        content, fragment_number, candidate_id
                    ),
                }
            )
        items.append(
            {
                "qid": row["qid"],
                "question": row["question"],
                "primary_identity": {
                    "manufacturer": row["manufacturer"],
                    "product_model": row["product_model"],
                    "normalized_product_key": row["product_key"],
                },
                "eligible_answer_points": row["answer_points"],
                "baseline_reaching_generation_points": row[
                    "baseline_reaching_generation_points"
                ],
                "serving_context_sha256": row["context_row"][
                    "serving_context_sha256"
                ],
                "evidence_sources": evidence_sources,
            }
        )

    selection = {
        "seed": SEED,
        "eligible_questions": len(eligible),
        "items": len(items),
        "manufacturers": len(
            {item["primary_identity"]["manufacturer"] for item in items}
        ),
        "unique_normalized_products": len(
            {
                item["primary_identity"]["normalized_product_key"]
                for item in items
            }
        ),
        "eligible_answer_points": sum(
            item["eligible_answer_points"] for item in items
        ),
        "baseline_reaching_generation_points": sum(
            item["baseline_reaching_generation_points"] for item in items
        ),
        "target_question_overlap": len(
            {item["qid"] for item in items} & TARGET_QIDS
        ),
        "default_off_candidate_question_overlap": len(
            {item["qid"] for item in items} & DEFAULT_OFF_CANDIDATE_QIDS
        ),
        "question_selection_uses_answer_class_or_pipeline_outcome": False,
        "question_selection_uses_planner_output": False,
        "source_table": "chunks_v2",
        "chunks_v3_used": False,
    }
    body = {
        "instrument": "s201_real_question_planner_packet_v1",
        "status": "SEALED_PREEXISTING_REAL_QUESTION_HOLDOUT",
        "inputs": {
            str(BASELINE.relative_to(ROOT)).replace("\\", "/"): file_sha(BASELINE),
            str(CONTEXTS.relative_to(ROOT)).replace("\\", "/"): file_sha(CONTEXTS),
        },
        "selection": selection,
        "excluded_qids": {
            "target_synthesis_residual": sorted(TARGET_QIDS),
            "default_off_candidates": sorted(DEFAULT_OFF_CANDIDATE_QIDS),
        },
        "items": items,
        "database_reads": 0,
        "database_writes": 0,
        "gold_claims_present": False,
    }
    return {**body, "packet_sha256": stable_sha(body)}


def main() -> int:
    payload = build_packet()
    DEFAULT_OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["selection"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
