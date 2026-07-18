#!/usr/bin/env python3
"""Transport-only resume of the frozen S263 Kidde authorship cohort."""
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
PREREG = ROOT / "evals/s264_kidde_transport_resume_prereg_v1.yaml"
S263_RESULT = ROOT / "evals/s263_kidde_dual_authorship_result_v1.json"
S263_LEDGER = ROOT / "evals/s263_kidde_dual_authorship_ledger_v1.json"
S263_FABLE = ROOT / "evals/s263_kidde_fable_generations_v1.json"
S263_SOL = ROOT / "evals/s263_kidde_sol_generations_v1.json"
ATTEMPTS = ROOT / "evals/s264_kidde_transport_resume_attempts_v1.json"
LEDGER = ROOT / "evals/s264_kidde_transport_resume_ledger_v1.json"
FABLE_GENERATIONS = ROOT / "evals/s264_kidde_fable_generations_v1.json"
SOL_GENERATIONS = ROOT / "evals/s264_kidde_sol_generations_v1.json"
RESULT = ROOT / "evals/s264_kidde_transport_resume_result_v1.json"
OUTPUTS = (ATTEMPTS, LEDGER, FABLE_GENERATIONS, SOL_GENERATIONS, RESULT)

SOL = "gpt-5.6-sol"
FABLE = "claude-fable-5"
FABLE_MAX_TOKENS = 16000
MIN_VALID_PAIRS = 3
MAX_NEW_CALLS = 7
INTERNAL_BUDGET_USD = 35.0
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
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
    body = {"schema": "s264_kidde_transport_resume_attempts_v1", "attempts": []}
    if ATTEMPTS.exists():
        body = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    body["attempts"].append({
        "provider": provider,
        "call_label": label,
        "status": "STARTED_NO_RETRY",
    })
    write_json(ATTEMPTS, body)


class S264Runtime(FrontierVisualRuntime):
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


