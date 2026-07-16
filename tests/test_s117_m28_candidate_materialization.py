from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import s117_m28_candidate_materialization as runner
from scripts import s117_m28_candidate_validation as validation
from scripts import s117_materialize_chunks_v3_local as row_validator
from src.reingest.chunk import Chunk, chunk_document
from src.reingest import chunk_provenance as materializer


ROOT = Path(__file__).resolve().parents[1]
REAL_SEEDS = (
    ROOT / "evals/s117_m27_loss_safe_chunking_probe_seed1_v2.json",
    ROOT / "evals/s117_m27_loss_safe_chunking_probe_seed2_v2.json",
)
ALLOWED_LOCAL_MODULES = {
    "src",
    "src.reingest",
    "src.reingest.chunk",
    "src.reingest.chunk_provenance",
    "scripts",
    "scripts.s117_materialize_chunks_v3_local",
    "scripts.s117_m28_candidate_validation",
    "scripts.s117_m28_candidate_materialization",
}
LOCAL_CLOSURE = {
    "src": ROOT / "src/__init__.py",
    "src.reingest": ROOT / "src/reingest/__init__.py",
    "src.reingest.chunk": ROOT / "src/reingest/chunk.py",
    "src.reingest.chunk_provenance": ROOT / "src/reingest/chunk_provenance.py",
    "scripts.s117_materialize_chunks_v3_local": ROOT
    / "scripts/s117_materialize_chunks_v3_local.py",
    "scripts.s117_m28_candidate_validation": ROOT
    / "scripts/s117_m28_candidate_validation.py",
    "scripts.s117_m28_candidate_materialization": ROOT
    / "scripts/s117_m28_candidate_materialization.py",
}
FORBIDDEN_IMPORT_PREFIXES = (
    "anthropic",
    "openai",
    "dotenv",
    "requests",
    "httpx",
    "urllib",
    "psycopg",
    "sqlalchemy",
    "supabase",
    "src.config",
    "src.reingest.contextualize",
    "src.reingest.embed",
    "scripts.s117_m2_",
    "scripts.s117_m26_",
    "scripts.s117_m27_",
)

# urllib remains forbidden as a direct source dependency because this gate must
# stay offline. It is not a valid runtime-module tripwire: PyYAML and Python's
# standard library may import urllib transitively without performing I/O.
RUNTIME_FORBIDDEN_IMPORT_PREFIXES = tuple(
    prefix for prefix in FORBIDDEN_IMPORT_PREFIXES if prefix != "urllib"
)


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _chunk(content: str, start: int, end: int, *, index: int = 0) -> Chunk:
    return Chunk(
        content=content,
        section_title=None,
        section_path=None,
        page_number=1,
        chunk_index=index,
        source_block_start=start,
        source_block_end=end,
    )


def _raw_record(markdown: str = "alpha\n\nbeta") -> tuple[bytes, dict]:
    record = {
        "sha256": "a" * 64,
        "result": {"pages": [{"page": 1, "md": markdown}]},
    }
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return raw, record


def _dependencies() -> dict[str, str]:
    result = {key: "d" * 64 for key in validation.DEPENDENCY_KEYS}
    result["chunker_sha256"] = _sha(ROOT / "src/reingest/chunk.py")
    result["materializer_sha256"] = _sha(ROOT / "src/reingest/chunk_provenance.py")
    result["row_validator_sha256"] = _sha(
        ROOT / "scripts/s117_materialize_chunks_v3_local.py"
    )
    result["candidate_validator_sha256"] = _sha(
        ROOT / "scripts/s117_m28_candidate_validation.py"
    )
    return result


