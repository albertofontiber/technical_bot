#!/usr/bin/env python3
"""Write bounded addenda from S220's blind selections without opening golds."""
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


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.s219_run_omission_pilot as prior  # noqa: E402
from src.rag.omission_correction import invalid_citations  # noqa: E402
from src.rag.visual_gold import normalized_text_sha  # noqa: E402


PACKET = ROOT / "evals/s219_omission_generation_packet_v1.json"
BASELINES = ROOT / "evals/s219_baseline_answer_receipts_v1.json"
SELECTIONS = ROOT / "evals/s220_omission_selector_receipts_v1.json"
PREREG = ROOT / "evals/s222_monotonic_addendum_prereg_v1.yaml"
RECEIPTS = ROOT / "evals/s222_monotonic_addendum_receipts_v1.json"
GENERATION = ROOT / "evals/s222_monotonic_addendum_generation_v1.json"

SYSTEM = """Eres un redactor técnico de correcciones aditivas. Recibes una pregunta,
un borrador que NO debes reescribir y unidades fuente que un detector ya marcó
como materialmente omitidas. Devuelve solo precisiones adicionales, breves y no
redundantes, explícitamente apoyadas por esas unidades. Cita cada precisión con
[F#]. No repitas el borrador, no añadas conocimiento externo, no menciones IDs
internos ni el proceso de evaluación. Devuelve únicamente el JSON requerido."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["addendum"],
    "properties": {"addendum": {"type": "string"}},
}


def verify() -> tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, list[Any]]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S222 preregistration is not frozen")
    for label, spec in prereg["frozen_generation_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S222 frozen generation input drift: {label}")
    packet = prior._sealed(PACKET)
    baseline_receipts = prior._sealed(BASELINES)
    selections = prior._sealed(SELECTIONS)
    if (
        packet.get("status") != "SEALED_NO_SCORE_FACTS"
        or baseline_receipts.get("status") != "COMPLETE"
        or selections.get("status") != "COMPLETE"
        or selections.get("invalid_outputs") != 0
        or len(selections.get("receipts") or []) != 85
    ):
        raise ValueError("S222 inherited blind input boundary drift")
    baselines = {
        item["item_id"]: item["baseline_answer"]
        for item in packet["items"]
        if item["baseline_answer"] is not None
    }
    baselines.update(
        {row["item_id"]: row["answer"] for row in baseline_receipts["receipts"]}
    )
    selected_ids: dict[str, list[str]] = {item["item_id"]: [] for item in packet["items"]}
    for receipt in selections["receipts"]:
        selected_ids[receipt["item_id"]].extend(receipt["selected_ids"])
    selected_units: dict[str, list[Any]] = {}
    for item in packet["items"]:
        units = {
            unit.unit_id: unit
            for rows in prior.units_by_fragment(item["context"]).values()
            for unit in rows
        }
        if not set(selected_ids[item["item_id"]]).issubset(units):
            raise ValueError(f"S222 unknown inherited unit: {item['item_id']}")
        selected_units[item["item_id"]] = [
            units[unit_id] for unit_id in selected_ids[item["item_id"]]
        ]
    if set(baselines) != set(selected_units) or any(not units for units in selected_units.values()):
        raise ValueError("S222 baseline or selection matrix incomplete")
    return prereg, packet, baselines, selected_units


def execute(
    prereg: dict[str, Any],
    packet: dict[str, Any],
    baselines: dict[str, str],
    selected: dict[str, list[Any]],
    env_file: Path,
) -> int:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    if RECEIPTS.exists() or GENERATION.exists():
        raise RuntimeError("S222 already attempted")
    key = (
        dotenv_values(env_file).get("ANTHROPIC_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or ""
    ).strip()
    if not key:
        raise RuntimeError("S222 ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key, max_retries=0)
    model = prereg["model"]
    prices = prereg["pricing_usd_per_million_tokens"]
    by_item = {item["item_id"]: item for item in packet["items"]}

    def call(item_id: str) -> tuple[str, Any]:
        payload = json.dumps(
            {
                "question": by_item[item_id]["question"],
                "draft_answer": baselines[item_id],
                "selected_source_units": [
                    {
                        "fragment_number": unit.fragment_number,
                        "content": unit.content,
                    }
                    for unit in selected[item_id]
                ],
            },
            ensure_ascii=False,
        )
        response = client.messages.create(
            model=model["id"],
            max_tokens=model["max_output_tokens"],
            temperature=0,
            system=SYSTEM,
            messages=[{"role": "user", "content": payload}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
        return item_id, response

    receipts = []
    rows = []
    actual = 0.0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(call, item_id) for item_id in selected]
        for future in as_completed(futures):
            item_id, response = future.result()
            raw = prior._text(response)
            value = json.loads(raw)
            addendum = str(value.get("addendum") or "").strip()
            if not addendum:
                raise ValueError(f"S222 empty addendum: {item_id}")
            invalid = invalid_citations(addendum, len(by_item[item_id]["context"]))
            if invalid:
                raise ValueError(f"S222 invalid addendum citations {item_id}: {invalid}")
            baseline = baselines[item_id]
            candidate = baseline + "\n\n### Precisiones adicionales\n\n" + addendum
            if not candidate.startswith(baseline):
                raise ValueError("S222 monotonic prefix invariant failed")
            usage = prior._usage(response)
            cost = prior._cost(usage, prices)
            actual += cost
            receipts.append(
                {
                    "item_id": item_id,
                    "response_id": response.id,
                    "usage": usage,
                    "cost_usd": round(cost, 8),
                    "stop_reason": response.stop_reason,
                    "addendum": addendum,
                    "addendum_sha256": hashlib.sha256(addendum.encode()).hexdigest(),
                }
            )
            rows.append(
                {
                    "item_id": item_id,
                    "role": by_item[item_id]["role"],
                    "fragment_count": len(by_item[item_id]["context"]),
                    "baseline_answer": baseline,
                    "candidate_answer": candidate,
                    "selected_unit_ids": [unit.unit_id for unit in selected[item_id]],
                    "candidate_source": "monotonic_addendum",
                }
            )
            prior._checkpoint(
                RECEIPTS,
                "s222_monotonic_addendum_receipts_v1",
                {"status": "IN_PROGRESS", "receipts": receipts},
            )
    prior._checkpoint(
        RECEIPTS,
        "s222_monotonic_addendum_receipts_v1",
        {"status": "COMPLETE", "receipts": receipts},
    )
    stops = sum(row["stop_reason"] == "max_tokens" for row in receipts)
    prior._checkpoint(
        GENERATION,
        "s222_monotonic_addendum_generation_v1",
        {
            "status": "COMPLETE_SCORE_NOT_OPENED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "items": sorted(rows, key=lambda row: list(selected).index(row["item_id"])),
            "metrics": {
                "inherited_selector_calls": 85,
                "addendum_calls": len(receipts),
                "invalid_selector_outputs": 0,
                "token_limit_stops": stops,
                "actual_cost_usd": round(actual, 8),
            },
            "monotonic_prefix_invariant": True,
            "score_packet_opened": False,
            "provider_retries": 0,
            "target_calls": 0,
            "official_fact_credit": 0,
        },
    )
    print(json.dumps({"status": "COMPLETE_SCORE_NOT_OPENED", "calls": len(receipts), "cost_usd": round(actual, 8)}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=prior.DEFAULT_ENV)
    args = parser.parse_args()
    prereg, packet, baselines, selected = verify()
    if not args.execute:
        print(json.dumps({"status": "PREFLIGHT_PASS", "items": 9, "addendum_calls": 9, "target_calls": 0, "score_packet_opened": False}, indent=2))
        return 0
    return execute(prereg, packet, baselines, selected, args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
