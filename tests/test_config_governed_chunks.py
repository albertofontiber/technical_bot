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
