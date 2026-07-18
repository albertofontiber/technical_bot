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

from src.rag.frontier_visual_runtime_v3 import FrontierVisualRuntime  # noqa: E402
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
    parse_json,
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
    attempts: list[dict[str, Any]] = []
    if ATTEMPTS.exists():
        value = _sealed(ATTEMPTS)
        if value.get("schema") != "s266_kidde_background_attempts_v1":
            raise ValueError("S266 attempt schema drift")
        attempts = list(value.get("attempts") or [])
    identity = (provider, label)
    identities = [(row.get("provider"), row.get("call_label")) for row in attempts]
    if identity in identities:
        if identities[-1] != identity:
            raise RuntimeError("S266 attempt identity is duplicated out of order")
        return
    attempts.append({
        "provider": provider,
        "call_label": label,
        "semantic_attempt": 1,
    })
    _checkpoint(ATTEMPTS, "s266_kidde_background_attempts_v1", {
        "attempts": attempts,
    })


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


def preflight(packet: dict[str, Any], *, allow_resume: bool = False) -> int:
    verify_prereg(packet)
    images = 0
    for item in packet["items"]:
        page_content_openai(ROOT, item, "verify")
        page_content_fable(ROOT, item, "verify")
        images += len(item["rendered_pages"])
    existing = [path.relative_to(ROOT).as_posix() for path in OUTPUTS if path.exists()]
    if not allow_resume and (existing or BACKGROUND_STATES.exists()):
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


def _call_plan(packet: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    items = packet["items"]
    if len(items) != 4:
        raise ValueError("S266 packet item count drift")
    return [
        ("sol", items[1]),
        ("fable", items[2]),
        ("sol", items[2]),
        ("fable", items[3]),
        ("sol", items[3]),
    ]


def _call_identity(provider: str, item: dict[str, Any]) -> tuple[str, str]:
    return provider, f"generate:{item['canary_id']}"


def _carried_rows(prior_fable, prior_sol) -> dict[str, list[dict[str, Any]]]:
    rows = {
        "fable": [deepcopy(row) for row in prior_fable["items"]],
        "sol": [deepcopy(row) for row in prior_sol["items"]],
    }
    for provider in rows:
        for row in rows[provider]:
            row["carried_from"] = f"s264_kidde_{provider}_generations_v1"
    return rows


def _validate_generation_checkpoint(
    path: Path,
    schema: str,
    reconstructed: list[dict[str, Any]],
) -> None:
    if not path.exists():
        return
    value = _sealed(path)
    if value.get("schema") != schema:
        raise ValueError(f"S266 generation schema drift: {path.name}")
    if value.get("status") not in {"IN_PROGRESS", "COMPLETE"}:
        raise ValueError(f"S266 generation status drift: {path.name}")
    checkpointed = value.get("items") or []
    if checkpointed != reconstructed[:len(checkpointed)]:
        raise ValueError(f"S266 generation checkpoint is not a valid prefix: {path.name}")
    if len(checkpointed) > len(reconstructed):
        raise ValueError(f"S266 generation checkpoint is ahead of ledger: {path.name}")


def _reconstruct_resume_state(
    packet: dict[str, Any],
    runtime: S266Runtime,
    prior_fable: dict[str, Any],
    prior_sol: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, set[str]], int]:
    plan = _call_plan(packet)
    expected = [_call_identity(provider, item) for provider, item in plan]
    calls = list(runtime.load_ledger().get("calls") or [])
    actual = [(row.get("provider"), row.get("call_label")) for row in calls]
    if actual != expected[:len(actual)] or len(actual) > MAX_NEW_CALLS:
        raise ValueError("S266 ledger is not an exact call-plan prefix")

    rows = _carried_rows(prior_fable, prior_sol)
    items_by_id = {item["canary_id"]: item for item in packet["items"]}
    for receipt in calls:
        provider = str(receipt["provider"])
        required_status = "completed" if provider == "sol" else "end_turn"
        required_model = SOL if provider == "sol" else FABLE
        if receipt.get("status") != required_status or receipt.get("model") != required_model:
            raise RuntimeError("S266 cannot resume past an incomplete frontier receipt")
        item_id = str(receipt["call_label"]).removeprefix("generate:")
        value = parse_json(str(receipt.get("raw_output") or ""))
        row, _accepted = _candidate_row(
            provider, items_by_id[item_id], value, receipt
        )
        rows[provider].append(row)

    _validate_generation_checkpoint(
        FABLE_GENERATIONS, "s266_kidde_fable_generations_v1", rows["fable"]
    )
    _validate_generation_checkpoint(
        SOL_GENERATIONS, "s266_kidde_sol_generations_v1", rows["sol"]
    )

    attempts: list[dict[str, Any]] = []
    if ATTEMPTS.exists():
        attempt_artifact = _sealed(ATTEMPTS)
        if attempt_artifact.get("schema") != "s266_kidde_background_attempts_v1":
            raise ValueError("S266 attempt schema drift")
        attempts = list(attempt_artifact.get("attempts") or [])
    attempt_ids = [
        (row.get("provider"), row.get("call_label")) for row in attempts
    ]
    if attempt_ids[:len(actual)] != actual or len(attempt_ids) > len(actual) + 1:
        raise ValueError("S266 attempts are not an exact ledger prefix")
    if len(attempt_ids) == len(actual) + 1:
        if len(actual) == len(expected):
            raise ValueError("S266 has a dangling attempt after the complete call plan")
        if attempt_ids[-1] != expected[len(actual)]:
            raise ValueError("S266 dangling attempt is not the next planned call")
        if attempt_ids[-1][0] != "sol" or not BACKGROUND_STATES.exists():
            raise RuntimeError(
                "S266 cannot safely repeat an ambiguous non-resumable frontier POST"
            )

    valid = {
        provider: {
            row["canary_id"]
            for row in provider_rows
            if row.get("validation_status") == "VALID"
        }
        for provider, provider_rows in rows.items()
    }
    return rows, valid, len(calls)


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
    preflight(packet, allow_resume=True)
    s263_ledger, s264_ledger, prior_fable, prior_sol = verify_prereg(packet)
    prior_calls = _all_prior_calls(s263_ledger, s264_ledger)
    runtime = _runtime(env_file)
    if RESULT.exists():
        prior_result = _sealed(RESULT)
        terminal = prior_result.get("status")
        if terminal == "GO_S266_TO_SEPARATE_RECIPROCAL_PIXEL_REVIEW":
            return 0
        if terminal == "NO_GO_S266_DUAL_AUTHORSHIP":
            return 2
        if terminal != "HOLD_S266_EXTERNAL_OR_INCOMPLETE":
            raise ValueError("S266 result status drift")
    rows, valid, completed_calls = _reconstruct_resume_state(
        packet, runtime, prior_fable, prior_sol
    )
    _checkpoint(FABLE_GENERATIONS, "s266_kidde_fable_generations_v1", {
        "status": "IN_PROGRESS", "items": rows["fable"]
    })
    _checkpoint(SOL_GENERATIONS, "s266_kidde_sol_generations_v1", {
        "status": "IN_PROGRESS", "items": rows["sol"]
    })
    try:
        for call_index, (provider, item) in enumerate(_call_plan(packet)):
            if call_index < completed_calls:
                continue
            item_id = item["canary_id"]
            prompt = author_prompt(packet, item)
            if provider == "fable":
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
            else:
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
