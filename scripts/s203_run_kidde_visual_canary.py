#!/usr/bin/env python3
"""Run the bounded Sol/Fable Kidde visual-gold canary.

Three independent generations per model are followed by one batched cross-review
per model.  There are no retries, candidate merges, bot calls or database calls.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import anthropic
import yaml
from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = ROOT / "evals" / "s203_kidde_visual_canary_packet_v1.json"
PREREG_PATH = ROOT / "evals" / "s203_kidde_visual_canary_prereg_v1.yaml"
SOL_GENERATIONS = ROOT / "evals" / "s203_kidde_sol_generations_v1.json"
FABLE_GENERATIONS = ROOT / "evals" / "s203_kidde_fable_generations_v1.json"
SOL_REVIEW = ROOT / "evals" / "s203_kidde_sol_review_of_fable_v1.json"
FABLE_REVIEW = ROOT / "evals" / "s203_kidde_fable_review_of_sol_v1.json"
FINAL_GOLD = ROOT / "evals" / "s203_kidde_visual_gold_v1.json"
RESULT = ROOT / "evals" / "s203_kidde_visual_canary_result_v1.json"
CALL_LEDGER = ROOT / "evals" / "s203_kidde_frontier_call_ledger_v1.json"

SOL_MODEL = "gpt-5.6-sol"
FABLE_MODEL = "claude-fable-5"
SOL_REASONING = "xhigh"
MAX_CALLS = 8
INTERNAL_BUDGET_USD = 40.0
CONSERVATIVE_PRICES = {
    "sol": {"input": 15.0, "output": 120.0},
    "fable": {"input": 30.0, "output": 150.0},
}


class SemanticNoGo(RuntimeError):
    """The source or candidate is semantically insufficient, not unavailable."""


AUTHOR_PROMPT = """You are independently authoring ONE benchmark gold for a Spanish
technical RAG assistant used by fire-safety professionals. Use ONLY the supplied
Kidde manual page pixels. No OCR or extracted text is provided.

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
  cite exactly one supplied PDF page. A short visual_evidence phrase must point to
  the visible row, cell or sentence that supports it.
- Do not duplicate or paraphrase any existing benchmark question listed below.
- Use precise units, inequalities, states, button durations and model restrictions.
- If the pages cannot support a safe complete gold, set adequacy to INSUFFICIENT
  and explain why; do not invent a candidate.

Existing benchmark questions and facts to avoid semantically:
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


