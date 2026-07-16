from __future__ import annotations

import ast
import copy
import json
import socket
import subprocess
from pathlib import Path

import pytest

from scripts import s117_m29_reconciled_loss_ledger as runner


ROOT = Path(__file__).resolve().parents[1]
REAL_PATHS = {
    role: ROOT / path
    for role, path in runner.SELECTED_PATHS.items()
    if role in runner.PARSED_ROLES
}


@pytest.fixture(scope="module")
def real_inputs() -> dict[str, dict]:
    return {
        role: runner.strict_json_bytes(path.read_bytes())
        for role, path in REAL_PATHS.items()
    }


def _dependencies(char: str = "a") -> dict[str, str]:
    return {role: char * 64 for role in runner.DEPENDENCY_ROLES}


def _build(inputs: dict[str, dict], seed: int = 1) -> dict:
    return runner.build_payload(
        inputs["m27c_seed1"],
        inputs["m27c_seed2"],
        inputs["compact100"],
        inputs["m28_seed1"],
        inputs["m28_seed2"],
        _dependencies(),
        seed,
    )


def _reseal_compact(compact: dict) -> None:
    logical = dict(compact)
    logical.pop("logical_payload_sha256", None)
    compact["logical_payload_sha256"] = runner.sha256_bytes(
        runner.canonical_json_bytes(logical)
    )


def _resign_output(payload: dict) -> None:
    receipt_by_document = {}
    for document in payload["documents"]:
        base = dict(document)
        base.pop("m29_document_receipt_sha256", None)
        receipt = runner.sha256_bytes(runner.canonical_json_bytes(base))
        document["m29_document_receipt_sha256"] = receipt
        receipt_by_document[document["extraction_sha256"]] = receipt
    for resolution in payload["resolved_baseline_missing_identities"]:
        resolution["m29_document_receipt_sha256"] = receipt_by_document[
            resolution["extraction_sha256"]
        ]
        base = dict(resolution)
        base.pop("m29_resolution_receipt_sha256", None)
        resolution["m29_resolution_receipt_sha256"] = runner.sha256_bytes(
            runner.canonical_json_bytes(base)
        )
    baseline_missing = sorted(
        (
            {"extraction_sha256": row["extraction_sha256"], "source_block_index": index}
            for row in payload["documents"]
            for index in row["baseline_missing_block_indexes"]
        ),
        key=lambda row: (row["extraction_sha256"], row["source_block_index"]),
    )
    candidate_missing = sorted(
        (
            {"extraction_sha256": row["extraction_sha256"], "source_block_index": index}
            for row in payload["documents"]
            for index in row["candidate_missing_block_indexes"]
        ),
        key=lambda row: (row["extraction_sha256"], row["source_block_index"]),
    )
    payload["manifests"] = runner._manifest_payload(
        payload["documents"],
        payload["resolved_baseline_missing_identities"],
        baseline_missing,
        candidate_missing,
    )


def _prereg(frozen_inputs: dict[str, dict]) -> dict:
    return {
        "instrument": "s117_m29_reconciled_loss_ledger_prereg_v1",
        "schema_version": 1,
        "status": "frozen_before_execution",
        "scope": {
            "purpose": "derive_reconciled_loss_ledger_from_frozen_evidence",
            "authority": "reconciled_frozen_evidence_raw_parsed_block_surface_only",
            "allowed": ["local_frozen_evidence_read", "local_eval_write"],
            "forbidden": ["raw_store_read", "chunk_execution", "network", "models"],
        },
        "frozen_inputs": frozen_inputs,
        "expected": {
            "projection": {
                "bytes": runner.EXPECTED_PROJECTION_BYTES,
                "sha256": runner.EXPECTED_PROJECTION_SHA256,
            },
            "population": runner.EXPECTED_POPULATION,
            "check_keys": list(runner.CHECK_KEYS),
            "failure_codes": list(runner.FAILURE_CODES),
            "dependency_roles": list(runner.DEPENDENCY_ROLES),
        },
        "execution": {
            "seeds": [1, 2],
            "outputs": {
                "1": runner.OUTPUT_RELATIVES[1],
                "2": runner.OUTPUT_RELATIVES[2],
            },
            "perturbation": "shuffle_documents_and_resolutions_then_restore_canonical_order",
            "required": ["focused_tests_green", "adversarial_go", "permit_valid"],
        },
        "authorization": {
            "preregistration_frozen": True,
            "ledger_execution": False,
            "raw_store_read": False,
            "chunk_execution": False,
            "database": False,
            "network": False,
            "models": False,
            "load": False,
            "serving": False,
            "deploy": False,
            "facts_moved_to_ok": 0,
            "M3": "BLOCKED",
        },
    }


