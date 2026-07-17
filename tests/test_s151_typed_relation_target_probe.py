from __future__ import annotations

from types import SimpleNamespace

from scripts.s151_typed_relation_target_probe import _batches, relation_covered_by_claims


def test_batches_are_bounded_and_lossless() -> None:
    chunks = [{"chunk_id": str(index), "content": "x" * 100} for index in range(10)]
    batches = _batches(chunks, max_chunks=3, max_chars=250)
    assert [row["chunk_id"] for batch in batches for row in batch] == [row["chunk_id"] for row in chunks]
    assert all(len(batch) <= 3 for batch in batches)
    assert all(sum(len(row["content"]) for row in batch) <= 250 or len(batch) == 1 for batch in batches)


def test_relation_coverage_uses_claim_and_quote_from_same_chunk() -> None:
    obligation = SimpleNamespace(candidate_id="a", required_anchors=("reset", "30 s"))
    claims = (
        SimpleNamespace(chunk_id="a", claim_text="Reset inhibit", exact_quote="Reset is inhibited."),
        SimpleNamespace(chunk_id="a", claim_text="Duration", exact_quote="The value is 30 s."),
    )
    assert relation_covered_by_claims(obligation, claims)
    assert not relation_covered_by_claims(obligation, claims[:1])
