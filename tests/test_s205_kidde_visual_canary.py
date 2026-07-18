from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.s205_run_kidde_visual_canary import (
    FABLE_MODEL,
    SOL_MODEL,
    page_content_fable,
    page_content_openai,
    verify_prereg,
)


ROOT = Path(__file__).resolve().parents[1]


def _packet():
    return json.loads(
        (ROOT / "evals/s205_kidde_visual_canary_packet_v1.json").read_text(
            encoding="utf-8"
        )
    )


def test_s205_population_is_fresh_pixel_bound_and_geometry_precedes_selection():
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
    selection = packet["selection"]
    assert selection["geometry_frozen_in_prior_commit"] == "af6de65"
    assert selection["model_outputs_seen"] == 0
    assert selection["bot_outputs_seen"] == 0
    assert selection["excluded_closed_cohorts"] == ["s203", "s204"]
    assert selection["selected_source_overlap_with_existing_gold"] == []
    assert selection[
        "selected_source_sha_overlap_with_resolved_existing_gold"
    ] == []
    assert packet["kidde_pdf_universe_count"] == 55
    assert packet["existing_gold_question_count"] == 51
    assert packet["selected_source_hyq_question_count"] == 116
    assert packet["existing_gold_unresolved_source_refs"] == []
    assert len(packet["items"]) == 3
    assert len({item["stratum"] for item in packet["items"]}) == 3

    pages = [page for item in packet["items"] for page in item["rendered_pages"]]
    assert len(pages) == 3
    for page in pages:
        assert "extracted_text" not in page
        data = (ROOT / page["image"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == page["image_sha256"]
        assert len(data) == page["image_bytes"]
        assert page["dpi"] == 200
        assert page["width_px"] > 1000 and page["height_px"] > 1000
    for item in packet["items"]:
        assert set(item["product_manuals"]) == set(
            item["discovered_product_manuals"]
        )


def test_s205_payload_is_pixel_only_and_models_have_exact_roles():
    packet = _packet()
    item = packet["items"][0]
    openai_content = page_content_openai(ROOT, item, "frozen prompt")
    fable_content = page_content_fable(ROOT, item, "frozen prompt")
    assert any(row["type"] == "input_image" for row in openai_content)
    assert any(row["type"] == "image" for row in fable_content)
    text = "\n".join(
        row["text"] for row in openai_content if row["type"] == "input_text"
    )
    assert "AUXILIARY EXTRACTED TEXT" not in text

    contract = packet["generation_contract"]
    assert contract["principal"] == {
        "model": SOL_MODEL,
        "reasoning_effort": "xhigh",
    }
    assert contract["independent"] == {"model": FABLE_MODEL}
    assert contract["final_gold_author"] == SOL_MODEL
    assert contract["principal_publication_review"] == (
        "fable_must_pass_every_sol_candidate"
    )
    assert contract["counterpart_role"] == (
        "blind_material_disagreement_probe_not_publication_candidate"
    )
    assert contract["counterpart_gate"] == (
        "topic_aligned_and_zero_material_disagreement"
    )
    assert contract["merge_candidates"] is False
    assert contract["same_item_retry"] is False


def test_s205_prereg_is_frozen():
    verify_prereg(_packet())
