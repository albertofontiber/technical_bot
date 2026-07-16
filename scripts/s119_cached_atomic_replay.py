#!/usr/bin/env python3
"""Replay the 22 S118 transformed claims from frozen local S113 artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts.s118_build_atomic_benchmark import (
        ROOT,
        _assert_safe_output,
        _write_json,
        file_sha256,
        load_json,
        load_yaml,
        normalized_text_sha256,
        object_sha256,
    )
except ModuleNotFoundError:  # Direct `python scripts/...py` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.s118_build_atomic_benchmark import (
        ROOT,
        _assert_safe_output,
        _write_json,
        file_sha256,
        load_json,
        load_yaml,
        normalized_text_sha256,
        object_sha256,
    )


CONTRACT_KEYS = {
    "instrument", "schema_version", "status", "authority", "frozen_inputs",
    "external_source", "parent_fact_key_overrides", "policy", "authorization",
    "expected_population", "claims",
}
CLAIM_KEYS = {"claim_id", "qid", "source_row_key", "evidence_groups", "synthesis"}
GROUP_KEYS = {"group_id", "alternatives"}
ALTERNATIVE_KEYS = {
    "candidate_id", "source_file", "page_number", "content_sha256", "match_patterns",
}
SYNTHESIS_KEYS = {"coverage_patterns"}
FORBIDDEN_CONTRACT_KEYS = {
    "answer", "answer_available", "answer_sha256", "coverage_passed", "covered",
    "evidence_passed", "facts_moved_to_ok", "generator_support", "matched",
    "result", "reaches_generator", "stage_after", "stage_bucket", "stage_status",
}
SOURCE_ROW_FIELDS = {
    "key", "source_trace", "source_truth", "question_requiredness", "atomicity",
    "governance", "evidence",
}
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_PATTERN = re.compile(r"[a-z0-9 .{}(),?|\-]+")
EXACT_AUTHORITY = "diagnostic_hybrid_replay_only_no_official_atomic_credit"
EXACT_POLICY = {
    "population": "exact_s118_pending_replay_claims_only",
    "evidence": "all_required_groups_must_bind_to_exact_s113_context_chunks",
    "missing_evidence": "evidence-binding-unresolved",
    "missing_answer": "synthesis-not-measured",
    "answer_coverage": "all_bounded_semantic_patterns_must_match",
    "ok_credit": "hybrid_diagnostic_only",
    "official_atomic_denominator": None,
    "official_atomic_target_ok": None,
}
EXACT_AUTHORIZATION_KEYS = {
    "network", "database", "models", "retrieval", "rerank", "synthesis_calls",
    "serving", "deploy", "gold_mutation",
}
EVIDENCE_ADJUDICATION_KEYS = {
    "instrument", "schema_version", "status", "independent_of_cached_answer_outcome",
    "review_basis", "rows",
}
EVIDENCE_ADJUDICATION_ROW_KEYS = {
    "claim_id", "qid", "source_row_key", "claim_text_sha256", "claim_value_sha256",
    "claim_cita_sha256", "claim_source_pages", "page_basis", "evidence_groups",
    "adjudicator_status",
}
EVIDENCE_ADJUDICATION_GROUP_KEYS = {
    "group_id", "accepted_candidate_id", "relation", "support_spans",
}
ANSWER_ADJUDICATION_KEYS = {
    "instrument", "schema_version", "status", "reviewed_without_model_calls", "scope",
    "rows",
}
ANSWER_ADJUDICATION_ROW_KEYS = {
    "claim_id", "qid", "answer_sha256", "verdict", "rationale",
}
ALLOWED_EVIDENCE_RELATIONS = {
    "direct_explicit",
    "direct_explicit_current_revision",
    "explicit_gui_operation_equivalent",
    "diagram_entails_closed_out_and_return_path",
    "diagram_direct_terminal_labels",
    "explicit_general_rule_plus_abort_exception",
    "direct_explicit_definition",
    "two_direct_spans_form_required_rule_and_deletion_obligation",
    "final_of_circuit_is_last_device_placement",
    "direct_explicit_component_pair",
}
ALLOWED_PAGE_BASES = {
    "direct_same_manual_explicit_normative_limit",
    "direct_same_manual_explicit_pearl_limit",
    "two_same_manual_spans_required_for_no_internal_isolator_and_fet_scope",
    "direct_same_manual_supply_section",
    "same_family_current_revision_workflow_pages_replace_older_indexed_citation",
    "physical_page_7_maps_to_extracted_printed_page_8",
    "cross_manual_same_id3000_programming_workflow_previously_generator_admitted_by_s110",
    "direct_same_manual_diagram_page",
    "same_manual_operational_restatement_on_page_53_of_page_44_input_behavior",
    "direct_same_manual_page",
    "glossary_page_12_is_explicit_equivalent_of_physical_page_14_core",
    "physical_page_43_maps_to_extracted_printed_page_45",
    "printed_page_20_corresponds_to_physical_page_21_in_same_manual",
    "direct_same_manual_page_29_s118_child_binding",
}


def _recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(
            *(_recursive_keys(item) for item in value.values()), set(),
        )
    if isinstance(value, list):
        return set().union(*(_recursive_keys(item) for item in value), set())
    return set()


def normalize_for_match(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    flattened = "".join(ch if ch.isalnum() else " " for ch in without_marks)
    return " ".join(flattened.split())


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    if (not isinstance(pattern, str) or not pattern or len(pattern) > 512
            or not SAFE_PATTERN.fullmatch(pattern)
            or "(?" in pattern or "\\" in pattern
            or re.search(r"\{[0-9]+,\}", pattern)):
        raise ValueError(f"unsafe semantic pattern: {pattern!r}")
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"invalid semantic pattern: {pattern!r}") from exc


def _resolve_inside_root(root: Path, ref: dict, label: str) -> Path:
    path = (root / str(ref.get("path") or "")).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes root: {path}") from exc
    return path


def _assert_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or not SHA256.fullmatch(str(expected or "")):
        raise ValueError(f"{label} lacks a valid frozen file/hash")
    actual = file_sha256(path)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 drift: {actual} != {expected}")


def _validate_payload(value: dict, label: str) -> None:
    expected = value.get("payload_sha256")
    unsigned = dict(value)
    unsigned.pop("payload_sha256", None)
    if not SHA256.fullmatch(str(expected or "")) or object_sha256(unsigned) != expected:
        raise ValueError(f"{label} payload hash is invalid")


def validate_contract(contract: dict, *, allow_pending_projection: bool = False) -> None:
    if set(contract) != CONTRACT_KEYS:
        raise ValueError("S119 contract schema is not exact")
    if (contract.get("instrument") != "s119_cached_atomic_replay_contract_v1"
            or contract.get("schema_version") != 1
            or contract.get("status") != "frozen_retrospective_cache_only_contract"
            or contract.get("authority") != EXACT_AUTHORITY
            or contract.get("policy") != EXACT_POLICY):
        raise ValueError("S119 contract identity is invalid")
    forbidden = _recursive_keys(contract) & FORBIDDEN_CONTRACT_KEYS
    if forbidden:
        raise ValueError(f"S119 contract contains runtime outcome fields: {sorted(forbidden)}")
    frozen = contract.get("frozen_inputs") or {}
    if set(frozen) != {
        "s118_bridge", "s118_gate", "s113_contexts", "s113_answers", "source_projection",
        "claim_evidence_adjudication", "cached_answer_adjudication",
    }:
        raise ValueError("S119 frozen input set is not exact")
    for key, ref in frozen.items():
        if set(ref) != {"path", "sha256"} or not str(ref.get("path") or ""):
            raise ValueError(f"S119 input receipt is invalid: {key}")
        if key == "source_projection" and allow_pending_projection:
            if (ref.get("sha256") != "PENDING_AFTER_MECHANICAL_FREEZE"
                    and not SHA256.fullmatch(str(ref.get("sha256") or ""))):
                raise ValueError("projection freeze expects a sentinel or frozen SHA-256")
        elif not SHA256.fullmatch(str(ref.get("sha256") or "")):
            raise ValueError(f"S119 input hash is invalid: {key}")
    external = contract.get("external_source") or {}
    if (set(external) != {"logical_path", "sha256", "required_row_keys"}
            or not SHA256.fullmatch(str(external.get("sha256") or ""))):
        raise ValueError("S119 external source receipt is invalid")
    row_keys = external.get("required_row_keys") or []
    if len(row_keys) != len(set(row_keys)) or not row_keys:
        raise ValueError("S119 source row keys are absent or duplicated")
    overrides = contract.get("parent_fact_key_overrides") or {}
    if (not isinstance(overrides, dict)
            or any(not isinstance(key, str) or not isinstance(value, str)
                   for key, value in overrides.items())):
        raise ValueError("S119 parent fact key overrides are invalid")
    authorization = contract.get("authorization") or {}
    if (set(authorization) != EXACT_AUTHORIZATION_KEYS
            or any(value is not False for value in authorization.values())):
        raise ValueError("S119 authority must remain entirely local/read-only")
    expected = contract.get("expected_population") or {}
    claims = contract.get("claims") or []
    if (set(expected) != {"pending_claims", "qids"}
            or expected.get("pending_claims") != len(claims)
            or expected.get("qids") != len({row.get("qid") for row in claims})):
        raise ValueError("S119 expected population does not reconcile")

    claim_ids: set[str] = set()
    for claim in claims:
        if set(claim) != CLAIM_KEYS:
            raise ValueError("S119 claim schema is not exact")
        claim_id, qid = claim.get("claim_id"), claim.get("qid")
        if (not isinstance(claim_id, str) or not claim_id or claim_id in claim_ids
                or not isinstance(qid, str) or not qid
                or claim.get("source_row_key") not in row_keys
                or not str(claim["source_row_key"]).startswith(qid + "#")):
            raise ValueError(f"S119 claim identity is invalid: {claim_id!r}")
        claim_ids.add(claim_id)
        groups = claim.get("evidence_groups") or []
        if not groups:
            raise ValueError(f"S119 claim lacks evidence groups: {claim_id}")
        group_ids: set[str] = set()
        for group in groups:
            if set(group) != GROUP_KEYS:
                raise ValueError(f"S119 evidence group schema is not exact: {claim_id}")
            group_id = group.get("group_id")
            alternatives = group.get("alternatives") or []
            if (not isinstance(group_id, str) or not group_id or group_id in group_ids
                    or not alternatives):
                raise ValueError(f"S119 evidence group is invalid: {claim_id}")
            group_ids.add(group_id)
            candidate_ids: set[str] = set()
            for alternative in alternatives:
                if set(alternative) != ALTERNATIVE_KEYS:
                    raise ValueError(f"S119 evidence alternative schema is not exact: {claim_id}")
                candidate_id = alternative.get("candidate_id")
                if (not isinstance(candidate_id, str) or not candidate_id
                        or candidate_id in candidate_ids
                        or not isinstance(alternative.get("source_file"), str)
                        or not alternative["source_file"]
                        or isinstance(alternative.get("page_number"), bool)
                        or not isinstance(alternative.get("page_number"), int)
                        or alternative["page_number"] <= 0
                        or not SHA256.fullmatch(str(alternative.get("content_sha256") or ""))):
                    raise ValueError(f"S119 evidence alternative identity is invalid: {claim_id}")
                candidate_ids.add(candidate_id)
                patterns = alternative.get("match_patterns") or []
                if not patterns:
                    raise ValueError(f"S119 evidence alternative lacks semantic patterns: {claim_id}")
                for pattern in patterns:
                    _compile_pattern(pattern)
        synthesis = claim.get("synthesis") or {}
        if set(synthesis) != SYNTHESIS_KEYS or not synthesis.get("coverage_patterns"):
            raise ValueError(f"S119 synthesis contract is invalid: {claim_id}")
        for pattern in synthesis["coverage_patterns"]:
            _compile_pattern(pattern)
    if not set(overrides) <= claim_ids:
        raise ValueError("S119 parent fact key overrides reference unknown claims")


def build_source_projection(source: dict, contract: dict) -> dict:
    if source.get("instrument") != "s106_p0_selection_adjudication_v1":
        raise ValueError("unexpected S106 source adjudication instrument")
    rows = source.get("rows") or []
    by_key = {row.get("key"): row for row in rows}
    if len(by_key) != len(rows) or None in by_key:
        raise ValueError("S106 source rows lack unique keys")
    required = contract["external_source"]["required_row_keys"]
    projected = []
    for key in required:
        row = by_key.get(key)
        if not row:
            raise ValueError(f"required S106 source row is absent: {key}")
        compact = {field: row[field] for field in SOURCE_ROW_FIELDS if field in row}
        if compact.get("key") != key:
            raise ValueError(f"S106 source row identity drift: {key}")
        projected.append({
            "row_key": key,
            "row_sha256": object_sha256(row),
            "source_row": compact,
        })
    output = {
        "instrument": "s119_source_contract_projection_v1",
        "schema_version": 1,
        "status": "MECHANICAL_SOURCE_TRUTH_PROJECTION_NO_RUNTIME_OUTCOMES",
        "source": {
            "logical_path": contract["external_source"]["logical_path"],
            "sha256": contract["external_source"]["sha256"],
            "instrument": source.get("instrument"),
        },
        "row_keys": required,
        "rows": projected,
    }
    output["payload_sha256"] = object_sha256(output)
    return output


def validate_source_projection(projection: dict, contract: dict) -> dict[str, dict]:
    _validate_payload(projection, "S119 source projection")
    if (set(projection) != {
            "instrument", "schema_version", "status", "source", "row_keys", "rows",
            "payload_sha256",
        } or projection.get("instrument") != "s119_source_contract_projection_v1"
            or projection.get("schema_version") != 1
            or projection.get("status")
            != "MECHANICAL_SOURCE_TRUTH_PROJECTION_NO_RUNTIME_OUTCOMES"):
        raise ValueError("S119 source projection identity is invalid")
    expected_source = contract["external_source"]
    source = projection.get("source") or {}
    if (source.get("logical_path") != expected_source["logical_path"]
            or source.get("sha256") != expected_source["sha256"]
            or source.get("instrument") != "s106_p0_selection_adjudication_v1"
            or projection.get("row_keys") != expected_source["required_row_keys"]):
        raise ValueError("S119 source projection receipt differs from contract")
    rows = projection.get("rows") or []
    by_key: dict[str, dict] = {}
    for row in rows:
        if set(row) != {"row_key", "row_sha256", "source_row"}:
            raise ValueError("S119 projected source row schema is not exact")
        key = row.get("row_key")
        source_row = row.get("source_row") or {}
        if (key in by_key or source_row.get("key") != key
                or not SHA256.fullmatch(str(row.get("row_sha256") or ""))):
            raise ValueError("S119 projected source row identity is invalid")
        if _recursive_keys(source_row) & FORBIDDEN_CONTRACT_KEYS:
            raise ValueError("S119 source projection contains runtime outcome fields")
        by_key[key] = row
    if list(by_key) != projection["row_keys"]:
        raise ValueError("S119 projected source rows are not bijective")
    return by_key


def _index_contexts(contexts: dict) -> tuple[dict[str, dict], dict[tuple[str, str], dict]]:
    rows = contexts.get("rows") or []
    by_qid = {row.get("qid"): row for row in rows}
    if len(by_qid) != len(rows) or None in by_qid:
        raise ValueError("S113 contexts lack unique qids")
    candidates: dict[tuple[str, str], dict] = {}
    for qid, row in by_qid.items():
        context = row.get("context") or []
        ids = [candidate.get("id") for candidate in context]
        if len(ids) != len(set(ids)) or None in ids:
            raise ValueError(f"S113 context candidates are not unique: {qid}")
        for candidate in context:
            candidate_id = candidate["id"]
            candidates[(qid, candidate_id)] = candidate
    return by_qid, candidates


def _index_answers(answers: dict) -> dict[str, dict]:
    rows = answers.get("rows") or []
    by_qid = {row.get("qid"): row for row in rows}
    if len(by_qid) != len(rows) or None in by_qid:
        raise ValueError("S113 answers lack unique qids")
    for qid, row in by_qid.items():
        answer = row.get("answer")
        if answer is None:
            if row.get("executed") is not False or row.get("answer_sha256") is not None:
                raise ValueError(f"S113 missing answer receipt is inconsistent: {qid}")
        else:
            actual = hashlib.sha256(answer.encode("utf-8")).hexdigest()
            if row.get("executed") is not True or row.get("answer_sha256") != actual:
                raise ValueError(f"S113 answer receipt is inconsistent: {qid}")
    return by_qid


def validate_claim_evidence_adjudication(
    adjudication: dict, *, contract: dict, pending: dict[str, dict],
    candidates: dict[tuple[str, str], dict],
) -> dict[str, dict]:
    if (set(adjudication) != EVIDENCE_ADJUDICATION_KEYS
            or adjudication.get("instrument") != "s119_claim_evidence_adjudication_v1"
            or adjudication.get("schema_version") != 1
            or adjudication.get("status") != "frozen_retrospective_source_binding_review"
            or adjudication.get("independent_of_cached_answer_outcome") is not True
            or adjudication.get("review_basis")
            != "source_truth_and_frozen_generator_context_only"):
        raise ValueError("S119 claim evidence adjudication identity is invalid")
    contract_by_id = {row["claim_id"]: row for row in contract["claims"]}
    rows = adjudication.get("rows") or []
    by_id = {row.get("claim_id"): row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != set(contract_by_id):
        raise ValueError("S119 claim evidence adjudication is not bijective")
    validated: dict[str, dict] = {}
    for claim_id, row in by_id.items():
        if set(row) != EVIDENCE_ADJUDICATION_ROW_KEYS:
            raise ValueError(f"S119 evidence adjudication row schema is not exact: {claim_id}")
        claim = contract_by_id[claim_id]
        bridge_claim = pending[claim_id]
        if (row.get("qid") != claim["qid"] or row.get("source_row_key") != claim["source_row_key"]
                or normalized_text_sha256(str(bridge_claim.get("texto") or ""))
                != row.get("claim_text_sha256")
                or normalized_text_sha256(str(bridge_claim.get("valor") or ""))
                != row.get("claim_value_sha256")
                or normalized_text_sha256(str(bridge_claim.get("cita") or ""))
                != row.get("claim_cita_sha256")
                or bridge_claim.get("source_pages") != row.get("claim_source_pages")
                or row.get("page_basis") not in ALLOWED_PAGE_BASES
                or row.get("adjudicator_status") != "accepted"):
            raise ValueError(f"S119 claim evidence adjudication lineage drift: {claim_id}")
        contract_groups = {group["group_id"]: group for group in claim["evidence_groups"]}
        adjudicated_groups = row.get("evidence_groups") or []
        by_group = {group.get("group_id"): group for group in adjudicated_groups}
        if len(by_group) != len(adjudicated_groups) or set(by_group) != set(contract_groups):
            raise ValueError(f"S119 evidence groups are not bijective: {claim_id}")
        group_receipts = {}
        for group_id, group in by_group.items():
            if set(group) != EVIDENCE_ADJUDICATION_GROUP_KEYS:
                raise ValueError(f"S119 evidence adjudication group schema is not exact: {claim_id}")
            accepted_id = group.get("accepted_candidate_id")
            alternative = next(
                (item for item in contract_groups[group_id]["alternatives"]
                 if item["candidate_id"] == accepted_id), None,
            )
            candidate = candidates.get((claim["qid"], accepted_id))
            spans = group.get("support_spans") or []
            if (alternative is None or candidate is None
                    or candidate.get("source_file") != alternative["source_file"]
                    or candidate.get("page_number") != alternative["page_number"]
                    or hashlib.sha256(candidate.get("content", "").encode("utf-8")).hexdigest()
                    != alternative["content_sha256"]
                    or group.get("relation") not in ALLOWED_EVIDENCE_RELATIONS
                    or not spans or any(not isinstance(span, str) or not span for span in spans)):
                raise ValueError(f"S119 accepted evidence binding is invalid: {claim_id}/{group_id}")
            normalized_content = normalize_for_match(candidate.get("content", ""))
            normalized_spans = [normalize_for_match(span) for span in spans]
            if any(not span or span not in normalized_content for span in normalized_spans):
                raise ValueError(f"S119 adjudicated support span is absent: {claim_id}/{group_id}")
            group_receipts[group_id] = {
                "accepted_candidate_id": accepted_id,
                "relation": group["relation"],
                "page_basis": row["page_basis"],
                "support_span_sha256s": [normalized_text_sha256(span) for span in spans],
            }
        validated[claim_id] = group_receipts
    return validated


def validate_cached_answer_adjudication(
    adjudication: dict, *, results: list[dict], answers: dict[str, dict],
) -> None:
    if (set(adjudication) != ANSWER_ADJUDICATION_KEYS
            or adjudication.get("instrument") != "s119_cached_answer_adjudication_v1"
            or adjudication.get("schema_version") != 1
            or adjudication.get("status") != "frozen_retrospective_manual_semantic_review"
            or adjudication.get("reviewed_without_model_calls") is not True
            or adjudication.get("scope") != "exact_s113_cached_answers_only"):
        raise ValueError("S119 cached answer adjudication identity is invalid")
    answer_results = {row["claim_id"]: row for row in results if row["answer_available"]}
    rows = adjudication.get("rows") or []
    by_id = {row.get("claim_id"): row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != set(answer_results):
        raise ValueError("S119 cached answer adjudication is not bijective")
    for claim_id, row in by_id.items():
        if set(row) != ANSWER_ADJUDICATION_ROW_KEYS:
            raise ValueError(f"S119 cached answer adjudication row schema is not exact: {claim_id}")
        result = answer_results[claim_id]
        answer = answers[result["qid"]]
        if (row.get("qid") != result["qid"]
                or row.get("answer_sha256") != answer.get("answer_sha256")
                or row.get("verdict") not in {"OK", "synthesis-miss"}
                or row.get("verdict") != result["stage_bucket"]
                or not str(row.get("rationale") or "").strip()):
            raise ValueError(f"S119 cached answer semantic verdict drift: {claim_id}")


def _pattern_rows(patterns: list[str], normalized: str) -> list[dict]:
    return [
        {"pattern": pattern, "matched": bool(_compile_pattern(pattern).search(normalized))}
        for pattern in patterns
    ]


def _coverage_pattern_rows(patterns: list[str], answer: str) -> list[dict]:
    """Match inside one line or one adjacent pair, never across a blank/section gap."""
    raw_lines = answer.splitlines()
    lines = [normalize_for_match(line) for line in raw_lines]
    windows: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        if not line:
            continue
        windows.append((index + 1, 1, line))
        if index + 1 < len(lines) and lines[index + 1]:
            windows.append((index + 1, 2, f"{line} {lines[index + 1]}"))
    rows = []
    for pattern in patterns:
        compiled = _compile_pattern(pattern)
        matched_window = next(
            (window for window in windows if compiled.search(window[2])), None,
        )
        rows.append({
            "pattern": pattern,
            "matched": matched_window is not None,
            "matched_line_start": matched_window[0] if matched_window else None,
            "matched_line_count": matched_window[1] if matched_window else None,
        })
    return rows


def build_replay(
    *, contract: dict, bridge: dict, gate: dict, contexts: dict, answers: dict,
    projection: dict, claim_evidence_adjudication: dict,
    cached_answer_adjudication: dict, input_receipts: dict,
) -> dict:
    validate_contract(contract)
    validate_source_projection(projection, contract)
    _validate_payload(bridge, "S118 bridge")
    if (bridge.get("instrument") != "s118_atomic_benchmark_bridge_v1"
            or bridge.get("status") != "HYBRID_DIAGNOSTIC_BRIDGE_NO_OFFICIAL_ATOMIC_CREDIT"
            or (bridge.get("summary") or {}).get("official_atomic_content_denominator") is not None
            or gate.get("status") != "HYBRID_DIAGNOSTIC_BRIDGE_GO_REPLAY_DESIGN_ONLY"
            or (gate.get("decision") or {}).get("local_replay_design_for_22_transformed_claims") != "GO"
            or (gate.get("decision") or {}).get("official_atomic_denominator") != "NO_GO"):
        raise ValueError("S118 authority does not permit this bounded replay")

    pending = {
        row.get("claim_id"): row for row in bridge.get("claims") or []
        if row.get("stage_bucket") == "pending-replay"
    }
    contract_claims = contract["claims"]
    contract_ids = [row["claim_id"] for row in contract_claims]
    if (len(pending) != len(contract_ids) or set(pending) != set(contract_ids)
            or len(contract_ids) != len(set(contract_ids))):
        raise ValueError("S119 contract is not bijective with S118 pending claims")
    if len(pending) != contract["expected_population"]["pending_claims"]:
        raise ValueError("S119 pending population count drift")

    context_by_qid, candidates = _index_contexts(contexts)
    answer_by_qid = _index_answers(answers)
    if answers.get("frozen_contexts_sha256") != contexts.get("frozen_contexts_sha256"):
        raise ValueError("S113 answers and contexts do not share the same freeze")
    for qid, answer_row in answer_by_qid.items():
        context_row = context_by_qid.get(qid)
        if (context_row is None
                or answer_row.get("serving_context_sha256")
                != context_row.get("serving_context_sha256")):
            raise ValueError(f"S113 answer/context per-qid receipt mismatch: {qid}")
    evidence_bindings = validate_claim_evidence_adjudication(
        claim_evidence_adjudication, contract=contract, pending=pending,
        candidates=candidates,
    )

    results: list[dict] = []
    for claim in contract_claims:
        claim_id, qid = claim["claim_id"], claim["qid"]
        bridge_claim = pending[claim_id]
        expected_parent = contract["parent_fact_key_overrides"].get(
            claim_id, claim["source_row_key"],
        )
        if (bridge_claim.get("qid") != qid
                or bridge_claim.get("parent_fact_key") != expected_parent
                or qid not in context_by_qid or qid not in answer_by_qid):
            raise ValueError(f"S119 claim lineage drift: {claim_id}")
        evidence_rows = []
        all_groups_matched = True
        for group in claim["evidence_groups"]:
            accepted_binding = evidence_bindings[claim_id][group["group_id"]]
            alternatives = []
            matched_candidate_id = None
            for alternative in group["alternatives"]:
                candidate_id = alternative["candidate_id"]
                indexed = candidates.get((qid, candidate_id))
                identity_match = bool(
                    indexed
                    and indexed.get("source_file") == alternative["source_file"]
                    and indexed.get("page_number") == alternative["page_number"]
                    and hashlib.sha256(indexed.get("content", "").encode("utf-8")).hexdigest()
                    == alternative["content_sha256"]
                )
                pattern_receipts = []
                if identity_match:
                    pattern_receipts = _pattern_rows(
                        alternative["match_patterns"],
                        normalize_for_match(indexed["content"]),
                    )
                matched = identity_match and all(row["matched"] for row in pattern_receipts)
                alternatives.append({
                    "candidate_id": candidate_id,
                    "identity_match": identity_match,
                    "content_sha256": alternative["content_sha256"],
                    "pattern_receipts": pattern_receipts,
                    "matched": matched,
                })
                if (matched and candidate_id == accepted_binding["accepted_candidate_id"]
                        and matched_candidate_id is None):
                    matched_candidate_id = candidate_id
            group_matched = matched_candidate_id is not None
            all_groups_matched &= group_matched
            evidence_rows.append({
                "group_id": group["group_id"],
                "matched": group_matched,
                "matched_candidate_id": matched_candidate_id,
                "adjudicated_binding": accepted_binding,
                "alternatives": alternatives,
            })

        answer_row = answer_by_qid[qid]
        answer = answer_row.get("answer")
        answer_available = answer is not None
        coverage_rows = []
        coverage_passed = False
        if answer_available:
            coverage_rows = _coverage_pattern_rows(
                claim["synthesis"]["coverage_patterns"], answer,
            )
            coverage_passed = all(row["matched"] for row in coverage_rows)

        if not all_groups_matched:
            stage_bucket = "evidence-binding-unresolved"
            stage_status = "source_bound_support_not_proven_in_frozen_generator_context"
        elif not answer_available:
            stage_bucket = "synthesis-not-measured"
            stage_status = "generator_support_present_but_no_exact_frozen_answer"
        elif not coverage_passed:
            stage_bucket = "synthesis-miss"
            stage_status = "generator_support_present_cached_answer_lacks_claim_coverage"
        else:
            stage_bucket = "OK"
            stage_status = "generator_support_and_cached_answer_coverage_pass"

        results.append({
            "claim_id": claim_id,
            "qid": qid,
            "parent_fact_key": bridge_claim["parent_fact_key"],
            "source_row_key": claim["source_row_key"],
            "source_projection_row_sha256": next(
                row["row_sha256"] for row in projection["rows"]
                if row["row_key"] == claim["source_row_key"]
            ),
            "generator_support": all_groups_matched,
            "evidence_groups": evidence_rows,
            "answer_available": answer_available,
            "answer_sha256": answer_row.get("answer_sha256"),
            "coverage_passed": coverage_passed if answer_available else None,
            "coverage_receipts": coverage_rows,
            "stage_bucket": stage_bucket,
            "stage_status": stage_status,
        })

    validate_cached_answer_adjudication(
        cached_answer_adjudication, results=results, answers=answer_by_qid,
    )

    histogram = Counter(row["stage_bucket"] for row in results)
    bridge_histogram = Counter((bridge.get("summary") or {}).get(
        "provisional_hybrid_stage_histogram") or {})
    if bridge_histogram.get("pending-replay") != len(results):
        raise ValueError("S118 pending histogram does not reconcile with S119 replay")
    del bridge_histogram["pending-replay"]
    bridge_histogram.update(histogram)
    observed_ok = histogram.get("OK", 0)
    summary = {
        "cohort_claims": len(results),
        "cohort_qids": len({row["qid"] for row in results}),
        "generator_support_present": sum(row["generator_support"] for row in results),
        "evidence_binding_unresolved": histogram.get("evidence-binding-unresolved", 0),
        "cached_answers_available": sum(row["answer_available"] for row in results),
        "cached_answers_missing": sum(not row["answer_available"] for row in results),
        "cached_claims_observed_ok": observed_ok,
        "cached_replay_synthesis_miss": histogram.get("synthesis-miss", 0),
        "synthesis_not_measured": histogram.get("synthesis-not-measured", 0),
        "facts_moved_to_ok_by_runtime_change": 0,
        "causal_bot_improvement_claimed": False,
        "cohort_stage_histogram": dict(sorted(histogram.items())),
        "provisional_hybrid_stage_histogram_after_cached_replay": dict(
            sorted(bridge_histogram.items())
        ),
        "provisional_hybrid_content_denominator": (
            bridge.get("summary") or {}).get("provisional_hybrid_content_denominator"),
        "official_atomic_content_denominator": None,
        "official_atomic_target_ok_for_95_percent": None,
        "official_ok_after_replay": None,
    }
    if sum(histogram.values()) != len(results) or sum(bridge_histogram.values()) != summary[
        "provisional_hybrid_content_denominator"
    ]:
        raise ValueError("S119 replay denominator does not reconcile")

    output = {
        "instrument": "s119_cached_atomic_replay_v1",
        "schema_version": 1,
        "status": "CACHED_REPLAY_DIAGNOSTIC_NO_OFFICIAL_ATOMIC_CREDIT",
        "authority": contract["authority"],
        "input_receipts": input_receipts,
        "policy": contract["policy"],
        "summary": summary,
        "claim_results": sorted(results, key=lambda row: row["claim_id"]),
        "authorization": contract["authorization"],
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
        "limitations": [
            "retrospective cached replay; not a prospective holdout",
            "observed OK classifications are retrospective and not caused by a runtime change",
            "hybrid histogram is diagnostic only and not an official benchmark score",
            "missing answers are not synthesis failures",
            "official atomic denominator and 95 percent target remain blocked",
        ],
    }
    output["payload_sha256"] = object_sha256(output)
    return output


def freeze_source_projection_execute(
    *, root: Path, contract_path: Path, external_source_path: Path, output_path: Path,
) -> dict:
    root = root.resolve()
    contract_path = contract_path.resolve()
    external_source_path = external_source_path.resolve()
    contract = load_yaml(contract_path)
    validate_contract(contract, allow_pending_projection=True)
    _assert_hash(
        external_source_path, contract["external_source"]["sha256"], "S106 external source",
    )
    projection = build_source_projection(load_yaml(external_source_path), contract)
    expected_projection_sha = contract["frozen_inputs"]["source_projection"]["sha256"]
    if expected_projection_sha != "PENDING_AFTER_MECHANICAL_FREEZE":
        serialized = (
            json.dumps(projection, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        actual_projection_sha = hashlib.sha256(serialized).hexdigest()
        if actual_projection_sha != expected_projection_sha:
            raise ValueError(
                "regenerated source projection differs from frozen contract: "
                f"{actual_projection_sha} != {expected_projection_sha}"
            )
    output_path = _assert_safe_output(
        root, output_path, {contract_path, external_source_path},
        "evals/s119_source_contract_projection_v1.json",
    )
    _write_json(output_path, projection)
    return projection


def execute(*, root: Path, contract_path: Path, output_path: Path) -> dict:
    root = root.resolve()
    contract_path = contract_path.resolve()
    contract = load_yaml(contract_path)
    validate_contract(contract)
    paths = {
        key: _resolve_inside_root(root, ref, key)
        for key, ref in contract["frozen_inputs"].items()
    }
    for key, path in paths.items():
        _assert_hash(path, contract["frozen_inputs"][key]["sha256"], key)
    input_receipts = {
        "contract": {
            "path": str(contract_path.relative_to(root)).replace("\\", "/"),
            "sha256": file_sha256(contract_path),
        },
        **contract["frozen_inputs"],
        "external_source": contract["external_source"],
    }
    replay = build_replay(
        contract=contract,
        bridge=load_json(paths["s118_bridge"]),
        gate=load_yaml(paths["s118_gate"]),
        contexts=load_json(paths["s113_contexts"]),
        answers=load_json(paths["s113_answers"]),
        projection=load_json(paths["source_projection"]),
        claim_evidence_adjudication=load_yaml(paths["claim_evidence_adjudication"]),
        cached_answer_adjudication=load_yaml(paths["cached_answer_adjudication"]),
        input_receipts=input_receipts,
    )
    output_path = _assert_safe_output(
        root, output_path, {contract_path, *paths.values()},
        "evals/s119_cached_atomic_replay_v1.json",
    )
    _write_json(output_path, replay)
    return replay


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--contract", type=Path,
        default=ROOT / "evals/s119_cached_atomic_replay_contract_v1.yaml",
    )
    parser.add_argument("--freeze-source-projection", action="store_true")
    parser.add_argument("--external-source", type=Path)
    parser.add_argument(
        "--projection-output", type=Path,
        default=ROOT / "evals/s119_source_contract_projection_v1.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "evals/s119_cached_atomic_replay_v1.json",
    )
    args = parser.parse_args()
    if args.freeze_source_projection:
        if args.external_source is None:
            parser.error("--external-source is required with --freeze-source-projection")
        freeze_source_projection_execute(
            root=args.root, contract_path=args.contract,
            external_source_path=args.external_source,
            output_path=args.projection_output,
        )
    else:
        execute(root=args.root, contract_path=args.contract, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
