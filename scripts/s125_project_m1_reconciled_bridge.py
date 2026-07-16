#!/usr/bin/env python3
"""Project the S125 M1 migration onto the prior hybrid diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PREREG_PATH = ROOT / "evals" / "s125_m1_reconciled_bridge_prereg_v1.yaml"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def frozen_input(receipt: dict[str, Any], label: str) -> Path:
    path = (ROOT / receipt["path"]).resolve()
    if not path.is_file() or file_sha256(path) != receipt["sha256"]:
        raise ValueError(f"frozen {label} mismatch")
    return path


def build_projection(
    prereg: dict[str, Any],
    prior_gate: dict[str, Any],
    replay: dict[str, Any],
    atomic_bridge: dict[str, Any],
) -> dict[str, Any]:
    contract = prereg["projection_contract"]
    receipts = prereg["frozen_inputs"]
    if replay.get("payload_sha256") != receipts["migrated_cohort_replay"]["payload_sha256"]:
        raise ValueError("migrated replay payload mismatch")
    replay_body = dict(replay)
    declared_replay_payload = replay_body.pop("payload_sha256", None)
    if declared_replay_payload != canonical_sha256(replay_body):
        raise ValueError("migrated replay canonical payload is invalid")

    prior = prior_gate["reconciled_hybrid_diagnostic"]
    prior_hist = Counter(prior["stage_histogram"])
    removed = Counter(contract["remove_bucket"])
    if any(prior_hist[bucket] != count for bucket, count in removed.items()):
        raise ValueError("prior hold population mismatch")

    replay_summary = replay["summary"]
    core_rows = [row for row in replay.get("rows") or [] if row.get("content_eligible") is True]
    supplementary_rows = [row for row in replay.get("rows") or [] if row.get("content_eligible") is False]
    recomputed_core_hist = dict(sorted(Counter(row["stage_bucket"] for row in core_rows).items()))
    recomputed_supp_hist = dict(sorted(Counter(row["stage_bucket"] for row in supplementary_rows).items()))
    if (
        replay_summary["content_claim_count"] != len(core_rows)
        or replay_summary["supplementary_claim_count"] != len(supplementary_rows)
        or replay_summary["content_stage_histogram"] != recomputed_core_hist
        or replay_summary["supplementary_stage_histogram"] != recomputed_supp_hist
    ):
        raise ValueError("migrated replay summary does not match rows")
    if replay_summary["content_claim_count"] != contract["expected_migrated_content_claims"]:
        raise ValueError("migrated content population mismatch")
    if any(not row["content_eligible"] for row in replay["rows"] if row["stage_bucket"] in {"OK", "synthesis-miss", "synthesis-not-measured"}):
        raise ValueError("supplementary claim leaked into content funnel")

    remaining_carries = atomic_bridge["summary"]["legacy_carries_without_known_m1_blocker"]
    if remaining_carries != contract["expected_remaining_provisional_legacy_carries"]:
        raise ValueError("remaining provisional carry count mismatch")

    projected = prior_hist - removed
    projected.update(replay_summary["content_stage_histogram"])
    projected.pop("known-m1-contract-hold", None)
    projected_hist = dict(sorted(projected.items()))
    projected_total = sum(projected.values())
    expected_total = prior["content_denominator"] - sum(removed.values()) + replay_summary["content_claim_count"]
    if projected_total != expected_total:
        raise ValueError("projected denominator arithmetic mismatch")

    ok_count = projected["OK"]
    not_measured = projected["synthesis-not-measured"]
    measured_denominator = projected_total - not_measured
    result: dict[str, Any] = {
        "schema_version": "s125_m1_reconciled_bridge_v1",
        "instrument": "s125_project_m1_reconciled_bridge",
        "status": "LOCAL_MEASUREMENT_RECONCILIATION_COMPLETE",
        "authority": {
            "preregistration": str(PREREG_PATH.relative_to(ROOT)).replace("\\", "/"),
            "preregistration_sha256": file_sha256(PREREG_PATH),
            "prior_hybrid_gate_sha256": receipts["prior_hybrid_gate"]["sha256"],
            "migrated_cohort_replay_sha256": receipts["migrated_cohort_replay"]["sha256"],
            "atomic_bridge_sha256": receipts["atomic_bridge"]["sha256"],
        },
        "bridge_arithmetic": {
            "prior_content_denominator": prior["content_denominator"],
            "removed_known_hold_parents": sum(removed.values()),
            "added_migrated_core_claims": replay_summary["content_claim_count"],
            "excluded_migrated_supplementary_claims": replay_summary["supplementary_claim_count"],
            "projected_content_denominator": projected_total,
            "formula": f"{prior['content_denominator']} - {sum(removed.values())} + {replay_summary['content_claim_count']} = {projected_total}",
        },
        "provisional_hybrid_diagnostic": {
            "content_denominator": projected_total,
            "stage_histogram": projected_hist,
            "ok_count": ok_count,
            "measured_content_denominator": measured_denominator,
            "measured_ok_rate": ok_count / measured_denominator,
            "all_provisional_content_ok_rate": ok_count / projected_total,
            "provisional_target_ok_for_95_percent": math.ceil(0.95 * projected_total),
            "provisional_gap_to_95_percent": math.ceil(0.95 * projected_total) - ok_count,
        },
        "credit_and_limitations": {
            "facts_moved_to_ok_due_to_bot_change": contract["facts_moved_to_ok_due_to_bot_change"],
            "confirmed_ok_claims_exposed_by_measurement_reconciliation": replay_summary["content_stage_histogram"]["OK"],
            "remaining_provisional_legacy_carries": remaining_carries,
            "official_atomic_content_denominator": None,
            "official_ok_count": None,
            "official_95_percent_claim": None,
            "reason_official_kpi_is_null": "77 other legacy carries still lack completed atomic requiredness adjudication.",
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
    }
    result["payload_sha256"] = canonical_sha256(result)
    return result


def build_from_files() -> dict[str, Any]:
    prereg = load_yaml(PREREG_PATH)
    receipts = prereg["frozen_inputs"]
    prior = load_yaml(frozen_input(receipts["prior_hybrid_gate"], "prior hybrid gate"))
    replay = load_json(frozen_input(receipts["migrated_cohort_replay"], "migrated replay"))
    bridge = load_json(frozen_input(receipts["atomic_bridge"], "atomic bridge"))
    return build_projection(prereg, prior, replay, bridge)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals" / "s125_m1_reconciled_bridge_v1.json",
    )
    args = parser.parse_args()
    result = build_from_files()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["provisional_hybrid_diagnostic"], ensure_ascii=False, sort_keys=True))
    print(f"payload_sha256={result['payload_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
