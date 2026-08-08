"""Fail-closed contracts for pixel-grounded, multi-document benchmark golds.

The historical visual-gold contracts intentionally remain immutable.  This
module generalizes the same author -> reciprocal review -> support mapping
geometry to questions whose answer genuinely depends on more than one source.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from src.rag.visual_gold import SemanticNoGo, sha256_bytes


AUTHOR_PROMPT = """You are independently authoring ONE benchmark gold for a
Spanish technical RAG assistant used by fire-safety professionals. Use ONLY the
supplied manual-page PIXELS. No OCR or extracted text is provided.

CANARY ID: {canary_id}
PRODUCT/FAMILY: {product}
PRE-FROZEN TOPIC: {topic}
ALLOWED SOURCE-PAGES: {allowed_source_pages}
KNOWN SOURCE CONFLICTS OR EXCLUSIONS: {known_conflicts}

Requirements:
- Write a realistic, self-contained Spanish question a technician might ask.
  Do not mention manuals, page numbers, benchmarks or evaluation.
- The question must require evidence from at least {distinct_sources_min}
  different PDFs. A one-source question with decorative extra citations fails.
- The complete answer must be supported by the supplied pixels and contain 2-8
  independently scorable atomic facts, including at least two core facts.
- Every atomic fact must cite all and only the PDF-page pairs needed to establish
  it. Include one short visual-evidence receipt per citation.
- At least {cross_source_facts_min} atomic fact(s) must be genuinely cross-source:
  the comparison or distinction is not entailed by either source alone.
- Do not duplicate or paraphrase the listed official-gold or same-source
  retriever-augmentation coverage. Semantic overlap contaminates evaluation.
- Do not infer suitability, safety, installation consequences or a purchasing
  recommendation merely from numbers. A bounded selection is allowed only when
  the pixels explicitly establish every criterion used.
- Do not silently reconcile a known contradiction. Avoid the conflicting field,
  or state each source's exact claim and identify the conflict without choosing a
  winner.
- Use exact model restrictions, states, units, inequalities and option effects.
- If a precise, useful and novel gold cannot be supported, set adequacy to
  INSUFFICIENT, leave question/gold_answer empty and atomic_facts [], and explain
  the reason in notes. Never invent or repair evidence.

Coverage to avoid semantically:
{existing_coverage}

Return ONLY valid JSON:
{{
  "canary_id": "{canary_id}",
  "adequacy": "SUFFICIENT or INSUFFICIENT",
  "question": "...",
  "expected_behavior": "answer",
  "gold_answer": "...",
  "atomic_facts": [
    {{"fact_id":"F01","text":"...","type":"core or supplementary",
      "state":"present","value":"...",
      "citations":[{{"pdf":"source.pdf","page":1}}],
      "visual_evidence":[{{"pdf":"source.pdf","page":1,
        "evidence":"short visible evidence"}}]}}
  ],
  "notes": ""
}}
"""


REVIEW_PROMPT = """You are the independent pixel-level reviewer of ONE
multi-document benchmark-gold candidate written by the OTHER frontier model.
Do not rewrite, repair or merge either candidate. Review every claim against
the supplied manual-page pixels.

PASS only when all conditions hold:
1. the Spanish question is realistic, self-contained, technically useful and
   genuinely requires the frozen number of distinct sources;
2. it is not a semantic duplicate of the disclosed official or same-source
   retriever-augmentation coverage;
3. every fact is visible on all and only its cited PDF-page pairs, correctly
   scoped, numerically exact, atomic and entailed by the answer;
4. at least the frozen number of facts are genuinely cross-source;
5. the answer is complete and contains no unsupported claim or inferred
   suitability/consequence; and
6. every disclosed source conflict is avoided or explicitly represented without
   silently choosing a winner.

The independently authored counterpart is a disagreement probe, not text to
merge. counterpart_materially_agrees is false if it reveals a substantive model,
value, scope or conflict-handling disagreement. Put only invalidating findings in
blocking_issues. A PASS has no blocking issue or material disagreement.

