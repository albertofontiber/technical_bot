#!/usr/bin/env python3
"""Apply the verified S247 duo adjudication without rewriting prior JSONL bytes."""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
TARGET_TS = "2026-07-18T18:41:09"


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
        raise RuntimeError("S247 review is not the final log entry")
    if row.get("duo_status") == "complete_adjudicated_no_pass":
        print("S247_ADJUDICATION_ALREADY_APPLIED")
        return 0
    if row.get("duo_status") != "complete_pending_adjudication":
        raise RuntimeError("S247 duo is not ready for adjudication")
    row.update(
        duo_status="complete_adjudicated_no_pass",
        findings=10,
        confirmed=10,
        false_pos=0,
        severity_max="critical",
        verdict_notes=(
            "NO_PASS_DUAL_FRONTIER. All 10 actionable findings confirmed. S175 "
            "already tested the same compact source-bound policy on S173/S171 "
            "and measured 26->23 points, 6->4 complete questions, 3 regressions; "
            "S247 would be prohibited same-cohort rewording, while its compiler "
            "routes were not exercised. Additional confirmed gaps: cross-brand "
            "short-circuit is narrow; conflict precedence differs by revision/region; "
            "guided is not enforced S122; 2-of-2 vs 0-of-2 hides directional "
            "regressions; matrix/calendar policy and ambiguity routing were "
            "unvalidated; control did not pin shipped fidelity. Closed before "
            "implementation/calls."
        ),
    )
    row["fable_review"].update(
        findings=4,
        confirmed=4,
        false_pos=0,
        severity_max="critical",
    )
    lines[-1] = (
        json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + ending
    )
    temporary = LOG.with_name(".adversarial_review_log.s247.tmp")
    try:
        temporary.write_bytes(b"".join(lines))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S247_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
