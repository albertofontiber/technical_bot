#!/usr/bin/env python3
"""Bind the unchanged S198 semantic engine to S199's fresh population and outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import s198_point_first_scope_gate as engine
from scripts.s165_answer_archetype_ledger import stable_sha


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = engine.DEFAULT_ENV
SOURCE = ROOT / "evals/s199_restored_margin_source_packet_v1.json"
DEFAULT_PREREG = ROOT / "evals/s199_point_first_replay_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s199_point_first_replay_execution_permit_v1.yaml"
DEFAULT_LOCK = ROOT / "evals/s199_point_first_replay_execution_lock_v1.json"
DEFAULT_POINT_AUTHOR_PREPAID = ROOT / "evals/s199_point_author_prepaid_v1.json"
DEFAULT_POINT_AUTHOR_RECEIPTS = ROOT / "evals/s199_point_author_receipts_v1.json"
DEFAULT_POINT_SCREEN_PREPAID = ROOT / "evals/s199_point_screen_prepaid_v1.json"
DEFAULT_POINT_SCREEN_RECEIPTS = ROOT / "evals/s199_point_screen_receipts_v1.json"
DEFAULT_QUESTION_WRITER_PREPAID = ROOT / "evals/s199_question_writer_prepaid_v1.json"
DEFAULT_QUESTION_WRITER_RECEIPTS = ROOT / "evals/s199_question_writer_receipts_v1.json"
DEFAULT_QUESTION_SCREEN_PREPAID = ROOT / "evals/s199_question_screen_prepaid_v1.json"
DEFAULT_QUESTION_SCREEN_RECEIPTS = ROOT / "evals/s199_question_screen_receipts_v1.json"
DEFAULT_COHORT = ROOT / "evals/s199_point_first_replay_screened_cohort_v1.json"
DEFAULT_RESULT = ROOT / "evals/s199_point_first_replay_gate_v1.json"

OUTPUT_PATHS = (
    DEFAULT_LOCK,
    DEFAULT_POINT_AUTHOR_PREPAID,
    DEFAULT_POINT_AUTHOR_RECEIPTS,
    DEFAULT_POINT_SCREEN_PREPAID,
    DEFAULT_POINT_SCREEN_RECEIPTS,
    DEFAULT_QUESTION_WRITER_PREPAID,
    DEFAULT_QUESTION_WRITER_RECEIPTS,
    DEFAULT_QUESTION_SCREEN_PREPAID,
    DEFAULT_QUESTION_SCREEN_RECEIPTS,
    DEFAULT_COHORT,
    DEFAULT_RESULT,
)

EXPECTED_EXECUTION = {
    **engine.EXPECTED_EXECUTION,
    "point_author_calls_max": 14,
    "point_screen_calls_max": 14,
    "question_writer_calls_max": 14,
    "question_screen_calls_max": 14,
    "paid_calls_max": 56,
    "provider_preflight_requests_max": 56,
    "provider_requests_max": 112,
}
EXPECTED_OUTPUTS = {
    "execution_lock": "evals/s199_point_first_replay_execution_lock_v1.json",
    "point_author_prepaid": "evals/s199_point_author_prepaid_v1.json",
    "point_author_receipts": "evals/s199_point_author_receipts_v1.json",
    "point_screen_prepaid": "evals/s199_point_screen_prepaid_v1.json",
    "point_screen_receipts": "evals/s199_point_screen_receipts_v1.json",
    "question_writer_prepaid": "evals/s199_question_writer_prepaid_v1.json",
    "question_writer_receipts": "evals/s199_question_writer_receipts_v1.json",
    "question_screen_prepaid": "evals/s199_question_screen_prepaid_v1.json",
    "question_screen_receipts": "evals/s199_question_screen_receipts_v1.json",
    "screened_cohort": "evals/s199_point_first_replay_screened_cohort_v1.json",
    "result": "evals/s199_point_first_replay_gate_v1.json",
}
EXPECTED_FORBIDDEN = {
    "retry_repair_or_rebuild_same_source_cohort",
    "change_s198_semantic_engine_schema_prompt_facet_or_threshold",
    "use_s198_item_level_outputs_for_s199_selection_or_repair",
    "open_downstream_planner_or_protected_target_probe_before_upstream_go",
    "use_frontier_model_for_execution",
    "database_write_or_chunks_table_change",
    "chunks_v3_wholesale_reopen_or_per_question_patch",
    "deployment_or_railway_gate",
    "production_or_official_fact_credit",
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable_text_sha(path: Path) -> str:
    """Hash text canonically while ignoring only the CRLF/LF checkout difference."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _normalized(value: Any) -> str:
    return engine.normalized_identity(value)


