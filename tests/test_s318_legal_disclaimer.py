# -*- coding: utf-8 -*-
"""s318/#71 — Frame legal_disclaimer del evidence_contract (flag-gated).

El aparato de obligaciones citó el párrafo de responsabilidad legal de KGS
(bcn-3100017 p.4) como obligación técnica: el boilerplate legal lleva
cuantificador universal («en ningún caso…») y vocabulario de obligación.
Censo s318: 108 docs / 119 chunks. Aparato PROTEGIDO (DEC-148): default OFF
byte-idéntico; el ON es adjudicación de Alberto.
"""
from __future__ import annotations

import pytest

from src.rag import evidence_contract as ec
from src.rag.catalog import _fold

KGS = _fold("KGS Fire & Security no se hará responsable en ningún caso de "
            "los daños derivados de la instalación")


def test_flag_off_conducta_byte_identica(monkeypatch):
    """Aparato protegido: sin flag, el frame NO existe — la cláusula KGS sigue
    entrando (la conducta de hoy, con su defecto, intacta hasta adjudicar)."""
    monkeypatch.delenv("EC_LEGAL_DISCLAIMER_SKIP", raising=False)
    assert ec._universal_frame_skip(KGS) is False
    assert ec.lexicon_version_efectiva() == ec.LEXICON_VERSION


def test_flag_on_salta_la_clausula_kgs(monkeypatch):
    monkeypatch.setenv("EC_LEGAL_DISCLAIMER_SKIP", "on")
    assert ec._universal_frame_skip(KGS) is True
    assert ec.lexicon_version_efectiva() == ec._LEXICON_VERSION_V3


@pytest.mark.parametrize("clausula", [
    # ES: variantes reales de exención de responsabilidad
    "el fabricante no se hará responsable de los daños",
    "el fabricante declina toda responsabilidad por uso indebido",
    "la empresa no asume ninguna responsabilidad derivada",
    "queda excluida la responsabilidad por daños indirectos",
    # (Sol r16 M3) las variantes del censo que el regex v1 dejaba fuera:
    "en ningún caso será responsable de las pérdidas ocasionadas",
    # los casos REALES del corpus (sonda s318): KGS + Spectrex + Notifier
    "no se hará responsable en ningún caso de los daños derivados de la instalación",
    "no asume ninguna responsabilidad a causa de omisiones en el documento",
    "no será responsable ante usted ni cualquier otra persona de cualquier pérdida, gasto o daño fortuito",
    # EN
    "the manufacturer shall not be liable for any damages",
    "the company assumes no liability for improper installation",
    "in no event shall the manufacturer be liable for damages",
    "no liability for consequential damages is accepted",
    # PT (defensivo — 0 docs en censo, declarado)
    "o fabricante nao se responsabiliza por danos",
])
def test_clase_responsabilidad_matchea(monkeypatch, clausula):
    monkeypatch.setenv("EC_LEGAL_DISCLAIMER_SKIP", "on")
    assert ec._universal_frame_skip(_fold(clausula)) is True


@pytest.mark.parametrize("clausula", [
    # Obligaciones TÉCNICAS reales que comparten vocabulario — JAMÁS se saltan
    # (el daño de un falso skip es PERDER una obligación del manual):
    "todos los detectores deben conectarse al lazo con cable apantallado",
    "cada circuito de sirena requiere supervision de linea",
    # «responsable» en sentido operativo, sin negación de exención:
    "el tecnico responsable de la instalacion debe verificar cada zona",
    # (Fable r16) responsabilidad FUNCIONAL de componentes — arquitectura real
    # con la forma negada pero SIN contexto de exención: no se salta:
    "el modulo aislador no es responsable de generar la señal de alarma",
    "la central no sera responsable de la supervision del lazo secundario",
    # «in no event» TÉCNICO (sin contexto de responsabilidad): no matchea
    "in no event should the loop current exceed 500 ma on any circuit",
    # garantía: clase FUERA del v1 a conciencia (carga contenido operativo)
    "la garantia quedara anulada si se abre la carcasa del detector",
])
def test_precision_no_se_come_obligaciones_reales(monkeypatch, clausula):
    monkeypatch.setenv("EC_LEGAL_DISCLAIMER_SKIP", "on")
    assert bool(ec._LEGAL_DISCLAIMER_RX.search(_fold(clausula))) is False


def test_camino_real_universal_obligations_kgs_off_on(monkeypatch):
    """(Sol r16 M4) El GATE REAL, no el regex: `_universal_obligations` con la
    cláusula de responsabilidad REAL del corpus (Notifier, sonda s318 — doble
    «cualquier» = pasa el gate de compuesto) y pregunta-oráculo aplicable.
    Flag OFF: la cláusula legal ENTRA como obligación (el defecto #71, vivo).
    Flag ON: desaparece — y la obligación TÉCNICA de control es INVARIANTE."""
    legal = ("Notifier no será responsable ante usted ni cualquier otra "
             "persona de cualquier pérdida, gasto o daño fortuito, indirecto "
             "o resultante de la instalación del equipo.")
    control = ("Todos los detectores de la serie deben conectarse al lazo "
               "mediante cable apantallado homologado.")
    card = {"source_file": "E56-6514ES-000_test.pdf", "page_number": 4}
    views = [(0, card, legal + "\n\n" + control)]
    q = {"responsable", "perdida", "gasto", "detectores", "apantallado",
         "homologado"}

    def frases(obs):
        return [o["quote"] if "quote" in o else str(o) for o in obs]

    monkeypatch.delenv("EC_LEGAL_DISCLAIMER_SKIP", raising=False)
    off = ec._universal_obligations(q, views)
    texto_off = " || ".join(str(o) for o in off)
    assert "responsable ante usted" in texto_off, (
        "la cláusula legal debe ENTRAR con el flag OFF (el defecto observado); "
        f"obligaciones: {frases(off)}")
    assert "cable apantallado" in texto_off

    monkeypatch.setenv("EC_LEGAL_DISCLAIMER_SKIP", "on")
    on = ec._universal_obligations(q, views)
    texto_on = " || ".join(str(o) for o in on)
    assert "responsable ante usted" not in texto_on, (
        f"la cláusula legal debe SALTARSE con el flag ON; obligaciones: {frases(on)}")
    assert "cable apantallado" in texto_on, (
        "la obligación técnica de control debe ser INVARIANTE al flag")


def test_los_frames_previos_no_cambian_con_el_flag(monkeypatch):
    """El frame nuevo se AÑADE: capability/conditional/example siguen igual en
    ambos estados del flag (no re-litiga el léxico v2)."""
    casos = [
        ("puede conectarse a cualquier central de la serie", True),
        ("si la central esta en modo dia, cada zona se rearma", True),
        ("todos los detectores deben conectarse al lazo", False),
    ]
    for flag in ("", "on"):
        monkeypatch.setenv("EC_LEGAL_DISCLAIMER_SKIP", flag)
        for clausula, esperado in casos:
            assert ec._universal_frame_skip(_fold(clausula)) is esperado, (
                f"flag={flag!r}: {clausula}")
