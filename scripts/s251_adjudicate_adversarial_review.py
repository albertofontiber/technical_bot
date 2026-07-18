#!/usr/bin/env python3
"""Adjudicate the completed-but-invalid S251 adversarial duo."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
TARGET_TS = "2026-07-18T19:27:06"


def main() -> int:
    raw = LOG.read_bytes()
    lines = raw.splitlines(keepends=True)
    ending = b"\r\n" if lines[-1].endswith(b"\r\n") else (
        b"\n" if lines[-1].endswith(b"\n") else b""
    )
    payload = lines[-1][:-len(ending)] if ending else lines[-1]
    row = json.loads(payload.decode("utf-8"))
    if row.get("ts") != TARGET_TS:
        raise RuntimeError("S251 review is not the final log entry")
    if row.get("duo_status") == "complete_adjudicated_no_pass":
        print("S251_ADJUDICATION_ALREADY_APPLIED")
        return 0
    if row.get("duo_status") != "complete_pending_adjudication":
        raise RuntimeError("S251 duo is not ready for adjudication")
    row.update(
        duo_status="complete_adjudicated_no_pass",
        findings=5,
        confirmed=5,
        false_pos=0,
        severity_max="critical",
        verdict_notes=(
            "NO_PASS. Sol principal returned five confirmed findings, including a "
            "critical freeze gap between generation and scoring: the scorer did not "
            "verify the score packet, its own bytes or imported evaluator modules "
            "against a post-generation permit. It also omitted exact two-replicate "
            "validation, full-answer hallucination review, accurate treatment-package "
            "attribution and transport-billing caveats. Fable completed at the provider "
            "but returned only an intention to use an unavailable tool and no review "
            "findings; classify that receipt as invalid/incomplete, not unavailable. "
            "No S251 generation was authorized."
        ),
    )
    row["fable_review"].update(
        status="completed_invalid_no_review",
        findings=0,
        confirmed=0,
        false_pos=0,
        severity_max=None,
    )
    lines[-1] = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + ending
    temporary = LOG.with_name(".adversarial_review_log.s251.tmp")
    try:
        temporary.write_bytes(b"".join(lines))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S251_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

