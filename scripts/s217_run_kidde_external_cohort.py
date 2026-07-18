#!/usr/bin/env python3
"""Execute the frozen S217 multi-source Kidde authorship and support gate."""
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
from src.rag.visual_gold import (  # noqa: E402
    SemanticNoGo,
    conservative_cost,
    normalized_text_sha,
    sealed_artifact,
    stable_sha,
    write_json,
)


PACKET_PATH = ROOT / "evals/s217_kidde_external_cohort_packet_v1.json"
PREREG_PATH = ROOT / "evals/s217_kidde_external_cohort_prereg_v1.yaml"
DESIGN_GATE_PATH = ROOT / "evals/s217_frontier_design_gate_reviews_v1.json"
SOL_GENERATIONS = ROOT / "evals/s217_kidde_sol_generations_v1.json"
FABLE_GENERATIONS = ROOT / "evals/s217_kidde_fable_generations_v1.json"
SOL_REVIEWS = ROOT / "evals/s217_kidde_sol_reviews_of_fable_v1.json"
FABLE_REVIEWS = ROOT / "evals/s217_kidde_fable_reviews_of_sol_v1.json"
PIXEL_GOLD = ROOT / "evals/s217_kidde_pixel_gold_v1.json"
SOL_MAPPINGS = ROOT / "evals/s217_kidde_sol_support_mappings_v1.json"
FABLE_SUPPORT_REVIEWS = ROOT / "evals/s217_kidde_fable_support_reviews_v1.json"
SUPPORTED_GOLD = ROOT / "evals/s217_kidde_supported_gold_v1.json"
RESULT = ROOT / "evals/s217_kidde_external_cohort_result_v1.json"
CALL_LEDGER = ROOT / "evals/s217_frontier_call_ledger_v1.json"

SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
SOL_REASONING = "xhigh"
CANDIDATE_ITEMS = 4
MINIMUM_ITEMS = 3
GENERATION_CALLS = 8
FRONTIER_CALLS_MAX = 24
INTERNAL_BUDGET_USD = 150.0
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
        ledger_schema="s217_frontier_call_ledger_v1",
        sol_model=SOL_MODEL,
        fable_model=FABLE_MODEL,
        sol_reasoning=SOL_REASONING,
        prices=FRONTIER_PRICES,
        openai_api_key=os.environ["OPENAI_API_KEY"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
    )


