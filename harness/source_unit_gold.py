"""Reusable contracts for binding frozen fact points to immutable source units.

The Anthropic-facing shape is deliberately static and rectangular.  Dynamic
identity, cardinality and membership constraints stay in deterministic local
validation; the provider schema therefore contains no arrays, enums, refs,
combinators or source-bound values.
"""
from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator


POINT_SLOTS = 6
SUPPORT_SLOTS = 6
FORBIDDEN_PROVIDER_KEYS = frozenset(
    {
        "$defs",
        "$ref",
        "allOf",
        "anyOf",
        "const",
        "contains",
        "enum",
        "maxItems",
        "minItems",
        "oneOf",
        "prefixItems",
        "uniqueItems",
    }
)


def _author_point_schema() -> dict[str, Any]:
    required = ["supported", *[f"support_{index}" for index in range(1, 7)]]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": {
            "supported": {"type": "boolean"},
            **{
                f"support_{index}": {"type": "string"}
                for index in range(1, 7)
            },
        },
    }


def static_author_schema() -> dict[str, Any]:
    """Return the source-independent six-by-six provider transport."""
    point_names = [f"point_{index}" for index in range(1, 7)]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["qid", "point_slots"],
        "properties": {
            "qid": {"type": "string"},
            "point_slots": {
                "type": "object",
                "additionalProperties": False,
                "required": point_names,
                "properties": {
                    point_name: _author_point_schema()
                    for point_name in point_names
                },
            },
        },
    }


def validate_static_author_schema(schema: dict[str, Any]) -> None:
    """Fail if provider-specific complexity leaks back into the transport."""
    Draft202012Validator.check_schema(schema)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            forbidden = FORBIDDEN_PROVIDER_KEYS.intersection(value)
            if forbidden:
                raise ValueError(
                    "static author schema contains forbidden keyword(s): "
                    + ", ".join(sorted(forbidden))
                )
            if value.get("type") == "array":
                raise ValueError("static author schema must not contain arrays")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)


def validate_static_author_output(
    value: dict[str, Any],
    *,
    qid: str,
    point_ids: list[str],
    known_unit_ids: set[str],
) -> list[dict[str, Any]]:
    """Normalize provider slots into ordered point mappings, failing closed."""
    if not 1 <= len(point_ids) <= POINT_SLOTS:
        raise ValueError("point count exceeds static transport")
    errors = sorted(
        Draft202012Validator(static_author_schema()).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise ValueError(f"provider grammar violation: {errors[0].message}")
    if value["qid"] != qid:
        raise ValueError("author qid identity mismatch")

    clean: list[dict[str, Any]] = []
    for index in range(1, POINT_SLOTS + 1):
        slot = value["point_slots"][f"point_{index}"]
        raw_supports = [
            slot[f"support_{support}"]
            for support in range(1, SUPPORT_SLOTS + 1)
        ]
        if any(raw != raw.strip() for raw in raw_supports):
            raise ValueError("support IDs must not contain outer whitespace")
        supports = [support for support in raw_supports if support]
        if raw_supports[: len(supports)] != supports:
            raise ValueError("support slots must be non-empty then empty")
        if len(supports) != len(set(supports)):
            raise ValueError("duplicate support-unit ID")
        if not set(supports).issubset(known_unit_ids):
            raise ValueError("unknown support-unit ID")

        if index > len(point_ids):
            if slot["supported"] or supports:
                raise ValueError("inactive point slot must be false and empty")
            continue
        supported = bool(slot["supported"])
        if supported and not supports:
            raise ValueError("supported point requires at least one unit")
        if not supported and supports:
            raise ValueError("unsupported point contains support units")
        clean.append(
            {
                "point_id": point_ids[index - 1],
                "supported": supported,
                "support_unit_ids": supports,
            }
        )
    return clean


def validator_schema(point_ids: list[str]) -> dict[str, Any]:
    """OpenAI structured-output contract for independent semantic validation."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["qid", "points"],
        "properties": {
            "qid": {"type": "string"},
            "points": {
                "type": "array",
                "minItems": len(point_ids),
                "maxItems": len(point_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "point_id",
                        "agrees_with_author",
                        "support_unit_sets",
                    ],
                    "properties": {
                        "point_id": {"type": "string", "enum": point_ids},
                        "agrees_with_author": {"type": "boolean"},
                        "support_unit_sets": {
                            "type": "array",
                            "maxItems": 3,
                            "items": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": SUPPORT_SLOTS,
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    }


def validate_validator_output(
    value: dict[str, Any],
    *,
    qid: str,
    author_points: list[dict[str, Any]],
    known_unit_ids: set[str],
) -> list[dict[str, Any]]:
    """Validate reviewer identity, set membership and agreement consistency."""
    point_ids = [str(row["point_id"]) for row in author_points]
    errors = sorted(
        Draft202012Validator(validator_schema(point_ids)).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise ValueError(f"validator grammar violation: {errors[0].message}")
    if value["qid"] != qid:
        raise ValueError("validator qid identity mismatch")
    observed = [str(row["point_id"]) for row in value["points"]]
    if len(set(observed)) != len(observed) or set(observed) != set(point_ids):
        raise ValueError("validator point identity mismatch")

    author_by_id = {str(row["point_id"]): row for row in author_points}
    validator_by_id = {str(row["point_id"]): row for row in value["points"]}
    clean: list[dict[str, Any]] = []
    for point_id in point_ids:
        author = author_by_id[point_id]
        row = validator_by_id[point_id]
        canonical_sets: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        for support_set in row["support_unit_sets"]:
            if len(support_set) != len(set(support_set)):
                raise ValueError("duplicate ID inside validator support set")
            if not set(support_set).issubset(known_unit_ids):
                raise ValueError("unknown ID inside validator support set")
            key = tuple(sorted(support_set))
            if key in seen:
                raise ValueError("duplicate validator support set")
            seen.add(key)
            canonical_sets.append(support_set)

        agrees = bool(row["agrees_with_author"])
        author_set = set(author["support_unit_ids"])
        if agrees and author["supported"]:
            if not canonical_sets or not any(
                set(support_set) == author_set for support_set in canonical_sets
            ):
                raise ValueError("validator agrees but omits author support set")
        if agrees and not author["supported"] and canonical_sets:
            raise ValueError("validator agrees with unsupported but supplies support")
        clean.append(
            {
                "point_id": point_id,
                "agrees_with_author": agrees,
                "support_unit_sets": canonical_sets,
            }
        )
    return clean