Return ONLY valid JSON:
{{"reviewer_model":"{reviewer_model}","candidate_author":"{candidate_author}",
  "reviews":[{{"canary_id":"{canary_id}","verdict":"PASS or FAIL",
    "question_fully_answerable":true,"question_duplicate":false,
    "topic_aligned":true,"gold_complete":true,
    "source_geometry_valid":true,"known_conflicts_handled":true,
    "counterpart_materially_agrees":true,"material_disagreements":[],
    "unsupported_answer_claims":[],"blocking_issues":[],
    "nonblocking_notes":[],
    "fact_verdicts":[{{"fact_id":"F01","supported":true,
      "source_pages_correct":true,"answer_entails":true,
      "genuinely_cross_source":true,"notes":""}}]}}]}}

Coverage to avoid semantically:
{existing_coverage}
"""


SUPPORT_MAPPING_PROMPT = """You are the principal support mapper for ONE
immutable, pixel-authored multi-document gold. Verify every fact against all
cited pixels and then map it to the smallest complete set of supplied textual
evidence-unit IDs. The mapped set's PDF-page pairs must equal the fact's citation
pairs exactly: no missing or undeclared source-page. Enumerate every alternative
minimal complete support set; do not list supersets, partial paths or the primary
set again. Do not rewrite any gold field or invent an ID.

Return ONLY valid JSON:
{"mapper_model":"gpt-5.6-sol","mappings":[{"canary_id":"...",
"facts":[{"fact_id":"F01","support_unit_ids":["..."],
"alternative_support_unit_id_sets":[]}]}]}
"""


SUPPORT_REVIEW_PROMPT = """You are the independent reviewer of ONE immutable
multi-document support mapping authored by the other frontier model. Check each
fact against every cited pixel, then verify that each mapped unit set is minimal,
complete, and has exactly the same PDF-page pairs as the citations. Verify that
all alternative minimal complete sets were enumerated. Do not repair or remap.

