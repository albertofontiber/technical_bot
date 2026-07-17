"""Contrato de generate_answer tras la instrumentación del gate s58 (DEC-036b).

`stop_reason`/`output_tokens` se capturan de la respuesta Anthropic y se propagan en el
dict de retorno (antes no se capturaban — el gate de atribución los necesita para
confirmar/descartar truncamiento por max_tokens=2048). Los early-returns sin llamada LLM
devuelven stop_reason=None (distinguible de end_turn/max_tokens). Backward-compatible:
los callers existentes solo leen answer/diagrams.
"""
from types import SimpleNamespace

import src.rag.generator as gen
from src.rag.compatibility_bundle_coverage import build_compatibility_bundle
from src.rag.post_rerank_coverage import append_validated_coverage


class _FakeMessages:
    def __init__(self, stop_reason, output_tokens, text=None):
        self._stop_reason = stop_reason
        self._output_tokens = output_tokens
        self._text = text or "Respuesta técnica [F1].\nFuente: manual X (rev. 1)"
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text=self._text)],
            stop_reason=self._stop_reason,
            usage=SimpleNamespace(input_tokens=456, output_tokens=self._output_tokens),
        )


def _fake_anthropic(monkeypatch, stop_reason="end_turn", output_tokens=123, text=None):
    fake = _FakeMessages(stop_reason, output_tokens, text=text)
    monkeypatch.setattr(
        gen.anthropic, "Anthropic",
        lambda api_key=None: SimpleNamespace(messages=fake),
    )
    return fake


def _chunk(similarity=0.9):
    return {
        "content": "Texto del manual con el dato 42 V.",
        "similarity": similarity,
        "product_model": "CAD-250",
        "section_title": "Especificaciones",
        "content_type": "specs",
        "source_file": "manual_cad250.pdf",
    }


def test_stop_reason_propagado(monkeypatch):
    fake = _fake_anthropic(monkeypatch, stop_reason="end_turn", output_tokens=321)
    res = gen.generate_answer("¿Tensión del lazo de la CAD-250?", [_chunk()])
    assert res["stop_reason"] == "end_turn"
    assert res["input_tokens"] == 456
    assert res["output_tokens"] == 321
    assert res["answer"].startswith("Respuesta técnica")
    assert len(fake.calls) == 1
    # Los knobs que el gate vigila quedan en la llamada: max_tokens de config, temp=0.
    assert fake.calls[0]["max_tokens"] == gen.LLM_MAX_TOKENS
    assert fake.calls[0]["temperature"] == 0


def test_governed_evidence_view_reaches_prompt_before_generation(monkeypatch):
    fake = _fake_anthropic(monkeypatch)
    trace = {
        "status": "applied",
        "artifact_sha256": "a" * 64,
        "modified_rows": 1,
        "applied_derivations": [{"row_id": "source"}],
        "abstentions": [],
    }

    def derive(rows):
        derived = [dict(row) for row in rows]
        derived[0]["content"] = "Vida util: 10<sup>5</sup> operaciones."
        return derived, trace

    monkeypatch.setattr(gen, "apply_evidence_derivations_with_trace", derive)
    result = gen.generate_answer("Vida util del rele?", [_chunk()])

    prompt = fake.calls[0]["messages"][0]["content"]
    assert "10<sup>5</sup>" in prompt
    assert "Texto del manual con el dato 42 V" not in prompt
    assert result["evidence_derivation"] == trace


def test_stop_reason_max_tokens_visible(monkeypatch):
    _fake_anthropic(monkeypatch, stop_reason="max_tokens", output_tokens=2048)
    res = gen.generate_answer("¿Procedimiento completo de la central?", [_chunk()])
    assert res["stop_reason"] == "max_tokens"  # truncamiento DETECTABLE (antes invisible)


def test_early_return_sin_llm_stop_reason_none(monkeypatch):
    fake = _fake_anthropic(monkeypatch)
    # Todos los chunks bajo RELEVANCE_THRESHOLD (0.4) → early-return sin llamada API.
    res = gen.generate_answer("pregunta", [_chunk(similarity=0.1)])
    assert res["stop_reason"] is None
    assert res["input_tokens"] is None
    assert res["output_tokens"] is None
    assert "answer" in res and "diagrams" in res
    assert fake.calls == []  # NO hubo llamada LLM


