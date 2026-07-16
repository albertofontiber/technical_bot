#!/usr/bin/env python3
"""Offline counterfactual for removing length-only chunk deletion.

The treatment is diagnostic-only.  It has its own contract identity and never
reuses the frozen baseline materialization identity while the override is on.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import yaml

from scripts import s117_m27_live_evidence as live
from scripts import s117_m27_loss_accounted_alignment as m27b
from scripts import s117_m27_upstream_sql_budget_v2 as m27
from scripts import s117_materialize_chunks_v3_local as replay
from src.reingest import chunk as chunk_module
from src.reingest import chunk_provenance as provenance


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m27_loss_safe_chunking_probe_prereg_v1.yaml"
TREATMENT_NAMESPACE = uuid.UUID("424a6330-6f8c-5ed9-a18f-f02d81fb8a69")
BASELINE_NOISE_CHARS = 15
TREATMENT_NOISE_CHARS = 0


def _canonical(value: Any) -> bytes:
    return live._canonical(value)


def _sha_bytes(value: bytes) -> str:
    return live._sha_bytes(value)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for piece in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(piece)
    return digest.hexdigest()


def _manifest(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: tuple(item[key] for key in keys)):
        digest.update(_canonical(row) + b"\n")
    return digest.hexdigest()


def _load_contract(prereg_path: Path) -> dict[str, Any]:
    if prereg_path.resolve() != DEFAULT_PREREG.resolve():
        raise RuntimeError("M2.7C prereg path mismatch")
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("instrument")
        != "s117_m27_loss_safe_chunking_probe_prereg_v1"
        or prereg.get("status") != "frozen_before_seeded_probe"
    ):
        raise RuntimeError("M2.7C prereg drift")
    for item in live._iter_hashed_paths(prereg.get("frozen_inputs", {})):
        path = (ROOT / item["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("M2.7C frozen input escapes workspace") from exc
        if _sha_file(path) != item["sha256"]:
            raise RuntimeError(f"M2.7C frozen input drift: {item['path']}")
    selected = prereg.get("selected_paths", {})
    bindings = prereg.get("selected_path_bindings", {})
    frozen = prereg.get("frozen_inputs", {})
    if set(selected) != set(bindings):
        raise RuntimeError("M2.7C selected path binding set drift")
    for name, frozen_name in bindings.items():
        item = frozen.get(frozen_name)
        if (
            not isinstance(item, dict)
            or selected[name] != item.get("path")
            or not live._is_sha256(item.get("sha256"))
        ):
            raise RuntimeError("M2.7C selected path is not hash-bound")
    if prereg.get("override_contract") != {
        "symbol": "src.reingest.chunk.NOISE_CHARS",
        "baseline": BASELINE_NOISE_CHARS,
        "treatment": TREATMENT_NOISE_CHARS,
        "scope": "single_call_with_finally_restore",
        "only_behavioral_override": True,
    }:
        raise RuntimeError("M2.7C override contract drift")
    return prereg


def _with_treatment_override(
    record: dict[str, Any],
    *,
    chunker: Callable[[dict[str, Any]], list[Any]] | None = None,
) -> list[Any]:
    if chunk_module.NOISE_CHARS != BASELINE_NOISE_CHARS:
        raise RuntimeError("M2.7C baseline NOISE_CHARS drift before override")
    if chunker is None:
        chunker = chunk_module.chunk_document
    try:
        chunk_module.NOISE_CHARS = TREATMENT_NOISE_CHARS
        result = chunker(record)
        if chunk_module.NOISE_CHARS != TREATMENT_NOISE_CHARS:
            raise RuntimeError("M2.7C treatment override mutated during call")
        return result
    finally:
        chunk_module.NOISE_CHARS = BASELINE_NOISE_CHARS


def _lineage(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, tuple):
        return [provenance.anchor_to_dict(anchor) for anchor in value]
    if isinstance(value, list):
        return value
    raise ValueError("invalid lineage representation")


def _row_core_from_baseline(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ordinal": row["chunk_index"],
        "content": row["content"],
        "source_block_start": row["source_block_start"],
        "source_block_end": row["source_block_end"],
        "section_anchor": row["section_anchor"],
        "section_lineage": _lineage(row["section_lineage"]),
        "section_title": row["section_title"],
        "section_path": row["section_path"],
        "page_number": row["page_number"],
        "is_flow_diagram": row["is_flow_diagram"],
        "has_diagram": row["has_diagram"],
        "confidence": row["confidence"],
    }


def _row_core_from_treatment(chunk: Any) -> dict[str, Any]:
    return {
        "ordinal": chunk.chunk_index,
        "content": chunk.content,
        "source_block_start": chunk.source_block_start,
        "source_block_end": chunk.source_block_end,
        "section_anchor": provenance.anchor_to_dict(chunk.section_anchor),
        "section_lineage": _lineage(chunk.section_lineage),
        "section_title": chunk.section_title,
        "section_path": chunk.section_path,
        "page_number": chunk.page_number,
        "is_flow_diagram": bool(chunk.is_flow_diagram),
        "has_diagram": bool(chunk.has_diagram),
        "confidence": chunk.confidence,
    }


def _fingerprinted(core: dict[str, Any]) -> dict[str, Any]:
    fingerprint_core = {
        "content_surface_sha256": _sha_bytes(
            live._surface(core["content"]).encode("utf-8")
        ),
        "source_block_start": core["source_block_start"],
        "source_block_end": core["source_block_end"],
        "section_lineage": core["section_lineage"],
        "section_title": core["section_title"],
        "section_path": core["section_path"],
        "page_number": core["page_number"],
        "is_flow_diagram": core["is_flow_diagram"],
        "has_diagram": core["has_diagram"],
        "confidence": core["confidence"],
    }
    return {
        **core,
        "content_sha256": _sha_bytes(core["content"].encode("utf-8")),
        "fingerprint": fingerprint_core,
        "fingerprint_sha256": _sha_bytes(_canonical(fingerprint_core)),
    }


def _validate_rows(rows: list[dict[str, Any]], block_count: int) -> None:
    if [row["ordinal"] for row in rows] != list(range(len(rows))):
        raise RuntimeError("non-contiguous diagnostic row ordinals")
    for row in rows:
        start = row["source_block_start"]
        end = row["source_block_end"]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or not 0 <= start <= end < block_count
        ):
            raise RuntimeError("diagnostic span outside raw block population")


def _validate_treatment_against_raw(
    raw: bytes,
    record: dict[str, Any],
    chunks: list[Any],
    rows: list[dict[str, Any]],
) -> None:
    if len(chunks) != len(rows):
        raise RuntimeError("treatment chunk/row cardinality drift")
    lineage_rows = []
    pages = record.get("result", {}).get("pages", [])
    image_pages = {
        page.get("page")
        for page in pages
        if page.get("page") is not None and page.get("images")
    }
    page_confidence = {
        page.get("page"): page.get("confidence")
        for page in pages
        if page.get("page") is not None and page.get("confidence") is not None
    }
    blocks = chunk_module._flatten(pages)
    for chunk, row in zip(chunks, rows):
        replay._validate_expected_chunk(chunk)
        start = row["source_block_start"]
        end = row["source_block_end"]
        covered_blocks = blocks[start : end + 1]
        expected_page = next(
            (block.page for block in covered_blocks if block.page is not None), None
        )
        if row["page_number"] != expected_page:
            raise RuntimeError("treatment page number is not raw-span-bound")
        if row["is_flow_diagram"] != any(
            block.kind == "mermaid" for block in covered_blocks
        ):
            raise RuntimeError("treatment flow flag is not raw-span-bound")
        if row["has_diagram"] != (expected_page in image_pages):
            raise RuntimeError("treatment diagram flag is not raw-page-bound")
        if row["confidence"] != page_confidence.get(expected_page):
            raise RuntimeError("treatment confidence is not raw-page-bound")
        lineage_rows.append({
            "chunk_index": row["ordinal"],
            "source_block_start": start,
            "source_block_end": end,
            "section_anchor": row["section_anchor"],
            "section_lineage": row["section_lineage"],
            "section_title": row["section_title"],
            "section_path": row["section_path"],
        })
    failures = replay._validate_lineage(raw, lineage_rows)
    if failures:
        raise RuntimeError(f"treatment lineage is not raw-bound: {failures[:3]}")

    groups: list[list[dict[str, Any]]] = []
    for row in rows:
        span = (row["source_block_start"], row["source_block_end"])
        if groups and span == (
            groups[-1][0]["source_block_start"],
            groups[-1][0]["source_block_end"],
        ):
            groups[-1].append(row)
        else:
            groups.append([row])
    cursor = 0
    for group in groups:
        start = group[0]["source_block_start"]
        end = group[0]["source_block_end"]
        if start != cursor:
            raise RuntimeError("treatment span groups are not a full ordered partition")
        raw_span_surface = live._surface(
            "\n\n".join(block.text for block in blocks[start : end + 1])
        )
        treatment_span_surface = live._surface(
            "\n\n".join(row["content"] for row in group)
        )
        if treatment_span_surface != raw_span_surface:
            raise RuntimeError("treatment content is not bound to its raw span")
        cursor = end + 1
    if cursor != len(blocks):
        raise RuntimeError("treatment span groups do not cover the raw block population")


def _covered(rows: list[dict[str, Any]]) -> set[int]:
    result: set[int] = set()
    for row in rows:
        result.update(range(row["source_block_start"], row["source_block_end"] + 1))
    return result


def _multiset_delta(
    baseline: list[dict[str, Any]], treatment: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    baseline_by_fp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    treatment_by_fp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in baseline:
        baseline_by_fp[row["fingerprint_sha256"]].append(row)
    for row in treatment:
        treatment_by_fp[row["fingerprint_sha256"]].append(row)
    unchanged: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []
    for fingerprint in sorted(set(baseline_by_fp) | set(treatment_by_fp)):
        left = sorted(baseline_by_fp.get(fingerprint, []), key=lambda row: row["ordinal"])
        right = sorted(treatment_by_fp.get(fingerprint, []), key=lambda row: row["ordinal"])
        paired = min(len(left), len(right))
        unchanged.extend({
            "fingerprint_sha256": fingerprint,
            "baseline_ordinal": left[index]["ordinal"],
            "treatment_ordinal": right[index]["ordinal"],
        } for index in range(paired))
        removed.extend(left[paired:])
        added.extend(right[paired:])
    modified = []
    for left in removed:
        for right in added:
            overlap_start = max(left["source_block_start"], right["source_block_start"])
            overlap_end = min(left["source_block_end"], right["source_block_end"])
            if overlap_start <= overlap_end:
                modified.append({
                    "baseline_ordinal": left["ordinal"],
                    "baseline_fingerprint_sha256": left["fingerprint_sha256"],
                    "treatment_ordinal": right["ordinal"],
                    "treatment_fingerprint_sha256": right["fingerprint_sha256"],
                    "overlap_start": overlap_start,
                    "overlap_end": overlap_end,
                })
    return {
        "unchanged": unchanged,
        "removed": removed,
        "added": added,
        "modified": modified,
    }


def _row_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ordinal": row["ordinal"],
        "content": row["content"],
        "content_sha256": row["content_sha256"],
        "content_surface_sha256": row["fingerprint"]["content_surface_sha256"],
        "source_block_start": row["source_block_start"],
        "source_block_end": row["source_block_end"],
        "section_anchor": row["section_anchor"],
        "section_lineage": row["section_lineage"],
        "section_title": row["section_title"],
        "section_path": row["section_path"],
        "page_number": row["page_number"],
        "is_flow_diagram": row["is_flow_diagram"],
        "has_diagram": row["has_diagram"],
        "confidence": row["confidence"],
        "fingerprint_sha256": row["fingerprint_sha256"],
        "meaningful_characters": chunk_module._meaningful_len(row["content"]),
    }


def _document_probe(
    *,
    extraction_sha256: str,
    raw: bytes,
    record: dict[str, Any],
    baseline_rows_raw: list[dict[str, Any]],
    treatment_contract_sha256: str,
    rng: random.Random | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    blocks = m27b._blocks_with_page_ordinal(record)
    baseline_rows_raw = list(baseline_rows_raw)
    if rng is not None:
        rng.shuffle(baseline_rows_raw)
    baseline = [
        _fingerprinted(_row_core_from_baseline(row))
        for row in sorted(baseline_rows_raw, key=lambda item: item["chunk_index"])
    ]
    treatment_chunks = _with_treatment_override(record)
    if chunk_module.NOISE_CHARS != BASELINE_NOISE_CHARS:
        raise RuntimeError("M2.7C treatment override failed to restore")
    if rng is not None:
        rng.shuffle(treatment_chunks)
    treatment_chunks.sort(key=lambda item: item.chunk_index)
    treatment = [
        _fingerprinted(_row_core_from_treatment(chunk))
        for chunk in treatment_chunks
    ]
    _validate_rows(baseline, len(blocks))
    _validate_rows(treatment, len(blocks))
    _validate_treatment_against_raw(
        raw, record, treatment_chunks, treatment
    )
    baseline_covered = _covered(baseline)
    treatment_covered = _covered(treatment)
    raw_surface = live._surface("\n\n".join(block["text"] for block in blocks))
    baseline_surface = live._surface("\n\n".join(row["content"] for row in baseline))
    treatment_surface = live._surface("\n\n".join(row["content"] for row in treatment))
    delta = _multiset_delta(baseline, treatment)
    baseline_manifest_rows = [{
        "fingerprint_sha256": row["fingerprint_sha256"],
        "occurrence": occurrence,
    } for occurrence, row in enumerate(sorted(
        baseline, key=lambda item: (item["fingerprint_sha256"], item["ordinal"])
    ))]
    treatment_manifest_rows = [{
        "fingerprint_sha256": row["fingerprint_sha256"],
        "occurrence": occurrence,
    } for occurrence, row in enumerate(sorted(
        treatment, key=lambda item: (item["fingerprint_sha256"], item["ordinal"])
    ))]
    changed = bool(delta["removed"] or delta["added"])
    core = {
        "schema": "s117_m27_loss_safe_chunking_document_v1",
        "extraction_sha256": extraction_sha256,
        "raw_artifact_sha256": _sha_bytes(raw),
        "treatment_contract_sha256": treatment_contract_sha256,
        "raw_blocks": len(blocks),
        "baseline_rows": len(baseline),
        "treatment_rows": len(treatment),
        "baseline_covered_blocks": len(baseline_covered),
        "treatment_covered_blocks": len(treatment_covered),
        "baseline_missing_block_indexes": sorted(set(range(len(blocks))) - baseline_covered),
        "treatment_missing_block_indexes": sorted(set(range(len(blocks))) - treatment_covered),
        "coverage_regression_block_indexes": sorted(baseline_covered - treatment_covered),
        "coverage_gain_block_indexes": sorted(treatment_covered - baseline_covered),
        "raw_surface_sha256": _sha_bytes(raw_surface.encode("utf-8")),
        "baseline_surface_sha256": _sha_bytes(baseline_surface.encode("utf-8")),
        "treatment_surface_sha256": _sha_bytes(treatment_surface.encode("utf-8")),
        "treatment_surface_equal_raw": treatment_surface == raw_surface,
        "baseline_fingerprint_multiset_sha256": _sha_bytes(_canonical(baseline_manifest_rows)),
        "treatment_fingerprint_multiset_sha256": _sha_bytes(_canonical(treatment_manifest_rows)),
        "fingerprint_multiset_equal": baseline_manifest_rows == treatment_manifest_rows,
        "delta_counts": {name: len(rows) for name, rows in delta.items()},
        "delta_partition_exact": (
            len(delta["unchanged"]) + len(delta["removed"]) == len(baseline)
            and len(delta["unchanged"]) + len(delta["added"]) == len(treatment)
        ),
        "changed": changed,
    }
    document = m27b._receipt(core)
    if not changed:
        return document, None
    detail_core = {
        "schema": "s117_m27_loss_safe_chunking_delta_v1",
        "extraction_sha256": extraction_sha256,
        "treatment_contract_sha256": treatment_contract_sha256,
        "unchanged": delta["unchanged"],
        "removed": [_row_projection(row) for row in delta["removed"]],
        "added": [_row_projection(row) for row in delta["added"]],
        "modified": delta["modified"],
    }
    return document, m27b._receipt(detail_core)


def _diagnostic_id(
    treatment_contract_sha256: str,
    extraction_sha256: str,
    ordinal: int,
    fingerprint_sha256: str,
) -> str:
    name = "\x00".join((
        "m27c-v1",
        treatment_contract_sha256,
        extraction_sha256,
        str(ordinal),
        fingerprint_sha256,
    ))
    return str(uuid.uuid5(TREATMENT_NAMESPACE, name))


def build_probe(
    *,
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
    seed: int,
) -> dict[str, Any]:
    prereg = _load_contract(prereg_path)
    if seed not in prereg["execution"]["seeds"]:
        raise RuntimeError("unregistered M2.7C seed")
    if chunk_module.NOISE_CHARS != BASELINE_NOISE_CHARS:
        raise RuntimeError("M2.7C baseline NOISE_CHARS drift")

    selected = prereg["selected_paths"]
    _, m2_state = m27.preflight(
        ROOT / selected["m27_prereg"], store, sidecar_root, source_snapshot
    )
    development_path = ROOT / selected["development_result"]
    development = json.loads(development_path.read_text(encoding="utf-8"))
    compact = json.loads((ROOT / selected["loss_rows_compact"]).read_text(encoding="utf-8"))
    compact_dispositions = Counter(row.get("disposition") for row in compact.get("rows", []))
    compact_logical_core = {
        key: value for key, value in compact.items()
        if key != "logical_payload_sha256"
    }
    if (
        compact.get("instrument") != "s117_m27_compact_loss_report_v1"
        or compact.get("authority")
        != "diagnostic_only_no_policy_or_semantic_adjudication"
        or compact_dispositions
        != Counter({"authorized_exclusion": 13, "unruled_loss": 87})
        or compact.get("source", {}).get("sha256")
        != prereg["frozen_inputs"]["m27b_seed1"]["sha256"]
        or compact.get("logical_payload_sha256")
        != _sha_bytes(_canonical(compact_logical_core))
    ):
        raise RuntimeError("M2.7C compact loss contract drift")
    expected_records = {
        row["extraction_sha256"]
        for row in development["generation"]["manifest"]["records"]
    }
    frozen_loss_identities = sorted({
        (row["extraction_sha256"], row["source_block_index"])
        for row in compact["rows"]
    })
    if len(frozen_loss_identities) != prereg["expected"]["baseline_missing_blocks"]:
        raise RuntimeError("M2.7C frozen loss identity count drift")
    loss_documents = {identity[0] for identity in frozen_loss_identities}

    runner_sha256 = _sha_file(Path(__file__))
    treatment_contract = {
        "base_chunker_sha256": prereg["frozen_inputs"]["chunker"]["sha256"],
        "override": prereg["override_contract"],
        "runner_sha256": runner_sha256,
    }
    treatment_contract_sha256 = _sha_bytes(_canonical(treatment_contract))

    materialization_id = development["generation"]["materialization_id"]
    base_chunker_sha256 = development["dependencies"]["chunker_sha256"]
    record_files = list(m2_state["record_files"])
    rng = random.Random(seed)
    rng.shuffle(record_files)
    if (
        len(record_files) != prereg["expected"]["documents"]
        or {path.stem for path in record_files} != expected_records
    ):
        raise RuntimeError("M2.7C extraction population drift")

    documents: list[dict[str, Any]] = []
    deltas: list[dict[str, Any]] = []
    all_baseline_rows: list[dict[str, Any]] = []
    observed_baseline_missing: list[tuple[str, int]] = []
    observed_treatment_missing: list[tuple[str, int]] = []
    baseline_covered_total = 0
    treatment_covered_total = 0
    raw_blocks_total = 0
    treatment_rows_total = 0
    for path in record_files:
        raw = path.read_bytes()
        record = m27b._strict_json(raw)
        if record.get("sha256") != path.stem:
            raise RuntimeError("M2.7C raw record identity drift")
        baseline_rows = provenance.materialize_raw_record(
            raw,
            materialization_id=materialization_id,
            chunker_sha256=base_chunker_sha256,
        )
        all_baseline_rows.extend(baseline_rows)
        document, delta = _document_probe(
            extraction_sha256=path.stem,
            raw=raw,
            record=record,
            baseline_rows_raw=baseline_rows,
            treatment_contract_sha256=treatment_contract_sha256,
            rng=rng,
        )
        documents.append(document)
        if delta is not None:
            for row in delta["added"]:
                row["diagnostic_id"] = _diagnostic_id(
                    treatment_contract_sha256,
                    path.stem,
                    row["ordinal"],
                    row["fingerprint_sha256"],
                )
            deltas.append(m27b._receipt({
                key: value for key, value in delta.items() if key != "receipt_sha256"
            }))
        raw_blocks_total += document["raw_blocks"]
        treatment_rows_total += document["treatment_rows"]
        baseline_covered_total += document["baseline_covered_blocks"]
        treatment_covered_total += document["treatment_covered_blocks"]
        observed_baseline_missing.extend(
            (path.stem, index)
            for index in document["baseline_missing_block_indexes"]
        )
        observed_treatment_missing.extend(
            (path.stem, index)
            for index in document["treatment_missing_block_indexes"]
        )
    if chunk_module.NOISE_CHARS != BASELINE_NOISE_CHARS:
        raise RuntimeError("M2.7C global override leaked after population")

    documents.sort(key=lambda row: row["extraction_sha256"])
    deltas.sort(key=lambda row: row["extraction_sha256"])
    observed_baseline_missing.sort()
    observed_treatment_missing.sort()
    baseline_manifest_sha256 = _sha_bytes(provenance.row_manifest_bytes(all_baseline_rows))
    changed_documents = {row["extraction_sha256"] for row in documents if row["changed"]}
    stable_documents = [row for row in documents if row["extraction_sha256"] not in loss_documents]
    observed_coverage_gain = sorted(
        (row["extraction_sha256"], index)
        for row in documents
        for index in row["coverage_gain_block_indexes"]
    )
    checks = {
        "document_population_exact": len(documents) == prereg["expected"]["documents"],
        "baseline_rows_exact": len(all_baseline_rows) == prereg["expected"]["baseline_rows"],
        "baseline_manifest_exact": baseline_manifest_sha256
        == development["generation"]["rows_manifest_sha256"],
        "raw_blocks_exact": raw_blocks_total == prereg["expected"]["raw_blocks"],
        "baseline_covered_exact": baseline_covered_total
        == prereg["expected"]["baseline_covered_blocks"],
        "baseline_missing_exact": observed_baseline_missing == frozen_loss_identities,
        "baseline_missing_count_exact": len(observed_baseline_missing)
        == prereg["expected"]["baseline_missing_blocks"],
        "treatment_all_blocks_covered": treatment_covered_total == raw_blocks_total,
        "treatment_zero_missing": not observed_treatment_missing,
        "coverage_gain_exact": observed_coverage_gain == frozen_loss_identities,
        "no_coverage_regression": all(
            not row["coverage_regression_block_indexes"] for row in documents
        ),
        "treatment_surface_equal_raw_every_document": all(
            row["treatment_surface_equal_raw"] for row in documents
        ),
        "delta_partitions_exact": all(
            row["delta_partition_exact"] for row in documents
        ),
        "loss_document_set_exact": changed_documents == loss_documents,
        "unchanged_document_count_exact": len(stable_documents)
        == prereg["expected"]["unchanged_documents"],
        "unaffected_fingerprint_multisets_equal": all(
            row["fingerprint_multiset_equal"] for row in stable_documents
        ),
        "changed_documents_have_delta": changed_documents
        == {row["extraction_sha256"] for row in deltas},
        "override_restored": chunk_module.NOISE_CHARS == BASELINE_NOISE_CHARS,
        "zero_external_cost": True,
        "zero_adjudication": True,
    }
    contract_integrity = "GO" if all(checks.values()) else "NO_GO"
    baseline_replay = "GO" if all(checks[key] for key in (
        "document_population_exact",
        "baseline_rows_exact",
        "baseline_manifest_exact",
        "raw_blocks_exact",
        "baseline_covered_exact",
        "baseline_missing_exact",
        "baseline_missing_count_exact",
    )) else "NO_GO"
    treatment_lossless = "GO" if all(checks[key] for key in (
        "treatment_all_blocks_covered",
        "treatment_zero_missing",
        "no_coverage_regression",
        "treatment_surface_equal_raw_every_document",
        "override_restored",
    )) else "NO_GO"
    delta_accounted = "GO" if (
        baseline_replay == "GO"
        and treatment_lossless == "GO"
        and all(checks[key] for key in (
            "coverage_gain_exact",
            "loss_document_set_exact",
            "unchanged_document_count_exact",
            "unaffected_fingerprint_multisets_equal",
            "delta_partitions_exact",
            "changed_documents_have_delta",
        ))
    ) else "NO_GO"
    result: dict[str, Any] = {
        "instrument": "s117_m27_loss_safe_chunking_probe_v1",
        "authority": "raw_store_parsed_block_surface_only",
        "status": (
            f"CONTRACT_{contract_integrity}_BASELINE_{baseline_replay}_"
            f"TREATMENT_{treatment_lossless}_DELTA_{delta_accounted}"
        ),
        "statuses": {
            "contract_integrity": contract_integrity,
            "baseline_replay": baseline_replay,
            "treatment_lossless": treatment_lossless,
            "delta_accounted": delta_accounted,
        },
        "population": {
            "documents": len(documents),
            "raw_blocks": raw_blocks_total,
            "baseline_rows": len(all_baseline_rows),
            "treatment_rows": treatment_rows_total,
            "baseline_covered_blocks": baseline_covered_total,
            "treatment_covered_blocks": treatment_covered_total,
            "baseline_missing_blocks": len(observed_baseline_missing),
            "treatment_missing_blocks": len(observed_treatment_missing),
            "changed_documents": len(changed_documents),
            "unchanged_documents": len(stable_documents),
        },
        "treatment_contract": {
            **treatment_contract,
            "sha256": treatment_contract_sha256,
            "loadable": False,
        },
        "manifests": {
            "baseline_rows_sha256": baseline_manifest_sha256,
            "documents_sha256": _manifest(documents, ("extraction_sha256",)),
            "deltas_sha256": _manifest(deltas, ("extraction_sha256",)),
            "baseline_missing_identities_sha256": _sha_bytes(
                _canonical(observed_baseline_missing)
            ),
            "treatment_missing_identities_sha256": _sha_bytes(
                _canonical(observed_treatment_missing)
            ),
        },
        "checks": checks,
        "documents": documents,
        "changed_document_deltas": deltas,
        "authorization": {
            "implementation": False,
            "policy_change": False,
            "database": False,
            "network": False,
            "models": False,
            "context_generation": False,
            "embeddings": False,
            "load": False,
            "serving": False,
            "deploy": False,
            "M3": "BLOCKED",
            "facts_moved_to_ok": 0,
        },
        "dependencies": {
            "prereg_sha256": _sha_file(prereg_path),
            "development_result_sha256": prereg["frozen_inputs"][
                "development_result"
            ]["sha256"],
            "loss_rows_compact_sha256": prereg["frozen_inputs"][
                "loss_rows_compact"
            ]["sha256"],
            "m27b_gate_sha256": prereg["frozen_inputs"]["m27b_gate"][
                "sha256"
            ],
            "m27b_seed1_sha256": prereg["frozen_inputs"]["m27b_seed1"][
                "sha256"
            ],
            "m27b_seed2_sha256": prereg["frozen_inputs"]["m27b_seed2"][
                "sha256"
            ],
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
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
    result = build_probe(
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
        "population": result["population"],
        "logical_payload_sha256": result["determinism"]["logical_payload_sha256"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