def _permit(prereg_raw: bytes, prereg: dict) -> dict:
    return {
        "instrument": "s117_m29_reconciled_loss_ledger_execution_permit_v1",
        "schema_version": 1,
        "status": "authorized_two_seeded_local_ledger_executions",
        "bindings": {
            "preregistration_sha256": runner.sha256_bytes(prereg_raw),
            "design_v2_sha256": prereg["frozen_inputs"]["design_v2"]["sha256"],
            "runner_sha256": prereg["frozen_inputs"]["runner"]["sha256"],
            "runner_tests_sha256": prereg["frozen_inputs"]["runner_tests"]["sha256"],
        },
        "allowed_seeds": [1, 2],
        "additional_candidate_execution": False,
        "authorization": {
            "ledger_execution": True,
            "raw_store_read": False,
            "chunk_execution": False,
            "database": False,
            "network": False,
            "models": False,
            "load": False,
            "serving": False,
            "deploy": False,
            "facts_moved_to_ok": 0,
            "M3": "BLOCKED",
        },
    }


def _contract_tree(tmp_path: Path) -> tuple[dict, dict]:
    frozen: dict[str, dict] = {}
    for role, relative in runner.SELECTED_PATHS.items():
        path = tmp_path.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (role + "\n").encode()
        path.write_bytes(raw)
        frozen[role] = {
            "path": relative,
            "sha256": runner.sha256_bytes(raw),
            "format": "JSON" if role in runner.PARSED_ROLES else "blob",
            "use": "parsed" if role in runner.PARSED_ROLES else "hash-only",
        }
    prereg = _prereg(frozen)
    prereg_raw = runner.canonical_json_bytes(prereg) + b"\n"
    prereg_path = tmp_path.joinpath(*runner.PREREG_RELATIVE.split("/"))
    prereg_path.parent.mkdir(parents=True, exist_ok=True)
    prereg_path.write_bytes(prereg_raw)
    permit = _permit(prereg_raw, prereg)
    permit_path = tmp_path.joinpath(*runner.PERMIT_RELATIVE.split("/"))
    permit_path.write_bytes(runner.canonical_json_bytes(permit) + b"\n")
    return prereg, permit


def test_real_frozen_evidence_builds_closed_go(real_inputs: dict[str, dict]) -> None:
    payload = _build(real_inputs)
    assert payload["status"] == "RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY"
    assert payload["population"] == runner.EXPECTED_POPULATION
    assert len(payload["documents"]) == 1068
    assert len(payload["resolved_baseline_missing_identities"]) == 100
    assert payload["authorization"]["facts_moved_to_ok"] == 0
    assert payload["authorization"]["M27A"] is False
    assert payload["loadable"] is False
    runner.validate_output(payload)


def test_seed_perturbation_restores_byte_identical_output(real_inputs: dict[str, dict]) -> None:
    seed1 = _build(real_inputs, 1)
    seed2 = _build(real_inputs, 2)
    assert runner.canonical_json_bytes(seed1) == runner.canonical_json_bytes(seed2)


@pytest.mark.parametrize(
    "raw",
    [
        b"\xef\xbb\xbf{}",
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b'{"a":-Infinity}',
        b'{"a":1e999}',
    ],
)
def test_strict_json_rejects_ambiguous_or_nonfinite_values(raw: bytes) -> None:
    with pytest.raises(runner.LedgerFailure, match="contract_integrity_failure"):
        runner.strict_json_bytes(raw)


def test_m27_document_equations_reject_covered_drift(real_inputs: dict[str, dict]) -> None:
    mutated = copy.deepcopy(real_inputs)
    mutated["m27c_seed1"]["documents"][0]["baseline_covered_blocks"] += 1
    with pytest.raises(runner.LedgerFailure, match="document_partition_failure"):
        _build(mutated)


def test_projection_drift_is_not_accepted_as_candidate_bridge(real_inputs: dict[str, dict]) -> None:
    mutated = copy.deepcopy(real_inputs)
    mutated["m27c_seed1"]["documents"][0]["treatment_surface_sha256"] = "f" * 64
    with pytest.raises(runner.LedgerFailure, match="candidate_projection_bridge_failure"):
        _build(mutated)


