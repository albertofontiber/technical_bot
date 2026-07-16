from __future__ import annotations

import copy
import json
import random

import pytest

from scripts import s117_m27_loss_accounted_alignment as audit
from src.reingest import chunk_provenance as provenance


def _block(
    text: str,
    page,
    *,
    kind: str = "paragraph",
    first: bool = True,
    last: bool = True,
) -> dict:
    return {
        "source_block_index": 0,
        "source_page_ordinal": 0,
        "kind": kind,
        "page": page,
        "page_type": type(page).__name__,
        "text": text,
        "text_sha256": audit._sha_bytes(text.encode("utf-8")),
        "lineage": [],
        "is_first_block_of_page_occurrence": first,
        "is_last_block_of_page_occurrence": last,
    }


def _row(
    content: str,
    start: int,
    end: int,
    *,
    index: int = 0,
) -> dict:
    return {
        "id": f"row-{index}",
        "chunk_index": index,
        "content": content,
        "source_block_start": start,
        "source_block_end": end,
        "provenance_payload_sha256": f"{index + 1:064x}",
    }


@pytest.mark.parametrize("page", [None, True, False, "24", 0, -1])
def test_page_rule_rejects_invalid_page_types_and_range(page):
    result = audit._rule_evaluation(_block(str(page), page), [])
    assert not result["authorized"]


def test_page_rule_rejects_leading_zero_and_non_exact_text():
    assert not audit._rule_evaluation(_block("024", 24), [])["authorized"]
    assert not audit._rule_evaluation(_block("24.0", 24), [])["authorized"]
    assert not audit._rule_evaluation(_block("24 V", 24), [])["authorized"]
    assert not audit._rule_evaluation(_block("1-2", 1), [])["authorized"]
    assert not audit._rule_evaluation(_block("24", 24, kind="heading"), [
    ])["authorized"]


def test_page_rule_requires_page_occurrence_boundary():
    result = audit._rule_evaluation(
        _block("24", 24, first=False, last=False), []
    )
    assert not result["authorized"]


def test_standalone_24_matches_but_is_not_semantic_noise_proof():
    result = audit._rule_evaluation(_block("24", 24), [])
    assert result["authorized"]
    assert result["residual_risk"] == "shape_match_not_semantic_noise_proof"


def test_rule_match_retained_is_not_authorized_exclusion():
    covering = [{"id": "row-0", "chunk_index": 0}]
    result = audit._rule_evaluation(_block("24", 24), covering)
    assert result["shape_match"]
    assert not result["authorized"]


def test_repeated_page_labels_keep_distinct_source_page_ordinals():
    record = {
        "result": {
            "pages": [
                {"page": 1, "md": "1\n\nalpha"},
                {"page": 1, "md": "1\n\nbeta"},
            ]
        }
    }
    rows = audit._blocks_with_page_ordinal(record)
    assert [row["source_page_ordinal"] for row in rows] == [0, 0, 1, 1]
    assert rows[0]["is_first_block_of_page_occurrence"]
    assert rows[1]["is_last_block_of_page_occurrence"]
    assert rows[2]["is_first_block_of_page_occurrence"]
    assert rows[3]["is_last_block_of_page_occurrence"]


def test_canonical_order_restores_boundaries_after_input_shuffle():
    record = {
        "result": {
            "pages": [
                {"page": 7, "md": "first\n\nsecond\n\nthird"},
            ]
        }
    }
    canonical = audit._blocks_with_page_ordinal(record)
    shuffled = list(reversed(canonical))
    restored = audit._canonicalize_blocks(shuffled)
    assert [row["source_block_index"] for row in restored] == [0, 1, 2]
    assert restored[0]["is_first_block_of_page_occurrence"]
    assert not restored[1]["is_first_block_of_page_occurrence"]
    assert restored[2]["is_last_block_of_page_occurrence"]


def test_document_entirely_excluded_is_no_go():
    record = {
        "result": {"pages": [{"page": 24, "md": "24"}]}
    }
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=json.dumps(record).encode("utf-8"),
        record=record,
        rows=[],
        rule_contract_sha256="a" * 64,
    )
    assert ledger[0]["disposition"] == "authorized_exclusion"
    assert document["loss_accounted_stream_equal"]
    assert not document["document_nonempty_after_exclusions"]
    assert document["status"] == "NO_GO"


