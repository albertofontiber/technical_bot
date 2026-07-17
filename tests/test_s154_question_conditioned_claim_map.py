from __future__ import annotations

import pytest

from scripts.s154_question_conditioned_claim_map import (
    Job,
    build_jobs,
    independent_metrics,
    response_schema,
    validate_response,
)


def _job(content: str = "Antes del mantenimiento, desconecte las salidas remotas.") -> Job:
    return Job("j1", "independent", "q1", "¿Qué comprobar?", "c1", content, "manual")


def test_population_is_frozen_at_51_plus_14():
    jobs, _ = build_jobs()
    assert len(jobs) == 65
    assert sum(row.cohort == "target" for row in jobs) == 51
    assert sum(row.cohort == "independent" for row in jobs) == 14


def test_schema_forbids_model_authored_identity_fields():
    schema = response_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["claims"]["items"]["additionalProperties"] is False
    assert "chunk_id" not in schema["properties"]["claims"]["items"]["properties"]
    assert "maxItems" not in schema["properties"]["claims"]


def test_exact_quote_is_application_bound_and_auditable():
    value = {"claims": [{"facet": "prerequisite_safety",
                         "claim_text": "Disconnect remote outputs before maintenance.",
                         "exact_quote": "Antes del mantenimiento, desconecte las salidas remotas."}]}
    claims, stats = validate_response(value, _job())
    assert len(claims) == 1
    assert claims[0].chunk_id == "c1"
    assert claims[0].source_start == 0
    assert stats == {"whitespace_only_repairs": 0, "invalid_quote_drops": 0}


def test_unique_whitespace_only_quote_repair_is_allowed():
    value = {"claims": [{"facet": "direct_answer", "claim_text": "A B", "exact_quote": "A B"}]}
    claims, stats = validate_response(value, _job("A\n  B"))
    assert claims[0].exact_quote == "A\n  B"
    assert stats["whitespace_only_repairs"] == 1


def test_invalid_quote_is_dropped_not_inferred():
    value = {"claims": [{"facet": "direct_answer", "claim_text": "Invented", "exact_quote": "absent"}]}
    claims, stats = validate_response(value, _job())
    assert claims == []
    assert stats["invalid_quote_drops"] == 1


def test_schema_rejects_unknown_facet():
    with pytest.raises(RuntimeError, match="schema violation"):
        validate_response({"claims": [{"facet": "other", "claim_text": "x", "exact_quote": "x"}]}, _job("x"))


def test_application_enforces_the_claim_count_outside_provider_schema():
    claim = {"facet": "direct_answer", "claim_text": "x", "exact_quote": "x"}
    with pytest.raises(RuntimeError, match="claim count"):
        validate_response({"claims": [claim] * 11}, _job("x"))


def test_independent_metric_requires_material_quote_overlap():
    value = {"claims": [{"facet": "direct_answer", "claim_text": "Disconnect remote outputs.",
                         "exact_quote": "desconecte las salidas remotas"}]}
    claims, _ = validate_response(value, _job("Antes, desconecte las salidas remotas por seguridad."))
    metrics = independent_metrics(claims, {"q1": {"answer_points": [
        {"exact_quote": "Antes, desconecte las salidas remotas por seguridad."}
    ]}})
    assert metrics["useful_claim_precision"] == 1.0
