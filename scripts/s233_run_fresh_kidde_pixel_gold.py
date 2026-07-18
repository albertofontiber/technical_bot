#!/usr/bin/env python3
"""Run the frozen S233 fresh Kidde pixel-gold gate with strict schemas."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s217_run_kidde_external_cohort as base  # noqa: E402
from src.rag.frontier_visual_runtime_v2 import FrontierVisualRuntime  # noqa: E402
from src.rag.frontier_visual_schemas import (  # noqa: E402
    anthropic_compatible_schema,
    candidate_schema,
    review_schema,
    support_mapping_schema,
    support_review_schema,
)
from src.rag.multisource_visual_gold import (  # noqa: E402
    page_content_fable,
    page_content_openai,
)
from src.rag.visual_gold import (  # noqa: E402
    conservative_cost,
    normalized_text_sha,
    sealed_artifact,
    stable_sha,
    write_json,
)


PACKET = ROOT / "evals/s230_kidde_fresh_clause_bound_packet_v1.json"
PREREG = ROOT / "evals/s233_fresh_kidde_pixel_gold_prereg_v1.yaml"
DESIGN_GATE = ROOT / "evals/s232_design_frontier_reviews_v1.json"
ATTEMPTS = ROOT / "evals/s233_frontier_attempts_v1.json"
LEDGER = ROOT / "evals/s233_frontier_call_ledger_v1.json"
SOL_GENERATIONS = ROOT / "evals/s233_kidde_sol_generations_v1.json"
FABLE_GENERATIONS = ROOT / "evals/s233_kidde_fable_generations_v1.json"
SOL_REVIEWS = ROOT / "evals/s233_kidde_sol_reviews_of_fable_v1.json"
FABLE_REVIEWS = ROOT / "evals/s233_kidde_fable_reviews_of_sol_v1.json"
PIXEL_GOLD = ROOT / "evals/s233_kidde_pixel_gold_v1.json"
SOL_MAPPINGS = ROOT / "evals/s233_kidde_sol_support_mappings_v1.json"
FABLE_SUPPORT_REVIEWS = ROOT / "evals/s233_kidde_fable_support_reviews_v1.json"
SUPPORTED_GOLD = ROOT / "evals/s233_kidde_supported_gold_v1.json"
RESULT = ROOT / "evals/s233_kidde_pixel_gold_result_v1.json"
SOL = "gpt-5.6-sol"
FABLE = "claude-fable-5"
PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}
INTERNAL_BUDGET_USD = 100.0
ENV_FILE: Path | None = None


def _sealed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def verify_prereg(packet: dict[str, Any], *, require_design_gate: bool = True) -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise ValueError("S233 prereg is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if normalized_text_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError(f"S233 frozen input drift: {label}")
    packet_body = dict(packet)
    packet_sha = packet_body.pop("packet_sha256", None)
    if stable_sha(packet_body) != packet_sha or prereg["packet_sha256"] != packet_sha:
        raise ValueError("S233 packet identity drift")
    if len(packet.get("items") or []) != 3:
        raise ValueError("S233 requires exactly three frozen items")
    if require_design_gate and _sealed(DESIGN_GATE).get("status") != "DUAL_PASS":
        raise ValueError("S233 design gate is not DUAL_PASS")


def _checkpoint_attempt(label: str) -> None:
    body = {"schema": "s233_frontier_attempts_v1", "attempts": []}
    if ATTEMPTS.exists():
        body = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    body["attempts"].append({"call_label": label, "status": "STARTED_NO_RETRY"})
    write_json(ATTEMPTS, body)


def _schema(label: str) -> dict[str, Any]:
    if label.startswith("generate:"):
        return candidate_schema(label.removeprefix("generate:"))
    if label.startswith("review:fable:"):
        return review_schema(SOL, FABLE, label.removeprefix("review:fable:"))
    if label.startswith("review:sol:"):
        return review_schema(FABLE, SOL, label.removeprefix("review:sol:"))
    if label.startswith("map:support:"):
        return support_mapping_schema(SOL, label.removeprefix("map:support:"))
    if label.startswith("review:support:"):
        return support_review_schema(FABLE, SOL, label.removeprefix("review:support:"))
    raise ValueError(f"unknown S233 call label: {label}")


class S233Runtime(FrontierVisualRuntime):
    def call_sol(
        self,
        content: list[dict[str, Any]],
        call_label: str,
        *,
        output_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        _checkpoint_attempt(call_label)
        return super().call_sol(content, call_label, output_schema=_schema(call_label))

    def call_fable(
        self,
        content: list[dict[str, Any]],
        max_tokens: int,
        call_label: str,
        *,
        output_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del max_tokens
        _checkpoint_attempt(call_label)
        bounded_tokens = 16000 if call_label.startswith("generate:") else 12000
        return super().call_fable(
            content,
            bounded_tokens,
            call_label,
            output_schema=anthropic_compatible_schema(_schema(call_label)),
        )


def _runtime() -> FrontierVisualRuntime:
    if ENV_FILE is None:
        raise RuntimeError("S233 env file was not configured")
    secrets = dotenv_values(ENV_FILE)
    openai_key = str(secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    anthropic_key = str(secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not openai_key or not anthropic_key:
        raise RuntimeError("S233 provider credential missing")
    return S233Runtime(
        ledger_path=LEDGER,
        ledger_schema="s233_frontier_call_ledger_v1",
        sol_model=SOL,
        fable_model=FABLE,
        sol_reasoning="xhigh",
        fable_effort="xhigh",
        prices=PRICES,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
    )


def _rename(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _rename(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rename(item) for item in value]
    if isinstance(value, str):
        return value.replace("S217", "S233").replace("s217", "s233")
    return value


def _checkpoint(path: Path, schema: str, body: dict[str, Any]) -> None:
    write_json(path, sealed_artifact(_rename(schema), _rename(body)))


def _write_result(runtime: FrontierVisualRuntime, body: dict[str, Any]) -> None:
    calls = runtime.load_ledger().get("calls") or []
    _checkpoint(
        RESULT,
        "s233_kidde_pixel_gold_result_v1",
        {
            **_rename(body),
            "frontier_calls": len(calls),
            "conservative_frontier_cost_usd": conservative_cost(calls, PRICES),
            "internal_budget_usd": INTERNAL_BUDGET_USD,
            "provider_retries": 0,
            "official_fact_credit": 0,
            "official_denominator_change": 0,
            "target_calls": 0,
            "runtime_integration": False,
            "production_default_changed": False,
            "chunks_v2_status": "ACTIVE_READ_ONLY",
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    )


def _seal_and_stop(
    runtime: FrontierVisualRuntime, status: str, reason: str, body: dict[str, Any]
) -> int:
    calls = runtime.load_ledger().get("calls") or []
    runtime.seal_complete(len(calls))
    _write_result(runtime, {"status": _rename(status), "reason": reason, **body})
    return 2


def _configure_base() -> None:
    paths = {
        "PACKET_PATH": PACKET,
        "PREREG_PATH": PREREG,
        "DESIGN_GATE_PATH": DESIGN_GATE,
        "SOL_GENERATIONS": SOL_GENERATIONS,
        "FABLE_GENERATIONS": FABLE_GENERATIONS,
        "SOL_REVIEWS": SOL_REVIEWS,
        "FABLE_REVIEWS": FABLE_REVIEWS,
        "PIXEL_GOLD": PIXEL_GOLD,
        "SOL_MAPPINGS": SOL_MAPPINGS,
        "FABLE_SUPPORT_REVIEWS": FABLE_SUPPORT_REVIEWS,
        "SUPPORTED_GOLD": SUPPORTED_GOLD,
        "RESULT": RESULT,
        "CALL_LEDGER": LEDGER,
    }
    for name, path in paths.items():
        setattr(base, name, path)
    base.SOL_MODEL = SOL
    base.FABLE_MODEL = FABLE
    base.SOL_REASONING = "xhigh"
    base.CANDIDATE_ITEMS = 3
    base.MINIMUM_ITEMS = 3
    base.GENERATION_CALLS = 6
    base.FRONTIER_CALLS_MAX = 18
    base.INTERNAL_BUDGET_USD = INTERNAL_BUDGET_USD
    base.FRONTIER_PRICES = PRICES
    base.verify_prereg = verify_prereg
    base._runtime = _runtime
    base._checkpoint = _checkpoint
    base._write_result = _write_result
    base._seal_and_stop = _seal_and_stop


def preflight(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    images = 0
    for item in packet["items"]:
        page_content_openai(ROOT, item, "verify")
        page_content_fable(ROOT, item, "verify")
        images += len(item["rendered_pages"])
        if any(len(unit["content"]) > 600 for unit in item["evidence_units"]):
            raise ValueError("S233 broad evidence unit escaped packet gate")
        if "maxItems" in json.dumps(
            anthropic_compatible_schema(candidate_schema(item["canary_id"]))
        ):
            raise ValueError("S233 Anthropic schema still contains maxItems")
    print(json.dumps({"status": "PREFLIGHT_PASS", "items": 3, "images": images, "paid_calls": 0}, indent=2))
    return 0


def _write_hold(exc: Exception) -> None:
    if RESULT.exists():
        return
    calls: list[dict[str, Any]] = []
    if LEDGER.exists():
        calls = json.loads(LEDGER.read_text(encoding="utf-8")).get("calls") or []
    _checkpoint(
        RESULT,
        "s233_kidde_pixel_gold_result_v1",
        {
            "status": "HOLD_S233_EXTERNAL_OR_INCOMPLETE",
            "reason": f"{type(exc).__name__}: {exc}",
            "frontier_calls": len(calls),
            "conservative_frontier_cost_usd": conservative_cost(calls, PRICES),
            "provider_retries": 0,
            "official_fact_credit": 0,
            "target_calls": 0,
            "production_default_changed": False,
            "chunks_v2_status": "ACTIVE_READ_ONLY",
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    )


def main() -> int:
    global ENV_FILE
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    if not args.execute:
        return preflight(packet)
    if args.env_file is None:
        raise ValueError("--env-file is required with --execute")
    ENV_FILE = args.env_file
    _configure_base()
    try:
        return base.execute(packet)
    except Exception as exc:
        _write_hold(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
