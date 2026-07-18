#!/usr/bin/env python3
"""Reciprocally review the S266 Kidde candidates against immutable pixels."""
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

from src.rag.frontier_visual_runtime_v3 import FrontierVisualRuntime  # noqa: E402
from src.rag.frontier_visual_schemas import (  # noqa: E402
    anthropic_compatible_schema,
    review_schema,
)
from src.rag.multisource_visual_gold import (  # noqa: E402
    page_content_fable,
    page_content_openai,
    principal_publication_gate,
    review_prompt,
    validate_review,
)
from src.rag.visual_gold import (  # noqa: E402
    conservative_cost,
    normalized_text_sha,
    parse_json,
    sealed_artifact,
    stable_sha,
    write_json,
)


PACKET = ROOT / "evals/s217_kidde_external_cohort_packet_v1.json"
PREREG = ROOT / "evals/s267_kidde_reciprocal_pixel_review_prereg_v1.yaml"
S266_RESULT = ROOT / "evals/s266_kidde_background_result_v1.json"
S266_LEDGER = ROOT / "evals/s266_kidde_background_ledger_v1.json"
S266_FABLE = ROOT / "evals/s266_kidde_fable_generations_v1.json"
S266_SOL = ROOT / "evals/s266_kidde_sol_generations_v1.json"
ATTEMPTS = ROOT / "evals/s267_kidde_reciprocal_review_attempts_v1.json"
LEDGER = ROOT / "evals/s267_kidde_reciprocal_review_ledger_v1.json"
BACKGROUND_STATES = ROOT / "evals/s267_kidde_reciprocal_review_states_v1"
SOL_REVIEWS = ROOT / "evals/s267_kidde_sol_reviews_of_fable_v1.json"
FABLE_REVIEWS = ROOT / "evals/s267_kidde_fable_reviews_of_sol_v1.json"
PIXEL_GOLD = ROOT / "evals/s267_kidde_pixel_gold_v1.json"
RESULT = ROOT / "evals/s267_kidde_reciprocal_review_result_v1.json"
OUTPUTS = (ATTEMPTS, LEDGER, SOL_REVIEWS, FABLE_REVIEWS, PIXEL_GOLD, RESULT)

SOL = "gpt-5.6-sol"
FABLE = "claude-fable-5"
FABLE_MAX_TOKENS = 16000
MIN_PIXEL_GOLDS = 3
EXPECTED_CALLS = 8
INTERNAL_BUDGET_USD = 80.0
PRICES = {
    "sol": {"input": 5.0, "output": 30.0},
    "fable": {"input": 30.0, "output": 150.0},
}


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _checkpoint(path: Path, schema: str, body: dict[str, Any]) -> None:
    write_json(path, sealed_artifact(schema, body))


def _record_attempt(provider: str, label: str) -> None:
    attempts: list[dict[str, Any]] = []
    if ATTEMPTS.exists():
        value = _sealed(ATTEMPTS)
        if value.get("schema") != "s267_kidde_reciprocal_review_attempts_v1":
            raise ValueError("S267 attempt schema drift")
        attempts = list(value.get("attempts") or [])
    identity = (provider, label)
    identities = [(row.get("provider"), row.get("call_label")) for row in attempts]
    if identity in identities:
        if identities[-1] != identity:
            raise RuntimeError("S267 attempt identity is duplicated out of order")
        return
    attempts.append({
        "provider": provider,
        "call_label": label,
        "semantic_attempt": 1,
    })
    _checkpoint(ATTEMPTS, "s267_kidde_reciprocal_review_attempts_v1", {
        "attempts": attempts,
    })