def _synthetic_case(tmp_path: Path) -> dict:
    store = tmp_path / runner.DEFAULT_STORE_RELATIVE
    store.mkdir(parents=True)
    record = {
        "sha256": "a" * 64,
        "result": {
            "pages": [
                {"page": 1, "md": "# Setup\n\nalpha\n\nbeta", "confidence": 0.9}
            ]
        },
    }
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    (store / f"{record['sha256']}.json").write_bytes(raw)
    (store / "_failures.json").write_text("{}\n", encoding="utf-8")

    dependencies = _dependencies()
    descriptor = [{
        "extraction_sha256": record["sha256"],
        "raw_artifact_sha256": validation.sha256_bytes(raw),
    }]
    manifest = materializer.generation_manifest(
        descriptor,
        chunker_sha256=dependencies["chunker_sha256"],
        materializer_sha256=dependencies["materializer_sha256"],
    )
    manifest_sha, materialization_id = materializer.materialization_identity(manifest)
    fingerprint_rows = validation.fingerprint_rows(chunk_document(record))
    fingerprint_multiset = validation._fingerprint_multiset_sha256(fingerprint_rows)
    raw_surface = validation.surface("# Setup\n\nalpha\n\nbeta")
    document = {
        "extraction_sha256": record["sha256"],
        "raw_artifact_sha256": validation.sha256_bytes(raw),
        "raw_blocks": 3,
        "baseline_missing_block_indexes": [],
        "baseline_fingerprint_multiset_sha256": fingerprint_multiset,
        "treatment_rows": 1,
        "treatment_covered_blocks": 3,
        "treatment_missing_block_indexes": [],
        "treatment_surface_sha256": validation.sha256_bytes(
            raw_surface.encode("utf-8")
        ),
        "treatment_surface_equal_raw": True,
        "treatment_fingerprint_multiset_sha256": fingerprint_multiset,
        "coverage_gain_block_indexes": [],
        "coverage_regression_block_indexes": [],
        "changed": False,
    }
    seed = {"documents": [document]}
    projection = validation.treatment_projection_from_seed(seed)
    projection_bytes = validation.canonical_json_bytes(projection)
    frozen_inputs = {
        role: {"path": path, "sha256": "f" * 64}
        for role, path in runner.REQUIRED_PATHS.items()
    }
    expected_population = {
        "documents": 1,
        "raw_blocks": 3,
        "rows": 1,
        "titled_rows": 1,
        "untitled_rows": 0,
        "covered_blocks": 3,
        "missing_blocks": 0,
        "coverage_gain_blocks": 0,
        "coverage_regression_blocks": 0,
        "changed_documents": 0,
        "unchanged_documents": 1,
        "delta_unchanged_rows": 0,
        "delta_removed_rows": 0,
        "delta_added_rows": 0,
        "delta_overlap_modified_rows": 0,
        "delta_pure_added_rows": 0,
        "validation_failures": 0,
    }
    contract = {
        "instrument": "s117_m28_candidate_materialization_prereg_v1",
        "status": "frozen_before_candidate_execution",
        "selected_store_relative_path": runner.DEFAULT_STORE_RELATIVE.as_posix(),
        "frozen_inputs": frozen_inputs,
        "expected": {
            "source": {
                "json_files": 2,
                "records": 1,
                "non_record_artifacts": ["_failures.json"],
                "manifest_sha256": row_validator._store_manifest(
                    sorted(store.glob("*.json"), key=lambda path: path.name)
                ),
            },
            "generation": {
                "manifest_sha256": manifest_sha,
                "materialization_id": materialization_id,
            },
            "projection": {
                "bytes": len(projection_bytes),
                "sha256": validation.sha256_bytes(projection_bytes),
            },
            "population": expected_population,
            "baseline_rows_manifest_sha256": "e" * 64,
        },
    }
    baseline = {
        "dependencies": {"chunker_sha256": "b" * 64},
        "generation": {
            "manifest_sha256": "c" * 64,
            "materialization_id": "11111111-1111-5111-8111-111111111111",
        },
    }
    return {
        "store": store,
        "prereg": contract,
        "dependencies": dependencies,
        "baseline_receipt": baseline,
        "m27c_seed1": seed,
        "m27c_seed2": copy.deepcopy(seed),
    }


def _build(case: dict, seed: int = 1) -> dict:
    return runner.safe_build_candidate_payload(seed=seed, **case)