def test_candidate_seed_drift_is_detected(real_inputs: dict[str, dict]) -> None:
    mutated = copy.deepcopy(real_inputs)
    mutated["m28_seed2"]["dependencies"]["runner_sha256"] = "f" * 64
    with pytest.raises(runner.LedgerFailure, match="candidate_seed_drift"):
        _build(mutated)


def test_candidate_check_false_is_rejected(real_inputs: dict[str, dict]) -> None:
    mutated = copy.deepcopy(real_inputs)
    mutated["m28_seed1"]["checks"]["treatment_projection_exact"] = False
    with pytest.raises(runner.LedgerFailure, match="candidate_seed_drift"):
        _build(mutated)


def test_compact_text_hash_and_rule_are_verified(real_inputs: dict[str, dict]) -> None:
    for field, value in (("text_sha256", "f" * 64), ("rule_id", "invented_rule")):
        mutated = copy.deepcopy(real_inputs)
        mutated["compact100"]["rows"][0][field] = value
        _reseal_compact(mutated["compact100"])
        with pytest.raises(runner.LedgerFailure, match="compact_integrity_failure"):
            _build(mutated)


def test_compact_identity_move_preserving_count_is_rejected(real_inputs: dict[str, dict], monkeypatch: pytest.MonkeyPatch) -> None:
    mutated = copy.deepcopy(real_inputs)
    row = mutated["compact100"]["rows"][0]
    row["source_block_index"] += 100000
    _reseal_compact(mutated["compact100"])
    monkeypatch.setattr(
        runner,
        "EXPECTED_COMPACT_LOGICAL_SHA256",
        mutated["compact100"]["logical_payload_sha256"],
    )
    with pytest.raises(runner.LedgerFailure, match="baseline_missing_identity_drift"):
        _build(mutated)


def test_compact_duplicate_identity_is_rejected(real_inputs: dict[str, dict]) -> None:
    mutated = copy.deepcopy(real_inputs)
    first = mutated["compact100"]["rows"][0]
    second = mutated["compact100"]["rows"][1]
    for key in ("extraction_sha256", "source_block_index"):
        second[key] = first[key]
    _reseal_compact(mutated["compact100"])
    with pytest.raises(runner.LedgerFailure, match="compact_integrity_failure"):
        _build(mutated)


def test_receipt_manifest_and_extra_key_drift_fail_closed(real_inputs: dict[str, dict]) -> None:
    payload = _build(real_inputs)
    cases = []
    receipt = copy.deepcopy(payload)
    receipt["documents"][0]["m29_document_receipt_sha256"] = "f" * 64
    cases.append(receipt)
    manifest = copy.deepcopy(payload)
    manifest["manifests"]["documents_sha256"] = "f" * 64
    cases.append(manifest)
    extra = copy.deepcopy(payload)
    extra["unexpected"] = True
    cases.append(extra)
    for case in cases:
        with pytest.raises(runner.LedgerFailure):
            runner.validate_output(case)


@pytest.mark.parametrize("manifest_key", runner.MANIFEST_KEYS)
def test_each_manifest_is_verified(real_inputs: dict[str, dict], manifest_key: str) -> None:
    payload = _build(real_inputs)
    payload["manifests"][manifest_key] = "f" * 64
    with pytest.raises(runner.LedgerFailure):
        runner.validate_output(payload)


def test_resolution_receipt_and_missing_key_are_rejected(real_inputs: dict[str, dict]) -> None:
    receipt = _build(real_inputs)
    receipt["resolved_baseline_missing_identities"][0]["m29_resolution_receipt_sha256"] = "f" * 64
    with pytest.raises(runner.LedgerFailure, match="output_schema_failure"):
        runner.validate_output(receipt)
    missing = _build(real_inputs)
    missing.pop("cost")
    with pytest.raises(runner.LedgerFailure, match="output_schema_failure"):
        runner.validate_output(missing)


