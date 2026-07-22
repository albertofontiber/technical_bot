#!/usr/bin/env python3
"""Development-only, zero-call counterfactual preflight for S277 C1 P1.

The instrument replays only the deterministic post-generation boundary over the
drafts and served contexts persisted by an existing P1.  It deliberately does
not create authoritative P1 receipts and cannot award release credit.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from typing import Any, Callable, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SCHEMA_VERSION = "s277_c1_p1_offline_counterfactual_v1"
AUTHORITY = "DEVELOPMENT_PREFLIGHT_ONLY_NO_RELEASE_CREDIT"
FROZEN_CONTEXT_PASS = "OFFLINE_FROZEN_CONTEXT_PASS"
HOLD = "OFFLINE_PREFLIGHT_HOLD"
SOURCE_CONTEXT_MODE = "FROZEN_SOURCE_RUN_ONLY"
NEXT_REQUIRED_GATE = "CANDIDATE_CONTEXT_SOURCE_RECEIPT_PREFLIGHT"
BASELINE_PASS = "ADJUDICATED_PASS"
BASELINE_FAIL = "ADJUDICATED_FAIL"
EXPECTED_REVIEW_ITEMS = 91
EXPECTED_BASELINE_PASSES = 62
EXPECTED_BASELINE_FAILS = 29
STAGE_NAMES = (
    "diagram_postprocess",
    "answer_planner",
    "must_preserve",
    "conflict_guard",
)


class CounterfactualPreflightError(RuntimeError):
    """Raised when the frozen inputs or the development instrument drift."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CounterfactualPreflightError(message)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_lf_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CounterfactualPreflightError(
            f"cannot read JSON object {path}: {type(exc).__name__}"
        ) from exc
    _require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def assert_output_outside_source_run(output: Path, source_run: Path) -> None:
    resolved_output = output.resolve()
    resolved_source = source_run.resolve()
    _require(
        not resolved_output.is_relative_to(resolved_source),
        "output may not modify the frozen source run",
    )


def _decision_rows(payload: Mapping[str, Any], path: Path) -> list[dict[str, Any]]:
    for key in ("recommendations", "rows"):
        rows = payload.get(key)
        if isinstance(rows, list) and all(isinstance(row, dict) for row in rows):
            return rows
    raise CounterfactualPreflightError(f"adjudication rows are absent: {path}")


def load_decisions(
    paths: Sequence[Path],
    *,
    require_binding: bool = False,
) -> dict[str, dict[str, Any]]:
    """Load canonical adjudications or the three blind-batch row shapes."""

    decisions: dict[str, dict[str, Any]] = {}
    for path in paths:
        payload = read_json_object(path)
        for row in _decision_rows(payload, path):
            review_key = str(row.get("review_key") or "")
            decision = row.get("decision") or row.get("recommendation")
            binding = row.get("binding_sha256")
            _require(bool(review_key), f"empty review_key in {path}")
            _require(
                decision in {BASELINE_PASS, BASELINE_FAIL},
                f"invalid decision for {review_key} in {path}",
            )
            _require(review_key not in decisions, f"duplicate decision: {review_key}")
            if require_binding:
                _require(
                    isinstance(binding, str) and len(binding) == 64,
                    f"candidate decision lacks a hash binding: {review_key}",
                )
            decisions[review_key] = {
                "review_key": review_key,
                "decision": decision,
                "binding_sha256": binding,
                "source": str(path.resolve()),
            }
    return decisions


