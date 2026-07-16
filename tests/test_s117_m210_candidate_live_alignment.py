from __future__ import annotations

import ast
import copy
import socket
import subprocess
from pathlib import Path

import pytest

from scripts import s117_m210_candidate_live_alignment as runner


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def real_inputs() -> dict[str, dict]:
    return {
        role: runner.strict_json((ROOT / runner.SELECTED_PATHS[role]).read_bytes())
        for role in runner.PRIMARY_JSON_ROLES
    }


def _dependencies(char: str = "a") -> dict[str, str]:
    return {role: char * 64 for role in runner.DEPENDENCY_ROLES}


def _build(inputs: dict[str, dict], seed: int = 1) -> dict:
    return runner.build_payload(
        inputs["m27a_seed1"], inputs["m27c_seed1"], inputs["m28_seed1"],
        inputs["m29_seed1"], _dependencies(), seed,
    )


@pytest.fixture(scope="module")
def go_payload(real_inputs: dict[str, dict]) -> dict:
    return _build(real_inputs)


def _resign_output(payload: dict) -> None:
    receipt_by_document: dict[str, str] = {}
    for document in payload["documents"]:
        core = dict(document)
        core.pop("m210_document_receipt_sha256", None)
        receipt = runner.sha(runner.canonical(core))
        document["m210_document_receipt_sha256"] = receipt
        receipt_by_document[document["extraction_sha256"]] = receipt
    for task in payload["tasks"]:
        task["m210_document_receipt_sha256"] = receipt_by_document[task["extraction_sha256"]]
        core = dict(task)
        core.pop("m210_task_receipt_sha256", None)
        task["m210_task_receipt_sha256"] = runner.sha(runner.canonical(core))
    payload["documents"].sort(key=lambda row: row["extraction_sha256"])
    payload["tasks"].sort(key=lambda row: row["local_row_id"])
    payload["manifests"] = runner._manifests(payload["documents"], payload["tasks"])


def _resign_m29(payload: dict) -> None:
    receipt_by_document: dict[str, str] = {}
    for document in payload["documents"]:
        core = dict(document)
        core.pop("m29_document_receipt_sha256", None)
        receipt = runner.sha(runner.canonical(core))
        document["m29_document_receipt_sha256"] = receipt
        receipt_by_document[document["extraction_sha256"]] = receipt
    for resolution in payload["resolved_baseline_missing_identities"]:
        resolution["m29_document_receipt_sha256"] = receipt_by_document[resolution["extraction_sha256"]]
        core = dict(resolution)
        core.pop("m29_resolution_receipt_sha256", None)
        resolution["m29_resolution_receipt_sha256"] = runner.sha(runner.canonical(core))
    documents = payload["documents"]
    resolved = payload["resolved_baseline_missing_identities"]
    document_receipts = [
        {"extraction_sha256": row["extraction_sha256"], "m29_document_receipt_sha256": row["m29_document_receipt_sha256"]}
        for row in documents
    ]
    resolution_receipts = [
        {"extraction_sha256": row["extraction_sha256"], "source_block_index": row["source_block_index"], "m29_resolution_receipt_sha256": row["m29_resolution_receipt_sha256"]}
        for row in resolved
    ]
    baseline_missing = sorted(
        ({"extraction_sha256": row["extraction_sha256"], "source_block_index": index} for row in documents for index in row["baseline_missing_block_indexes"]),
        key=lambda row: (row["extraction_sha256"], row["source_block_index"]),
    )
    candidate_missing = sorted(
        ({"extraction_sha256": row["extraction_sha256"], "source_block_index": index} for row in documents for index in row["candidate_missing_block_indexes"]),
        key=lambda row: (row["extraction_sha256"], row["source_block_index"]),
    )
    payload["manifests"] = {
        "documents_sha256": runner.sha(runner.canonical(documents)),
        "document_receipts_sha256": runner.sha(runner.canonical(document_receipts)),
        "resolved_baseline_missing_sha256": runner.sha(runner.canonical(resolved)),
        "resolution_receipts_sha256": runner.sha(runner.canonical(resolution_receipts)),
        "baseline_missing_identities_sha256": runner.sha(runner.canonical(baseline_missing)),
        "candidate_missing_identities_sha256": runner.sha(runner.canonical(candidate_missing)),
    }


