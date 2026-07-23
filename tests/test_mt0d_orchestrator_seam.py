"""MT-0d: Telegram ingress adapter + ORCHESTRATOR_PATH / CONVO_SHADOW /
CONVO_MAINTENANCE seams (S281 Phase 0, last lane).

Coverage map (brief F):
  (1) byte-invariance OFF     — the three flags default OFF; with them off the
      handler path never touches the shadow module.
  (2) adapter fidelity        — build_turn_request preserves None-vs-[] and every
      routing field.
  (3) ORCHESTRATOR_PATH=on     — a turn driven adapter->run_turn is byte-identical
      to the direct execute_rag_turn call; plus a real-handler ON test (stubbed
      from_production, no DB).
  (4) shadow persistence      — shadow_persist_turn writes the full turn into a
      FakeConvoStore, leaving the run ``answer_ready`` and the outbox ``pending``
      (NO delivery leg in shadow, NO poller in Phase 0); dedup is idempotent.
  (5) shadow fail-open        — a store that raises never tumbles the handler.
  (6) CONVO_MAINTENANCE wiring — schedule_maintenance registers the poller +
      janitor on a (fake) JobQueue only when the flag is on; the callbacks drive
      the real sweeps against a FakeConvoStore.

RGPD: everything runs on the synthetic FakeConvoStore; no real DB is touched.
"""

import asyncio
import copy
import os
import types
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

import src.rag.generator as gen
from src.orchestrator import execute_rag_turn, replay_adapters, run_turn
from src.orchestrator.contracts import (
    PlanKind,
    RetrievalResult,
    SingleHopPlan,
    TurnRequest,
    TurnResult,
)
from src.orchestrator.fake_convo_store import FakeConvoStore
from src.orchestrator.telegram_adapter import build_turn_request


_QUERY = "¿Cuál es la tensión del lazo de la CAD-250?"
_RETRIEVAL_TOP_K = 50
_RERANK_TOP_K = 5

_FIXTURE = [
    {
        "id": "chunk-1",
        "content": "La tensión nominal del lazo es 24 V CC.",
        "similarity": 0.93,
        "product_model": "CAD-250",
        "section_title": "Especificaciones eléctricas",
        "content_type": "specs",
        "source_file": "manual_cad250.pdf",
        "document_revision": "A",
    },
    {
        "id": "chunk-2",
        "content": "El consumo en reposo es de 120 mA.",
        "similarity": 0.88,
        "product_model": "CAD-250",
        "section_title": "Consumo",
        "content_type": "specs",
        "source_file": "manual_cad250.pdf",
    },
]


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


def _shadow_request(*, update_id=555, chat_id=777, query="¿tensión del lazo?"):
    return build_turn_request(
        query=query,
        query_for_retrieval=query,
        target_models=["CAD-250"],
        available_models=None,
        update_id=update_id,
        chat_id=chat_id,
        source="text",
    )


def _shadow_result(*, answer="24 V CC"):
    retrieval = RetrievalResult(
        chunks=({"id": "c1", "content": "24 V CC"},),
        coverage_trace={"served": 1, "policy": "c1_v4"},
        retrieval_rows=3,
        reranked_rows=1,
    )
    return TurnResult(
        answer=answer,
        diagrams=(),
        plan=SingleHopPlan(
            query_for_retrieval="q", retrieval_top_k=50, rerank_top_k=5
        ),
        compute_status="answer_ready",
        retrieval=retrieval,
        generation={
            "answer": answer,
            "diagrams": [],
            "input_tokens": 100,
            "output_tokens": 20,
        },
    )


class _CaptureMessages:
    """Fake Anthropic client: records each ``create`` envelope, returns a canned
    response so ``generate_answer`` completes offline (mirrors the MT-0a gate)."""

    def __init__(self, envelopes):
        self._envelopes = envelopes

    def create(self, **kwargs):
        self._envelopes.append(copy.deepcopy(kwargs))
        return SimpleNamespace(
            content=[SimpleNamespace(text="La tensión del lazo es 24 V CC [F1].")],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
        )


@pytest.fixture
def captured_envelopes(monkeypatch):
    envelopes: list[dict] = []
    monkeypatch.setattr(
        gen.anthropic,
        "Anthropic",
        lambda api_key=None: SimpleNamespace(messages=_CaptureMessages(envelopes)),
    )
    return envelopes


@pytest.fixture(autouse=True)
def _clear_shadow_store():
    """No shadow store leaks between tests (the module holds a process global)."""
    import src.orchestrator.shadow as shadow

    shadow.register_shadow_store(None)
    yield
    shadow.register_shadow_store(None)


