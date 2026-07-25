#!/usr/bin/env python3
"""Run the one-shot non-target S228 clause-bound synthesis diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic
import yaml
from dotenv import dotenv_values
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.clause_bound_synthesis import (  # noqa: E402
    WRITER_SYSTEM,
    assemble_claim_blocks,
    validate_claim_block,
    writer_payload,
)
from src.rag.decomposed_evidence_planner import (  # noqa: E402
    PLANNER_SYSTEM,
    output_format,
    planner_payload,
    validate_plan,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units  # noqa: E402
from src.rag.visual_gold import parse_json, sealed_artifact, stable_sha, write_json  # noqa: E402

PACKET = ROOT / "evals/s219_omission_generation_packet_v1.json"
BASELINES = ROOT / "evals/s219_baseline_answer_receipts_v1.json"
PREREG = ROOT / "evals/s228_clause_bound_synthesis_prereg_v1.yaml"
OUT = ROOT / "evals/s228_clause_bound_synthesis_generation_v1.json"
CLOSURE = ROOT / "evals/s229_clause_bound_synthesis_transport_closeout_v1.yaml"
DEFAULT_ENV = Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env")
TERRA = "gpt-5.6-terra"
WRITER = "claude-sonnet-4-6"
REPLICATES = (1, 2)
AGGREGATE_TOKENS = 2400
MAX_COST = 25.0


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value); expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _units(item: dict[str, Any]):
    output = []
    for fragment, chunk in enumerate(item["context"], 1):
        output.extend(build_header_aware_evidence_units(
            chunk["content"], fragment_number=fragment,
            candidate_id=str(chunk["id"]), max_chars=600, overlap_chars=120,
        ))
    if not output or len(output) > 500:
        raise ValueError("invalid evidence-unit population")
    if len({unit.unit_id for unit in output}) != len(output):
        raise ValueError("evidence-unit identity collision")
    return output


def _cost(usage: Any, input_price: float, output_price: float) -> float:
    return ((getattr(usage, "input_tokens", 0) or 0) * input_price
            + (getattr(usage, "output_tokens", 0) or 0) * output_price) / 1_000_000


def verify() -> tuple[dict[str, Any], dict[str, Any]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_NON_TARGET_DIAGNOSTIC_FRONTIER_HOLD":
        raise ValueError("S228 preregistration drift")
    packet = _sealed(PACKET); baselines = _sealed(BASELINES)
    if len(packet.get("items") or []) != 9 or prereg["target_calls"] != 0:
        raise ValueError("S228 population drift")
    return packet, baselines


def execute(env_file: Path) -> int:
    if CLOSURE.exists():
        raise RuntimeError("S228 is closed after its one authorized execution")
    if OUT.exists():
        raise RuntimeError("S228 output exists; retries are forbidden")
    packet, baseline_receipts = verify()
    secrets = dotenv_values(env_file)
    openai_key = (secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    anthropic_key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("provider credentials unavailable")
    terra = OpenAI(api_key=openai_key, max_retries=0)
    sonnet = anthropic.Anthropic(api_key=anthropic_key, max_retries=0)
    extra_baselines = {row["item_id"]: row["answer"] for row in baseline_receipts["receipts"]}
    outputs = []; calls = []; actual = 0.0
    for item in packet["items"]:
        baseline = item["baseline_answer"] or extra_baselines[item["item_id"]]
        units = _units(item); by_id = {unit.unit_id: unit for unit in units}
        source_identity = {
            str(chunk["id"]): {
                "source_file": str(chunk.get("source_file") or "unknown"),
                "page_number": int(chunk.get("page_number") or 0),
                "product_model": str(chunk.get("product_model") or "unknown"),
            }
            for chunk in item["context"]
        }
        replicas = []
        for replica in REPLICATES:
            prompt = planner_payload(
                item["question"],
                {
                    "question_sha256": hashlib.sha256(item["question"].encode()).hexdigest(),
                    "source_files": sorted({str(c.get("source_file") or "unknown") for c in item["context"]}),
                    "product_models": sorted({str(c.get("product_model") or "unknown") for c in item["context"]}),
                },
                units,
                source_identity,
            )
            if len(prompt.encode("utf-8")) > 300_000:
                raise RuntimeError("planner prompt exceeds byte cap")
            response = terra.responses.create(
                model=TERRA, reasoning={"effort": "low"}, instructions=PLANNER_SYSTEM,
                input=prompt, text=output_format("s228_clause_source_plan"),
                max_output_tokens=1200, store=False,
            )
            if response.status != "completed" or response.model != TERRA:
                raise RuntimeError("planner incomplete or model mismatch")
            plan, _ = validate_plan(json.loads(response.output_text), set(by_id))
            if len(plan) > 8:
                raise ValueError("planner emitted more than eight obligations")
            plan_cost = _cost(response.usage, 2.5, 15.0); actual += plan_cost
            calls.append({"item_id": item["item_id"], "replicate": replica, "role": "planner",
                          "model": response.model, "status": response.status,
                          "usage": response.usage.model_dump(mode="json"), "cost_usd": plan_cost})
            per_block_tokens = max(300, AGGREGATE_TOKENS // len(plan))
            if per_block_tokens * len(plan) > AGGREGATE_TOKENS:
                raise RuntimeError("aggregate writer budget drift")
            blocks = []
            for index, obligation in enumerate(plan, 1):
                selected = [by_id[unit_id] for unit_id in obligation["unit_ids"]]
                writer_response = sonnet.messages.create(
                    model=WRITER, max_tokens=per_block_tokens, temperature=0,
                    system=WRITER_SYSTEM,
                    messages=[{"role": "user", "content": writer_payload(
                        item["question"], obligation["label"], selected)}],
                )
                raw = "\n".join(block.text for block in writer_response.content if block.type == "text")
                if writer_response.stop_reason != "end_turn":
                    raise RuntimeError("writer did not end normally")
                value = parse_json(raw); validate_claim_block(value, set(obligation["unit_ids"]))
                cost = _cost(writer_response.usage, 3.0, 15.0); actual += cost
                calls.append({"item_id": item["item_id"], "replicate": replica,
                              "role": "writer", "obligation_index": index,
                              "model": writer_response.model, "status": writer_response.stop_reason,
                              "usage": writer_response.usage.model_dump(mode="json"), "cost_usd": cost})
                blocks.append({"obligation_index": index, "value": value})
                if actual >= MAX_COST:
                    raise RuntimeError("S228 cost ceiling reached")
            answer, assembly = assemble_claim_blocks(item["question"], plan, blocks, units)
            replicas.append({"replicate": replica, "plan": plan, "answer": answer,
                             "assembly": assembly, "fragment_count": len(item["context"])})
        outputs.append({"item_id": item["item_id"], "role": item["role"],
                        "baseline_answer": baseline, "replicas": replicas})
        write_json(OUT, sealed_artifact("s228_clause_bound_synthesis_generation_v1",
            {"status": "IN_PROGRESS_SCORE_NOT_OPENED", "items": outputs, "calls": calls,
             "actual_cost_usd": actual, "score_packet_opened": False, "target_calls": 0}))
    write_json(OUT, sealed_artifact("s228_clause_bound_synthesis_generation_v1",
        {"status": "COMPLETE_SCORE_NOT_OPENED", "items": outputs, "calls": calls,
         "actual_cost_usd": actual, "score_packet_opened": False, "target_calls": 0}))
    print(json.dumps({"status": "COMPLETE_SCORE_NOT_OPENED", "items": len(outputs),
                      "calls": len(calls), "cost_usd": round(actual, 6)}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV); args = parser.parse_args()
    packet, _ = verify()
    if not args.execute:
        print(json.dumps({"status": "CLOSED" if CLOSURE.exists() else "PREFLIGHT_PASS", "items": len(packet["items"]),
                          "replicates": 2, "target_calls": 0}, indent=2)); return 0
    return execute(args.env_file)

if __name__ == "__main__":
    raise SystemExit(main())
