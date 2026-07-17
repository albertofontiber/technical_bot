#!/usr/bin/env python3
"""Reconcile the frozen S141 synthesis relations against current frozen answers.

This is a measurement audit, not a production mechanism.  It deliberately
reuses the immutable source-bound obligations and validators that defined the
S141 bucket, then reports whether each relation is actually absent, partial,
internally inconsistent, or already covered by the frozen answer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s141_source_bound_technical_obligations import (
    TARGET_KINDS,
    answer_map,
    plan_for,
)
from src.rag.answer_planner import validate_answer_plan


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
S141 = ROOT / "evals/s141_source_bound_technical_obligations_v1.json"
S161 = ROOT / "evals/s161_reconciled_funnel_projection_v1.yaml"
DEFAULT_OUTPUT = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
QIDS = ("cat018", "hp002", "hp011", "hp017")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def _anchor_present(answer: str, anchor: str) -> bool:
    folded_answer = _fold(answer)
    folded_anchor = _fold(anchor)
    aliases = {
        "seis": ("seis", "six", "6"),
        "six": ("seis", "six", "6"),
    }
    if folded_anchor in aliases:
        return any(
            re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded_answer)
            for alias in aliases[folded_anchor]
        )
    compact_answer = re.sub(r"\s+", "", folded_answer)
    compact_anchor = re.sub(r"\s+", "", folded_anchor)
    return bool(compact_anchor and compact_anchor in compact_answer)


def _category(
    *, answer: str, kind: str, covered: bool, present_anchors: int, total_anchors: int
) -> str:
    if covered:
        return "fully_covered"
    if kind == "option_family_cardinality" and present_anchors == total_anchors:
        return "internal_cardinality_contradiction"
    if present_anchors:
        return "partial_relation"
    return "relation_omitted"


def run() -> dict[str, Any]:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in freeze["rows"]}
    answers = answer_map()
    rows: list[dict[str, Any]] = []

    for qid in QIDS:
        answer = answers[qid]
        obligations = [
            item for item in plan_for(frozen[qid]) if item.kind in TARGET_KINDS[qid]
        ]
        validation = validate_answer_plan(answer, obligations)
        validation_by_id = {
            str(row["obligation_id"]): row for row in validation["rows"]
        }
        for obligation in obligations:
            validated = validation_by_id[obligation.obligation_id]
            anchors = list(obligation.required_anchors)
            present = [anchor for anchor in anchors if _anchor_present(answer, anchor)]
            missing = [anchor for anchor in anchors if anchor not in present]
            covered = bool(validated["covered"])
            rows.append(
                {
                    "qid": qid,
                    "kind": obligation.kind,
                    "obligation_id": obligation.obligation_id,
                    "candidate_id": obligation.candidate_id,
                    "fragment_number": obligation.fragment_number,
                    "source_statement_sha256": hashlib.sha256(
                        obligation.statement.encode("utf-8")
                    ).hexdigest(),
                    "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
                    "covered": covered,
                    "diagnostic_category": _category(
                        answer=answer,
                        kind=obligation.kind,
                        covered=covered,
                        present_anchors=len(present),
                        total_anchors=len(anchors),
                    ),
                    "present_required_anchors": present,
                    "missing_required_anchors": missing,
                    "source_fragment_cited": bool(
                        re.search(rf"\[F{obligation.fragment_number}\]", answer)
                    ),
                }
            )

    covered = [row for row in rows if row["covered"]]
    missing = [row for row in rows if not row["covered"]]
    categories = {
        category: sum(row["diagnostic_category"] == category for row in rows)
        for category in (
            "fully_covered",
            "partial_relation",
            "relation_omitted",
            "internal_cardinality_contradiction",
        )
    }
    body: dict[str, Any] = {
        "schema_version": "s163_synthesis_residual_audit_v1",
        "instrument": "s163_frozen_answer_relation_reconciliation",
        "status": "LOCAL_MEASUREMENT_RECONCILIATION_COMPLETE",
        "authority": {
            "contexts": {
                "path": str(FREEZE.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _file_sha(FREEZE),
            },
            "obligation_audit": {
                "path": str(S141.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _file_sha(S141),
            },
            "prior_funnel": {
                "path": str(S161.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _file_sha(S161),
            },
        },
        "population": {
            "questions": len(QIDS),
            "relations": len(rows),
            "covered_in_current_frozen_answers": len(covered),
            "genuine_synthesis_residuals": len(missing),
            "diagnostic_categories": categories,
        },
        "rows": rows,
        "measurement_bridge": {
            "stale_synthesis_carry_reclassified_to_ok": len(covered),
            "stale_rows": [
                {"qid": row["qid"], "kind": row["kind"]} for row in covered
            ],
            "bot_improvement_credit": 0,
            "measurement_reconciliation_credit": len(covered),
            "reason": (
                "The exact frozen answer already entails the relation; this corrects "
                "the diagnostic funnel but is not a new bot behavior."
            ),
        },
        "diagnostic_projection": {
            "denominator": 157,
            "stage_histogram": {
                "OK": 139 + len(covered),
                "retrieval-miss": 4,
                "document-extraction-hold": 1,
                "synthesis-miss": len(missing),
            },
            "ok_rate_percent": round((139 + len(covered)) / 157 * 100, 2),
            "target_ok_for_95_percent": 150,
            "gap_to_95_percent": 150 - (139 + len(covered)),
        },
        "decision": {
            "official_atomic_kpi": None,
            "production_change": False,
            "facts_moved_to_ok_due_to_bot_change": 0,
            "next": "ATTACK_12_GENUINE_SYNTHESIS_RESIDUALS_BY_FAILURE_TOPOLOGY",
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_calls": 0,
            "usd": 0,
        },
    }
    return {**body, "result_sha256": _stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run()
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "covered": result["population"]["covered_in_current_frozen_answers"],
                "residuals": result["population"]["genuine_synthesis_residuals"],
                "categories": result["population"]["diagnostic_categories"],
                "cost_usd": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