def _prereg(frozen_inputs: dict[str, dict]) -> dict:
    return {
        "instrument": "s117_m210_candidate_live_alignment_prereg_v1",
        "schema_version": 1,
        "status": "frozen_before_execution",
        "scope": {
            "purpose": "derive_candidate_live_alignment_from_frozen_evidence",
            "authority": "frozen_candidate_projection_and_delta_raw_parsed_block_surface_only",
            "allowed": ["local_frozen_evidence_read", "local_eval_write"],
            "forbidden": ["raw_store_read", "chunk_execution", "candidate_execution", "database", "network", "models"],
        },
        "frozen_inputs": frozen_inputs,
        "expected": {
            "counts": copy.deepcopy(runner.EXPECTED_COUNTS),
            "projection": {"bytes": runner.PROJECTION_BYTES, "sha256": runner.PROJECTION_SHA},
            "changed_extraction_sha256": runner.CHANGED_EXTRACTION,
            "changed_task_id": runner.CHANGED_TASK,
            "changed_mapping": {
                "target_baseline_ordinal": 61, "target_candidate_ordinal": 61,
                "modified_baseline_ordinal": 39, "modified_candidate_ordinal": 39,
                "coverage_gain_block_indexes": [630, 631],
            },
            "check_keys": list(runner.CHECK_KEYS),
            "failure_codes": list(runner.FAILURE_CODES),
            "dependency_roles": list(runner.DEPENDENCY_ROLES),
            "document_identities_sha256": runner.DOCUMENT_IDENTITIES_SHA,
            "task_identities_sha256": runner.TASK_IDENTITIES_SHA,
        },
        "execution": {
            "seeds": [1, 2],
            "outputs": {"1": runner.OUTPUTS[1], "2": runner.OUTPUTS[2]},
            "perturbation": "shuffle_documents_and_tasks_then_restore_canonical_order",
            "required": ["focused_tests_green", "adversarial_go", "permit_valid"],
        },
        "authorization": {
            "preregistration_frozen": True, "alignment_execution": False,
            "raw_store_read": False, "chunk_execution": False,
            "additional_candidate_execution": False, "database": False,
            "network": False, "models": False, "load": False, "serving": False,
            "deploy": False, "facts_moved_to_ok": 0, "M3": "BLOCKED",
        },
    }


def _permit(prereg_raw: bytes, prereg: dict) -> dict:
    return {
        "instrument": "s117_m210_candidate_live_alignment_execution_permit_v1",
        "schema_version": 1,
        "status": "authorized_two_seeded_local_alignment_derivations",
        "bindings": {
            "preregistration_sha256": runner.sha(prereg_raw),
            "design_sha256": prereg["frozen_inputs"]["design"]["sha256"],
            "runner_sha256": prereg["frozen_inputs"]["runner"]["sha256"],
            "runner_tests_sha256": prereg["frozen_inputs"]["runner_tests"]["sha256"],
        },
        "allowed_seeds": [1, 2],
        "additional_candidate_execution": False,
        "authorization": {
            "alignment_execution": True, "raw_store_read": False,
            "chunk_execution": False, "additional_candidate_execution": False,
            "database": False, "network": False, "models": False, "load": False,
            "serving": False, "deploy": False, "facts_moved_to_ok": 0,
            "M3": "BLOCKED",
        },
    }


