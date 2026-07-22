"""Build the additive P1 v2 preregistration and release-config schema.

The protected fact/model/cost contract remains v1.  This builder changes only
the release identity and evidence surfaces required by coverage_c1_v2.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREREG_V1 = ROOT / "evals/s277_c1_p1_prereg_v1.yaml"
SCHEMA_V1 = ROOT / "evals/s277_c1_p1_release_config_schema_v1.json"
PREREG_V2 = ROOT / "evals/s277_c1_p1_prereg_v2.yaml"
SCHEMA_V2 = ROOT / "evals/s277_c1_p1_release_config_schema_v2.json"
DOCUMENT_LOCAL_FLAG = "DOCUMENT_LOCAL_COVERAGE"
DOCUMENT_LOCAL_RPC = "document_local_snapshot_v2"
LINEAGE_RELATION = "public.document_revision_lineages"


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _coverage_schema(schema: dict[str, Any], name: str) -> dict[str, Any]:
    return schema["properties"]["derived_config"]["properties"][name][
        "properties"
    ]["coverage"]


def build_schema() -> dict[str, Any]:
    schema = json.loads(SCHEMA_V1.read_text(encoding="utf-8"))
    assert schema["$id"] == "s277_c1_p1_release_config_schema_v1"
    schema["$id"] = "s277_c1_p1_release_config_schema_v2"
    schema["title"] = "Safe, secret-free release identity for S277 C1 P1 v2"
    schema["properties"]["schema_version"]["const"] = (
        "s277_c1_p1_release_config_v2"
    )

    patch = schema["properties"]["railway"]["properties"][
        "planned_bootstrap_patch"
    ]["properties"]["delete"]
    assert patch["minItems"] == patch["maxItems"] == 4
    patch["minItems"] = patch["maxItems"] = 5
    patch["items"]["enum"].append(DOCUMENT_LOCAL_FLAG)

    derived = schema["properties"]["derived_config"]["properties"]
    assert derived["p1_target_profile"]["const"] == "coverage_c1_v1"
    derived["p1_target_profile"]["const"] = "coverage_c1_v2"
    for name, enabled in (
        ("bootstrap_semantic_config", False),
        ("target_semantic_config", True),
    ):
        coverage = _coverage_schema(schema, name)
        coverage["required"].append("document_local_coverage")
        coverage["properties"]["document_local_coverage"] = {"const": enabled}
    _coverage_schema(schema, "target_semantic_config")["properties"][
        "release_profile"
    ]["const"] = "coverage_c1_v2"

    rpc = schema["properties"]["rpc_allowlist"]
    rpc["minItems"] = 3
    rpc["allOf"].append({"contains": {"const": DOCUMENT_LOCAL_RPC}})
    return schema


def build_prereg(schema: dict[str, Any]) -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG_V1.read_text(encoding="utf-8"))
    assert prereg["schema_version"] == "s277_c1_p1_prereg_v1"
    prereg["schema_version"] = "s277_c1_p1_prereg_v2"
    prereg["prereg_id"] = "S277-C1-P1-E2E-27-V2"
    prereg["date"] = "2026-07-22"
    prereg["decision"]["question"] = (
        "Can coverage_c1_v2 proceed to the release sequence without observed "
        "protected loss in the preregistered dev cohort?"
    )

    sealed = prereg["sealed_inputs"]
    sealed["release_config_schema"] = {
        "path": "evals/s277_c1_p1_release_config_schema_v2.json",
        "sha256_lf": _sha256_lf(SCHEMA_V2),
        "schema_object_sha256": _canonical_sha256(schema),
    }
    sealed["release_config"]["required_path"] = (
        "evals/s277_c1_p1_release_config_v2.json"
    )

    stages = prereg["candidate_path"]["required_stages"]
    assert "structural_fetch" in stages and "coverage" in stages
    stages.insert(stages.index("coverage"), "document_local_fetch")

    pipeline = prereg["receipt_pipeline"]
    pipeline["lineage"]["order"].insert(
        pipeline["lineage"]["order"].index("coverage_output"),
        "document_local_fetch",
    )
    pipeline["lineage"]["effective_config_required"] = (
        "coverage_c1_v2_and_must_preserve_true"
    )

    fence = prereg["corpus_fence"]
    fence["postgrest_guard"]["document_local_get_receipt_one_to_one"] = True
    fence["postgrest_guard"]["document_local_post_forbidden"] = True
    relations = fence["base_relations_exact"]
    assert relations[-1] == "public.documents"
    relations.append(LINEAGE_RELATION)
    fence["base_rpc_allowlist_exact"].append(DOCUMENT_LOCAL_RPC)

    semantic = prereg["semantic_runtime_contract"]
    semantic["semantic_projection_exact_sections"]["coverage"].append(
        "document_local_coverage"
    )
    semantic["cross_field_equalities"].append(
        "target_semantic.coverage.document_local_coverage == true"
    )

    release = prereg["release_identity"]
    release["p1_target_profile"] = "coverage_c1_v2"
    release["only_activation_transition"] = (
        "COVERAGE_RELEASE_PROFILE:off->coverage_c1_v2"
    )
    release["legacy_flags_to_delete"].append(DOCUMENT_LOCAL_FLAG)
    invariants = release["target_invariants"]
    assert invariants.pop("only_structural_coverage_lane") is True
    invariants["only_structural_and_document_local_coverage_lanes"] = True
    return prereg


def main() -> int:
    schema = build_schema()
    SCHEMA_V2.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    prereg = build_prereg(schema)
    PREREG_V2.write_text(
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
                "schema": str(SCHEMA_V2.relative_to(ROOT)),
                "schema_sha256_lf": _sha256_lf(SCHEMA_V2),
                "prereg": str(PREREG_V2.relative_to(ROOT)),
                "prereg_sha256_lf": _sha256_lf(PREREG_V2),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
