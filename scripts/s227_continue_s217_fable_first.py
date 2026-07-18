#!/usr/bin/env python3
"""Continue the zero-response S217 transport hold, Fable-first per item.

S217 and S218 returned no OpenAI model response.  This continuation does not
change the frozen source packet or gold contract.  It changes only call order:
Fable authors one item before Sol authors the same item, so another Sol
transport failure cannot consume the remaining Fable calls.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s217_run_kidde_external_cohort as s217  # noqa: E402
from src.rag.frontier_visual_runtime import FrontierVisualRuntime  # noqa: E402
from src.rag.multisource_visual_gold import (  # noqa: E402
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
    sealed_artifact,
    stable_sha,
    write_json,
)


PACKET = ROOT / "evals/s217_kidde_external_cohort_packet_v1.json"
PREREG = ROOT / "evals/s227_s217_fable_first_continuation_prereg_v1.yaml"
S217_RESULT = ROOT / "evals/s217_kidde_external_cohort_result_v1.json"
S218_RESULT = ROOT / "evals/s218_kidde_external_cohort_result_v1.json"
LEDGER = ROOT / "evals/s227_kidde_fable_first_frontier_call_ledger_v1.json"
FABLE_GENERATIONS = ROOT / "evals/s227_kidde_fable_generations_v1.json"
SOL_GENERATIONS = ROOT / "evals/s227_kidde_sol_generations_v1.json"
SOL_REVIEWS = ROOT / "evals/s227_kidde_sol_reviews_of_fable_v1.json"
FABLE_REVIEWS = ROOT / "evals/s227_kidde_fable_reviews_of_sol_v1.json"
PIXEL_GOLD = ROOT / "evals/s227_kidde_pixel_gold_v1.json"
SOL_MAPPINGS = ROOT / "evals/s227_kidde_sol_support_mappings_v1.json"
FABLE_SUPPORT_REVIEWS = ROOT / "evals/s227_kidde_fable_support_reviews_v1.json"
SUPPORTED_GOLD = ROOT / "evals/s227_kidde_supported_gold_v1.json"
RESULT = ROOT / "evals/s227_kidde_external_cohort_result_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)

SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
SOL_REASONING = "xhigh"
MINIMUM_ITEMS = 3
MAX_CALLS = 24
INTERNAL_BUDGET_USD = 90.0
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}
OUTPUTS = (
    LEDGER,
    FABLE_GENERATIONS,
    SOL_GENERATIONS,
    SOL_REVIEWS,
    FABLE_REVIEWS,
    PIXEL_GOLD,
    SOL_MAPPINGS,
    FABLE_SUPPORT_REVIEWS,
    SUPPORTED_GOLD,
    RESULT,
)


def _checkpoint(path: Path, schema: str, body: dict[str, Any]) -> None:
    write_json(path, sealed_artifact(schema, body))


def _load_sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _verify_prereg(packet: dict[str, Any]) -> None:
    s217.verify_prereg(packet, require_design_gate=False)
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_CONTINUATION":
        raise ValueError("S227 continuation preregistration is not frozen")
    if prereg.get("packet_sha256") != packet.get("packet_sha256"):
        raise ValueError("S227 packet identity drift")
    if prereg.get("models") != {
        "principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING},
        "independent": {"id": FABLE_MODEL},
    }:
        raise ValueError("S227 model contract drift")
    prior_s217 = _load_sealed(S217_RESULT)
    prior_s218 = _load_sealed(S218_RESULT)
    if prior_s217.get("frontier_calls") != 0 or prior_s218.get("frontier_calls") != 0:
        raise ValueError("S227 is only authorized after two zero-response holds")
    if not str(prior_s217.get("status", "")).startswith("HOLD_"):
        raise ValueError("S217 prior state is not a transport hold")
    if prior_s218.get("status") != "HOLD_S218_EXTERNAL_HTTP_520":
        raise ValueError("S218 prior state drift")


def _runtime(env_file: Path) -> FrontierVisualRuntime:
    secrets = dotenv_values(env_file)
    openai_key = (secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    anthropic_key = (
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S227 provider credentials are unavailable")
    return FrontierVisualRuntime(
        ledger_path=LEDGER,
        ledger_schema="s227_kidde_fable_first_frontier_call_ledger_v1",
        sol_model=SOL_MODEL,
        fable_model=FABLE_MODEL,
        sol_reasoning=SOL_REASONING,
        prices=PRICES,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
    )


def _cost_guard(runtime: FrontierVisualRuntime, phase: str) -> None:
    cost = conservative_cost(runtime.load_ledger().get("calls") or [], PRICES)
    if cost > INTERNAL_BUDGET_USD:
        raise RuntimeError(f"S227 budget exceeded after {phase}: {cost}")


def _write_result(runtime: FrontierVisualRuntime, body: dict[str, Any]) -> None:
    calls = runtime.load_ledger().get("calls") or []
    _checkpoint(
        RESULT,
        "s227_kidde_external_cohort_result_v1",
        {
            **body,
            "frontier_calls": len(calls),
            "conservative_frontier_cost_usd": conservative_cost(calls, PRICES),
            "provider_retries": 0,
            "same_item_retry": False,
            "official_fact_credit": 0,
            "target_calls": 0,
            "runtime_integration": False,
            "chunks_v2_status": "ACTIVE_READ_ONLY",
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    )


def _generation_row(
    provider: str,
    item: dict[str, Any],
    candidate: dict[str, Any],
    receipt: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    validation_status = "VALID"
    validation_error = None
    valid = True
    try:
        validate_candidate(candidate, item)
    except SemanticNoGo as exc:
        validation_status = "INSUFFICIENT"
        validation_error = str(exc)
        valid = False
    except ValueError as exc:
        validation_status = "INVALID"
        validation_error = str(exc)
        valid = False
    return (
        {
            "canary_id": item["canary_id"],
            "provider": provider,
            "candidate": candidate,
            "validation_status": validation_status,
            "validation_error": validation_error,
            "receipt": receipt,
        },
        valid,
    )


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


def _seal_no_go(
    runtime: FrontierVisualRuntime, status: str, reason: str, **extra: Any
) -> int:
    calls = runtime.load_ledger().get("calls") or []
    runtime.seal_complete(len(calls))
    _write_result(runtime, {"status": status, "reason": reason, **extra})
    print(json.dumps({"status": status, "reason": reason}, ensure_ascii=False))
    return 2


def execute(packet: dict[str, Any], env_file: Path) -> int:
    _verify_prereg(packet)
    existing = [path.relative_to(ROOT).as_posix() for path in OUTPUTS if path.exists()]
    if existing:
        raise RuntimeError(f"S227 execution artifacts already exist: {existing}")
    runtime = _runtime(env_file)
    rows = {"fable": [], "sol": []}
    candidates: dict[str, dict[str, dict[str, Any]]] = {"fable": {}, "sol": {}}

    # Per-item Fable -> Sol ordering is the only operational delta from S217.
    for item in packet["items"]:
        item_id = item["canary_id"]
        prompt = author_prompt(packet, item)
        fable_value, fable_receipt = runtime.call_fable(
            page_content_fable(ROOT, item, prompt), 8000, f"generate:{item_id}"
        )
        row, valid = _generation_row("fable", item, fable_value, fable_receipt)
        rows["fable"].append(row)
        if valid:
            candidates["fable"][item_id] = fable_value
        _checkpoint(
            FABLE_GENERATIONS,
            "s227_kidde_fable_generations_v1",
            {"status": "IN_PROGRESS", "items": rows["fable"]},
        )
        _cost_guard(runtime, f"Fable authorship {item_id}")

        sol_value, sol_receipt = runtime.call_sol(
            page_content_openai(ROOT, item, prompt), f"generate:{item_id}"
        )
        row, valid = _generation_row("sol", item, sol_value, sol_receipt)
        rows["sol"].append(row)
        if valid:
            candidates["sol"][item_id] = sol_value
        _checkpoint(
            SOL_GENERATIONS,
            "s227_kidde_sol_generations_v1",
            {"status": "IN_PROGRESS", "items": rows["sol"]},
        )
        _cost_guard(runtime, f"Sol authorship {item_id}")

    _checkpoint(
        FABLE_GENERATIONS,
        "s227_kidde_fable_generations_v1",
        {"status": "COMPLETE", "items": rows["fable"]},
    )
    _checkpoint(
        SOL_GENERATIONS,
        "s227_kidde_sol_generations_v1",
        {"status": "COMPLETE", "items": rows["sol"]},
    )
    eligible = [
        item
        for item in packet["items"]
        if item["canary_id"] in candidates["fable"]
        and item["canary_id"] in candidates["sol"]
    ]
    if len(eligible) < MINIMUM_ITEMS:
        return _seal_no_go(
            runtime,
            "NO_GO_S227_INSUFFICIENT_AUTHORSHIP",
            "fewer than three items produced independently valid candidates",
            eligible_items=[item["canary_id"] for item in eligible],
        )

    sol_reviews: list[dict[str, Any]] = []
    fable_reviews: list[dict[str, Any]] = []
    publication_items: list[dict[str, Any]] = []
    for item in eligible:
        item_id = item["canary_id"]
        sol_candidate = candidates["sol"][item_id]
        fable_candidate = candidates["fable"][item_id]
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
        sol_reviews.append(
            {
                "canary_id": item_id,
                "review": sol_value,
                "validation_error": sol_error,
                "receipt": sol_receipt,
            }
        )
        _checkpoint(
            SOL_REVIEWS,
            "s227_kidde_sol_reviews_of_fable_v1",
            {"status": "IN_PROGRESS", "items": sol_reviews},
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
        fable_reviews.append(
            {
                "canary_id": item_id,
                "review": fable_value,
                "validation_error": fable_error,
                "receipt": fable_receipt,
            }
        )
        _checkpoint(
            FABLE_REVIEWS,
            "s227_kidde_fable_reviews_of_sol_v1",
            {"status": "IN_PROGRESS", "items": fable_reviews},
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
        "s227_kidde_sol_reviews_of_fable_v1",
        {"status": "COMPLETE", "items": sol_reviews},
    )
    _checkpoint(
        FABLE_REVIEWS,
        "s227_kidde_fable_reviews_of_sol_v1",
        {"status": "COMPLETE", "items": fable_reviews},
    )
    if len(publication_items) < MINIMUM_ITEMS:
        return _seal_no_go(
            runtime,
            "NO_GO_S227_PIXEL_REVIEW",
            "fewer than three Sol golds passed reciprocal pixel review",
            published_items=[item["canary_id"] for item in publication_items],
        )

    questions = []
    for index, item in enumerate(publication_items, 1):
        item_id = item["canary_id"]
        questions.append(
            {
                "qid": f"s227k{index:02d}",
                **candidates["sol"][item_id],
                "split": "fresh_multisource_mechanism_cohort_unintegrated",
                "source_pdf_sha256": {
                    source["source_pdf"]: source["sha256"] for source in item["sources"]
                },
                "pixel_sha256": [
                    page["image_sha256"] for page in item["rendered_pages"]
                ],
                "cross_review": {
                    "fable_of_sol_publication": "PASS",
                    "sol_of_fable_disagreement_probe": "PASS",
                },
            }
        )
    _checkpoint(
        PIXEL_GOLD,
        "s227_kidde_pixel_gold_v1",
        {
            "status": "PIXEL_GOLD_PASS_UNINTEGRATED",
            "questions": questions,
            "official_fact_credit": 0,
        },
    )

    question_by_canary = {row["canary_id"]: row for row in questions}
    mapping_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    support_validated: list[dict[str, Any]] = []
    mappings: dict[str, dict[str, list[list[str]]]] = {}
    for item in publication_items:
        item_id = item["canary_id"]
        candidate = candidates["sol"][item_id]
        mapping_value, mapping_receipt = runtime.call_sol(
            s217._mapping_content(item, candidate, "sol"),
            f"map:support:{item_id}",
        )
        mapping_error = None
        normalized = None
        try:
            normalized = validate_support_mapping(
                mapping_value, candidate, item, SOL_MODEL
            )
        except ValueError as exc:
            mapping_error = str(exc)
        mapping_rows.append(
            {
                "canary_id": item_id,
                "mapping": mapping_value,
                "normalized_mapping": normalized,
                "validation_error": mapping_error,
                "receipt": mapping_receipt,
            }
        )
        _checkpoint(
            SOL_MAPPINGS,
            "s227_kidde_sol_support_mappings_v1",
            {"status": "IN_PROGRESS", "items": mapping_rows},
        )
        _cost_guard(runtime, f"Sol support mapping {item_id}")
        if mapping_error is not None:
            continue

        support_value, support_receipt = runtime.call_fable(
            s217._mapping_content(item, candidate, "fable", mapping_value),
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
        support_rows.append(
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
            "s227_kidde_fable_support_reviews_v1",
            {"status": "IN_PROGRESS", "items": support_rows},
        )
        _cost_guard(runtime, f"Fable support review {item_id}")
        if support_error is None and support_pass:
            support_validated.append(item)
            mappings[item_id] = normalized or {}

    _checkpoint(
        SOL_MAPPINGS,
        "s227_kidde_sol_support_mappings_v1",
        {"status": "COMPLETE", "items": mapping_rows},
    )
    _checkpoint(
        FABLE_SUPPORT_REVIEWS,
        "s227_kidde_fable_support_reviews_v1",
        {"status": "COMPLETE", "items": support_rows},
    )
    calls = runtime.load_ledger().get("calls") or []
    if len(calls) > MAX_CALLS:
        raise RuntimeError("S227 call ceiling exceeded")
    runtime.seal_complete(len(calls))
    if len(support_validated) < MINIMUM_ITEMS:
        _write_result(
            runtime,
            {
                "status": "NO_GO_S227_SUPPORT_MAPPING",
                "reason": "fewer than three pixel golds passed exact support review",
                "published_items": [item["canary_id"] for item in publication_items],
                "support_validated_items": [
                    item["canary_id"] for item in support_validated
                ],
            },
        )
        return 2

    supported_questions = [
        {
            **question_by_canary[item["canary_id"]],
            "support_equivalent_unit_id_sets": mappings[item["canary_id"]],
        }
        for item in support_validated
    ]
    _checkpoint(
        SUPPORTED_GOLD,
        "s227_kidde_supported_gold_v1",
        {
            "status": "SUPPORTED_FRESH_COHORT_PASS_UNINTEGRATED",
            "questions": supported_questions,
            "official_fact_credit": 0,
        },
    )
    _write_result(
        runtime,
        {
            "status": "GO_S227_FRESH_MULTISOURCE_COHORT",
            "published_items": [item["canary_id"] for item in publication_items],
            "support_validated_items": [
                item["canary_id"] for item in support_validated
            ],
            "supported_question_count": len(supported_questions),
            "next_authorized_step": "clause_bound_source_bound_synthesis_screen",
        },
    )
    print(
        json.dumps(
            {
                "status": "GO_S227_FRESH_MULTISOURCE_COHORT",
                "supported_questions": len(supported_questions),
                "frontier_calls": len(calls),
                "cost_usd": conservative_cost(calls, PRICES),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _write_hold(exc: Exception) -> None:
    if RESULT.exists():
        return
    calls: list[dict[str, Any]] = []
    if LEDGER.exists():
        try:
            calls = _load_sealed(LEDGER).get("calls") or []
        except Exception:
            calls = []
    _checkpoint(
        RESULT,
        "s227_kidde_external_cohort_result_v1",
        {
            "status": "HOLD_S227_EXTERNAL_OR_INCOMPLETE",
            "reason_type": type(exc).__name__,
            "reason_sha256": stable_sha(str(exc)),
            "frontier_calls": len(calls),
            "conservative_frontier_cost_usd": conservative_cost(calls, PRICES),
            "provider_retries": 0,
            "same_item_retry": False,
            "official_fact_credit": 0,
            "target_calls": 0,
            "chunks_v2_status": "ACTIVE_READ_ONLY",
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    )


def preflight(packet: dict[str, Any], env_file: Path) -> int:
    _verify_prereg(packet)
    if any(path.exists() for path in OUTPUTS):
        raise RuntimeError("S227 output artifact already exists")
    # Credential discovery is part of zero-call preflight.  Constructing the
    # provider clients performs no network request and prevents a paid stage
    # from starting with a worktree-local .env assumption.
    _runtime(env_file)
    for item in packet["items"]:
        prompt = author_prompt(packet, item)
        page_content_fable(ROOT, item, prompt)
        page_content_openai(ROOT, item, prompt)
    print(
        json.dumps(
            {
                "status": "PREFLIGHT_PASS",
                "items": len(packet["items"]),
                "per_item_call_order": ["fable_author", "sol_author"],
                "max_calls": MAX_CALLS,
                "target_calls": 0,
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    if not args.execute:
        return preflight(packet, args.env_file)
    try:
        return execute(packet, args.env_file)
    except Exception as exc:
        _write_hold(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
