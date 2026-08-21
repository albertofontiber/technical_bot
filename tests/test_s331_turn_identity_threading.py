"""s331 M3c-threading — el CANAL de `turn_identity` (v6 §3.D), sin conducta.

La identidad estructurada que resuelve la política tiene que llegar a generación
SIN pasar por el texto de la query (spoofing cerrado). Este fichero prueba el
canal ENTERO, tramo a tramo, y su propiedad de seguridad:

  (a) `TurnRequest` / `SingleHopPlan` admiten el campo y su default es `None`;
  (b) `plan_turn` lo COPIA al plan (no lo deriva ni lo interpreta);
  (c) `run_turn` lo entrega a `execute_rag_turn` — y el seam lo reenvía a
      `generate` (se mide el tramo completo, no solo la llamada intermedia);
  (d) `build_turn_request` lo copia del ingress al request;
  (e) BYTE-IDENTIDAD estructural: con el default `None`, los objetos construidos
      son IGUALES a los que se construían antes del threading (mismo dataclass
      sin el kwarg) — el threading no cambia nada por sí solo;
  (f) e2e del call-site real (`telegram_bot`, rama F1): la identidad que devuelve
      la resolución es la que ve el generador.

En M3c-threading NINGUNA conducta depende de la identidad: el generador solo la
recibe. El trigger (prompt + plantillas) es M3c-conducta, con su propia revisión.

Sin red, sin DB, sin API de pago: adapters de replay + generate grabador.
"""
from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

from src.orchestrator import (  # noqa: E402
    PlanKind,
    SingleHopPlan,
    TurnRequest,
    plan_turn,
    replay_adapters,
    run_turn,
)
from src.orchestrator.conversation_policy import (  # noqa: E402
    PolicyRoute,
    TurnIdentity,
    TurnResolution,
    WorkingState,
)
from src.orchestrator.telegram_adapter import build_turn_request  # noqa: E402

_FIXTURE = [
    {"id": "c1", "content": "La tensión nominal del lazo es 24 V CC.", "similarity": 0.9},
]

# Estado mixto REPRESENTABLE (caso Sol-3 r-v2): canónico arrastrado + mención
# nueva sin resolver. Se usa como testigo para que el canal no pueda "aprobar"
# transportando una identidad trivial.
_IDENTIDAD = TurnIdentity(
    resolved_models=("2X-AF1-FB-S",),
    models_provenance="carried",
    mention="2X-AF1-XQ2",
    mention_provenance="this_turn",
    presence="vigente",
    route_cut=True,
)


def _recording_generate(record):
    def generate(query, chunks, *, available_models=None, turn_identity=None):
        record["turn_identity"] = turn_identity
        record["calls"] = record.get("calls", 0) + 1
        return {"answer": "ok", "diagrams": []}

    return generate


# ---------------------------------------------------------------------------
# (a) el campo existe en los dos contratos y su default es None
# ---------------------------------------------------------------------------
def test_turn_request_admite_la_identidad_y_su_default_es_none():
    sin = TurnRequest(query="q", retrieval_top_k=50, rerank_top_k=5, source="text")
    con = TurnRequest(
        query="q", retrieval_top_k=50, rerank_top_k=5, source="text",
        turn_identity=_IDENTIDAD,
    )

    assert sin.turn_identity is None
    assert con.turn_identity is _IDENTIDAD


def test_single_hop_plan_admite_la_identidad_y_su_default_es_none():
    sin = SingleHopPlan(query_for_retrieval="q", retrieval_top_k=50, rerank_top_k=5)
    con = SingleHopPlan(
        query_for_retrieval="q", retrieval_top_k=50, rerank_top_k=5,
        turn_identity=_IDENTIDAD,
    )

    assert sin.turn_identity is None
    assert con.turn_identity is _IDENTIDAD
    assert con.kind is PlanKind.SINGLE_HOP


# ---------------------------------------------------------------------------
# (b) plan_turn la COPIA — misma instancia, sin interpretarla
# ---------------------------------------------------------------------------
def test_plan_turn_copia_la_identidad_del_request_al_plan():
    req = TurnRequest(
        query="¿y el XQ2?", retrieval_top_k=50, rerank_top_k=5, source="text",
        turn_identity=_IDENTIDAD,
    )

    plan = plan_turn(req)

    # `is`, no `==`: el planner transporta, no reconstruye (una copia con otra
    # procedencia sería una interpretación silenciosa).
    assert plan.turn_identity is _IDENTIDAD


