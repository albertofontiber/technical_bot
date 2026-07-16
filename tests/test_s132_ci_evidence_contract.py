from __future__ import annotations

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "evals/s132_ci_evidence_contract_v1.yaml"


def test_historical_replays_are_explicitly_retired_from_active_tests() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    paths = contract["historical_replay_sources"]["paths"]
    assert len(paths) == len(set(paths)) == 13
    assert all(not (ROOT / path).exists() for path in paths)
    assert contract["historical_replay_sources"]["active_ci_contract"] is False


def test_active_tests_do_not_depend_on_nonversioned_s117_snapshots() -> None:
    forbidden = ("tmp/s117_", "tmp\\s117_")
    offenders = []
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"open", "read_bytes", "read_text"}:
                continue
            literals = {
                child.value
                for child in ast.walk(node.func.value)
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            }
            if any(value in literal for value in forbidden for literal in literals):
                offenders.append(path.name)
                break
    assert offenders == []


def test_ci_contract_forbids_missing_artifact_skips() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    active = contract["active_suite"]
    assert active == {
        "missing_artifact_skips_allowed": False,
        "untracked_tmp_dependencies_allowed": False,
        "historical_replays_collected_by_pytest": False,
        "clean_linux_checkout_required": True,
    }
