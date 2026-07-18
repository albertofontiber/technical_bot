"""Fail-closed gold and support-mapping contracts for planner holdouts.

This is a clean v2 of the visual authorship contract.  It binds the citation
example to an actually allowed page and adds a separate, immutable mapping
phase after the pixel gold is frozen.
"""
from __future__ import annotations

import json
from typing import Any


AUTHOR_PROMPT_V2 = """You are independently authoring ONE benchmark gold for a
Spanish technical RAG assistant used by fire-safety professionals. Use ONLY the
supplied manual page pixels. No OCR or extracted text is provided.

CANARY ID: {canary_id}
PRODUCT: {product}
PRE-FROZEN TOPIC: {topic}
FOCUS PAGES: {focus_pages}
SOURCE PDF: {source_pdf}

Requirements:
- Write a realistic, self-contained Spanish question a technician might ask. Do
  not mention the manual, page numbers, benchmark or evaluation.
- The question and complete answer must be supported by the supplied page PIXELS.
- Keep the scope technically useful but bounded: 2-8 atomic facts, at least two
  core facts, no generic filler and no fact from outside these pages.
- Each atomic fact must be independently scorable, have a distinctive value, and
  cite exactly one FOCUS page. A short visual_evidence phrase must point to the
  visible row, cell or sentence that supports it.
- Do not duplicate or paraphrase any listed question. Entries marked
  retriever_augmentation_not_test_gold are not golds, but semantic overlap with
  them would contaminate a later evaluation and is also forbidden.
- Do not infer, recommend or invent an application, installation scenario,
  suitability claim or operating consequence unless the pixels explicitly state
  it. Numeric limits alone never justify an application recommendation.
- Use precise units, inequalities, states, button durations and model restrictions.
- If the pages cannot support a safe complete gold, set adequacy to INSUFFICIENT
  and explain why; do not invent a candidate.

Existing gold and retriever-augmentation coverage to avoid semantically:
{existing_gold_coverage}

Return ONLY valid JSON, with this shape:
{{
  "canary_id": "{canary_id}",
  "adequacy": "SUFFICIENT or INSUFFICIENT",
  "question": "...",
  "expected_behavior": "answer",
  "gold_answer": "...",
  "atomic_facts": [
    {{"fact_id":"F01","text":"...","type":"core or supplementary",
      "state":"present","value":"...",
      "citation":{{"pdf":"{source_pdf}","page":{example_page}}},
      "visual_evidence":"short visible evidence"}}
  ],
  "notes": ""
}}
"""


SUPPORT_MAPPING_PROMPT = """You are the principal support mapper for a frozen
pixel-authored planner holdout. The question, answer and atomic facts are
immutable. For every fact, select the smallest complete set of supplied
evidence-unit IDs that entails that fact. Verify the fact first against the
manual pixels and then against the extracted units. Do not rewrite any field,
invent an ID, map by keyword alone, or include a merely adjacent unit.

Return ONLY valid JSON:
{"mapper_model":"gpt-5.6-sol","mappings":[{"canary_id":"...",
"facts":[{"fact_id":"F01","support_unit_ids":["..."]}]}]}
"""


SUPPORT_REVIEW_PROMPT = """You are the independent reviewer of an immutable
support mapping authored by the other frontier model. Check every frozen fact
pixel by pixel, then verify that its mapped evidence units are the smallest
complete textual support. Do not repair, remap or rewrite. PASS an item only
when every fact is supported by both pixels and units, uses the correct page,
and has a minimal complete mapping.

Return ONLY valid JSON:
{"reviewer_model":"claude-fable-5","mapper_model":"gpt-5.6-sol",
"reviews":[{"canary_id":"...","verdict":"PASS or FAIL",
"blocking_issues":[],"fact_reviews":[{"fact_id":"F01",
"pixel_supported":true,"unit_text_supported":true,
"minimal_complete":true,"citation_page_correct":true,"issues":[]}]}]}
"""


def author_prompt_v2(packet: dict[str, Any], item: dict[str, Any]) -> str:
    focus_pages = item.get("focus_pages") or []
    if not focus_pages or any(not isinstance(page, int) for page in focus_pages):
        raise ValueError("focus_pages must contain at least one integer page")
    source_stem = str(item["source_pdf"]).rsplit(".", 1)[0].casefold()
    relevant_coverage = [
        row
        for row in packet["existing_gold_coverage"]
        if row.get("kind") == "official_gold"
        or str(row.get("source_file") or "").casefold() == source_stem
    ]
    return AUTHOR_PROMPT_V2.format(
        canary_id=item["canary_id"],
        product=item["product"],
        topic=item["topic"],
        focus_pages=focus_pages,
        source_pdf=item["source_pdf"],
        example_page=focus_pages[0],
        existing_gold_coverage=json.dumps(
            relevant_coverage, ensure_ascii=False
        ),
    )