def test_plan_turn_sin_identidad_deja_el_plan_en_none():
    req = TurnRequest(query="q", retrieval_top_k=50, rerank_top_k=5, source="text")

    assert plan_turn(req).turn_identity is None


# ---------------------------------------------------------------------------
# (c) run_turn -> execute_rag_turn -> adapters.generate
# ---------------------------------------------------------------------------
def test_run_turn_entrega_la_identidad_a_execute_rag_turn(monkeypatch):
    import src.orchestrator.orchestrator as orch_mod

    visto: dict = {}
    real = orch_mod.execute_rag_turn

    def _spy(**kwargs):
        visto.update(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(orch_mod, "execute_rag_turn", _spy)

    record: dict = {}
    req = TurnRequest(
        query="¿y el XQ2?", retrieval_top_k=50, rerank_top_k=5, source="text",
        turn_identity=_IDENTIDAD,
    )
    run_turn(req, replay_adapters(retrieved=_FIXTURE, generate=_recording_generate(record)))

    # el kwarg cruza el seam POR NOMBRE (no posicional: `execute_rag_turn` es kw_only)
    assert visto["turn_identity"] is _IDENTIDAD


def test_el_seam_reenvia_la_identidad_al_generador():
    """El tramo que importa de verdad: lo que ve el escritor. Aquí corre el
    `execute_rag_turn` REAL, no un espía — si el seam se olvidara del kwarg, el
    canal quedaría cortado justo antes de generación y (c) no lo vería."""
    record: dict = {}
    req = TurnRequest(
        query="¿y el XQ2?", retrieval_top_k=50, rerank_top_k=5, source="text",
        turn_identity=_IDENTIDAD,
    )

    result = run_turn(
        req, replay_adapters(retrieved=_FIXTURE, generate=_recording_generate(record))
    )

    assert record["turn_identity"] is _IDENTIDAD
    assert result.answer == "ok"


def test_sin_identidad_el_generador_recibe_none():
    record: dict = {}
    req = TurnRequest(query="q", retrieval_top_k=50, rerank_top_k=5, source="text")

    run_turn(req, replay_adapters(retrieved=_FIXTURE, generate=_recording_generate(record)))

    assert record["calls"] == 1
    assert record["turn_identity"] is None


def test_el_generador_de_produccion_acepta_el_kwarg():
    """`from_production` cablea `generate_answer`: si su firma no admitiera
    `turn_identity`, la ruta servida reventaría con TypeError EN PRODUCCIÓN y
    ningún test con fakes lo vería (el kwarg se pasa siempre, por protocolo)."""
    import inspect

    from src.rag.generator import generate_answer

    firma = inspect.signature(generate_answer)
    assert "turn_identity" in firma.parameters
    assert firma.parameters["turn_identity"].default is None


# ---------------------------------------------------------------------------
# (d) build_turn_request copia la identidad del ingress
# ---------------------------------------------------------------------------
def _request_de_ingress(**extra):
    return build_turn_request(
        query="¿y el XQ2?",
        query_for_retrieval="¿y el XQ2?",
        target_models=["2X-AF1-FB-S"],
        available_models=[],
        update_id=11,
        chat_id=22,
        source="text",
        **extra,
    )


def test_build_turn_request_copia_la_identidad():
    req = _request_de_ingress(turn_identity=_IDENTIDAD)

    assert req.turn_identity is _IDENTIDAD


# ---------------------------------------------------------------------------
# (e) byte-identidad estructural con el default None
# ---------------------------------------------------------------------------
def test_con_default_none_los_objetos_son_iguales_a_los_de_antes():
    """El threading NO cambia nada por sí solo: construir sin el kwarg y
    construir con `turn_identity=None` produce dataclasses IGUALES (frozen ⇒ `==`
    compara todos los campos, `kind` incluido), y el plan derivado también."""
    sin_kwarg = _request_de_ingress()
    con_none = _request_de_ingress(turn_identity=None)

    assert sin_kwarg == con_none
    assert repr(sin_kwarg) == repr(con_none)
    assert plan_turn(sin_kwarg) == plan_turn(con_none)

    # y el plan sin identidad es EL MISMO objeto-valor que el de antes del campo
    plan_esperado = SingleHopPlan(
        query_for_retrieval="¿y el XQ2?",
        retrieval_top_k=sin_kwarg.retrieval_top_k,
        rerank_top_k=sin_kwarg.rerank_top_k,
        target_models=("2X-AF1-FB-S",),
        available_models=(),
    )
    assert plan_turn(sin_kwarg) == plan_esperado


def test_la_identidad_no_altera_las_entradas_de_retrieval():
    """Aislamiento del canal: dos requests idénticos salvo la identidad producen
    el MISMO plan de retrieval (query, top_k y modelos). Si el threading tocara
    la ruta de recuperación, la comparación de eval dejaría de ser limpia."""
    base = _request_de_ingress()
    con_identidad = _request_de_ingress(turn_identity=_IDENTIDAD)

    p_base, p_id = plan_turn(base), plan_turn(con_identidad)

    assert (p_base.query_for_retrieval, p_base.target_models, p_base.available_models,
            p_base.retrieval_top_k, p_base.rerank_top_k) == (
        p_id.query_for_retrieval, p_id.target_models, p_id.available_models,
        p_id.retrieval_top_k, p_id.rerank_top_k)


# ---------------------------------------------------------------------------
# (f) e2e del call-site real: rama F1 de `_process_query`
# ---------------------------------------------------------------------------
class _Message:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)

    async def reply_photo(self, **_kwargs):
        pass

    async def reply_media_group(self, media, **_kwargs):
        pass


