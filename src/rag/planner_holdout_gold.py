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


AUTHOR_PROMPT_V3 = """You are independently authoring ONE benchmark gold for a
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
- Each atomic fact must be independently scorable and cite EVERY focus page
  needed to establish it. A fact may cite one page or several pages. Never add a
  redundant page merely to make a fact look multi-page.
- For every citation, include a separate short visual-evidence receipt pointing
  to the visible row, cell, footnote, heading or sentence on that page.
- This item requires at least {cross_page_facts_min} genuinely cross-page atomic
  fact(s). If the pixels cannot support that geometry, set adequacy to
  INSUFFICIENT instead of manufacturing a dependency.
- Do not duplicate or paraphrase any listed question or fact. Entries marked
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
      "citations":[{{"pdf":"{source_pdf}","page":{example_page}}}],
      "visual_evidence":[{{"page":{example_page},
        "evidence":"short visible evidence on this page"}}]}}
  ],
  "notes": ""
}}
"""


SUPPORT_MAPPING_PROMPT_V3 = """You are the principal support mapper for a
frozen pixel-authored planner holdout. The question, answer, atomic facts and
their complete citation-page lists are immutable. For every fact, select the
smallest complete set of supplied evidence-unit IDs that entails that fact.
Verify the fact first against every cited manual-page pixel and then against the
extracted units. The mapped unit pages must match the declared citation pages
exactly: no missing page and no undeclared page. Do not rewrite any field,
invent an ID, map by keyword alone, or include a merely adjacent unit. In
alternative_support_unit_id_sets, enumerate every other minimal complete unit
set that independently entails the same fact; return [] only after checking all
supplied units. Do not list supersets, partial support or the primary set again.

Return ONLY valid JSON:
{"mapper_model":"gpt-5.6-sol","mappings":[{"canary_id":"...",
"facts":[{"fact_id":"F01","support_unit_ids":["..."],
"alternative_support_unit_id_sets":[]}]}]}
"""


