# -*- coding: utf-8 -*-
"""s324f — El atajo de catálogo: responder a la pregunta que se hizo.

Estos tests SON el gate G1-G6 de `evals/s324f_catalogo_propuesta_v2.md`. Nacen de
un fallo observado en producción, no de una hipótesis: Alberto preguntó «¿qué
fabricantes tienes?» y el bot respondió con 22 modelos de 756 agrupados bajo
`DESCARTADO`, `EN_unico`, `ES` y `PT`, sin botones para puntuarlo y sin guardar la
respuesta.
"""
from __future__ import annotations

import pytest

from src.bot import acotar as _acotar
from src.bot.acotar import Acotado, acotar
from src.orchestrator import turn_plan


def _plan_de(texto: str):
    """El plan de un turno LIMPIO (sin estado previo y sin hechos de DB).

    Una pregunta de catálogo no pide ningún hecho —lo declara
    `plan_turn_hechos`— así que el mapa vacío es el escenario real, no un atajo
    de test.
    """
    return turn_plan.plan_turn(texto, (), turn_plan.Meta(), {})


# ───────────────────────────────── G1 · la intención

@pytest.mark.parametrize("texto", [
    "¿qué fabricantes tienes?",
    "que marcas tienes",
    "¿qué empresas tienes?",
    "dame el listado de fabricantes",
    "lista de marcas",
])
def test_g1_pregunta_por_marcas_va_a_fabricantes(texto):
    """El fallo original: esto contestaba con modelos."""
    plan = _plan_de(texto)
    assert plan.ruta == "fabricantes", f"{texto!r} -> {plan.ruta}"


@pytest.mark.xfail(strict=True, reason=(
    "DEUDA DECLARADA (s324f): `_CATALOG_PATTERNS` solo reconoce espanol, asi que "
    "una pregunta en ingles ni siquiera llega al split de intencion. "
    "`sujeto_es_marca` YA cubre manufacturers/brands/vendors, de modo que el dia "
    "que el patron acepte ingles esto pasara a XPASS y el strict obligara a "
    "retirar el xfail — el trinquete, no un TODO."))
@pytest.mark.parametrize("texto", [
    "which manufacturers do you have?",
    "what brands do you have",
])
def test_g1_ingles_todavia_no(texto):
    plan = _plan_de(texto)
    assert plan.ruta == "fabricantes", f"{texto!r} -> {plan.ruta}"


@pytest.mark.parametrize("texto", [
    "¿qué productos tienes?",
    "que modelos tienes",
    "¿qué equipos tienes?",
    "listado de productos",
])
def test_g1_pregunta_por_productos_sigue_en_catalogo(texto):
    plan = _plan_de(texto)
    assert plan.ruta == "catalogo", f"{texto!r} -> {plan.ruta}"


def test_g1_desempate_declarado_gana_marcas():
    """«¿qué marcas y modelos tienes?» → marcas: es la respuesta que cabe entera.

    La regla de desempate está escrita en `sujeto_es_marca`; este test la ancla
    para que un cambio de patrón que la invierta no pase inadvertido.
    """
    plan = _plan_de("dame el listado de marcas y modelos")
    assert plan.ruta == "fabricantes"


@pytest.mark.parametrize("texto", [
    "¿cuántos lazos admite la CAD-250?",
    "cómo se conecta un detector Detnov",
    "hola",
    "gracias",
])
def test_g6_sin_sobre_routing(texto):
    """Control: preguntas que NO son de catálogo no deben caer en `fabricantes`."""
    plan = _plan_de(texto)
    assert plan.ruta != "fabricantes"


# ───────────────────────────────── G3/G4 · la pieza de «no cabe»

def test_g4_si_recorta_lo_dice():
    r = acotar([f"• elemento {i}" for i in range(500)], presupuesto=300,
               encabezado="Cabecera:", coletilla="Pide más así.",
               plural="fabricantes")
    assert r.recortado
    assert "Faltan" in r.texto and "fabricantes" in r.texto
    assert "no caben" in r.texto


