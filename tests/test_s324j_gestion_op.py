# -*- coding: utf-8 -*-
"""s324j — Idempotencia por operación y la firma de la anulación (puertas 7 y
el lado-código de 9-bis; `evals/s324i_panel_vercel_propuesta_v9.md` §4.2-§4.3).
"""
from __future__ import annotations

import pytest

from dashboard import datos, gestion


def _escribir_doble(respuestas):
    """Un `_escribir` de mentira que consume respuestas por orden y registra
    cada llamada. `respuestas` = lista de (estado, filas, detalle)."""
    def escribir(metodo, tabla, *, params=None, json=None):
        escribir.llamadas.append((metodo, tabla, params, json))
        return respuestas.pop(0)
    escribir.llamadas = []
    return escribir


# ------------------------------------------------------------------- puerta 7


def test_mismo_op_dos_veces_una_invitacion_y_el_mensaje_sin_enlace(monkeypatch):
    """El F5: el segundo POST con el MISMO op choca con el UNIQUE (DUPLICADO)
    → no se crea nada, no se finge poder re-enseñar el enlace."""
    fila = {"id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"}
    doble = _escribir_doble([
        (datos.OK, [fila], ""),
        (gestion.DUPLICADO, [], "bot_invitaciones"),
    ])
    monkeypatch.setattr(gestion, "_escribir", doble)

    primera = gestion.generar_invitacion(nota="Ana, DG", dias=2,
                                         por="alberto", op="op-repetida-123")
    assert primera.ok and primera.enlace

    segunda = gestion.generar_invitacion(nota="Ana, DG", dias=2,
                                         por="alberto", op="op-repetida-123")
    assert not segunda.ok
    assert segunda.enlace is None
    assert "Ya emitiste" in segunda.mensaje
    assert segunda.tono == "aviso"               # reintento, no error del panel
    assert len(doble.llamadas) == 2              # y solo DOS intentos de escritura


def test_op_distinto_son_dos_invitaciones(monkeypatch):
    doble = _escribir_doble([
        (datos.OK, [{"id": "a" * 8}], ""),
        (datos.OK, [{"id": "b" * 8}], ""),
    ])
    monkeypatch.setattr(gestion, "_escribir", doble)
    r1 = gestion.generar_invitacion(nota="x", dias=2, por="a", op="op-uno-1234")
    r2 = gestion.generar_invitacion(nota="x", dias=2, por="a", op="op-dos-1234")
    assert r1.ok and r2.ok
    assert doble.llamadas[0][3]["op"] == "op-uno-1234"
    assert doble.llamadas[1][3]["op"] == "op-dos-1234"


@pytest.mark.parametrize("op_malo", ["", "corto", "x" * 65, "con espacio!", None])
def test_un_op_manipulado_no_llega_a_la_base(monkeypatch, op_malo):
    def prohibido(*a, **k):
        raise AssertionError("no se escribe con un op inadmisible")
    monkeypatch.setattr(gestion, "_escribir", prohibido)
    resultado = gestion.generar_invitacion(nota="x", dias=2, por="a", op=op_malo)
    assert not resultado.ok
    assert "Recarga" in resultado.mensaje


def test_el_409_de_otros_caminos_sigue_siendo_error(monkeypatch):
    """`DUPLICADO` lo consume SOLO la emisión: para el resto de escrituras un
    duplicado es el error que es (v9 §4.2)."""
    doble = _escribir_doble([
        (datos.OK, [{"id": "3f2a1b4c-5d6e-4f70-8192-a3b4c5d6e7f8",
                     "nota": "x", "canjeada_at": None, "revocada_at": None}], ""),
        (gestion.DUPLICADO, [], "bot_invitaciones"),
    ])
    monkeypatch.setattr(gestion, "_escribir", doble)
    resultado = gestion.revocar_invitacion(
        invitacion_id="3f2a1b4c-5d6e-4f70-8192-a3b4c5d6e7f8", por="alberto")
    assert not resultado.ok                      # no se disfraza de éxito


# ------------------------------------------------- la firma de la anulación


def test_anular_firma_en_revocada_por_y_es_condicional(monkeypatch):
    doble = _escribir_doble([
        (datos.OK, [{"id": "3f2a1b4c-5d6e-4f70-8192-a3b4c5d6e7f8",
                     "nota": "Ana, DG", "canjeada_at": None,
                     "revocada_at": None}], ""),
        (datos.OK, [{"id": "3f2a1b4c-5d6e-4f70-8192-a3b4c5d6e7f8"}], ""),
    ])
    monkeypatch.setattr(gestion, "_escribir", doble)
    resultado = gestion.revocar_invitacion(
        invitacion_id="3f2a1b4c-5d6e-4f70-8192-a3b4c5d6e7f8", por="alberto")
    assert resultado.ok
    metodo, tabla, params, json = doble.llamadas[1]
    assert (metodo, tabla) == ("PATCH", "bot_invitaciones")
    # Condicional (la carrera con el canje) + firma en LA COLUMNA, no en la nota:
    assert params["revocada_at"] == "is.null"
    assert params["canjeada_at"] == "is.null"
    assert json["revocada_por"] == "panel:alberto"
    assert "nota" not in json                    # r41 retirado: 42501 imposible
