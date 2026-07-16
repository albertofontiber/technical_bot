#!/usr/bin/env python3
"""Independent local audit of retrieval eligibility and legacy enrichment evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from scripts import s117_m2_legacy_reuse_analysis as m2
from src.reingest import retrieval_policy


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m26_independent_audit_prereg_v1.yaml"

LOAD_STATUSES = (
    "live_exact_active",
    "live_exact_nonactive",
    "projected_backfill_candidate",
    "projected_backfill_nonactive",
    "binding_unresolved",
)
STRUCTURAL_STATUSES = (
    "no_content_donor",
    "no_structural_donor",
    "multiple_structural_donors",
    "unique_donor_marked_duplicate",
    "independent_unique_structural_donor",
)
BINDING_EVIDENCE_STATUSES = (
    "structural_donor_not_unique",
    "live_exact_document_match",
    "projected_observed_document_match",
    "expected_document_binding_unavailable",
    "donor_document_binding_mismatch",
)
CONTEXT_STATUSES = (
    "structural_identity_not_unique",
    "context_missing_or_empty",
    "context_generation_receipt_unavailable",
    "context_output_receipt_unavailable",
    "context_contract_mismatch",
    "context_target_donor_input_mismatch",
    "context_evidence_compatible",
)
EMBEDDING_STATUSES = (
    "structural_identity_not_unique",
    "embedding_missing",
    "embedding_model_receipt_unavailable",
    "embedding_vector_receipt_unavailable",
    "embedding_query_contract_mismatch",
    "embedding_target_donor_input_mismatch",
    "embedding_evidence_compatible",
)
EFFECTIVE_STATUSES = (
    "binding_not_live_active",
    "policy_excluded",
    "returnable_static_envelope",
)
STRUCTURE_FIELDS = (
    "section_title",
    "section_path",
    "page_number",
    "is_flow_diagram",
    "has_diagram",
    "confidence_f32",
)


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


def preflight(
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if prereg_path.resolve() != DEFAULT_PREREG.resolve():
        raise RuntimeError("M2.6 independent audit prereg path mismatch")
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("instrument") != "s117_m26_independent_audit_prereg_v1"
        or prereg.get("status") != "frozen_before_seeded_independent_audit"
    ):
        raise RuntimeError("M2.6 independent audit prereg drift")
    for item in _iter_hashed_paths(prereg.get("frozen_inputs", {})):
        path = (ROOT / item["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("M2.6 frozen input escapes workspace") from exc
        if _sha_file(path) != item["sha256"]:
            raise RuntimeError(f"M2.6 frozen input drift: {item['path']}")
    if source_snapshot.resolve() != (
        ROOT / prereg["selected_paths"]["source_snapshot"]
    ).resolve():
        raise RuntimeError("M2.6 source snapshot path mismatch")
    m2_state = m2.preflight(
        ROOT / prereg["selected_paths"]["m2_prereg"], store, sidecar_root
    )
    return prereg, m2_state


def _policy_contract_sha256(prereg: dict[str, Any]) -> str:
    contract = prereg["policy_contract"]
    if (
        contract["design_sha256"]
        != prereg["frozen_inputs"]["design_v4"]["sha256"]
        or contract["implementation_sha256"]
        != prereg["frozen_inputs"]["policy"]["sha256"]
    ):
        raise RuntimeError("M2.6 policy contract is not bound to frozen inputs")
    payload = {
        "design_sha256": contract["design_sha256"],
        "implementation_sha256": contract["implementation_sha256"],
        "policy": retrieval_policy.contract_payload(),
    }
    observed = _sha_bytes(_canonical(payload))
    if observed != contract["sha256"]:
        raise RuntimeError("M2.6 retrieval policy contract drift")
    return observed


def _validate_enrichment_contracts(prereg: dict[str, Any]) -> None:
    observed_context = {
        "contextualizer_sha256": prereg["frozen_inputs"]["contextualizer"][
            "sha256"
        ],
        "context_prompt_sha256": _sha_bytes(
            m2.contextualize._INSTRUCTION.encode("utf-8")
        ),
        "context_model": m2.contextualize._MODEL,
        "context_limits": {
            "max_doc_chars": m2.contextualize._MAX_DOC_CHARS,
            "max_chunk_chars": m2.contextualize._MAX_CHUNK_CHARS,
            "max_output_tokens": 200,
        },
    }
    observed_embedding = {
        "embedding_provider": m2.embed.EMBED_PROVIDER,
        "embedding_model": m2.embed.EMBED_MODEL,
        "embedding_input_type": "document",
        "embedding_dimensions": m2.embed.EMBED_DIMENSIONS,
        "embedding_max_chars": m2.embed._MAX_EMBED_CHARS,
    }
    if observed_context != prereg["expected_context_contract"]:
        raise RuntimeError("M2.6 context contract drift")
    if observed_embedding != prereg["expected_embedding_contract"]:
        raise RuntimeError("M2.6 embedding contract drift")


def _structure_matches(local: dict[str, Any], donor: dict[str, Any]) -> bool:
    return all(local.get(field) == donor.get(field) for field in STRUCTURE_FIELDS)


def _discover_structural(
    local: dict[str, Any], donors: list[dict[str, Any]]
) -> tuple[str, dict[str, Any] | None]:
    content_candidates = [
        donor
        for donor in donors
        if donor.get("extraction_sha256") == local["extraction_sha256"]
        and donor.get("content") == local["content"]
    ]
    if not content_candidates:
        return "no_content_donor", None
    structural_candidates = [
        donor for donor in content_candidates if _structure_matches(local, donor)
    ]
    if not structural_candidates:
        return "no_structural_donor", None
    if len(structural_candidates) != 1:
        return "multiple_structural_donors", None
    donor = structural_candidates[0]
    if donor.get("duplicate_of") is not None:
        return "unique_donor_marked_duplicate", donor
    return "independent_unique_structural_donor", donor


def _binding_status_and_expected_id(
    primary_row: dict[str, Any], binding_row: dict[str, Any]
) -> tuple[str, str | None]:
    terminal = primary_row["terminal"]
    if terminal == "primary_unique_active_pdf_sha":
        return "live_exact_active", primary_row["document_id"]
    if terminal == "primary_non_active_pdf_sha":
        return "live_exact_nonactive", primary_row["document_id"]
    fallback = binding_row["terminal"]
    if fallback == "fallback_unique_active_backfill_binding":
        return "projected_backfill_candidate", binding_row["document_id"]
    if fallback == "fallback_non_active_document":
        return "projected_backfill_nonactive", None
    return "binding_unresolved", None


def _validate_primary_binding_against_source(
    primary_rows: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> str:
    documents_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        documents_by_sha[document.get("source_pdf_sha256")].append(document)
    receipts: list[dict[str, Any]] = []
    for primary in primary_rows:
        matches = documents_by_sha.get(primary["extraction_sha256"], [])
        if not matches:
            observed = {
                "terminal": "primary_absent_pdf_sha",
                "document_id": None,
                "status": None,
                "matching_document_count": 0,
            }
        elif len(matches) != 1:
            observed = {
                "terminal": "primary_ambiguous_pdf_sha",
                "document_id": None,
                "status": None,
                "matching_document_count": len(matches),
            }
        else:
            document = matches[0]
            observed = {
                "terminal": (
                    "primary_unique_active_pdf_sha"
                    if document.get("status") == "active"
                    else "primary_non_active_pdf_sha"
                ),
                "document_id": document["id"],
                "status": document.get("status"),
                "matching_document_count": 1,
            }
        expected = {
            key: primary.get(key)
            for key in (
                "terminal",
                "document_id",
                "status",
                "matching_document_count",
            )
        }
        if observed != expected:
            raise RuntimeError("M2.6 primary binding contradicts source documents")
        receipts.append({"extraction_sha256": primary["extraction_sha256"], **observed})
    return _manifest_binding_receipts(receipts)


def _manifest_binding_receipts(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["extraction_sha256"]):
        digest.update(_canonical(row) + b"\n")
    return digest.hexdigest()


def _donor_binding_evidence(
    structural_status: str,
    donor: dict[str, Any] | None,
    load_status: str,
    expected_document_id: str | None,
) -> str:
    if donor is None or structural_status not in {
        "unique_donor_marked_duplicate",
        "independent_unique_structural_donor",
    }:
        return "structural_donor_not_unique"
    if expected_document_id is None:
        return "expected_document_binding_unavailable"
    if donor.get("document_id") != expected_document_id:
        return "donor_document_binding_mismatch"
    if load_status in {"live_exact_active", "live_exact_nonactive"}:
        return "live_exact_document_match"
    if load_status == "projected_backfill_candidate":
        return "projected_observed_document_match"
    return "expected_document_binding_unavailable"


def _context_evidence(
    local: dict[str, Any],
    donor: dict[str, Any] | None,
    structural_status: str,
    expected_contract: dict[str, Any],
) -> str:
    if structural_status != "independent_unique_structural_donor" or donor is None:
        return "structural_identity_not_unique"
    context = donor.get("context")
    if not isinstance(context, str) or not context.strip():
        return "context_missing_or_empty"
    generation_fields = (
        "context_input_sha256",
        "contextualizer_sha256",
        "context_prompt_sha256",
        "context_model",
        "context_limits",
    )
    if any(donor.get(field) is None for field in generation_fields):
        return "context_generation_receipt_unavailable"
    if donor.get("context_sha256") is None:
        return "context_output_receipt_unavailable"
    if donor["context_sha256"] != _sha_bytes(context.encode("utf-8")):
        raise RuntimeError("declared context output receipt is inconsistent")
    observed_contract = {
        "contextualizer_sha256": donor["contextualizer_sha256"],
        "context_prompt_sha256": donor["context_prompt_sha256"],
        "context_model": donor["context_model"],
        "context_limits": donor["context_limits"],
    }
    if observed_contract != expected_contract:
        return "context_contract_mismatch"
    if donor["context_input_sha256"] != local["context_input_sha256"]:
        return "context_target_donor_input_mismatch"
    return "context_evidence_compatible"


def _vector_sha256(values: list[Any]) -> str:
    payload = bytearray()
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise RuntimeError("declared embedding payload is non-finite")
        payload.extend(struct.pack(">f", number))
    return _sha_bytes(bytes(payload))


def _embedding_evidence(
    local: dict[str, Any],
    donor: dict[str, Any] | None,
    structural_status: str,
    expected_contract: dict[str, Any],
) -> str:
    if structural_status != "independent_unique_structural_donor" or donor is None:
        return "structural_identity_not_unique"
    if donor.get("embedding_present") is not True:
        return "embedding_missing"
    model_fields = (
        "embedding_input_sha256",
        "embedding_provider",
        "embedding_model",
        "embedding_input_type",
        "embedding_dimensions",
        "embedding_max_chars",
    )
    if any(donor.get(field) is None for field in model_fields):
        return "embedding_model_receipt_unavailable"
    payload = donor.get("embedding_payload_f32")
    if donor.get("embedding_sha256") is None or not isinstance(payload, list):
        return "embedding_vector_receipt_unavailable"
    if donor["embedding_sha256"] != _vector_sha256(payload):
        raise RuntimeError("declared embedding vector receipt is inconsistent")
    observed_contract = {
        "embedding_provider": donor["embedding_provider"],
        "embedding_model": donor["embedding_model"],
        "embedding_input_type": donor["embedding_input_type"],
        "embedding_dimensions": donor["embedding_dimensions"],
        "embedding_max_chars": donor["embedding_max_chars"],
    }
    if observed_contract != expected_contract:
        return "embedding_query_contract_mismatch"
    if len(payload) != donor["embedding_dimensions"]:
        raise RuntimeError("declared embedding dimensions contradict payload")
    context = donor.get("context")
    if not isinstance(context, str) or not context.strip():
        return "embedding_target_donor_input_mismatch"
    expected_input = m2._embedding_receipt(context, local["content"])[
        "embedding_input_sha256"
    ]
    if donor["embedding_input_sha256"] != expected_input:
        return "embedding_target_donor_input_mismatch"
    return "embedding_evidence_compatible"


def _effective_status(load_status: str, policy_class: str) -> str:
    if load_status != "live_exact_active":
        return "binding_not_live_active"
    if not retrieval_policy.is_eligible(policy_class):
        return "policy_excluded"
    return "returnable_static_envelope"


def _authorization(
    *,
    load_status: str,
    policy_class: str,
    structural_status: str,
    binding_evidence: str,
    context_status: str,
    embedding_status: str,
) -> tuple[bool, bool]:
    base_authorizable = (
        load_status == "live_exact_active"
        and policy_class == "eligible"
        and structural_status == "independent_unique_structural_donor"
        and binding_evidence == "live_exact_document_match"
    )
    context_authorized = (
        base_authorizable and context_status == "context_evidence_compatible"
    )
    embedding_authorized = (
        context_authorized
        and embedding_status == "embedding_evidence_compatible"
    )
    return context_authorized, embedding_authorized


def _counter_payload(counter: Counter, terminals: tuple[str, ...]) -> dict[str, int]:
    return {terminal: counter.get(terminal, 0) for terminal in terminals}


def _taxonomy_closed(
    counter: Counter, terminals: tuple[str, ...], expected_rows: int
) -> bool:
    return set(counter) <= set(terminals) and sum(counter.values()) == expected_rows


def _manifest(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["local_row_id"]):
        digest.update(_canonical(row) + b"\n")
    return digest.hexdigest()


def run_audit(
    *,
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
    seed: int,
) -> dict[str, Any]:
    prereg, m2_state = preflight(
        prereg_path, store, sidecar_root, source_snapshot
    )
    _validate_enrichment_contracts(prereg)
    if seed not in prereg["execution"]["seeds"]:
        raise RuntimeError("M2.6 unregistered seed")
    s117_result_path = ROOT / m2_state["prereg"]["frozen_inputs"][
        "s117_development_result"
    ]["path"]
    local_rows, local_receipt = m2.build_local_population(
        m2_state["record_files"],
        s117_result_path,
        m2_state["prereg"]["frozen_inputs"]["chunker"]["sha256"],
        sidecar_root,
    )
    snapshot_header, documents, remote_chunks, snapshot_receipt = m2.read_snapshot(
        source_snapshot
    )
    rng = random.Random(seed)
    rng.shuffle(local_rows)
    rng.shuffle(documents)
    rng.shuffle(remote_chunks)
    base_chunks = [row for row in remote_chunks if row.get("parent_id") is None]
    donors_by_extraction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for donor in base_chunks:
        donors_by_extraction[donor.get("extraction_sha256")].append(donor)

    primary = json.loads(
        (ROOT / prereg["selected_paths"]["primary_baseline"]).read_text(
            encoding="utf-8"
        )
    )
    m25 = json.loads(
        (ROOT / prereg["selected_paths"]["m25_result"]).read_text(encoding="utf-8")
    )
    primary_by_sha = {row["extraction_sha256"]: row for row in primary["rows"]}
    binding_by_sha = {
        row["extraction_sha256"]: row for row in m25["binding"]["rows"]
    }
    if set(primary_by_sha) != set(binding_by_sha) or len(primary_by_sha) != 1068:
        raise RuntimeError("M2.6 binding population drift")
    source_binding_manifest = _validate_primary_binding_against_source(
        primary["rows"], documents
    )

    expected_context_contract = prereg["expected_context_contract"]
    expected_embedding_contract = prereg["expected_embedding_contract"]
    policy_contract_sha256 = _policy_contract_sha256(prereg)
    audit_rows: list[dict[str, Any]] = []
    counters = {
        "load": Counter(),
        "policy": Counter(),
        "structural": Counter(),
        "binding_evidence": Counter(),
        "context": Counter(),
        "embedding": Counter(),
        "effective": Counter(),
    }
    authorized_context = 0
    authorized_embedding = 0
    for local in local_rows:
        sha = local["extraction_sha256"]
        load_status, expected_document_id = _binding_status_and_expected_id(
            primary_by_sha[sha], binding_by_sha[sha]
        )
        policy_class = retrieval_policy.classify(
            local.get("preterminal"), local.get("duplicate_of")
        )
        structural_status, donor = _discover_structural(
            local, donors_by_extraction.get(sha, [])
        )
        binding_evidence = _donor_binding_evidence(
            structural_status,
            donor,
            load_status,
            expected_document_id,
        )
        context_status = _context_evidence(
            local, donor, structural_status, expected_context_contract
        )
        embedding_status = _embedding_evidence(
            local, donor, structural_status, expected_embedding_contract
        )
        effective_status = _effective_status(load_status, policy_class)
        context_authorized, embedding_authorized = _authorization(
            load_status=load_status,
            policy_class=policy_class,
            structural_status=structural_status,
            binding_evidence=binding_evidence,
            context_status=context_status,
            embedding_status=embedding_status,
        )
        authorized_context += int(context_authorized)
        authorized_embedding += int(embedding_authorized)
        policy_receipt = {
            "extraction_sha256": sha,
            "chunk_index": local["chunk_index"],
            "retrieval_policy_class": policy_class,
            "language": local.get("language"),
            "duplicate_of": local.get("duplicate_of"),
            "policy_contract_sha256": policy_contract_sha256,
        }
        core = {
            "local_row_id": local["id"],
            "extraction_sha256": sha,
            "chunk_index": local["chunk_index"],
            "load_binding_status": load_status,
            "retrieval_policy_class": policy_class,
            "policy_receipt_sha256": _sha_bytes(_canonical(policy_receipt)),
            "structural_identity_status": structural_status,
            "independent_donor_chunk_id": donor.get("id") if donor else None,
            "donor_binding_evidence_status": binding_evidence,
            "context_evidence_status": context_status,
            "embedding_evidence_status": embedding_status,
            "effective_returnability_status": effective_status,
            "context_authorized": context_authorized,
            "embedding_authorized": embedding_authorized,
        }
        row = {**core, "receipt_sha256": _sha_bytes(_canonical(core))}
        audit_rows.append(row)
        counters["load"][load_status] += 1
        counters["policy"][policy_class] += 1
        counters["structural"][structural_status] += 1
        counters["binding_evidence"][binding_evidence] += 1
        counters["context"][context_status] += 1
        counters["embedding"][embedding_status] += 1
        counters["effective"][effective_status] += 1

    # Membership is consumed only after independent discovery/classification.
    cohort_freeze = json.loads(
        (ROOT / prereg["selected_paths"]["cohort_freeze"]).read_text(
            encoding="utf-8"
        )
    )
    row_by_id = {row["local_row_id"]: row for row in audit_rows}
    cohort_results: dict[str, Any] = {}
    cohort_ids: dict[str, set[str]] = {}
    for name, cohort in cohort_freeze["cohorts"].items():
        frozen_pairs = {
            row["local_row_id"]: row["donor_chunk_id"] for row in cohort["rows"]
        }
        ids = set(frozen_pairs)
        cohort_ids[name] = ids
        if not ids <= set(row_by_id):
            raise RuntimeError(f"M2.6 cohort rows missing from audit: {name}")
        selected = [row_by_id[local_id] for local_id in sorted(ids)]
        cohort_results[name] = {
            "count": len(selected),
            "load_binding_status": dict(
                sorted(Counter(row["load_binding_status"] for row in selected).items())
            ),
            "retrieval_policy_class": dict(
                sorted(Counter(row["retrieval_policy_class"] for row in selected).items())
            ),
            "structural_identity_status": dict(
                sorted(
                    Counter(row["structural_identity_status"] for row in selected).items()
                )
            ),
            "donor_binding_evidence_status": dict(
                sorted(
                    Counter(
                        row["donor_binding_evidence_status"] for row in selected
                    ).items()
                )
            ),
            "context_evidence_status": dict(
                sorted(Counter(row["context_evidence_status"] for row in selected).items())
            ),
            "embedding_evidence_status": dict(
                sorted(
                    Counter(row["embedding_evidence_status"] for row in selected).items()
                )
            ),
            "frozen_donor_matches_independent": sum(
                row_by_id[local_id]["independent_donor_chunk_id"] == donor_id
                for local_id, donor_id in frozen_pairs.items()
            ),
            "authorized_context_rows": sum(
                row["context_authorized"] for row in selected
            ),
            "authorized_embedding_rows": sum(
                row["embedding_authorized"] for row in selected
            ),
            "audit_receipt_manifest_sha256": _manifest(selected),
        }

    expected = prereg["expected_evidence"]
    observed_load = _counter_payload(counters["load"], LOAD_STATUSES)
    observed_policy = _counter_payload(
        counters["policy"], retrieval_policy.POLICY_CLASSES
    )
    checks = {
        "local_target_count_exact": len(audit_rows) == expected["local_targets"],
        "legacy_base_donor_count_exact": len(base_chunks)
        == expected["legacy_base_donors"],
        "load_binding_counts_exact": observed_load == expected["load_binding_status"],
        "source_binding_manifest_exact": source_binding_manifest
        == expected["source_binding_receipts_sha256"],
        "policy_counts_exact": observed_policy == expected["policy_counts"],
        "policy_taxonomy_closed": _taxonomy_closed(
            counters["policy"], retrieval_policy.POLICY_CLASSES, len(audit_rows)
        ),
        "structural_taxonomy_closed": _taxonomy_closed(
            counters["structural"], STRUCTURAL_STATUSES, len(audit_rows)
        ),
        "binding_evidence_taxonomy_closed": _taxonomy_closed(
            counters["binding_evidence"],
            BINDING_EVIDENCE_STATUSES,
            len(audit_rows),
        ),
        "context_taxonomy_closed": _taxonomy_closed(
            counters["context"], CONTEXT_STATUSES, len(audit_rows)
        ),
        "embedding_taxonomy_closed": _taxonomy_closed(
            counters["embedding"], EMBEDDING_STATUSES, len(audit_rows)
        ),
        "effective_taxonomy_closed": _taxonomy_closed(
            counters["effective"], EFFECTIVE_STATUSES, len(audit_rows)
        ),
        "cohort_counts_exact": {
            name: result["count"] for name, result in cohort_results.items()
        }
        == expected["cohorts"],
        "new_m25_cohort_policy_clean": cohort_results["new_m25_strict"][
            "retrieval_policy_class"
        ]
        == {"eligible": expected["cohorts"]["new_m25_strict"]},
        "authorized_context_rows_exact_zero": authorized_context
        == expected["authorized_context_rows"],
        "authorized_embedding_rows_exact_zero": authorized_embedding
        == expected["authorized_embedding_rows"],
        "embedding_never_authorized_without_context": all(
            not row["embedding_authorized"] or row["context_authorized"]
            for row in audit_rows
        ),
        "cohort_freeze_checks_all": all(cohort_freeze["checks"].values()),
        "m25_checks_all": all(m25["checks"].values())
        and all(m25["projection"]["checks"].values()),
        "source_snapshot_vector_payloads_zero": snapshot_header.get(
            "vector_payloads"
        )
        == 0,
        "no_reuse_admitted": True,
    }
    contract_integrity = "GO" if all(checks.values()) else "NO_GO"
    result = {
        "instrument": "s117_m26_independent_reuse_audit_v1",
        "contract_integrity": contract_integrity,
        "status": (
            "CONTRACT_INTEGRITY_GO"
            if contract_integrity == "GO"
            else "CONTRACT_INTEGRITY_NO_GO"
        ),
        "source_snapshot": snapshot_receipt,
        "local": local_receipt,
        "counts": {
            "load_binding_status": observed_load,
            "retrieval_policy_class": observed_policy,
            "structural_identity_status": _counter_payload(
                counters["structural"], STRUCTURAL_STATUSES
            ),
            "donor_binding_evidence_status": _counter_payload(
                counters["binding_evidence"], BINDING_EVIDENCE_STATUSES
            ),
            "context_evidence_status": _counter_payload(
                counters["context"], CONTEXT_STATUSES
            ),
            "embedding_evidence_status": _counter_payload(
                counters["embedding"], EMBEDDING_STATUSES
            ),
            "effective_returnability_status": _counter_payload(
                counters["effective"], EFFECTIVE_STATUSES
            ),
        },
        "cohorts": cohort_results,
        "authorization": {
            "authorized_context_rows": authorized_context,
            "authorized_embedding_rows": authorized_embedding,
            "regenerate_context_rows": counters["effective"][
                "returnable_static_envelope"
            ],
            "regenerate_embedding_rows": counters["effective"][
                "returnable_static_envelope"
            ],
            "M3": "BLOCKED",
        },
        "manifests": {
            "audit_rows_sha256": _manifest(audit_rows),
            "source_binding_receipts_sha256": source_binding_manifest,
        },
        "rows": sorted(audit_rows, key=lambda item: item["local_row_id"]),
        "checks": checks,
        "claim": {
            "contract_integrity_only": True,
            "reuse_admitted": False,
            "projected_bindings_are_live": False,
        },
        "cost": {
            "database_reads": 0,
            "database_writes": 0,
            "model_calls": 0,
            "vector_payloads": 0,
        },
        "dependencies": {
            "prereg_sha256": _sha_file(prereg_path),
            "runner_sha256": _sha_file(Path(__file__)),
            "policy_sha256": _sha_file(Path(retrieval_policy.__file__)),
        },
    }
    logical = _canonical(result)
    result["determinism"] = {"logical_payload_sha256": _sha_bytes(logical)}
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
        json.dumps(result, allow_nan=False, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "counts": result["counts"],
                "cohorts": result["cohorts"],
                "authorization": result["authorization"],
                "checks": result["checks"],
                "determinism": result["determinism"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["contract_integrity"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
