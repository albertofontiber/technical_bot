from __future__ import annotations

import json
from pathlib import Path

from src.rag.visual_gold import stable_sha


ROOT = Path(__file__).resolve().parents[1]


def _json(name: str):
    return json.loads((ROOT / "evals" / name).read_text(encoding="utf-8"))


def test_s205_raw_go_is_closed_by_exact_same_source_hyq_contamination():
    raw = _json("s205_kidde_visual_canary_result_v1.json")
    diagnosis = _json("s205_kidde_visual_canary_diagnosis_v1.json")
    packet = _json("s205_kidde_visual_canary_packet_v1.json")
    gold = _json("s205_kidde_visual_gold_v1.json")

    assert raw["status"] == "GO_KIDDE_GOLD_CANARY"
    assert diagnosis["status"] == "CLOSED_NO_GO_VISUAL_GOLD"
    assert diagnosis["decision"]["official_fact_credit"] == 0
    assert diagnosis["decision"]["bot_evaluation_opened"] is False
    assert diagnosis["decision"]["postselect_two_clean_candidates"] is False
    assert all(row["split"] == "candidate_unintegrated" for row in gold["questions"])

    case = diagnosis["blocking_case"]
    source_stem = Path(case["selected_source_pdf"]).stem
    assert source_stem == case["existing_retriever_source_file"]
    coverage = {
        row["qid"]: row["question"] for row in packet["existing_gold_coverage"]
    }
    assert coverage[case["existing_retriever_question_qid"]] == case[
        "existing_retriever_question"
    ]

    body = dict(diagnosis)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
