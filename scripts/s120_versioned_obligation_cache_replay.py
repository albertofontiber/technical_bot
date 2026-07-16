#!/usr/bin/env python3
"""Replay S120 answer obligations over the frozen S113 generator contexts.

No environment file is loaded and no external client is instantiated. The
output is a diagnostic plan/cache projection only; it never generates or
judges an answer.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
CONTEXTS = ROOT / "evals/s113_full_contexts_freeze_v1.json"
LEGACY_PREFLIGHT = ROOT / "evals/s113_full_regression_preflight_v1.json"
PREREG = ROOT / "evals/s120_versioned_obligation_cache_prereg_v1.yaml"
OUT = ROOT / "evals/s120_versioned_obligation_cache_replay_v1.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _counter_delta(new: list[str], old: list[str]) -> tuple[list[str], list[str]]:
    added_counter = Counter(new) - Counter(old)
    removed_counter = Counter(old) - Counter(new)
    added = []
    for kind in new:
        if added_counter[kind] > 0:
            added.append(kind)
            added_counter[kind] -= 1
    removed = []
    for kind in old:
        if removed_counter[kind] > 0:
            removed.append(kind)
            removed_counter[kind] -= 1
    return added, removed


def build_replay() -> dict:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.rag.answer_obligation_contract import (
        ANSWER_OBLIGATION_CONTRACT_VERSION,
        canonical_obligation_packet,
        stable_sha256,
    )
    from src.rag.answer_planner import (
        ANSWER_PLANNER_CONTRACT_S119,
        ANSWER_PLANNER_CONTRACT_S120,
        build_answer_plan,
    )

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    contexts_artifact = json.loads(CONTEXTS.read_text(encoding="utf-8"))
    legacy_artifact = json.loads(LEGACY_PREFLIGHT.read_text(encoding="utf-8"))
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    questions = {row["qid"]: row["question"] for row in baseline["per_gold"]}
    contexts = {row["qid"]: row["context"] for row in contexts_artifact["rows"]}
    legacy = {row["qid"]: row for row in legacy_artifact["rows"]}
    if set(questions) != set(contexts) or set(questions) != set(legacy):
        raise RuntimeError("frozen cohort inputs do not have identical qid sets")

    rows = []
    for qid in sorted(questions):
        question = questions[qid]
        old = legacy[qid]
        legacy_plan = build_answer_plan(
            question,
            contexts[qid],
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S119,
        )
        plan = build_answer_plan(
            question,
            contexts[qid],
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S120,
        )
        legacy_kinds = [item.kind for item in legacy_plan]
        kinds = [item.kind for item in plan]
        added, removed = _counter_delta(kinds, legacy_kinds)
        legacy_packet = canonical_obligation_packet(
            legacy_plan,
            contract_version=ANSWER_PLANNER_CONTRACT_S119,
        )
        packet = canonical_obligation_packet(
            plan,
            contract_version=ANSWER_PLANNER_CONTRACT_S120,
        )
        exact_obligations_equal = (
            legacy_packet["obligations"] == packet["obligations"]
        )
        if not legacy_kinds and not kinds:
            legacy_reuse_decision = "legacy_empty_plan_still_empty"
        elif not legacy_kinds and kinds:
            legacy_reuse_decision = "invalidate_legacy_no_plan_answer"
        else:
            legacy_reuse_decision = "require_exact_versioned_packet_identity"
        rows.append(
            {
                "qid": qid,
                "s113_historical_obligation_kinds": list(old["obligation_kinds"]),
                "legacy_obligation_kinds": legacy_kinds,
                "candidate_obligation_kinds": kinds,
                "added_obligation_kinds": added,
                "removed_obligation_kinds": removed,
                "legacy_obligation_count": len(legacy_plan),
                "candidate_obligation_count": len(plan),
                "legacy_obligation_packet": legacy_packet,
                "legacy_obligation_packet_sha256": stable_sha256(legacy_packet),
                "canonical_obligation_packet": packet,
                "canonical_obligation_packet_sha256": stable_sha256(packet),
                "exact_obligation_payload_equal": exact_obligations_equal,
                "legacy_reuse_decision": legacy_reuse_decision,
            }
        )

    expected = prereg["acceptance"]["diagnostic_obligation_families"]
    diagnostic_checks = {
        qid: set(required).issubset(
            next(row for row in rows if row["qid"] == qid)["candidate_obligation_kinds"]
        )
        for qid, required in expected.items()
    }
    claim_mapping = prereg["acceptance"]["diagnostic_claim_mapping"]
    claim_checks = {
        claim_id: set(mapping["obligation_kinds"]).issubset(
            next(row for row in rows if row["qid"] == mapping["qid"])[
                "candidate_obligation_kinds"
            ]
        )
        for claim_id, mapping in claim_mapping.items()
    }
    removed = [
        {"qid": row["qid"], "kinds": row["removed_obligation_kinds"]}
        for row in rows
        if row["removed_obligation_kinds"]
    ]
    invalidated_no_plan = [
        row["qid"]
        for row in rows
        if row["legacy_reuse_decision"] == "invalidate_legacy_no_plan_answer"
    ]
    historical_legacy_kind_mismatches = [
        {
            "qid": row["qid"],
            "s113": row["s113_historical_obligation_kinds"],
            "versioned_s119": row["legacy_obligation_kinds"],
        }
        for row in rows
        if row["s113_historical_obligation_kinds"] != row["legacy_obligation_kinds"]
    ]
    expected_invalidations = list(
        prereg["acceptance"]["expected_legacy_no_plan_invalidations"]
    )
    changed_obligation_packet_qids = [
        row["qid"] for row in rows if not row["exact_obligation_payload_equal"]
    ]
    unexpected_obligation_packet_changes = sorted(
        set(changed_obligation_packet_qids) - set(expected_invalidations)
    )
    missing_expected_obligation_packet_changes = sorted(
        set(expected_invalidations) - set(changed_obligation_packet_qids)
    )
    all_new = [
        {"qid": row["qid"], "kinds": row["added_obligation_kinds"]}
        for row in rows
        if row["added_obligation_kinds"]
    ]
    local_go = (
        all(diagnostic_checks.values())
        and all(claim_checks.values())
        and not unexpected_obligation_packet_changes
        and not missing_expected_obligation_packet_changes
        and invalidated_no_plan == expected_invalidations
        and not historical_legacy_kind_mismatches
    )
    return {
        "instrument": "s120_versioned_obligation_cache_replay_v1",
        "authority": "local_deterministic_design_only",
        "input_receipts": [
            {"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)}
            for path in (BASELINE, CONTEXTS, LEGACY_PREFLIGHT, PREREG)
        ],
        "implementation_receipts": [
            {
                "path": path,
                "sha256": file_sha256(ROOT / path),
            }
            for path in (
                "src/rag/answer_planner.py",
                "src/rag/answer_obligation_contract.py",
                "scripts/s120_versioned_obligation_cache_replay.py",
            )
        ],
        "contract": {
            "obligation_contract_version": ANSWER_OBLIGATION_CONTRACT_VERSION,
            "legacy_planner_contract_version": ANSWER_PLANNER_CONTRACT_S119,
            "candidate_planner_contract_version": ANSWER_PLANNER_CONTRACT_S120,
            "cache_identity_requires_exact_provider_request_envelope": True,
            "causal_answer_improvement_claimed": False,
            "facts_moved_to_ok": 0,
            "fresh_answer_calls_authorized": 0,
        },
        "gate": {
            "status": (
                "LOCAL_OBLIGATION_CACHE_GO_PROBE_NOT_AUTHORIZED"
                if local_go
                else "LOCAL_OBLIGATION_CACHE_NO_GO"
            ),
            "questions": len(rows),
            "diagnostic_checks": diagnostic_checks,
            "diagnostic_claim_checks": claim_checks,
            "legacy_obligation_kinds_removed": removed,
            "legacy_no_plan_answers_invalidated": invalidated_no_plan,
            "historical_legacy_kind_mismatches": historical_legacy_kind_mismatches,
            "expected_legacy_no_plan_invalidations": expected_invalidations,
            "changed_obligation_packet_qids": changed_obligation_packet_qids,
            "unexpected_obligation_packet_changes": unexpected_obligation_packet_changes,
            "missing_expected_obligation_packet_changes": missing_expected_obligation_packet_changes,
            "all_new_obligations": all_new,
            "distinct_probe_candidates": invalidated_no_plan,
            "model_calls": 0,
            "network_calls": 0,
            "database_calls": 0,
        },
        "rows": rows,
        "limitations": [
            "New obligations are a local synthesis-control improvement, not evidence that any answer is now correct.",
            "Exact ordered obligation payload comparison, not kind equality, is the preservation authority for the frozen cohort.",
            "A real cache key must receive the exact provider request envelope; S120 does not fabricate a substitute envelope.",
        ],
    }


def main() -> int:
    payload = build_replay()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["gate"], ensure_ascii=False, indent=2))
    return 0 if payload["gate"]["status"].startswith("LOCAL_OBLIGATION_CACHE_GO") else 1


if __name__ == "__main__":
    raise SystemExit(main())
