#!/usr/bin/env python3
"""Run S219 generation without importing or opening its score packet."""
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

from scripts.s156_frontier_synthesis_ceiling import build_prompt  # noqa: E402
from scripts.s157_post_answer_omission_correction import (  # noqa: E402
    REVISION_POLICY,
    SELECTOR_SYSTEM,
    build_revision_prompt,
)
from src.rag.omission_correction import (  # noqa: E402
    prompt_payload,
    render_verified_omissions,
    selector_schema,
    units_by_fragment,
    validate_selected_ids,
)
from src.rag.visual_gold import (  # noqa: E402
    normalized_text_sha,
    sealed_artifact,
    stable_sha,
    write_json,
)


PACKET = ROOT / "evals/s219_omission_generation_packet_v1.json"
PREREG = ROOT / "evals/s219_omission_pilot_prereg_v1.yaml"
BASELINE_OUT = ROOT / "evals/s219_baseline_answer_receipts_v1.json"
SELECTOR_OUT = ROOT / "evals/s219_omission_selector_receipts_v1.json"
REVISION_OUT = ROOT / "evals/s219_revision_answer_receipts_v1.json"
GENERATION_OUT = ROOT / "evals/s219_omission_generation_result_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _text(response: Any) -> str:
    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    )


def _usage(response: Any) -> dict[str, Any]:
    return response.usage.model_dump(mode="json")


def _cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        usage.get("input_tokens", 0) * prices["input"]
        + usage.get("output_tokens", 0) * prices["output"]
    ) / 1_000_000


def _format() -> dict[str, Any]:
    return {"format": {"type": "json_schema", "schema": selector_schema()}}


def _checkpoint(path: Path, schema: str, body: dict[str, Any]) -> None:
    write_json(path, sealed_artifact(schema, body))


def _forbidden_generation_keys(value: Any) -> list[str]:
    forbidden = {
        "facts",
        "atomic_facts",
        "answer_points",
        "gold_answer",
        "expected_fact",
        "baseline_class",
    }
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                found.append(key)
            found.extend(_forbidden_generation_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_forbidden_generation_keys(child))
    return found


