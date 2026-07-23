#!/usr/bin/env python3
"""Adjudicate the four bounded S277 document-local review duos in place."""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
ADJUDICATIONS = {
    "2026-07-21T22:59:27": {
        "findings": 11,
        "confirmed": 9,
        "false_pos": 2,
        "severity_max": "critical",
        "notes": (
            "ADJUDICATED_ADDRESSED. Confirmed findings drove the atomic one-GET "
            "snapshot, independently rejected scopes, complete bounded lifecycle "
            "hydration and explicit ES/Markdown-row scope. The generic-record and "
            "ES/EN readings exceeded the deliberately narrowed v1 contract. The "
            "terminal v2 mechanism now uses a canonical governed lineage UUID, "
            "exact active blob authority and fail-closed lifecycle checks."
        ),
    },
    "2026-07-21T23:33:33": {
        "findings": 10,
        "confirmed": 8,
        "false_pos": 2,
        "severity_max": "critical",
        "notes": (
            "ADJUDICATED_ADDRESSED. Family and candidate reads now use limit+1 "
            "sentinels, scope-ranked overflow, explicit combined cap 64 and accurate "
            "overflow traces. Migration history was reconciled without repair, and "
            "the two v2 migrations were dry-run then normally applied. Client timeout "
            "is described as client-side rather than server cancellation; malformed "
            "tsquery and blob rejection are exercised live."
        ),
    },
    "2026-07-22T00:09:18": {
        "findings": 9,
        "confirmed": 8,
        "false_pos": 1,
        "severity_max": "medium",
        "notes": (
            "ADJUDICATED_ADDRESSED. Candidate identity is overwritten from the active "
            "document authority and no legacy chunk label is a membership gate. The "
            "probe derives exercised project modules from sys.modules, separately "
            "hashes integration/config surfaces, records provider import/load evidence, "
            "blocks mutating verbs, includes live SQL negative controls and cites a "
            "durable migration receipt. The Markdown claim is narrowed to one complete "
            "pipe row with an immediate separator."
        ),
    },
    "2026-07-22T01:01:29": {
        "findings": 5,
        "confirmed": 5,
        "false_pos": 0,
        "severity_max": "critical",
        "notes": (
            "ADJUDICATED_ADDRESSED. Exact legacy labels are no longer positive family "
            "membership: document_revision_lineages plus revision_lineage_id provide "
            "the sole governed key, with one active row per lineage and NULL/unverified "
            "fail-closed. The selector ceiling is aligned to 64 with an explicit "
            "combined-overflow status and tests for 32+32/40+40/per-scope overflow. "
            "Packet framing now reports applicability and the immediate-line rule. "
            "Live receipt is RECONCILED 7/7 and probe v2 is GO_MECHANISM 22/22."
        ),
    },
}


def main() -> int:
    raw = LOG.read_bytes()
    lines = raw.splitlines(keepends=True)
    seen: set[str] = set()
    changed = False
    output: list[bytes] = []
    for line in lines:
        ending = b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
        payload = line[: -len(ending)] if ending else line
        row = json.loads(payload.decode("utf-8"))
        timestamp = str(row.get("ts") or "")
        adjudication = ADJUDICATIONS.get(timestamp)
        if adjudication is None:
            output.append(line)
            continue
        seen.add(timestamp)
        if row.get("duo_status") == "complete_adjudicated":
            output.append(line)
            continue
        if row.get("duo_status") != "complete_pending_adjudication":
            raise RuntimeError(f"review {timestamp} is not pending adjudication")
        row.update(
            duo_status="complete_adjudicated",
            findings=adjudication["findings"],
            confirmed=adjudication["confirmed"],
            false_pos=adjudication["false_pos"],
            severity_max=adjudication["severity_max"],
            verdict_notes=adjudication["notes"],
        )
        fable = row.get("fable_review")
        if not isinstance(fable, dict) or fable.get("status") not in {
            "completed_pending_adjudication",
            "completed_adjudicated",
        }:
            raise RuntimeError(f"review {timestamp} has no adjudicable Fable result")
        fable["status"] = "completed_adjudicated"
        changed = True
        output.append(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            + ending
        )
    if seen != set(ADJUDICATIONS):
        raise RuntimeError(f"missing review rows: {sorted(set(ADJUDICATIONS) - seen)}")
    if not changed:
        print("S277_DOCUMENT_LOCAL_ADJUDICATION_ALREADY_APPLIED")
        return 0
    temporary = LOG.with_name(".adversarial_review_log.s277_document_local.tmp")
    try:
        temporary.write_bytes(b"".join(output))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S277_DOCUMENT_LOCAL_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