def test_authorized_page_number_plus_retained_content_is_accounted():
    record = {
        "result": {"pages": [{"page": 24, "md": "24\n\n# Technical"}]}
    }
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=json.dumps(record).encode("utf-8"),
        record=record,
        rows=[_row("# Technical", 1, 1)],
        rule_contract_sha256="a" * 64,
    )
    assert [row["disposition"] for row in ledger] == [
        "authorized_exclusion",
        "covered_by_v3",
    ]
    assert document["document_nonempty_after_exclusions"]
    assert document["loss_accounted_stream_equal"]
    assert document["status"] == "GO"


def test_unruled_short_code_remains_loss_and_no_go():
    record = {"result": {"pages": [{"page": 1, "md": "E01"}]}}
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=json.dumps(record).encode("utf-8"),
        record=record,
        rows=[],
        rule_contract_sha256="a" * 64,
    )
    assert ledger[0]["disposition"] == "unruled_loss"
    assert document["status"] == "NO_GO"


def test_covered_page_number_stays_in_stream_and_is_diagnostic_only():
    record = {"result": {"pages": [{"page": 24, "md": "24"}]}}
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=json.dumps(record).encode("utf-8"),
        record=record,
        rows=[_row("24", 0, 0)],
        rule_contract_sha256="a" * 64,
    )
    assert ledger[0]["disposition"] == "covered_by_v3"
    assert ledger[0]["rule_matched_but_retained"]
    assert document["authorized_exclusion_block_indexes"] == []
    assert document["status"] == "GO"


def test_span_coverage_cannot_hide_partial_text_loss():
    record = {
        "result": {"pages": [{"page": 1, "md": "technical value 24 V"}]}
    }
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=json.dumps(record).encode("utf-8"),
        record=record,
        rows=[_row("technical value", 0, 0)],
        rule_contract_sha256="a" * 64,
    )
    assert ledger[0]["disposition"] == "covered_by_v3"
    assert not document["loss_accounted_stream_equal"]
    assert document["first_accounted_mismatch"] is not None
    assert document["status"] == "NO_GO"


@pytest.mark.parametrize(
    "content",
    ["beta\n\nalpha", "alpha\n\nalpha\n\nbeta"],
)
def test_multiblock_reorder_or_duplication_is_no_go(content):
    record = {"result": {"pages": [{"page": 1, "md": "alpha\n\nbeta"}]}}
    document, _ = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=json.dumps(record).encode("utf-8"),
        record=record,
        rows=[_row(content, 0, 1)],
        rule_contract_sha256="a" * 64,
    )
    assert not document["loss_accounted_stream_equal"]
    assert document["status"] == "NO_GO"


def test_oversized_shared_block_is_covered_and_stream_exact():
    record = {
        "sha256": "f" * 64,
        "result": {
            "pages": [{"page": 1, "md": "Sentence. " * 1200}],
        },
    }
    raw = json.dumps(record, sort_keys=True).encode("utf-8")
    rows = provenance.materialize_raw_record(
        raw,
        materialization_id="00000000-0000-0000-0000-000000000001",
        chunker_sha256="a" * 64,
    )
    assert len(rows) >= 2
    assert {(row["source_block_start"], row["source_block_end"]) for row in rows} == {
        (0, 0)
    }
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        rows=rows,
        rule_contract_sha256="a" * 64,
    )
    assert ledger[0]["disposition"] == "covered_by_v3"
    assert len(ledger[0]["covering_v3_chunks"]) == len(rows)
    assert document["loss_accounted_stream_equal"]
    assert audit._crosslinked(
        [document],
        ledger,
        expected_rule_contract_sha256="a" * 64,
        raw_by_sha={"f" * 64: raw},
        expected_rows_by_sha={"f" * 64: rows},
    )


def test_seeded_input_perturbation_preserves_document_bytes():
    record = {
        "result": {"pages": [{"page": 3, "md": "3\n\n# Heading\n\ncontent"}]}
    }
    raw = json.dumps(record, sort_keys=True).encode("utf-8")
    rows = [_row("# Heading\n\ncontent", 1, 2)]
    first = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        rows=rows,
        rule_contract_sha256="a" * 64,
        rng=random.Random(1),
    )
    second = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        rows=rows,
        rule_contract_sha256="a" * 64,
        rng=random.Random(2),
    )
    assert first == second


