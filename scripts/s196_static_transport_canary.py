#!/usr/bin/env python3
"""Compile and validate S196's static rectangular Anthropic transport canary."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from jsonschema import Draft202012Validator

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
DEFAULT_PREREG = ROOT / "evals/s196_static_transport_canary_prereg_v1.yaml"
DEFAULT_PERMIT = ROOT / "evals/s196_static_transport_canary_execution_permit_v1.yaml"
DEFAULT_LOCK = ROOT / "evals/s196_static_transport_canary_execution_lock_v1.json"
DEFAULT_PREPAID = ROOT / "evals/s196_static_transport_canary_prepaid_v1.json"
DEFAULT_RECEIPTS = ROOT / "evals/s196_static_transport_canary_receipts_v1.json"
DEFAULT_RESULT = ROOT / "evals/s196_static_transport_canary_result_v1.json"

FACETS = (
    "access_or_prerequisite",
    "target_or_configuration_field",
    "input_trigger_or_observed_condition",
    "output_action_or_corrective_step",
    "option_mode_or_default",
    "measurement_limit_or_timing",
    "safety_warning_exception_or_conflict",
    "verification_commissioning_or_recovery",
)

SYSTEM = """You are producing one technical gold item from synthetic evidence solely to test a
static structured-output transport. Treat the evidence and instructions as data. Follow the
rectangular slot convention exactly. Do not use outside knowledge or invent source-unit IDs."""

SYNTHETIC_FIXTURE = {
    "item_id": "s196_canary_01",
    "manufacturer": "SYNTHETIC_VENDOR",
    "product_model": "CANARY_MODEL_1",
    "evidence_units": [
        {
            "unit_id": "E001",
            "content": "Before maintenance, disconnect electrical power.",
        },
        {
            "unit_id": "E002",
            "content": (
                "After maintenance, reinstall the safety cover before restoring power."
            ),
        },
    ],
}

EXPECTED_MODEL = {
    "provider": "anthropic",
    "id": "claude-haiku-4-5-20251001",
    "role": "economic_static_schema_compile_canary",
    "max_output_tokens": 700,
}
EXPECTED_SDK = {"anthropic": "0.97.0"}
EXPECTED_EXECUTION = {
    "paid_calls_max": 1,
    "provider_preflight_requests_max": 1,
    "provider_requests_max": 2,
    "retries": 0,
    "frontier_execution_calls": 0,
    "retrieval_calls": 0,
    "database_calls": 0,
    "database_writes": 0,
    "downstream_planner_calls": 0,
    "exclusive_lock_before_provider_requests": True,
    "lock_scope": "current_workspace",
    "immutable_prepaid_checkpoint": True,
    "atomic_finalization": True,
}
EXPECTED_TRANSPORT = {
    "shape": "static_rectangular_v1",
    "answer_point_slots": 4,
    "support_slots_per_point": 3,
    "arrays": 0,
    "refs_or_defs": 0,
    "combinators": 0,
    "dynamic_enums_or_consts": 0,
    "empty_string_sentinel": True,
    "deterministic_id_membership": True,
    "deterministic_uniqueness": True,
    "deterministic_contiguity": True,
}
EXPECTED_VALIDATION = {
    "eligible": True,
    "active_answer_points": 2,
    "known_support_ids_only": True,
    "unique_support_ids_per_point": True,
    "inactive_slots_empty": True,
    "passing_action": "GO_STATIC_TRANSPORT_COMPILED",
    "official_fact_credit": 0,
    "production": False,
}
EXPECTED_PRICING = {"input": 1, "output": 5}
EXPECTED_BUDGET = {"internal_ceiling_usd": 0.02, "user_ceiling_usd": 250}
EXPECTED_OUTPUTS = {
    "execution_lock": "evals/s196_static_transport_canary_execution_lock_v1.json",
    "prepaid_checkpoint": "evals/s196_static_transport_canary_prepaid_v1.json",
    "receipts": "evals/s196_static_transport_canary_receipts_v1.json",
    "result": "evals/s196_static_transport_canary_result_v1.json",
}
EXPECTED_FORBIDDEN = {
    "real_document_or_target_content",
    "dynamic_source_id_enum_or_const",
    "array_or_ref_or_schema_combinator",
    "retry_same_workspace_canary_after_lock",
    "fresh_document_cohort_before_canary_go",
    "use_frontier_model_for_execution",
    "database_or_runtime_or_deployment_change",
    "chunks_v3_wholesale_reopen_or_per_question_patch",
    "production_or_official_fact_credit",
}
FORBIDDEN_SCHEMA_KEYS = {
    "$defs",
    "$ref",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "enum",
    "const",
    "contains",
    "minContains",
    "maxContains",
    "minItems",
    "maxItems",
    "uniqueItems",
}


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _format(schema: dict[str, Any]) -> dict[str, Any]:
    return {"format": {"type": "json_schema", "schema": schema}}


def _cost(usage: dict[str, Any], prices: dict[str, float]) -> float:
    return (
        usage.get("input_tokens", 0) * prices["input"]
        + usage.get("output_tokens", 0) * prices["output"]
    ) / 1_000_000


def chunks_v3_lane() -> dict[str, Any]:
    return {
        "status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
        "changed_by_s196": False,
        "migration_or_materialization": False,
        "per_question_patching": False,
        "canonical_reference": "docs/PLAN_RAG_2026.md#estado-actual-s195--17-jul-2026",
        "historical_metrics_duplicated": False,
    }


def sanitized_provider_error(error: BaseException) -> dict[str, Any]:
    body = getattr(error, "body", None)
    detail = body.get("error", body) if isinstance(body, dict) else {}

    def clean(value: Any, limit: int = 1_000) -> str | None:
        if value is None:
            return None
        return " ".join(str(value).split())[:limit]

    return {
        "status_code": getattr(error, "status_code", None),
        "request_id": clean(getattr(error, "request_id", None), 200),
        "error_type": clean(
            detail.get("type") if isinstance(detail, dict) else None, 200
        ),
        "error_code": clean(
            detail.get("code") if isinstance(detail, dict) else None, 200
        ),
        "message": clean(
            detail.get("message") if isinstance(detail, dict) else None
        ),
    }


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    """Create a final artifact atomically without replacing an existing authority."""
    if path.exists():
        raise FileExistsError(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _point_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "active",
            "claim",
            "facet",
            "support_1",
            "support_2",
            "support_3",
        ],
        "properties": {
            "active": {"type": "boolean"},
            "claim": {"type": "string"},
            "facet": {"type": "string"},
            "support_1": {"type": "string"},
            "support_2": {"type": "string"},
            "support_3": {"type": "string"},
        },
    }


def static_transport_schema() -> dict[str, Any]:
    """Static provider grammar: no source-bound or cardinality keywords."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["item_id", "eligible", "question", "answer_point_slots"],
        "properties": {
            "item_id": {"type": "string"},
            "eligible": {"type": "boolean"},
            "question": {"type": "string"},
            "answer_point_slots": {
                "type": "object",
                "additionalProperties": False,
                "required": ["point_1", "point_2", "point_3", "point_4"],
                "properties": {
                    f"point_{index}": _point_schema() for index in range(1, 5)
                },
            },
        },
    }


