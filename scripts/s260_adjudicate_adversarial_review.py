#!/usr/bin/env python3
"""Adjudicate the S260 design duo and close before Terra execution."""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
TARGET_TS = "2026-07-18T20:12:24"


def main() -> int:
    raw = LOG.read_bytes()
    lines = raw.splitlines(keepends=True)
    ending = b"\r\n" if lines[-1].endswith(b"\r\n") else (
        b"\n" if lines[-1].endswith(b"\n") else b""
    )
    payload = lines[-1][:-len(ending)] if ending else lines[-1]
    row = json.loads(payload.decode("utf-8"))
    if row.get("ts") != TARGET_TS:
        raise RuntimeError("S260 review is not the final log entry")
    if row.get("duo_status") == "complete_adjudicated_no_pass":
        print("S260_ADJUDICATION_ALREADY_APPLIED")
        return 0
    if row.get("duo_status") != "complete_pending_adjudication":
        raise RuntimeError("S260 duo is not ready for adjudication")
    row.update(
        duo_status="complete_adjudicated_no_pass",
        findings=9,
        confirmed=9,
        false_pos=0,
        severity_max="critical",
        verdict_notes=(
            "NO_PASS_DUAL_FRONTIER. Sol's five findings are confirmed: S260 "
            "reversed the canonical independent-to-target order, lacked a "
            "contemporary same-model control, did not validate semantic entailment "
            "between claims and cited fragments, allowed conflict omission to pass, "
            "and failed to bind the execution permit used by generation. Fable "
            "independently confirmed target-order leakage and added valid concerns "
            "about target-derived prompt guards, accumulated multiple testing on the "
            "same residuals, lexical-proxy/projection circularity and a citation gate "
            "that is structurally vacuous after local citation derivation. The local "
            "IR and freeze mechanics passed their tests, but cannot make the target "
            "experiment generalizable. Sol exhausted the adaptive 60-read budget and "
            "listed uninspected dependencies. No Terra generation, execution permit "
            "or score permit was authorized; no corrected S260 successor is allowed."
        ),
    )
    row["fable_review"].update(
        findings=5,
        confirmed=5,
        false_pos=0,
        severity_max="critical",
    )
    lines[-1] = (
        json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + ending
    )
    temporary = LOG.with_name(".adversarial_review_log.s260.tmp")
    try:
        temporary.write_bytes(b"".join(lines))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S260_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
