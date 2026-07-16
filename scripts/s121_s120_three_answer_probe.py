#!/usr/bin/env python3
"""Checkpointed three-answer probe for the S120 obligation contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
PREREG = ROOT / "evals/s121_s120_three_answer_probe_prereg_v1.yaml"
CHECKPOINT = ROOT / "evals/s121_s120_three_answer_probe_v1.partial.jsonl"
OUT = ROOT / "evals/s121_s120_three_answer_probe_v1.json"
QIDS = ("hp005", "hp009", "hp017")


def stable_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def fact_checks(qid: str, answer: str) -> list[dict]:
    folded = _fold(answer)
    if qid == "hp005":
        rows = [
            (
                "m0.hp005.output_selection.1",
                "circuito sirena" in folded
                and "activar" in folded
                and bool(re.search(r"seleccion\w*[^.\n]{0,100}(?:circuito|equipos? del lazo)", folded)),
            )
        ]
    elif qid == "hp009":
        rows = [
            (
                "m0.hp009.closed_loop_return.1",
                "lazo" in folded
                and bool(re.search(r"\bcerrad\w*\b", folded))
                and "retorno" in folded,
            ),
            (
                "m0.hp009.closed_loop_return.2",
                "inicio lazo" in folded
                and bool(re.search(r"(?<![a-z0-9])out(?![a-z0-9])", folded))
                and "retorno" in folded,
            ),
        ]
    elif qid == "hp017":
        rows = [
            (
                "m0.hp017.rule1.2",
                "regla 1" in folded
                and "cualquier entrada de alarma" in folded
                and "todas las sirenas" in folded
                and "por defecto" in folded
                and "elimin" in folded,
            )
        ]
    else:
        raise KeyError(qid)
    return [
        {"claim_id": claim_id, "deterministic_surface_present": present}
        for claim_id, present in rows
    ]


def _load_checkpoints() -> dict[str, dict]:
    rows = {}
    if not CHECKPOINT.exists():
        return rows
    for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["qid"] in rows:
            raise RuntimeError(f"duplicate checkpoint qid: {row['qid']}")
        rows[row["qid"]] = row
    return rows


def _append_checkpoint(row: dict) -> None:
    with CHECKPOINT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--execute-qids", default="")
    args = parser.parse_args()
    requested = tuple(
        item.strip() for item in args.execute_qids.split(",") if item.strip()
    )
    if len(requested) != len(set(requested)) or any(qid not in QIDS for qid in requested):
        raise RuntimeError(f"execute-qids must be a unique subset of {QIDS}")

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

    from src.config import LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.answer_planner import (
        ANSWER_PLANNER_CONTRACT_S120,
        build_answer_plan,
        render_answer_plan_guidance,
        validate_answer_plan,
    )
    from src.rag.generator import (
        RELEVANCE_THRESHOLD,
        _assemble_system,
        generate_answer,
    )
    from src.rag.post_rerank_coverage import (
        coverage_context_content,
        is_validated_coverage_chunk,
    )

    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if LLM_MODEL != prereg["scope"]["generator_model"] or LLM_MAX_TOKENS != 3500:
        raise RuntimeError("generator model or output budget drifted from preregistration")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {row["qid"]: row for row in freeze["rows"]}
    if not set(QIDS) <= set(frozen):
        raise RuntimeError("frozen context is missing an authorized qid")
    checkpoints = _load_checkpoints()
    source_receipts = {
        path: file_sha256(ROOT / path)
        for path in (
            "src/rag/answer_planner.py",
            "src/rag/answer_obligation_contract.py",
            "src/rag/generator.py",
            "scripts/s121_s120_three_answer_probe.py",
            "evals/s121_s120_three_answer_probe_prereg_v1.yaml",
        )
    }

    runtime = {}
    preflight = []
    for qid in QIDS:
        row = frozen[qid]
        relevant = [
            chunk
            for chunk in row["context"]
            if chunk.get("similarity", 0) >= RELEVANCE_THRESHOLD
            or is_validated_coverage_chunk(chunk)
        ]
        plan = build_answer_plan(
            row["question"],
            relevant,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S120,
        )
        kinds = [item.kind for item in plan]
        expected = prereg["expected_obligations"][qid]
        if kinds != expected:
            raise RuntimeError(
                f"planner contract drift for {qid}: expected {expected}, got {kinds}"
            )
        generation_contract = {
            "contract": "s121_s120_generation_contract_v1",
            "qid": qid,
            "question": row["question"],
            "context": row["context"],
            "relevant_context_ids": [chunk.get("id") for chunk in relevant],
            "rendered_context": [coverage_context_content(chunk) for chunk in relevant],
            "answer_plan": [item.to_dict() for item in plan],
            "answer_plan_guidance": render_answer_plan_guidance(plan),
            "system": _assemble_system(row["question"]),
            "model": LLM_MODEL,
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": 0,
            "source_receipts": source_receipts,
        }
        contract_sha256 = stable_sha256(generation_contract)
        checkpoint = checkpoints.get(qid)
        if checkpoint and checkpoint["generation_contract_sha256"] != contract_sha256:
            raise RuntimeError(f"stale checkpoint for {qid}; refusing repeat spend")
        citations = sorted({f"[F{item.fragment_number}]" for item in plan})
        preflight.append(
            {
                "qid": qid,
                "context_rows": len(relevant),
                "obligation_kinds": kinds,
                "obligation_citations": citations,
                "generation_contract_sha256": contract_sha256,
                "checkpoint_reusable": checkpoint is not None,
            }
        )
        runtime[qid] = (row, relevant, plan, citations, contract_sha256)

    fresh_this_run = []
    for qid in requested:
        if qid in checkpoints:
            continue
        row, relevant, plan, citations, contract_sha256 = runtime[qid]
        result = generate_answer(row["question"], relevant)
        answer = result["answer"]
        validation = validate_answer_plan(answer, plan)
        checkpoint = {
            "qid": qid,
            "generation_contract_sha256": contract_sha256,
            "model": LLM_MODEL,
            "max_output_tokens": LLM_MAX_TOKENS,
            "stop_reason": result.get("stop_reason"),
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            "obligation_citations_present": all(citation in answer for citation in citations),
            "local_validation": validation,
            "diagnostic_claims": fact_checks(qid, answer),
            "answer_planner": result.get("answer_planner"),
            "answer": answer,
            "manual_review_required": True,
        }
        _append_checkpoint(checkpoint)
        checkpoints[qid] = checkpoint
        fresh_this_run.append(qid)

    rows = []
    for pre in preflight:
        checkpoint = checkpoints.get(pre["qid"])
        rows.append({**pre, "executed": checkpoint is not None, **(checkpoint or {})})
    executed = [row for row in rows if row["executed"]]
    gate = {
        "authorized_qids": list(QIDS),
        "requested_this_run": list(requested),
        "fresh_calls_this_run": fresh_this_run,
        "successful_answer_checkpoints": len(executed),
        "remaining_answers": len(QIDS) - len(executed),
        "input_tokens": sum(row.get("input_tokens") or 0 for row in executed),
        "output_tokens": sum(row.get("output_tokens") or 0 for row in executed),
        "max_token_stops": sum(row.get("stop_reason") == "max_tokens" for row in executed),
        "locally_covered_qids": [
            row["qid"]
            for row in executed
            if row["local_validation"]["covered"] == row["local_validation"]["total"]
        ],
        "all_citations_present_qids": [
            row["qid"] for row in executed if row["obligation_citations_present"]
        ],
        "deterministic_claim_surfaces_present": sum(
            claim["deterministic_surface_present"]
            for row in executed
            for claim in row["diagnostic_claims"]
        ),
        "diagnostic_claims": sum(
            len(row["diagnostic_claims"]) for row in executed
        ),
        "retrieval_calls": 0,
        "reranker_calls": 0,
        "judge_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "facts_moved_to_ok": 0,
        "status": (
            "MEASURED_THREE_ANSWER_PROBE_PENDING_MANUAL_ADJUDICATION"
            if len(executed) == len(QIDS)
            else "PREFLIGHT_OR_PARTIAL_CHECKPOINT"
        ),
    }
    payload = {
        "instrument": "s121_s120_three_answer_probe_v1",
        "frozen_contexts_sha256": freeze["frozen_contexts_sha256"],
        "planner_contract": ANSWER_PLANNER_CONTRACT_S120,
        "source_receipts": source_receipts,
        "gate": gate,
        "rows": rows,
        "limitations": [
            "Local validation checks answer obligations, not final atomic correctness.",
            "No fact moves to OK before manual and adversarial adjudication.",
            "The probe changes synthesis only and makes no retrieval or rerank claim.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
