#!/usr/bin/env python3
"""Run the preregistered cheap visual-utility executor over S191."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv
from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
COHORT_PATH = ROOT / "evals" / "s191_visual_utility_cohort_v1.json"
RECEIPTS_PATH = ROOT / "evals" / "s191_visual_utility_executor_receipts_v1.json"
PARTIAL_PATH = ROOT / "evals" / "s191_visual_utility_executor_receipts_v1.partial.jsonl"
RESULT_PATH = ROOT / "evals" / "s191_visual_utility_executor_v1.json"
MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 10
INPUT_USD_PER_MILLION = 1.0
OUTPUT_USD_PER_MILLION = 5.0

ROLES = {
    "wiring",
    "table",
    "procedure",
    "ui",
    "product_photo",
    "cover",
    "marketing",
    "other",
}
UTILITIES = {"useful", "not_useful", "uncertain"}
CONFIDENCES = {"high", "medium", "low"}
SERVABLE_ROLES = {"wiring", "table", "procedure", "ui"}

SYSTEM = """You classify exact images from technical manuals for a field-service chatbot.
Be conservative. An image is useful only if it visibly contains a legible technical wiring
diagram, technical table, operational procedure illustration, or user-interface screen that can
materially help execute or verify work. Covers, logos, product beauty photos, marketing pages,
mostly prose pages, and illegible visuals are not useful. A whole page may be useful if its
technical visual is legible. Never infer utility from an item id. Return JSON only."""


def parse_labels(raw_text: str, expected_ids: list[str]) -> list[dict[str, Any]]:
    text = raw_text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    payload = json.loads(text)
    if not isinstance(payload, list) or len(payload) != len(expected_ids):
        raise ValueError("label array cardinality mismatch")
    by_id: dict[str, dict[str, Any]] = {}
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("label is not an object")
        item_id = row.get("item_id")
        if item_id in by_id or item_id not in expected_ids:
            raise ValueError("unknown or duplicate item_id")
        utility = row.get("technical_utility")
        role = row.get("visual_role")
        confidence = row.get("confidence")
        legible = row.get("has_legible_technical_visual")
        reason = row.get("reason")
        if utility not in UTILITIES or role not in ROLES or confidence not in CONFIDENCES:
            raise ValueError("closed-vocabulary violation")
        if type(legible) is not bool:
            raise ValueError("legibility must be boolean")
        if not isinstance(reason, str) or len(reason.split()) > 12:
            raise ValueError("reason must contain at most 12 words")
        by_id[item_id] = {
            "item_id": item_id,
            "technical_utility": utility,
            "visual_role": role,
            "confidence": confidence,
            "has_legible_technical_visual": legible,
            "reason": reason,
        }
    if set(by_id) != set(expected_ids):
        raise ValueError("missing item ids")
    return [by_id[item_id] for item_id in expected_ids]


def is_positive(label: dict[str, Any]) -> bool:
    return (
        label["technical_utility"] == "useful"
        and label["confidence"] == "high"
        and label["has_legible_technical_visual"] is True
        and label["visual_role"] in SERVABLE_ROLES
    )


def _thumbnail(binary: bytes) -> bytes:
    with Image.open(io.BytesIO(binary)) as image:
        converted = image.convert("RGB")
        converted.thumbnail((1152, 1152))
        output = io.BytesIO()
        converted.save(output, format="JPEG", quality=82, optimize=True)
    return output.getvalue()


def _load_asset(
    http: httpx.Client,
    *,
    base_url: str,
    headers: dict[str, str],
    row: dict[str, Any],
) -> bytes:
    response = http.get(
        f"{base_url}/rest/v1/chunks",
        headers=headers,
        params={
            "select": "diagram_url",
            "document_id": f"eq.{row['document_id']}",
            "page_number": f"eq.{row['page_number']}",
            "diagram_url": "not.is.null",
            "limit": "100",
        },
        timeout=60,
    )
    response.raise_for_status()
    urls = {item["diagram_url"] for item in response.json() if item.get("diagram_url")}
    matching = [
        url
        for url in urls
        if hashlib.sha256(url.encode("utf-8")).hexdigest()
        == row["diagram_url_sha256"]
    ]
    if len(matching) != 1:
        raise RuntimeError(f"URL receipt mismatch for {row['item_id']}")
    asset = http.get(matching[0], timeout=60, follow_redirects=True)
    asset.raise_for_status()
    if hashlib.sha256(asset.content).hexdigest() != row["asset_sha256"]:
        raise RuntimeError(f"binary receipt mismatch for {row['item_id']}")
    return asset.content


def _batch_content(batch: list[dict[str, Any]], images: list[bytes]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Classify every following image. Return a JSON array in the same order. "
                "Each object must contain exactly: item_id, technical_utility "
                "(useful|not_useful|uncertain), visual_role "
                "(wiring|table|procedure|ui|product_photo|cover|marketing|other), "
                "confidence (high|medium|low), has_legible_technical_visual (boolean), "
                "reason (at most 12 words)."
            ),
        }
    ]
    for row, binary in zip(batch, images, strict=True):
        content.append({"type": "text", "text": f"ITEM {row['item_id']}"})
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(_thumbnail(binary)).decode("ascii"),
                },
            }
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
    anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
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
            response = anthropic.messages.create(
                model=MODEL,
                max_tokens=1800,
                temperature=0,
                system=SYSTEM,
                messages=[
                    {"role": "user", "content": _batch_content(batch, images)}
                ],
            )
            raw_text = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
            labels = parse_labels(raw_text, expected_ids)
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_creation_input_tokens": getattr(
                    response.usage, "cache_creation_input_tokens", 0
                )
                or 0,
                "cache_read_input_tokens": getattr(
                    response.usage, "cache_read_input_tokens", 0
                )
                or 0,
            }
            cost = (
                usage["input_tokens"] * INPUT_USD_PER_MILLION
                + usage["output_tokens"] * OUTPUT_USD_PER_MILLION
            ) / 1_000_000
            receipt = {
                "batch": batch_index,
                "response_id": response.id,
                "model": response.model,
                "stop_reason": response.stop_reason,
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
    receipts_payload = {
        "instrument": "s191_visual_utility_executor_receipts_v1",
        "model": MODEL,
        "batches": receipts,
        "total_cost_usd": total_cost,
    }
    RECEIPTS_PATH.write_text(
        json.dumps(receipts_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    result = {
        "instrument": "s191_visual_utility_executor_v1",
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
        "cost": {"haiku_usd": total_cost, "calls": len(receipts), "retries": 0},
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
