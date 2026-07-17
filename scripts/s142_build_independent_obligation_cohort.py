#!/usr/bin/env python3
"""Build and optionally label a sealed, source-first S142 held-out cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import yaml


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "tmp/s116_independent_holdout/extraction/agent_anthropic-sonnet-45"
ACQUISITION = ROOT / "evals/s116_independent_holdout_acquisition_v2.json"
DEFAULT_PACKET = ROOT / "evals/s142_independent_source_packet_v1.json"
DEFAULT_COHORT = ROOT / "evals/s142_independent_obligation_cohort_v1.json"
DEFAULT_RAW_RECEIPT = ROOT / "evals/s142_haiku_raw_response_v3.json"
DEFAULT_PREREG = ROOT / "evals/s142_independent_obligation_cohort_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s142_independent_obligation_cohort_execution_permit_v1.yaml"
MODEL = "claude-haiku-4-5-20251001"
MAX_OUTPUT_TOKENS = 12000

RELATION_MARKERS = (
    " must ", " shall ", " should ", " before ", " after ", " when ", " if ",
    " set ", " select ", " configure", " connect", " test", " reset", " alarm",
    " fault", " output", " input", " voltage", " resistance", " delay", " switch",
    " terminal", " battery", " relay", " address", " power", " current", " zone",
)

SYSTEM = """You create a sealed evaluation cohort for a technical-manual RAG system.
Use only each supplied exact excerpt. For every item, write one natural Spanish question a field
technician could ask and 2-5 atomic answer claims that are explicitly supported by that excerpt.
Each claim must preserve conditions, qualifiers, units, polarity and action. Copy one shortest exact
supporting quote per claim from the excerpt. Do not use outside knowledge or infer a product feature.
If the excerpt cannot support at least two useful related claims, mark it ineligible and return no
question or claims. Do not mention this evaluation or the excerpt in the question."""


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_paid_authorization(prereg_path: Path, permit_path: Path) -> None:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S142 preregistration is not frozen")
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise RuntimeError("S142 paid execution is not permitted")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S142 frozen input drift: {label}")
    for label, spec in {
        "preregistration": permit["preregistration"],
        "runner": permit["runner"],
        "source_packet": permit["source_packet"],
    }.items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S142 permit artifact drift: {label}")


def _score(value: str) -> int:
    folded = " " + re.sub(r"\s+", " ", value).casefold() + " "
    marker_score = sum(folded.count(marker) for marker in RELATION_MARKERS)
    numeric = len(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?\s*(?:v|ma|a|ohm|ω|s|sec|min|%|°c|ft|m)?\b", folded))
    conditional = len(re.findall(r"\b(?:if|when|before|after|unless|must|shall|should)\b", folded))
    penalty = 15 if "table of contents" in folded else 0
    return marker_score * 4 + min(numeric, 20) + conditional * 3 - penalty


def _best_excerpt(pages: list[dict[str, Any]], max_chars: int = 6000) -> dict[str, Any]:
    candidates = []
    for page in pages:
        text = str(page.get("text") or "")
        if len(text.strip()) < 350:
            continue
        starts = range(0, max(1, len(text)), max_chars // 2)
        for start in starts:
            end = min(len(text), start + max_chars)
            raw = text[start:end]
            if len(raw.strip()) < 350:
                continue
            candidates.append((_score(raw), int(page.get("page") or 0), start, end, raw))
            if end == len(text):
                break
    if not candidates:
        raise RuntimeError("document has no eligible excerpt window")
    score, page_number, start, end, raw = max(
        candidates, key=lambda row: (row[0], len(row[4].strip()), -row[1], -row[2])
    )
    return {
        "page_number": page_number,
        "source_start": start,
        "source_end": end,
        "selection_score": score,
        "excerpt": raw,
        "excerpt_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }


def build_packet() -> dict[str, Any]:
    acquisition = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    docs_by_sha = {row["sha256"]: row for row in acquisition["documents"] if row["status"] == "ok"}
    rows = []
    for raw_path in sorted(RAW.glob("*.json")):
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        sha = payload["sha256"]
        if sha not in docs_by_sha:
            continue
        doc = docs_by_sha[sha]
        excerpt = _best_excerpt(payload["result"]["pages"])
        rows.append(
            {
                "item_id": doc["id"],
                "manufacturer": doc["manufacturer"],
                "stratum": doc["stratum"],
                "filename": doc["filename"],
                "document_sha256": sha,
                **excerpt,
            }
        )
    if len(rows) != 12 or len({row["document_sha256"] for row in rows}) != 12:
        raise RuntimeError("S142 requires exactly 12 independent documents")
    body = {
        "instrument": "s142_independent_source_packet_v1",
        "selection": {
            "source": "s116_independent_document_holdout",
            "source_first": True,
            "s141_output_inspected": False,
            "algorithm": "highest_relation_marker_window_v1",
            "max_excerpt_chars": 6000,
        },
        "source_receipts": {
            "acquisition_path": str(ACQUISITION.relative_to(ROOT)).replace("\\", "/"),
            "acquisition_sha256": file_sha(ACQUISITION),
        },
        "items": rows,
    }
    return {**body, "packet_sha256": stable_sha(body)}


def output_schema(item_ids: list[str]) -> dict[str, Any]:
    claim = {
        "type": "object",
        "additionalProperties": False,
        "required": ["claim", "exact_quote"],
        "properties": {
            "claim": {"type": "string", "minLength": 8},
            "exact_quote": {"type": "string", "minLength": 4},
        },
    }
    item = {
        "type": "object",
        "additionalProperties": False,
        "required": ["item_id", "eligible", "question", "claims"],
        "properties": {
            "item_id": {"type": "string", "enum": item_ids},
            "eligible": {"type": "boolean"},
            "question": {"type": "string"},
            "claims": {"type": "array", "items": claim},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {"items": {"type": "array", "items": item}},
    }


def _validate_labels(labels: dict[str, Any], packet: dict[str, Any]) -> None:
    ids = [row["item_id"] for row in packet["items"]]
    schema = output_schema(ids)
    errors = list(Draft202012Validator(schema).iter_errors(labels))
    if errors:
        raise RuntimeError(f"invalid S142 label schema: {errors[0].message}")
    rows = labels["items"]
    if len(rows) != len(ids) or {row["item_id"] for row in rows} != set(ids):
        raise RuntimeError("S142 label item mismatch")
    source = {row["item_id"]: row["excerpt"] for row in packet["items"]}
    for row in rows:
        if row["eligible"]:
            if not row["question"].strip() or not (2 <= len(row["claims"]) <= 5):
                raise RuntimeError(f"invalid eligible S142 item: {row['item_id']}")
            if any(claim["exact_quote"] not in source[row["item_id"]] for claim in row["claims"]):
                raise RuntimeError(f"non-exact S142 quote: {row['item_id']}")
        elif row["question"].strip() or row["claims"]:
            raise RuntimeError(f"ineligible S142 item carries claims: {row['item_id']}")


def execute_labels(
    packet: dict[str, Any], *, env_file: Path, raw_receipt_path: Path
) -> dict[str, Any]:
    from anthropic import Anthropic
    from dotenv import dotenv_values

    secrets = dotenv_values(env_file)
    key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    client = Anthropic(api_key=key)
    public_items = [
        {key: row[key] for key in ("item_id", "manufacturer", "stratum", "filename", "excerpt")}
        for row in packet["items"]
    ]
    prompt = "Create the sealed cohort for all items:\n\n" + json.dumps(
        {"items": public_items}, ensure_ascii=False, sort_keys=True
    )
    schema = output_schema([row["item_id"] for row in packet["items"]])
    counted = client.messages.count_tokens(
        model=MODEL,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    ).input_tokens
    conservative_worst = counted * 2 / 1_000_000 + MAX_OUTPUT_TOKENS * 10 / 1_000_000
    if counted > 90000 or conservative_worst > 0.35:
        raise RuntimeError("S142 paid preflight exceeds internal cap")
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    usage = response.usage.model_dump(mode="json")
    raw_receipt = {
        "instrument": "s142_haiku_raw_response_v3",
        "status": "RECEIVED_UNVALIDATED",
        "source_packet_sha256": packet["packet_sha256"],
        "model": MODEL,
        "response_id": response.id,
        "stop_reason": response.stop_reason,
        "usage": usage,
        "raw_text": text,
        "raw_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    raw_receipt_path.write_text(
        json.dumps(raw_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    labels = json.loads(text)
    _validate_labels(labels, packet)
    conservative_actual = (
        usage.get("input_tokens", 0) * 2 + usage.get("output_tokens", 0) * 10
    ) / 1_000_000
    body = {
        "instrument": "s142_independent_obligation_cohort_v1",
        "status": "SEALED_VALIDATED",
        "source_packet_sha256": packet["packet_sha256"],
        "model": MODEL,
        "response_id": response.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usage": usage,
        "conservative_cost_usd": round(conservative_actual, 8),
        "items": labels["items"],
    }
    return {**body, "cohort_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--raw-receipt", type=Path, default=DEFAULT_RAW_RECEIPT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--execute-paid", action="store_true")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"),
    )
    args = parser.parse_args()
    packet = build_packet()
    args.packet.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.execute_paid:
        print(json.dumps({"status": "PACKET_ONLY", "items": len(packet["items"]), "packet_sha256": packet["packet_sha256"]}))
        return 0
    validate_paid_authorization(args.prereg, args.permit)
    cohort = execute_labels(
        packet, env_file=args.env_file, raw_receipt_path=args.raw_receipt
    )
    args.cohort.write_text(json.dumps(cohort, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": cohort["status"],
        "items": len(cohort["items"]),
        "eligible": sum(row["eligible"] for row in cohort["items"]),
        "claims": sum(len(row["claims"]) for row in cohort["items"]),
        "conservative_cost_usd": cohort["conservative_cost_usd"],
        "cohort_sha256": cohort["cohort_sha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
