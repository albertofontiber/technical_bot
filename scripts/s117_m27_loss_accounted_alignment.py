#!/usr/bin/env python3
"""Corpus-wide, offline audit of text excluded by the frozen v3 chunker."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from scripts import s117_m27_live_evidence as live
from scripts import s117_m27_upstream_sql_budget_v2 as m27
from scripts import s117_materialize_chunks_v3_local as replay
from src.reingest import chunk as chunk_module
from src.reingest import chunk_provenance as provenance


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m27_loss_accounted_alignment_prereg_v1.yaml"

RULE_ID = "standalone_numeric_page_boundary_exact_v1"
EXPECTED_RULE = {
    "rule_id": RULE_ID,
    "block_kind": "paragraph",
    "page_type": "integer_not_boolean",
    "page_min_inclusive": 1,
    "page_max_inclusive": 9999,
    "text_contract": "strip_text_equals_ascii_decimal_str_of_page",
    "page_identity": "source_page_ordinal",
    "page_position": "first_or_last_block",
    "coverage": "zero_covering_v3_chunks",
    "selectors_forbidden": [
        "manufacturer",
        "model",
        "document",
        "extraction_sha256",
        "uuid",
        "filename",
        "observed_literal",
    ],
}
DISPOSITIONS = (
    "covered_by_v3",
    "authorized_exclusion",
    "unruled_loss",
)


def _canonical(value: Any) -> bytes:
    return live._canonical(value)


def _sha_bytes(value: bytes) -> str:
    return live._sha_bytes(value)


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _surface(text: str) -> str:
    return live._surface(text)


def _receipt(core: dict[str, Any]) -> dict[str, Any]:
    return {**core, "receipt_sha256": _sha_bytes(_canonical(core))}


def _receipt_valid(row: dict[str, Any]) -> bool:
    expected = row.get("receipt_sha256")
    core = {key: value for key, value in row.items() if key != "receipt_sha256"}
    return live._is_sha256(expected) and expected == _sha_bytes(_canonical(core))


def _manifest(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: tuple(item[key] for key in keys)):
        digest.update(_canonical(row) + b"\n")
    return digest.hexdigest()


def _iter_hashed_paths(value: Any):
    yield from live._iter_hashed_paths(value)


def _strict_json(raw: bytes) -> dict[str, Any]:
    return live._strict_json_bytes(raw)


def _load_contract(prereg_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if prereg_path.resolve() != DEFAULT_PREREG.resolve():
        raise RuntimeError("M2.7B prereg path mismatch")
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("instrument")
        != "s117_m27_loss_accounted_alignment_prereg_v1"
        or prereg.get("status") != "frozen_before_seeded_corpus_audit"
    ):
        raise RuntimeError("M2.7B prereg drift")
    for item in _iter_hashed_paths(prereg.get("frozen_inputs", {})):
        path = (ROOT / item["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("M2.7B frozen input escapes workspace") from exc
        if _sha_file(path) != item["sha256"]:
            raise RuntimeError(f"M2.7B frozen input drift: {item['path']}")
    selected = prereg.get("selected_paths", {})
    bindings = prereg.get("selected_path_bindings", {})
    frozen = prereg.get("frozen_inputs", {})
    if set(selected) != set(bindings):
        raise RuntimeError("M2.7B selected path binding set drift")
    for name, frozen_name in bindings.items():
        item = frozen.get(frozen_name)
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("path"), str)
            or not live._is_sha256(item.get("sha256"))
            or selected[name] != item["path"]
        ):
            raise RuntimeError("M2.7B selected path is not hash-bound")
    policy = yaml.safe_load(
        (ROOT / selected["loss_policy"]).read_text(encoding="utf-8")
    )
    if (
        policy.get("schema") != "s117_chunk_loss_policy_v1"
        or policy.get("version") != 1
        or policy.get("authority")
        != "raw_store_shape_only_not_semantic_noise_proof"
        or policy.get("rules") != [EXPECTED_RULE]
        or policy.get("residual_risk") != {
            "shape_match_is_semantic_noise_proof": False,
            "standalone_24_on_integer_page_24_boundary_matches": True,
        }
        or policy.get("fail_closed") != {
            "unknown_rule": True,
            "unruled_loss": True,
            "empty_document_after_exclusions": True,
            "approximate_matching_allowed": False,
        }
    ):
        raise RuntimeError("M2.7B loss policy is not the closed v1 registry")
    return prereg, policy


def _anchor(anchor: Any) -> dict[str, Any] | None:
    return live._anchor(anchor)


def _blocks_with_page_ordinal(record: dict[str, Any]) -> list[dict[str, Any]]:
    pages = record.get("result", {}).get("pages", [])
    canonical = chunk_module._flatten(pages)
    rows: list[dict[str, Any]] = []
    cursor = 0
    for source_page_ordinal, page_row in enumerate(pages):
        markdown = page_row.get("md") or page_row.get("text") or ""
        if not markdown.strip():
            continue
        page_blocks = chunk_module.parse_blocks(markdown, page_row.get("page"))
        for parsed in page_blocks:
            if cursor >= len(canonical):
                raise RuntimeError("page/block reconstruction overflow")
            block = canonical[cursor]
            if (
                parsed.kind != block.kind
                or parsed.text != block.text
                or parsed.page != block.page
                or block.source_block_index != cursor
            ):
                raise RuntimeError("page/block reconstruction drift")
            rows.append({
                "source_block_index": block.source_block_index,
                "source_page_ordinal": source_page_ordinal,
                "kind": block.kind,
                "page": block.page,
                "page_type": type(block.page).__name__,
                "text": block.text,
                "text_sha256": _sha_bytes(block.text.encode("utf-8")),
                "lineage": [_anchor(item) for item in block.lineage],
            })
            cursor += 1
    if cursor != len(canonical):
        raise RuntimeError("page/block reconstruction underflow")
    return _canonicalize_blocks(rows)


def _canonicalize_blocks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            row["source_page_ordinal"],
            row["source_block_index"],
        ),
    )
    by_ordinal: dict[int, list[int]] = defaultdict(list)
    for row in ordered:
        by_ordinal[row["source_page_ordinal"]].append(row["source_block_index"])
    for row in ordered:
        positions = by_ordinal[row["source_page_ordinal"]]
        row["is_first_block_of_page_occurrence"] = (
            row["source_block_index"] == positions[0]
        )
        row["is_last_block_of_page_occurrence"] = (
            row["source_block_index"] == positions[-1]
        )
    return ordered


def _rule_evaluation(
    block: dict[str, Any], covering_chunks: list[dict[str, Any]]
) -> dict[str, Any]:
    page = block["page"]
    stripped = block["text"].strip()
    predicates = {
        "kind_is_paragraph": block["kind"] == "paragraph",
        "page_is_integer_not_boolean": isinstance(page, int)
        and not isinstance(page, bool),
        "page_in_1_9999": isinstance(page, int)
        and not isinstance(page, bool)
        and 1 <= page <= 9999,
        "text_is_ascii_digits_1_4": re.fullmatch(r"[0-9]{1,4}", stripped)
        is not None,
        "text_strip_equals_str_page": isinstance(page, int)
        and not isinstance(page, bool)
        and stripped == str(page),
        "is_page_occurrence_boundary": bool(
            block["is_first_block_of_page_occurrence"]
            or block["is_last_block_of_page_occurrence"]
        ),
        "zero_covering_v3_chunks": not covering_chunks,
    }
    shape_fields = tuple(key for key in predicates if key != "zero_covering_v3_chunks")
    shape_match = all(predicates[key] for key in shape_fields)
    authorized = shape_match and predicates["zero_covering_v3_chunks"]
    return {
        "rule_id": RULE_ID,
        "predicates": predicates,
        "shape_match": shape_match,
        "authorized": authorized,
        "residual_risk": (
            "shape_match_not_semantic_noise_proof" if shape_match else None
        ),
    }


def _neighbor(block: dict[str, Any] | None) -> dict[str, Any] | None:
    if block is None:
        return None
    return {
        "source_block_index": block["source_block_index"],
        "source_page_ordinal": block["source_page_ordinal"],
        "kind": block["kind"],
        "page": block["page"],
        "text_sha256": block["text_sha256"],
    }


def _v3_row(row: dict[str, Any]) -> dict[str, Any]:
    return _receipt({
        "id": row["id"],
        "chunk_index": row["chunk_index"],
        "content": row["content"],
        "content_sha256": _sha_bytes(row["content"].encode("utf-8")),
        "source_block_start": row["source_block_start"],
        "source_block_end": row["source_block_end"],
        "provenance_payload_sha256": row["provenance_payload_sha256"],
    })


def _document_audit(
    *,
    extraction_sha256: str,
    raw: bytes,
    record: dict[str, Any],
    rows: list[dict[str, Any]],
    rule_contract_sha256: str,
    rng: random.Random | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blocks = _blocks_with_page_ordinal(record)
    rows = list(rows)
    if rng is not None:
        rng.shuffle(blocks)
        rng.shuffle(rows)
    blocks = _canonicalize_blocks(blocks)
    rows.sort(key=lambda row: row["chunk_index"])
    if [row["source_block_index"] for row in blocks] != list(range(len(blocks))):
        raise RuntimeError("non-contiguous source block ordinals")
    covering_by_block: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        start = row["source_block_start"]
        end = row["source_block_end"]
        if not (0 <= start <= end < len(blocks)):
            raise RuntimeError("v3 span outside raw block population")
        for block_index in range(start, end + 1):
            covering_by_block[block_index].append({
                "id": row["id"],
                "chunk_index": row["chunk_index"],
            })
    ledger: list[dict[str, Any]] = []
    for position, block in enumerate(blocks):
        covering = sorted(
            covering_by_block.get(block["source_block_index"], []),
            key=lambda item: item["chunk_index"],
        )
        evaluation = _rule_evaluation(block, covering)
        if covering:
            disposition = "covered_by_v3"
        elif evaluation["authorized"]:
            disposition = "authorized_exclusion"
        else:
            disposition = "unruled_loss"
        core = {
            "schema": "s117_m27_block_loss_ledger_v1",
            "extraction_sha256": extraction_sha256,
            **block,
            "previous_block": _neighbor(blocks[position - 1] if position else None),
            "next_block": _neighbor(
                blocks[position + 1] if position + 1 < len(blocks) else None
            ),
            "covering_v3_chunks": covering,
            "rule_contract_sha256": rule_contract_sha256,
            "rule_evaluation": evaluation,
            "rule_matched_but_retained": bool(
                covering and evaluation["shape_match"]
            ),
            "disposition": disposition,
        }
        ledger.append(_receipt(core))

    authorized = {
        row["source_block_index"]
        for row in ledger
        if row["disposition"] == "authorized_exclusion"
    }
    raw_stream = "\n\n".join(row["text"] for row in blocks)
    accounted_stream = "\n\n".join(
        row["text"]
        for row in blocks
        if row["source_block_index"] not in authorized
    )
    v3_rows = [_v3_row(row) for row in rows]
    v3_stream = "\n\n".join(row["content"] for row in v3_rows)
    counts = Counter(row["disposition"] for row in ledger)
    nonempty_after_exclusions = bool(
        not blocks
        or (
            counts["covered_by_v3"] > 0
            and bool(_surface(v3_stream))
        )
    )
    stream_equal = _surface(accounted_stream) == _surface(v3_stream)
    core = {
        "schema": "s117_m27_loss_accounted_document_v1",
        "extraction_sha256": extraction_sha256,
        "raw_artifact_sha256": _sha_bytes(raw),
        "raw_block_count": len(blocks),
        "v3_chunk_count": len(rows),
        "block_ledger_manifest_sha256": _manifest(
            ledger, ("source_block_index",)
        ),
        "v3_rows": v3_rows,
        "v3_rows_manifest_sha256": _manifest(v3_rows, ("chunk_index",)),
        "disposition_counts": {
            disposition: counts[disposition] for disposition in DISPOSITIONS
        },
        "authorized_exclusion_block_indexes": sorted(authorized),
        "unruled_loss_block_indexes": [
            row["source_block_index"]
            for row in ledger
            if row["disposition"] == "unruled_loss"
        ],
        "rule_matched_but_retained_block_indexes": [
            row["source_block_index"]
            for row in ledger
            if row["rule_matched_but_retained"]
        ],
        "raw_surface_sha256": _sha_bytes(_surface(raw_stream).encode("utf-8")),
        "accounted_surface_sha256": _sha_bytes(
            _surface(accounted_stream).encode("utf-8")
        ),
        "v3_surface_sha256": _sha_bytes(_surface(v3_stream).encode("utf-8")),
        "first_accounted_mismatch": live._first_surface_mismatch(
            accounted_stream, v3_stream
        ),
        "document_nonempty_after_exclusions": nonempty_after_exclusions,
        "loss_accounted_stream_equal": stream_equal,
        "status": (
            "GO"
            if not counts["unruled_loss"]
            and nonempty_after_exclusions
            and stream_equal
            else "NO_GO"
        ),
    }
    return _receipt(core), ledger


def _crosslinked(
    documents: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
    *,
    expected_rule_contract_sha256: str,
    raw_by_sha: dict[str, bytes],
    expected_rows_by_sha: dict[str, list[dict[str, Any]]],
) -> bool:
    docs = {row["extraction_sha256"]: row for row in documents}
    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ledger:
        by_sha[row["extraction_sha256"]].append(row)
    if (
        len(docs) != len(documents)
        or set(by_sha) - set(docs)
        or set(docs) != set(raw_by_sha)
        or set(docs) != set(expected_rows_by_sha)
    ):
        return False
    for sha, document in docs.items():
        rows = sorted(
            by_sha.get(sha, []), key=lambda row: row["source_block_index"]
        )
        v3_rows = document["v3_rows"]
        raw = raw_by_sha[sha]
        expected_blocks = _blocks_with_page_ordinal(_strict_json(raw))
        expected_block_fields = (
            "source_block_index",
            "source_page_ordinal",
            "kind",
            "page",
            "page_type",
            "text",
            "text_sha256",
            "lineage",
            "is_first_block_of_page_occurrence",
            "is_last_block_of_page_occurrence",
        )
        observed_blocks = [
            {key: row[key] for key in expected_block_fields} for row in rows
        ]
        expected_v3_rows = [
            _v3_row(row)
            for row in sorted(
                expected_rows_by_sha[sha], key=lambda row: row["chunk_index"]
            )
        ]
        if observed_blocks != expected_blocks or v3_rows != expected_v3_rows:
            return False
        covering_by_block: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for v3_row in v3_rows:
            if (
                not rows
                or not 0
                <= v3_row["source_block_start"]
                <= v3_row["source_block_end"]
                < len(rows)
                or v3_row["content_sha256"]
                != _sha_bytes(v3_row["content"].encode("utf-8"))
                or not live._is_sha256(v3_row["provenance_payload_sha256"])
            ):
                return False
            for block_index in range(
                v3_row["source_block_start"],
                v3_row["source_block_end"] + 1,
            ):
                covering_by_block[block_index].append({
                    "id": v3_row["id"],
                    "chunk_index": v3_row["chunk_index"],
                })
        page_positions: dict[int, list[int]] = defaultdict(list)
        for row in rows:
            page_positions[row["source_page_ordinal"]].append(
                row["source_block_index"]
            )
        derived_dispositions = Counter()
        for position, row in enumerate(rows):
            covering = sorted(
                covering_by_block.get(row["source_block_index"], []),
                key=lambda item: item["chunk_index"],
            )
            base = {
                key: row[key]
                for key in (
                    "source_block_index",
                    "source_page_ordinal",
                    "kind",
                    "page",
                    "page_type",
                    "text",
                    "text_sha256",
                    "lineage",
                    "is_first_block_of_page_occurrence",
                    "is_last_block_of_page_occurrence",
                )
            }
            positions = page_positions[row["source_page_ordinal"]]
            expected_evaluation = _rule_evaluation(base, covering)
            expected_disposition = (
                "covered_by_v3"
                if covering
                else (
                    "authorized_exclusion"
                    if expected_evaluation["authorized"]
                    else "unruled_loss"
                )
            )
            if (
                row["page_type"] != type(row["page"]).__name__
                or row["text_sha256"]
                != _sha_bytes(row["text"].encode("utf-8"))
                or row["is_first_block_of_page_occurrence"]
                != (row["source_block_index"] == positions[0])
                or row["is_last_block_of_page_occurrence"]
                != (row["source_block_index"] == positions[-1])
                or row["previous_block"]
                != _neighbor(rows[position - 1] if position else None)
                or row["next_block"]
                != _neighbor(rows[position + 1] if position + 1 < len(rows) else None)
                or row["covering_v3_chunks"] != covering
                or row["rule_contract_sha256"]
                != expected_rule_contract_sha256
                or row["rule_evaluation"] != expected_evaluation
                or row["rule_matched_but_retained"]
                != bool(covering and expected_evaluation["shape_match"])
                or row["disposition"] != expected_disposition
            ):
                return False
            derived_dispositions[expected_disposition] += 1
        authorized = {
            row["source_block_index"]
            for row in rows
            if row["disposition"] == "authorized_exclusion"
        }
        raw_stream = "\n\n".join(row["text"] for row in rows)
        accounted_stream = "\n\n".join(
            row["text"]
            for row in rows
            if row["source_block_index"] not in authorized
        )
        v3_stream = "\n\n".join(row["content"] for row in v3_rows)
        stream_equal = _surface(accounted_stream) == _surface(v3_stream)
        nonempty = bool(
            not rows
            or (
                derived_dispositions["covered_by_v3"] > 0
                and bool(_surface(v3_stream))
            )
        )
        derived_status = (
            "GO"
            if not derived_dispositions["unruled_loss"]
            and nonempty
            and stream_equal
            else "NO_GO"
        )
        if (
            not _receipt_valid(document)
            or not all(_receipt_valid(row) for row in (*rows, *v3_rows))
            or document["raw_artifact_sha256"] != _sha_bytes(raw)
            or [row["source_block_index"] for row in rows]
            != list(range(document["raw_block_count"]))
            or [row["chunk_index"] for row in v3_rows]
            != list(range(document["v3_chunk_count"]))
            or document["block_ledger_manifest_sha256"]
            != _manifest(rows, ("source_block_index",))
            or document["v3_rows_manifest_sha256"]
            != _manifest(v3_rows, ("chunk_index",))
            or document["disposition_counts"]
            != {
                disposition: derived_dispositions[disposition]
                for disposition in DISPOSITIONS
            }
            or document["authorized_exclusion_block_indexes"]
            != sorted(authorized)
            or document["unruled_loss_block_indexes"]
            != [
                row["source_block_index"]
                for row in rows
                if row["disposition"] == "unruled_loss"
            ]
            or document["rule_matched_but_retained_block_indexes"]
            != [
                row["source_block_index"]
                for row in rows
                if row["rule_matched_but_retained"]
            ]
            or document["raw_surface_sha256"]
            != _sha_bytes(_surface(raw_stream).encode("utf-8"))
            or document["accounted_surface_sha256"]
            != _sha_bytes(_surface(accounted_stream).encode("utf-8"))
            or document["v3_surface_sha256"]
            != _sha_bytes(_surface(v3_stream).encode("utf-8"))
            or document["first_accounted_mismatch"]
            != live._first_surface_mismatch(accounted_stream, v3_stream)
            or document["document_nonempty_after_exclusions"] != nonempty
            or document["loss_accounted_stream_equal"] != stream_equal
            or document["status"] != derived_status
        ):
            return False
    return True


def _population_checks(
    *,
    expected_records: set[str],
    expected_documents: int,
    expected_v3_rows: int,
    documents: list[dict[str, Any]],
    all_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    document_ids = [row["extraction_sha256"] for row in documents]
    row_ids = [row["id"] for row in all_rows]
    ordinals = [
        (row["extraction_sha256"], row["chunk_index"])
        for row in all_rows
    ]
    return {
        "document_population_exact": len(documents) == expected_documents,
        "document_identities_unique": len(document_ids) == len(set(document_ids)),
        "document_identity_set_exact": set(document_ids) == expected_records,
        "v3_rows_exact": len(all_rows) == expected_v3_rows,
        "v3_ids_unique": len(row_ids) == len(set(row_ids)),
        "v3_ordinals_unique": len(ordinals) == len(set(ordinals)),
    }


def build_audit(
    *,
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
    seed: int,
) -> dict[str, Any]:
    prereg, policy = _load_contract(prereg_path)
    if seed not in prereg["execution"]["seeds"]:
        raise RuntimeError("unregistered M2.7B seed")
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
    expected_records = {
        row["extraction_sha256"]
        for row in development["generation"]["manifest"]["records"]
    }
    record_files = list(m2_state["record_files"])
    rng = random.Random(seed)
    rng.shuffle(record_files)
    observed_records = {path.stem for path in record_files}
    if (
        len(record_files) != prereg["expected"]["documents"]
        or len(observed_records) != len(record_files)
        or observed_records != expected_records
    ):
        raise RuntimeError("M2.7B extraction population drift")

    policy_contract = {
        "policy": policy,
        "policy_sha256": _sha_file(ROOT / prereg["selected_paths"]["loss_policy"]),
        "design_v1_sha256": prereg["frozen_inputs"]["design_v1"]["sha256"],
        "design_v2_sha256": prereg["frozen_inputs"]["design_v2"]["sha256"],
    }
    policy_contract_sha256 = _sha_bytes(_canonical(policy_contract))
    all_rows: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    raw_by_sha: dict[str, bytes] = {}
    expected_rows_by_sha: dict[str, list[dict[str, Any]]] = {}
    validation_failures: list[str] = []
    for path in record_files:
        raw = path.read_bytes()
        record = _strict_json(raw)
        if record.get("sha256") != path.stem:
            raise RuntimeError("raw record identity drift")
        raw_by_sha[path.stem] = raw
        rows = provenance.materialize_raw_record(
            raw,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        )
        rng.shuffle(rows)
        rows.sort(key=lambda row: row["chunk_index"])
        expected_rows_by_sha[path.stem] = list(rows)
        expected = replay._expected_rows(
            raw,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        )
        if rows != expected:
            validation_failures.append(f"{path.stem}:row_mismatch")
        for failure in replay.validate_rows_against_raw(
            raw,
            rows,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        ):
            validation_failures.append(f"{path.stem}:{failure}")
        if [row["chunk_index"] for row in rows] != list(range(len(rows))):
            validation_failures.append(f"{path.stem}:chunk_index_noncontiguous")
        document, block_ledger = _document_audit(
            extraction_sha256=path.stem,
            raw=raw,
            record=record,
            rows=rows,
            rule_contract_sha256=policy_contract_sha256,
            rng=rng,
        )
        rng.shuffle(block_ledger)
        all_rows.extend(rows)
        documents.append(document)
        ledger.extend(block_ledger)

    observed_rows_manifest = _sha_bytes(provenance.row_manifest_bytes(all_rows))
    expected_rows_manifest = development["generation"]["rows_manifest_sha256"]
    dispositions = Counter(row["disposition"] for row in ledger)
    matched_retained = sum(row["rule_matched_but_retained"] for row in ledger)
    nonempty_failures = sum(
        not row["document_nonempty_after_exclusions"] for row in documents
    )
    alignment_failures = sum(
        not row["loss_accounted_stream_equal"] for row in documents
    )
    checks = {
        **_population_checks(
            expected_records=expected_records,
            expected_documents=prereg["expected"]["documents"],
            expected_v3_rows=prereg["expected"]["v3_rows"],
            documents=documents,
            all_rows=all_rows,
        ),
        "v3_rows_manifest_exact": observed_rows_manifest == expected_rows_manifest,
        "zero_independent_validation_failures": not validation_failures,
        "ledger_taxonomy_closed": set(dispositions) <= set(DISPOSITIONS),
        "ledger_crosslinked": _crosslinked(
            documents,
            ledger,
            expected_rule_contract_sha256=policy_contract_sha256,
            raw_by_sha=raw_by_sha,
            expected_rows_by_sha=expected_rows_by_sha,
        ),
        "zero_external_cost": True,
        "zero_adjudication": True,
    }
    contract_integrity = "GO" if all(checks.values()) else "NO_GO"
    coverage_status = "GO" if contract_integrity == "GO" else "NO_GO"
    loss_policy_status = (
        "GO"
        if contract_integrity == "GO"
        and dispositions["unruled_loss"] == 0
        else "NO_GO"
    )
    alignment_status = (
        "GO"
        if loss_policy_status == "GO"
        and nonempty_failures == 0
        and alignment_failures == 0
        else "NO_GO"
    )
    loss_rows = [
        {
            "extraction_sha256": row["extraction_sha256"],
            "source_block_index": row["source_block_index"],
            "source_page_ordinal": row["source_page_ordinal"],
            "page": row["page"],
            "kind": row["kind"],
            "text": row["text"],
            "disposition": row["disposition"],
            "rule_id": (
                row["rule_evaluation"]["rule_id"]
                if row["rule_evaluation"]["shape_match"]
                else None
            ),
            "residual_risk": row["rule_evaluation"]["residual_risk"],
            "ledger_receipt_sha256": row["receipt_sha256"],
        }
        for row in ledger
        if row["disposition"] != "covered_by_v3"
    ]
    result = {
        "instrument": "s117_m27_loss_accounted_alignment_v1",
        "contract_integrity": contract_integrity,
        "coverage_ledger_status": coverage_status,
        "loss_policy_status": loss_policy_status,
        "loss_accounted_alignment_status": alignment_status,
        "status": (
            f"CONTRACT_{contract_integrity}_COVERAGE_{coverage_status}_"
            f"LOSS_POLICY_{loss_policy_status}_ALIGNMENT_{alignment_status}"
        ),
        "population": {
            "documents": len(documents),
            "v3_rows": len(all_rows),
            "raw_blocks": len(ledger),
        },
        "counts": {
            "dispositions": {
                disposition: dispositions[disposition]
                for disposition in DISPOSITIONS
            },
            "rule_matched_but_retained": matched_retained,
            "documents_nonempty_failure": nonempty_failures,
            "documents_alignment_failure": alignment_failures,
            "documents_go": sum(row["status"] == "GO" for row in documents),
            "documents_no_go": sum(row["status"] != "GO" for row in documents),
        },
        "policy_contract": {
            **policy_contract,
            "sha256": policy_contract_sha256,
            "semantic_noise_proof": False,
        },
        "manifests": {
            "documents_sha256": _manifest(documents, ("extraction_sha256",)),
            "block_ledger_sha256": _manifest(
                ledger, ("extraction_sha256", "source_block_index")
            ),
            "loss_rows_sha256": _manifest(
                loss_rows, ("extraction_sha256", "source_block_index")
            ),
            "v3_rows_manifest_sha256": observed_rows_manifest,
        },
        "documents": sorted(documents, key=lambda row: row["extraction_sha256"]),
        "block_ledger": sorted(
            ledger,
            key=lambda row: (
                row["extraction_sha256"],
                row["source_block_index"],
            ),
        ),
        "loss_rows": sorted(
            loss_rows,
            key=lambda row: (
                row["extraction_sha256"],
                row["source_block_index"],
            ),
        ),
        "checks": checks,
        "validation_failures": sorted(validation_failures),
        "authorization": {
            "chunk_change": False,
            "policy_change": False,
            "adjudication": False,
            "model_calls": False,
            "database": False,
            "context_generation": False,
            "embedding_generation": False,
            "load": False,
            "serving": False,
            "M3": "BLOCKED",
        },
        "claim": {
            "authority": "raw_store_only_not_pdf_or_visual_fidelity",
            "rule_match_is_semantic_noise_proof": False,
            "facts_moved_to_ok": 0,
        },
        "dependencies": {
            "prereg_sha256": _sha_file(prereg_path),
            "development_result_sha256": _sha_file(development_path),
            "m27_live_evidence_gate_sha256": _sha_file(
                ROOT / prereg["selected_paths"]["m27_live_evidence_gate"]
            ),
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
    result = build_audit(
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
        "counts": result["counts"],
        "logical_payload_sha256": result["determinism"][
            "logical_payload_sha256"
        ],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
