from __future__ import annotations

from pathlib import Path

import pytest

import scripts.s198_build_fresh_source_packet as s198
from scripts.s198_build_fresh_source_packet import (
    PRIOR_SOURCE_PACKETS,
    PROSE_ITEMS,
    S197_PACKET,
    SEED,
    TABLE_ITEMS,
    eligible_inventory_counts,
)


def test_s198_seed_and_history_exclude_s194_s195_and_s197():
    assert SEED == "s198-point-first-scope-fresh-v1"
    assert (TABLE_ITEMS, PROSE_ITEMS) == (7, 5)
    assert s198.DEFAULT_OUT.name == "s198_fresh_source_packet_v2.json"
    assert S197_PACKET.name == "s197_fresh_source_packet_v1.json"
    assert PRIOR_SOURCE_PACKETS[-1] == S197_PACKET
    assert [path.name for path in PRIOR_SOURCE_PACKETS[-3:]] == [
        "s194_fresh_source_packet_v1.json",
        "s195_fresh_source_packet_v1.json",
        "s197_fresh_source_packet_v1.json",
    ]
    assert all(isinstance(path, Path) for path in PRIOR_SOURCE_PACKETS)


def _receipt(rows):
    return {
        "table": "chunks_v2",
        "rows": len(rows),
        "get_requests": 3,
        "database_writes": 0,
        "snapshot_sha256": s198.stable_sha(rows),
    }


def test_double_scan_requires_identical_full_rows(tmp_path, monkeypatch):
    rows = [{"id": "1", "content": "stable"}]
    scans = iter([(rows, _receipt(rows)), (rows, _receipt(rows))])
    monkeypatch.setattr(s198, "_read_chunks_v2", lambda *args, **kwargs: next(scans))
    observed, receipt = s198.read_chunks_v2_stable(tmp_path / ".env")
    assert observed == rows
    assert receipt["consistency"] == "DOUBLE_IDENTICAL_FULL_SCAN"
    assert receipt["get_requests"] == 6
    assert receipt["database_writes"] == 0
    assert receipt["scan_1"]["full_scan_sha256"] == receipt["scan_2"][
        "full_scan_sha256"
    ]


def test_double_scan_rejects_same_cardinality_with_content_drift(
    tmp_path, monkeypatch
):
    first = [{"id": "1", "content": "before"}]
    second = [{"id": "1", "content": "after"}]
    scans = iter([(first, _receipt(first)), (second, _receipt(second))])
    monkeypatch.setattr(s198, "_read_chunks_v2", lambda *args, **kwargs: next(scans))
    with pytest.raises(RuntimeError, match="double-scan fingerprint drift"):
        s198.read_chunks_v2_stable(tmp_path / ".env")


def test_inventory_counter_reports_exact_population_and_reserve_dimensions():
    rows = [
        {
            "document_id": "d1",
            "source_file": "A.pdf",
            "manufacturer": "Vendor A",
            "product_model": "M1",
            "stratum": "table",
        },
        {
            "document_id": "d1",
            "source_file": "A.pdf",
            "manufacturer": "Vendor A",
            "product_model": "M1",
            "stratum": "prose",
        },
        {
            "document_id": "d2",
            "source_file": "B.pdf",
            "manufacturer": "Vendor B",
            "product_model": "M2",
            "stratum": "prose",
        },
    ]
    assert eligible_inventory_counts(rows) == {
        "chunk_rows": 3,
        "documents": 2,
        "source_files": 2,
        "manufacturer_product_pairs": 2,
        "manufacturers": 2,
        "table_documents": 1,
        "prose_documents": 2,
        "table_manufacturers": 1,
        "prose_manufacturers": 2,
    }


def test_candidate_eligibility_receives_chunk_kind(tmp_path, monkeypatch):
    observed = []

    def eligible(row, active, excluded):
        observed.append(row.get("kind"))
        return False

    monkeypatch.setattr(s198, "_eligible", eligible)
    monkeypatch.setattr(s198, "_prior_contract", lambda paths: (set(), set(), set(), {}))
    monkeypatch.setattr(s198, "TARGET_FILES", ())
    s198.eligible_inventory(
        [
            {
                "id": "chunk-1",
                "document_id": "doc-1",
                "source_file": "source.pdf",
                "manufacturer": "Vendor",
                "product_model": "Model",
                "content": "Technical content long enough for the generic gate.",
            }
        ]
    )
    assert observed == ["chunk"]
