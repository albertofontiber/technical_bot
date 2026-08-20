# -*- coding: utf-8 -*-
"""s329 — el enlace de invitación es de copiar y pegar SIEMPRE.

Lo que protege: la resolución del username del bot dejó de depender de que
alguien acuerde poner `TELEGRAM_BOT_USERNAME` en cada entorno (Vercel prod,
previews, local, CLI). El default vive en código (`BOT_USERNAME_DEFECTO`,
verificado contra `getMe` con el token vivo del worker en s329) y la variable
queda como override. La clase de fallo «enlace con `<NOMBRE_DEL_BOT>` a mano»
se elimina por construcción: sin rama-placeholder no hay placeholder.
"""
from __future__ import annotations

import pytest

from dashboard import datos, gestion
from src.bot import access


@pytest.fixture(autouse=True)
def sin_variable(monkeypatch):
    """El suelo de estos tests es el entorno SIN la variable: exactamente el
    estado real de Vercel y Railway hoy (censo s329)."""
    monkeypatch.delenv("TELEGRAM_BOT_USERNAME", raising=False)


# ------------------------------------------------------------- resolución


def test_sin_variable_resuelve_al_default_de_produccion():
    assert access.bot_username_publico() == access.BOT_USERNAME_DEFECTO
    assert access.BOT_USERNAME_DEFECTO == "PCI_Soporte_tecnico_bot"


def test_la_variable_manda_sobre_el_default(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "@Otro_Bot_De_Pruebas")
    assert access.bot_username_publico() == "Otro_Bot_De_Pruebas"


def test_el_explicito_manda_sobre_la_variable(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "Otro_Bot_De_Pruebas")
    assert access.bot_username_publico("@Bot_Del_Flag") == "Bot_Del_Flag"


def test_variable_vacia_o_solo_arroba_no_rompe_el_enlace(monkeypatch):
    """Una variable puesta-pero-inútil no puede devolver un username vacío:
    `t.me/?start=...` sería un enlace roto con cara de éxito."""
    for basura in ("", "   ", "@", "@@"):
        monkeypatch.setenv("TELEGRAM_BOT_USERNAME", basura)
        assert access.bot_username_publico() == access.BOT_USERNAME_DEFECTO


# ------------------------------------------------- el panel emite completo


def test_generar_invitacion_sin_variable_da_enlace_de_copiar_y_pegar(monkeypatch):
    escrito = {}

    def _escribir_fingido(metodo, tabla, json):
        escrito["json"] = json
        return datos.OK, [{"id": "11111111-1111-1111-1111-111111111111"}], ""

    monkeypatch.setattr(gestion, "_escribir", _escribir_fingido)
    accion = gestion.generar_invitacion(
        nota="Gabriel de Muguerza", dias=2, por="alberto", op="op_de_prueba_1"
    )
    assert accion.ok
    assert accion.enlace is not None
    assert accion.enlace.startswith(
        f"https://t.me/{access.BOT_USERNAME_DEFECTO}?start="
    )
    assert "<NOMBRE_DEL_BOT>" not in accion.enlace
    assert "OJO" not in accion.mensaje