def test_go_impossible_with_false_check_failure_or_cost(real_inputs: dict[str, dict]) -> None:
    payload = _build(real_inputs)
    cases = []
    false_check = copy.deepcopy(payload)
    false_check["checks"][runner.CHECK_KEYS[0]] = False
    cases.append(false_check)
    failure = copy.deepcopy(payload)
    failure["failures"] = ["internal_failure"]
    cases.append(failure)
    cost = copy.deepcopy(payload)
    cost["cost"]["model_calls"] = 1
    cases.append(cost)
    permit = copy.deepcopy(payload)
    permit["authorization"]["execution_permit_valid"] = False
    cases.append(permit)
    non_boolean = copy.deepcopy(payload)
    non_boolean["authorization"]["execution_permit_valid"] = 1
    cases.append(non_boolean)
    for case in cases:
        with pytest.raises(runner.LedgerFailure, match="output_schema_failure"):
            runner.validate_output(case)


def test_resigned_hidden_candidate_missing_is_rejected(real_inputs: dict[str, dict]) -> None:
    payload = _build(real_inputs)
    document = next(row for row in payload["documents"] if row["baseline_missing_block_indexes"])
    hidden = document["baseline_missing_block_indexes"][0]
    document["candidate_missing_block_indexes"] = [hidden]
    document["candidate_covered_blocks"] -= 1
    document["coverage_gain_block_indexes"] = [
        index for index in document["coverage_gain_block_indexes"] if index != hidden
    ]
    _resign_output(payload)
    with pytest.raises(runner.LedgerFailure, match="output_schema_failure"):
        runner.validate_output(payload)


def test_resigned_hidden_regression_is_rejected(real_inputs: dict[str, dict]) -> None:
    payload = _build(real_inputs)
    document = next(
        row for row in payload["documents"]
        if row["raw_blocks"] and 0 not in row["baseline_missing_block_indexes"]
    )
    document["candidate_missing_block_indexes"] = [0]
    document["candidate_covered_blocks"] -= 1
    document["coverage_regression_block_indexes"] = [0]
    _resign_output(payload)
    with pytest.raises(runner.LedgerFailure, match="output_schema_failure"):
        runner.validate_output(payload)


def test_resigned_identity_delete_add_move_is_rejected_by_frozen_anchor(real_inputs: dict[str, dict]) -> None:
    payload = _build(real_inputs)
    resolution = payload["resolved_baseline_missing_identities"][0]
    document = next(
        row for row in payload["documents"]
        if row["extraction_sha256"] == resolution["extraction_sha256"]
    )
    old_index = resolution["source_block_index"]
    unavailable = set(document["baseline_missing_block_indexes"]) | set(
        document["candidate_missing_block_indexes"]
    )
    new_index = next(index for index in range(document["raw_blocks"]) if index not in unavailable)
    document["baseline_missing_block_indexes"] = sorted(
        new_index if index == old_index else index
        for index in document["baseline_missing_block_indexes"]
    )
    document["coverage_gain_block_indexes"] = sorted(
        new_index if index == old_index else index
        for index in document["coverage_gain_block_indexes"]
    )
    resolution["source_block_index"] = new_index
    payload["resolved_baseline_missing_identities"].sort(
        key=lambda row: (row["extraction_sha256"], row["source_block_index"])
    )
    _resign_output(payload)
    with pytest.raises(runner.LedgerFailure, match="output_schema_failure"):
        runner.validate_output(payload)


def test_no_go_is_closed_conservative_and_leak_free() -> None:
    canaries = (
        "SECRET_VALUE_123",
        "C:\\sensitive\\manual.pdf",
        "ENV_API_KEY",
        "table content from manual",
        "Traceback",
    )
    payload = runner._failure_payload("internal_failure", True, False)
    runner.validate_output(payload)
    encoded = runner.canonical_json_bytes(payload).decode("utf-8")
    assert all(canary not in encoded for canary in canaries)
    assert all(value is False for value in payload["checks"].values())
    assert payload["authorization"]["preregistration_frozen"] is True
    assert payload["authorization"]["execution_permit_valid"] is False


def test_no_go_rejects_python_bool_int_and_null_aliases() -> None:
    cases = []
    null_check = runner._failure_payload("internal_failure")
    null_check["checks"][runner.CHECK_KEYS[0]] = None
    cases.append(null_check)
    nonzero_dependency = runner._failure_payload("internal_failure")
    nonzero_dependency["dependencies"][runner.DEPENDENCY_ROLES[0]] = "f" * 64
    cases.append(nonzero_dependency)
    integer_flag = runner._failure_payload("internal_failure")
    integer_flag["authorization"]["network"] = 0
    cases.append(integer_flag)
    boolean_schema = runner._failure_payload("internal_failure")
    boolean_schema["schema_version"] = True
    cases.append(boolean_schema)
    boolean_cost = runner._failure_payload("internal_failure")
    boolean_cost["cost"]["model_calls"] = False
    cases.append(boolean_cost)
    invalid_implication = runner._failure_payload("internal_failure", False, True)
    cases.append(invalid_implication)
    for payload in cases:
        with pytest.raises(runner.LedgerFailure, match="output_schema_failure"):
            runner.validate_output(payload)


