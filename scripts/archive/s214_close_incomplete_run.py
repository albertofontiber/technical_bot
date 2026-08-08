#!/usr/bin/env python3
"""Seal the fail-closed S214 Fable completion-limit stop without retry."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.multisource_visual_gold import validate_candidate  # noqa: E402
from src.rag.query_evidence_compiler import portable_file_sha  # noqa: E402
from src.rag.visual_gold import stable_sha, write_json  # noqa: E402


PACKET = ROOT / "evals/s214_kidde_multisource_gold_packet_v1.json"
PREREG = ROOT / "evals/s214_kidde_multisource_gold_prereg_v1.yaml"
DESIGN_GATE = ROOT / "evals/s214_frontier_design_gate_reviews_v1.json"
LEDGER = ROOT / "evals/s214_frontier_call_ledger_v1.json"
SOL_GENERATIONS = ROOT / "evals/s214_kidde_sol_generations_v1.json"
RESULT = ROOT / "evals/s214_kidde_multisource_gold_result_v1.json"
OUT = ROOT / "evals/s214_kidde_multisource_incomplete_closure_v1.json"

DOWNSTREAM = (
    ROOT / "evals/s214_kidde_fable_generations_v1.json",
    ROOT / "evals/s214_kidde_sol_reviews_of_fable_v1.json",
    ROOT / "evals/s214_kidde_fable_reviews_of_sol_v1.json",
    ROOT / "evals/s214_kidde_pixel_gold_v1.json",
    ROOT / "evals/s214_kidde_sol_support_mappings_v1.json",
    ROOT / "evals/s214_kidde_fable_support_reviews_v1.json",
    ROOT / "evals/s214_kidde_supported_gold_v1.json",
)

ITEM_IDS = (
    "kidde_nc_capacity_tradeoffs",
    "kidde_2xa_interface_tradeoffs",
    "kidde_mcp_surface_kit_selection",
    "kidde_modulaser_role_selection",
)
SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
FAILURE_REASON = (
    "RuntimeError: Fable incomplete or model mismatch: "
    "max_tokens / claude-fable-5"
)


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise RuntimeError(f"sealed artifact drift: {path.name}")
    return value


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    body = dict(value)
    body.pop("result_sha256", None)
    return {**body, "result_sha256": stable_sha(body)}


def _verify_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if OUT.exists():
        raise RuntimeError("S214 incomplete closure already exists")
    escaped = [path.relative_to(ROOT).as_posix() for path in DOWNSTREAM if path.exists()]
    if escaped:
        raise RuntimeError(f"S214 downstream artifacts must not exist: {escaped}")

    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    items = packet.get("items") or []
    if tuple(item.get("canary_id") for item in items) != ITEM_IDS:
        raise RuntimeError("S214 frozen item order drift")

    ledger = _sealed(LEDGER)
    if ledger.get("status") != "IN_PROGRESS":
        raise RuntimeError("S214 call ledger is not the open interrupted run")
    calls = ledger.get("calls") or []
    expected_labels = [f"generate:{item_id}" for item_id in ITEM_IDS]
    if len(calls) != 5:
        raise RuntimeError("S214 interrupted call geometry drift")
    for index, (call, label) in enumerate(zip(calls[:4], expected_labels), 1):
        if (
            call.get("provider") != "sol"
            or call.get("call_label") != label
            or call.get("model") != SOL_MODEL
            or call.get("reasoning_effort") != "xhigh"
            or call.get("status") != "completed"
            or not call.get("raw_output")
        ):
            raise RuntimeError(f"S214 Sol call {index} drift")
    failed = calls[4]
    if (
        failed.get("provider") != "fable"
        or failed.get("call_label") != expected_labels[0]
        or failed.get("model") != FABLE_MODEL
        or failed.get("status") != "max_tokens"
        or not failed.get("raw_output")
        or failed.get("usage", {}).get("input_tokens") != 62_668
        or failed.get("usage", {}).get("output_tokens") != 8_000
        or len(failed["raw_output"]) != 8_723
    ):
        raise RuntimeError("S214 Fable completion-limit receipt drift")
    if ledger.get("conservative_cost_usd") != 8.73762:
        raise RuntimeError("S214 conservative cost drift")

    sol = _sealed(SOL_GENERATIONS)
    sol_rows = sol.get("items") or []
    if (
        sol.get("status") != "COMPLETE"
        or sol.get("provider") != "sol"
        or tuple(row.get("canary_id") for row in sol_rows) != ITEM_IDS
        or any(row.get("validation_status") != "VALID" for row in sol_rows)
    ):
        raise RuntimeError("S214 Sol generation checkpoint drift")
    by_id = {item["canary_id"]: item for item in items}
    for row in sol_rows:
        validate_candidate(row["candidate"], by_id[row["canary_id"]])

    result = _sealed(RESULT)
    if (
        result.get("status") != "HOLD_S214_EXTERNAL_OR_INCOMPLETE"
        or result.get("reason") != FAILURE_REASON
        or result.get("frontier_calls") != 5
        or result.get("official_fact_credit") != 0
        or result.get("target_calls") != 0
    ):
        raise RuntimeError("S214 HOLD result drift")
    return ledger, sol, result


def main() -> int:
    ledger, _, _ = _verify_inputs()
    ledger.pop("result_sha256")
    ledger["status"] = "INCOMPLETE_FINAL"
    ledger["closure"] = {
        "reason": "FABLE_MAX_TOKENS_FIRST_AUTHOR_ITEM",
        "provider_retries": 0,
        "same_item_retry": False,
        "resume": False,
        "official_fact_credit": 0,
    }
    write_json(LEDGER, _seal(ledger))

    failed = ledger["calls"][4]
    body = {
        "schema": "s214_kidde_multisource_incomplete_closure_v1",
        "status": "NO_GO_INCOMPLETE_FAIL_CLOSED",
        "failure": {
            "stage": "FABLE_BLIND_AUTHORSHIP",
            "classification": "PROVIDER_COMPLETION_LIMIT",
            "error": FAILURE_REASON,
            "attempted_item": ITEM_IDS[0],
            "provider": "fable",
            "model": FABLE_MODEL,
            "provider_status": "max_tokens",
            "input_tokens": failed["usage"]["input_tokens"],
            "output_tokens": failed["usage"]["output_tokens"],
            "raw_output_chars": len(failed["raw_output"]),
        },
        "execution": {
            "completed_transport_calls": 5,
            "planned_frontier_calls_max": 24,
            "completed_sol_authorship_calls": 4,
            "valid_sol_candidates": 4,
            "completed_fable_authorship_calls": 0,
            "incomplete_fable_authorship_calls": 1,
            "provider_retries": 0,
            "same_item_retry": False,
            "resume": False,
            "reciprocal_review_calls": 0,
            "support_calls": 0,
            "downstream_artifacts_written": False,
        },
        "unattempted_items": list(ITEM_IDS[1:]),
        "inputs": {
            "packet_sha256": portable_file_sha(PACKET),
            "prereg_sha256": portable_file_sha(PREREG),
            "design_gate_sha256": portable_file_sha(DESIGN_GATE),
            "closed_call_ledger_sha256": portable_file_sha(LEDGER),
            "sol_generations_sha256": portable_file_sha(SOL_GENERATIONS),
            "hold_result_sha256": portable_file_sha(RESULT),
        },
        "cost": {
            "actual_sunk_usd": 8.73762,
            "budget_ceiling_usd": 100.0,
            "within_budget": True,
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
            "retry_or_repair_failed_item": False,
            "runtime_integration": False,
            "production_default": "off",
            "next": "DESIGN_S215_ONLY_ON_THREE_PRE_FROZEN_UNATTEMPTED_ITEMS",
            "reason": (
                "Preserve the four valid Sol candidates and exclude the attempted NC item "
                "without semantic selection; evaluate only the three never attempted by Fable."
            ),
        },
        "invariants": {
            "source_independent_validation": False,
            "chunks_v2": "ACTIVE_READ_ONLY",
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    write_json(OUT, _seal(body))
    print(
        json.dumps(
            {
                "status": body["status"],
                "calls": 5,
                "cost_usd": body["cost"]["actual_sunk_usd"],
                "unattempted_items": len(body["unattempted_items"]),
                "facts_moved_to_ok": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
