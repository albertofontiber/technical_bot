from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals/s277_c1_p1_prereg_v2.yaml"
SCHEMA = ROOT / "evals/s277_c1_p1_release_config_schema_v2.json"


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def test_v2_prereg_preserves_fact_cost_and_replica_contract() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    assert prereg["schema_version"] == "s277_c1_p1_prereg_v2"
    assert prereg["decision"]["official_atomic_kpi"] == "146/154"
    assert prereg["decision"]["p1_can_change_kpi"] is False
    assert len(prereg["population"]["qids"]) == 13
    assert len(prereg["population"]["replica_order"]) == 27
    assert prereg["model_calls"]["expected"] == {
        "voyage_embedding": 27,
        "sonnet_rerank": 27,
        "sonnet_synthesis": 27,
        "total": 81,
    }
    assert prereg["cost"]["static_worst_case_usd"] == "29.727"
    assert prereg["cost"]["list_price_cap"] == 30.0
    assert prereg["sealed_inputs"]["fact_contract"]["path"].endswith(
        "fact_contract_v1.json"
    )


def test_v2_release_identity_and_document_local_surfaces_are_exact() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    release = prereg["release_identity"]
    assert release["bootstrap_profile"] == "off"
    assert release["p1_target_profile"] == "coverage_c1_v2"
    assert release["legacy_flags_to_delete"][-1] == "DOCUMENT_LOCAL_COVERAGE"
    assert release["target_invariants"][
        "only_structural_and_document_local_coverage_lanes"
    ] is True
    assert "public.document_revision_lineages" in prereg["corpus_fence"][
        "base_relations_exact"
    ]
    assert "document_local_snapshot_v2" in prereg["corpus_fence"][
        "base_rpc_allowlist_exact"
    ]
    assert prereg["corpus_fence"]["postgrest_guard"][
        "document_local_get_receipt_one_to_one"
    ] is True


def test_v2_release_schema_hashes_are_self_consistent() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    sealed = prereg["sealed_inputs"]["release_config_schema"]
    assert schema["$id"] == "s277_c1_p1_release_config_schema_v2"
    assert schema["properties"]["schema_version"]["const"] == (
        "s277_c1_p1_release_config_v2"
    )
    assert sealed["path"] == "evals/s277_c1_p1_release_config_schema_v2.json"
    assert sealed["sha256_lf"] == _sha256_lf(SCHEMA)
    assert sealed["schema_object_sha256"] == _canonical_sha256(schema)
    coverage = schema["properties"]["derived_config"]["properties"]
    assert coverage["bootstrap_semantic_config"]["properties"]["coverage"][
        "properties"
    ]["document_local_coverage"]["const"] is False
    assert coverage["target_semantic_config"]["properties"]["coverage"][
        "properties"
    ]["document_local_coverage"]["const"] is True
    assert {"contains": {"const": "document_local_snapshot_v2"}} in schema[
        "properties"
    ]["rpc_allowlist"]["allOf"]
