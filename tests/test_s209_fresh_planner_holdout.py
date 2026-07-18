from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from src.rag.holdout_evidence import atomic_evidence_unit_rows
from src.rag.planner_holdout_gold import (
    author_prompt_v3,
    validate_candidate_v3,
    validate_support_mapping_v3,
)
from src.rag.planner_support_review import validate_support_review_v4
from src.rag.visual_gold import normalized_text_sha


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evals/s209_fresh_planner_holdout_packet_v1.json"
PREREG = ROOT / "evals/s209_fresh_planner_holdout_prereg_v1.yaml"


def _packet():
    return json.loads(PACKET.read_text(encoding="utf-8"))


def _candidate(item, citations):
    pages = [row["page"] for row in citations]
    return {
        "canary_id": item["canary_id"],
        "adequacy": "SUFFICIENT",
        "question": "Pregunta tecnica",
        "expected_behavior": "answer",
        "gold_answer": "Respuesta tecnica completa",
        "atomic_facts": [
            {
                "fact_id": "F01",
                "text": "Hecho uno",
                "type": "core",
                "state": "present",
                "value": "valor uno",
                "citations": citations,
                "visual_evidence": [
                    {"page": page, "evidence": f"evidencia pagina {page}"}
                    for page in pages
                ],
            },
            {
                "fact_id": "F02",
                "text": "Hecho dos",
                "type": "core",
                "state": "present",
                "value": "valor dos",
                "citations": [citations[0]],
                "visual_evidence": [
                    {"page": pages[0], "evidence": "segunda evidencia"}
                ],
            },
        ],
        "notes": "",
    }


def test_s209_packet_is_sealed_and_honest_about_source_overlap():
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
    assert selection["selected_items"] == 2
    assert selection["selected_documents"] == 2
    assert len(selection["selected_source_overlap_with_official_gold"]) == 2
    assert selection["selected_source_overlap_with_prior_visual_cohorts"] == []
    assert selection["source_independent_validation_claimed"] is False
    assert selection["new_predicate_validation_claimed"] is False
    assert selection["new_predicate_candidate_claimed"] is True
    assert selection["semantic_novelty_requires_frontier_pass"] is True
    assert selection["genuine_cross_page_items"] == 1


