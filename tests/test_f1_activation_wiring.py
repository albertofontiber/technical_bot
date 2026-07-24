"""S281 Phase-1 (F1) ACTIVATION wiring — telegram_bot ORCHESTRATOR_PATH branch
plus CONVERSATION_POLICY=impl (lane s281c-f1-activation).

The activation cables the deterministic conversational policy
(``resolve_conversational_turn``) into ``_process_query``, gated behind BOTH
``ORCHESTRATOR_PATH`` and ``CONVERSATION_POLICY=impl`` (default OFF). Coverage:

  (1) byte-invariance OFF     — flags default off => no working state, historical
      reply; ORCHESTRATOR_PATH on but the policy flag off keeps the MT-0d path.
  (2) carry-forward feeds gen — a 2-turn flow whose 2nd turn is a carry-forward:
      the GENERATION call receives the RESOLVED query (the measured e2e fix), not
      the raw follow-up.
  (3) clarify direct, $0      — a dangling first turn CLARIFYs directly: no
      retrieval, no generation, the pipeline is never entered.
  (4) excerpt backfill        — after a retrieving turn the durable working state
      carries the answer excerpt (the closed TODO).
  (5) rewriter laziness       — a $0 route never imports/constructs the rewriter.

RGPD / cost: everything runs on fakes (replay adapters + recording generate);
no DB, no network, no paid API. ``extract_product_models`` /
``get_category_models`` are patched so the policy's own detection is deterministic
and never touches Supabase.
"""

import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.orchestrator import replay_adapters
from src.orchestrator.conversation_policy import WorkingState


# --- fakes -------------------------------------------------------------------
class _Message:
    def __init__(self):
        self.replies = []
        self.photos = []
        self.media_groups = []

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)

    async def reply_photo(self, **kwargs):
        self.photos.append(kwargs)

    async def reply_media_group(self, media, **_kwargs):
        self.media_groups.append(media)


def _make_update(*, update_id=1, chat_id=2, user_id=7):
    return SimpleNamespace(
        message=_Message(),
        update_id=update_id,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
    )


_FIXTURE = [
    {
        "id": "chunk-1",
        "content": "La tensión nominal del lazo es 24 V CC.",
        "similarity": 0.93,
        "product_model": "CAD-250",
    }
]


def _recording_adapters(record):
    """Replay adapters whose generate records every served query (the exact
    string the writer sees) and returns a canned answer."""

    def _generate(query, chunks, *, available_models=None):
        record["generate_queries"].append(query)
        return {"answer": "La tensión del lazo es 24 V CC.", "diagrams": []}

    return replay_adapters(retrieved=_FIXTURE, generate=_generate)


@pytest.fixture
def f1_env(monkeypatch):
    """Activate F1 (ORCHESTRATOR_PATH + CONVERSATION_POLICY=impl) with the policy's
    detection stubbed offline. Returns a record dict + a from_production spy."""
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch
    import src.rag.retriever as retriever

    monkeypatch.setattr(bot, "ORCHESTRATOR_PATH", True)
    monkeypatch.setenv("CONVERSATION_POLICY", "impl")
    monkeypatch.setattr(bot, "log_query", lambda **k: None)

    # Deterministic, DB-free detection shared by handler + policy.
    monkeypatch.setattr(
        retriever, "extract_product_models",
        lambda q: ["CAD-250"] if "CAD-250" in q else [],
    )
    monkeypatch.setattr(retriever, "get_category_models", lambda cat: [])
    # The handler step 1a binding (used only on the non-F1 path here, patched for
    # symmetry so nothing hits the real extractor).
    monkeypatch.setattr(
        bot, "extract_product_models",
        lambda q: ["CAD-250"] if "CAD-250" in q else [],
    )

    record = {"generate_queries": [], "from_production_calls": 0}

    def _fake_from_production():
        record["from_production_calls"] += 1
        return _recording_adapters(record)

    monkeypatch.setattr(orch, "from_production", _fake_from_production)
    return record


# --- (1) byte-invariance OFF -------------------------------------------------
def test_conversation_policy_default_off():
    from src.orchestrator.conversation_policy_impl import conversation_policy_active

    # No CONVERSATION_POLICY set in the ambient env => stub route.
    assert conversation_policy_active() is False


def test_orchestrator_path_on_but_policy_off_keeps_mt0d_path(monkeypatch):
    """ORCHESTRATOR_PATH on, CONVERSATION_POLICY unset => f1_active False: the
    handler runs the MT-0d passthrough and never creates F1 working state."""
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch

    monkeypatch.delenv("CONVERSATION_POLICY", raising=False)
    monkeypatch.setattr(bot, "ORCHESTRATOR_PATH", True)
    monkeypatch.setattr(bot, "log_query", lambda **k: None)
    monkeypatch.setattr(bot, "extract_product_models", lambda q: [])

    def _gen(query, chunks, *, available_models=None):
        return {"answer": "MT0D-ANSWER", "diagrams": []}

    monkeypatch.setattr(
        orch, "from_production", lambda: replay_adapters(retrieved=_FIXTURE, generate=_gen)
    )

    update = _make_update()
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "pregunta tecnica generica"))

    assert update.message.replies == ["MT0D-ANSWER"]
    assert "mt_working_state" not in context.user_data  # F1 never activated


