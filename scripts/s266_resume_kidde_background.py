#!/usr/bin/env python3
"""Finish the S217 dual-authorship holdout with resumable Sol background calls."""
from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.frontier_visual_runtime_v2 import FrontierVisualRuntime  # noqa: E402
from src.rag.frontier_visual_schemas import (  # noqa: E402
    anthropic_compatible_schema,
    candidate_schema,
)
from src.rag.multisource_visual_gold import (  # noqa: E402
    author_prompt,
    page_content_fable,
    page_content_openai,
    validate_candidate,
)
from src.rag.visual_gold import (  # noqa: E402
    SemanticNoGo,
    conservative_cost,
    normalized_text_sha,
    sealed_artifact,
    stable_sha,
    write_json,
)


PACKET = ROOT / "evals/s217_kidde_external_cohort_packet_v1.json"
PREREG = ROOT / "evals/s266_kidde_background_resume_prereg_v1.yaml"
S263_LEDGER = ROOT / "evals/s263_kidde_dual_authorship_ledger_v1.json"
S264_RESULT = ROOT / "evals/s264_kidde_transport_resume_result_v1.json"
S264_LEDGER = ROOT / "evals/s264_kidde_transport_resume_ledger_v1.json"
S264_FABLE = ROOT / "evals/s264_kidde_fable_generations_v1.json"
S264_SOL = ROOT / "evals/s264_kidde_sol_generations_v1.json"
ATTEMPTS = ROOT / "evals/s266_kidde_background_attempts_v1.json"
LEDGER = ROOT / "evals/s266_kidde_background_ledger_v1.json"
BACKGROUND_STATES = ROOT / "evals/s266_kidde_background_states_v1"
FABLE_GENERATIONS = ROOT / "evals/s266_kidde_fable_generations_v1.json"
SOL_GENERATIONS = ROOT / "evals/s266_kidde_sol_generations_v1.json"
RESULT = ROOT / "evals/s266_kidde_background_result_v1.json"
OUTPUTS = (ATTEMPTS, LEDGER, FABLE_GENERATIONS, SOL_GENERATIONS, RESULT)

SOL = "gpt-5.6-sol"
FABLE = "claude-fable-5"
FABLE_MAX_TOKENS = 16000
MIN_VALID_PAIRS = 3
MAX_NEW_CALLS = 5
INTERNAL_BUDGET_USD = 35.0
PRICES = {
    "sol": {"input": 5.0, "output": 30.0},
    "fable": {"input": 30.0, "output": 150.0},
}


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _checkpoint(path: Path, schema: str, body: dict[str, Any]) -> None:
    write_json(path, sealed_artifact(schema, body))


def _record_attempt(provider: str, label: str) -> None:
    body = {"schema": "s266_kidde_background_attempts_v1", "attempts": []}
    if ATTEMPTS.exists():
        body = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    body["attempts"].append({
        "provider": provider,
        "call_label": label,
        "semantic_attempt": 1,
    })
    write_json(ATTEMPTS, body)


