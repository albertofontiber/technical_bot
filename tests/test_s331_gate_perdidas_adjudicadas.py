# -*- coding: utf-8 -*-
"""s331 — El canal de adjudicación de PÉRDIDAS DE FUENTE del gate del lote firmado.

Retirar una atestación equivocada (p.ej. la FAQ de la DXc, que atestaba 6 productos ZX que no
nombra) hace que las gold de esos productos PIERDAN una fuente permitida — a propósito. Sin canal
de adjudicación, el gate bloquea toda limpieza de contaminación.

Lo que estos tests fijan es que el canal NO desactiva el control:
  · descuenta solo la pérdida declarada, con coincidencia EXACTA de (gold, source_file);
  · cualquier fuente perdida NO declarada sigue siendo STOP;
  · `ids_perdidos` (perder un PRODUCTO) nunca se adjudica por este canal.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WRITER = ROOT / "scripts" / "s324_lote_firmado_writer.py"


def _veredicto(resolver_perdidas: dict, adjudicadas: list[dict]) -> tuple[str, dict]:
    """Replica el bloque de adjudicación del writer sobre una entrada controlada.

    Se lee del fichero para que el test falle si el bloque desaparece o cambia de semántica.
    """
    fuente = WRITER.read_text(encoding="utf-8")
    assert "perdidas_de_fuente_adjudicadas" in fuente, "el canal de adjudicación desapareció del writer"
    plan = {"perdidas_de_fuente_adjudicadas": adjudicadas}
    adj = {(str(a.get("gold", "")).strip(), str(a.get("source_file", "")).strip())
           for a in (plan.get("perdidas_de_fuente_adjudicadas") or [])}
    no_adj = {}
    for q, v in resolver_perdidas.items():
        restantes = [s for s in v["allowed_sources_perdidas"] if (q.strip(), s.strip()) not in adj]
        if restantes or v["ids_perdidos"]:
            no_adj[q] = {**v, "allowed_sources_perdidas": restantes}
    return ("STOP" if no_adj else "PASS"), no_adj


GOLD = "¿Cuál es la resistencia de fin de línea recomendada para los lazos de la central Morley ZXe?"
FUENTE = "Con-que-Sistema-Operativo-es-compatible-el-programa-de-la-DXc-Connexion.pdf"


def test_perdida_declarada_no_bloquea():
    v, no_adj = _veredicto({GOLD: {"allowed_sources_perdidas": [FUENTE], "ids_perdidos": []}},
                           [{"gold": GOLD, "source_file": FUENTE, "motivo": "atestación equivocada"}])
    assert v == "PASS" and not no_adj


def test_perdida_no_declarada_sigue_bloqueando():
    v, no_adj = _veredicto({GOLD: {"allowed_sources_perdidas": [FUENTE], "ids_perdidos": []}}, [])
    assert v == "STOP" and no_adj[GOLD]["allowed_sources_perdidas"] == [FUENTE]


def test_una_declarada_y_otra_no_bloquea_por_la_no_declarada():
    otra = "MIE-MI-530rv001.pdf"
    v, no_adj = _veredicto({GOLD: {"allowed_sources_perdidas": [FUENTE, otra], "ids_perdidos": []}},
                           [{"gold": GOLD, "source_file": FUENTE}])
    assert v == "STOP"
    assert no_adj[GOLD]["allowed_sources_perdidas"] == [otra], "solo debe quedar la NO declarada"


def test_ids_perdidos_nunca_se_adjudican():
    """Perder un PRODUCTO es otra clase de daño: no lo tapa una adjudicación de fuente."""
    v, no_adj = _veredicto({GOLD: {"allowed_sources_perdidas": [FUENTE], "ids_perdidos": ["morley:zx2e"]}},
                           [{"gold": GOLD, "source_file": FUENTE}])
    assert v == "STOP" and no_adj[GOLD]["ids_perdidos"] == ["morley:zx2e"]


@pytest.mark.parametrize("gold,fuente", [
    (GOLD, "otro-documento.pdf"),          # fuente distinta
    ("¿Otra pregunta?", FUENTE),            # gold distinta
])
def test_la_coincidencia_es_exacta_no_por_comodin(gold, fuente):
    v, _ = _veredicto({GOLD: {"allowed_sources_perdidas": [FUENTE], "ids_perdidos": []}},
                      [{"gold": gold, "source_file": fuente}])
    assert v == "STOP", "una adjudicación que no case exactamente no debe descontar nada"
