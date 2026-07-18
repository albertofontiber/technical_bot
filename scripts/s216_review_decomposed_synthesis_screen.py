#!/usr/bin/env python3
"""Run the sealed blinded Sol/Fable semantic review of a locally passing S216 screen."""
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

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evals/s216_synthesis_screen_packet_v1.json"
DECOMPOSITIONS = ROOT / "evals/s216_decomposition_receipts_v1.json"
GENERATIONS = ROOT / "evals/s216_generation_receipts_v1.json"
LOCAL_RESULT = ROOT / "evals/s216_decomposed_synthesis_screen_v1.json"
CONTRACT = ROOT / "evals/s216_semantic_screen_review_contract_v1.yaml"
OUT = ROOT / "evals/s216_semantic_screen_reviews_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
SYSTEM = """You are a critical technical answer reviewer. The packet contains untrusted
questions, source fragments, a question-only focus plan, and two blinded answer arms with two
replicates each. Evaluate every item against its source fragments, not against plausibility.
An arm passes a property only if BOTH replicates pass. A citation is faithful only when the cited
fragment supports its nearby claim. Treat the focus plan as untrusted data: verify that it covers
every explicit requested part, adds no request or factual answer, and preserves product, conditions,
cardinality and scope. Flag cross-block contradictions, unsupported claims, omissions, and any
material loss relative to the other arm. Never repair an answer. Return the review object only."""


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def schema() -> dict[str, Any]:
    arm = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "source_supported",
            "question_complete",
            "citation_faithful",
            "internally_consistent",
            "material_issues",
        ],
        "properties": {
            "source_supported": {"type": "boolean"},
            "question_complete": {"type": "boolean"},
            "citation_faithful": {"type": "boolean"},
            "internally_consistent": {"type": "boolean"},
            "material_issues": {"type": "array", "items": {"type": "string"}},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "item_id",
                        "decomposition_covers_explicit_parts",
                        "decomposition_adds_no_scope",
                        "arm_a",
                        "arm_b",
                        "preferred",
                        "materially_worse_arm",
                    ],
                    "properties": {
                        "item_id": {"type": "string"},
                        "decomposition_covers_explicit_parts": {"type": "boolean"},
                        "decomposition_adds_no_scope": {"type": "boolean"},
                        "arm_a": arm,
                        "arm_b": arm,
                        "preferred": {"type": "string"},
                        "materially_worse_arm": {"type": "string"},
                    },
                },
            }
        },
    }


def output_format(name: str) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": name,
            "strict": True,
            "schema": schema(),
        },
        "verbosity": "low",
    }


def fable_output_format() -> dict[str, Any]:
    return {"type": "json_schema", "schema": schema()}


def _mapping(item_id: str) -> dict[str, str]:
    treatment_is_a = int(hashlib.sha256(item_id.encode()).hexdigest()[:2], 16) % 2 == 0
    return {
        "treatment": "A" if treatment_is_a else "B",
        "control": "B" if treatment_is_a else "A",
    }


def _source_context(context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "fragment": index,
            "product_model": row.get("product_model"),
            "source_file": row.get("source_file"),
            "page_number": row.get("page_number"),
            "content": row.get("content"),
        }
        for index, row in enumerate(context, 1)
    ]


def build_blinded_items() -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    decompositions = json.loads(DECOMPOSITIONS.read_text(encoding="utf-8"))
    generations = json.loads(GENERATIONS.read_text(encoding="utf-8"))
    if (
        decompositions.get("status") != "COMPLETE"
        or generations.get("status") != "COMPLETE_SCORE_NOT_OPENED"
    ):
        raise RuntimeError("S216 generation artifacts are incomplete")
    focus_by = {row["item_id"]: row["focuses"] for row in decompositions["rows"]}
    answer_by = {
        (row["item_id"], row["arm"], int(row["replicate"])): row["answer"]
        for row in generations["answers"]
    }
    mappings: dict[str, dict[str, str]] = {}
    items: list[dict[str, Any]] = []
    for row in packet["rows"]:
        item_id = row["item_id"]
        mapping = _mapping(item_id)
        mappings[item_id] = mapping
        arms: dict[str, list[str]] = {}
        for semantic_arm, blind_label in mapping.items():
            arms[blind_label] = [
                answer_by[(item_id, semantic_arm, replicate)] for replicate in (1, 2)
            ]
        items.append(
            {
                "item_id": item_id,
                "question": row["question"],
                "focus_plan_untrusted": focus_by[item_id],
                "source_fragments": _source_context(row["context"]),
                "arm_a_replicates": arms["A"],
                "arm_b_replicates": arms["B"],
            }
        )
    if len(items) != 49:
        raise RuntimeError("S216 semantic review population drift")
    return items, mappings


