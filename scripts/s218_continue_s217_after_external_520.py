#!/usr/bin/env python3
"""Run one fail-closed continuation of S217 after its zero-call HTTP 520."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.visual_gold import normalized_text_sha, stable_sha  # noqa: E402


BASE_RUNNER = ROOT / "scripts/s217_run_kidde_external_cohort.py"
PACKET_PATH = ROOT / "evals/s217_kidde_external_cohort_packet_v1.json"
PRIOR_RESULT = ROOT / "evals/s217_kidde_external_cohort_result_v1.json"
PRIOR_LEDGER = ROOT / "evals/s217_frontier_call_ledger_v1.json"
PREREG_PATH = ROOT / "evals/s218_s217_external_520_continuation_prereg_v1.yaml"

OUTPUT_PATHS = {
    "SOL_GENERATIONS": ROOT / "evals/s218_kidde_sol_generations_v1.json",
    "FABLE_GENERATIONS": ROOT / "evals/s218_kidde_fable_generations_v1.json",
    "SOL_REVIEWS": ROOT / "evals/s218_kidde_sol_reviews_of_fable_v1.json",
    "FABLE_REVIEWS": ROOT / "evals/s218_kidde_fable_reviews_of_sol_v1.json",
    "PIXEL_GOLD": ROOT / "evals/s218_kidde_pixel_gold_v1.json",
    "SOL_MAPPINGS": ROOT / "evals/s218_kidde_sol_support_mappings_v1.json",
    "FABLE_SUPPORT_REVIEWS": ROOT
    / "evals/s218_kidde_fable_support_reviews_v1.json",
    "SUPPORTED_GOLD": ROOT / "evals/s218_kidde_supported_gold_v1.json",
    "RESULT": ROOT / "evals/s218_kidde_external_cohort_result_v1.json",
    "CALL_LEDGER": ROOT / "evals/s218_frontier_call_ledger_v1.json",
}


def _load_base() -> Any:
    spec = importlib.util.spec_from_file_location("s217_runner", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen S217 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def _verify_continuation() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_SINGLE_CONTINUATION_ATTEMPT":
        raise ValueError("S218 continuation is not frozen")
    for label, frozen in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / frozen["path"]) != frozen["sha256"]:
            raise ValueError(f"S218 frozen input drift: {label}")

    prior = _sealed(PRIOR_RESULT)
    reason = str(prior.get("reason", ""))
    if (
        prior.get("status") != "HOLD_S217_EXTERNAL_OR_INCOMPLETE"
        or prior.get("frontier_calls") != 0
        or "Error code: 520" not in reason
        or "'retryable': True" not in reason
        or "'retry_after': 60" not in reason
    ):
        raise ValueError("S217 is not the frozen zero-call retryable HTTP 520 hold")
    if PRIOR_LEDGER.exists():
        raise ValueError("S217 unexpectedly has a call ledger")
    existing = [
        path.relative_to(ROOT).as_posix()
        for path in OUTPUT_PATHS.values()
        if path.exists()
    ]
    if existing:
        raise ValueError(f"S218 continuation already attempted: {existing}")
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    packet = _verify_continuation()
    base = _load_base()
    for name, path in OUTPUT_PATHS.items():
        setattr(base, name, path)
    if not args.execute:
        base.verify_prereg(packet, require_design_gate=False)
        print(
            json.dumps(
                {
                    "status": "PREFLIGHT_PASS",
                    "prior_frontier_calls": 0,
                    "continuation_attempts_authorized": 1,
                    "provider_retries_inside_attempt": 0,
                    "target_calls": 0,
                },
                indent=2,
            )
        )
        return 0
    return base.execute(packet)


if __name__ == "__main__":
    raise SystemExit(main())
