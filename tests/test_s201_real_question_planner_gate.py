from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s201_build_real_question_planner_packet import build_packet
from scripts.s201_real_question_planner_gate import (
    chunks_v3_lane,
    frozen_conflicts,
    frozen_obligations,
    score_selection,
    target_has_minimum_gain,
    validate_gold,
    validate_gold_validator,
    verified_units,
)
from src.rag.decomposed_evidence_planner import compile_append, validate_plan


ROOT = Path(__file__).resolve().parents[1]

# Commit that sealed evals/s201_target_evaluation_packet_v1.json ("eval:
# freeze S201 real-question planner gate", PR #134 merge; the packet records
# no commit id). The packet can no longer be rebuilt from the live tree —
# src/rag/answer_planner.py legitimately evolved — so reproducibility is
# anchored to the sealed blobs instead (DEC-147: version, do not relax).
TARGET_PACKET_SEAL_COMMIT = "6f301deba3a4682aeebd9f8468ba6df4fb5bab1c"


def _sealed_bytes(relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{TARGET_PACKET_SEAL_COMMIT}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, f"sealed blob missing: {relative}"
    return completed.stdout


def test_frozen_packet_is_reproducible_real_question_holdout():
    frozen = json.loads(
        open(
            "evals/s201_real_question_planner_packet_v1.json", encoding="utf-8"
        ).read()
    )
    assert build_packet() == frozen
    selection = frozen["selection"]
    assert frozen["status"] == "SEALED_PREEXISTING_REAL_QUESTION_HOLDOUT"
    assert selection["items"] == 12
    assert selection["manufacturers"] == 8
    assert selection["unique_normalized_products"] == 12
    assert selection["eligible_answer_points"] == 43
    assert selection["baseline_reaching_generation_points"] == 37
    assert selection["target_question_overlap"] == 0
    assert selection["default_off_candidate_question_overlap"] == 0
    assert (
        selection["question_selection_uses_answer_class_or_pipeline_outcome"]
        is False
    )
    assert selection["question_selection_uses_planner_output"] is False
    assert selection["source_table"] == "chunks_v2"
    assert selection["chunks_v3_used"] is False
    assert frozen["gold_claims_present"] is False
    assert [row["qid"] for row in frozen["items"]] == [
        "cat012",
        "cat019",
        "hp007",
        "cat010",
        "hp013",
        "cat005",
        "cat021",
        "hp010",
        "hp003",
        "hp008",
        "cat011",
        "hp006",
    ]


def test_packet_units_reconstruct_from_frozen_source_spans():
    frozen = json.loads(
        open(
            "evals/s201_real_question_planner_packet_v1.json", encoding="utf-8"
        ).read()
    )
    for item in frozen["items"]:
        units, source_by_candidate = verified_units(item)
        assert units
        assert len({unit.unit_id for unit in units}) == len(units)
        for source in item["evidence_sources"]:
            assert source["content_sha256"] == hashlib.sha256(
                source["content"].encode("utf-8")
            ).hexdigest()
            assert source["candidate_id"] in source_by_candidate


def test_target_evaluator_packet_is_reproducible_and_self_contained():
    """DEC-147: rebuilding the packet from the live tree would report the
    legitimate post-seal evolution of src/rag/answer_planner.py as drift, so
    the packet is validated as sealed instead: unchanged since
    TARGET_PACKET_SEAL_COMMIT, internally consistent with its own
    packet_sha256 seal, and with every frozen input matching its sealed
    blob."""
    frozen = json.loads(
        open("evals/s201_target_evaluation_packet_v1.json", encoding="utf-8").read()
    )
    tree_bytes = (
        (ROOT / "evals/s201_target_evaluation_packet_v1.json")
        .read_bytes()
        .replace(b"\r\n", b"\n")
    )
    sealed_bytes = _sealed_bytes(
        "evals/s201_target_evaluation_packet_v1.json"
    ).replace(b"\r\n", b"\n")
    assert tree_bytes == sealed_bytes
    body = {key: value for key, value in frozen.items() if key != "packet_sha256"}
    assert frozen["packet_sha256"] == stable_sha(body)
    for relative, expected in frozen["inputs"].items():
        assert (
            hashlib.sha256(
                _sealed_bytes(relative).replace(b"\r\n", b"\n")
            ).hexdigest()
            == expected
        ), relative
    assert frozen["status"] == "SEALED_TARGET_EVALUATOR_INPUTS"
    assert frozen["population"]["qids"] == ["cat018", "hp002", "hp011", "hp017"]
    assert frozen["population"]["obligations"] == 20
    assert frozen["database_reads"] == frozen["database_writes"] == 0
    for item in frozen["items"]:
        assert frozen_obligations(item)
        assert isinstance(frozen_conflicts(item), list)
        assert item["base_answer"]


def test_validate_gold_preserves_frozen_point_order_and_fails_closed():
    value = {
        "qid": "q1",
        "points": [
            {"point_id": "p2", "supported": True, "support_unit_ids": ["u2"]},
            {"point_id": "p1", "supported": True, "support_unit_ids": ["u1"]},
        ],
    }
    assert [row["point_id"] for row in validate_gold(
        value, "q1", ["p1", "p2"], {"u1", "u2"}
    )] == ["p1", "p2"]
    value["points"][0]["support_unit_ids"] = ["unknown"]
    with pytest.raises(ValueError):
        validate_gold(value, "q1", ["p1", "p2"], {"u1", "u2"})


def test_dual_gold_accepts_alternative_sets_but_requires_author_set_on_agreement():
    author = [
        {
            "point_id": "p1",
            "supported": True,
            "support_unit_ids": ["u1"],
        }
    ]
    value = {
        "qid": "q1",
        "points": [
            {
                "point_id": "p1",
                "agrees_with_author": True,
                "support_unit_sets": [["u1"], ["u2"]],
            }
        ],
    }
    validated = validate_gold_validator(value, "q1", author, {"u1", "u2"})
    assert validated[0]["support_unit_sets"] == [["u1"], ["u2"]]
    value["points"][0]["support_unit_sets"] = [["u2"]]
    with pytest.raises(ValueError):
        validate_gold_validator(value, "q1", author, {"u1", "u2"})


def test_generic_planner_and_compiler_are_exact_across_real_fragments():
    frozen = json.loads(
        open(
            "evals/s201_real_question_planner_packet_v1.json", encoding="utf-8"
        ).read()
    )
    units, _sources = verified_units(frozen["items"][0])
    selected_input = [units[0].unit_id, units[-1].unit_id]
    plan, selected = validate_plan(
        {
            "obligations": [
                {"label": "primera", "unit_ids": [selected_input[0]]},
                {"label": "segunda", "unit_ids": selected_input},
            ]
        },
        {unit.unit_id for unit in units},
    )
    assert [row["label"] for row in plan] == ["primera", "segunda"]
    assert selected == selected_input
    first, receipt = compile_append("Base.", units, selected)
    second, second_receipt = compile_append("Base.", units, selected)
    assert first == second
    assert receipt == second_receipt
    assert receipt["baseline_is_exact_prefix"]
    assert all(unit_id in first for unit_id in selected)


def test_scoring_requires_every_gold_unit_for_each_point():
    frozen = json.loads(
        open(
            "evals/s201_real_question_planner_packet_v1.json", encoding="utf-8"
        ).read()
    )
    units, sources = verified_units(frozen["items"][0])
    gold = {
        "points": [
            {
                "point_id": "p1",
                "supported": True,
                "support_unit_sets": [
                    [units[0].unit_id, units[-1].unit_id],
                    [units[1].unit_id],
                ],
            }
        ]
    }
    partial = score_selection(gold, units, sources, [units[0].unit_id])
    complete = score_selection(
        gold, units, sources, [units[0].unit_id, units[-1].unit_id]
    )
    assert partial["points_covered"] == 0
    assert complete["points_covered"] == 1
    assert complete["complete"]
    assert complete["compiler_exact"]
    assert complete["compiler_deterministic"]


def test_target_requires_at_least_one_new_residual_fact():
    assert target_has_minimum_gain(0) is False
    assert target_has_minimum_gain(1) is True


def test_chunks_v3_is_explicit_unchanged_no_go_lane():
    lane = chunks_v3_lane()
    assert lane["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert lane["baseline"]["chunks_v2_recall_at_10"] == "16/24"
    assert lane["baseline"]["chunks_v3_recall_at_10"] == "16/24"
    assert lane["baseline"]["chunks_v3_mrr"] < lane["baseline"]["chunks_v2_mrr"]
    assert lane["changed_by_s201"] is False
    assert lane["per_question_patching"] is False
