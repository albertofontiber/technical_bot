#!/usr/bin/env python3
"""Fresh S212 run using the provider-compatible deterministic overflow policy."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s210_run_query_evidence_compiler as engine  # noqa: E402
from src.rag.query_evidence_compiler import stable_sha  # noqa: E402
from src.rag.query_evidence_compiler_v3 import (  # noqa: E402
    MAX_MODEL_CLAIMS_PER_CHUNK,
    claim_schema,
    validate_claim_response,
)


PREFLIGHT = ROOT / "evals/s212_query_evidence_compiler_preflight_v1.json"
PERMIT = ROOT / "evals/s212_query_evidence_compiler_execution_permit_v1.yaml"
PARTIAL = ROOT / "evals/s212_query_evidence_compiler_calls_v1.partial.jsonl"
OUT = ROOT / "evals/s212_query_evidence_compiler_receipts_v1.json"


def _legacy_limit_receipt() -> dict:
    rows = [
        json.loads(line)
        for line in PARTIAL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    observed = []
    for row in rows:
        if row["role"] != "extractor":
            continue
        count = len(json.loads(row["raw_output"])["claims"])
        excess = max(0, count - MAX_MODEL_CLAIMS_PER_CHUNK)
        if excess:
            observed.append(
                {
                    "call_id": row["call_id"],
                    "raw_claims": count,
                    "binding_batch_size": MAX_MODEL_CLAIMS_PER_CHUNK,
                    "excess_claims_fully_bound": excess,
                    "raw_output_sha256": row["raw_output_sha256"],
                }
            )
    return {
        "policy": "BIND_ALL_IN_PROVIDER_ORDER_USING_BATCHES_OF_16",
        "calls_exceeding_legacy_limit": len(observed),
        "excess_claims_fully_bound": sum(
            row["excess_claims_fully_bound"] for row in observed
        ),
        "max_raw_claims": max((row["raw_claims"] for row in observed), default=0),
        "calls": observed,
    }


def main() -> int:
    engine.PREFLIGHT = PREFLIGHT
    engine.PERMIT = PERMIT
    engine.PARTIAL = PARTIAL
    engine.OUT = OUT
    engine.claim_schema = claim_schema
    engine.validate_claim_response = validate_claim_response
    status = engine.main()
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    payload.pop("result_sha256")
    payload["schema"] = "s212_query_evidence_compiler_receipts_v1"
    payload["legacy_claim_limit"] = _legacy_limit_receipt()
    payload["lineage"] = {
        "engine": "S210_FROZEN_EXECUTION_ENGINE",
        "contract": "S212_DETERMINISTIC_BATCHED_FULL_BINDING_V3",
        "prior_outputs_reused": False,
    }
    body = payload
    sealed = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(sealed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
