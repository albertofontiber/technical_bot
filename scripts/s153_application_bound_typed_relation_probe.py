#!/usr/bin/env python3
"""Application-bound per-chunk typed relation extraction and target probe."""
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
from scripts.s151_typed_relation_target_probe import file_sha, relation_covered_by_claims, stable_sha
from src.rag.typed_relations import (
    SELECTION_SYSTEM,
    TypedRelation,
    build_claim_selection_prompt,
    claim_selection_schema,
    validate_claim_selection,
)
from src.rag.typed_relations_v2 import (
    SINGLE_CHUNK_EXTRACTION_SYSTEM,
    single_chunk_extraction_schema,
    validate_single_chunk_extraction,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
DEFAULT_PREREG = ROOT / "evals/s153_application_bound_typed_relation_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s153_application_bound_typed_relation_execution_permit_v1.yaml"
DEFAULT_STORE = ROOT / "evals/s153_typed_relation_store_v1.json"
DEFAULT_EXTRACTION_RECEIPTS = ROOT / "evals/s153_typed_relation_extraction_receipts_v1.json"
DEFAULT_SELECTION_RECEIPTS = ROOT / "evals/s153_typed_relation_selection_receipts_v1.json"
DEFAULT_OUT = ROOT / "evals/s153_application_bound_typed_relation_probe_v1.json"
DEFAULT_ENV = Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env")
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S153 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED_FINAL":
        raise RuntimeError("S153 execution is not permitted")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S153 frozen input drift: {label}")
    for label, spec in permit["frozen_artifacts"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S153 permitted artifact drift: {label}")
    return prereg


def _usage_cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        usage.get("input_tokens", 0) * prices["input"]
        + usage.get("output_tokens", 0) * prices["output"]
    ) / 1_000_000


def _source_inventory(frozen: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    unique: dict[str, dict[str, Any]] = {}
    by_qid: dict[str, list[str]] = {}
    for qid in QIDS:
        ids = []
        for chunk in attested(frozen[qid]):
            chunk_id = str(chunk.get("id") or "")
            if not chunk_id:
                raise RuntimeError("S153 chunk without immutable ID")
            ids.append(chunk_id)
            unique.setdefault(
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
        by_qid[qid] = ids
    return sorted(unique.values(), key=lambda row: (str(row["source_file"]), row["chunk_id"])), by_qid


def _extraction_prompt(chunk: dict[str, Any]) -> str:
    return json.dumps(
        {
            key: chunk.get(key)
            for key in ("manufacturer", "product_model", "section_title", "content")
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def execute(
    prereg: dict[str, Any], env_file: Path, store_path: Path,
    extraction_receipts_path: Path, selection_receipts_path: Path,
) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    for path in (store_path, extraction_receipts_path, selection_receipts_path):
        if path.exists():
            raise RuntimeError("S153 checkpoint exists; retries are forbidden")
    secrets = dotenv_values(env_file)
    key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("S153 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in payload["rows"]}
    chunks, qid_chunk_ids = _source_inventory(frozen)
    model = prereg["model"]
    prices = prereg["pricing_usd_per_million_tokens"]
    budget = prereg["budget"]

    prepared = []
    extraction_counted = 0
    for ordinal, chunk in enumerate(chunks, 1):
        prompt = _extraction_prompt(chunk)
        counted = client.messages.count_tokens(
            model=model["id"], system=SINGLE_CHUNK_EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": single_chunk_extraction_schema()}},
        ).input_tokens
        extraction_counted += counted
        prepared.append((ordinal, chunk, prompt, counted))
    if extraction_counted > model["extraction_max_counted_input_tokens_total"]:
        raise RuntimeError("S153 extraction input exceeds cap")
    extraction_worst = (
        extraction_counted * prices["input"]
        + len(chunks) * model["extraction_max_output_tokens_per_call"] * prices["output"]
    ) / 1_000_000
    if extraction_worst >= budget["internal_ceiling_usd"]:
        raise RuntimeError("S153 extraction worst-case cost exceeds cap")

    relations: list[TypedRelation] = []
    receipts = []
    repairs = drops = 0
    extraction_cost = 0.0
    for ordinal, chunk, prompt, counted in prepared:
        response = client.messages.create(
            model=model["id"], max_tokens=model["extraction_max_output_tokens_per_call"],
            system=SINGLE_CHUNK_EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": single_chunk_extraction_schema()}},
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        usage = response.usage.model_dump(mode="json")
        cost = _usage_cost(usage, prices)
        extraction_cost += cost
        receipt = {
            "ordinal": ordinal, "chunk_id": chunk["chunk_id"], "response_id": response.id,
            "counted_input_tokens": counted, "usage": usage,
            "conservative_cost_usd": round(cost, 8), "validation": "PENDING",
            "raw_text": text, "raw_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        receipts.append(receipt)
        _write(extraction_receipts_path, {"instrument": "s153_typed_relation_extraction_receipts_v1", "status": "IN_PROGRESS", "model": model["id"], "receipts": receipts})
        try:
            extracted, stats = validate_single_chunk_extraction(
                json.loads(text), chunk_id=chunk["chunk_id"], content=chunk["content"]
            )
        except Exception:
            receipt["validation"] = "TERMINAL_INVALID_NO_RETRY"
            _write(extraction_receipts_path, {"instrument": "s153_typed_relation_extraction_receipts_v1", "status": "TERMINAL_INVALID_NO_RETRY", "model": model["id"], "receipts": receipts})
            raise
        receipt["validation"] = "VALIDATED"
        receipt["relations"] = len(extracted)
        relations.extend(extracted)
        repairs += stats["whitespace_only_repairs"]
        drops += stats["invalid_quote_drops"]
        _write(extraction_receipts_path, {"instrument": "s153_typed_relation_extraction_receipts_v1", "status": "IN_PROGRESS", "model": model["id"], "receipts": receipts})
    if len({row.claim_id for row in relations}) != len(relations):
        raise RuntimeError("S153 claim-ID collision")
    relations = sorted(relations, key=lambda row: (row.chunk_id, row.source_start, row.relation_type))
    store_body = {
        "instrument": "s153_typed_relation_store_v1", "status": "SOURCE_BOUND_LOCAL_PILOT",
        "chunks": len(chunks), "relations": [row.__dict__ for row in relations],
        "validation": {"whitespace_only_repairs": repairs, "invalid_quote_drops": drops},
    }
    store = {**store_body, "store_sha256": stable_sha(store_body)}
    _write(store_path, store)
    _write(extraction_receipts_path, {"instrument": "s153_typed_relation_extraction_receipts_v1", "status": "COMPLETE", "created_at": datetime.now(timezone.utc).isoformat(), "model": model["id"], "receipts": receipts})

    selections = []
    selection_counted = 0
    for qid in QIDS:
        allowed = set(qid_chunk_ids[qid])
        available = [claim for claim in relations if claim.chunk_id in allowed]
        prompt = build_claim_selection_prompt(frozen[qid]["question"], available)
        counted = client.messages.count_tokens(
            model=model["id"], system=SELECTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": claim_selection_schema()}},
        ).input_tokens
        selection_counted += counted
        expected = [obligation for obligation in plan_for(frozen[qid]) if obligation.kind in TARGET_KINDS[qid]]
        selections.append((qid, available, prompt, counted, expected))
    if selection_counted > model["selection_max_counted_input_tokens_total"]:
        raise RuntimeError("S153 selection input exceeds cap")
    total_worst = extraction_worst + (
        selection_counted * prices["input"]
        + len(QIDS) * model["selection_max_output_tokens_per_call"] * prices["output"]
    ) / 1_000_000
    if total_worst >= budget["internal_ceiling_usd"]:
        raise RuntimeError("S153 total worst-case cost exceeds cap")

    selection_receipts = []
    rows = []
    selection_cost = 0.0
    expected_total = covered_total = 0
    for qid, available, prompt, counted, expected in selections:
        response = client.messages.create(
            model=model["id"], max_tokens=model["selection_max_output_tokens_per_call"],
            system=SELECTION_SYSTEM, messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": claim_selection_schema()}},
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        usage = response.usage.model_dump(mode="json")
        cost = _usage_cost(usage, prices)
        selection_cost += cost
        receipt = {"qid": qid, "response_id": response.id, "counted_input_tokens": counted, "usage": usage, "conservative_cost_usd": round(cost, 8), "validation": "PENDING", "raw_text": text, "raw_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
        selection_receipts.append(receipt)
        _write(selection_receipts_path, {"instrument": "s153_typed_relation_selection_receipts_v1", "status": "IN_PROGRESS", "model": model["id"], "receipts": selection_receipts})
        try:
            intent, selected = validate_claim_selection(json.loads(text), available)
        except Exception:
            receipt["validation"] = "TERMINAL_INVALID_NO_RETRY"
            _write(selection_receipts_path, {"instrument": "s153_typed_relation_selection_receipts_v1", "status": "TERMINAL_INVALID_NO_RETRY", "model": model["id"], "receipts": selection_receipts})
            raise
        receipt["validation"] = "VALIDATED"
        relation_rows = [{"kind": obligation.kind, "anchors_covered": relation_covered_by_claims(obligation, selected)} for obligation in expected]
        expected_total += len(relation_rows)
        covered_total += sum(row["anchors_covered"] for row in relation_rows)
        rows.append({
            "qid": qid, "intent": intent, "available_claims": len(available),
            "selected_claims": len(selected), "expected_relations": len(relation_rows),
            "covered_relations": sum(row["anchors_covered"] for row in relation_rows),
            "relations": relation_rows,
            "selected_claim_receipts": [{"claim_id": claim.claim_id, "chunk_id": claim.chunk_id, "relation_type": claim.relation_type, "source_start": claim.source_start, "source_end": claim.source_end, "quote_sha256": claim.quote_sha256} for claim in selected],
        })
        _write(selection_receipts_path, {"instrument": "s153_typed_relation_selection_receipts_v1", "status": "IN_PROGRESS", "model": model["id"], "receipts": selection_receipts})
    _write(selection_receipts_path, {"instrument": "s153_typed_relation_selection_receipts_v1", "status": "COMPLETE", "created_at": datetime.now(timezone.utc).isoformat(), "model": model["id"], "receipts": selection_receipts})

    go = covered_total == expected_total == prereg["validation"]["target_relations"]
    body = {
        "instrument": "s153_application_bound_typed_relation_probe_v1",
        "status": "GO_TO_FRESH_TYPED_RELATION_COHORT" if go else "NO_GO",
        "result": {
            "source_chunks": len(chunks), "typed_relations": len(relations),
            "questions": len(rows), "target_relations": expected_total,
            "covered_relations": covered_total, "coverage_rate": round(covered_total / expected_total, 8),
            "selected_claims": sum(row["selected_claims"] for row in rows),
            "invalid_claim_ids": 0, "whitespace_only_repairs": repairs, "invalid_quote_drops": drops,
        },
        "cost": {
            "extraction_calls": len(chunks), "selection_calls": len(rows),
            "extraction_usd": round(extraction_cost, 8), "selection_usd": round(selection_cost, 8),
            "total_usd": round(extraction_cost + selection_cost, 8),
            "worst_case_preflight_usd": round(total_worst, 8), "internal_ceiling_usd": budget["internal_ceiling_usd"],
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
        raise RuntimeError("S153 paid execution requires --execute-paid")
    prereg = validate_authorization(args.prereg, args.permit)
    result = execute(prereg, args.env_file, args.store, args.extraction_receipts, args.selection_receipts)
    _write(args.out, result)
    print(json.dumps({"status": result["status"], **result["result"], **result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
