#!/usr/bin/env python3
"""Zero-call feasibility gate for the S206 generic answer-facet ledger."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s141_source_bound_technical_obligations import answer_map
from src.rag.answer_facets import (
    DEFAULT_CONFIG,
    _load,
    classify_answer_archetype,
    render_answer_facet_ledger,
)
from src.rag.retriever import extract_product_models

FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
RESIDUAL = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
OUT = ROOT / "evals/s206_answer_facet_ledger_feasibility_v1.json"
TARGET_QIDS = ("cat018", "hp002", "hp011", "hp017")

KIND_FACETS = {
    "software_type_cbe_activation": {"input_condition", "output_action"},
    "point_programming_fields": {"navigation_fields"},
    "initial_reference_calibration": {"reference_calibration"},
    "bounded_fault_window": {"thresholds_timing"},
    "maintenance_isolation_prerequisite": {"safety_prerequisites"},
    "extinction_duration_range": {"thresholds_timing"},
    "reset_inhibit_special_state": {"recovery_verification"},
    "option_family_cardinality": {"values_ranges_states"},
    "input_condition_definition": {"input_condition"},
    "output_condition_action": {"output_action"},
    "logic_contradiction_warning": {"warnings_conflicts"},
    "commissioning_rule_verification": {"commissioning_verification"},
}


def _stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _configured_text(payload: dict[str, Any]) -> str:
    return " ".join(
        text
        for spec in payload["archetypes"].values()
        for text in [spec["label"], *(item["text"] for item in spec["checks"])]
    )


def run() -> dict[str, Any]:
    config = _load(str(DEFAULT_CONFIG.resolve()))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    residual = json.loads(RESIDUAL.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in freeze["rows"]}
    baselines = answer_map()

    target_routes = {
        qid: classify_answer_archetype(frozen[qid]["question"])
        for qid in TARGET_QIDS
    }
    target_archetypes = set(target_routes.values())
    all_routes = {
        qid: classify_answer_archetype(row["question"])
        for qid, row in frozen.items()
    }
    guardrails = sorted(
        qid
        for qid, archetype in all_routes.items()
        if qid not in TARGET_QIDS
        and archetype in target_archetypes
        and bool(baselines.get(qid))
    )
    identity_bound = {
        qid: bool(extract_product_models(frozen[qid]["question"]))
        for qid in TARGET_QIDS
    }
    prior_mode = os.environ.get("ANSWER_FACET_LEDGER")
    os.environ["ANSWER_FACET_LEDGER"] = "on"
    try:
        target_ledgers = {
            qid: bool(render_answer_facet_ledger(frozen[qid]["question"]))
            for qid in TARGET_QIDS
        }
        ambiguous_inert = not render_answer_facet_ledger(
            "Después de resetear el panel no vuelve a normal; ¿qué compruebo?"
        )
    finally:
        if prior_mode is None:
            os.environ.pop("ANSWER_FACET_LEDGER", None)
        else:
            os.environ["ANSWER_FACET_LEDGER"] = prior_mode

    residual_rows = [
        row for row in residual["rows"] if not row.get("covered")
    ]
    facet_rows = []
    for row in residual_rows:
        qid = str(row["qid"])
        kind = str(row["kind"])
        archetype = target_routes[qid]
        configured_ids = {
            item["id"] for item in config["archetypes"][archetype]["checks"]
        }
        expected = KIND_FACETS.get(kind, set())
        facet_rows.append(
            {
                "qid": qid,
                "kind": kind,
                "archetype": archetype,
                "required_facet_ids": sorted(expected),
                "covered_by_generic_ontology": bool(expected)
                and expected <= configured_ids,
            }
        )

    configured_text = _configured_text(config)
    forbidden_target_literals = (
        "cat018",
        "hp002",
        "hp011",
        "hp017",
        "AM-8200",
        "ASD535",
        "RP1r",
        "PEARL",
    )
    checks = {
        "runtime_scope_exactly_measured_archetypes": set(config["archetypes"])
        == {"fault_reset_recovery", "program_delay_cause_effect"},
        "all_four_targets_routed": all(target_routes.values()),
        "all_four_targets_identity_bound": all(identity_bound.values()),
        "all_four_targets_receive_ledger": all(target_ledgers.values()),
        "ambiguous_query_is_inert": ambiguous_inert,
        "targets_use_existing_archetypes_only": target_archetypes
        == {"fault_reset_recovery", "program_delay_cause_effect"},
        "all_residual_kinds_mapped": len(facet_rows) == 12
        and all(row["covered_by_generic_ontology"] for row in facet_rows),
        "non_target_same_archetype_guardrails_exist": len(guardrails) >= 2,
        "runtime_ledger_has_no_numeric_values": not re.search(r"\d", configured_text),
        "runtime_ledger_has_no_target_literals": not any(
            literal.casefold() in configured_text.casefold()
            for literal in forbidden_target_literals
        ),
    }
    body: dict[str, Any] = {
        "schema": "s206_answer_facet_ledger_feasibility_v1",
        "status": "GO_LOCAL_FEASIBILITY" if all(checks.values()) else "NO_GO",
        "population": {
            "frozen_questions": len(frozen),
            "target_questions": len(TARGET_QIDS),
            "genuine_residual_relations": len(residual_rows),
            "protected_guardrail_questions": len(guardrails),
        },
        "target_routes": target_routes,
        "target_identity_bound": identity_bound,
        "target_ledgers_enabled": target_ledgers,
        "frozen_route_distribution": dict(
            sorted(
                (
                    (archetype or "(unrouted)", count)
                    for archetype, count in Counter(all_routes.values()).items()
                ),
                key=lambda item: item[0],
            )
        ),
        "protected_guardrail_qids": guardrails,
        "residual_facet_rows": facet_rows,
        "checks": checks,
        "decision": {
            "paid_treatment_authorized": False,
            "next": "BUILD_EXECUTABLE_PREFLIGHT_THEN_RERUN_DUO_REVIEW_ONCE",
            "production": False,
            "facts_moved_to_ok": 0,
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
    result = run()
    OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "target_routes": result["target_routes"],
                "protected_guardrails": result["population"][
                    "protected_guardrail_questions"
                ],
                "residual_facets_covered": sum(
                    row["covered_by_generic_ontology"]
                    for row in result["residual_facet_rows"]
                ),
                "checks": result["checks"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["status"] == "GO_LOCAL_FEASIBILITY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