def test_canonical_surface_and_fingerprint_vectors_are_literal():
    value = {"a": "é", "b": [1, True, None]}
    assert validation.canonical_json_bytes(value) == b'{"a":"\xc3\xa9","b":[1,true,null]}'
    assert (
        validation.sha256_bytes(validation.canonical_json_bytes(value))
        == "170409917e32971e79e71df2c0a04cc84c3c089ef0c7c2a94dbde72cafebd52d"
    )
    assert validation.surface(" alpha\t beta\n gamma ") == "alpha beta gamma"
    record = {
        "sha256": "a" * 64,
        "result": {
            "pages": [
                {"page": 1, "md": "# Setup\n\nalpha\n\nbeta", "confidence": 0.9}
            ]
        },
    }
    rows = validation.fingerprint_rows(chunk_document(record))
    assert rows[0]["fingerprint_sha256"] == (
        "9cced6799f26f2926a31bef6f93ecefb508be1d7d7fa1c519c482459a57d9593"
    )
    assert validation._fingerprint_multiset_sha256(rows) == (
        "a6277bf6d4aede1b12af20f100d48a802cd9a75435035141bfd78c8a6af226b4"
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"[]",
        b'{"a":1,"a":2}',
        b'{"a":{"b":1,"b":2}}',
        b'{"a":NaN}',
        b'{"a":1e999}',
        "{\"a\":\"é\"}".encode("utf-16"),
    ],
)
def test_strict_json_rejects_non_object_duplicate_nonfinite_and_non_utf8(raw: bytes):
    with pytest.raises((UnicodeDecodeError, ValueError)):
        validation.strict_json_loads(raw)


def test_token_interval_validator_accepts_exact_and_rejects_loss_modes():
    raw, record = _raw_record()
    exact = [_chunk("alpha beta", 0, 1)]
    validation.validate_token_intervals(
        raw, record, exact, validation.fingerprint_rows(exact)
    )
    malformed = [
        [_chunk("alpha", 0, 1)],
        [_chunk("alpha alpha beta", 0, 1)],
        [_chunk("beta alpha", 0, 1)],
        [_chunk("alpha", 0, 1), _chunk("beta", 1, 1, index=1)],
    ]
    for chunks in malformed:
        with pytest.raises(RuntimeError):
            validation.validate_token_intervals(
                raw, record, chunks, validation.fingerprint_rows(chunks)
            )


def test_token_interval_validator_accepts_shared_and_partial_overlap_spans():
    raw, record = _raw_record("alpha beta")
    shared = [_chunk("alpha", 0, 0), _chunk("beta", 0, 0, index=1)]
    validation.validate_token_intervals(
        raw, record, shared, validation.fingerprint_rows(shared)
    )

    raw, record = _raw_record("alpha beta\n\ngamma")
    partial = [_chunk("alpha", 0, 0), _chunk("beta gamma", 0, 1, index=1)]
    validation.validate_token_intervals(
        raw, record, partial, validation.fingerprint_rows(partial)
    )


def test_token_interval_validator_rejects_raw_metadata_and_lineage_drift():
    cases = []
    raw, record = _raw_record("alpha")
    wrong_page = _chunk("alpha", 0, 0)
    wrong_page.page_number = 2
    cases.append((raw, record, [wrong_page]))

    raw, record = _raw_record("```mermaid\ngraph TD;A-->B\n```")
    cases.append((raw, record, [_chunk("```mermaid\ngraph TD;A-->B\n```", 0, 0)]))

    record = {
        "sha256": "a" * 64,
        "result": {"pages": [{"page": 1, "md": "alpha", "images": [{"id": 1}]}]},
    }
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    cases.append((raw, record, [_chunk("alpha", 0, 0)]))

    record = {
        "sha256": "a" * 64,
        "result": {"pages": [{"page": 1, "md": "alpha", "confidence": 0.9}]},
    }
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    wrong_confidence = _chunk("alpha", 0, 0)
    wrong_confidence.confidence = 0.8
    cases.append((raw, record, [wrong_confidence]))

    raw, record = _raw_record("# Setup\n\nalpha")
    cases.append((raw, record, [_chunk("# Setup\n\nalpha", 0, 1)]))

    for raw, record, chunks in cases:
        with pytest.raises(RuntimeError):
            validation.validate_token_intervals(
                raw, record, chunks, validation.fingerprint_rows(chunks)
            )


