#!/usr/bin/env python3
"""Checkpointed answer regression over the 39-question S113 context freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
PREFLIGHT = ROOT / "evals/s113_full_regression_preflight_v1.json"
INCREMENTAL = ROOT / "evals/s112_incremental_answer_replay_v1.json"
GUIDED = ROOT / "evals/s112_guided_synthesis_probe_v1.json"
CHECKPOINT = ROOT / "evals/s113_full_answer_regression_v1.partial.jsonl"
OUT = ROOT / "evals/s113_full_answer_regression_v1.json"


def _load_checkpoints() -> dict[str, dict]:
    rows = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["qid"]] = row
    return rows


def _append_checkpoint(row: dict) -> None:
    with CHECKPOINT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument(
        "--execute-qids",
        default="",
        help="Comma-separated subset of preflight-required qids. Empty is zero-call.",
    )
    args = parser.parse_args()
    requested = {item.strip() for item in args.execute_qids.split(",") if item.strip()}

    load_dotenv(args.env_file, override=True)
    os.environ.update(
        {
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
    )
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from scripts.s113_full_regression_preflight import (
        guided_prompt_contract,
        stable_sha,
    )
    from src.config import LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.answer_planner import build_answer_plan, render_answer_plan_guidance
    from src.rag.generator import _assemble_system, generate_answer
    from src.rag.post_rerank_coverage import coverage_context_content

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    baseline_by_qid = {row["qid"]: row for row in baseline["per_gold"]}
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen_by_qid = {row["qid"]: row for row in freeze["rows"]}
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    manifest = {row["qid"]: row for row in preflight["rows"]}
    incremental = {
        row["qid"]: row
        for row in json.loads(INCREMENTAL.read_text(encoding="utf-8"))["rows"]
    }
    guided = {
        row["qid"]: row
        for row in json.loads(GUIDED.read_text(encoding="utf-8"))["rows"]
        if row.get("executed")
    }
    checkpoints = _load_checkpoints()
    required = {qid for qid, row in manifest.items() if row["requires_new_generator_call"]}
    if not requested <= required:
        raise RuntimeError(f"execute-qids outside required set: {sorted(requested - required)}")

    rows = []
    for qid in sorted(manifest):
        frozen = frozen_by_qid[qid]
        pre = manifest[qid]
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
        prompt_sha256 = stable_sha({"qid": qid, **contract})
        if prompt_sha256 != pre["guided_prompt_sha256"]:
            raise RuntimeError(
                f"preflight prompt drift for {qid}: "
                f"{pre['guided_prompt_sha256']} != {prompt_sha256}"
            )

        source = pre["reuse_source"]
        paid = None
        if source == "s100_bit_inert_no_plan":
            answer = baseline_by_qid[qid]["answer"]
        elif source == "s112_incremental_exact_context_no_plan":
            answer = incremental[qid]["answer"]
        elif source == "s112_guided_exact_prompt":
            answer = guided[qid]["answer"]
        else:
            paid = checkpoints.get(qid)
            if paid and paid.get("guided_prompt_sha256") != prompt_sha256:
                raise RuntimeError(f"stale paid checkpoint for {qid}; refusing repeat spend")
            if qid in requested and paid is None:
                result = generate_answer(frozen["question"], frozen["context"])
                paid = {
                    "qid": qid,
                    "guided_prompt_sha256": prompt_sha256,
                    "model": LLM_MODEL,
                    "max_output_tokens": LLM_MAX_TOKENS,
                    "stop_reason": result.get("stop_reason"),
                    "input_tokens": result.get("input_tokens"),
                    "output_tokens": result.get("output_tokens"),
                    "answer_planner": result.get("answer_planner"),
                    "answer": result["answer"],
                }
                _append_checkpoint(paid)
                checkpoints[qid] = paid
            answer = paid.get("answer") if paid else None
            source = "s113_fresh_checkpoint" if paid else None

        rows.append(
            {
                "qid": qid,
                "executed": answer is not None,
                "answer_source": source,
                "guided_prompt_sha256": prompt_sha256,
                "serving_context_sha256": frozen["serving_context_sha256"],
                "obligation_kinds": [item.kind for item in plan],
                "answer_sha256": (
                    hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else None
                ),
                "model": paid.get("model") if paid else None,
                "stop_reason": paid.get("stop_reason") if paid else None,
                "input_tokens": paid.get("input_tokens") if paid else 0,
                "output_tokens": paid.get("output_tokens") if paid else 0,
                "answer_planner": paid.get("answer_planner") if paid else None,
                "answer": answer,
            }
        )

    fresh = [row for row in rows if row["answer_source"] == "s113_fresh_checkpoint"]
    gate = {
        "questions": len(rows),
        "answers_available": sum(row["executed"] for row in rows),
        "preexisting_exact_reuses": sum(
            row["answer_source"] not in (None, "s113_fresh_checkpoint") for row in rows
        ),
        "fresh_paid_generator_calls": len(fresh),
        "remaining_generator_calls": sum(not row["executed"] for row in rows),
        "fresh_input_tokens": sum(row["input_tokens"] or 0 for row in fresh),
        "fresh_output_tokens": sum(row["output_tokens"] or 0 for row in fresh),
        "max_token_stops": sum(row["stop_reason"] == "max_tokens" for row in fresh),
        "reranker_calls": 0,
        "judge_calls": 0,
        "database_writes": 0,
        "interpretation": (
            "MEASURED_FULL_ANSWER_REPLAY_PENDING_FACT_ADJUDICATION"
            if all(row["executed"] for row in rows)
            else "PARTIAL_CHECKPOINTED_ANSWER_REPLAY"
        ),
    }
    payload = {
        "instrument": "s113_full_answer_regression_v1",
        "frozen_contexts_sha256": freeze["frozen_contexts_sha256"],
        "planner_mode": "guided",
        "gate": gate,
        "rows": rows,
        "limitations": [
            "This artifact measures answers only; fact-stage adjudication is a separate gate.",
            "Preexisting answers are reused only under the S113 exact preflight contract.",
            "No reranker or judge call is made here.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
