#!/usr/bin/env python3
"""Run S173's bounded single-source omission-correction screen."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s156_frontier_synthesis_ceiling import build_prompt
from scripts.s157_post_answer_omission_correction import (
    REVISION_POLICY,
    SELECTOR_SYSTEM,
    build_revision_prompt,
)
from src.rag.omission_correction import (
    invalid_citations,
    point_covered,
    prompt_payload,
    render_verified_omissions,
    selector_schema,
    units_by_fragment,
    validate_selected_ids,
)


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
DEFAULT_PREREG = ROOT / "evals/s173_single_source_omission_correction_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s173_single_source_omission_correction_execution_permit_v1.yaml"
DEFAULT_BASELINE = ROOT / "evals/s173_baseline_answer_receipts_v1.json"
DEFAULT_SELECTOR = ROOT / "evals/s173_omission_selector_receipts_v1.json"
DEFAULT_REVISION = ROOT / "evals/s173_revision_answer_receipts_v1.json"
DEFAULT_RESULT = ROOT / "evals/s173_single_source_omission_correction_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def anthropic_text(response: Any) -> str:
    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    )


def output_format(schema: dict[str, Any]) -> dict[str, Any]:
    return {"format": {"type": "json_schema", "schema": schema}}


def cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        usage.get("input_tokens", 0) * prices["input"]
        + usage.get("output_tokens", 0) * prices["output"]
    ) / 1_000_000


def runtime_chunk(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": item["chunk_id"],
            "content": item["excerpt"],
            "product_model": item["product_model"],
            "source_file": item["source_file"],
            "section_title": item["section_title"],
            "content_type": "specification" if item["stratum"] == "table" else "general",
            "similarity": 1.0,
            "page_number": item["page_number"],
            "document_revision": None,
            "document_revision_date": None,
            "has_diagram": False,
            "diagram_url": None,
        }
    ]


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S173 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise RuntimeError("S173 execution is not permitted")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S173 frozen input drift: {spec['path']}")
    for spec in permit["frozen_artifacts"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S173 permitted artifact drift: {spec['path']}")
    return prereg


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    outputs = (DEFAULT_BASELINE, DEFAULT_SELECTOR, DEFAULT_REVISION, DEFAULT_RESULT)
    if any(path.exists() for path in outputs):
        raise RuntimeError("S173 checkpoint exists; retries are forbidden")
    key = (
        dotenv_values(env_file).get("ANTHROPIC_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or ""
    ).strip()
    if not key:
        raise RuntimeError("S173 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    items = cohort["items"]
    if len(items) != 14 or any(
        key in item for item in items for key in ("answer_points", "exact_quote")
    ):
        raise RuntimeError("S173 generation cohort contains gold or has drifted")

    models = prereg["models"]
    prices = prereg["pricing_usd_per_million_tokens"]
    ceiling = prereg["budget"]["internal_ceiling_usd"]
    actual = 0.0

    baseline_jobs = []
    baseline_input = 0
    for item in items:
        chunks = runtime_chunk(item)
        system, prompt = build_prompt({"question": item["question"], "context": chunks})
        counted = client.messages.count_tokens(
            model=models["writer"],
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ).input_tokens
        baseline_input += counted
        baseline_jobs.append((item, chunks, system, prompt, counted))
    baseline_worst = (
        baseline_input * prices["writer"]["input"]
        + len(baseline_jobs)
        * models["writer_max_output_tokens"]
        * prices["writer"]["output"]
    ) / 1_000_000
    if baseline_worst >= ceiling:
        raise RuntimeError("S173 baseline preflight exceeds budget")

    baseline_receipts = []
    baselines: dict[str, str] = {}
    baseline_stop_failures = 0
    for item, chunks, system, prompt, counted in baseline_jobs:
        response = client.messages.create(
            model=models["writer"],
            max_tokens=models["writer_max_output_tokens"],
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = anthropic_text(response)
        usage = response.usage.model_dump(mode="json")
        call_cost = cost(usage, prices["writer"])
        actual += call_cost
        baseline_stop_failures += int(response.stop_reason == "max_tokens")
        receipt = {
            "item_id": item["item_id"],
            "response_id": response.id,
            "counted_input_tokens": counted,
            "usage": usage,
            "cost_usd": round(call_cost, 8),
            "stop_reason": response.stop_reason,
            "answer": answer,
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        }
        baseline_receipts.append(receipt)
        baselines[item["item_id"]] = answer
        write_json(
            DEFAULT_BASELINE,
            {
                "instrument": "s173_baseline_answer_receipts_v1",
                "status": "IN_PROGRESS",
                "receipts": baseline_receipts,
            },
        )
    write_json(
        DEFAULT_BASELINE,
        {
            "instrument": "s173_baseline_answer_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "receipts": baseline_receipts,
        },
    )

    selector_jobs = []
    selector_input = 0
    worst_revision_input = 0
    for item, chunks, system, base_prompt, _counted in baseline_jobs:
        draft = baselines[item["item_id"]]
        grouped = units_by_fragment(chunks)
        all_units = [unit for units in grouped.values() for unit in units]
        worst_prompt = build_revision_prompt(
            base_prompt, draft, render_verified_omissions(all_units)
        )
        worst_revision_input += client.messages.count_tokens(
            model=models["writer"],
            system=system + REVISION_POLICY,
            messages=[{"role": "user", "content": worst_prompt}],
        ).input_tokens
        for fragment, units in grouped.items():
            prompt = prompt_payload(item["question"], draft, units)
            counted = client.messages.count_tokens(
                model=models["executor"],
                system=SELECTOR_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                output_config=output_format(selector_schema()),
            ).input_tokens
            selector_input += counted
            selector_jobs.append((item, fragment, units, prompt, counted))
    total_worst = baseline_worst + (
        selector_input * prices["executor"]["input"]
        + len(selector_jobs)
        * models["selector_max_output_tokens"]
        * prices["executor"]["output"]
        + worst_revision_input * prices["writer"]["input"]
        + len(items)
        * models["writer_max_output_tokens"]
        * prices["writer"]["output"]
    ) / 1_000_000
    if total_worst >= ceiling:
        raise RuntimeError("S173 full preflight exceeds budget")

    selector_receipts = []
    selected_by: dict[str, list[Any]] = {item["item_id"]: [] for item in items}
    invalid_selector_outputs = 0
    for item, fragment, units, prompt, counted in selector_jobs:
        response = client.messages.create(
            model=models["executor"],
            max_tokens=models["selector_max_output_tokens"],
            system=SELECTOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config=output_format(selector_schema()),
        )
        raw_text = anthropic_text(response)
        usage = response.usage.model_dump(mode="json")
        call_cost = cost(usage, prices["executor"])
        actual += call_cost
        validation_error = None
        try:
            raw = json.loads(raw_text)
            errors = list(Draft202012Validator(selector_schema()).iter_errors(raw))
            if errors:
                raise ValueError(errors[0].message)
            selected = validate_selected_ids(raw, units)
            if len(selected) > prereg["execution"]["selected_units_per_item_max"]:
                raise ValueError("selected-unit cap exceeded")
        except (json.JSONDecodeError, ValueError) as exc:
            selected = []
            validation_error = str(exc)
            invalid_selector_outputs += 1
        selected_by[item["item_id"]].extend(selected)
        selector_receipts.append(
            {
                "item_id": item["item_id"],
                "fragment_number": fragment,
                "response_id": response.id,
                "counted_input_tokens": counted,
                "usage": usage,
                "cost_usd": round(call_cost, 8),
                "raw_text": raw_text,
                "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                "selected_ids": [unit.unit_id for unit in selected],
                "validation_error": validation_error,
            }
        )
        write_json(
            DEFAULT_SELECTOR,
            {
                "instrument": "s173_omission_selector_receipts_v1",
                "status": "IN_PROGRESS",
                "receipts": selector_receipts,
            },
        )
    write_json(
        DEFAULT_SELECTOR,
        {
            "instrument": "s173_omission_selector_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "receipts": selector_receipts,
        },
    )

    revision_receipts = []
    candidates: dict[str, dict[str, Any]] = {}
    revision_stop_failures = 0
    for item, chunks, system, base_prompt, _counted in baseline_jobs:
        item_id = item["item_id"]
        draft = baselines[item_id]
        selected = selected_by[item_id]
        if not selected:
            candidates[item_id] = {
                "answer": draft,
                "source": "baseline_no_omission_selected",
            }
            continue
        prompt = build_revision_prompt(
            base_prompt, draft, render_verified_omissions(selected)
        )
        counted = client.messages.count_tokens(
            model=models["writer"],
            system=system + REVISION_POLICY,
            messages=[{"role": "user", "content": prompt}],
        ).input_tokens
        response = client.messages.create(
            model=models["writer"],
            max_tokens=models["writer_max_output_tokens"],
            temperature=0,
            system=system + REVISION_POLICY,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = anthropic_text(response)
        usage = response.usage.model_dump(mode="json")
        call_cost = cost(usage, prices["writer"])
        actual += call_cost
        revision_stop_failures += int(response.stop_reason == "max_tokens")
        receipt = {
            "item_id": item_id,
            "response_id": response.id,
            "counted_input_tokens": counted,
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
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        }
        revision_receipts.append(receipt)
        candidates[item_id] = {"answer": answer, "source": "bounded_revision"}
        write_json(
            DEFAULT_REVISION,
            {
                "instrument": "s173_revision_answer_receipts_v1",
                "status": "IN_PROGRESS",
                "receipts": revision_receipts,
            },
        )
    write_json(
        DEFAULT_REVISION,
        {
            "instrument": "s173_revision_answer_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "receipts": revision_receipts,
        },
    )

    # Gold is deliberately loaded only after all generation checkpoints exist.
    gold_payload = json.loads(GOLD.read_text(encoding="utf-8"))
    gold_by = {row["item_id"]: row for row in gold_payload["items"] if row["eligible"]}
    rows = []
    baseline_points = candidate_points = 0
    baseline_complete = candidate_complete = regressions = 0
    invalid_answer_citations = 0
    for item in items:
        item_id = item["item_id"]
        points = gold_by[item_id]["answer_points"]
        baseline = baselines[item_id]
        candidate = candidates[item_id]["answer"]
        base_hits = [point_covered(baseline, point) for point in points]
        candidate_hits = [point_covered(candidate, point) for point in points]
        regressed = sum(
            before and not after for before, after in zip(base_hits, candidate_hits)
        )
        baseline_points += sum(base_hits)
        candidate_points += sum(candidate_hits)
        baseline_complete += int(all(base_hits))
        candidate_complete += int(all(candidate_hits))
        regressions += regressed
        invalid_base = invalid_citations(baseline, 1)
        invalid_candidate = invalid_citations(candidate, 1)
        invalid_answer_citations += len(invalid_base) + len(invalid_candidate)
        rows.append(
            {
                "item_id": item_id,
                "stratum": item["stratum"],
                "answer_points": len(points),
                "baseline_points_covered": sum(base_hits),
                "candidate_points_covered": sum(candidate_hits),
                "baseline_complete": all(base_hits),
                "candidate_complete": all(candidate_hits),
                "regressed_points": regressed,
                "selected_units": len(selected_by[item_id]),
                "candidate_source": candidates[item_id]["source"],
                "baseline_invalid_citations": invalid_base,
                "candidate_invalid_citations": invalid_candidate,
            }
        )
    point_gain = candidate_points - baseline_points
    complete_gain = candidate_complete - baseline_complete
    selected_total = sum(len(units) for units in selected_by.values())
    checks = {
        "all_14_items_scored": len(rows) == 14,
        "point_gain_gte_4": point_gain >= 4,
        "complete_question_gain_gte_2": complete_gain >= 2,
        "regressed_points_zero": regressions == 0,
        "invalid_selector_outputs_zero": invalid_selector_outputs == 0,
        "invalid_answer_citations_zero": invalid_answer_citations == 0,
        "token_limit_stops_zero": baseline_stop_failures + revision_stop_failures == 0,
        "at_least_one_source_unit_selected": selected_total > 0,
        "actual_cost_below_ceiling": actual < ceiling,
    }
    passed = all(checks.values())
    body = {
        "instrument": "s173_single_source_omission_correction_v1",
        "status": "GO_TO_BLINDED_SOL_SEMANTIC_GATE" if passed else "NO_GO",
        "population": {
            "items": len(items),
            "manufacturers": len({row["manufacturer"] for row in items}),
            "table": sum(row["stratum"] == "table" for row in items),
            "prose": sum(row["stratum"] == "prose" for row in items),
            "answer_points": sum(len(row["answer_points"]) for row in gold_by.values()),
            "target_question_overlap": 0,
            "gold_loaded_after_generation_checkpoints": True,
        },
        "metrics": {
            "baseline_points_covered": baseline_points,
            "candidate_points_covered": candidate_points,
            "point_gain": point_gain,
            "baseline_questions_complete": baseline_complete,
            "candidate_questions_complete": candidate_complete,
            "complete_question_gain": complete_gain,
            "regressed_points": regressions,
            "selected_units": selected_total,
            "revised_items": len(revision_receipts),
            "invalid_selector_outputs": invalid_selector_outputs,
            "invalid_answer_citations": invalid_answer_citations,
            "token_limit_stops": baseline_stop_failures + revision_stop_failures,
        },
        "checks": checks,
        "rows": rows,
        "cost": {
            "worst_case_preflight_usd": round(total_worst, 8),
            "actual_usd": round(actual, 8),
            "baseline_calls": len(baseline_receipts),
            "selector_calls": len(selector_receipts),
            "revision_calls": len(revision_receipts),
        },
        "decision": {
            "blinded_sol_semantic_gate": passed,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    write_json(DEFAULT_RESULT, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute:
        cohort = json.loads(COHORT.read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "items": len(cohort["items"]),
                    "selector_schema": selector_schema(),
                }
            )
        )
        return 0
    prereg = validate_authorization(DEFAULT_PREREG, DEFAULT_PERMIT)
    print(json.dumps(execute(prereg, args.env_file), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
