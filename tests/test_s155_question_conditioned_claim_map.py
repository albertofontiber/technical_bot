from __future__ import annotations

import pytest

from scripts.s155_question_conditioned_claim_map import (
    MAX_CLAIMS,
    SYSTEM,
    Job,
    build_jobs,
    response_schema,
    validate_response,
)


def test_s155_population_and_transport_contract():
    jobs, _ = build_jobs()
    assert len(jobs) == 65
    assert MAX_CLAIMS == 16
    assert "at most sixteen claims" in SYSTEM
    assert "maxItems" not in response_schema()["properties"]["claims"]


def test_s155_accepts_sixteen_and_rejects_seventeen_locally():
    job = Job("j", "target", "q", "question", "c", "x", "manual")
    claim = {"facet": "direct_answer", "claim_text": "x", "exact_quote": "x"}
    accepted, _ = validate_response({"claims": [claim] * 16}, job)
    # Exact duplicate spans are deterministically deduplicated after the cap.
    assert len(accepted) == 1
    with pytest.raises(RuntimeError, match="claim count"):
        validate_response({"claims": [claim] * 17}, job)

