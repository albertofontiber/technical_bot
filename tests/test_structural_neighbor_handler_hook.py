import asyncio
import types

import src.bot.telegram_bot as bot


class _Message:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)


class _Update:
    def __init__(self):
        self.message = _Message()
        self.effective_user = types.SimpleNamespace(id=7)


def test_real_handler_shadow_exception_cannot_change_served_context_or_answer(monkeypatch):
    pool = [{"id": "pool", "content": "pool"}]
    served = [{"id": "served", "content": "evidencia exacta", "similarity": 1.0}]
    generator_inputs = []

    monkeypatch.setattr(bot, "extract_product_models", lambda _query: ["ID2000"])
    monkeypatch.setattr(bot, "retrieve_chunks", lambda *_args, **_kwargs: pool)
    monkeypatch.setattr(bot, "rerank", lambda *_args, **_kwargs: served)

    def broken_shadow(_query, observed):
        assert observed is served
        raise RuntimeError("observer failure")

    monkeypatch.setattr(bot, "observe_structural_neighbor_shadow", broken_shadow)

    def generate(_query, chunks, **_kwargs):
        generator_inputs.append(chunks)
        return {"answer": "respuesta estable", "diagrams": []}

    monkeypatch.setattr(bot, "generate_answer", generate)
    monkeypatch.setattr(bot, "log_query", lambda **_kwargs: None)
    update = _Update()
    context = types.SimpleNamespace(user_data={})

    asyncio.run(bot._process_query(update, context, "Conectar aislador ID2000"))

    assert generator_inputs == [served]
    assert update.message.replies == ["respuesta estable"]