def validate_support_mapping(
    value: dict[str, Any],
    candidates: list[dict[str, Any]],
    items: list[dict[str, Any]],
    mapper_model: str,
) -> dict[str, dict[str, list[str]]]:
    if value.get("mapper_model") != mapper_model:
        raise ValueError("support mapper model identity mismatch")
    rows = value.get("mappings")
    candidate_by_id = {row["canary_id"]: row for row in candidates}
    item_by_id = {row["canary_id"]: row for row in items}
    if (
        not isinstance(rows, list)
        or len(rows) != len(candidate_by_id)
        or {row.get("canary_id") for row in rows} != set(candidate_by_id)
    ):
        raise ValueError("support mapping item coverage mismatch")
    result: dict[str, dict[str, list[str]]] = {}
    for row in rows:
        item_id = row["canary_id"]
        item = item_by_id[item_id]
        unit_by_id = {unit["unit_id"]: unit for unit in item["evidence_units"]}
        fact_by_id = {
            fact["fact_id"]: fact
            for fact in candidate_by_id[item_id]["atomic_facts"]
        }
        facts = row.get("facts")
        if (
            not isinstance(facts, list)
            or len(facts) != len(fact_by_id)
            or {fact.get("fact_id") for fact in facts} != set(fact_by_id)
        ):
            raise ValueError("support mapping fact coverage mismatch")
        result[item_id] = {}
        for mapping in facts:
            fact_id = mapping["fact_id"]
            unit_ids = mapping.get("support_unit_ids")
            if (
                not isinstance(unit_ids, list)
                or not 1 <= len(unit_ids) <= 4
                or any(not isinstance(unit_id, str) for unit_id in unit_ids)
                or len(unit_ids) != len(set(unit_ids))
                or not set(unit_ids).issubset(unit_by_id)
            ):
                raise ValueError("invalid support unit IDs")
            citation_page = fact_by_id[fact_id]["citation"]["page"]
            if any(
                unit_by_id[unit_id]["fragment_number"] != citation_page
                for unit_id in unit_ids
            ):
                raise ValueError("support mapping crosses the cited page")
            result[item_id][fact_id] = unit_ids
    return result


def validate_support_review(
    value: dict[str, Any],
    candidates: list[dict[str, Any]],
    reviewer_model: str,
    mapper_model: str,
) -> bool:
    if value.get("reviewer_model") != reviewer_model:
        raise ValueError("support reviewer model identity mismatch")
    if value.get("mapper_model") != mapper_model:
        raise ValueError("reviewed mapper model identity mismatch")
    candidate_by_id = {row["canary_id"]: row for row in candidates}
    rows = value.get("reviews")
    if (
        not isinstance(rows, list)
        or len(rows) != len(candidate_by_id)
        or {row.get("canary_id") for row in rows} != set(candidate_by_id)
    ):
        raise ValueError("support review item coverage mismatch")
    all_pass = True
    for row in rows:
        expected_facts = {
            fact["fact_id"]
            for fact in candidate_by_id[row["canary_id"]]["atomic_facts"]
        }
        fact_reviews = row.get("fact_reviews")
        blocking = row.get("blocking_issues")
        if (
            not isinstance(fact_reviews, list)
            or len(fact_reviews) != len(expected_facts)
            or {fact.get("fact_id") for fact in fact_reviews} != expected_facts
            or not isinstance(blocking, list)
            or row.get("verdict") not in {"PASS", "FAIL"}
        ):
            raise ValueError("invalid support review shape")
        conditions = not blocking
        for fact in fact_reviews:
            if not isinstance(fact.get("issues"), list):
                raise ValueError("support review fact issues missing")
            conditions = conditions and not fact["issues"] and all(
                fact.get(field) is True
                for field in (
                    "pixel_supported",
                    "unit_text_supported",
                    "minimal_complete",
                    "citation_page_correct",
                )
            )
        if (row["verdict"] == "PASS") != conditions:
            raise ValueError("support review verdict contradicts its fields")
        all_pass = all_pass and conditions
    return all_pass
