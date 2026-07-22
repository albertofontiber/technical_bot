import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "evals/s277_c1_live_reachability_receipt_v1.json"
EXPECTED_LIVE_STATUS = (
    "PASS_C1_LIVE_NEIGHBOR_FETCH_FROM_FROZEN_PREFIX_READ_ONLY"
)
EXPECTED_RUNTIME_INPUTS = {
    "scripts/s277_c1_live_reachability_probe.py",
    "src/config.py",
    "src/release_profiles.py",
    "src/rag/serving_pipeline.py",
    "src/rag/coverage_runtime.py",
    "src/rag/post_rerank_coverage.py",
    "src/rag/structural_neighbor_shadow.py",
    "src/rag/structural_neighbor_coverage.py",
    "src/rag/evidence_coverage.py",
    "src/rag/evidence_window.py",
    "src/rag/query_facets.py",
    "src/rag/structured_claims.py",
    "src/rag/toc_detection.py",
    "src/rag/mp_lexicon.py",
    "src/rag/catalog.py",
    "config/structural_neighbor_coverage_v1.yaml",
    "config/retrieval_facets_v3.yaml",
    "config/evidence_coverage_facets_v4.yaml",
    "config/evidence_coverage_facets_v2.yaml",
    "config/structured_numeric_claims_v2.yaml",
}


def _sha256_lf(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# Commit that sealed evals/s277_c1_live_reachability_receipt_v1.json (the live
# probe reviewed this exact runtime; the receipt records no commit id itself,
# so the sealing commit is pinned here per DEC-147: version, do not relax).
RECEIPT_SEAL_COMMIT = "f764f5aede413474dadd293749dca51931484d59"


def _sealed_sha256_lf(relative: str) -> str:
    import hashlib

    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{RECEIPT_SEAL_COMMIT}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, f"sealed blob missing: {relative}"
    return hashlib.sha256(
        completed.stdout.replace(b"\r\n", b"\n")
    ).hexdigest()


def test_hp017_c1_gate_crosses_the_production_seam_without_external_calls():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    # Hostile inherited values prove the assembly runner, rather than the
    # developer .env, owns every flag that can alter this deterministic path.
    for name in (
        "TABLE_PREAMBLE_CLOSURE",
        "CANONICAL_HYQ_COVERAGE",
        "COMPATIBILITY_BUNDLE_COVERAGE",
        "RERANK_POOL_COVERAGE",
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
        "EVIDENCE_DERIVATION_OVERLAY",
        "VISUAL_ASSETS_REGISTRY",
        "DEDUP_REFERENCE_NAVIGATION",
        "R2_REPAIR_NAVIGATION",
        "STRUCTURAL_NEIGHBOR_SHADOW",
        "MP_HYBRID_DETECT",
        "MP_SERVED_BINDING",
        "MP_DEFLINE_EQ",
        "MP_STEM_BINDING",
        "MP_DISTINCTIVE_TOKEN",
    ):
        env[name] = "on"
    env.update(
        {
            "POST_RERANK_COVERAGE": "off",
            "STRUCTURAL_NEIGHBOR_COVERAGE": "off",
            "COVERAGE_MANDATORY_CALLOUT": "off",
            "MP_MANDATORY_VERB_TRIGGER": "off",
            "ANSWER_OBLIGATION_PLANNER": "enforced",
            "GENERATOR_PROMPT_VARIANT": "fidelity",
            "GENERATOR_SELECTION_BLOCK": "on",
            "GENERATOR_INCLUDE_CONTEXT": "1",
            "IDENTITY_RESOLVE": "on",
            "IDENTITY_FETCH": "llm",
            "PYTHON_DOTENV_DISABLED": "0",
        }
    )
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/s277_c1_release_gate.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    result = json.loads(completed.stdout)
    assert result["gate"] == "PASS_C1_ASSEMBLY_OFFLINE"
    assert result["profile"] == "coverage_c1_v1"
    assert result["served_rows"] > result["prefix_rows"] == 10
    assert result["mandatory_callout_cards"] >= 1
    assert result["atoms_appended"] >= 2
    assert result["candidate_scope_rows"] == 2
    assert result["forced_target_citation"] is True
    assert result["uncited_negative_control_passed"] is True
    environment = result["assembly_environment"]
    assert environment["profile_owned_legacy_flags_present"] == []
    assert set(environment["off_flags"].values()) == {"off"}
    assert environment["fixed_values"]["COVERAGE_RELEASE_PROFILE"] == (
        "coverage_c1_v1"
    )
    assert environment["fixed_values"]["GENERATOR_PROMPT_VARIANT"] == "base"
    assert environment["fixed_values"]["IDENTITY_RESOLVE"] == "off"
    assert environment["fixed_values"]["PYTHON_DOTENV_DISABLED"] == "1"
    assert result["proves_live_reachability"] is False
    assert result["proves_model_synthesis"] is False
    assert result["fake_model_transports"] == 2
    assert result["external_http_requests"] == 0
    assert result["database_writes"] == 0
    assert result["paid_model_calls"] == 0


def test_live_probe_manifest_has_exact_effective_runtime_inputs():
    from scripts.s277_c1_live_reachability_probe import (
        EFFECTIVE_RUNTIME_INPUTS,
        MANIFEST_SCHEMA,
        build_implementation_manifest,
    )

    assert MANIFEST_SCHEMA == "s277_c1_live_neighbor_fetch_runtime_manifest_v1"
    assert set(EFFECTIVE_RUNTIME_INPUTS) == EXPECTED_RUNTIME_INPUTS
    manifest = build_implementation_manifest()
    assert set(manifest) == EXPECTED_RUNTIME_INPUTS
    assert manifest == {
        relative: _sha256_lf(ROOT / relative)
        for relative in sorted(EXPECTED_RUNTIME_INPUTS)
    }


def test_live_read_only_receipt_is_pinned_to_the_reviewed_runtime():
    """The receipt stays pinned to the runtime blobs sealed at
    RECEIPT_SEAL_COMMIT: the branch legitimately evolved several of those
    files afterwards, so asserting against the working tree would report
    development as tampering (DEC-147 mandate: version, do not relax)."""
    from scripts.s277_c1_live_reachability_probe import (
        FREEZE_SHA256,
        MANIFEST_SCHEMA,
    )

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["status"] == EXPECTED_LIVE_STATUS
    assert receipt["scope"] == {
        "production_database_writes": 0,
        "railway_changed": False,
        "paid_model_calls": 0,
        "uses_frozen_retrieval_prefix": True,
        "proves_live_retrieval": False,
        "proves_live_rerank": False,
        "proves_model_synthesis": False,
    }
    authority = receipt["authority"]
    assert authority["schema"] == MANIFEST_SCHEMA
    manifest = authority["implementation_sha256_lf"]
    assert set(manifest) == EXPECTED_RUNTIME_INPUTS
    assert manifest == {
        relative: _sealed_sha256_lf(relative) for relative in manifest
    }
    import hashlib

    assert authority["source_freeze_sha256"] == FREEZE_SHA256
    freeze_bytes = (ROOT / "evals/s113_full_contexts_freeze_v1.json").read_bytes()
    assert FREEZE_SHA256 == hashlib.sha256(
        freeze_bytes.replace(b"\r\n", b"\n")
    ).hexdigest()
    assert authority["selector_config_sha256"] == _sealed_sha256_lf(
        "config/structural_neighbor_coverage_v1.yaml"
    )
    assert len(authority["fetched_candidate_snapshot_sha256"]) == 64
    assert receipt["receipt"]["fetched_candidate_rows"] == 110
    assert receipt["receipt"]["target_callout_receipted"] is True
