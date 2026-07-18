#!/usr/bin/env python3
"""Ask the stored S235 Sol reasoning for its final JSON, and run one Fable review."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import anthropic
import yaml
from dotenv import dotenv_values
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s235_review_direct_clause_bound_ab_design import (  # noqa: E402
    DESIGN,
    FABLE,
    PRICES,
    SOL,
    schema,
    validate,
)
from src.rag.frontier_visual_schemas import anthropic_compatible_schema  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    conservative_cost,
    parse_json,
    sealed_artifact,
    usage_dict,
    write_json,
)

PREREG = ROOT / "evals/s238_s235_review_continuation_prereg_v1.yaml"
LEDGER = ROOT / "evals/s238_s235_review_continuation_ledger_v1.json"
RESULT = ROOT / "evals/s235_design_frontier_reviews_v1.json"
PREVIOUS_RESPONSE_ID = "resp_0007d25ae2a53e05006a5b976a89208195ba0644b412776fac"
POLL_SECONDS = 5
POLL_DEADLINE_SECONDS = 600
TERMINAL = {"completed", "failed", "cancelled", "incomplete"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_ONE_STORED_RESPONSE_CONTINUATION":
        raise ValueError("S238 continuation is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S238 frozen input drift: {label}")
    if LEDGER.exists() or RESULT.exists():
        raise RuntimeError("S238 was already attempted")


def _full_prompt() -> str:
    code = "\n\n".join(
        f"## FILE: {path.relative_to(ROOT).as_posix()}\n{path.read_text(encoding='utf-8')}"
        for path in (
            DESIGN,
            ROOT / "scripts/s235_run_direct_clause_bound_ab.py",
            ROOT / "scripts/s235_score_direct_clause_bound_ab.py",
            ROOT / "src/rag/clause_bound_synthesis.py",
        )
    )
    return (
        "Adversarially review this one-shot direct experiment. PASS only if every "
        "structured check is true and the executable design cannot create a false GO. "
        "The 12 target misses are already frozen; using them now is intentional, and no "
        "new gold is requested. Treat stylistic improvements as nonblocking. FAIL only "
        "for a concrete causal, leakage, safety, overfit, transport, budget, or unsupported-"
        "credit blocker. Do not request broader research or a convergence round.\n\n" + code
    )


def _fable_text(response: Any) -> str:
    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    _verify()
    secrets = dotenv_values(args.env_file)
    openai_key = str(
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = str(
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S238 provider credentials missing")
    sol_client = OpenAI(api_key=openai_key, max_retries=0)
    fable_client = anthropic.Anthropic(api_key=anthropic_key, max_retries=0)
    previous = sol_client.responses.retrieve(PREVIOUS_RESPONSE_ID)
    if (
        previous.status != "incomplete"
        or previous.model != SOL
        or not previous.incomplete_details
        or previous.incomplete_details.reason != "max_output_tokens"
    ):
        raise ValueError("S238 stored Sol response geometry drift")

    continuation = sol_client.responses.create(
        model=SOL,
        previous_response_id=PREVIOUS_RESPONSE_ID,
        background=True,
        store=True,
        instructions="Return the final structured review JSON now. Do not restart the analysis.",
        input="Emit the final verdict from your completed review reasoning.",
        reasoning={"effort": "xhigh"},
        max_output_tokens=6000,
        text={
            "format": {
                "type": "json_schema",
                "name": "s235_continued_design_sol",
                "strict": True,
                "schema": schema(SOL),
            },
            "verbosity": "low",
        },
    )

    def fable_call() -> Any:
        return fable_client.messages.create(
            model=FABLE,
            max_tokens=8000,
            system="Follow the user contract exactly. Return only JSON.",
            messages=[{"role": "user", "content": [{"type": "text", "text": _full_prompt()}]}],
            thinking={"type": "adaptive"},
            output_config={
                "effort": "xhigh",
                "format": {
                    "type": "json_schema",
                    "schema": anthropic_compatible_schema(schema(FABLE)),
                },
            },
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        fable_future = pool.submit(fable_call)
        polls = [str(continuation.status)]
        started = time.monotonic()
        while continuation.status not in TERMINAL:
            if time.monotonic() - started >= POLL_DEADLINE_SECONDS:
                raise TimeoutError("S238 Sol continuation exceeded polling deadline")
            time.sleep(POLL_SECONDS)
            continuation = sol_client.responses.retrieve(continuation.id)
            polls.append(str(continuation.status))
        fable_response = fable_future.result()

    raw_sol = (continuation.output_text or "").strip()
    raw_fable = _fable_text(fable_response)
    ledger = {
        "status": "COMPLETE" if continuation.status == "completed" else "HOLD",
        "previous_sol": {
            "response_id": previous.id,
            "status": previous.status,
            "incomplete_reason": previous.incomplete_details.reason,
            "usage": usage_dict(previous),
        },
        "continued_sol": {
            "response_id": continuation.id,
            "status": continuation.status,
            "model": continuation.model,
            "polls": polls,
            "usage": usage_dict(continuation),
            "raw_output": raw_sol,
        },
        "fable": {
            "response_id": fable_response.id,
            "status": fable_response.stop_reason,
            "model": fable_response.model,
            "usage": usage_dict(fable_response),
            "raw_output": raw_fable,
        },
    }
    write_json(LEDGER, sealed_artifact("s238_s235_review_continuation_ledger_v1", ledger))
    if continuation.status != "completed" or continuation.model != SOL or not raw_sol:
        raise RuntimeError(
            f"S238 continued Sol incomplete: {continuation.status}/{continuation.model}"
        )
    if fable_response.stop_reason != "end_turn" or fable_response.model != FABLE or not raw_fable:
        raise RuntimeError(
            f"S238 Fable incomplete: {fable_response.stop_reason}/{fable_response.model}"
        )
    sol_review = parse_json(raw_sol)
    fable_review = parse_json(raw_fable)
    sol_pass = validate(sol_review, SOL)
    fable_pass = validate(fable_review, FABLE)
    calls = [
        {"provider": "sol", "usage": usage_dict(previous)},
        {"provider": "sol", "usage": usage_dict(continuation)},
        {"provider": "fable", "usage": usage_dict(fable_response)},
    ]
    dual_pass = sol_pass and fable_pass
    write_json(
        RESULT,
        sealed_artifact(
            "s235_design_frontier_reviews_v1",
            {
                "status": "DUAL_PASS" if dual_pass else "NO_GO_NO_CONVERGENCE",
                "reviews": {"sol": sol_review, "fable": fable_review},
                "sol_full_background_jobs": 1,
                "sol_same_response_continuations": 1,
                "fable_calls": 1,
                "pre_inference_sync_transport_failures": 2,
                "provider_sdk_retries": 0,
                "semantic_convergence_rounds": 0,
                "cost_usd": conservative_cost(calls, PRICES),
                "next_authorized_step": "direct_ab" if dual_pass else "close_s235",
                "official_fact_credit": 0,
                "production_default_changed": False,
                "chunks_v2": "ACTIVE_READ_ONLY",
                "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
                "railway_merge_gate": False,
            },
        ),
    )
    print(json.dumps({"status": "DUAL_PASS" if dual_pass else "NO_GO_NO_CONVERGENCE"}, indent=2))
    return 0 if dual_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
