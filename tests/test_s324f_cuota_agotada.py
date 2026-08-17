# -*- coding: utf-8 -*-
"""s324f — Un 429 por CUOTA no es un 429 por congestión.

Nace de un fallo observado en el piloto, no de una hipótesis: la primera usuaria
invitada mandó un audio, la cuenta de OpenAI de producción no tenía saldo, y el
bot le respondió que estaba **saturado** y que probara más tarde. Dos cosas
falsas en una frase: no había saturación, y reintentar nunca iba a funcionar.
Encima, la única vía por la que eso llegó al responsable fue que ella lo contara.

Se usan los SDK REALES —no dobles— por el mismo motivo que el resto de la suite
de taxonomía: si `openai` renombra o reestructura sus errores, esto tiene que
caer aquí y no en producción.
"""
from __future__ import annotations

import httpx
import openai
import pytest

from src.bot import error_taxonomy as tax


def _respuesta(status: int) -> httpx.Response:
    return httpx.Response(
        status, request=httpx.Request("POST", "https://api.openai.com/v1/audio")
    )


def _rate_limit(mensaje: str) -> Exception:
    return openai.RateLimitError(mensaje, response=_respuesta(429), body=None)


# El mensaje EXACTO que devolvió OpenAI en el incidente (recortado), con su
# `type` y su texto. Si algún día se toca el detector, este es el caso que no
# puede volver a fallar.
_REAL = (
    "Error code: 429 - {'error': {'message': 'You have no credits remaining. "
    "Add credits to continue using the API at https://platform.openai.com/"
    "settings/organization/billing', 'type': 'insufficient_quota', "
    "'param': None, 'code': 'insufficient_quota'}}"
)


def test_el_caso_real_del_piloto_ya_no_dice_saturado():
    d = tax.clasificar(_rate_limit(_REAL))
    assert d.reintentable is False, "no puede invitar a reintentar algo que falla siempre"
    assert d.severidad == "critico"
    texto = d.mensaje.lower()
    assert "satur" not in texto
    assert "unos minutos" not in texto and "más tarde" not in texto
    # y dice de quién es el problema, sin culpar a quien pregunta
    assert "cosa nuestra" in texto or "de la cuenta" in texto


@pytest.mark.parametrize("cuerpo", [
    "Error code: 429 - insufficient_quota",
    "You have no credits remaining",
    "You exceeded your current quota, please check your plan and billing details",
    "Your credit balance is too low to access the Anthropic API",
])
def test_variantes_de_los_dos_proveedores(cuerpo):
    assert tax.clasificar(_rate_limit(cuerpo)).reintentable is False, cuerpo


@pytest.mark.parametrize("cuerpo", [
    "Rate limit reached for gpt-4o in organization org-x on requests per min",
    "Number of request tokens has exceeded your per-minute rate limit",
    "429 Too Many Requests",
])
def test_la_saturacion_de_verdad_sigue_siendo_reintentable(cuerpo):
    """El control que impide arreglar de más: una congestión real SÍ se arregla
    esperando, y ahí el mensaje de siempre es el correcto."""
    d = tax.clasificar(_rate_limit(cuerpo))
    assert d.clase == tax.LLM_SATURADO
    assert d.reintentable is True


def test_la_clase_cabe_en_el_check_de_la_base():
    """`bot_errors.clase` tiene un CHECK cerrado con SEIS valores (migración
    015). Una clase nueva exigiría migración aplicada a mano; por eso la cuota va
    como `llm_fallo`, que además es correcto: es determinista. Si alguien la
    cambia a un valor nuevo sin migrar, el INSERT fallaría EN PRODUCCIÓN y el
    diagnóstico se perdería justo cuando más falta hace."""
    d = tax.clasificar(_rate_limit(_REAL))
    assert d.clase in tax.CLASES
    assert d.clase == tax.LLM_FALLO


def test_la_degradacion_si_el_proveedor_cambia_el_texto():
    """Si mañana OpenAI escribe «out of funds», el detector no lo reconoce y
    volvemos a la conducta de hoy. Se pierde la mejora, no se rompe nada — y
    este test lo deja escrito para que nadie lo descubra a base de sustos."""
    d = tax.clasificar(_rate_limit("Error 429: out of funds, top up"))
    assert d.clase == tax.LLM_SATURADO
    assert d.reintentable is True


def test_un_texto_que_explota_no_tumba_la_clasificacion():
    """`_es_cuota_agotada` mira el texto de la excepción. Si ese `str()` revienta
    —un SDK con `__str__` roto— la clasificación no puede caerse con él."""
    class _Raro(Exception):
        __module__ = "openai"
        status_code = 429

        def __str__(self):
            raise RuntimeError("este __str__ explota")

    d = tax.clasificar(_Raro())
    assert d.clase == tax.LLM_SATURADO      # degrada, no revienta


# ─────────────────────────── el aviso a quien puede arreglarlo

def _incidencia(clase="llm_fallo", etapa="handle_voice", severidad="critico"):
    return tax.Incidencia(
        codigo="abc123", clase=clase, severidad=severidad, reintentable=False,
        tipo_excepcion="RateLimitError", etapa=etapa,
        origen="src/bot/telegram_bot.py:1219",
        mensaje_corto="Error code: 429 - insufficient_quota",
    )


class _Bot:
    def __init__(self):
        self.enviados = []

    async def send_message(self, chat_id, text):
        self.enviados.append((chat_id, text))