def test_g4_si_cabe_todo_no_inventa_un_aviso():
    r = acotar(["• uno", "• dos"], presupuesto=3500, encabezado="Cab:",
               coletilla="Cola.")
    assert not r.recortado
    assert "Faltan" not in r.texto
    assert r.mostrados == r.total == 2


def test_g4_la_coletilla_va_siempre():
    """Quepa o no: es la que facilita el follow-up (adjudicación de Alberto)."""
    cola = "Dime una marca."
    assert cola in acotar(["• x"], presupuesto=3500, coletilla=cola).texto
    assert cola in acotar([f"• {i}" * 20 for i in range(200)],
                          presupuesto=400, coletilla=cola).texto


def test_g3_nunca_supera_el_presupuesto():
    for n in (0, 1, 5, 50, 500, 5000):
        r = acotar([f"• fabricante numero {i}" for i in range(n)],
                   presupuesto=800, encabezado="Cabecera larga:" * 3,
                   coletilla="Coletilla de follow-up." * 2)
        assert len(r.texto) <= 800, f"n={n} -> {len(r.texto)}"


def test_g3_el_aviso_cabe_incluso_en_el_limite():
    """La ironía que este diseño evita: quedarse sin sitio para la línea que
    explica que no había sitio. El espacio del aviso se reserva ANTES."""
    r = acotar([f"• elemento largo numero {i}" for i in range(100)],
               presupuesto=200, encabezado="Cab:", coletilla="Cola.",
               plural="elementos")
    assert r.recortado
    assert "Faltan" in r.texto
    assert len(r.texto) <= 200


def test_singular_del_aviso():
    r = acotar(["• a" * 100, "• b" * 100], presupuesto=170, plural="fabricantes")
    if r.total - r.mostrados == 1:
        assert "1 fabricante:" in r.texto or "1 fabricante " in r.texto


def test_lista_vacia_no_revienta():
    r = acotar([], presupuesto=3500, encabezado="Cab:", coletilla="Cola.")
    assert r.total == 0 and not r.recortado
    assert "Faltan" not in r.texto


# ───────────────────────────────── G2 · la fuente

def test_g2_la_fuente_es_documents_no_los_pm_de_chunks(monkeypatch):
    """Regla r27 C1 («jamás los pm de chunks»), que este atajo era el último en
    incumplir. Si alguien vuelve a colgar el catálogo de `chunks`, esto cae."""
    from src.bot import telegram_bot as tb

    llamadas = []
    monkeypatch.setattr(tb, "get_manufacturers_by_docs",
                        lambda: (llamadas.append("docs") or
                                 [("Notifier", 456), ("Morley", 230)]))

    def _prohibida():
        raise AssertionError("el atajo NO puede leer los product_model de chunks")

    monkeypatch.setattr(tb, "get_all_models_by_category", _prohibida)
    texto = tb._texto_fabricantes(por_producto=False)
    assert llamadas == ["docs"]
    assert "Notifier" in texto and "Morley" in texto


def test_g2_fail_open_si_la_base_no_responde(monkeypatch):
    from src.bot import telegram_bot as tb

    def _cae():
        raise RuntimeError("supabase caido")

    monkeypatch.setattr(tb, "get_manufacturers_by_docs", _cae)
    texto = tb._texto_fabricantes(por_producto=False)
    assert texto                      # degrada, no deja al técnico sin nada
    assert "Notifier" in texto


def test_el_encabezado_reconoce_lo_que_se_pregunto(monkeypatch):
    from src.bot import telegram_bot as tb
    monkeypatch.setattr(tb, "get_manufacturers_by_docs",
                        lambda: [("Notifier", 456), ("Morley", 230)])
    marcas = tb._texto_fabricantes(por_producto=False)
    productos = tb._texto_fabricantes(por_producto=True)
    assert "fabricantes" in marcas.lower()
    # quien pregunta por PRODUCTOS recibe una explicación de por qué ve marcas
    assert "producto" in productos.lower()
    assert marcas != productos