REVIEW_PROMPT = """You are the independent pixel-level reviewer for three benchmark
gold candidates written by the OTHER frontier model. Do not rewrite, repair or
merge candidates. Review every claim against the supplied Kidde page pixels.

For each candidate, PASS only if all conditions hold:
1. the Spanish question is realistic, self-contained, fully answerable from the
   supplied pages, and not a duplicate of the existing benchmark questions;
2. every atomic fact is visible on the cited page, correctly scoped to the named
   model/mode, numerically exact, genuinely atomic, and entailed by gold_answer;
3. gold_answer is complete for the question and adds no unsupported technical claim;
4. citations use only the allowed PDF and page span; and
5. there is no safety-significant ambiguity or material omission.

Return ONLY valid JSON:
{{"reviewer_model":"{reviewer_model}","candidate_author":"{candidate_author}",
  "reviews":[{{"canary_id":"...","verdict":"PASS or FAIL",
    "question_fully_answerable":true,"question_duplicate":false,
    "topic_aligned":true,"gold_complete":true,
    "counterpart_materially_agrees":true,"material_disagreements":[],
    "unsupported_answer_claims":[],"issues":[],
    "fact_verdicts":[{{"fact_id":"F01","supported":true,
      "page_correct":true,"answer_entails":true,"notes":""}}]}}]}}

Existing benchmark questions and facts:
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


def verify_prereg(packet: dict[str, Any]) -> None:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_FRONTIER_EXECUTION":
        raise ValueError("S203 preregistration is not frozen")
    for label, spec in prereg["frozen_inputs"].items():
        path = ROOT / spec["path"]
        if normalized_text_sha(path) != spec["sha256"]:
            raise ValueError(f"S203 frozen input drift: {label}")
    if prereg["packet_sha256"] != packet["packet_sha256"]:
        raise ValueError("S203 packet identity drift")
    if prereg["models"] != {
        "principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING},
        "independent": {"id": FABLE_MODEL},
    }:
        raise ValueError("S203 model contract drift")
    if prereg["execution"] != {
        "generation_calls_per_model": 3,
        "cross_review_calls_per_model": 1,
        "paid_calls_max": MAX_CALLS,
        "provider_retries": 0,
        "same_item_retry": False,
        "candidate_merge": False,
        "frontier_input": "pixel_only",
    }:
        raise ValueError("S203 execution contract drift")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_call_ledger(record: dict[str, Any]) -> None:
    if CALL_LEDGER.exists():
        ledger = json.loads(CALL_LEDGER.read_text(encoding="utf-8"))
        body = dict(ledger)
        expected = body.pop("result_sha256")
        if stable_sha(body) != expected:
            raise RuntimeError("frontier call ledger hash drift")
    else:
        ledger = {
            "schema": "s203_kidde_frontier_call_ledger_v1",
            "status": "IN_PROGRESS",
            "calls": [],
        }
    ledger.pop("result_sha256", None)
    ledger["calls"].append(record)
    ledger["conservative_cost_usd"] = conservative_cost(ledger["calls"])
    ledger["result_sha256"] = stable_sha(ledger)
    write_json(CALL_LEDGER, ledger)


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
        return {k: int(v or 0) for k, v in raw.items() if isinstance(v, (int, float))}
    keys = (
        "input_tokens", "output_tokens", "total_tokens",
        "cache_creation_input_tokens", "cache_read_input_tokens",
    )
    return {key: int(getattr(usage, key, 0) or 0) for key in keys}


def conservative_cost(receipts: list[dict[str, Any]]) -> float:
    total = 0.0
    for receipt in receipts:
        usage = receipt.get("usage") or {}
        prices = CONSERVATIVE_PRICES[receipt["provider"]]
        input_tokens = int(usage.get("input_tokens", 0) or 0)
        input_tokens += int(usage.get("cache_creation_input_tokens", 0) or 0)
        input_tokens += int(usage.get("cache_read_input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        total += input_tokens / 1_000_000 * prices["input"]
        total += output_tokens / 1_000_000 * prices["output"]
    return round(total, 6)


def page_content_openai(item: dict[str, Any], leading_text: str) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": leading_text}]
    for page in item["rendered_pages"]:
        path = ROOT / page["image"]
        b64, actual_sha = image_data(path)
        if actual_sha != page["image_sha256"]:
            raise ValueError(f"image hash drift: {page['image']}")
        content.append(
            {"type": "input_text", "text": (
                f"SOURCE {item['source_pdf']} PAGE {page['page']}"
            )}
        )
        content.append({"type": "input_image", "image_url": f"data:image/png;base64,{b64}"})
    return content


def page_content_fable(item: dict[str, Any], leading_text: str) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": leading_text}]
    for page in item["rendered_pages"]:
        path = ROOT / page["image"]
        b64, actual_sha = image_data(path)
        if actual_sha != page["image_sha256"]:
            raise ValueError(f"image hash drift: {page['image']}")
        content.append(
            {"type": "text", "text": (
                f"SOURCE {item['source_pdf']} PAGE {page['page']}"
            )}
        )
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": b64},
        })
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


def validate_candidate(candidate: dict[str, Any], item: dict[str, Any]) -> None:
    required = {"canary_id", "adequacy", "question", "expected_behavior", "gold_answer", "atomic_facts", "notes"}
    if not required <= set(candidate):
        raise ValueError(f"candidate missing fields: {sorted(required - set(candidate))}")
    if candidate["canary_id"] != item["canary_id"]:
        raise ValueError("candidate canary_id mismatch")
    if candidate["adequacy"] != "SUFFICIENT":
        raise SemanticNoGo("candidate marked source insufficient")
    if candidate["expected_behavior"] != "answer":
        raise ValueError("expected_behavior must be answer")
    if not all(isinstance(candidate[key], str) and candidate[key].strip() for key in ("question", "gold_answer")):
        raise ValueError("question and gold_answer must be non-empty strings")
    facts = candidate["atomic_facts"]
    if not isinstance(facts, list) or not 2 <= len(facts) <= 8:
        raise ValueError("atomic_facts cardinality must be 2..8")
    allowed_pages = set(item["focus_pages"])
    ids: list[str] = []
    core = 0
    for fact in facts:
        keys = {"fact_id", "text", "type", "state", "value", "citation", "visual_evidence"}
        if not isinstance(fact, dict) or not keys <= set(fact):
            raise ValueError("fact shape invalid")
        ids.append(str(fact["fact_id"]))
        if fact["type"] not in {"core", "supplementary"}:
            raise ValueError("fact type invalid")
        core += fact["type"] == "core"
        if fact["state"] != "present":
            raise ValueError("fact state invalid")
        if not all(isinstance(fact[key], str) and fact[key].strip() for key in ("text", "value", "visual_evidence")):
            raise ValueError("fact text fields must be non-empty")
        citation = fact["citation"]
        if citation != {"pdf": item["source_pdf"], "page": citation.get("page")}:
            raise ValueError("fact citation PDF or shape invalid")
        if citation["page"] not in allowed_pages:
            raise ValueError("fact citation page outside frozen span")
    if len(ids) != len(set(ids)) or ids != [f"F{i:02d}" for i in range(1, len(ids) + 1)]:
        raise ValueError("fact IDs must be contiguous F01..")
    if core < 2:
        raise ValueError("candidate needs at least two core facts")


def call_sol(
    client: OpenAI, content: list[dict[str, Any]], call_label: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = client.responses.create(
        model=SOL_MODEL,
        instructions="Follow the user contract exactly. Return only JSON.",
        input=[{"role": "user", "content": content}],
        reasoning={"effort": SOL_REASONING},
        max_output_tokens=12000,
        store=False,
    )
    raw = (getattr(response, "output_text", "") or "").strip()
    trace = response.model_dump(mode="json", exclude_none=False)
    receipt = {
        "provider": "sol",
        "call_label": call_label,
        "model": getattr(response, "model", None),
        "reasoning_effort": SOL_REASONING,
        "status": getattr(response, "status", None),
        "raw_output": raw,
        "usage": usage_dict(response),
        "provider_trace": trace,
    }
    append_call_ledger(receipt)
    if getattr(response, "model", None) != SOL_MODEL or getattr(response, "status", None) != "completed":
        raise RuntimeError(f"Sol incomplete or model mismatch: {getattr(response, 'status', None)} / {getattr(response, 'model', None)}")
    if not raw:
        raise RuntimeError("Sol completed with empty final output")
    return parse_json(raw), receipt


def call_fable(
    client: anthropic.Anthropic,
    content: list[dict[str, Any]],
    max_tokens: int,
    call_label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = client.messages.create(
        model=FABLE_MODEL,
        max_tokens=max_tokens,
        system="Follow the user contract exactly. Return only JSON.",
        messages=[{"role": "user", "content": content}],
    )
    raw = "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    trace = response.model_dump(mode="json", exclude_none=False)
    receipt = {
        "provider": "fable",
        "call_label": call_label,
        "model": getattr(response, "model", None),
        "status": getattr(response, "stop_reason", None),
        "raw_output": raw,
        "usage": usage_dict(response),
        "provider_trace": trace,
    }
    append_call_ledger(receipt)
    if getattr(response, "model", None) != FABLE_MODEL or getattr(response, "stop_reason", None) != "end_turn":
        raise RuntimeError(f"Fable incomplete or model mismatch: {getattr(response, 'stop_reason', None)} / {getattr(response, 'model', None)}")
    if not raw:
        raise RuntimeError("Fable completed with empty final output")
    return parse_json(raw), receipt


def persist_checkpoint(path: Path, provider: str, receipts: list[dict[str, Any]], status: str) -> None:
    body = {
        "schema": f"s203_{provider}_generation_receipts_v1",
        "status": status,
        "provider": provider,
        "receipts": receipts,
        "conservative_cost_usd": conservative_cost(receipts),
    }
    body["result_sha256"] = stable_sha(body)
    write_json(path, body)


def review_content_openai(
    packet: dict[str, Any],
    candidates: list[dict[str, Any]],
    counterparts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prompt = REVIEW_PROMPT.format(
        reviewer_model=SOL_MODEL,
        candidate_author=FABLE_MODEL,
        existing_gold_coverage=json.dumps(
            packet["existing_gold_coverage"], ensure_ascii=False
        ),
    )
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    by_id = {row["canary_id"]: row for row in candidates}
    counterpart_by_id = {row["canary_id"]: row for row in counterparts}
    for item in packet["items"]:
        content.extend(page_content_openai(item, (
            f"PRE-FROZEN TOPIC: {item['topic']}\nFOCUS PAGES: {item['focus_pages']}\n"
            f"CANDIDATE TO REVIEW:\n{json.dumps(by_id[item['canary_id']], ensure_ascii=False)}\n"
            f"INDEPENDENT COUNTERPART FOR DISAGREEMENT CHECK:\n"
            f"{json.dumps(counterpart_by_id[item['canary_id']], ensure_ascii=False)}"
        )))
    return content


def review_content_fable(
    packet: dict[str, Any],
    candidates: list[dict[str, Any]],
    counterparts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prompt = REVIEW_PROMPT.format(
        reviewer_model=FABLE_MODEL,
        candidate_author=SOL_MODEL,
        existing_gold_coverage=json.dumps(
            packet["existing_gold_coverage"], ensure_ascii=False
        ),
    )
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    by_id = {row["canary_id"]: row for row in candidates}
    counterpart_by_id = {row["canary_id"]: row for row in counterparts}
    for item in packet["items"]:
        content.extend(page_content_fable(item, (
            f"PRE-FROZEN TOPIC: {item['topic']}\nFOCUS PAGES: {item['focus_pages']}\n"
            f"CANDIDATE TO REVIEW:\n{json.dumps(by_id[item['canary_id']], ensure_ascii=False)}\n"
            f"INDEPENDENT COUNTERPART FOR DISAGREEMENT CHECK:\n"
            f"{json.dumps(counterpart_by_id[item['canary_id']], ensure_ascii=False)}"
        )))
    return content


def validate_review(review: dict[str, Any], reviewer: str, author: str, candidates: list[dict[str, Any]]) -> None:
    if review.get("reviewer_model") != reviewer or review.get("candidate_author") != author:
        raise ValueError("review model identity mismatch")
    rows = review.get("reviews")
    if not isinstance(rows, list) or len(rows) != len(candidates):
        raise ValueError("review cardinality mismatch")
    candidate_map = {row["canary_id"]: row for row in candidates}
    if {row.get("canary_id") for row in rows} != set(candidate_map):
        raise ValueError("review canary identity mismatch")
    for row in rows:
        candidate = candidate_map[row["canary_id"]]
        expected_fact_ids = {fact["fact_id"] for fact in candidate["atomic_facts"]}
        fact_rows = row.get("fact_verdicts")
        if not isinstance(fact_rows, list) or {fact.get("fact_id") for fact in fact_rows} != expected_fact_ids:
            raise ValueError("review fact coverage mismatch")
        if row.get("verdict") not in {"PASS", "FAIL"}:
            raise ValueError("review verdict invalid")
        for fact in fact_rows:
            for key in ("supported", "page_correct", "answer_entails"):
                if not isinstance(fact.get(key), bool):
                    raise ValueError("review fact boolean missing")


def all_pass(review: dict[str, Any]) -> bool:
    for row in review["reviews"]:
        if row["verdict"] != "PASS":
            return False
        if (
            row.get("question_fully_answerable") is not True
            or row.get("question_duplicate") is not False
            or row.get("topic_aligned") is not True
            or row.get("gold_complete") is not True
            or row.get("counterpart_materially_agrees") is not True
        ):
            return False
        if (
            row.get("material_disagreements")
            or row.get("unsupported_answer_claims")
            or row.get("issues")
        ):
            return False
        if not all(f["supported"] and f["page_correct"] and f["answer_entails"] for f in row["fact_verdicts"]):
            return False
    return True


def sealed_artifact(schema: str, body: dict[str, Any]) -> dict[str, Any]:
    value = {"schema": schema, **body}
    value["result_sha256"] = stable_sha(value)
    return value


def execute(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    planned_outputs = (
        CALL_LEDGER, SOL_GENERATIONS, FABLE_GENERATIONS, SOL_REVIEW,
        FABLE_REVIEW, FINAL_GOLD, RESULT
    )
    existing = [path.relative_to(ROOT).as_posix() for path in planned_outputs if path.exists()]
    if existing:
        raise RuntimeError(f"same-cohort execution artifacts already exist: {existing}")
    load_dotenv(ROOT / ".env", override=True)
    missing = [key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"missing provider credentials: {missing}")
    sol_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    fable_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0)
    all_receipts: list[dict[str, Any]] = []
    sol_candidates: list[dict[str, Any]] = []
    fable_candidates: list[dict[str, Any]] = []

    for item in packet["items"]:
        candidate, trace = call_sol(
            sol_client,
            page_content_openai(item, author_prompt(packet, item)),
            f"generate:{item['canary_id']}",
        )
        validate_candidate(candidate, item)
        receipt = {"provider": "sol", "model": SOL_MODEL, "reasoning_effort": SOL_REASONING, "canary_id": item["canary_id"], "candidate": candidate, **trace}
        sol_candidates.append(candidate)
        all_receipts.append(receipt)
        persist_checkpoint(SOL_GENERATIONS, "sol", [r for r in all_receipts if r["provider"] == "sol"], "IN_PROGRESS")
        if conservative_cost(all_receipts) > INTERNAL_BUDGET_USD:
            raise RuntimeError("conservative budget exceeded after Sol call")
    persist_checkpoint(SOL_GENERATIONS, "sol", [r for r in all_receipts if r["provider"] == "sol"], "COMPLETE")

    for item in packet["items"]:
        candidate, trace = call_fable(
            fable_client,
            page_content_fable(item, author_prompt(packet, item)),
            6000,
            f"generate:{item['canary_id']}",
        )
        validate_candidate(candidate, item)
        receipt = {"provider": "fable", "model": FABLE_MODEL, "canary_id": item["canary_id"], "candidate": candidate, **trace}
        fable_candidates.append(candidate)
        all_receipts.append(receipt)
        persist_checkpoint(FABLE_GENERATIONS, "fable", [r for r in all_receipts if r["provider"] == "fable"], "IN_PROGRESS")
        if conservative_cost(all_receipts) > INTERNAL_BUDGET_USD:
            raise RuntimeError("conservative budget exceeded after Fable call")
    persist_checkpoint(FABLE_GENERATIONS, "fable", [r for r in all_receipts if r["provider"] == "fable"], "COMPLETE")

    sol_review, sol_trace = call_sol(
        sol_client,
        review_content_openai(packet, fable_candidates, sol_candidates),
        "review:fable_candidates",
    )
    validate_review(sol_review, SOL_MODEL, FABLE_MODEL, fable_candidates)
    all_receipts.append({"provider": "sol", "model": SOL_MODEL, "reasoning_effort": SOL_REASONING, "phase": "review_fable", **sol_trace})
    sol_review_artifact = sealed_artifact("s203_sol_review_of_fable_v1", {"review": sol_review, "receipt": all_receipts[-1]})
    write_json(SOL_REVIEW, sol_review_artifact)
    if conservative_cost(all_receipts) > INTERNAL_BUDGET_USD:
        raise RuntimeError("conservative budget exceeded after Sol review")

    fable_review, fable_trace = call_fable(
        fable_client,
        review_content_fable(packet, sol_candidates, fable_candidates),
        10000,
        "review:sol_candidates",
    )
    validate_review(fable_review, FABLE_MODEL, SOL_MODEL, sol_candidates)
    all_receipts.append({"provider": "fable", "model": FABLE_MODEL, "phase": "review_sol", **fable_trace})
    fable_review_artifact = sealed_artifact("s203_fable_review_of_sol_v1", {"review": fable_review, "receipt": all_receipts[-1]})
    write_json(FABLE_REVIEW, fable_review_artifact)
    if conservative_cost(all_receipts) > INTERNAL_BUDGET_USD:
        raise RuntimeError("conservative budget exceeded after Fable review")

    if len(all_receipts) != MAX_CALLS:
        raise RuntimeError(f"call-contract drift: {len(all_receipts)} != {MAX_CALLS}")
    ledger = json.loads(CALL_LEDGER.read_text(encoding="utf-8"))
    ledger_body = dict(ledger)
    ledger_sha = ledger_body.pop("result_sha256")
    if stable_sha(ledger_body) != ledger_sha or len(ledger["calls"]) != MAX_CALLS:
        raise RuntimeError("frontier call ledger incomplete or corrupt")
    ledger.pop("result_sha256")
    ledger["status"] = "COMPLETE"
    ledger["result_sha256"] = stable_sha(ledger)
    write_json(CALL_LEDGER, ledger)

    passed = all_pass(sol_review) and all_pass(fable_review)
    status = "GO_KIDDE_GOLD_CANARY" if passed else "NO_GO_VISUAL_GOLD"
    if passed:
        rows = []
        for index, candidate in enumerate(sol_candidates, 1):
            item = packet["items"][index - 1]
            row = {
                "qid": f"s203k{index:02d}",
                **candidate,
                "split": "candidate_unintegrated",
                "source_pdf_sha256": item["source"]["sha256"],
                "pixel_sha256": [page["image_sha256"] for page in item["rendered_pages"]],
                "cross_review": {"fable_of_sol": "PASS", "sol_of_fable": "PASS"},
            }
            rows.append(row)
        write_json(FINAL_GOLD, sealed_artifact("s203_kidde_visual_gold_v1", {"status": status, "questions": rows, "official_fact_credit": 0}))

    result = sealed_artifact(
        "s203_kidde_visual_canary_result_v1",
        {
            "status": status,
            "calls": len(all_receipts),
            "models": {"principal": {"id": SOL_MODEL, "reasoning_effort": SOL_REASONING}, "independent": FABLE_MODEL},
            "generation": {"sol_valid": len(sol_candidates), "fable_valid": len(fable_candidates)},
            "cross_review": {"sol_of_fable_all_pass": all_pass(sol_review), "fable_of_sol_all_pass": all_pass(fable_review)},
            "conservative_cost_usd": conservative_cost(all_receipts),
            "conservative_prices_usd_per_million": CONSERVATIVE_PRICES,
            "budget_usd": INTERNAL_BUDGET_USD,
            "official_fact_credit": 0,
            "bot_evaluation_opened": False,
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
    )
    write_json(RESULT, result)
    print(json.dumps({"status": status, "calls": len(all_receipts), "conservative_cost_usd": result["conservative_cost_usd"]}, indent=2))
    return 0 if passed else 2


def preflight(packet: dict[str, Any]) -> int:
    verify_prereg(packet)
    body = dict(packet)
    expected = body.pop("packet_sha256")
    if stable_sha(body) != expected:
        raise ValueError("packet hash mismatch")
    images = 0
    for item in packet["items"]:
        for page in item["rendered_pages"]:
            data = (ROOT / page["image"]).read_bytes()
            if sha256_bytes(data) != page["image_sha256"]:
                raise ValueError(f"image hash mismatch: {page['image']}")
            images += 1
    if packet["generation_contract"] != {
        "principal": {"model": SOL_MODEL, "reasoning_effort": SOL_REASONING},
        "independent": {"model": FABLE_MODEL},
        "pixel_only_frontier_input": True,
        "independent_generation_before_cross_review": True,
        "final_gold_precedence": "sol_candidate_only_if_fable_pixel_review_passes",
        "fable_candidate_must_pass_sol_pixel_review": True,
        "merge_candidates": False,
        "same_item_retry": False,
    }:
        raise ValueError("packet generation contract drift")
    print(json.dumps({"status": "PREFLIGHT_PASS", "items": len(packet["items"]), "images": images, "paid_calls": 0}, indent=2))
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    if not args.execute:
        return preflight(packet)
    try:
        return execute(packet)
    except Exception as exc:
        if not RESULT.exists():
            paid_calls: list[dict[str, Any]] = []
            if CALL_LEDGER.exists():
                paid_calls = json.loads(
                    CALL_LEDGER.read_text(encoding="utf-8")
                ).get("calls") or []
            status = (
                "NO_GO_VISUAL_GOLD"
                if isinstance(exc, SemanticNoGo)
                else "HOLD_FRONTIER_INCOMPLETE"
            )
            failure = sealed_artifact(
                "s203_kidde_visual_canary_result_v1",
                {
                    "status": status,
                    "failure_type": type(exc).__name__,
                    "provider_responses_received": len(paid_calls),
                    "conservative_cost_usd": conservative_cost(paid_calls),
                    "same_item_retry": False,
                    "official_fact_credit": 0,
                    "bot_evaluation_opened": False,
                    "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
                    "railway_merge_gate": False,
                },
            )
            write_json(RESULT, failure)
        print(
            json.dumps(
                {
                    "status": (
                        "NO_GO_VISUAL_GOLD"
                        if isinstance(exc, SemanticNoGo)
                        else "HOLD_FRONTIER_INCOMPLETE"
                    ),
                    "failure_type": type(exc).__name__,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