def test_early_return_con_available_models(monkeypatch):
    fake = _fake_anthropic(monkeypatch)
    res = gen.generate_answer("pregunta", [], available_models=["CAD-250", "ZXe"])
    assert res["stop_reason"] is None
    assert res["input_tokens"] is None
    assert res["output_tokens"] is None
    assert fake.calls == []


def test_validated_post_rerank_source_bypasses_similarity_floor(monkeypatch):
    fake = _fake_anthropic(monkeypatch)
    chunk = _chunk(similarity=0.0)
    chunk.update(
        {
            "id": "source-parent",
            "retrieval_lane": "canonical_document_hyq_coverage_v1",
            "local_semantic_validated": True,
            "hyq_navigation_validated": True,
            "coverage_validated": True,
            "post_rerank_coverage": True,
            "coverage_cards": [
                {
                    "candidate_id": "source-parent",
                    "start": 0,
                    "end": len(chunk["content"]),
                    "quote": chunk["content"],
                    "exact_source_span_validated": True,
                }
            ],
        }
    )

    res = gen.generate_answer("pregunta", [chunk])

    assert res["stop_reason"] == "end_turn"
    assert len(fake.calls) == 1


def test_unvalidated_low_similarity_coverage_claim_is_rejected(monkeypatch):
    fake = _fake_anthropic(monkeypatch)
    chunk = _chunk(similarity=0.0)
    chunk.update(
        {
            "id": "source-parent",
            "retrieval_lane": "canonical_document_hyq_coverage_v1",
            "local_semantic_validated": True,
            "coverage_validated": True,
            "post_rerank_coverage": True,
            "coverage_cards": [{"quote": "not an exact receipt"}],
        }
    )

    res = gen.generate_answer("pregunta", [chunk])

    assert res["stop_reason"] is None
    assert fake.calls == []


def test_complete_cross_manufacturer_bundle_refuses_without_model_call(monkeypatch):
    fake = _fake_anthropic(
        monkeypatch,
        text="Sí, los equipos son compatibles.",
    )
    query = (
        "Tengo una central Detnov CAD-150 y un detector Notifier SDX-751; "
        "¿es compatible / puedo montarlo en su lazo?"
    )
    groups = [
        {
            "token": "CAD-150",
            "ids": ["detnov:cad-150-8"],
            "sources": ["host-manual"],
        },
        {
            "token": "SDX-751",
            "ids": ["notifier:sdx-751"],
            "sources": ["device-manual"],
        },
    ]
    specs = [
        ("p", "protocol_scope", "device-manual", "Protocolo P-CLIP.", "device-doc", "a" * 64, 1),
        ("r", "supported_device_roster", "device-manual", "Compatible: SDX-751.", "device-doc", "a" * 64, 2),
        ("t", "loop_topology", "host-manual", "Lazo cerrado con retorno.", "host-doc", "b" * 64, 3),
    ]
    rows = []
    for row_id, facet, source, content, document, extraction, index in specs:
        rows.append(
            {
                "id": row_id,
                "content": content,
                "source_file": source,
                "document_id": document,
                "extraction_sha256": extraction,
                "chunk_index": index,
                "similarity": 0.0,
                "coverage_cards": [
                    {
                        "candidate_id": row_id,
                        "start": 0,
                        "end": len(content),
                        "quote": content,
                        "facet": facet,
                        "exact_source_span_validated": True,
                    }
                ],
            }
        )
    served = append_validated_coverage(
        [], build_compatibility_bundle(query, rows, groups)
    )

    result = gen.generate_answer(query, served)

    assert fake.calls == []
    assert result["answer_policy"] == "source_bound_cross_manufacturer_refusal_v1"
    assert "No puedo confirmar la compatibilidad directa" in result["answer"]
    assert "Sí, los equipos son compatibles" not in result["answer"]
    assert result["input_tokens"] is None

    # If any row disappears after the serving seam, none of the remaining
    # compatibility rows may reach a model as ordinary partial evidence.
    partial_result = gen.generate_answer(query, served[:-1])
    assert fake.calls == []
    assert partial_result["stop_reason"] is None
    assert partial_result["answer_policy"] == (
        "incomplete_bundle_cross_manufacturer_guard_v1"
    )
    assert "No puedo confirmar la compatibilidad" in partial_result["answer"]

    tampered_attestation = [dict(row) for row in served]
    tampered_attestation[0] = dict(tampered_attestation[0])
    tampered_attestation[1] = dict(tampered_attestation[1])
    tampered_attestation[1]["coverage_validated"] = False
    tampered_result = gen.generate_answer(query, tampered_attestation)
    assert fake.calls == []
    assert tampered_result["stop_reason"] is None
    assert tampered_result["answer_policy"] == (
        "incomplete_bundle_cross_manufacturer_guard_v1"
    )
    assert "No puedo confirmar la compatibilidad" in tampered_result["answer"]


