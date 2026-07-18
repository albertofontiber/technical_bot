#!/usr/bin/env python3
"""Adjudicate the bounded S252 adversarial duo and close before generation."""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
TARGET_TS = "2026-07-18T19:42:36"


def main() -> int:
    raw = LOG.read_bytes()
    lines = raw.splitlines(keepends=True)
    if not lines:
        raise RuntimeError("adversarial review log is empty")
    ending = b"\r\n" if lines[-1].endswith(b"\r\n") else (
        b"\n" if lines[-1].endswith(b"\n") else b""
    )
    payload = lines[-1][:-len(ending)] if ending else lines[-1]
    row = json.loads(payload.decode("utf-8"))
    if row.get("ts") != TARGET_TS:
        raise RuntimeError("S252 review is not the final log entry")
    if row.get("duo_status") == "complete_adjudicated_no_pass":
        print("S252_ADJUDICATION_ALREADY_APPLIED")
        return 0
    if row.get("duo_status") != "complete_pending_adjudication":
        raise RuntimeError("S252 duo is not ready for adjudication")

    row.update(
        duo_status="complete_adjudicated_no_pass",
        findings=6,
        confirmed=6,
        false_pos=1,
        severity_max="critical",
        verdict_notes=(
            "NO_PASS_DUAL_FRONTIER. Sol principal found four confirmed defects, "
            "including two critical blockers: generation did not hash-freeze all "
            "dynamic prompt dependencies, and the mandatory semantic review omitted "
            "control answers even though the measured gain compares control with "
            "treatment. Its retry-ledger and self-contained-objective findings were "
            "also confirmed. Fable independently confirmed the retry metadata defect "
            "and added two valid auditability findings: an unbound mutable prereg root "
            "and undeclared treatment-only citation scope. Its zero-retry monkeypatch "
            "observation duplicates the retry defect; the tautological equality check "
            "is not a functional defect and is counted as one false positive. Sol "
            "exhausted the fixed 30-tool-call allowance, so future repository-wide "
            "reviews must use an adaptive budget rather than treating 30 as a hard "
            "governance limit. No S252 generation was authorized and no S253 "
            "correction loop will be opened."
        ),
    )
    row["fable_review"].update(
        findings=5,
        confirmed=4,
        false_pos=1,
        severity_max="medium",
    )
    lines[-1] = (
        json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + ending
    )
    temporary = LOG.with_name(".adversarial_review_log.s252.tmp")
    try:
        temporary.write_bytes(b"".join(lines))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S252_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
