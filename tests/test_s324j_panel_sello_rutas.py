# -*- coding: utf-8 -*-
"""s324j — La revalidación por sello, ejercida por las RUTAS (puertas 1, 2 y 3
de `evals/s324i_panel_vercel_propuesta_v9.md`): revocar y cambiar la
contraseña expulsan en la SIGUIENTE petición — la promesa por la que Alberto
eligió (a2) — y una caída del backend es un 503 que no miente ni mata cookies.

Reutiliza el cliente ASGI y el suelo de `test_s324f_dashboard_rutas` (sin red,
sin claves): mismo panel entero, backend enchufado distinto por test.
"""
from __future__ import annotations

import pytest

from dashboard import auth, sesion

from tests.test_s324f_dashboard_rutas import (  # noqa: F401  (fixtures)
    SECRETO, Cliente, entorno,
)


class BackendMutable:
    """Un backend cuyo estado se puede cambiar A MITAD de sesión — que es
    exactamente lo que el sello existe para detectar."""

    def __init__(self):
        self.registros = {"alberto": "scrypt$n=1024,r=2,p=1$c2Fs$aGFzaA"}
        self.caido = False

    def autenticar(self, usuario, contrasena):
        registro = self.registros.get(usuario.strip().lower())
        if registro is None or contrasena != "correcta":
            return None
        return auth.Usuario(usuario.strip().lower(),
                            sello=auth.sello_de_registro(registro))

    def sello(self, nombre):
        if self.caido:
            raise auth.IdentidadNoDisponible("supabase caído")
        registro = self.registros.get((nombre or "").strip().lower())
        return None if registro is None else auth.sello_de_registro(registro)


@pytest.fixture
def backend():
    b = BackendMutable()
    anterior = auth.usar_backend(b)
    yield b
    auth.usar_backend(anterior)


def _cookie_para(backend, nombre="alberto"):
    payload = sesion.nueva(nombre)
    payload["h"] = backend.sello(nombre)
    return sesion.firmar(payload, SECRETO.encode("utf-8")), payload["csrf"]


# ------------------------------------------------------------------- puerta 1


def test_revocar_expulsa_en_la_siguiente_peticion_borrando_la_cookie(backend):
    cookie, _ = _cookie_para(backend)
    assert Cliente(cookie).get("/").estado == 200        # dentro
    del backend.registros["alberto"]                     # revocado (activo=false)
    respuesta = Cliente(cookie).get("/")
    assert respuesta.estado == 303                       # fuera, YA
    assert respuesta.cabecera("location") == "/entrar"
    assert "Max-Age=0" in respuesta.cabecera("set-cookie")


def test_control_el_activo_no_es_expulsado(backend):
    cookie, _ = _cookie_para(backend)
    for _ in range(3):
        assert Cliente(cookie).get("/").estado == 200


# ------------------------------------------------------------------- puerta 2


def test_cambiar_la_contrasena_expulsa_en_la_siguiente_peticion(backend):
    cookie, _ = _cookie_para(backend)
    assert Cliente(cookie).get("/").estado == 200
    backend.registros["alberto"] = "scrypt$n=1024,r=2,p=1$b3RyYQ$b3Ryb2hhc2g"
    respuesta = Cliente(cookie).get("/")
    assert respuesta.estado == 303
    assert "Max-Age=0" in respuesta.cabecera("set-cookie")


def test_cookie_firmada_valida_pero_sin_h_sale_por_el_camino_normal(backend):
    """El caso legado (ronda F2-m1): cookies de antes del despliegue no llevan
    `h` → fuera SIN excepción (compare_digest no llega a ver un None)."""
    payload = sesion.nueva("alberto")                    # sin h
    cookie = sesion.firmar(payload, SECRETO.encode("utf-8"))
    respuesta = Cliente(cookie).get("/")
    assert respuesta.estado == 303
    assert "Max-Age=0" in respuesta.cabecera("set-cookie")


# ------------------------------------------------------------------- puerta 3


def test_backend_caido_es_503_de_estado_sin_matar_la_cookie(backend):
    """Fail-closed SIN mentir: no se sirve NINGÚN dato, la cookie sigue viva
    (un timeout no es un cierre de sesión falso), y al volver la base el
    revocado es expulsado en su primera petición."""
    cookie, _ = _cookie_para(backend)
    backend.caido = True
    respuesta = Cliente(cookie).get("/acceso")
    assert respuesta.estado == 503
    assert "no puede comprobar identidades" in respuesta.texto.lower() or \
           "no puede comprobar" in respuesta.texto
    assert respuesta.cabecera("set-cookie") is None      # sin matar la cookie
    assert "Juan" not in respuesta.texto                 # y sin servir datos
    # La base vuelve — y el revocado durante la caída sale a la primera:
    backend.caido = False
    del backend.registros["alberto"]
    assert Cliente(cookie).get("/").estado == 303


def test_login_con_backend_caido_es_503_no_credenciales_incorrectas(backend):
    backend.caido = True

    def autenticar_caido(usuario, contrasena):
        raise auth.IdentidadNoDisponible("supabase caído")

    backend.autenticar = autenticar_caido
    respuesta = Cliente().post("/entrar", {"usuario": "alberto",
                                           "contrasena": "correcta"})
    assert respuesta.estado == 503
    assert "Usuario o contraseña incorrectos" not in respuesta.texto


# --------------------------------------------------------- /salir es LOCAL


def test_salir_funciona_con_el_backend_caido(backend):
    """Ronda S4-m1: borrar tu propia cookie no puede depender de Supabase — con
    la base caída, el /salir revalidado daría 503 y dejaría VIVA la cookie que
    intentabas destruir."""
    cookie, csrf = _cookie_para(backend)
    backend.caido = True
    respuesta = Cliente(cookie).post("/salir", {"csrf": csrf})
    assert respuesta.estado == 303
    assert "Max-Age=0" in respuesta.cabecera("set-cookie")