def test_active_compatibility_guard_refuses_on_collector_error_with_base_prefix(monkeypatch):
    fake = _fake_anthropic(monkeypatch, text="Sí, es compatible.")
    monkeypatch.setattr(gen, "COMPATIBILITY_BUNDLE_COVERAGE", True)
    query = (
        "Tengo una central Detnov CAD-150 y un detector Notifier SDX-751; "
        "¿es compatible / puedo montarlo en su lazo?"
    )

    result = gen.generate_answer(query, [_chunk(similarity=0.9)])

    assert fake.calls == []
    assert result["answer_policy"] == "incomplete_bundle_cross_manufacturer_guard_v1"
    assert "No puedo confirmar la compatibilidad" in result["answer"]


def test_guided_planner_injects_exact_obligation_before_generation(monkeypatch):
    fake = _fake_anthropic(monkeypatch)
    monkeypatch.setenv("ANSWER_OBLIGATION_PLANNER", "guided")
    chunk = {
        **_chunk(),
        "id": "inspire-capacity",
        "content": "El modulo de lazo proporciona un maximo de 750 mA por lazo.",
        "product_model": "INSPIRE E10",
    }
    result = gen.generate_answer(
        "Como se cablea el lazo de INSPIRE E10?", [chunk]
    )
    user_prompt = fake.calls[0]["messages"][0]["content"]
    assert "Plan de cobertura factual" in user_prompt
    assert "750 mA por lazo" in user_prompt
    assert result["answer"].startswith("Respuesta")
    assert "Fuente: manual X" in result["answer"]
    assert result["answer_planner"]["mode"] == "guided"
    assert result["answer_planner"]["validation"]["covered"] == 0


def _output_selector_chunk():
    chunk = _chunk()
    chunk.update(
        {
            "id": "id3000-output",
            "product_model": "ID3000",
            "content": (
                "Accion: Activar\nFuncion Especial: Circuito Sirena 1\n"
                "Seleccionar Equipos del Lazo: 1"
            ),
        }
    )
    return chunk


def test_enforced_contract_keeps_source_data_out_of_system_and_passes_once(monkeypatch):
    fake = _fake_anthropic(
        monkeypatch,
        text="Accion: Activar. Funcion Especial: Circuito Sirena 1 [F1].",
    )
    monkeypatch.setenv("ANSWER_OBLIGATION_PLANNER", "enforced")
    result = gen.generate_answer(
        "Como activo la salida de sirena de la ID3000?",
        [_output_selector_chunk()],
    )
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert "CONTRATO DE RESPUESTA SOURCE-BOUND" in call["system"]
    assert "<<<BEGIN_SOURCE_BOUND_ANSWER_CONTRACT_JSON>>>" not in call["system"]
    user_prompt = call["messages"][0]["content"]
    assert "<<<BEGIN_SOURCE_BOUND_ANSWER_CONTRACT_JSON>>>" in user_prompt
    assert "Circuito Sirena 1" in user_prompt
    assert result["answer_planner"]["action"] == "pass"
    assert "cache_identity" in result["answer_planner"]


def test_enforced_contract_reconstructs_locally_without_second_provider_call(monkeypatch):
    fake = _fake_anthropic(monkeypatch, text="Respuesta que omite la salida.")
    monkeypatch.setenv("ANSWER_OBLIGATION_PLANNER", "enforced")
    result = gen.generate_answer(
        "Como activo la salida de sirena de la ID3000?",
        [_output_selector_chunk()],
    )
    assert len(fake.calls) == 1
    assert result["answer_planner"]["action"] == "source_bound_reconstruction"
    assert "Respuesta que omite" not in result["answer"]
    assert "Circuito Sirena 1" in result["answer"]
