#!/usr/bin/env python3
"""Run the bounded S205 principal-author visual-gold canary."""
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
from src.rag.principal_visual_gold import principal_publication_gate  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    SemanticNoGo,
    all_pass,
    author_prompt,
    conservative_cost,
    normalized_text_sha,
    page_content_fable,
    page_content_openai,
    review_prompt,
    sealed_artifact,
    stable_sha,
    validate_candidate,
    validate_review,
    write_json,
)


PACKET_PATH = ROOT / "evals/s205_kidde_visual_canary_packet_v1.json"
PREREG_PATH = ROOT / "evals/s205_kidde_visual_canary_prereg_v1.yaml"
SOL_GENERATIONS = ROOT / "evals/s205_kidde_sol_generations_v1.json"
FABLE_GENERATIONS = ROOT / "evals/s205_kidde_fable_generations_v1.json"
SOL_REVIEW = ROOT / "evals/s205_kidde_sol_review_of_fable_v1.json"
FABLE_REVIEW = ROOT / "evals/s205_kidde_fable_review_of_sol_v1.json"
FINAL_GOLD = ROOT / "evals/s205_kidde_visual_gold_v1.json"
RESULT = ROOT / "evals/s205_kidde_visual_canary_result_v1.json"
CALL_LEDGER = ROOT / "evals/s205_kidde_frontier_call_ledger_v1.json"

SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
SOL_REASONING = "xhigh"
MAX_CALLS = 8
INTERNAL_BUDGET_USD = 40.0
CONSERVATIVE_PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}


def verify_prereg(packet: dict[str, Any]) -> None:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_FRONTIER_EXECUTION":
        raise ValueError("S205 preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S205 frozen input drift: {label}")
    if prereg["packet_sha256"] != packet["packet_sha256"]:
        raise ValueError("S205 packet identity drift")
    expected_models = {
        "principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING},
        "independent": {"id": FABLE_MODEL},
    }
    if prereg["models"] != expected_models:
        raise ValueError("S205 model contract drift")
    expected_execution = {
        "generation_calls_per_model": 3,
        "cross_review_calls_per_model": 1,
        "paid_calls_max": MAX_CALLS,
        "provider_retries": 0,
        "same_item_retry": False,
        "candidate_merge": False,
        "frontier_input": "pixel_only",
    }
    if prereg["execution"] != expected_execution:
        raise ValueError("S205 execution contract drift")