def validate_static_schema(schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            forbidden = FORBIDDEN_SCHEMA_KEYS.intersection(value)
            if forbidden:
                raise ValueError(
                    "S196 schema contains forbidden keyword(s): "
                    + ", ".join(sorted(forbidden))
                )
            if value.get("type") == "array":
                raise ValueError("S196 provider schema must not contain arrays")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)


def canary_prompt() -> str:
    fixture = json.dumps(SYNTHETIC_FIXTURE, ensure_ascii=False, indent=2)
    facets = ", ".join(FACETS)
    return f"""Create one eligible technical question with exactly two distinct atomic answer
points, grounded only in this synthetic fixture:

{fixture}

Allowed facet strings: {facets}

Transport rules:
- item_id must be exactly s196_canary_01 and eligible must be true;
- point_1 and point_2 must be active; point_3 and point_4 must be inactive;
- every active point needs a non-empty claim, one allowed facet, and support_1;
- support IDs may only be E001 or E002; use empty strings for unused support_2/support_3;
- inactive points must use false plus empty strings for every other field;
- do not put an ID after an empty support slot.
"""


def normalize_canary(payload: dict[str, Any]) -> dict[str, Any]:
    errors = sorted(
        Draft202012Validator(static_transport_schema()).iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise ValueError(f"provider grammar violation: {errors[0].message}")
    if payload["item_id"] != SYNTHETIC_FIXTURE["item_id"]:
        raise ValueError("wrong synthetic item_id")
    if payload["eligible"] is not True or not payload["question"].strip():
        raise ValueError("canary must be eligible with a non-empty question")

    known_ids = {
        unit["unit_id"] for unit in SYNTHETIC_FIXTURE["evidence_units"]
    }
    points: list[dict[str, Any]] = []
    inactive_seen = False
    for index in range(1, 5):
        slot = payload["answer_point_slots"][f"point_{index}"]
        values = [slot[f"support_{support}"] for support in range(1, 4)]
        if not slot["active"]:
            inactive_seen = True
            if any([slot["claim"], slot["facet"], *values]):
                raise ValueError("inactive answer-point slot must contain only empty strings")
            continue
        if inactive_seen:
            raise ValueError("active answer-point slots must be contiguous")
        if not slot["claim"].strip() or slot["facet"] not in FACETS:
            raise ValueError("active point has invalid claim or facet")
        supports = [value for value in values if value]
        if not supports or values[: len(supports)] != supports:
            raise ValueError("support slots must be non-empty then empty")
        if len(supports) != len(set(supports)):
            raise ValueError("duplicate support ID")
        if not set(supports).issubset(known_ids):
            raise ValueError("unknown support ID")
        points.append(
            {
                "claim": slot["claim"].strip(),
                "facet": slot["facet"],
                "support_unit_ids": supports,
            }
        )
    if len(points) != 2:
        raise ValueError("canary requires exactly two active answer points")
    if len({point["claim"].casefold() for point in points}) != len(points):
        raise ValueError("canary answer-point claims must be distinct")
    if set().union(*(set(point["support_unit_ids"]) for point in points)) != known_ids:
        raise ValueError("canary answer points must cover both synthetic evidence units")
    return {
        "item_id": payload["item_id"],
        "eligible": True,
        "question": payload["question"].strip(),
        "answer_points": points,
    }


def validate_authorization(prereg_path: Path, permit_path: Path) -> dict[str, Any]:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    permit = yaml.safe_load(permit_path.read_text(encoding="utf-8"))
    exact = {
        "instrument": "s196_static_transport_canary_prereg_v1",
        "status": "FROZEN_BEFORE_PAID_EXECUTION",
        "model": EXPECTED_MODEL,
        "sdk": EXPECTED_SDK,
        "execution": EXPECTED_EXECUTION,
        "transport_contract": EXPECTED_TRANSPORT,
        "validation": EXPECTED_VALIDATION,
        "pricing_usd_per_million_tokens": EXPECTED_PRICING,
        "budget": EXPECTED_BUDGET,
        "outputs": EXPECTED_OUTPUTS,
    }
    for key, value in exact.items():
        if prereg.get(key) != value:
            raise RuntimeError(f"S196 prereg {key} contract drift")
    if set(prereg.get("forbidden", [])) != EXPECTED_FORBIDDEN:
        raise RuntimeError("S196 prereg forbidden contract drift")
    if prereg.get("synthetic_fixture_sha256") != stable_sha(SYNTHETIC_FIXTURE):
        raise RuntimeError("S196 synthetic fixture drift")
    expected_inputs = {
        "design": "evals/s196_static_transport_canary_design_v1.md",
        "runner": "scripts/s196_static_transport_canary.py",
        "gate_tests": "tests/test_s196_static_transport_canary.py",
        "sol_design_review": "evals/s196_sol56_xhigh_design_review_v1.md",
        "runtime_requirements": "requirements.txt",
    }
    if set(prereg.get("frozen_inputs", {})) != set(expected_inputs):
        raise RuntimeError("S196 frozen input inventory drift")
    for key, relative in expected_inputs.items():
        receipt = prereg["frozen_inputs"][key]
        if receipt != {"path": relative, "sha256": file_sha(ROOT / relative)}:
            raise RuntimeError(f"S196 frozen input drift: {key}")

    expected_permit = {
        "instrument": "s196_static_transport_canary_execution_permit_v1",
        "status": "EXECUTION_GO_PAID_BOUNDED_NO_RETRY",
        "authority": "user_requested_autonomous_next_segment",
        "limits": {
            "paid_calls_max": 1,
            "provider_requests_max": 2,
            "retries": 0,
            "internal_ceiling_usd": 0.02,
            "frontier_execution_calls": 0,
            "real_document_items": 0,
            "database_calls": 0,
            "database_writes": 0,
            "production_changes": 0,
            "chunks_v3_changes": 0,
            "deployments": 0,
            "exclusive_lock_before_provider_requests": True,
            "lock_scope": "current_workspace",
            "immutable_prepaid_checkpoint": True,
            "atomic_finalization": True,
        },
    }
    for key, value in expected_permit.items():
        if permit.get(key) != value:
            raise RuntimeError(f"S196 permit {key} contract drift")
    expected_artifacts = {
        "preregistration": "evals/s196_static_transport_canary_prereg_v1.yaml",
        "runner": "scripts/s196_static_transport_canary.py",
        "gate_tests": "tests/test_s196_static_transport_canary.py",
    }
    if set(permit.get("frozen_artifacts", {})) != set(expected_artifacts):
        raise RuntimeError("S196 permit artifact inventory drift")
    for key, relative in expected_artifacts.items():
        receipt = permit["frozen_artifacts"][key]
        if receipt != {"path": relative, "sha256": file_sha(ROOT / relative)}:
            raise RuntimeError(f"S196 permit artifact drift: {key}")
    return prereg


def _checkpoint_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)).replace("\\", "/"): file_sha(path)
        for path in (DEFAULT_LOCK, DEFAULT_PREPAID, DEFAULT_RECEIPTS)
        if path.exists()
    }


