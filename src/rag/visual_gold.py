"""Reusable, fail-closed contract for pixel-grounded benchmark golds.

This module contains no provider or benchmark-specific execution policy.  It
defines the author/reviewer prompts, pixel-only payload construction and local
semantic validation shared by bounded frontier canaries.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any


class SemanticNoGo(RuntimeError):
    """The source or candidate is semantically insufficient, not unavailable."""


AUTHOR_PROMPT = """You are independently authoring ONE benchmark gold for a Spanish
technical RAG assistant used by fire-safety professionals. Use ONLY the supplied
manual page pixels. No OCR or extracted text is provided.

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
  them would contaminate a later retrieval evaluation and is also forbidden.
- Do not infer, recommend or invent an application, installation scenario,
  suitability claim or operating consequence unless the source pixels explicitly
  state it. Numeric limits alone never justify an application recommendation.
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
      "citation":{{"pdf":"{source_pdf}","page":1}},
      "visual_evidence":"short visible evidence"}}
  ],
  "notes": ""
}}
"""


REVIEW_PROMPT = """You are the independent pixel-level reviewer for benchmark
gold candidates written by the OTHER frontier model. Do not rewrite, repair or
merge candidates. Review every claim against the supplied manual page pixels.

For each candidate, PASS only if all conditions hold:
1. the Spanish question is realistic, self-contained, fully answerable from the
   supplied pages, and not a semantic duplicate of listed gold or retriever-
   augmentation coverage;
2. every atomic fact is visible on its cited FOCUS page, correctly scoped to the
   named model/mode, numerically exact, genuinely atomic, and entailed by the answer;
3. the answer is complete for the question and adds no unsupported technical claim;
4. citations use only the allowed PDF and focus pages;
5. there is no safety-significant ambiguity or material omission; and
6. no application, scenario, suitability or operating consequence is inferred
   merely from numeric specifications unless the pixels explicitly state it.

Classify findings by materiality. Put only findings that invalidate a gold in
blocking_issues. Put wording/style observations that do not affect correctness,
completeness, scope, safety or scoring in nonblocking_notes. A PASS may contain
nonblocking_notes but must have zero blocking_issues. A FAIL must identify at
least one blocking condition or blocking_issue. Keep verdict and fields consistent.

Return ONLY valid JSON:
{{"reviewer_model":"{reviewer_model}","candidate_author":"{candidate_author}",
  "reviews":[{{"canary_id":"...","verdict":"PASS or FAIL",
    "question_fully_answerable":true,"question_duplicate":false,
    "topic_aligned":true,"gold_complete":true,
    "counterpart_materially_agrees":true,"material_disagreements":[],
    "unsupported_answer_claims":[],"blocking_issues":[],
    "nonblocking_notes":[],
    "fact_verdicts":[{{"fact_id":"F01","supported":true,
      "page_correct":true,"answer_entails":true,"notes":""}}]}}]}}

Existing gold and retriever-augmentation questions and facts:
{existing_gold_coverage}
"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_sha(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def normalized_text_sha(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return sha256_bytes(text.encode("utf-8"))


def parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"provider output is not exact JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("provider output must be a JSON object")
    return value