class S266Runtime(FrontierVisualRuntime):
    def call_sol(
        self,
        content: list[dict[str, Any]],
        call_label: str,
        *,
        output_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del output_schema
        _record_attempt("sol", call_label)
        item_id = call_label.removeprefix("generate:")
        return super().call_sol(
            content, call_label, output_schema=candidate_schema(item_id)
        )

    def call_fable(
        self,
        content: list[dict[str, Any]],
        max_tokens: int,
        call_label: str,
        *,
        output_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del max_tokens, output_schema
        _record_attempt("fable", call_label)
        item_id = call_label.removeprefix("generate:")
        return super().call_fable(
            content,
            FABLE_MAX_TOKENS,
            call_label,
            output_schema=anthropic_compatible_schema(candidate_schema(item_id)),
        )


def _runtime(env_file: Path) -> S266Runtime:
    secrets = dotenv_values(env_file)
    openai_key = str(
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = str(
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S266 provider credentials are unavailable")
    return S266Runtime(
        ledger_path=LEDGER,
        ledger_schema="s266_kidde_background_ledger_v1",
        sol_model=SOL,
        fable_model=FABLE,
        sol_reasoning="xhigh",
        fable_effort="xhigh",
        prices=PRICES,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
        sol_background=True,
        sol_transport_retries=2,
        sol_poll_interval_seconds=2.0,
        sol_poll_timeout_seconds=1800.0,
        sol_state_dir=BACKGROUND_STATES,
    )


def verify_prereg(packet: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_BACKGROUND_RESUME":
        raise ValueError("S266 preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S266 frozen input drift: {label}")
    packet_body = dict(packet)
    expected = packet_body.pop("packet_sha256", None)
    if stable_sha(packet_body) != expected or prereg["lineage"]["packet_sha256"] != expected:
        raise ValueError("S266 packet identity drift")
    s263_ledger = _sealed(S263_LEDGER)
    result = _sealed(S264_RESULT)
    s264_ledger = _sealed(S264_LEDGER)
    fable = _sealed(S264_FABLE)
    sol = _sealed(S264_SOL)
    if result.get("status") != "HOLD_S264_EXTERNAL_OR_INCOMPLETE":
        raise ValueError("S266 requires the S264 external hold")
    if "Error code: 520" not in str(result.get("reason")):
        raise ValueError("S266 requires the exact S264 HTTP 520 cause")
    if len(s263_ledger.get("calls") or []) != 1:
        raise ValueError("S266 S263 lineage drift")
    calls = s264_ledger.get("calls") or []
    if [(row.get("provider"), row.get("status")) for row in calls] != [
        ("sol", "completed"), ("fable", "end_turn")
    ]:
        raise ValueError("S266 S264 call lineage drift")
    if len(fable.get("items") or []) != 2 or len(sol.get("items") or []) != 1:
        raise ValueError("S266 carried candidate count drift")
    if any(row.get("validation_status") != "VALID" for row in fable["items"] + sol["items"]):
        raise ValueError("S266 can carry only valid candidates")
    return s263_ledger, s264_ledger, fable, sol


def preflight(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    images = 0
    for item in packet["items"]:
        page_content_openai(ROOT, item, "verify")
        page_content_fable(ROOT, item, "verify")
        images += len(item["rendered_pages"])
    existing = [path.relative_to(ROOT).as_posix() for path in OUTPUTS if path.exists()]
    if existing or BACKGROUND_STATES.exists():
        raise FileExistsError(
            f"S266 outputs already exist: {existing + ([BACKGROUND_STATES.relative_to(ROOT).as_posix()] if BACKGROUND_STATES.exists() else [])}"
        )
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "carried_valid_fable": 2,
        "carried_valid_sol": 1,
        "new_calls_max": MAX_NEW_CALLS,
        "sol_background": True,
        "images": images,
        "paid_calls": 0,
    }))
    return 0


def _candidate_row(provider, item, value, receipt):
    status, error, valid = "VALID", None, True
    try:
        validate_candidate(value, item)
    except SemanticNoGo as exc:
        status, error, valid = "INSUFFICIENT", str(exc), False
    except ValueError as exc:
        status, error, valid = "INVALID", str(exc), False
    return ({
        "canary_id": item["canary_id"],
        "provider": provider,
        "candidate": value,
        "validation_status": status,
        "validation_error": error,
        "receipt": receipt,
    }, valid)


def _all_prior_calls(s263_ledger, s264_ledger):
    return list(s263_ledger.get("calls") or []) + list(s264_ledger.get("calls") or [])


def _write_result(runtime, prior_calls, status, **extra):
    new_calls = runtime.load_ledger().get("calls") or []
    all_calls = prior_calls + list(new_calls)
    _checkpoint(RESULT, "s266_kidde_background_result_v1", {
        "status": status,
        **extra,
        "carried_calls": len(prior_calls),
        "s266_new_calls": len(new_calls),
        "frontier_calls_total": len(all_calls),
        "conservative_cost_total_usd": conservative_cost(all_calls, PRICES),
        "conservative_cost_s266_usd": conservative_cost(new_calls, PRICES),
        "sol_background": True,
        "transport_retries_max_per_http_operation": 2,
        "semantic_retries": 0,
        "reciprocal_review_calls": 0,
        "support_mapping_calls": 0,
        "synthesis_calls": 0,
        "target_calls": 0,
        "official_fact_credit": 0,
        "production_default_changed": False,
        "chunks_v2": "ACTIVE_READ_ONLY",
        "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
        "railway_merge_gate": False,
    })


def execute(packet: dict[str, Any], env_file: Path) -> int:
    preflight(packet)
    s263_ledger, s264_ledger, prior_fable, prior_sol = verify_prereg(packet)
    prior_calls = _all_prior_calls(s263_ledger, s264_ledger)
    runtime = _runtime(env_file)
    rows = {
        "fable": [deepcopy(row) for row in prior_fable["items"]],
        "sol": [deepcopy(row) for row in prior_sol["items"]],
    }
    for provider in rows:
        for row in rows[provider]:
            row["carried_from"] = f"s264_kidde_{provider}_generations_v1"
    valid = {
        provider: {row["canary_id"] for row in provider_rows}
        for provider, provider_rows in rows.items()
    }
    _checkpoint(FABLE_GENERATIONS, "s266_kidde_fable_generations_v1", {
        "status": "IN_PROGRESS", "items": rows["fable"]
    })
    _checkpoint(SOL_GENERATIONS, "s266_kidde_sol_generations_v1", {
        "status": "IN_PROGRESS", "items": rows["sol"]
    })
    try:
        for index, item in enumerate(packet["items"][1:], start=1):
            item_id = item["canary_id"]
            prompt = author_prompt(packet, item)
            if index > 1:
                fable_value, fable_receipt = runtime.call_fable(
                    page_content_fable(ROOT, item, prompt),
                    FABLE_MAX_TOKENS,
                    f"generate:{item_id}",
                )
                row, accepted = _candidate_row("fable", item, fable_value, fable_receipt)
                rows["fable"].append(row)
                valid["fable"].update([item_id] if accepted else [])
                _checkpoint(FABLE_GENERATIONS, "s266_kidde_fable_generations_v1", {
                    "status": "IN_PROGRESS", "items": rows["fable"]
                })

            sol_value, sol_receipt = runtime.call_sol(
                page_content_openai(ROOT, item, prompt), f"generate:{item_id}"
            )
            row, accepted = _candidate_row("sol", item, sol_value, sol_receipt)
            rows["sol"].append(row)
            valid["sol"].update([item_id] if accepted else [])
            _checkpoint(SOL_GENERATIONS, "s266_kidde_sol_generations_v1", {
                "status": "IN_PROGRESS", "items": rows["sol"]
            })
            if conservative_cost(runtime.load_ledger()["calls"], PRICES) > INTERNAL_BUDGET_USD:
                raise RuntimeError("S266 internal budget exceeded")
    except Exception as exc:
        _write_result(
            runtime, prior_calls, "HOLD_S266_EXTERNAL_OR_INCOMPLETE",
            reason=f"{type(exc).__name__}: {exc}",
        )
        raise

    _checkpoint(FABLE_GENERATIONS, "s266_kidde_fable_generations_v1", {
        "status": "COMPLETE", "items": rows["fable"]
    })
    _checkpoint(SOL_GENERATIONS, "s266_kidde_sol_generations_v1", {
        "status": "COMPLETE", "items": rows["sol"]
    })
    runtime.seal_complete(MAX_NEW_CALLS)
    pairs = sorted(valid["fable"] & valid["sol"])
    if len(pairs) < MIN_VALID_PAIRS:
        _write_result(runtime, prior_calls, "NO_GO_S266_DUAL_AUTHORSHIP", valid_pair_ids=pairs)
        return 2
    _write_result(
        runtime, prior_calls, "GO_S266_TO_SEPARATE_RECIPROCAL_PIXEL_REVIEW",
        valid_pair_ids=pairs,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    if not args.execute:
        return preflight(packet)
    if args.env_file is None:
        raise ValueError("--env-file is required with --execute")
    return execute(packet, args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
