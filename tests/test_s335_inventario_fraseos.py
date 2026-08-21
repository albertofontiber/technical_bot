# -*- coding: utf-8 -*-
"""s335 (DEC-270) — Gramática v2 del atajo de inventario, flag INVENTARIO_FRASEOS.

Lo que se prueba, en el orden del contrato (evals/s335_propuesta_v2.md §1/§4-GB1):
1. Flag ESTRICTO (on/off/ausente/typo-revienta) — patrón `mismatch_answer_activo`.
2. Formas nuevas CON marca (dinámicas): desiderativas/imperativas ES + EN, con y
   sin punto final, con filtros censados de cola.
3. El hueco VIVO de Whisper: las formas interrogativas EXISTENTES con «.» final
   (rotas hoy por el ancla `\\??$`) pasan con el flag ON — y siguen rotas con OFF
   (no-cambio byte a byte, que es el contrato del default).
4. FRONTERA anti-sobre-disparo (dúo s335 Sol-4): 6 continuaciones técnicas con el
   mismo prefijo desiderativo NO matchean — siguen yendo al RAG.
5. FRONTERA pieza A/pieza B: la anafórica («Y ahora quiero ver las de Morley.»)
   NO la traga el atajo — es población del clasificador (prompt v3, cohorte v3).
6. Guardia #70: `marca_destino` comparte la definición de intención (fase B viva:
   la transición del plan ES la fuente de invalidación) — solo cambia el
   PREDICADO de población; la mecánica de invalidación no se toca aquí.
7. Plan completo (puro, convención test_s324f): ruta y filtros con flag on/off.
"""
from __future__ import annotations

import pytest

from src.flags import inventario_fraseos_activo
from src.orchestrator import turn_plan as tp

_INV = tp._intencion_inventario

# --- 2 · formas nuevas con marca (GB1) ----------------------------------------

POSITIVAS_MARCA = [
    ("Quiero ver las centrales de Morley.", "Morley"),      # la del replay real
    ("quiero ver las centrales de Morley", "Morley"),       # sin punto
    ("quiero ver las centrales Morley.", "Morley"),         # sin «de»
    ("quiero centrales de Morley.", "Morley"),              # desiderativa elíptica
    ("dame las centrales de Morley de 4 lazos.", "Morley"),
    ("quiero ver las centrales analógicas de Notifier.", "Notifier"),
    ("necesito ver los detectores de Aguilera", "Aguilera"),
    ("I want to see Morley panels", "Morley"),
    ("I want to see Morley catalogs.", "Morley"),
    ("show me Morley panels", "Morley"),
    ("show me the Kidde detectors.", "Kidde"),
]


@pytest.mark.parametrize("texto,marca", POSITIVAS_MARCA)
def test_formas_nuevas_con_marca(texto, marca):
    assert _INV(texto, marca, fraseos=True), texto
    # y NINGUNA entra con el flag apagado (no-cambio del default)
    assert not _INV(texto, marca), f"cambió conducta con flag off: {texto}"


# --- 3 · el punto de Whisper sobre las formas EXISTENTES ----------------------

def test_interrogativa_existente_con_punto_de_whisper():
    """«dime qué centrales de Morley tienes» ya funciona HOY; con el «.» que
    Whisper añade al transcribir, el ancla `\\??$` la rompía (hueco VIVO,
    dúo s335 Fable-4). La v2 la admite; el default la sigue perdiendo — ese
    no-cambio ES el contrato del flag off."""
    con_punto = "dime qué centrales de Morley tienes."
    assert _INV(con_punto, "Morley", fraseos=True)
    assert not _INV(con_punto, "Morley")            # hoy: roto (documentado)
    sin_punto = "dime qué centrales de Morley tienes"
    assert _INV(sin_punto, "Morley")                # hoy: funciona
    assert _INV(sin_punto, "Morley", fraseos=True)  # y sigue funcionando


@pytest.mark.parametrize("texto", [
    "¿Qué centrales de KIDDE tienes?",     # la del replay real (turno 1)
    "listado de productos",
    "catálogo de Morley",
    "which panels do you have?",
    # estas dos parecen «nuevas» pero YA matchean hoy por la alternancia
    # «(listado|catálogo) de {sustantivo}» sin ancla — van aquí a propósito:
    "Muéstrame el catálogo de centrales de Kidde.",
    "necesito ver el listado de detectores de Aguilera",
])
def test_superconjunto_formas_existentes(texto):
    """Todo lo que matchea hoy sigue matcheando con la v2 (ancla tolerante =
    superconjunto; las alternancias nuevas solo AÑADEN)."""
    assert _INV(texto, "Morley")
    assert _INV(texto, "Morley", fraseos=True)


