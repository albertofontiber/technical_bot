"""Current independent support-review contract for planner holdouts.

Historical contracts stay in :mod:`planner_holdout_gold` because their source
hashes are frozen by completed preregistrations. New cohorts use this module so
contract changes cannot rewrite prior evidence.
"""
from __future__ import annotations

from typing import Any


SUPPORT_REVIEW_PROMPT_V4 = """You are the independent reviewer of an immutable
multi-page support mapping authored by the other frontier model. Check every
frozen fact pixel by pixel, then verify that its mapped evidence units are the
smallest complete textual support. The mapped pages must equal the fact's
declared citation pages exactly. Do not repair, remap or rewrite. PASS an item
only when every fact is supported by all and only its cited pages and units.
Also verify that the mapper exhaustively enumerated every alternative minimal
complete support set in the supplied units, without admitting partial paths or
supersets.

Use blocking_issues only for defects that make the item or fact fail. Put
explanations, positive audit observations and other non-blocking commentary in
notes. A PASS must have every boolean true and no blocking issue. A FAIL must
name at least one blocking issue at the affected item or fact level. Notes never
change the verdict.

Return ONLY valid JSON and no extra fields:
{"reviewer_model":"claude-fable-5","mapper_model":"gpt-5.6-sol",
"reviews":[{"canary_id":"...","verdict":"PASS or FAIL",
"blocking_issues":[],"notes":[],"fact_reviews":[{"fact_id":"F01",
"pixel_supported":true,"unit_text_supported":true,
"minimal_complete":true,"citation_pages_complete":true,
"alternative_paths_complete":true,"blocking_issues":[],"notes":[]}]}]}
"""


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(row, str) and bool(row.strip()) for row in value
    )


def validate_support_review_v4(
    value: dict[str, Any],
    candidates: list[dict[str, Any]],
    reviewer_model: str,
    mapper_model: str,
) -> bool:
    """Validate the explicit blocking-versus-notes support-review contract.

    Booleans and blocking issues derive the verdict. Notes are retained for the
    audit trail but cannot turn a failure into a pass or a pass into a failure.
    """
    if set(value) != {"reviewer_model", "mapper_model", "reviews"}:
        raise ValueError("invalid support review top-level shape")
    if value.get("reviewer_model") != reviewer_model:
        raise ValueError("support reviewer model identity mismatch")
    if value.get("mapper_model") != mapper_model:
        raise ValueError("reviewed mapper model identity mismatch")
    candidate_by_id = {row["canary_id"]: row for row in candidates}
    rows = value.get("reviews")
    if (
        not isinstance(rows, list)
        or len(rows) != len(candidate_by_id)
        or any(not isinstance(row, dict) for row in rows)
        or {row.get("canary_id") for row in rows} != set(candidate_by_id)
    ):
        raise ValueError("support review item coverage mismatch")

    item_keys = {
        "canary_id",
        "verdict",
        "blocking_issues",
        "notes",
        "fact_reviews",
    }
    fact_keys = {
        "fact_id",
        "pixel_supported",
        "unit_text_supported",
        "minimal_complete",
        "citation_pages_complete",
        "alternative_paths_complete",
        "blocking_issues",
        "notes",
    }
    boolean_fields = (
        "pixel_supported",
        "unit_text_supported",
        "minimal_complete",
        "citation_pages_complete",
        "alternative_paths_complete",
    )
    all_pass = True
    for row in rows:
        if set(row) != item_keys:
            raise ValueError("invalid support review item shape")
        expected_facts = {
            fact["fact_id"]
            for fact in candidate_by_id[row["canary_id"]]["atomic_facts"]
        }
        fact_reviews = row["fact_reviews"]
        blocking = row["blocking_issues"]
        notes = row["notes"]
        if (
            not isinstance(fact_reviews, list)
            or len(fact_reviews) != len(expected_facts)
            or any(not isinstance(fact, dict) for fact in fact_reviews)
            or {fact.get("fact_id") for fact in fact_reviews} != expected_facts
            or not _string_list(blocking)
            or not _string_list(notes)
            or row["verdict"] not in {"PASS", "FAIL"}
        ):
            raise ValueError("invalid support review shape")

        facts_pass = True
        for fact in fact_reviews:
            if set(fact) != fact_keys:
                raise ValueError("invalid support review fact shape")
            fact_blocking = fact["blocking_issues"]
            fact_notes = fact["notes"]
            if not _string_list(fact_blocking) or not _string_list(fact_notes):
                raise ValueError("invalid support review fact commentary")
            if any(type(fact[field]) is not bool for field in boolean_fields):
                raise ValueError("support review fact booleans must be explicit")
            booleans_pass = all(fact[field] for field in boolean_fields)
            if not booleans_pass and not fact_blocking:
                raise ValueError("failed fact must identify a blocking issue")
            facts_pass = facts_pass and booleans_pass and not fact_blocking

        conditions = not blocking and facts_pass
        if (row["verdict"] == "PASS") != conditions:
            raise ValueError("support review verdict contradicts its fields")
        all_pass = all_pass and conditions
    return all_pass
