from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.s204_run_kidde_visual_canary import (
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


def _packet():
    return json.loads(
        (ROOT / "evals/s204_kidde_visual_canary_packet_v1.json").read_text(
            encoding="utf-8"
        )
    )


def _candidate(item):
    return {
        "canary_id": item["canary_id"],
        "adequacy": "SUFFICIENT",
        "question": "¿Qué condiciones técnicas exactas se aplican?",
        "expected_behavior": "answer",
        "gold_answer": "La fuente establece dos condiciones exactas.",
        "atomic_facts": [
            {
                "fact_id": fact_id,
                "text": f"Hecho {fact_id}",
                "type": "core",
                "state": "present",
                "value": fact_id,
                "citation": {
                    "pdf": item["source_pdf"],
                    "page": item["focus_pages"][0],
                },
                "visual_evidence": f"fila {fact_id}",
            }
            for fact_id in ("F01", "F02")
        ],
        "notes": "",
    }


def _review(candidates):
    return {
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
                "blocking_issues": [],
                "nonblocking_notes": [],
                "fact_verdicts": [
                    {
                        "fact_id": fact["fact_id"],
                        "supported": True,
                        "page_correct": True,
                        "answer_entails": True,
                        "notes": "",
                    }
                    for fact in candidate["atomic_facts"]
                ],
            }
            for candidate in candidates
        ],
    }


def test_s204_packet_is_fresh_pixel_bound_and_pre_model():
    packet = _packet()
    body = dict(packet)
    expected = body.pop("packet_sha256")
    actual = hashlib.sha256(
        json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    assert actual == expected
    assert packet["status"] == "FROZEN_BEFORE_FRONTIER_CALLS"
    assert packet["selection"]["model_outputs_seen"] == 0
    assert packet["selection"]["bot_outputs_seen"] == 0
    assert packet["selection"]["excluded_closed_cohort"] == "s203"
    assert packet["selection"]["selected_source_overlap_with_existing_gold"] == []
    assert packet["selection"][
        "selected_source_sha_overlap_with_resolved_existing_gold"
    ] == []
    assert packet["kidde_pdf_universe_count"] == 55
    assert len(packet["items"]) == 3
    assert len({item["stratum"] for item in packet["items"]}) == 3
    assert all("s203" not in item["source_pdf"] for item in packet["items"])

    pages = [page for item in packet["items"] for page in item["rendered_pages"]]
    assert len(pages) == 5
    for page in pages:
        assert "extracted_text" not in page
        data = (ROOT / page["image"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == page["image_sha256"]
        assert len(data) == page["image_bytes"]
        assert page["dpi"] == 200
        assert page["width_px"] > 1000 and page["height_px"] > 1000
    for item in packet["items"]:
        assert set(item["product_manuals"]) == set(item["discovered_product_manuals"])


def test_s204_payload_is_pixel_only_and_focus_citations_fail_closed():
    packet = _packet()
    item = packet["items"][0]
    openai_content = page_content_openai(ROOT, item, "frozen prompt")
    fable_content = page_content_fable(ROOT, item, "frozen prompt")
    assert any(row["type"] == "input_image" for row in openai_content)
    assert any(row["type"] == "image" for row in fable_content)
    text = "\n".join(
        row["text"]
        for row in openai_content
        if row["type"] == "input_text"
    )
    assert "AUXILIARY EXTRACTED TEXT" not in text

    candidate = _candidate(item)
    validate_candidate(candidate, item)
    candidate["atomic_facts"][0]["citation"]["page"] = 999
    with pytest.raises(ValueError, match="outside frozen focus span"):
        validate_candidate(candidate, item)


def test_s204_review_separates_blocking_findings_from_notes():
    candidates = [_candidate(item) for item in _packet()["items"]]
    review = _review(candidates)
    validate_review(review, FABLE_MODEL, SOL_MODEL, candidates)
    assert all_pass(review)
    assert not all_pass({"reviews": []})

    review["reviews"][0]["nonblocking_notes"] = ["Redacción mejorable, no material."]
    validate_review(review, FABLE_MODEL, SOL_MODEL, candidates)
    assert all_pass(review)

    review["reviews"][0]["blocking_issues"] = ["Una afirmación no está soportada."]
    with pytest.raises(ValueError, match="PASS verdict contradicts"):
        validate_review(review, FABLE_MODEL, SOL_MODEL, candidates)

    review["reviews"][0]["verdict"] = "FAIL"
    validate_review(review, FABLE_MODEL, SOL_MODEL, candidates)
    assert not all_pass(review)


def test_s204_generation_contract_and_prereg_are_frozen():
    packet = _packet()
    contract = packet["generation_contract"]
    assert contract["principal"] == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
    }
    assert contract["independent"] == {"model": "claude-fable-5"}
    assert contract["pixel_only_frontier_input"] is True
    assert contract["merge_candidates"] is False
    assert contract["same_item_retry"] is False
    assert contract["application_inference_without_explicit_pixel_support"] == (
        "forbidden"
    )
    assert contract["nonblocking_notes_invalidate_pass"] is False
    verify_prereg(packet)
