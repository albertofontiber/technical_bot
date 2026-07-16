from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import psycopg2
import pytest

from scripts import s117_m2_legacy_reuse_analysis as audit


def _metadata() -> dict[str, object]:
    return {
        "language": "es",
        "source_file": "manual",
        "product_model": "MODEL-1",
        "manufacturer": "Vendor",
        "distributor": None,
        "protocol": None,
        "doc_type": "usuario",
        "category": None,
        "content_type": "general",
    }


def _local(sha: str = "a" * 64, preterminal: str | None = None) -> dict:
    return {
        "id": f"local-{sha[0]}",
        "extraction_sha256": sha,
        "chunk_index": 0,
        "content": "Exact technical content",
        "section_title": "Setup",
        "section_path": "Setup",
        "page_number": 1,
        "is_flow_diagram": False,
        "has_diagram": False,
        "confidence_f32": audit._f32_hex(0.9),
        "preterminal": preterminal,
        "context_input_sha256": "c" * 64,
        "context_input_chars": 100,
        "context_document_chars": 60,
        "context_instruction_chars": 40,
        **_metadata(),
    }


def _doc(sha: str = "a" * 64, status: str = "active") -> dict:
    return {
        "kind": "document",
        "id": f"doc-{sha[0]}",
        "source_pdf_sha256": sha,
        "status": status,
    }


def _donor(sha: str = "a" * 64, donor_id: str = "donor-1") -> dict:
    return {
        "kind": "chunk",
        "id": donor_id,
        "document_id": f"doc-{sha[0]}",
        "extraction_sha256": sha,
        "chunk_index": 0,
        "content": "Exact technical content",
        "context": "Context for the exact product and section.",
        "section_title": "Setup",
        "section_path": "Setup",
        "page_number": 1,
        "is_flow_diagram": False,
        "has_diagram": False,
        "confidence_f32": audit._f32_hex(0.9),
        "parent_id": None,
        "duplicate_of": None,
        "embedding_present": True,
        "embedding_dimensions": 1024,
        **_metadata(),
    }


def _analyze(tmp_path: Path, local: dict, docs: list[dict], donors: list[dict]) -> dict:
    snapshot = tmp_path / "snapshot.jsonl.gz"
    audit._write_snapshot_lines(
        snapshot,
        {
            "schema": "s117_m2_remote_snapshot_v1",
            "transaction_read_only": "on",
            "transaction_isolation": "repeatable read",
            "server_version_num": "170000",
            "vector_payloads": 0,
        },
        docs,
        donors,
    )
    return audit.analyze_snapshot(
        snapshot,
        [local],
        {
            "rows": 1,
            "documents": 1,
            "portal_source_paths": 0,
            "resolved_portal_source_paths": 0,
            "missing_portal_source_paths": 0,
            "manifest_sha256": "m",
            "per_document_count_manifest_sha256": "p",
        },
    )


def test_sql_contract_is_read_only_and_never_selects_vector_payload() -> None:
    audit.assert_readonly_sql_contract()
    sql = audit.CHUNKS_SQL.casefold()
    assert "embedding::text" not in sql
    assert "vector_dims(embedding)" in sql
    assert "embedding is not null" in sql
    for verb in ("insert", "update", "delete", "merge", "alter", "drop", "create"):
        assert not __import__("re").search(rf"\b{verb}\b", sql)


def test_snapshot_is_canonical_deterministic_and_roundtrips(tmp_path: Path) -> None:
    first = tmp_path / "first.gz"
    second = tmp_path / "second.gz"
    header = {
        "schema": "s117_m2_remote_snapshot_v1",
        "transaction_read_only": "on",
        "transaction_isolation": "repeatable read",
        "server_version_num": "170000",
        "vector_payloads": 0,
    }
    first_receipt = audit._write_snapshot_lines(first, header, [_doc()], [_donor()])
    second_receipt = audit._write_snapshot_lines(second, header, [_doc()], [_donor()])
    assert first.read_bytes() == second.read_bytes()
    assert first_receipt == second_receipt
    read_header, documents, chunks, receipt = audit.read_snapshot(first)
    assert read_header == header
    assert documents[0]["id"] == "doc-a"
    assert chunks[0]["id"] == "donor-1"
    assert receipt == first_receipt


