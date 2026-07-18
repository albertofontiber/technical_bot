#!/usr/bin/env python3
"""Continue S219 once from its sealed baselines after the 86/85 bug."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.s219_run_omission_pilot as base  # noqa: E402
from src.rag.visual_gold import normalized_text_sha  # noqa: E402


PACKET = ROOT / "evals/s219_omission_generation_packet_v1.json"
PRIOR_RESULT = ROOT / "evals/s219_omission_generation_result_v1.json"
PRIOR_BASELINES = ROOT / "evals/s219_baseline_answer_receipts_v1.json"
PREREG = ROOT / "evals/s220_omission_pilot_continuation_prereg_v1.yaml"
SELECTOR_OUT = ROOT / "evals/s220_omission_selector_receipts_v1.json"
REVISION_OUT = ROOT / "evals/s220_revision_answer_receipts_v1.json"
GENERATION_OUT = ROOT / "evals/s220_omission_generation_result_v1.json"


def verify() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_SINGLE_CONTINUATION_ATTEMPT":
        raise ValueError("S220 continuation is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S220 frozen input drift: {label}")
    prior = base._sealed(PRIOR_RESULT)
    baselines = base._sealed(PRIOR_BASELINES)
    packet = base._sealed(PACKET)
    if (
        prior.get("status") != "HOLD_S219_EXTERNAL_OR_INCOMPLETE"
        or prior.get("reason") != "ValueError: S219 selector geometry drift: 85"
        or prior.get("score_packet_opened") is not False
        or baselines.get("status") != "COMPLETE"
        or len(baselines.get("receipts") or []) != 2
        or any(
            receipt.get("stop_reason") == "max_tokens"
            for receipt in baselines["receipts"]
        )
        or packet.get("status") != "SEALED_NO_SCORE_FACTS"
        or base.SELECTOR_OUT.exists()
        or base.REVISION_OUT.exists()
    ):
        raise ValueError("S219 deterministic continuation boundary drift")
    inherited = {
        receipt["item_id"]: receipt["answer"] for receipt in baselines["receipts"]
    }
    if set(inherited) != {
        "kidde_2xa_interface_tradeoffs",
        "kidde_modulaser_role_selection",
    }:
        raise ValueError("S219 inherited baseline identity drift")
    existing = [
        path.name
        for path in (SELECTOR_OUT, REVISION_OUT, GENERATION_OUT)
        if path.exists()
    ]
    if existing:
        raise ValueError(f"S220 continuation already attempted: {existing}")
    return prereg, packet, inherited


def _write_hold(exc: Exception) -> None:
    if GENERATION_OUT.exists():
        return
    base._checkpoint(
        GENERATION_OUT,
        "s220_omission_generation_result_v1",
        {
            "status": "HOLD_S220_EXTERNAL_OR_INCOMPLETE",
            "reason": f"{type(exc).__name__}: {exc}",
            "score_packet_opened": False,
            "resume": False,
            "provider_retries": 0,
            "target_calls": 0,
            "official_fact_credit": 0,
        },
    )


def execute(
    prereg: dict[str, Any],
    packet: dict[str, Any],
    inherited: dict[str, str],
    env_file: Path,
) -> int:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    key = (
        dotenv_values(env_file).get("ANTHROPIC_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or ""
    ).strip()
    if not key:
        raise RuntimeError("S220 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key, max_retries=0)
    models = prereg["models"]
    prices = prereg["pricing_usd_per_million_tokens"]
    actual = 0.0

    jobs: dict[str, tuple[dict[str, Any], str, str]] = {}
    baselines = dict(inherited)
    for item in packet["items"]:
        system, prompt = base.build_prompt(
            {"question": item["question"], "context": item["context"]}
        )
        jobs[item["item_id"]] = (item, system, prompt)
        if item["baseline_answer"] is not None:
            baselines[item["item_id"]] = item["baseline_answer"]
    if set(baselines) != set(jobs):
        raise ValueError("S220 inherited baseline matrix incomplete")

    selector_jobs: list[tuple[str, int, list[Any], str]] = []
    for item_id, (item, _system, _prompt) in jobs.items():
        grouped = base.units_by_fragment(item["context"])
        for fragment, units in grouped.items():
            selector_jobs.append(
                (
                    item_id,
                    fragment,
                    units,
                    base.prompt_payload(item["question"], baselines[item_id], units),
                )
            )
    if len(selector_jobs) != 85:
        raise ValueError(f"S220 selector geometry drift: {len(selector_jobs)}")

    def selector_call(job: tuple[str, int, list[Any], str]) -> tuple[Any, Any]:
        response = client.messages.create(
            model=models["selector"],
            max_tokens=models["selector_max_output_tokens"],
            system=base.SELECTOR_SYSTEM,
            messages=[{"role": "user", "content": job[3]}],
            output_config=base._format(),
        )
        return job, response

    receipts: list[dict[str, Any]] = []
    selected_by: dict[str, list[Any]] = {item_id: [] for item_id in jobs}
    invalid = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(selector_call, job) for job in selector_jobs]
        for future in as_completed(futures):
            job, response = future.result()
            item_id, fragment, units, _prompt = job
            raw_text = base._text(response)
            usage = base._usage(response)
            call_cost = base._cost(usage, prices["selector"])
            actual += call_cost
            error = None
            try:
                raw = json.loads(raw_text)
                errors = list(
                    Draft202012Validator(base.selector_schema()).iter_errors(raw)
                )
                if errors:
                    raise ValueError(errors[0].message)
                selected = base.validate_selected_ids(raw, units)
            except (json.JSONDecodeError, ValueError) as exc:
                selected = []
                error = str(exc)
                invalid += 1
            selected_by[item_id].extend(selected)
            receipts.append(
                {
                    "item_id": item_id,
                    "fragment_number": fragment,
                    "response_id": response.id,
                    "usage": usage,
                    "cost_usd": round(call_cost, 8),
                    "raw_text": raw_text,
                    "selected_ids": [unit.unit_id for unit in selected],
                    "validation_error": error,
                }
            )
            base._checkpoint(
                SELECTOR_OUT,
                "s220_omission_selector_receipts_v1",
                {"status": "IN_PROGRESS", "receipts": receipts},
            )
    if any(len(units) > 32 for units in selected_by.values()):
        raise ValueError("S220 total selected-unit cap exceeded")
    base._checkpoint(
        SELECTOR_OUT,
        "s220_omission_selector_receipts_v1",
        {"status": "COMPLETE", "invalid_outputs": invalid, "receipts": receipts},
    )

    def revision_call(item_id: str) -> tuple[str, Any, list[Any]]:
        _item, system, prompt = jobs[item_id]
        selected = selected_by[item_id]
        revision_prompt = base.build_revision_prompt(
            prompt, baselines[item_id], base.render_verified_omissions(selected)
        )
        response = client.messages.create(
            model=models["writer"],
            max_tokens=models["writer_max_output_tokens"],
            temperature=0,
            system=system + base.REVISION_POLICY,
            messages=[{"role": "user", "content": revision_prompt}],
        )
        return item_id, response, selected

    candidates = dict(baselines)
    revision_receipts: list[dict[str, Any]] = []
    to_revise = [item_id for item_id, units in selected_by.items() if units]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(revision_call, item_id) for item_id in to_revise]
        for future in as_completed(futures):
            item_id, response, selected = future.result()
            answer = base._text(response)
            usage = base._usage(response)
            call_cost = base._cost(usage, prices["writer"])
            actual += call_cost
            candidates[item_id] = answer
            revision_receipts.append(
                {
                    "item_id": item_id,
                    "response_id": response.id,
                    "selected_unit_ids": [unit.unit_id for unit in selected],
                    "usage": usage,
                    "cost_usd": round(call_cost, 8),
                    "stop_reason": response.stop_reason,
                    "answer": answer,
                    "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
                }
            )
            base._checkpoint(
                REVISION_OUT,
                "s220_revision_answer_receipts_v1",
                {"status": "IN_PROGRESS", "receipts": revision_receipts},
            )
    base._checkpoint(
        REVISION_OUT,
        "s220_revision_answer_receipts_v1",
        {"status": "COMPLETE", "receipts": revision_receipts},
    )

    stops = sum(
        row["stop_reason"] == "max_tokens" for row in revision_receipts
    )
    if actual >= float(prereg["budget"]["internal_stop_usd"]):
        raise RuntimeError(f"S220 actual cost exceeded internal stop: {actual}")
    base._checkpoint(
        GENERATION_OUT,
        "s220_omission_generation_result_v1",
        {
            "status": "COMPLETE_SCORE_NOT_OPENED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "items": [
                {
                    "item_id": item_id,
                    "role": jobs[item_id][0]["role"],
                    "fragment_count": len(jobs[item_id][0]["context"]),
                    "baseline_answer": baselines[item_id],
                    "candidate_answer": candidates[item_id],
                    "selected_unit_ids": [
                        unit.unit_id for unit in selected_by[item_id]
                    ],
                    "candidate_source": (
                        "bounded_revision"
                        if selected_by[item_id]
                        else "baseline_no_omission_selected"
                    ),
                }
                for item_id in jobs
            ],
            "metrics": {
                "inherited_baseline_calls": 2,
                "new_baseline_calls": 0,
                "selector_calls": len(receipts),
                "revision_calls": len(revision_receipts),
                "selected_units": sum(len(value) for value in selected_by.values()),
                "invalid_selector_outputs": invalid,
                "token_limit_stops": stops,
                "s219_inherited_cost_usd": 0.106914,
                "s220_actual_cost_usd": round(actual, 8),
                "actual_cost_usd": round(actual + 0.106914, 8),
            },
            "score_packet_opened": False,
            "provider_retries": 0,
            "target_calls": 0,
            "official_fact_credit": 0,
        },
    )
    print(
        json.dumps(
            {
                "status": "COMPLETE_SCORE_NOT_OPENED",
                "selector_calls": len(receipts),
                "revision_calls": len(revision_receipts),
                "total_cost_usd": round(actual + 0.106914, 8),
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=base.DEFAULT_ENV)
    args = parser.parse_args()
    prereg, packet, inherited = verify()
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "PREFLIGHT_PASS",
                    "inherited_baseline_calls": 2,
                    "new_baseline_calls": 0,
                    "selector_calls": 85,
                    "target_calls": 0,
                    "score_packet_opened": False,
                },
                indent=2,
            )
        )
        return 0
    try:
        return execute(prereg, packet, inherited, args.env_file)
    except Exception as exc:
        _write_hold(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
