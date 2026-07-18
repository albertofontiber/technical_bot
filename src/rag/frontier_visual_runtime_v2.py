"""V2 frontier runtime with strict schemas and bounded adaptive Fable effort."""
from __future__ import annotations

import json
import re
import time
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
    """Exact-model runtime with resumable Sol background execution."""

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
        fable_effort: str | None = None,
        sol_background: bool = False,
        sol_transport_retries: int = 2,
        sol_poll_interval_seconds: float = 2.0,
        sol_poll_timeout_seconds: float = 1800.0,
        sol_state_dir: Path | None = None,
    ) -> None:
        if sol_transport_retries < 0 or sol_transport_retries > 4:
            raise ValueError("sol_transport_retries must be between 0 and 4")
        if not 0 < sol_poll_interval_seconds <= 30:
            raise ValueError("sol_poll_interval_seconds must be in (0, 30]")
        if not 1 <= sol_poll_timeout_seconds <= 7200:
            raise ValueError("sol_poll_timeout_seconds must be in [1, 7200]")
        self.ledger_path = ledger_path
        self.ledger_schema = ledger_schema
        self.sol_model = sol_model
        self.fable_model = fable_model
        self.sol_reasoning = sol_reasoning
        self.fable_effort = fable_effort
        self.prices = prices
        self.sol_background = sol_background
        self.sol_transport_retries = sol_transport_retries
        self.sol_poll_interval_seconds = sol_poll_interval_seconds
        self.sol_poll_timeout_seconds = sol_poll_timeout_seconds
        self.sol_state_dir = sol_state_dir or ledger_path.with_name(
            f"{ledger_path.stem}_sol_background"
        )
        self.sol = OpenAI(
            api_key=openai_api_key,
            max_retries=sol_transport_retries,
        )
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

    def _background_state_path(self, call_label: str) -> Path:
        digest = stable_sha(
            {
                "contract": "frontier_visual_sol_background_state_v1",
                "ledger_schema": self.ledger_schema,
                "call_label": call_label,
            }
        )[:16]
        return self.sol_state_dir / f"{digest}.json"

    def _load_background_state(
        self, call_label: str, request_sha256: str
    ) -> dict[str, Any] | None:
        path = self._background_state_path(call_label)
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        body = dict(value)
        expected = body.pop("result_sha256", None)
        if not expected or stable_sha(body) != expected:
            raise RuntimeError("Sol background state hash drift")
        if (
            value.get("schema") != "frontier_visual_sol_background_state_v1"
            or value.get("ledger_schema") != self.ledger_schema
            or value.get("call_label") != call_label
            or value.get("request_sha256") != request_sha256
        ):
            raise RuntimeError("Sol background state identity drift")
        return value

    def _write_background_state(
        self,
        *,
        call_label: str,
        request_sha256: str,
        response_id: str,
        status: str,
        polls: int,
        client_request_id: str,
    ) -> None:
        self.sol_state_dir.mkdir(parents=True, exist_ok=True)
        body = {
            "schema": "frontier_visual_sol_background_state_v1",
            "ledger_schema": self.ledger_schema,
            "call_label": call_label,
            "request_sha256": request_sha256,
            "response_id": response_id,
            "status": status,
            "polls": polls,
            "client_request_id": client_request_id,
        }
        body["result_sha256"] = stable_sha(body)
        write_json(self._background_state_path(call_label), body)

    def _call_sol_background(
        self,
        request: dict[str, Any],
        call_label: str,
    ) -> Any:
        request = {**request, "background": True}
        request_sha256 = stable_sha(request)
        client_request_id = f"fv-{request_sha256[:24]}-{stable_sha(call_label)[:16]}"
        state = self._load_background_state(call_label, request_sha256)
        if state is None:
            response = self.sol.responses.create(
                **request,
                extra_headers={"X-Client-Request-Id": client_request_id},
            )
            response_id = str(getattr(response, "id", "") or "")
            status = str(getattr(response, "status", "") or "")
            if not response_id:
                raise RuntimeError("Sol background create returned no response ID")
            polls = 0
            self._write_background_state(
                call_label=call_label,
                request_sha256=request_sha256,
                response_id=response_id,
                status=status,
                polls=polls,
                client_request_id=client_request_id,
            )
        else:
            response_id = str(state["response_id"])
            polls = int(state["polls"])
            response = self.sol.responses.retrieve(
                response_id,
                extra_headers={"X-Client-Request-Id": client_request_id},
            )
            status = str(getattr(response, "status", "") or "")

        started = time.monotonic()
        while status in {"queued", "in_progress"}:
            if time.monotonic() - started >= self.sol_poll_timeout_seconds:
                raise TimeoutError(
                    f"Sol background polling exceeded {self.sol_poll_timeout_seconds}s; "
                    f"response_id={response_id}"
                )
            time.sleep(self.sol_poll_interval_seconds)
            response = self.sol.responses.retrieve(
                response_id,
                extra_headers={"X-Client-Request-Id": client_request_id},
            )
            polls += 1
            status = str(getattr(response, "status", "") or "")
            self._write_background_state(
                call_label=call_label,
                request_sha256=request_sha256,
                response_id=response_id,
                status=status,
                polls=polls,
                client_request_id=client_request_id,
            )
        return response

    @staticmethod
    def _schema_name(call_label: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9_-]+", "_", call_label).strip("_")
        return (value or "structured_output")[:64]

    def call_sol(
        self,
        content: list[dict[str, Any]],
        call_label: str,
        *,
        output_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        request: dict[str, Any] = {
            "model": self.sol_model,
            "instructions": "Follow the user contract exactly. Return only JSON.",
            "input": [{"role": "user", "content": content}],
            "reasoning": {"effort": self.sol_reasoning},
            "max_output_tokens": 12000,
            "store": False,
        }
        if output_schema is not None:
            request["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": self._schema_name(call_label),
                    "strict": True,
                    "schema": output_schema,
                },
                "verbosity": "low",
            }
        response = (
            self._call_sol_background(request, call_label)
            if self.sol_background
            else self.sol.responses.create(**request)
        )
        raw = (getattr(response, "output_text", "") or "").strip()
        receipt = {
            "provider": "sol",
            "call_label": call_label,
            "model": getattr(response, "model", None),
            "reasoning_effort": self.sol_reasoning,
            "background": self.sol_background,
            "transport_retries_configured": self.sol_transport_retries,
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
        *,
        output_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        request: dict[str, Any] = {
            "model": self.fable_model,
            "max_tokens": max_tokens,
            "system": "Follow the user contract exactly. Return only JSON.",
            "messages": [{"role": "user", "content": content}],
        }
        if output_schema is not None:
            request["output_config"] = {
                "format": {"type": "json_schema", "schema": output_schema}
            }
            if self.fable_effort is not None:
                request["thinking"] = {"type": "adaptive"}
                request["output_config"]["effort"] = self.fable_effort
        response = self.fable.messages.create(**request)
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


