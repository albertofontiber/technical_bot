# -*- coding: utf-8 -*-
"""s317 — Cliente HTTP compartido (#72 fase 1): contratos del shim y del pool.

La SUITE entera corre con HTTP_POOL=off (conftest.py raíz): los fakes de red
existentes siguen interceptando y lo que la suite verifica es la EQUIVALENCIA
de conducta de los 55 sitios migrados. Aquí se fija además la mecánica del
pool ON (con dobles propios) y el kill-switch.
"""
import os

import httpx
import pytest

from src import http_pool


@pytest.fixture(autouse=True)
def _pool_limpio():
    http_pool.cerrar()
    yield
    http_pool.cerrar()


def test_la_suite_corre_con_pool_off():
    """El conftest raíz fija el OFF para que los ~20 ficheros de fakes de red
    sigan interceptando sin churn. Si esto falla, la suite entera está
    ejercitando un camino distinto del que cree."""
    assert os.environ.get("HTTP_POOL") == "off"


def test_pool_on_reutiliza_un_unico_cliente(monkeypatch):
    monkeypatch.setenv("HTTP_POOL", "on")
    construidos = []
    real = httpx.Client

    def espia(**kwargs):
        construidos.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(http_pool.httpx, "Client", espia)
    a = http_pool._cliente_proceso()
    b = http_pool._cliente_proceso()
    assert a is b
    assert len(construidos) == 1


def test_limits_viven_en_el_transporte(monkeypatch):
    """(Sol r14 M1, verificado ejecutando) Un HTTPTransport explícito IGNORA
    los limits del Client: el keep-alive prometido era código muerto con
    expiry default de 5 s. Los limits DEBEN entrar por el transporte — y este
    test lo mide en el POOL EFECTIVO, no en kwargs."""
    monkeypatch.setenv("HTTP_POOL", "on")
    cliente = http_pool._cliente_proceso()
    pool = cliente._transport._pool
    assert pool._max_keepalive_connections == 10
    assert pool._keepalive_expiry == 30.0
    assert pool._max_connections == 40
    # y CERO retries: hasta el retry de connect es política (fase 2 de #72)
    assert pool._retries == 0


def test_shim_on_inyecta_el_timeout_del_sitio(monkeypatch):
    """Cada sitio conserva SU timeout: el shim lo pasa por PETICIÓN al cliente
    compartido — la migración no puede cambiar un timeout ni un byte."""
    monkeypatch.setenv("HTTP_POOL", "on")
    vistos = {}

    class _FakeCliente:
        def request(self, metodo, url, **kwargs):
            vistos.update(metodo=metodo, url=url, **kwargs)
            return "resp"

    monkeypatch.setattr(http_pool, "_cliente_proceso", lambda: _FakeCliente())
    with http_pool.abierto(timeout=7.5) as client:
        assert client.post("http://x", json={"a": 1}) == "resp"
    assert vistos["metodo"] == "POST" and vistos["timeout"] == 7.5
    # un timeout explícito de la llamada GANA al del sitio
    http_pool.abierto(timeout=7.5).get("http://y", timeout=2.0)
    assert vistos["timeout"] == 2.0


def test_shim_off_un_cliente_por_bloque_with(monkeypatch):
    """Kill-switch: UN cliente fresco POR BLOQUE `with` que sirve VARIAS
    peticiones (Sol r14 M2: así es hoy — el retry de compatibilidad de
    logging_db hace 2 POSTs con el mismo cliente), timeout en el CONSTRUCTOR y
    llamada por método nominal — la forma exacta que interceptan los fakes."""
    monkeypatch.setenv("HTTP_POOL", "off")
    construcciones, salidas = [], []

    class _FakeCliente:
        def __init__(self, **kwargs):
            construcciones.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            salidas.append(True)
            return False

        def post(self, url, **kwargs):
            return ("post", url, kwargs)

    monkeypatch.setattr(http_pool.httpx, "Client", _FakeCliente)
    with http_pool.abierto(timeout=9.0) as client:
        out1 = client.post("http://x", json={})
        out2 = client.post("http://x", json={})
    assert out1[0] == out2[0] == "post"
    assert construcciones == [{"timeout": 9.0}]      # UNO por bloque, no dos
    assert salidas == [True]                         # protocolo with, no .close()
    assert "timeout" not in out1[2]                  # NO se inyecta en la petición


def test_shim_off_sin_with_por_peticion(monkeypatch):
    """Fuera de un `with` (SupabaseHTTP persistente) el kill-switch degrada a
    cliente-por-petición — divergencia DECLARADA de la ruta de rollback."""
    monkeypatch.setenv("HTTP_POOL", "off")
    construcciones = []

    class _FakeCliente:
        def __init__(self, **kwargs):
            construcciones.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def get(self, url, **kwargs):
            return "resp"

    monkeypatch.setattr(http_pool.httpx, "Client", _FakeCliente)
    shim = http_pool.abierto(timeout=4.0)
    assert shim.get("http://a") == "resp"
    assert shim.get("http://b") == "resp"
    assert len(construcciones) == 2


def test_timeout_none_no_se_inyecta(monkeypatch):
    """(Fable r14 F3) `abierto()` sin timeout NO puede inyectar timeout=None
    (= infinito explícito): sin timeout de sitio manda el default del cliente
    de proceso."""
    monkeypatch.setenv("HTTP_POOL", "on")
    vistos = {}

    class _FakeCliente:
        def request(self, metodo, url, **kwargs):
            vistos.update(kwargs)
            return "resp"

    monkeypatch.setattr(http_pool, "_cliente_proceso", lambda: _FakeCliente())
    http_pool.abierto().get("http://x")
    assert "timeout" not in vistos


def test_shim_no_cierra_el_cliente_de_proceso(monkeypatch):
    monkeypatch.setenv("HTTP_POOL", "on")
    with http_pool.abierto(timeout=1.0):
        pass
    cliente = http_pool._cliente_proceso()
    with http_pool.abierto(timeout=1.0):
        pass
    assert http_pool._cliente_proceso() is cliente
    assert not cliente.is_closed


def test_cerrar_resetea_el_proceso(monkeypatch):
    monkeypatch.setenv("HTTP_POOL", "on")
    a = http_pool._cliente_proceso()
    http_pool.cerrar()
    b = http_pool._cliente_proceso()
    assert a is not b and a.is_closed and not b.is_closed


def test_ningun_modulo_de_src_construye_httpx_client():
    """Trinquete ESTRUCTURAL (Fable r14 F4: vigilar solo los 10 migrados dejaba
    a los módulos FUTUROS libres de reintroducir el patrón — con 30+ fabricantes
    vendrán módulos nuevos): barrido src/**/*.py entero. La ÚNICA casa legítima
    de `httpx.Client(` es http_pool (el kill-switch y el cliente de proceso)."""
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    permitidos = {"src/http_pool.py"}
    culpables = []
    for py in sorted((raiz / "src").rglob("*.py")):
        rel = py.relative_to(raiz).as_posix()
        if rel in permitidos:
            continue
        if "httpx.Client(" in py.read_text(encoding="utf-8"):
            culpables.append(rel)
    assert not culpables, (
        f"cliente-por-llamada (re)introducido en {culpables} — usa "
        "http_pool.abierto(timeout=...) (#72, perfil s317: 14 clientes/consulta "
        "eran ~10 s/turno)")