# --- (1) byte-invariance OFF -------------------------------------------------
def test_phase0_flags_default_off():
    import src.config as config
    import src.bot.telegram_bot as bot

    assert config.ORCHESTRATOR_PATH is False
    assert config.CONVO_SHADOW is False
    assert config.CONVO_MAINTENANCE is False
    # The bot imported the same immutable values.
    assert bot.ORCHESTRATOR_PATH is False
    assert bot.CONVO_SHADOW is False
    assert bot.CONVO_MAINTENANCE is False


def test_default_handler_path_never_touches_shadow(monkeypatch):
    """With the default (OFF) flags the handler runs the historical inline path
    and never enters the shadow module — even with a store injected."""
    import src.bot.telegram_bot as bot
    import src.orchestrator.shadow as shadow

    # A store IS injected, and the shadow core is booby-trapped: if the OFF path
    # touched it the test would fail loudly.
    shadow.register_shadow_store(FakeConvoStore())
    called = []
    monkeypatch.setattr(
        shadow, "shadow_persist_turn", lambda *a, **k: called.append(1)
    )

    monkeypatch.setattr(bot, "extract_product_models", lambda _q: ["ID2000"])
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
    assert called == []  # shadow_persist_turn never invoked while CONVO_SHADOW off


# --- (2) adapter fidelity: None vs [] and fields -----------------------------
def test_build_turn_request_preserves_none_vs_empty_and_fields():
    from src.config import RERANK_TOP_K, RETRIEVAL_TOP_K

    # Empty list must stay an EMPTY tuple (-> [] downstream), never None.
    r = build_turn_request(
        query="q",
        query_for_retrieval="q",
        target_models=[],
        available_models=None,
        update_id=42,
        chat_id=99,
    )
    assert r.target_models == ()
    assert r.available_models is None
    assert r.channel == "telegram"
    assert r.external_update_id == "42"
    assert r.conversation_id == "99"
    assert r.source == "text"
    assert r.transcription is None
    assert r.retrieval_top_k == RETRIEVAL_TOP_K
    assert r.rerank_top_k == RERANK_TOP_K

    # Populated models + voice + a distinct resolved retrieval query.
    r2 = build_turn_request(
        query="q",
        query_for_retrieval="q (contexto: CAD-250)",
        target_models=["CAD-250"],
        available_models=["CAD-250", "MAD-461"],
        update_id="7",
        chat_id="8",
        source="voice",
        transcription="raw asr",
    )
    assert r2.target_models == ("CAD-250",)
    assert r2.available_models == ("CAD-250", "MAD-461")
    assert r2.query_for_retrieval == "q (contexto: CAD-250)"
    assert r2.effective_retrieval_query == "q (contexto: CAD-250)"
    assert r2.source == "voice"
    assert r2.transcription == "raw asr"

    # None target stays None (the gold-harness shape).
    r3 = build_turn_request(
        query="q",
        query_for_retrieval="q",
        target_models=None,
        available_models=None,
        update_id=1,
        chat_id=2,
    )
    assert r3.target_models is None
    assert r3.available_models is None


# --- (3) ORCHESTRATOR_PATH parity --------------------------------------------
def test_adapter_route_matches_direct_pipeline_byte_for_byte(captured_envelopes):
    """build_turn_request -> run_turn is byte-identical to the direct
    execute_rag_turn call the handler makes today (same resolved inputs)."""
    adapters = replay_adapters(retrieved=_FIXTURE, generate=gen.generate_answer)

    # DIRECT — the handler's inline call: target_models=[] (empty list).
    direct = execute_rag_turn(
        query=_QUERY,
        query_for_retrieval=_QUERY,
        target_models=[],
        available_models=None,
        retrieval_top_k=_RETRIEVAL_TOP_K,
        rerank_top_k=_RERANK_TOP_K,
        adapters=adapters,
    )

    # ORCH — the same turn built through the ingress adapter.
    request = build_turn_request(
        query=_QUERY,
        query_for_retrieval=_QUERY,
        target_models=[],
        available_models=None,
        update_id=1,
        chat_id=2,
        retrieval_top_k=_RETRIEVAL_TOP_K,
        rerank_top_k=_RERANK_TOP_K,
    )
    result = run_turn(request, adapters)

    assert len(captured_envelopes) == 2
    direct_envelope, orch_envelope = captured_envelopes

    assert result.plan.kind is PlanKind.SINGLE_HOP
    assert list(result.retrieval.chunks) == list(direct["chunks"])
    assert result.answer == direct["generation"]["answer"]
    # The whole provider request envelope is byte-identical.
    assert orch_envelope == direct_envelope
    assert "24 V CC" in orch_envelope["messages"][0]["content"]