def test_s209_prereg_freezes_models_calls_and_every_declared_input():
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    packet = _packet()
    assert prereg["status"] == "FROZEN_BEFORE_PAID_EXECUTION"
    assert prereg["packet_sha256"] == packet["packet_sha256"]
    assert prereg["models"] == {
        "principal": {"id": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
        "independent": {"id": "claude-fable-5"},
        "planner": {"id": "gpt-5.6-terra", "reasoning_effort": "low"},
    }
    assert prereg["execution"]["frontier_paid_calls_max"] == 8
    assert prereg["execution"]["planner_calls"] == 2
    assert prereg["execution"]["provider_retries"] == 0
    assert prereg["design_review"]["independent_execution_gate_waived"] is False
    assert prereg["validation"]["fable_publication_reviews_pass_required"] == 2
    assert prereg["validation"]["fable_support_reviews_pass_required"] == 2
    for spec in prereg["frozen_inputs"].values():
        assert normalized_text_sha(ROOT / spec["path"]) == spec["sha256"]


def test_s209_pixels_and_units_are_source_bound():
    packet = _packet()
    assert packet["rendering_receipt"]["pages_inspected"] == 3
    assert len(packet["items"]) == 2
    for item in packet["items"]:
        assert item["evidence_units"]
        unit_ids = [row["unit_id"] for row in item["evidence_units"]]
        assert len(unit_ids) == len(set(unit_ids))
        assert item["novelty_receipt"]["semantic_duplicate_veto"] is True
        for unit in item["evidence_units"]:
            assert len(unit["content"]) <= 600
            assert unit["fragment_number"] in item["focus_pages"]
            assert hashlib.sha256(unit["content"].encode("utf-8")).hexdigest() == (
                unit["content_sha256"]
            )
        covered_by_page = {}
        for unit in item["evidence_units"]:
            assert unit["unit_kind"] == "gap_free_partition_v1"
            covered = covered_by_page.setdefault(unit["fragment_number"], set())
            for start, end in unit["source_spans"]:
                assert not (covered & set(range(start, end)))
                covered.update(range(start, end))
        for page in item["rendered_pages"]:
            data = (ROOT / page["image"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == page["image_sha256"]
            assert len(data) == page["image_bytes"]
            assert page["dpi"] == 200
            assert page["visual_inspection"]["status"] == "PASS"
            assert page["visual_inspection"]["visible_anchors"]

    joined = {
        item["canary_id"]: "\n".join(
            unit["content"] for unit in item["evidence_units"]
        )
        for item in packet["items"]
    }
    assert "0.1 a 0.25 dB/m" in joined["kidde_dp3020_detection_discrimination"]
    assert "hacia adelante y hacia atr" in joined[
        "kidde_dp3020_detection_discrimination"
    ]
    assert "al menos un dispositivo por zona" in joined[
        "kidde_nc_maintenance_schedule"
    ]
    assert "productos que contengan disolventes" in joined[
        "kidde_nc_maintenance_schedule"
    ]


def test_holdout_partition_has_no_gap_overlap_or_alternative_id_path():
    source = "A" * 239 + "\n" + "B" * 470 + "\nfin"
    rows = atomic_evidence_unit_rows(source, "fixture", 7)
    coverage = [0] * len(source)
    for row in rows:
        assert row["unit_kind"] == "gap_free_partition_v1"
        assert len(row["source_spans"]) == 1
        start, end = row["source_spans"][0]
        for index in range(start, end):
            if not source[index].isspace():
                coverage[index] += 1
    assert all(
        count == 1
        for index, count in enumerate(coverage)
        if not source[index].isspace()
    )


def test_s209_v3_candidate_requires_complete_nonredundant_page_lists():
    packet = _packet()
    item = packet["items"][0]
    citations = [
        {"pdf": item["source_pdf"], "page": 1},
        {"pdf": item["source_pdf"], "page": 2},
    ]
    candidate = _candidate(item, citations)
    validate_candidate_v3(candidate, item)
    prompt = author_prompt_v3(packet, item)
    assert "cite EVERY focus page" in prompt
    assert "at least 1 genuinely cross-page" in prompt

    singular = json.loads(json.dumps(candidate))
    singular["atomic_facts"][0]["citation"] = singular["atomic_facts"][0].pop(
        "citations"
    )[0]
    with pytest.raises(ValueError, match="fact shape invalid|singular citation"):
        validate_candidate_v3(singular, item)

    redundant = json.loads(json.dumps(candidate))
    redundant["atomic_facts"][0]["citations"].append(citations[0])
    redundant["atomic_facts"][0]["visual_evidence"].append(
        {"page": 1, "evidence": "duplicada"}
    )
    with pytest.raises(ValueError, match="unique"):
        validate_candidate_v3(redundant, item)


def test_s209_mapping_requires_exact_page_set_not_same_page_only():
    packet = _packet()
    item = packet["items"][0]
    units_by_page = {
        page: next(
            unit for unit in item["evidence_units"] if unit["fragment_number"] == page
        )
        for page in (1, 2)
    }
    citations = [
        {"pdf": item["source_pdf"], "page": 1},
        {"pdf": item["source_pdf"], "page": 2},
    ]
    candidate = _candidate(item, citations)
    mapping = {
        "mapper_model": "gpt-5.6-sol",
        "mappings": [
            {
                "canary_id": item["canary_id"],
                "facts": [
                    {
                        "fact_id": "F01",
                        "support_unit_ids": [
                            units_by_page[1]["unit_id"],
                            units_by_page[2]["unit_id"],
                        ],
                        "alternative_support_unit_id_sets": [],
                    },
                    {
                        "fact_id": "F02",
                        "support_unit_ids": [units_by_page[1]["unit_id"]],
                        "alternative_support_unit_id_sets": [],
                    },
                ],
            }
        ],
    }
    assert validate_support_mapping_v3(
        mapping, [candidate], [item], "gpt-5.6-sol"
    )[item["canary_id"]]["F01"] == [
        [units_by_page[1]["unit_id"], units_by_page[2]["unit_id"]]
    ]
    mapping["mappings"][0]["facts"][0]["support_unit_ids"] = [
        units_by_page[1]["unit_id"]
    ]
    with pytest.raises(ValueError, match="do not equal"):
        validate_support_mapping_v3(
            mapping, [candidate], [item], "gpt-5.6-sol"
        )


def test_s209_independent_support_review_v4_fails_closed():
    packet = _packet()
    item = packet["items"][0]
    citations = [
        {"pdf": item["source_pdf"], "page": 1},
        {"pdf": item["source_pdf"], "page": 2},
    ]
    candidate = _candidate(item, citations)
    review = {
        "reviewer_model": "claude-fable-5",
        "mapper_model": "gpt-5.6-sol",
        "reviews": [
            {
                "canary_id": item["canary_id"],
                "verdict": "PASS",
                "blocking_issues": [],
                "notes": ["independent item audit passed"],
                "fact_reviews": [
                    {
                        "fact_id": fact_id,
                        "pixel_supported": True,
                        "unit_text_supported": True,
                        "minimal_complete": True,
                        "citation_pages_complete": True,
                        "alternative_paths_complete": True,
                        "blocking_issues": [],
                        "notes": ["independent fact audit passed"],
                    }
                    for fact_id in ("F01", "F02")
                ],
            }
        ],
    }
    assert validate_support_review_v4(
        review, [candidate], "claude-fable-5", "gpt-5.6-sol"
    )
    review["reviews"][0]["fact_reviews"][0]["citation_pages_complete"] = False
    with pytest.raises(ValueError, match="failed fact must identify"):
        validate_support_review_v4(
            review, [candidate], "claude-fable-5", "gpt-5.6-sol"
        )
