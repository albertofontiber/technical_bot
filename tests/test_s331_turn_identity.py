"""s331 M3a — invariantes de `TurnIdentity` (v6 §3.D, G0-h) y compat del estado.

La tabla de combinaciones válidas/ inválidas es el CONTRATO: provenance POR
COMPONENTE (Sol-4 r-v4), `pending_derived` (Sol-3 r-v5), «no se construye vacío»,
y `route_cut ⇒ mención de ESTE turno`. Además: los campos `pending_*` nuevos de
`WorkingState` no rompen a los constructores existentes (defaults) y el espejo
MT-1b sigue construyendo estados compatibles (lock-step G0-f, slice estructural).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.orchestrator.conversation_policy import TurnIdentity, WorkingState


# ---------------------------------------------------------------------------
# Combinaciones VÁLIDAS (tabla v6 §3.D)
# ---------------------------------------------------------------------------
def test_valida_resuelto_este_turno():
    ti = TurnIdentity(resolved_models=("2X-AF1-FB-S",),
                      models_provenance="resolved_this_turn")
    assert ti.route_cut is False and ti.mention is None


def test_valida_estado_mixto_carried_mas_mencion_nueva():
    # El caso Sol-3 r-v2: canónico arrastrado + mención nueva sin resolver.
    ti = TurnIdentity(resolved_models=("2X-AF1-FB-S",), models_provenance="carried",
                      mention="2X-AF1-XQ2", mention_provenance="this_turn",
                      route_cut=True)
    assert ti.models_provenance == "carried"


def test_valida_pending_derived():
    # Regla 2 de la gramática: afirmación sin binding ⇒ familia derivada del pending.
    ti = TurnIdentity(resolved_models=("2X-AF1",), models_provenance="pending_derived",
                      mention="2X-AF1-XQ2", mention_provenance="pending_carried")
    assert ti.models_provenance == "pending_derived"


def test_valida_solo_mencion():
    ti = TurnIdentity(mention="TSR-9100", mention_provenance="this_turn",
                      route_cut=False)
    assert ti.resolved_models == ()


@pytest.mark.parametrize("presence", ["vigente", "stale", "cold", None])
def test_valida_presence(presence):
    TurnIdentity(resolved_models=("X-1",), models_provenance="resolved_this_turn",
                 presence=presence)


# ---------------------------------------------------------------------------
# Combinaciones INVÁLIDAS (cada una revienta en construcción)
# ---------------------------------------------------------------------------
def test_invalida_vacia():
    with pytest.raises(ValueError, match="vacía"):
        TurnIdentity()


def test_invalida_route_cut_sin_mencion_de_este_turno():
    with pytest.raises(ValueError, match="route_cut"):
        TurnIdentity(resolved_models=("X-1",), models_provenance="carried",
                     mention="Y-2", mention_provenance="pending_carried",
                     route_cut=True)


def test_invalida_mencion_sin_provenance():
    with pytest.raises(ValueError, match="mention"):
        TurnIdentity(mention="Y-2", mention_provenance="none")


def test_invalida_provenance_sin_mencion():
    with pytest.raises(ValueError, match="mention"):
        TurnIdentity(resolved_models=("X-1",), models_provenance="carried",
                     mention=None, mention_provenance="this_turn")


def test_invalida_modelos_sin_provenance():
    with pytest.raises(ValueError, match="resolved_models"):
        TurnIdentity(resolved_models=("X-1",), models_provenance="none",
                     mention="Y-2", mention_provenance="this_turn")


def test_invalida_provenance_sin_modelos():
    with pytest.raises(ValueError, match="resolved_models"):
        TurnIdentity(resolved_models=(), models_provenance="carried")


@pytest.mark.parametrize("campo, valor", [
    ("models_provenance", "inventada"),
    ("mention_provenance", "inventada"),
    ("presence", "tibia"),
])
def test_invalida_enums(campo, valor):
    kwargs = {"resolved_models": ("X-1",), "models_provenance": "carried"}
    if campo == "mention_provenance":
        kwargs.update(mention="Y-2")
    kwargs[campo] = valor
    with pytest.raises(ValueError):
        TurnIdentity(**kwargs)


# ---------------------------------------------------------------------------
# WorkingState: compat de los campos pending nuevos + ventana propia
# ---------------------------------------------------------------------------
def test_working_state_defaults_compat():
    ws = WorkingState()  # los constructores existentes no pasan pending_*
    assert ws.pending_mention is None and ws.pending_at is None
    assert ws.is_empty


def test_pending_within_window():
    now = datetime.now(timezone.utc)
    ws = WorkingState(pending_mention="2X-AF1-XQ2", pending_at=now)
    assert ws.pending_within_window(now + timedelta(minutes=59), 3600)
    assert not ws.pending_within_window(now + timedelta(minutes=61), 3600)
    assert not WorkingState().pending_within_window(now, 3600)


def test_espejo_mt1b_sigue_construyendo_estados_compatibles():
    """Lock-step G0-f (slice estructural): el `update_working_state` del harness
    construye WorkingState sin los campos pending — los defaults deben mantener a
    prod y eval byte-compatibles hasta que M3b cablee las transiciones en AMBOS."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "mt_harness", Path(__file__).resolve().parent.parent
        / "scripts" / "test_multiturn_vs_gold.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # importa el harness real, no una copia

    from src.orchestrator.conversation_policy import PolicyRoute, TurnResolution
    now = datetime.now(timezone.utc)
    res = TurnResolution(route=PolicyRoute.STANDALONE, query_for_retrieval="q",
                         target_models=("X-1",))
    ws2 = mod.update_working_state(WorkingState(), res, "q", None, now, None)
    assert ws2.pending_mention is None and ws2.pending_at is None
