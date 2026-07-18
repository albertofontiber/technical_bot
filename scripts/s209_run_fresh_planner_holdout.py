#!/usr/bin/env python3
"""Execute the frozen S209 fresh-predicate support and planner holdout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.decomposed_evidence_planner import (  # noqa: E402
    PLANNER_SYSTEM,
    compile_append,
    output_format,
    planner_payload,
    validate_plan,
)
from src.rag.evidence_units_v2 import EvidenceUnitV2  # noqa: E402
from src.rag.frontier_visual_runtime import FrontierVisualRuntime  # noqa: E402
from src.rag.planner_holdout_gold import (  # noqa: E402
    SUPPORT_MAPPING_PROMPT_V3,
    author_prompt_v3,
    validate_candidate_v3,
    validate_support_mapping_v3,
)
from src.rag.planner_support_review import (  # noqa: E402
    SUPPORT_REVIEW_PROMPT_V4,
    validate_support_review_v4,
)
from src.rag.principal_visual_gold import principal_publication_gate  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    all_pass,
    conservative_cost,
    normalized_text_sha,
    page_content_fable,
    page_content_openai,
    review_prompt,
    sealed_artifact,
    stable_sha,
    validate_review,
    write_json,
)


PACKET_PATH = ROOT / "evals/s209_fresh_planner_holdout_packet_v1.json"
PREREG_PATH = ROOT / "evals/s209_fresh_planner_holdout_prereg_v1.yaml"
SOL_GENERATIONS = ROOT / "evals/s209_kidde_sol_generations_v1.json"
FABLE_GENERATIONS = ROOT / "evals/s209_kidde_fable_generations_v1.json"
SOL_REVIEW = ROOT / "evals/s209_kidde_sol_review_of_fable_v1.json"
FABLE_REVIEW = ROOT / "evals/s209_kidde_fable_review_of_sol_v1.json"
FINAL_GOLD = ROOT / "evals/s209_kidde_visual_gold_v1.json"
SUPPORT_MAPPING = ROOT / "evals/s209_sol_support_mapping_v1.json"
SUPPORT_REVIEW = ROOT / "evals/s209_fable_support_review_v1.json"
PLANNER_RECEIPTS = ROOT / "evals/s209_terra_planner_receipts_v1.json"
RESULT = ROOT / "evals/s209_fresh_planner_holdout_result_v1.json"
CALL_LEDGER = ROOT / "evals/s209_frontier_call_ledger_v1.json"

SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
TERRA_MODEL = "gpt-5.6-terra"
SOL_REASONING = "xhigh"
TERRA_REASONING = "low"
ITEM_COUNT = 2
FRONTIER_CALLS_MAX = 8
PLANNER_CALLS = 2
INTERNAL_BUDGET_USD = 50.0
FRONTIER_PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}
TERRA_PRICES = {"input": 2.5, "output": 15.0}


def _units(item: dict[str, Any]) -> list[EvidenceUnitV2]:
    return [
        EvidenceUnitV2(
            unit_id=row["unit_id"],
            fragment_number=int(row["fragment_number"]),
            candidate_id=row["candidate_id"],
            unit_kind=row["unit_kind"],
            source_spans=tuple(tuple(span) for span in row["source_spans"]),
            content=row["content"],
            content_sha256=row["content_sha256"],
        )
        for row in item["evidence_units"]
    ]


def verify_prereg(packet: dict[str, Any]) -> None:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S209 preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S209 frozen input drift: {label}")
    body = dict(packet)
    packet_sha = body.pop("packet_sha256")
    if stable_sha(body) != packet_sha or prereg["packet_sha256"] != packet_sha:
        raise ValueError("S209 packet identity drift")
    if prereg["models"] != {
        "principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING},
        "independent": {"id": FABLE_MODEL},
        "planner": {"id": TERRA_MODEL, "reasoning_effort": TERRA_REASONING},
    }:
        raise ValueError("S209 model contract drift")
    if prereg["execution"] != {
        "frontier_generation_calls": 4,
        "frontier_cross_review_calls": 2,
        "frontier_support_mapping_calls": 2,
        "frontier_paid_calls_max": FRONTIER_CALLS_MAX,
        "planner_calls": PLANNER_CALLS,
        "provider_retries": 0,
        "same_item_retry": False,
        "candidate_merge_or_repair": False,
        "target_calls": 0,
        "retrieval_calls": 0,
        "database_calls": 0,
    }:
        raise ValueError("S209 execution contract drift")


def _runtime() -> FrontierVisualRuntime:
    missing = [
        key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    return FrontierVisualRuntime(
        ledger_path=CALL_LEDGER,
        ledger_schema="s209_frontier_call_ledger_v1",
        sol_model=SOL_MODEL,
        fable_model=FABLE_MODEL,
        sol_reasoning=SOL_REASONING,
        prices=FRONTIER_PRICES,
        openai_api_key=os.environ["OPENAI_API_KEY"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
    )


def _checkpoint(
    path: Path, schema: str, provider: str, receipts: list[dict[str, Any]], status: str
) -> None:
    write_json(
        path,
        sealed_artifact(
            schema,
            {
                "status": status,
                "provider": provider,
                "receipts": receipts,
                "conservative_cost_usd": conservative_cost(receipts, FRONTIER_PRICES),
            },
        ),
    )


def _review_content(
    packet: dict[str, Any],
    candidates: list[dict[str, Any]],
    counterparts: list[dict[str, Any]],
    reviewer: str,
    author: str,
    provider: str,
) -> list[dict[str, Any]]:
    text_type = "input_text" if provider == "sol" else "text"
    content: list[dict[str, Any]] = [
        {"type": text_type, "text": review_prompt(packet, reviewer, author)}
    ]
    candidates_by_id = {row["canary_id"]: row for row in candidates}
    counterparts_by_id = {row["canary_id"]: row for row in counterparts}
    for item in packet["items"]:
        item_id = item["canary_id"]
        leading = (
            f"PRE-FROZEN TOPIC: {item['topic']}\n"
            f"FOCUS PAGES: {item['focus_pages']}\n"
            f"REQUIRED GENUINE CROSS-PAGE FACTS: {item['cross_page_facts_min']}\n"
            "CANDIDATE TO REVIEW:\n"
            f"{json.dumps(candidates_by_id[item_id], ensure_ascii=False)}\n"
            "INDEPENDENT COUNTERPART FOR MATERIAL-DISAGREEMENT CHECK:\n"
            f"{json.dumps(counterparts_by_id[item_id], ensure_ascii=False)}"
        )
        content.extend(
            page_content_openai(ROOT, item, leading)
            if provider == "sol"
            else page_content_fable(ROOT, item, leading)
        )
    return content


def _mapping_content(
    packet: dict[str, Any],
    candidates: list[dict[str, Any]],
    provider: str,
    mapping: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    text_type = "input_text" if provider == "sol" else "text"
    contract = (
        SUPPORT_MAPPING_PROMPT_V3 if provider == "sol" else SUPPORT_REVIEW_PROMPT_V4
    )
    content: list[dict[str, Any]] = [{"type": text_type, "text": contract}]
    candidate_by_id = {row["canary_id"]: row for row in candidates}
    for item in packet["items"]:
        item_id = item["canary_id"]
        leading = (
            "IMMUTABLE PIXEL GOLD:\n"
            f"{json.dumps(candidate_by_id[item_id], ensure_ascii=False)}\n"
            "IMMUTABLE EVIDENCE UNITS:\n"
            f"{json.dumps(item['evidence_units'], ensure_ascii=False)}"
        )
        if mapping is not None:
            item_mapping = {
                **mapping,
                "mappings": [
                    row
                    for row in mapping.get("mappings") or []
                    if row.get("canary_id") == item_id
                ],
            }
            leading += "\nPRINCIPAL SUPPORT MAPPING TO REVIEW:\n" + json.dumps(
                item_mapping, ensure_ascii=False
            )
        content.extend(
            page_content_openai(ROOT, item, leading)
            if provider == "sol"
            else page_content_fable(ROOT, item, leading)
        )
    return content


def _frontier_cost_guard(receipts: list[dict[str, Any]], phase: str) -> None:
    if conservative_cost(receipts, FRONTIER_PRICES) > INTERNAL_BUDGET_USD:
        raise RuntimeError(f"S209 conservative budget exceeded after {phase}")


def _write_result(body: dict[str, Any]) -> None:
    write_json(
        RESULT,
        sealed_artifact(
            "s209_fresh_planner_holdout_result_v1",
            {
                **body,
                "official_fact_credit": 0,
                "target_calls": 0,
                "runtime_integration": False,
                "source_independent_validation": False,
                "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
                "railway_merge_gate": False,
            },
        ),
    )


def _no_go(
    runtime: FrontierVisualRuntime,
    receipts: list[dict[str, Any]],
    status: str,
    reason: str,
) -> int:
    runtime.seal_complete(len(receipts))
    _write_result(
        {
            "status": status,
            "reason": reason,
            "frontier_calls": len(receipts),
            "planner_calls": 0,
            "target_prereg_authorized": False,
            "conservative_frontier_cost_usd": conservative_cost(
                receipts, FRONTIER_PRICES
            ),
        }
    )
    print(json.dumps({"status": status, "reason": reason}, indent=2))
    return 2


def _run_planner(
    packet: dict[str, Any],
    candidates: list[dict[str, Any]],
    mappings: dict[str, dict[str, list[list[str]]]],
) -> tuple[list[dict[str, Any]], dict[str, Any], float]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    candidate_by_id = {row["canary_id"]: row for row in candidates}
    receipts: list[dict[str, Any]] = []
    for item in packet["items"]:
        item_id = item["canary_id"]
        candidate = candidate_by_id[item_id]
        units = _units(item)
        question = candidate["question"]
        identity = {
            "canary_id": item_id,
            "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
            "source_pdf_sha256": item["source"]["sha256"],
        }
        response = client.responses.create(
            model=TERRA_MODEL,
            reasoning={"effort": TERRA_REASONING},
            instructions=PLANNER_SYSTEM,
            input=planner_payload(question, identity, units),
            text=output_format("s209_fresh_evidence_plan"),
            max_output_tokens=1200,
            store=False,
        )
        plan: list[dict[str, Any]] = []
        selected_ids: list[str] = []
        validation_error = None
        compile_receipt = None
        compiled_sha256 = None
        try:
            if response.status != "completed" or response.model != TERRA_MODEL:
                raise ValueError(
                    f"planner incomplete/model mismatch: {response.status}/{response.model}"
                )
            plan, selected_ids = validate_plan(
                json.loads(response.output_text), {unit.unit_id for unit in units}
            )
            if len(plan) < 2:
                raise ValueError("S209 requires at least two distinct obligations")
            compiled, compile_receipt = compile_append("", units, selected_ids)
            if not all(
                next(unit for unit in units if unit.unit_id == unit_id).content in compiled
                for unit_id in selected_ids
            ):
                raise ValueError("deterministic compiler omitted a selected unit")
            compiled_sha256 = hashlib.sha256(compiled.encode("utf-8")).hexdigest()
        except (json.JSONDecodeError, ValueError, StopIteration) as exc:
            validation_error = f"{type(exc).__name__}: {exc}"
            plan, selected_ids = [], []
        usage = response.usage.model_dump(mode="json", exclude_none=False)
        cost = (
            int(usage.get("input_tokens", 0) or 0) * TERRA_PRICES["input"]
            + int(usage.get("output_tokens", 0) or 0) * TERRA_PRICES["output"]
        ) / 1_000_000
        receipts.append(
            {
                "canary_id": item_id,
                "response_id": response.id,
                "model": response.model,
                "reasoning_effort": TERRA_REASONING,
                "status": response.status,
                "usage": usage,
                "cost_usd": round(cost, 8),
                "raw_text_sha256": hashlib.sha256(
                    response.output_text.encode("utf-8")
                ).hexdigest(),
                "plan": plan,
                "selected_unit_ids": selected_ids,
                "validation_error": validation_error,
                "compiled_sha256": compiled_sha256,
                "compile_receipt": compile_receipt,
            }
        )
        write_json(
            PLANNER_RECEIPTS,
            sealed_artifact(
                "s209_terra_planner_receipts_v1",
                {"status": "IN_PROGRESS", "receipts": receipts},
            ),
        )
    write_json(
        PLANNER_RECEIPTS,
        sealed_artifact(
            "s209_terra_planner_receipts_v1",
            {"status": "COMPLETE", "receipts": receipts},
        ),
    )

    receipt_by_id = {row["canary_id"]: row for row in receipts}
    facts_total = facts_recalled = selected_total = selected_relevant = complete = 0
    question_scores = []
    for item_id, candidate in candidate_by_id.items():
        selected = set(receipt_by_id[item_id]["selected_unit_ids"])
        relevant = {
            unit_id
            for support_sets in mappings[item_id].values()
            for support_set in support_sets
            for unit_id in support_set
        }
        fact_rows = []
        for fact in candidate["atomic_facts"]:
            support_sets = [
                set(support_set)
                for support_set in mappings[item_id][fact["fact_id"]]
            ]
            recalled = any(support.issubset(selected) for support in support_sets)
            fact_rows.append(
                {
                    "fact_id": fact["fact_id"],
                    "support_equivalent_unit_id_sets": [
                        sorted(support) for support in support_sets
                    ],
                    "recalled": recalled,
                }
            )
            facts_total += 1
            facts_recalled += int(recalled)
        selected_total += len(selected)
        selected_relevant += len(selected & relevant)
        question_complete = bool(fact_rows) and all(row["recalled"] for row in fact_rows)
        complete += int(question_complete)
        question_scores.append(
            {
                "canary_id": item_id,
                "facts": fact_rows,
                "question_complete": question_complete,
                "selected_units": len(selected),
                "relevant_selected_units": len(selected & relevant),
            }
        )
    metrics = {
        "facts_total": facts_total,
        "facts_recalled": facts_recalled,
        "atomic_fact_support_recall": round(facts_recalled / facts_total, 6),
        "selected_units": selected_total,
        "selected_relevant_units": selected_relevant,
        "selected_unit_precision": round(
            selected_relevant / selected_total if selected_total else 0.0, 6
        ),
        "complete_questions": complete,
        "question_count": len(candidate_by_id),
        "question_scores": question_scores,
        "invalid_planner_outputs": sum(
            row["validation_error"] is not None for row in receipts
        ),
        "exact_compilations": sum(row["compile_receipt"] is not None for row in receipts),
    }
    return receipts, metrics, round(sum(row["cost_usd"] for row in receipts), 8)


def execute(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    planned = (
        CALL_LEDGER,
        SOL_GENERATIONS,
        FABLE_GENERATIONS,
        SOL_REVIEW,
        FABLE_REVIEW,
        FINAL_GOLD,
        SUPPORT_MAPPING,
        SUPPORT_REVIEW,
        PLANNER_RECEIPTS,
        RESULT,
    )
    existing = [path.relative_to(ROOT).as_posix() for path in planned if path.exists()]
    if existing:
        raise RuntimeError(f"S209 execution artifacts already exist: {existing}")
    runtime = _runtime()
    frontier_receipts: list[dict[str, Any]] = []
    candidates_by_provider: dict[str, list[dict[str, Any]]] = {
        "sol": [],
        "fable": [],
    }
    receipt_groups: dict[str, list[dict[str, Any]]] = {"sol": [], "fable": []}
    generation_specs = (
        ("sol", SOL_GENERATIONS, "s209_sol_generation_receipts_v1"),
        ("fable", FABLE_GENERATIONS, "s209_fable_generation_receipts_v1"),
    )
    for provider, path, schema in generation_specs:
        for item in packet["items"]:
            content = (
                page_content_openai(ROOT, item, author_prompt_v3(packet, item))
                if provider == "sol"
                else page_content_fable(ROOT, item, author_prompt_v3(packet, item))
            )
            if provider == "sol":
                candidate, receipt = runtime.call_sol(
                    content, f"generate:{item['canary_id']}"
                )
            else:
                candidate, receipt = runtime.call_fable(
                    content, 6000, f"generate:{item['canary_id']}"
                )
            frontier_receipts.append(receipt)
            receipt_groups[provider].append(receipt)
            try:
                validate_candidate_v3(candidate, item)
            except ValueError as exc:
                return _no_go(
                    runtime,
                    frontier_receipts,
                    "NO_GO_S209_GOLD",
                    f"{provider} candidate invalid: {exc}",
                )
            candidates_by_provider[provider].append(candidate)
            _checkpoint(path, schema, provider, receipt_groups[provider], "IN_PROGRESS")
            _frontier_cost_guard(frontier_receipts, f"{provider} generation")
        _checkpoint(path, schema, provider, receipt_groups[provider], "COMPLETE")

    sol_candidates = candidates_by_provider["sol"]
    fable_candidates = candidates_by_provider["fable"]
    sol_review, sol_review_receipt = runtime.call_sol(
        _review_content(
            packet, fable_candidates, sol_candidates, SOL_MODEL, FABLE_MODEL, "sol"
        ),
        "review:fable_candidates",
    )
    frontier_receipts.append(sol_review_receipt)
    try:
        validate_review(sol_review, SOL_MODEL, FABLE_MODEL, fable_candidates)
    except ValueError as exc:
        return _no_go(
            runtime,
            frontier_receipts,
            "NO_GO_S209_GOLD_REVIEW",
            f"Sol review invalid: {exc}",
        )
    write_json(
        SOL_REVIEW,
        sealed_artifact(
            "s209_sol_review_of_fable_v1",
            {"review": sol_review, "receipt": sol_review_receipt},
        ),
    )
    _frontier_cost_guard(frontier_receipts, "Sol cross-review")

    fable_review, fable_review_receipt = runtime.call_fable(
        _review_content(
            packet, sol_candidates, fable_candidates, FABLE_MODEL, SOL_MODEL, "fable"
        ),
        10000,
        "review:sol_candidates",
    )
    frontier_receipts.append(fable_review_receipt)
    try:
        validate_review(fable_review, FABLE_MODEL, SOL_MODEL, sol_candidates)
    except ValueError as exc:
        return _no_go(
            runtime,
            frontier_receipts,
            "NO_GO_S209_GOLD_REVIEW",
            f"Fable review invalid: {exc}",
        )
    write_json(
        FABLE_REVIEW,
        sealed_artifact(
            "s209_fable_review_of_sol_v1",
            {"review": fable_review, "receipt": fable_review_receipt},
        ),
    )
    _frontier_cost_guard(frontier_receipts, "Fable cross-review")
    if not principal_publication_gate(fable_review, sol_review):
        return _no_go(
            runtime,
            frontier_receipts,
            "NO_GO_S209_GOLD_REVIEW",
            "principal publication or material-disagreement gate failed",
        )

    questions = []
    for index, (candidate, item) in enumerate(
        zip(sol_candidates, packet["items"], strict=True), 1
    ):
        questions.append(
            {
                "qid": f"s209k{index:02d}",
                **candidate,
                "split": "planner_holdout_candidate_unintegrated",
                "source_pdf_sha256": item["source"]["sha256"],
                "pixel_sha256": [
                    page["image_sha256"] for page in item["rendered_pages"]
                ],
                "cross_review": {
                    "fable_of_sol_publication": "PASS",
                    "sol_of_fable_disagreement_probe": "PASS",
                },
            }
        )
    write_json(
        FINAL_GOLD,
        sealed_artifact(
            "s209_kidde_visual_gold_v1",
            {
                "status": "PIXEL_GOLD_PASS_UNINTEGRATED",
                "questions": questions,
                "official_fact_credit": 0,
            },
        ),
    )

    mapping_value, mapping_receipt = runtime.call_sol(
        _mapping_content(packet, sol_candidates, "sol"),
        "map:gold_facts_to_units",
    )
    frontier_receipts.append(mapping_receipt)
    try:
        mappings = validate_support_mapping_v3(
            mapping_value, sol_candidates, packet["items"], SOL_MODEL
        )
    except ValueError as exc:
        return _no_go(
            runtime,
            frontier_receipts,
            "NO_GO_S209_SUPPORT_MAPPING",
            f"principal support mapping invalid: {exc}",
        )
    write_json(
        SUPPORT_MAPPING,
        sealed_artifact(
            "s209_sol_support_mapping_v1",
            {"mapping": mapping_value, "receipt": mapping_receipt},
        ),
    )
    _frontier_cost_guard(frontier_receipts, "Sol support mapping")

    support_review_value, support_review_receipt = runtime.call_fable(
        _mapping_content(packet, sol_candidates, "fable", mapping_value),
        10000,
        "review:support_mapping",
    )
    frontier_receipts.append(support_review_receipt)
    try:
        support_pass = validate_support_review_v4(
            support_review_value, sol_candidates, FABLE_MODEL, SOL_MODEL
        )
    except ValueError as exc:
        return _no_go(
            runtime,
            frontier_receipts,
            "NO_GO_S209_SUPPORT_MAPPING",
            f"independent support review invalid: {exc}",
        )
    write_json(
        SUPPORT_REVIEW,
        sealed_artifact(
            "s209_fable_support_review_v1",
            {"review": support_review_value, "receipt": support_review_receipt},
        ),
    )
    _frontier_cost_guard(frontier_receipts, "Fable support review")
    if not support_pass:
        return _no_go(
            runtime,
            frontier_receipts,
            "NO_GO_S209_SUPPORT_MAPPING",
            "Fable did not pass every immutable multi-page mapping",
        )
    if len(frontier_receipts) != FRONTIER_CALLS_MAX:
        raise RuntimeError("S209 frontier call count drift")
    runtime.seal_complete(FRONTIER_CALLS_MAX)

    planner_receipts, metrics, terra_cost = _run_planner(
        packet, sol_candidates, mappings
    )
    external_incomplete = [
        row
        for row in planner_receipts
        if row["status"] != "completed" or row["model"] != TERRA_MODEL
    ]
    if external_incomplete:
        _write_result(
            {
                "status": "HOLD_S209_EXTERNAL_OR_INCOMPLETE",
                "reason": "Terra planner call incomplete or provider model mismatch",
                "frontier_calls": len(frontier_receipts),
                "planner_calls": len(planner_receipts),
                "metrics": metrics,
                "conservative_frontier_cost_usd": conservative_cost(
                    frontier_receipts, FRONTIER_PRICES
                ),
                "terra_cost_usd": terra_cost,
                "internal_budget_usd": INTERNAL_BUDGET_USD,
                "target_prereg_authorized": False,
            }
        )
        return 2
    passed = (
        len(planner_receipts) == PLANNER_CALLS
        and metrics["invalid_planner_outputs"] == 0
        and metrics["selected_unit_precision"] >= 0.80
        and metrics["complete_questions"] == metrics["question_count"] == ITEM_COUNT
        and metrics["exact_compilations"] == ITEM_COUNT
    )
    status = "GO_S209_TARGET_PREREG" if passed else "NO_GO_S209_TERRA_LOW"
    _write_result(
        {
            "status": status,
            "frontier_calls": len(frontier_receipts),
            "planner_calls": len(planner_receipts),
            "models": {
                "principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING},
                "independent": {"id": FABLE_MODEL},
                "planner": {"id": TERRA_MODEL, "reasoning_effort": TERRA_REASONING},
            },
            "gold_geometry": {
                "sol_valid": len(sol_candidates),
                "fable_valid": len(fable_candidates),
                "fable_of_sol_publication_all_pass": all_pass(fable_review),
                "support_mapping_review_all_pass": support_pass,
                "genuine_cross_page_items": 1,
            },
            "metrics": metrics,
            "conservative_frontier_cost_usd": conservative_cost(
                frontier_receipts, FRONTIER_PRICES
            ),
            "terra_cost_usd": terra_cost,
            "internal_budget_usd": INTERNAL_BUDGET_USD,
            "target_prereg_authorized": passed,
        }
    )
    print(
        json.dumps(
            {
                "status": status,
                "metrics": metrics,
                "conservative_frontier_cost_usd": conservative_cost(
                    frontier_receipts, FRONTIER_PRICES
                ),
                "terra_cost_usd": terra_cost,
            },
            indent=2,
        )
    )
    return 0 if passed else 2


def preflight(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    images = 0
    for item in packet["items"]:
        prompt = author_prompt_v3(packet, item)
        if f'"page":{item["focus_pages"][0]}' not in prompt:
            raise ValueError("S209 author prompt example page drift")
        for page in item["rendered_pages"]:
            page_content_openai(ROOT, {**item, "rendered_pages": [page]}, "verify")
            images += 1
        if any(len(unit.content) > 600 for unit in _units(item)):
            raise ValueError("S209 broad evidence unit escaped the packet gate")
    print(
        json.dumps(
            {
                "status": "PREFLIGHT_PASS",
                "items": len(packet["items"]),
                "images": images,
                "evidence_units": sum(len(_units(item)) for item in packet["items"]),
                "paid_calls": 0,
                "target_calls": 0,
            },
            indent=2,
        )
    )
    return 0


def _write_hold(exc: Exception) -> None:
    if RESULT.exists():
        return
    calls = []
    if CALL_LEDGER.exists():
        calls = json.loads(CALL_LEDGER.read_text(encoding="utf-8")).get("calls") or []
    _write_result(
        {
            "status": "HOLD_S209_EXTERNAL_OR_INCOMPLETE",
            "reason": f"{type(exc).__name__}: {exc}",
            "frontier_calls": len(calls),
            "planner_calls": 0,
            "target_prereg_authorized": False,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    if not args.execute:
        return preflight(packet)
    try:
        return execute(packet)
    except Exception as exc:
        _write_hold(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
