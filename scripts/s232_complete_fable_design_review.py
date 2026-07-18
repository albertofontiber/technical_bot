#!/usr/bin/env python3
"""One Fable-only completion after S231's pre-inference schema rejection."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s230_review_fresh_clause_bound_design as base  # noqa: E402
from src.rag.visual_gold import (  # noqa: E402
    normalized_text_sha,
    sealed_artifact,
    write_json,
)


PREREG = ROOT / "evals/s232_fable_schema_correction_prereg_v1.yaml"
PRIOR_LEDGER = ROOT / "evals/s231_design_frontier_call_ledger_v1.json"
LEDGER = ROOT / "evals/s232_design_fable_call_ledger_v1.json"
ATTEMPTS = ROOT / "evals/s232_design_fable_attempts_v1.json"
RESULT = ROOT / "evals/s232_design_frontier_reviews_v1.json"


def verify_prereg() -> dict:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S232 prereg is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S232 frozen input drift: {label}")
    return prereg


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    verify_prereg()
    existing = [path.name for path in (LEDGER, ATTEMPTS, RESULT) if path.exists()]
    if existing:
        raise RuntimeError(f"S232 artifacts already exist: {existing}")

    prior = json.loads(PRIOR_LEDGER.read_text(encoding="utf-8"))
    if len(prior.get("calls") or []) != 1:
        raise ValueError("S231 must contain exactly one completed principal call")
    principal = json.loads(prior["calls"][0]["raw_output"])
    if not base.validate(principal, base.SOL):
        raise ValueError("S231 principal review is not PASS")

    prompt = (
        "Review this single bounded design. PASS only if every structured check is true. "
        "FAIL only for a concrete false-GO, contamination, unsupported-credit, transport, "
        "or budget blocker. Do not request convergence, broader research, or another round.\n\n"
        + base.DESIGN.read_text(encoding="utf-8")
    )
    write_json(
        ATTEMPTS,
        {
            "schema": "s232_design_fable_attempts_v1",
            "attempts": [
                {"call_label": "design:fable", "status": "STARTED_NO_RETRY"}
            ],
        },
    )
    base.LEDGER = LEDGER
    rt = base.runtime(args.env_file)
    independent, _ = rt.call_fable(
        [{"type": "text", "text": prompt}],
        12000,
        "design:fable",
        output_schema=base.schema(base.FABLE),
    )
    independent_pass = base.validate(independent, base.FABLE)
    current = rt.seal_complete(1)
    total_cost = round(
        float(prior["conservative_cost_usd"])
        + float(current["conservative_cost_usd"]),
        6,
    )
    dual = independent_pass
    write_json(
        RESULT,
        sealed_artifact(
            "s232_design_frontier_reviews_v1",
            {
                "status": "DUAL_PASS" if dual else "NO_GO_NO_RETRY",
                "reviews": {"sol": principal, "fable": independent},
                "frontier_calls_total": 2,
                "frontier_calls_s232": 1,
                "provider_retries": 0,
                "cost_usd_total": total_cost,
                "next_authorized_step": "pixel_gold" if dual else "close_s232",
                "target_calls": 0,
                "facts_moved_to_ok": 0,
                "production_default_changed": False,
                "chunks_v2": "ACTIVE_READ_ONLY",
                "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
                "railway_merge_gate": False,
            },
        ),
    )
    print(json.dumps({"status": "DUAL_PASS" if dual else "NO_GO_NO_RETRY", "cost_usd_total": total_cost}, indent=2))
    return 0 if dual else 2


if __name__ == "__main__":
    raise SystemExit(main())
