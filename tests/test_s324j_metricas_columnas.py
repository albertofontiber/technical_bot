# -*- coding: utf-8 -*-
"""s324j — Las métricas: columnas declaradas en los DOS sentidos (puerta 8 de
`evals/s324i_panel_vercel_propuesta_v9.md` §7). Esto INVIERTE una decisión
escrita (`select=*` para que lo nuevo se enseñara): expuesto a internet, nada
se pinta sin que alguien lo haya declarado.
"""
from __future__ import annotations

from dashboard import app as panel
from dashboard import datos


def test_leer_vista_pide_solo_las_columnas_declaradas(monkeypatch):
    capturado = {}

    def leer(recurso, params):
        capturado["recurso"] = recurso
        capturado["params"] = dict(params)
        return datos.Resultado(datos.VACIO, [])

    monkeypatch.setattr(datos, "leer", leer)
    vista = datos.VISTAS_POR_CLAVE["bot_health_daily"]
    datos.leer_vista(vista)
    assert capturado["params"]["select"] == ",".join(
        c.nombre for c in vista.columnas)
    assert "*" not in capturado["params"]["select"]


def test_sentido_1_una_columna_no_declarada_no_se_pinta():
    """Aunque el transporte trajera una columna de más (una vista redeployada
    antes que el panel), el render NO la enseña: doble cierre con el select."""
    vista = datos.VISTAS_POR_CLAVE["bot_motivos_negativos"]
    resultado = datos.Resultado(datos.OK, [{
        "semana": "2026-08-10", "motivo": "info", "votos": 2,
        "telegram_user_id_filtrado": 111222333,      # la intrusa
    }])
    html = str(panel._tabla_de_vista(vista, resultado))
    assert "111222333" not in html
    assert "telegram_user_id_filtrado" not in html
    assert "info" in html                            # y lo declarado sí


def test_sentido_2_una_declarada_que_desaparece_se_detecta_y_se_dice(monkeypatch):
    """Con el select explícito, la columna declarada que la vista pierde
    produce un 42703 que `datos.leer` traduce a un detalle LEGIBLE — la
    tarjeta lo dice en vez de romper la página o murmurar «Supabase respondió
    400»."""
    class _Resp:
        status_code = 400
        def json(self):
            return {"code": "42703", "message": "column x does not exist"}

    class _Cliente:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, *a, **k): return _Resp()

    monkeypatch.setattr(datos, "hay_credenciales", lambda: True)
    monkeypatch.setattr(datos.httpx, "Client", _Cliente)
    resultado = datos.leer("bot_health_daily", {"select": "no_existe"})
    assert resultado.estado == datos.ERROR
    assert "columna declarada" in resultado.detalle
    assert "datos.VISTAS" in resultado.detalle
