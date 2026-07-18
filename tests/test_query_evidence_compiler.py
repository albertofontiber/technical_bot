from __future__ import annotations

import hashlib

import pytest

from src.rag.query_evidence_compiler import (
    EvidenceCandidate,
    append_to_answer,
    compile_evidence_appendix,
    deterministic_fallback_candidates,
    merge_candidate_pool,
    validate_claim_response,
    validate_plan,
    validate_verification,
)


def _chunk(content: str) -> dict:
    return {"id": "chunk-1", "content": content, "section_title": "Configuración"}


def _candidate(evidence_id: str, *, quote: str = "Pruebe todas las reglas.") -> EvidenceCandidate:
    return EvidenceCandidate(
        evidence_id=evidence_id,
        origin="model_exact_claim",
        facet="verification",
        claim_text="Verificar las reglas durante la puesta en marcha",
        exact_quote=quote,
        fragment_number=2,
        candidate_id="chunk-2",
        source_start=0,
        source_end=len(quote),
        quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
    )


def test_claims_are_bound_to_exact_source_and_whitespace_only_repair_is_audited():
    chunk = _chunk("Antes de iniciar la prueba, desconecte las salidas remotas.\nLuego verifique el panel.")
    value = {
        "claims": [
            {
                "facet": "prerequisite_safety",
                "claim_text": "Desconectar salidas remotas antes de probar",
                "exact_quote": "Antes de iniciar la prueba,   desconecte las salidas remotas.",
            },
            {
                "facet": "verification",
                "claim_text": "No está en la fuente",
                "exact_quote": "Texto inventado",
            },
        ]
    }
    claims, stats = validate_claim_response(value, chunk=chunk, fragment_number=1)
    assert len(claims) == 1
    assert claims[0].exact_quote in chunk["content"]
    assert stats == {
        "whitespace_only_repairs": 1,
        "invalid_quote_drops": 1,
        "duplicate_span_drops": 0,
    }


def test_duplicate_source_span_is_dropped_even_when_the_facet_differs():
    chunk = _chunk("El retardo se ajusta de 5 a 30 segundos.")
    value = {
        "claims": [
            {
                "facet": "configuration",
                "claim_text": "Ajustar el retardo",
                "exact_quote": chunk["content"],
            },
            {
                "facet": "threshold_default",
                "claim_text": "Rango del retardo",
                "exact_quote": chunk["content"],
            },
        ]
    }
    claims, stats = validate_claim_response(value, chunk=chunk, fragment_number=1)
    assert len(claims) == 1
    assert stats["duplicate_span_drops"] == 1


def test_deterministic_fallback_uses_only_exact_served_spans():
    chunks = [
        _chunk(
            "Para configurar el retardo de alarma, seleccione el valor y pruebe la salida.\n"
            "El intervalo permitido es de 5 a 30 segundos."
        )
    ]
    rows = deterministic_fallback_candidates(
        "¿Cómo configuro y pruebo el retardo de alarma?", chunks, max_candidates=4
    )
    assert rows
    assert all(row.exact_quote in chunks[0]["content"] for row in rows)
    assert all(row.origin == "deterministic_query_fallback" for row in rows)


def test_model_lane_wins_when_both_lanes_bind_the_same_span():
    model = _candidate("QE_same")
    fallback = EvidenceCandidate(**{**model.__dict__, "origin": "deterministic_query_fallback"})
    assert merge_candidate_pool([model], [fallback]) == [model]


def test_planner_and_verifier_fail_closed_on_unknown_or_contradictory_ids():
    candidates = [_candidate("QE_one"), _candidate("QE_two")]
    assert validate_plan({"evidence_ids": ["QE_one"]}, candidates) == ("QE_one",)
    with pytest.raises(ValueError, match="unknown"):
        validate_plan({"evidence_ids": ["QE_missing"]}, candidates)
    with pytest.raises(ValueError, match="complete verification"):
        validate_verification(
            {
                "status": "COMPLETE",
                "missing_facets": ["warning"],
                "additional_evidence_ids": [],
            },
            candidates,
            ("QE_one",),
        )
    status, facets, additions = validate_verification(
        {
            "status": "INCOMPLETE",
            "missing_facets": ["verification"],
            "additional_evidence_ids": ["QE_two"],
        },
        candidates,
        ("QE_one",),
    )
    assert (status, facets, additions) == (
        "INCOMPLETE",
        ("verification",),
        ("QE_two",),
    )


def test_compiler_renders_every_selected_exact_quote_with_valid_fragment_markers():
    candidates = [_candidate("QE_one"), _candidate("QE_two", quote="Evite lógicas contradictorias.")]
    appendix, receipts = compile_evidence_appendix(candidates, ["QE_two", "QE_one"])
    assert appendix.index("Evite lógicas") < appendix.index("Pruebe todas")
    assert appendix.count("[F2]") == 4
    assert [row["evidence_id"] for row in receipts] == ["QE_two", "QE_one"]
    answer = append_to_answer("Respuesta base [F1]", appendix)
    assert answer.startswith("Respuesta base [F1]\n\n---")
    assert "Evidencia adicional verificada" in answer


def test_compiler_never_accepts_duplicate_selection():
    with pytest.raises(ValueError, match="duplicate"):
        compile_evidence_appendix([_candidate("QE_one")], ["QE_one", "QE_one"])
