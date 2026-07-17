from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.s203_run_kidde_visual_canary import (
    FABLE_MODEL,
    SOL_MODEL,
    all_pass,
    page_content_fable,
    page_content_openai,
    validate_candidate,
    validate_review,
    verify_prereg,
)


ROOT = Path(__file__).resolve().parents[1]


def stable_sha(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def test_s203_packet_is_pixel_bound_and_pre_model():
    packet = json.loads(
        (ROOT / "evals/s203_kidde_visual_canary_packet_v1.json").read_text(
            encoding="utf-8"
        )
    )
    body = dict(packet)
    expected_sha = body.pop("packet_sha256")
    assert stable_sha(body) == expected_sha
    assert packet["status"] == "FROZEN_BEFORE_FRONTIER_CALLS"
    assert packet["selection"]["model_outputs_seen"] == 0
    assert packet["selection"]["bot_outputs_seen"] == 0
    assert packet["selection"]["selected_source_overlap_with_existing_gold"] == []
    assert packet["selection"][
        "selected_source_sha_overlap_with_resolved_existing_gold"
    ] == []
    assert packet["selection"]["existing_kidde_gold_qids"] == [
        "ho001", "ho002", "ho003", "ho006", "ho009", "ho010", "ho014"
    ]
    assert len(packet["items"]) == 3
    assert len({row["stratum"] for row in packet["items"]}) == 3

    rendered = [
        page for item in packet["items"] for page in item["rendered_pages"]
    ]
    assert len(rendered) == 11
    for page in rendered:
        path = ROOT / page["image"]
        assert path.is_file()
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == page["image_sha256"]
        assert len(data) == page["image_bytes"]
        assert page["dpi"] == 200
        assert page["width_px"] > 1000
        assert page["height_px"] > 1000
        assert page["extracted_text"].strip()
    for item in packet["items"]:
        assert set(item["product_manuals"]) == set(
            item["discovered_product_manuals"]
        )


def test_s203_generation_contract_is_bounded_and_non_merging():
    packet = json.loads(
        (ROOT / "evals/s203_kidde_visual_canary_packet_v1.json").read_text(
            encoding="utf-8"
        )
    )
    contract = packet["generation_contract"]
    assert contract["principal"] == {
        "model": "gpt-5.6-sol", "reasoning_effort": "xhigh"
    }
    assert contract["independent"] == {"model": "claude-fable-5"}
    assert contract["pixel_only_frontier_input"] is True
    assert contract["independent_generation_before_cross_review"] is True
    assert contract["merge_candidates"] is False
    assert contract["same_item_retry"] is False
    verify_prereg(packet)


def _candidate(item):
    return {
        "canary_id": item["canary_id"],
        "adequacy": "SUFFICIENT",
        "question": "¿Cuál es la configuración aplicable?",
        "expected_behavior": "answer",
        "gold_answer": "La fuente establece dos condiciones exactas.",
        "atomic_facts": [
            {
                "fact_id": fact_id,
                "text": f"Hecho {fact_id}",
                "type": "core",
                "state": "present",
                "value": fact_id,
                "citation": {"pdf": item["source_pdf"], "page": item["focus_pages"][0]},
                "visual_evidence": f"fila {fact_id}",
            }
            for fact_id in ("F01", "F02")
        ],
        "notes": "",
    }


def test_s203_candidate_and_cross_review_fail_closed():
    packet = json.loads(
        (ROOT / "evals/s203_kidde_visual_canary_packet_v1.json").read_text(
            encoding="utf-8"
        )
    )
    item = packet["items"][0]
    openai_content = page_content_openai(item, "frozen prompt")
    fable_content = page_content_fable(item, "frozen prompt")
    openai_text = "\n".join(
        row["text"] for row in openai_content if row["type"] == "input_text"
    )
    fable_text = "\n".join(
        row["text"] for row in fable_content if row["type"] == "text"
    )
    assert "AUXILIARY EXTRACTED TEXT" not in openai_text
    assert "AUXILIARY EXTRACTED TEXT" not in fable_text
    assert item["rendered_pages"][0]["extracted_text"].strip() not in openai_text
    assert item["rendered_pages"][0]["extracted_text"].strip() not in fable_text

    candidate = _candidate(item)
    validate_candidate(candidate, item)
    context_only_page = next(page for page in item["pages"] if page not in item["focus_pages"])
    candidate["atomic_facts"][0]["citation"]["page"] = context_only_page
    with pytest.raises(ValueError, match="outside frozen span"):
        validate_candidate(candidate, item)

    candidates = [_candidate(row) for row in packet["items"]]
    review = {
        "reviewer_model": FABLE_MODEL,
        "candidate_author": SOL_MODEL,
        "reviews": [
            {
                "canary_id": candidate["canary_id"],
                "verdict": "PASS",
                "question_fully_answerable": True,
                "question_duplicate": False,
                "topic_aligned": True,
                "gold_complete": True,
                "counterpart_materially_agrees": True,
                "material_disagreements": [],
                "unsupported_answer_claims": [],
                "issues": [],
                "fact_verdicts": [
                    {"fact_id": fact["fact_id"], "supported": True,
                     "page_correct": True, "answer_entails": True, "notes": ""}
                    for fact in candidate["atomic_facts"]
                ],
            }
            for candidate in candidates
        ],
    }
    validate_review(review, FABLE_MODEL, SOL_MODEL, candidates)
    assert all_pass(review)
    review["reviews"][0]["fact_verdicts"][0]["supported"] = False
    assert not all_pass(review)