def test_e2e_el_call_site_f1_pasa_la_identidad_de_la_resolucion(monkeypatch):
    """El tramo que ningún test unitario cubre: que el HANDLER copie
    `TurnResolution.turn_identity` al request. Se sustituye la resolución (no la
    detección) para no depender de la conducta de los levers de s331."""
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch
    import src.orchestrator.conversation_policy_impl as policy_impl

    monkeypatch.setenv("CONVERSATION_POLICY", "impl")
    monkeypatch.setattr(bot, "log_query", lambda **k: None)

    def _resolve(query, prev_state, now, **_kwargs):
        return (
            TurnResolution(
                route=PolicyRoute.STANDALONE,
                query_for_retrieval=query,
                target_models=("2X-AF1-FB-S",),
                available_models=(),
                turn_identity=_IDENTIDAD,
            ),
            WorkingState(),
        )

    monkeypatch.setattr(policy_impl, "resolve_conversational_turn", _resolve)

    record: dict = {}
    monkeypatch.setattr(
        orch, "from_production",
        lambda: replay_adapters(retrieved=_FIXTURE, generate=_recording_generate(record)),
    )

    update = SimpleNamespace(
        message=_Message(), update_id=1,
        effective_user=SimpleNamespace(id=7), effective_chat=SimpleNamespace(id=2),
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "¿y el XQ2?", source="text"))

    assert record["turn_identity"] is _IDENTIDAD


def test_e2e_regimen_sin_f1_no_inventa_identidad(monkeypatch):
    """Régimen STUB (`CONVERSATION_POLICY=stub`): no hay resolución, así que el
    generador recibe `None` — la fila queda byte-idéntica a la de hoy."""
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch
    import src.rag.retriever as retriever

    monkeypatch.setenv("CONVERSATION_POLICY", "stub")
    monkeypatch.setattr(bot, "log_query", lambda **k: None)
    monkeypatch.setattr(bot, "extract_product_models", lambda q: [])
    monkeypatch.setattr(retriever, "get_category_models", lambda cat: [])

    record: dict = {}
    monkeypatch.setattr(
        orch, "from_production",
        lambda: replay_adapters(retrieved=_FIXTURE, generate=_recording_generate(record)),
    )

    update = SimpleNamespace(
        message=_Message(), update_id=1,
        effective_user=SimpleNamespace(id=7), effective_chat=SimpleNamespace(id=2),
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "pregunta generica", source="text"))

    assert record["calls"] == 1
    assert record["turn_identity"] is None
