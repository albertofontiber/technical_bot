from __future__ import annotations

import copy

import pytest

from scripts import s277_build_c1_p1_v3_contract as builder
from scripts import s277_c1_p1 as p1


PREREG_V2_PATH = p1.ROOT / "evals/s277_c1_p1_prereg_v2.yaml"
PREREG_V3_PATH = p1.ROOT / "evals/s277_c1_p1_prereg_v3.yaml"
RELEASE_SCHEMA_V2_PATH = (
    p1.ROOT / "evals/s277_c1_p1_release_config_schema_v2.json"
)


def _prereg_v3() -> dict:
    return p1.load_data_object(PREREG_V3_PATH)


def test_v3_builder_rebuilds_stored_prereg_exactly() -> None:
    stored = _prereg_v3()
    rebuilt = builder.build_prereg()
    prior = p1.load_data_object(PREREG_V2_PATH)

    assert rebuilt == stored
    assert stored["schema_version"] == "s277_c1_p1_prereg_v3"
    assert stored["prereg_id"] == "S277-C1-P1-E2E-27-V3"

    # V3 versions the measurement contract, not the sealed population,
    # provider call plan, or cost boundary inherited from V2.
    for field in ("population", "model_calls", "cost"):
        assert stored[field] == prior[field]


def test_v3_seals_design_and_governed_source_registry() -> None:
    prereg = _prereg_v3()
    sealed = prereg["sealed_inputs"]

    design = sealed["design_contract"]
    design_path = p1.ROOT / design["path"]
    assert design["path"] == "evals/s277_c1_p1_design_v3.md"
    assert design["sha256_lf"] == p1.sha256_file(
        design_path, lf_normalized=True
    )

    registry = sealed["document_local_source_contract_registry"]
    registry_path = p1.ROOT / registry["path"]
    registry_payload = p1.load_data_object(registry_path)
    assert registry == {
        "path": "config/document_local_source_contracts_v1.yaml",
        "sha256_lf": p1.sha256_file(registry_path, lf_normalized=True),
        "payload_sha256": p1.sha256_json(registry_payload),
        "schema": "document_local_source_contracts_v1",
        "max_scopes_per_query": 2,
    }

    p1.verify_prereg_sealed_inputs(prereg)


def test_v3_preserves_release_config_schema_v2_as_independent_component() -> None:
    prereg_v2 = p1.load_data_object(PREREG_V2_PATH)
    prereg_v3 = _prereg_v3()
    sealed_v3 = prereg_v3["sealed_inputs"]
    schema = p1.load_json_object(RELEASE_SCHEMA_V2_PATH)

    assert p1.RELEASE_CONFIG_SCHEMA == "s277_c1_p1_release_config_v2"
    assert schema["$id"] == "s277_c1_p1_release_config_schema_v2"
    assert schema["properties"]["schema_version"] == {
        "const": "s277_c1_p1_release_config_v2"
    }
    assert sealed_v3["release_config_schema"] == prereg_v2["sealed_inputs"][
        "release_config_schema"
    ]
    assert sealed_v3["release_config_schema"] == {
        "path": "evals/s277_c1_p1_release_config_schema_v2.json",
        "sha256_lf": p1.sha256_file(
            RELEASE_SCHEMA_V2_PATH, lf_normalized=True
        ),
        "schema_object_sha256": p1.sha256_json(schema),
    }
    assert sealed_v3["release_config"] == prereg_v2["sealed_inputs"][
        "release_config"
    ]
    assert (
        sealed_v3["release_config"]["required_path"]
        == "evals/s277_c1_p1_release_config_v2.json"
    )


@pytest.mark.parametrize(
    "weakening",
    (
        "governed_not_exclusive",
        "fallback_without_structural_anchor",
        "registry_as_live_authority",
        "two_physical_gets",
        "structural_target_attestation",
        "organic_generalization_claim",
    ),
)
def test_v3_rejects_weakened_document_local_anchor_contract(
    weakening: str,
) -> None:
    prereg = _prereg_v3()
    assert (
        prereg["document_local_anchor_contract"]
        == builder.build_prereg()["document_local_anchor_contract"]
        == p1.DOCUMENT_LOCAL_ANCHOR_CONTRACT_V1
    )
    p1.verify_prereg_document_local_anchor_contract(prereg)

    weakened = copy.deepcopy(prereg)
    contract = weakened["document_local_anchor_contract"]
    if weakening == "governed_not_exclusive":
        contract["governed_route"]["exclusive_when_present"] = False
    elif weakening == "fallback_without_structural_anchor":
        contract["fallback_route"][
            "served_validated_structural_anchor_required"
        ] = False
    elif weakening == "registry_as_live_authority":
        contract["live_authority"]["registry_is_hint_only"] = False
    elif weakening == "two_physical_gets":
        contract["live_authority"]["max_physical_gets"] = 2
    elif weakening == "structural_target_attestation":
        contract["required_target_attestation"]["seed_sources"] = {
            "served_structural_append": 1
        }
    elif weakening == "organic_generalization_claim":
        contract["claim_limit"] = "ORGANIC_GENERALIZATION"
    else:  # pragma: no cover - the parameter set above is exhaustive.
        raise AssertionError(f"unknown mutation: {weakening}")

    with pytest.raises(p1.P1Error) as exc_info:
        p1.verify_prereg_document_local_anchor_contract(weakened)
    assert exc_info.value.code == "HOLD_PREREG_DRIFT"