def _runtime(env_file: Path) -> S264Runtime:
    secrets = dotenv_values(env_file)
    openai_key = str(
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = str(
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S264 provider credentials are unavailable")
    return S264Runtime(
        ledger_path=LEDGER,
        ledger_schema="s264_kidde_transport_resume_ledger_v1",
        sol_model=SOL,
        fable_model=FABLE,
        sol_reasoning="xhigh",
        fable_effort="xhigh",
        prices=PRICES,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
    )


def verify_prereg(packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_SINGLE_TRANSPORT_RESUME":
        raise ValueError("S264 preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S264 frozen input drift: {label}")
    packet_body = dict(packet)
    expected = packet_body.pop("packet_sha256", None)
    if stable_sha(packet_body) != expected or prereg["lineage"]["packet_sha256"] != expected:
        raise ValueError("S264 packet identity drift")
    result = _sealed(S263_RESULT)
    ledger = _sealed(S263_LEDGER)
    fable = _sealed(S263_FABLE)
    calls = ledger.get("calls") or []
    items = fable.get("items") or []
    if result.get("status") != "HOLD_S263_EXTERNAL_OR_INCOMPLETE":
        raise ValueError("S264 requires the S263 external hold")
    if "Error code: 520" not in str(result.get("reason")):
        raise ValueError("S264 requires the exact S263 HTTP 520 cause")
    if len(calls) != 1 or calls[0].get("provider") != "fable" or calls[0].get("status") != "end_turn":
        raise ValueError("S264 requires exactly one complete S263 Fable call")
    if len(items) != 1 or items[0].get("validation_status") != "VALID":
        raise ValueError("S264 requires exactly one valid S263 Fable candidate")
    if items[0].get("canary_id") != packet["items"][0]["canary_id"]:
        raise ValueError("S264 carried candidate identity drift")
    if S263_SOL.exists():
        raise ValueError("S264 cannot resume after an S263 Sol response artifact")
    return ledger, fable


def preflight(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    images = 0
    for item in packet["items"]:
        page_content_openai(ROOT, item, "verify")
        page_content_fable(ROOT, item, "verify")
        images += len(item["rendered_pages"])
    existing = [path.relative_to(ROOT).as_posix() for path in OUTPUTS if path.exists()]
    if existing:
        raise FileExistsError(f"S264 outputs already exist: {existing}")
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "carried_valid_fable": 1,
        "new_calls_max": MAX_NEW_CALLS,
        "images": images,
        "paid_calls": 0,
    }))
    return 0


def _candidate_row(
    provider: str,
    item: dict[str, Any],
    value: dict[str, Any],
    receipt: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    status = "VALID"
    error = None
    valid = True
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


def _combined_calls(runtime: S264Runtime, s263_ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return list(s263_ledger.get("calls") or []) + list(runtime.load_ledger().get("calls") or [])


def _write_result(
    runtime: S264Runtime,
    s263_ledger: dict[str, Any],
    status: str,
    **extra: Any,
) -> None:
    new_calls = runtime.load_ledger().get("calls") or []
    all_calls = _combined_calls(runtime, s263_ledger)
    _checkpoint(RESULT, "s264_kidde_transport_resume_result_v1", {
        "status": status,
        **extra,
        "s263_carried_calls": 1,
        "s264_new_calls": len(new_calls),
        "frontier_calls_total": len(all_calls),
        "conservative_cost_total_usd": conservative_cost(all_calls, PRICES),
        "conservative_cost_s264_usd": conservative_cost(new_calls, PRICES),
        "provider_retries_within_s264": 0,
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
    s263_ledger, s263_fable = verify_prereg(packet)
    runtime = _runtime(env_file)
    carried = deepcopy(s263_fable["items"][0])
    carried["carried_from"] = "s263_kidde_fable_generations_v1"
    rows: dict[str, list[dict[str, Any]]] = {"fable": [carried], "sol": []}
    valid: dict[str, set[str]] = {
        "fable": {carried["canary_id"]},
        "sol": set(),
    }
    _checkpoint(FABLE_GENERATIONS, "s264_kidde_fable_generations_v1", {
        "status": "IN_PROGRESS", "items": rows["fable"]
    })
    try:
        for index, item in enumerate(packet["items"]):
            item_id = item["canary_id"]
            prompt = author_prompt(packet, item)
            if index > 0:
                fable_value, fable_receipt = runtime.call_fable(
                    page_content_fable(ROOT, item, prompt),
                    FABLE_MAX_TOKENS,
                    f"generate:{item_id}",
                )
                row, accepted = _candidate_row("fable", item, fable_value, fable_receipt)
                rows["fable"].append(row)
                valid["fable"].update([item_id] if accepted else [])
                _checkpoint(FABLE_GENERATIONS, "s264_kidde_fable_generations_v1", {
                    "status": "IN_PROGRESS", "items": rows["fable"]
                })

            sol_value, sol_receipt = runtime.call_sol(
                page_content_openai(ROOT, item, prompt), f"generate:{item_id}"
            )
            row, accepted = _candidate_row("sol", item, sol_value, sol_receipt)
            rows["sol"].append(row)
            valid["sol"].update([item_id] if accepted else [])
            _checkpoint(SOL_GENERATIONS, "s264_kidde_sol_generations_v1", {
                "status": "IN_PROGRESS", "items": rows["sol"]
            })
            if conservative_cost(runtime.load_ledger()["calls"], PRICES) > INTERNAL_BUDGET_USD:
                raise RuntimeError("S264 internal budget exceeded")
    except Exception as exc:
        _write_result(
            runtime,
            s263_ledger,
            "HOLD_S264_EXTERNAL_OR_INCOMPLETE",
            reason=f"{type(exc).__name__}: {exc}",
        )
        raise

    _checkpoint(FABLE_GENERATIONS, "s264_kidde_fable_generations_v1", {
        "status": "COMPLETE", "items": rows["fable"]
    })
    _checkpoint(SOL_GENERATIONS, "s264_kidde_sol_generations_v1", {
        "status": "COMPLETE", "items": rows["sol"]
    })
    runtime.seal_complete(MAX_NEW_CALLS)
    pairs = sorted(valid["fable"] & valid["sol"])
    if len(pairs) < MIN_VALID_PAIRS:
        _write_result(
            runtime, s263_ledger, "NO_GO_S264_DUAL_AUTHORSHIP", valid_pair_ids=pairs
        )
        return 2
    _write_result(
        runtime,
        s263_ledger,
        "GO_S264_TO_SEPARATE_RECIPROCAL_PIXEL_REVIEW",
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