def test_delta_binding_requires_frozen_treatment_ordinals_and_fingerprints():
    fingerprint = "a" * 64
    frozen = {
        "unchanged": [[0, fingerprint]],
        "added": [[0, fingerprint]],
        "modified": [[0, fingerprint]],
        "pure_added": [],
    }
    validation.validate_candidate_delta_bindings(
        "b" * 64,
        [{"ordinal": 0, "fingerprint_sha256": fingerprint}],
        frozen,
    )
    with pytest.raises(RuntimeError, match="delta treatment binding"):
        validation.validate_candidate_delta_bindings(
            "b" * 64,
            [{"ordinal": 1, "fingerprint_sha256": fingerprint}],
            frozen,
        )


@pytest.mark.parametrize("seed_path", REAL_SEEDS)
def test_real_frozen_seed_projection_has_exact_neutral_hash_and_size(
    seed_path: Path,
):
    seed = validation.strict_json_loads(seed_path.read_bytes())
    projection = validation.treatment_projection_from_seed(seed)
    payload = validation.canonical_json_bytes(projection)
    assert len(projection) == 1068
    assert len(payload) == 640933
    assert validation.sha256_bytes(payload) == (
        "4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881"
    )
    delta = validation.delta_contract_from_seed(seed)
    assert delta["counts"] == {
        "delta_unchanged_rows": 2529,
        "delta_removed_rows": 15,
        "delta_added_rows": 29,
        "delta_overlap_modified_rows": 15,
        "delta_pure_added_rows": 14,
    }


def test_synthetic_candidate_is_go_seed_stable_and_nonloadable(tmp_path: Path):
    case = _synthetic_case(tmp_path)
    seed1 = _build(case, 1)
    seed2 = _build(case, 2)
    assert seed1["status"] == "GO"
    assert seed1["loadable"] is False
    assert validation.canonical_json_bytes(seed1) == validation.canonical_json_bytes(seed2)
    validation.validate_output_schema(seed1)


def test_each_validation_edge_and_global_invariant_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case = _synthetic_case(tmp_path)
    production = runner.materializer.materialize_raw_record

    def drifted_production(*args, **kwargs):
        rows = production(*args, **kwargs)
        rows[0]["section_title"] = "drifted"
        return rows

    monkeypatch.setattr(
        runner.materializer, "materialize_raw_record", drifted_production
    )
    assert _build(case)["failures"] == ["row_validation_failure"]
    monkeypatch.undo()

    monkeypatch.setattr(
        runner.row_validator, "validate_rows_against_raw", lambda *_a, **_k: ["drift"]
    )
    assert _build(case)["failures"] == ["row_validation_failure"]
    monkeypatch.undo()

    monkeypatch.setattr(
        runner.validation,
        "validate_token_intervals",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("CANARY_EXCEPTION")),
    )
    assert _build(case)["failures"] == ["raw_token_interval_failure"]
    monkeypatch.undo()

    seed_disagreement = copy.deepcopy(case)
    seed_disagreement["m27c_seed2"]["documents"][0]["treatment_rows"] = 2
    assert _build(seed_disagreement)["failures"] == ["contract_integrity"]

    projection_drift = copy.deepcopy(case)
    for key in ("m27c_seed1", "m27c_seed2"):
        projection_drift[key]["documents"][0]["treatment_rows"] = 2
    projected = validation.treatment_projection_from_seed(
        projection_drift["m27c_seed1"]
    )
    projected_bytes = validation.canonical_json_bytes(projected)
    projection_drift["prereg"]["expected"]["projection"] = {
        "bytes": len(projected_bytes),
        "sha256": validation.sha256_bytes(projected_bytes),
    }
    assert _build(projection_drift)["failures"] == ["treatment_projection_drift"]

    monkeypatch.setattr(runner.row_validator, "_global_failures", lambda _rows: ["x"])
    assert _build(case)["failures"] == ["global_invariant_failure"]


