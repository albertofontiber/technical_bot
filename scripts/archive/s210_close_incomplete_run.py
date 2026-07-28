#!/usr/bin/env python3
"""Seal the fail-closed S210 partial journal after its first contract violation."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.query_evidence_compiler import (  # noqa: E402
    MAX_MODEL_CLAIMS_PER_CHUNK,
    portable_file_sha,
    stable_sha,
)


PARTIAL = ROOT / "evals/s210_query_evidence_compiler_calls_v1.partial.jsonl"
PREFLIGHT = ROOT / "evals/s210_query_evidence_compiler_preflight_v1.json"
PERMIT = ROOT / "evals/s210_query_evidence_compiler_execution_permit_v1.yaml"
RECEIPTS = ROOT / "evals/s210_query_evidence_compiler_receipts_v1.json"
SCORE = ROOT / "evals/s210_query_evidence_compiler_score_v1.json"
OUT = ROOT / "evals/s210_query_evidence_compiler_incomplete_closure_v1.json"


def main() -> int:
    if OUT.exists():
        raise RuntimeError("S210 incomplete closure already exists")
    if RECEIPTS.exists() or SCORE.exists():
        raise RuntimeError("S210 cannot close incomplete with result/score artifacts")
    rows = [
        json.loads(line)
        for line in PARTIAL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 126 or [row["call_index"] for row in rows] != list(range(1, 127)):
        raise RuntimeError("S210 partial call sequence drift")
    if any(
        hashlib.sha256(row["raw_output"].encode("utf-8")).hexdigest()
        != row["raw_output_sha256"]
        for row in rows
    ):
        raise RuntimeError("S210 raw response receipt drift")
    last = rows[-1]
    last_claims = json.loads(last["raw_output"])["claims"]
    if (
        last["call_id"] != "hp002:r2:extract:f10"
        or last["role"] != "extractor"
        or len(last_claims) != 17
        or MAX_MODEL_CLAIMS_PER_CHUNK != 16
    ):
        raise RuntimeError("S210 first contract violation identity drift")

    roles = Counter(row["role"] for row in rows)
    models = Counter(row["model"] for row in rows)
    body = {
        "schema": "s210_query_evidence_compiler_incomplete_closure_v1",
        "status": "NO_GO_INCOMPLETE_FAIL_CLOSED",
        "executed_against_main_sha": "90e4597a346dc09c45ab4c901f3479d124c2e5e4",
        "inputs": {
            "preflight_sha256": portable_file_sha(PREFLIGHT),
            "permit_sha256": portable_file_sha(PERMIT),
            "partial_journal_sha256": portable_file_sha(PARTIAL),
        },
        "execution": {
            "sealed_calls": len(rows),
            "planned_calls": 202,
            "completed_answer_rows": roles["verifier"],
            "planned_answer_rows": 36,
            "role_calls": dict(sorted(roles.items())),
            "model_calls": dict(sorted(models.items())),
            "provider_retries": 0,
            "resume_attempts": 0,
            "estimated_cost_usd": round(sum(float(row["cost_usd"]) for row in rows), 8),
        },
        "first_failure": {
            "call_index": last["call_index"],
            "call_id": last["call_id"],
            "provider": last["provider"],
            "model": last["model"],
            "response_id": last["response_id"],
            "response_status": last["status"],
            "raw_output_sha256": last["raw_output_sha256"],
            "exception_type": "ValueError",
            "exception_message": "claim count exceeds the per-chunk bound",
            "observed_claims": len(last_claims),
            "local_claim_limit": MAX_MODEL_CLAIMS_PER_CHUNK,
            "provider_schema_claims_max_items": None,
        },
        "causal_analysis": {
            "category": "SCHEMA_VALIDATOR_BOUND_DRIFT",
            "upstream_defect": (
                "The JSON schema omitted maxItems while the downstream validator "
                "enforced 16, so a provider-valid 17-claim response stopped the run."
            ),
            "target_specific": False,
            "semantic_prompt_failure": False,
            "provider_transport_failure": False,
            "result_quality_observed": False,
        },
        "credit": {
            "facts_moved_to_ok": 0,
            "canonical_facts_ok": 143,
            "denominator": 157,
            "ok_rate_percent": 91.08,
            "relation_projection_allowed": False,
        },
        "decision": {
            "same_run_resume": False,
            "same_run_retry": False,
            "partial_result_scoring": False,
            "runtime_integration": False,
            "production_default": "off",
            "next": "S211_SCHEMA_VALIDATOR_BOUND_EQUIVALENCE_FRESH_PREREG",
        },
        "invariants": {
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
                "calls": body["execution"]["sealed_calls"],
                "cost": body["execution"]["estimated_cost_usd"],
                "next": body["decision"]["next"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