def test_orchestrator_path_on_real_handler_matches(monkeypatch):
    """The real handler ON branch (build_turn_request + asyncio.to_thread(run_turn)
    + from_production) produces the served answer. from_production is stubbed to
    replay adapters so no DB/network is touched."""
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch

    def _gen(query, chunks, *, available_models=None):
        return {"answer": "ANSWER-ORCH", "diagrams": []}

    monkeypatch.setattr(
        orch, "from_production", lambda: replay_adapters(retrieved=_FIXTURE, generate=_gen)
    )
    monkeypatch.setattr(bot, "ORCHESTRATOR_PATH", True)
    monkeypatch.setattr(bot, "extract_product_models", lambda _q: [])
    monkeypatch.setattr(bot, "log_query", lambda **k: None)

    update = _make_update(update_id=11, chat_id=22)
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "pregunta tecnica generica"))

    assert update.message.replies == ["ANSWER-ORCH"]


# --- (4) shadow persistence: exact declared state ----------------------------
def test_shadow_persists_turn_answer_ready_outbox_pending_no_delivery():
    import src.orchestrator.shadow as shadow

    store = FakeConvoStore()
    request = _shadow_request(update_id=555, chat_id=777)
    result = _shadow_result(answer="24 V CC")

    complete = shadow.shadow_persist_turn(store, request, result)
    assert complete is not None and complete["completed"] is True
    outbox_id = complete["outbox_id"]

    # Recover the run id via idempotent re-ingress (duplicate event, no advance).
    ingress = store.ingress(
        channel="telegram", external_update_id="555", external_chat_id="777"
    )
    assert ingress["is_new_event"] is False
    turn_run_id = ingress["turn_run_id"]

    # DECLARED Phase-0 state: run answer_ready (no delivery leg in shadow),
    # outbox pending (no poller in Phase 0 — it is never delivered).
    assert store.run_status(turn_run_id) == "answer_ready"
    assert store.outbox_status(outbox_id) == "pending"

    # The retrieval/coverage trace + answer are persisted on the outbox payload.
    ob = store._outbox[outbox_id]
    assert ob.payload_text == "24 V CC"
    assert ob.payload["coverage_trace"] == {"served": 1, "policy": "c1_v4"}
    assert ob.payload["retrieval_rows"] == 3
    assert ob.payload["reranked_rows"] == 1
    assert ob.payload["chunks_served"] == 1
    # Token metrics land on the run (generator keys mapped correctly).
    run = store._runs[turn_run_id]
    assert run.tokens_input == 100 and run.tokens_output == 20

    # Idempotent: a second shadow-persist of the same update is a no-op (dedup:
    # the run is answer_ready, no longer claimable) — no new outbox, no re-complete.
    assert shadow.shadow_persist_turn(store, request, result) is None
    assert store.run_status(turn_run_id) == "answer_ready"
    assert len(store._outbox) == 1


def test_handler_shadow_persists_via_pipeline(monkeypatch):
    """CONVO_SHADOW on + ORCHESTRATOR_PATH off: the handler answers via the
    historical inline pipeline AND shadow-persists that turn (through
    turn_result_from_pipeline)."""
    import src.bot.telegram_bot as bot
    import src.orchestrator.shadow as shadow

    store = FakeConvoStore()
    shadow.register_shadow_store(store)
    monkeypatch.setattr(bot, "CONVO_SHADOW", True)

    monkeypatch.setattr(bot, "extract_product_models", lambda _q: [])
    monkeypatch.setattr(bot, "retrieve_chunks", lambda *a, **k: [{"id": "a", "content": "A", "similarity": 0.9}])
    monkeypatch.setattr(bot, "rerank", lambda *a, **k: [{"id": "a", "content": "A", "similarity": 0.9}])
    monkeypatch.setattr(bot, "observe_structural_neighbor_shadow", lambda *a, **k: None)
    monkeypatch.setattr(
        bot, "generate_answer", lambda *a, **k: {"answer": "respuesta servida", "diagrams": []}
    )
    monkeypatch.setattr(bot, "log_query", lambda **k: None)

    update = _make_update(update_id=321, chat_id=654)
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "pregunta tecnica generica"))

    # The user answer is unchanged by the shadow.
    assert update.message.replies == ["respuesta servida"]

    # And the turn was persisted at the declared state.
    ingress = store.ingress(
        channel="telegram", external_update_id="321", external_chat_id="654"
    )
    turn_run_id = ingress["turn_run_id"]
    assert store.run_status(turn_run_id) == "answer_ready"
    run = store._runs[turn_run_id]
    # complete_run was reached: an outbox exists, pending, carrying the answer.
    assert len(store._outbox) == 1
    (ob,) = store._outbox.values()
    assert ob.payload_text == "respuesta servida"
    assert ob.delivery_status == "pending"


