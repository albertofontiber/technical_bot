# -*- coding: utf-8 -*-
"""s326 — el Explorador: filtros CERRADOS y render sin fugas.

Los invariantes:
  1. ningún parámetro de la URL llega a PostgREST sin pasar por su lista
     cerrada (periodo/feedback fijas, categoría = taxonomía, marca = derivada
     de los datos) — lo de fuera de lista cae al defecto, no se parsea;
  2. la prosa del técnico se pinta ESCAPADA (la pregunta es texto hostil);
  3. sin la migración 021 la página lo DICE (tabla_ausente → «falta aplicar»),
     no revienta ni miente con una tabla vacía.

La puerta de sesión, las cabeceras y el CSRF de `/explorador` los cubre
`test_s324f_dashboard_rutas.py`, que parametriza sobre TODAS las rutas de
`panel.RUTAS` — esta página entra ahí sola al registrarse.
"""
from __future__ import annotations

import pytest

from dashboard import app as panel
from dashboard import datos, explorador

CATS = explorador.categorias_validas()
MARCAS = ["Detnov", "Morley-IAS"]


# ------------------------------------------------------------------- filtros


def _filtros(**consulta):
    consulta = {k: [v] for k, v in consulta.items()}
    return explorador.normalizar(consulta, categorias=CATS, marcas=MARCAS)


def test_categorias_fail_open_si_la_taxonomia_no_carga(monkeypatch):
    """Incidente del preview (19-ago): un fallo cargando la taxonomía no puede
    ser un 500 — la lista queda vacía, el select en «todas», la página vive."""
    def _roto():
        raise RuntimeError("yaml roto o ausente")

    explorador.categorias_validas.cache_clear()
    monkeypatch.setattr(explorador, "cargar_taxonomia", _roto)
    try:
        assert explorador.categorias_validas() == ()
        filtros = explorador.normalizar({"categoria": ["normativa"]},
                                        categorias=(), marcas=MARCAS)
        assert filtros.categoria is None
    finally:
        explorador.categorias_validas.cache_clear()


def test_todo_fuera_de_lista_cae_al_defecto():
    filtros = _filtros(dias="9999", categoria="inventada",
                       marca="ACME'; DROP TABLE--", feedback="lo que sea")
    assert filtros.dias == explorador.VENTANA_DEFECTO
    assert filtros.categoria is None
    assert filtros.marca is None
    assert filtros.feedback == explorador.FEEDBACK_DEFECTO


def test_los_valores_de_lista_pasan_enteros():
    filtros = _filtros(dias="7", categoria="averias_diagnostico",
                       marca="Morley-IAS", feedback="down")
    assert (filtros.dias, filtros.categoria, filtros.marca, filtros.feedback) \
        == (7, "averias_diagnostico", "Morley-IAS", "down")


def test_parametros_construye_los_filtros_de_postgrest():
    params = explorador.parametros(_filtros(
        dias="7", categoria="normativa", marca="Detnov", feedback="down"))
    assert params["categoria"] == "eq.normativa"
    assert params["marcas"] == 'cs.{"Detnov"}'
    assert params["verdict"] == "eq.down"
    assert params["created_at"].startswith("gte.")
    assert params["order"] == "created_at.desc"
    assert params["limit"] == str(explorador.TOPE_FILAS)


def test_parametros_sin_filtros_y_ventana_todo():
    params = explorador.parametros(_filtros(dias="0"))
    assert "created_at" not in params
    assert "categoria" not in params and "marcas" not in params
    assert "verdict" not in params and "comment" not in params


def test_comentados_filtra_por_comment_no_por_verdict():
    params = explorador.parametros(_filtros(feedback="comentados"))
    assert params["comment"] == "not.is.null"
    assert "verdict" not in params


# -------------------------------------------------------------------- página


FILA = {
    "id": "u-1", "created_at": "2026-08-18T20:36:00Z", "canal": "voice",
    "ruta": "rag", "categoria": "averias_diagnostico", "taxonomia_version": 1,
    "marcas": ["Detnov"], "modelos": ["CAD-250"],
    "pregunta": "<script>alert('x')</script> ¿fallo de tierra?",
    "response_length": 494, "quien": "Juan Pérez, DG de Acme",
    "verdict": "down", "reason_class": "info",
    "comment": "faltaba el paso <b>3</b>",
}


def _peticion(consulta=None):
    return panel.Peticion(
        metodo="GET", ruta="/explorador", consulta=consulta or {},
        cabeceras={}, cuerpo=b"", ip="1.2.3.4", nonce="nonce-de-pruebas",
        sesion={"u": "alberto", "csrf": "token"})


@pytest.fixture()
def doble(monkeypatch):
    lecturas = {}

    def _leer(recurso, params, presupuesto=None):
        lecturas[recurso] = params
        if recurso == "documents":
            return datos.Resultado(datos.OK,
                                   [{"manufacturer": m} for m in MARCAS])
        if recurso == "bot_explorador_v1":
            return datos.Resultado(datos.OK, [FILA])
        return datos.Resultado(datos.TABLA_AUSENTE, detalle=recurso)

    monkeypatch.setattr(datos, "leer", _leer)
    return lecturas


def test_la_pagina_pinta_la_prosa_escapada(doble):
    respuesta = panel.pagina_explorador(_peticion({"feedback": ["down"]}))
    texto = respuesta.cuerpo.decode("utf-8")
    assert respuesta.estado == 200
    assert "&lt;script&gt;" in texto and "<script>alert" not in texto
    assert "faltaba el paso &lt;b&gt;3&lt;/b&gt;" in texto
    assert "Juan Pérez, DG de Acme" in texto
    assert "👎 · info" in texto
    assert doble["bot_explorador_v1"]["verdict"] == "eq.down"


def test_un_parametro_hostil_no_llega_a_postgrest(doble):
    panel.pagina_explorador(_peticion({"marca": ["ACME'; DROP--"],
                                       "categoria": ["inventada"]}))
    params = doble["bot_explorador_v1"]
    assert "marcas" not in params and "categoria" not in params


def test_sin_la_021_la_pagina_lo_dice(monkeypatch):
    def _leer(recurso, params, presupuesto=None):
        if recurso == "documents":
            return datos.Resultado(datos.VACIO)
        return datos.Resultado(datos.TABLA_AUSENTE, detalle=recurso)

    monkeypatch.setattr(datos, "leer", _leer)
    texto = panel.pagina_explorador(_peticion()).cuerpo.decode("utf-8")
    assert "021_query_clasificacion.sql" in texto


def test_si_la_lista_de_marcas_no_se_puede_leer_la_pagina_lo_dice(monkeypatch):
    """«no hay marcas» y «no se pudo leer la lista» son pantallas distintas
    (hallazgo Fable r1 s326): la degradación se declara, no se esconde."""
    def _leer(recurso, params, presupuesto=None):
        if recurso == "bot_explorador_v1":
            return datos.Resultado(datos.OK, [FILA])
        return datos.Resultado(datos.ERROR, detalle="caída")

    monkeypatch.setattr(datos, "leer", _leer)
    texto = panel.pagina_explorador(_peticion()).cuerpo.decode("utf-8")
    assert "No se pudo leer la lista de fabricantes" in texto


def test_el_filtro_elegido_queda_seleccionado(doble):
    texto = panel.pagina_explorador(
        _peticion({"categoria": ["normativa"], "dias": ["7"]})
    ).cuerpo.decode("utf-8")
    assert '<option value="normativa" selected>' in texto
    assert '<option value="7" selected>' in texto
