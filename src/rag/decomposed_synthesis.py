"""Question-decomposed answer synthesis with lossless local assembly.

The decomposition stage sees only the user's question.  It never sees source
chunks, gold facts, benchmark identities, or previous answers.  Each validated
focus is answered independently by the normal generator with the complete
served context, and the resulting blocks are assembled without another model
call that could compress them again.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable


DECOMPOSED_SYNTHESIS_CONTRACT = "question_decomposed_synthesis_s216_v1"
MAX_FOCUSES = 6
MAX_FOCUS_CHARS = 280

DECOMPOSITION_SYSTEM = """You decompose a technical field-support question into the
smallest set of independently answerable focuses needed to answer every explicit part of the
question. You see the question only. Preserve product identity, operation, conditions, units,
requested list cardinality, and requested diagnostic/procedural scope in every focus where they
apply. Do not invent a requested fact, infer source contents, answer the question, or add generic
advice. A simple atomic question stays as one focus. Return only the structured decomposition."""


def decomposition_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["focuses"],
        "properties": {
            "focuses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["focus_id", "question"],
                    "properties": {
                        "focus_id": {
                            "type": "string",
                        },
                        "question": {
                            "type": "string",
                        },
                    },
                },
            }
        },
    }


def decomposition_output_format() -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "question_decomposition_s216",
            "strict": True,
            "schema": decomposition_schema(),
        },
        "verbosity": "low",
    }


def decomposition_payload(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    return json.dumps(
        {"untrusted_question": question.strip()},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_decomposition(value: dict[str, Any]) -> list[dict[str, str]]:
    if not isinstance(value, dict) or set(value) != {"focuses"}:
        raise ValueError("invalid decomposition object")
    raw = value["focuses"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_FOCUSES:
        raise ValueError("invalid focus cardinality")
    clean: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    for index, row in enumerate(raw, 1):
        if not isinstance(row, dict) or set(row) != {"focus_id", "question"}:
            raise ValueError("invalid focus object")
        focus_id = row["focus_id"]
        question = row["question"]
        if focus_id != f"focus_{index}" or focus_id in seen_ids:
            raise ValueError("focus IDs must be unique, contiguous, and ordered")
        if not isinstance(question, str):
            raise ValueError("focus question must be a string")
        question = re.sub(r"\s+", " ", question).strip()
        if not 8 <= len(question) <= MAX_FOCUS_CHARS:
            raise ValueError("focus question length is invalid")
        normalized = question.casefold()
        if normalized in seen_questions:
            raise ValueError("duplicate focus question")
        seen_ids.add(focus_id)
        seen_questions.add(normalized)
        clean.append({"focus_id": focus_id, "question": question})
    return clean


def focused_query(original_question: str, focus_question: str) -> str:
    """Create the query passed to the unchanged production generator."""
    if not original_question.strip() or not focus_question.strip():
        raise ValueError("original and focus questions are required")
    return (
        f"Consulta original del técnico: {original_question.strip()}\n"
        f"Parte que debes responder en este bloque: {focus_question.strip()}\n"
        "Responde únicamente esta parte, conservando el producto, las condiciones y "
        "el alcance de la consulta original."
    )


def cited_fragments(answer: str) -> list[int]:
    return [int(value) for value in re.findall(r"\[F(\d+)\]", answer or "")]


def invalid_citations(answer: str, fragment_count: int) -> list[int]:
    return sorted(
        {
            value
            for value in cited_fragments(answer)
            if not 1 <= value <= fragment_count
        }
    )


def assemble_blocks(
    original_question: str,
    focuses: list[dict[str, str]],
    answers: Iterable[dict[str, str]],
) -> tuple[str, dict[str, Any]]:
    """Assemble every validated block exactly once, without semantic rewriting."""
    answer_rows = list(answers)
    expected = [row["focus_id"] for row in focuses]
    observed = [row.get("focus_id") for row in answer_rows]
    if observed != expected:
        raise ValueError("answer blocks do not match the ordered focus plan")
    rendered: list[str] = []
    receipts: list[dict[str, str]] = []
    for focus, row in zip(focuses, answer_rows):
        answer = row.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("empty answer block")
        answer = answer.strip()
        rendered.append(f"## {focus['question']}\n\n{answer}")
        receipts.append(
            {
                "focus_id": focus["focus_id"],
                "focus_sha256": hashlib.sha256(
                    focus["question"].encode("utf-8")
                ).hexdigest(),
                "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            }
        )
    candidate = "\n\n---\n\n".join(rendered)
    return candidate, {
        "contract": DECOMPOSED_SYNTHESIS_CONTRACT,
        "original_question_sha256": hashlib.sha256(
            original_question.encode("utf-8")
        ).hexdigest(),
        "focus_count": len(focuses),
        "all_focuses_assembled_once": len(receipts) == len(focuses),
        "blocks": receipts,
        "candidate_sha256": hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
    }
