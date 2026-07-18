#!/usr/bin/env python3
"""Execute the sealed S216 contemporary 2x2 synthesis screen once."""
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
    has_source_citation,
    invalid_citations,
    validate_decomposition,
)


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evals/s216_synthesis_screen_packet_v1.json"
PREREG = ROOT / "evals/s216_decomposed_synthesis_prereg_v1.yaml"
PERMIT = ROOT / "evals/s216_decomposed_synthesis_execution_permit_v1.yaml"
DECOMPOSITION_RECEIPTS = ROOT / "evals/s216_decomposition_receipts_v1.json"
GENERATION_RECEIPTS = ROOT / "evals/s216_generation_receipts_v1.json"
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
REPLICATES = (1, 2)
AGGREGATE_OUTPUT_BUDGET = 1600


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
    generator_module: Any,
    query: str,
    chunks: list[dict[str, Any]],
    max_tokens: int,
) -> dict[str, Any]:
    captured: list[dict[str, Any]] = []
    original_factory = generator_module.anthropic.Anthropic
    original_max = generator_module.LLM_MAX_TOKENS
    generator_module.LLM_MAX_TOKENS = max_tokens
    generator_module.anthropic.Anthropic = lambda **_: SimpleNamespace(
        messages=_CaptureMessages(captured)
    )
    try:
        generator_module.generate_answer(query, deepcopy(chunks))
    finally:
        generator_module.anthropic.Anthropic = original_factory
        generator_module.LLM_MAX_TOKENS = original_max
    if len(captured) != 1:
        raise RuntimeError("expected exactly one captured generator envelope")
    return captured[0]


def _artifact_set(rows: list[dict[str, str]]) -> set[tuple[str, str]]:
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("S216 frozen artifact set is empty")
    output: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise RuntimeError("S216 frozen artifact receipt shape invalid")
        output.add((row["path"], row["sha256"]))
    if len(output) != len(rows):
        raise RuntimeError("S216 frozen artifact receipts contain duplicates")
    return output


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
    expected = _artifact_set(list(prereg["frozen_inputs"].values()))
    observed = _artifact_set(permit.get("frozen_artifacts"))
    if observed != expected:
        raise RuntimeError("S216 permit does not freeze every preregistered artifact")
    for relative, expected_sha in observed:
        path = ROOT / relative
        if not path.is_file() or file_sha(path) != expected_sha:
            raise RuntimeError(f"S216 permitted artifact drift: {relative}")
    gate = permit.get("frontier_design_gate") or {}
    gate_path = ROOT / str(gate.get("path") or "")
    if (
        gate.get("status") != "PASS_DUAL_FRONTIER"
        or not gate_path.is_file()
        or file_sha(gate_path) != gate.get("sha256")
    ):
        raise RuntimeError("S216 dual Frontier gate is absent or not PASS")
    return prereg


def _cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        (usage.get("input_tokens") or 0) * prices["input"]
        + (usage.get("output_tokens") or 0) * prices["output"]
    ) / 1_000_000


def _write_decomposition(rows: list[dict[str, Any]], status: str) -> None:
    write_json(
        DECOMPOSITION_RECEIPTS,
        {
            "schema": "s216_decomposition_receipts_v2",
            "status": status,
            "rows": rows,
        },
    )


def _write_generation(
    calls: list[dict[str, Any]],
    status: str,
    *,
    answers: list[dict[str, Any]] | None = None,
) -> None:
    body: dict[str, Any] = {
        "schema": "s216_generation_receipts_v2",
        "status": status,
        "calls": calls,
    }
    if answers is not None:
        body["answers"] = answers
    write_json(GENERATION_RECEIPTS, body)