def test_go_and_no_go_outputs_do_not_leak_canaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("M28_FAKE_SECRET", "ENV_SECRET_CANARY")
    case = _synthetic_case(tmp_path)
    go = _build(case)
    go_bytes = validation.canonical_json_bytes(go)
    for canary in (
        b"alpha",
        b"# Setup",
        str(tmp_path).encode("utf-8"),
        b"FAKE_SECRET_CANARY",
        b"ENV_SECRET_CANARY",
    ):
        assert canary not in go_bytes

    monkeypatch.setattr(
        runner,
        "build_candidate_payload",
        lambda *_a, **_k: (_ for _ in ()).throw(
            ValueError("FAKE_SECRET_CANARY alpha " + str(tmp_path))
        ),
    )
    no_go = runner.safe_build_candidate_payload(dependencies=case["dependencies"])
    no_go_bytes = validation.canonical_json_bytes(no_go)
    assert no_go["failures"] == ["internal_failure"]
    for canary in (
        b"FAKE_SECRET_CANARY",
        b"ENV_SECRET_CANARY",
        b"alpha",
        str(tmp_path).encode("utf-8"),
    ):
        assert canary not in no_go_bytes
    validation.validate_output_schema(no_go)


def test_output_schema_is_recursively_closed(tmp_path: Path):
    payload = _build(_synthetic_case(tmp_path))
    payload["generation"]["content"] = "forbidden"
    with pytest.raises(RuntimeError, match="schema drift"):
        validation.validate_output_schema(payload)


def test_output_schema_rejects_wrong_nested_types(tmp_path: Path):
    original = _build(_synthetic_case(tmp_path))
    payload = copy.deepcopy(original)
    payload["population"]["rows"] = True
    with pytest.raises(RuntimeError, match="population type drift"):
        validation.validate_output_schema(payload)
    payload = copy.deepcopy(original)
    payload["dependencies"]["runner_sha256"] = "not-a-hash"
    with pytest.raises(RuntimeError, match="dependency hash drift"):
        validation.validate_output_schema(payload)
    payload = copy.deepcopy(original)
    payload["schema_version"] = True
    with pytest.raises(RuntimeError, match="envelope drift"):
        validation.validate_output_schema(payload)
    payload = copy.deepcopy(original)
    payload["source"]["manifest_sha256"] = 7
    with pytest.raises(RuntimeError, match="source type drift"):
        validation.validate_output_schema(payload)


def _module_path(module: str) -> Path | None:
    base = ROOT.joinpath(*module.split("."))
    module_file = base.with_suffix(".py")
    package_file = base / "__init__.py"
    if module_file.is_file():
        return module_file
    if package_file.is_file():
        return package_file
    return None


def _resolved_imports(module: str, path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = set()
    package = module.split(".")[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - node.level + 1]
                target = ".".join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ""
            if target:
                result.add(target)
                for alias in node.names:
                    assert alias.name != "*"
                    candidate = f"{target}.{alias.name}"
                    if _module_path(candidate) is not None:
                        result.add(candidate)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in {"__import__", "eval", "exec"}
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"import_module", "exec_module"}
    return result


def _package_initializers(module: str) -> set[str]:
    parts = module.split(".")
    return {
        candidate
        for index in range(1, len(parts))
        if _module_path(candidate := ".".join(parts[:index])) is not None
    }


def _discover_local_import_closure() -> set[str]:
    pending = [
        "scripts.s117_m28_candidate_materialization",
        "scripts.s117_m28_candidate_validation",
    ]
    reached = set()
    allowed_external = set(sys.stdlib_module_names) | {"yaml"}
    while pending:
        module = pending.pop()
        if module in reached:
            continue
        path = _module_path(module)
        assert path is not None, module
        reached.add(module)
        pending.extend(_package_initializers(module) - reached)
        for imported in _resolved_imports(module, path):
            local_path = _module_path(imported)
            if local_path is not None:
                pending.append(imported)
                continue
            root = imported.split(".")[0]
            if (ROOT / root).is_dir():
                assert imported in {"scripts"}, imported
                continue
            assert root in allowed_external, imported
    return reached


def test_recursive_local_import_closure_is_allowlisted_and_safe():
    assert (ROOT / "src/__init__.py").is_file()
    assert (ROOT / "src/reingest/__init__.py").is_file()
    reached = _discover_local_import_closure()
    assert reached == set(LOCAL_CLOSURE)
    for module in reached:
        path = LOCAL_CLOSURE[module]
        imports = _resolved_imports(module, path)
        for name in imports:
            assert not name.startswith(FORBIDDEN_IMPORT_PREFIXES)
        source = path.read_text(encoding="utf-8")
        if module in {
            "scripts.s117_m28_candidate_validation",
            "scripts.s117_m28_candidate_materialization",
        }:
            assert "NOISE_CHARS" not in source
        assert "os.environ" not in source
        assert "os.getenv" not in source
    assert reached <= ALLOWED_LOCAL_MODULES


