#!/usr/bin/env python3
"""Run the single versioned S138 recovery after a pre-response OpenAI 520."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s135_representative_chunks_shadow as files
from scripts import s138_symmetric_semantic_mrr as s138


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECOVERY_PERMIT = ROOT / "evals/s138_openai_520_recovery_execution_permit_v2.yaml"
FAILURE_OUTPUT = ROOT / "evals/s138_openai_520_recovery_failure_v2.json"


class RecoveryFailure(RuntimeError):
    pass


def validate_recovery_permit(permit: dict[str, Any], *, root: Path = ROOT) -> None:
    if permit.get("status") != "EXECUTION_GO_ONE_LOGICAL_RETRY":
        raise RecoveryFailure("S138 recovery permit is not GO")
    for name in (
        "design",
        "incident_receipt",
        "s138_preregistration",
        "s138_v1_permit",
        "s138_v1_runner",
        "recovery_runner",
        "recovery_tests",
        "packet",
        "mapping",
    ):
        spec = permit[name]
        if files.file_sha(root / spec["path"]) != spec["sha256"]:
            raise RecoveryFailure(f"S138 recovery artifact drift: {name}")


def require_clean_resume(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    names = [
        "sol_response",
        "fable_q1",
        "fable_q2",
        "fable_q3",
        "fable_combined",
        "arbitration_response",
        "aggregate",
    ]
    present = [name for name in names if (root / prereg["execution"][name]).exists()]
    if present:
        raise RecoveryFailure(f"S138 recovery refuses partial/completed outputs: {present}")


def exception_receipt(exc: Exception) -> dict[str, Any]:
    return {
        "instrument": "s138_openai_520_recovery_failure_v2",
        "status": "RECOVERY_FAILED_NO_FURTHER_RETRY_AUTHORIZED",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "exception_type": type(exc).__name__,
        "http_status": getattr(exc, "status_code", None),
        "request_id": getattr(exc, "request_id", None),
        "message": str(exc),
        "authorization": {
            "further_retry": False,
            "production": False,
            "deploy": False,
            "migration_apply": False,
            "facts_moved_to_ok": 0,
        },
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--permit", type=Path, default=DEFAULT_RECOVERY_PERMIT)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--confirm-paid-recovery", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid_recovery:
        raise RecoveryFailure("S138 recovery requires --confirm-paid-recovery")
    permit_path = args.permit if args.permit.is_absolute() else ROOT / args.permit
    permit = files.load_yaml(permit_path)
    validate_recovery_permit(permit)
    prereg = files.load_yaml(ROOT / permit["s138_preregistration"]["path"])
    v1_permit = files.load_yaml(ROOT / permit["s138_v1_permit"]["path"])
    require_clean_resume(prereg)
    try:
        result = s138.execute_paid(prereg, v1_permit, args.env_file.resolve())
    except Exception as exc:
        write_json(FAILURE_OUTPUT, exception_receipt(exc))
        raise
    return 0 if result["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
