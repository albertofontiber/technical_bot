#!/usr/bin/env python3
"""Recover a sealed S142 cohort using exact whitespace-only source alignment."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s142_build_independent_obligation_cohort as builder


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "evals/s142_independent_source_packet_v1.json"
DEFAULT_RAW = ROOT / "evals/s142_haiku_raw_response_v3.json"
DEFAULT_PREREG = ROOT / "evals/s142_sealed_cohort_offline_recovery_prereg_v1.yaml"
DEFAULT_OUT = ROOT / "evals/s142_independent_obligation_cohort_v1.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def exact_whitespace_alignment(quote: str, source: str) -> str | None:
    if quote in source:
        return quote
    tokens = quote.split()
    if not tokens:
        return None
    pattern = r"\s+".join(re.escape(token) for token in tokens)
    matches = list(re.finditer(pattern, source))
    if len(matches) != 1:
        return None
    match = matches[0]
    return source[match.start() : match.end()]


def validate_freeze(prereg_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_OFFLINE_RECOVERY":
        raise RuntimeError("S142 offline recovery preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S142 offline recovery input drift: {label}")
    return prereg


def recover(packet: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("source_packet_sha256") != packet.get("packet_sha256"):
        raise RuntimeError("S142 raw response/packet mismatch")
    labels = json.loads(raw["raw_text"])
    source = {row["item_id"]: row["excerpt"] for row in packet["items"]}
    recovered_rows = []
    exact_before = 0
    whitespace_repaired = 0
    dropped = 0
    for row in labels.get("items", []):
        item_id = row.get("item_id")
        if item_id not in source:
            raise RuntimeError(f"unknown S142 item: {item_id}")
        claims = []
        for claim in row.get("claims", []):
            quote = str(claim.get("exact_quote") or "")
            if quote in source[item_id]:
                aligned = quote
                exact_before += 1
            else:
                aligned = exact_whitespace_alignment(quote, source[item_id])
                if aligned is None:
                    dropped += 1
                    continue
                whitespace_repaired += 1
            claims.append({"claim": str(claim.get("claim") or ""), "exact_quote": aligned})
        claims = claims[:5]
        eligible = bool(row.get("eligible")) and len(claims) >= 2
        recovered_rows.append(
            {
                "item_id": item_id,
                "eligible": eligible,
                "question": str(row.get("question") or "") if eligible else "",
                "claims": claims if eligible else [],
            }
        )
    recovered_labels = {"items": recovered_rows}
    builder._validate_labels(recovered_labels, packet)
    usage = raw.get("usage") or {}
    conservative_cost = (
        usage.get("input_tokens", 0) * 2 + usage.get("output_tokens", 0) * 10
    ) / 1_000_000
    body = {
        "instrument": "s142_independent_obligation_cohort_v1",
        "status": "SEALED_VALIDATED_OFFLINE_WHITESPACE_RECOVERY",
        "source_packet_sha256": packet["packet_sha256"],
        "model": raw.get("model"),
        "response_id": raw.get("response_id"),
        "usage": usage,
        "conservative_cost_usd": round(conservative_cost, 8),
        "recovery": {
            "contract": "exact_unique_whitespace_alignment_v1",
            "exact_quotes_before": exact_before,
            "whitespace_repaired_quotes": whitespace_repaired,
            "dropped_unalignable_claims": dropped,
            "new_model_calls": 0,
        },
        "items": recovered_rows,
    }
    return {**body, "cohort_sha256": stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    validate_freeze(args.prereg)
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    cohort = recover(packet, raw)
    args.out.write_text(json.dumps(cohort, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": cohort["status"],
        "eligible": sum(row["eligible"] for row in cohort["items"]),
        "claims": sum(len(row["claims"]) for row in cohort["items"]),
        "recovery": cohort["recovery"],
        "conservative_cost_usd": cohort["conservative_cost_usd"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
