#!/usr/bin/env python3
"""Versioned Luna successor for the provider-failed S191 cheap executor."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from openai import OpenAI

try:
    from scripts.s191_visual_utility_executor import (
        BATCH_SIZE,
        COHORT_PATH,
        DEFAULT_ENV,
        ROOT,
        SYSTEM,
        _load_asset,
        _thumbnail,
        is_positive,
        parse_labels,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from s191_visual_utility_executor import (
        BATCH_SIZE,
        COHORT_PATH,
        DEFAULT_ENV,
        ROOT,
        SYSTEM,
        _load_asset,
        _thumbnail,
        is_positive,
        parse_labels,
    )


MODEL = "gpt-5.6-luna"
INPUT_USD_PER_MILLION = 1.0
OUTPUT_USD_PER_MILLION = 6.0
RECEIPTS_PATH = ROOT / "evals" / "s191_visual_utility_luna_receipts_v2.json"
PARTIAL_PATH = ROOT / "evals" / "s191_visual_utility_luna_receipts_v2.partial.jsonl"
RESULT_PATH = ROOT / "evals" / "s191_visual_utility_executor_v2.json"


def _input_content(batch: list[dict[str, Any]], images: list[bytes]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": (
                SYSTEM
                + "\n\nClassify every following image. Return a JSON array in the same order. "
                "Each object must contain exactly: item_id, technical_utility "
                "(useful|not_useful|uncertain), visual_role "
                "(wiring|table|procedure|ui|product_photo|cover|marketing|other), "
                "confidence (high|medium|low), has_legible_technical_visual (boolean), "
                "reason (at most 12 words)."
            ),
        }
    ]
    for row, binary in zip(batch, images, strict=True):
        thumbnail = _thumbnail(binary)
        content.extend(
            [
                {"type": "input_text", "text": f"ITEM {row['item_id']}"},
                {
                    "type": "input_image",
                    "image_url": "data:image/jpeg;base64,"
                    + base64.b64encode(thumbnail).decode("ascii"),
                    "detail": "low",
                },
            ]
        )
    return content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    load_dotenv(args.env, override=True)
    cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
    rows = cohort["rows"]
    if len(rows) != 60 or cohort["status"] != "FROZEN_BEFORE_LABELING":
        raise RuntimeError("unexpected cohort contract")
    base_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    receipts: list[dict[str, Any]] = []
    all_labels: list[dict[str, Any]] = []
    PARTIAL_PATH.unlink(missing_ok=True)

    with httpx.Client() as http:
        for batch_index, offset in enumerate(range(0, len(rows), BATCH_SIZE), 1):
            batch = rows[offset : offset + BATCH_SIZE]
            images = [
                _load_asset(http, base_url=base_url, headers=headers, row=row)
                for row in batch
            ]
            expected_ids = [row["item_id"] for row in batch]
            response = openai.responses.create(
                model=MODEL,
                reasoning={"effort": "none"},
                max_output_tokens=1800,
                input=[
                    {
                        "role": "user",
                        "content": _input_content(batch, images),
                    }
                ],
            )
            raw_text = response.output_text
            labels = parse_labels(raw_text, expected_ids)
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            cost = (
                usage["input_tokens"] * INPUT_USD_PER_MILLION
                + usage["output_tokens"] * OUTPUT_USD_PER_MILLION
            ) / 1_000_000
            receipt = {
                "batch": batch_index,
                "response_id": response.id,
                "model": response.model,
                "status": response.status,
                "usage": usage,
                "cost_usd": round(cost, 8),
                "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                "labels": labels,
            }
            receipts.append(receipt)
            all_labels.extend(labels)
            with PARTIAL_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            print(
                f"batch {batch_index}/6: labels={len(labels)} "
                f"positives={sum(is_positive(label) for label in labels)} cost=${cost:.4f}",
                flush=True,
            )

    total_cost = round(sum(receipt["cost_usd"] for receipt in receipts), 8)
    positives = [label["item_id"] for label in all_labels if is_positive(label)]
    complete = len(all_labels) == 60 and len({row["item_id"] for row in all_labels}) == 60
    frontier_trigger = complete and 10 <= len(positives) <= 30 and total_cost < 2
    RECEIPTS_PATH.write_text(
        json.dumps(
            {
                "instrument": "s191_visual_utility_luna_receipts_v2",
                "model": MODEL,
                "batches": receipts,
                "total_cost_usd": total_cost,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    result = {
        "instrument": "s191_visual_utility_executor_v2",
        "status": "EXECUTOR_GO_TO_FRONTIER" if frontier_trigger else "EXECUTOR_NO_GO",
        "cohort_sha256": cohort["selection"]["cohort_sha256"],
        "measurement": {
            "valid_labels": len(all_labels),
            "unique_items": len({label["item_id"] for label in all_labels}),
            "positives": len(positives),
            "positive_item_ids": positives,
            "by_utility": dict(Counter(label["technical_utility"] for label in all_labels)),
            "by_role": dict(Counter(label["visual_role"] for label in all_labels)),
            "frontier_trigger": frontier_trigger,
        },
        "labels": all_labels,
        "cost": {
            "luna_usd": total_cost,
            "haiku_failure_conservative_upper_bound_usd": 0.2,
            "calls": len(receipts),
            "retries": 0,
        },
        "authorization": {
            "frontier_calls": 0,
            "database_writes": 0,
            "production": False,
        },
    }
    RESULT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    PARTIAL_PATH.unlink(missing_ok=True)
    print(json.dumps(result["measurement"], indent=2, ensure_ascii=False))
    return 0 if frontier_trigger else 2


if __name__ == "__main__":
    raise SystemExit(main())