def chunks_v3_lane() -> dict[str, Any]:
    return {
        "status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
        "changed_by_s199": False,
        "migration_or_materialization": False,
        "per_question_patching": False,
        "historical_metrics_duplicated": False,
    }


def source_contract(source: dict[str, Any]) -> None:
    body = dict(source)
    sealed = body.pop("packet_sha256", None)
    items = source.get("items") or []
    selection = source.get("selection") or {}
    read = source.get("read_receipt") or {}
    equivalence = source.get("target_equivalence_exclusion") or {}
    inventory = source.get("eligible_inventory") or {}
    documents = {str(item["document_id"]) for item in items}
    sources = {_normalized(item["source_file"]) for item in items}
    pairs = {
        (_normalized(item["manufacturer"]), _normalized(item["product_model"]))
        for item in items
    }
    manufacturers = {_normalized(item["manufacturer"]) for item in items}
    zero_overlap_keys = (
        "prior_document_overlap",
        "prior_source_file_overlap",
        "prior_manufacturer_product_pair_overlap",
        "target_document_overlap",
        "target_chunk_overlap",
        "target_exact_content_overlap",
        "target_extraction_overlap",
    )
    if (
        source.get("status") != "SEALED_FRESH_LIVE_CHUNKS_V2_GET_ONLY"
        or sealed != stable_sha(body)
        or len(items) != 14
        or len({item["item_id"] for item in items}) != 14
        or not all(item["item_id"].startswith("s199_src_") for item in items)
        or len(documents) != 14
        or len(sources) != 14
        or len(pairs) != 14
        or len(manufacturers) not in {13, 14}
        or selection.get("unique_manufacturers") != len(manufacturers)
        or selection.get("within_cohort_manufacturer_repeat_count")
        != 14 - len(manufacturers)
        or selection.get("fallback_used") != (len(manufacturers) == 13)
        or sum(item["stratum"] == "table" for item in items) != 7
        or sum(item["stratum"] == "prose" for item in items) != 7
        or selection.get("question_gold_claim_facet_or_model_outcome_used_for_selection")
        is not False
        or any(selection.get(key) != 0 for key in zero_overlap_keys)
        or selection.get("semantic_near_duplicate_overlap_status") != "NOT_MEASURED"
        or selection.get("oem_relabel_overlap_status") != "NOT_MEASURED"
        or read.get("database_writes") != 0
        or read.get("consistency") != "DOUBLE_IDENTICAL_FULL_SCAN"
        or read.get("scan_1", {}).get("rows") != read.get("scan_2", {}).get("rows")
        or read.get("scan_1", {}).get("full_scan_sha256")
        != read.get("scan_2", {}).get("full_scan_sha256")
        or read.get("scan_2", {}).get("full_scan_sha256")
        != read.get("stable_full_scan_sha256")
        or equivalence.get("all_target_uuids_resolved") is not True
        or equivalence.get("unresolved_target_uuids") != []
        or inventory.get("counts", {}).get("manufacturers") < 13
        or len(inventory.get("selected_identities") or []) != 14
        or source.get("chunks_v3_lane", {}).get("status")
        != "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
        or source.get("railway_deploy_gate") is not False
    ):
        raise RuntimeError("S199 restored-margin source contract failed")
    for item in items:
        if item["excerpt_sha256"] != hashlib.sha256(
            str(item["excerpt"]).encode("utf-8")
        ).hexdigest():
            raise RuntimeError("S199 source excerpt hash drift")
        engine.verified_units(item)


