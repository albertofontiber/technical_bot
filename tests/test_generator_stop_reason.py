"""Contrato de generate_answer tras la instrumentación del gate s58 (DEC-036b).

`stop_reason`/`output_tokens` se capturan de la respuesta Anthropic y se propagan en el
dict de retorno (antes no se capturaban — el gate de atribución los necesita para
confirmar/descartar truncamiento por max_tokens=2048). Los early-returns sin llamada LLM
devuelven stop_reason=None (distinguible de end_turn/max_tokens). Backward-compatible:
los callers existentes solo leen answer/diagrams.
"""
from types import SimpleNamespace

import src.rag.generator as gen


class _FakeMessages:
    def __init__(self, stop_reason, output_tokens):
        self._stop_reason = stop_reason
        self._output_tokens = output_tokens
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text="Respuesta técnica [F1].\nFuente: manual X (rev. 1)")],
            stop_reason=self._stop_reason,
            usage=SimpleNamespace(output_tokens=self._output_tokens),
        )


def _fake_anthropic(monkeypatch, stop_reason="end_turn", output_tokens=123):
    fake = _FakeMessages(stop_reason, output_tokens)
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
    assert res["output_tokens"] == 321
    assert res["answer"].startswith("Respuesta técnica")
    assert len(fake.calls) == 1
    # Los knobs que el gate vigila quedan en la llamada: max_tokens de config, temp=0.
    assert fake.calls[0]["max_tokens"] == gen.LLM_MAX_TOKENS
    assert fake.calls[0]["temperature"] == 0


def test_stop_reason_max_tokens_visible(monkeypatch):
    _fake_anthropic(monkeypatch, stop_reason="max_tokens", output_tokens=2048)
    res = gen.generate_answer("¿Procedimiento completo de la central?", [_chunk()])
    assert res["stop_reason"] == "max_tokens"  # truncamiento DETECTABLE (antes invisible)


def test_early_return_sin_llm_stop_reason_none(monkeypatch):
    fake = _fake_anthropic(monkeypatch)
    # Todos los chunks bajo RELEVANCE_THRESHOLD (0.4) → early-return sin llamada API.
    res = gen.generate_answer("pregunta", [_chunk(similarity=0.1)])
    assert res["stop_reason"] is None
    assert res["output_tokens"] is None
    assert "answer" in res and "diagrams" in res
    assert fake.calls == []  # NO hubo llamada LLM


def test_early_return_con_available_models(monkeypatch):
    fake = _fake_anthropic(monkeypatch)
    res = gen.generate_answer("pregunta", [], available_models=["CAD-250", "ZXe"])
    assert res["stop_reason"] is None
    assert res["output_tokens"] is None
    assert fake.calls == []
