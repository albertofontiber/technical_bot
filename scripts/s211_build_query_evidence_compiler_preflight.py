#!/usr/bin/env python3
"""Build S211 by reusing the frozen S210 population builder without output reuse."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s210_build_query_evidence_compiler_preflight as engine  # noqa: E402
from src.rag.query_evidence_compiler import stable_sha  # noqa: E402


PREREG = ROOT / "evals/s211_query_evidence_compiler_prereg_v1.yaml"
OUT = ROOT / "evals/s211_query_evidence_compiler_preflight_v1.json"


def main() -> int:
    engine.PREREG = PREREG
    engine.OUT = OUT
    engine.IMPLEMENTATION_FILES = (
        "src/rag/query_evidence_compiler.py",
        "src/rag/query_evidence_compiler_v2.py",
        "src/rag/query_evidence_obligations.py",
        "scripts/s210_build_query_evidence_compiler_preflight.py",
        "scripts/s210_run_query_evidence_compiler.py",
        "scripts/s210_score_query_evidence_compiler.py",
        "scripts/s211_build_query_evidence_compiler_preflight.py",
        "scripts/s211_run_query_evidence_compiler.py",
        "scripts/s211_score_query_evidence_compiler.py",
        "evals/s211_query_evidence_compiler_design_v1.md",
        "evals/s211_query_evidence_compiler_prereg_v1.yaml",
    )
    status = engine.main()
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    payload.pop("result_sha256")
    payload["schema"] = "s211_query_evidence_compiler_preflight_v1"
    payload["main_sha"] = "dd7d35b214f8913e89c614bf2d534327edcd926b"
    payload["lineage"] = {
        "engine": "S210_FROZEN_EXECUTION_ENGINE",
        "contract_delta": "PROVIDER_CLAIMS_MAX_ITEMS_EQUALS_LOCAL_LIMIT_16",
        "s210_outputs_reused": False,
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