def _verify_seal(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _verify_design_gate() -> None:
    gate = _verify_seal(DESIGN_GATE_PATH)
    if gate.get("status") != "COMPLETE":
        raise ValueError("S217 Frontier design gate is incomplete")
    expected_subject = "evals/s217_frontier_design_gate_brief_v1.md"
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    expected_normalized_sha = prereg["frozen_inputs"]["design_gate_brief"][
        "sha256"
    ]
    if gate.get("subject") != expected_subject:
        raise ValueError("S217 Frontier design gate subject mismatch")
    if gate.get("subject_normalized_sha256") != expected_normalized_sha:
        raise ValueError("S217 Frontier design gate normalized subject mismatch")
    if normalized_text_sha(ROOT / expected_subject) != expected_normalized_sha:
        raise ValueError("S217 current design brief drift")
    decisions = gate.get("decisions") or {}
    if decisions.get("sol") != {
        "reviewer": SOL_MODEL,
        "verdict": "PASS",
        "blocking_findings": [],
    }:
        raise ValueError("S217 principal design gate did not PASS")
    if decisions.get("fable") != {
        "reviewer": FABLE_MODEL,
        "verdict": "PASS",
        "blocking_findings": [],
    }:
        raise ValueError("S217 independent design gate did not PASS")


def verify_prereg(packet: dict[str, Any], *, require_design_gate: bool) -> None:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S217 preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S217 frozen input drift: {label}")
    packet_body = dict(packet)
    packet_sha = packet_body.pop("packet_sha256", None)
    if stable_sha(packet_body) != packet_sha or prereg["packet_sha256"] != packet_sha:
        raise ValueError("S217 packet identity drift")
    if prereg["models"] != {
        "principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING},
        "independent": {"id": FABLE_MODEL},
    }:
        raise ValueError("S217 model contract drift")
    if prereg["execution"] != {
        "frontier_generation_calls": GENERATION_CALLS,
        "frontier_reciprocal_review_calls_max": 8,
        "frontier_support_calls_max": 8,
        "frontier_paid_calls_max": FRONTIER_CALLS_MAX,
        "provider_retries": 0,
        "same_item_retry": False,
        "candidate_merge_or_repair": False,
        "target_calls": 0,
        "retrieval_calls": 0,
        "database_calls": 0,
    }:
        raise ValueError("S217 execution contract drift")
    if require_design_gate:
        _verify_design_gate()


def _checkpoint(path: Path, schema: str, body: dict[str, Any]) -> None:
    write_json(path, sealed_artifact(schema, body))


def _cost_guard(runtime: FrontierVisualRuntime, phase: str) -> None:
    ledger = runtime.load_ledger()
    cost = conservative_cost(ledger.get("calls") or [], FRONTIER_PRICES)
    if cost > INTERNAL_BUDGET_USD:
        raise RuntimeError(f"S217 conservative budget exceeded after {phase}: {cost}")


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
        "s217_kidde_external_cohort_result_v1",
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


def _seal_and_stop(
    runtime: FrontierVisualRuntime, status: str, reason: str, body: dict[str, Any]
) -> int:
    calls = runtime.load_ledger().get("calls") or []
    runtime.seal_complete(len(calls))
    _write_result(runtime, {"status": status, "reason": reason, **body})
    print(json.dumps({"status": status, "reason": reason}, indent=2))
    return 2


def execute(packet: dict[str, Any]) -> int:
    verify_prereg(packet, require_design_gate=False)
    planned = (
        CALL_LEDGER,
        SOL_GENERATIONS,
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
        raise RuntimeError(f"S217 execution artifacts already exist: {existing}")

    runtime = _runtime()
    generation_rows: dict[str, list[dict[str, Any]]] = {"sol": [], "fable": []}
    valid_candidates: dict[str, dict[str, dict[str, Any]]] = {
        "sol": {},
        "fable": {},
    }
    generation_specs = (
        ("sol", SOL_GENERATIONS, "s217_kidde_sol_generations_v1"),
        ("fable", FABLE_GENERATIONS, "s217_kidde_fable_generations_v1"),
    )
    for provider, path, schema in generation_specs:
        for item in packet["items"]:
            item_id = item["canary_id"]
            prompt = author_prompt(packet, item)
            content = (
                page_content_openai(ROOT, item, prompt)
                if provider == "sol"
                else page_content_fable(ROOT, item, prompt)
            )
            if provider == "sol":
                candidate, receipt = runtime.call_sol(content, f"generate:{item_id}")
            else:
                candidate, receipt = runtime.call_fable(
                    content, 8000, f"generate:{item_id}"
                )
            validation_status = "VALID"
            validation_error = None
            try:
                validate_candidate(candidate, item)
                valid_candidates[provider][item_id] = candidate
            except SemanticNoGo as exc:
                validation_status = "INSUFFICIENT"
                validation_error = str(exc)
            except ValueError as exc:
                validation_status = "INVALID"
                validation_error = str(exc)
            generation_rows[provider].append(
                {
                    "canary_id": item_id,
                    "candidate": candidate,
                    "validation_status": validation_status,
                    "validation_error": validation_error,
                    "receipt": receipt,
                }
            )
            _checkpoint(
                path,
                schema,
                {
                    "status": "IN_PROGRESS",
                    "provider": provider,
                    "items": generation_rows[provider],
                },
            )
            _cost_guard(runtime, f"{provider} generation {item_id}")
        _checkpoint(
            path,
            schema,
            {
                "status": "COMPLETE",
                "provider": provider,
                "items": generation_rows[provider],
            },
        )

    if len(runtime.load_ledger().get("calls") or []) != GENERATION_CALLS:
        raise RuntimeError("S217 generation call geometry drift")
    eligible = [
        item
        for item in packet["items"]
        if item["canary_id"] in valid_candidates["sol"]
        and item["canary_id"] in valid_candidates["fable"]
    ]
    if len(eligible) < MINIMUM_ITEMS:
        return _seal_and_stop(
            runtime,
            "NO_GO_S217_INSUFFICIENT_AUTHORSHIP",
            "fewer than three items produced independently valid Sol and Fable candidates",
            {"eligible_items": [item["canary_id"] for item in eligible]},
        )

    sol_review_rows: list[dict[str, Any]] = []
    fable_review_rows: list[dict[str, Any]] = []
    publication_items: list[dict[str, Any]] = []
    for item in eligible:
        item_id = item["canary_id"]
        sol_candidate = valid_candidates["sol"][item_id]
        fable_candidate = valid_candidates["fable"][item_id]

        sol_review_value, sol_receipt = runtime.call_sol(
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
        sol_validation_error = None
        try:
            validate_review(
                sol_review_value, SOL_MODEL, FABLE_MODEL, fable_candidate
            )
        except ValueError as exc:
            sol_validation_error = str(exc)
        sol_review_rows.append(
            {
                "canary_id": item_id,
                "review": sol_review_value,
                "validation_error": sol_validation_error,
                "receipt": sol_receipt,
            }
        )
        _checkpoint(
            SOL_REVIEWS,
            "s217_kidde_sol_reviews_of_fable_v1",
            {"status": "IN_PROGRESS", "items": sol_review_rows},
        )
        _cost_guard(runtime, f"Sol review {item_id}")

        fable_review_value, fable_receipt = runtime.call_fable(
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
        fable_validation_error = None
        try:
            validate_review(
                fable_review_value, FABLE_MODEL, SOL_MODEL, sol_candidate
            )
        except ValueError as exc:
            fable_validation_error = str(exc)
        fable_review_rows.append(
            {
                "canary_id": item_id,
                "review": fable_review_value,
                "validation_error": fable_validation_error,
                "receipt": fable_receipt,
            }
        )
        _checkpoint(
            FABLE_REVIEWS,
            "s217_kidde_fable_reviews_of_sol_v1",
            {"status": "IN_PROGRESS", "items": fable_review_rows},
        )
        _cost_guard(runtime, f"Fable review {item_id}")

        if (
            sol_validation_error is None
            and fable_validation_error is None
            and principal_publication_gate(fable_review_value, sol_review_value)
        ):
            publication_items.append(item)

    _checkpoint(
        SOL_REVIEWS,
        "s217_kidde_sol_reviews_of_fable_v1",
        {"status": "COMPLETE", "items": sol_review_rows},
    )
    _checkpoint(
        FABLE_REVIEWS,
        "s217_kidde_fable_reviews_of_sol_v1",
        {"status": "COMPLETE", "items": fable_review_rows},
    )
    if len(publication_items) < MINIMUM_ITEMS:
        return _seal_and_stop(
            runtime,
            "NO_GO_S217_PIXEL_REVIEW",
            "fewer than three principal candidates passed independent pixel publication and disagreement gates",
            {"published_items": [item["canary_id"] for item in publication_items]},
        )

    questions: list[dict[str, Any]] = []
    for index, item in enumerate(publication_items, 1):
        item_id = item["canary_id"]
        questions.append(
            {
                "qid": f"s217k{index:02d}",
                **valid_candidates["sol"][item_id],
                "split": "fresh_multisource_mechanism_cohort_unintegrated",
                "source_pdf_sha256": {
                    source["source_pdf"]: source["sha256"] for source in item["sources"]
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
        "s217_kidde_pixel_gold_v1",
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
        candidate = valid_candidates["sol"][item_id]
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
            "s217_kidde_sol_support_mappings_v1",
            {"status": "IN_PROGRESS", "items": sol_mapping_rows},
        )
        _cost_guard(runtime, f"Sol support mapping {item_id}")
        if mapping_error is not None:
            continue

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
            "s217_kidde_fable_support_reviews_v1",
            {"status": "IN_PROGRESS", "items": fable_support_rows},
        )
        _cost_guard(runtime, f"Fable support review {item_id}")
        if support_error is None and support_pass:
            support_validated.append(item)
            mappings_by_id[item_id] = normalized_mapping or {}

    _checkpoint(
        SOL_MAPPINGS,
        "s217_kidde_sol_support_mappings_v1",
        {"status": "COMPLETE", "items": sol_mapping_rows},
    )
    _checkpoint(
        FABLE_SUPPORT_REVIEWS,
        "s217_kidde_fable_support_reviews_v1",
        {"status": "COMPLETE", "items": fable_support_rows},
    )
    calls = runtime.load_ledger().get("calls") or []
    if len(calls) > FRONTIER_CALLS_MAX:
        raise RuntimeError("S217 frontier call ceiling exceeded")
    runtime.seal_complete(len(calls))

    if len(support_validated) < MINIMUM_ITEMS:
        _write_result(
            runtime,
            {
                "status": "NO_GO_S217_SUPPORT_MAPPING",
                "reason": "fewer than three pixel golds passed exact source-page support mapping and independent review",
                "authorship_eligible_items": [item["canary_id"] for item in eligible],
                "pixel_published_items": [
                    item["canary_id"] for item in publication_items
                ],
                "support_validated_items": [
                    item["canary_id"] for item in support_validated
                ],
            },
        )
        return 2

    supported_questions = []
    for item in support_validated:
        item_id = item["canary_id"]
        supported_questions.append(
            {
                **question_by_id[item_id],
                "support_equivalent_unit_id_sets": mappings_by_id[item_id],
            }
        )
    _checkpoint(
        SUPPORTED_GOLD,
        "s217_kidde_supported_gold_v1",
        {
            "status": "SUPPORTED_FRESH_COHORT_PASS_UNINTEGRATED",
            "questions": supported_questions,
            "official_fact_credit": 0,
        },
    )
    _write_result(
        runtime,
        {
            "status": "GO_S217_FRESH_MULTISOURCE_COHORT",
            "authorship_eligible_items": [item["canary_id"] for item in eligible],
            "pixel_published_items": [item["canary_id"] for item in publication_items],
            "support_validated_items": [
                item["canary_id"] for item in support_validated
            ],
            "supported_question_count": len(supported_questions),
            "next_authorized_step": (
                "develop a generic relevance/compression mechanism on this "
                "fresh cohort before any target preregistration"
            ),
        },
    )
    print(
        json.dumps(
            {
                "status": "GO_S217_FRESH_MULTISOURCE_COHORT",
                "supported_questions": len(supported_questions),
                "frontier_calls": len(calls),
                "cost_usd": conservative_cost(calls, FRONTIER_PRICES),
            },
            indent=2,
        )
    )
    return 0


def preflight(packet: dict[str, Any]) -> int:
    verify_prereg(packet, require_design_gate=False)
    images = 0
    for item in packet["items"]:
        prompt = author_prompt(packet, item)
        if item["canary_id"] not in prompt:
            raise ValueError("S217 author prompt identity drift")
        page_content_openai(ROOT, item, "verify")
        page_content_fable(ROOT, item, "verify")
        images += len(item["rendered_pages"])
        if any(len(unit["content"]) > 600 for unit in item["evidence_units"]):
            raise ValueError("S217 broad evidence unit escaped packet gate")
    print(
        json.dumps(
            {
                "status": "PREFLIGHT_PASS",
                "items": len(packet["items"]),
                "sources": packet["selection"]["distinct_source_pdfs"],
                "images": images,
                "evidence_units": sum(
                    len(item["evidence_units"]) for item in packet["items"]
                ),
                "paid_calls": 0,
                "design_gate_required_for_execute": False,
                "target_calls": 0,
            },
            indent=2,
        )
    )
    return 0


def _write_hold(exc: Exception) -> None:
    if RESULT.exists():
        return
    calls: list[dict[str, Any]] = []
    if CALL_LEDGER.exists():
        try:
            calls = _verify_seal(CALL_LEDGER).get("calls") or []
        except Exception:
            calls = []
    _checkpoint(
        RESULT,
        "s217_kidde_external_cohort_result_v1",
        {
            "status": "HOLD_S217_EXTERNAL_OR_INCOMPLETE",
            "reason": f"{type(exc).__name__}: {exc}",
            "frontier_calls": len(calls),
            "official_fact_credit": 0,
            "target_calls": 0,
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
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