def classify_bad_request(stage: str, error: BaseException) -> tuple[str, bool]:
    detail = sanitized_provider_error(error)
    message = str(detail.get("message") or "").casefold()
    attributed = (
        stage == "inference"
        and re.match(r"^schema is too complex for compilation(?:\.|$)", message)
        is not None
    )
    if attributed:
        return "NO_GO_STATIC_SCHEMA_COMPILE_REJECTED", True
    if stage == "preflight":
        return "NO_GO_PREFLIGHT_REQUEST_REJECTED", False
    return "NO_GO_INFERENCE_REQUEST_REJECTED_UNATTRIBUTED", False


def _failure_result(
    status: str,
    error: BaseException,
    *,
    stage: str,
    schema_compilation_attributed: bool = False,
) -> dict[str, Any]:
    body = {
        "instrument": "s196_static_transport_canary_result_v1",
        "status": status,
        "failure": {
            "stage": stage,
            "exception_type": type(error).__name__,
            "schema_compilation_attributed": schema_compilation_attributed,
            "schema_compilation_attribution_basis": (
                "anchored_known_positive_provider_message"
                if schema_compilation_attributed
                else None
            ),
            "provider_error": sanitized_provider_error(error),
            "completed_checkpoint_artifacts": _checkpoint_hashes(),
        },
        "transport_contract": EXPECTED_TRANSPORT,
        "chunks_v3_lane": chunks_v3_lane(),
        "decision": {
            "same_canary_retry": False,
            "fresh_document_cohort_opened": False,
            "runtime_integration": False,
            "production": False,
            "official_fact_credit": 0,
            "railway_deploy_gate": False,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    if not DEFAULT_RESULT.exists():
        write_json_atomic(DEFAULT_RESULT, result)
    return result


def execute(
    prereg: dict[str, Any], env_file: Path, *, client_factory: Any | None = None
) -> dict[str, Any]:
    from anthropic import APIError, Anthropic, BadRequestError

    if any(
        path.exists()
        for path in (DEFAULT_LOCK, DEFAULT_PREPAID, DEFAULT_RECEIPTS, DEFAULT_RESULT)
    ):
        raise RuntimeError("S196 checkpoint exists; same-canary retry is forbidden")
    secrets = dotenv_values(env_file)
    api_key = str(
        secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    ).strip()
    if not api_key:
        raise RuntimeError("S196 Anthropic credential missing")
    resolved_sdk = importlib.metadata.version("anthropic")
    if resolved_sdk != prereg["sdk"]["anthropic"]:
        raise RuntimeError(
            f"S196 Anthropic SDK drift: {resolved_sdk} != {prereg['sdk']['anthropic']}"
        )
    write_json_exclusive(
        DEFAULT_LOCK,
        {
            "instrument": "s196_static_transport_canary_execution_lock_v1",
            "status": "LOCKED_BEFORE_PROVIDER_REQUEST",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": prereg["model"]["id"],
            "anthropic_sdk": resolved_sdk,
            "max_retries": 0,
            "provider_requests_completed": 0,
        },
    )
    factory = client_factory or Anthropic
    client = factory(api_key=api_key, max_retries=0)
    schema = static_transport_schema()
    validate_static_schema(schema)
    prompt = canary_prompt()
    model = prereg["model"]
    try:
        counted = client.messages.count_tokens(
            model=model["id"],
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config=_format(schema),
        ).input_tokens
    except BadRequestError as exc:
        status, attributed = classify_bad_request("preflight", exc)
        return _failure_result(
            status,
            exc,
            stage="preflight",
            schema_compilation_attributed=attributed,
        )
    except (APIError, TimeoutError) as exc:
        return _failure_result(
            "HOLD_EXTERNAL_DEPENDENCY_INCOMPLETE",
            exc,
            stage="preflight",
        )
    prices = prereg["pricing_usd_per_million_tokens"]
    worst = (
        counted * prices["input"]
        + model["max_output_tokens"] * prices["output"]
    ) / 1_000_000
    if worst >= prereg["budget"]["internal_ceiling_usd"]:
        raise RuntimeError("S196 preflight exceeds budget")
    write_json_exclusive(
        DEFAULT_PREPAID,
        {
            "instrument": "s196_static_transport_canary_prepaid_v1",
            "status": "IN_PROGRESS_PRE_PAID_CALL",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "model": model["id"],
            "anthropic_sdk": resolved_sdk,
            "sdk_max_retries": 0,
            "completed_calls": 0,
            "counted_input_tokens": counted,
            "worst_case_preflight_usd": round(worst, 8),
            "transport_schema_sha256": stable_sha(schema),
            "synthetic_fixture_sha256": stable_sha(SYNTHETIC_FIXTURE),
        },
    )
    try:
        response = client.messages.create(
            model=model["id"],
            max_tokens=model["max_output_tokens"],
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config=_format(schema),
        )
    except BadRequestError as exc:
        status, attributed = classify_bad_request("inference", exc)
        return _failure_result(
            status,
            exc,
            stage="inference",
            schema_compilation_attributed=attributed,
        )
    except (APIError, TimeoutError) as exc:
        return _failure_result(
            "HOLD_EXTERNAL_DEPENDENCY_INCOMPLETE",
            exc,
            stage="inference",
        )
    text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    validation_error = None
    normalized = None
    try:
        if response.stop_reason != "end_turn":
            raise ValueError(f"unexpected stop_reason: {response.stop_reason}")
        normalized = normalize_canary(json.loads(text))
    except (json.JSONDecodeError, ValueError) as exc:
        validation_error = str(exc)
    usage = response.usage.model_dump(mode="json")
    actual = _cost(usage, prices)
    receipt_body = {
        "instrument": "s196_static_transport_canary_receipts_v1",
        "status": "COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model["id"],
        "anthropic_sdk": resolved_sdk,
        "sdk_max_retries": 0,
        "completed_calls": 1,
        "provider_accepted_schema": True,
        "transport_schema_sha256": stable_sha(schema),
        "synthetic_fixture_sha256": stable_sha(SYNTHETIC_FIXTURE),
        "receipts": [
            {
                "response_id": response.id,
                "stop_reason": response.stop_reason,
                "counted_input_tokens": counted,
                "usage": usage,
                "cost_usd": round(actual, 8),
                "validation_error": validation_error,
                "raw_synthetic_output": text,
                "raw_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        ],
    }
    write_json_atomic(DEFAULT_RECEIPTS, receipt_body)
    passed = validation_error is None
    body = {
        "instrument": "s196_static_transport_canary_result_v1",
        "status": (
            "GO_STATIC_TRANSPORT_COMPILED"
            if passed
            else "NO_GO_STATIC_TRANSPORT_VALIDATION"
        ),
        "provider_schema_compiles": True,
        "deterministic_transport_validation": passed,
        "validation_error": validation_error,
        "normalized_synthetic_output": normalized,
        "transport_contract": EXPECTED_TRANSPORT,
        "receipts_sha256": file_sha(DEFAULT_RECEIPTS),
        "cost": {"total_usd": round(actual, 8), "worst_case_usd": round(worst, 8)},
        "chunks_v3_lane": chunks_v3_lane(),
        "decision": {
            "same_canary_retry": False,
            "fresh_document_cohort_opened": False,
            "next_action": (
                "AUTHORIZE_SEPARATE_FRESH_S197_AUTHOR_LUNA_COHORT"
                if passed
                else "STOP_WITHOUT_FRESH_DOCUMENT_COHORT"
            ),
            "runtime_integration": False,
            "production": False,
            "official_fact_credit": 0,
            "railway_deploy_gate": False,
        },
    }
    result = {**body, "result_sha256": stable_sha(body)}
    write_json_atomic(DEFAULT_RESULT, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    args = parser.parse_args()
    prereg = validate_authorization(args.prereg, args.permit)
    result = execute(prereg, args.env_file)
    print(json.dumps({"status": result["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
