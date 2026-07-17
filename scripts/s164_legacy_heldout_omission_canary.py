#!/usr/bin/env python3
"""Run the bounded S164 legacy held-out omission-correction canary."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
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
    _anthropic_text,
    _cost,
    _format,
    build_revision_prompt,
)
from src.rag.omission_correction import (
    invalid_citations,
    prompt_payload,
    render_verified_omissions,
    selector_schema,
    units_by_fragment,
    validate_selected_ids,
)


ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = ROOT / "evals/s63ho_treat_frozen_contexts.json"
GENERATIONS = ROOT / "evals/s63ho_treat_generations.json"
GOLD = ROOT / "evals/gold_answers_v1.yaml"
DEFAULT_PREREG = ROOT / "evals/s164_legacy_heldout_omission_canary_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s164_legacy_heldout_omission_canary_execution_permit_v1.yaml"
DEFAULT_SELECTOR = ROOT / "evals/s164_legacy_heldout_selector_receipts_v1.json"
DEFAULT_REVISION = ROOT / "evals/s164_legacy_heldout_revision_receipt_v1.json"
DEFAULT_RESULT = ROOT / "evals/s164_legacy_heldout_omission_canary_v1.json"
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


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _has(value: str, *patterns: str) -> bool:
    folded = _fold(value)
    return all(re.search(pattern, folded) for pattern in patterns)


def score_atomic_facts(answer: str) -> list[dict[str, Any]]:
    """Evaluation-only oracle frozen from the ten pre-existing ho008 facts."""
    checks = (
        (
            "base_loops_devices",
            (r"\b2\s+lazos?\b", r"\b500\s+dispositivos?\b", r"\b250\b[^.\n]{0,80}\b(?:por|cada)\s+lazo\b"),
        ),
        (
            "zones_areas_groups",
            (r"\b2[. ]?000\s+zonas?\b", r"\b250\s+areas?\b", r"\b1[. ]?000\s+grupos?\b"),
        ),
        (
            "devices_per_loop",
            (r"\b250\s+dispositivos?\b", r"\b(?:por|cada)\s+lazo\b"),
        ),
        (
            "absolute_zone_limit",
            (r"\b(?:maxim\w*|limite|absolut\w*)\b[^.\n]{0,100}\b2[. ]?000\s+zonas?\b",),
        ),
        (
            "three_tbud_cards",
            (r"\b3\s+(?:tarjetas?|placas?)\b", r"\btbud-?ng\b", r"\b2\s+lazos?\b"),
        ),
        ("eight_loops", (r"\b(?:hasta|maxim\w*)\s+8\s+lazos?\b",)),
        (
            "network_64_nodes",
            (r"\b(?:t-?network|rs\s*485|red)\b", r"\b64\s+nodos?\b"),
        ),
        (
            "network_512k_devices",
            (r"(?:>|mas\s+de)\s*512[. ]?000\s+dispositivos?",),
        ),
        (
            "zone_32_initiating_elements",
            (r"\b32\s+elementos?\b", r"\b(?:iniciacion|alarma)\b", r"\bzona\b"),
        ),
        (
            "ethernet_and_usb",
            (r"\bethernet\b", r"\busb\b"),
        ),
    )
    return [
        {"fact_id": fact_id, "covered": _has(answer, *patterns)}
        for fact_id, patterns in checks
    ]


def load_population() -> dict[str, Any]:
    contexts = json.loads(CONTEXTS.read_text(encoding="utf-8"))["ho008"]
    generations = json.loads(GENERATIONS.read_text(encoding="utf-8"))["ho008"]
    gold = next(
        row
        for row in yaml.safe_load(GOLD.read_text(encoding="utf-8"))
        if row["qid"] == "ho008"
    )
    chunks = []
    for row in contexts["top5"]:
        chunks.append(
            {
                **row,
                "document_revision": row.get("document_revision"),
                "document_revision_date": row.get("document_revision_date"),
            }
        )
    if len(chunks) != 5 or len(gold["atomic_facts"]) != 10:
        raise RuntimeError("S164 frozen population drift")
    return {
        "qid": "ho008",
        "question": contexts["question"],
        "chunks": chunks,
        "draft": generations["0"]["answer"],
        "draft_stop_reason": generations["0"]["stop_reason"],
    }


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S164 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise RuntimeError("S164 execution is not permitted")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S164 frozen input drift: {spec['path']}")
    for spec in permit["frozen_artifacts"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S164 permitted artifact drift: {spec['path']}")
    return prereg


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    if any(path.exists() for path in (DEFAULT_SELECTOR, DEFAULT_REVISION, DEFAULT_RESULT)):
        raise RuntimeError("S164 checkpoint exists; retries are forbidden")
    key = (
        dotenv_values(env_file).get("ANTHROPIC_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or ""
    ).strip()
    if not key:
        raise RuntimeError("S164 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    population = load_population()
    model = prereg["models"]
    prices = prereg["pricing_usd_per_million_tokens"]
    ceiling = prereg["budget"]["internal_ceiling_usd"]
    grouped = units_by_fragment(population["chunks"])

    jobs = []
    selector_input = 0
    for fragment, units in grouped.items():
        prompt = prompt_payload(population["question"], population["draft"], units)
        counted = client.messages.count_tokens(
            model=model["executor"],
            system=SELECTOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config=_format(selector_schema()),
        ).input_tokens
        selector_input += counted
        jobs.append((fragment, units, prompt, counted))

    system, base_prompt = build_prompt(
        {"question": population["question"], "context": population["chunks"]}
    )
    worst_units = [
        unit
        for units in grouped.values()
        for unit in sorted(units, key=lambda item: -len(item.content))[:8]
    ]
    worst_revision_prompt = build_revision_prompt(
        base_prompt,
        population["draft"],
        render_verified_omissions(worst_units),
    )
    revision_input = client.messages.count_tokens(
        model=model["writer"],
        system=system + REVISION_POLICY,
        messages=[{"role": "user", "content": worst_revision_prompt}],
    ).input_tokens
    worst = (
        selector_input * prices["executor"]["input"]
        + len(jobs) * model["selector_max_output_tokens"] * prices["executor"]["output"]
        + revision_input * prices["writer"]["input"]
        + model["writer_max_output_tokens"] * prices["writer"]["output"]
    ) / 1_000_000
    if worst >= ceiling:
        raise RuntimeError("S164 preflight exceeds budget")

    receipts = []
    selected = []
    invalid_outputs = 0
    actual = 0.0
    for fragment, units, prompt, counted in jobs:
        response = client.messages.create(
            model=model["executor"],
            max_tokens=model["selector_max_output_tokens"],
            system=SELECTOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config=_format(selector_schema()),
        )
        text = _anthropic_text(response)
        usage = response.usage.model_dump(mode="json")
        cost = _cost(usage, prices["executor"])
        actual += cost
        error = None
        try:
            raw = json.loads(text)
            errors = list(Draft202012Validator(selector_schema()).iter_errors(raw))
            if errors:
                raise ValueError(errors[0].message)
            rows = validate_selected_ids(raw, units)
        except (json.JSONDecodeError, ValueError) as exc:
            rows = []
            error = str(exc)
            invalid_outputs += 1
        selected.extend(rows)
        receipts.append(
            {
                "fragment_number": fragment,
                "response_id": response.id,
                "counted_input_tokens": counted,
                "usage": usage,
                "cost_usd": round(cost, 8),
                "raw_text": text,
                "raw_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "selected_ids": [row.unit_id for row in rows],
                "validation_error": error,
            }
        )
        _write(
            DEFAULT_SELECTOR,
            {
                "instrument": "s164_legacy_heldout_selector_receipts_v1",
                "status": "IN_PROGRESS",
                "receipts": receipts,
            },
        )
    _write(
        DEFAULT_SELECTOR,
        {
            "instrument": "s164_legacy_heldout_selector_receipts_v1",
            "status": "COMPLETE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "receipts": receipts,
        },
    )

    if selected:
        revision_prompt = build_revision_prompt(
            base_prompt,
            population["draft"],
            render_verified_omissions(selected),
        )
        counted = client.messages.count_tokens(
            model=model["writer"],
            system=system + REVISION_POLICY,
            messages=[{"role": "user", "content": revision_prompt}],
        ).input_tokens
        response = client.messages.create(
            model=model["writer"],
            max_tokens=model["writer_max_output_tokens"],
            temperature=model["writer_temperature"],
            system=system + REVISION_POLICY,
            messages=[{"role": "user", "content": revision_prompt}],
        )
        candidate = _anthropic_text(response)
        usage = response.usage.model_dump(mode="json")
        revision_cost = _cost(usage, prices["writer"])
        actual += revision_cost
        revision_receipt = {
            "response_id": response.id,
            "counted_input_tokens": counted,
            "selected_unit_receipts": [
                {
                    "unit_id": row.unit_id,
                    "fragment_number": row.fragment_number,
                    "source_spans": [list(span) for span in row.source_spans],
                    "content_sha256": row.content_sha256,
                }
                for row in selected
            ],
            "usage": usage,
            "cost_usd": round(revision_cost, 8),
            "stop_reason": response.stop_reason,
            "answer": candidate,
            "answer_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        }
        candidate_source = "bounded_revision"
    else:
        candidate = population["draft"]
        revision_receipt = {
            "response_id": None,
            "selected_unit_receipts": [],
            "cost_usd": 0,
            "stop_reason": None,
            "answer": candidate,
            "answer_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        }
        candidate_source = "baseline_no_omission_selected"
    _write(
        DEFAULT_REVISION,
        {
            "instrument": "s164_legacy_heldout_revision_receipt_v1",
            "status": "COMPLETE",
            **revision_receipt,
        },
    )

    baseline_rows = score_atomic_facts(population["draft"])
    candidate_rows = score_atomic_facts(candidate)
    baseline_by = {row["fact_id"]: row["covered"] for row in baseline_rows}
    candidate_by = {row["fact_id"]: row["covered"] for row in candidate_rows}
    baseline_points = sum(baseline_by.values())
    candidate_points = sum(candidate_by.values())
    regressed = [
        fact_id
        for fact_id, covered in baseline_by.items()
        if covered and not candidate_by[fact_id]
    ]
    invalid = invalid_citations(candidate, len(population["chunks"]))
    checks = {
        "point_gain_gte_2": candidate_points - baseline_points >= 2,
        "regressed_points_zero": not regressed,
        "invalid_selector_outputs_zero": invalid_outputs == 0,
        "invalid_answer_citations_zero": not invalid,
        "selected_units_gte_1": len(selected) >= 1,
        "actual_cost_below_ceiling": actual < ceiling,
    }
    passed = all(checks.values())
    body: dict[str, Any] = {
        "instrument": "s164_legacy_heldout_omission_canary_v1",
        "status": "GO_TO_LARGER_LEGACY_HELDOUT_TEST" if passed else "NO_GO",
        "population": {
            "qid": "ho008",
            "fragments": len(population["chunks"]),
            "atomic_facts": len(baseline_rows),
            "historical_drafts_used": 1,
            "target_question_overlap": 0,
        },
        "metrics": {
            "baseline_points_covered": baseline_points,
            "candidate_points_covered": candidate_points,
            "point_gain": candidate_points - baseline_points,
            "regressed_fact_ids": regressed,
            "selected_units": len(selected),
            "invalid_selector_outputs": invalid_outputs,
            "invalid_candidate_citations": invalid,
            "candidate_source": candidate_source,
        },
        "fact_rows": [
            {
                "fact_id": fact_id,
                "baseline_covered": baseline_by[fact_id],
                "candidate_covered": candidate_by[fact_id],
            }
            for fact_id in baseline_by
        ],
        "checks": checks,
        "cost": {
            "worst_case_preflight_usd": round(worst, 8),
            "actual_usd": round(actual, 8),
        },
        "decision": {
            "larger_heldout_test": passed,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
            "same_canary_tuning": False,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    _write(DEFAULT_RESULT, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute:
        population = load_population()
        print(
            json.dumps(
                {
                    "qid": population["qid"],
                    "fragments": len(population["chunks"]),
                    "draft_sha256": hashlib.sha256(
                        population["draft"].encode()
                    ).hexdigest(),
                    "baseline_local_points": sum(
                        row["covered"] for row in score_atomic_facts(population["draft"])
                    ),
                }
            )
        )
        return 0
    prereg = validate_authorization(DEFAULT_PREREG, DEFAULT_PERMIT)
    print(json.dumps(execute(prereg, args.env_file), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