def _write_json(path: Path, value: dict) -> bytes:
    raw = runner.canonical(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _contract_tree(tmp_path: Path) -> tuple[dict, dict]:
    pair_names = {role: role.split("_seed")[0] for pair in runner.SEED_PAIRS for role in pair}
    frozen: dict[str, dict] = {}
    for role, relative in runner.SELECTED_PATHS.items():
        raw = ((pair_names.get(role) or role) + "\n").encode()
        path = tmp_path.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        parsed = role in runner.PRIMARY_JSON_ROLES
        frozen[role] = {
            "path": relative, "sha256": runner.sha(raw),
            "format": "JSON" if parsed else "blob",
            "use": "parsed" if parsed else "hash-only",
        }
    prereg = _prereg(frozen)
    prereg_path = tmp_path.joinpath(*runner.PREREG_RELATIVE.split("/"))
    prereg_raw = _write_json(prereg_path, prereg)
    permit = _permit(prereg_raw, prereg)
    _write_json(tmp_path.joinpath(*runner.PERMIT_RELATIVE.split("/")), permit)
    return prereg, permit


def test_real_frozen_evidence_builds_closed_go(go_payload: dict) -> None:
    assert go_payload["status"] == "CANDIDATE_LIVE_ALIGNMENT_GO_UPSTREAM_ONLY"
    assert go_payload["counts"] == runner.EXPECTED_COUNTS
    assert len(go_payload["documents"]) == 18
    assert len(go_payload["tasks"]) == 21
    assert go_payload["authorization"]["facts_moved_to_ok"] == 0
    assert go_payload["authorization"]["M3"] == "BLOCKED"
    runner.validate_output(go_payload)


def test_seed_perturbation_restores_byte_identical_output(real_inputs: dict[str, dict], go_payload: dict) -> None:
    seed2 = _build(real_inputs, 2)
    assert runner.canonical(go_payload) == runner.canonical(seed2)


def test_only_changed_live_document_and_task_have_frozen_delta(go_payload: dict) -> None:
    changed_documents = [row for row in go_payload["documents"] if row["fingerprint_multiset_changed"]]
    changed_tasks = [row for row in go_payload["tasks"] if row["candidate_membership_mode"] == "frozen_delta_unchanged_mapping"]
    assert [(row["extraction_sha256"], row["coverage_gain_block_indexes"]) for row in changed_documents] == [(runner.CHANGED_EXTRACTION, [630, 631])]
    assert [(row["local_row_id"], row["candidate_ordinal"], row["target_source_block_start"]) for row in changed_tasks] == [(runner.CHANGED_TASK, 61, 796)]


@pytest.mark.parametrize("raw", [
    b"\xef\xbb\xbf{}", b'{"a":1,"a":2}', b'{"a":NaN}',
    b'{"a":Infinity}', b'{"a":-Infinity}', b'{"a":1e999}',
])
def test_strict_json_rejects_ambiguous_or_nonfinite_values(raw: bytes) -> None:
    with pytest.raises(runner.AlignmentFailure, match="contract_integrity_failure"):
        runner.strict_json(raw)


def test_receipt_and_fingerprint_formulas_are_exact(real_inputs: dict[str, dict]) -> None:
    document = real_inputs["m27a_seed1"]["raw_document_receipts"][0]
    row = document["v3_rows"][0]
    assert runner._receipt(document)
    assert runner._receipt(row)
    assert runner._fingerprint(row) == runner._fingerprint(copy.deepcopy(row))
    assert runner._multiset(document["v3_rows"]) == next(
        item["baseline_fingerprint_multiset_sha256"]
        for item in real_inputs["m27c_seed1"]["documents"]
        if item["extraction_sha256"] == document["extraction_sha256"]
    )


def test_m27a_m27c_bridge_rejects_fully_resigned_surface_drift(real_inputs: dict[str, dict]) -> None:
    m27a = dict(real_inputs["m27a_seed1"])
    documents = list(m27a["raw_document_receipts"])
    index = next(i for i, row in enumerate(documents) if row["extraction_sha256"] == runner.CHANGED_EXTRACTION)
    document = dict(documents[index])
    document["raw_surface_sha256"] = "f" * 64
    core = dict(document); core.pop("receipt_sha256")
    document["receipt_sha256"] = runner.sha(runner.canonical(core))
    documents[index] = document
    tasks = list(m27a["task_evidence"])
    for task_index, original in enumerate(tasks):
        if original["extraction_sha256"] == runner.CHANGED_EXTRACTION:
            task = dict(original)
            task["raw_document_receipt_sha256"] = document["receipt_sha256"]
            core = dict(task); core.pop("receipt_sha256")
            task["receipt_sha256"] = runner.sha(runner.canonical(core))
            tasks[task_index] = task
    m27a["raw_document_receipts"] = documents
    m27a["task_evidence"] = tasks
    manifests = dict(m27a["manifests"])
    manifests["raw_document_receipts_sha256"] = runner._jsonl_manifest(documents, "extraction_sha256")
    manifests["task_evidence_sha256"] = runner._jsonl_manifest(tasks, "local_row_id")
    m27a["manifests"] = manifests
    inputs = dict(real_inputs); inputs["m27a_seed1"] = m27a
    with pytest.raises(runner.AlignmentFailure, match="m27a_m27c_baseline_bridge_failure"):
        _build(inputs)


def test_m28_projection_manifest_drift_is_rejected(real_inputs: dict[str, dict]) -> None:
    m28 = copy.deepcopy(real_inputs["m28_seed1"])
    m28["manifests"]["candidate_projection_sha256"] = "f" * 64
    inputs = dict(real_inputs); inputs["m28_seed1"] = m28
    with pytest.raises(runner.AlignmentFailure, match="candidate_projection_bridge_failure"):
        _build(inputs)


def test_m29_resigned_document_link_drift_is_rejected_by_frozen_manifest(real_inputs: dict[str, dict]) -> None:
    m29 = copy.deepcopy(real_inputs["m29_seed1"])
    document = next(row for row in m29["documents"] if row["extraction_sha256"] == runner.CHANGED_EXTRACTION)
    document["raw_artifact_sha256"] = "f" * 64
    _resign_m29(m29)
    inputs = dict(real_inputs); inputs["m29_seed1"] = m29
    with pytest.raises(runner.AlignmentFailure, match="m29_seed_drift"):
        _build(inputs)


@pytest.mark.parametrize("role,validator,code", [
    ("m28_seed1", runner._validate_m28, "m28_seed_drift"),
    ("m29_seed1", runner._validate_m29, "m29_seed_drift"),
])
def test_historical_external_calls_blocked_requires_exact_bool(real_inputs: dict[str, dict], role: str, validator, code: str) -> None:
    payload = copy.deepcopy(real_inputs[role])
    payload["cost"]["external_calls_blocked"] = 1
    with pytest.raises(runner.AlignmentFailure, match=code):
        validator(payload)


@pytest.mark.parametrize("key", ["json_files", "records"])
def test_m28_source_counts_require_exact_int(real_inputs: dict[str, dict], key: str) -> None:
    payload = copy.deepcopy(real_inputs["m28_seed1"])
    payload["source"][key] = float(payload["source"][key])
    with pytest.raises(runner.AlignmentFailure, match="m28_seed_drift"):
        runner._validate_m28(payload)


def test_m28_generation_schema_is_exact(real_inputs: dict[str, dict]) -> None:
    payload = copy.deepcopy(real_inputs["m28_seed1"])
    payload["generation"]["manifest_schema"] = 123
    with pytest.raises(runner.AlignmentFailure, match="m28_seed_drift"):
        runner._validate_m28(payload)


def test_changed_delta_resigned_mapping_attack_is_rejected_by_frozen_manifest(real_inputs: dict[str, dict]) -> None:
    m27c = copy.deepcopy(real_inputs["m27c_seed1"])
    delta = next(row for row in m27c["changed_document_deltas"] if row["extraction_sha256"] == runner.CHANGED_EXTRACTION)
    mapping = next(row for row in delta["unchanged"] if row["baseline_ordinal"] == 61)
    mapping["treatment_ordinal"] = 62
    core = dict(delta); core.pop("receipt_sha256")
    delta["receipt_sha256"] = runner.sha(runner.canonical(core))
    m27c["manifests"]["deltas_sha256"] = runner._jsonl_manifest(m27c["changed_document_deltas"], "extraction_sha256")
    inputs = dict(real_inputs); inputs["m27c_seed1"] = m27c
    with pytest.raises(runner.AlignmentFailure, match="m27c_receipt_failure"):
        _build(inputs)


def test_m27a_resigned_adjudication_status_attack_is_rejected(real_inputs: dict[str, dict]) -> None:
    m27a = dict(real_inputs["m27a_seed1"])
    tasks = list(m27a["task_evidence"])
    task = dict(tasks[0])
    task["adjudication_status"] = "authorized"
    core = dict(task); core.pop("receipt_sha256")
    task["receipt_sha256"] = runner.sha(runner.canonical(core))
    tasks[0] = task
    m27a["task_evidence"] = tasks
    manifests = dict(m27a["manifests"])
    manifests["task_evidence_sha256"] = runner._jsonl_manifest(tasks, "local_row_id")
    m27a["manifests"] = manifests
    inputs = dict(real_inputs); inputs["m27a_seed1"] = m27a
    with pytest.raises(runner.AlignmentFailure, match="m27a_receipt_failure"):
        _build(inputs)


def test_resigned_document_identity_attack_hits_preregistered_anchor(go_payload: dict) -> None:
    payload = copy.deepcopy(go_payload)
    document = next(row for row in payload["documents"] if not row["fingerprint_multiset_changed"])
    old = document["extraction_sha256"]
    document["extraction_sha256"] = "f" * 64
    for task in payload["tasks"]:
        if task["extraction_sha256"] == old:
            task["extraction_sha256"] = "f" * 64
    _resign_output(payload)
    with pytest.raises(runner.AlignmentFailure, match="manifest_integrity_failure"):
        runner.validate_output(payload)


def test_resigned_task_identity_attack_hits_preregistered_anchor(go_payload: dict) -> None:
    payload = copy.deepcopy(go_payload)
    task = next(row for row in payload["tasks"] if row["local_row_id"] != runner.CHANGED_TASK)
    task["local_row_id"] = "00000000-0000-4000-8000-000000000001"
    _resign_output(payload)
    with pytest.raises(runner.AlignmentFailure, match="manifest_integrity_failure"):
        runner.validate_output(payload)


def test_resigned_unchanged_document_normative_fields_hit_full_output_anchor(go_payload: dict) -> None:
    payload = copy.deepcopy(go_payload)
    document = next(row for row in payload["documents"] if not row["fingerprint_multiset_changed"])
    document["candidate_surface_sha256"] = "f" * 64
    document["raw_surface_sha256"] = "f" * 64
    _resign_output(payload)
    with pytest.raises(runner.AlignmentFailure, match="manifest_integrity_failure"):
        runner.validate_output(payload)


def test_resigned_unchanged_task_normative_fields_hit_full_output_anchor(go_payload: dict) -> None:
    payload = copy.deepcopy(go_payload)
    task = next(row for row in payload["tasks"] if row["local_row_id"] != runner.CHANGED_TASK)
    task["original_task_evidence_receipt_sha256"] = "f" * 64
    task["target_content_sha256"] = "e" * 64
    task["target_fingerprint_sha256"] = "d" * 64
    task["target_source_block_start"] += 1
    task["target_source_block_end"] += 1
    task["overlap_fingerprints_sha256"] = "c" * 64
    _resign_output(payload)
    with pytest.raises(runner.AlignmentFailure, match="manifest_integrity_failure"):
        runner.validate_output(payload)


@pytest.mark.parametrize("mutation", ["extra", "missing", "bool_count", "cost_bool", "bad_authority"])
def test_output_envelope_and_exact_types_are_closed(go_payload: dict, mutation: str) -> None:
    payload = copy.deepcopy(go_payload)
    if mutation == "extra":
        payload["unexpected"] = True
    elif mutation == "missing":
        payload.pop("authority")
    elif mutation == "bool_count":
        payload["counts"]["documents"] = True
    elif mutation == "cost_bool":
        payload["cost"]["network_calls"] = False
    else:
        payload["authority"] = "broader_authority"
    with pytest.raises(runner.AlignmentFailure, match="output_schema_failure"):
        runner.validate_output(payload)


def test_output_document_conditional_is_enforced_after_resigning(go_payload: dict) -> None:
    payload = copy.deepcopy(go_payload)
    document = next(row for row in payload["documents"] if not row["fingerprint_multiset_changed"])
    document["fingerprint_multiset_changed"] = True
    document["candidate_mapping_mode"] = "frozen_changed_delta"
    _resign_output(payload)
    with pytest.raises(runner.AlignmentFailure, match="output_schema_failure"):
        runner.validate_output(payload)


def test_output_task_conditional_is_enforced_after_resigning(go_payload: dict) -> None:
    payload = copy.deepcopy(go_payload)
    task = next(row for row in payload["tasks"] if row["local_row_id"] == runner.CHANGED_TASK)
    task["candidate_ordinal"] = None
    _resign_output(payload)
    with pytest.raises(runner.AlignmentFailure, match="output_schema_failure"):
        runner.validate_output(payload)


@pytest.mark.parametrize("collection,key", [("documents", "extraction_sha256"), ("tasks", "local_row_id")])
def test_nested_missing_key_is_sanitized_as_output_schema_failure(go_payload: dict, collection: str, key: str) -> None:
    payload = copy.deepcopy(go_payload)
    payload[collection][0].pop(key)
    with pytest.raises(runner.AlignmentFailure, match="output_schema_failure"):
        runner.validate_output(payload)


@pytest.mark.parametrize("code", runner.FAILURE_CODES)
def test_each_sanitized_no_go_is_closed(code: str) -> None:
    payload = runner._failure_payload(code, True, False)
    runner.validate_output(payload)
    assert payload["failures"] == [code]
    assert payload["documents"] == [] and payload["tasks"] == []


def test_preflight_accepts_exact_15_inputs_and_17_dependencies(tmp_path: Path) -> None:
    _contract_tree(tmp_path)
    raws, dependencies = runner._load_authorized(1, tmp_path)
    assert set(raws) == set(runner.PRIMARY_JSON_ROLES)
    assert set(dependencies) == set(runner.DEPENDENCY_ROLES)


def test_prereg_extra_key_is_rejected(tmp_path: Path) -> None:
    prereg, _ = _contract_tree(tmp_path)
    prereg["unexpected"] = True
    _write_json(tmp_path.joinpath(*runner.PREREG_RELATIVE.split("/")), prereg)
    with pytest.raises(runner.PreflightFailure):
        runner._load_authorized(1, tmp_path)


def test_prereg_bool_integer_alias_is_rejected(tmp_path: Path) -> None:
    prereg, _ = _contract_tree(tmp_path)
    prereg["expected"]["counts"]["documents"] = True
    _write_json(tmp_path.joinpath(*runner.PREREG_RELATIVE.split("/")), prereg)
    with pytest.raises(runner.PreflightFailure):
        runner._load_authorized(1, tmp_path)


def test_seed_pair_drift_is_classified_before_permit(tmp_path: Path) -> None:
    prereg, _ = _contract_tree(tmp_path)
    role = "m27a_seed2"
    raw = b"drift\n"
    tmp_path.joinpath(*runner.SELECTED_PATHS[role].split("/")).write_bytes(raw)
    prereg["frozen_inputs"][role]["sha256"] = runner.sha(raw)
    _write_json(tmp_path.joinpath(*runner.PREREG_RELATIVE.split("/")), prereg)
    with pytest.raises(runner.PreflightFailure, match="m27a_seed_drift"):
        runner._load_authorized(1, tmp_path)


def test_selected_input_hash_drift_is_rejected(tmp_path: Path) -> None:
    _contract_tree(tmp_path)
    tmp_path.joinpath(*runner.SELECTED_PATHS["m28_gate"].split("/")).write_bytes(b"drift")
    with pytest.raises(runner.PreflightFailure, match="contract_integrity_failure"):
        runner._load_authorized(1, tmp_path)


def test_missing_permit_retains_validated_prereg_status(tmp_path: Path) -> None:
    _contract_tree(tmp_path)
    tmp_path.joinpath(*runner.PERMIT_RELATIVE.split("/")).unlink()
    with pytest.raises(runner.PreflightFailure) as caught:
        runner._load_authorized(1, tmp_path)
    assert caught.value.prereg is True
    assert caught.value.permit is False


def test_permit_bool_integer_alias_is_rejected(tmp_path: Path) -> None:
    prereg, permit = _contract_tree(tmp_path)
    permit["allowed_seeds"] = [True, 2]
    _write_json(tmp_path.joinpath(*runner.PERMIT_RELATIVE.split("/")), permit)
    with pytest.raises(runner.PreflightFailure):
        runner._load_authorized(1, tmp_path)


@pytest.mark.parametrize("relative", ["C:/escape.json", "../escape.json", "evals\\escape.json", "/absolute.json"])
def test_path_escape_forms_are_rejected(tmp_path: Path, relative: str) -> None:
    with pytest.raises(runner.AlignmentFailure):
        runner._resolve_file(tmp_path, relative)
    with pytest.raises(runner.AlignmentFailure):
        runner._output_path(tmp_path, relative)


def test_symlink_selected_input_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("x", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(runner.AlignmentFailure):
        runner._resolve_file(tmp_path, "link.txt")


def test_output_file_link_or_preexisting_file_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "outside.json"
    target.write_text("unchanged", encoding="utf-8")
    output = tmp_path.joinpath(*runner.OUTPUTS[1].split("/"))
    output.parent.mkdir(parents=True)
    try:
        output.symlink_to(target)
    except OSError:
        output.hardlink_to(target)
    with pytest.raises(runner.AlignmentFailure, match="contract_integrity_failure"):
        runner._write(tmp_path, runner.OUTPUTS[1], runner._failure_payload("internal_failure"))
    assert target.read_text(encoding="utf-8") == "unchanged"


def test_output_directory_symlink_or_junction_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}_outside"
    outside.mkdir()
    evals = tmp_path / "evals"
    try:
        evals.symlink_to(outside, target_is_directory=True)
    except OSError:
        created = subprocess.run(["cmd", "/c", "mklink", "/J", str(evals), str(outside)], capture_output=True, check=False)
        if created.returncode != 0:
            outside.rmdir()
            pytest.skip("directory symlink and junction creation are unavailable")
    try:
        with pytest.raises(runner.AlignmentFailure, match="contract_integrity_failure"):
            runner._write(tmp_path, runner.OUTPUTS[1], runner._failure_payload("internal_failure"))
        assert list(outside.iterdir()) == []
    finally:
        if evals.exists() or evals.is_symlink():
            evals.rmdir()
        outside.rmdir()


def test_runner_import_allowlist_and_no_dynamic_or_external_imports() -> None:
    path = ROOT / "scripts/s117_m210_candidate_live_alignment.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    observed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            observed.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            observed.add(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "__import__"}
    assert observed == {"__future__", "hashlib", "json", "math", "random", "socket", "sys", "pathlib", "typing", "uuid"}
    source = path.read_text(encoding="utf-8")
    for forbidden in ("import os", "subprocess", "importlib", "urllib", "openai", "anthropic", "dotenv", "scripts.s117_m27", "scripts.s117_m28", "scripts.s117_m29"):
        assert forbidden not in source


def test_network_tripwire_rejects_and_restores_on_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original = socket.socket
    strict = runner.strict_json
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_load_authorized", lambda _: ({role: role.encode() for role in runner.PRIMARY_JSON_ROLES}, _dependencies()))
    monkeypatch.setattr(runner, "strict_json", lambda _: {})

    def attempt_network(*args, **kwargs):
        socket.socket()
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(runner, "build_payload", attempt_network)
    assert runner.main(["--seed", "1"]) == 1
    assert socket.socket is original
    payload = strict(tmp_path.joinpath(*runner.OUTPUTS[1].split("/")).read_bytes())
    assert payload["failures"] == ["external_call_attempt"]
    assert payload["authorization"]["execution_permit_valid"] is True


def test_network_tripwire_restores_on_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, go_payload: dict) -> None:
    original = socket.socket
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_load_authorized", lambda _: ({role: role.encode() for role in runner.PRIMARY_JSON_ROLES}, _dependencies()))
    monkeypatch.setattr(runner, "strict_json", lambda _: {})
    monkeypatch.setattr(runner, "build_payload", lambda *args, **kwargs: copy.deepcopy(go_payload))
    assert runner.main(["--seed", "2"]) == 0
    assert socket.socket is original
    raw = tmp_path.joinpath(*runner.OUTPUTS[2].split("/")).read_bytes()
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")


def test_real_exception_canaries_never_reach_no_go(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    canary = "SECRET_ENV=abc C:\\private\\manual.pdf table-content Traceback"
    strict = runner.strict_json
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_load_authorized", lambda _: ({role: role.encode() for role in runner.PRIMARY_JSON_ROLES}, _dependencies()))
    monkeypatch.setattr(runner, "strict_json", lambda _: {})

    def explode(*args, **kwargs):
        raise RuntimeError(canary + repr((args, kwargs)))

    monkeypatch.setattr(runner, "build_payload", explode)
    assert runner.main(["--seed", "1"]) == 1
    raw = tmp_path.joinpath(*runner.OUTPUTS[1].split("/")).read_text(encoding="utf-8")
    assert canary not in raw and "manual.pdf" not in raw and "private" not in raw
    assert strict(raw.encode())["failures"] == ["internal_failure"]
