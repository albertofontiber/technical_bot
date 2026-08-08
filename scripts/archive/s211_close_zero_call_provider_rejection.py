#!/usr/bin/env python3
"""Seal the pre-model Anthropic schema rejection that closed S211."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.query_evidence_compiler import (  # noqa: E402
    portable_file_sha,
    stable_sha,
)


PREFLIGHT = ROOT / "evals/s211_query_evidence_compiler_preflight_v1.json"
PERMIT = ROOT / "evals/s211_query_evidence_compiler_execution_permit_v1.yaml"
PARTIAL = ROOT / "evals/s211_query_evidence_compiler_calls_v1.partial.jsonl"
RECEIPTS = ROOT / "evals/s211_query_evidence_compiler_receipts_v1.json"
SCORE = ROOT / "evals/s211_query_evidence_compiler_score_v1.json"
OUT = ROOT / "evals/s211_query_evidence_compiler_zero_call_closure_v1.json"


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S211 zero-call closure already exists")
    if PARTIAL.exists() or RECEIPTS.exists() or SCORE.exists():
        raise RuntimeError("S211 zero-call closure found execution artifacts")
    body = {
        "schema": "s211_query_evidence_compiler_zero_call_closure_v1",
        "status": "NO_GO_ZERO_MODEL_CALL_PROVIDER_SCHEMA_UNSUPPORTED",
        "executed_against_main_sha": "22eda34249f0109b67e817e1209b23654617f435",
        "inputs": {
            "preflight_sha256": portable_file_sha(PREFLIGHT),
            "permit_sha256": portable_file_sha(PERMIT),
        },
        "execution": {
            "network_requests": 1,
            "model_calls": 0,
            "tokens": 0,
            "estimated_cost_usd": 0.0,
            "provider_retries": 0,
            "resume_attempts": 0,
        },
        "first_failure": {
            "provider": "anthropic",
            "model_requested": "claude-haiku-4-5-20251001",
            "http_status": 400,
            "error_type": "invalid_request_error",
            "request_id": "req_011Cd959XAcMbb96r4izgo3r",
            "message": (
                "output_config.format.schema: For 'array' type, property "
                "'maxItems' is not supported"
            ),
        },
        "causal_analysis": {
            "category": "PROVIDER_STRUCTURED_SCHEMA_CAPABILITY_MISMATCH",
            "semantic_prompt_failure": False,
            "target_specific": False,
            "target_output_observed": False,
            "result_quality_observed": False,
            "safe_general_correction": (
                "Use the provider-supported schema and deterministically retain at "
                "most the first 16 claims locally; source binding and all result "
                "gates remain fail-closed."
            ),
        },
        "credit": {
            "facts_moved_to_ok": 0,
            "canonical_facts_ok": 143,
            "denominator": 157,
            "ok_rate_percent": 91.08,
        },
        "decision": {
            "same_run_retry": False,
            "runtime_integration": False,
            "production_default": "off",
            "next": "S212_DETERMINISTIC_OVERFLOW_DROP_FRESH_PREREG",
        },
        "invariants": {
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    }
    payload = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": payload["status"], "next": body["decision"]["next"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