def test_crosslink_rejects_duplicate_document_identity():
    record = {"result": {"pages": [{"page": 1, "md": "content"}]}}
    raw = json.dumps(record).encode("utf-8")
    source_rows = [_row("content", 0, 0)]
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        rows=source_rows,
        rule_contract_sha256="a" * 64,
    )
    kwargs = {
        "expected_rule_contract_sha256": "a" * 64,
        "raw_by_sha": {"f" * 64: raw},
        "expected_rows_by_sha": {"f" * 64: source_rows},
    }
    assert audit._crosslinked([document], ledger, **kwargs)
    assert not audit._crosslinked([document, document], ledger, **kwargs)


def _rebind_document(document: dict, *, ledger=None, v3_rows=None) -> dict:
    core = {
        key: value for key, value in document.items() if key != "receipt_sha256"
    }
    if ledger is not None:
        core["block_ledger_manifest_sha256"] = audit._manifest(
            ledger, ("source_block_index",)
        )
    if v3_rows is not None:
        core["v3_rows"] = v3_rows
        core["v3_rows_manifest_sha256"] = audit._manifest(
            v3_rows, ("chunk_index",)
        )
    return audit._receipt(core)


def test_crosslink_reparses_raw_and_rejects_forged_lineage_and_page_ordinal():
    record = {"result": {"pages": [{"page": 1, "md": "content"}]}}
    raw = json.dumps(record).encode("utf-8")
    source_rows = [_row("content", 0, 0)]
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        rows=source_rows,
        rule_contract_sha256="a" * 64,
    )
    forged = copy.deepcopy(ledger)
    forged_core = {
        key: value for key, value in forged[0].items() if key != "receipt_sha256"
    }
    forged_core["lineage"] = [{"title": "forged"}]
    forged_core["source_page_ordinal"] = 99
    forged[0] = audit._receipt(forged_core)
    rebound = _rebind_document(document, ledger=forged)
    assert not audit._crosslinked(
        [rebound],
        forged,
        expected_rule_contract_sha256="a" * 64,
        raw_by_sha={"f" * 64: raw},
        expected_rows_by_sha={"f" * 64: source_rows},
    )


def test_crosslink_rejects_out_of_range_span_and_stale_content_hash():
    record = {"result": {"pages": [{"page": 1, "md": "alpha\n\nbeta"}]}}
    raw = json.dumps(record).encode("utf-8")
    source_rows = [_row("alpha\n\nbeta", 0, 1)]
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        rows=source_rows,
        rule_contract_sha256="a" * 64,
    )
    forged_v3 = copy.deepcopy(document["v3_rows"])
    row_core = {
        key: value for key, value in forged_v3[0].items() if key != "receipt_sha256"
    }
    row_core["source_block_end"] = 99
    row_core["content"] = "alpha  beta"
    forged_v3[0] = audit._receipt(row_core)
    rebound = _rebind_document(document, v3_rows=forged_v3)
    assert not audit._crosslinked(
        [rebound],
        ledger,
        expected_rule_contract_sha256="a" * 64,
        raw_by_sha={"f" * 64: raw},
        expected_rows_by_sha={"f" * 64: source_rows},
    )


def test_empty_raw_document_crosslinks_and_is_not_a_false_population_gap():
    record = {"result": {"pages": []}}
    raw = json.dumps(record).encode("utf-8")
    document, ledger = audit._document_audit(
        extraction_sha256="f" * 64,
        raw=raw,
        record=record,
        rows=[],
        rule_contract_sha256="a" * 64,
    )
    assert ledger == []
    assert document["status"] == "GO"
    assert audit._crosslinked(
        [document],
        ledger,
        expected_rule_contract_sha256="a" * 64,
        raw_by_sha={"f" * 64: raw},
        expected_rows_by_sha={"f" * 64: []},
    )


def test_population_closure_rejects_removed_or_duplicate_extraction():
    docs = [
        {"extraction_sha256": "a" * 64},
        {"extraction_sha256": "b" * 64},
    ]
    rows = [
        {"id": "1", "extraction_sha256": "a" * 64, "chunk_index": 0},
        {"id": "2", "extraction_sha256": "b" * 64, "chunk_index": 0},
    ]
    kwargs = {
        "expected_records": {"a" * 64, "b" * 64},
        "expected_documents": 2,
        "expected_v3_rows": 2,
        "all_rows": rows,
    }
    assert all(audit._population_checks(documents=docs, **kwargs).values())
    assert not all(
        audit._population_checks(documents=docs[:1], **kwargs).values()
    )
    assert not all(
        audit._population_checks(documents=[docs[0], docs[0]], **kwargs).values()
    )