def test_clean_interpreter_loads_no_forbidden_project_or_provider_namespaces():
    code = f"""
import json, sys
sys.path.insert(0, {str(ROOT)!r})
import scripts.s117_m28_candidate_materialization
import scripts.s117_m28_candidate_validation
forbidden = {list(RUNTIME_FORBIDDEN_IMPORT_PREFIXES)!r}
def blocked(name, prefix):
    return name.startswith(prefix) if prefix.endswith('_') else name == prefix or name.startswith(prefix + '.')
loaded = sorted(name for name in sys.modules if any(blocked(name, p) for p in forbidden))
print(json.dumps(loaded))
"""
    env = {
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for key in ("SYSTEMROOT", "WINDIR"):
        if key in os.environ:
            env[key] = os.environ[key]
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == []


def test_socket_tripwire_blocks_and_restores():
    original_socket = runner.socket.socket
    original = runner.socket.create_connection
    with pytest.raises(ValueError, match="arbitrary"):
        with runner.block_external_connections():
            with pytest.raises(runner.ExternalCallBlocked):
                runner.socket.create_connection(("127.0.0.1", 9))
            with pytest.raises(runner.ExternalCallBlocked):
                runner.socket.socket()
            raise ValueError("arbitrary")
    assert runner.socket.socket is original_socket
    assert runner.socket.create_connection is original


def test_real_store_cli_interlock_rejects_before_any_store_read(tmp_path: Path):
    with pytest.raises(runner.CandidateFailure, match="contract_integrity"):
        runner._load_authorized(
            tmp_path / "not-the-frozen-prereg.yaml",
            tmp_path / "not-the-frozen-permit.yaml",
        )


def test_cli_interlock_does_not_reach_store_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    reached_store = False

    def forbidden_store_read(_store: Path):
        nonlocal reached_store
        reached_store = True
        raise AssertionError("store read reached")

    out = tmp_path / "interlock.json"
    monkeypatch.setattr(runner, "_selected_json_files", forbidden_store_read)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "s117_m28_candidate_materialization.py",
            "--source-workspace-root",
            str(tmp_path),
            "--seed",
            "1",
            "--prereg",
            str(tmp_path / "missing-prereg.yaml"),
            "--permit",
            str(tmp_path / "missing-permit.yaml"),
            "--out",
            str(out),
        ],
    )
    assert runner.main() == 1
    assert reached_store is False
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "NO_GO"


def test_contract_rejects_same_hash_under_wrong_selected_path(tmp_path: Path):
    contract = _synthetic_case(tmp_path)["prereg"]
    contract["frozen_inputs"]["runner"]["path"] = "copied/runner.py"
    with pytest.raises(runner.CandidateFailure, match="contract_integrity"):
        runner._validate_contract_shape(contract)


def test_store_file_selection_rejects_symlink_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case = _synthetic_case(tmp_path)
    extra = case["store"] / "unexpected.txt"
    extra.write_text("unexpected", encoding="utf-8")
    with pytest.raises(runner.CandidateFailure, match="source_drift"):
        runner._selected_json_files(case["store"])
    extra.unlink()
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self.suffix == ".json" or original(self),
    )
    with pytest.raises(runner.CandidateFailure, match="source_drift"):
        runner._selected_json_files(case["store"])


def test_selected_path_rejects_symlinked_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case = _synthetic_case(tmp_path)
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self.name == "extraction" or original(self),
    )
    with pytest.raises(runner.CandidateFailure, match="contract_integrity"):
        runner._under(tmp_path, runner.DEFAULT_STORE_RELATIVE)


def test_malformed_source_json_maps_to_source_drift(tmp_path: Path):
    path = tmp_path / f"{'a' * 64}.json"
    path.write_bytes(b'{"x":1e999}')
    with pytest.raises(runner.CandidateFailure, match="source_drift"):
        runner._strict_record(path)