# --- (5) shadow fail-open ----------------------------------------------------
def test_maybe_shadow_persist_no_store_is_noop():
    import src.orchestrator.shadow as shadow

    shadow.register_shadow_store(None)
    # Must not raise, must not require a store.
    shadow.maybe_shadow_persist(_shadow_request(), _shadow_result())


def test_maybe_shadow_persist_is_fail_open_when_store_raises():
    import src.orchestrator.shadow as shadow

    class _Boom:
        def ingress(self, **_k):
            raise RuntimeError("db down")

    shadow.register_shadow_store(_Boom())
    # Fail-open: the raising store must not propagate.
    shadow.maybe_shadow_persist(_shadow_request(), _shadow_result())


def test_handler_shadow_failopen_does_not_tumble_the_reply(monkeypatch):
    """A store that raises inside the shadow block leaves the served answer
    intact and produces NO error reply to the user."""
    import src.bot.telegram_bot as bot
    import src.orchestrator.shadow as shadow

    class _Boom:
        def ingress(self, **_k):
            raise RuntimeError("shadow store exploded")

    shadow.register_shadow_store(_Boom())
    monkeypatch.setattr(bot, "CONVO_SHADOW", True)

    monkeypatch.setattr(bot, "extract_product_models", lambda _q: [])
    monkeypatch.setattr(bot, "retrieve_chunks", lambda *a, **k: [{"id": "a", "content": "A", "similarity": 0.9}])
    monkeypatch.setattr(bot, "rerank", lambda *a, **k: [{"id": "a", "content": "A", "similarity": 0.9}])
    monkeypatch.setattr(bot, "observe_structural_neighbor_shadow", lambda *a, **k: None)
    monkeypatch.setattr(
        bot, "generate_answer", lambda *a, **k: {"answer": "respuesta intacta", "diagrams": []}
    )
    monkeypatch.setattr(bot, "log_query", lambda **k: None)

    update = _make_update(update_id=1, chat_id=2)
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "pregunta tecnica generica"))

    # Exactly the served answer — no "Ha ocurrido un error..." error message.
    assert update.message.replies == ["respuesta intacta"]


# --- (6) CONVO_MAINTENANCE scheduling wiring ---------------------------------
class _FakeJobQueue:
    def __init__(self):
        self.jobs = []

    def run_repeating(self, callback, interval, first=None, name=None):
        job = SimpleNamespace(
            callback=callback, interval=interval, first=first, name=name
        )
        self.jobs.append(job)
        return job


class _FakeApp:
    def __init__(self):
        self.job_queue = _FakeJobQueue()


def test_schedule_maintenance_off_registers_nothing(monkeypatch):
    import src.bot.telegram_bot as bot

    monkeypatch.setattr(bot, "CONVO_MAINTENANCE", False)
    app = _FakeApp()
    jobs = bot.schedule_maintenance(app, store=None, interval=60, sender=lambda p: "")
    assert jobs == []
    assert app.job_queue.jobs == []


def test_schedule_maintenance_on_wires_poller_and_janitor(monkeypatch):
    import src.bot.telegram_bot as bot
    import src.orchestrator.shadow as shadow

    monkeypatch.setattr(bot, "CONVO_MAINTENANCE", True)

    # Seed a pending outbox by shadow-persisting a turn (answer_ready + pending).
    store = FakeConvoStore()
    complete = shadow.shadow_persist_turn(store, _shadow_request(), _shadow_result())
    outbox_id = complete["outbox_id"]
    assert store.outbox_status(outbox_id) == "pending"

    sends = []

    def sender(payload):
        sends.append(payload)
        return f"tg-{payload.outbox_id}"

    app = _FakeApp()
    jobs = bot.schedule_maintenance(app, store, interval=30, sender=sender)

    assert [j.name for j in jobs] == [
        "convo_deliver_pending",
        "convo_reclaim_and_repair",
    ]
    assert len(app.job_queue.jobs) == 2

    # The poller callback delivers the pending outbox (send outside the store).
    poll_cb = app.job_queue.jobs[0].callback
    asyncio.run(poll_cb(None))
    assert store.outbox_status(outbox_id) == "delivered"
    assert len(sends) == 1 and sends[0].outbox_id == outbox_id

    # The janitor callback runs (no stuck sending here) without crashing.
    janitor_cb = app.job_queue.jobs[1].callback
    asyncio.run(janitor_cb(None))