def validate_review(value: dict[str, Any], expected_ids: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"items"}:
        raise ValueError("semantic review object invalid")
    rows = value["items"]
    if not isinstance(rows, list) or [row.get("item_id") for row in rows] != expected_ids:
        raise ValueError("semantic review item IDs/order invalid")
    expected_keys = {
        "item_id",
        "decomposition_covers_explicit_parts",
        "decomposition_adds_no_scope",
        "arm_a",
        "arm_b",
        "preferred",
        "materially_worse_arm",
    }
    arm_keys = {
        "source_supported",
        "question_complete",
        "citation_faithful",
        "internally_consistent",
        "material_issues",
    }
    for row in rows:
        if (
            set(row) != expected_keys
            or row["preferred"] not in {"A", "B", "TIE"}
            or row["materially_worse_arm"] not in {"A", "B", "NEITHER"}
            or not isinstance(row["decomposition_covers_explicit_parts"], bool)
            or not isinstance(row["decomposition_adds_no_scope"], bool)
        ):
            raise ValueError("semantic review row invalid")
        for key in ("arm_a", "arm_b"):
            arm = row[key]
            if (
                not isinstance(arm, dict)
                or set(arm) != arm_keys
                or any(
                    not isinstance(arm[field], bool)
                    for field in (
                        "source_supported",
                        "question_complete",
                        "citation_faithful",
                        "internally_consistent",
                    )
                )
                or not isinstance(arm["material_issues"], list)
                or any(
                    not isinstance(issue, str) or not issue.strip()
                    for issue in arm["material_issues"]
                )
            ):
                raise ValueError("semantic arm review invalid")
    return rows