@pytest.mark.parametrize(
    ("terminal", "setup"),
    [
        ("policy_excluded_register_only", "register_only"),
        ("policy_excluded_language", "language"),
        ("target_document_unresolved", "unresolved"),
        ("document_status_excluded", "retired"),
        ("no_extraction_donor", "no_donor"),
        ("content_miss", "content"),
        ("structure_miss", "structure"),
        ("metadata_miss", "metadata"),
        ("ambiguous_donor", "ambiguous"),
        ("unique_donor_context_missing", "context"),
        ("unique_donor_embedding_missing_or_wrong_dim", "embedding"),
        ("legacy_context_and_embedding_candidate", "candidate"),
    ],
)
def test_terminal_taxonomy_is_closed(
    tmp_path: Path,
    terminal: str,
    setup: str,
) -> None:
    preterminal = terminal if setup in {"register_only", "language"} else None
    local = _local(preterminal=preterminal)
    docs = [] if setup in {"register_only", "language", "unresolved"} else [_doc()]
    if setup == "retired":
        docs = [_doc(status="retired")]
    donors = [] if setup in {"register_only", "language", "unresolved", "retired", "no_donor"} else [_donor()]
    if setup == "content":
        donors[0]["content"] = "Different content"
    elif setup == "structure":
        donors[0]["section_path"] = "Other"
    elif setup == "metadata":
        donors[0]["manufacturer"] = "Other"
    elif setup == "ambiguous":
        donors.append(_donor(donor_id="donor-2"))
    elif setup == "context":
        donors[0]["context"] = None
    elif setup == "embedding":
        donors[0]["embedding_present"] = False
        donors[0]["embedding_dimensions"] = None
    result = _analyze(tmp_path, local, docs, donors)
    assert result["status"] == "GO"
    assert result["terminals"][terminal] == 1
    assert sum(result["terminals"].values()) == 1
    assert result["checks"]["terminal_taxonomy_closed"] is True
    assert result["checks"]["funnel_monotonic"] is True


def test_donor_document_drift_is_diagnostic_not_reuse_blocker(tmp_path: Path) -> None:
    donor = _donor()
    donor["document_id"] = None
    result = _analyze(tmp_path, _local(), [_doc()], [donor])
    assert result["terminals"]["legacy_context_and_embedding_candidate"] == 1
    assert result["diagnostics"]["donor_document_binding_drift"] == 1


def test_workload_excludes_reused_context_and_bounds_generated_context() -> None:
    reused = _local("a" * 64)
    generated = _local("b" * 64)
    context_reuse = {reused["id"]: {"context": "Legacy context"}}
    result = audit._workload([reused, generated], context_reuse, {reused["id"]})
    assert result["context_calls"] == 1
    assert result["embedding_calls"] == 1
    assert result["embedding_rows_with_generated_context"] == 1
    assert result["embedding_input_chars_lower_bound_when_context_generated"] == len(
        generated["content"]
    )
    assert result["embedding_input_chars_upper_bound_when_context_generated"] == 16000
    assert result["currency_estimate"] is None


