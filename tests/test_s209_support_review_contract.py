from __future__ import annotations

from copy import deepcopy

import pytest

from src.rag.planner_support_review import (
    SUPPORT_REVIEW_PROMPT_V4,
    validate_support_review_v4,
)


REVIEWER = "claude-fable-5"
MAPPER = "gpt-5.6-sol"
CANDIDATES = [
    {
        "canary_id": "fresh_multipage_item",
        "atomic_facts": [{"fact_id": "F01"}, {"fact_id": "F02"}],
    }
]


def _passing_review() -> dict:
    fact_reviews = []
    for fact_id in ("F01", "F02"):
        fact_reviews.append(
            {
                "fact_id": fact_id,
                "pixel_supported": True,
                "unit_text_supported": True,
                "minimal_complete": True,
                "citation_pages_complete": True,
                "alternative_paths_complete": True,
                "blocking_issues": [],
                "notes": [
                    "The declared pages and minimal unit set support this fact."
                ],
            }
        )
    return {
        "reviewer_model": REVIEWER,
        "mapper_model": MAPPER,
        "reviews": [
            {
                "canary_id": "fresh_multipage_item",
                "verdict": "PASS",
                "blocking_issues": [],
                "notes": ["All facts passed the independent audit."],
                "fact_reviews": fact_reviews,
            }
        ],
    }


def test_v4_prompt_separates_blockers_from_notes():
    assert "Use blocking_issues only for defects" in SUPPORT_REVIEW_PROMPT_V4
    assert "Notes never" in SUPPORT_REVIEW_PROMPT_V4
    assert '"blocking_issues":[],"notes":[]' in SUPPORT_REVIEW_PROMPT_V4
    assert '"issues"' not in SUPPORT_REVIEW_PROMPT_V4


def test_v4_accepts_positive_audit_notes_without_weakening_pass_gate():
    assert validate_support_review_v4(
        _passing_review(), CANDIDATES, REVIEWER, MAPPER
    )


def test_v4_rejects_positive_text_in_blocking_channel_for_pass():
    review = _passing_review()
    review["reviews"][0]["fact_reviews"][0]["blocking_issues"] = [
        "The mapped evidence is complete."
    ]
    with pytest.raises(ValueError, match="verdict contradicts"):
        validate_support_review_v4(review, CANDIDATES, REVIEWER, MAPPER)


def test_v4_requires_failed_fact_to_name_its_blocker():
    review = _passing_review()
    review["reviews"][0]["verdict"] = "FAIL"
    review["reviews"][0]["fact_reviews"][0]["minimal_complete"] = False
    with pytest.raises(ValueError, match="failed fact must identify"):
        validate_support_review_v4(review, CANDIDATES, REVIEWER, MAPPER)


def test_v4_accepts_explained_fail_and_returns_false():
    review = _passing_review()
    review["reviews"][0]["verdict"] = "FAIL"
    fact = review["reviews"][0]["fact_reviews"][0]
    fact["minimal_complete"] = False
    fact["blocking_issues"] = ["The primary set includes a redundant unit."]
    assert not validate_support_review_v4(review, CANDIDATES, REVIEWER, MAPPER)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda review: review["reviews"][0]["fact_reviews"][0].update(
            {"issues": []}
        ),
        lambda review: review["reviews"][0].update({"extra": "ambiguous"}),
        lambda review: review.update({"extra": "ambiguous"}),
    ),
)
def test_v4_rejects_legacy_or_extra_fields(mutation):
    review = deepcopy(_passing_review())
    mutation(review)
    with pytest.raises(ValueError, match="shape"):
        validate_support_review_v4(review, CANDIDATES, REVIEWER, MAPPER)


def test_v4_rejects_truthy_non_boolean_values():
    review = _passing_review()
    review["reviews"][0]["fact_reviews"][0]["pixel_supported"] = 1
    with pytest.raises(ValueError, match="booleans must be explicit"):
        validate_support_review_v4(review, CANDIDATES, REVIEWER, MAPPER)
