#!/usr/bin/env python3
"""Per-chunk checkpointed typed-relation extraction and target probe."""
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

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s141_source_bound_technical_obligations import TARGET_KINDS, attested, plan_for
from scripts.s151_typed_relation_target_probe import (
    _public_batch,
    file_sha,
    relation_covered_by_claims,
    stable_sha,
)
from src.rag.typed_relations import (
    EXTRACTION_SYSTEM,
    SELECTION_SYSTEM,
    TypedRelation,
    build_claim_selection_prompt,
    claim_selection_schema,
    extraction_schema,
    validate_claim_selection,
    validate_extraction_value,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
DEFAULT_PREREG = ROOT / "evals/s152_per_chunk_typed_relation_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s152_per_chunk_typed_relation_execution_permit_v1.yaml"
DEFAULT_STORE = ROOT / "evals/s152_typed_relation_store_v1.json"
DEFAULT_EXTRACTION_RECEIPTS = ROOT / "evals/s152_typed_relation_extraction_receipts_v1.json"
DEFAULT_SELECTION_RECEIPTS = ROOT / "evals/s152_typed_relation_selection_receipts_v1.json"
DEFAULT_OUT = ROOT / "evals/s152_per_chunk_typed_relation_probe_v1.json"
DEFAULT_ENV = Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env")
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S152 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_FINAL":
        raise RuntimeError("S152 execution is not permitted")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S152 frozen input drift: {label}")
    for label, spec in permit["frozen_artifacts"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S152 permitted artifact drift: {label}")
    return prereg


def _cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        usage.get("input_tokens", 0) * prices["input"]
        + usage.get("output_tokens", 0) * prices["output"]
    ) / 1_000_000


def execute(
    prereg: dict[str, Any],
    env_file: Path,
    store_path: Path,
    extraction_receipts_path: Path,
    selection_receipts_path: Path,
) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    for path in (store_path, extraction_receipts_path, selection_receipts_path):
        if path.exists():
            raise RuntimeError("S152 checkpoint exists; retries are forbidden")
    secrets = dotenv_values(env_file)
    key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("S152 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in freeze["rows"]}
    model = prereg["model"]
    prices = prereg["pricing_usd_per_million_tokens"]
    budget = prereg["budget"]

    unique_chunks: dict[str, dict[str, Any]] = {}
    qid_chunk_ids: dict[str, list[str]] = {}
    for qid in QIDS:
        ids = []
        for chunk in attested(frozen[qid]):
            chunk_id = str(chunk.get("id") or "")
            if not chunk_id:
                raise RuntimeError("S152 chunk without immutable ID")
            ids.append(chunk_id)
            unique_chunks.setdefault(
                chunk_id,
                {
                    "chunk_id": chunk_id,
                    "content": str(chunk.get("content") or ""),
                    "manufacturer": chunk.get("manufacturer"),
                    "product_model": chunk.get("product_model"),
                    "section_title": chunk.get("section_title"),
                    "source_file": chunk.get("source_file"),
                },
            )
        qid_chunk_ids[qid] = ids
    ordered = sorted(unique_chunks.values(), key=lambda row: (str(row["source_file"]), row["chunk_id"]))

    prepared_extractions = []
    extraction_counted = 0
    for index, chunk in enumerate(ordered, 1):
        prompt = json.dumps(_public_batch([chunk]), ensure_ascii=False, sort_keys=True)
        counted = client.messages.count_tokens(
            model=model["id"],
            system=EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": extraction_schema()}},
        ).input_tokens
        extraction_counted += counted
        prepared_extractions.append((index, chunk, prompt, counted))
    if extraction_counted > model["extraction_max_counted_input_tokens_total"]:
        raise RuntimeError("S152 extraction input exceeds cap")
    extraction_worst = (
        extraction_counted * prices["input"]
        + len(ordered) * model["extraction_max_output_tokens_per_call"] * prices["output"]
    ) / 1_000_000
    if extraction_worst >= budget["internal_ceiling_usd"]:
        raise RuntimeError("S152 extraction worst-case cost exceeds cap")

    receipts = []
    relations: list[TypedRelation] = []
    repairs = drops = 0
    extraction_cost = 0.0
    for index, chunk, prompt, counted in prepared_extractions:
        response = client.messages.create(
            model=model["id"],
            max_tokens=model["extraction_max_output_tokens_per_call"],
            system=EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": extraction_schema()}},
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        usage = response.usage.model_dump(mode="json")
        call_cost = _cost(usage, prices)
        extraction_cost += call_cost
        receipt = {
            "ordinal": index,
            "chunk_id": chunk["chunk_id"],
            "response_id": response.id,
            "counted_input_tokens": counted,
            "usage": usage,
            "conservative_cost_usd": round(call_cost, 8),
            "validation": "PENDING",
            "raw_text": text,
            "raw_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        receipts.append(receipt)
        _write(
            extraction_receipts_path,
            {"instrument": "s152_typed_relation_extraction_receipts_v1", "status": "IN_PROGRESS", "model": model["id"], "receipts": receipts},
        )
        try:
            chunk_relations, stats = validate_extraction_value(json.loads(text), [chunk])
        except Exception:
            receipt["validation"] = "TERMINAL_INVALID_NO_RETRY"
            _write(
                extraction_receipts_path,
                {"instrument": "s152_typed_relation_extraction_receipts_v1", "status": "TERMINAL_INVALID_NO_RETRY", "model": model["id"], "receipts": receipts},
            )
            raise
        receipt["validation"] = "VALIDATED"
        receipt["relations"] = len(chunk_relations)
        relations.extend(chunk_relations)
        repairs += stats["whitespace_only_repairs"]
        drops += stats["invalid_quote_drops"]
        _write(
            extraction_receipts_path,
            {"instrument": "s152_typed_relation_extraction_receipts_v1", "status": "IN_PROGRESS", "model": model["id"], "receipts": receipts},
        )
    if len({row.claim_id for row in relations}) != len(relations):
        raise RuntimeError("S152 claim-ID collision")
    relations = sorted(relations, key=lambda row: (row.chunk_id, row.source_start, row.relation_type))
    store_body = {
        "instrument": "s152_typed_relation_store_v1",
        "status": "SOURCE_BOUND_LOCAL_PILOT",
        "chunks": len(ordered),
        "relations": [row.__dict__ for row in relations],
        "validation": {"whitespace_only_repairs": repairs, "invalid_quote_drops": drops},
    }
    store = {**store_body, "store_sha256": stable_sha(store_body)}
    _write(store_path, store)
    _write(
        extraction_receipts_path,
        {"instrument": "s152_typed_relation_extraction_receipts_v1", "status": "COMPLETE", "created_at": datetime.now(timezone.utc).isoformat(), "model": model["id"], "receipts": receipts},
    )

    prepared_selections = []
    selection_counted = 0
    for qid in QIDS:
        allowed = set(qid_chunk_ids[qid])
        available = [claim for claim in relations if claim.chunk_id in allowed]
        prompt = build_claim_selection_prompt(frozen[qid]["question"], available)
        counted = client.messages.count_tokens(
            model=model["id"],
            system=SELECTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": claim_selection_schema()}},
        ).input_tokens
        selection_counted += counted
        expected = [obligation for obligation in plan_for(frozen[qid]) if obligation.kind in TARGET_KINDS[qid]]
        prepared_selections.append((qid, available, prompt, counted, expected))
    if selection_counted > model["selection_max_counted_input_tokens_total"]:
        raise RuntimeError("S152 selection input exceeds cap")
    total_worst = extraction_worst + (
        selection_counted * prices["input"]
        + len(QIDS) * model["selection_max_output_tokens_per_call"] * prices["output"]
    ) / 1_000_000
    if total_worst >= budget["internal_ceiling_usd"]:
        raise RuntimeError("S152 total worst-case cost exceeds cap")

    selection_receipts = []
    rows = []
    selection_cost = 0.0
    total_expected = total_covered = 0
    for qid, available, prompt, counted, expected in prepared_selections:
        response = client.messages.create(
            model=model["id"],
            max_tokens=model["selection_max_output_tokens_per_call"],
            system=SELECTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": claim_selection_schema()}},
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        usage = response.usage.model_dump(mode="json")
        call_cost = _cost(usage, prices)
        selection_cost += call_cost
        receipt = {"qid": qid, "response_id": response.id, "counted_input_tokens": counted, "usage": usage, "conservative_cost_usd": round(call_cost, 8), "validation": "PENDING", "raw_text": text, "raw_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
        selection_receipts.append(receipt)
        _write(selection_receipts_path, {"instrument": "s152_typed_relation_selection_receipts_v1", "status": "IN_PROGRESS", "model": model["id"], "receipts": selection_receipts})
        try:
            intent, selected = validate_claim_selection(json.loads(text), available)
        except Exception:
            receipt["validation"] = "TERMINAL_INVALID_NO_RETRY"
            _write(selection_receipts_path, {"instrument": "s152_typed_relation_selection_receipts_v1", "status": "TERMINAL_INVALID_NO_RETRY", "model": model["id"], "receipts": selection_receipts})
            raise
        receipt["validation"] = "VALIDATED"
        relation_rows = [{"kind": obligation.kind, "anchors_covered": relation_covered_by_claims(obligation, selected)} for obligation in expected]
        total_expected += len(relation_rows)
        total_covered += sum(row["anchors_covered"] for row in relation_rows)
        rows.append(
            {
                "qid": qid,
                "intent": intent,
                "available_claims": len(available),
                "selected_claims": len(selected),
                "expected_relations": len(relation_rows),
                "covered_relations": sum(row["anchors_covered"] for row in relation_rows),
                "relations": relation_rows,
                "selected_claim_receipts": [{"claim_id": claim.claim_id, "chunk_id": claim.chunk_id, "relation_type": claim.relation_type, "source_start": claim.source_start, "source_end": claim.source_end, "quote_sha256": claim.quote_sha256} for claim in selected],
            }
        )
        _write(selection_receipts_path, {"instrument": "s152_typed_relation_selection_receipts_v1", "status": "IN_PROGRESS", "model": model["id"], "receipts": selection_receipts})
    _write(selection_receipts_path, {"instrument": "s152_typed_relation_selection_receipts_v1", "status": "COMPLETE", "created_at": datetime.now(timezone.utc).isoformat(), "model": model["id"], "receipts": selection_receipts})

    go = total_covered == total_expected == prereg["validation"]["target_relations"]
    body = {
        "instrument": "s152_per_chunk_typed_relation_probe_v1",
        "status": "GO_TO_FRESH_TYPED_RELATION_COHORT" if go else "NO_GO",
        "result": {
            "source_chunks": len(ordered),
            "typed_relations": len(relations),
            "questions": len(rows),
            "target_relations": total_expected,
            "covered_relations": total_covered,
            "coverage_rate": round(total_covered / total_expected, 8),
            "selected_claims": sum(row["selected_claims"] for row in rows),
            "invalid_claim_ids": 0,
            "whitespace_only_repairs": repairs,
            "invalid_quote_drops": drops,
        },
        "cost": {
            "extraction_calls": len(ordered),
            "selection_calls": len(rows),
            "extraction_usd": round(extraction_cost, 8),
            "selection_usd": round(selection_cost, 8),
            "total_usd": round(extraction_cost + selection_cost, 8),
            "worst_case_preflight_usd": round(total_worst, 8),
            "internal_ceiling_usd": budget["internal_ceiling_usd"],
        },
        "store": {"path": str(store_path.relative_to(ROOT)).replace("\\", "/"), "sha256": file_sha(store_path), "store_sha256": store["store_sha256"]},
        "rows": rows,
        "decision": {"fresh_typed_relation_cohort": "GO" if go else "NO_GO", "four_answer_probe": "NO_GO", "production": "NO_GO", "facts_moved_to_ok": 0},
    }
    return {**body, "result_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-paid", action="store_true")
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--extraction-receipts", type=Path, default=DEFAULT_EXTRACTION_RECEIPTS)
    parser.add_argument("--selection-receipts", type=Path, default=DEFAULT_SELECTION_RECEIPTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute_paid:
        raise RuntimeError("S152 paid execution requires --execute-paid")
    prereg = validate_authorization(args.prereg, args.permit)
    result = execute(prereg, args.env_file, args.store, args.extraction_receipts, args.selection_receipts)
    _write(args.out, result)
    print(json.dumps({"status": result["status"], **result["result"], **result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