def test_register_only_uses_structural_layer_without_productive_rechunk_or_b1_b5(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    raw_path = tmp_path / ("a" * 64 + ".json")
    raw_path.write_text(
        json.dumps({"sha256": "a" * 64, "source_path": "manual.pdf", "result": {}}),
        encoding="utf-8",
    )
    result_path = tmp_path / "s117.json"
    result_path.write_text(
        json.dumps({"generation": {"materialization_id": "00000000-0000-0000-0000-000000000000"}}),
        encoding="utf-8",
    )
    def profile(_record: dict) -> SimpleNamespace:
        calls.append("profile")
        return SimpleNamespace(verdict="register_only", dominant="fr")

    def materialize(*_args: object, **_kwargs: object) -> list[dict]:
        calls.append("materialize")
        return [{
            "id": "row",
            "extraction_sha256": "a" * 64,
            "chunk_index": 0,
            "content": "Technical body",
            "section_title": None,
            "section_path": None,
            "page_number": 1,
            "is_flow_diagram": False,
            "has_diagram": False,
            "confidence": 0.9,
        }]

    monkeypatch.setattr(audit.language, "profile_document", profile)
    monkeypatch.setattr(audit.provenance, "materialize_raw_record", materialize)
    monkeypatch.setattr(
        audit.chunk_module,
        "chunk_document",
        lambda _record: (_ for _ in ()).throw(
            AssertionError("register_only must not be productively re-chunked")
        ),
    )
    monkeypatch.setattr(audit.sidecar, "is_portal_channel", lambda _path: False)
    monkeypatch.setattr(
        audit.language,
        "detect_language",
        lambda _content: (_ for _ in ()).throw(AssertionError("B1 must not run")),
    )
    monkeypatch.setattr(
        audit.metadata,
        "detect_document_metadata",
        lambda *_args: (_ for _ in ()).throw(AssertionError("B5 must not run")),
    )
    rows, receipt = audit.build_local_population([raw_path], result_path, "b" * 64)
    assert calls == ["materialize", "profile"]
    assert rows[0]["preterminal"] == "policy_excluded_register_only"
    assert receipt["rows"] == 1


def test_v24_prereg_inherits_frozen_contract_and_seals_sidecars() -> None:
    prereg = audit._load_prereg(audit.DEFAULT_PREREG)
    assert prereg["runtime"] == {
        "python": "3.14.3",
        "lingua-language-detector": "2.2.0",
        "psycopg2-binary": "2.9.11",
        "PyYAML": "6.0.3",
    }
    assert prereg["design"]["clarification"].endswith(
        "s117_m2_legacy_reuse_design_v22.md"
    )
    assert prereg["design"]["sidecar_clarification"].endswith(
        "s117_m2_legacy_reuse_design_v23.md"
    )
    assert prereg["design"]["authoritative_binding"].endswith(
        "s117_m2_legacy_reuse_design_v24.md"
    )
    assert prereg["frozen_inputs"]["raw_store"]["expected_portal_source_paths"] == 95
    assert prereg["frozen_inputs"]["portal_sidecars"]["expected_resolved_portal_paths"] == 95
    assert prereg["policy_pipeline"]["structural_layer"] == (
        "rematerialize_all_s117_rows_once"
    )
    assert prereg["policy_pipeline"]["productive_projection_register_only"] == (
        "classify_existing_structural_rows_without_second_chunk_or_B1_or_B5"
    )
    assert prereg["policy_pipeline"]["productive_projection_indexable"] == (
        "profile_then_chunk_alignment_then_language_and_B5"
    )
    assert prereg["policy_pipeline"]["exact_order"][0] == "profile_document"


def test_portal_sidecars_are_hash_sealed_and_binding_is_restored(tmp_path: Path) -> None:
    relative = Path("Manuales_Kidde/_metadata.json")
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    raw = b'[{"local_filename":"manual.pdf","equipo":"MODEL-1"}]'
    path.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    manifest = hashlib.sha256(
        f"{relative.as_posix()}\0{len(raw)}\0{sha}\n".encode("utf-8")
    ).hexdigest()
    contract = {
        "files": [{
            "path": relative.as_posix(),
            "bytes": len(raw),
            "entries": 1,
            "sha256": sha,
        }],
        "manifest_sha256": manifest,
    }
    assert audit._verify_portal_sidecars(tmp_path, contract) == {
        "files": 1,
        "entries": 1,
        "manifest_sha256": manifest,
    }

    original_root = audit.sidecar._ROOT
    with audit._bound_sidecar_root(tmp_path):
        assert audit.sidecar.lookup("Manuales_Kidde/manual.pdf")["equipo"] == "MODEL-1"
    assert audit.sidecar._ROOT == original_root

    path.write_bytes(raw + b"\n")
    with pytest.raises(RuntimeError, match="portal sidecar drift"):
        audit._verify_portal_sidecars(tmp_path, contract)


def test_absolute_portal_path_cannot_bypass_sealed_root_with_decoy(
    tmp_path: Path,
) -> None:
    sealed_root = tmp_path / "sealed"
    decoy_root = tmp_path / "decoy"
    for root, model in ((sealed_root, "SEALED"), (decoy_root, "DECOY")):
        folder = root / "Manuales_Kidde"
        folder.mkdir(parents=True)
        (folder / "_metadata.json").write_text(
            json.dumps([{"local_filename": "manual.pdf", "equipo": model}]),
            encoding="utf-8",
        )

    absolute_source = str(decoy_root / "Manuales_Kidde" / "manual.pdf")
    with audit._bound_sidecar_root(sealed_root):
        assert audit.sidecar.lookup(absolute_source)["equipo"] == "DECOY"
        with pytest.raises(RuntimeError, match="non-canonical portal source_path"):
            audit._canonical_portal_source_path(absolute_source)
        assert audit._canonical_portal_source_path(
            "Manuales_Kidde/manual.pdf"
        ) == "Manuales_Kidde/manual.pdf"


@pytest.mark.parametrize(
    "source_path",
    [
        "./Manuales_Kidde/manual.pdf",
        "Manuales_Kidde/./manual.pdf",
        "Manuales_Kidde//manual.pdf",
        "../Manuales_Kidde/manual.pdf",
        "Manuales_Kidde/../manual.pdf",
        "prefix/Manuales_Kidde/manual.pdf",
    ],
)
def test_malformed_portal_paths_fail_before_pathlib_normalization(
    source_path: str,
) -> None:
    with pytest.raises(RuntimeError, match="non-canonical portal source_path"):
        audit._canonical_portal_source_path(source_path)


class _FakeCursor:
    def __init__(self, connection: "_FakeConnection", name: str | None):
        self.connection = connection
        self.name = name
        self.itersize = 0
        self._rows: list[tuple] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, sql: str, _params: object = None) -> None:
        self.connection.executed.append(sql)
        if self.name == "s117_m2_documents":
            self._rows = [("doc-a", "a" * 64, "active")]
        elif self.name == "s117_m2_chunks":
            row = _donor()
            self._rows = [tuple(
                0.9 if column == "confidence" else row.get(column)
                for column in audit.CHUNK_COLUMNS
            )]

    def fetchone(self) -> tuple[str, str, str]:
        return ("on", "repeatable read", "170000")

    def __iter__(self):
        return iter(self._rows)


