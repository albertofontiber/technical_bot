"""Tests del dispatcher del reranker (s61, evals/_s61_lever_design.md §4).

Cubren: default llm · flag voyage · dispatch condicional Y1 (target_models →
LLM aunque el flag sea voyage) · short-circuit etiquetado · header de paridad
2.0 (expresiones literales de rerank_chunks, quirk None incluido) · strict
(fail-open → RerankStrictError) · provenance por chunk. Sin red: los backends
se monkeypatchean.
"""

import pytest

import src.rag.reranker as rr
from src.rag.reranker import RerankStrictError, _voyage_doc, rerank


def _chunks(n: int) -> list[dict]:
    return [
        {
            "id": i,
            "content": f"contenido {i}",
            "product_model": f"MOD-{i}",
            "section_title": f"Sección {i}",
            "content_type": "prose",
        }
        for i in range(n)
    ]


def _mark_calls(monkeypatch, name):
    calls = []

    def stub(query, chunks, top_k=5, **kwargs):
        calls.append(kwargs)
        return chunks[:top_k]

    monkeypatch.setattr(rr, name, stub)
    return calls


def test_default_backend_is_llm(monkeypatch):
    monkeypatch.setattr(rr, "RERANKER_BACKEND", "llm")
    llm_calls = _mark_calls(monkeypatch, "rerank_chunks")
    voyage_calls = _mark_calls(monkeypatch, "rerank_chunks_voyage")
    rerank("q", _chunks(8), top_k=5)
    assert len(llm_calls) == 1 and len(voyage_calls) == 0


def test_voyage_flag_without_targets_dispatches_voyage(monkeypatch):
    monkeypatch.setattr(rr, "RERANKER_BACKEND", "voyage")
    llm_calls = _mark_calls(monkeypatch, "rerank_chunks")
    voyage_calls = _mark_calls(monkeypatch, "rerank_chunks_voyage")
    rerank("q", _chunks(8), top_k=5)
    assert len(voyage_calls) == 1 and len(llm_calls) == 0


def test_voyage_flag_with_targets_keeps_llm(monkeypatch):
    # Dispatch condicional Y1: el path con target_models NO se midió en el A/B
    # → conserva el LLM aunque el flag global sea voyage.
    monkeypatch.setattr(rr, "RERANKER_BACKEND", "voyage")
    llm_calls = _mark_calls(monkeypatch, "rerank_chunks")
    voyage_calls = _mark_calls(monkeypatch, "rerank_chunks_voyage")
    rerank("q", _chunks(8), top_k=5, target_models=["CAD-250"])
    assert len(llm_calls) == 1 and len(voyage_calls) == 0


def test_short_circuit_tags_without_backend_call():
    # pool ≤ top_k: ningún backend corre (idéntico en ambos, reranker.py) y los
    # chunks quedan etiquetados para el assert de provenance del harness.
    chunks = _chunks(3)
    out = rerank("q", chunks, top_k=5)
    assert out == chunks
    assert all(c["rerank_backend_used"] == "short-circuit" for c in out)


def test_voyage_doc_header_paridad():
    c = _chunks(1)[0]
    doc = _voyage_doc(c)
    assert doc.startswith("Producto: MOD-0 | Sección: Sección 0 | Tipo: prose\n")
    assert doc.endswith("contenido 0")


def test_voyage_doc_quirk_none_es_paridad():
    # .get("section_title", "") con valor None devuelve None → "Sección: None".
    # Es el MISMO comportamiento del LLM-rerank (rerank_chunks, chunk_summaries):
    # paridad = misma cadena, quirk incluido (G5 r2). 27/384 chunks reales traen
    # section_title vacío/None.
    doc = _voyage_doc({"content": "x", "product_model": "M", "section_title": None})
    assert "Sección: None" in doc
    assert "Tipo: \n" in doc  # key ausente → default "" del .get


def test_voyage_doc_truncates_content():
    c = {"content": "y" * 9000, "product_model": "M", "section_title": "S", "content_type": "t"}
    doc = _voyage_doc(c)
    header, body = doc.split("\n", 1)
    assert len(body) == rr.VOYAGE_RERANK_DOC_CHARS


def test_voyage_strict_raises_on_failure(monkeypatch):
    def boom():
        raise RuntimeError("api caída")

    monkeypatch.setattr(rr, "_get_voyage_rerank_client", boom)
    chunks = _chunks(8)
    with pytest.raises(RerankStrictError):
        rr.rerank_chunks_voyage("q", chunks, top_k=5, strict=True)
    # prod (strict=False): fail-open al orden de entrada, ETIQUETADO (detectable).
    out = rr.rerank_chunks_voyage("q", chunks, top_k=5, strict=False)
    assert len(out) == 5
    assert all(c["rerank_backend_used"] == "fallback-truncate" for c in out)


class _FakeAnthropicMsg:
    def __init__(self, text):
        self.content = [type("B", (), {"text": text})()]


class _FakeAnthropic:
    def __init__(self, text):
        self._text = text
        self.messages = self

    def create(self, **kwargs):
        return _FakeAnthropicMsg(self._text)


def test_llm_not_a_list_strict_raises(monkeypatch):
    monkeypatch.setattr(
        rr.anthropic, "Anthropic", lambda api_key=None: _FakeAnthropic('{"no": "lista"}')
    )
    chunks = _chunks(8)
    with pytest.raises(RerankStrictError):
        rr.rerank_chunks("q", chunks, top_k=5, strict=True)
    out = rr.rerank_chunks("q", chunks, top_k=5, strict=False)
    assert all(c["rerank_backend_used"] == "fallback-truncate" for c in out)


def test_llm_padding_is_tagged(monkeypatch):
    # El LLM puede devolver <top_k legítimamente (el prompt lo permite); el relleno
    # re-inyecta orden de entrada → etiqueta distinta para que el harness lo REPORTE
    # (F6-v4: detectable, no escondido).
    monkeypatch.setattr(rr.anthropic, "Anthropic", lambda api_key=None: _FakeAnthropic("[2]"))
    chunks = _chunks(8)
    out = rr.rerank_chunks("q", chunks, top_k=5, strict=False)
    assert len(out) == 5
    assert out[0]["id"] == 2
    assert all(c["rerank_backend_used"] == "llm-padded" for c in out)


def test_llm_clean_ranking_tagged_llm(monkeypatch):
    monkeypatch.setattr(
        rr.anthropic, "Anthropic", lambda api_key=None: _FakeAnthropic("[4, 1, 7, 0, 3]")
    )
    chunks = _chunks(8)
    out = rr.rerank_chunks("q", chunks, top_k=5, strict=True)
    assert [c["id"] for c in out] == [4, 1, 7, 0, 3]
    assert all(c["rerank_backend_used"] == "llm" for c in out)
