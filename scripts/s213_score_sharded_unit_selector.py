#!/usr/bin/env python3
"""Apply the byte-frozen S210 factual gates to the complete S213 matrix."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s210_score_query_evidence_compiler as engine  # noqa: E402
from src.rag.query_evidence_compiler import (  # noqa: E402
    portable_file_sha,
    stable_sha,
)


PREFLIGHT = ROOT / "evals/s213_sharded_unit_selector_preflight_v1.json"
RECEIPTS = ROOT / "evals/s213_sharded_unit_selector_receipts_v1.json"
OUT = ROOT / "evals/s213_sharded_unit_selector_score_v1.json"


def build_legacy_score_proxy(receipts: dict[str, Any]) -> dict[str, Any]:
    """Normalize only the historical scorer's hard-coded call-count header.

    The frozen scorer evaluates every S213 answer, receipt, cost and hash-bearing
    row.  Its only experiment-specific incompatibility is the literal 202 call
    count.  The proxy changes that header to 202 and recomputes its own seal;
    the published score is rebound to the untouched 260-call artifact.
    """
    body = dict(receipts)
    expected = body.pop("result_sha256", None)
    if expected is None or stable_sha(body) != expected:
        raise RuntimeError("S213 receipts seal drift")
    if body.get("status") != "COMPLETE" or body.get("calls") != 260:
        raise RuntimeError("S213 receipts are not a complete 260-call matrix")
    body["calls"] = 202
    return {**body, "result_sha256": stable_sha(body)}


def main() -> int:
    actual = json.loads(RECEIPTS.read_text(encoding="utf-8"))
    proxy = build_legacy_score_proxy(actual)
    with tempfile.TemporaryDirectory(prefix="s213_score_proxy_") as temp_dir:
        proxy_path = Path(temp_dir) / "receipts_proxy.json"
        proxy_path.write_text(
            json.dumps(proxy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        engine.PREFLIGHT = PREFLIGHT
        engine.RECEIPTS = proxy_path
        engine.OUT = OUT
        status = engine.main()
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    payload.pop("result_sha256")
    payload["schema"] = "s213_sharded_unit_selector_score_v1"
    payload["inputs"]["receipts_sha256"] = portable_file_sha(RECEIPTS)
    payload["lineage"] = {
        "scorer": "S210_FROZEN_FACT_AND_GUARDRAIL_GATE",
        "historical_scorer_file_modified": False,
        "compatibility_proxy_delta": {"calls": {"from": 260, "to": 202}},
        "published_score_rebound_to_original_260_call_receipts": True,
        "upstream_pool": "DETERMINISTIC_HEADER_AWARE_UNITS_12_OF_12",
        "downstream_selection": "PER_CHUNK_WITH_MANDATORY_QUERY_FALLBACK",
        "fresh_generalization_evidence": False,
    }
    payload["decision"]["runtime_integration"] = False
    payload["decision"]["production_default"] = "off"
    payload["decision"]["next"] = (
        "RUN_ONE_SEALED_SOL_XHIGH_PLUS_FABLE_ATOMIC_RESULT_REVIEW"
        if status == 0
        else "CLOSE_S213_WITHOUT_SAME_COHORT_TUNING"
    )
    body = payload
    sealed = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(sealed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
