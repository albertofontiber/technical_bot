#!/usr/bin/env python3
"""M2.7 local fidelity audit and fresh-enrichment planning workload.

This runner is deliberately offline.  It never reads env files, connects to a
database, calls a model, fetches vector payloads, or authorizes loading/serving.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from scripts import s117_m2_legacy_reuse_analysis as m2
from scripts import s117_m26_independent_reuse_audit as m26
from scripts import s117_materialize_chunks_v3_local as replay


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m27_upstream_sql_budget_prereg_v1.yaml"

STRUCTURE_FIELDS = (
    "section_title",
    "section_path",
    "page_number",
    "is_flow_diagram",
    "has_diagram",
    "confidence_f32",
)
TARGET_STRUCTURAL_STATUSES = (
    "no_content_donor",
    "no_structural_donor",
    "multiple_structural_donors",
)
FIDELITY_OUTCOMES = (
    "exact_resegmentation_evidence",
    "structure_only_delta",
    "adjudicated_benign_delta",
    "material_fidelity_risk",
    "unresolved_requires_adjudication",
)
_TECHNICAL_SYMBOLS = set("<>=≤≥±+−–—-/×÷%°µμΩΩ²³⁰¹⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉")
_UNIT_TOKENS = {
    "a", "ma", "ua", "µa", "v", "mv", "kv", "w", "mw", "kw",
    "pa", "kpa", "mpa", "bar", "hz", "khz", "mhz", "ohm", "ω",
    "c", "°c", "f", "°f", "s", "ms", "min", "h", "mm", "cm", "m",
    "rpm", "db", "ip", "vac", "vdc", "ac", "dc", "%",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def _iter_hashed_paths(value: Any):
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            yield value
        for child in value.values():
            yield from _iter_hashed_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_hashed_paths(child)


def _surface_tokens(text: str) -> list[str]:
    """Whitespace-only normalization; case and Unicode remain untouched."""
    return text.split()


def _surface_text(text: str) -> str:
    return " ".join(_surface_tokens(text))


def _candidate_tokens(text: str) -> list[str]:
    """Permissive discovery only.  Never sufficient for automatic closure."""
    return unicodedata.normalize("NFKC", text).casefold().split()


def _protected_tokens(tokens: list[str]) -> list[str]:
    has_numeric = [bool(re.search(r"\d", token)) for token in tokens]
    pure_numeric = [
        bool(re.fullmatch(r"[+\-−]?\d[\d.,]*", token.strip("()[]{};:")))
        for token in tokens
    ]
    protected: list[str] = []
    for index, token in enumerate(tokens):
        lower = token.casefold().strip(".,;:()[]{}")
        adjacent_numeric = (
            (index > 0 and pure_numeric[index - 1])
            or (index + 1 < len(tokens) and pure_numeric[index + 1])
        )
        has_case_signal = any(char.isupper() for char in token)
        has_technical_symbol = any(char in _TECHNICAL_SYMBOLS for char in token)
        alphanumeric_code = bool(re.search(r"[A-Za-z].*\d|\d.*[A-Za-z]", token))
        if (
            has_numeric[index]
            or adjacent_numeric
            or has_case_signal
            or has_technical_symbol
            or alphanumeric_code
            or lower in _UNIT_TOKENS
        ):
            protected.append(token)
    return protected


def _find_subsequences(haystack: list[str], needle: list[str]) -> list[tuple[int, int]]:
    if not needle or len(needle) > len(haystack):
        return []
    width = len(needle)
    return [
        (start, start + width)
        for start in range(len(haystack) - width + 1)
        if haystack[start : start + width] == needle
    ]


def _shingles(tokens: list[str], width: int = 5) -> set[tuple[str, ...]]:
    if not tokens:
        return set()
    if len(tokens) < width:
        return {tuple(tokens)}
    return {tuple(tokens[index : index + width]) for index in range(len(tokens) - width + 1)}


def _near_discovery(local_content: str, donors: list[dict[str, Any]]) -> dict[str, Any]:
    local = _candidate_tokens(local_content)
    donor_tokens: list[str] = []
    donor_ids: list[str] = []
    for donor in donors:
        tokens = _candidate_tokens(donor.get("content") or "")
        donor_tokens.extend(tokens)
        donor_ids.extend([donor.get("id")] * len(tokens))
    local_shingles = _shingles(local)
    donor_shingles = _shingles(donor_tokens)
    coverage = (
        len(local_shingles & donor_shingles) / len(local_shingles)
        if local_shingles
        else 0.0
    )
    matching_indexes: list[int] = []
    if local_shingles:
        width = min(5, len(local))
        wanted = local_shingles
        for index in range(max(0, len(donor_tokens) - width + 1)):
            if tuple(donor_tokens[index : index + width]) in wanted:
                matching_indexes.extend(range(index, index + width))
    candidate_ids = sorted({donor_ids[index] for index in matching_indexes if donor_ids[index]})
    return {
        "method": "nfkc_casefold_5_shingle_candidate_discovery_only",
        "coverage_f32": float.hex(float(coverage)),
        "threshold_f32": float.hex(0.98),
        "candidate_donor_ids": candidate_ids[:12],
        "candidate_count_capped": len(candidate_ids) > 12,
    }


def _provenance_receipts(
    record_files: list[Path],
    *,
    materialization_id: str,
    chunker_sha256: str,
) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for path in sorted(record_files):
        raw = path.read_bytes()
        rows = replay._expected_rows(
            raw,
            materialization_id=materialization_id,
            chunker_sha256=chunker_sha256,
        )
        lineage_failures = set(replay._validate_lineage(raw, rows))
        for row in rows:
            core = {
                "local_row_id": row["id"],
                "extraction_sha256": row["extraction_sha256"],
                "provenance_payload_sha256": row["provenance_payload_sha256"],
                "source_block_start": row["source_block_start"],
                "source_block_end": row["source_block_end"],
                "lineage_valid": not lineage_failures,
            }
            receipts[row["id"]] = {
                **core,
                "receipt_sha256": _sha_bytes(_canonical(core)),
            }
    return receipts


def _provenance_valid(local: dict[str, Any], receipt: dict[str, Any] | None) -> bool:
    return bool(
        receipt
        and receipt["lineage_valid"]
        and receipt["extraction_sha256"] == local["extraction_sha256"]
        and receipt["provenance_payload_sha256"]
        == local["provenance_payload_sha256"]
        and receipt["source_block_start"] == local["source_block_start"]
        and receipt["source_block_end"] == local["source_block_end"]
    )


def _task(
    *,
    local: dict[str, Any],
    cohort: str,
    comparison: dict[str, Any],
    donors: list[dict[str, Any]],
    reason: str,
) -> dict[str, Any]:
    local_snippet = local["content"][:500]
    donor_snippets = [
        {
            "id": donor.get("id"),
            "chunk_index": donor.get("chunk_index"),
            "content_sha256": _sha_bytes((donor.get("content") or "").encode("utf-8")),
            "snippet": (donor.get("content") or "")[:500],
        }
        for donor in donors[:12]
    ]
    raw_evidence = {
        "local_content_sha256": _sha_bytes(local["content"].encode("utf-8")),
        "local_surface_sha256": _sha_bytes(_surface_text(local["content"]).encode("utf-8")),
        "local_protected_tokens": _protected_tokens(_surface_tokens(local["content"])),
        "donors": donor_snippets,
    }
    raw_evidence_sha256 = _sha_bytes(_canonical(raw_evidence))
    core = {
        "schema": "s117_m27_fidelity_task_v1",
        "local_row_id": local["id"],
        "cohort": cohort,
        "extraction_sha256": local["extraction_sha256"],
        "comparison_receipt_sha256": _sha_bytes(_canonical(comparison)),
        "raw_evidence_sha256": raw_evidence_sha256,
        "candidate_method": comparison.get("method"),
        "reason": reason,
        "local_snippet": local_snippet,
        "donor_evidence": donor_snippets,
        "protected_technical_tokens": raw_evidence["local_protected_tokens"],
    }
    return {**core, "task_receipt_sha256": _sha_bytes(_canonical(core))}


def validate_adjudication(
    payload: dict[str, Any],
    *,
    expected_task_manifest_sha256: str,
    tasks: list[dict[str, Any]],
) -> dict[str, str]:
    """Validate the frozen v1 receipt contract; importing remains unauthorized."""
    if (
        payload.get("schema") != "s117_m27_fidelity_adjudication_v1"
        or payload.get("version") != 1
        or payload.get("task_manifest_sha256") != expected_task_manifest_sha256
    ):
        raise ValueError("adjudication envelope mismatch")
    reviewer = payload.get("reviewer")
    if not isinstance(reviewer, dict) or reviewer.get("method") not in {
        "human_expert", "named_adversarial_model"
    } or not reviewer.get("identity"):
        raise ValueError("invalid adjudication reviewer")
    if reviewer["method"] == "human_expert":
        if reviewer.get("provider") is not None or reviewer.get("model") is not None:
            raise ValueError("human adjudicator cannot claim model identity")
    elif not reviewer.get("provider") or not reviewer.get("model"):
        raise ValueError("model adjudicator identity incomplete")

    tasks_by_id = {task["local_row_id"]: task for task in tasks}
    if len(tasks_by_id) != len(tasks):
        raise ValueError("duplicate task identity")
    decisions: dict[str, str] = {}
    rubric_fields = {
        "negation_changed",
        "condition_or_scope_changed",
        "warning_or_safety_changed",
        "procedure_order_changed",
        "reference_target_changed",
        "protected_technical_tokens_changed",
    }
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("adjudication rows missing")
    for row in rows:
        local_id = row.get("local_row_id") if isinstance(row, dict) else None
        if local_id in decisions or local_id not in tasks_by_id:
            raise ValueError("duplicate or unknown adjudication row")
        task = tasks_by_id[local_id]
        if (
            row.get("comparison_receipt_sha256")
            != task["comparison_receipt_sha256"]
            or row.get("raw_evidence_sha256") != task["raw_evidence_sha256"]
        ):
            raise ValueError("adjudication evidence mismatch")
        rubric = row.get("rubric")
        if (
            not isinstance(rubric, dict)
            or set(rubric) != rubric_fields
            or not all(isinstance(value, bool) for value in rubric.values())
        ):
            raise ValueError("invalid adjudication rubric")
        verdict = row.get("verdict")
        if verdict not in {"benign", "material"} or not row.get("rationale"):
            raise ValueError("invalid adjudication verdict")
        any_material = any(rubric.values())
        if (verdict == "benign" and any_material) or (verdict == "material" and not any_material):
            raise ValueError("adjudication rubric/verdict conflict")
        decisions[local_id] = verdict
    return decisions


def _audit_row(
    local: dict[str, Any],
    m26_row: dict[str, Any],
    donors: list[dict[str, Any]],
    provenance_receipt: dict[str, Any] | None,
    cohort: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    structural = m26_row["structural_identity_status"]
    valid_provenance = _provenance_valid(local, provenance_receipt)
    task = None
    if not valid_provenance:
        comparison = {
            "method": "independent_provenance_reconstruction",
            "provenance_receipt_sha256": (
                provenance_receipt.get("receipt_sha256") if provenance_receipt else None
            ),
        }
        outcome = "material_fidelity_risk"
        reason = "invalid_local_provenance_or_lineage"
    elif structural == "no_structural_donor":
        content_candidates = [
            donor for donor in donors if donor.get("content") == local["content"]
        ]
        differences = []
        for donor in content_candidates:
            differences.append({
                "donor_chunk_id": donor.get("id"),
                "fields": {
                    field: {"local": local.get(field), "donor": donor.get(field)}
                    for field in STRUCTURE_FIELDS
                    if local.get(field) != donor.get(field)
                },
            })
        comparison = {
            "method": "raw_content_identity_plus_structure_delta",
            "local_content_sha256": _sha_bytes(local["content"].encode("utf-8")),
            "content_candidate_count": len(content_candidates),
            "differences": differences,
            "provenance_receipt_sha256": provenance_receipt["receipt_sha256"],
        }
        if content_candidates and all(item["fields"] for item in differences):
            outcome = "structure_only_delta"
            reason = "raw_content_equal_structure_fields_differ"
        else:
            outcome = "material_fidelity_risk"
            reason = "m26_structure_status_not_reproduced"
    elif structural in ("no_content_donor", "multiple_structural_donors"):
        local_tokens = _surface_tokens(local["content"])
        donor_tokens: list[str] = []
        donor_token_ids: list[str] = []
        donor_by_id = {donor.get("id"): donor for donor in donors}
        for donor in donors:
            tokens = _surface_tokens(donor.get("content") or "")
            donor_tokens.extend(tokens)
            donor_token_ids.extend([donor.get("id")] * len(tokens))
        occurrences = _find_subsequences(donor_tokens, local_tokens)
        occurrence_receipts = []
        for start, end in occurrences:
            span_ids = list(dict.fromkeys(donor_token_ids[start:end]))
            span_tokens = donor_tokens[start:end]
            occurrence_receipts.append({
                "start_token": start,
                "end_token_exclusive": end,
                "donor_chunk_ids": span_ids,
                "surface_sha256": _sha_bytes(" ".join(span_tokens).encode("utf-8")),
                "protected_tokens": _protected_tokens(span_tokens),
            })
        comparison = {
            "method": "surface_safe_whitespace_only_token_sequence",
            "local_raw_sha256": _sha_bytes(local["content"].encode("utf-8")),
            "local_surface_sha256": _sha_bytes(_surface_text(local["content"]).encode("utf-8")),
            "local_protected_tokens": _protected_tokens(local_tokens),
            "occurrence_count": len(occurrences),
            "occurrences": occurrence_receipts,
            "provenance_receipt_sha256": provenance_receipt["receipt_sha256"],
        }
        protected_equal = bool(
            len(occurrence_receipts) == 1
            and occurrence_receipts[0]["protected_tokens"]
            == comparison["local_protected_tokens"]
        )
        if len(occurrences) == 1 and protected_equal:
            outcome = "exact_resegmentation_evidence"
            reason = "unique_surface_safe_occurrence"
        else:
            near = _near_discovery(local["content"], donors)
            comparison["candidate_discovery"] = near
            outcome = "unresolved_requires_adjudication"
            reason = (
                "ambiguous_surface_safe_occurrence"
                if occurrences
                else "near_or_unresolved_content_delta"
            )
            selected_ids = near["candidate_donor_ids"]
            task_donors = [donor_by_id[item] for item in selected_ids if item in donor_by_id]
            if not task_donors:
                task_donors = donors[:12]
            task = _task(
                local=local,
                cohort=cohort,
                comparison=comparison,
                donors=task_donors,
                reason=reason,
            )
    else:
        raise RuntimeError(f"unexpected M2.7 structural status: {structural}")

    core = {
        "local_row_id": local["id"],
        "extraction_sha256": local["extraction_sha256"],
        "chunk_index": local["chunk_index"],
        "cohort": cohort,
        "m26_structural_identity_status": structural,
        "fidelity_outcome": outcome,
        "reason": reason,
        "comparison_receipt_sha256": _sha_bytes(_canonical(comparison)),
        "provenance_receipt_sha256": (
            provenance_receipt.get("receipt_sha256") if provenance_receipt else None
        ),
    }
    return {**core, "row_receipt_sha256": _sha_bytes(_canonical(core))}, task


def _money(tokens: int, rate_per_million: Decimal) -> str:
    return str((Decimal(tokens) * rate_per_million / Decimal(1_000_000)).quantize(Decimal("0.000001")))


def _ceil4(chars: int) -> int:
    return (chars + 3) // 4


def _context_scenario(
    *,
    base_input: int,
    cache_write: int,
    cache_read: int,
    output_ceiling: int,
) -> dict[str, Any]:
    rates = {
        "base_input": Decimal("1.00"),
        "cache_write_5m": Decimal("1.25"),
        "cache_read": Decimal("0.10"),
        "output": Decimal("5.00"),
    }
    components = {
        "base_input_usd": _money(base_input, rates["base_input"]),
        "cache_write_usd": _money(cache_write, rates["cache_write_5m"]),
        "cache_read_usd": _money(cache_read, rates["cache_read"]),
        "output_ceiling_usd": _money(output_ceiling, rates["output"]),
    }
    total = sum(Decimal(value) for value in components.values())
    return {
        "base_input_tokens_char4_planning_proxy": base_input,
        "cache_write_tokens_char4_planning_proxy": cache_write,
        "cache_read_tokens_char4_planning_proxy": cache_read,
        "output_tokens_requested_ceiling": output_ceiling,
        "usd_planning_proxy": {**components, "total": str(total.quantize(Decimal("0.000001")))},
    }


def _workload(live_rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in live_rows:
        groups[row["extraction_sha256"]].append(row)
    for rows in groups.values():
        if len({row["context_document_chars"] for row in rows}) != 1:
            raise RuntimeError("document prompt chars drift within extraction")

    output_ceiling = len(live_rows) * 200
    no_cache_base = sum(_ceil4(row["context_input_chars"]) for row in live_rows)
    instruction_proxy = sum(_ceil4(row["context_instruction_chars"]) for row in live_rows)
    ideal_write = sum(_ceil4(rows[0]["context_document_chars"]) for rows in groups.values())
    ideal_read = sum(
        _ceil4(rows[0]["context_document_chars"]) * (len(rows) - 1)
        for rows in groups.values()
    )

    min_base = 0
    min_write = 0
    min_read = 0
    cacheable_documents = 0
    cacheable_requests = 0
    for rows in groups.values():
        document_proxy = _ceil4(rows[0]["context_document_chars"])
        if document_proxy >= 4096:
            cacheable_documents += 1
            cacheable_requests += len(rows)
            min_write += document_proxy
            min_read += document_proxy * (len(rows) - 1)
            min_base += sum(_ceil4(row["context_instruction_chars"]) for row in rows)
        else:
            min_base += sum(_ceil4(row["context_input_chars"]) for row in rows)

    lower_chars = sum(min(len(row["content"]) + 2, 16000) for row in live_rows)
    upper_chars = len(live_rows) * 16000
    embedding_low = sum(_ceil4(min(len(row["content"]) + 2, 16000)) for row in live_rows)
    embedding_high = len(live_rows) * _ceil4(16000)
    batch_low = max(math.ceil(len(live_rows) / 128), math.ceil(lower_chars / 320000))
    batch_high = math.ceil(len(live_rows) / 20)

    return {
        "exact_before_generation": {
            "logical_context_calls": len(live_rows),
            "distinct_extraction_documents": len(groups),
            "subsequent_calls_within_document": len(live_rows) - len(groups),
            "http_retries": None,
            "context_input_chars": sum(row["context_input_chars"] for row in live_rows),
            "context_output_tokens_requested_ceiling": output_ceiling,
        },
        "context_planning_proxies": {
            "model": "claude-haiku-4-5",
            "rates_usd_per_million": {
                "base_input": "1.00",
                "cache_write_5m": "1.25",
                "cache_read": "0.10",
                "output": "5.00",
            },
            "no_cache_conservative": _context_scenario(
                base_input=no_cache_base,
                cache_write=0,
                cache_read=0,
                output_ceiling=output_ceiling,
            ),
            "ideal_cache_proxy": _context_scenario(
                base_input=instruction_proxy,
                cache_write=ideal_write,
                cache_read=ideal_read,
                output_ceiling=output_ceiling,
            ),
            "minimum_cacheable_char4_proxy": {
                "minimum_cacheable_tokens": 4096,
                "cacheable_documents": cacheable_documents,
                "cacheable_logical_calls": cacheable_requests,
                **_context_scenario(
                    base_input=min_base,
                    cache_write=min_write,
                    cache_read=min_read,
                    output_ceiling=output_ceiling,
                ),
            },
            "cache_hits_require_usage_receipts": True,
        },
        "embedding_precontext_plan": {
            "provider": "voyage",
            "model": "voyage-4-large",
            "logical_inputs": len(live_rows),
            "input_chars_floor_from_empty_context": lower_chars,
            "input_chars_truncation_ceiling": upper_chars,
            "tokens_char4_planning_proxy_low": embedding_low,
            "tokens_char4_planning_proxy_high": embedding_high,
            "greedy_batch_http_requests_planning_low": batch_low,
            "greedy_batch_http_requests_planning_high": batch_high,
            "batch_contract": {"max_texts": 128, "max_total_chars": 320000, "max_chars_per_text": 16000},
            "list_rate_usd_per_million": "0.12",
            "usd_planning_proxy_low": _money(embedding_low, Decimal("0.12")),
            "usd_planning_proxy_high": _money(embedding_high, Decimal("0.12")),
            "free_tier_assumed": False,
            "exact_batch_manifest_available_after_context_generation_only": True,
        },
    }


def _manifest(rows: list[dict[str, Any]], key: str) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item[key]):
        digest.update(_canonical(row) + b"\n")
    return digest.hexdigest()


def preflight(
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if prereg_path.resolve() != DEFAULT_PREREG.resolve():
        raise RuntimeError("M2.7 prereg path mismatch")
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("instrument") != "s117_m27_upstream_sql_budget_prereg_v1"
        or prereg.get("status") != "frozen_before_seeded_local_audit"
    ):
        raise RuntimeError("M2.7 prereg drift")
    for item in _iter_hashed_paths(prereg.get("frozen_inputs", {})):
        path = (ROOT / item["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("M2.7 frozen input escapes workspace") from exc
        if _sha_file(path) != item["sha256"]:
            raise RuntimeError(f"M2.7 frozen input drift: {item['path']}")
    m26_prereg = ROOT / prereg["selected_paths"]["m26_prereg"]
    _, m2_state = m26.preflight(m26_prereg, store, sidecar_root, source_snapshot)
    return prereg, m2_state


def run_audit(
    *,
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
    seed: int,
) -> dict[str, Any]:
    prereg, m2_state = preflight(prereg_path, store, sidecar_root, source_snapshot)
    if seed not in prereg["execution"]["seeds"]:
        raise RuntimeError("M2.7 unregistered seed")
    m26_result = json.loads(
        (ROOT / prereg["selected_paths"]["m26_result"]).read_text(encoding="utf-8")
    )
    if m26_result.get("contract_integrity") != "GO" or not all(m26_result["checks"].values()):
        raise RuntimeError("M2.6 source gate is not GO")

    s117_result_path = ROOT / m2_state["prereg"]["frozen_inputs"]["s117_development_result"]["path"]
    local_rows, local_receipt = m2.build_local_population(
        m2_state["record_files"],
        s117_result_path,
        m2_state["prereg"]["frozen_inputs"]["chunker"]["sha256"],
        sidecar_root,
    )
    _, _, remote_chunks, snapshot_receipt = m2.read_snapshot(source_snapshot)
    rng = random.Random(seed)
    rng.shuffle(local_rows)
    rng.shuffle(remote_chunks)
    local_by_id = {row["id"]: row for row in local_rows}
    donors_by_extraction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for donor in remote_chunks:
        if donor.get("parent_id") is None:
            donors_by_extraction[donor.get("extraction_sha256")].append(donor)
    for donors in donors_by_extraction.values():
        donors.sort(key=lambda row: (row.get("chunk_index", -1), row.get("id") or ""))

    development = json.loads(s117_result_path.read_text(encoding="utf-8"))
    provenance = _provenance_receipts(
        m2_state["record_files"],
        materialization_id=development["generation"]["materialization_id"],
        chunker_sha256=m2_state["prereg"]["frozen_inputs"]["chunker"]["sha256"],
    )
    m26_rows = m26_result["rows"]
    live_source = [
        row for row in m26_rows
        if row["load_binding_status"] == "live_exact_active"
        and row["retrieval_policy_class"] == "eligible"
        and row["structural_identity_status"] in TARGET_STRUCTURAL_STATUSES
    ]
    projected_source = [
        row for row in m26_rows
        if row["load_binding_status"] == "projected_backfill_candidate"
        and row["retrieval_policy_class"] == "eligible"
        and row["structural_identity_status"] in TARGET_STRUCTURAL_STATUSES
    ]

    audit_rows: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    for cohort, source_rows in (("live", live_source), ("projected", projected_source)):
        for source in source_rows:
            local = local_by_id[source["local_row_id"]]
            row, task = _audit_row(
                local,
                source,
                donors_by_extraction.get(local["extraction_sha256"], []),
                provenance.get(local["id"]),
                cohort,
            )
            audit_rows.append(row)
            if task:
                tasks.append(task)

    live_returnable_ids = {
        row["local_row_id"]
        for row in m26_rows
        if row["effective_returnability_status"] == "returnable_static_envelope"
    }
    workload_rows = [local_by_id[row_id] for row_id in sorted(live_returnable_ids)]
    workload = _workload(workload_rows)

    expected = prereg["expected_population"]
    outcome_counts = {
        cohort: {
            outcome: sum(
                row["cohort"] == cohort and row["fidelity_outcome"] == outcome
                for row in audit_rows
            )
            for outcome in FIDELITY_OUTCOMES
        }
        for cohort in ("live", "projected")
    }
    live_unresolved = outcome_counts["live"]["unresolved_requires_adjudication"]
    live_risk = outcome_counts["live"]["material_fidelity_risk"]
    task_manifest_sha256 = _manifest(tasks, "task_receipt_sha256")
    checks = {
        "m26_source_gate_go": True,
        "local_population_exact": local_receipt["rows"] == expected["local_rows"],
        "live_target_count_exact": len(live_source) == expected["live_targets"],
        "projected_target_count_exact": len(projected_source) == expected["projected_targets"],
        "workload_logical_calls_exact": len(workload_rows) == expected["fresh_context_rows"],
        "workload_documents_exact": len({row["extraction_sha256"] for row in workload_rows}) == expected["fresh_context_documents"],
        "fidelity_taxonomy_closed": set(row["fidelity_outcome"] for row in audit_rows) <= set(FIDELITY_OUTCOMES),
        "every_target_exactly_once": len(audit_rows) == len({row["local_row_id"] for row in audit_rows}),
        "task_rows_match_unresolved": len(tasks)
        == sum(row["fidelity_outcome"] == "unresolved_requires_adjudication" for row in audit_rows),
        "no_adjudication_imported": all(row["fidelity_outcome"] != "adjudicated_benign_delta" for row in audit_rows),
        "no_external_cost": True,
    }
    integrity = "GO" if all(checks.values()) else "NO_GO"
    readiness = "GO" if integrity == "GO" and live_unresolved == 0 and live_risk == 0 else "NO_GO"
    result = {
        "instrument": "s117_m27_upstream_sql_budget_v1",
        "contract_integrity": integrity,
        "local_readiness": readiness,
        "status": f"CONTRACT_{integrity}_LOCAL_READINESS_{readiness}",
        "counts": {
            "targets": {"live": len(live_source), "projected": len(projected_source)},
            "fidelity_outcomes": outcome_counts,
            "adjudication_tasks": {
                "live": sum(task["cohort"] == "live" for task in tasks),
                "projected": sum(task["cohort"] == "projected" for task in tasks),
            },
        },
        "workload": workload,
        "manifests": {
            "audit_rows_sha256": _manifest(audit_rows, "local_row_id"),
            "task_manifest_sha256": task_manifest_sha256,
            "workload_local_ids_sha256": _sha_bytes(_canonical(sorted(live_returnable_ids))),
        },
        "audit_rows": sorted(audit_rows, key=lambda row: (row["cohort"], row["local_row_id"])),
        "task_manifest": {
            "schema": "s117_m27_fidelity_task_manifest_v1",
            "sha256": task_manifest_sha256,
            "rows": sorted(tasks, key=lambda row: (row["cohort"], row["local_row_id"])),
        },
        "checks": checks,
        "authorization": {
            "adjudication_import": False,
            "context_generation": False,
            "embedding_generation": False,
            "database": False,
            "schema_apply": False,
            "load": False,
            "serving": False,
            "M3": "BLOCKED",
        },
        "claim": {
            "structure_only_is_semantic_improvement": False,
            "projected_is_live": False,
            "reuse_admitted": False,
            "token_or_billing_exact": False,
        },
        "cost": {"database_reads": 0, "database_writes": 0, "model_calls": 0, "vector_payloads": 0},
        "source": {"snapshot": snapshot_receipt, "local": local_receipt},
        "dependencies": {
            "prereg_sha256": _sha_file(prereg_path),
            "runner_sha256": _sha_file(Path(__file__)),
            "m26_result_sha256": _sha_file(ROOT / prereg["selected_paths"]["m26_result"]),
            "sql_spec_sha256": _sha_file(ROOT / prereg["selected_paths"]["sql_spec"]),
        },
    }
    result["determinism"] = {"logical_payload_sha256": _sha_bytes(_canonical(result))}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run_audit(
        prereg_path=args.prereg,
        store=args.store,
        sidecar_root=args.sidecar_root,
        source_snapshot=args.source_snapshot,
        seed=args.seed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, allow_nan=False, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "counts": result["counts"],
        "workload": result["workload"],
        "checks": result["checks"],
        "determinism": result["determinism"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["contract_integrity"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
