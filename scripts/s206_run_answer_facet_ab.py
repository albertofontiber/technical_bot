#!/usr/bin/env python3
"""Execute the sealed S206 2x2 answer A/B with append-only checkpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PREFLIGHT = ROOT / "evals/s206_answer_facet_ab_preflight_v1.json"
PERMIT = ROOT / "evals/s206_answer_facet_ab_execution_permit_v1.yaml"
CHECKPOINT = ROOT / "evals/s206_answer_facet_ab_receipts_v1.partial.jsonl"
OUT = ROOT / "evals/s206_answer_facet_ab_receipts_v1.json"
PRICE_INPUT = 3.0
PRICE_OUTPUT = 15.0


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _append(row: dict[str, Any]) -> None:
    with CHECKPOINT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def validate_permit() -> tuple[dict[str, Any], dict[str, Any]]:
    if not PERMIT.is_file():
        raise RuntimeError("S206 execution permit is missing")
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    if permit.get("status") != "EXECUTION_GO_PAID_BOUNDED":
        raise RuntimeError("S206 execution permit is not GO")
    if file_sha(PREFLIGHT) != permit.get("preflight_sha256"):
        raise RuntimeError("S206 preflight drift")
    for receipt in permit.get("frozen_artifacts") or []:
        path = ROOT / receipt["path"]
        if not path.is_file() or file_sha(path) != receipt["sha256"]:
            raise RuntimeError(f"S206 permitted artifact drift: {receipt['path']}")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight.get("status") != "GO_ZERO_CALL_PREFLIGHT":
        raise RuntimeError("S206 preflight is not GO")
    if preflight.get("paid_calls") != 28:
        raise RuntimeError("S206 call plan changed")
    return permit, preflight


def _cost(row: dict[str, Any]) -> float:
    return (
        (row.get("input_tokens") or 0) * PRICE_INPUT
        + (row.get("output_tokens") or 0) * PRICE_OUTPUT
    ) / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        raise RuntimeError("zero-call by default; pass --execute after the sealed permit")

    permit, preflight = validate_permit()
    load_dotenv(args.env_file, override=True)
    os.environ.update({str(k): str(v) for k, v in preflight["flags"].items()})
    os.environ["ANSWER_FACET_LEDGER"] = "off"
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        raise RuntimeError("ANTHROPIC_API_KEY missing")

    from scripts.s206_answer_facet_ab_preflight import capture_envelope
    from src.rag import generator

    if CHECKPOINT.exists() or OUT.exists():
        raise RuntimeError(
            "S206 execution artifact already exists; resume and retries are forbidden"
        )
    checkpoints: dict[str, dict[str, Any]] = {}

    schedule = []
    for row in preflight["rows"]:
        for label in preflight["call_order"]:
            arm, raw_rep = label.rsplit("_", 1)
            schedule.append((row, arm, int(raw_rep)))
    if len(schedule) != 28:
        raise RuntimeError("S206 schedule must contain exactly 28 calls")
    # One UTF-8 byte is an intentionally conservative upper bound for one input
    # token. Reject the whole run before its first call if that bound plus every
    # maximum output could reach the sealed ceiling.
    worst_case = sum(
        (
            row["request_envelopes"][arm]["serialized_bytes"] * PRICE_INPUT
            + row["request_envelopes"][arm]["max_tokens"] * PRICE_OUTPUT
        )
        / 1_000_000
        for row, arm, _rep in schedule
    )
    if worst_case >= float(permit["budget_ceiling_usd"]):
        raise RuntimeError("S206 worst-case spend exceeds the sealed ceiling")

    for row, arm, replicate in schedule:
        call_id = f"{row['qid']}:{arm}:{replicate}"
        expected = row["request_envelopes"][arm]
        actual = capture_envelope(generator, row, arm)
        if actual != expected:
            raise RuntimeError(f"S206 request-envelope drift before {call_id}")
        os.environ["ANSWER_FACET_LEDGER"] = "on" if arm == "treatment" else "off"
        try:
            result = generator.generate_answer(row["question"], row["context"])
            receipt = {
                "call_id": call_id,
                "status": "completed",
                "qid": row["qid"],
                "role": row["role"],
                "arm": arm,
                "replicate": replicate,
                "request_envelope_sha256": actual["sha256"],
                "model": actual["model"],
                "stop_reason": result.get("stop_reason"),
                "input_tokens": result.get("input_tokens"),
                "output_tokens": result.get("output_tokens"),
                "answer_sha256": hashlib.sha256(
                    result["answer"].encode("utf-8")
                ).hexdigest(),
                "answer": result["answer"],
            }
        except Exception as exc:
            receipt = {
                "call_id": call_id,
                "status": "failed_no_retry",
                "qid": row["qid"],
                "role": row["role"],
                "arm": arm,
                "replicate": replicate,
                "request_envelope_sha256": actual["sha256"],
                "error_type": type(exc).__name__,
                "error_sha256": hashlib.sha256(str(exc).encode("utf-8")).hexdigest(),
            }
            _append(receipt)
            raise RuntimeError(f"S206 provider attempt failed at {call_id}; hard stop") from exc
        _append(receipt)
        checkpoints[call_id] = receipt

    rows = [checkpoints[f"{row['qid']}:{arm}:{rep}"] for row, arm, rep in schedule]
    body = {
        "schema": "s206_answer_facet_ab_receipts_v1",
        "status": "COMPLETE",
        "preflight_sha256": file_sha(PREFLIGHT),
        "permit_sha256": file_sha(PERMIT),
        "calls": len(rows),
        "rows": rows,
        "cost": {
            "input_tokens": sum(row.get("input_tokens") or 0 for row in rows),
            "output_tokens": sum(row.get("output_tokens") or 0 for row in rows),
            "estimated_usd": round(sum(_cost(row) for row in rows), 8),
            "pricing_usd_per_million": {
                "input": PRICE_INPUT,
                "output": PRICE_OUTPUT,
            },
        },
    }
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": body["status"], "calls": 28, "cost": body["cost"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
