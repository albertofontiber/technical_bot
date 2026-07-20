#!/usr/bin/env python3
"""Apply the verified S276 duo adjudication without rewriting prior JSONL bytes."""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
TARGET_TS = "2026-07-20T09:29:35"


def main() -> int:
    raw = LOG.read_bytes()
    lines = raw.splitlines(keepends=True)
    ending = (
        b"\r\n"
        if lines[-1].endswith(b"\r\n")
        else b"\n"
        if lines[-1].endswith(b"\n")
        else b""
    )
    payload = lines[-1][: -len(ending)] if ending else lines[-1]
    row = json.loads(payload.decode("utf-8"))
    if row.get("ts") != TARGET_TS:
        raise RuntimeError("S276 review is not the final log entry")
    if row.get("duo_status") == "complete_adjudicated_no_pass":
        print("S276_ADJUDICATION_ALREADY_APPLIED")
        return 0
    if row.get("duo_status") != "complete_pending_adjudication":
        raise RuntimeError("S276 duo is not ready for adjudication")

    row.update(
        duo_status="complete_adjudicated_no_pass",
        findings=8,
        confirmed=8,
        false_pos=0,
        severity_max="medium",
        verdict_notes=(
            "NO_PASS_DUAL_FRONTIER_WITH_DECISIONS_UNCHANGED. Eight unique findings "
            "were confirmed from nine raw observations (Fable's prior-cohort hash "
            "finding is the concrete instance of Sol's broader freeze finding): the "
            "full freeze chronology is not attested; 67/67 is parser self-consistency, "
            "not independent grammar recall; sampled_docs does not count non-empty "
            "fetches; boundary controls are synthetic; repair is a second writer; the "
            "RGPD lifecycle was incomplete; a unique ingress key is not exactly-once "
            "delivery; and the measured-levers heading mixed measured, design-closed "
            "and NOT_MEASURED lines. The closeout and architecture assessment were "
            "corrected under evals/s276_duo_adjudication_v1.yaml. The offline verdict "
            "remains NO_GO, with zero funnel credit, no paid A/B and no runtime/schema "
            "build authorization. Reuse requires a fresh seed and a new reviewed freeze."
        ),
    )
    row["fable_review"].update(
        findings=3,
        confirmed=3,
        false_pos=0,
        severity_max="medium",
    )
    lines[-1] = (
        json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + ending
    )
    temporary = LOG.with_name(".adversarial_review_log.s276.tmp")
    try:
        temporary.write_bytes(b"".join(lines))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S276_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
