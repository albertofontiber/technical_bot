#!/usr/bin/env python3
"""Seal the fail-closed S213 character-bound stop without scoring or retry."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.query_evidence_compiler import portable_file_sha, stable_sha  # noqa: E402
from src.rag.sharded_unit_selector import (  # noqa: E402
    MAX_COMPILED_CHARS,
    build_sharded_candidates,
    compile_sharded_appendix,
    validate_selection,
    validate_verification,
)


PREFLIGHT = ROOT / "evals/s213_sharded_unit_selector_preflight_v1.json"
PERMIT = ROOT / "evals/s213_sharded_unit_selector_execution_permit_v1.yaml"
PARTIAL = ROOT / "evals/s213_sharded_unit_selector_calls_v1.partial.jsonl"
RECEIPTS = ROOT / "evals/s213_sharded_unit_selector_receipts_v1.json"
SCORE = ROOT / "evals/s213_sharded_unit_selector_score_v1.json"
OUT = ROOT / "evals/s213_sharded_unit_selector_incomplete_closure_v1.json"


def _appendix_chars(candidates: list[Any], selected_ids: list[str]) -> int:
    by_id = {row.evidence_id: row for row in candidates}
    blocks = []
    for evidence_id in selected_ids:
        row = by_id[evidence_id]
        marker = f"[F{row.fragment_number}]"
        blocks.append(f"- {marker} {row.content.strip()} {marker}")
    appendix = (
        "### Evidencia adicional verificada\n\n"
        "Los siguientes puntos proceden literalmente de los fragmentos servidos y "
        "completan la respuesta anterior:\n\n"
        + "\n\n".join(blocks)
    )
    return len(appendix)


def main() -> int:
    if RECEIPTS.exists() or SCORE.exists():
        raise RuntimeError("S213 final receipts/score must not exist after fail-closed stop")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    calls = [
        json.loads(line)
        for line in PARTIAL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(calls) != 26 or [row["call_index"] for row in calls] != list(range(1, 27)):
        raise RuntimeError("S213 partial journal geometry drift")
    if any(row["model"] != "gpt-5.6-terra" or row["status"] != "completed" for row in calls):
        raise RuntimeError("S213 journal contains an incomplete or wrong-model call")

    row = preflight["rows"][0]
    if row["qid"] != "cat018" or row["role"] != "target":
        raise RuntimeError("S213 first frozen row drift")
    shards = build_sharded_candidates(row["question"], row["context"])
    if len(shards) != 13:
        raise RuntimeError("S213 cat018 shard geometry drift")
    by_call = {call["call_id"]: call for call in calls}
    selected_all: list[str] = []
    shard_rows: list[dict[str, Any]] = []
    for fragment_number, shard in enumerate(shards, 1):
        select_id = f"cat018:r1:select:f{fragment_number}"
        verify_id = f"cat018:r1:verify:f{fragment_number}"
        primary = validate_selection(json.loads(by_call[select_id]["raw_output"]), shard)
        status, facets, additions = validate_verification(
            json.loads(by_call[verify_id]["raw_output"]), shard, primary
        )
        selected = primary + additions
        selected_all.extend(selected)
        shard_rows.append(
            {
                "fragment_number": fragment_number,
                "primary_ids": len(primary),
                "verifier_status": status,
                "missing_facets": list(facets),
                "additional_ids": len(additions),
                "selected_ids": len(selected),
            }
        )
    if len(selected_all) != len(set(selected_all)):
        raise RuntimeError("S213 selected IDs unexpectedly duplicate across shards")
    candidates = [candidate for shard in shards for candidate in shard]
    unbounded_chars = _appendix_chars(candidates, selected_all)
    if unbounded_chars <= MAX_COMPILED_CHARS:
        raise RuntimeError("S213 closure did not reproduce the character overflow")
    try:
        compile_sharded_appendix(candidates, selected_all)
    except ValueError as exc:
        error = str(exc)
    else:
        raise RuntimeError("S213 compiler unexpectedly accepted the failed selection")
    if error != "compiled evidence exceeds the character bound":
        raise RuntimeError("S213 reproduced a different compiler failure")

    cost = round(sum(float(call["cost_usd"]) for call in calls), 8)
    body = {
        "schema": "s213_sharded_unit_selector_incomplete_closure_v1",
        "status": "NO_GO_INCOMPLETE_FAIL_CLOSED",
        "failure": {
            "stage": "DETERMINISTIC_EXACT_COMPILER",
            "classification": "DOWNSTREAM_SHARD_UNION_LENGTH_BOUND",
            "error": error,
            "qid": "cat018",
            "replicate": 1,
            "completed_shards": 13,
            "selected_unique_ids": len(selected_all),
            "would_be_appendix_chars": unbounded_chars,
            "compiled_char_bound": MAX_COMPILED_CHARS,
            "overflow_chars": unbounded_chars - MAX_COMPILED_CHARS,
            "shards": shard_rows,
        },
        "execution": {
            "completed_calls": len(calls),
            "planned_calls": preflight["call_geometry"]["total_paid_calls"],
            "selector_calls": sum(call["role"] == "shard_selector" for call in calls),
            "verifier_calls": sum(call["role"] == "shard_verifier" for call in calls),
            "provider_retries": 0,
            "resume": False,
            "final_receipts_written": False,
            "score_written": False,
            "candidate_answer_written": False,
            "gold_or_scorer_opened_before_stop": False,
        },
        "inputs": {
            "preflight_sha256": portable_file_sha(PREFLIGHT),
            "permit_sha256": portable_file_sha(PERMIT),
            "partial_journal_sha256": portable_file_sha(PARTIAL),
        },
        "cost": {
            "actual_sunk_usd": cost,
            "budget_ceiling_usd": 75,
            "within_budget": cost < 75,
        },
        "credit": {
            "facts_ok_before": 143,
            "facts_ok_after": 143,
            "denominator": 157,
            "facts_moved_to_ok": 0,
            "canonical_ok_rate_percent": 91.08,
        },
        "decision": {
            "same_run_retry": False,
            "resume": False,
            "same_cohort_prompt_threshold_or_cap_tuning": False,
            "runtime_integration": False,
            "production_default": "off",
            "next": "DESIGN_ON_FRESH_INDEPENDENT_KIDDE_QUESTION_GOLD_COHORT",
            "reason": (
                "Per-chunk selection removed global competition but accumulated source dumping; "
                "learn the next generic relevance/compression contract on fresh population."
            ),
        },
        "invariants": {
            "upstream_deterministic_residual_span_coverage": "12_OF_12_PREFLIGHT_ONLY",
            "chunks_v2": "ACTIVE_READ_ONLY",
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    payload = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "calls": len(calls),
                "cost": cost,
                "selected_ids": len(selected_all),
                "appendix_chars": unbounded_chars,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
