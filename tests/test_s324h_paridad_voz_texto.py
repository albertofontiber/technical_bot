# -*- coding: utf-8 -*-
"""s324h — GATE: la misma pregunta, la misma respuesta por voz y por texto.

Nace de un fallo del piloto vivo (Alberto, 18-ago): preguntó «¿Qué centrales de
Detnov tienes?» POR VOZ con la transcripción ya correcta, y el bot contestó «no he
encontrado información relevante»; la MISMA pregunta TECLEADA devolvió el listado
de 14 centrales. Medido: el plan acierta con las dos formas — pero `handle_voice`
nunca le pregunta al plan, así que las nueve rutas de atajo son inalcanzables por
voz (declarado en el código como aplazamiento de fase B del #70).

**Este fichero es la PUERTA del GO, no una comprobación de cortesía.** Se escribe
ANTES del cableado, y se ha verificado que DISCRIMINA: hoy falla en las rutas rotas
y pasa en las que ya funcionan. Un gate que pasara igual antes y después no probaría
nada.

Tres clases de test, con intenciones distintas:

  1. **Paridad** (`xfail` hoy) — lo que el lote debe arreglar.
  2. **Procedencia** (`xfail` hoy en las rutas que registran) — que la voz declare su
     canal. Lleva aserción ANTI-VACUIDAD: sin ella el test pasaba cuando la voz no
     escribía NADA, que es justo el estado roto.
  3. **No-regresión** (PASAN hoy, y no pueden dejar de pasar) — la ruta conversacional
     es el destino mayoritario de la voz y HOY sí lleva `source`/`transcription`,
     porque `handle_voice` llama a `_process_query` ella misma. `_ejecutar_plan`
     termina en `_process_query(...)` SIN esos campos, así que un cableado ingenuo
     registraría toda pregunta técnica hablada como texto. Lo cazaron Sol y Opus 5
     por separado en la ronda r44; ninguna de las otras puertas lo veía.

DIFERENCIAS PERMITIDAS entre canales, y sólo estas tres: la burbuja `🎤` que la voz
emite antes de responder, `source`, y `transcription`.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


#: Se pone a True EN EL MISMO COMMIT que cablea la voz al plan. Los `xfail` son
#: `strict`, así que si el cableado llega y esto sigue en False, la suite lo canta
#: por XPASS en vez de dejar la puerta abierta en silencio.
VOZ_CABLEADA_AL_PLAN = True

_PENDIENTE = pytest.mark.xfail(
    not VOZ_CABLEADA_AL_PLAN, strict=True,
    reason="s324h: la voz aún no pasa por plan_turn")


# ─────────────────────────────────── dobles (mismo patrón que test_audio_input.py)

class _Grabadora:
    """Captura lo que el bot EMITE y lo que ESCRIBE, en orden."""

    def __init__(self):
        self.mensajes: list[str] = []
        self.logs: list[dict] = []
        self.rag: list[dict] = []


def _mensaje_base(*, es_reply):
    return dict(
        chat=SimpleNamespace(send_action=AsyncMock()),
        reply_text=AsyncMock(),
        reply_to_message=(SimpleNamespace(message_id=7, chat=SimpleNamespace(id=9))
                          if es_reply else None),
    )


def _update(texto, *, es_reply=False):
    m = SimpleNamespace(text=texto, voice=None, audio=None,
                        **_mensaje_base(es_reply=es_reply))
    return SimpleNamespace(message=m, effective_user=SimpleNamespace(id=123))


def _update_voz(*, es_reply=False):
    voz = SimpleNamespace(file_id="v1", duration=3, file_name=None,
                          mime_type="audio/ogg")
    m = SimpleNamespace(text=None, voice=voz, audio=None,
                        **_mensaje_base(es_reply=es_reply))
    return SimpleNamespace(message=m, effective_user=SimpleNamespace(id=123))


def _context(user_data=None):
    return SimpleNamespace(
        bot=SimpleNamespace(get_file=AsyncMock(
            return_value=SimpleNamespace(download_to_drive=AsyncMock()))),
        user_data={} if user_data is None else user_data,
    )


# ───────────────────────────────────────────────────── el arnés de los dos canales

_MARCAS = {"detnov", "notifier", "aguilera"}
_MODELO_DE = {"CAD-250": "Detnov"}


def _instrumentar(monkeypatch, bot, grab):
    """Turno DETERMINISTA y sin red, SIN saltarse el plan.

    Se doblan las tres funciones de base que el plan declara como hechos —no
    `_resolver_hechos`—, para que la mecánica del plan corra de verdad: lo que se
    mide es paridad, y para eso los dos canales tienen que ver los MISMOS hechos.
    """
    monkeypatch.setattr(bot, "has_consent", lambda _uid: True)
    monkeypatch.setattr(bot, "asegurar_seudonimo", lambda _uid: None)
    monkeypatch.setattr(bot, "manufacturer_in_db", lambda n: n.lower() in _MARCAS)
    monkeypatch.setattr(bot, "lookup_model_manufacturer", lambda m: _MODELO_DE.get(m))
    monkeypatch.setattr(bot, "_lexico_marcas_cacheado", lambda: frozenset(_MARCAS))

    def _log(**kw):
        grab.logs.append(kw)
        return "qlog-1"
    monkeypatch.setattr(bot, "log_query", _log)

    async def _rag(update, context, query, **kw):
        grab.rag.append({"query": query, **kw})
    monkeypatch.setattr(bot, "_process_query", _rag)


def _correr(monkeypatch, bot, texto, *, canal, es_reply=False, user_data=None):
    grab = _Grabadora()
    _instrumentar(monkeypatch, bot, grab)
    ctx = _context(user_data)
    if canal == "voz":
        async def _transcribe(_path):
            return texto
        monkeypatch.setattr(bot, "transcribe_audio", _transcribe)
        up = _update_voz(es_reply=es_reply)
        asyncio.run(bot.handle_voice(up, ctx))
    else:
        up = _update(texto, es_reply=es_reply)
        asyncio.run(bot.handle_message(up, ctx))
    grab.mensajes = [c.args[0] for c in up.message.reply_text.await_args_list]
    return grab, ctx.user_data


# ────────────────────────────────────────────────────────── la tabla de paridad

#: (ruta, pregunta, registra_en_query_logs). `registra` es DATO, no criterio de
#: quien lea: las tres cortesías declaran `log_consulta=False` y feedback escribe
#: en `answer_feedback`, que es otra tabla (censo verificado en s324h).
_FILAS = [
    ("inventario",       "Qué centrales de Detnov tienes",         True),
    ("catalogo",         "Qué productos tienes",                   True),
    ("fabricantes",      "Qué fabricantes tienes",                 True),
    ("cortesia_saludo",  "Hola",                                   False),
    ("cortesia_gracias", "Gracias",                                False),
    ("cortesia_adios",   "Adiós",                                  False),
    ("marca_no_servida", "Tienes algo de Bosch",                   True),
    ("feedback",         "Está mal, eso no es correcto",           False),
    ("conversacional",   "Cómo se conecta el lazo de la CAD-250",  False),
]

#: Dos tablas, porque lo que está roto hoy NO es lo mismo en los dos tests — y el
#: `xfail` es `strict`, así que marcar de más se paga con un XPASS. Esa precisión es
#: el punto: el gate declara exactamente qué falla y por qué.
#:
#: PARIDAD: falla en las ocho rutas de atajo. `conversacional` es la única que la voz
#: ya alcanza hoy (va directa al RAG), así que es la única sin marca.
_TABLA_PARIDAD = [
    pytest.param(r, p, reg, marks=([] if r == "conversacional" else [_PENDIENTE]),
                 id=r)
    for r, p, reg in _FILAS
]

#: PROCEDENCIA: sólo puede fallar donde hay fila que inspeccionar. En las rutas que
#: NO registran (las tres cortesías y feedback) el test pasa hoy —vacuamente— y
#: seguirá pasando: marcarlas `xfail` sería afirmar un fallo que no existe.
_TABLA_PROCEDENCIA = [
    pytest.param(r, p, reg, marks=([_PENDIENTE] if reg else []), id=r)
    for r, p, reg in _FILAS
]


def _sin_burbuja_asr(mensajes: list[str], crudo: str) -> list[str]:
    return [m for m in mensajes if not (m.startswith("🎤") and crudo in m)]


def _comparables(logs: list[dict]) -> list[dict]:
    """Quita lo que DEBE diferir y normaliza lo que es aleatorio POR DISEÑO.

    `query_log_id` es un `uuid4()` por fila: compararlo sería comparar el
    generador de UUIDs, no la conducta. Se NORMALIZA en vez de borrarse — así el
    gate sigue cazando que una ruta dejara de generarlo (presente/ausente sí es
    conducta; el valor no).
    """
    fuera = ("source", "transcription")
    return [{k: ("<uuid>" if k == "query_log_id" and v else v)
             for k, v in d.items() if k not in fuera}
            for d in logs]


@pytest.mark.parametrize("ruta,pregunta,registra", _TABLA_PARIDAD)
def test_paridad_voz_texto(monkeypatch, ruta, pregunta, registra):
    from src.bot import telegram_bot as bot

    t, _ = _correr(monkeypatch, bot, pregunta, canal="texto")
    v, _ = _correr(monkeypatch, bot, pregunta, canal="voz")

    assert _sin_burbuja_asr(v.mensajes, pregunta) == t.mensajes, (
        f"[{ruta}] la voz no emite los mismos mensajes que el texto")
    assert _comparables(v.logs) == _comparables(t.logs), (
        f"[{ruta}] las filas de query_logs difieren mas alla de source/transcription")
    assert len(v.rag) == len(t.rag), (
        f"[{ruta}] distinto numero de llamadas al RAG: voz={len(v.rag)} texto={len(t.rag)}")


@pytest.mark.parametrize("ruta,pregunta,registra", _TABLA_PROCEDENCIA)
def test_la_voz_declara_su_procedencia(monkeypatch, ruta, pregunta, registra):
    """Donde SÍ debe diferir, tiene que diferir.

    Sin esto, «paridad» se podría conseguir haciendo que la voz MIENTA y se
    registre como texto — que es el crítico que cazó el dúo r42.
    """
    from src.bot import telegram_bot as bot

    v, _ = _correr(monkeypatch, bot, pregunta, canal="voz")
    if registra:
        # ANTI-VACUIDAD: sin esta línea el test pasaba cuando la voz no escribía
        # NADA (el estado roto de hoy) y habría dado por bueno un cableado que
        # dejara los atajos sin alcanzar. Un bucle sobre lista vacía no prueba nada.
        assert v.logs, (
            f"[{ruta}] la voz no escribio NINGUNA fila: o no alcanza el atajo, "
            f"o el atajo dejo de registrar")
    for fila in v.logs:
        assert fila.get("source") == "voice", f"[{ruta}] fila de log SIN canal"
        assert fila.get("transcription") == pregunta, f"[{ruta}] fila sin ASR crudo"


def test_la_burbuja_asr_es_la_unica_diferencia_que_se_perdona(monkeypatch):
    """Guardarraíl del propio gate: `_sin_burbuja_asr` filtra la burbuja y NADA
    más. Si mañana la voz emitiera un mensaje extra, no puede taparlo."""
    assert _sin_burbuja_asr(["🎤 hola", "respuesta"], "hola") == ["respuesta"]
    assert _sin_burbuja_asr(["🎤 hola", "extra", "respuesta"], "hola") == [
        "extra", "respuesta"]


# ──────── NO-REGRESIÓN: la ruta conversacional es el destino mayoritario en voz

@pytest.mark.parametrize("pregunta", [
    "Cómo se conecta el lazo de la CAD-250",
    "Qué tensión pide la central",
])
def test_la_pregunta_tecnica_hablada_llega_al_rag_CON_su_procedencia(
        monkeypatch, pregunta):
    """El agujero que ninguna otra puerta veía (Sol y Opus 5, r44, por separado).

    `_ejecutar_plan` termina en `_process_query(update, context, query,
    preambulo=plan.preambulo)` — SIN `source` ni `transcription`. Hoy la voz no
    pasa por ahí: `handle_voice` llama a `_process_query` ella misma y sí los pasa.
    Cablear la voz al despachador sin reenviar la procedencia registraría TODA
    pregunta técnica hablada como texto y sin ASR crudo.

    Este test PASA HOY y debe seguir pasando: es el único del fichero que protege
    algo que ya funciona, y por eso es el que más vale.
    """
    from src.bot import telegram_bot as bot

    v, _ = _correr(monkeypatch, bot, pregunta, canal="voz")
    assert v.rag, "la pregunta tecnica hablada no llego al RAG"
    for llamada in v.rag:
        assert llamada.get("source") == "voice", (
            "la ruta conversacional perdio el canal: quedaria registrada como texto")
        assert llamada.get("transcription") == pregunta, (
            "la ruta conversacional perdio el ASR crudo")


def test_el_texto_no_se_contamina_de_procedencia_de_voz(monkeypatch):
    """Control del anterior: si alguien lo 'arreglara' fijando `source='voice'`,
    esto lo caza."""
    from src.bot import telegram_bot as bot

    t, _ = _correr(monkeypatch, bot, "Cómo se conecta el lazo de la CAD-250",
                   canal="texto")
    assert t.rag, "la pregunta tecnica tecleada no llego al RAG"
    for llamada in t.rag:
        assert llamada.get("source", "text") == "text"
        assert llamada.get("transcription") is None


# ─────────── B2: `es_reply` en voz — se afirma el ESTADO, no los mensajes

def _con_contexto(modelos: tuple[str, ...]) -> dict:
    from src.bot.telegram_bot import WorkingState
    return {"mt_working_state": WorkingState(last_target_models=list(modelos))}


#: Frase VERIFICADA con sonda: es la que dispara invalidación. Una mención suelta
#: («y de Notifier?») PRESERVA en los dos canales — la primera versión de este test
#: usaba esa y no discriminaba nada.
_CAMBIA_DE_MARCA = "qué centrales de Notifier tienes"


@_PENDIENTE
def test_b2_un_audio_en_reply_no_debe_invalidar_el_contexto(monkeypatch):
    """(Sol r44) B2 es una MUTACIÓN DE ESTADO, no de mensajes: invalidar o
    preservar puede dar exactamente la misma respuesta en ese turno, así que una
    tabla que sólo compare texto daría GO sin probar la garantía. Se afirma
    `mt_working_state` DESPUÉS del turno, que es donde vive la diferencia.

    Hoy falla: `handle_voice` construye `Meta(fuente="voz")` sin `es_reply`, así
    que un audio en reply invalida cuando el texto equivalente preserva.
    """
    from src.bot import telegram_bot as bot

    _, ud = _correr(monkeypatch, bot, _CAMBIA_DE_MARCA, canal="voz",
                    es_reply=True, user_data=_con_contexto(("CAD-250",)))
    assert bot._estado_modelos_conversacion(ud) == ("CAD-250",), (
        "un audio EN REPLY invalido el contexto de producto; el texto no lo hace")


def test_b2_control_un_audio_normal_SI_invalida(monkeypatch):
    """Control que impide 'arreglar' lo anterior desactivando la invalidación
    entera: un audio NORMAL que cambia de marca sí debe limpiar el contexto.
    PASA hoy y tiene que seguir pasando."""
    from src.bot import telegram_bot as bot

    _, ud = _correr(monkeypatch, bot, _CAMBIA_DE_MARCA, canal="voz",
                    es_reply=False, user_data=_con_contexto(("CAD-250",)))
    assert bot._estado_modelos_conversacion(ud) == (), (
        "un cambio de marca hablado debe invalidar el contexto de producto")