def test_contract_preflight_accepts_exact_13_plus_permit(tmp_path: Path) -> None:
    _contract_tree(tmp_path)
    raws, dependencies = runner._load_authorized(1, tmp_path)
    assert set(raws) == runner.PARSED_ROLES
    assert set(dependencies) == set(runner.DEPENDENCY_ROLES)


def test_contract_hash_drift_fails_before_parsed_input_read(tmp_path: Path) -> None:
    _contract_tree(tmp_path)
    selected = tmp_path.joinpath(*runner.SELECTED_PATHS["compact100"].split("/"))
    selected.write_bytes(b"drift\n")
    with pytest.raises(runner.PreflightFailure) as caught:
        runner._load_authorized(1, tmp_path)
    assert caught.value.preregistration_frozen is False
    assert caught.value.execution_permit_valid is False


@pytest.mark.parametrize(
    "role",
    [
        "m27c_seed2",
        "m27c_gate",
        "compact100",
        "m28_seed1",
        "m28_gate",
        "design_v2",
        "runner",
        "runner_tests",
    ],
)
def test_each_selected_input_class_is_hash_bound(tmp_path: Path, role: str) -> None:
    _contract_tree(tmp_path)
    selected = tmp_path.joinpath(*runner.SELECTED_PATHS[role].split("/"))
    selected.write_bytes(b"class-specific-drift\n")
    with pytest.raises(runner.PreflightFailure):
        runner._load_authorized(1, tmp_path)


def test_permit_binding_drift_preserves_only_prereg_status(tmp_path: Path) -> None:
    prereg, permit = _contract_tree(tmp_path)
    permit["bindings"]["runner_sha256"] = "f" * 64
    permit_path = tmp_path.joinpath(*runner.PERMIT_RELATIVE.split("/"))
    permit_path.write_bytes(runner.canonical_json_bytes(permit) + b"\n")
    with pytest.raises(runner.PreflightFailure) as caught:
        runner._load_authorized(1, tmp_path)
    assert caught.value.preregistration_frozen is True
    assert caught.value.execution_permit_valid is False
    assert prereg["frozen_inputs"]["runner"]["sha256"] != "f" * 64


def test_additional_prereg_key_is_rejected(tmp_path: Path) -> None:
    prereg, _ = _contract_tree(tmp_path)
    prereg["unexpected"] = True
    prereg_path = tmp_path.joinpath(*runner.PREREG_RELATIVE.split("/"))
    prereg_path.write_bytes(runner.canonical_json_bytes(prereg) + b"\n")
    with pytest.raises(runner.PreflightFailure):
        runner._load_authorized(1, tmp_path)


def test_missing_prereg_key_is_rejected(tmp_path: Path) -> None:
    prereg, _ = _contract_tree(tmp_path)
    prereg.pop("scope")
    prereg_path = tmp_path.joinpath(*runner.PREREG_RELATIVE.split("/"))
    prereg_path.write_bytes(runner.canonical_json_bytes(prereg) + b"\n")
    with pytest.raises(runner.PreflightFailure):
        runner._load_authorized(1, tmp_path)


def test_missing_permit_retains_validated_prereg_status(tmp_path: Path) -> None:
    _contract_tree(tmp_path)
    permit_path = tmp_path.joinpath(*runner.PERMIT_RELATIVE.split("/"))
    permit_path.unlink()
    with pytest.raises(runner.PreflightFailure) as caught:
        runner._load_authorized(1, tmp_path)
    assert caught.value.preregistration_frozen is True
    assert caught.value.execution_permit_valid is False


@pytest.mark.parametrize(
    "relative",
    ["C:/escape.json", "../escape.json", "evals\\escape.json", "/absolute.json"],
)
def test_path_escape_forms_are_rejected(tmp_path: Path, relative: str) -> None:
    with pytest.raises(runner.LedgerFailure):
        runner._resolve_file(tmp_path, relative)


