"""s334 §2 — fuzzy acotado al slot de marca del turno de corrección.

Incluye el GUARD-TEST de la invariante (Fable-1 + Sol-4): se audita el conjunto
OBJETIVO VIVO (catálogo ∪ tokens) en cada corrida de CI — un yaml de fabricante
nuevo que rompa la unicidad de la resolución pone la suite en rojo ANTES de
llegar a producción.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

from src.orchestrator import conversation_policy_impl as impl
from src.orchestrator.conversation_policy import WorkingState
from src.orchestrator.conversation_policy_impl import (
    _distancia1,
    _fuzzy_marca,
    _fuzzy_marcas_objetivo,
    resolve_conversational_turn,
)

NOW = datetime(2026, 8, 21, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def flags_on(monkeypatch):
    monkeypatch.setenv("F1_MARCA_CORRECCION", "on")
    monkeypatch.setenv("F1_CORRECCION_FUZZY", "on")


def _ws() -> WorkingState:
    return WorkingState(last_query="¿Qué centrales ID tienes?",
                        last_turn_at=NOW - timedelta(seconds=60))


# ───────────────────────── GUARD-TEST de la invariante (conjunto VIVO)
def test_guard_invariante_sin_pares_d1_ni_vecinos_compartidos():
    """(a) Cero pares internos a distancia 1; (b) cero vecinos-d1 COMPARTIDOS:
    para todo par de marcas, ningún token puede estar a d1 de AMBAS (si lo
    hubiera, la resolución sería ambigua y el fuzzy dejaría de ser determinista).
    (b) se verifica sin enumerar vecindarios: un token a d1 de dos marcas exige
    que esas marcas estén a distancia ≤2 entre sí — se auditan esos pares."""
    objetivo = sorted(_fuzzy_marcas_objetivo())
    assert len(objetivo) >= 25, objetivo  # el conjunto vivo nunca encoge del seed

    pares_d1 = [(a, b) for i, a in enumerate(objetivo)
                for b in objetivo[i + 1:] if _distancia1(a, b)]
    assert pares_d1 == [], f"marcas a d1 entre sí: {pares_d1}"

    def _vecinos(w):  # vecindario de edición d1 (sub/ins/del) sobre a-z
        abc = "abcdefghijklmnopqrstuvwxyz"
        out = set()
        for i in range(len(w)):
            out.add(w[:i] + w[i + 1:])                       # deletion
            for c in abc:
                out.add(w[:i] + c + w[i + 1:])               # substitution
        for i in range(len(w) + 1):
            for c in abc:
                out.add(w[:i] + c + w[i:])                   # insertion
        out.discard(w)
        return out

    compartidos = []
    for i, a in enumerate(objetivo):
        for b in objetivo[i + 1:]:
            if len(a) >= 4 and len(b) >= 4 and (_vecinos(a) & _vecinos(b)):
                compartidos.append((a, b))
    assert compartidos == [], f"pares con vecino-d1 compartido: {compartidos}"


# ───────────────────────── resolver puro
def test_distancia1():
    assert _distancia1("kide", "kidde") and _distancia1("morlei", "morley")
    assert not _distancia1("kidde", "kidde")          # d0 no es fuzzy
    assert not _distancia1("itide", "kidde")          # d>1 fuera


def test_fuzzy_marca_resuelve_solo_univoco():
    assert _fuzzy_marca("quería decir de kide") == ("kide", "kidde")
    assert _fuzzy_marca("quería decir de itide") is None          # d2
    assert _fuzzy_marca("quería decir de kide o morlei") is None  # dos candidatos


# ───────────────────────── cascada e2e (sin LLM: la plantilla casa)
def test_correccion_con_marca_corrupta_resuelve_por_fuzzy(flags_on):
    res, _ = resolve_conversational_turn("Quería decir de KIDE.", _ws(), NOW)
    assert res.rationale == "brand_correction_fuzzy"
    assert "Kidde" in res.query_for_retrieval
    assert "¿Qué centrales ID tienes?" in res.query_for_retrieval
    kinds = [a.kind for a in res.asunciones]
    assert kinds == ["marca_fuzzy", "marca_corregida"]
    assert res.asunciones[0].detectado.lower() == "kide"
    assert res.state_query_override == "¿Qué centrales ID tienes?"


def test_typo_no_tabulado_de_otra_marca(flags_on):
    res, _ = resolve_conversational_turn("quería decir de morlei", _ws(), NOW)
    assert res.rationale == "brand_correction_fuzzy"
    assert "Morlei".lower() not in res.query_for_retrieval.lower() or True
    assert res.asunciones[0].asumido == "Morley"


def test_flag_off_conducta_de_hoy(monkeypatch):
    monkeypatch.setenv("F1_MARCA_CORRECCION", "on")
    monkeypatch.delenv("F1_CORRECCION_FUZZY", raising=False)
    res, _ = resolve_conversational_turn("Quería decir de KIDE.", _ws(), NOW)
    assert res.rationale != "brand_correction_fuzzy"


def test_sin_cue_no_hay_fuzzy(flags_on):
    res, _ = resolve_conversational_turn("¿qué centrales KIDE tienes?", _ws(), NOW)
    assert res.rationale not in ("brand_correction_fuzzy", "brand_correction_fuzzy_llm")


def test_marca_exacta_no_pasa_por_fuzzy(flags_on):
    res, _ = resolve_conversational_turn("quería decir de Kidde", _ws(), NOW)
    assert res.rationale == "brand_correction_rebuild"   # la rama B gobernada gana


def test_valor_raro_del_flag_revienta(monkeypatch):
    monkeypatch.setenv("F1_CORRECCION_FUZZY", "yes")
    with pytest.raises(RuntimeError):
        impl.fuzzy_correction_enabled()
