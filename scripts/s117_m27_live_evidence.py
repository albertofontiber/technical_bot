#!/usr/bin/env python3
"""Build deterministic, offline evidence for the 21 M2.7 live tasks.

The runner does not adjudicate.  It never reads env files, connects to a
database, calls a model, changes policy, or authorizes M3/load/serving.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from scripts import s117_m2_legacy_reuse_analysis as m2
from scripts import s117_m26_independent_reuse_audit as m26
from scripts import s117_m27_upstream_sql_budget_v2 as m27
from scripts import s117_materialize_chunks_v3_local as replay
from src.reingest import chunk as chunk_module
from src.reingest import chunk_provenance as provenance
from src.reingest import retrieval_policy


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m27_live_evidence_prereg_v1.yaml"
_SHA256 = set("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= _SHA256
    )


def _strict_json_bytes(raw: bytes) -> dict[str, Any]:
    parsed = json.loads(
        raw,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {value}")
        ),
    )
    if not isinstance(parsed, dict):
        raise ValueError("JSON root must be an object")
    return parsed


def _surface(text: str) -> str:
    """The only normalization allowed by the M2.7A alignment contract."""
    return " ".join(text.split())


def _first_surface_mismatch(
    raw_text: str, v3_text: str, *, radius: int = 8
) -> dict[str, Any] | None:
    raw_tokens = raw_text.split()
    v3_tokens = v3_text.split()
    limit = min(len(raw_tokens), len(v3_tokens))
    index = next(
        (position for position in range(limit) if raw_tokens[position] != v3_tokens[position]),
        limit if len(raw_tokens) != len(v3_tokens) else None,
    )
    if index is None:
        return None
    start = max(0, index - radius)
    return {
        "token_index": index,
        "raw_token_count": len(raw_tokens),
        "v3_token_count": len(v3_tokens),
        "raw_token": raw_tokens[index] if index < len(raw_tokens) else None,
        "v3_token": v3_tokens[index] if index < len(v3_tokens) else None,
        "raw_context": raw_tokens[start : index + radius + 1],
        "v3_context": v3_tokens[start : index + radius + 1],
    }


def _manifest(rows: list[dict[str, Any]], key: str) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item[key]):
        digest.update(_canonical(row) + b"\n")
    return digest.hexdigest()


def _iter_hashed_paths(value: Any):
    if isinstance(value, dict):
        if set(("path", "sha256")) <= set(value):
            yield value
        for child in value.values():
            yield from _iter_hashed_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_hashed_paths(child)


def _anchor(anchor: Any) -> dict[str, Any] | None:
    if anchor is None:
        return None
    return {
        "heading_text": anchor.heading_text,
        "title": anchor.title,
        "level": anchor.level,
        "source_page": anchor.source_page,
        "source_block_index": anchor.source_block_index,
        "heading_sha256": anchor.heading_sha256,
    }


def _block_row(block: Any) -> dict[str, Any]:
    core = {
        "source_block_index": block.source_block_index,
        "kind": block.kind,
        "page": block.page,
        "text": block.text,
        "text_sha256": _sha_bytes(block.text.encode("utf-8")),
        "lineage": [_anchor(item) for item in block.lineage],
    }
    return {**core, "receipt_sha256": _sha_bytes(_canonical(core))}


def _structural_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "id",
            "materialization_id",
            "extraction_sha256",
            "chunk_index",
            "content",
            "content_sha256",
            "provenance_version",
            "provenance_contract",
            "raw_artifact_sha256",
            "chunker_sha256",
            "provenance_payload_sha256",
            "source_block_start",
            "source_block_end",
            "section_anchor",
            "section_lineage",
            "section_title",
            "section_path",
            "page_number",
            "is_flow_diagram",
            "has_diagram",
            "confidence",
            "duplicate_of",
        )
    }


def _chunk_row(row: dict[str, Any]) -> dict[str, Any]:
    core = _structural_row(row)
    core["content_sha256"] = _sha_bytes(row["content"].encode("utf-8"))
    return {**core, "receipt_sha256": _sha_bytes(_canonical(core))}


def _overlapping_rows(
    rows: list[dict[str, Any]], target: dict[str, Any]
) -> list[dict[str, Any]]:
    start = target["source_block_start"]
    end = target["source_block_end"]
    return sorted(
        (
            row
            for row in rows
            if row["source_block_start"] <= end
            and row["source_block_end"] >= start
        ),
        key=lambda row: row["chunk_index"],
    )


def _block_window(
    blocks: list[dict[str, Any]], overlapping: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int | None]]:
    first = min(row["source_block_start"] for row in overlapping)
    last = max(row["source_block_end"] for row in overlapping)
    window_start = max(0, first - 1)
    window_end = min(len(blocks) - 1, last + 1)
    return (
        blocks[window_start : window_end + 1],
        {
            "overlap_start": first,
            "overlap_end": last,
            "previous_boundary": first - 1 if first > 0 else None,
            "next_boundary": last + 1 if last + 1 < len(blocks) else None,
        },
    )


def _legacy_document_receipt(
    extraction_sha256: str, donors: list[dict[str, Any]]
) -> dict[str, Any]:
    rows = sorted(
        donors,
        key=lambda row: (
            row.get("chunk_index") is None,
            row.get("chunk_index"),
            row.get("id") or "",
        ),
    )
    core = {
        "schema": "s117_m27_full_legacy_document_evidence_v1",
        "extraction_sha256": extraction_sha256,
        "donor_count": len(rows),
        "donor_rows": rows,
        "donor_manifest_sha256": _manifest(rows, "id"),
    }
    return {**core, "receipt_sha256": _sha_bytes(_canonical(core))}


def _evaluated_policy_rules(
    preterminal: str | None, duplicate_of: Any
) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "policy_excluded_register_only",
            "predicate": "preterminal == policy_excluded_register_only",
            "matched": preterminal == "policy_excluded_register_only",
        },
        {
            "rule_id": "policy_excluded_language",
            "predicate": "preterminal == policy_excluded_language",
            "matched": preterminal == "policy_excluded_language",
        },
        {
            "rule_id": "duplicate",
            "predicate": "preterminal is null and duplicate_of is not null",
            "matched": preterminal is None and duplicate_of is not None,
        },
        {
            "rule_id": "eligible",
            "predicate": "preterminal is null and duplicate_of is null",
            "matched": preterminal is None and duplicate_of is None,
        },
    ]


def _policy_receipt(
    local: dict[str, Any],
    m26_row: dict[str, Any],
    policy_contract_sha256: str,
) -> dict[str, Any]:
    policy_class = retrieval_policy.classify(
        local.get("preterminal"), local.get("duplicate_of")
    )
    core = {
        "extraction_sha256": local["extraction_sha256"],
        "chunk_index": local["chunk_index"],
        "retrieval_policy_class": policy_class,
        "language": local.get("language"),
        "duplicate_of": local.get("duplicate_of"),
        "policy_contract_sha256": policy_contract_sha256,
    }
    receipt_sha256 = _sha_bytes(_canonical(core))
    if (
        policy_class != m26_row["retrieval_policy_class"]
        or receipt_sha256 != m26_row["policy_receipt_sha256"]
    ):
        raise RuntimeError("M2.6 policy receipt did not reproduce")
    selected_rule_by_class = {
        "register_only": "policy_excluded_register_only",
        "unsupported_language": "policy_excluded_language",
        "duplicate": "duplicate",
        "eligible": "eligible",
    }
    evaluated_rules = _evaluated_policy_rules(
        local.get("preterminal"), local.get("duplicate_of")
    )
    matched_rules = [row["rule_id"] for row in evaluated_rules if row["matched"]]
    selected_rule_id = selected_rule_by_class[policy_class]
    if matched_rules != [selected_rule_id]:
        raise RuntimeError("frozen policy predicates are not closed")
    contract_payload = retrieval_policy.contract_payload()
    wrapper_core = {
        "schema": "s117_m27_frozen_policy_evidence_v1",
        "version": 1,
        "policy_contract_payload": contract_payload,
        "policy_contract_payload_sha256": _sha_bytes(_canonical(contract_payload)),
        "policy_contract_sha256": policy_contract_sha256,
        "extraction_sha256": local["extraction_sha256"],
        "chunk_index": local["chunk_index"],
        "language": local.get("language"),
        "preterminal": local.get("preterminal"),
        "duplicate_of": local.get("duplicate_of"),
        "evaluated_rules": evaluated_rules,
        "selected_rule_id": selected_rule_id,
        "retrieval_policy_class": policy_class,
        "m26_policy_receipt_sha256": receipt_sha256,
        "m26_row_receipt_sha256": m26_row["receipt_sha256"],
    }
    return {
        **wrapper_core,
        "receipt_sha256": _sha_bytes(_canonical(wrapper_core)),
    }


def _receipt_valid(receipt: dict[str, Any]) -> bool:
    expected = receipt.get("receipt_sha256")
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return _is_sha256(expected) and expected == _sha_bytes(_canonical(core))


def _document_receipt_valid(receipt: dict[str, Any]) -> bool:
    try:
        raw = base64.b64decode(receipt["raw_artifact_base64"], validate=True)
        blocks = receipt["raw_blocks"]
        rows = receipt["v3_rows"]
        raw_stream = "\n\n".join(row["text"] for row in blocks)
        v3_stream = "\n\n".join(row["content"] for row in rows)
        stream_equal = _surface(raw_stream) == _surface(v3_stream)
        derived_alignment = (
            "exact_whitespace_equivalent"
            if receipt["row_by_row_regeneration_equal"]
            and not receipt["independent_validation_failures"]
            and stream_equal
            else "unresolved"
        )
        return bool(
            _receipt_valid(receipt)
            and len({row["source_block_index"] for row in blocks}) == len(blocks)
            and len({row["id"] for row in rows}) == len(rows)
            and len({row["chunk_index"] for row in rows}) == len(rows)
            and all(_receipt_valid(row) for row in (*blocks, *rows))
            and receipt["raw_artifact_bytes"] == len(raw)
            and receipt["raw_artifact_sha256"] == _sha_bytes(raw)
            and receipt["raw_block_manifest_sha256"]
            == _manifest(blocks, "source_block_index")
            and receipt["v3_row_manifest_sha256"] == _manifest(rows, "chunk_index")
            and receipt["raw_surface_sha256"]
            == _sha_bytes(_surface(raw_stream).encode("utf-8"))
            and receipt["v3_surface_sha256"]
            == _sha_bytes(_surface(v3_stream).encode("utf-8"))
            and receipt["document_stream_whitespace_equal"] == stream_equal
            and receipt["first_surface_mismatch"]
            == _first_surface_mismatch(raw_stream, v3_stream)
            and receipt["alignment_status"] == derived_alignment
        )
    except (KeyError, TypeError, ValueError):
        return False


def _legacy_receipt_valid(receipt: dict[str, Any]) -> bool:
    try:
        rows = receipt["donor_rows"]
        return bool(
            _receipt_valid(receipt)
            and receipt["donor_count"] == len(rows)
            and len({row["id"] for row in rows}) == len(rows)
            and all(
                row.get("extraction_sha256") == receipt["extraction_sha256"]
                for row in rows
            )
            and receipt["donor_manifest_sha256"] == _manifest(rows, "id")
        )
    except (KeyError, TypeError, ValueError):
        return False


def _policy_wrapper_valid(
    receipt: dict[str, Any], expected_policy_contract_sha256: str
) -> bool:
    try:
        rules = receipt["evaluated_rules"]
        matched = [row["rule_id"] for row in rules if row["matched"]]
        expected_rules = _evaluated_policy_rules(
            receipt["preterminal"], receipt["duplicate_of"]
        )
        expected_class = retrieval_policy.classify(
            receipt["preterminal"], receipt["duplicate_of"]
        )
        m26_policy_core = {
            "extraction_sha256": receipt["extraction_sha256"],
            "chunk_index": receipt["chunk_index"],
            "retrieval_policy_class": expected_class,
            "language": receipt["language"],
            "duplicate_of": receipt["duplicate_of"],
            "policy_contract_sha256": expected_policy_contract_sha256,
        }
        selected_by_class = {
            "register_only": "policy_excluded_register_only",
            "unsupported_language": "policy_excluded_language",
            "duplicate": "duplicate",
            "eligible": "eligible",
        }
        return bool(
            _receipt_valid(receipt)
            and receipt["version"] == 1
            and receipt["policy_contract_payload"]
            == retrieval_policy.contract_payload()
            and receipt["policy_contract_sha256"]
            == expected_policy_contract_sha256
            and receipt["policy_contract_payload_sha256"]
            == _sha_bytes(_canonical(receipt["policy_contract_payload"]))
            and [row["rule_id"] for row in rules]
            == list(retrieval_policy.POLICY_PRECEDENCE)
            and rules == expected_rules
            and matched == [receipt["selected_rule_id"]]
            and receipt["retrieval_policy_class"] == expected_class
            and receipt["selected_rule_id"] == selected_by_class[expected_class]
            and receipt["m26_policy_receipt_sha256"]
            == _sha_bytes(_canonical(m26_policy_core))
        )
    except (KeyError, TypeError, ValueError):
        return False


def _evidence_crosslinked(
    *,
    task_evidence: list[dict[str, Any]],
    review_fiches: list[dict[str, Any]],
    document_receipts: list[dict[str, Any]],
    legacy_receipts: list[dict[str, Any]],
    original_raw: dict[str, dict[str, Any]],
    comparisons: dict[str, dict[str, Any]],
    original_tasks: dict[str, dict[str, Any]],
    m26_rows: dict[str, dict[str, Any]],
    policy_contract_sha256: str,
) -> bool:
    documents = {row["receipt_sha256"]: row for row in document_receipts}
    legacies = {row["receipt_sha256"]: row for row in legacy_receipts}
    tasks = {row["local_row_id"]: row for row in task_evidence}
    fiches = {row["local_row_id"]: row for row in review_fiches}
    if any((
        len(documents) != len(document_receipts),
        len(legacies) != len(legacy_receipts),
        len(tasks) != len(task_evidence),
        len(fiches) != len(review_fiches),
        set(tasks) != set(fiches),
    )):
        return False
    if (
        not all(_document_receipt_valid(row) for row in document_receipts)
        or not all(_legacy_receipt_valid(row) for row in legacy_receipts)
        or not all(_receipt_valid(row) for row in task_evidence)
    ):
        return False
    for local_id, task in tasks.items():
        original_task = original_tasks.get(local_id)
        m26_row = m26_rows.get(local_id)
        document = documents.get(task["raw_document_receipt_sha256"])
        document_targets = (
            []
            if document is None
            else [row for row in document["v3_rows"] if row["id"] == local_id]
        )
        expected_overlap = (
            []
            if len(document_targets) != 1
            else _overlapping_rows(document["v3_rows"], document_targets[0])
        )
        expected_window = ([], {})
        if document is not None and expected_overlap:
            expected_window = _block_window(document["raw_blocks"], expected_overlap)
        if (
            document is None
            or original_task is None
            or m26_row is None
            or document["extraction_sha256"] != task["extraction_sha256"]
            or task["mechanical_raw_alignment"] != document["alignment_status"]
            or len(document_targets) != 1
            or task["target_row"]["id"] != local_id
            or task["target_row"] != document_targets[0]
            or task["original_task_receipt_sha256"]
            != original_task["task_receipt_sha256"]
            or not _receipt_valid(task["target_row"])
            or not task["legacy_evidence_completion_verified"]
            or not task["evidence_complete"]
            or task["overlapping_v3_rows"] != expected_overlap
            or not all(_receipt_valid(row) for row in task["overlapping_v3_rows"])
            or task["overlap_manifest_sha256"]
            != _manifest(task["overlapping_v3_rows"], "chunk_index")
            or task["raw_block_window"] != expected_window[0]
            or not all(_receipt_valid(row) for row in task["raw_block_window"])
            or task["boundary"] != expected_window[1]
            or task["raw_block_window_manifest_sha256"]
            != _manifest(task["raw_block_window"], "source_block_index")
            or task["comparison_receipt_sha256"]
            != comparisons[local_id]["receipt_sha256"]
            or task["original_raw_evidence_sha256"]
            != original_raw[local_id]["receipt_sha256"]
            or not _receipt_valid(comparisons[local_id])
            or not _receipt_valid(original_raw[local_id])
            or not _policy_wrapper_valid(
                task["frozen_policy_evidence"], policy_contract_sha256
            )
            or task["frozen_policy_evidence"]["extraction_sha256"]
            != task["extraction_sha256"]
            or task["frozen_policy_evidence"]["chunk_index"]
            != task["target_row"]["chunk_index"]
            or not _receipt_valid(m26_row)
            or task["frozen_policy_evidence"]["m26_row_receipt_sha256"]
            != m26_row["receipt_sha256"]
            or task["frozen_policy_evidence"]["m26_policy_receipt_sha256"]
            != m26_row["policy_receipt_sha256"]
            or task["frozen_policy_evidence"]["retrieval_policy_class"]
            != m26_row["retrieval_policy_class"]
        ):
            return False
        if task["legacy_evidence_mode"] == "m27_original_complete":
            if task["legacy_evidence_receipt_sha256"] != original_raw[local_id]["receipt_sha256"]:
                return False
        elif task["legacy_evidence_mode"] == "full_legacy_document_materialized":
            legacy = legacies.get(task["legacy_evidence_receipt_sha256"])
            if legacy is None or legacy["extraction_sha256"] != task["extraction_sha256"]:
                return False
        else:
            return False
        fiche = fiches[local_id]
        if (
            fiche["task_evidence_receipt_sha256"] != task["receipt_sha256"]
            or fiche["comparison_receipt_sha256"] != task["comparison_receipt_sha256"]
            or fiche["mechanical_raw_alignment"] != task["mechanical_raw_alignment"]
            or fiche["reason"] != original_task["reason"]
            or fiche["candidate_method"] != original_task["candidate_method"]
            or fiche["local_content"] != task["target_row"]["content"]
            or fiche["local_protected_tokens"]
            != original_raw[local_id]["local_protected_tokens"]
            or fiche["raw_block_window"] != task["raw_block_window"]
            or fiche["overlapping_v3_chunk_indexes"]
            != [row["chunk_index"] for row in task["overlapping_v3_rows"]]
            or fiche["original_donor_evidence"]
            != original_raw[local_id]["donors"]
            or fiche["policy_class_under_frozen_contract"]
            != task["frozen_policy_evidence"]["retrieval_policy_class"]
            or fiche["review_status"] != "not_authorized"
            or fiche["legacy_full_document_receipt_sha256"]
            != (
                task["legacy_evidence_receipt_sha256"]
                if task["legacy_evidence_mode"]
                == "full_legacy_document_materialized"
                else None
            )
        ):
            return False
    return True


def _validate_seed(seed: dict[str, Any]) -> None:
    if (
        seed.get("instrument") != "s117_m27_upstream_sql_budget_v2"
        or seed.get("contract_integrity") != "GO"
        or seed.get("local_readiness") != "NO_GO"
    ):
        raise RuntimeError("M2.7 v2 seed status drift")
    tasks = seed["task_manifest"]["rows"]
    task_ids = [row["local_row_id"] for row in tasks]
    comparison_ids = [row["local_row_id"] for row in seed["comparison_receipts"]]
    raw_ids = [row["local_row_id"] for row in seed["raw_evidence_receipts"]]
    audit_ids = [row["local_row_id"] for row in seed["audit_rows"]]
    if (
        len(task_ids) != len(set(task_ids))
        or len(comparison_ids) != len(set(comparison_ids))
        or len(raw_ids) != len(set(raw_ids))
        or len(audit_ids) != len(set(audit_ids))
        or set(task_ids) != set(raw_ids)
        or not set(task_ids) <= set(comparison_ids)
    ):
        raise RuntimeError("M2.7 seed identity sets are not closed")
    if seed["task_manifest"]["sha256"] != _manifest(
        tasks, "task_receipt_sha256"
    ):
        raise RuntimeError("M2.7 task manifest drift")
    manifests = seed["manifests"]
    if (
        manifests["audit_rows_sha256"] != _manifest(seed["audit_rows"], "local_row_id")
        or manifests["comparison_receipts_sha256"]
        != _manifest(seed["comparison_receipts"], "local_row_id")
        or manifests["raw_evidence_receipts_sha256"]
        != _manifest(seed["raw_evidence_receipts"], "local_row_id")
    ):
        raise RuntimeError("M2.7 seed receipt manifest drift")
    if not m27._receipts_crosslinked(
        tasks,
        seed["comparison_receipts"],
        seed["raw_evidence_receipts"],
    ):
        raise RuntimeError("M2.7 evidence receipts no longer crosslink")


def _load_prereg(prereg_path: Path) -> dict[str, Any]:
    if prereg_path.resolve() != DEFAULT_PREREG.resolve():
        raise RuntimeError("M2.7A prereg path mismatch")
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("instrument") != "s117_m27_live_evidence_prereg_v1"
        or prereg.get("status") != "frozen_before_seeded_evidence"
    ):
        raise RuntimeError("M2.7A prereg drift")
    for item in _iter_hashed_paths(prereg.get("frozen_inputs", {})):
        path = (ROOT / item["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("M2.7A frozen input escapes workspace") from exc
        if _sha_file(path) != item["sha256"]:
            raise RuntimeError(f"M2.7A frozen input drift: {item['path']}")
    selected = prereg.get("selected_paths", {})
    bindings = prereg.get("selected_path_bindings", {})
    frozen = prereg.get("frozen_inputs", {})
    if set(selected) != set(bindings):
        raise RuntimeError("M2.7A selected path binding set drift")
    for selected_name, frozen_name in bindings.items():
        frozen_item = frozen.get(frozen_name)
        if (
            not isinstance(frozen_item, dict)
            or not isinstance(frozen_item.get("path"), str)
            or not _is_sha256(frozen_item.get("sha256"))
            or selected[selected_name] != frozen_item.get("path")
        ):
            raise RuntimeError("M2.7A selected path is not hash-bound")
    return prereg


def build_evidence(
    *,
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
    seed: int,
) -> dict[str, Any]:
    prereg = _load_prereg(prereg_path)
    if seed not in prereg["execution"]["seeds"]:
        raise RuntimeError("unregistered M2.7A seed")

    seed1_path = ROOT / prereg["selected_paths"]["m27_seed1"]
    seed2_path = ROOT / prereg["selected_paths"]["m27_seed2"]
    seed1_raw = seed1_path.read_bytes()
    seed2_raw = seed2_path.read_bytes()
    if seed1_raw != seed2_raw:
        raise RuntimeError("M2.7 v2 seeds are no longer byte-identical")
    m27_seed = _strict_json_bytes(seed1_raw)
    _validate_seed(m27_seed)

    _, m2_state = m27.preflight(
        ROOT / prereg["selected_paths"]["m27_prereg"],
        store,
        sidecar_root,
        source_snapshot,
    )
    development_path = ROOT / prereg["selected_paths"]["development_result"]
    development = json.loads(development_path.read_text(encoding="utf-8"))
    materialization_id = development["generation"]["materialization_id"]
    chunker_sha256 = development["dependencies"]["chunker_sha256"]

    local_rows, local_receipt = m2.build_local_population(
        m2_state["record_files"],
        development_path,
        chunker_sha256,
        sidecar_root,
    )
    if local_receipt != m27_seed["source"]["local"]:
        raise RuntimeError("local materialization no longer matches M2.7 seed")

    _, _, snapshot_chunks, snapshot_receipt = m2.read_snapshot(source_snapshot)
    if snapshot_receipt != m27_seed["source"]["snapshot"]:
        raise RuntimeError("legacy snapshot no longer matches M2.7 seed")
    base_donors = [row for row in snapshot_chunks if row.get("parent_id") is None]
    donors_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in base_donors:
        donors_by_sha[row.get("extraction_sha256")].append(row)

    m26_result = json.loads(
        (ROOT / prereg["selected_paths"]["m26_result"]).read_text(encoding="utf-8")
    )
    m26_rows = {row["local_row_id"]: row for row in m26_result["rows"]}
    m26_prereg = yaml.safe_load(
        (ROOT / prereg["selected_paths"]["m26_prereg"]).read_text(encoding="utf-8")
    )
    policy_contract_sha256 = m26._policy_contract_sha256(m26_prereg)

    all_tasks = m27_seed["task_manifest"]["rows"]
    live_tasks = [task for task in all_tasks if task["cohort"] == "live"]
    rng = random.Random(seed)
    rng.shuffle(live_tasks)
    rng.shuffle(local_rows)
    rng.shuffle(base_donors)
    if len(live_tasks) != prereg["expected"]["live_tasks"]:
        raise RuntimeError("live task population drift")
    incomplete = [task for task in live_tasks if not task["evidence_complete"]]
    if len(incomplete) != prereg["expected"]["incomplete_tasks"]:
        raise RuntimeError("incomplete task population drift")

    tasks_by_id = {task["local_row_id"]: task for task in live_tasks}
    local_by_id = {row["id"]: row for row in local_rows}
    local_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in local_rows:
        local_by_sha[row["extraction_sha256"]].append(row)
    raw_receipts = {
        row["local_row_id"]: row for row in m27_seed["raw_evidence_receipts"]
    }
    comparisons = {
        row["local_row_id"]: row for row in m27_seed["comparison_receipts"]
    }
    live_ids = {task["local_row_id"] for task in live_tasks}
    if (
        len(tasks_by_id) != len(live_tasks)
        or len(local_by_id) != len(local_rows)
        or len(m26_rows) != len(m26_result["rows"])
        or not live_ids <= set(local_by_id)
        or not live_ids <= set(m26_rows)
        or not live_ids <= set(raw_receipts)
        or not live_ids <= set(comparisons)
    ):
        raise RuntimeError("M2.7A live identity sets are not closed")

    affected_shas = sorted({task["extraction_sha256"] for task in live_tasks})
    document_receipts: list[dict[str, Any]] = []
    documents_by_sha: dict[str, dict[str, Any]] = {}
    raw_blocks_by_sha: dict[str, list[dict[str, Any]]] = {}
    structural_by_sha: dict[str, list[dict[str, Any]]] = {}
    for extraction_sha256 in affected_shas:
        raw_path = store / f"{extraction_sha256}.json"
        raw = raw_path.read_bytes()
        record = _strict_json_bytes(raw)
        if record.get("sha256") != extraction_sha256:
            raise RuntimeError("raw record identity drift")
        rows = sorted(
            local_by_sha[extraction_sha256], key=lambda row: row["chunk_index"]
        )
        structural_rows = [_structural_row(row) for row in rows]
        expected_rows = replay._expected_rows(
            raw,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        )
        row_by_row_equal = structural_rows == expected_rows
        validation_failures = replay.validate_rows_against_raw(
            raw,
            structural_rows,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        )
        blocks = [
            _block_row(block)
            for block in chunk_module._flatten(
                record.get("result", {}).get("pages", [])
            )
        ]
        raw_stream = "\n\n".join(block["text"] for block in blocks)
        v3_stream = "\n\n".join(row["content"] for row in rows)
        raw_surface = _surface(raw_stream)
        v3_surface = _surface(v3_stream)
        stream_equal = raw_surface == v3_surface
        first_surface_mismatch = _first_surface_mismatch(raw_stream, v3_stream)
        alignment_status = (
            "exact_whitespace_equivalent"
            if row_by_row_equal and not validation_failures and stream_equal
            else "unresolved"
        )
        core = {
            "schema": "s117_m27_raw_document_stream_evidence_v1",
            "extraction_sha256": extraction_sha256,
            "raw_artifact_bytes": len(raw),
            "raw_artifact_sha256": _sha_bytes(raw),
            "raw_artifact_base64": base64.b64encode(raw).decode("ascii"),
            "raw_blocks": blocks,
            "raw_block_manifest_sha256": _manifest(blocks, "source_block_index"),
            "v3_rows": [_chunk_row(row) for row in rows],
            "v3_row_manifest_sha256": _manifest(
                [_chunk_row(row) for row in rows], "chunk_index"
            ),
            "raw_surface_sha256": _sha_bytes(raw_surface.encode("utf-8")),
            "v3_surface_sha256": _sha_bytes(v3_surface.encode("utf-8")),
            "row_by_row_regeneration_equal": row_by_row_equal,
            "independent_validation_failures": validation_failures,
            "document_stream_whitespace_equal": stream_equal,
            "first_surface_mismatch": first_surface_mismatch,
            "alignment_status": alignment_status,
        }
        receipt = {**core, "receipt_sha256": _sha_bytes(_canonical(core))}
        document_receipts.append(receipt)
        documents_by_sha[extraction_sha256] = receipt
        raw_blocks_by_sha[extraction_sha256] = blocks
        structural_by_sha[extraction_sha256] = rows

    legacy_receipts: list[dict[str, Any]] = []
    legacy_by_sha: dict[str, dict[str, Any]] = {}
    for extraction_sha256 in sorted(
        {task["extraction_sha256"] for task in incomplete}
    ):
        receipt = _legacy_document_receipt(
            extraction_sha256, donors_by_sha[extraction_sha256]
        )
        if not receipt["donor_rows"]:
            raise RuntimeError("incomplete task has no legacy document donors")
        legacy_receipts.append(receipt)
        legacy_by_sha[extraction_sha256] = receipt

    task_evidence: list[dict[str, Any]] = []
    review_fiches: list[dict[str, Any]] = []
    for local_id in sorted(tasks_by_id):
        task = tasks_by_id[local_id]
        local = local_by_id.get(local_id)
        if local is None:
            raise RuntimeError("live task local row no longer exists")
        original_raw = raw_receipts[local_id]
        if (
            original_raw["local_content"] != local["content"]
            or original_raw["local_content_sha256"]
            != _sha_bytes(local["content"].encode("utf-8"))
        ):
            raise RuntimeError("live task content drift")
        document = documents_by_sha[task["extraction_sha256"]]
        overlapping = _overlapping_rows(
            structural_by_sha[task["extraction_sha256"]], local
        )
        overlap_rows = [_chunk_row(row) for row in overlapping]
        block_window, boundary = _block_window(
            raw_blocks_by_sha[task["extraction_sha256"]], overlapping
        )
        policy = _policy_receipt(
            local, m26_rows[local_id], policy_contract_sha256
        )
        if task["evidence_complete"]:
            legacy_mode = "m27_original_complete"
            legacy_receipt_sha256 = original_raw["receipt_sha256"]
            legacy_completion_verified = True
        else:
            legacy_mode = "full_legacy_document_materialized"
            full_legacy = legacy_by_sha[task["extraction_sha256"]]
            legacy_receipt_sha256 = full_legacy["receipt_sha256"]
            full_donor_ids = {row["id"] for row in full_legacy["donor_rows"]}
            candidate = task.get("candidate_discovery") or {}
            referenced_donor_ids = {
                row["id"] for row in task.get("donor_evidence", [])
            } | {
                row["id"] for row in original_raw.get("donors", [])
            } | set(candidate.get("candidate_donor_ids", [])) | {
                donor_id
                for occurrence in task.get("occurrences", [])
                for donor_id in occurrence.get("donor_chunk_ids", [])
            }
            legacy_completion_verified = bool(
                full_legacy["donor_count"]
                and referenced_donor_ids <= full_donor_ids
            )
            if not legacy_completion_verified:
                raise RuntimeError("full legacy evidence does not cover cited donors")
        core = {
            "schema": "s117_m27_live_task_evidence_v1",
            "local_row_id": local_id,
            "extraction_sha256": task["extraction_sha256"],
            "original_task_receipt_sha256": task["task_receipt_sha256"],
            "comparison_receipt_sha256": comparisons[local_id]["receipt_sha256"],
            "original_raw_evidence_sha256": original_raw["receipt_sha256"],
            "raw_document_receipt_sha256": document["receipt_sha256"],
            "target_row": _chunk_row(local),
            "overlapping_v3_rows": overlap_rows,
            "overlap_manifest_sha256": _manifest(overlap_rows, "chunk_index"),
            "raw_block_window": block_window,
            "raw_block_window_manifest_sha256": _manifest(
                block_window, "source_block_index"
            ),
            "boundary": boundary,
            "legacy_evidence_mode": legacy_mode,
            "legacy_evidence_receipt_sha256": legacy_receipt_sha256,
            "legacy_evidence_completion_verified": legacy_completion_verified,
            "frozen_policy_evidence": policy,
            "mechanical_raw_alignment": document["alignment_status"],
            "evidence_complete": legacy_completion_verified,
            "adjudication_status": "not_authorized",
        }
        task_receipt = {
            **core,
            "receipt_sha256": _sha_bytes(_canonical(core)),
        }
        task_evidence.append(task_receipt)
        review_fiches.append({
            "schema": "s117_m27_live_review_fiche_v1",
            "local_row_id": local_id,
            "reason": task["reason"],
            "candidate_method": task["candidate_method"],
            "local_content": local["content"],
            "local_protected_tokens": original_raw["local_protected_tokens"],
            "raw_block_window": block_window,
            "overlapping_v3_chunk_indexes": [
                row["chunk_index"] for row in overlap_rows
            ],
            "original_donor_evidence": original_raw["donors"],
            "comparison_receipt_sha256": comparisons[local_id]["receipt_sha256"],
            "task_evidence_receipt_sha256": task_receipt["receipt_sha256"],
            "legacy_full_document_receipt_sha256": (
                legacy_receipt_sha256
                if legacy_mode == "full_legacy_document_materialized"
                else None
            ),
            "mechanical_raw_alignment": document["alignment_status"],
            "policy_class_under_frozen_contract": policy[
                "retrieval_policy_class"
            ],
            "review_status": "not_authorized",
        })

    aligned_docs = sum(
        row["alignment_status"] == "exact_whitespace_equivalent"
        for row in document_receipts
    )
    aligned_tasks = sum(
        row["mechanical_raw_alignment"] == "exact_whitespace_equivalent"
        for row in task_evidence
    )
    evidence_crosslinked = _evidence_crosslinked(
        task_evidence=task_evidence,
        review_fiches=review_fiches,
        document_receipts=document_receipts,
        legacy_receipts=legacy_receipts,
        original_raw=raw_receipts,
        comparisons=comparisons,
        original_tasks=tasks_by_id,
        m26_rows=m26_rows,
        policy_contract_sha256=policy_contract_sha256,
    )
    checks = {
        "m27_seed_bytes_identical": seed1_raw == seed2_raw,
        "m27_seed_receipts_valid": True,
        "live_tasks_exact": len(live_tasks) == prereg["expected"]["live_tasks"],
        "original_complete_exact": len(live_tasks) - len(incomplete)
        == prereg["expected"]["original_complete_tasks"],
        "supplemented_incomplete_exact": len(incomplete)
        == prereg["expected"]["incomplete_tasks"],
        "affected_documents_exact": len(document_receipts)
        == prereg["expected"]["affected_documents"],
        "all_21_evidence_complete": all(
            row["evidence_complete"] for row in task_evidence
        ) and len(task_evidence) == prereg["expected"]["live_tasks"],
        "review_fiches_exact": len(review_fiches)
        == prereg["expected"]["live_tasks"],
        "all_task_receipts_crosslinked": evidence_crosslinked,
        "zero_adjudication": all(
            row["adjudication_status"] == "not_authorized"
            for row in task_evidence
        ),
        "zero_external_cost": True,
    }
    contract_integrity = "GO" if all(checks.values()) else "NO_GO"
    evidence_status = (
        "GO" if contract_integrity == "GO" and checks["all_21_evidence_complete"]
        else "NO_GO"
    )
    alignment_status = (
        "GO" if aligned_docs == len(document_receipts) else "NO_GO"
    )
    result = {
        "instrument": "s117_m27_live_evidence_v1",
        "contract_integrity": contract_integrity,
        "evidence_status": evidence_status,
        "mechanical_alignment_status": alignment_status,
        "status": (
            f"CONTRACT_{contract_integrity}_EVIDENCE_{evidence_status}_"
            f"ALIGNMENT_{alignment_status}"
        ),
        "counts": {
            "live_tasks": len(live_tasks),
            "original_complete_tasks": len(live_tasks) - len(incomplete),
            "supplemented_tasks": len(incomplete),
            "affected_documents": len(document_receipts),
            "aligned_documents": aligned_docs,
            "unresolved_alignment_documents": len(document_receipts) - aligned_docs,
            "aligned_tasks": aligned_tasks,
            "unresolved_alignment_tasks": len(task_evidence) - aligned_tasks,
        },
        "manifests": {
            "raw_document_receipts_sha256": _manifest(
                document_receipts, "extraction_sha256"
            ),
            "legacy_document_receipts_sha256": _manifest(
                legacy_receipts, "extraction_sha256"
            ),
            "task_evidence_sha256": _manifest(task_evidence, "local_row_id"),
            "review_fiches_sha256": _manifest(review_fiches, "local_row_id"),
        },
        "raw_document_receipts": sorted(
            document_receipts, key=lambda row: row["extraction_sha256"]
        ),
        "legacy_document_receipts": sorted(
            legacy_receipts, key=lambda row: row["extraction_sha256"]
        ),
        "task_evidence": sorted(task_evidence, key=lambda row: row["local_row_id"]),
        "review_fiches": sorted(review_fiches, key=lambda row: row["local_row_id"]),
        "checks": checks,
        "authorization": {
            "adjudication": False,
            "model_calls": False,
            "database": False,
            "policy_change": False,
            "chunk_change": False,
            "context_generation": False,
            "embedding_generation": False,
            "load": False,
            "serving": False,
            "M3": "BLOCKED",
        },
        "claim": {
            "raw_store_only_not_pdf_fidelity": True,
            "alignment_is_adjudication": False,
            "facts_moved_to_ok": 0,
        },
        "dependencies": {
            "prereg_sha256": _sha_file(prereg_path),
            "m27_seed_sha256": _sha_bytes(seed1_raw),
            "m27_task_manifest_sha256": m27_seed["task_manifest"]["sha256"],
            "policy_contract_sha256": policy_contract_sha256,
        },
        "cost": {
            "database_reads": 0,
            "database_writes": 0,
            "model_calls": 0,
            "embedding_calls": 0,
        },
    }
    result["determinism"] = {
        "logical_payload_sha256": _sha_bytes(_canonical(result))
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_evidence(
        prereg_path=args.prereg,
        store=args.store,
        sidecar_root=args.sidecar_root,
        source_snapshot=args.source_snapshot,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "counts": result["counts"],
        "logical_payload_sha256": result["determinism"][
            "logical_payload_sha256"
        ],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
