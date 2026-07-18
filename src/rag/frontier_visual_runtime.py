"""Reusable, bounded provider runtime for pixel-grounded frontier reviews."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anthropic
from openai import OpenAI

from src.rag.visual_gold import (
    conservative_cost,
    parse_json,
    stable_sha,
    usage_dict,
    write_json,
)


class FrontierVisualRuntime:
    """Exact-model, zero-retry runtime with an append-only sealed call ledger."""

    def __init__(
        self,
        *,
        ledger_path: Path,
        ledger_schema: str,
        sol_model: str,
        fable_model: str,
        sol_reasoning: str,
        prices: dict[str, dict[str, float]],
        openai_api_key: str,
        anthropic_api_key: str,
    ) -> None:
        self.ledger_path = ledger_path
        self.ledger_schema = ledger_schema
        self.sol_model = sol_model
        self.fable_model = fable_model
        self.sol_reasoning = sol_reasoning
        self.prices = prices
        self.sol = OpenAI(api_key=openai_api_key, max_retries=0)
        self.fable = anthropic.Anthropic(
            api_key=anthropic_api_key, max_retries=0
        )

    def load_ledger(self) -> dict[str, Any]:
        if not self.ledger_path.exists():
            return {
                "schema": self.ledger_schema,
                "status": "IN_PROGRESS",
                "calls": [],
            }
        ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        body = dict(ledger)
        expected = body.pop("result_sha256")
        if stable_sha(body) != expected:
            raise RuntimeError("frontier ledger hash drift")
        return ledger

    def _append(self, receipt: dict[str, Any]) -> None:
        ledger = self.load_ledger()
        ledger.pop("result_sha256", None)
        ledger["calls"].append(receipt)
        ledger["conservative_cost_usd"] = conservative_cost(
            ledger["calls"], self.prices
        )
        ledger["result_sha256"] = stable_sha(ledger)
        write_json(self.ledger_path, ledger)

    def call_sol(
        self, content: list[dict[str, Any]], call_label: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        response = self.sol.responses.create(
            model=self.sol_model,
            instructions="Follow the user contract exactly. Return only JSON.",
            input=[{"role": "user", "content": content}],
            reasoning={"effort": self.sol_reasoning},
            max_output_tokens=12000,
            store=False,
        )
        raw = (getattr(response, "output_text", "") or "").strip()
        receipt = {
            "provider": "sol",
            "call_label": call_label,
            "model": getattr(response, "model", None),
            "reasoning_effort": self.sol_reasoning,
            "status": getattr(response, "status", None),
            "raw_output": raw,
            "usage": usage_dict(response),
            "provider_trace": response.model_dump(mode="json", exclude_none=False),
        }
        self._append(receipt)
        if receipt["model"] != self.sol_model or receipt["status"] != "completed":
            raise RuntimeError(
                "Sol incomplete or model mismatch: "
                f"{receipt['status']} / {receipt['model']}"
            )
        if not raw:
            raise RuntimeError("Sol completed with empty final output")
        return parse_json(raw), receipt

    def call_fable(
        self,
        content: list[dict[str, Any]],
        max_tokens: int,
        call_label: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        response = self.fable.messages.create(
            model=self.fable_model,
            max_tokens=max_tokens,
            system="Follow the user contract exactly. Return only JSON.",
            messages=[{"role": "user", "content": content}],
        )
        raw = "\n".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        receipt = {
            "provider": "fable",
            "call_label": call_label,
            "model": getattr(response, "model", None),
            "status": getattr(response, "stop_reason", None),
            "raw_output": raw,
            "usage": usage_dict(response),
            "provider_trace": response.model_dump(mode="json", exclude_none=False),
        }
        self._append(receipt)
        if receipt["model"] != self.fable_model or receipt["status"] != "end_turn":
            raise RuntimeError(
                "Fable incomplete or model mismatch: "
                f"{receipt['status']} / {receipt['model']}"
            )
        if not raw:
            raise RuntimeError("Fable completed with empty final output")
        return parse_json(raw), receipt

    def seal_complete(self, expected_calls: int) -> dict[str, Any]:
        ledger = self.load_ledger()
        if len(ledger["calls"]) != expected_calls:
            raise RuntimeError("frontier call ledger incomplete")
        ledger.pop("result_sha256", None)
        ledger["status"] = "COMPLETE"
        ledger["result_sha256"] = stable_sha(ledger)
        write_json(self.ledger_path, ledger)
        return ledger
