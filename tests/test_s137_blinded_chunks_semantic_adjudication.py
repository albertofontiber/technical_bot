from __future__ import annotations

from pathlib import Path

import pytest

from scripts import s137_blinded_chunks_semantic_adjudication as audit


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
                "evidence": [
                    {
                        "evidence_id": "E-A",
                        "section_title": "Values",
                        "section_path": "Manual > Values",
                        "page_number": 1,
                        "source_content": "The value is 10 ohm.",
                    },
                    {
                        "evidence_id": "E-B",
                        "section_title": "Other",
                        "section_path": "Manual > Other",
                        "page_number": 2,
                        "source_content": "Unrelated content.",
                    },
                ],
            }
        ],
        "checks": {},
        "manifests": {"questions_sha256": "test"},
    }


def judgement(*, minimum: list[str] | None = None, answerability: str = "COMPLETE") -> dict:
    return {
        "judgements": [
            {
                "question_id": "q1",
                "answerability": answerability,
                "minimum_sufficient_evidence_ids": ["E-A"] if minimum is None else minimum,
                "evidence_assessments": [
                    {
                        "evidence_id": "E-A",
                        "relevance": "DIRECT",
                        "supported_claim": "The value is 10 ohm.",
                        "redundant_with": [],
                    },
                    {
                        "evidence_id": "E-B",
                        "relevance": "IRRELEVANT",
                        "supported_claim": "",
                        "redundant_with": [],
                    },
                ],
                "confidence": "HIGH",
                "rationale": "The first item directly gives the requested value.",
            }
        ]
    }


def mapping(rank: int | None) -> dict:
    return {
        "questions": [
            {
                "question_id": "q1",
                "s136_baseline_rank": 1,
                "s136_candidate_rank": rank,
                "evidence": [
                    {"evidence_id": "E-A", "candidate_rank": rank},
                    {"evidence_id": "E-B", "candidate_rank": 2},
                ],
            }
        ]
    }


def test_blind_labels_are_stable_and_source_ids_are_not_recoverable() -> None:
    first = audit.blind_label("seed", "question", "candidate")
    second = audit.blind_label("seed", "question", "candidate")
    assert first == second
    assert first.startswith("E-")
    assert "candidate" not in first


def test_public_packet_rejects_hidden_retrieval_fields() -> None:
    audit.assert_public_packet_blind(packet())
    leaked = packet()
    leaked["questions"][0]["evidence"][0]["rank"] = 1
    with pytest.raises(audit.S137Failure, match="leaks"):
        audit.assert_public_packet_blind(leaked)


def test_judgement_validation_is_closed_and_terminal_rule_is_mechanical() -> None:
    valid = judgement()
    audit.validate_judgement(valid, packet())
    assert audit.terminal_decisions(valid, mapping(10)) == {"q1": audit.SUCCESS}
    assert audit.terminal_decisions(valid, mapping(11)) == {"q1": audit.FAILURE}
    assert audit.terminal_decisions(valid, mapping(None)) == {"q1": audit.FAILURE}

    incomplete = judgement(minimum=[], answerability="PARTIAL")
    audit.validate_judgement(incomplete, packet())
    assert audit.terminal_decisions(incomplete, mapping(1)) == {"q1": audit.FAILURE}


def test_complete_requires_consistent_minimum_set() -> None:
    invalid = judgement(minimum=[])
    with pytest.raises(audit.S137Failure, match="without minimum"):
        audit.validate_judgement(invalid, packet())
    invalid = judgement(minimum=["E-B"])
    with pytest.raises(audit.S137Failure, match="inconsistent"):
        audit.validate_judgement(invalid, packet())


def test_worst_case_reserves_optional_arbitration_below_internal_ceiling() -> None:
    prereg = audit.base.load_yaml(audit.DEFAULT_PREREG)
    worst = audit.worst_case_cost(prereg, 120_000, 120_000)
    assert worst < prereg["budget"]["stricter_s137_runtime_ceiling_usd"]
    assert worst > 0


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
    audit.assert_public_packet_blind(audit.base.load_json(first))

