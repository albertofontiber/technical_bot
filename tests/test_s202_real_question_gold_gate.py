from __future__ import annotations

import copy
import json

import pytest

from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s202_build_real_question_gold_packet import build_packet
from scripts.s202_real_question_gold_gate import chunks_v3_lane, verified_units
from src.rag.source_unit_gold import (
    FORBIDDEN_PROVIDER_KEYS,
    POINT_SLOTS,
    SUPPORT_SLOTS,
    static_author_schema,
    validate_static_author_output,
    validate_static_author_schema,
    validate_validator_output,
)


def _point(*supports: str, supported: bool = True) -> dict[str, object]:
    padded = [*supports, *([""] * (SUPPORT_SLOTS - len(supports)))]
    return {
        "supported": supported,
        **{
            f"support_{index}": padded[index - 1]
            for index in range(1, SUPPORT_SLOTS + 1)
        },
    }


def _author_payload() -> dict[str, object]:
    return {
        "qid": "q1",
        "point_slots": {
            "point_1": _point("u1"),
            "point_2": _point(supported=False),
            **{
                f"point_{index}": _point(supported=False)
                for index in range(3, POINT_SLOTS + 1)
            },
        },
    }


def test_fresh_real_question_packet_is_reproducible_and_uncontaminated():
    frozen = json.loads(
        open("evals/s202_real_question_gold_packet_v1.json", encoding="utf-8").read()
    )
    assert build_packet() == frozen
    selection = frozen["selection"]
    assert frozen["status"] == "SEALED_FRESH_PREEXISTING_REAL_QUESTION_HOLDOUT"
    assert selection["eligible_questions"] == 16
    assert selection["items"] == 12
    assert selection["manufacturers"] == 5
    assert selection["unique_normalized_products"] == 12
    assert selection["eligible_answer_points"] == 43
    assert selection["s201_question_overlap"] == 0
    assert selection["target_question_overlap"] == 0
    assert selection["default_off_candidate_question_overlap"] == 0
    assert selection["question_selection_uses_answer_class_or_pipeline_outcome"] is False
    assert selection["question_selection_uses_planner_output"] is False
    assert selection["source_table"] == "chunks_v2"
    assert selection["chunks_v3_used"] is False
    assert [row["qid"] for row in frozen["items"]] == [
        "cat023",
        "cat020",
        "cat001",
        "cat022",
        "cat016",
        "cat017",
        "hp012",
        "hp005",
        "cat024",
        "hp014",
        "hp001",
        "hp015",
    ]


def test_s201_is_sealed_before_inference_and_forbids_same_cohort_retry():
    result = json.loads(
        open("evals/s201_real_question_planner_gate_v1.json", encoding="utf-8").read()
    )
    sealed = dict(result)
    observed_sha = sealed.pop("result_sha256")
    assert stable_sha(sealed) == observed_sha
    assert result["status"] == "HOLD_EXTERNAL_DEPENDENCY_INCOMPLETE"
    assert result["failure"]["completed_inference_calls"] == 0
    assert result["decision"]["same_cohort_retry"] is False
    assert result["decision"]["s201_cohort_closed"] is True
    assert result["cost"]["known_inference_cost_usd"] == 0


def test_fresh_packet_evidence_units_reconstruct_exactly():
    frozen = json.loads(
        open("evals/s202_real_question_gold_packet_v1.json", encoding="utf-8").read()
    )
    for item in frozen["items"]:
        units = verified_units(item)
        assert units
        assert len({unit.unit_id for unit in units}) == len(units)


def test_anthropic_transport_is_static_rectangular_and_source_independent():
    schema = static_author_schema()
    validate_static_author_schema(schema)
    serialized = json.dumps(schema, sort_keys=True)
    assert all(f'"{key}"' not in serialized for key in FORBIDDEN_PROVIDER_KEYS)
    assert '"type": "array"' not in serialized
    points = schema["properties"]["point_slots"]
    assert points["required"] == [f"point_{index}" for index in range(1, 7)]
    for point in points["properties"].values():
        assert point["required"] == [
            "supported",
            *[f"support_{index}" for index in range(1, 7)],
        ]


def test_static_author_output_binds_order_locally_and_fails_closed():
    payload = _author_payload()
    assert validate_static_author_output(
        payload,
        qid="q1",
        point_ids=["p1", "p2"],
        known_unit_ids={"u1", "u2"},
    ) == [
        {"point_id": "p1", "supported": True, "support_unit_ids": ["u1"]},
        {"point_id": "p2", "supported": False, "support_unit_ids": []},
    ]
    mutations = [
        lambda value: value["point_slots"]["point_1"].update(support_1="unknown"),
        lambda value: value["point_slots"]["point_1"].update(
            support_1="", support_2="u1"
        ),
        lambda value: value["point_slots"]["point_1"].update(
            support_1="u1", support_2="u1"
        ),
        lambda value: value["point_slots"]["point_3"].update(
            supported=True, support_1="u1"
        ),
    ]
    for mutate in mutations:
        invalid = copy.deepcopy(payload)
        mutate(invalid)
        with pytest.raises(ValueError):
            validate_static_author_output(
                invalid,
                qid="q1",
                point_ids=["p1", "p2"],
                known_unit_ids={"u1", "u2"},
            )


def test_independent_validator_can_supply_equivalent_support_sets():
    author = [
        {"point_id": "p1", "supported": True, "support_unit_ids": ["u1"]},
        {"point_id": "p2", "supported": False, "support_unit_ids": []},
    ]
    value = {
        "qid": "q1",
        "points": [
            {
                "point_id": "p1",
                "agrees_with_author": True,
                "support_unit_sets": [["u1"], ["u2"]],
            },
            {
                "point_id": "p2",
                "agrees_with_author": True,
                "support_unit_sets": [],
            },
        ],
    }
    clean = validate_validator_output(
        value,
        qid="q1",
        author_points=author,
        known_unit_ids={"u1", "u2"},
    )
    assert clean[0]["support_unit_sets"] == [["u1"], ["u2"]]
    value["points"][0]["support_unit_sets"] = [["u2"]]
    with pytest.raises(ValueError):
        validate_validator_output(
            value,
            qid="q1",
            author_points=author,
            known_unit_ids={"u1", "u2"},
        )


def test_exact_transport_preflight_passed_without_inference():
    result = json.loads(
        open("evals/s202_static_transport_preflight_v1.json", encoding="utf-8").read()
    )
    assert result["status"] == "PASS_PROVIDER_SCHEMA_COUNT_TOKENS"
    assert result["schema_sha256"]
    assert result["inference_calls"] == 0
    assert result["retries"] == 0
    assert result["cost_usd"] == 0


def test_chunks_v3_remains_explicit_and_unchanged():
    lane = chunks_v3_lane()
    assert lane["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert lane["baseline"]["chunks_v2_recall_at_10"] == "16/24"
    assert lane["baseline"]["chunks_v3_recall_at_10"] == "16/24"
    assert lane["baseline"]["chunks_v3_mrr"] < lane["baseline"]["chunks_v2_mrr"]
    assert lane["changed_by_s202"] is False
    assert lane["per_question_patching"] is False