class S267Runtime(FrontierVisualRuntime):
    def call_sol(
        self,
        content: list[dict[str, Any]],
        call_label: str,
        *,
        output_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del output_schema
        _record_attempt("sol", call_label)
        item_id = call_label.removeprefix("review:fable:")
        return super().call_sol(
            content,
            call_label,
            output_schema=review_schema(SOL, FABLE, item_id),
        )

    def call_fable(
        self,
        content: list[dict[str, Any]],
        max_tokens: int,
        call_label: str,
        *,
        output_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del max_tokens, output_schema
        _record_attempt("fable", call_label)
        item_id = call_label.removeprefix("review:sol:")
        schema = review_schema(FABLE, SOL, item_id)
        return super().call_fable(
            content,
            FABLE_MAX_TOKENS,
            call_label,
            output_schema=anthropic_compatible_schema(schema),
        )


def _runtime(env_file: Path) -> S267Runtime:
    secrets = dotenv_values(env_file)
    openai_key = str(
        secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = str(
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S267 provider credentials are unavailable")
    return S267Runtime(
        ledger_path=LEDGER,
        ledger_schema="s267_kidde_reciprocal_review_ledger_v1",
        sol_model=SOL,
        fable_model=FABLE,
        sol_reasoning="xhigh",
        fable_effort="xhigh",
        prices=PRICES,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
        sol_background=True,
        sol_transport_retries=2,
        sol_poll_interval_seconds=2.0,
        sol_poll_timeout_seconds=1800.0,
        sol_state_dir=BACKGROUND_STATES,
    )


def verify_prereg(
    packet: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_RECIPROCAL_PIXEL_REVIEW":
        raise ValueError("S267 preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S267 frozen input drift: {label}")
    packet_body = dict(packet)
    packet_sha = packet_body.pop("packet_sha256", None)
    if stable_sha(packet_body) != packet_sha:
        raise ValueError("S267 packet identity drift")
    result = _sealed(S266_RESULT)
    ledger = _sealed(S266_LEDGER)
    fable = _sealed(S266_FABLE)
    sol = _sealed(S266_SOL)
    if result.get("status") != "GO_S266_TO_SEPARATE_RECIPROCAL_PIXEL_REVIEW":
        raise ValueError("S267 requires the exact S266 GO")
    if ledger.get("status") != "COMPLETE" or len(ledger.get("calls") or []) != 5:
        raise ValueError("S267 S266 ledger lineage drift")
    for provider, artifact in (("fable", fable), ("sol", sol)):
        items = artifact.get("items") or []
        if artifact.get("status") != "COMPLETE" or len(items) != 4:
            raise ValueError(f"S267 {provider} candidate lineage drift")
        if any(row.get("validation_status") != "VALID" for row in items):
            raise ValueError(f"S267 can review only valid {provider} candidates")
    fable_ids = [row["canary_id"] for row in fable["items"]]
    sol_ids = [row["canary_id"] for row in sol["items"]]
    packet_ids = [row["canary_id"] for row in packet["items"]]
    if fable_ids != packet_ids or sol_ids != packet_ids:
        raise ValueError("S267 candidate order or coverage drift")
    return result, fable, sol


def preflight(packet: dict[str, Any], *, allow_resume: bool = False) -> int:
    verify_prereg(packet)
    images = 0
    for item in packet["items"]:
        page_content_openai(ROOT, item, "verify")
        page_content_fable(ROOT, item, "verify")
        images += len(item["rendered_pages"])
    existing = [path.relative_to(ROOT).as_posix() for path in OUTPUTS if path.exists()]
    if not allow_resume and (existing or BACKGROUND_STATES.exists()):
        raise FileExistsError(
            f"S267 outputs already exist: {existing + ([BACKGROUND_STATES.relative_to(ROOT).as_posix()] if BACKGROUND_STATES.exists() else [])}"
        )
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "candidate_pairs": 4,
        "reciprocal_review_calls": EXPECTED_CALLS,
        "sol_background": True,
        "images": images,
        "paid_calls": 0,
        "target_calls": 0,
    }))
    return 0


def _candidate_maps(
    fable: dict[str, Any], sol: dict[str, Any]
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        "fable": {row["canary_id"]: row["candidate"] for row in fable["items"]},
        "sol": {row["canary_id"]: row["candidate"] for row in sol["items"]},
    }


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
        + json.dumps({
            "topic": item["topic"],
            "distinct_sources_min": item["distinct_sources_min"],
            "cross_source_facts_min": item["cross_source_facts_min"],
            "known_conflicts": item["known_conflicts"],
        }, ensure_ascii=False)
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


def _call_plan(packet: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    plan: list[tuple[str, dict[str, Any]]] = []
    for item in packet["items"]:
        plan.extend((("sol", item), ("fable", item)))
    if len(plan) != EXPECTED_CALLS:
        raise ValueError("S267 review call geometry drift")
    return plan


def _call_identity(provider: str, item: dict[str, Any]) -> tuple[str, str]:
    author = "fable" if provider == "sol" else "sol"
    return provider, f"review:{author}:{item['canary_id']}"


def _review_row(
    provider: str,
    item: dict[str, Any],
    value: dict[str, Any],
    receipt: dict[str, Any],
    candidates: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    reviewer, author = (SOL, FABLE) if provider == "sol" else (FABLE, SOL)
    candidate_provider = "fable" if provider == "sol" else "sol"
    error = None
    try:
        validate_review(
            value,
            reviewer,
            author,
            candidates[candidate_provider][item["canary_id"]],
        )
    except ValueError as exc:
        error = str(exc)
    return {
        "canary_id": item["canary_id"],
        "review": value,
        "validation_error": error,
        "receipt": receipt,
    }


def _validate_review_checkpoint(
    path: Path, schema: str, reconstructed: list[dict[str, Any]]
) -> None:
    if not path.exists():
        return
    value = _sealed(path)
    if value.get("schema") != schema or value.get("status") not in {
        "IN_PROGRESS", "COMPLETE"
    }:
        raise ValueError(f"S267 review checkpoint metadata drift: {path.name}")
    checkpointed = value.get("items") or []
    if len(checkpointed) > len(reconstructed):
        raise ValueError(f"S267 review checkpoint is ahead of ledger: {path.name}")
    if checkpointed != reconstructed[:len(checkpointed)]:
        raise ValueError(f"S267 review checkpoint is not a ledger prefix: {path.name}")


def _reconstruct_resume_state(
    packet: dict[str, Any],
    runtime: S267Runtime,
    candidates: dict[str, dict[str, dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], int]:
    plan = _call_plan(packet)
    expected = [_call_identity(provider, item) for provider, item in plan]
    calls = list(runtime.load_ledger().get("calls") or [])
    actual = [(row.get("provider"), row.get("call_label")) for row in calls]
    if actual != expected[:len(actual)] or len(actual) > EXPECTED_CALLS:
        raise ValueError("S267 ledger is not an exact call-plan prefix")
    rows: dict[str, list[dict[str, Any]]] = {"sol": [], "fable": []}
    items_by_id = {item["canary_id"]: item for item in packet["items"]}
    for receipt in calls:
        provider = str(receipt["provider"])
        required_status = "completed" if provider == "sol" else "end_turn"
        required_model = SOL if provider == "sol" else FABLE
        if receipt.get("status") != required_status or receipt.get("model") != required_model:
            raise RuntimeError("S267 cannot resume past an incomplete review receipt")
        item_id = str(receipt["call_label"]).split(":", 2)[-1]
        rows[provider].append(_review_row(
            provider,
            items_by_id[item_id],
            parse_json(str(receipt.get("raw_output") or "")),
            receipt,
            candidates,
        ))
    _validate_review_checkpoint(
        SOL_REVIEWS, "s267_kidde_sol_reviews_of_fable_v1", rows["sol"]
    )
    _validate_review_checkpoint(
        FABLE_REVIEWS, "s267_kidde_fable_reviews_of_sol_v1", rows["fable"]
    )
    attempts: list[dict[str, Any]] = []
    if ATTEMPTS.exists():
        artifact = _sealed(ATTEMPTS)
        if artifact.get("schema") != "s267_kidde_reciprocal_review_attempts_v1":
            raise ValueError("S267 attempt schema drift")
        attempts = list(artifact.get("attempts") or [])
    attempt_ids = [(row.get("provider"), row.get("call_label")) for row in attempts]
    if attempt_ids[:len(actual)] != actual or len(attempt_ids) > len(actual) + 1:
        raise ValueError("S267 attempts are not an exact ledger prefix")
    if len(attempt_ids) == len(actual) + 1:
        if len(actual) == len(expected) or attempt_ids[-1] != expected[len(actual)]:
            raise ValueError("S267 dangling attempt is outside the frozen call plan")
        if attempt_ids[-1][0] != "sol" or not BACKGROUND_STATES.exists():
            raise RuntimeError(
                "S267 cannot safely repeat an ambiguous non-resumable frontier POST"
            )
    return rows, len(calls)


def _write_result(runtime: S267Runtime, status: str, **extra: Any) -> None:
    calls = runtime.load_ledger().get("calls") or []
    s266 = _sealed(S266_RESULT)
    prior_cost = float(s266["conservative_cost_total_usd"])
    new_cost = conservative_cost(calls, PRICES)
    _checkpoint(RESULT, "s267_kidde_reciprocal_review_result_v1", {
        "status": status,
        **extra,
        "s267_review_calls": len(calls),
        "conservative_cost_s267_usd": new_cost,
        "conservative_cost_through_s267_usd": prior_cost + new_cost,
        "sol_background": True,
        "background_create_retries": 0,
        "poll_get_retries_max": 2,
        "semantic_retries": 0,
        "candidate_repairs_or_merges": 0,
        "support_mapping_calls": 0,
        "target_calls": 0,
        "official_fact_credit": 0,
        "official_denominator_change": 0,
        "production_default_changed": False,
        "chunks_v2": "ACTIVE_READ_ONLY",
        "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
        "railway_merge_gate": False,
    })


def execute(packet: dict[str, Any], env_file: Path) -> int:
    preflight(packet, allow_resume=True)
    _result, fable, sol = verify_prereg(packet)
    candidates = _candidate_maps(fable, sol)
    runtime = _runtime(env_file)
    if RESULT.exists():
        prior = _sealed(RESULT)
        if prior.get("status") == "GO_S267_PIXEL_GOLD":
            return 0
        if prior.get("status") == "NO_GO_S267_PIXEL_REVIEW":
            return 2
        if prior.get("status") != "HOLD_S267_EXTERNAL_OR_INCOMPLETE":
            raise ValueError("S267 result status drift")
    rows, completed = _reconstruct_resume_state(packet, runtime, candidates)
    _checkpoint(SOL_REVIEWS, "s267_kidde_sol_reviews_of_fable_v1", {
        "status": "IN_PROGRESS", "items": rows["sol"]
    })
    _checkpoint(FABLE_REVIEWS, "s267_kidde_fable_reviews_of_sol_v1", {
        "status": "IN_PROGRESS", "items": rows["fable"]
    })
    try:
        for index, (provider, item) in enumerate(_call_plan(packet)):
            if index < completed:
                continue
            item_id = item["canary_id"]
            if provider == "sol":
                value, receipt = runtime.call_sol(
                    _review_content(
                        packet, item, candidates["fable"][item_id],
                        candidates["sol"][item_id], SOL, FABLE, "sol"
                    ),
                    f"review:fable:{item_id}",
                )
                path, schema = SOL_REVIEWS, "s267_kidde_sol_reviews_of_fable_v1"
            else:
                value, receipt = runtime.call_fable(
                    _review_content(
                        packet, item, candidates["sol"][item_id],
                        candidates["fable"][item_id], FABLE, SOL, "fable"
                    ),
                    FABLE_MAX_TOKENS,
                    f"review:sol:{item_id}",
                )
                path, schema = FABLE_REVIEWS, "s267_kidde_fable_reviews_of_sol_v1"
            rows[provider].append(
                _review_row(provider, item, value, receipt, candidates)
            )
            _checkpoint(path, schema, {
                "status": "IN_PROGRESS", "items": rows[provider]
            })
            if conservative_cost(runtime.load_ledger()["calls"], PRICES) > INTERNAL_BUDGET_USD:
                raise RuntimeError("S267 internal budget exceeded")
    except Exception as exc:
        _write_result(
            runtime,
            "HOLD_S267_EXTERNAL_OR_INCOMPLETE",
            reason=f"{type(exc).__name__}: {exc}",
        )
        raise

    _checkpoint(SOL_REVIEWS, "s267_kidde_sol_reviews_of_fable_v1", {
        "status": "COMPLETE", "items": rows["sol"]
    })
    _checkpoint(FABLE_REVIEWS, "s267_kidde_fable_reviews_of_sol_v1", {
        "status": "COMPLETE", "items": rows["fable"]
    })
    runtime.seal_complete(EXPECTED_CALLS)
    sol_by_id = {row["canary_id"]: row for row in rows["sol"]}
    fable_by_id = {row["canary_id"]: row for row in rows["fable"]}
    published_ids = []
    for item in packet["items"]:
        item_id = item["canary_id"]
        sol_row, fable_row = sol_by_id[item_id], fable_by_id[item_id]
        if (
            sol_row["validation_error"] is None
            and fable_row["validation_error"] is None
            and principal_publication_gate(fable_row["review"], sol_row["review"])
        ):
            published_ids.append(item_id)
    if len(published_ids) < MIN_PIXEL_GOLDS:
        _write_result(
            runtime,
            "NO_GO_S267_PIXEL_REVIEW",
            pixel_published_ids=published_ids,
        )
        return 2
    questions = []
    for index, item_id in enumerate(published_ids, 1):
        questions.append({
            "qid": f"s267k{index:02d}",
            **candidates["sol"][item_id],
            "split": "fresh_multisource_pixel_gold_unintegrated",
            "cross_review": {
                "fable_of_sol_publication": "PASS",
                "sol_of_fable_disagreement_probe": "PASS",
            },
        })
    _checkpoint(PIXEL_GOLD, "s267_kidde_pixel_gold_v1", {
        "status": "PIXEL_GOLD_PASS_UNINTEGRATED",
        "questions": questions,
        "official_fact_credit": 0,
    })
    _write_result(
        runtime,
        "GO_S267_PIXEL_GOLD",
        pixel_published_ids=published_ids,
        next_authorized_step="independent minimal-complete textual support mapping",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    if not args.execute:
        return preflight(packet)
    if args.env_file is None:
        raise ValueError("--env-file is required with --execute")
    return execute(packet, args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
