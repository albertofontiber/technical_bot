#!/usr/bin/env python3
"""Thin S211 adapter: fresh run, v2 schema, frozen S210 execution engine."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s210_run_query_evidence_compiler as engine  # noqa: E402
from src.rag.query_evidence_compiler import stable_sha  # noqa: E402
from src.rag.query_evidence_compiler_v2 import (  # noqa: E402
    claim_schema,
    validate_claim_response,
)


PREFLIGHT = ROOT / "evals/s211_query_evidence_compiler_preflight_v1.json"
PERMIT = ROOT / "evals/s211_query_evidence_compiler_execution_permit_v1.yaml"
PARTIAL = ROOT / "evals/s211_query_evidence_compiler_calls_v1.partial.jsonl"
OUT = ROOT / "evals/s211_query_evidence_compiler_receipts_v1.json"


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
    payload["schema"] = "s211_query_evidence_compiler_receipts_v1"
    payload["lineage"] = {
        "engine": "S210_FROZEN_EXECUTION_ENGINE",
        "contract": "S211_SCHEMA_VALIDATOR_EQUIVALENCE_V2",
        "s210_outputs_reused": False,
    }
    body = payload
    sealed = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(sealed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
