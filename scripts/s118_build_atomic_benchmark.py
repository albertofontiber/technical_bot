#!/usr/bin/env python3
"""Build a lineage-safe atomic projection of the frozen S100 benchmark.

This is a local measurement bridge.  It does not mutate either gold ruler and
does not classify transformed claims from their parent result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
FACT_KEY = re.compile(r"^(?P<qid>[^#]+)#(?P<index>[0-9]+):(?P<value>.*)$")
CONTENT_STAGES = {"OK", "synthesis-miss", "rerank-miss", "retrieval-miss"}
FORBIDDEN_TRANSFORM_KEYS = {
    "answer", "answer_sha256", "answer_status", "baseline_class", "best_pool_rank",
    "in_pool", "in_topk", "reaches_gen", "stage", "stage_class", "target_class",
}
AFTER_REQUIRED_KEYS = {
    "migration_id", "texto", "tipo", "estado", "valor", "cita", "source_pages",
    "basis", "requiredness_reason",
}
TRANSFORM_REQUIRED_KEYS = {
    "migration_id", "qid", "fact_key", "parent_fact_sha",
    "required_adjudicated_class", "operation", "after", "withdrawals",
}
DELTA_OPERATIONS = {
    "split_and_withdraw_unsupported_absence",
    "demote_and_withdraw_unsupported_impossibility",
}
ACCEPTED_ADJUDICATION_KEYS = {
    "row_type", "parent_identity", "child_id", "supported_subclaim_id",
    "supported_subclaim", "supported_subclaim_sha256", "texto_sha256",
    "valor_sha256", "cita_sha256", "citation_binding", "basis",
    "score_track", "requiredness", "requiredness_rationale",
    "adjudicator_status", "independent_of_runtime_outcome",
}
WITHDRAWAL_ADJUDICATION_KEYS = {
    "row_type", "parent_identity", "withdrawal_id", "unsupported_subclaim",
    "unsupported_subclaim_sha256", "adjudicator_status",
    "independent_of_runtime_outcome",
}
PARENT_IDENTITY_KEYS = {"qid", "fact_key", "parent_fact_sha256", "hold_class"}
CITATION_BINDING_KEYS = {
    "search_fact_key", "candidate_id", "manual_id", "page_numbers",
    "excerpt_sha256",
}


class StrictSafeLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):  # type: ignore[no-untyped-def]
        if self.check_event(yaml.AliasEvent):
            raise ValueError("YAML aliases are not allowed in frozen contracts")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):  # type: ignore[no-untyped-def]
        self.flatten_mapping(node)
        pairs = self.construct_pairs(node, deep=deep)
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate YAML key: {key!r}")
            result[key] = value
        return result


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_text_sha256(value: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> Any:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=StrictSafeLoader)
    _reject_nonfinite(value)
    return value


def load_json(path: Path) -> Any:
    def strict_pairs(pairs):  # type: ignore[no-untyped-def]
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key!r}")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {token}")
        ),
    )


def _reject_nonfinite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite YAML number is not allowed")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite(key)
            _reject_nonfinite(item)
    elif isinstance(value, list):
        for item in value:
            _reject_nonfinite(item)


def _assert_exact_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or not re.fullmatch(r"[0-9a-f]{64}", str(expected or "")):
        raise ValueError(f"{label} lacks a valid frozen file/hash")
    actual = file_sha256(path)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 drift: {actual} != {expected}")


def _recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_recursive_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_recursive_keys(item) for item in value), set())
    return set()


def _historical_core_facts(gold: dict) -> list[dict]:
    """Reproduce the S100 index domain, including later-excluded meta refs."""
    return [
        fact for fact in (gold.get("atomic_facts") or [])
        if isinstance(fact, dict)
        and fact.get("tipo") == "core"
        and fact.get("estado") == "presente"
    ]


def _is_meta_class(row: dict) -> bool:
    return row["baseline_class"] == "meta-ref"


def _stage_bucket(diagnostic_class: str) -> str:
    return diagnostic_class if diagnostic_class in CONTENT_STAGES else "rest"


def reconstruct_historical_population(
    gold_rows: list[dict], assessment: dict, current_ledger: dict,
) -> tuple[list[dict], dict[tuple[str, str], dict]]:
    gold_by_qid = {row.get("qid"): row for row in gold_rows}
    if len(gold_by_qid) != len(gold_rows) or None in gold_by_qid:
        raise ValueError("gold qids must be present and unique")

    ledger_rows = current_ledger.get("rows") or []
    ledger_by_key = {row.get("fact_key"): row for row in ledger_rows}
    if len(ledger_by_key) != len(ledger_rows) or None in ledger_by_key:
        raise ValueError("S114 fact keys must be present and unique")

    parents: list[dict] = []
    source_by_identity: dict[tuple[str, str], dict] = {}
    seen_keys: set[str] = set()
    for measured_gold in assessment.get("per_gold") or []:
        qid = measured_gold.get("qid")
        source_gold = gold_by_qid.get(qid)
        if not source_gold:
            raise ValueError(f"assessment qid absent from gold: {qid}")
        indexed = _historical_core_facts(source_gold)
        for measured in measured_gold.get("facts") or []:
            key = measured.get("key")
            match = FACT_KEY.fullmatch(str(key or ""))
            if not match or key in seen_keys or match.group("qid") != qid:
                raise ValueError(f"invalid or duplicate historical fact key: {key!r}")
            index = int(match.group("index"))
            if index >= len(indexed):
                raise ValueError(f"historical fact index outside gold: {key}")
            source_fact = indexed[index]
            measured_value = str(measured.get("valor") or "")
            source_value = str(source_fact.get("valor") or "")
            if match.group("value") != measured_value or measured_value != source_value:
                raise ValueError(f"historical value/identity drift: {key}")
            ledger = ledger_by_key.get(key)
            if not ledger or ledger.get("baseline_class") != measured.get("clase"):
                raise ValueError(f"S114 baseline does not match S100: {key}")
            parent_sha = object_sha256(source_fact)
            source_by_identity[(qid, parent_sha)] = source_fact
            parents.append({
                "fact_key": key,
                "qid": qid,
                "parent_fact_sha256": parent_sha,
                "baseline_class": measured.get("clase"),
                "current_diagnostic_class": ledger.get("diagnostic_class"),
                "current_diagnostic_evidence": ledger.get("diagnostic_evidence"),
                "source_fact": source_fact,
            })
            seen_keys.add(key)

    if set(ledger_by_key) != seen_keys:
        raise ValueError("S114 and S100 populations are not exactly equal")
    return parents, source_by_identity


def validate_m0_manifest(
    manifest: dict, gold_sha256: str,
    source_by_identity: dict[tuple[str, str], dict],
) -> dict[tuple[str, str], dict]:
    if (manifest.get("instrument") != "s106_atomic_migrator_v1"
            or (manifest.get("source") or {}).get("sha256") != gold_sha256
            or (manifest.get("validation") or {}) != {"v2_fact_errors": 0, "gold_store_errors": 0}):
        raise ValueError("M0 manifest identity or validation is not closed")
    changes = manifest.get("changes") or []
    by_parent: dict[tuple[str, str], dict] = {}
    migration_ids: set[str] = set()
    for change in changes:
        parent_sha = change.get("parent_fact_sha")
        migration_id = change.get("migration_id")
        qid = change.get("qid")
        identity = (qid, parent_sha)
        if (not re.fullmatch(r"[0-9a-f]{64}", str(parent_sha or ""))
                or not isinstance(qid, str) or not qid
                or not isinstance(migration_id, str) or not migration_id
                or identity in by_parent or migration_id in migration_ids):
            raise ValueError("M0 transformations lack unique identities")
        source = source_by_identity.get(identity)
        if source is not None and change.get("before") != source:
            raise ValueError(f"M0 before payload differs from parent: {migration_id}")
        if not isinstance(change.get("after"), list) or not change["after"]:
            raise ValueError(f"M0 transformation has no children: {migration_id}")
        by_parent[identity] = change
        migration_ids.add(migration_id)
    return by_parent


def _delta_parent_identities(
    spec: dict, parents: list[dict], source_by_identity: dict[tuple[str, str], dict],
) -> set[tuple[str, str]]:
    parent_by_key = {row["fact_key"]: row for row in parents}
    identities: set[tuple[str, str]] = set()
    for transform in spec.get("transformations") or []:
        qid = transform.get("qid")
        parent_sha = transform.get("parent_fact_sha")
        fact_key = transform.get("fact_key")
        identity = (qid, parent_sha)
        parent = parent_by_key.get(fact_key)
        if (not parent or parent["qid"] != qid
                or parent["parent_fact_sha256"] != parent_sha
                or source_by_identity.get(identity) != parent["source_fact"]
                or identity in identities):
            raise ValueError(f"delta parent identity mismatch: {fact_key}")
        identities.add(identity)
    return identities


def _validate_payload_receipt(value: dict, label: str) -> None:
    if not isinstance(value, dict) or not re.fullmatch(
        r"[0-9a-f]{64}", str(value.get("payload_sha256") or ""),
    ):
        raise ValueError(f"{label} payload receipt is missing")
    payload = dict(value)
    expected = payload.pop("payload_sha256")
    if object_sha256(payload) != expected:
        raise ValueError(f"{label} payload receipt drift")


def freeze_external_contract_projection(
    *, gold_rows: list[dict], assessment: dict, current_ledger: dict,
    m0_manifest: dict, m1_blockers: dict, delta_spec: dict,
    population_receipts: dict,
) -> dict:
    """Project external S106 contracts mechanically onto the frozen S100 cohort."""
    parents, source_by_identity = reconstruct_historical_population(
        gold_rows, assessment, current_ledger,
    )
    gold_sha = population_receipts["gold_v1"]["sha256"]
    m0_all = validate_m0_manifest(m0_manifest, gold_sha, source_by_identity)
    delta_identities = _delta_parent_identities(delta_spec, parents, source_by_identity)
    eligible_parent_identities = {
        (row["qid"], row["parent_fact_sha256"])
        for row in parents if not _is_meta_class(row)
    }
    m0_selected = {
        identity: change for identity, change in m0_all.items()
        if identity in eligible_parent_identities
    }
    if set(m0_selected) & delta_identities:
        raise ValueError("M0 and S118 transformations overlap")

    external = delta_spec.get("external_sources") or {}
    if set(external) != {"m0_full_manifest", "m1_pending_blockers"}:
        raise ValueError("external source contract is not exact")
    if (m1_blockers.get("schema") != "s106_m1_pending_blockers_v1"
            or m1_blockers.get("status") != "diagnostic_only_no_promotions"
            or not isinstance(m1_blockers.get("source_hashes"), dict)):
        raise ValueError("M1 blocker diagnostic identity is not closed")
    decisions = m1_blockers.get("decisions") or []
    if len(decisions) != (m1_blockers.get("counts") or {}).get("pending_decisions"):
        raise ValueError("M1 blocker decision count drift")

    carry_by_migration_id: dict[str, dict] = {}
    parent_by_identity = {
        (row["qid"], row["parent_fact_sha256"]): row for row in parents
    }
    for identity in sorted(eligible_parent_identities - set(m0_selected) - delta_identities):
        row = parent_by_identity[identity]
        migration_id = f"carry.{row['qid']}.{row['parent_fact_sha256'][:16]}"
        if migration_id in carry_by_migration_id:
            raise ValueError("carry prefix collision in frozen population")
        carry_by_migration_id[migration_id] = row

    known_holds: list[dict] = []
    seen_decisions: set[str] = set()
    for decision in decisions:
        migration_id = decision.get("migration_id")
        if not isinstance(migration_id, str) or migration_id in seen_decisions:
            raise ValueError("M1 blocker migration identities are not unique")
        seen_decisions.add(migration_id)
        parent = carry_by_migration_id.get(migration_id)
        if parent is None:
            continue
        if decision.get("qid") != parent["qid"]:
            raise ValueError(f"M1 blocker qid mismatch: {migration_id}")
        known_holds.append({
            "parent_identity": {
                "qid": parent["qid"],
                "fact_key": parent["fact_key"],
                "parent_fact_sha256": parent["parent_fact_sha256"],
            },
            "source_decision": decision,
        })

    expected = delta_spec.get("expected_bridge") or {}
    if len(m0_selected) != expected.get("m0_transformed_parents_in_population"):
        raise ValueError("projected M0 transformation count differs from contract")
    if len(known_holds) != expected.get("known_m1_contract_holds"):
        raise ValueError("projected M1 known-hold count differs from contract")

    projection = {
        "instrument": "s118_external_contract_projection_v1",
        "schema_version": 1,
        "status": "FROZEN_DIAGNOSTIC_PROJECTION_NO_PROMOTIONS",
        "source_receipts": {
            "m0_full_manifest": external["m0_full_manifest"],
            "m1_pending_blockers": {
                **external["m1_pending_blockers"],
                "upstream_receipts": m1_blockers["source_hashes"],
            },
        },
        "population_receipts": population_receipts,
        "selection_policy": {
            "m0": "all qid_plus_full_parent_sha matches in non_meta S100 population",
            "m1": "all exact carry.qid.parent_sha_prefix16 matches after M0 and S118 transforms",
            "runtime_outcome_fields_used": False,
            "promotions_authorized": False,
        },
        "source_counts": {
            "m0_changes": len(m0_manifest.get("changes") or []),
            "m1_pending_decisions": len(decisions),
        },
        "projected_counts": {
            "m0_changes": len(m0_selected),
            "m1_known_holds": len(known_holds),
        },
        "m0_changes": sorted(
            m0_selected.values(), key=lambda row: row["migration_id"],
        ),
        "m1_known_holds": sorted(
            known_holds, key=lambda row: row["parent_identity"]["fact_key"],
        ),
    }
    projection["payload_sha256"] = object_sha256(projection)
    return projection


def validate_external_contract_projection(
    projection: dict, *, gold_sha256: str, parents: list[dict],
    source_by_identity: dict[tuple[str, str], dict], delta_spec: dict,
    input_receipts: dict,
) -> tuple[dict[tuple[str, str], dict], dict[tuple[str, str], dict]]:
    _validate_payload_receipt(projection, "external contract projection")
    projected_source_receipts = {
        key: {k: v for k, v in value.items() if k != "upstream_receipts"}
        for key, value in (projection.get("source_receipts") or {}).items()
    }
    if (projection.get("instrument") != "s118_external_contract_projection_v1"
            or projection.get("status") != "FROZEN_DIAGNOSTIC_PROJECTION_NO_PROMOTIONS"
            or projected_source_receipts != delta_spec.get("external_sources")):
        raise ValueError("external contract projection identity drift")
    expected_population_receipts = {
        key: input_receipts[key]
        for key in ("gold_v1", "historical_assessment", "current_partial_ledger")
    }
    if projection.get("population_receipts") != expected_population_receipts:
        raise ValueError("external projection population receipt drift")

    projected_manifest = {
        "instrument": "s106_atomic_migrator_v1",
        "source": {"sha256": gold_sha256},
        "validation": {"v2_fact_errors": 0, "gold_store_errors": 0},
        "changes": projection.get("m0_changes") or [],
    }
    m0 = validate_m0_manifest(projected_manifest, gold_sha256, source_by_identity)
    parent_by_identity = {
        (row["qid"], row["parent_fact_sha256"]): row for row in parents
    }
    holds: dict[tuple[str, str], dict] = {}
    for row in projection.get("m1_known_holds") or []:
        parent_identity = row.get("parent_identity") or {}
        identity = (parent_identity.get("qid"), parent_identity.get("parent_fact_sha256"))
        parent = parent_by_identity.get(identity)
        decision = row.get("source_decision") or {}
        expected_migration = f"carry.{identity[0]}.{str(identity[1])[:16]}"
        if (not parent or parent_identity.get("fact_key") != parent["fact_key"]
                or decision.get("migration_id") != expected_migration
                or decision.get("qid") != identity[0] or identity in holds
                or identity in m0):
            raise ValueError("projected M1 hold identity drift")
        holds[identity] = row
    expected = delta_spec.get("expected_bridge") or {}
    if (len(m0) != expected.get("m0_transformed_parents_in_population")
            or len(holds) != expected.get("known_m1_contract_holds")):
        raise ValueError("external projection count drift")
    return m0, holds


def _adjudication_map(adjudication: dict) -> dict[str, dict]:
    rows = adjudication.get("rows") or []
    result = {row.get("fact_key"): row for row in rows}
    if len(result) != len(rows) or None in result:
        raise ValueError("atomicity adjudication fact keys must be unique")
    return result


def _evidence_candidates(search: dict) -> dict[tuple[str, str], dict]:
    result: dict[tuple[str, str], dict] = {}
    for row in search.get("rows") or []:
        fact_key = row.get("fact_key")
        for candidate in row.get("candidate_rows") or []:
            identity = (fact_key, candidate.get("id"))
            if None in identity or identity in result:
                raise ValueError("evidence candidate identities must be unique")
            result[identity] = candidate
    return result


def _validate_child_adjudication_header(
    child_adjudication: dict, input_receipts: dict,
) -> None:
    expected_keys = {
        "instrument", "status", "normalization", "independent_of_runtime_outcome",
        "source_receipts", "rows",
    }
    if (set(child_adjudication) != expected_keys
            or child_adjudication.get("instrument") != "s118_child_claim_adjudication_v1"
            or child_adjudication.get("status") != "frozen_before_hybrid_bridge_execution"
            or child_adjudication.get("normalization")
            != "NFKC_then_unicode_whitespace_collapse_then_utf8_sha256"
            or child_adjudication.get("independent_of_runtime_outcome") is not True):
        raise ValueError("child adjudication header is not frozen exactly")
    receipts = child_adjudication.get("source_receipts") or {}
    expected = {
        "gold_v1": {
            "path": input_receipts["gold_v1"]["logical_path"],
            "sha256": input_receipts["gold_v1"]["sha256"],
        },
        "s114_atomicity_adjudication": {
            "path": input_receipts["atomicity_adjudication"]["logical_path"],
            "sha256": input_receipts["atomicity_adjudication"]["sha256"],
        },
        "s114_evidence_search": {
            "path": input_receipts["evidence_search"]["logical_path"],
            "sha256": input_receipts["evidence_search"]["sha256"],
        },
    }
    if receipts != expected:
        raise ValueError("child adjudication source receipt drift")


def validate_delta_spec(
    spec: dict, parents: list[dict], source_by_identity: dict[tuple[str, str], dict],
    m0_by_parent: dict[tuple[str, str], dict], s114_adjudication: dict,
    child_adjudication: dict, evidence_search: dict, input_receipts: dict,
) -> dict[tuple[str, str], dict]:
    transformations = spec.get("transformations") or []
    forbidden = _recursive_keys(transformations) & FORBIDDEN_TRANSFORM_KEYS
    if forbidden:
        raise ValueError(f"delta transformations select on runtime outcomes: {sorted(forbidden)}")
    parent_by_key = {row["fact_key"]: row for row in parents}
    _validate_child_adjudication_header(child_adjudication, input_receipts)
    s114_adjudicated = _adjudication_map(s114_adjudication)
    candidates = _evidence_candidates(evidence_search)
    adjudication_rows = child_adjudication.get("rows") or []
    if _recursive_keys(adjudication_rows) & FORBIDDEN_TRANSFORM_KEYS:
        raise ValueError("child adjudication contains runtime outcome fields")
    accepted_by_child: dict[str, dict] = {}
    withdrawn_by_parent: dict[tuple[str, str], dict[str, dict]] = {}
    adjudicated_parent_identities: set[tuple[str, str]] = set()
    seen_supported_ids: set[str] = set()
    seen_withdrawal_ids: set[str] = set()
    for row in adjudication_rows:
        row_type = row.get("row_type")
        parent_identity = row.get("parent_identity") or {}
        if set(parent_identity) != PARENT_IDENTITY_KEYS:
            raise ValueError("child adjudication parent identity schema is not exact")
        identity = (
            parent_identity.get("qid"), parent_identity.get("parent_fact_sha256"),
        )
        if (parent_identity.get("hold_class") != "atomicity-and-absence-inference-hold"
                or parent_identity.get("fact_key") not in parent_by_key
                or parent_by_key[parent_identity["fact_key"]]["qid"] != identity[0]
                or parent_by_key[parent_identity["fact_key"]]["parent_fact_sha256"] != identity[1]
                or row.get("independent_of_runtime_outcome") is not True):
            raise ValueError("child adjudication parent binding is invalid")
        adjudicated_parent_identities.add(identity)
        if row_type == "accepted_child":
            if (set(row) != ACCEPTED_ADJUDICATION_KEYS
                    or row.get("adjudicator_status") != "accepted"
                    or row.get("basis") != "explicit"
                    or row.get("score_track") not in {"content", "supplementary"}
                    or row.get("requiredness") not in {"core", "supplementary"}
                    or (row.get("score_track"), row.get("requiredness"))
                    not in {("content", "core"), ("supplementary", "supplementary")}
                    or not str(row.get("requiredness_rationale") or "").strip()):
                raise ValueError("accepted child adjudication schema is not exact")
            child_id = row.get("child_id")
            supported_id = row.get("supported_subclaim_id")
            if (not isinstance(child_id, str) or child_id in accepted_by_child
                    or not isinstance(supported_id, str) or supported_id in seen_supported_ids
                    or normalized_text_sha256(str(row.get("supported_subclaim") or ""))
                    != row.get("supported_subclaim_sha256")):
                raise ValueError("accepted child/support binding is not unique or hash-valid")
            binding = row.get("citation_binding") or {}
            if set(binding) != CITATION_BINDING_KEYS:
                raise ValueError("citation binding schema is not exact")
            candidate = candidates.get((binding.get("search_fact_key"), binding.get("candidate_id")))
            if (not candidate or candidate.get("source_file") != binding.get("manual_id")
                    or [candidate.get("page_number")] != binding.get("page_numbers")
                    or normalized_text_sha256(str(candidate.get("excerpt") or ""))
                    != binding.get("excerpt_sha256")):
                raise ValueError("citation binding does not match frozen evidence search")
            accepted_by_child[child_id] = row
            seen_supported_ids.add(supported_id)
        elif row_type == "withdrawal":
            if (set(row) != WITHDRAWAL_ADJUDICATION_KEYS
                    or row.get("adjudicator_status") != "withdrawn"):
                raise ValueError("withdrawal adjudication schema is not exact")
            withdrawal_id = row.get("withdrawal_id")
            unsupported = str(row.get("unsupported_subclaim") or "")
            if (not isinstance(withdrawal_id, str) or withdrawal_id in seen_withdrawal_ids
                    or normalized_text_sha256(unsupported)
                    != row.get("unsupported_subclaim_sha256")):
                raise ValueError("withdrawal adjudication is not unique or hash-valid")
            parent_withdrawals = withdrawn_by_parent.setdefault(identity, {})
            if row["unsupported_subclaim_sha256"] in parent_withdrawals:
                raise ValueError("withdrawal subclaim hashes must be unique per parent")
            parent_withdrawals[row["unsupported_subclaim_sha256"]] = row
            seen_withdrawal_ids.add(withdrawal_id)
        else:
            raise ValueError("unknown child adjudication row type")
    by_parent: dict[tuple[str, str], dict] = {}
    all_child_ids: set[str] = set()
    for transform in transformations:
        if set(transform) != TRANSFORM_REQUIRED_KEYS:
            raise ValueError("delta transformation schema is not exact")
        parent_sha = transform.get("parent_fact_sha")
        fact_key = transform.get("fact_key")
        parent = parent_by_key.get(fact_key)
        identity = (transform.get("qid"), parent_sha)
        if (not parent or parent["qid"] != transform.get("qid")
                or parent["parent_fact_sha256"] != parent_sha
                or source_by_identity.get(identity) != parent["source_fact"]):
            raise ValueError(f"delta parent identity mismatch: {fact_key}")
        if identity in by_parent or identity in m0_by_parent:
            raise ValueError(f"delta transformation overlaps another transform: {fact_key}")
        if (not isinstance(transform.get("migration_id"), str)
                or not transform["migration_id"].startswith(f"s118.{parent['qid']}.")
                or transform.get("operation") not in DELTA_OPERATIONS):
            raise ValueError(f"delta transformation identity or operation is invalid: {fact_key}")
        required_class = transform.get("required_adjudicated_class")
        prior_evidence = s114_adjudicated.get(fact_key)
        if required_class != "atomicity-and-absence-inference-hold":
            raise ValueError(f"delta parent lacks exact atomicity hold: {fact_key}")
        if prior_evidence is not None and (
            prior_evidence.get("adjudicated_class") != required_class
            or parent["current_diagnostic_class"] != required_class
        ):
            raise ValueError(f"delta parent conflicts with S114 atomicity hold: {fact_key}")
        after = transform.get("after")
        withdrawals = transform.get("withdrawals")
        if not isinstance(after, list) or not after or not isinstance(withdrawals, list) or not withdrawals:
            raise ValueError(f"delta transform must retain positives and record withdrawals: {fact_key}")
        for child in after:
            if set(child) != AFTER_REQUIRED_KEYS:
                raise ValueError(f"delta child schema is not exact: {fact_key}")
            child_id = child.get("migration_id")
            if (not isinstance(child_id, str) or not child_id.startswith(transform["migration_id"] + ".")
                    or child_id in all_child_ids
                    or child.get("tipo") not in {"core", "supplementary"}
                    or child.get("estado") != "presente"
                    or child.get("basis") != "explicit"
                    or not str(child.get("texto") or "").strip()
                    or not str(child.get("valor") or "").strip()
                    or not str(child.get("cita") or "").strip()
                    or not str(child.get("requiredness_reason") or "").strip()
                    or not isinstance(child.get("source_pages"), list)
                    or not child["source_pages"]
                    or any(isinstance(page, bool) or not isinstance(page, int) or page <= 0
                           for page in child["source_pages"])):
                raise ValueError(f"delta child is not an explicit positive claim: {child_id}")
            accepted = accepted_by_child.get(child_id)
            if (not accepted
                    or accepted["parent_identity"]["fact_key"] != fact_key
                    or normalized_text_sha256(child["texto"]) != accepted.get("texto_sha256")
                    or normalized_text_sha256(child["valor"]) != accepted.get("valor_sha256")
                    or normalized_text_sha256(child["cita"]) != accepted.get("cita_sha256")
                    or child["source_pages"] != accepted["citation_binding"]["page_numbers"]
                    or child["tipo"] != accepted.get("requiredness")):
                raise ValueError(f"delta child lacks exact accepted adjudication: {child_id}")
            all_child_ids.add(child_id)
        expected_withdrawal_hashes: set[str] = set()
        for withdrawal in withdrawals:
            if (set(withdrawal) != {"component", "reason"}
                    or not str(withdrawal.get("component") or "").strip()
                    or not str(withdrawal.get("reason") or "").strip()):
                raise ValueError(f"delta withdrawal schema is incomplete: {fact_key}")
            expected_withdrawal_hashes.add(normalized_text_sha256(withdrawal["component"]))
        actual_withdrawal_hashes = set(withdrawn_by_parent.get(identity, {}))
        if expected_withdrawal_hashes != actual_withdrawal_hashes:
            raise ValueError(f"delta withdrawals lack a bijective adjudication: {fact_key}")
        by_parent[identity] = transform
    if set(accepted_by_child) != all_child_ids:
        raise ValueError("accepted child adjudications are not bijective with delta children")
    if adjudicated_parent_identities != set(by_parent):
        raise ValueError("child adjudication parent set differs from delta transformations")
    return by_parent


def _eligible_child(child: dict) -> bool:
    return bool(
        child.get("tipo") == "core"
        and child.get("estado") == "presente"
        and child.get("basis") == "explicit"
        and child.get("score_track", "content") == "content"
        and child.get("valor") is not None
    )


def _claim_from_child(parent: dict, child: dict, transform_source: str) -> dict:
    return {
        "claim_id": child["migration_id"],
        "qid": parent["qid"],
        "parent_fact_key": parent["fact_key"],
        "parent_fact_sha256": parent["parent_fact_sha256"],
        "transform_source": transform_source,
        "texto": child.get("texto"),
        "valor": child.get("valor"),
        "tipo": child.get("tipo"),
        "estado": child.get("estado"),
        "basis": child.get("basis"),
        "cita": child.get("cita"),
        "source_pages": child.get("source_pages") or [],
        "stage_status": "pending-replay",
        "stage_bucket": "pending-replay",
        "stage_evidence": None,
    }


def build_bridge(
    *, gold_rows: list[dict], assessment: dict, current_ledger: dict,
    s114_adjudication: dict, child_adjudication: dict, evidence_search: dict,
    external_projection: dict, delta_spec: dict, input_receipts: dict,
    upstream_gate: dict,
) -> dict:
    parents, source_by_identity = reconstruct_historical_population(
        gold_rows, assessment, current_ledger,
    )
    gold_sha = input_receipts["gold_v1"]["sha256"]
    m0_all, known_m1_holds = validate_external_contract_projection(
        external_projection, gold_sha256=gold_sha, parents=parents,
        source_by_identity=source_by_identity, delta_spec=delta_spec,
        input_receipts=input_receipts,
    )
    delta = validate_delta_spec(
        delta_spec, parents, source_by_identity, m0_all, s114_adjudication,
        child_adjudication, evidence_search, input_receipts,
    )

    historical_identities = {
        (row["qid"], row["parent_fact_sha256"]) for row in parents
    }
    m0 = {
        identity: transform for identity, transform in m0_all.items()
        if identity in historical_identities
    }
    claims: list[dict] = []
    parent_rows: list[dict] = []
    excluded_rows: list[dict] = []
    transformed_claims = 0
    carry_claims = 0
    known_hold_claims = 0

    for parent in sorted(parents, key=lambda row: row["fact_key"]):
        compact_parent = {key: value for key, value in parent.items() if key != "source_fact"}
        if _is_meta_class(parent):
            excluded_rows.append({
                "fact_key": parent["fact_key"],
                "qid": parent["qid"],
                "parent_fact_sha256": parent["parent_fact_sha256"],
                "reason": "historical_meta_reference",
            })
            parent_rows.append({**compact_parent, "projection": "excluded-meta-reference",
                                "content_claim_ids": []})
            continue

        parent_sha = parent["parent_fact_sha256"]
        identity = (parent["qid"], parent_sha)
        transform = m0.get(identity) or delta.get(identity)
        if transform:
            source = "m0" if identity in m0 else "s118"
            child_claims = [
                _claim_from_child(parent, child, source)
                for child in transform.get("after") or [] if _eligible_child(child)
            ]
            claims.extend(child_claims)
            transformed_claims += len(child_claims)
            parent_rows.append({
                **compact_parent,
                "projection": f"transformed-{source}",
                "transformation_id": transform.get("migration_id"),
                "content_claim_ids": [claim["claim_id"] for claim in child_claims],
                "excluded_child_count": len(transform.get("after") or []) - len(child_claims),
                "withdrawal_count": len(transform.get("withdrawals") or []),
            })
            continue

        source_fact = parent["source_fact"]
        claim_id = f"benchmark_carry.{parent['qid']}.{parent_sha[:24]}"
        legacy_bucket = _stage_bucket(str(parent["current_diagnostic_class"] or ""))
        known_hold = known_m1_holds.get(identity)
        bucket = "known-m1-contract-hold" if known_hold else legacy_bucket
        stage_status = (
            "known-m1-contract-hold-no-stage-credit" if known_hold
            else "provisional-legacy-carry-no-known-m1-blocker"
        )
        claims.append({
            "claim_id": claim_id,
            "qid": parent["qid"],
            "parent_fact_key": parent["fact_key"],
            "parent_fact_sha256": parent_sha,
            "transform_source": "frozen-benchmark-carry",
            "texto": source_fact.get("texto"),
            "valor": source_fact.get("valor"),
            "tipo": source_fact.get("tipo"),
            "estado": source_fact.get("estado"),
            "basis": "benchmark_carry",
            "cita": source_fact.get("cita"),
            "source_pages": [],
            "stage_status": stage_status,
            "stage_bucket": bucket,
            "stage_evidence": parent["current_diagnostic_evidence"],
            "legacy_stage_bucket": legacy_bucket,
            "known_m1_blocker": (
                known_hold["source_decision"] if known_hold else None
            ),
        })
        carry_claims += 1
        known_hold_claims += int(known_hold is not None)
        parent_rows.append({
            **compact_parent,
            "projection": (
                "known-m1-contract-hold" if known_hold
                else "provisional-legacy-carry-no-known-m1-blocker"
            ),
            "content_claim_ids": [claim_id],
        })

    claim_ids = [claim["claim_id"] for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("projected claim identities are not unique")
    stage_hist = Counter(claim["stage_bucket"] for claim in claims)
    summary = {
        "historical_rows": len(parents),
        "historical_scored_parents": sum(not _is_meta_class(row) for row in parents),
        "meta_reference_exclusions": len(excluded_rows),
        "m0_transformed_parents_in_population": len(m0),
        "s118_transformed_parents_in_population": len(delta),
        "unchanged_scored_parents": carry_claims,
        "known_m1_contract_holds": known_hold_claims,
        "legacy_carries_without_known_m1_blocker": carry_claims - known_hold_claims,
        "transformed_content_claims_pending_replay": transformed_claims,
        "provisional_hybrid_content_denominator": len(claims),
        "provisional_hybrid_target_ok_for_95_percent": math.ceil(len(claims) * 0.95),
        "official_atomic_content_denominator": None,
        "official_atomic_target_ok_for_95_percent": None,
        "facts_moved_to_ok": 0,
        "provisional_hybrid_stage_histogram": dict(sorted(stage_hist.items())),
        "official_ok_after_bridge": None,
        "official_ok_status": "blocked_until_atomic_requiredness_contract_is_complete",
    }
    expected = delta_spec.get("expected_bridge") or {}
    for key in (
        "historical_rows", "historical_scored_parents", "meta_reference_exclusions",
        "m0_transformed_parents_in_population", "s118_transformed_parents_in_population",
        "unchanged_scored_parents", "known_m1_contract_holds",
        "legacy_carries_without_known_m1_blocker",
        "transformed_content_claims_pending_replay",
        "provisional_hybrid_content_denominator",
        "provisional_hybrid_target_ok_for_95_percent",
        "official_atomic_content_denominator", "official_atomic_target_ok_for_95_percent",
        "facts_moved_to_ok",
    ):
        if summary[key] != expected.get(key):
            raise ValueError(f"bridge count differs from preregistration: {key}")
    if carry_claims + transformed_claims != len(claims):
        raise ValueError("bridge denominator does not reconcile")
    if (upstream_gate.get("status") != "CANDIDATE_LIVE_ALIGNMENT_GO_UPSTREAM_ONLY"
            or (upstream_gate.get("decision") or {}).get("facts_moved_to_ok") != 0
            or (upstream_gate.get("decision") or {}).get("M3") != "BLOCKED"):
        raise ValueError("M2.10 authority drift would overclaim the bridge")

    output = {
        "instrument": "s118_atomic_benchmark_bridge_v1",
        "schema_version": 2,
        "status": "HYBRID_DIAGNOSTIC_BRIDGE_NO_OFFICIAL_ATOMIC_CREDIT",
        "authority": "diagnostic_measurement_only_no_final_denominator",
        "input_receipts": input_receipts,
        "policy": delta_spec.get("benchmark_policy"),
        "upstream_m210": {
            "status": upstream_gate.get("status"),
            "authority": upstream_gate.get("authority"),
            "facts_moved_to_ok": 0,
            "benchmark_claims_moved": 0,
            "interpretation": "structural upstream evidence only; no cardinality join to claims",
        },
        "summary": summary,
        "parents": parent_rows,
        "claims": sorted(claims, key=lambda claim: claim["claim_id"]),
        "excluded_rows": excluded_rows,
        "authorization": {
            "network": False,
            "database": False,
            "models": False,
            "gold_mutation": False,
            "fact_relabeling": False,
            "retrieval": False,
            "rerank": False,
            "synthesis": False,
            "serving": False,
            "deploy": False,
            "full_replay": False,
        },
        "cost": {"model_calls": 0, "network_calls": 0,
                 "database_reads": 0, "database_writes": 0},
    }
    output["payload_sha256"] = object_sha256(output)
    return output


def _resolve_declared(root: Path, ref: dict) -> Path:
    path = (root / str(ref.get("path") or "")).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"declared input escapes root: {path}") from exc
    return path


def _resolve_inside_root(root: Path, path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes root: {resolved}") from exc
    return resolved


def _assert_safe_output(
    root: Path, output: Path, protected: set[Path], allowed_relative: str,
) -> Path:
    candidate = output if output.is_absolute() else root / output
    candidate_lexical = candidate.absolute()
    allowed_lexical = (root / allowed_relative).absolute()
    if candidate_lexical != allowed_lexical:
        raise ValueError(f"output is not the canonical allowlisted artifact: {allowed_relative}")
    cursor = allowed_lexical
    root_lexical = root.absolute()
    while True:
        if cursor.exists() and (
            cursor.is_symlink()
            or (hasattr(cursor, "is_junction") and cursor.is_junction())
        ):
            raise ValueError("canonical output path cannot traverse a symlink or junction")
        if cursor == root_lexical:
            break
        if cursor.parent == cursor:
            raise ValueError("canonical output ancestry does not reach root")
        cursor = cursor.parent
    output = _resolve_inside_root(root, candidate, "output")
    allowed = _resolve_inside_root(root, root / allowed_relative, "allowed output")
    protected_resolved = {path.resolve() for path in protected}
    if output != allowed:
        raise ValueError(f"output is not the canonical allowlisted artifact: {allowed_relative}")
    if output in protected_resolved:
        raise ValueError("output cannot overwrite a frozen input")
    return output


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists() and (
        temporary.is_symlink()
        or (hasattr(temporary, "is_junction") and temporary.is_junction())
    ):
        raise ValueError("temporary output cannot be a symlink or junction")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def freeze_projection_execute(
    *, root: Path, delta_path: Path, m0_manifest_path: Path,
    m1_blockers_path: Path, projection_output_path: Path,
) -> dict:
    root = root.resolve()
    delta_path = _resolve_inside_root(root, delta_path, "delta")
    m0_manifest_path = m0_manifest_path.resolve()
    m1_blockers_path = m1_blockers_path.resolve()
    spec = load_yaml(delta_path)
    if spec.get("instrument") != "s118_atomic_benchmark_delta_v1":
        raise ValueError("unexpected delta instrument")
    refs = spec.get("frozen_inputs") or {}
    required_population = {
        "gold_v1", "historical_assessment", "current_partial_ledger",
    }
    if not required_population <= set(refs):
        raise ValueError("projection population inputs are incomplete")
    paths = {key: _resolve_declared(root, refs[key]) for key in required_population}
    for key in required_population:
        _assert_exact_hash(paths[key], refs[key].get("sha256"), key)
    external = spec.get("external_sources") or {}
    external_paths = {
        "m0_full_manifest": m0_manifest_path,
        "m1_pending_blockers": m1_blockers_path,
    }
    for key, path in external_paths.items():
        _assert_exact_hash(path, (external.get(key) or {}).get("sha256"), key)
    population_receipts = {
        key: {"logical_path": refs[key]["path"], "sha256": refs[key]["sha256"]}
        for key in sorted(required_population)
    }
    projection = freeze_external_contract_projection(
        gold_rows=load_yaml(paths["gold_v1"]),
        assessment=load_yaml(paths["historical_assessment"]),
        current_ledger=load_json(paths["current_partial_ledger"]),
        m0_manifest=load_json(m0_manifest_path),
        m1_blockers=load_json(m1_blockers_path),
        delta_spec=spec,
        population_receipts=population_receipts,
    )
    output = _assert_safe_output(
        root, projection_output_path,
        {delta_path, *paths.values(), m0_manifest_path, m1_blockers_path},
        "evals/s118_external_contract_projection_v1.json",
    )
    _write_json(output, projection)
    return projection


def execute(
    *, root: Path, delta_path: Path, output_path: Path,
) -> dict:
    root = root.resolve()
    delta_path = _resolve_inside_root(root, delta_path, "delta")
    spec = load_yaml(delta_path)
    if spec.get("instrument") != "s118_atomic_benchmark_delta_v1":
        raise ValueError("unexpected delta instrument")
    refs = spec.get("frozen_inputs") or {}
    required_refs = {
        "gold_v1", "historical_assessment", "current_partial_ledger",
        "atomicity_adjudication", "evidence_search", "child_adjudication",
        "external_contract_projection", "upstream_m210_gate",
    }
    if set(refs) != required_refs:
        raise ValueError("delta frozen input set is not exact")

    paths = {key: _resolve_declared(root, ref) for key, ref in refs.items()}
    for key, ref in refs.items():
        _assert_exact_hash(paths[key], ref.get("sha256"), key)

    input_receipts = {
        key: {"logical_path": ref.get("path") or ref.get("logical_path"),
              "sha256": ref["sha256"]}
        for key, ref in sorted(refs.items())
    }
    input_receipts["delta_spec"] = {
        "logical_path": delta_path.relative_to(root).as_posix(),
        "sha256": file_sha256(delta_path),
    }
    output = build_bridge(
        gold_rows=load_yaml(paths["gold_v1"]),
        assessment=load_yaml(paths["historical_assessment"]),
        current_ledger=load_json(paths["current_partial_ledger"]),
        s114_adjudication=load_yaml(paths["atomicity_adjudication"]),
        child_adjudication=load_yaml(paths["child_adjudication"]),
        evidence_search=load_json(paths["evidence_search"]),
        external_projection=load_json(paths["external_contract_projection"]),
        delta_spec=spec,
        input_receipts=input_receipts,
        upstream_gate=load_yaml(paths["upstream_m210_gate"]),
    )
    output_path = _assert_safe_output(
        root, output_path, {delta_path, *paths.values()},
        "evals/s118_atomic_benchmark_bridge_v1.json",
    )
    _write_json(output_path, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--delta", type=Path,
        default=ROOT / "evals/s118_atomic_benchmark_delta_v1.yaml",
    )
    parser.add_argument("--freeze-external-contracts", action="store_true")
    parser.add_argument("--m0-manifest", type=Path)
    parser.add_argument("--m1-blockers", type=Path)
    parser.add_argument(
        "--projection-output", type=Path,
        default=ROOT / "evals/s118_external_contract_projection_v1.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "evals/s118_atomic_benchmark_bridge_v1.json",
    )
    args = parser.parse_args()
    if args.freeze_external_contracts:
        if args.m0_manifest is None or args.m1_blockers is None:
            parser.error("--freeze-external-contracts requires --m0-manifest and --m1-blockers")
        result = freeze_projection_execute(
            root=args.root, delta_path=args.delta,
            m0_manifest_path=args.m0_manifest,
            m1_blockers_path=args.m1_blockers,
            projection_output_path=args.projection_output,
        )
        print(json.dumps(result["projected_counts"], ensure_ascii=False, sort_keys=True))
    else:
        result = execute(root=args.root, delta_path=args.delta, output_path=args.output)
        print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