def _checkpoint(
    path: Path,
    schema: str,
    provider: str,
    receipts: list[dict[str, Any]],
    status: str,
) -> None:
    write_json(
        path,
        sealed_artifact(
            schema,
            {
                "status": status,
                "provider": provider,
                "receipts": receipts,
                "conservative_cost_usd": conservative_cost(
                    receipts, CONSERVATIVE_PRICES
                ),
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
            "CANDIDATE TO REVIEW:\n"
            f"{json.dumps(candidates_by_id[item_id], ensure_ascii=False)}\n"
            "INDEPENDENT COUNTERPART FOR MATERIAL-DISAGREEMENT CHECK:\n"
            f"{json.dumps(counterparts_by_id[item_id], ensure_ascii=False)}"
        )
        if provider == "sol":
            content.extend(page_content_openai(ROOT, item, leading))
        else:
            content.extend(page_content_fable(ROOT, item, leading))
    return content


def _check_budget(receipts: list[dict[str, Any]], phase: str) -> None:
    if conservative_cost(receipts, CONSERVATIVE_PRICES) > INTERNAL_BUDGET_USD:
        raise RuntimeError(f"conservative budget exceeded after {phase}")


def _runtime() -> FrontierVisualRuntime:
    missing = [
        key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    return FrontierVisualRuntime(
        ledger_path=CALL_LEDGER,
        ledger_schema="s205_kidde_frontier_call_ledger_v1",
        sol_model=SOL_MODEL,
        fable_model=FABLE_MODEL,
        sol_reasoning=SOL_REASONING,
        prices=CONSERVATIVE_PRICES,
        openai_api_key=os.environ["OPENAI_API_KEY"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
    )


def execute(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    planned = (
        CALL_LEDGER,
        SOL_GENERATIONS,
        FABLE_GENERATIONS,
        SOL_REVIEW,
        FABLE_REVIEW,
        FINAL_GOLD,
        RESULT,
    )
    existing = [path.relative_to(ROOT).as_posix() for path in planned if path.exists()]
    if existing:
        raise RuntimeError(f"same-cohort execution artifacts already exist: {existing}")
    runtime = _runtime()
    receipts: list[dict[str, Any]] = []
    sol_candidates: list[dict[str, Any]] = []
    fable_candidates: list[dict[str, Any]] = []

    sol_receipts: list[dict[str, Any]] = []
    for item in packet["items"]:
        candidate, receipt = runtime.call_sol(
            page_content_openai(ROOT, item, author_prompt(packet, item)),
            f"generate:{item['canary_id']}",
        )
        validate_candidate(candidate, item)
        sol_candidates.append(candidate)
        receipts.append(receipt)
        sol_receipts.append(receipt)
        _checkpoint(
            SOL_GENERATIONS,
            "s205_sol_generation_receipts_v1",
            "sol",
            sol_receipts.copy(),
            "IN_PROGRESS",
        )
        _check_budget(receipts, "Sol generation")
    _checkpoint(
        SOL_GENERATIONS,
        "s205_sol_generation_receipts_v1",
        "sol",
        sol_receipts,
        "COMPLETE",
    )

    fable_receipts: list[dict[str, Any]] = []
    for item in packet["items"]:
        candidate, receipt = runtime.call_fable(
            page_content_fable(ROOT, item, author_prompt(packet, item)),
            6000,
            f"generate:{item['canary_id']}",
        )
        validate_candidate(candidate, item)
        fable_candidates.append(candidate)
        receipts.append(receipt)
        fable_receipts.append(receipt)
        _checkpoint(
            FABLE_GENERATIONS,
            "s205_fable_generation_receipts_v1",
            "fable",
            fable_receipts.copy(),
            "IN_PROGRESS",
        )
        _check_budget(receipts, "Fable generation")
    _checkpoint(
        FABLE_GENERATIONS,
        "s205_fable_generation_receipts_v1",
        "fable",
        fable_receipts,
        "COMPLETE",
    )

    sol_review, sol_review_receipt = runtime.call_sol(
        _review_content(
            packet,
            fable_candidates,
            sol_candidates,
            SOL_MODEL,
            FABLE_MODEL,
            "sol",
        ),
        "review:fable_candidates",
    )
    validate_review(sol_review, SOL_MODEL, FABLE_MODEL, fable_candidates)
    receipts.append(sol_review_receipt)
    write_json(
        SOL_REVIEW,
        sealed_artifact(
            "s205_sol_review_of_fable_v1",
            {"review": sol_review, "receipt": sol_review_receipt},
        ),
    )
    _check_budget(receipts, "Sol cross-review")

    fable_review, fable_review_receipt = runtime.call_fable(
        _review_content(
            packet,
            sol_candidates,
            fable_candidates,
            FABLE_MODEL,
            SOL_MODEL,
            "fable",
        ),
        10000,
        "review:sol_candidates",
    )
    validate_review(fable_review, FABLE_MODEL, SOL_MODEL, sol_candidates)
    receipts.append(fable_review_receipt)
    write_json(
        FABLE_REVIEW,
        sealed_artifact(
            "s205_fable_review_of_sol_v1",
            {"review": fable_review, "receipt": fable_review_receipt},
        ),
    )
    _check_budget(receipts, "Fable cross-review")

    if len(receipts) != MAX_CALLS:
        raise RuntimeError(f"call-contract drift: {len(receipts)} != {MAX_CALLS}")
    runtime.seal_complete(MAX_CALLS)

    passed = principal_publication_gate(fable_review, sol_review)
    status = "GO_KIDDE_GOLD_CANARY" if passed else "NO_GO_VISUAL_GOLD"
    if passed:
        questions = []
        for index, (candidate, item) in enumerate(
            zip(sol_candidates, packet["items"], strict=True), 1
        ):
            questions.append(
                {
                    "qid": f"s205k{index:02d}",
                    **candidate,
                    "split": "candidate_unintegrated",
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
                "s205_kidde_visual_gold_v1",
                {"status": status, "questions": questions, "official_fact_credit": 0},
            ),
        )

    result = sealed_artifact(
        "s205_kidde_visual_canary_result_v1",
        {
            "status": status,
            "calls": len(receipts),
            "models": {
                "principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING},
                "independent": FABLE_MODEL,
            },
            "generation": {
                "sol_valid": len(sol_candidates),
                "fable_valid": len(fable_candidates),
            },
            "publication_geometry": {
                "final_gold_author": SOL_MODEL,
                "fable_of_sol_publication_all_pass": all_pass(fable_review),
                "sol_of_fable_publication_all_pass_diagnostic": all_pass(sol_review),
                "counterpart_disagreement_probe_pass": principal_publication_gate(
                    fable_review, sol_review
                ),
            },
            "conservative_cost_usd": conservative_cost(
                receipts, CONSERVATIVE_PRICES
            ),
            "budget_usd": INTERNAL_BUDGET_USD,
            "official_fact_credit": 0,
            "bot_evaluation_opened": False,
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    )
    write_json(RESULT, result)
    print(
        json.dumps(
            {
                "status": status,
                "calls": len(receipts),
                "conservative_cost_usd": result["conservative_cost_usd"],
            },
            indent=2,
        )
    )
    return 0 if passed else 2


def preflight(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    body = dict(packet)
    expected = body.pop("packet_sha256")
    if stable_sha(body) != expected:
        raise ValueError("S205 packet hash mismatch")
    images = 0
    for item in packet["items"]:
        for page in item["rendered_pages"]:
            page_content_openai(ROOT, {**item, "rendered_pages": [page]}, "verify")
            images += 1
    expected_contract = {
        "principal": {"model": SOL_MODEL, "reasoning_effort": SOL_REASONING},
        "independent": {"model": FABLE_MODEL},
        "pixel_only_frontier_input": True,
        "independent_generation_before_cross_review": True,
        "final_gold_author": SOL_MODEL,
        "principal_publication_review": "fable_must_pass_every_sol_candidate",
        "counterpart_role": "blind_material_disagreement_probe_not_publication_candidate",
        "counterpart_gate": "topic_aligned_and_zero_material_disagreement",
        "merge_candidates": False,
        "same_item_retry": False,
        "application_inference_without_explicit_pixel_support": "forbidden",
    }
    if packet["generation_contract"] != expected_contract:
        raise ValueError("S205 generation contract drift")
    print(
        json.dumps(
            {
                "status": "PREFLIGHT_PASS",
                "items": len(packet["items"]),
                "images": images,
                "paid_calls": 0,
            },
            indent=2,
        )
    )
    return 0


def _write_terminal_result(exc: Exception) -> None:
    if RESULT.exists():
        return
    calls: list[dict[str, Any]] = []
    if CALL_LEDGER.exists():
        ledger = json.loads(CALL_LEDGER.read_text(encoding="utf-8"))
        calls = ledger.get("calls") or []
    status = (
        "NO_GO_VISUAL_GOLD"
        if isinstance(exc, SemanticNoGo)
        else "HOLD_FRONTIER_INCOMPLETE"
    )
    write_json(
        RESULT,
        sealed_artifact(
            "s205_kidde_visual_canary_result_v1",
            {
                "status": status,
                "calls": len(calls),
                "reason": f"{type(exc).__name__}: {exc}",
                "official_fact_credit": 0,
                "bot_evaluation_opened": False,
                "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
                "railway_merge_gate": False,
            },
        ),
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
        _write_terminal_result(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