def _decompose(
    client: Any,
    rows: list[dict[str, Any]],
    model: dict[str, Any],
    prices: dict[str, float],
    ceiling: float,
) -> tuple[dict[str, list[dict[str, str]]], float, list[dict[str, Any]]]:
    prepared: list[tuple[dict[str, Any], str, int]] = []
    counted_total = 0
    for row in rows:
        prompt = decomposition_payload(row["question"])
        counted = client.responses.input_tokens.count(
            model=model["id"],
            reasoning={"effort": model["reasoning_effort"]},
            instructions=DECOMPOSITION_SYSTEM,
            input=prompt,
            text=decomposition_output_format(),
        ).input_tokens
        counted_total += counted
        prepared.append((row, prompt, counted))
    worst = (
        counted_total * prices["input"]
        + len(prepared) * model["max_output_tokens"] * prices["output"]
    ) / 1_000_000
    if worst >= ceiling:
        raise RuntimeError("S216 decomposition worst-case spend exceeds ceiling")

    receipts: list[dict[str, Any]] = []
    plans: dict[str, list[dict[str, str]]] = {}
    actual = 0.0
    for row, prompt, counted in prepared:
        response = None
        raw = ""
        try:
            response = client.responses.create(
                model=model["id"],
                reasoning={"effort": model["reasoning_effort"]},
                instructions=DECOMPOSITION_SYSTEM,
                input=prompt,
                text=decomposition_output_format(),
                max_output_tokens=model["max_output_tokens"],
                store=False,
            )
            if response.status != "completed" or response.model != model["id"]:
                raise RuntimeError("decomposer completion or model identity mismatch")
            raw = response.output_text
            focuses = validate_decomposition(json.loads(raw))
            usage = response.usage.model_dump(mode="json")
            call_cost = _cost(usage, prices)
            actual += call_cost
            plans[row["item_id"]] = focuses
            receipts.append(
                {
                    "item_id": row["item_id"],
                    "response_id": response.id,
                    "status": "completed",
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
            usage = usage_obj.model_dump(mode="json") if usage_obj else {}
            call_cost = _cost(usage, prices)
            actual += call_cost
            receipts.append(
                {
                    "item_id": row["item_id"],
                    "response_id": getattr(response, "id", None),
                    "status": "FAILED_NO_RETRY",
                    "provider_status": getattr(response, "status", None),
                    "counted_input_tokens": counted,
                    "usage": usage or None,
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
            _write_decomposition(receipts, "FAILED_NO_RETRY")
            raise RuntimeError(
                f"S216 decomposition failed for {row['item_id']}; hard stop"
            ) from exc
        _write_decomposition(receipts, "IN_PROGRESS")
    _write_decomposition(receipts, "COMPLETE")
    return plans, actual, receipts


def _writer_schedule(
    rows: list[dict[str, Any]], plans: dict[str, list[dict[str, str]]]
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for row in rows:
        focuses = plans[row["item_id"]]
        focus_budget = AGGREGATE_OUTPUT_BUDGET // len(focuses)
        if focus_budget * len(focuses) > AGGREGATE_OUTPUT_BUDGET:
            raise RuntimeError("S216 treatment output budget exceeds control")
        # Symmetric ordering bounds within-item provider drift.
        jobs.append(
            {
                "row": row,
                "arm": "control",
                "replicate": 1,
                "focus": None,
                "query": row["question"],
                "max_tokens": AGGREGATE_OUTPUT_BUDGET,
            }
        )
        for replicate in REPLICATES:
            for focus in focuses:
                jobs.append(
                    {
                        "row": row,
                        "arm": "treatment",
                        "replicate": replicate,
                        "focus": focus,
                        "query": focused_query(row["question"], focus["question"]),
                        "max_tokens": focus_budget,
                    }
                )
        jobs.append(
            {
                "row": row,
                "arm": "control",
                "replicate": 2,
                "focus": None,
                "query": row["question"],
                "max_tokens": AGGREGATE_OUTPUT_BUDGET,
            }
        )
    return jobs


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values
    from openai import OpenAI

    if DECOMPOSITION_RECEIPTS.exists() or GENERATION_RECEIPTS.exists():
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
    from src.rag import generator

    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    rows = packet["rows"]
    if (
        packet.get("status") != "FROZEN_SCORE_FREE_GENERATION_PACKET"
        or len(rows) != 49
        or packet["population"].get("target_questions") != 0
        or any(
            key in row
            for row in rows
            for key in ("facts", "answer_points", "gold", "answer")
        )
    ):
        raise RuntimeError("S216 generation packet is not score-free or has drifted")

    models = prereg["models"]
    prices = prereg["pricing_usd_per_million_tokens"]
    ceiling = float(prereg["budget"]["generation_and_local_screen_ceiling_usd"])
    openai = OpenAI(api_key=openai_key, max_retries=0)
    anthropic = Anthropic(api_key=anthropic_key, max_retries=0)
    plans, actual, decomposition_rows = _decompose(
        openai,
        rows,
        models["decomposer"],
        prices["decomposer"],
        ceiling,
    )

    schedule = _writer_schedule(rows, plans)
    if not 196 <= len(schedule) <= 686:
        raise RuntimeError("S216 writer call cardinality outside sealed bounds")
    prepared: list[dict[str, Any]] = []
    counted_total = 0
    for job in schedule:
        envelope = capture_generator_envelope(
            generator,
            job["query"],
            job["row"]["context"],
            job["max_tokens"],
        )
        if (
            envelope.get("model") != models["writer"]["id"]
            or envelope.get("max_tokens") != job["max_tokens"]
            or envelope.get("temperature") != 0
        ):
            raise RuntimeError("S216 writer envelope contract drift")
        counted = anthropic.messages.count_tokens(
            model=envelope["model"],
            system=envelope["system"],
            messages=envelope["messages"],
        ).input_tokens
        counted_total += counted
        prepared.append(
            {
                **job,
                "counted_input_tokens": counted,
                "envelope_sha256": stable_sha(envelope),
            }
        )
    worst_writer = (
        counted_total * prices["writer"]["input"]
        + sum(job["max_tokens"] for job in prepared) * prices["writer"]["output"]
    ) / 1_000_000
    if actual + worst_writer >= ceiling:
        raise RuntimeError("S216 writer worst-case spend exceeds ceiling")

    calls: list[dict[str, Any]] = []
    answers: dict[tuple[str, str, int], list[dict[str, str]]] = {}
    original_factory = generator.anthropic.Anthropic
    original_max = generator.LLM_MAX_TOKENS
    try:
        for job in prepared:
            row = job["row"]
            focus = job["focus"]
            call_id = (
                f"{row['item_id']}:{job['arm']}:{job['replicate']}:"
                + (focus["focus_id"] if focus else "whole")
            )
            generator.anthropic.Anthropic = original_factory
            envelope = capture_generator_envelope(
                generator,
                job["query"],
                row["context"],
                job["max_tokens"],
            )
            if stable_sha(envelope) != job["envelope_sha256"]:
                failure = {
                    "call_id": call_id,
                    "status": "FAILED_PRECALL_ENVELOPE_DRIFT",
                }
                calls.append(failure)
                _write_generation(calls, "FAILED_NO_RETRY")
                raise RuntimeError("S216 generator envelope drift")
            generator.LLM_MAX_TOKENS = job["max_tokens"]
            generator.anthropic.Anthropic = lambda **_: anthropic
            result = None
            answer = ""
            try:
                result = generator.generate_answer(
                    job["query"], deepcopy(row["context"])
                )
                if result.get("stop_reason") != "end_turn":
                    raise RuntimeError("writer response did not end_turn")
                answer = result["answer"]
                if not has_source_citation(answer):
                    raise RuntimeError("writer answer has no source citation")
                invalid = invalid_citations(answer, len(row["context"]))
                if invalid:
                    raise RuntimeError("writer answer has out-of-range citation")
                usage = {
                    "input_tokens": result.get("input_tokens"),
                    "output_tokens": result.get("output_tokens"),
                }
                call_cost = _cost(usage, prices["writer"])
                actual += call_cost
                receipt = {
                    "call_id": call_id,
                    "status": "completed",
                    "item_id": row["item_id"],
                    "role": row["role"],
                    "arm": job["arm"],
                    "replicate": job["replicate"],
                    "focus_id": focus["focus_id"] if focus else None,
                    "focus_question_sha256": (
                        hashlib.sha256(focus["question"].encode("utf-8")).hexdigest()
                        if focus
                        else None
                    ),
                    "request_envelope_sha256": job["envelope_sha256"],
                    "counted_input_tokens": job["counted_input_tokens"],
                    "max_tokens": job["max_tokens"],
                    "stop_reason": result.get("stop_reason"),
                    **usage,
                    "cost_usd": round(call_cost, 8),
                    "answer": answer,
                    "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
                }
                calls.append(receipt)
                key = (row["item_id"], job["arm"], job["replicate"])
                answers.setdefault(key, []).append(
                    {
                        "focus_id": focus["focus_id"] if focus else "whole",
                        "answer": answer,
                    }
                )
            except Exception as exc:
                usage = {
                    "input_tokens": (result or {}).get("input_tokens"),
                    "output_tokens": (result or {}).get("output_tokens"),
                }
                call_cost = _cost(usage, prices["writer"])
                actual += call_cost
                calls.append(
                    {
                        "call_id": call_id,
                        "status": "FAILED_NO_RETRY",
                        "item_id": row["item_id"],
                        "arm": job["arm"],
                        "replicate": job["replicate"],
                        "focus_id": focus["focus_id"] if focus else None,
                        "request_envelope_sha256": job["envelope_sha256"],
                        "stop_reason": (result or {}).get("stop_reason"),
                        **usage,
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
                _write_generation(calls, "FAILED_NO_RETRY")
                raise RuntimeError(f"S216 writer failed at {call_id}; hard stop") from exc
            _write_generation(calls, "IN_PROGRESS")
    finally:
        generator.anthropic.Anthropic = original_factory
        generator.LLM_MAX_TOKENS = original_max

    final_answers: list[dict[str, Any]] = []
    for row in rows:
        item_id = row["item_id"]
        focuses = plans[item_id]
        for replicate in REPLICATES:
            control_blocks = answers[(item_id, "control", replicate)]
            if len(control_blocks) != 1:
                raise RuntimeError("S216 control answer cardinality drift")
            treatment, assembly = assemble_blocks(
                row["question"],
                focuses,
                answers[(item_id, "treatment", replicate)],
            )
            treatment_output_tokens = sum(
                call["output_tokens"] or 0
                for call in calls
                if call.get("item_id") == item_id
                and call.get("arm") == "treatment"
                and call.get("replicate") == replicate
            )
            if treatment_output_tokens > AGGREGATE_OUTPUT_BUDGET:
                raise RuntimeError("S216 realized treatment output exceeds control budget")
            final_answers.extend(
                [
                    {
                        "item_id": item_id,
                        "role": row["role"],
                        "arm": "control",
                        "replicate": replicate,
                        "answer": control_blocks[0]["answer"],
                        "answer_sha256": hashlib.sha256(
                            control_blocks[0]["answer"].encode("utf-8")
                        ).hexdigest(),
                        "aggregate_output_tokens": next(
                            call["output_tokens"]
                            for call in calls
                            if call.get("item_id") == item_id
                            and call.get("arm") == "control"
                            and call.get("replicate") == replicate
                        ),
                    },
                    {
                        "item_id": item_id,
                        "role": row["role"],
                        "arm": "treatment",
                        "replicate": replicate,
                        "answer": treatment,
                        "answer_sha256": assembly["candidate_sha256"],
                        "aggregate_output_tokens": treatment_output_tokens,
                        "assembly": assembly,
                    },
                ]
            )
    _write_generation(calls, "COMPLETE_SCORE_NOT_OPENED", answers=final_answers)
    return {
        "status": "COMPLETE_SCORE_NOT_OPENED",
        "questions": len(rows),
        "decomposition_calls": len(decomposition_rows),
        "writer_calls": len(calls),
        "actual_cost_usd": round(actual, 8),
        "score_packet_opened": False,
        "target_questions_opened": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute:
        packet = json.loads(PACKET.read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "status": "ZERO_CALL",
                    "packet_sha256": file_sha(PACKET),
                    "questions": packet["population"]["questions"],
                    "target_questions": packet["population"]["target_questions"],
                    "score_packet_opened": False,
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