def verify_prereg() -> tuple[dict[str, Any], dict[str, Any]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S219 preregistration is not frozen")
    for label, spec in prereg["frozen_generation_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S219 frozen generation input drift: {label}")
    packet = _sealed(PACKET)
    if (
        packet.get("status") != "SEALED_NO_SCORE_FACTS"
        or packet["population"]
        != {
            "items": 9,
            "historical_multichunk_development": 7,
            "kidde_multisource_guardrail": 2,
            "canonical_targets": 0,
        }
        or _forbidden_generation_keys(packet)
    ):
        raise ValueError("S219 generation packet isolation or geometry drift")
    if prereg["models"] != {
        "selector": "claude-haiku-4-5-20251001",
        "writer": "claude-sonnet-4-6",
        "selector_max_output_tokens": 500,
        "writer_max_output_tokens": 2200,
    }:
        raise ValueError("S219 model contract drift")
    return prereg, packet


def _write_hold(exc: Exception) -> None:
    if GENERATION_OUT.exists():
        return
    _checkpoint(
        GENERATION_OUT,
        "s219_omission_generation_result_v1",
        {
            "status": "HOLD_S219_EXTERNAL_OR_INCOMPLETE",
            "reason": f"{type(exc).__name__}: {exc}",
            "score_packet_opened": False,
            "resume": False,
            "provider_retries": 0,
            "official_fact_credit": 0,
            "target_calls": 0,
        },
    )


def execute(prereg: dict[str, Any], packet: dict[str, Any], env_file: Path) -> int:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    planned = (BASELINE_OUT, SELECTOR_OUT, REVISION_OUT, GENERATION_OUT)
    existing = [path.name for path in planned if path.exists()]
    if existing:
        raise RuntimeError(f"S219 generation already attempted: {existing}")
    key = (
        dotenv_values(env_file).get("ANTHROPIC_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or ""
    ).strip()
    if not key:
        raise RuntimeError("S219 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key, max_retries=0)
    models = prereg["models"]
    prices = prereg["pricing_usd_per_million_tokens"]
    actual = 0.0

    jobs: dict[str, tuple[dict[str, Any], str, str]] = {}
    baselines: dict[str, str] = {}
    for item in packet["items"]:
        system, prompt = build_prompt(
            {"question": item["question"], "context": item["context"]}
        )
        jobs[item["item_id"]] = (item, system, prompt)
        if item["baseline_answer"] is not None:
            baselines[item["item_id"]] = item["baseline_answer"]

    baseline_receipts: list[dict[str, Any]] = []
    external = [job for job in jobs.values() if job[0]["baseline_answer"] is None]

    def baseline_call(job: tuple[dict[str, Any], str, str]) -> tuple[str, Any]:
        item, system, prompt = job
        response = client.messages.create(
            model=models["writer"],
            max_tokens=models["writer_max_output_tokens"],
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return item["item_id"], response

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(baseline_call, job) for job in external]
        for future in as_completed(futures):
            item_id, response = future.result()
            answer = _text(response)
            usage = _usage(response)
            call_cost = _cost(usage, prices["writer"])
            actual += call_cost
            baselines[item_id] = answer
            baseline_receipts.append(
                {
                    "item_id": item_id,
                    "response_id": response.id,
                    "usage": usage,
                    "cost_usd": round(call_cost, 8),
                    "stop_reason": response.stop_reason,
                    "answer": answer,
                    "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
                }
            )
            _checkpoint(
                BASELINE_OUT,
                "s219_baseline_answer_receipts_v1",
                {"status": "IN_PROGRESS", "receipts": baseline_receipts},
            )
    _checkpoint(
        BASELINE_OUT,
        "s219_baseline_answer_receipts_v1",
        {
            "status": "COMPLETE",
            "historical_reused": 7,
            "contemporary_generated": 2,
            "receipts": baseline_receipts,
        },
    )

    selector_jobs: list[tuple[str, int, list[Any], str]] = []
    units_by_item: dict[str, dict[int, list[Any]]] = {}
    for item_id, (item, _system, _prompt) in jobs.items():
        grouped = units_by_fragment(item["context"])
        units_by_item[item_id] = grouped
        for fragment, units in grouped.items():
            selector_jobs.append(
                (
                    item_id,
                    fragment,
                    units,
                    prompt_payload(item["question"], baselines[item_id], units),
                )
            )
    if len(selector_jobs) != 86:
        raise ValueError(f"S219 selector geometry drift: {len(selector_jobs)}")

    def selector_call(job: tuple[str, int, list[Any], str]) -> tuple[Any, Any]:
        response = client.messages.create(
            model=models["selector"],
            max_tokens=models["selector_max_output_tokens"],
            system=SELECTOR_SYSTEM,
            messages=[{"role": "user", "content": job[3]}],
            output_config=_format(),
        )
        return job, response

    selector_receipts: list[dict[str, Any]] = []
    selected_by: dict[str, list[Any]] = {item_id: [] for item_id in jobs}
    invalid_selectors = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(selector_call, job) for job in selector_jobs]
        for future in as_completed(futures):
            job, response = future.result()
            item_id, fragment, units, _prompt = job
            raw_text = _text(response)
            usage = _usage(response)
            call_cost = _cost(usage, prices["selector"])
            actual += call_cost
            error = None
            try:
                raw = json.loads(raw_text)
                errors = list(
                    Draft202012Validator(selector_schema()).iter_errors(raw)
                )
                if errors:
                    raise ValueError(errors[0].message)
                selected = validate_selected_ids(raw, units)
            except (json.JSONDecodeError, ValueError) as exc:
                selected = []
                error = str(exc)
                invalid_selectors += 1
            selected_by[item_id].extend(selected)
            selector_receipts.append(
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
            _checkpoint(
                SELECTOR_OUT,
                "s219_omission_selector_receipts_v1",
                {"status": "IN_PROGRESS", "receipts": selector_receipts},
            )
    if any(len(units) > 32 for units in selected_by.values()):
        raise ValueError("S219 total selected-unit cap exceeded")
    _checkpoint(
        SELECTOR_OUT,
        "s219_omission_selector_receipts_v1",
        {
            "status": "COMPLETE",
            "invalid_outputs": invalid_selectors,
            "receipts": selector_receipts,
        },
    )

    def revision_call(item_id: str) -> tuple[str, Any, list[Any]]:
        item, system, base_prompt = jobs[item_id]
        selected = selected_by[item_id]
        prompt = build_revision_prompt(
            base_prompt, baselines[item_id], render_verified_omissions(selected)
        )
        response = client.messages.create(
            model=models["writer"],
            max_tokens=models["writer_max_output_tokens"],
            temperature=0,
            system=system + REVISION_POLICY,
            messages=[{"role": "user", "content": prompt}],
        )
        return item_id, response, selected

    candidates = dict(baselines)
    revision_receipts: list[dict[str, Any]] = []
    to_revise = [item_id for item_id, units in selected_by.items() if units]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(revision_call, item_id) for item_id in to_revise]
        for future in as_completed(futures):
            item_id, response, selected = future.result()
            answer = _text(response)
            usage = _usage(response)
            call_cost = _cost(usage, prices["writer"])
            actual += call_cost
            candidates[item_id] = answer
            revision_receipts.append(
                {
                    "item_id": item_id,
                    "response_id": response.id,
                    "selected_unit_ids": [unit.unit_id for unit in selected],
                    "selected_unit_receipts": [
                        {
                            "unit_id": unit.unit_id,
                            "fragment_number": unit.fragment_number,
                            "source_spans": [list(span) for span in unit.source_spans],
                            "content_sha256": unit.content_sha256,
                        }
                        for unit in selected
                    ],
                    "usage": usage,
                    "cost_usd": round(call_cost, 8),
                    "stop_reason": response.stop_reason,
                    "answer": answer,
                    "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
                }
            )
            _checkpoint(
                REVISION_OUT,
                "s219_revision_answer_receipts_v1",
                {"status": "IN_PROGRESS", "receipts": revision_receipts},
            )
    _checkpoint(
        REVISION_OUT,
        "s219_revision_answer_receipts_v1",
        {"status": "COMPLETE", "receipts": revision_receipts},
    )

    stops = sum(
        receipt["stop_reason"] == "max_tokens"
        for receipt in baseline_receipts + revision_receipts
    )
    if actual >= float(prereg["budget"]["internal_stop_usd"]):
        raise RuntimeError(f"S219 actual cost exceeded internal stop: {actual}")
    _checkpoint(
        GENERATION_OUT,
        "s219_omission_generation_result_v1",
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
                "baseline_calls": len(baseline_receipts),
                "selector_calls": len(selector_receipts),
                "revision_calls": len(revision_receipts),
                "selected_units": sum(len(value) for value in selected_by.values()),
                "invalid_selector_outputs": invalid_selectors,
                "token_limit_stops": stops,
                "actual_cost_usd": round(actual, 8),
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
                "selector_calls": len(selector_receipts),
                "revision_calls": len(revision_receipts),
                "cost_usd": round(actual, 8),
            },
            indent=2,
        )
    )
    return 0


def preflight(prereg: dict[str, Any], packet: dict[str, Any]) -> int:
    chars = sum(
        len(item["question"])
        + sum(len(chunk["content"]) for chunk in item["context"])
        + len(item["baseline_answer"] or "")
        for item in packet["items"]
    )
    conservative_tokens = chars // 2 + 9 * 2200 + 86 * 500
    conservative_cost = conservative_tokens * 15 / 1_000_000
    if conservative_cost >= float(prereg["budget"]["internal_stop_usd"]):
        raise ValueError("S219 conservative preflight exceeds budget")
    print(
        json.dumps(
            {
                "status": "PREFLIGHT_PASS",
                "items": 9,
                "selector_calls": 86,
                "canonical_targets": 0,
                "score_packet_opened": False,
                "conservative_cost_bound_usd": round(conservative_cost, 4),
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    prereg, packet = verify_prereg()
    if not args.execute:
        return preflight(prereg, packet)
    try:
        return execute(prereg, packet, args.env_file)
    except Exception as exc:
        _write_hold(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