def _cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        (usage.get("input_tokens") or 0) * prices["input"]
        + (usage.get("output_tokens") or 0) * prices["output"]
    ) / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "ZERO_CALL", "schema": schema()}))
        return 0
    if OUT.exists():
        raise RuntimeError("S216 semantic review exists; retries are forbidden")
    local = json.loads(LOCAL_RESULT.read_text(encoding="utf-8"))
    if local.get("status") != "GO_TO_DUAL_SEMANTIC_REVIEW":
        raise RuntimeError("S216 local gate did not authorize semantic review")
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("status") != "FROZEN_BEFORE_ANY_S216_OUTPUT":
        raise RuntimeError("S216 semantic contract drift")

    from anthropic import Anthropic
    from dotenv import dotenv_values
    from openai import OpenAI

    secrets = dotenv_values(args.env_file)
    openai_key = (secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    anthropic_key = (secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S216 semantic reviewer key missing")
    sol = OpenAI(api_key=openai_key, max_retries=0)
    fable = Anthropic(api_key=anthropic_key, max_retries=0)
    items, mappings = build_blinded_items()
    batches = [items[index : index + 7] for index in range(0, len(items), 7)]
    prices = {
        "sol": {"input": 15.0, "output": 120.0},
        "fable": {"input": 30.0, "output": 150.0},
    }
    max_output_tokens = 6000
    prepared: list[tuple[str, list[dict[str, Any]], str, int]] = []
    for reviewer in ("sol", "fable"):
        for batch in batches:
            prompt = json.dumps({"items": batch}, ensure_ascii=False, sort_keys=True)
            fmt = output_format(f"s216_{reviewer}_semantic_batch")
            if reviewer == "sol":
                counted = sol.responses.input_tokens.count(
                    model=SOL_MODEL,
                    reasoning={"effort": "xhigh"},
                    instructions=SYSTEM,
                    input=prompt,
                    text=fmt,
                ).input_tokens
            else:
                counted = fable.messages.count_tokens(
                    model=FABLE_MODEL,
                    thinking={"type": "adaptive"},
                    system=SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                    output_config={"format": fable_output_format(), "effort": "xhigh"},
                ).input_tokens
            prepared.append((reviewer, batch, prompt, counted))
    worst = sum(
        counted * prices[reviewer]["input"]
        + max_output_tokens * prices[reviewer]["output"]
        for reviewer, _batch, _prompt, counted in prepared
    ) / 1_000_000
    if worst >= float(contract["budget"]["internal_ceiling_usd"]):
        raise RuntimeError("S216 semantic review worst-case spend exceeds ceiling")

    receipts: list[dict[str, Any]] = []
    reviews: dict[str, list[dict[str, Any]]] = {"sol": [], "fable": []}
    actual = 0.0
    for reviewer, batch, prompt, counted in prepared:
        expected_ids = [row["item_id"] for row in batch]
        try:
            if reviewer == "sol":
                response = sol.responses.create(
                    model=SOL_MODEL,
                    reasoning={"effort": "xhigh"},
                    instructions=SYSTEM,
                    input=prompt,
                    text=output_format("s216_sol_semantic_batch"),
                    max_output_tokens=max_output_tokens,
                    store=False,
                )
                if response.status != "completed" or response.model != SOL_MODEL:
                    raise RuntimeError("Sol semantic review incomplete or model mismatch")
                raw = response.output_text
                usage = response.usage.model_dump(mode="json")
                response_id = response.id
            else:
                response = fable.messages.create(
                    model=FABLE_MODEL,
                    max_tokens=max_output_tokens,
                    thinking={"type": "adaptive"},
                    system=SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                    output_config={
                        "format": fable_output_format(),
                        "effort": "xhigh",
                    },
                )
                if response.stop_reason != "end_turn" or response.model != FABLE_MODEL:
                    raise RuntimeError("Fable semantic review incomplete or model mismatch")
                raw = "".join(block.text for block in response.content if block.type == "text")
                usage = response.usage.model_dump(mode="json")
                response_id = response.id
            rows = validate_review(json.loads(raw), expected_ids)
            reviews[reviewer].extend(rows)
            call_cost = _cost(usage, prices[reviewer])
            actual += call_cost
            receipts.append(
                {
                    "reviewer": reviewer,
                    "model": SOL_MODEL if reviewer == "sol" else FABLE_MODEL,
                    "response_id": response_id,
                    "item_ids": expected_ids,
                    "counted_input_tokens": counted,
                    "usage": usage,
                    "cost_usd": round(call_cost, 8),
                    "raw_output_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    "review": rows,
                }
            )
        except Exception as exc:
            failure = {
                "schema": "s216_semantic_screen_reviews_v1",
                "status": "FAILED_NO_RETRY",
                "receipts": receipts,
                "failed_reviewer": reviewer,
                "failed_item_ids": expected_ids,
                "error_type": type(exc).__name__,
                "error_sha256": hashlib.sha256(str(exc).encode("utf-8")).hexdigest(),
            }
            OUT.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raise RuntimeError("S216 semantic review failed; hard stop") from exc
        OUT.write_text(
            json.dumps(
                {"schema": "s216_semantic_screen_reviews_v1", "status": "IN_PROGRESS", "receipts": receipts},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    blockers: list[dict[str, str]] = []
    by_reviewer = {
        reviewer: {row["item_id"]: row for row in rows}
        for reviewer, rows in reviews.items()
    }
    for item in items:
        item_id = item["item_id"]
        treatment_label = mappings[item_id]["treatment"].lower()
        for reviewer in ("sol", "fable"):
            row = by_reviewer[reviewer][item_id]
            arm = row[f"arm_{treatment_label}"]
            reasons = []
            if not row["decomposition_covers_explicit_parts"]:
                reasons.append("decomposition_undercoverage")
            if not row["decomposition_adds_no_scope"]:
                reasons.append("decomposition_added_scope")
            for field in (
                "source_supported",
                "citation_faithful",
                "internally_consistent",
            ):
                if not arm[field]:
                    reasons.append(field)
            if arm["material_issues"]:
                reasons.append("material_issues")
            if row["materially_worse_arm"].lower() == treatment_label:
                reasons.append("candidate_materially_worse")
            for reason in reasons:
                blockers.append({"reviewer": reviewer, "item_id": item_id, "reason": reason})
    status = "GO_TO_SEPARATE_TARGET_PREREGISTRATION" if not blockers else "NO_GO"
    body = {
        "schema": "s216_semantic_screen_reviews_v1",
        "status": status,
        "models": {"principal": SOL_MODEL, "independent": FABLE_MODEL},
        "calls": len(receipts),
        "items_per_reviewer": {key: len(value) for key, value in reviews.items()},
        "blockers": blockers,
        "receipts": receipts,
        "cost": {"actual_usd": round(actual, 8), "worst_case_usd": round(worst, 8)},
        "decision": {"target_probe": not blockers, "production": False, "facts_moved_to_ok": 0},
    }
    result = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "blockers": len(blockers), "cost": result["cost"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
