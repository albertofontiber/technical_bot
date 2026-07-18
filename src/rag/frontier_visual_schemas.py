"""Strict frontier-output schemas kept separate from frozen gold contracts."""
from __future__ import annotations

from typing import Any


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def _array(
    items: dict[str, Any], *, minimum: int | None = None, maximum: int | None = None
) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "array", "items": items}
    if minimum is not None:
        value["minItems"] = minimum
    if maximum is not None:
        value["maxItems"] = maximum
    return value


def candidate_schema(canary_id: str) -> dict[str, Any]:
    citation = _object(
        {"pdf": {"type": "string"}, "page": {"type": "integer", "minimum": 1}}
    )
    visual = _object(
        {
            "pdf": {"type": "string"},
            "page": {"type": "integer", "minimum": 1},
            "evidence": {"type": "string"},
        }
    )
    fact = _object(
        {
            "fact_id": {"type": "string"},
            "text": {"type": "string"},
            "type": {"type": "string", "enum": ["core", "supplementary"]},
            "state": {"type": "string", "enum": ["present"]},
            "value": {"type": "string"},
            "citations": _array(citation, minimum=0, maximum=4),
            "visual_evidence": _array(visual, minimum=0, maximum=4),
        }
    )
    return _object(
        {
            "canary_id": {"type": "string", "enum": [canary_id]},
            "adequacy": {
                "type": "string",
                "enum": ["SUFFICIENT", "INSUFFICIENT"],
            },
            "question": {"type": "string"},
            "expected_behavior": {"type": "string", "enum": ["answer"]},
            "gold_answer": {"type": "string"},
            "atomic_facts": _array(fact, minimum=0, maximum=8),
            "notes": {"type": "string"},
        }
    )


def review_schema(
    reviewer_model: str, candidate_author: str, canary_id: str
) -> dict[str, Any]:
    fact = _object(
        {
            "fact_id": {"type": "string"},
            "supported": {"type": "boolean"},
            "source_pages_correct": {"type": "boolean"},
            "answer_entails": {"type": "boolean"},
            "genuinely_cross_source": {"type": "boolean"},
            "notes": {"type": "string"},
        }
    )
    strings = _array({"type": "string"})
    row = _object(
        {
            "canary_id": {"type": "string", "enum": [canary_id]},
            "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
            "question_fully_answerable": {"type": "boolean"},
            "question_duplicate": {"type": "boolean"},
            "topic_aligned": {"type": "boolean"},
            "gold_complete": {"type": "boolean"},
            "source_geometry_valid": {"type": "boolean"},
            "known_conflicts_handled": {"type": "boolean"},
            "counterpart_materially_agrees": {"type": "boolean"},
            "material_disagreements": strings,
            "unsupported_answer_claims": strings,
            "blocking_issues": strings,
            "nonblocking_notes": strings,
            "fact_verdicts": _array(fact, minimum=0, maximum=8),
        }
    )
    return _object(
        {
            "reviewer_model": {"type": "string", "enum": [reviewer_model]},
            "candidate_author": {"type": "string", "enum": [candidate_author]},
            "reviews": _array(row, minimum=1, maximum=1),
        }
    )


def support_mapping_schema(mapper_model: str, canary_id: str) -> dict[str, Any]:
    ids = _array({"type": "string"}, minimum=1, maximum=8)
    fact = _object(
        {
            "fact_id": {"type": "string"},
            "support_unit_ids": ids,
            "alternative_support_unit_id_sets": _array(ids, maximum=4),
        }
    )
    mapping = _object(
        {
            "canary_id": {"type": "string", "enum": [canary_id]},
            "facts": _array(fact, minimum=2, maximum=8),
        }
    )
    return _object(
        {
            "mapper_model": {"type": "string", "enum": [mapper_model]},
            "mappings": _array(mapping, minimum=1, maximum=1),
        }
    )


def support_review_schema(
    reviewer_model: str, mapper_model: str, canary_id: str
) -> dict[str, Any]:
    fact = _object(
        {
            "fact_id": {"type": "string"},
            "pixel_supported": {"type": "boolean"},
            "unit_text_supported": {"type": "boolean"},
            "minimal_complete": {"type": "boolean"},
            "citation_source_pages_complete": {"type": "boolean"},
            "alternative_paths_complete": {"type": "boolean"},
            "issues": _array({"type": "string"}),
        }
    )
    row = _object(
        {
            "canary_id": {"type": "string", "enum": [canary_id]},
            "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
            "blocking_issues": _array({"type": "string"}),
            "fact_reviews": _array(fact, minimum=2, maximum=8),
        }
    )
    return _object(
        {
            "reviewer_model": {"type": "string", "enum": [reviewer_model]},
            "mapper_model": {"type": "string", "enum": [mapper_model]},
            "reviews": _array(row, minimum=1, maximum=1),
        }
    )


_ANTHROPIC_UNSUPPORTED_CONSTRAINTS = {
    "exclusiveMaximum",
    "exclusiveMinimum",
    "maxItems",
    "maxLength",
    "maxProperties",
    "maximum",
    "minItems",
    "minLength",
    "minProperties",
    "minimum",
    "multipleOf",
    "uniqueItems",
}


def anthropic_compatible_schema(value: Any) -> Any:
    """Strip provider-unsupported constraints; local validators retain them."""
    if isinstance(value, dict):
        return {
            key: anthropic_compatible_schema(item)
            for key, item in value.items()
            if key not in _ANTHROPIC_UNSUPPORTED_CONSTRAINTS
        }
    if isinstance(value, list):
        return [anthropic_compatible_schema(item) for item in value]
    return value