# --- 4 · frontera anti-sobre-disparo (Sol-4): 6 negativos técnicos ------------

NEGATIVAS_TECNICAS = [
    "quiero saber qué centrales Morley tienen salida de relé",
    "quiero saber si las centrales de Morley soportan lazos redundantes",
    "necesito ver el esquema de conexión de la central de Morley",
    "dime qué centrales de Morley tienen certificación EN 54",
    "muéstrame cómo configurar las centrales de Morley",
    "quiero ver las centrales de Morley conectadas en red",
]


@pytest.mark.parametrize("texto", NEGATIVAS_TECNICAS)
def test_negativas_tecnicas_siguen_al_rag(texto):
    assert not _INV(texto, "Morley", fraseos=True), texto
    assert not _INV(texto, "Morley"), texto


# --- 5 · frontera pieza A / pieza B (anafórica = clasificador, no atajo) ------

@pytest.mark.parametrize("texto", [
    "Y ahora quiero ver las de Morley.",   # fabef50b — población del prompt v3
    "Ahora quiero Morley.",
])
def test_anaforica_no_la_traga_el_atajo(texto):
    """Sin sustantivo de inventario NO hay atajo: el mensaje anafórico sigue a la
    cascada conversacional, donde lo juzga el clasificador (cohorte v3, fila
    obligatoria). Si esto matcheara, la pieza A pisaría a la B."""
    assert not _INV(texto, "Morley", fraseos=True), texto
    assert not _INV(texto, "Morley"), texto


# --- 6 · guardia #70: el predicado de población de `marca_destino` ------------

def test_marca_destino_comparte_la_definicion():
    texto = "Quiero ver las centrales de Morley."
    assert tp.marca_destino(texto, ["Morley"], fraseos=True) == "Morley"
    assert tp.marca_destino(texto, ["Morley"]) is None      # off: byte-idéntico
    # la forma existente resuelve igual en los dos regímenes
    assert tp.marca_destino("listado de Morley", ["Morley"]) == "Morley"
    assert tp.marca_destino("listado de Morley", ["Morley"],
                            fraseos=True) == "Morley"


# --- 7 · plan completo (puro): ruta y filtros ---------------------------------

def _plan(texto: str, marca: str, fraseos: bool):
    meta = tp.Meta(inventario_fraseos=fraseos)
    hechos = {tp.Hecho("marca_servida", marca): True}
    return tp.plan_turn(texto, (), meta, hechos)


def test_plan_ruta_inventario_con_flag():
    plan = _plan("Quiero ver las centrales de Morley.", "Morley", fraseos=True)
    assert plan.ruta == "inventario"
    assert plan.datos["marca"] == "Morley"
    assert plan.datos["filtros"] == {"categoria": "central"}
    assert plan.fallback_ruta == "conversacional"


def test_plan_sin_flag_no_cambia():
    plan = _plan("Quiero ver las centrales de Morley.", "Morley", fraseos=False)
    assert plan.ruta == "conversacional"


def test_plan_filtros_de_cola():
    plan = _plan("dame las centrales de Morley de 4 lazos.", "Morley", fraseos=True)
    assert plan.ruta == "inventario"
    assert plan.datos["filtros"] == {"categoria": "central", "lazos": 4}


def test_plan_en_panels_mapea_categoria():
    plan = _plan("I want to see Morley panels", "Morley", fraseos=True)
    assert plan.ruta == "inventario"
    assert plan.datos["filtros"] == {"categoria": "central"}   # panels → central


def test_plan_replay_turno_1_ambos_regimenes():
    """El turno 1 del replay real entra al atajo HOY y con la v2 (no-regresión)."""
    for fraseos in (False, True):
        plan = _plan("¿Qué centrales de KIDDE tienes?", "KIDDE", fraseos=fraseos)
        assert plan.ruta == "inventario", f"fraseos={fraseos}"


# --- 1 · el flag estricto ------------------------------------------------------

def test_flag_estricto(monkeypatch):
    monkeypatch.delenv("INVENTARIO_FRASEOS", raising=False)
    assert inventario_fraseos_activo() is False
    monkeypatch.setenv("INVENTARIO_FRASEOS", "on")
    assert inventario_fraseos_activo() is True
    monkeypatch.setenv("INVENTARIO_FRASEOS", "off")
    assert inventario_fraseos_activo() is False
    monkeypatch.setenv("INVENTARIO_FRASEOS", "ON ")
    assert inventario_fraseos_activo() is True      # tolerancia espacios/mayúsculas
    monkeypatch.setenv("INVENTARIO_FRASEOS", "true")
    with pytest.raises(RuntimeError):
        inventario_fraseos_activo()                 # typo revienta RUIDOSO
