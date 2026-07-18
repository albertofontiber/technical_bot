#!/usr/bin/env python3
"""Run the sealed S216 non-target decomposed-synthesis screen once."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.decomposed_synthesis import (
    DECOMPOSITION_SYSTEM,
    assemble_blocks,
    decomposition_output_format,
    decomposition_payload,
    focused_query,
    invalid_citations,
    validate_decomposition,
)
from src.rag.omission_correction import point_covered


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
BASELINE = ROOT / "evals/s173_baseline_answer_receipts_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
PREREG = ROOT / "evals/s216_decomposed_synthesis_prereg_v1.yaml"
PERMIT = ROOT / "evals/s216_decomposed_synthesis_execution_permit_v1.yaml"
DECOMPOSITION_RECEIPTS = ROOT / "evals/s216_decomposition_receipts_v1.json"
BLOCK_RECEIPTS = ROOT / "evals/s216_answer_block_receipts_v1.json"
RESULT = ROOT / "evals/s216_decomposed_synthesis_screen_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)

RUNTIME_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2",
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "GENERATOR_SELECTION_BLOCK": "on",
    "GENERATOR_INCLUDE_CONTEXT": "0",
    "ANSWER_OBLIGATION_PLANNER": "guided",
    "LLM_MODEL": "claude-sonnet-4-6",
    "LLM_MAX_TOKENS": "1600",
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def runtime_chunks(item: dict[str, Any]) -> list[dict[str, Any]]:
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


class _CaptureMessages:
    def __init__(self, sink: list[dict[str, Any]]) -> None:
        self.sink = sink

    def create(self, **kwargs):
        self.sink.append(deepcopy(kwargs))
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="S216 CAPTURE [F1]")],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=0, output_tokens=0),
        )


def capture_generator_envelope(
    generator_module: Any, query: str, chunks: list[dict[str, Any]]
) -> dict[str, Any]:
    captured: list[dict[str, Any]] = []
    original = generator_module.anthropic.Anthropic
    generator_module.anthropic.Anthropic = lambda **_: SimpleNamespace(
        messages=_CaptureMessages(captured)
    )
    try:
        generator_module.generate_answer(query, deepcopy(chunks))
    finally:
        generator_module.anthropic.Anthropic = original
    if len(captured) != 1:
        raise RuntimeError("expected exactly one captured generator envelope")
    return captured[0]


def validate_authorization() -> dict[str, Any]:
    if not PERMIT.is_file():
        raise RuntimeError("S216 execution permit is missing")
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_FRONTIER_DESIGN_REVIEW":
        raise RuntimeError("S216 preregistration status drift")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise RuntimeError("S216 execution is not permitted")
    if file_sha(PREREG) != permit.get("preregistration_sha256"):
        raise RuntimeError("S216 preregistration drift")
    if prereg.get("runtime_flags") != RUNTIME_FLAGS:
        raise RuntimeError("S216 runtime flag contract drift")
    for receipt in permit.get("frozen_artifacts") or []:
        path = ROOT / receipt["path"]
        if not path.is_file() or file_sha(path) != receipt["sha256"]:
            raise RuntimeError(f"S216 permitted artifact drift: {receipt['path']}")
    return prereg


def _openai_cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        (usage.get("input_tokens") or 0) * prices["input"]
        + (usage.get("output_tokens") or 0) * prices["output"]
    ) / 1_000_000


def _anthropic_cost(row: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        (row.get("input_tokens") or 0) * prices["input"]
        + (row.get("output_tokens") or 0) * prices["output"]
    ) / 1_000_000


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values
    from openai import OpenAI

    if any(
        path.exists()
        for path in (DECOMPOSITION_RECEIPTS, BLOCK_RECEIPTS, RESULT)
    ):
        raise RuntimeError("S216 checkpoint exists; resume and retries are forbidden")
    secrets = dotenv_values(env_file)
    openai_key = (
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = (
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S216 provider API key missing")

    os.environ.update(RUNTIME_FLAGS)
    # Import only after the sealed runtime flags are active.
    from src.rag import generator

    openai = OpenAI(api_key=openai_key, max_retries=0)
    anthropic = Anthropic(api_key=anthropic_key, max_retries=0)
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    items = cohort["items"]
    if len(items) != 14 or any(
        key in item for item in items for key in ("answer_points", "exact_quote")
    ):
        raise RuntimeError("S216 generation cohort contains gold or has drifted")
    models = prereg["models"]
    prices = prereg["pricing_usd_per_million_tokens"]
    ceiling = float(prereg["budget"]["internal_ceiling_usd"])

    decomposition_rows: list[dict[str, Any]] = []
    focus_by_item: dict[str, list[dict[str, str]]] = {}
    actual_cost = 0.0
    decomposition_jobs: list[tuple[dict[str, Any], str, int]] = []
    decomposition_input_tokens = 0
    for item in items:
        prompt = decomposition_payload(item["question"])
        counted = openai.responses.input_tokens.count(
            model=models["decomposer"]["id"],
            reasoning={"effort": models["decomposer"]["reasoning_effort"]},
            instructions=DECOMPOSITION_SYSTEM,
            input=prompt,
            text=decomposition_output_format(),
        ).input_tokens
        decomposition_input_tokens += counted
        decomposition_jobs.append((item, prompt, counted))
    worst_decomposition_cost = (
        decomposition_input_tokens * prices["decomposer"]["input"]
        + len(decomposition_jobs)
        * models["decomposer"]["max_output_tokens"]
        * prices["decomposer"]["output"]
    ) / 1_000_000
    if worst_decomposition_cost >= ceiling:
        raise RuntimeError("S216 decomposition worst-case spend exceeds ceiling")

    for item, prompt, counted in decomposition_jobs:
        response = None
        raw = ""
        try:
            response = openai.responses.create(
                model=models["decomposer"]["id"],
                reasoning={"effort": models["decomposer"]["reasoning_effort"]},
                instructions=DECOMPOSITION_SYSTEM,
                input=prompt,
                text=decomposition_output_format(),
                max_output_tokens=models["decomposer"]["max_output_tokens"],
                store=False,
            )
            if response.status != "completed":
                raise RuntimeError("decomposition response was not completed")
            if response.model != models["decomposer"]["id"]:
                raise RuntimeError("decomposer model identity mismatch")
            raw = response.output_text
            focuses = validate_decomposition(json.loads(raw))
            usage = response.usage.model_dump(mode="json")
            call_cost = _openai_cost(usage, prices["decomposer"])
            actual_cost += call_cost
            focus_by_item[item["item_id"]] = focuses
            decomposition_rows.append(
                {
                    "item_id": item["item_id"],
                    "response_id": response.id,
                    "status": response.status,
                    "model": response.model,
                    "counted_input_tokens": counted,
                    "usage": usage,
                    "cost_usd": round(call_cost, 8),
                    "raw_output_sha256": hashlib.sha256(
                        raw.encode("utf-8")
                    ).hexdigest(),
                    "focuses": focuses,
                }
            )
        except Exception as exc:
            usage_obj = getattr(response, "usage", None)
            usage = usage_obj.model_dump(mode="json") if usage_obj else None
            call_cost = _openai_cost(usage or {}, prices["decomposer"])
            actual_cost += call_cost
            decomposition_rows.append(
                {
                    "item_id": item["item_id"],
                    "response_id": getattr(response, "id", None),
                    "status": "FAILED_NO_RETRY",
                    "provider_status": getattr(response, "status", None),
                    "counted_input_tokens": counted,
                    "usage": usage,
                    "cost_usd": round(call_cost, 8),
                    "raw_output_sha256": (
                        hashlib.sha256(raw.encode("utf-8")).hexdigest()
                        if raw
                        else None
                    ),
                    "error_type": type(exc).__name__,
                    "error_sha256": hashlib.sha256(
                        str(exc).encode("utf-8")
                    ).hexdigest(),
                }
            )
            write_json(
                DECOMPOSITION_RECEIPTS,
                {
                    "schema": "s216_decomposition_receipts_v1",
                    "status": "FAILED_NO_RETRY",
                    "rows": decomposition_rows,
                },
            )
            raise RuntimeError(
                f"S216 decomposition failed for {item['item_id']}; hard stop"
            ) from exc
        write_json(
            DECOMPOSITION_RECEIPTS,
            {
                "schema": "s216_decomposition_receipts_v1",
                "status": "IN_PROGRESS",
                "rows": decomposition_rows,
            },
        )
    write_json(
        DECOMPOSITION_RECEIPTS,
        {
            "schema": "s216_decomposition_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rows": decomposition_rows,
        },
    )

    answer_jobs: list[dict[str, Any]] = []
    answer_input_tokens = 0
    for item in items:
        chunks = runtime_chunks(item)
        for focus in focus_by_item[item["item_id"]]:
            query = focused_query(item["question"], focus["question"])
            envelope = capture_generator_envelope(generator, query, chunks)
            if (
                envelope.get("model") != models["writer"]["id"]
                or envelope.get("max_tokens")
                != models["writer"]["max_output_tokens"]
                or envelope.get("temperature") != 0
            ):
                raise RuntimeError("S216 writer envelope contract drift")
            counted = anthropic.messages.count_tokens(
                model=envelope["model"],
                system=envelope["system"],
                messages=envelope["messages"],
            ).input_tokens
            answer_input_tokens += counted
            answer_jobs.append(
                {
                    "item": item,
                    "chunks": chunks,
                    "focus": focus,
                    "query": query,
                    "counted_input_tokens": counted,
                    "envelope_sha256": stable_sha(envelope),
                }
            )
    if not 14 <= len(answer_jobs) <= 84:
        raise RuntimeError("S216 answer call cardinality is outside the sealed bound")
    worst_answer_cost = (
        answer_input_tokens * prices["writer"]["input"]
        + len(answer_jobs)
        * models["writer"]["max_output_tokens"]
        * prices["writer"]["output"]
    ) / 1_000_000
    if actual_cost + worst_answer_cost >= ceiling:
        raise RuntimeError("S216 post-decomposition worst-case spend exceeds ceiling")

    original_factory = generator.anthropic.Anthropic
    generator.anthropic.Anthropic = lambda **_: anthropic
    block_rows: list[dict[str, Any]] = []
    blocks_by_item: dict[str, list[dict[str, str]]] = {
        item["item_id"]: [] for item in items
    }
    try:
        for job in answer_jobs:
            item = job["item"]
            focus = job["focus"]
            # Re-capture immediately before the paid call and fail on drift.
            generator.anthropic.Anthropic = original_factory
            envelope = capture_generator_envelope(
                generator, job["query"], job["chunks"]
            )
            if stable_sha(envelope) != job["envelope_sha256"]:
                raise RuntimeError("S216 generator envelope drift")
            generator.anthropic.Anthropic = lambda **_: anthropic
            result = None
            answer = ""
            try:
                result = generator.generate_answer(
                    job["query"], deepcopy(job["chunks"])
                )
                if result.get("stop_reason") != "end_turn":
                    raise RuntimeError("writer response did not end_turn")
                answer = result["answer"]
                invalid = invalid_citations(answer, len(job["chunks"]))
                if invalid:
                    raise RuntimeError("writer returned an invalid fragment citation")
                cost_row = {
                    "input_tokens": result.get("input_tokens"),
                    "output_tokens": result.get("output_tokens"),
                }
                call_cost = _anthropic_cost(cost_row, prices["writer"])
                actual_cost += call_cost
            except Exception as exc:
                cost_row = {
                    "input_tokens": (result or {}).get("input_tokens"),
                    "output_tokens": (result or {}).get("output_tokens"),
                }
                call_cost = _anthropic_cost(cost_row, prices["writer"])
                actual_cost += call_cost
                block_rows.append(
                    {
                        "item_id": item["item_id"],
                        "focus_id": focus["focus_id"],
                        "focus_question": focus["question"],
                        "request_envelope_sha256": job["envelope_sha256"],
                        "counted_input_tokens": job["counted_input_tokens"],
                        "model": models["writer"]["id"],
                        "status": "FAILED_NO_RETRY",
                        "stop_reason": (result or {}).get("stop_reason"),
                        **cost_row,
                        "cost_usd": round(call_cost, 8),
                        "answer_sha256": (
                            hashlib.sha256(answer.encode("utf-8")).hexdigest()
                            if answer
                            else None
                        ),
                        "error_type": type(exc).__name__,
                        "error_sha256": hashlib.sha256(
                            str(exc).encode("utf-8")
                        ).hexdigest(),
                    }
                )
                write_json(
                    BLOCK_RECEIPTS,
                    {
                        "schema": "s216_answer_block_receipts_v1",
                        "status": "FAILED_NO_RETRY",
                        "rows": block_rows,
                    },
                )
                raise RuntimeError(
                    f"S216 writer failed for {item['item_id']} "
                    f"{focus['focus_id']}; hard stop"
                ) from exc
            blocks_by_item[item["item_id"]].append(
                {"focus_id": focus["focus_id"], "answer": answer}
            )
            block_rows.append(
                {
                    "item_id": item["item_id"],
                    "focus_id": focus["focus_id"],
                    "focus_question": focus["question"],
                    "request_envelope_sha256": job["envelope_sha256"],
                    "counted_input_tokens": job["counted_input_tokens"],
                    "model": models["writer"]["id"],
                    "stop_reason": result.get("stop_reason"),
                    **cost_row,
                    "cost_usd": round(call_cost, 8),
                    "answer": answer,
                    "answer_sha256": hashlib.sha256(
                        answer.encode("utf-8")
                    ).hexdigest(),
                }
            )
            write_json(
                BLOCK_RECEIPTS,
                {
                    "schema": "s216_answer_block_receipts_v1",
                    "status": "IN_PROGRESS",
                    "worst_case_usd": round(actual_cost + worst_answer_cost, 8),
                    "rows": block_rows,
                },
            )
    finally:
        generator.anthropic.Anthropic = original_factory

    candidates: dict[str, str] = {}
    assembly_receipts: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item["item_id"]
        candidate, receipt = assemble_blocks(
            item["question"], focus_by_item[item_id], blocks_by_item[item_id]
        )
        candidates[item_id] = candidate
        assembly_receipts[item_id] = receipt
    write_json(
        BLOCK_RECEIPTS,
        {
            "schema": "s216_answer_block_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rows": block_rows,
            "candidates": [
                {
                    "item_id": item["item_id"],
                    "answer": candidates[item["item_id"]],
                    "assembly": assembly_receipts[item["item_id"]],
                }
                for item in items
            ],
        },
    )

    # The scorer opens gold only after every model output is checkpointed.
    baseline_payload = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline_by = {row["item_id"]: row["answer"] for row in baseline_payload["receipts"]}
    gold_payload = json.loads(GOLD.read_text(encoding="utf-8"))
    gold_by = {
        row["item_id"]: row for row in gold_payload["items"] if row["eligible"]
    }
    score_rows: list[dict[str, Any]] = []
    baseline_points = candidate_points = 0
    baseline_complete = candidate_complete = regressions = 0
    for item in items:
        item_id = item["item_id"]
        points = gold_by[item_id]["answer_points"]
        before = [point_covered(baseline_by[item_id], point) for point in points]
        after = [point_covered(candidates[item_id], point) for point in points]
        regressed = sum(old and not new for old, new in zip(before, after))
        baseline_points += sum(before)
        candidate_points += sum(after)
        baseline_complete += int(all(before))
        candidate_complete += int(all(after))
        regressions += regressed
        score_rows.append(
            {
                "item_id": item_id,
                "stratum": item["stratum"],
                "focus_count": len(focus_by_item[item_id]),
                "answer_points": len(points),
                "baseline_points_covered": sum(before),
                "candidate_points_covered": sum(after),
                "baseline_complete": all(before),
                "candidate_complete": all(after),
                "regressed_points": regressed,
            }
        )
    point_gain = candidate_points - baseline_points
    complete_gain = candidate_complete - baseline_complete
    checks = {
        "all_items_scored": len(score_rows) == 14,
        "point_gain_gte_4": point_gain >= 4,
        "complete_question_gain_gte_2": complete_gain >= 2,
        "regressed_points_zero": regressions == 0,
        "all_decompositions_valid": len(decomposition_rows) == 14,
        "all_blocks_completed": len(block_rows) == len(answer_jobs),
        "all_focuses_assembled_once": all(
            row["all_focuses_assembled_once"]
            for row in assembly_receipts.values()
        ),
        "actual_cost_below_ceiling": actual_cost < ceiling,
    }
    passed = all(checks.values())
    body = {
        "schema": "s216_decomposed_synthesis_screen_v1",
        "status": "GO_TO_DUAL_SEMANTIC_REVIEW" if passed else "NO_GO",
        "population": {
            "items": 14,
            "manufacturers": 14,
            "answer_points": 37,
            "target_questions_opened": 0,
            "gold_loaded_after_generation_checkpoints": True,
        },
        "metrics": {
            "baseline_points_covered": baseline_points,
            "candidate_points_covered": candidate_points,
            "point_gain": point_gain,
            "baseline_questions_complete": baseline_complete,
            "candidate_questions_complete": candidate_complete,
            "complete_question_gain": complete_gain,
            "regressed_points": regressions,
            "decomposition_calls": len(decomposition_rows),
            "answer_calls": len(block_rows),
            "total_focuses": sum(len(rows) for rows in focus_by_item.values()),
        },
        "checks": checks,
        "rows": score_rows,
        "cost": {
            "actual_usd": round(actual_cost, 8),
            "internal_ceiling_usd": ceiling,
        },
        "decision": {
            "dual_semantic_review": passed,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    write_json(RESULT, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "ZERO_CALL",
                    "cohort_sha256": file_sha(COHORT),
                    "baseline_sha256": file_sha(BASELINE),
                    "gold_not_loaded": True,
                    "decomposition_schema": decomposition_output_format(),
                },
                ensure_ascii=False,
            )
        )
        return 0
    prereg = validate_authorization()
    print(json.dumps(execute(prereg, args.env_file), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
