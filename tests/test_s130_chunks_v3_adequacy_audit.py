import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import yaml
import scripts.s130_chunks_v3_adequacy_audit as s130
import pytest

from scripts.s130_chunks_v3_adequacy_audit import (
    ROOT,
    _basename,
    _fixed_point,
    _row_index_s114,
    _surface_category,
)


def _canonical_text_sha(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_s130_prereg_has_portable_active_source_receipts():
    prereg = yaml.safe_load(
        (ROOT / "evals/s130_chunks_v3_adequacy_prereg_v2.yaml").read_text(
            encoding="utf-8"
        )
    )
    ci_contract = yaml.safe_load(
        (ROOT / "evals/s132_ci_evidence_contract_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert _canonical_text_sha(ROOT / prereg["design"]["path"]) == ci_contract[
        "portable_receipts"
    ]["s130_design_utf8_lf"]
    assert _canonical_text_sha(
        ROOT / prereg["frozen_inputs"]["chunker"]["path"]
    ) == ci_contract["portable_receipts"]["s130_chunker_utf8_lf"]
    assert prereg["cost_contract"] == {
        "model_calls": 0,
        "network_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "embeddings": 0,
    }
    assert not any(key.startswith("s116") for key in prereg["frozen_inputs"])
    assert prereg["decision_contract"]["s116_authority"] == "excluded_exploratory_only"


def test_s130_normalizes_windows_and_posix_pdf_identities():
    assert _basename(r"Manuales_Aritech\Manual ES.PDF") == "manual es"
    assert _basename("Manuales_Aritech/Manual ES.pdf") == "manual es"
    assert _basename("ÁREA/Ñandú.pdf") == "ñandú"


def test_s130_relation_closure_is_undirected_and_deterministic():
    graph = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}, "z": set()}
    assert _fixed_point({"a"}, graph) == {"a", "b", "c"}
    assert _fixed_point({"z"}, graph) == {"z"}


def test_s130_s114_row_index_includes_direct_and_candidate_rows():
    freeze = {
        "source_rows": {"direct": {"id": "direct", "content": "x"}},
        "candidate_scopes": {
            "scope": [
                {"id": "candidate", "content": "y"},
                {"id": "direct", "content": "must-not-overwrite"},
            ]
        },
    }
    rows = _row_index_s114(freeze)
    assert sorted(rows) == ["candidate", "direct"]
    assert rows["direct"]["content"] == "x"