Return ONLY valid JSON:
{"reviewer_model":"claude-fable-5","mapper_model":"gpt-5.6-sol",
"reviews":[{"canary_id":"...","verdict":"PASS or FAIL",
"blocking_issues":[],"fact_reviews":[{"fact_id":"F01",
"pixel_supported":true,"unit_text_supported":true,
"minimal_complete":true,"citation_source_pages_complete":true,
"alternative_paths_complete":true,"issues":[]}]}]}
"""


def _allowed_pairs(item: dict[str, Any]) -> set[tuple[str, int]]:
    pairs: set[tuple[str, int]] = set()
    for source in item.get("sources") or []:
        pdf = source.get("source_pdf")
        pages = source.get("pages")
        if not isinstance(pdf, str) or not pdf or not isinstance(pages, list):
            raise ValueError("invalid multi-source item geometry")
        for page_value in pages:
            page = (
                page_value.get("page")
                if isinstance(page_value, dict)
                else page_value
            )
            if not isinstance(page, int) or page < 1:
                raise ValueError("invalid source page")
            if (pdf, page) in pairs:
                raise ValueError("duplicate allowed source-page pair")
            pairs.add((pdf, page))
    if not pairs:
        raise ValueError("multi-source item has no source pages")
    return pairs


def _relevant_coverage(packet: dict[str, Any], item: dict[str, Any]) -> list[dict[str, Any]]:
    stems = {
        Path(source["source_pdf"]).stem.casefold()
        for source in item.get("sources") or []
    }
    return [
        row
        for row in packet.get("existing_gold_coverage") or []
        if row.get("kind") == "official_gold"
        or str(row.get("source_file") or "").casefold() in stems
    ]


def author_prompt(packet: dict[str, Any], item: dict[str, Any]) -> str:
    allowed = sorted(
        ({"pdf": pdf, "page": page} for pdf, page in _allowed_pairs(item)),
        key=lambda row: (row["pdf"].casefold(), row["page"]),
    )
    return AUTHOR_PROMPT.format(
        canary_id=item["canary_id"],
        product=item["product"],
        topic=item["topic"],
        allowed_source_pages=json.dumps(allowed, ensure_ascii=False),
        known_conflicts=json.dumps(item.get("known_conflicts") or [], ensure_ascii=False),
        distinct_sources_min=int(item["distinct_sources_min"]),
        cross_source_facts_min=int(item["cross_source_facts_min"]),
        existing_coverage=json.dumps(_relevant_coverage(packet, item), ensure_ascii=False),
    )


def review_prompt(
    packet: dict[str, Any],
    item: dict[str, Any],
    reviewer_model: str,
    candidate_author: str,
) -> str:
    return REVIEW_PROMPT.format(
        reviewer_model=reviewer_model,
        candidate_author=candidate_author,
        canary_id=item["canary_id"],
        existing_coverage=json.dumps(_relevant_coverage(packet, item), ensure_ascii=False),
    )


def _verified_image(root: Path, page: dict[str, Any]) -> str:
    data = (root / page["image"]).read_bytes()
    if sha256_bytes(data) != page["image_sha256"]:
        raise ValueError(f"image hash drift: {page['image']}")
    return base64.b64encode(data).decode("ascii")


def page_content_openai(
    root: Path, item: dict[str, Any], leading_text: str
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": leading_text}]
    for page in item["rendered_pages"]:
        content.append(
            {
                "type": "input_text",
                "text": f"SOURCE {page['source_pdf']} PAGE {page['page']}",
            }
        )
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{_verified_image(root, page)}",
            }
        )
    return content


def page_content_fable(
    root: Path, item: dict[str, Any], leading_text: str
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": leading_text}]
    for page in item["rendered_pages"]:
        content.append(
            {
                "type": "text",
                "text": f"SOURCE {page['source_pdf']} PAGE {page['page']}",
            }
        )
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": _verified_image(root, page),
                },
            }
        )
    return content


def validate_candidate(candidate: dict[str, Any], item: dict[str, Any]) -> None:
    required = {
        "canary_id",
        "adequacy",
        "question",
        "expected_behavior",
        "gold_answer",
        "atomic_facts",
        "notes",
    }
    if not isinstance(candidate, dict) or not required <= set(candidate):
        missing = sorted(required - set(candidate if isinstance(candidate, dict) else {}))
        raise ValueError(f"candidate missing fields: {missing}")
    if candidate["canary_id"] != item["canary_id"]:
        raise ValueError("candidate canary_id mismatch")
    if candidate["adequacy"] == "INSUFFICIENT":
        if (
            candidate["question"] not in {"", None}
            or candidate["gold_answer"] not in {"", None}
            or candidate["atomic_facts"] != []
            or not isinstance(candidate["notes"], str)
            or not candidate["notes"].strip()
        ):
            raise ValueError("INSUFFICIENT response must be empty and explained")
        raise SemanticNoGo("candidate marked source insufficient")
    if candidate["adequacy"] != "SUFFICIENT":
        raise ValueError("candidate adequacy invalid")
    if candidate["expected_behavior"] != "answer":
        raise ValueError("expected_behavior must be answer")
    for key in ("question", "gold_answer", "notes"):
        if not isinstance(candidate[key], str):
            raise ValueError(f"{key} must be a string")
    if not candidate["question"].strip() or not candidate["gold_answer"].strip():
        raise ValueError("question and gold_answer must be non-empty")

    facts = candidate["atomic_facts"]
    if not isinstance(facts, list) or not 2 <= len(facts) <= 8:
        raise ValueError("atomic_facts cardinality must be 2..8")
    allowed = _allowed_pairs(item)
    ids: list[str] = []
    core = 0
    cross_source = 0
    sources_covered: set[str] = set()
    for fact in facts:
        required_fact = {
            "fact_id",
            "text",
            "type",
            "state",
            "value",
            "citations",
            "visual_evidence",
        }
        if not isinstance(fact, dict) or not required_fact <= set(fact):
            raise ValueError("fact shape invalid")
        ids.append(str(fact["fact_id"]))
        if fact["type"] not in {"core", "supplementary"}:
            raise ValueError("fact type invalid")
        core += fact["type"] == "core"
        if fact["state"] != "present":
            raise ValueError("fact state invalid")
        if any(
            not isinstance(fact[key], str) or not fact[key].strip()
            for key in ("text", "value")
        ):
            raise ValueError("fact text fields must be non-empty")

        citations = fact["citations"]
        if not isinstance(citations, list) or not 1 <= len(citations) <= 4:
            raise ValueError("fact citations cardinality must be 1..4")
        pairs: list[tuple[str, int]] = []
        for citation in citations:
            if not isinstance(citation, dict) or set(citation) != {"pdf", "page"}:
                raise ValueError("citation shape invalid")
            pair = (citation["pdf"], citation["page"])
            if pair not in allowed:
                raise ValueError("citation outside frozen source-page geometry")
            pairs.append(pair)
        if len(pairs) != len(set(pairs)):
            raise ValueError("citation source-page pairs must be unique")
        fact_sources = {pdf for pdf, _ in pairs}
        sources_covered.update(fact_sources)
        cross_source += len(fact_sources) > 1

        evidence = fact["visual_evidence"]
        if not isinstance(evidence, list) or len(evidence) != len(pairs):
            raise ValueError("visual evidence must cover every citation")
        evidence_pairs: list[tuple[str, int]] = []
        for receipt in evidence:
            if not isinstance(receipt, dict) or set(receipt) != {
                "pdf",
                "page",
                "evidence",
            }:
                raise ValueError("visual evidence shape invalid")
            if not isinstance(receipt["evidence"], str) or not receipt["evidence"].strip():
                raise ValueError("visual evidence text must be non-empty")
            evidence_pairs.append((receipt["pdf"], receipt["page"]))
        if set(evidence_pairs) != set(pairs) or len(evidence_pairs) != len(
            set(evidence_pairs)
        ):
            raise ValueError("visual evidence pairs must equal citation pairs")

    expected_ids = [f"F{index:02d}" for index in range(1, len(ids) + 1)]
    if ids != expected_ids or len(ids) != len(set(ids)):
        raise ValueError("fact IDs must be contiguous F01..")
    if core < 2:
        raise ValueError("candidate needs at least two core facts")
    if len(sources_covered) < int(item["distinct_sources_min"]):
        raise ValueError("candidate does not cover the required distinct sources")
    if cross_source < int(item["cross_source_facts_min"]):
        raise ValueError("candidate lacks a genuine cross-source fact")


def validate_review(
    review: dict[str, Any],
    reviewer: str,
    author: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    if review.get("reviewer_model") != reviewer:
        raise ValueError("reviewer model identity mismatch")
    if review.get("candidate_author") != author:
        raise ValueError("candidate author identity mismatch")
    rows = review.get("reviews")
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("review must cover exactly one candidate")
    row = rows[0]
    if row.get("canary_id") != candidate["canary_id"]:
        raise ValueError("review canary identity mismatch")
    if row.get("verdict") not in {"PASS", "FAIL"}:
        raise ValueError("review verdict invalid")
    boolean_fields = (
        "question_fully_answerable",
        "question_duplicate",
        "topic_aligned",
        "gold_complete",
        "source_geometry_valid",
        "known_conflicts_handled",
        "counterpart_materially_agrees",
    )
    list_fields = (
        "material_disagreements",
        "unsupported_answer_claims",
        "blocking_issues",
        "nonblocking_notes",
    )
    if any(not isinstance(row.get(field), bool) for field in boolean_fields):
        raise ValueError("review condition boolean missing")
    if any(not isinstance(row.get(field), list) for field in list_fields):
        raise ValueError("review issue list missing")
    expected_facts = {fact["fact_id"] for fact in candidate["atomic_facts"]}
    fact_rows = row.get("fact_verdicts")
    if (
        not isinstance(fact_rows, list)
        or {fact.get("fact_id") for fact in fact_rows} != expected_facts
    ):
        raise ValueError("review fact coverage mismatch")
    for fact in fact_rows:
        for field in (
            "supported",
            "source_pages_correct",
            "answer_entails",
            "genuinely_cross_source",
        ):
            if not isinstance(fact.get(field), bool):
                raise ValueError("review fact boolean missing")
        if not isinstance(fact.get("notes"), str):
            raise ValueError("review fact notes missing")
    conditions = review_row_passes(row)
    if (row["verdict"] == "PASS") != conditions:
        raise ValueError("review verdict contradicts its fields")
    return row


def review_row_passes(row: dict[str, Any]) -> bool:
    return (
        row.get("question_fully_answerable") is True
        and row.get("question_duplicate") is False
        and row.get("topic_aligned") is True
        and row.get("gold_complete") is True
        and row.get("source_geometry_valid") is True
        and row.get("known_conflicts_handled") is True
        and row.get("counterpart_materially_agrees") is True
        and not row.get("material_disagreements")
        and not row.get("unsupported_answer_claims")
        and not row.get("blocking_issues")
        and all(
            fact.get("supported") is True
            and fact.get("source_pages_correct") is True
            and fact.get("answer_entails") is True
            for fact in row.get("fact_verdicts") or []
        )
    )


def principal_publication_gate(
    independent_review_of_principal: dict[str, Any],
    principal_review_of_independent: dict[str, Any],
) -> bool:
    principal_rows = independent_review_of_principal.get("reviews") or []
    counterpart_rows = principal_review_of_independent.get("reviews") or []
    if len(principal_rows) != 1 or len(counterpart_rows) != 1:
        return False
    return (
        review_row_passes(principal_rows[0])
        and counterpart_rows[0].get("topic_aligned") is True
        and counterpart_rows[0].get("counterpart_materially_agrees") is True
        and not counterpart_rows[0].get("material_disagreements")
    )


def validate_support_mapping(
    value: dict[str, Any],
    candidate: dict[str, Any],
    item: dict[str, Any],
    mapper_model: str,
) -> dict[str, list[list[str]]]:
    if value.get("mapper_model") != mapper_model:
        raise ValueError("support mapper model identity mismatch")
    rows = value.get("mappings")
    if (
        not isinstance(rows, list)
        or len(rows) != 1
        or rows[0].get("canary_id") != candidate["canary_id"]
    ):
        raise ValueError("support mapping item coverage mismatch")
    unit_by_id = {unit["unit_id"]: unit for unit in item["evidence_units"]}
    fact_by_id = {fact["fact_id"]: fact for fact in candidate["atomic_facts"]}
    facts = rows[0].get("facts")
    if (
        not isinstance(facts, list)
        or {fact.get("fact_id") for fact in facts} != set(fact_by_id)
        or len(facts) != len(fact_by_id)
    ):
        raise ValueError("support mapping fact coverage mismatch")
    result: dict[str, list[list[str]]] = {}
    for mapping in facts:
        fact_id = mapping["fact_id"]
        alternatives = mapping.get("alternative_support_unit_id_sets")
        if not isinstance(alternatives, list) or len(alternatives) > 4:
            raise ValueError("invalid alternative support sets")
        support_sets = [mapping.get("support_unit_ids"), *alternatives]
        declared = {
            (citation["pdf"], int(citation["page"]))
            for citation in fact_by_id[fact_id]["citations"]
        }
        normalized: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        for support_set in support_sets:
            if (
                not isinstance(support_set, list)
                or not 1 <= len(support_set) <= 8
                or any(not isinstance(unit_id, str) for unit_id in support_set)
                or len(support_set) != len(set(support_set))
                or not set(support_set).issubset(unit_by_id)
            ):
                raise ValueError("invalid support unit IDs")
            identity = tuple(sorted(support_set))
            if identity in seen:
                raise ValueError("duplicate support-equivalent set")
            seen.add(identity)
            mapped = {
                (
                    unit_by_id[unit_id]["source_pdf"],
                    int(unit_by_id[unit_id]["page"]),
                )
                for unit_id in support_set
            }
            if mapped != declared:
                raise ValueError("support source-pages do not equal citations")
            normalized.append(list(support_set))
        result[fact_id] = normalized
    return result


def validate_support_review(
    value: dict[str, Any],
    candidate: dict[str, Any],
    reviewer_model: str,
    mapper_model: str,
) -> bool:
    if value.get("reviewer_model") != reviewer_model:
        raise ValueError("support reviewer model identity mismatch")
    if value.get("mapper_model") != mapper_model:
        raise ValueError("support mapper identity mismatch")
    rows = value.get("reviews")
    if (
        not isinstance(rows, list)
        or len(rows) != 1
        or rows[0].get("canary_id") != candidate["canary_id"]
    ):
        raise ValueError("support review item coverage mismatch")
    row = rows[0]
    if row.get("verdict") not in {"PASS", "FAIL"}:
        raise ValueError("support review verdict invalid")
    if not isinstance(row.get("blocking_issues"), list):
        raise ValueError("support review blocking issues missing")
    expected = {fact["fact_id"] for fact in candidate["atomic_facts"]}
    fact_rows = row.get("fact_reviews")
    if (
        not isinstance(fact_rows, list)
        or len(fact_rows) != len(expected)
        or {fact.get("fact_id") for fact in fact_rows} != expected
    ):
        raise ValueError("support review fact coverage mismatch")
    conditions = not row["blocking_issues"]
    for fact in fact_rows:
        if not isinstance(fact.get("issues"), list):
            raise ValueError("support review fact issues missing")
        conditions = conditions and not fact["issues"] and all(
            fact.get(field) is True
            for field in (
                "pixel_supported",
                "unit_text_supported",
                "minimal_complete",
                "citation_source_pages_complete",
                "alternative_paths_complete",
            )
        )
    if (row["verdict"] == "PASS") != conditions:
        raise ValueError("support review verdict contradicts its fields")
    return conditions
