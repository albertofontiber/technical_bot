#!/usr/bin/env python3
"""Checkpointed two-answer probe for the S122 v2 enforcement boundary.

The runner uses frozen contexts and performs no retrieval, rerank, judge or
database work.  It records an attempt before contacting the provider, disables
SDK retries, and refuses to repeat an ambiguous attempt after a connection loss.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
LOCAL_GATE = ROOT / "evals/s122_enforced_answer_contract_gate_v2.yaml"
PREREG = ROOT / "evals/s123_s122_enforced_two_answer_probe_prereg_v1.yaml"
EXECUTION_PERMIT = ROOT / "evals/s123_s122_enforced_two_answer_probe_execution_permit_v1.yaml"
CHECKPOINT = ROOT / "evals/s123_s122_enforced_two_answer_probe_v1.partial.jsonl"
OUT = ROOT / "evals/s123_s122_enforced_two_answer_probe_v1.json"
QIDS = ("hp009", "hp017")


def stable_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def fact_checks(qid: str, answer: str) -> list[dict[str, Any]]:
    folded = _fold(answer)
    if qid == "hp009":
        rows = [
            (
                "m0.hp009.closed_loop_return.1",
                "lazo" in folded
                and bool(re.search(r"\bcerrad\w*\b", folded))
                and "retorno" in folded,
            ),
            (
                "m0.hp009.closed_loop_return.2",
                "inicio lazo" in folded
                and bool(re.search(r"(?<![a-z0-9])out(?![a-z0-9])", folded))
                and "retorno" in folded,
            ),
        ]
    elif qid == "hp017":
        rows = [
            (
                "m0.hp017.rule1.2",
                "regla 1" in folded
                and "cualquier entrada de alarma" in folded
                and "todas las sirenas" in folded
                and "por defecto" in folded
                and "elimin" in folded,
            )
        ]
    else:
        raise KeyError(qid)
    return [
        {"claim_id": claim_id, "deterministic_surface_present": present}
        for claim_id, present in rows
    ]


def _load_events() -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    attempts: dict[str, dict] = {}
    completions: dict[str, dict] = {}
    errors: dict[str, dict] = {}
    if not CHECKPOINT.exists():
        return attempts, completions, errors
    for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        qid = event["qid"]
        if qid not in QIDS:
            raise RuntimeError(f"unauthorized checkpoint qid: {qid}")
        event_type = event.get("event")
        if event_type == "attempt_started":
            if qid in attempts or qid in completions or qid in errors:
                raise RuntimeError(f"invalid or duplicate checkpoint event for {qid}")
            attempts[qid] = event
        elif event_type in {"answer_completed", "attempt_error"}:
            if qid not in attempts or qid in completions or qid in errors:
                raise RuntimeError(f"invalid or out-of-order checkpoint event for {qid}")
            target = completions if event_type == "answer_completed" else errors
            target[qid] = event
        else:
            raise RuntimeError(f"invalid checkpoint event for {qid}")
    return attempts, completions, errors


def _append_event(event: dict[str, Any]) -> None:
    with CHECKPOINT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _claim_path(qid: str) -> Path:
    return CHECKPOINT.with_name(f"{CHECKPOINT.stem}.{qid}.claim")


def _claim_attempt(qid: str, contract_sha256: str) -> None:
    path = _claim_path(qid)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(
            f"atomic claim already exists for {qid}; refusing concurrent or repeat spend"
        ) from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(contract_sha256 + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_payload(payload: dict[str, Any]) -> None:
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _automated_completion_checks(
    completed_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for row in completed_rows:
        qid = row["qid"]
        planner = row.get("answer_planner") or {}
        validation = row.get("final_validation") or {}
        conflict_validation = row.get("final_conflict_validation") or {}
        claims = row.get("diagnostic_claims") or []
        checks.update(
            {
                f"{qid}.stop_reason_end_turn": row.get("stop_reason") == "end_turn",
                f"{qid}.obligations_complete": (
                    validation.get("total") == 2
                    and validation.get("covered") == validation.get("total")
                ),
                f"{qid}.conflict_safe": not conflict_validation.get("unsafe"),
                f"{qid}.citations_present": bool(
                    row.get("obligation_citations_present")
                ),
                f"{qid}.diagnostic_surfaces_present": bool(claims)
                and all(claim["deterministic_surface_present"] for claim in claims),
            }
        )
        if qid == "hp009":
            checks.update(
                {
                    "hp009.action_allowed": planner.get("action")
                    in {"pass", "source_bound_reconstruction"},
                    "hp009.query_core_covered": planner.get("query_core_coverage")
                    is True,
                    "hp009.no_positive_eol_claim": not row.get(
                        "unsafe_positive_eol_claim"
                    ),
                }
            )
        elif qid == "hp017":
            checks.update(
                {
                    "hp017.action_fail_closed": planner.get("action")
                    == "fail_closed",
                    "hp017.query_core_not_covered": planner.get(
                        "query_core_coverage"
                    )
                    is False,
                }
            )
    return checks


def _assert_probe_open_for_spend(
    requested: tuple[str, ...],
    attempts: dict[str, dict],
    completions: dict[str, dict],
) -> None:
    if not requested:
        return
    ambiguous_or_failed = sorted(set(attempts) - set(completions))
    if ambiguous_or_failed:
        raise RuntimeError(
            "prior attempt is failed or ambiguous; remaining probe spend is forbidden: "
            + ", ".join(ambiguous_or_failed)
        )
    prior_checks = _automated_completion_checks(list(completions.values()))
    failed_checks = sorted(name for name, passed in prior_checks.items() if not passed)
    if failed_checks:
        raise RuntimeError(
            "prior completion is an automatic NO-GO; remaining probe spend is forbidden: "
            + ", ".join(failed_checks)
        )
    if requested == ("hp017",) and "hp009" not in completions:
        raise RuntimeError("hp017 spend requires a passing hp009 completion")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--execute-qids", default="")
    args = parser.parse_args()
    requested = tuple(
        item.strip() for item in args.execute_qids.split(",") if item.strip()
    )
    if (
        len(requested) != len(set(requested))
        or len(requested) > 1
        or any(qid not in QIDS for qid in requested)
    ):
        raise RuntimeError(f"execute-qids must be a unique subset of {QIDS}")

    load_dotenv(args.env_file, override=True)
    os.environ.update(
        {
            "CHUNKS_TABLE": "chunks_v2",
            "LLM_MAX_TOKENS": "3500",
            "GENERATOR_PROMPT_VARIANT": "fidelity",
            "GENERATOR_SELECTION_BLOCK": "on",
            "GENERATOR_INCLUDE_CONTEXT": "0",
            "ANSWER_OBLIGATION_PLANNER": "enforced",
            "POST_RERANK_COVERAGE": "on",
            "STRUCTURAL_NEIGHBOR_COVERAGE": "on",
            "CANONICAL_HYQ_COVERAGE": "on",
            "RERANK_POOL_COVERAGE": "on",
            "STRUCTURAL_CASCADE_COVERAGE": "on",
            "LOGICAL_RECORD_COVERAGE": "on",
        }
    )
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from src.config import LLM_MAX_TOKENS, LLM_MODEL
    from src.rag.answer_obligation_contract import ENFORCEMENT_POLICY_VERSION
    from src.rag.answer_planner import (
        ANSWER_PLANNER_CONTRACT_S122,
        _closed_loop_has_unsafe_eol_claim,
        build_answer_conflicts,
        build_answer_plan,
        enforceable_answer_plan,
        render_enforced_answer_contract_data,
        validate_answer_conflicts,
        validate_answer_plan,
    )
    import src.rag.generator as generator_module
    from src.rag.post_rerank_coverage import (
        coverage_context_content,
        is_validated_coverage_chunk,
    )

    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if LLM_MODEL != prereg["scope"]["generator_model"] or LLM_MAX_TOKENS != 3500:
        raise RuntimeError("generator model or output budget drifted from preregistration")
    if ENFORCEMENT_POLICY_VERSION != prereg["scope"]["enforcement_policy"]:
        raise RuntimeError("enforcement policy drifted from preregistration")
    if file_sha256(LOCAL_GATE) != prereg["lineage"]["local_gate"]["sha256"]:
        raise RuntimeError("local gate receipt drifted")
    if file_sha256(FREEZE) != prereg["lineage"]["frozen_contexts"]["sha256"]:
        raise RuntimeError("frozen context receipt drifted")
    local_gate = yaml.safe_load(LOCAL_GATE.read_text(encoding="utf-8"))
    for name, receipt in local_gate["implementation"].items():
        if file_sha256(ROOT / receipt["path"]) != receipt["sha256"]:
            raise RuntimeError(f"local gate implementation drift: {name}")
    if local_gate["contracts"]["planner"] != ANSWER_PLANNER_CONTRACT_S122:
        raise RuntimeError("planner version drifted from local gate")
    if local_gate["contracts"]["enforcement_policy"] != ENFORCEMENT_POLICY_VERSION:
        raise RuntimeError("enforcement version drifted from local gate")

    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {row["qid"]: row for row in freeze["rows"]}
    if not set(QIDS) <= set(frozen):
        raise RuntimeError("frozen context is missing an authorized qid")

    attempts, completions, errors = _load_events()
    source_receipts = {
        path: file_sha256(ROOT / path)
        for path in (
            "src/rag/answer_planner.py",
            "src/rag/answer_obligation_contract.py",
            "src/rag/generator.py",
            "scripts/s123_s122_enforced_two_answer_probe.py",
            "evals/s123_s122_enforced_two_answer_probe_prereg_v1.yaml",
            "evals/s122_enforced_answer_contract_gate_v2.yaml",
        )
    }

    runtime: dict[str, tuple] = {}
    preflight = []
    for qid in QIDS:
        row = frozen[qid]
        relevant = [
            chunk
            for chunk in row["context"]
            if chunk.get("similarity", 0) >= generator_module.RELEVANCE_THRESHOLD
            or is_validated_coverage_chunk(chunk)
        ]
        plan = build_answer_plan(
            row["question"],
            relevant,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        enforced_plan = enforceable_answer_plan(plan)
        conflicts = build_answer_conflicts(
            row["question"],
            relevant,
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
        )
        expected = prereg["expected_contract"][qid]
        kinds = [item.kind for item in plan]
        if kinds != expected["obligations"]:
            raise RuntimeError(
                f"planner contract drift for {qid}: expected {expected['obligations']}, got {kinds}"
            )
        conflict_values = sorted(
            {value for conflict in conflicts for value in conflict.values}, key=int
        )
        expected_values = sorted(expected.get("conflict_values", []), key=int)
        if conflict_values != expected_values:
            raise RuntimeError(
                f"conflict contract drift for {qid}: expected {expected_values}, got {conflict_values}"
            )
        generation_contract = {
            "contract": "s123_s122_enforced_generation_contract_v1",
            "qid": qid,
            "question": row["question"],
            "frozen_context": row["context"],
            "relevant_context_ids": [chunk.get("id") for chunk in relevant],
            "rendered_context": [coverage_context_content(chunk) for chunk in relevant],
            "answer_plan": [item.to_dict() for item in plan],
            "enforced_plan": [item.to_dict() for item in enforced_plan],
            "conflicts": [item.to_dict() for item in conflicts],
            "rendered_enforced_contract": render_enforced_answer_contract_data(
                enforced_plan, conflicts
            ),
            "system": generator_module._assemble_system(
                row["question"], enforced_policy=True
            ),
            "model": LLM_MODEL,
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": 0,
            "provider_sdk_max_retries": 0,
            "provider_timeout_seconds": 120,
            "source_receipts": source_receipts,
        }
        contract_sha256 = stable_sha256(generation_contract)
        for event in (attempts.get(qid), completions.get(qid), errors.get(qid)):
            if event and event["generation_contract_sha256"] != contract_sha256:
                raise RuntimeError(f"stale checkpoint for {qid}; refusing repeat spend")
        claim_path = _claim_path(qid)
        if claim_path.exists():
            claimed_contract = claim_path.read_text(encoding="utf-8").strip()
            if claimed_contract != contract_sha256:
                raise RuntimeError(f"stale atomic claim for {qid}; refusing spend")
            if qid not in attempts:
                raise RuntimeError(
                    f"orphan atomic claim for {qid}; provider outcome is ambiguous"
                )
        citations = sorted({f"[F{item.fragment_number}]" for item in enforced_plan})
        preflight.append(
            {
                "qid": qid,
                "context_rows": len(relevant),
                "obligation_kinds": kinds,
                "conflict_values": conflict_values,
                "obligation_citations": citations,
                "generation_contract_sha256": contract_sha256,
                "attempted": qid in attempts,
                "completed": qid in completions,
                "ambiguous_or_failed": qid in attempts and qid not in completions,
            }
        )
        runtime[qid] = (
            row,
            relevant,
            plan,
            enforced_plan,
            conflicts,
            citations,
            contract_sha256,
        )

    permit_valid = False
    permit_status = "missing"
    if EXECUTION_PERMIT.exists():
        permit = yaml.safe_load(EXECUTION_PERMIT.read_text(encoding="utf-8"))
        permit_status = permit.get("status", "invalid")
        if permit_status == "APPROVED_AFTER_ADVERSARIAL_REVIEW":
            for name, receipt in permit["pinned_files"].items():
                if file_sha256(ROOT / receipt["path"]) != receipt["sha256"]:
                    raise RuntimeError(f"execution permit file drift: {name}")
            observed_contracts = {qid: runtime[qid][-1] for qid in QIDS}
            if observed_contracts != permit["generation_contract_sha256"]:
                raise RuntimeError("generation contract drifted from execution permit")
            if permit["controls"]["maximum_calls_per_qid"] != 1:
                raise RuntimeError("execution permit call control drift")
            permit_valid = True
            permit_status = "valid"
    if requested and not permit_valid:
        raise RuntimeError("valid execution permit required before provider spend")
    _assert_probe_open_for_spend(requested, attempts, completions)

    fresh_attempts_this_run: list[str] = []
    for qid in requested:
        if qid in completions:
            continue
        if qid in attempts:
            raise RuntimeError(
                f"{qid} already has an incomplete or failed attempt; automatic retry forbidden"
            )
        (
            row,
            relevant,
            plan,
            enforced_plan,
            conflicts,
            citations,
            contract_sha256,
        ) = runtime[qid]
        _claim_attempt(qid, contract_sha256)
        attempts, completions, errors = _load_events()
        if qid in attempts or qid in completions or qid in errors:
            raise RuntimeError(
                f"checkpoint appeared after atomic claim for {qid}; refusing spend"
            )
        attempt = {
            "event": "attempt_started",
            "qid": qid,
            "generation_contract_sha256": contract_sha256,
            "model": LLM_MODEL,
            "max_output_tokens": LLM_MAX_TOKENS,
            "provider_sdk_max_retries": 0,
        }
        _append_event(attempt)
        attempts[qid] = attempt
        fresh_attempts_this_run.append(qid)

        original_client = generator_module.anthropic.Anthropic
        generator_module.anthropic.Anthropic = lambda api_key: original_client(
            api_key=api_key,
            max_retries=0,
            timeout=120.0,
        )
        try:
            result = generator_module.generate_answer(row["question"], relevant)
        except Exception as exc:
            error = {
                "event": "attempt_error",
                "qid": qid,
                "generation_contract_sha256": contract_sha256,
                "error_type": type(exc).__name__,
                "automatic_retry_permitted": False,
            }
            _append_event(error)
            errors[qid] = error
            continue
        finally:
            generator_module.anthropic.Anthropic = original_client

        answer = result["answer"]
        planner = result.get("answer_planner") or {}
        final_validation = validate_answer_plan(answer, enforced_plan)
        final_conflicts = validate_answer_conflicts(answer, conflicts)
        completion = {
            "event": "answer_completed",
            "qid": qid,
            "generation_contract_sha256": contract_sha256,
            "model": LLM_MODEL,
            "max_output_tokens": LLM_MAX_TOKENS,
            "stop_reason": result.get("stop_reason"),
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
            "answer_sha256": text_sha256(answer),
            "obligation_citations_present": all(
                citation in answer for citation in citations
            ),
            "final_validation": final_validation,
            "final_conflict_validation": final_conflicts,
            "unsafe_positive_eol_claim": (
                _closed_loop_has_unsafe_eol_claim(answer) if qid == "hp009" else False
            ),
            "diagnostic_claims": fact_checks(qid, answer),
            "answer_planner": planner,
            "answer": answer,
            "manual_review_required": True,
        }
        _append_event(completion)
        completions[qid] = completion

    rows = []
    for item in preflight:
        qid = item["qid"]
        completion = completions.get(qid)
        rows.append(
            {
                **item,
                "attempted": qid in attempts,
                "completed": completion is not None,
                "ambiguous_or_failed": qid in attempts and completion is None,
                **(completion or {}),
                **({"attempt_error": errors[qid]} if qid in errors else {}),
            }
        )
    completed_rows = [row for row in rows if row["completed"]]
    surfaces = [
        claim
        for row in completed_rows
        for claim in row.get("diagnostic_claims", [])
    ]
    automated_checks = _automated_completion_checks(completed_rows)
    ambiguous_or_failed = sorted(set(attempts) - set(completions))
    completed_automatic_failure = any(
        not passed for passed in automated_checks.values()
    )
    if ambiguous_or_failed:
        status = "ATTEMPT_FAILED_OR_AMBIGUOUS_NO_RETRY"
    elif completed_automatic_failure:
        status = "AUTOMATIC_NO_GO"
    elif len(completions) == len(QIDS):
        status = "MEASURED_TWO_ANSWER_PROBE_PENDING_MANUAL_ADJUDICATION"
    else:
        status = "PREFLIGHT_OR_PARTIAL_CHECKPOINT"
    gate = {
        "authorized_qids": list(QIDS),
        "requested_this_run": list(requested),
        "fresh_attempts_this_run": fresh_attempts_this_run,
        "attempted_qids": sorted(attempts),
        "completed_qids": sorted(completions),
        "ambiguous_or_failed_qids": ambiguous_or_failed,
        "remaining_unattempted_qids": sorted(set(QIDS) - set(attempts)),
        "input_tokens": sum(row.get("input_tokens") or 0 for row in completed_rows),
        "output_tokens": sum(row.get("output_tokens") or 0 for row in completed_rows),
        "max_token_stops": sum(
            row.get("stop_reason") == "max_tokens" for row in completed_rows
        ),
        "actions": {
            row["qid"]: (row.get("answer_planner") or {}).get("action")
            for row in completed_rows
        },
        "deterministic_claim_surfaces_present": sum(
            claim["deterministic_surface_present"] for claim in surfaces
        ),
        "diagnostic_claims": len(surfaces),
        "execution_permit": permit_status,
        "automated_checks": automated_checks,
        "failed_automated_checks": sorted(
            name for name, passed in automated_checks.items() if not passed
        ),
        "retrieval_calls": 0,
        "reranker_calls": 0,
        "judge_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "facts_moved_to_ok": 0,
        "status": status,
    }
    payload = {
        "instrument": "s123_s122_enforced_two_answer_probe_v1",
        "planner_contract": ANSWER_PLANNER_CONTRACT_S122,
        "enforcement_policy": ENFORCEMENT_POLICY_VERSION,
        "source_receipts": source_receipts,
        "gate": gate,
        "rows": rows,
        "limitations": [
            "No fact moves to OK before local atomic and adversarial adjudication.",
            "The provider model is held constant with S121 to isolate enforcement.",
            "A persisted ambiguous attempt is never retried automatically.",
            "The probe performs no retrieval, rerank, judge or database work.",
        ],
    }
    _write_payload(payload)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 1 if status in {"AUTOMATIC_NO_GO", "ATTEMPT_FAILED_OR_AMBIGUOUS_NO_RETRY"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
