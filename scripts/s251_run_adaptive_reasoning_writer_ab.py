#!/usr/bin/env python3
"""Run the frozen paired Sonnet control/adaptive-reasoning experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import anthropic
import yaml
from dotenv import dotenv_values

from scripts.s156_frontier_synthesis_ceiling import build_prompt
from src.rag.visual_gold import sealed_artifact, stable_sha, write_json

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evals/s235_direct_clause_bound_generation_packet_v1.json"
PREREG = ROOT / "evals/s251_adaptive_reasoning_writer_ab_prereg_v1.yaml"
PERMIT = ROOT / "evals/s251_adaptive_reasoning_writer_ab_execution_permit_v1.yaml"
OUT = ROOT / "evals/s251_adaptive_reasoning_writer_generation_v1.json"
LEDGER = ROOT / "evals/s251_adaptive_reasoning_writer_call_ledger_v1.json"
DEFAULT_ENV = Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env")
MODEL = "claude-sonnet-4-6"
QIDS = ("cat018", "hp002", "hp011", "hp017")
REPLICATES = (1, 2)
MAX_TOKENS = 8000
STAGE_COST_CEILING_USD = 15.0
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
        "base_answer", "canonical_answer", "obligations", "conflicts",
        "residual_obligation_ids", "required_anchors",
    }
    output: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                output.append(key)
            output.extend(_forbidden_score_keys(child))
    elif isinstance(value, list):
        for child in value:
            output.extend(_forbidden_score_keys(child))
    return output


def _text(response: Any) -> str:
    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()


def _usage(response: Any) -> dict[str, Any]:
    return response.usage.model_dump(mode="json")


def _cost(usage: dict[str, Any]) -> float:
    return (
        int(usage.get("input_tokens") or 0) * 3.0
        + int(usage.get("output_tokens") or 0) * 15.0
    ) / 1_000_000


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.RateLimitError)):
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and status in TRANSIENT_STATUSES


def build_arm_requests(system: str, prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    messages = [{"role": "user", "content": prompt}]
    control = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
        "system": system,
        "messages": messages,
    }
    treatment = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": messages,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high"},
    }
    if control["system"] != treatment["system"] or control["messages"] != treatment["messages"]:
        raise ValueError("S251 provider-visible prompt drift between arms")
    return control, treatment


def verify() -> tuple[dict[str, Any], dict[str, Any], float]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_AFTER_DUAL_FRONTIER_PASS":
        raise ValueError("S251 preregistration is not execution-frozen")
    if permit.get("status") != "EXECUTION_GO_DUAL_FRONTIER_PASS":
        raise ValueError("S251 execution permit absent")
    for collection in (prereg["frozen_generation_inputs"], permit["frozen_artifacts"]):
        for label, spec in collection.items():
            if _sha(ROOT / spec["path"]) != spec["sha256"]:
                raise ValueError(f"S251 frozen input drift: {label}")
    packet = _sealed(PACKET)
    if (
        packet.get("status") != "SEALED_GENERATION_ONLY_NO_SCORE_FIELDS"
        or packet.get("population") != {"questions": 4, "qids": list(QIDS), "chunks": 51}
        or _forbidden_score_keys(packet)
    ):
        raise ValueError("S251 generation isolation or population drift")
    request_bytes = 0
    for item in packet["items"]:
        system, prompt = build_prompt(item)
        request_bytes += len(system.encode("utf-8")) + len(prompt.encode("utf-8"))
    # One UTF-8 byte per possible input token is deliberately conservative.
    input_upper = len(REPLICATES) * 2 * request_bytes * 3.0 / 1_000_000
    output_upper = len(QIDS) * len(REPLICATES) * 2 * MAX_TOKENS * 15.0 / 1_000_000
    worst = input_upper + output_upper
    if worst >= STAGE_COST_CEILING_USD:
        raise RuntimeError(f"S251 worst-case cost exceeds stage ceiling: {worst:.4f}")
    return prereg, packet, worst


class Runner:
    def __init__(self, env_file: Path) -> None:
        secrets = dotenv_values(env_file)
        key = str(secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
        if not key:
            raise RuntimeError("S251 ANTHROPIC_API_KEY missing")
        self.client = anthropic.Anthropic(api_key=key, max_retries=0)
        self.lock = threading.Lock()
        self.actual_cost = 0.0

    def event(self, value: dict[str, Any]) -> None:
        with self.lock:
            ledger = _sealed(LEDGER)
            body = {key: val for key, val in ledger.items() if key not in {"schema", "result_sha256"}}
            body["events"].append(value)
            body["actual_cost_usd"] = round(self.actual_cost, 8)
            write_json(LEDGER, sealed_artifact("s251_adaptive_reasoning_writer_call_ledger_v1", body))

    def call(self, label: str, request: dict[str, Any]) -> dict[str, Any]:
        response = None
        for attempt in (1, 2):
            self.event({"event": "ATTEMPTED", "label": label, "attempt": attempt})
            try:
                response = self.client.messages.create(**request)
            except Exception as exc:
                retryable = _retryable(exc)
                self.event({
                    "event": "TRANSPORT_ERROR", "label": label, "attempt": attempt,
                    "retryable": retryable, "error": f"{type(exc).__name__}: {exc}",
                })
                if not retryable or attempt == 2:
                    raise
                time.sleep(2)
                continue
            break
        if response is None:
            raise RuntimeError("S251 provider returned no response")
        answer = _text(response)
        usage = _usage(response)
        call_cost = _cost(usage)
        with self.lock:
            self.actual_cost += call_cost
            over = self.actual_cost >= STAGE_COST_CEILING_USD
        self.event({
            "event": "COMPLETED", "label": label, "attempt": attempt,
            "response_id": response.id, "model": response.model,
            "stop_reason": response.stop_reason, "usage": usage,
            "cost_usd": round(call_cost, 8), "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
        })
        if over:
            raise RuntimeError("S251 actual cost ceiling reached")
        if response.model != MODEL or response.stop_reason != "end_turn" or not answer:
            raise RuntimeError(
                f"S251 incomplete or model mismatch: {response.model}/{response.stop_reason}"
            )
        return {"answer": answer, "usage": usage, "cost_usd": round(call_cost, 8)}


def _checkpoint(items: list[dict[str, Any]], runner: Runner, status: str) -> None:
    write_json(
        OUT,
        sealed_artifact(
            "s251_adaptive_reasoning_writer_generation_v1",
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


def execute(packet: dict[str, Any], env_file: Path) -> None:
    if OUT.exists() or LEDGER.exists():
        raise RuntimeError("S251 generation already attempted")
    write_json(
        LEDGER,
        sealed_artifact(
            "s251_adaptive_reasoning_writer_call_ledger_v1",
            {
                "status": "IN_PROGRESS", "events": [], "actual_cost_usd": 0.0,
                "semantic_retries": 0, "transport_retries_max_per_label": 1,
            },
        ),
    )
    runner = Runner(env_file)
    outputs: list[dict[str, Any]] = []
    try:
        for item in packet["items"]:
            system, prompt = build_prompt(item)
            replicas = []
            for replicate in REPLICATES:
                base, treatment = build_arm_requests(system, prompt)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    control_future = pool.submit(
                        runner.call, f"{item['qid']}:r{replicate}:control", base
                    )
                    treatment_future = pool.submit(
                        runner.call, f"{item['qid']}:r{replicate}:adaptive", treatment
                    )
                    control = control_future.result()
                    adaptive = treatment_future.result()
                replicas.append({
                    "replicate": replicate,
                    "baseline_answer": control["answer"],
                    "baseline_usage": control["usage"],
                    "treatment_answer": adaptive["answer"],
                    "treatment_usage": adaptive["usage"],
                })
            outputs.append({"qid": item["qid"], "replicas": replicas})
            _checkpoint(outputs, runner, "IN_PROGRESS_SCORE_NOT_OPENED")
    except Exception:
        _checkpoint(outputs, runner, "INCOMPLETE_NO_SEMANTIC_RETRY")
        raise
    _checkpoint(outputs, runner, "COMPLETE_SCORE_NOT_OPENED")
    ledger = _sealed(LEDGER)
    body = {key: value for key, value in ledger.items() if key not in {"schema", "result_sha256"}}
    body["status"] = "COMPLETE"
    write_json(LEDGER, sealed_artifact("s251_adaptive_reasoning_writer_call_ledger_v1", body))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    _prereg, packet, worst = verify()
    print(json.dumps({"status": "S251_PREFLIGHT_PASS", "worst_case_usd": round(worst, 6)}, indent=2))
    execute(packet, args.env_file)
    print(json.dumps({"status": "S251_GENERATION_COMPLETE"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