def test_s130_s114_metadata_ledger_receipt_is_exact():
    prereg = yaml.safe_load(
        (ROOT / "evals/s130_chunks_v3_adequacy_prereg_v2.yaml").read_text(
            encoding="utf-8"
        )
    )
    freeze = json.loads(
        (ROOT / prereg["frozen_inputs"]["s114_freeze"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    ledger = s130._build_s114_metadata_ledger(
        freeze, prereg["phase0_embargo"]["expected"]
    )
    assert len(ledger["rows"]) == 1859
    assert len(ledger["ledger"]) == 36
    assert (
        ledger["ledger_sha256"]
        == "50e52bbb52288da94b31f57721223634f10afbf81b2f5d1198c9a556fc2b8e3f"
    )


def test_s130_s114_metadata_conflict_cannot_false_go():
    extraction = "a" * 64
    freeze = {
        "source_rows": {
            "one": {
                "id": "one",
                "extraction_sha256": extraction,
                "document_id": "doc-one",
                "source_file": "manual.pdf",
            }
        },
        "candidate_scopes": {
            "scope": [
                {
                    "id": "two",
                    "extraction_sha256": extraction,
                    "document_id": "doc-two",
                    "source_file": "manual.pdf",
                }
            ]
        },
    }
    with pytest.raises(RuntimeError, match="not reciprocal"):
        s130._build_s114_metadata_ledger(
            freeze,
            {
                "s114_metadata_rows": 2,
                "s114_ledger_entries": 1,
                "s114_ledger_sha256": "unreachable",
            },
        )


def test_s130_primary_absent_requires_repeated_binding_and_keeps_namespaces_separate():
    extraction = "b" * 64
    document = "doc"
    catalog = {
        "snapshot_documents": {
            document: {"source_pdf_sha256": "backfill:" + "c" * 64}
        },
        "snapshot_pair_counts": {(document, extraction): 3},
        "snapshot_doc_to_extractions": {document: {extraction}},
        "snapshot_extraction_to_docs": {extraction: {document}},
        "m25_receipts": {
            extraction: {
                "terminal": "primary_absent_pdf_sha",
                "document_id": None,
                "matching_document_count": 0,
            }
        },
        "docs": {},
    }
    metadata = {
        "by_extraction": {
            extraction: {
                "document_id": document,
                "source_basename": "manual",
                "occurrences": 2,
            }
        }
    }
    resolved, error = s130._resolve_direct_row(
        {
            "extraction_sha256": extraction,
            "document_id": document,
            "source_file": "manual.pdf",
        },
        raw_index={"records": {extraction: {"path": "raw"}}},
        catalog=catalog,
        metadata_ledger=metadata,
        require_metadata_ledger=True,
    )
    assert error is None
    assert resolved["extraction_sha256"] == extraction
    assert "source_pdf_sha256" not in resolved
    assert resolved["source_pdf_identity_status"] == "synthetic_backfill"
    metadata["by_extraction"][extraction]["occurrences"] = 1
    resolved, error = s130._resolve_direct_row(
        {
            "extraction_sha256": extraction,
            "document_id": document,
            "source_file": "manual.pdf",
        },
        raw_index={"records": {extraction: {"path": "raw"}}},
        catalog=catalog,
        metadata_ledger=metadata,
        require_metadata_ledger=True,
    )
    assert resolved is None
    assert error == "m25_absent_binding_not_corroborated"


def test_s130_surface_proxies_do_not_call_long_text_noise():
    assert _surface_category("___") == "symbol_only"
    assert _surface_category("123") == "short_numeric_only"
    assert _surface_category("ESP") == "very_short_token"
    assert _surface_category("Configuración del detector") is None


def test_s130_script_contains_no_network_database_or_model_client():
    source = (ROOT / "scripts/s130_chunks_v3_adequacy_audit.py").read_text(
        encoding="utf-8"
    )
    forbidden = ("requests.", "httpx.", "openai", "anthropic", "supabase", "psycopg")
    assert not any(token in source.casefold() for token in forbidden)
    assert json.loads('{"local": true}')["local"] is True


def _gate_fixture(rows: int, blocks: int, gains: int = 0) -> tuple[dict, dict]:
    m28 = {
        "status": "CANDIDATE_MATERIALIZATION_GO_STRUCTURAL_ONLY",
        "population": {
            "documents": 1,
            "rows": rows,
            "raw_blocks": blocks,
            "coverage_gain_blocks": gains,
            "coverage_regression_blocks": 0,
            "changed_documents": 0 if gains == 0 else 1,
            "delta_added_rows": 0,
            "delta_removed_rows": 0,
        },
    }
    m29 = {
        "status": "RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY",
        "population": {
            "documents": 1,
            "raw_blocks": blocks,
            "coverage_gain_blocks": gains,
            "coverage_regression_blocks": 0,
            "changed_fingerprint_multiset_documents": 0 if gains == 0 else 1,
        },
    }
    return m28, m29


def _patch_local_audit_inputs(monkeypatch, prereg: dict, m28: dict, m29: dict):
    def fake_yaml(path):
        name = Path(path).name
        if name == "prereg.yaml":
            return prereg
        if name == "m28.yaml":
            return m28
        if name == "m29.yaml":
            return m29
        if name == "m28-implementation.yaml":
            return {
                "status": "IMPLEMENTATION_GO_CANDIDATE_DESIGN_ONLY",
                "causal_result_carried_forward": {
                    "baseline_rows": m28["population"]["rows"],
                    "candidate_oracle_rows": m28["population"]["rows"],
                    "changed_documents": m28["population"]["changed_documents"],
                },
            }
        raise AssertionError(f"unexpected yaml read: {path}")

    monkeypatch.setattr(s130, "_yaml", fake_yaml)
    monkeypatch.setattr(s130, "_json", lambda _path: {"rows": []})
    monkeypatch.setattr(
        s130,
        "build_impact_map",
        lambda *_args, **_kwargs: {
            "status": "COMPLETE",
            "population": {},
            "claim_dispositions": {},
            "block_dispositions": {},
            "impact_gate": "no_kpi_shadow_signal",
            "facts_moved_to_ok": 0,
        },
    )


def test_s130_embargo_is_checked_before_json_parse_or_chunking(monkeypatch, tmp_path):
    extraction = "a" * 64
    (tmp_path / f"{extraction}.json").write_text("not-json", encoding="utf-8")
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text("test: true\n", encoding="utf-8")
    m28, m29 = _gate_fixture(0, 0)
    prereg = {
        "frozen_inputs": {
            "m28_gate": {"path": "m28.yaml", "sha256": "x"},
            "m29_gate": {"path": "m29.yaml", "sha256": "y"},
            "m28_implementation_gate": {"path": "m28-implementation.yaml", "sha256": "i"},
            "compact100": {"path": "compact.json", "sha256": "z"},
            "chunker": {"sha256": "chunker"},
        },
        "phase1_audit": {
            "expected_candidate_rows": 0,
            "expected_baseline_rows": 0,
            "expected_raw_blocks": 0,
            "expected_gain_blocks": 0,
            "expected_regression_blocks": 0,
            "max_examples_per_metric": 2,
        },
    }
    _patch_local_audit_inputs(monkeypatch, prereg, m28, m29)
    embargo = {
        "status": "GO",
        "closure": {"extraction_sha256s": [extraction]},
        "determinism": {"logical_payload_sha256": "embargo"},
    }
    payload = s130.audit_corpus(tmp_path, embargo, prereg_path)
    assert payload["population"]["eligible_documents"] == 0
    assert payload["population"]["embargoed_extractions"] == 1
    assert payload["integrity"]["embargo_go"] is True


def test_s130_changed_content_stream_cannot_false_go(monkeypatch, tmp_path):
    extraction = "b" * 64
    record = {
        "sha256": extraction,
        "source_path": "manual.pdf",
        "result": {"pages": [{"page": 1, "md": "# Heading\n\nBody text", "images": []}]},
    }
    (tmp_path / f"{extraction}.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text("test: true\n", encoding="utf-8")
    real_chunks = s130.chunk_module.chunk_document(record)
    real_blocks = s130.chunk_module._flatten(record["result"]["pages"])
    m28, m29 = _gate_fixture(len(real_chunks), len(real_blocks))
    prereg = {
        "frozen_inputs": {
            "m28_gate": {"path": "m28.yaml", "sha256": "x"},
            "m29_gate": {"path": "m29.yaml", "sha256": "y"},
            "m28_implementation_gate": {"path": "m28-implementation.yaml", "sha256": "i"},
            "compact100": {"path": "compact.json", "sha256": "z"},
            "chunker": {"sha256": "chunker"},
        },
        "phase1_audit": {
            "expected_candidate_rows": len(real_chunks),
            "expected_baseline_rows": len(real_chunks),
            "expected_raw_blocks": len(real_blocks),
            "expected_gain_blocks": 0,
            "expected_regression_blocks": 0,
            "max_examples_per_metric": 2,
        },
    }
    _patch_local_audit_inputs(monkeypatch, prereg, m28, m29)
    original = s130.chunk_module.chunk_document

    def corrupted(raw):
        chunks = original(raw)
        chunks[0].content += " DUPLICATED"
        return chunks

    monkeypatch.setattr(s130.chunk_module, "chunk_document", corrupted)
    embargo = {
        "status": "GO",
        "closure": {"extraction_sha256s": []},
        "determinism": {"logical_payload_sha256": "embargo"},
    }
    payload = s130.audit_corpus(tmp_path, embargo, prereg_path)
    assert payload["status"] == "NO_GO"
    assert payload["integrity"]["eligible_streams_exact"] is False
    assert payload["metrics"]["content_token_stream_mismatch"]["occurrences"] == 1


def test_s130_truth_table_never_authorizes_build_or_migration():
    complete = {"x": True}
    impact = {"status": "COMPLETE"}
    decision = s130._decide_axes(complete, {}, impact)
    assert decision["S"] == "v3_adequate"
    assert decision["P"] == "no_projection_design_signal"
    assert decision["v4_build_authorized"] is False
    assert decision["migration_authorized"] is False

    pending = {
        "risk": {"occurrences": 1, "semantic_judgment": "NOT_ADJUDICATED"}
    }
    decision = s130._decide_axes(complete, pending, impact)
    assert decision["S"] == decision["P"] == "inconclusive"


def test_s130_real_impact_map_resolves_both_legacy_and_m1_lanes():
    report = json.loads(
        (ROOT / "evals/s130_chunks_v3_adequacy_audit_v2.json").read_text(
            encoding="utf-8"
        )
    )
    impact = report["impact"]
    assert impact["population"]["claims_total"] == 157
    assert {row["lane"] for row in impact["claims"]} == {"legacy", "migrated_m1"}
    assert sum(row["binding_count"] > 0 for row in impact["claims"]) > 0
    assert impact["facts_moved_to_ok"] == 0
    cat008 = [row for row in impact["claims"] if row["qid"] == "cat008"]
    assert cat008
    assert {row["disposition"] for row in cat008} == {"binding_unresolved"}
    assert all(
        any(failure.startswith("unstructured_citations_") for failure in row["binding_failures"])
        for row in cat008
    )



def test_s130_gold_pdf_bindings_are_hermetic_and_fail_closed():
    extraction = "a" * 64
    catalog = {"by_basename": {"manual": {("doc", extraction)}}}
    gold = {
        "clean": {
            "pdfs_used": ["Manual.pdf"],
            "citations": [{"pdf": "Manual.pdf", "page": 2, "quote": "exact"}],
        },
        "mixed": {
            "pdfs_used": ["Manual.pdf"],
            "citations": ["legacy citation", {"pdf": "Manual.pdf", "page": 3}],
        },
    }
    bindings, failures = s130._gold_pdf_bindings("clean", gold, catalog)
    assert failures == []
    assert bindings == [
        {
            "source_basename": "manual",
            "extraction_sha256": extraction,
            "document_id": "doc",
            "pages": [2],
            "quotes": ["exact"],
        }
    ]
    _, failures = s130._gold_pdf_bindings("mixed", gold, catalog)
    assert "unstructured_citations_1" in failures


def test_s130_m1_document_multibinding_is_a_collision():
    extraction_a = "a" * 64
    extraction_b = "b" * 64
    catalog = {
        "snapshot_doc_to_extractions": {"doc": {extraction_a, extraction_b}},
        "snapshot_extraction_to_docs": {
            extraction_a: {"doc"},
            extraction_b: {"doc"},
        },
    }
    extraction, error = s130._unique_reciprocal_snapshot_extraction(
        "doc", catalog
    )
    assert extraction is None
    assert error == "binding_collision_2"
    catalog["snapshot_extraction_to_docs"][extraction_b] = {"different-doc"}
    extraction, error = s130._unique_reciprocal_snapshot_extraction(
        "doc", catalog
    )
    assert extraction is None
    assert error == "binding_collision_2"


def test_s130_pdf_manual_citation_disagreement_fails_closed():
    identity, error = s130._citation_document_identity(
        {"pdf": "one.pdf", "manual": "two.pdf"}
    )
    assert identity is None
    assert error == "citation_pdf_manual_disagreement"


def test_s130_runner_excludes_s116_and_uses_versioned_identity_ledgers():
    source = (ROOT / "scripts/s130_chunks_v3_adequacy_audit.py").read_text(
        encoding="utf-8"
    )
    for token in (
        'snapshot_pair_counts',
        '_build_s114_metadata_ledger',
        'products',
        'docrel',
        'doc_graph',
        'build_impact_map',
        'content_token_stream_mismatch',
    ):
        assert token in source
    assert 's116_status' not in source
    assert 's116_replay' not in source
    assert '"source_pdf_sha256": extraction' not in source


@pytest.mark.parametrize(
    ("start", "end"),
    [(-1, 0), (1, 0), (0, 99)],
)
def test_s130_invalid_spans_cannot_false_go(monkeypatch, tmp_path, start, end):
    extraction = "c" * 64
    record = {
        "sha256": extraction,
        "source_path": "span.pdf",
        "result": {"pages": [{"page": 1, "md": "# H\n\nBody", "images": []}]},
    }
    (tmp_path / f"{extraction}.json").write_text(json.dumps(record), encoding="utf-8")
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text("test: true\n", encoding="utf-8")
    real_chunks = s130.chunk_module.chunk_document(record)
    real_blocks = s130.chunk_module._flatten(record["result"]["pages"])
    m28, m29 = _gate_fixture(len(real_chunks), len(real_blocks))
    prereg = {
        "frozen_inputs": {
            "m28_gate": {"path": "m28.yaml", "sha256": "x"},
            "m29_gate": {"path": "m29.yaml", "sha256": "y"},
            "m28_implementation_gate": {"path": "m28-implementation.yaml", "sha256": "i"},
            "compact100": {"path": "compact.json", "sha256": "z"},
            "chunker": {"sha256": "chunker"},
        },
        "phase1_audit": {
            "expected_candidate_rows": len(real_chunks),
            "expected_baseline_rows": len(real_chunks),
            "expected_raw_blocks": len(real_blocks),
            "expected_gain_blocks": 0,
            "expected_regression_blocks": 0,
            "max_examples_per_metric": 2,
        },
    }
    _patch_local_audit_inputs(monkeypatch, prereg, m28, m29)
    original = s130.chunk_module.chunk_document

    def invalid(raw):
        chunks = original(raw)
        chunks[0].source_block_start = start
        chunks[0].source_block_end = end
        return chunks

    monkeypatch.setattr(s130.chunk_module, "chunk_document", invalid)
    embargo = {
        "status": "GO",
        "closure": {"extraction_sha256s": []},
        "determinism": {"logical_payload_sha256": "embargo"},
    }
    payload = s130.audit_corpus(tmp_path, embargo, prereg_path)
    assert payload["status"] == "NO_GO"
    assert payload["integrity"]["zero_invalid_source_spans"] is False


def test_s130_valid_but_swapped_spans_cannot_false_go(monkeypatch, tmp_path):
    extraction = "d" * 64
    pages = [
        {"page": 1, "md": "Alpha paragraph", "images": []},
        {"page": 2, "md": "Beta paragraph", "images": []},
    ]
    record = {
        "sha256": extraction,
        "source_path": "swapped.pdf",
        "result": {"pages": pages},
    }
    (tmp_path / f"{extraction}.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    blocks = s130.chunk_module._flatten(pages)
    assert len(blocks) == 2
    chunks = [
        s130.chunk_module.Chunk(
            content=blocks[0].text,
            section_title=None,
            section_path=None,
            page_number=1,
            chunk_index=0,
            source_block_start=1,
            source_block_end=1,
        ),
        s130.chunk_module.Chunk(
            content=blocks[1].text,
            section_title=None,
            section_path=None,
            page_number=2,
            chunk_index=1,
            source_block_start=0,
            source_block_end=0,
        ),
    ]
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text("test: true\n", encoding="utf-8")
    m28, m29 = _gate_fixture(2, 2)
    prereg = {
        "frozen_inputs": {
            "m28_gate": {"path": "m28.yaml", "sha256": "x"},
            "m29_gate": {"path": "m29.yaml", "sha256": "y"},
            "m28_implementation_gate": {
                "path": "m28-implementation.yaml",
                "sha256": "i",
            },
            "compact100": {"path": "compact.json", "sha256": "z"},
            "chunker": {"sha256": "chunker"},
        },
        "phase1_audit": {
            "expected_candidate_rows": 2,
            "expected_baseline_rows": 2,
            "expected_raw_blocks": 2,
            "expected_gain_blocks": 0,
            "expected_regression_blocks": 0,
            "max_examples_per_metric": 2,
        },
    }
    _patch_local_audit_inputs(monkeypatch, prereg, m28, m29)
    monkeypatch.setattr(s130.chunk_module, "chunk_document", lambda _raw: chunks)
    payload = s130.audit_corpus(
        tmp_path,
        {
            "status": "GO",
            "closure": {"extraction_sha256s": []},
            "determinism": {"logical_payload_sha256": "embargo"},
        },
        prereg_path,
    )
    assert payload["status"] == "NO_GO"
    assert payload["integrity"]["eligible_streams_exact"] is True
    assert payload["integrity"]["zero_invalid_source_spans"] is True
    assert payload["integrity"]["zero_chunk_span_token_mismatches"] is False
    assert payload["metrics"]["chunk_span_token_mismatch"]["occurrences"] == 2


def test_s130_one_shot_permit_blocks_output_bypass_and_reuse(monkeypatch, tmp_path):
    monkeypatch.setattr(s130, "ROOT", tmp_path)
    receipts = {
        "consumption_receipt_output": "evals/consumed.json",
        "embargo_output": "evals/embargo.json",
        "audit_output": "evals/audit.json",
    }
    with pytest.raises(RuntimeError, match="differs"):
        s130._consume_execution_permit(
            receipts,
            embargo_out=tmp_path / "evals/other.json",
            audit_out=tmp_path / "evals/audit.json",
        )
    assert not (tmp_path / "evals/consumed.json").exists()
    s130._consume_execution_permit(
        receipts,
        embargo_out=tmp_path / "evals/embargo.json",
        audit_out=tmp_path / "evals/audit.json",
    )
    assert (tmp_path / "evals/consumed.json").exists()
    with pytest.raises(FileExistsError):
        s130._consume_execution_permit(
            receipts,
            embargo_out=tmp_path / "evals/embargo.json",
            audit_out=tmp_path / "evals/audit.json",
        )


def test_s130_endpoint_guard_fails_closed():
    with pytest.raises(RuntimeError, match="endpoint missing"):
        s130._require_endpoints("a", "missing", {"a"}, "product")


def test_s130_m28_m29_accounting_drift_cannot_go(monkeypatch, tmp_path):
    extraction = "e" * 64
    record = {
        "sha256": extraction,
        "source_path": "accounting.pdf",
        "result": {"pages": [{"page": 1, "md": "Body", "images": []}]},
    }
    (tmp_path / f"{extraction}.json").write_text(json.dumps(record), encoding="utf-8")
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text("test: true\n", encoding="utf-8")
    chunks = s130.chunk_module.chunk_document(record)
    blocks = s130.chunk_module._flatten(record["result"]["pages"])
    m28, m29 = _gate_fixture(len(chunks), len(blocks))
    m29["population"]["coverage_gain_blocks"] = 1
    prereg = {
        "frozen_inputs": {
            "m28_gate": {"path": "m28.yaml", "sha256": "x"},
            "m29_gate": {"path": "m29.yaml", "sha256": "y"},
            "m28_implementation_gate": {"path": "m28-implementation.yaml", "sha256": "i"},
            "compact100": {"path": "compact.json", "sha256": "z"},
            "chunker": {"sha256": "chunker"},
        },
        "phase1_audit": {
            "expected_candidate_rows": len(chunks),
            "expected_baseline_rows": len(chunks),
            "expected_raw_blocks": len(blocks),
            "expected_gain_blocks": 0,
            "expected_regression_blocks": 0,
            "max_examples_per_metric": 2,
        },
    }
    _patch_local_audit_inputs(monkeypatch, prereg, m28, m29)
    embargo = {
        "status": "GO",
        "closure": {"extraction_sha256s": []},
        "determinism": {"logical_payload_sha256": "embargo"},
    }
    payload = s130.audit_corpus(tmp_path, embargo, prereg_path)
    assert payload["status"] == "NO_GO"
    assert payload["integrity"]["gained_blocks_exact"] is False


def test_s130_visual_screenshot_only_uses_all_row_pages(monkeypatch, tmp_path):
    extraction = "f" * 64
    pages = [
        {
            "page": 1,
            "md": "First page",
            "images": [{"name": "page_1.jpg", "type": "full_page_screenshot"}],
        },
        {"page": 2, "md": "Second page", "images": [{"name": "diagram.png"}]},
    ]
    record = {"sha256": extraction, "source_path": "visual.pdf", "result": {"pages": pages}}
    (tmp_path / f"{extraction}.json").write_text(json.dumps(record), encoding="utf-8")
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text("test: true\n", encoding="utf-8")
    blocks = s130.chunk_module._flatten(pages)
    content = "\n\n".join(block.text for block in blocks)
    combined = s130.chunk_module.Chunk(
        content=content,
        section_title=None,
        section_path=None,
        page_number=1,
        chunk_index=0,
        source_block_start=0,
        source_block_end=len(blocks) - 1,
        has_diagram=True,
    )
    m28, m29 = _gate_fixture(1, len(blocks))
    prereg = {
        "frozen_inputs": {
            "m28_gate": {"path": "m28.yaml", "sha256": "x"},
            "m29_gate": {"path": "m29.yaml", "sha256": "y"},
            "m28_implementation_gate": {"path": "m28-implementation.yaml", "sha256": "i"},
            "compact100": {"path": "compact.json", "sha256": "z"},
            "chunker": {"sha256": "chunker"},
        },
        "phase1_audit": {
            "expected_candidate_rows": 1,
            "expected_baseline_rows": 1,
            "expected_raw_blocks": len(blocks),
            "expected_gain_blocks": 0,
            "expected_regression_blocks": 0,
            "max_examples_per_metric": 2,
        },
    }
    _patch_local_audit_inputs(monkeypatch, prereg, m28, m29)
    monkeypatch.setattr(s130.chunk_module, "chunk_document", lambda _raw: [combined])
    embargo = {
        "status": "GO",
        "closure": {"extraction_sha256s": []},
        "determinism": {"logical_payload_sha256": "embargo"},
    }
    payload = s130.audit_corpus(tmp_path, embargo, prereg_path)
    assert "visual_metadata_screenshot_only" not in payload["metrics"]
