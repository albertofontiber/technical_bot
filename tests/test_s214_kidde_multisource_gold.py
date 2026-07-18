from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from src.rag.multisource_visual_gold import (
    author_prompt,
    principal_publication_gate,
    validate_candidate,
    validate_review,
    validate_support_mapping,
    validate_support_review,
)
from src.rag.visual_gold import SemanticNoGo, normalized_text_sha, stable_sha
from scripts.s214_run_kidde_multisource_gold import _verify_design_gate


ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = ROOT / "evals/s214_kidde_multisource_gold_packet_v1.json"
PREREG_PATH = ROOT / "evals/s214_kidde_multisource_gold_prereg_v1.yaml"


def _packet():
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def _candidate(item):
    source_pairs = [
        (source["source_pdf"], int(source["pages"][0]["page"]))
        for source in item["sources"]
    ]
    first_pdf, first_page = source_pairs[0]
    return {
        "canary_id": item["canary_id"],
        "adequacy": "SUFFICIENT",
        "question": "¿Qué diferencias técnicas delimitan estas opciones?",
        "expected_behavior": "answer",
        "gold_answer": "Comparación técnica completa y acotada.",
        "atomic_facts": [
            {
                "fact_id": "F01",
                "text": "Comparación entre todas las fuentes",
                "type": "core",
                "state": "present",
                "value": "diferencias explícitas",
                "citations": [
                    {"pdf": pdf, "page": page} for pdf, page in source_pairs
                ],
                "visual_evidence": [
                    {
                        "pdf": pdf,
                        "page": page,
                        "evidence": f"evidencia visible {pdf} p{page}",
                    }
                    for pdf, page in source_pairs
                ],
            },
            {
                "fact_id": "F02",
                "text": "Hecho acotado de la primera fuente",
                "type": "core",
                "state": "present",
                "value": "valor explícito",
                "citations": [{"pdf": first_pdf, "page": first_page}],
                "visual_evidence": [
                    {
                        "pdf": first_pdf,
                        "page": first_page,
                        "evidence": "fila visible de la primera fuente",
                    }
                ],
            },
        ],
        "notes": "",
    }


def _review(candidate, reviewer, author, *, pass_gate=True):
    return {
        "reviewer_model": reviewer,
        "candidate_author": author,
        "reviews": [
            {
                "canary_id": candidate["canary_id"],
                "verdict": "PASS" if pass_gate else "FAIL",
                "question_fully_answerable": True,
                "question_duplicate": False,
                "topic_aligned": True,
                "gold_complete": True,
                "source_geometry_valid": True,
                "known_conflicts_handled": True,
                "counterpart_materially_agrees": True,
                "material_disagreements": [],
                "unsupported_answer_claims": [],
                "blocking_issues": [] if pass_gate else ["material defect"],
                "nonblocking_notes": [],
                "fact_verdicts": [
                    {
                        "fact_id": fact["fact_id"],
                        "supported": True,
                        "source_pages_correct": True,
                        "answer_entails": True,
                        "genuinely_cross_source": len(
                            {citation["pdf"] for citation in fact["citations"]}
                        )
                        > 1,
                        "notes": "",
                    }
                    for fact in candidate["atomic_facts"]
                ],
            }
        ],
    }


def test_s214_packet_is_fresh_sealed_and_zero_call():
    packet = _packet()
    body = dict(packet)
    expected = body.pop("packet_sha256")
    assert stable_sha(body) == expected
    assert packet["status"] == "FROZEN_BEFORE_FRONTIER_AUTHORSHIP"
    selection = packet["selection"]
    assert selection["candidate_items"] == 4
    assert selection["distinct_source_pdfs"] == 9
    assert selection["source_overlap_with_s203_s209"] == 0
    assert selection["source_overlap_with_official_gold"] == 0
    assert selection["minimum_pixel_gold_items"] == 3
    assert selection["minimum_support_validated_items"] == 3
    assert selection["model_outputs_seen"] == 0
    assert selection["bot_outputs_seen"] == 0
    assert selection["official_fact_credit"] == 0
    assert packet["execution_contract"]["frontier_paid_calls_max"] == 24
    assert packet["execution_contract"]["provider_retries"] == 0


