import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_config_rejects_legacy_chunks_runtime():
    env = os.environ.copy()
    env["CHUNKS_TABLE"] = "chunks"
    result = subprocess.run(
        [sys.executable, "-c", "import src.config"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode != 0
    assert "production retrieval requires CHUNKS_TABLE=chunks_v2" in result.stderr


def test_config_accepts_governed_chunks_runtime():
    env = os.environ.copy()
    env["CHUNKS_TABLE"] = "chunks_v2"
    result = subprocess.run(
        [sys.executable, "-c",
         "import src.config as c; assert c.RPC_SUFFIX == '_v2'"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_voice_transcription_model_is_measured_default_and_strictly_governed():
    env = os.environ.copy()
    env["CHUNKS_TABLE"] = "chunks_v2"
    env.pop("VOICE_TRANSCRIPTION_MODEL", None)
    default = subprocess.run(
        [
            sys.executable,
            "-c",
            "import src.config as c; assert c.VOICE_TRANSCRIPTION_MODEL == 'whisper-1'",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert default.returncode == 0, default.stderr

    env["VOICE_TRANSCRIPTION_MODEL"] = "gpt-4o-mini-transcribe-2025-12-15"
    candidate = subprocess.run(
        [sys.executable, "-c", "import src.config"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert candidate.returncode == 0, candidate.stderr

    env["VOICE_TRANSCRIPTION_MODEL"] = "latest-magic-asr"
    invalid = subprocess.run(
        [sys.executable, "-c", "import src.config"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert invalid.returncode != 0
    assert "VOICE_TRANSCRIPTION_MODEL must be one of" in invalid.stderr


def test_structural_neighbor_shadow_requires_key_and_version_when_enabled():
    env = os.environ.copy()
    env["CHUNKS_TABLE"] = "chunks_v2"
    env["STRUCTURAL_NEIGHBOR_SHADOW"] = "on"
    env["STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY"] = "s" * 32
    env.pop("STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION", None)
    missing = subprocess.run(
        [sys.executable, "-c", "import src.config"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert missing.returncode != 0
    assert "HMAC_KEY_VERSION=v1" in missing.stderr

    env["STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION"] = "v1"
    accepted = subprocess.run(
        [sys.executable, "-c", "import src.config"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stderr


def test_post_rerank_release_flags_are_strict_and_default_off():
    env = os.environ.copy()
    env["CHUNKS_TABLE"] = "chunks_v2"
    env.pop("COVERAGE_RELEASE_PROFILE", None)
    for name in (
        "POST_RERANK_COVERAGE",
        "STRUCTURAL_NEIGHBOR_COVERAGE",
        "TABLE_PREAMBLE_CLOSURE",
        "EVIDENCE_DERIVATION_OVERLAY",
        "CANONICAL_HYQ_COVERAGE",
        "COMPATIBILITY_BUNDLE_COVERAGE",
        "RERANK_POOL_COVERAGE",
        "DOCUMENT_LOCAL_COVERAGE",
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
    ):
        env.pop(name, None)
    default = subprocess.run(
        [
            sys.executable,
            "-c",
            "import src.config as c; "
            "assert not c.POST_RERANK_COVERAGE; "
            "assert not c.STRUCTURAL_NEIGHBOR_COVERAGE; "
            "assert not c.TABLE_PREAMBLE_CLOSURE; "
            "assert not c.EVIDENCE_DERIVATION_OVERLAY; "
            "assert not c.CANONICAL_HYQ_COVERAGE; "
            "assert not c.COMPATIBILITY_BUNDLE_COVERAGE; "
            "assert not c.RERANK_POOL_COVERAGE; "
            "assert not c.DOCUMENT_LOCAL_COVERAGE; "
            "assert not c.STRUCTURAL_CASCADE_COVERAGE; "
            "assert not c.LOGICAL_RECORD_COVERAGE",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert default.returncode == 0, default.stderr

    env["DOCUMENT_LOCAL_COVERAGE"] = "enabled"
    invalid = subprocess.run(
        [sys.executable, "-c", "import src.config"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert invalid.returncode != 0
    assert "on|off" in invalid.stderr


def test_c1_profiles_import_as_atomic_units_and_visual_registry_is_orthogonal():
    base_env = os.environ.copy()
    base_env.update(
        {
            "CHUNKS_TABLE": "chunks_v2",
            "ANTHROPIC_API_KEY": "test-anthropic",
            "OPENAI_API_KEY": "test-openai",
            "SUPABASE_URL": "https://example.invalid",
            "SUPABASE_SERVICE_KEY": "test-service-role",
            "MUST_PRESERVE_CONTRACT": "on",
            "VISUAL_ASSETS_REGISTRY": "on",
            "TABLE_PREAMBLE_CLOSURE": "off",
            "CANONICAL_HYQ_COVERAGE": "off",
            "COMPATIBILITY_BUNDLE_COVERAGE": "off",
            "RERANK_POOL_COVERAGE": "off",
            "STRUCTURAL_CASCADE_COVERAGE": "off",
            "LOGICAL_RECORD_COVERAGE": "off",
        }
    )
    for leaf in (
        "POST_RERANK_COVERAGE",
        "STRUCTURAL_NEIGHBOR_COVERAGE",
        "COVERAGE_MANDATORY_CALLOUT",
        "MP_MANDATORY_VERB_TRIGGER",
        "DOCUMENT_LOCAL_COVERAGE",
    ):
        base_env.pop(leaf, None)

    expectations = (
        ("coverage_c1_v1", "False"),
        ("coverage_c1_v2", "True"),
    )
    for profile, document_local in expectations:
        env = base_env | {"COVERAGE_RELEASE_PROFILE": profile}
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import src.config as c; "
                "c.validate_config(production=True); "
                "assert c.POST_RERANK_COVERAGE; "
                "assert c.STRUCTURAL_NEIGHBOR_COVERAGE; "
                "assert c.COVERAGE_RELEASE_POLICY.coverage_mandatory_callout; "
                "assert c.COVERAGE_RELEASE_POLICY.mp_mandatory_verb_trigger; "
                f"assert c.DOCUMENT_LOCAL_COVERAGE is {document_local}; "
                "assert c.VISUAL_ASSETS_REGISTRY",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 0, result.stderr
