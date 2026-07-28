#!/usr/bin/env python3
"""Read-only probe for the two cat007 table-representation false misses.

The frozen support judge had already accredited the candidate chunks, but the
secondary lexical guard removed the correct FAAST rows because Markdown split
number/unit cells and PDF extraction flattened ``10^5`` to ``105``.  This probe
checks only whether the repaired guard preserves those prior semantic supports.
It performs no model call and never grants an official OK verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import psycopg2
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_locator import (  # noqa: E402
    SCORE_FLOOR,
    fact_match_score,
    support_candidate_priority,
    support_l1_guard_allows,
)

BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
OUT = ROOT / "evals/s108_cat007_measurement_probe_v1.json"
TARGET_KEYS = {
    "cat007#3:2 A / 0,5 A",
    "cat007#4:10^5",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _same_family(product_model: str, gold_families: list[str]) -> bool:
    model = _fold(product_model)
    return bool(model and model in {_fold(item) for item in gold_families})


def evaluate(
    baseline_row: dict[str, Any],
    hydrated: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    gold_families = list(baseline_row["gold_families"])
    served_ids = set(baseline_row["served_ids"])
    facts = []
    for fact in baseline_row["facts"]:
        if fact["key"] not in TARGET_KEYS:
            continue
        candidate_ids = list(fact.get("support_l1_killed") or [])
        candidates = []
        for chunk_id in candidate_ids:
            row = hydrated[chunk_id]
            same_family = _same_family(row.get("product_model") or "", gold_families)
            priority = support_candidate_priority(
                fact["valor"], fact["texto"], row.get("content") or "", same_family
            )
            candidates.append(
                {
                    "chunk_id": chunk_id,
                    "product_model": row.get("product_model"),
                    "source_file": row.get("source_file"),
                    "page_number": row.get("page_number"),
                    "same_family": same_family,
                    "served_in_frozen_baseline": chunk_id in served_ids,
                    "guard_allows": support_l1_guard_allows(
                        fact["valor"],
                        fact["texto"],
                        row.get("content") or "",
                        same_family,
                    ),
                    "representation_bridge": bool(priority and priority[0] == 1),
                }
            )
        recovered = [
            row
            for row in candidates
            if row["same_family"] and row["guard_allows"]
        ]
        answer_score = fact_match_score(
            fact["valor"], fact["texto"], baseline_row["answer"]
        )
        facts.append(
            {
                "key": fact["key"],
                "baseline_class": fact["clase"],
                "baseline_support_l1_killed": candidate_ids,
                "recovered_same_family_ids": [row["chunk_id"] for row in recovered],
                "recovered_served_ids": [
                    row["chunk_id"]
                    for row in recovered
                    if row["served_in_frozen_baseline"]
                ],
                "cross_family_admitted_ids": [
                    row["chunk_id"]
                    for row in candidates
                    if not row["same_family"] and row["guard_allows"]
                ],
                "answer_fact_score": answer_score,
                "answer_value_present": bool(
                    answer_score is not None and answer_score >= SCORE_FLOOR
                ),
                "candidates": candidates,
                "candidate_interpretation": (
                    "support_and_conveyed_precondition_pending_frozen_judge_replay"
                ),
            }
        )
    if {row["key"] for row in facts} != TARGET_KEYS:
        raise RuntimeError("frozen cat007 target set changed")
    gate = {
        "facts": len(facts),
        "model_calls": 0,
        "database_writes": 0,
        "same_family_recovered_facts": sum(
            bool(row["recovered_same_family_ids"]) for row in facts
        ),
        "recovered_reaches_generator_facts": sum(
            bool(row["recovered_served_ids"]) for row in facts
        ),
        "answer_value_present_facts": sum(row["answer_value_present"] for row in facts),
        "cross_family_admitted_chunks": sum(
            len(row["cross_family_admitted_ids"]) for row in facts
        ),
        "official_ok_uplift": 0,
    }
    gate["interpretation"] = (
        "GO_MEASUREMENT_REPLAY_ONLY"
        if gate["same_family_recovered_facts"] == 2
        and gate["recovered_reaches_generator_facts"] == 2
        and gate["answer_value_present_facts"] == 2
        and gate["cross_family_admitted_chunks"] == 0
        else "NO_GO_MEASUREMENT_BRIDGE"
    )
    return {"gate": gate, "facts": facts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    row = next(item for item in baseline["per_gold"] if item["qid"] == "cat007")
    ids = sorted(
        {
            chunk_id
            for fact in row["facts"]
            if fact["key"] in TARGET_KEYS
            for chunk_id in (fact.get("support_l1_killed") or [])
        }
    )
    connection = psycopg2.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=20,
        application_name="codex_s108_cat007_measurement_readonly",
    )
    connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout='20s'; SET LOCAL lock_timeout='3s'")
        cursor.execute(
            """
            SELECT id::text, product_model, source_file, page_number, content
              FROM public.chunks_v2
             WHERE id=ANY(%s::uuid[])
             ORDER BY id
            """,
            (ids,),
        )
        hydrated = {
            item[0]: {
                "id": item[0],
                "product_model": item[1],
                "source_file": item[2],
                "page_number": item[3],
                "content": item[4],
            }
            for item in cursor.fetchall()
        }
    connection.rollback()
    connection.close()
    if set(hydrated) != set(ids):
        raise RuntimeError("one or more frozen support chunks are unavailable")

    evaluated = evaluate(row, hydrated)
    row_receipt = [
        {
            "id": item["id"],
            "product_model": item["product_model"],
            "source_file": item["source_file"],
            "page_number": item["page_number"],
            "content_sha256": hashlib.sha256(
                item["content"].encode("utf-8")
            ).hexdigest(),
        }
        for item in sorted(hydrated.values(), key=lambda value: value["id"])
    ]
    payload = {
        "instrument": "s108_cat007_measurement_probe_v1",
        "read_only": True,
        "frozen_inputs": {
            "baseline": BASELINE.relative_to(ROOT).as_posix(),
            "baseline_sha256": _sha256(BASELINE),
            "audit_locator_sha256": _sha256(ROOT / "scripts/audit_locator.py"),
            "probe_sha256": _sha256(Path(__file__).resolve()),
            "target_keys": sorted(TARGET_KEYS),
        },
        "source_rows": row_receipt,
        **evaluated,
        "limitations": [
            "The bridge preserves prior semantic support; it never grants support alone.",
            "This probe does not rerun the frozen dual judge and cannot change official OK.",
            "Only the two preregistered cat007 representation failures are measured here.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["gate"], ensure_ascii=False, indent=2))
    return 0 if payload["gate"]["interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