def test_s214_sources_pixels_and_units_are_exactly_bound():
    packet = _packet()
    assert len(packet["items"]) == 4
    assert sum(len(item["rendered_pages"]) for item in packet["items"]) == 16
    assert sum(len(item["evidence_units"]) for item in packet["items"]) == 168
    source_names = {
        source["source_pdf"]
        for item in packet["items"]
        for source in item["sources"]
    }
    assert len(source_names) == 9
    for item in packet["items"]:
        allowed = {
            (source["source_pdf"], page["page"])
            for source in item["sources"]
            for page in source["pages"]
        }
        unit_ids = [unit["unit_id"] for unit in item["evidence_units"]]
        assert len(unit_ids) == len(set(unit_ids))
        for unit in item["evidence_units"]:
            assert len(unit["content"]) <= 600
            assert (unit["source_pdf"], unit["page"]) in allowed
            assert hashlib.sha256(unit["content"].encode("utf-8")).hexdigest() == (
                unit["content_sha256"]
            )
        for page in item["rendered_pages"]:
            data = (ROOT / page["image"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == page["image_sha256"]
            assert len(data) == page["image_bytes"]
            assert (page["source_pdf"], page["page"]) in allowed
            assert page["visual_inspection"]["status"].startswith("PASS")
            assert page["visual_inspection"]["visible_anchors"]


def test_s214_authorship_requires_real_multi_source_geometry():
    packet = _packet()
    for item in packet["items"]:
        candidate = _candidate(item)
        validate_candidate(candidate, item)
        prompt = author_prompt(packet, item)
        assert "genuinely cross-source" in prompt
        assert item["canary_id"] in prompt

        one_source = json.loads(json.dumps(candidate))
        kept_pdf = one_source["atomic_facts"][0]["citations"][0]["pdf"]
        one_source["atomic_facts"][0]["citations"] = [
            citation
            for citation in one_source["atomic_facts"][0]["citations"]
            if citation["pdf"] == kept_pdf
        ]
        one_source["atomic_facts"][0]["visual_evidence"] = [
            receipt
            for receipt in one_source["atomic_facts"][0]["visual_evidence"]
            if receipt["pdf"] == kept_pdf
        ]
        with pytest.raises(ValueError, match="required distinct sources"):
            validate_candidate(one_source, item)

    insufficient = {
        "canary_id": packet["items"][0]["canary_id"],
        "adequacy": "INSUFFICIENT",
        "question": "",
        "expected_behavior": "answer",
        "gold_answer": "",
        "atomic_facts": [],
        "notes": "No hay una comparación precisa y novedosa.",
    }
    with pytest.raises(SemanticNoGo):
        validate_candidate(insufficient, packet["items"][0])


def test_s214_reciprocal_review_and_principal_publication_are_fail_closed():
    item = _packet()["items"][1]
    candidate = _candidate(item)
    fable_of_sol = _review(candidate, "claude-fable-5", "gpt-5.6-sol")
    sol_of_fable = _review(candidate, "gpt-5.6-sol", "claude-fable-5")
    validate_review(fable_of_sol, "claude-fable-5", "gpt-5.6-sol", candidate)
    validate_review(sol_of_fable, "gpt-5.6-sol", "claude-fable-5", candidate)
    assert principal_publication_gate(fable_of_sol, sol_of_fable)

    failed = _review(
        candidate, "claude-fable-5", "gpt-5.6-sol", pass_gate=False
    )
    validate_review(failed, "claude-fable-5", "gpt-5.6-sol", candidate)
    assert not principal_publication_gate(failed, sol_of_fable)


def test_s214_support_mapping_requires_exact_pdf_page_pairs():
    item = _packet()["items"][0]
    candidate = _candidate(item)
    first_units = []
    for citation in candidate["atomic_facts"][0]["citations"]:
        first_units.append(
            next(
                unit
                for unit in item["evidence_units"]
                if unit["source_pdf"] == citation["pdf"]
                and unit["page"] == citation["page"]
            )
        )
    single_unit = first_units[0]
    mapping = {
        "mapper_model": "gpt-5.6-sol",
        "mappings": [
            {
                "canary_id": item["canary_id"],
                "facts": [
                    {
                        "fact_id": "F01",
                        "support_unit_ids": [unit["unit_id"] for unit in first_units],
                        "alternative_support_unit_id_sets": [],
                    },
                    {
                        "fact_id": "F02",
                        "support_unit_ids": [single_unit["unit_id"]],
                        "alternative_support_unit_id_sets": [],
                    },
                ],
            }
        ],
    }
    normalized = validate_support_mapping(
        mapping, candidate, item, "gpt-5.6-sol"
    )
    assert normalized["F01"] == [[unit["unit_id"] for unit in first_units]]
    mapping["mappings"][0]["facts"][0]["support_unit_ids"] = [
        first_units[0]["unit_id"]
    ]
    with pytest.raises(ValueError, match="do not equal"):
        validate_support_mapping(mapping, candidate, item, "gpt-5.6-sol")


def test_s214_support_review_has_no_notes_loophole():
    item = _packet()["items"][2]
    candidate = _candidate(item)
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
                        "fact_id": fact["fact_id"],
                        "pixel_supported": True,
                        "unit_text_supported": True,
                        "minimal_complete": True,
                        "citation_source_pages_complete": True,
                        "alternative_paths_complete": True,
                        "issues": [],
                    }
                    for fact in candidate["atomic_facts"]
                ],
            }
        ],
    }
    assert validate_support_review(
        review, candidate, "claude-fable-5", "gpt-5.6-sol"
    )
    review["reviews"][0]["fact_reviews"][0]["minimal_complete"] = False
    with pytest.raises(ValueError, match="contradicts"):
        validate_support_review(
            review, candidate, "claude-fable-5", "gpt-5.6-sol"
        )


def test_s214_prereg_freezes_models_calls_and_inputs():
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    packet = _packet()
    assert prereg["status"] == "FROZEN_BEFORE_PAID_EXECUTION"
    assert prereg["packet_sha256"] == packet["packet_sha256"]
    assert prereg["models"] == {
        "principal": {"id": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
        "independent": {"id": "claude-fable-5"},
    }
    assert prereg["execution"]["frontier_paid_calls_max"] == 24
    assert prereg["execution"]["provider_retries"] == 0
    assert prereg["validation"]["minimum_support_validated_items"] == 3
    assert prereg["states"]["go"] == "GO_S214_FRESH_MULTISOURCE_COHORT"
    for spec in prereg["frozen_inputs"].values():
        assert normalized_text_sha(ROOT / spec["path"]) == spec["sha256"]


def test_s214_actual_design_gate_is_subject_bound_and_dual_pass():
    gate_path = ROOT / "evals/s214_frontier_design_gate_reviews_v1.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    body = dict(gate)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    assert gate["subject"] == "evals/s214_frontier_design_gate_brief_v1.md"
    assert gate["subject_normalized_sha256"] == normalized_text_sha(
        ROOT / gate["subject"]
    )
    _verify_design_gate()