def image_data(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii"), sha256_bytes(data)


def usage_dict(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        raw = usage.model_dump(mode="json", exclude_none=False)
        return {
            key: int(value or 0)
            for key, value in raw.items()
            if isinstance(value, (int, float))
        }
    keys = (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    )
    return {key: int(getattr(usage, key, 0) or 0) for key in keys}


def conservative_cost(
    receipts: list[dict[str, Any]], prices: dict[str, dict[str, float]]
) -> float:
    total = 0.0
    for receipt in receipts:
        usage = receipt.get("usage") or {}
        provider_prices = prices[receipt["provider"]]
        input_tokens = sum(
            int(usage.get(key, 0) or 0)
            for key in (
                "input_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
            )
        )
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        total += input_tokens / 1_000_000 * provider_prices["input"]
        total += output_tokens / 1_000_000 * provider_prices["output"]
    return round(total, 6)


def _verified_image(root: Path, page: dict[str, Any]) -> str:
    encoded, actual_sha = image_data(root / page["image"])
    if actual_sha != page["image_sha256"]:
        raise ValueError(f"image hash drift: {page['image']}")
    return encoded


def page_content_openai(
    root: Path, item: dict[str, Any], leading_text: str
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": leading_text}]
    for page in item["rendered_pages"]:
        encoded = _verified_image(root, page)
        content.append(
            {
                "type": "input_text",
                "text": f"SOURCE {item['source_pdf']} PAGE {page['page']}",
            }
        )
        content.append(
            {"type": "input_image", "image_url": f"data:image/png;base64,{encoded}"}
        )
    return content


def page_content_fable(
    root: Path, item: dict[str, Any], leading_text: str
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": leading_text}]
    for page in item["rendered_pages"]:
        encoded = _verified_image(root, page)
        content.append(
            {
                "type": "text",
                "text": f"SOURCE {item['source_pdf']} PAGE {page['page']}",
            }
        )
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": encoded,
                },
            }
        )
    return content


def author_prompt(packet: dict[str, Any], item: dict[str, Any]) -> str:
    return AUTHOR_PROMPT.format(
        canary_id=item["canary_id"],
        product=item["product"],
        topic=item["topic"],
        focus_pages=item["focus_pages"],
        source_pdf=item["source_pdf"],
        existing_gold_coverage=json.dumps(
            packet["existing_gold_coverage"], ensure_ascii=False
        ),
    )


def review_prompt(
    packet: dict[str, Any], reviewer_model: str, candidate_author: str
) -> str:
    return REVIEW_PROMPT.format(
        reviewer_model=reviewer_model,
        candidate_author=candidate_author,
        existing_gold_coverage=json.dumps(
            packet["existing_gold_coverage"], ensure_ascii=False
        ),
    )


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
    if not required <= set(candidate):
        raise ValueError(f"candidate missing fields: {sorted(required - set(candidate))}")
    if candidate["canary_id"] != item["canary_id"]:
        raise ValueError("candidate canary_id mismatch")
    if candidate["adequacy"] != "SUFFICIENT":
        raise SemanticNoGo("candidate marked source insufficient")
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
    for fact in facts:
        keys = {
            "fact_id",
            "text",
            "type",
            "state",
            "value",
            "citation",
            "visual_evidence",
        }
        if not isinstance(fact, dict) or not keys <= set(fact):
            raise ValueError("fact shape invalid")
        ids.append(str(fact["fact_id"]))
        if fact["type"] not in {"core", "supplementary"}:
            raise ValueError("fact type invalid")
        core += fact["type"] == "core"
        if fact["state"] != "present":
            raise ValueError("fact state invalid")
        for key in ("text", "value", "visual_evidence"):
            if not isinstance(fact[key], str) or not fact[key].strip():
                raise ValueError("fact text fields must be non-empty")
        citation = fact["citation"]
        if not isinstance(citation, dict) or set(citation) != {"pdf", "page"}:
            raise ValueError("fact citation shape invalid")
        if citation["pdf"] != item["source_pdf"]:
            raise ValueError("fact citation PDF invalid")
        if citation["page"] not in allowed_pages:
            raise ValueError("fact citation page outside frozen focus span")
    expected_ids = [f"F{index:02d}" for index in range(1, len(ids) + 1)]
    if len(ids) != len(set(ids)) or ids != expected_ids:
        raise ValueError("fact IDs must be contiguous F01..")
    if core < 2:
        raise ValueError("candidate needs at least two core facts")


def validate_review(
    review: dict[str, Any],
    reviewer: str,
    author: str,
    candidates: list[dict[str, Any]],
) -> None:
    if review.get("reviewer_model") != reviewer:
        raise ValueError("reviewer model identity mismatch")
    if review.get("candidate_author") != author:
        raise ValueError("candidate author identity mismatch")
    rows = review.get("reviews")
    if not isinstance(rows, list) or len(rows) != len(candidates):
        raise ValueError("review cardinality mismatch")
    candidate_map = {row["canary_id"]: row for row in candidates}
    if {row.get("canary_id") for row in rows} != set(candidate_map):
        raise ValueError("review canary identity mismatch")
    boolean_fields = (
        "question_fully_answerable",
        "question_duplicate",
        "topic_aligned",
        "gold_complete",
        "counterpart_materially_agrees",
    )
    list_fields = (
        "material_disagreements",
        "unsupported_answer_claims",
        "blocking_issues",
        "nonblocking_notes",
    )
    for row in rows:
        if row.get("verdict") not in {"PASS", "FAIL"}:
            raise ValueError("review verdict invalid")
        if any(not isinstance(row.get(field), bool) for field in boolean_fields):
            raise ValueError("review condition boolean missing")
        if any(not isinstance(row.get(field), list) for field in list_fields):
            raise ValueError("review issue list missing")
        candidate = candidate_map[row["canary_id"]]
        expected_fact_ids = {fact["fact_id"] for fact in candidate["atomic_facts"]}
        fact_rows = row.get("fact_verdicts")
        if not isinstance(fact_rows, list):
            raise ValueError("review fact verdicts missing")
        if {fact.get("fact_id") for fact in fact_rows} != expected_fact_ids:
            raise ValueError("review fact coverage mismatch")
        for fact in fact_rows:
            for field in ("supported", "page_correct", "answer_entails"):
                if not isinstance(fact.get(field), bool):
                    raise ValueError("review fact boolean missing")
        conditions_pass = _review_conditions_pass(row)
        if row["verdict"] == "PASS" and not conditions_pass:
            raise ValueError("PASS verdict contradicts blocking fields")
        if row["verdict"] == "FAIL" and conditions_pass:
            raise ValueError("FAIL verdict has no blocking reason")


def _review_conditions_pass(row: dict[str, Any]) -> bool:
    return (
        row.get("question_fully_answerable") is True
        and row.get("question_duplicate") is False
        and row.get("topic_aligned") is True
        and row.get("gold_complete") is True
        and row.get("counterpart_materially_agrees") is True
        and not row.get("material_disagreements")
        and not row.get("unsupported_answer_claims")
        and not row.get("blocking_issues")
        and all(
            fact.get("supported") is True
            and fact.get("page_correct") is True
            and fact.get("answer_entails") is True
            for fact in row.get("fact_verdicts") or []
        )
    )


def all_pass(review: dict[str, Any]) -> bool:
    rows = review.get("reviews")
    return bool(rows) and all(
        row.get("verdict") == "PASS" and _review_conditions_pass(row)
        for row in rows
    )


def sealed_artifact(schema: str, body: dict[str, Any]) -> dict[str, Any]:
    value = {"schema": schema, **body}
    value["result_sha256"] = stable_sha(value)
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
