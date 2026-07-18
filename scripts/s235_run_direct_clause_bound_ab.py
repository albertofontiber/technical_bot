#!/usr/bin/env python3
"""Run a leakage-safe paired A/B on the four frozen synthesis-miss questions."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import anthropic
import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s156_frontier_synthesis_ceiling import build_prompt  # noqa: E402
from src.rag.clause_bound_synthesis import (  # noqa: E402
    WRITER_SYSTEM,
    assemble_claim_blocks,
    claim_block_schema,
    validate_claim_block,
    writer_payload,
)
from src.rag.decomposed_evidence_planner_v2 import (  # noqa: E402
    PLANNER_SYSTEM,
    planner_payload,
    planner_schema,
    validate_plan,
)
from src.rag.evidence_units_v2 import (  # noqa: E402
    EvidenceUnitV2,
    build_header_aware_evidence_units,
)
from src.rag.frontier_visual_schemas import anthropic_compatible_schema  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    parse_json,
    sealed_artifact,
    stable_sha,
    write_json,
)

PACKET = ROOT / "evals/s235_direct_clause_bound_generation_packet_v1.json"
PREREG = ROOT / "evals/s235_direct_clause_bound_ab_prereg_v1.yaml"
PERMIT = ROOT / "evals/s235_direct_clause_bound_ab_execution_permit_v1.yaml"
OUT = ROOT / "evals/s235_direct_clause_bound_generation_v1.json"
LEDGER = ROOT / "evals/s235_direct_clause_bound_call_ledger_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
QIDS = ("cat018", "hp002", "hp011", "hp017")
REPLICATES = (1, 2)
PLANNER_MAX_TOKENS = 1200
BASELINE_MAX_TOKENS = 3600
AGGREGATE_TREATMENT_TOKENS = 3600
MAX_WRITER_WORKERS = 4
MAX_STAGE_COST_USD = 25.0
TRANSIENT_STATUSES = {408, 409, 429, 500, 502, 503, 504, 520, 529}


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _forbidden_score_keys(value: Any) -> list[str]:
    forbidden = {
        "base_answer",
        "canonical_answer",
        "obligations",
        "conflicts",
        "residual_obligation_ids",
        "required_anchors",
    }
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                found.append(key)
            found.extend(_forbidden_score_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_forbidden_score_keys(child))
    return found


def _units(item: dict[str, Any]) -> list[EvidenceUnitV2]:
    output: list[EvidenceUnitV2] = []
    for fragment_number, chunk in enumerate(item["context"], 1):
        output.extend(
            build_header_aware_evidence_units(
                str(chunk.get("content") or ""),
                fragment_number=fragment_number,
                candidate_id=str(chunk.get("id") or ""),
                max_chars=600,
                overlap_chars=120,
            )
        )
    if not output or len(output) > 500:
        raise ValueError("invalid evidence-unit population")
    if len({unit.unit_id for unit in output}) != len(output):
        raise ValueError("evidence-unit identity collision")
    return output


def _text(response: Any) -> str:
    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    ).strip()


def _usage(response: Any) -> dict[str, Any]:
    return response.usage.model_dump(mode="json")


def _cost(usage: dict[str, Any], price: dict[str, float]) -> float:
    return (
        int(usage.get("input_tokens") or 0) * float(price["input"])
        + int(usage.get("output_tokens") or 0) * float(price["output"])
    ) / 1_000_000


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.RateLimitError)):
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and status in TRANSIENT_STATUSES


def verify() -> tuple[dict[str, Any], dict[str, Any], float]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S235 preregistration is not frozen")
    for label, spec in prereg["frozen_generation_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S235 frozen input drift: {label}")
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    if permit.get("status") != "EXECUTION_GO_DIRECT_AB_DUAL_PASS":
        raise ValueError("S235 paid execution permit is absent or not GO")
    for label, spec in permit["frozen_artifacts"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S235 permitted artifact drift: {label}")
    packet = _sealed(PACKET)
    if (
        packet.get("status") != "SEALED_GENERATION_ONLY_NO_SCORE_FIELDS"
        or packet.get("population")
        != {"questions": 4, "qids": list(QIDS), "chunks": 51}
        or _forbidden_score_keys(packet)
    ):
        raise ValueError("S235 generation packet isolation or population drift")
    if prereg["models"] != {
        "planner": "claude-haiku-4-5-20251001",
        "writer": "claude-sonnet-4-6",
        "planner_max_output_tokens": PLANNER_MAX_TOKENS,
        "baseline_max_output_tokens": BASELINE_MAX_TOKENS,
        "aggregate_treatment_max_output_tokens_per_question": AGGREGATE_TREATMENT_TOKENS,
    }:
        raise ValueError("S235 model contract drift")

    baseline_bytes = 0
    planner_bytes = 0
    total_units = 0
    for item in packet["items"]:
        system, prompt = build_prompt(item)
        baseline_bytes += len(system.encode("utf-8")) + len(prompt.encode("utf-8"))
        units = _units(item)
        total_units += len(units)
        identity = {
            "question_sha256": hashlib.sha256(item["question"].encode()).hexdigest(),
            "source_files": sorted(
                {str(chunk.get("source_file") or "unknown") for chunk in item["context"]}
            ),
            "product_models": sorted(
                {str(chunk.get("product_model") or "unknown") for chunk in item["context"]}
            ),
        }
        source_identity = {
            str(chunk.get("id") or ""): {
                "source_file": str(chunk.get("source_file") or "unknown"),
                "page_number": int(chunk.get("page_number") or 0),
                "product_model": str(chunk.get("product_model") or "unknown"),
            }
            for chunk in item["context"]
        }
        planner_bytes += len(
            planner_payload(item["question"], identity, units, source_identity).encode(
                "utf-8"
            )
        )
    prices = prereg["pricing_usd_per_million_tokens"]
    repetitions = len(REPLICATES)
    max_writer_calls = len(QIDS) * repetitions * 12
    input_token_upper = repetitions * (baseline_bytes + planner_bytes) + max_writer_calls * 5000
    output_cost_upper = (
        len(QIDS) * repetitions * BASELINE_MAX_TOKENS * prices["writer"]["output"]
        + len(QIDS) * repetitions * PLANNER_MAX_TOKENS * prices["planner"]["output"]
        + len(QIDS) * repetitions * AGGREGATE_TREATMENT_TOKENS * prices["writer"]["output"]
    ) / 1_000_000
    input_cost_upper = input_token_upper * max(
        prices["planner"]["input"], prices["writer"]["input"]
    ) / 1_000_000
    worst_case = 2 * (input_cost_upper + output_cost_upper)
    if worst_case >= MAX_STAGE_COST_USD:
        raise RuntimeError(f"S235 worst-case preflight exceeds stage cap: {worst_case:.4f}")
    if total_units <= 0:
        raise ValueError("S235 unit population is empty")
    return prereg, packet, worst_case


class Runner:
    def __init__(self, prereg: dict[str, Any], env_file: Path) -> None:
        secrets = dotenv_values(env_file)
        key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
        if not key:
            raise RuntimeError("S235 ANTHROPIC_API_KEY missing")
        self.client = anthropic.Anthropic(api_key=key, max_retries=0)
        self.models = prereg["models"]
        self.prices = prereg["pricing_usd_per_million_tokens"]
        self.lock = threading.Lock()
        self.actual_cost = 0.0

    def _event(self, event: dict[str, Any]) -> None:
        with self.lock:
            ledger = _sealed(LEDGER)
            body = {key: value for key, value in ledger.items() if key != "result_sha256"}
            body["events"].append(event)
            body["actual_cost_usd"] = round(self.actual_cost, 8)
            write_json(LEDGER, sealed_artifact("s235_direct_clause_bound_call_ledger_v1", {
                key: value for key, value in body.items() if key != "schema"
            }))

    def call(
        self,
        *,
        label: str,
        role: str,
        request: dict[str, Any],
    ) -> tuple[str, dict[str, Any], float]:
        response = None
        for attempt in (1, 2):
            self._event({"event": "ATTEMPTED", "label": label, "role": role, "attempt": attempt})
            try:
                response = self.client.messages.create(**request)
            except Exception as exc:
                retryable = _retryable(exc)
                self._event(
                    {
                        "event": "TRANSPORT_ERROR",
                        "label": label,
                        "role": role,
                        "attempt": attempt,
                        "retryable": retryable,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                if not retryable or attempt == 2:
                    raise
                time.sleep(2)
                continue
            break
        if response is None:
            raise RuntimeError("S235 provider call did not produce a response")
        raw = _text(response)
        usage = _usage(response)
        call_cost = _cost(usage, self.prices[role])
        with self.lock:
            self.actual_cost += call_cost
            over_budget = self.actual_cost >= MAX_STAGE_COST_USD
        self._event(
            {
                "event": "COMPLETED",
                "label": label,
                "role": role,
                "attempt": attempt,
                "response_id": response.id,
                "model": response.model,
                "stop_reason": response.stop_reason,
                "usage": usage,
                "cost_usd": round(call_cost, 8),
                "raw_output": raw,
            }
        )
        if over_budget:
            raise RuntimeError("S235 actual cost ceiling reached")
        expected_model = self.models["planner" if role == "planner" else "writer"]
        if response.model != expected_model or response.stop_reason != "end_turn" or not raw:
            raise RuntimeError(
                f"S235 incomplete or model mismatch: {response.model}/{response.stop_reason}"
            )
        return raw, usage, call_cost


def _initialize_ledger() -> None:
    write_json(
        LEDGER,
        sealed_artifact(
            "s235_direct_clause_bound_call_ledger_v1",
            {
                "status": "IN_PROGRESS",
                "events": [],
                "actual_cost_usd": 0.0,
                "semantic_retries": 0,
                "transport_retries_max_per_label": 1,
            },
        ),
    )


def _checkpoint(items: list[dict[str, Any]], runner: Runner, status: str) -> None:
    write_json(
        OUT,
        sealed_artifact(
            "s235_direct_clause_bound_generation_v1",
            {
                "status": status,
                "items": items,
                "actual_cost_usd": round(runner.actual_cost, 8),
                "score_packet_opened": False,
                "semantic_retries": 0,
                "transport_retries_max_per_label": 1,
            },
        ),
    )


def execute(prereg: dict[str, Any], packet: dict[str, Any], env_file: Path) -> int:
    if OUT.exists() or LEDGER.exists():
        raise RuntimeError("S235 paid generation was already attempted")
    _initialize_ledger()
    runner = Runner(prereg, env_file)
    outputs: list[dict[str, Any]] = []
    try:
        for item in packet["items"]:
            units = _units(item)
            by_id = {unit.unit_id: unit for unit in units}
            identity = {
                "question_sha256": hashlib.sha256(item["question"].encode()).hexdigest(),
                "source_files": sorted(
                    {str(chunk.get("source_file") or "unknown") for chunk in item["context"]}
                ),
                "product_models": sorted(
                    {str(chunk.get("product_model") or "unknown") for chunk in item["context"]}
                ),
            }
            source_identity = {
                str(chunk.get("id") or ""): {
                    "source_file": str(chunk.get("source_file") or "unknown"),
                    "page_number": int(chunk.get("page_number") or 0),
                    "product_model": str(chunk.get("product_model") or "unknown"),
                }
                for chunk in item["context"]
            }
            planner_prompt = planner_payload(
                item["question"], identity, units, source_identity
            )
            baseline_system, baseline_prompt = build_prompt(item)
            replicas = []
            for replicate in REPLICATES:
                baseline_label = f"{item['qid']}:r{replicate}:baseline"
                planner_label = f"{item['qid']}:r{replicate}:planner"
                baseline_request = {
                    "model": runner.models["writer"],
                    "max_tokens": BASELINE_MAX_TOKENS,
                    "temperature": 0,
                    "system": baseline_system,
                    "messages": [{"role": "user", "content": baseline_prompt}],
                }
                planner_request = {
                    "model": runner.models["planner"],
                    "max_tokens": PLANNER_MAX_TOKENS,
                    "temperature": 0,
                    "system": PLANNER_SYSTEM,
                    "messages": [{"role": "user", "content": planner_prompt}],
                    "output_config": {
                        "format": {
                            "type": "json_schema",
                            "schema": anthropic_compatible_schema(planner_schema()),
                        }
                    },
                }
                with ThreadPoolExecutor(max_workers=2) as pool:
                    baseline_future = pool.submit(
                        runner.call,
                        label=baseline_label,
                        role="writer",
                        request=baseline_request,
                    )
                    planner_future = pool.submit(
                        runner.call,
                        label=planner_label,
                        role="planner",
                        request=planner_request,
                    )
                    baseline_answer = baseline_future.result()[0]
                    planner_raw = planner_future.result()[0]
                plan, selected_ids = validate_plan(parse_json(planner_raw), set(by_id))
                per_block_tokens = AGGREGATE_TREATMENT_TOKENS // len(plan)
                if per_block_tokens < 300 or per_block_tokens * len(plan) > AGGREGATE_TREATMENT_TOKENS:
                    raise RuntimeError("S235 aggregate treatment output budget drift")

                blocks_by_index: dict[int, dict[str, Any]] = {}

                def writer_job(index: int, obligation: dict[str, Any]) -> tuple[int, dict[str, Any]]:
                    selected_units = [by_id[unit_id] for unit_id in obligation["unit_ids"]]
                    label = f"{item['qid']}:r{replicate}:writer:{index}"
                    request = {
                        "model": runner.models["writer"],
                        "max_tokens": per_block_tokens,
                        "temperature": 0,
                        "system": WRITER_SYSTEM,
                        "messages": [
                            {
                                "role": "user",
                                "content": writer_payload(
                                    item["question"], obligation["label"], selected_units
                                ),
                            }
                        ],
                        "output_config": {
                            "format": {
                                "type": "json_schema",
                                "schema": anthropic_compatible_schema(claim_block_schema()),
                            }
                        },
                    }
                    raw = runner.call(label=label, role="writer", request=request)[0]
                    value = parse_json(raw)
                    validate_claim_block(value, set(obligation["unit_ids"]))
                    return index, value

                with ThreadPoolExecutor(max_workers=min(MAX_WRITER_WORKERS, len(plan))) as pool:
                    futures = [
                        pool.submit(writer_job, index, obligation)
                        for index, obligation in enumerate(plan, 1)
                    ]
                    for future in as_completed(futures):
                        index, value = future.result()
                        blocks_by_index[index] = value
                blocks = [
                    {"obligation_index": index, "value": blocks_by_index[index]}
                    for index in range(1, len(plan) + 1)
                ]
                treatment_answer, assembly = assemble_claim_blocks(
                    item["question"], plan, blocks, units
                )
                replicas.append(
                    {
                        "replicate": replicate,
                        "baseline_answer": baseline_answer,
                        "treatment_answer": treatment_answer,
                        "plan": plan,
                        "selected_unit_ids": selected_ids,
                        "claim_blocks": blocks,
                        "assembly": assembly,
                        "fragment_count": len(item["context"]),
                    }
                )
                provisional = outputs + [{"qid": item["qid"], "replicas": replicas}]
                _checkpoint(provisional, runner, "IN_PROGRESS_SCORE_NOT_OPENED")
            outputs.append({"qid": item["qid"], "replicas": replicas})

        _checkpoint(outputs, runner, "COMPLETE_SCORE_NOT_OPENED")
        ledger = _sealed(LEDGER)
        ledger_body = {key: value for key, value in ledger.items() if key not in {"schema", "result_sha256"}}
        ledger_body["status"] = "COMPLETE"
        write_json(
            LEDGER,
            sealed_artifact("s235_direct_clause_bound_call_ledger_v1", ledger_body),
        )
        print(
            json.dumps(
                {
                    "status": "COMPLETE_SCORE_NOT_OPENED",
                    "questions": len(outputs),
                    "replicates": sum(len(item["replicas"]) for item in outputs),
                    "cost_usd": round(runner.actual_cost, 6),
                },
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        _checkpoint(outputs, runner, "HOLD_EXTERNAL_OR_INVALID_NO_SEMANTIC_RETRY")
        ledger = _sealed(LEDGER)
        ledger_body = {key: value for key, value in ledger.items() if key not in {"schema", "result_sha256"}}
        ledger_body["status"] = "HOLD"
        ledger_body["terminal_error"] = f"{type(exc).__name__}: {exc}"
        write_json(
            LEDGER,
            sealed_artifact("s235_direct_clause_bound_call_ledger_v1", ledger_body),
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    prereg, packet, worst_case = verify()
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "PREFLIGHT_PASS",
                    "questions": len(packet["items"]),
                    "replicates": len(REPLICATES),
                    "maximum_semantic_calls": 112,
                    "worst_case_cost_usd": round(worst_case, 6),
                    "score_packet_opened": False,
                },
                indent=2,
            )
        )
        return 0
    return execute(prereg, packet, args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