SUPPORT_REVIEW_PROMPT_V3 = """You are the independent reviewer of an immutable
multi-page support mapping authored by the other frontier model. Check every
frozen fact pixel by pixel, then verify that its mapped evidence units are the
smallest complete textual support. The mapped pages must equal the fact's
declared citation pages exactly. Do not repair, remap or rewrite. PASS an item
only when every fact is supported by all and only its cited pages and units.
Also verify that the mapper exhaustively enumerated every alternative minimal
complete support set in the supplied units, without admitting partial paths or
supersets.

Return ONLY valid JSON:
{"reviewer_model":"claude-fable-5","mapper_model":"gpt-5.6-sol",
"reviews":[{"canary_id":"...","verdict":"PASS or FAIL",
"blocking_issues":[],"fact_reviews":[{"fact_id":"F01",
"pixel_supported":true,"unit_text_supported":true,
"minimal_complete":true,"citation_pages_complete":true,
"alternative_paths_complete":true,"issues":[]}]}]}
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


def author_prompt_v3(packet: dict[str, Any], item: dict[str, Any]) -> str:
    """Build the clean multi-page authorship contract used after S207.

    V2 remains available for immutable historical artifacts. V3 does not accept
    the singular ``citation`` field; every fact owns an explicit citation list.
    """
    focus_pages = item.get("focus_pages") or []
    if not focus_pages or any(not isinstance(page, int) for page in focus_pages):
        raise ValueError("focus_pages must contain at least one integer page")
    cross_page_min = item.get("cross_page_facts_min", 0)
    if not isinstance(cross_page_min, int) or cross_page_min < 0:
        raise ValueError("cross_page_facts_min must be a non-negative integer")
    source_stem = str(item["source_pdf"]).rsplit(".", 1)[0].casefold()
    relevant_coverage = [
        row
        for row in packet["existing_gold_coverage"]
        if row.get("kind") == "official_gold"
        or str(row.get("source_file") or "").casefold() == source_stem
    ]
    return AUTHOR_PROMPT_V3.format(
        canary_id=item["canary_id"],
        product=item["product"],
        topic=item["topic"],
        focus_pages=focus_pages,
        source_pdf=item["source_pdf"],
        example_page=focus_pages[0],
        cross_page_facts_min=cross_page_min,
        existing_gold_coverage=json.dumps(relevant_coverage, ensure_ascii=False),
    )


def validate_candidate_v3(candidate: dict[str, Any], item: dict[str, Any]) -> None:
    required = {
        "canary_id",
        "adequacy",
        "question",
        "expected_behavior",
        "gold_answer",
        "atomic_facts",
        "notes",
    }
    if not required <= set(candidate):
        raise ValueError(f"candidate missing fields: {sorted(required - set(candidate))}")
    if candidate["canary_id"] != item["canary_id"]:
        raise ValueError("candidate canary_id mismatch")
    if candidate["adequacy"] != "SUFFICIENT":
        raise ValueError("candidate marked source insufficient")
    if candidate["expected_behavior"] != "answer":
        raise ValueError("expected_behavior must be answer")
    for key in ("question", "gold_answer"):
        if not isinstance(candidate[key], str) or not candidate[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    facts = candidate["atomic_facts"]
    if not isinstance(facts, list) or not 2 <= len(facts) <= 8:
        raise ValueError("atomic_facts cardinality must be 2..8")
    allowed_pages = set(item["focus_pages"])
    ids: list[str] = []
    core = 0
    cross_page_facts = 0
    for fact in facts:
        keys = {
            "fact_id",
            "text",
            "type",
            "state",
            "value",
            "citations",
            "visual_evidence",
        }
        if not isinstance(fact, dict) or not keys <= set(fact):
            raise ValueError("fact shape invalid")
        if "citation" in fact:
            raise ValueError("singular citation is forbidden by v3")
        ids.append(str(fact["fact_id"]))
        if fact["type"] not in {"core", "supplementary"}:
            raise ValueError("fact type invalid")
        core += fact["type"] == "core"
        if fact["state"] != "present":
            raise ValueError("fact state invalid")
        for key in ("text", "value"):
            if not isinstance(fact[key], str) or not fact[key].strip():
                raise ValueError("fact text fields must be non-empty")
        citations = fact["citations"]
        if not isinstance(citations, list) or not 1 <= len(citations) <= 3:
            raise ValueError("fact citations cardinality must be 1..3")
        citation_pages: list[int] = []
        for citation in citations:
            if not isinstance(citation, dict) or set(citation) != {"pdf", "page"}:
                raise ValueError("fact citation shape invalid")
            if citation["pdf"] != item["source_pdf"]:
                raise ValueError("fact citation PDF invalid")
            if citation["page"] not in allowed_pages:
                raise ValueError("fact citation page outside frozen focus span")
            citation_pages.append(citation["page"])
        if len(citation_pages) != len(set(citation_pages)):
            raise ValueError("fact citation pages must be unique")
        evidence = fact["visual_evidence"]
        if not isinstance(evidence, list) or len(evidence) != len(citations):
            raise ValueError("visual evidence must cover every citation page")
        evidence_pages: list[int] = []
        for receipt in evidence:
            if not isinstance(receipt, dict) or set(receipt) != {"page", "evidence"}:
                raise ValueError("visual evidence receipt shape invalid")
            if not isinstance(receipt["evidence"], str) or not receipt["evidence"].strip():
                raise ValueError("visual evidence text must be non-empty")
            evidence_pages.append(receipt["page"])
        if set(evidence_pages) != set(citation_pages) or len(evidence_pages) != len(
            set(evidence_pages)
        ):
            raise ValueError("visual evidence pages must equal citation pages")
        cross_page_facts += len(citation_pages) > 1
    expected_ids = [f"F{index:02d}" for index in range(1, len(ids) + 1)]
    if len(ids) != len(set(ids)) or ids != expected_ids:
        raise ValueError("fact IDs must be contiguous F01..")
    if core < 2:
        raise ValueError("candidate needs at least two core facts")
    if cross_page_facts < int(item.get("cross_page_facts_min", 0)):
        raise ValueError("candidate lacks required genuine cross-page facts")


def _citation_pages_v3(fact: dict[str, Any]) -> set[int]:
    return {int(row["page"]) for row in fact["citations"]}


def validate_support_mapping_v3(
    value: dict[str, Any],
    candidates: list[dict[str, Any]],
    items: list[dict[str, Any]],
    mapper_model: str,
) -> dict[str, dict[str, list[list[str]]]]:
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
    result: dict[str, dict[str, list[list[str]]]] = {}
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
            declared_pages = _citation_pages_v3(fact_by_id[fact_id])
            alternatives = mapping.get("alternative_support_unit_id_sets")
            if not isinstance(alternatives, list) or len(alternatives) > 4:
                raise ValueError("invalid alternative support sets")
            support_sets = [unit_ids, *alternatives]
            normalized: list[list[str]] = []
            seen_sets: set[tuple[str, ...]] = set()
            for support_set in support_sets:
                if (
                    not isinstance(support_set, list)
                    or not 1 <= len(support_set) <= 6
                    or any(not isinstance(unit_id, str) for unit_id in support_set)
                    or len(support_set) != len(set(support_set))
                    or not set(support_set).issubset(unit_by_id)
                ):
                    raise ValueError("invalid support unit IDs")
                identity = tuple(sorted(support_set))
                if identity in seen_sets:
                    raise ValueError("duplicate support-equivalent set")
                seen_sets.add(identity)
                mapped_pages = {
                    int(unit_by_id[unit_id]["fragment_number"])
                    for unit_id in support_set
                }
                if mapped_pages != declared_pages:
                    raise ValueError(
                        "support pages do not equal declared citation pages"
                    )
                normalized.append(list(support_set))
            result[item_id][fact_id] = normalized
    return result


def validate_support_review_v3(
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
                    "citation_pages_complete",
                    "alternative_paths_complete",
                )
            )
        if (row["verdict"] == "PASS") != conditions:
            raise ValueError("support review verdict contradicts its fields")
        all_pass = all_pass and conditions
    return all_pass


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