class _Ctx:
    def __init__(self, bot):
        self.bot = bot


def test_el_critico_avisa_al_operador(monkeypatch):
    """El agujero que esto cierra: en el piloto, la única vía por la que un fallo
    que sólo el operador puede arreglar llegó hasta él fue que la usuaria se lo
    contara."""
    import asyncio

    from src.bot import telegram_bot as tb

    monkeypatch.setattr(tb.access, "ids_bootstrap", lambda: frozenset({7642341119}))
    monkeypatch.setattr(tb, "_ULTIMO_AVISO_CRITICO", {})
    bot = _Bot()
    asyncio.run(tb._avisar_al_operador(_Ctx(bot), _incidencia()))
    assert len(bot.enviados) == 1
    destino, texto = bot.enviados[0]
    assert destino == 7642341119
    assert "CRÍTICA" in texto and "insufficient_quota" in texto
    assert "abc123" in texto                      # el código, para poder buscarlo


def test_el_aviso_no_lleva_ni_la_consulta_ni_a_quien_pregunto(monkeypatch):
    """El operador necesita saber QUÉ está roto, no quién tropezó. Eso ya vive en
    `bot_errors`/`query_logs` con su gobernanza de retención."""
    import asyncio

    from src.bot import telegram_bot as tb

    monkeypatch.setattr(tb.access, "ids_bootstrap", lambda: frozenset({7642341119}))
    monkeypatch.setattr(tb, "_ULTIMO_AVISO_CRITICO", {})
    bot = _Bot()
    asyncio.run(tb._avisar_al_operador(_Ctx(bot), _incidencia()))
    texto = bot.enviados[0][1]
    # la incidencia NO transporta ni el texto ni el autor, así que el aviso
    # tampoco puede: este test lo deja anclado
    assert "telegram_user_id" not in texto.lower()
    assert "consulta" not in texto.lower()


def test_no_inunda_repitiendo_la_misma_incidencia(monkeypatch):
    """Sin cota, un fallo de cuota manda un Telegram POR TURNO hasta que alguien
    pague — y el operador deja de mirarlos, que es perder el aviso."""
    import asyncio

    from src.bot import telegram_bot as tb

    monkeypatch.setattr(tb.access, "ids_bootstrap", lambda: frozenset({7642341119}))
    monkeypatch.setattr(tb, "_ULTIMO_AVISO_CRITICO", {})
    bot = _Bot()
    for _ in range(5):
        asyncio.run(tb._avisar_al_operador(_Ctx(bot), _incidencia()))
    assert len(bot.enviados) == 1, "el segundo y siguientes debían quedarse callados"


def test_una_incidencia_DISTINTA_si_avisa(monkeypatch):
    """La cota es por clase+etapa, no global: un problema nuevo mientras dura
    otro no puede quedarse mudo."""
    import asyncio

    from src.bot import telegram_bot as tb

    monkeypatch.setattr(tb.access, "ids_bootstrap", lambda: frozenset({7642341119}))
    monkeypatch.setattr(tb, "_ULTIMO_AVISO_CRITICO", {})
    bot = _Bot()
    asyncio.run(tb._avisar_al_operador(_Ctx(bot), _incidencia(etapa="handle_voice")))
    asyncio.run(tb._avisar_al_operador(_Ctx(bot), _incidencia(etapa="process_query")))
    assert len(bot.enviados) == 2


def test_sin_operador_configurado_no_falla(monkeypatch):
    """`BOT_ALLOWLIST_BOOTSTRAP` vacío: no hay a quién avisar, y eso no puede
    convertirse en un segundo error encima del primero."""
    import asyncio

    from src.bot import telegram_bot as tb

    monkeypatch.setattr(tb.access, "ids_bootstrap", frozenset)
    monkeypatch.setattr(tb, "_ULTIMO_AVISO_CRITICO", {})
    asyncio.run(tb._avisar_al_operador(_Ctx(_Bot()), _incidencia()))


def test_si_el_envio_falla_no_recursa(monkeypatch):
    """Un aviso que falla no puede disparar otro aviso: sería un bucle sobre el
    propio manejador de errores."""
    import asyncio

    from src.bot import telegram_bot as tb

    class _BotRoto:
        async def send_message(self, chat_id, text):
            raise RuntimeError("telegram caido")

    monkeypatch.setattr(tb.access, "ids_bootstrap", lambda: frozenset({1}))
    monkeypatch.setattr(tb, "_ULTIMO_AVISO_CRITICO", {})
    asyncio.run(tb._avisar_al_operador(_Ctx(_BotRoto()), _incidencia()))


def test_una_congestion_real_con_enlace_de_facturacion_no_se_confunde():
    """(dúo r40, Fable) El falso POSITIVO es el que cuesta caro: le diría al
    técnico «reintentar no va a servir» ante algo que se arregla esperando, y
    mandaría un aviso crítico falso al operador. Por eso se descartó la señal
    `"billing"`, que parecía cubrir a los dos proveedores pero aparece en los
    enlaces de ayuda de un 429 de ritmo perfectamente normal."""
    d = tax.clasificar(_rate_limit(
        "Rate limit reached for gpt-4o. Please try again in 20s. "
        "See https://platform.openai.com/account/billing for your limits."
    ))
    assert d.clase == tax.LLM_SATURADO
    assert d.reintentable is True