def test_symlink_selected_input_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("x", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(runner.LedgerFailure):
        runner._resolve_file(tmp_path, "link.txt")


def test_output_file_symlink_is_rejected_before_write(tmp_path: Path) -> None:
    target = tmp_path / "outside.json"
    target.write_text("unchanged", encoding="utf-8")
    output = tmp_path.joinpath(*runner.OUTPUT_RELATIVES[1].split("/"))
    output.parent.mkdir(parents=True)
    try:
        output.symlink_to(target)
    except OSError:
        output.hardlink_to(target)
    with pytest.raises(runner.LedgerFailure, match="contract_integrity_failure"):
        runner._write_payload(tmp_path, runner.OUTPUT_RELATIVES[1], runner._failure_payload("internal_failure"))
    assert target.read_text(encoding="utf-8") == "unchanged"


def test_output_directory_symlink_is_rejected_before_write(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}_outside"
    outside.mkdir()
    evals = tmp_path / "evals"
    try:
        evals.symlink_to(outside, target_is_directory=True)
    except OSError:
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(evals), str(outside)],
            capture_output=True,
            check=False,
        )
        if created.returncode != 0:
            outside.rmdir()
            pytest.skip("directory symlink and junction creation are unavailable")
    try:
        with pytest.raises(runner.LedgerFailure, match="contract_integrity_failure"):
            runner._write_payload(tmp_path, runner.OUTPUT_RELATIVES[1], runner._failure_payload("internal_failure"))
        assert list(outside.iterdir()) == []
    finally:
        if evals.exists() or evals.is_symlink():
            evals.rmdir()
        outside.rmdir()


def test_runner_import_allowlist_and_no_dynamic_or_external_imports() -> None:
    path = ROOT / "scripts/s117_m29_reconciled_loss_ledger.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    observed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            observed.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            observed.add(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "__import__"}
    assert observed == {"__future__", "hashlib", "json", "math", "random", "socket", "sys", "pathlib", "typing"}
    source = path.read_text(encoding="utf-8")
    for forbidden in ("import os", "subprocess", "importlib", "urllib", "openai", "anthropic", "dotenv", "src.", "scripts.s117_m27", "scripts.s117_m28"):
        assert forbidden not in source


def test_network_tripwire_rejects_and_restores_on_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, real_inputs: dict[str, dict]) -> None:
    raws = {
        role: runner.canonical_json_bytes(real_inputs[role])
        for role in runner.PARSED_ROLES
    }
    original = socket.socket

    def authorized(_: int):
        return raws, _dependencies()

    def attempt_network(*args, **kwargs):
        socket.socket()
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_load_authorized", authorized)
    monkeypatch.setattr(runner, "build_payload", attempt_network)
    assert runner.main(["--seed", "1"]) == 1
    assert socket.socket is original
    output = tmp_path.joinpath(*runner.OUTPUT_RELATIVES[1].split("/"))
    payload = runner.strict_json_bytes(output.read_bytes())
    assert payload["failures"] == ["external_call_attempt"]
    assert payload["authorization"]["preregistration_frozen"] is True
    assert payload["authorization"]["execution_permit_valid"] is True


def test_network_tripwire_restores_on_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, real_inputs: dict[str, dict]) -> None:
    raws = {
        role: runner.canonical_json_bytes(real_inputs[role])
        for role in runner.PARSED_ROLES
    }
    original = socket.socket
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_load_authorized", lambda _: (raws, _dependencies()))
    assert runner.main(["--seed", "2"]) == 0
    assert socket.socket is original
    output = tmp_path.joinpath(*runner.OUTPUT_RELATIVES[2].split("/"))
    raw = output.read_bytes()
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert runner.strict_json_bytes(raw)["status"] == "RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY"


def test_real_exception_canaries_never_reach_no_go(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    canary = "SECRET_ENV=abc C:\\private\\manual.pdf table-content Traceback"
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_load_authorized", lambda _: ({}, _dependencies()))

    def explode(*args, **kwargs):
        raise RuntimeError(canary + repr((args, kwargs)))

    monkeypatch.setattr(runner, "build_payload", explode)
    assert runner.main(["--seed", "1"]) == 1
    output = tmp_path.joinpath(*runner.OUTPUT_RELATIVES[1].split("/"))
    raw = output.read_text(encoding="utf-8")
    assert canary not in raw
    assert "private" not in raw
    assert "manual.pdf" not in raw
    assert runner.strict_json_bytes(raw.encode())["failures"] == ["internal_failure"]
