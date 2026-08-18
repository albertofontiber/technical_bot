# -*- coding: utf-8 -*-
"""s324h — Las dos puertas que la v5 declaraba PENDIENTES.

1. **La invariante de `Procedencia` vive en el TIPO.** La primera versión la ponía
   sólo en los constructores nombrados, y Sol y Fable la tumbaron por separado
   (r47): `Procedencia(...)` es público y saltárselos es trivial. Aquí se prueba
   que los estados inválidos LANZAN, en vez de afirmarlo en un documento.

2. **Test AST: ningún `log_query` del bot puede omitir su canal.** La v3 sólo
   exigía `source=`; Fable (r43) señaló que así un atajo podía registrar
   `source="voice"` y perder el ASR crudo sin que la suite lo notara. Se exigen
   los DOS. Precedente en casa: el test de mecanicidad por AST de
   `_resolver_hechos` en `test_s316e_fase_a_equivalencia.py`.

El defecto que ambas cierran es el mismo: un default que miente. `log_query`,
`_process_query`, `TurnRequest`, `build_turn_request`, `Meta.fuente` y la propia
columna `query_logs.source` declaraban todos `= "text"`, así que olvidarse de la
procedencia no fallaba — registraba en silencio que un audio se había tecleado.
"""
from __future__ import annotations

import ast
import inspect

import pytest

from src.bot.procedencia import CANALES, Procedencia


# ─────────────────────────────── 1. la invariante, probada y no afirmada

def test_los_constructores_nombrados_funcionan():
    assert Procedencia.de_texto() == Procedencia(source="text")
    assert Procedencia.de_voz("hola qué tal").transcription == "hola qué tal"
    assert Procedencia.de_voz("x").es_voz is True
    assert Procedencia.de_texto().es_voz is False


@pytest.mark.parametrize("kwargs,motivo", [
    ({"source": "voice"}, "voz sin ASR crudo"),
    ({"source": "voice", "transcription": None}, "voz con transcripción None"),
    ({"source": "voice", "transcription": ""}, "voz con ASR vacío"),
    ({"source": "voice", "transcription": "   "}, "voz con ASR en blanco"),
    ({"source": "text", "transcription": "algo"}, "texto CON transcripción"),
    ({"source": "whatsapp"}, "canal inventado"),
    ({"source": "error"}, "pseudo-fuente de logging, no canal de turno"),
    ({"source": ""}, "canal vacío"),
])
def test_el_estado_incorrecto_NO_se_puede_construir(kwargs, motivo):
    """Cada fila es un estado que la v4 afirmaba imposible y era construible."""
    with pytest.raises(ValueError):
        Procedencia(**kwargs)


def test_la_cadena_vacia_no_cuela_por_los_constructores():
    """(Sol, r48) `is not None` no sostenía «voz exige ASR crudo»."""
    with pytest.raises(ValueError):
        Procedencia.de_voz("")


def test_es_inmutable():
    p = Procedencia.de_voz("dicho")
    with pytest.raises(Exception):
        p.source = "text"                                    # type: ignore[misc]


def test_error_NO_es_un_canal_de_turno():
    """Declarado en la v5 §7: `query_logs.source` es TERNARIO ('error' incluido)
    y `Procedencia` es BINARIA. No es una incoherencia que arreglar: `'error'` es
    una pseudo-fuente de LOGGING que escribe el manejador de errores y que nunca
    construye una procedencia — un turno viene de una persona por un canal."""
    assert "error" not in CANALES


# ─────────────────────── 2. el mapa a `Meta.fuente` debe cubrir TODOS los canales

def test_el_mapa_de_Meta_cubre_todos_los_canales():
    """(Sol, r47) La primera versión hacía `"voz" if source == "voice" else
    "texto"`, que manda cualquier canal futuro a «texto» EN SILENCIO — el mismo
    default mentiroso que este lote mata, reintroducido en el arreglo. Con el mapa
    explícito, un canal sin traducir revienta aquí en vez de en producción."""
    from src.bot.telegram_bot import _FUENTE_META

    assert set(_FUENTE_META) == set(CANALES), (
        "hay un canal sin traducción a Meta.fuente: se clasificaría mal")


# ─────────────────────── 3. AST: ningún log_query del bot sin su procedencia

def _llamadas_log_query(fn) -> list[ast.Call]:
    arbol = ast.parse(inspect.getsource(fn).lstrip())
    return [n for n in ast.walk(arbol)
            if isinstance(n, ast.Call)
            and getattr(n.func, "id", None) == "log_query"]


@pytest.mark.parametrize("nombre", ["_ejecutar_plan", "_responder_atajo"])
def test_ningun_atajo_registra_sin_declarar_su_canal(nombre):
    """La puerta que convierte «acuérdate» en «no pasa la suite».

    Se exigen `source=` **y** `transcription=`: con sólo el primero, un atajo
    podía registrar `source="voice"` y tirar el ASR crudo sin que nadie lo notara
    (Fable, r43).
    """
    from src.bot import telegram_bot as bot

    llamadas = _llamadas_log_query(getattr(bot, nombre))
    assert llamadas, f"{nombre} ya no registra: ¿se movió el log?"
    for c in llamadas:
        claves = {k.arg for k in c.keywords}
        assert "source" in claves, (
            f"{nombre}: un log_query sin `source=` quedaría atribuido a texto")
        assert "transcription" in claves, (
            f"{nombre}: un log_query sin `transcription=` tiraría el ASR crudo")


def test_log_query_no_tiene_default_de_canal():
    """La raíz: mientras `source` tenga default, olvidarlo es una mentira
    silenciosa en vez de un `TypeError`."""
    from src.logging_db import log_query

    firma = inspect.signature(log_query)
    assert firma.parameters["source"].default is inspect.Parameter.empty, (
        "`log_query.source` volvió a tener default: el olvido vuelve a ser mudo")


def test_process_query_tampoco():
    """(Sol, r48) El QUINTO default: era una segunda vía viva de reetiquetar voz
    como texto que la partición Fase 1/Fase 2 dejaba abierta."""
    from src.bot.telegram_bot import _process_query

    firma = inspect.signature(_process_query)
    assert firma.parameters["source"].default is inspect.Parameter.empty
