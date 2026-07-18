#!/usr/bin/env python3
"""Run the unchanged S235 Sol review as one background job, then one Fable review."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
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
    stable_sha,
    usage_dict,
    write_json,
)

PREREG = ROOT / "evals/s237_s235_background_review_prereg_v1.yaml"
LEDGER = ROOT / "evals/s237_s235_background_review_ledger_v1.json"
RESULT = ROOT / "evals/s235_design_frontier_reviews_v1.json"
POLL_SECONDS = 5
POLL_DEADLINE_SECONDS = 900
TERMINAL = {"completed", "failed", "cancelled", "incomplete"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_ONE_BACKGROUND_SUBMISSION":
        raise ValueError("S237 background review is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S237 frozen input drift: {label}")
    if LEDGER.exists() or RESULT.exists():
        raise RuntimeError("S237 background review was already attempted")


def _prompt() -> str:
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


def _write_ledger(body: dict[str, Any]) -> None:
    write_json(LEDGER, sealed_artifact("s237_s235_background_review_ledger_v1", body))


def _load_ledger() -> dict[str, Any]:
    value = json.loads(LEDGER.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError("S237 ledger seal drift")
    return value


def _append_poll(status: str) -> None:
    value = _load_ledger()
    body = {key: child for key, child in value.items() if key not in {"schema", "result_sha256"}}
    body["polls"].append({"status": status})
    _write_ledger(body)


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
        raise RuntimeError("S237 provider credentials missing")
    prompt = _prompt()
    sol_client = OpenAI(api_key=openai_key, max_retries=0)
    response = sol_client.responses.create(
        model=SOL,
        background=True,
        store=True,
        instructions="Follow the user contract exactly. Return only JSON.",
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        reasoning={"effort": "xhigh"},
        max_output_tokens=12000,
        text={
            "format": {
                "type": "json_schema",
                "name": "s235_background_design_sol",
                "strict": True,
                "schema": schema(SOL),
            },
            "verbosity": "low",
        },
    )
    _write_ledger(
        {
            "status": "SOL_BACKGROUND_IN_PROGRESS",
            "sol": {
                "response_id": response.id,
                "model": response.model,
                "submission_status": response.status,
            },
            "polls": [{"status": response.status}],
            "fable": None,
        }
    )
    started = time.monotonic()
    while response.status not in TERMINAL:
        if time.monotonic() - started >= POLL_DEADLINE_SECONDS:
            raise TimeoutError("S237 background Sol response exceeded polling deadline")
        time.sleep(POLL_SECONDS)
        response = sol_client.responses.retrieve(response.id)
        _append_poll(str(response.status))
    raw_sol = (response.output_text or "").strip()
    if response.status != "completed" or response.model != SOL or not raw_sol:
        raise RuntimeError(
            f"S237 background Sol incomplete: {response.status}/{response.model}"
        )
    sol_review = parse_json(raw_sol)
    sol_pass = validate(sol_review, SOL)

    fable_client = anthropic.Anthropic(api_key=anthropic_key, max_retries=0)
    fable_response = fable_client.messages.create(
        model=FABLE,
        max_tokens=8000,
        system="Follow the user contract exactly. Return only JSON.",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        thinking={"type": "adaptive"},
        output_config={
            "effort": "xhigh",
            "format": {
                "type": "json_schema",
                "schema": anthropic_compatible_schema(schema(FABLE)),
            },
        },
    )
    raw_fable = _fable_text(fable_response)
    if fable_response.model != FABLE or fable_response.stop_reason != "end_turn" or not raw_fable:
        raise RuntimeError(
            f"S237 Fable incomplete: {fable_response.stop_reason}/{fable_response.model}"
        )
    fable_review = parse_json(raw_fable)
    fable_pass = validate(fable_review, FABLE)
    calls = [
        {"provider": "sol", "usage": usage_dict(response)},
        {"provider": "fable", "usage": usage_dict(fable_response)},
    ]
    dual_pass = sol_pass and fable_pass
    ledger_value = _load_ledger()
    ledger_body = {
        key: child
        for key, child in ledger_value.items()
        if key not in {"schema", "result_sha256"}
    }
    ledger_body.update(
        {
            "status": "COMPLETE",
            "sol": {
                "response_id": response.id,
                "model": response.model,
                "submission_status": ledger_body["sol"]["submission_status"],
                "final_status": response.status,
                "usage": usage_dict(response),
                "raw_output": raw_sol,
            },
            "fable": {
                "response_id": fable_response.id,
                "model": fable_response.model,
                "stop_reason": fable_response.stop_reason,
                "usage": usage_dict(fable_response),
                "raw_output": raw_fable,
            },
        }
    )
    _write_ledger(ledger_body)
    write_json(
        RESULT,
        sealed_artifact(
            "s235_design_frontier_reviews_v1",
            {
                "status": "DUAL_PASS" if dual_pass else "NO_GO_NO_CONVERGENCE",
                "reviews": {"sol": sol_review, "fable": fable_review},
                "frontier_calls_with_responses": 2,
                "pre_inference_sync_transport_failures": 2,
                "background_submissions": 1,
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
