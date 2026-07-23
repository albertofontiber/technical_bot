"""Phase 0 parity gate (fix GATE-PARIDAD-VACUO, design v2 §4).

The gate must be an instrument that drives a ``TurnRequest`` *through the
orchestrator* and proves PRE-LLM byte parity against the direct pipeline call
that the handler / gold harness make today. ``bvg`` enters below the refactored
seam, so it is a vacuous parity gate — this instrument is the real one.

Parity is measured at the DEEPEST reachable point without changing behavior: the
real provider request envelope (``system`` + ``messages``) assembled inside
``generate_answer`` right before ``client.messages.create``. We fake the
Anthropic client (as existing generator tests do) so the real envelope-assembly
code runs and is captured with zero network and zero duplication.

What is asserted byte-for-byte between the two routes:
  * CONTEXT  — the served chunks handed to the writer (identical objects);
  * PROMPT   — ``system`` (assembled system prompt) and ``messages[0].content``
               (user message with the embedded context);
  * PLAN     — the orchestrator plan is ``single_hop`` and maps 1:1 to the direct
               ``execute_rag_turn`` call.

Both routes share ONE ``replay_adapters`` instance (frozen retrieval, identity
rerank, no-op shadow, empty coverage fetchers) so coverage runs its real logic
deterministically offline.
"""

import copy
import os
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

import src.rag.generator as gen
from src.orchestrator import TurnRequest, execute_rag_turn, replay_adapters, run_turn
from src.orchestrator.contracts import PlanKind


_QUERY = "¿Cuál es la tensión del lazo de la CAD-250?"
_RETRIEVAL_TOP_K = 50
_RERANK_TOP_K = 5

# Fixture chunks that survive the generator's relevance filter and reach the
# prompt (similarity >= threshold, no compatibility lane).
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


class _CaptureMessages:
    """Fake Anthropic messages client: records each ``create`` envelope and
    returns a canned response so ``generate_answer`` completes offline."""

    def __init__(self, envelopes):
        self._envelopes = envelopes

    def create(self, **kwargs):
        # Deep-copy so later mutation by the caller cannot rewrite history.
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


def _adapters():
    return replay_adapters(retrieved=_FIXTURE, generate=gen.generate_answer)


def test_orchestrator_route_matches_direct_pipeline_byte_for_byte(captured_envelopes):
    adapters = _adapters()

    # Route DIRECT — how the gold harness / handler call the seam today.
    direct = execute_rag_turn(
        query=_QUERY,
        query_for_retrieval=_QUERY,
        target_models=None,
        available_models=None,
        retrieval_top_k=_RETRIEVAL_TOP_K,
        rerank_top_k=_RERANK_TOP_K,
        adapters=adapters,
    )

    # Route ORCH — the same turn driven through the orchestrator.
    request = TurnRequest(
        query=_QUERY,
        retrieval_top_k=_RETRIEVAL_TOP_K,
        rerank_top_k=_RERANK_TOP_K,
    )
    result = run_turn(request, adapters)

    # Exactly one LLM envelope per route.
    assert len(captured_envelopes) == 2, "each route must issue exactly one writer call"
    direct_envelope, orch_envelope = captured_envelopes

    # PLAN — orchestrator chose single_hop and mapped 1:1 to the direct call.
    assert result.plan.kind is PlanKind.SINGLE_HOP
    assert result.plan.query_for_retrieval == _QUERY

    # CONTEXT — the served chunks are byte-identical.
    assert list(result.retrieval.chunks) == list(direct["chunks"])

    # PROMPT — system prompt is byte-identical.
    assert orch_envelope["system"] == direct_envelope["system"]
    # PROMPT — the user message (with the embedded context) is byte-identical.
    assert (
        orch_envelope["messages"][0]["content"]
        == direct_envelope["messages"][0]["content"]
    )
    # And the whole provider request envelope matches (model/max_tokens/temp too).
    assert orch_envelope == direct_envelope

    # The served context is actually inside the captured prompt (not vacuously
    # equal because both were empty).
    assert "24 V CC" in orch_envelope["messages"][0]["content"]
    assert "Fragmento 1" in orch_envelope["messages"][0]["content"]


def test_orchestrator_route_matches_direct_with_resolved_query_and_models(
    captured_envelopes,
):
    # A dependent-turn shape: a distinct retrieval query + resolved models. The
    # orchestrator must still reach the exact same envelope as the direct call
    # built with the same resolved inputs.
    adapters = _adapters()
    resolved_query = f"{_QUERY} (contexto: CAD-250)"

    direct = execute_rag_turn(
        query=_QUERY,
        query_for_retrieval=resolved_query,
        target_models=["CAD-250"],
        available_models=["CAD-250", "MAD-461"],
        retrieval_top_k=_RETRIEVAL_TOP_K,
        rerank_top_k=_RERANK_TOP_K,
        adapters=adapters,
    )

    request = TurnRequest(
        query=_QUERY,
        retrieval_top_k=_RETRIEVAL_TOP_K,
        rerank_top_k=_RERANK_TOP_K,
        query_for_retrieval=resolved_query,
        target_models=("CAD-250",),
        available_models=("CAD-250", "MAD-461"),
    )
    result = run_turn(request, adapters)

    direct_envelope, orch_envelope = captured_envelopes
    assert list(result.retrieval.chunks) == list(direct["chunks"])
    assert orch_envelope == direct_envelope
    # available_models reaches the prompt via the models context block.
    assert "MAD-461" in orch_envelope["messages"][0]["content"]
