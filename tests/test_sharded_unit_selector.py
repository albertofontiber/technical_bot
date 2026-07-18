from __future__ import annotations

import json

import pytest

from scripts.s213_score_sharded_unit_selector import build_legacy_score_proxy
from src.rag.query_evidence_compiler import stable_sha
from src.rag.sharded_unit_selector import (
    MAX_COMPILED_IDS,
    ShardedEvidenceCandidate,
    build_sharded_candidates,
    compile_sharded_appendix,
    selector_payload,
    validate_selection,
    validate_verification,
)


def _candidate(evidence_id: str, *, start: int = 0):
    content = "manual evidence"
    return ShardedEvidenceCandidate(
        evidence_id=evidence_id,
        origin="test",
        unit_kind="contiguous",
        fragment_number=1,
        candidate_id="chunk-1",
        source_spans=((start, start + len(content)),),
        content=content,
        content_sha256="a" * 64,
    )


def test_builds_complete_source_bound_shards_without_a_parallel_fallback_lane():
    chunks = [
        {
            "id": "chunk-1",
            "content": (
                "Before maintenance, isolate the releasing circuit.\n\n"
                "The test window is 30 to 60 seconds."
            ),
        }
    ]
    shards = build_sharded_candidates("What must I isolate before maintenance?", chunks)
    assert len(shards) == 1
    assert shards[0]
    assert {row.origin for row in shards[0]} == {"deterministic_header_aware_unit"}
    for row in shards[0]:
        reconstructed = "\n\n".join(
            chunks[0]["content"][start:end] for start, end in row.source_spans
        )
        assert reconstructed == row.content


def test_selector_payload_exposes_only_local_units():
    candidates = [_candidate("E1"), _candidate("E2", start=20)]
    payload = json.loads(selector_payload("question", candidates))
    assert [row["evidence_id"] for row in payload["evidence_units"]] == ["E1", "E2"]
    assert "candidate_id" not in payload["evidence_units"][0]


def test_selection_allows_empty_but_rejects_duplicates_and_unknowns():
    candidates = [_candidate("E1"), _candidate("E2", start=20)]
    assert validate_selection({"evidence_ids": []}, candidates) == ()
    assert validate_selection({"evidence_ids": ["E2"]}, candidates) == ("E2",)
    with pytest.raises(ValueError, match="unknown"):
        validate_selection({"evidence_ids": ["NOPE"]}, candidates)


def test_verifier_contract_is_fail_closed():
    candidates = [_candidate("E1"), _candidate("E2", start=20)]
    assert validate_verification(
        {"status": "COMPLETE", "missing_facets": [], "additional_evidence_ids": []},
        candidates,
        ["E1"],
    ) == ("COMPLETE", (), ())
    assert validate_verification(
        {
            "status": "INCOMPLETE",
            "missing_facets": ["threshold"],
            "additional_evidence_ids": ["E2"],
        },
        candidates,
        ["E1"],
    ) == ("INCOMPLETE", ("threshold",), ("E2",))
    with pytest.raises(ValueError, match="must identify"):
        validate_verification(
            {"status": "INCOMPLETE", "missing_facets": [], "additional_evidence_ids": []},
            candidates,
            ["E1"],
        )


def test_compiler_emits_exact_span_receipts():
    candidates = [_candidate("E1"), _candidate("E2", start=20)]
    appendix, receipts = compile_sharded_appendix(candidates, ["E1", "E2"])
    assert "manual evidence" in appendix
    assert [row["source_start"] for row in receipts] == [0, 20]
    with pytest.raises(ValueError, match="unknown"):
        compile_sharded_appendix(candidates, ["NOPE"])


def test_compiler_enforces_global_id_bound():
    candidates = [_candidate(f"E{index}", start=index * 20) for index in range(MAX_COMPILED_IDS + 1)]
    with pytest.raises(ValueError, match="count"):
        compile_sharded_appendix(candidates, [row.evidence_id for row in candidates])


def test_compiler_rejects_duplicate_ids_instead_of_silently_repairing():
    candidates = [_candidate("E1")]
    with pytest.raises(ValueError, match="duplicate"):
        compile_sharded_appendix(candidates, ["E1", "E1"])


def test_legacy_score_proxy_changes_only_call_header_and_seal():
    body = {
        "schema": "s213_sharded_unit_selector_receipts_v1",
        "status": "COMPLETE",
        "calls": 260,
        "rows": [{"qid": "q1"}],
        "cost": {"estimated_usd": 1.0},
    }
    receipts = {**body, "result_sha256": stable_sha(body)}
    proxy = build_legacy_score_proxy(receipts)
    proxy_body = dict(proxy)
    proxy_seal = proxy_body.pop("result_sha256")
    assert proxy_seal == stable_sha(proxy_body)
    assert proxy_body == {**body, "calls": 202}
    assert receipts["calls"] == 260
