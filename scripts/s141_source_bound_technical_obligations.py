#!/usr/bin/env python3
"""Reproduce the local and independent S141 obligation gates."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag import catalog_resolver
from src.rag.answer_planner import (
    ANSWER_PLANNER_CONTRACT_S141,
    build_answer_plan,
    enforce_answer_contract,
    validate_answer_plan,
)
from src.rag.source_identity_attestation import attach_query_source_identity
from src.rag.technical_obligations import extract_technical_obligations


ROOT = Path(__file__).resolve().parents[1]
DEV_FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
HELDOUT_FREEZE = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
HELDOUT_PREREG = ROOT / "evals/s141_independent_generalization_prereg_v1.yaml"
DEFAULT_OUTPUT = ROOT / "evals/s141_source_bound_technical_obligations_v1.json"

TARGET_KINDS = {
    "cat007": set(),
    "cat018": {"point_programming_fields", "software_type_cbe_activation"},
    "hp002": {
        "maintenance_isolation_prerequisite",
        "initial_reference_calibration",
        "bounded_fault_window",
    },
    "hp011": {
        "default_latched_faults",
        "extinction_duration_range",
        "reset_inhibit_special_state",
    },
    "hp017": {
        "input_condition_definition",
        "output_condition_action",
        "logic_contradiction_warning",
        "commissioning_rule_verification",
        "option_family_cardinality",
    },
}
S141_KINDS = set().union(*TARGET_KINDS.values())
EXPECTED_FACT_COUNTS = {"cat018": 2, "hp002": 3, "hp011": 3, "hp017": 5}


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def validate_heldout_freeze() -> dict[str, Any]:
    prereg = yaml.safe_load(HELDOUT_PREREG.read_text(encoding="utf-8"))
    specs = {
        "heldout_input": prereg["heldout_input"],
        **prereg["frozen_implementation"],
    }
    for label, spec in specs.items():
        path = ROOT / spec["path"]
        if file_sha(path) != spec["sha256"]:
            raise RuntimeError(f"S141 held-out freeze drift: {label}")
    return prereg


def attested(row: dict[str, Any]) -> list[dict[str, Any]]:
    return attach_query_source_identity(
        row["question"],
        row["context"],
        catalog_resolver.resolve_query(row["question"]),
        catalog_commit="s141-frozen-audit",
    )


def plan_for(row: dict[str, Any]):
    return build_answer_plan(
        row["question"],
        attested(row),
        max_obligations=20,
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S141,
    )


def answer_map() -> dict[str, str]:
    output: dict[str, str] = {}
    for name in (
        "s113_full_answer_regression_v1.json",
        "s133_unmeasured_answer_probe_v1.json",
    ):
        payload = json.loads((ROOT / "evals" / name).read_text(encoding="utf-8"))
        output.update(
            {str(row["qid"]): str(row.get("answer") or "") for row in payload["rows"]}
        )
    return output


def obligation_receipt(row: Any, chunk: dict[str, Any]) -> dict[str, Any]:
    content = str(chunk.get("content") or "")
    raw_span = content[row.source_start : row.source_end]
    body = {
        "qid": None,
        "candidate_id": row.candidate_id,
        "source_file": str(chunk.get("source_file") or ""),
        "kind": row.kind,
        "source_start": row.source_start,
        "source_end": row.source_end,
        "raw_span_sha256": hashlib.sha256(raw_span.encode("utf-8")).hexdigest(),
        "statement_sha256": hashlib.sha256(row.statement.encode("utf-8")).hexdigest(),
        "identity_receipt_sha256": row.identity_receipt_sha256 or None,
    }
    return {**body, "receipt_sha256": stable_sha(body)}


def run() -> dict[str, Any]:
    prereg = validate_heldout_freeze()
    dev_payload = json.loads(DEV_FREEZE.read_text(encoding="utf-8"))
    dev = {str(row["qid"]): row for row in dev_payload["rows"]}
    answers = answer_map()

    target_rows = []
    target_emissions = 0
    source_receipts = []
    deterministic = True
    reconstruction_covered = 0
    for qid, expected in TARGET_KINDS.items():
        row = dev[qid]
        chunks = attested(row)
        first = plan_for(row)
        second = plan_for(row)
        deterministic &= [item.to_dict() for item in first] == [item.to_dict() for item in second]
        selected = [item for item in first if item.kind in S141_KINDS]
        emitted = {item.kind for item in selected}
        target_emissions += len(emitted)
        receipts = []
        for item in selected:
            chunk = next(
                chunk for chunk in chunks if str(chunk.get("id") or "") == item.candidate_id
            )
            receipt = obligation_receipt(item, chunk)
            receipt["qid"] = qid
            receipts.append(receipt)
            source_receipts.append(receipt)
        covered = None
        action = None
        if qid in EXPECTED_FACT_COUNTS:
            revised, metadata = enforce_answer_contract(
                row["question"],
                answers[qid],
                first,
                [],
                planner_contract_version=ANSWER_PLANNER_CONTRACT_S141,
            )
            validation = validate_answer_plan(revised, selected)
            covered = validation["covered"]
            reconstruction_covered += validation["covered"]
            action = metadata["action"]
        target_rows.append(
            {
                "qid": qid,
                "expected_kinds": sorted(expected),
                "emitted_kinds": sorted(emitted),
                "exact_match": emitted == expected,
                "source_receipts": receipts,
                "reconstruction_covered": covered,
                "reconstruction_action": action,
            }
        )

    target_qids = set(TARGET_KINDS)
    negative_rows = []
    for qid, row in sorted(dev.items()):
        if qid in target_qids:
            continue
        emitted = sorted(
            item.kind for item in plan_for(row) if item.kind in S141_KINDS
        )
        negative_rows.append({"qid": qid, "emitted_kinds": emitted})

    heldout = json.loads(HELDOUT_FREEZE.read_text(encoding="utf-8"))
    heldout_rows = []
    heldout_emissions = 0
    for selected in heldout["chosen"]:
        chunk = heldout["source_rows"][selected["chunk_id"]]
        first = extract_technical_obligations(selected["question"], [(1, chunk)])
        second = extract_technical_obligations(selected["question"], [(1, chunk)])
        deterministic &= first == second
        heldout_emissions += len(first)
        heldout_rows.append(
            {
                "manufacturer": selected["manufacturer"],
                "product_model": selected["product_model"],
                "chunk_id": selected["chunk_id"],
                "question_sha256": hashlib.sha256(
                    selected["question"].encode("utf-8")
                ).hexdigest(),
                "emitted_kinds": [item.kind for item in first],
            }
        )

    exact_source_receipts = all(
        receipt["raw_span_sha256"] and receipt["statement_sha256"]
        for receipt in source_receipts
    )
    target_exact = all(row["exact_match"] for row in target_rows)
    negatives_clean = all(not row["emitted_kinds"] for row in negative_rows)
    local_go = (
        target_exact
        and target_emissions == 13
        and reconstruction_covered == 13
        and exact_source_receipts
        and negatives_clean
        and deterministic
    )
    positive_generalization = heldout_emissions > 0
    return {
        "instrument": "s141_source_bound_technical_obligations_v1",
        "status": (
            "LOCAL_GO_INDEPENDENT_POSITIVE_INCONCLUSIVE"
            if local_go and not positive_generalization
            else "GO" if local_go and positive_generalization else "NO_GO"
        ),
        "inputs": {
            "development_freeze": {
                "path": str(DEV_FREEZE.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha(DEV_FREEZE),
            },
            "heldout_prereg": {
                "path": str(HELDOUT_PREREG.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha(HELDOUT_PREREG),
            },
            "heldout_freeze_sha256": prereg["heldout_input"]["sha256"],
        },
        "development": {
            "target_facts": 18,
            "source_incomplete_rejections": 5,
            "served_relation_targets": 13,
            "emitted_relations": target_emissions,
            "source_receipt_rate": 1.0 if exact_source_receipts else 0.0,
            "reconstruction_covered": reconstruction_covered,
            "target_rows": target_rows,
        },
        "negative_controls": {
            "questions": len(negative_rows),
            "acceptances": sum(bool(row["emitted_kinds"]) for row in negative_rows),
            "rows": negative_rows,
        },
        "independent_generalization": {
            "questions": len(heldout_rows),
            "manufacturers": len({row["manufacturer"] for row in heldout_rows}),
            "emitting_questions": sum(bool(row["emitted_kinds"]) for row in heldout_rows),
            "emitted_relations": heldout_emissions,
            "precision": None,
            "positive_gate": "PASS" if positive_generalization else "INCONCLUSIVE",
            "rows": heldout_rows,
        },
        "checks": {
            "local_target_exact": target_exact,
            "source_receipts_complete": exact_source_receipts,
            "negative_controls_clean": negatives_clean,
            "deterministic_two_runs": deterministic,
            "positive_generalization_observed": positive_generalization,
        },
        "decision": {
            "local_candidate": "GO" if local_go else "NO_GO",
            "paid_answer_probe": "NO_GO_UNTIL_POSITIVE_GENERALIZATION",
            "production": "NO_GO",
            "facts_moved_to_ok": 0,
            "next": "VERSIONED_GENERALIZATION_ITERATION_WITH_FRESH_HELDOUT",
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_calls": 0,
            "usd": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run()
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"],
        "target_emissions": result["development"]["emitted_relations"],
        "negative_acceptances": result["negative_controls"]["acceptances"],
        "heldout_emissions": result["independent_generalization"]["emitted_relations"],
        "cost_usd": result["cost"]["usd"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
