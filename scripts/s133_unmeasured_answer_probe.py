#!/usr/bin/env python3
"""Measure the seven exact answers behind the 27 S130 unmeasured claims.

The script is zero-call by default.  Paid generation is opt-in through
``--execute-qids`` and every completed answer is checkpointed immediately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
RECONCILIATION = ROOT / "evals/s130_unmeasured_answer_reconciliation_v1.yaml"
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
PREFLIGHT = ROOT / "evals/s113_full_regression_preflight_v1.json"
CHECKPOINT = ROOT / "evals/s133_unmeasured_answer_probe_v1.partial.jsonl"
OUT = ROOT / "evals/s133_unmeasured_answer_probe_v1.json"

RUNTIME_ENV = {
    "CHUNKS_TABLE": "chunks_v2",
    "LLM_MAX_TOKENS": "3500",
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "GENERATOR_SELECTION_BLOCK": "on",
    "GENERATOR_INCLUDE_CONTEXT": "0",
    "ANSWER_OBLIGATION_PLANNER": "guided",
    "POST_RERANK_COVERAGE": "on",
    "STRUCTURAL_NEIGHBOR_COVERAGE": "on",
    "CANONICAL_HYQ_COVERAGE": "on",
    "RERANK_POOL_COVERAGE": "on",
    "STRUCTURAL_CASCADE_COVERAGE": "on",
    "LOGICAL_RECORD_COVERAGE": "on",
}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_sha(payload: Any) -> str:
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _validate_reconciliation(payload: dict[str, Any]) -> list[dict[str, Any]]:
    reconciliation = payload.get("reconciliation", {})
    questions = payload.get("questions", [])
    qids = [row.get("qid") for row in questions]
    claim_ids = [claim for row in questions for claim in row.get("claim_ids", [])]
    if payload.get("status") != "LOCAL_RECONCILIATION_COMPLETE_GENERATION_NOT_EXECUTED":
        raise RuntimeError("unexpected S130 reconciliation status")
    if len(questions) != reconciliation.get("distinct_qids_requiring_exact_answers"):
        raise RuntimeError("S130 distinct-question count drift")
    if len(claim_ids) != reconciliation.get("unmeasured_claims"):
        raise RuntimeError("S130 unmeasured-claim count drift")
    if len(qids) != len(set(qids)) or len(claim_ids) != len(set(claim_ids)):
        raise RuntimeError("S130 qids or claim ids are not unique")
    for row in questions:
        if row.get("claim_count") != len(row.get("claim_ids", [])):
            raise RuntimeError(f"S130 claim count drift for {row.get('qid')}")
    return questions


def _verify_frozen_inputs(payload: dict[str, Any]) -> None:
    for name, receipt in payload.get("inputs", {}).items():
        path = ROOT / receipt["path"]
        if not path.is_file():
            raise RuntimeError(f"missing frozen S130 input {name}: {path}")
        actual = _file_sha256(path)
        if actual != receipt["sha256"]:
            raise RuntimeError(
                f"frozen S130 input drift for {name}: {receipt['sha256']} != {actual}"
            )


def _load_checkpoints(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return rows
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        qid = row.get("qid")
        if not qid or qid in rows:
            raise RuntimeError(f"invalid or duplicate checkpoint at line {line_number}")
        rows[qid] = row
    return rows


def _checkpoint_matches(
    row: dict[str, Any], expected: dict[str, Any]
) -> tuple[bool, list[str]]:
    fields = (
        "qid",
        "guided_prompt_sha256",
        "serving_context_sha256",
        "model",
        "max_output_tokens",
    )
    drift = [field for field in fields if row.get(field) != expected.get(field)]
    if not row.get("answer"):
        drift.append("answer")
    return not drift, drift


def _append_checkpoint(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def _parse_requested(raw: str, allowed: set[str]) -> set[str]:
    requested = {item.strip() for item in raw.split(",") if item.strip()}
    unknown = requested - allowed
    if unknown:
        raise RuntimeError(f"execute-qids outside S130 cohort: {sorted(unknown)}")
    return requested


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument(
        "--execute-qids",
        default="",
        help="Comma-separated S130 qids. Empty performs a zero-call preflight.",
    )
    args = parser.parse_args()

    reconciliation = _load_yaml(RECONCILIATION)
    questions = _validate_reconciliation(reconciliation)
    _verify_frozen_inputs(reconciliation)
    question_contracts = {row["qid"]: row for row in questions}
    requested = _parse_requested(args.execute_qids, set(question_contracts))

    if not args.env_file.is_file():
        raise RuntimeError(f"env file does not exist: {args.env_file}")
    load_dotenv(args.env_file, override=True)
    os.environ.update(RUNTIME_ENV)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from scripts.s113_full_regression_preflight import guided_prompt_contract
    from src.config import LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.answer_planner import build_answer_plan, render_answer_plan_guidance
    from src.rag.generator import _assemble_system, generate_answer
    from src.rag.post_rerank_coverage import coverage_context_content

    freeze = _load_json(FREEZE)
    frozen_by_qid = {row["qid"]: row for row in freeze["rows"]}
    preflight = _load_json(PREFLIGHT)
    manifest = {row["qid"]: row for row in preflight["rows"]}

    # Validate the complete cohort before the first possible paid call.
    runtime: dict[str, dict[str, Any]] = {}
    for qid, expected in question_contracts.items():
        frozen = frozen_by_qid.get(qid)
        pre = manifest.get(qid)
        if not frozen or not pre or not pre.get("requires_new_generator_call"):
            raise RuntimeError(f"{qid} is not an exact pending S113 answer")
        plan = build_answer_plan(frozen["question"], frozen["context"])
        contract = guided_prompt_contract(
            question=frozen["question"],
            context=frozen["context"],
            plan=plan,
            system=_assemble_system(frozen["question"]),
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            coverage_context_content=coverage_context_content,
            render_answer_plan_guidance=render_answer_plan_guidance,
        )
        prompt_sha256 = _stable_sha({"qid": qid, **contract})
        if prompt_sha256 != expected["guided_prompt_sha256"]:
            raise RuntimeError(f"guided prompt drift for {qid}")
        if prompt_sha256 != pre["guided_prompt_sha256"]:
            raise RuntimeError(f"S113 preflight prompt drift for {qid}")
        if frozen["serving_context_sha256"] != expected["serving_context_sha256"]:
            raise RuntimeError(f"serving context drift for {qid}")
        runtime[qid] = {
            "qid": qid,
            "guided_prompt_sha256": prompt_sha256,
            "serving_context_sha256": frozen["serving_context_sha256"],
            "model": LLM_MODEL,
            "max_output_tokens": LLM_MAX_TOKENS,
            "plan": plan,
            "frozen": frozen,
        }

    checkpoints = _load_checkpoints(CHECKPOINT)
    unexpected = set(checkpoints) - set(runtime)
    if unexpected:
        raise RuntimeError(f"checkpoint contains qids outside S130 cohort: {sorted(unexpected)}")
    for qid, checkpoint in checkpoints.items():
        matches, drift = _checkpoint_matches(checkpoint, runtime[qid])
        if not matches:
            raise RuntimeError(f"stale S133 checkpoint for {qid}: {drift}")

    fresh_qids: list[str] = []
    for qid in sorted(requested):
        if qid in checkpoints:
            continue
        if not os.getenv("ANTHROPIC_API_KEY", "").strip():
            raise RuntimeError("ANTHROPIC_API_KEY is required for paid execution")
        spec = runtime[qid]
        result = generate_answer(spec["frozen"]["question"], spec["frozen"]["context"])
        checkpoint = {
            "qid": qid,
            "guided_prompt_sha256": spec["guided_prompt_sha256"],
            "serving_context_sha256": spec["serving_context_sha256"],
            "model": spec["model"],
            "max_output_tokens": spec["max_output_tokens"],
            "stop_reason": result.get("stop_reason"),
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
            "answer_planner": result.get("answer_planner"),
            "answer": result["answer"],
        }
        _append_checkpoint(CHECKPOINT, checkpoint)
        checkpoints[qid] = checkpoint
        fresh_qids.append(qid)

    rows = []
    for qid in sorted(runtime):
        spec = runtime[qid]
        checkpoint = checkpoints.get(qid)
        rows.append(
            {
                "qid": qid,
                "claim_ids": question_contracts[qid]["claim_ids"],
                "executed": checkpoint is not None,
                "answer_source": "s133_exact_checkpoint" if checkpoint else None,
                "guided_prompt_sha256": spec["guided_prompt_sha256"],
                "serving_context_sha256": spec["serving_context_sha256"],
                "model": spec["model"],
                "max_output_tokens": spec["max_output_tokens"],
                "obligation_kinds": [item.kind for item in spec["plan"]],
                "stop_reason": checkpoint.get("stop_reason") if checkpoint else None,
                "input_tokens": checkpoint.get("input_tokens") if checkpoint else 0,
                "output_tokens": checkpoint.get("output_tokens") if checkpoint else 0,
                "answer_sha256": (
                    hashlib.sha256(checkpoint["answer"].encode("utf-8")).hexdigest()
                    if checkpoint
                    else None
                ),
                "answer": checkpoint.get("answer") if checkpoint else None,
            }
        )

    available_claims = sum(len(row["claim_ids"]) for row in rows if row["executed"])
    gate = {
        "questions": len(rows),
        "claims": sum(len(row["claim_ids"]) for row in rows),
        "answers_available": sum(row["executed"] for row in rows),
        "claims_with_answer_available": available_claims,
        "fresh_paid_generator_calls_this_run": len(fresh_qids),
        "fresh_qids_this_run": fresh_qids,
        "total_exact_checkpoints": len(checkpoints),
        "remaining_generator_calls": sum(not row["executed"] for row in rows),
        "total_input_tokens": sum(row["input_tokens"] or 0 for row in rows),
        "total_output_tokens": sum(row["output_tokens"] or 0 for row in rows),
        "max_token_stops": sum(row["stop_reason"] == "max_tokens" for row in rows),
        "retriever_calls": 0,
        "reranker_calls": 0,
        "judge_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "interpretation": (
            "EXACT_ANSWERS_COMPLETE_PENDING_FACT_ADJUDICATION"
            if all(row["executed"] for row in rows)
            else "ZERO_OR_PARTIAL_CALL_PREFLIGHT"
        ),
    }
    payload = {
        "instrument": "s133_unmeasured_answer_probe_v1",
        "source_reconciliation_sha256": _file_sha256(RECONCILIATION),
        "frozen_contexts_sha256": freeze["frozen_contexts_sha256"],
        "planner_mode": "guided",
        "gate": gate,
        "rows": rows,
        "limitations": [
            "This artifact measures exact bot answers, not fact outcomes.",
            "A separate fact-level adjudication is required before any KPI changes.",
            "Retrieval and rerank are frozen S113 inputs and are not re-executed here.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
