from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.rag.decomposed_evidence_planner import planner_payload, validate_plan
from src.rag.evidence_units_v2 import EvidenceUnitV2
from src.rag.planner_holdout_gold import (
    author_prompt_v2,
    validate_support_mapping,
    validate_support_review,
)


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evals/s207_decomposed_planner_holdout_packet_v1.json"


def _packet():
    return json.loads(PACKET.read_text(encoding="utf-8"))


def test_s207_packet_is_sealed_before_models_and_has_no_prior_source_overlap():
    packet = _packet()
    body = dict(packet)
    expected = body.pop("packet_sha256")
    actual = hashlib.sha256(
        json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    assert actual == expected
    assert packet["status"] == "FROZEN_BEFORE_FRONTIER_AUTHORSHIP"
    selection = packet["selection"]
    assert selection["model_outputs_seen"] == 0
    assert selection["bot_outputs_seen"] == 0
    assert selection["retrieval_calls"] == 0
    assert selection["database_calls"] == 0
    assert selection["selected_items"] == 3
    assert selection["selected_documents"] == 3
    assert selection["selected_source_overlap_with_official_gold"] == []
    assert selection["selected_source_overlap_with_s203_s205"] == []
    assert selection["exact_focus_page_hyq_questions"] == 0


def test_s207_pixels_and_evidence_units_are_exactly_source_bound():
    packet = _packet()
    assert packet["rendering_receipt"] == {
        "poppler_path_available": False,
        "fallback": "PyMuPDF_200dpi",
        "page_bound_pixel_receipts_completed_before_freeze": True,
        "pages_inspected": 4,
    }
    assert len(packet["items"]) == 3
    assert len({item["source_pdf"] for item in packet["items"]}) == 3
    assert len({item["stratum"] for item in packet["items"]}) == 3
    for item in packet["items"]:
        assert item["novelty_receipt"]["exact_focus_page_hyq_questions"] == 0
        assert item["novelty_receipt"]["source_identity_disclosed_to_frontier"]
        assert item["evidence_units"]
        unit_ids = [row["unit_id"] for row in item["evidence_units"]]
        assert len(unit_ids) == len(set(unit_ids))
        for unit in item["evidence_units"]:
            assert unit["content"]
            assert len(unit["content"]) <= 600
            assert hashlib.sha256(unit["content"].encode("utf-8")).hexdigest() == (
                unit["content_sha256"]
            )
            assert unit["fragment_number"] in item["focus_pages"]
        for page in item["rendered_pages"]:
            image = ROOT / page["image"]
            data = image.read_bytes()
            assert hashlib.sha256(data).hexdigest() == page["image_sha256"]
            assert len(data) == page["image_bytes"]
            assert page["dpi"] == 200
            assert page["width_px"] > 1000
            assert page["height_px"] > 1000
            inspection = page["visual_inspection"]
            assert inspection["status"] == "PASS"
            assert inspection["render_sha256_bound"] == page["image_sha256"]
            assert inspection["visible_anchors"]


def test_s207_table_facts_have_atomic_units_without_a_broad_duplicate_path():
    packet = _packet()
    by_id = {item["canary_id"]: item for item in packet["items"]}
    outdoor = [
        unit
        for unit in by_id["kidde_outdoor_isolator_nominal_currents"][
            "evidence_units"
        ]
        if "Nennstrom" in unit["content"]
        and "1,05 A" in unit["content"]
        and "1,4 A" in unit["content"]
    ]
    assert len(outdoor) == 1
    assert len(outdoor[0]["content"]) < 200
    mcp_units = by_id["kidde_mcp_isolation_parasitics"]["evidence_units"]
    assert not any(
        "Corrente di dispersione" in unit["content"]
        and "Impedenza in serie" in unit["content"]
        for unit in mcp_units
    )


def test_s207_model_roles_and_execution_boundaries_are_exact():
    packet = _packet()
    assert packet["generation_contract"] == {
        "principal": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
        "independent": {"model": "claude-fable-5"},
        "pixel_only_authorship_and_cross_review": True,
        "source_identity_and_all_same_source_hyq_disclosed": True,
        "final_gold_author": "gpt-5.6-sol",
        "fable_must_pass_every_sol_candidate": True,
        "sol_counterpart_review_is_disagreement_probe": True,
        "same_item_retry": False,
        "candidate_merge_or_repair": False,
    }
    planner = packet["planner_contract"]
    assert planner["mechanism"] == "decomposed_evidence_planner_v1"
    assert planner["planner_model"] == "gpt-5.6-terra"
    assert planner["planner_reasoning_effort"] == "low"
    assert planner["gold_claims_and_support_ids_hidden_from_planner"] is True
    assert planner["retrieval_calls"] == 0
    assert planner["reranker_calls"] == 0
    assert planner["database_calls"] == 0
    assert planner["production"] is False


def test_s207_v2_prompt_uses_an_allowed_example_page():
    packet = _packet()
    for item in packet["items"]:
        prompt = author_prompt_v2(packet, item)
        example_page = item["focus_pages"][0]
        assert f'"page":{example_page}' in prompt
        if 1 not in item["focus_pages"]:
            assert '"page":1}' not in prompt


def test_generic_planner_identity_is_whitelisted_and_plan_is_nonempty():
    unit = EvidenceUnitV2(
        unit_id="E001_test",
        fragment_number=10,
        candidate_id="candidate",
        unit_kind="contiguous",
        source_spans=((0, 4),),
        content="dato",
        content_sha256=hashlib.sha256(b"dato").hexdigest(),
    )
    payload = planner_payload(
        "pregunta",
        {
            "canary_id": "c1",
            "question_sha256": "a" * 64,
            "source_files": ["manual.pdf"],
        },
        [unit],
        {
            "candidate": {
                "document_id": "doc-1",
                "source_file": "manual.pdf",
                "page_number": 10,
            }
        },
    )
    assert "support_unit_ids" not in payload
    with pytest.raises(ValueError, match="unsafe question identity"):
        planner_payload("pregunta", {"gold_support_ids": "secret"}, [unit])
    with pytest.raises(ValueError, match="invalid obligation array"):
        validate_plan({"obligations": []}, {unit.unit_id})
    with pytest.raises(ValueError, match="duplicate obligation label"):
        validate_plan(
            {
                "obligations": [
                    {"label": "Límite", "unit_ids": [unit.unit_id]},
                    {"label": "límite", "unit_ids": [unit.unit_id]},
                ]
            },
            {unit.unit_id},
        )


def test_s207_support_mapping_and_independent_review_fail_closed():
    packet = _packet()
    item = packet["items"][0]
    unit = item["evidence_units"][0]
    candidate = {
        "canary_id": item["canary_id"],
        "atomic_facts": [
            {
                "fact_id": "F01",
                "citation": {
                    "pdf": item["source_pdf"],
                    "page": unit["fragment_number"],
                },
            }
        ],
    }
    mapping = {
        "mapper_model": "gpt-5.6-sol",
        "mappings": [
            {
                "canary_id": item["canary_id"],
                "facts": [
                    {"fact_id": "F01", "support_unit_ids": [unit["unit_id"]]}
                ],
            }
        ],
    }
    assert validate_support_mapping(
        mapping, [candidate], [item], "gpt-5.6-sol"
    ) == {item["canary_id"]: {"F01": [unit["unit_id"]]}}
    review = {
        "reviewer_model": "claude-fable-5",
        "mapper_model": "gpt-5.6-sol",
        "reviews": [
            {
                "canary_id": item["canary_id"],
                "verdict": "PASS",
                "blocking_issues": [],
                "fact_reviews": [
                    {
                        "fact_id": "F01",
                        "pixel_supported": True,
                        "unit_text_supported": True,
                        "minimal_complete": True,
                        "citation_page_correct": True,
                        "issues": [],
                    }
                ],
            }
        ],
    }
    assert validate_support_review(
        review, [candidate], "claude-fable-5", "gpt-5.6-sol"
    )
    review["reviews"][0]["fact_reviews"][0]["minimal_complete"] = False
    with pytest.raises(ValueError, match="contradicts"):
        validate_support_review(
            review, [candidate], "claude-fable-5", "gpt-5.6-sol"
        )