def leaf_checks(check: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    evidence = check.get("evidence")
    nested = evidence.get("checks") if isinstance(evidence, dict) else None
    if isinstance(nested, list) and nested and all(isinstance(row, dict) for row in nested):
        leaves: list[Mapping[str, Any]] = []
        for row in nested:
            leaves.extend(leaf_checks(row))
        return leaves
    return [check]


def leaf_check_map(score: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    checks = score.get("checks")
    _require(isinstance(checks, list), "candidate/source score has no checks list")
    output: dict[str, Mapping[str, Any]] = {}
    for top_level in checks:
        _require(isinstance(top_level, dict), "score check is not an object")
        for check in leaf_checks(top_level):
            check_id = str(check.get("check_id") or "")
            _require(bool(check_id), "leaf check lacks check_id")
            _require(check_id not in output, f"duplicate leaf check: {check_id}")
            output[check_id] = check
    return output


def _stage_map(receipt: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    chain = receipt.get("generation_chain")
    stages = chain.get("stages") if isinstance(chain, dict) else None
    _require(isinstance(stages, list), "generation_chain stages are absent")
    output: dict[str, Mapping[str, Any]] = {}
    for stage in stages:
        _require(isinstance(stage, dict), "generation stage is not an object")
        name = str(stage.get("name") or "")
        _require(name not in output, f"duplicate generation stage: {name}")
        output[name] = stage
    _require(
        all(name in output for name in STAGE_NAMES),
        "required post-generation stages are absent",
    )
    return output


def replay_receipt(
    receipt: Mapping[str, Any],
    *,
    apply_answer_planner: Callable[..., tuple[str, Any]],
    apply_must_preserve_contract: Callable[..., tuple[str, Any]],
    detect_atoms: Callable[..., Any],
    apply_answer_conflict_guard: Callable[..., tuple[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay the deterministic boundary and return row plus ephemeral score view."""

    replica_key = str(receipt.get("replica_key") or "")
    input_row = receipt.get("input")
    question = input_row.get("question") if isinstance(input_row, dict) else None
    context = receipt.get("served_context")
    _require(bool(replica_key), "replica_key is absent")
    _require(isinstance(question, str) and question.strip(), f"question absent: {replica_key}")
    _require(isinstance(context, list), f"served_context absent: {replica_key}")

    stages = _stage_map(receipt)
    frozen_draft = stages["diagram_postprocess"].get("output_text")
    _require(isinstance(frozen_draft, str), f"frozen draft absent: {replica_key}")
    _require(
        stages["diagram_postprocess"].get("output_sha256") == sha256_text(frozen_draft),
        f"frozen draft hash drift: {replica_key}",
    )

    planned, planner_trace = apply_answer_planner(question, context, frozen_draft)
    _require(isinstance(planned, str), f"planner returned non-text: {replica_key}")
    preserved, must_preserve_trace = apply_must_preserve_contract(
        question,
        context,
        planned,
        detect_fn=detect_atoms,
    )
    _require(isinstance(preserved, str), f"must-preserve returned non-text: {replica_key}")
    guarded, conflict_trace = apply_answer_conflict_guard(question, context, preserved)
    _require(isinstance(guarded, str), f"conflict guard returned non-text: {replica_key}")

    candidate_stages = [
        {
            "name": "answer_planner",
            "input_sha256": sha256_text(frozen_draft),
            "output_sha256": sha256_text(planned),
            "trace": planner_trace,
        },
        {
            "name": "must_preserve",
            "input_sha256": sha256_text(planned),
            "output_sha256": sha256_text(preserved),
            "trace": must_preserve_trace,
        },
        {
            "name": "conflict_guard",
            "input_sha256": sha256_text(preserved),
            "output_sha256": sha256_text(guarded),
            "trace": conflict_trace,
        },
    ]

    scoring_view = deepcopy(dict(receipt))
    scoring_view["answer"] = guarded
    scoring_view["answer_sha256"] = sha256_text(guarded)
    original_mp = scoring_view.get("must_preserve")
    scoring_view["must_preserve"] = {
        **(original_mp if isinstance(original_mp, dict) else {}),
        "status": "evaluated" if isinstance(must_preserve_trace, dict) else "not_evaluated",
        "input_answer_sha256": sha256_text(planned),
        "output_answer_sha256": sha256_text(preserved),
    }

    source_answer = receipt.get("answer")
    _require(isinstance(source_answer, str), f"source answer absent: {replica_key}")
    _require(
        receipt.get("answer_sha256") == sha256_text(source_answer),
        f"source answer hash drift: {replica_key}",
    )
    row = {
        "replica_key": replica_key,
        "qid": receipt.get("qid"),
        "replica_id": receipt.get("replica_id"),
        "question_sha256": sha256_text(question),
        "context_sha256": canonical_sha256(context),
        "source_answer_sha256": sha256_text(source_answer),
        "frozen_draft_sha256": sha256_text(frozen_draft),
        "candidate_answer": guarded,
        "candidate_answer_sha256": sha256_text(guarded),
        "source_answer_byte_exact": guarded == source_answer,
        "stages": candidate_stages,
    }
    return row, scoring_view


@contextmanager
def deny_network() -> Iterator[list[str]]:
    """Fail closed if any replay code attempts DNS or a socket connection."""

    attempts: list[str] = []

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        attempts.append("blocked_network_attempt")
        raise CounterfactualPreflightError("network access attempted during offline replay")

    originals = {
        "connect": socket.socket.connect,
        "connect_ex": socket.socket.connect_ex,
        "create_connection": socket.create_connection,
        "getaddrinfo": socket.getaddrinfo,
    }
    socket.socket.connect = blocked  # type: ignore[method-assign]
    socket.socket.connect_ex = blocked  # type: ignore[method-assign]
    socket.create_connection = blocked  # type: ignore[assignment]
    socket.getaddrinfo = blocked  # type: ignore[assignment]
    try:
        yield attempts
    finally:
        socket.socket.connect = originals["connect"]  # type: ignore[method-assign]
        socket.socket.connect_ex = originals["connect_ex"]  # type: ignore[method-assign]
        socket.create_connection = originals["create_connection"]  # type: ignore[assignment]
        socket.getaddrinfo = originals["getaddrinfo"]  # type: ignore[assignment]


def _review_item_map(score: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = score.get("review_items")
    _require(isinstance(rows, list), "score review_items are absent")
    output: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "review item is not an object")
        key = str(row.get("review_key") or "")
        _require(bool(key), "review item lacks review_key")
        _require(key not in output, f"duplicate review item: {key}")
        output[key] = row
    return output


def validate_baseline_decisions(
    source_score: Mapping[str, Any],
    decisions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    source_items = _review_item_map(source_score)
    _require(
        set(decisions) == set(source_items),
        "baseline adjudication is not a bijection over source review_items",
    )
    for key, decision in decisions.items():
        binding = decision.get("binding_sha256")
        if binding is not None:
            _require(
                binding == source_items[key].get("binding_sha256"),
                f"baseline adjudication binding drift: {key}",
            )
    counts = {
        BASELINE_PASS: sum(row.get("decision") == BASELINE_PASS for row in decisions.values()),
        BASELINE_FAIL: sum(row.get("decision") == BASELINE_FAIL for row in decisions.values()),
    }
    _require(len(source_items) == EXPECTED_REVIEW_ITEMS, "source review population drift")
    _require(counts[BASELINE_PASS] == EXPECTED_BASELINE_PASSES, "baseline PASS count drift")
    _require(counts[BASELINE_FAIL] == EXPECTED_BASELINE_FAILS, "baseline FAIL count drift")
    return source_items


def _replica_score_map(score_rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for row in score_rows:
        key = str(row.get("replica_key") or "")
        _require(bool(key) and key not in output, f"invalid/duplicate replica score: {key}")
        output[key] = row
    return output


def compare_scores(
    *,
    source_score: Mapping[str, Any],
    baseline_decisions: Mapping[str, Mapping[str, Any]],
    candidate_scores: Sequence[Mapping[str, Any]],
    candidate_decisions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare frozen human decisions and automatic PASS checks to a candidate."""

    candidate_decisions = candidate_decisions or {}
    source_items = _review_item_map(source_score)
    candidate_by_replica = _replica_score_map(candidate_scores)
    candidate_review_items: dict[str, Mapping[str, Any]] = {}
    for score in candidate_scores:
        for key, item in _review_item_map(score).items():
            _require(key not in candidate_review_items, f"duplicate candidate review: {key}")
            candidate_review_items[key] = item

    changed_review_items = {
        key: item
        for key, item in candidate_review_items.items()
        if key not in source_items
        or item.get("binding_sha256") != source_items[key].get("binding_sha256")
    }
    _require(
        set(candidate_decisions) <= set(changed_review_items),
        "candidate adjudication targets an unchanged or absent review item",
    )
    for key, decision in candidate_decisions.items():
        _require(
            decision.get("binding_sha256") == changed_review_items[key].get("binding_sha256"),
            f"candidate adjudication binding drift: {key}",
        )

    comparisons: list[dict[str, Any]] = []
    for key in sorted(source_items):
        source_item = source_items[key]
        replica_key = str(source_item.get("replica_key") or "")
        check_id = str(source_item.get("check_id") or "")
        candidate_score = candidate_by_replica.get(replica_key)
        candidate_check = (
            leaf_check_map(candidate_score).get(check_id)
            if isinstance(candidate_score, Mapping)
            else None
        )
        candidate_status = candidate_check.get("status") if candidate_check else "MISSING"
        baseline = baseline_decisions[key]["decision"]
        candidate_item = candidate_review_items.get(key)
        same_binding = bool(
            candidate_item
            and candidate_item.get("binding_sha256") == source_item.get("binding_sha256")
        )
        fresh = candidate_decisions.get(key)
        fresh_decision = fresh.get("decision") if fresh else None

        resolved_pass = False
        if baseline == BASELINE_PASS:
            if candidate_status == "PASS":
                classification = "PRESERVED_MACHINE_PASS"
                resolved_pass = True
            elif candidate_status == "REVIEW" and same_binding:
                classification = "PRESERVED_EXACT_BOUND_ADJUDICATION"
                resolved_pass = True
            elif candidate_status == "REVIEW" and fresh_decision == BASELINE_PASS:
                classification = "PRESERVED_AFTER_FRESH_BLIND_PASS"
                resolved_pass = True
            elif candidate_status == "REVIEW" and fresh_decision == BASELINE_FAIL:
                classification = "REGRESSION_FRESH_BLIND_FAIL"
            elif candidate_status == "REVIEW":
                classification = "HOLD_FRESH_BLIND_REVIEW_REQUIRED"
            else:
                classification = f"REGRESSION_{candidate_status}"
        else:
            if candidate_status == "PASS":
                classification = "FIXED_MACHINE_PASS"
                resolved_pass = True
            elif candidate_status == "REVIEW" and same_binding:
                classification = "STILL_FAILED_EXACT_BOUND_ADJUDICATION"
            elif candidate_status == "REVIEW" and fresh_decision == BASELINE_PASS:
                classification = "FIXED_AFTER_FRESH_BLIND_PASS"
                resolved_pass = True
            elif candidate_status == "REVIEW" and fresh_decision == BASELINE_FAIL:
                classification = "STILL_FAILED_FRESH_BLIND_FAIL"
            elif candidate_status == "REVIEW":
                classification = "HOLD_CANDIDATE_FIX_NEEDS_BLIND_REVIEW"
            else:
                classification = f"STILL_FAILED_{candidate_status}"

        comparisons.append(
            {
                "review_key": key,
                "replica_key": replica_key,
                "check_id": check_id,
                "baseline_decision": baseline,
                "candidate_status": candidate_status,
                "source_binding_sha256": source_item.get("binding_sha256"),
                "candidate_binding_sha256": (
                    candidate_item.get("binding_sha256") if candidate_item else None
                ),
                "fresh_candidate_decision": fresh_decision,
                "classification": classification,
                "resolved_pass": resolved_pass,
            }
        )

    source_replicas = source_score.get("replicas")
    _require(isinstance(source_replicas, list), "source score replicas are absent")
    automatic_passes: list[dict[str, Any]] = []
    for source_replica in source_replicas:
        _require(isinstance(source_replica, dict), "source replica score is not an object")
        replica_key = str(source_replica.get("replica_key") or "")
        candidate_score = candidate_by_replica.get(replica_key)
        candidate_leaves = leaf_check_map(candidate_score) if candidate_score else {}
        for check_id, source_check in leaf_check_map(source_replica).items():
            if source_check.get("status") != "PASS":
                continue
            candidate_status = (candidate_leaves.get(check_id) or {}).get("status", "MISSING")
            automatic_passes.append(
                {
                    "review_key": f"{replica_key}:{check_id}",
                    "candidate_status": candidate_status,
                    "preserved": candidate_status == "PASS",
                }
            )

    pending = sorted(
        key for key in changed_review_items if key not in candidate_decisions
    )
    candidate_failures = []
    candidate_instrument_errors = []
    for replica_key, score in candidate_by_replica.items():
        for check_id, check in leaf_check_map(score).items():
            if check.get("status") == "FAIL":
                candidate_failures.append(f"{replica_key}:{check_id}")
            elif check.get("status") == "INSTRUMENT_ERROR":
                candidate_instrument_errors.append(f"{replica_key}:{check_id}")

    pass_rows = [row for row in comparisons if row["baseline_decision"] == BASELINE_PASS]
    fail_rows = [row for row in comparisons if row["baseline_decision"] == BASELINE_FAIL]
    summary = {
        "baseline_adjudicated_pass": len(pass_rows),
        "baseline_adjudicated_pass_preserved": sum(row["resolved_pass"] for row in pass_rows),
        "baseline_adjudicated_pass_regressions_or_holds": sum(
            not row["resolved_pass"] for row in pass_rows
        ),
        "baseline_adjudicated_fail": len(fail_rows),
        "baseline_adjudicated_fail_fixed": sum(row["resolved_pass"] for row in fail_rows),
        "baseline_adjudicated_fail_remaining_or_holds": sum(
            not row["resolved_pass"] for row in fail_rows
        ),
        "automatic_pass_checks": len(automatic_passes),
        "automatic_pass_checks_preserved": sum(row["preserved"] for row in automatic_passes),
        "automatic_pass_regressions": sum(not row["preserved"] for row in automatic_passes),
        "pending_fresh_blind_reviews": len(pending),
        "candidate_fail_checks": len(candidate_failures),
        "candidate_instrument_errors": len(candidate_instrument_errors),
    }
    gate_pass = (
        summary["baseline_adjudicated_pass_preserved"] == EXPECTED_BASELINE_PASSES
        and summary["baseline_adjudicated_fail_fixed"] == EXPECTED_BASELINE_FAILS
        and summary["automatic_pass_regressions"] == 0
        and summary["pending_fresh_blind_reviews"] == 0
        and summary["candidate_fail_checks"] == 0
        and summary["candidate_instrument_errors"] == 0
    )
    return {
        "gate": FROZEN_CONTEXT_PASS if gate_pass else HOLD,
        "summary": summary,
        "review_comparisons": comparisons,
        "automatic_pass_comparisons": automatic_passes,
        "pending_review_keys": pending,
        "candidate_fail_check_keys": sorted(candidate_failures),
        "candidate_instrument_error_keys": sorted(candidate_instrument_errors),
        "changed_candidate_review_items": changed_review_items,
    }


def _git_identity(repo: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    status = git("status", "--porcelain")
    return {
        "commit_sha": git("rev-parse", "HEAD"),
        "tree_sha": git("rev-parse", "HEAD^{tree}"),
        "dirty": bool(status),
        "dirty_inventory_sha256": sha256_text(status),
    }


def apply_candidate_identity_gate(
    comparison_gate: str,
    candidate_identity: Mapping[str, Any],
) -> tuple[str, list[str]]:
    """A development PASS must describe committed, reproducible bytes."""

    hold_reasons: list[str] = []
    if comparison_gate != FROZEN_CONTEXT_PASS:
        hold_reasons.append("QUALITY_GATE_NOT_CLEARED")
    if candidate_identity.get("dirty") is not False:
        hold_reasons.append("CANDIDATE_WORKTREE_DIRTY")
    return (HOLD if hold_reasons else FROZEN_CONTEXT_PASS), hold_reasons


def _implementation_hashes() -> dict[str, str]:
    paths = (
        ROOT / "src/rag/answer_planner.py",
        ROOT / "src/rag/must_preserve.py",
        ROOT / "src/rag/generator.py",
        ROOT / "scripts/s277_c1_p1_scorer.py",
        Path(__file__).resolve(),
    )
    return {str(path.relative_to(ROOT)): sha256_lf_file(path) for path in paths}


def _blind_review_packet(
    pending_keys: Sequence[str],
    changed_items: Mapping[str, Mapping[str, Any]],
    materialized: Mapping[str, Mapping[str, Any]],
    source_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    rows = []
    for key in pending_keys:
        item = changed_items[key]
        replica_key = str(item.get("replica_key") or "")
        rows.append(
            {
                "review_item": item,
                "question": source_receipts[replica_key]["input"]["question"],
                "candidate_answer": materialized[replica_key]["candidate_answer"],
                "served_context": source_receipts[replica_key]["served_context"],
            }
        )
    return {
        "schema_version": "s277_c1_p1_counterfactual_blind_review_packet_v1",
        "authority": AUTHORITY,
        "blind_to_baseline_decisions": True,
        "rows": rows,
    }


def run_preflight(
    *,
    source_run: Path,
    release_config_path: Path,
    fact_contract_path: Path,
    baseline_adjudication_paths: Sequence[Path],
    candidate_adjudication_paths: Sequence[Path] = (),
) -> dict[str, Any]:
    source_run = source_run.resolve()
    release_config_path = release_config_path.resolve()
    fact_contract_path = fact_contract_path.resolve()
    source_score = read_json_object(source_run / "score.json")
    release_config = read_json_object(release_config_path)
    baseline_decisions = load_decisions(baseline_adjudication_paths)
    candidate_decisions = load_decisions(
        candidate_adjudication_paths,
        require_binding=True,
    )

    # This module is safe to import before product configuration; it owns the
    # release environment context and checks that config-bearing modules are late.
    from scripts.s277_c1_p1 import sealed_target_runtime_environment

    with sealed_target_runtime_environment(release_config) as target_environment:
        with deny_network() as network_attempts:
            from scripts import s277_c1_p1_scorer as scorer
            from src.rag.answer_planner import (
                apply_answer_conflict_guard,
                apply_answer_planner,
            )
            from src.rag.must_preserve import apply_must_preserve_contract, detect_atoms

            _require(
                source_score.get("scorer_sha256") == scorer.scorer_sha256(),
                "candidate scorer differs from the source-run scorer",
            )
            contract = scorer.load_fact_contract(fact_contract_path)
            _require(
                source_score.get("contract_sha256") == canonical_sha256(contract),
                "source score/fact contract binding drift",
            )
            source_items = validate_baseline_decisions(source_score, baseline_decisions)

            receipt_paths = sorted((source_run / "replicas").glob("*.json"))
            source_receipts: dict[str, Mapping[str, Any]] = {}
            for path in receipt_paths:
                receipt = read_json_object(path)
                key = str(receipt.get("replica_key") or "")
                _require(bool(key) and key not in source_receipts, f"duplicate receipt: {key}")
                source_receipts[key] = receipt
            _require(
                set(source_receipts) == set(scorer.P1_REPLICA_KEYS),
                "source run is not the exact 27-replica P1 population",
            )

            stored_score_rows = _replica_score_map(source_score.get("replicas") or [])
            materialized_rows: list[dict[str, Any]] = []
            candidate_scores: list[dict[str, Any]] = []
            for replica_key in scorer.P1_REPLICA_KEYS:
                source_receipt = source_receipts[replica_key]
                source_rescore = scorer.score_replica(source_receipt, contract)
                _require(
                    canonical_sha256(source_rescore)
                    == canonical_sha256(stored_score_rows.get(replica_key)),
                    f"source receipt no longer reproduces its stored score: {replica_key}",
                )
                materialized, scoring_view = replay_receipt(
                    source_receipt,
                    apply_answer_planner=apply_answer_planner,
                    apply_must_preserve_contract=apply_must_preserve_contract,
                    detect_atoms=detect_atoms,
                    apply_answer_conflict_guard=apply_answer_conflict_guard,
                )
                candidate_score = scorer.score_replica(scoring_view, contract)
                materialized["score"] = candidate_score
                materialized_rows.append(materialized)
                candidate_scores.append(candidate_score)

            comparison = compare_scores(
                source_score=source_score,
                baseline_decisions=baseline_decisions,
                candidate_scores=candidate_scores,
                candidate_decisions=candidate_decisions,
            )
            _require(not network_attempts, "network attempt was blocked during replay")

    materialized_by_key = {row["replica_key"]: row for row in materialized_rows}
    blind_packet = _blind_review_packet(
        comparison["pending_review_keys"],
        comparison["changed_candidate_review_items"],
        materialized_by_key,
        source_receipts,
    )
    summary = {
        **comparison["summary"],
        "replicas_materialized": len(materialized_rows),
        "source_answer_byte_exact_replays": sum(
            row["source_answer_byte_exact"] for row in materialized_rows
        ),
        "model_calls": 0,
        "database_calls": 0,
        "network_calls": 0,
    }
    candidate_identity = _git_identity(ROOT)
    gate, hold_reasons = apply_candidate_identity_gate(
        comparison["gate"], candidate_identity
    )
    summary["candidate_worktree_dirty"] = bool(candidate_identity["dirty"])
    return {
        "schema_version": SCHEMA_VERSION,
        "authority": AUTHORITY,
        "gate": gate,
        "hold_reasons": hold_reasons,
        "interpretation": (
            (
                "Candidate cleared only the frozen-context post-generation filter; "
                "a candidate-context/source-receipt gate is still required before spend."
            )
            if gate == FROZEN_CONTEXT_PASS
            else "Candidate has not cleared the development-only filter."
        ),
        "source_context_mode": SOURCE_CONTEXT_MODE,
        "next_required_gate": {
            "name": NEXT_REQUIRED_GATE,
            "status": "NOT_IMPLEMENTED",
            "requirement": (
                "Materialize hash-bound candidate served contexts from the versioned "
                "retrieval/coverage path. Reuse sealed provider receipts only when the "
                "request hash is identical; otherwise stop for a preregistered, bounded "
                "context-only provider experiment before combining source receipts with "
                "this post-generation regression oracle."
            ),
        },
        "source": {
            "run": str(source_run),
            "score_sha256_lf": sha256_lf_file(source_run / "score.json"),
            "release_config": str(release_config_path),
            "release_config_sha256_lf": sha256_lf_file(release_config_path),
            "fact_contract": str(fact_contract_path),
            "fact_contract_sha256_lf": sha256_lf_file(fact_contract_path),
            "review_item_count": len(source_items),
        },
        "candidate": {
            **candidate_identity,
            "target_environment_sha256": canonical_sha256(target_environment),
            "implementation_sha256_lf": _implementation_hashes(),
        },
        "zero_call_contract": {
            "model_calls": 0,
            "database_calls": 0,
            "network_calls": 0,
            "network_guard": "DNS_AND_SOCKET_CONNECT_FAIL_CLOSED",
            "must_preserve_detector": "DETERMINISTIC_DETECT_ATOMS_INJECTED",
        },
        "summary": summary,
        "review_comparisons": comparison["review_comparisons"],
        "automatic_pass_comparisons": comparison["automatic_pass_comparisons"],
        "candidate_fail_check_keys": comparison["candidate_fail_check_keys"],
        "candidate_instrument_error_keys": comparison["candidate_instrument_error_keys"],
        "blind_review_packet": blind_packet,
        "rows": materialized_rows,
        "limitations": [
            (
                "Exact only for deterministic post-generation changes over the "
                "frozen draft and served context."
            ),
            (
                "Does not test retrieval, reranking, coverage, prompt/model generation, "
                "or hybrid must-preserve detection."
            ),
            (
                "Does not recreate provider, billing, WAL, visual-asset, fence, "
                "database-manifest, or release identity evidence."
            ),
            "A temperature-zero provider rerun is not guaranteed to be byte-identical.",
            (
                "The 27 known cells provide no organic, multi-turn, multi-hop, or "
                "generalization claim."
            ),
            "Missing source evidence cannot be repaired honestly by post-generation logic.",
            (
                "This frozen-context instrument cannot by itself authorize spend; source "
                "gaps require a separate candidate-context/source-receipt preflight."
            ),
            "This artifact never authorizes a release; a new authoritative P1 remains mandatory.",
        ],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--release-config", type=Path, required=True)
    parser.add_argument("--fact-contract", type=Path, required=True)
    parser.add_argument(
        "--baseline-adjudication",
        type=Path,
        action="append",
        required=True,
        help="Repeat for split A/B/C files or pass one canonical adjudication.",
    )
    parser.add_argument(
        "--candidate-adjudication",
        type=Path,
        action="append",
        default=[],
        help="Optional fresh, hash-bound blind decisions for changed candidate REVIEW rows.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    assert_output_outside_source_run(args.output, args.source_run)
    payload = run_preflight(
        source_run=args.source_run,
        release_config_path=args.release_config,
        fact_contract_path=args.fact_contract,
        baseline_adjudication_paths=args.baseline_adjudication,
        candidate_adjudication_paths=args.candidate_adjudication,
    )
    write_json(args.output, payload)
    print(json.dumps({"gate": payload["gate"], **payload["summary"]}, indent=2))
    print(f"output: {args.output.resolve()}")
    return 0 if payload["gate"] == FROZEN_CONTEXT_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