def test_flags_all_off_no_working_state(monkeypatch):
    """Default flags off => legacy inline pipeline, no F1 working state written."""
    import src.bot.telegram_bot as bot

    monkeypatch.delenv("CONVERSATION_POLICY", raising=False)
    monkeypatch.setattr(bot, "extract_product_models", lambda q: ["ID2000"])
    monkeypatch.setattr(bot, "retrieve_chunks", lambda *a, **k: [{"id": "p", "content": "P"}])
    monkeypatch.setattr(
        bot, "rerank", lambda *a, **k: [{"id": "s", "content": "S", "similarity": 1.0}]
    )
    monkeypatch.setattr(bot, "observe_structural_neighbor_shadow", lambda *a, **k: None)
    monkeypatch.setattr(
        bot, "generate_answer", lambda *a, **k: {"answer": "estable", "diagrams": []}
    )
    monkeypatch.setattr(bot, "log_query", lambda **k: None)

    update = _make_update()
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "Conectar aislador ID2000"))

    assert update.message.replies == ["estable"]
    assert "mt_working_state" not in context.user_data


# --- (2) carry-forward feeds the RESOLVED query to generation -----------------
def test_two_turn_carry_forward_generation_gets_resolved_query(f1_env):
    import src.bot.telegram_bot as bot

    context = SimpleNamespace(user_data={})

    # Turn 1: explicit product -> STANDALONE. The working state fixes CAD-250.
    u1 = _make_update(update_id=1, chat_id=42)
    asyncio.run(
        bot._process_query(u1, context, "¿Cuál es la tensión del lazo de la CAD-250?")
    )
    ws = context.user_data["mt_working_state"]
    assert isinstance(ws, WorkingState)
    assert ws.last_target_models == ("CAD-250",)

    # Turn 2: product-less follow-up within the window -> CARRY_FORWARD.
    u2 = _make_update(update_id=2, chat_id=42)
    asyncio.run(bot._process_query(u2, context, "¿y su tensión?"))

    # The GENERATION call for turn 2 saw the RESOLVED query, not the raw follow-up
    # (the measured e2e fix: the resolved query feeds retrieval AND generation).
    served_turn2 = f1_env["generate_queries"][1]
    assert served_turn2 == "¿y su tensión? (contexto: CAD-250)"
    assert "CAD-250" in served_turn2

    # Turn 1 generation saw the raw (== resolved) standalone query.
    assert f1_env["generate_queries"][0] == "¿Cuál es la tensión del lazo de la CAD-250?"

    # The carry-forward kept the product in the durable state.
    assert context.user_data["mt_working_state"].last_target_models == ("CAD-250",)


# --- (3) clarify answers directly, no pipeline -------------------------------
def test_clarify_route_answers_directly_without_pipeline(f1_env):
    import src.bot.telegram_bot as bot

    # A dangling first turn (no antecedent) => CLARIFY.
    update = _make_update(update_id=9, chat_id=9)
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "¿y cuál es su tensión?"))

    # Exactly one reply — the policy's clarify question, verbatim.
    assert len(update.message.replies) == 1
    assert "modelo" in update.message.replies[0].lower()

    # $0: the pipeline was never entered (no from_production, no generation).
    assert f1_env["from_production_calls"] == 0
    assert f1_env["generate_queries"] == []

    # A dangling clarify fixes NO model (never leak/guess a product).
    ws = context.user_data["mt_working_state"]
    assert ws.last_target_models == ()


# --- (4) excerpt backfilled into durable working state -----------------------
def test_answer_excerpt_backfilled_into_working_state(f1_env):
    import src.bot.telegram_bot as bot

    update = _make_update(update_id=3, chat_id=3)
    context = SimpleNamespace(user_data={})
    asyncio.run(
        bot._process_query(update, context, "¿Cuál es la tensión del lazo de la CAD-250?")
    )

    ws = context.user_data["mt_working_state"]
    # The TODO closed: the durable state carries the answer excerpt for the next
    # turn's anaphora rewrite.
    assert ws.last_answer_excerpt == "La tensión del lazo es 24 V CC."
    assert ws.last_query == "¿Cuál es la tensión del lazo de la CAD-250?"


# --- (5) the rewriter is never constructed on a $0 route ---------------------
def test_rewriter_not_constructed_on_zero_cost_routes(f1_env, monkeypatch):
    import src.bot.telegram_bot as bot
    import src.orchestrator.rewriter as rewriter_mod

    calls = {"n": 0}
    _orig = rewriter_mod.make_rewriter

    def _spy(*a, **k):
        calls["n"] += 1
        return _orig(*a, **k)

    monkeypatch.setattr(rewriter_mod, "make_rewriter", _spy)

    context = SimpleNamespace(user_data={})
    # Turn 1 STANDALONE, turn 2 CARRY_FORWARD — both $0 routes.
    u1 = _make_update(update_id=1, chat_id=7)
    asyncio.run(
        bot._process_query(u1, context, "¿Cuál es la tensión del lazo de la CAD-250?")
    )
    u2 = _make_update(update_id=2, chat_id=7)
    asyncio.run(bot._process_query(u2, context, "¿y su tensión?"))

    # No REWRITE route was hit => the economical rewriter was never built.
    assert calls["n"] == 0
