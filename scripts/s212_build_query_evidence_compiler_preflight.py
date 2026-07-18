#!/usr/bin/env python3
"""Build the zero-call S212 manifest on the frozen S210 population."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s210_build_query_evidence_compiler_preflight as engine  # noqa: E402
from src.rag.query_evidence_compiler import stable_sha  # noqa: E402


PREREG = ROOT / "evals/s212_query_evidence_compiler_prereg_v1.yaml"
OUT = ROOT / "evals/s212_query_evidence_compiler_preflight_v1.json"


def main() -> int:
    engine.PREREG = PREREG
    engine.OUT = OUT
    engine.IMPLEMENTATION_FILES = (
        "src/rag/query_evidence_compiler.py",
        "src/rag/query_evidence_compiler_v3.py",
        "src/rag/query_evidence_obligations.py",
        "scripts/s210_build_query_evidence_compiler_preflight.py",
        "scripts/s210_run_query_evidence_compiler.py",
        "scripts/s210_score_query_evidence_compiler.py",
        "scripts/s212_build_query_evidence_compiler_preflight.py",
        "scripts/s212_run_query_evidence_compiler.py",
        "scripts/s212_score_query_evidence_compiler.py",
        "evals/s212_query_evidence_compiler_design_v1.md",
        "evals/s212_query_evidence_compiler_prereg_v1.yaml",
    )
    status = engine.main()
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    payload.pop("result_sha256")
    payload["schema"] = "s212_query_evidence_compiler_preflight_v1"
    payload["main_sha"] = "c9f1ced740fc78b4b13ec520974e859cbc8db1d5"
    payload["lineage"] = {
        "engine": "S210_FROZEN_EXECUTION_ENGINE",
        "contract_delta": "PROVIDER_SUPPORTED_SCHEMA_PLUS_LOCAL_BATCHED_FULL_BINDING",
        "s210_outputs_reused": False,
        "s211_target_outputs_observed": False,
        "target_cohort_prior_partial_exposure": True,
        "fresh_generalization_evidence": False,
    }
    body = payload
    sealed = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(sealed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": sealed["status"], "checks": sealed["checks"]}))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
