#!/usr/bin/env python3
"""Apply the verified S276 corrections-duo adjudication atomically."""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
TARGET_TS = "2026-07-20T10:06:50"


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
        raise RuntimeError("S276 corrections review is not the final log entry")
    if row.get("duo_status") == "complete_adjudicated_no_pass":
        print("S276_CORRECTIONS_ADJUDICATION_ALREADY_APPLIED")
        return 0
    if row.get("duo_status") != "complete_pending_adjudication":
        raise RuntimeError("S276 corrections duo is not ready for adjudication")

    row.update(
        duo_status="complete_adjudicated_no_pass",
        findings=8,
        confirmed=8,
        false_pos=0,
        severity_max="critical",
        verdict_notes=(
            "NO_PASS_CORRECTIONS_DUO. Eight unique findings were confirmed from ten "
            "raw observations. The empty-final recovery re-injected an invalid empty "
            "assistant message (live API check: HTTP 400); the final validator allowed "
            "tool_use; tool schemas were absent from the conservative bound; the "
            "blueprint lacked fencing/outbox uniqueness; prior duo tally/brief paths "
            "were not denied; non-object tool inputs diverged between runner and "
            "validator; out-of-position recovery lacked a test; and the physical trace "
            "was overframed as provider attestation. Fixes and live contract checks are "
            "recorded in evals/s276_corrections_duo_adjudication_v1.yaml. The subject "
            "mistakenly included a prior duo adjudication, so this row is not claimed as "
            "a clean independent PASS. No product runtime/schema/build was authorized; "
            "the seed-278 NO-GO and directional architecture decision are unchanged."
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
    temporary = LOG.with_name(".adversarial_review_log.s276-corrections.tmp")
    try:
        temporary.write_bytes(b"".join(lines))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S276_CORRECTIONS_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
