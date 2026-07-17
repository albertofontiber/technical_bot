from __future__ import annotations

import copy

import pytest

from scripts import s138_symmetric_semantic_mrr as audit


def packet() -> dict:
    return {
        "instrument": "test",
        "status": "FROZEN_BLIND_PACKET",
        "questions": [
            {
                "question_id": "q1",
                "question": "What is the value?",
                "manufacturer": "Maker",
                "product_model": "Model",
                "evidence_sets": [
                    {
                        "evidence_set_id": "S-A",
                        "evidence": [
                            {
                                "evidence_id": "E-A1",
                                "section_title": "Values",
                                "section_path": "Manual > Values",
                                "page_number": 1,
                                "source_content": "The value is 10 ohm.",
                            },
                            {
                                "evidence_id": "E-A2",
                                "section_title": "Other",
                                "section_path": "Manual > Other",
                                "page_number": 2,
                                "source_content": "Unrelated content.",
                            },
                        ],
                    },
                    {
                        "evidence_set_id": "S-B",
                        "evidence": [
                            {
                                "evidence_id": "E-B1",
                                "section_title": "Values",
                                "section_path": "Manual > Values",
                                "page_number": 3,
                                "source_content": "The value is 10 ohm.",
                            }
                        ],
                    },
                ],
            }
        ],
        "checks": {},
        "manifests": {"questions_sha256": "test"},
    }


def judgement() -> dict:
    return {
        "judgements": [
            {
                "question_id": "q1",
                "set_judgements": [
                    {
                        "evidence_set_id": "S-A",
                        "answerability": "COMPLETE",
                        "minimum_sufficient_evidence_ids": ["E-A1"],
                        "evidence_assessments": [
                            {
                                "evidence_id": "E-A1",
                                "relevance": "DIRECT",
                                "supported_claim": "The value is 10 ohm.",
                                "redundant_with": [],
                            },
                            {
                                "evidence_id": "E-A2",
                                "relevance": "IRRELEVANT",
                                "supported_claim": "",
                                "redundant_with": [],
                            },
                        ],
                        "confidence": "HIGH",
                        "rationale": "The first item directly answers the question.",
                    },
                    {
                        "evidence_set_id": "S-B",
                        "answerability": "COMPLETE",
                        "minimum_sufficient_evidence_ids": ["E-B1"],
                        "evidence_assessments": [
                            {
                                "evidence_id": "E-B1",
                                "relevance": "DIRECT",
                                "supported_claim": "The value is 10 ohm.",
                                "redundant_with": [],
                            }
                        ],
                        "confidence": "HIGH",
                        "rationale": "The item directly answers the question.",
                    },
                ],
            }
        ]
    }


def mapping() -> dict:
    return {
        "questions": [
            {
                "question_id": "q1",
                "evidence_sets": [
                    {
                        "evidence_set_id": "S-A",
                        "arm": "baseline_v2",
                        "evidence": [
                            {"evidence_id": "E-A1", "rank": 4},
                            {"evidence_id": "E-A2", "rank": 1},
                        ],
                    },
                    {
                        "evidence_set_id": "S-B",
                        "arm": "candidate_v3",
                        "evidence": [{"evidence_id": "E-B1", "rank": 2}],
                    },
                ],
            }
        ]
    }


def test_opaque_ids_are_stable_and_do_not_expose_arm() -> None:
    first = audit.opaque("seed", "q", "candidate_v3", prefix="S")
    assert first == audit.opaque("seed", "q", "candidate_v3", prefix="S")
    assert first.startswith("S-")
    assert "candidate" not in first


def test_blind_packet_rejects_hidden_retrieval_fields() -> None:
    audit.assert_blind(packet())
    leaked = copy.deepcopy(packet())
    leaked["questions"][0]["evidence_sets"][0]["evidence"][0]["rank"] = 1
    with pytest.raises(audit.S138Failure, match="leaks"):
        audit.assert_blind(leaked)


def test_judgement_validation_and_two_arm_semantic_rank_are_mechanical() -> None:
    value = judgement()
    audit.validate_judgement(value, packet())
    assert audit.semantic_ranks(value, mapping()) == {
        "q1": {"baseline_v2": 4, "candidate_v3": 2}
    }


def test_complete_requires_a_direct_minimum_set() -> None:
    invalid = judgement()
    invalid["judgements"][0]["set_judgements"][0][
        "minimum_sufficient_evidence_ids"
    ] = []
    with pytest.raises(audit.S138Failure, match="inconsistent complete set"):
        audit.validate_judgement(invalid, packet())


def test_worst_case_reserves_all_atomic_calls_and_arbitration() -> None:
    prereg = audit.base.load_yaml(audit.DEFAULT_PREREG)
    worst = audit.worst_case(prereg, 120_000, [50_000, 50_000, 50_000])
    assert 0 < worst < prereg["budget"]["internal_ceiling_usd"]


def test_hybrid_mrr_replaces_only_registered_fallback_rows() -> None:
    s135 = {
        "question_results": [
            {"question_id": "q1", "baseline_rank": 10, "candidate_rank": None},
            {"question_id": "q2", "baseline_rank": 2, "candidate_rank": 4},
        ]
    }
    baseline, candidate = audit.hybrid_mrr(
        s135,
        {"q1": {"baseline_v2": 4, "candidate_v3": 2}},
        {"q1"},
    )
    assert baseline == 0.375
    assert candidate == 0.375


def test_real_packets_are_byte_deterministic_when_built() -> None:
    prereg = audit.base.load_yaml(audit.DEFAULT_PREREG)
    first = audit.ROOT / prereg["execution"]["public_packet_seed1"]
    second = audit.ROOT / prereg["execution"]["public_packet_seed2"]
    private_first = audit.ROOT / prereg["execution"]["private_mapping_seed1"]
    private_second = audit.ROOT / prereg["execution"]["private_mapping_seed2"]
    if not all(path.exists() for path in (first, second, private_first, private_second)):
        return
    assert first.read_bytes() == second.read_bytes()
    assert private_first.read_bytes() == private_second.read_bytes()
    audit.assert_blind(audit.base.load_json(first))
