#!/usr/bin/env python3
"""Run S252 through the frozen S251 execution engine with retries disabled."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import s251_run_adaptive_reasoning_writer_ab as engine
from src.rag.visual_gold import sealed_artifact, write_json

ROOT = Path(__file__).resolve().parents[1]
engine.PREREG = ROOT / "evals/s252_adaptive_reasoning_writer_ab_prereg_v1.yaml"
engine.PERMIT = ROOT / "evals/s252_adaptive_reasoning_writer_ab_execution_permit_v1.yaml"
engine.OUT = ROOT / "evals/s252_adaptive_reasoning_writer_generation_v1.json"
engine.LEDGER = ROOT / "evals/s252_adaptive_reasoning_writer_call_ledger_v1.json"


def _disable_transport_retries(_exc: Exception) -> bool:
    return False


def _relabel(path: Path, schema: str) -> None:
    value = engine._sealed(path)
    body = {key: item for key, item in value.items() if key not in {"schema", "result_sha256"}}
    write_json(path, sealed_artifact(schema, body))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=engine.DEFAULT_ENV)
    args = parser.parse_args()
    engine._retryable = _disable_transport_retries
    _prereg, packet, response_usage_bound = engine.verify()
    print(json.dumps({
        "status": "S252_PREFLIGHT_RESPONSE_USAGE_BOUND_PASS",
        "response_usage_bound_usd": round(response_usage_bound, 6),
        "transport_retries": 0,
    }, indent=2))
    engine.execute(packet, args.env_file)
    _relabel(engine.OUT, "s252_adaptive_reasoning_writer_generation_v1")
    _relabel(engine.LEDGER, "s252_adaptive_reasoning_writer_call_ledger_v1")
    print(json.dumps({"status": "S252_GENERATION_COMPLETE_SCORE_NOT_OPENED"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

