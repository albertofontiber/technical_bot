import json
from pathlib import Path

import pytest

import scripts.s197_build_fresh_source_packet as s197_builder
from scripts.s194_build_fresh_source_packet import PRIOR_PACKETS
from scripts.s195_build_fresh_source_packet import S194_PACKET
from scripts.s197_build_fresh_source_packet import (
    PRIOR_SOURCE_PACKETS,
    S195_PACKET,
    SEED,
)


def test_s197_uses_a_new_seed_and_excludes_s194_and_s195_packets():
    assert SEED == "s197-static-author-luna-fresh-v1"
    assert S194_PACKET not in PRIOR_PACKETS
    assert S195_PACKET not in PRIOR_PACKETS
    assert S194_PACKET in PRIOR_SOURCE_PACKETS
    assert S195_PACKET in PRIOR_SOURCE_PACKETS
    assert PRIOR_SOURCE_PACKETS[-2:] == (S194_PACKET, S195_PACKET)


def test_s197_packet_paths_are_versioned_and_distinct():
    assert S194_PACKET.name == "s194_fresh_source_packet_v1.json"
    assert S195_PACKET.name == "s195_fresh_source_packet_v1.json"
    assert all(isinstance(path, Path) for path in PRIOR_SOURCE_PACKETS)


def _receipt(rows, fingerprint):
    return {
        "table": "chunks_v2",
        "rows": len(rows),
        "get_requests": 3,
        "database_writes": 0,
        "snapshot_sha256": fingerprint,
    }


def test_s197_requires_two_identical_full_scan_fingerprints(tmp_path, monkeypatch):
    rows = [{"id": "1", "content": "stable"}]
    fingerprint = s197_builder.stable_sha(rows)
    scans = iter([(rows, _receipt(rows, fingerprint))] * 2)
    monkeypatch.setattr(s197_builder, "_read_chunks_v2", lambda *args, **kwargs: next(scans))
    observed, receipt = s197_builder.read_chunks_v2_stable(tmp_path / ".env")
    assert observed == rows
    assert receipt["consistency"] == "DOUBLE_IDENTICAL_FULL_SCAN"
    assert receipt["get_requests"] == 6
    assert receipt["scan_1"]["full_scan_sha256"] == receipt["scan_2"][
        "full_scan_sha256"
    ]
    assert "snapshot_sha256" not in receipt
    assert "snapshot_sha256" not in receipt["scan_1"]


def test_s197_rejects_equal_cardinality_with_content_drift(tmp_path, monkeypatch):
    first = [{"id": "1", "content": "before"}]
    second = [{"id": "1", "content": "after"}]
    scans = iter(
        [
            (first, _receipt(first, s197_builder.stable_sha(first))),
            (second, _receipt(second, s197_builder.stable_sha(second))),
        ]
    )
    monkeypatch.setattr(s197_builder, "_read_chunks_v2", lambda *args, **kwargs: next(scans))
    with pytest.raises(RuntimeError, match="double-scan fingerprint drift"):
        s197_builder.read_chunks_v2_stable(tmp_path / ".env")


def test_s197_requires_every_protected_target_uuid_to_resolve(tmp_path, monkeypatch):
    target_id = "11111111-1111-4111-8111-111111111111"
    target_file = tmp_path / "target.json"
    target_file.write_text(json.dumps({"chunk_id": target_id}), encoding="utf-8")
    monkeypatch.setattr(s197_builder, "TARGET_FILES", (target_file,))
    rows = [{"id": target_id, "document_id": "other"}]
    resolution = s197_builder.target_uuid_resolution(rows)
    assert resolution == [
        {
            "target_uuid": target_id,
            "status": "RESOLVED_AS_CHUNK",
            "chunk_rows": 1,
            "document_rows": 0,
            "resolved_rows": 1,
        }
    ]
    with pytest.raises(RuntimeError, match="protected target UUID unresolved"):
        s197_builder.target_uuid_resolution([])
