"""s74 / Lever 1 sub-fix 2c — la ventana del preview del reranker LLM es configurable
por RERANK_PREVIEW_CHARS, con default 800 = comportamiento histórico (prod inerte).

Paridad de PROMPT (no de SHA): el dúo s74 señaló que cambiar `[:800]` → `[:RERANK_PREVIEW_CHARS]`
cambia el `rerank_fn_sha` del manifest legítimamente; lo que importa es que a 800 el reranker VEA
exactamente lo de antes. Estos tests mockean el cliente Anthropic para CAPTURAR el prompt y verificar
qué porción de cada chunk se expone, sin llamar a la API.
"""
import anthropic
import pytest

from src.rag import reranker


class _FakeResp:
    def __init__(self, text):
        self.content = [type("Block", (), {"text": text})()]


def _make_fake_anthropic(captured):
    class _FakeMessages:
        def create(self, **kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _FakeResp("[0, 1, 2, 3, 4]")

    class _FakeClient:
        def __init__(self, *a, **k):
            self.messages = _FakeMessages()

    return _FakeClient


def _chunks(n=6):
    # Cada chunk: 'A'*1000 + SENTINEL en char 1000 + 'C'*1500 + SENTINEL en char ~2514.
    out = []
    for i in range(n):
        content = (
            "A" * 1000 + f"SENTINEL1000_{i}" + "C" * 1500 + f"SENTINEL2514_{i}" + "D" * 1000
        )
        out.append(
            {
                "content": content,
                "product_model": f"M{i}",
                "section_title": "Sec",
                "content_type": "procedure",
            }
        )
    return out


def test_preview_default_800_is_inert(monkeypatch):
    """Default (800): el reranker ve exactamente content[:800] — el sentinel del char 1000 NO aparece."""
    captured = {}
    monkeypatch.setattr(anthropic, "Anthropic", _make_fake_anthropic(captured))
    assert reranker.RERANK_PREVIEW_CHARS == 800  # prod inerte por defecto
    reranker.rerank_chunks("pregunta", _chunks(), top_k=5)
    prompt = captured["prompt"]
    assert "A" * 800 in prompt                 # los primeros 800 chars SÍ
    assert "SENTINEL1000_0" not in prompt       # nada más allá del char 800


def test_preview_widened_includes_beyond_800_but_bounded(monkeypatch):
    """A 2400: el sentinel del char 1000 aparece; el del char ~2514 sigue truncado (ventana real)."""
    captured = {}
    monkeypatch.setattr(anthropic, "Anthropic", _make_fake_anthropic(captured))
    monkeypatch.setattr(reranker, "RERANK_PREVIEW_CHARS", 2400)
    reranker.rerank_chunks("pregunta", _chunks(), top_k=5)
    prompt = captured["prompt"]
    assert "SENTINEL1000_0" in prompt            # ahora visible (1000 < 2400)
    assert "SENTINEL2514_0" not in prompt        # sigue fuera (2514 > 2400) → ventana acotada, no ilimitada
