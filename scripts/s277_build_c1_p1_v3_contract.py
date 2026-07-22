"""Build the additive P1 v3 preregistration.

The productive release profile and its v2 config schema do not change.  This
builder versions only the measurement contract needed to admit and attest the
governed document-source activation route discovered after the v2 attempts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREREG_V2 = ROOT / "evals/s277_c1_p1_prereg_v2.yaml"
PREREG_V3 = ROOT / "evals/s277_c1_p1_prereg_v3.yaml"
DESIGN_V3 = ROOT / "evals/s277_c1_p1_design_v3.md"
SOURCE_CONTRACT_REGISTRY = (
    ROOT / "config/document_local_source_contracts_v1.yaml"
)


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_prereg() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG_V2.read_text(encoding="utf-8"))
    assert prereg["schema_version"] == "s277_c1_p1_prereg_v2"
    prereg["schema_version"] = "s277_c1_p1_prereg_v3"
    prereg["prereg_id"] = "S277-C1-P1-E2E-27-V3"
    prereg["decision"]["question"] = (
        "Can coverage_c1_v2 with governed document-source activation proceed "
        "to the release sequence without observed protected loss in the "
        "preregistered dev cohort?"
    )

    registry = yaml.safe_load(SOURCE_CONTRACT_REGISTRY.read_text(encoding="utf-8"))
    assert registry["schema"] == "document_local_source_contracts_v1"
    assert registry["max_scopes_per_query"] == 2
    sealed = prereg["sealed_inputs"]
    sealed["design_contract"] = {
        "path": "evals/s277_c1_p1_design_v3.md",
        "sha256_lf": _sha256_lf(DESIGN_V3),
    }
    sealed["document_local_source_contract_registry"] = {
        "path": "config/document_local_source_contracts_v1.yaml",
        "sha256_lf": _sha256_lf(SOURCE_CONTRACT_REGISTRY),
        "payload_sha256": _canonical_sha256(registry),
        "schema": "document_local_source_contracts_v1",
        "max_scopes_per_query": 2,
    }

    prereg["document_local_anchor_contract"] = {
        "schema_version": "s277_document_local_anchor_contract_v1",
        "query_resolution": "catalog_resolver.resolve_query.resolved_documents",
        "registry_eligibility": "catalog_doc_map_primary_doc_exact_join",
        "allowed_seed_sources": [
            "governed_source_contract",
            "protected_rerank_prefix",
            "served_structural_append",
        ],
        "governed_route": {
            "may_activate_without_served_structural_anchor": True,
            "exclusive_when_present": True,
            "scope_count_min": 1,
            "scope_count_max": 2,
            "malformed_duplicate_or_orphan": "FAIL_CLOSED_BEFORE_IO",
            "per_product_registry_overflow": "FAIL_CLOSED_BEFORE_IO",
            "query_resolution_overflow": "FAIL_CLOSED_BEFORE_IO",
        },
        "fallback_route": {
            "served_validated_structural_anchor_required": True,
            "protected_prefix_cannot_activate_alone": True,
        },
        "live_authority": {
            "rpc": "document_local_snapshot_v2",
            "registry_is_hint_only": True,
            "verified_lineage_active_revision_exact_blob_required": True,
            "max_physical_gets": 1,
            "model_calls": 0,
            "database_writes": 0,
        },
        "private_receipt_fields": [
            "seed_sources",
            "seed_scope_count",
            "seed_scopes_sha256",
            "seed_scopes_truncated",
        ],
        "runtime_telemetry_fields": [
            "seed_route",
            "seed_scopes",
            "seed_scopes_truncated",
            "satisfaction_route",
        ],
        "required_target_attestation": {
            "replicas": ["hp011:r1", "hp011:r2"],
            "seed_sources": {"governed_source_contract": 1},
            "seed_scope_count": 1,
            "seed_scopes_truncated": False,
            "physical_gets": 1,
            "authoritative_satisfied_chunks": 1,
        },
        "claim_limit": "BOUNDED_RP1R_PILOT_NOT_ORGANIC_GENERALIZATION",
    }
    return prereg


def main() -> int:
    prereg = build_prereg()
    PREREG_V3.write_text(
        yaml.safe_dump(
            prereg,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "prereg": str(PREREG_V3.relative_to(ROOT)),
                "prereg_sha256_lf": _sha256_lf(PREREG_V3),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