class _FakeConnection:
    def __init__(self):
        self.executed: list[str] = []
        self.session: dict | None = None
        self.rollback_count = 0
        self.closed = False

    def set_session(self, **kwargs: object) -> None:
        self.session = kwargs

    def cursor(self, name: str | None = None) -> _FakeCursor:
        return _FakeCursor(self, name)

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        raise AssertionError("M2 must never commit")


def test_capture_proves_read_only_and_always_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _FakeConnection()
    monkeypatch.setattr(psycopg2, "connect", lambda *_args, **_kwargs: connection)
    receipt = audit.capture_remote_snapshot(
        "postgresql://redacted",
        tmp_path / "snapshot.gz",
        {"remote_contract": {
            "statement_timeout_ms": 120000,
            "lock_timeout_ms": 2000,
            "cursor_batch_rows": 500,
        }},
    )
    assert connection.session == {
        "isolation_level": "REPEATABLE READ",
        "readonly": True,
        "autocommit": False,
    }
    assert connection.rollback_count == 1
    assert connection.closed is True
    assert receipt["rollback_completed_before_analysis"] is True
    assert receipt["database_writes"] == 0
    assert receipt["vector_payloads"] == 0
    assert all(sql.lstrip().upper().startswith(("SELECT", "SET")) for sql in connection.executed)


def test_analyzer_has_no_frozen_manufacturer_or_document_branches() -> None:
    text = Path(audit.__file__).read_text(encoding="utf-8").casefold()
    for forbidden in ("hochiki", "bosch", "siemens", "apollo", "0d175dd3", "b4926f04"):
        assert forbidden not in text


def _seeded_prereg() -> dict:
    return {
        "seeded_replay_gate": {"database_access": "forbidden"},
        "frozen_inputs": {"remote_snapshot": {
            "path": "tmp/s117_m2/remote_snapshot_v1.jsonl.gz",
            "sha256": "g" * 64,
            "canonical_jsonl_sha256": "c" * 64,
        }},
    }


def test_seeded_replay_cli_fails_closed_before_capture_or_credentials() -> None:
    expected = audit.ROOT / "tmp/s117_m2/remote_snapshot_v1.jsonl.gz"
    valid = SimpleNamespace(replay=True, env_file=None, snapshot=expected)
    audit._assert_seeded_replay_cli(_seeded_prereg(), valid)

    with pytest.raises(RuntimeError, match="replay-only"):
        audit._assert_seeded_replay_cli(
            _seeded_prereg(),
            SimpleNamespace(replay=False, env_file=None, snapshot=expected),
        )
    with pytest.raises(RuntimeError, match="forbids --env-file"):
        audit._assert_seeded_replay_cli(
            _seeded_prereg(),
            SimpleNamespace(replay=True, env_file=Path(".env"), snapshot=expected),
        )
    with pytest.raises(RuntimeError, match="snapshot path mismatch"):
        audit._assert_seeded_replay_cli(
            _seeded_prereg(),
            SimpleNamespace(
                replay=True,
                env_file=None,
                snapshot=audit.ROOT / "tmp/s117_m2/other.gz",
            ),
        )


@pytest.mark.parametrize(
    "receipt",
    [
        {"gzip_sha256": "x" * 64, "canonical_jsonl_sha256": "c" * 64},
        {"gzip_sha256": "g" * 64, "canonical_jsonl_sha256": "x" * 64},
    ],
)
def test_seeded_replay_checks_the_snapshot_actually_consumed(receipt: dict) -> None:
    with pytest.raises(RuntimeError, match="consumed snapshot receipt drift"):
        audit._assert_consumed_snapshot(_seeded_prereg(), receipt)
    audit._assert_consumed_snapshot(
        _seeded_prereg(),
        {"gzip_sha256": "g" * 64, "canonical_jsonl_sha256": "c" * 64},
    )
