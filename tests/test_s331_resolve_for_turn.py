"""s331 M1 — resolución gobernada en la seam de COMPOSICIÓN de F1 (G0 base).

Cubre: flag-off passthrough byte-idéntico (G0-e slice) · interlock fail-fast ·
binding de la variante del caso real Kidde en grafía ASR y canónica (G0-a slice) ·
canonicalize_only jamás escanea la query (B2 §11) · _presence_peek sin red
(vigente/stale/cold) · idempotencia detección con hint canónico (G0-c slice) ·
la seam de composición lleva el canónico al estado del hilo.

Sin DB: la detección/resolución es file-based (data/catalog/*.jsonl) y el peek
de presencia NUNCA fetchea — los tests lo asertan rompiendo si hay red.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from src.rag import catalog_resolver as CR


@pytest.fixture(autouse=True)
def _presence_aislada(monkeypatch):
    """Aísla el estado global de presencia por test y prohíbe red en los paths que
    estos tests ejercitan (el peek jamás debe fetchear ni re-chequear fingerprint)."""
    monkeypatch.setattr(CR, "_presence", None)

    def _boom(*_a, **_k):  # pragma: no cover - solo dispara si hay regresión
        raise AssertionError("el path de TURNO tocó red (s331: prohibido)")

    monkeypatch.setattr(CR, "_load_presence", _boom)
    monkeypatch.setattr(CR, "_try_corpus_fingerprint", _boom)
    yield


def _flags_on(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "on")
    monkeypatch.setenv("F1_RESOLVE_GOVERNED", "on")
    for legacy in ("LEVER2_IDENTITY", "LEVER2_PM_RESCUE", "IDENTITY_MAP"):
        monkeypatch.delenv(legacy, raising=False)
    monkeypatch.delenv("IDENTITY_RESOLVE_POLICY", raising=False)  # brazo add (drops inertes)


# ---------------------------------------------------------------------------
# Flag off = byte-idéntico
# ---------------------------------------------------------------------------
def test_flag_off_passthrough_byte_identico(monkeypatch):
    monkeypatch.delenv("F1_RESOLVE_GOVERNED", raising=False)
    monkeypatch.delenv("IDENTITY_RESOLVE", raising=False)
    base = ["2X-AF1"]
    out, info = CR.resolve_for_turn("Sobre la 2X-AF1-FBS.", base)
    assert out is base  # el MISMO objeto: passthrough exacto, no copia
    assert info is None


def test_interlock_flag_on_sin_resolver_revienta(monkeypatch):
    monkeypatch.setenv("F1_RESOLVE_GOVERNED", "on")
    monkeypatch.delenv("IDENTITY_RESOLVE", raising=False)
    with pytest.raises(RuntimeError, match="IDENTITY_RESOLVE=on"):
        CR.resolve_for_turn("Sobre la 2X-AF1-FBS.", ["2X-AF1"])


def test_valor_no_reconocido_revienta(monkeypatch):
    monkeypatch.setenv("F1_RESOLVE_GOVERNED", "quizas")
    with pytest.raises(RuntimeError, match="no reconocido"):
        CR.turn_resolve_enabled()


# ---------------------------------------------------------------------------
# Binding del caso real (G0-a slice)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("grafia", ["2X-AF1-FBS", "2X-AF1-FB-S"])
def test_binding_variante_asr_y_canonica(monkeypatch, grafia):
    _flags_on(monkeypatch)
    out, info = CR.resolve_for_turn(f"Sobre la {grafia}.", ["2X-AF1"])
    assert "2X-AF1-FB-S" in out, out
    assert "2X-AF1" in out  # brazo add: el token original se conserva
    assert info is not None and info["changed"] is True
    assert info["presence"] == "cold"  # sin caché previa y SIN tocar red


def test_query_sin_modelo_es_noop(monkeypatch):
    _flags_on(monkeypatch)
    base = ["2X-AF1"]
    out, info = CR.resolve_for_turn("Programación principalmente.", base)
    assert out == base
    assert info is not None and info["detected"] == [] and info["changed"] is False


# ---------------------------------------------------------------------------
# canonicalize_only (rama resolved_model del plan — B2 §11)
# ---------------------------------------------------------------------------
def test_canonicalize_only_no_escanea_query(monkeypatch):
    _flags_on(monkeypatch)
    out, info = CR.resolve_for_turn(
        "¿La CAD-150 es compatible?", ["2X-AF1-FBS"], canonicalize_only=True
    )
    assert "2X-AF1-FB-S" in out, out          # el string del plan se canonicaliza
    assert all("CAD" not in m for m in out), out  # la query JAMÁS se escanea en esta rama
    assert info is not None and "CAD-150" not in info["detected"]


# ---------------------------------------------------------------------------
# _presence_peek: estados sin red
# ---------------------------------------------------------------------------
def test_presence_peek_estados(monkeypatch):
    now = time.monotonic()
    assert CR._presence_peek(now) == (None, "cold")
    monkeypatch.setattr(CR, "_presence", {"elements": frozenset({"x"}), "at": now,
                                          "fp": ("t", "1"), "fp_at": now})
    elements, estado = CR._presence_peek(now)
    assert estado == "vigente" and elements == frozenset({"x"})
    monkeypatch.setattr(CR, "_presence", {"elements": frozenset({"x"}),
                                          "at": now - CR._PRESENCE_TTL_S - 1,
                                          "fp": ("t", "1"), "fp_at": now})
    assert CR._presence_peek(time.monotonic()) == (None, "stale")


def test_drop_gates_presencia_explicita_none_conserva(monkeypatch):
    # (Sol-1 r-v5) presencia None (stale/cold) ⇒ la regla corpus-aware CONSERVA aunque
    # el brazo sea replace y la via elegible: el drop jamás se decide con un set vencido.
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    resolved = {"all_members_consumable": True}
    assert CR._drop_gates_pass("zxe", "paraguas", resolved, None) is False
    # y con presencia explícita VIGENTE que contiene el core ⇒ también conserva
    core = CR._series.normalize_model("zxe")
    assert CR._drop_gates_pass("zxe", "paraguas", resolved, frozenset({core})) is False


# ---------------------------------------------------------------------------
# Idempotencia con hint canónico (G0-c slice, detección)
# ---------------------------------------------------------------------------
def test_idempotencia_hint_canonico(monkeypatch):
    _flags_on(monkeypatch)
    out1, _ = CR.resolve_for_turn("Sobre la 2X-AF1-FBS.", ["2X-AF1"])
    out2, _ = CR.resolve_for_turn(
        "Programación principalmente. (contexto: " + ", ".join(out1) + ")", list(out1)
    )
    assert set(out2) == set(out1), (out1, out2)


# ---------------------------------------------------------------------------
# Seam de composición: el estado del hilo recibe el canónico
# ---------------------------------------------------------------------------
def test_composition_seam_estado_lleva_canonico(monkeypatch):
    from src.orchestrator.conversation_policy import WorkingState
    from src.orchestrator.conversation_policy_impl import resolve_conversational_turn

    now = datetime.now(timezone.utc)
    _flags_on(monkeypatch)
    resolution, new_state = resolve_conversational_turn(
        "Sobre la 2X-AF1-FBS.", WorkingState(), now
    )
    assert "2X-AF1-FB-S" in (resolution.target_models or ()), resolution.target_models
    assert "2X-AF1-FB-S" in new_state.last_target_models


def test_composition_seam_flag_off_conducta_de_hoy(monkeypatch):
    from src.orchestrator.conversation_policy import WorkingState
    from src.orchestrator.conversation_policy_impl import resolve_conversational_turn

    monkeypatch.delenv("F1_RESOLVE_GOVERNED", raising=False)
    monkeypatch.delenv("IDENTITY_RESOLVE", raising=False)
    now = datetime.now(timezone.utc)
    resolution, new_state = resolve_conversational_turn(
        "Sobre la 2X-AF1-FBS.", WorkingState(), now
    )
    assert tuple(resolution.target_models or ()) == ("2X-AF1",)  # el truncado de hoy
    assert new_state.last_target_models == ("2X-AF1",)