def frozen_runtime_inputs() -> dict[str, str]:
    return {
        "s198_design": "evals/s198_point_first_scope_design_v1.md",
        "s198_frontier_adjudication": "evals/s198_point_first_scope_frontier_adjudication_v1.json",
        "s198_question_canary": "evals/s198_question_schema_canary_result_v1.json",
        "s198_semantic_engine": "scripts/s198_point_first_scope_gate.py",
        "s198_engine_tests": "tests/test_s198_point_first_scope_gate.py",
        "s199_population_addendum": "evals/s199_restored_margin_population_addendum_v1.md",
        "s199_source_packet": "evals/s199_restored_margin_source_packet_v1.json",
        "s199_source_builder": "scripts/s199_build_restored_margin_packet.py",
        "s199_source_tests": "tests/test_s199_restored_margin_packet.py",
        "s199_replay_adapter": "scripts/s199_point_first_replay.py",
        "s199_replay_tests": "tests/test_s199_point_first_replay.py",
        "point_transport_authority": "scripts/s196_static_transport_canary.py",
        "question_transport_authority": "scripts/s198_question_schema_canary.py",
        "evidence_unitizer": "src/rag/evidence_units_v2.py",
        "eol_contract": ".gitattributes",
        "runtime_requirements": "requirements.txt",
    }


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    exact = {
        "instrument": "s199_point_first_replay_prereg_v1",
        "status": "FROZEN_BEFORE_PAID_EXECUTION",
        "objective": "replay_unchanged_s198_semantic_package_on_s199_restored_margin_cohort",
        "models": engine.EXPECTED_MODELS,
        "sdk": engine.EXPECTED_SDK,
        "execution": EXPECTED_EXECUTION,
        "validation": engine.EXPECTED_VALIDATION,
        "pricing_usd_per_million_tokens": engine.EXPECTED_PRICING,
        "budget": engine.EXPECTED_BUDGET,
        "outputs": EXPECTED_OUTPUTS,
        "point_transport_schema_sha256": stable_sha(engine.static_transport_schema()),
        "question_transport_schema_sha256": stable_sha(engine.question_schema()),
        "eligibility_definition": engine.ELIGIBILITY_DEFINITION,
        "facet_definitions": engine.FACET_DEFINITIONS,
        "facet_precedence": list(engine.FACET_PRECEDENCE),
    }
    for key, value in exact.items():
        if prereg.get(key) != value:
            raise RuntimeError(f"S199 prereg {key} contract drift")
    if set(prereg.get("forbidden") or []) != EXPECTED_FORBIDDEN:
        raise RuntimeError("S199 forbidden contract drift")
    required = frozen_runtime_inputs()
    if {
        key: value.get("path")
        for key, value in (prereg.get("frozen_inputs") or {}).items()
    } != required:
        raise RuntimeError("S199 frozen input inventory drift")
    for key, relative in required.items():
        if prereg["frozen_inputs"][key]["sha256"] != portable_text_sha(
            ROOT / relative
        ):
            raise RuntimeError(f"S199 frozen input drift: {key}")

    expected_permit = {
        "instrument": "s199_point_first_replay_execution_permit_v1",
        "status": "EXECUTION_GO_PAID_BOUNDED_NO_RETRY",
        "authority": "user_requested_continue_toward_more_facts_ok",
        "frozen_artifacts": {
            "preregistration": {
                "path": "evals/s199_point_first_replay_prereg_v1.yaml",
                "sha256": file_sha(DEFAULT_PREREG),
            },
            "adapter": {
                "path": "scripts/s199_point_first_replay.py",
                "sha256": file_sha(ROOT / "scripts/s199_point_first_replay.py"),
            },
            "adapter_tests": {
                "path": "tests/test_s199_point_first_replay.py",
                "sha256": file_sha(ROOT / "tests/test_s199_point_first_replay.py"),
            },
            "semantic_engine": {
                "path": "scripts/s198_point_first_scope_gate.py",
                "sha256": file_sha(ROOT / "scripts/s198_point_first_scope_gate.py"),
            },
        },
        "limits": {
            "paid_calls_max": 56,
            "provider_requests_max": 112,
            "retries": 0,
            "internal_ceiling_usd": 3,
            "frontier_execution_calls": 0,
            "database_calls": 0,
            "database_writes": 0,
            "production_changes": 0,
            "chunks_v3_changes": 0,
            "deployments": 0,
            "exclusive_lock_before_provider_requests": True,
            "lock_scope": "current_workspace",
            "immutable_prepaid_checkpoints": True,
            "atomic_progress_and_finalization": True,
        },
    }
    for key, value in expected_permit.items():
        if permit.get(key) != value:
            raise RuntimeError(f"S199 permit {key} contract drift")
    return prereg


