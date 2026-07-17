#!/usr/bin/env python3
"""Bounded development pilot: complete relation index plus exact source units."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s156_frontier_synthesis_ceiling import build_prompt
from src.rag.evidence_units_v2 import build_header_aware_evidence_units
from src.rag.omission_correction import invalid_citations, point_covered


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
DEFAULT_PREREG = ROOT / "evals/s189_all_relation_writer_pilot_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s189_all_relation_writer_pilot_execution_permit_v1.yaml"
DEFAULT_RECEIPTS = ROOT / "evals/s189_all_relation_writer_pilot_receipts_v1.json"
DEFAULT_RESULT = ROOT / "evals/s189_all_relation_writer_pilot_v1.json"
SOURCE = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
STORE = ROOT / "evals/s186_relation_store_v1.json"
BASELINE = ROOT / "evals/s173_baseline_answer_receipts_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
ITEM_IDS = ("s147_src_01", "s147_src_04", "s147_src_08", "s147_src_11")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S189 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_NO_RETRY":
        raise RuntimeError("S189 paid execution is not permitted")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S189 frozen input drift: {spec['path']}")
    for spec in permit["frozen_artifacts"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S189 permitted artifact drift: {spec['path']}")
    return prereg


def render_relation_packet(item: dict[str, Any], store_item: dict[str, Any]) -> str:
    units = build_header_aware_evidence_units(
        item["excerpt"], fragment_number=1, candidate_id=item["item_id"]
    )
    by_id = {unit.unit_id: unit for unit in units}
    blocks = [
        "[ÍNDICE SEMÁNTICO DE NAVEGACIÓN — NO ES EVIDENCIA]",
        "Cada átomo siguiente debe verificarse contra sus SPANS FUENTE EXACTOS. "
        "Si el índice y el span difieren, manda siempre el span.",
    ]
    for relation in store_item["relations"]:
        unit_ids = list(relation["source_unit_ids"])
        if not unit_ids or not set(unit_ids).issubset(by_id):
            raise RuntimeError(f"S189 unknown source unit in {item['item_id']}")
        semantic = {
            key: relation[key]
            for key in (
                "relation_type",
                "subject",
                "predicate",
                "object",
                "conditions",
                "qualifiers",
            )
        }
        exact = "\n\n".join(
            f"[SPAN FUENTE EXACTO {unit_id}]\n{by_id[unit_id].content}"
            for unit_id in unit_ids
        )
        blocks.append(
            f"[ÁTOMO {relation['relation_id']} | navegación no probatoria]\n"
            f"{json.dumps(semantic, ensure_ascii=False, sort_keys=True)}\n{exact}"
        )
    return "\n\n---\n\n".join(blocks)


def runtime_row(item: dict[str, Any], store_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": item["question"],
        "context": [
            {
                "id": item["chunk_id"],
                "content": render_relation_packet(item, store_item),
                "product_model": item["product_model"],
                "source_file": item["source_file"],
                "section_title": item["section_title"],
                "content_type": "general",
                "similarity": 1.0,
                "page_number": item["page_number"],
                "document_revision": None,
                "document_revision_date": None,
                "has_diagram": False,
                "diagram_url": None,
            }
        ],
    }


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    from anthropic import Anthropic

    if DEFAULT_RECEIPTS.exists() or DEFAULT_RESULT.exists():
        raise RuntimeError("S189 checkpoint exists; retries are forbidden")
    key = (dotenv_values(env_file).get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("S189 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    source = {
        row["item_id"]: row
        for row in json.loads(SOURCE.read_text(encoding="utf-8"))["items"]
    }
    store = {
        row["item_id"]: row
        for row in json.loads(STORE.read_text(encoding="utf-8"))["items"]
    }
    jobs = []
    counted_total = 0
    for item_id in ITEM_IDS:
        row = runtime_row(source[item_id], store[item_id])
        system, prompt = build_prompt(row)
        counted = client.messages.count_tokens(
            model=prereg["model"]["id"],
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ).input_tokens
        counted_total += counted
        jobs.append((item_id, system, prompt, counted))
    prices = prereg["pricing_usd_per_million_tokens"]
    worst = (
        counted_total * prices["input"]
        + len(jobs) * prereg["model"]["max_output_tokens"] * prices["output"]
    ) / 1_000_000
    if worst > prereg["budget"]["internal_ceiling_usd"]:
        raise RuntimeError("S189 preflight exceeds internal budget")

    receipts = []
    actual = 0.0
    for item_id, system, prompt, counted in jobs:
        response = client.messages.create(
            model=prereg["model"]["id"],
            max_tokens=prereg["model"]["max_output_tokens"],
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", "") == "text"
        )
        usage = response.usage.model_dump(mode="json")
        call_cost = (
            usage.get("input_tokens", 0) * prices["input"]
            + usage.get("output_tokens", 0) * prices["output"]
        ) / 1_000_000
        actual += call_cost
        receipts.append(
            {
                "item_id": item_id,
                "response_id": response.id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "counted_input_tokens": counted,
                "usage": usage,
                "cost_usd": round(call_cost, 8),
                "stop_reason": response.stop_reason,
                "answer": answer,
            }
        )
    checkpoint = {
        "instrument": "s189_all_relation_writer_pilot_receipts_v1",
        "status": "PAID_CHECKPOINT_COMPLETE",
        "model": prereg["model"]["id"],
        "receipts": receipts,
        "cost": {
            "actual_usd": round(actual, 8),
            "worst_case_preflight_usd": round(worst, 8),
        },
    }
    write_json(DEFAULT_RECEIPTS, checkpoint)

    # Gold and baseline are intentionally loaded only after the paid checkpoint.
    gold = {
        row["item_id"]: row
        for row in json.loads(GOLD.read_text(encoding="utf-8"))["items"]
        if row.get("eligible")
    }
    baseline = {
        row["item_id"]: row
        for row in json.loads(BASELINE.read_text(encoding="utf-8"))["receipts"]
    }
    rows = []
    baseline_points = candidate_points = regressions = 0
    invalid = 0
    token_stops = 0
    for receipt in receipts:
        item_id = receipt["item_id"]
        base_answer = baseline[item_id]["answer"]
        answer = receipt["answer"]
        point_rows = []
        for point in gold[item_id]["answer_points"]:
            before = point_covered(base_answer, point)
            after = point_covered(answer, point)
            baseline_points += int(before)
            candidate_points += int(after)
            regressions += int(before and not after)
            point_rows.append(
                {"claim": point["claim"], "baseline": before, "candidate": after}
            )
        bad = invalid_citations(answer, 1)
        invalid += len(bad)
        token_stops += int(receipt["stop_reason"] == "max_tokens")
        rows.append(
            {
                "item_id": item_id,
                "points": point_rows,
                "invalid_citations": bad,
                "stop_reason": receipt["stop_reason"],
            }
        )
    gain = candidate_points - baseline_points
    checks = {
        "point_gain_min_3": gain >= 3,
        "regressions_zero": regressions == 0,
        "invalid_citations_zero": invalid == 0,
        "token_limit_stops_zero": token_stops == 0,
    }
    result = {
        "instrument": "s189_all_relation_writer_pilot_v1",
        "status": "GO_DEVELOPMENT_TO_FRESH_COHORT" if all(checks.values()) else "NO_GO_DEVELOPMENT",
        "population": {
            "questions": len(ITEM_IDS),
            "table": 2,
            "prose": 2,
            "answer_points": sum(len(gold[item_id]["answer_points"]) for item_id in ITEM_IDS),
            "target_questions_exposed": 0,
        },
        "measurement": {
            "baseline_points": baseline_points,
            "candidate_points": candidate_points,
            "point_gain": gain,
            "regressed_points": regressions,
            "invalid_citations": invalid,
            "token_limit_stops": token_stops,
        },
        "checks": checks,
        "rows": rows,
        "decision": {
            "same_cohort_retry": False,
            "target_probe": False,
            "runtime_or_production": False,
            "passing_action": "fresh_independent_cohort_and_fidelity_audit",
            "failing_action": "close_all_relation_writer_without_tuning",
            "facts_moved_to_ok": 0,
        },
        "cost": checkpoint["cost"],
    }
    write_json(DEFAULT_RESULT, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    args = parser.parse_args()
    prereg = validate_authorization(args.prereg, args.permit)
    result = execute(prereg, args.env_file)
    print(json.dumps({"status": result["status"], "measurement": result["measurement"], "cost": result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
