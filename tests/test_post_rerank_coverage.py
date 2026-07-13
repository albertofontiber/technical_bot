from copy import deepcopy

from src.rag.doc_scoped_hyq_coverage import LANE as HYQ_LANE
from src.rag.post_rerank_coverage import (
    append_validated_coverage,
    apply_post_rerank_coverage_with_trace,
    is_validated_coverage_chunk,
)
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE


def _candidate(row_id="coverage", *, lane=STRUCTURAL_LANE):
    content = "La resistencia máxima del lazo es 35 ohmios."
    start = content.index("resistencia")
    end = len(content) - 1
    row = {
        "id": row_id,
        "content": content,
        "source_file": "manual.pdf",
        "retrieval_lane": lane,
        "local_semantic_validated": True,
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "start": start,
                "end": end,
                "quote": content[start:end],
                "facet": "loop_resistance",
                "exact_source_span_validated": True,
            }
        ],
    }
    if lane == STRUCTURAL_LANE:
        row["structural_neighbor_validated"] = True
    else:
        row["hyq_navigation_validated"] = True
    return row


def test_master_off_is_bit_inert_and_does_not_call_lanes():
    reranked = [{"id": "base", "content": "base"}]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled lane was called")

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        enabled=False,
        structural_enabled=True,
        hyq_enabled=True,
        structural_collector=forbidden,
        hyq_collector=forbidden,
    )

    assert output is reranked
    assert trace["status"] == "disabled_or_not_applicable"


def test_append_preserves_prefix_and_attests_exact_real_source_span():
    reranked = [{"id": "base", "content": "base", "similarity": 0.9}]
    snapshot = deepcopy(reranked)

    output = append_validated_coverage(reranked, [_candidate()])

    assert reranked == snapshot
    assert output[:1] == snapshot
    assert output[0] is reranked[0]
    assert output[1]["coverage_validated"] is True
    assert output[1]["post_rerank_coverage_rank"] == 1
    assert is_validated_coverage_chunk(output[1]) is True


def test_rejects_tampered_span_unknown_lane_and_duplicate_parent():
    reranked = [{"id": "base", "content": "base"}]
    tampered = _candidate("tampered")
    tampered["coverage_cards"][0]["quote"] = "dato inventado"
    unknown = _candidate("unknown")
    unknown["retrieval_lane"] = "qid_specific_patch"
    duplicate = _candidate("base", lane=HYQ_LANE)

    assert append_validated_coverage(reranked, [tampered, unknown, duplicate]) is reranked


def test_generator_boundary_rejects_forged_attestation_without_lane_receipt():
    candidate = _candidate("forged", lane=HYQ_LANE)
    candidate.pop("hyq_navigation_validated")
    candidate.update({"coverage_validated": True, "post_rerank_coverage": True})

    assert is_validated_coverage_chunk(candidate) is False


def test_lane_failure_is_fail_open_and_other_lane_can_still_append():
    reranked = [{"id": "base", "content": "base"}]

    def broken(_query, _reranked):
        raise TimeoutError("bounded read timed out")

    def hyq(_query):
        return [_candidate("hyq", lane=HYQ_LANE)], {"lane": HYQ_LANE, "status": "selected"}

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        enabled=True,
        structural_enabled=True,
        hyq_enabled=True,
        structural_collector=broken,
        hyq_collector=hyq,
    )

    assert [row["id"] for row in output] == ["base", "hyq"]
    assert trace["protected_prefix_equal"] is True
    assert trace["model_calls"] == 0
    assert trace["database_writes"] == 0
    assert trace["lanes"][0]["status"] == "error"