def _renamed_payload(value: dict[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    instrument = payload.get("instrument")
    if isinstance(instrument, str) and instrument.startswith("s198_"):
        payload["instrument"] = "s199_" + instrument.removeprefix("s198_").replace(
            "_v2", "_v1"
        )
    decision = payload.get("decision")
    if isinstance(decision, dict):
        decision = dict(decision)
        if decision.get("next_action") == "AUTHORIZE_SEPARATE_S199_PLANNER_PREREGISTRATION":
            decision["next_action"] = "AUTHORIZE_SEPARATE_S200_PLANNER_PREREGISTRATION"
        if "s199_handoff_constraints" in decision:
            decision["s200_handoff_constraints"] = decision.pop(
                "s199_handoff_constraints"
            )
        payload["decision"] = decision
    for seal in ("cohort_sha256", "result_sha256"):
        if seal in payload:
            body = {key: item for key, item in payload.items() if key != seal}
            payload[seal] = stable_sha(body)
    return payload


def _write_json_exclusive_lf(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(path)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(_renamed_payload(value), ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_json_atomic_lf(path: Path, value: dict[str, Any], *, replace: bool) -> None:
    if path.exists() and not replace:
        raise FileExistsError(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(_renamed_payload(value), ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def bind_engine() -> dict[str, Any]:
    bindings = {
        "SOURCE": SOURCE,
        "DEFAULT_LOCK": DEFAULT_LOCK,
        "DEFAULT_POINT_AUTHOR_PREPAID": DEFAULT_POINT_AUTHOR_PREPAID,
        "DEFAULT_POINT_AUTHOR_RECEIPTS": DEFAULT_POINT_AUTHOR_RECEIPTS,
        "DEFAULT_POINT_SCREEN_PREPAID": DEFAULT_POINT_SCREEN_PREPAID,
        "DEFAULT_POINT_SCREEN_RECEIPTS": DEFAULT_POINT_SCREEN_RECEIPTS,
        "DEFAULT_QUESTION_WRITER_PREPAID": DEFAULT_QUESTION_WRITER_PREPAID,
        "DEFAULT_QUESTION_WRITER_RECEIPTS": DEFAULT_QUESTION_WRITER_RECEIPTS,
        "DEFAULT_QUESTION_SCREEN_PREPAID": DEFAULT_QUESTION_SCREEN_PREPAID,
        "DEFAULT_QUESTION_SCREEN_RECEIPTS": DEFAULT_QUESTION_SCREEN_RECEIPTS,
        "DEFAULT_COHORT": DEFAULT_COHORT,
        "DEFAULT_RESULT": DEFAULT_RESULT,
        "OUTPUT_PATHS": OUTPUT_PATHS,
        "source_contract": source_contract,
        "chunks_v3_lane": chunks_v3_lane,
        "write_json_exclusive": _write_json_exclusive_lf,
        "write_json_atomic": _write_json_atomic_lf,
    }
    originals = {name: getattr(engine, name) for name in bindings}
    for name, value in bindings.items():
        setattr(engine, name, value)
    return originals


def restore_engine(originals: dict[str, Any]) -> None:
    for name, value in originals.items():
        setattr(engine, name, value)


def execute(prereg: dict[str, Any], env_file: Path) -> dict[str, Any]:
    bind_engine()
    engine.execute(prereg, env_file)
    return json.loads(DEFAULT_RESULT.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    args = parser.parse_args()
    prereg = validate_authorization(args.prereg, args.permit)
    result = execute(prereg, args.env_file)
    print(
        json.dumps(
            {
                "status": result["status"],
                "population_checks": result.get("population_checks"),
                "point_plan_semantic_checks": result.get(
                    "point_plan_semantic_checks"
                ),
                "question_scope_checks": result.get("question_scope_checks"),
                "cost": result.get("cost"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
