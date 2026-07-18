#!/usr/bin/env python3
"""Execute the frozen S215 continuation on three never-attempted Fable items."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.frontier_visual_runtime import FrontierVisualRuntime  # noqa: E402
from src.rag.multisource_visual_gold import (  # noqa: E402
    SUPPORT_MAPPING_PROMPT,
    SUPPORT_REVIEW_PROMPT,
    author_prompt,
    page_content_fable,
    page_content_openai,
    principal_publication_gate,
    review_prompt,
    validate_candidate,
    validate_review,
    validate_support_mapping,
    validate_support_review,
)
from src.rag.query_evidence_compiler import portable_file_sha  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    SemanticNoGo,
    conservative_cost,
    normalized_text_sha,
    sealed_artifact,
    stable_sha,
    write_json,
)


PACKET_PATH = ROOT / "evals/s214_kidde_multisource_gold_packet_v1.json"
S214_LEDGER = ROOT / "evals/s214_frontier_call_ledger_v1.json"
S214_SOL = ROOT / "evals/s214_kidde_sol_generations_v1.json"
S214_CLOSURE = ROOT / "evals/s214_kidde_multisource_incomplete_closure_v1.json"
PREREG_PATH = ROOT / "evals/s215_kidde_multisource_continuation_prereg_v1.yaml"
DESIGN_GATE_PATH = ROOT / "evals/s215_frontier_design_gate_reviews_v1.json"

FABLE_GENERATIONS = ROOT / "evals/s215_kidde_fable_generations_v1.json"
SOL_REVIEWS = ROOT / "evals/s215_kidde_sol_reviews_of_fable_v1.json"
FABLE_REVIEWS = ROOT / "evals/s215_kidde_fable_reviews_of_sol_v1.json"
PIXEL_GOLD = ROOT / "evals/s215_kidde_pixel_gold_v1.json"
SOL_MAPPINGS = ROOT / "evals/s215_kidde_sol_support_mappings_v1.json"
FABLE_SUPPORT_REVIEWS = ROOT / "evals/s215_kidde_fable_support_reviews_v1.json"
SUPPORTED_GOLD = ROOT / "evals/s215_kidde_supported_gold_v1.json"
RESULT = ROOT / "evals/s215_kidde_multisource_continuation_result_v1.json"
CALL_LEDGER = ROOT / "evals/s215_frontier_call_ledger_v1.json"

SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
SOL_REASONING = "xhigh"
ITEM_IDS = (
    "kidde_2xa_interface_tradeoffs",
    "kidde_mcp_surface_kit_selection",
    "kidde_modulaser_role_selection",
)
ATTEMPTED_ITEM = "kidde_nc_capacity_tradeoffs"
FRONTIER_CALLS_MAX = 15
INTERNAL_BUDGET_USD = 90.0
FRONTIER_PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}


def _runtime() -> FrontierVisualRuntime:
    missing = [
        key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    return FrontierVisualRuntime(
        ledger_path=CALL_LEDGER,
        ledger_schema="s215_frontier_call_ledger_v1",
        sol_model=SOL_MODEL,
        fable_model=FABLE_MODEL,
        sol_reasoning=SOL_REASONING,
        prices=FRONTIER_PRICES,
        openai_api_key=os.environ["OPENAI_API_KEY"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
    )


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _checkpoint(path: Path, schema: str, body: dict[str, Any]) -> None:
    write_json(path, sealed_artifact(schema, body))


def _s214_inputs(packet: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    packet_body = dict(packet)
    packet_sha = packet_body.pop("packet_sha256", None)
    if not packet_sha or stable_sha(packet_body) != packet_sha:
        raise ValueError("S214 packet identity drift")
    s214_ledger = _sealed(S214_LEDGER)
    closure = _sealed(S214_CLOSURE)
    sol = _sealed(S214_SOL)
    calls = s214_ledger.get("calls") or []
    attempted_fable = [
        row["call_label"].removeprefix("generate:")
        for row in calls
        if row.get("provider") == "fable"
        and str(row.get("call_label", "")).startswith("generate:")
    ]
    packet_order = [item["canary_id"] for item in packet["items"]]
    derived = [item_id for item_id in packet_order if item_id not in attempted_fable]
    if (
        s214_ledger.get("status") != "INCOMPLETE_FINAL"
        or attempted_fable != [ATTEMPTED_ITEM]
        or tuple(derived) != ITEM_IDS
        or closure.get("status") != "NO_GO_INCOMPLETE_FAIL_CLOSED"
        or tuple(closure.get("unattempted_items") or []) != ITEM_IDS
        or closure.get("decision", {}).get("same_run_retry") is not False
        or closure.get("credit", {}).get("facts_moved_to_ok") != 0
    ):
        raise ValueError("S214 deterministic continuation boundary drift")
    if closure["inputs"]["closed_call_ledger_sha256"] != portable_file_sha(
        S214_LEDGER
    ):
        raise ValueError("S214 closed ledger receipt drift")

    rows = sol.get("items") or []
    by_item = {item["canary_id"]: item for item in packet["items"]}
    by_sol = {row["canary_id"]: row for row in rows}
    if sol.get("status") != "COMPLETE" or set(by_sol) != set(packet_order):
        raise ValueError("S214 Sol checkpoint geometry drift")
    inherited = []
    for item_id in ITEM_IDS:
        row = by_sol[item_id]
        if row.get("validation_status") != "VALID":
            raise ValueError(f"S214 inherited Sol candidate invalid: {item_id}")
        validate_candidate(row["candidate"], by_item[item_id])
        inherited.append(row["candidate"])
    return inherited, closure


def _verify_design_gate() -> None:
    gate = _sealed(DESIGN_GATE_PATH)
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    expected_subject = "evals/s215_frontier_design_gate_brief_v1.md"
    if (
        gate.get("status") != "COMPLETE"
        or gate.get("subject") != expected_subject
        or gate.get("subject_normalized_sha256")
        != prereg["frozen_inputs"]["design_gate_brief"]["sha256"]
        or normalized_text_sha(ROOT / expected_subject)
        != gate.get("subject_normalized_sha256")
    ):
        raise ValueError("S215 design gate subject or status drift")
    decisions = gate.get("decisions") or {}
    if decisions.get("sol") != {
        "reviewer": SOL_MODEL,
        "verdict": "PASS",
        "blocking_findings": [],
    } or decisions.get("fable") != {
        "reviewer": FABLE_MODEL,
        "verdict": "PASS",
        "blocking_findings": [],
    }:
        raise ValueError("S215 dual Frontier design gate did not PASS")


def verify_prereg(packet: dict[str, Any], *, require_design_gate: bool) -> None:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S215 preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S215 frozen input drift: {label}")
    inherited, _ = _s214_inputs(packet)
    if len(inherited) != 3:
        raise ValueError("S215 inherited principal candidate geometry drift")
    if prereg["models"] != {
        "principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING},
        "independent": {"id": FABLE_MODEL},
    }:
        raise ValueError("S215 model contract drift")
    if prereg["execution"] != {
        "inherited_sol_authorship_calls": 0,
        "first_attempt_fable_authorship_calls": 3,
        "frontier_reciprocal_review_calls_max": 6,
        "frontier_support_calls_max": 6,
        "frontier_paid_calls_max": FRONTIER_CALLS_MAX,
        "fable_authorship_max_tokens": 12000,
        "provider_retries": 0,
        "same_item_retry": False,
        "candidate_merge_repair_or_replacement": False,
        "target_calls": 0,
        "retrieval_calls": 0,
        "database_calls": 0,
    }:
        raise ValueError("S215 execution contract drift")
    if require_design_gate:
        _verify_design_gate()


def _review_content(
    packet: dict[str, Any],
    item: dict[str, Any],
    candidate: dict[str, Any],
    counterpart: dict[str, Any],
    reviewer: str,
    author: str,
    provider: str,
) -> list[dict[str, Any]]:
    leading = (
        review_prompt(packet, item, reviewer, author)
        + "\n\nFROZEN ITEM CONTRACT:\n"
        + json.dumps(
            {
                "topic": item["topic"],
                "distinct_sources_min": item["distinct_sources_min"],
                "cross_source_facts_min": item["cross_source_facts_min"],
                "known_conflicts": item["known_conflicts"],
            },
            ensure_ascii=False,
        )
        + "\nCANDIDATE TO REVIEW:\n"
        + json.dumps(candidate, ensure_ascii=False)
        + "\nINDEPENDENT COUNTERPART FOR DISAGREEMENT PROBE:\n"
        + json.dumps(counterpart, ensure_ascii=False)
    )
    return (
        page_content_openai(ROOT, item, leading)
        if provider == "sol"
        else page_content_fable(ROOT, item, leading)
    )


def _mapping_content(
    item: dict[str, Any],
    candidate: dict[str, Any],
    provider: str,
    mapping: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    contract = SUPPORT_MAPPING_PROMPT if provider == "sol" else SUPPORT_REVIEW_PROMPT
    leading = (
        contract
        + "\n\nIMMUTABLE PIXEL GOLD:\n"
        + json.dumps(candidate, ensure_ascii=False)
        + "\nIMMUTABLE EVIDENCE UNITS:\n"
        + json.dumps(item["evidence_units"], ensure_ascii=False)
    )
    if mapping is not None:
        leading += "\nPRINCIPAL SUPPORT MAPPING TO REVIEW:\n" + json.dumps(
            mapping, ensure_ascii=False
        )
    return (
        page_content_openai(ROOT, item, leading)
        if provider == "sol"
        else page_content_fable(ROOT, item, leading)
    )


def _write_result(runtime: FrontierVisualRuntime, body: dict[str, Any]) -> None:
    ledger = runtime.load_ledger()
    calls = ledger.get("calls") or []
    _checkpoint(
        RESULT,
        "s215_kidde_multisource_continuation_result_v1",
        {
            **body,
            "frontier_calls": len(calls),
            "conservative_frontier_cost_usd": conservative_cost(
                calls, FRONTIER_PRICES
            ),
            "internal_budget_usd": INTERNAL_BUDGET_USD,
            "provider_retries": 0,
            "official_fact_credit": 0,
            "official_denominator_change": 0,
            "target_calls": 0,
            "runtime_integration": False,
            "source_independent_validation": False,
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "chunks_v2_status": "ACTIVE_READ_ONLY",
            "railway_merge_gate": False,
        },
    )


def _cost_guard(runtime: FrontierVisualRuntime, phase: str) -> None:
    cost = conservative_cost(
        runtime.load_ledger().get("calls") or [], FRONTIER_PRICES
    )
    if cost > INTERNAL_BUDGET_USD:
        raise RuntimeError(f"S215 conservative budget exceeded after {phase}: {cost}")


def _no_go(
    runtime: FrontierVisualRuntime,
    status: str,
    reason: str,
    body: dict[str, Any],
) -> int:
    runtime.seal_complete(len(runtime.load_ledger().get("calls") or []))
    _write_result(runtime, {"status": status, "reason": reason, **body})
    print(json.dumps({"status": status, "reason": reason}, indent=2))
    return 2


def execute(packet: dict[str, Any]) -> int:
    verify_prereg(packet, require_design_gate=True)
    planned = (
        CALL_LEDGER,
        FABLE_GENERATIONS,
        SOL_REVIEWS,
        FABLE_REVIEWS,
        PIXEL_GOLD,
        SOL_MAPPINGS,
        FABLE_SUPPORT_REVIEWS,
        SUPPORTED_GOLD,
        RESULT,
    )
    existing = [path.relative_to(ROOT).as_posix() for path in planned if path.exists()]
    if existing:
        raise RuntimeError(f"S215 execution artifacts already exist: {existing}")

    inherited_candidates, _ = _s214_inputs(packet)
    sol_candidates = {
        candidate["canary_id"]: candidate for candidate in inherited_candidates
    }
    by_item = {item["canary_id"]: item for item in packet["items"]}
    items = [by_item[item_id] for item_id in ITEM_IDS]
    runtime = _runtime()

    fable_rows: list[dict[str, Any]] = []
    fable_candidates: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item["canary_id"]
        candidate, receipt = runtime.call_fable(
            page_content_fable(ROOT, item, author_prompt(packet, item)),
            12000,
            f"generate:{item_id}",
        )
        validation_status = "VALID"
        validation_error = None
        try:
            validate_candidate(candidate, item)
            fable_candidates[item_id] = candidate
        except SemanticNoGo as exc:
            validation_status = "INSUFFICIENT"
            validation_error = str(exc)
        except ValueError as exc:
            validation_status = "INVALID"
            validation_error = str(exc)
        fable_rows.append(
            {
                "canary_id": item_id,
                "candidate": candidate,
                "validation_status": validation_status,
                "validation_error": validation_error,
                "receipt": receipt,
            }
        )
        _checkpoint(
            FABLE_GENERATIONS,
            "s215_kidde_fable_generations_v1",
            {"status": "IN_PROGRESS", "provider": "fable", "items": fable_rows},
        )
        _cost_guard(runtime, f"Fable authorship {item_id}")
    _checkpoint(
        FABLE_GENERATIONS,
        "s215_kidde_fable_generations_v1",
        {"status": "COMPLETE", "provider": "fable", "items": fable_rows},
    )
    if tuple(fable_candidates) != ITEM_IDS:
        return _no_go(
            runtime,
            "NO_GO_S215_AUTHORSHIP",
            "not all three first-attempt Fable candidates passed the frozen validator",
            {"valid_fable_items": list(fable_candidates)},
        )

    sol_review_rows: list[dict[str, Any]] = []
    fable_review_rows: list[dict[str, Any]] = []
    publication_items: list[dict[str, Any]] = []
    for item in items:
        item_id = item["canary_id"]
        sol_candidate = sol_candidates[item_id]
        fable_candidate = fable_candidates[item_id]
        sol_value, sol_receipt = runtime.call_sol(
            _review_content(
                packet,
                item,
                fable_candidate,
                sol_candidate,
                SOL_MODEL,
                FABLE_MODEL,
                "sol",
            ),
            f"review:fable:{item_id}",
        )
        sol_error = None
        try:
            validate_review(sol_value, SOL_MODEL, FABLE_MODEL, fable_candidate)
        except ValueError as exc:
            sol_error = str(exc)
        sol_review_rows.append(
            {
                "canary_id": item_id,
                "review": sol_value,
                "validation_error": sol_error,
                "receipt": sol_receipt,
            }
        )
        _checkpoint(
            SOL_REVIEWS,
            "s215_kidde_sol_reviews_of_fable_v1",
            {"status": "IN_PROGRESS", "items": sol_review_rows},
        )
        _cost_guard(runtime, f"Sol review {item_id}")

        fable_value, fable_receipt = runtime.call_fable(
            _review_content(
                packet,
                item,
                sol_candidate,
                fable_candidate,
                FABLE_MODEL,
                SOL_MODEL,
                "fable",
            ),
            6000,
            f"review:sol:{item_id}",
        )
        fable_error = None
        try:
            validate_review(fable_value, FABLE_MODEL, SOL_MODEL, sol_candidate)
        except ValueError as exc:
            fable_error = str(exc)
        fable_review_rows.append(
            {
                "canary_id": item_id,
                "review": fable_value,
                "validation_error": fable_error,
                "receipt": fable_receipt,
            }
        )
        _checkpoint(
            FABLE_REVIEWS,
            "s215_kidde_fable_reviews_of_sol_v1",
            {"status": "IN_PROGRESS", "items": fable_review_rows},
        )
        _cost_guard(runtime, f"Fable review {item_id}")
        if (
            sol_error is None
            and fable_error is None
            and principal_publication_gate(fable_value, sol_value)
        ):
            publication_items.append(item)

    _checkpoint(
        SOL_REVIEWS,
        "s215_kidde_sol_reviews_of_fable_v1",
        {"status": "COMPLETE", "items": sol_review_rows},
    )
    _checkpoint(
        FABLE_REVIEWS,
        "s215_kidde_fable_reviews_of_sol_v1",
        {"status": "COMPLETE", "items": fable_review_rows},
    )
    if tuple(item["canary_id"] for item in publication_items) != ITEM_IDS:
        return _no_go(
            runtime,
            "NO_GO_S215_PIXEL_REVIEW",
            "not all three mandatory items passed reciprocal pixel publication",
            {"published_items": [item["canary_id"] for item in publication_items]},
        )

    questions: list[dict[str, Any]] = []
    for index, item in enumerate(publication_items, 1):
        candidate = sol_candidates[item["canary_id"]]
        questions.append(
            {
                "qid": f"s215k{index:02d}",
                **candidate,
                "split": "fresh_multisource_mechanism_cohort_unintegrated",
                "source_pdf_sha256": {
                    source["source_pdf"]: source["sha256"]
                    for source in item["sources"]
                },
                "pixel_sha256": [
                    page["image_sha256"] for page in item["rendered_pages"]
                ],
                "cross_review": {
                    "fable_of_sol_publication": "PASS",
                    "sol_of_fable_material_disagreement_probe": "PASS",
                },
            }
        )
    _checkpoint(
        PIXEL_GOLD,
        "s215_kidde_pixel_gold_v1",
        {
            "status": "PIXEL_GOLD_PASS_UNINTEGRATED",
            "questions": questions,
            "official_fact_credit": 0,
        },
    )

    question_by_id = {question["canary_id"]: question for question in questions}
    sol_mapping_rows: list[dict[str, Any]] = []
    fable_support_rows: list[dict[str, Any]] = []
    support_validated: list[dict[str, Any]] = []
    mappings_by_id: dict[str, dict[str, list[list[str]]]] = {}
    for item in publication_items:
        item_id = item["canary_id"]
        candidate = sol_candidates[item_id]
        mapping_value, mapping_receipt = runtime.call_sol(
            _mapping_content(item, candidate, "sol"),
            f"map:support:{item_id}",
        )
        mapping_error = None
        normalized_mapping = None
        try:
            normalized_mapping = validate_support_mapping(
                mapping_value, candidate, item, SOL_MODEL
            )
        except ValueError as exc:
            mapping_error = str(exc)
        sol_mapping_rows.append(
            {
                "canary_id": item_id,
                "mapping": mapping_value,
                "normalized_mapping": normalized_mapping,
                "validation_error": mapping_error,
                "receipt": mapping_receipt,
            }
        )
        _checkpoint(
            SOL_MAPPINGS,
            "s215_kidde_sol_support_mappings_v1",
            {"status": "IN_PROGRESS", "items": sol_mapping_rows},
        )
        _cost_guard(runtime, f"Sol support mapping {item_id}")

        if mapping_error is None:
            support_value, support_receipt = runtime.call_fable(
                _mapping_content(item, candidate, "fable", mapping_value),
                6000,
                f"review:support:{item_id}",
            )
            support_error = None
            support_pass = False
            try:
                support_pass = validate_support_review(
                    support_value, candidate, FABLE_MODEL, SOL_MODEL
                )
            except ValueError as exc:
                support_error = str(exc)
            fable_support_rows.append(
                {
                    "canary_id": item_id,
                    "review": support_value,
                    "pass": support_pass,
                    "validation_error": support_error,
                    "receipt": support_receipt,
                }
            )
            _checkpoint(
                FABLE_SUPPORT_REVIEWS,
                "s215_kidde_fable_support_reviews_v1",
                {"status": "IN_PROGRESS", "items": fable_support_rows},
            )
            _cost_guard(runtime, f"Fable support review {item_id}")
            if support_error is None and support_pass:
                support_validated.append(item)
                mappings_by_id[item_id] = normalized_mapping or {}

    _checkpoint(
        SOL_MAPPINGS,
        "s215_kidde_sol_support_mappings_v1",
        {"status": "COMPLETE", "items": sol_mapping_rows},
    )
    _checkpoint(
        FABLE_SUPPORT_REVIEWS,
        "s215_kidde_fable_support_reviews_v1",
        {"status": "COMPLETE", "items": fable_support_rows},
    )
    if len(runtime.load_ledger().get("calls") or []) > FRONTIER_CALLS_MAX:
        raise RuntimeError("S215 frontier call ceiling exceeded")
    if tuple(item["canary_id"] for item in support_validated) != ITEM_IDS:
        return _no_go(
            runtime,
            "NO_GO_S215_SUPPORT_MAPPING",
            "not all three mandatory pixel golds passed exact support validation",
            {
                "support_validated_items": [
                    item["canary_id"] for item in support_validated
                ]
            },
        )

    supported_questions = [
        {
            **question_by_id[item["canary_id"]],
            "support_equivalent_unit_id_sets": mappings_by_id[item["canary_id"]],
        }
        for item in support_validated
    ]
    _checkpoint(
        SUPPORTED_GOLD,
        "s215_kidde_supported_gold_v1",
        {
            "status": "SUPPORTED_FRESH_COHORT_PASS_UNINTEGRATED",
            "questions": supported_questions,
            "official_fact_credit": 0,
        },
    )
    runtime.seal_complete(FRONTIER_CALLS_MAX)
    _write_result(
        runtime,
        {
            "status": "GO_S215_FRESH_MULTISOURCE_COHORT",
            "support_validated_items": list(ITEM_IDS),
            "supported_question_count": 3,
            "next_authorized_step": (
                "develop a generic relevance/compression mechanism on this fresh "
                "cohort before any untouched target evaluation"
            ),
        },
    )
    print(
        json.dumps(
            {
                "status": "GO_S215_FRESH_MULTISOURCE_COHORT",
                "supported_questions": 3,
                "frontier_calls": FRONTIER_CALLS_MAX,
                "cost_usd": conservative_cost(
                    runtime.load_ledger()["calls"], FRONTIER_PRICES
                ),
            },
            indent=2,
        )
    )
    return 0


def preflight(packet: dict[str, Any]) -> int:
    verify_prereg(packet, require_design_gate=False)
    items = {item["canary_id"]: item for item in packet["items"]}
    for item_id in ITEM_IDS:
        item = items[item_id]
        prompt = author_prompt(packet, item)
        if item_id not in prompt:
            raise ValueError("S215 author prompt identity drift")
        page_content_fable(ROOT, item, prompt)
        page_content_openai(ROOT, item, "verify")
    print(
        json.dumps(
            {
                "status": "PREFLIGHT_PASS",
                "items": 3,
                "selection": "S214_PACKET_MINUS_ATTEMPTED_FABLE_ITEM",
                "new_sol_authorship_calls": 0,
                "paid_calls_max": FRONTIER_CALLS_MAX,
                "target_calls": 0,
                "design_gate_required_for_execute": True,
            },
            indent=2,
        )
    )
    return 0


def _finalize_incomplete(exc: Exception) -> None:
    if RESULT.exists():
        return
    calls: list[dict[str, Any]] = []
    runtime: FrontierVisualRuntime | None = None
    if CALL_LEDGER.exists():
        try:
            runtime = _runtime()
            ledger = runtime.load_ledger()
            calls = ledger.get("calls") or []
            ledger.pop("result_sha256", None)
            ledger["status"] = "INCOMPLETE_FINAL"
            ledger["closure"] = {
                "reason": f"{type(exc).__name__}: {exc}",
                "provider_retries": 0,
                "same_item_retry": False,
                "resume": False,
                "official_fact_credit": 0,
            }
            ledger["result_sha256"] = stable_sha(ledger)
            write_json(CALL_LEDGER, ledger)
        except Exception:
            runtime = None
            calls = []
    body = {
        "status": "HOLD_S215_EXTERNAL_OR_INCOMPLETE",
        "reason": f"{type(exc).__name__}: {exc}",
        "frontier_calls": len(calls),
        "conservative_frontier_cost_usd": conservative_cost(
            calls, FRONTIER_PRICES
        ),
        "internal_budget_usd": INTERNAL_BUDGET_USD,
        "provider_retries": 0,
        "same_item_retry": False,
        "resume": False,
        "official_fact_credit": 0,
        "official_denominator_change": 0,
        "target_calls": 0,
        "runtime_integration": False,
        "source_independent_validation": False,
        "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
        "chunks_v2_status": "ACTIVE_READ_ONLY",
        "railway_merge_gate": False,
    }
    _checkpoint(RESULT, "s215_kidde_multisource_continuation_result_v1", body)


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
        _finalize_incomplete(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
