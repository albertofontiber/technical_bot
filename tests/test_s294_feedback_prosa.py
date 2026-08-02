"""s294 · #60 punto 5b — la prosa del 👎, con intención explícita.

Contrato que se fija aquí (dúo r1: Sol 6 hallazgos + sub-agente 11, NO-SÓLIDA):

  · **La ambigüedad se resuelve por DISEÑO, no por heurística.** El aviso de
    Alberto —«el técnico puede pasar del feedback y hacer otra pregunta»— se
    atiende con `ForceReply`: la explicación llega como REPLY al mensaje del bot.
    Un mensaje suelto NUNCA se captura: sigue su curso y el bot lo responde.
  · La prosa va a `answer_feedback.comment` — la columna que s286/DEC-162f
    reservó («escribirá `answer_feedback.comment`, NO `feedback`»). Cero esquema
    nuevo. (El diseño v1 proponía una FK sobre `feedback`: lo tumbó el dúo por
    contradecir ese settled sin citarlo.)
  · El mensaje de invitación se ESTAMPA en `answer_messages` — sin eso la vía de
    reply queda desabastecida (hallazgo F5) y el reply no resolvería.
  · Binding EXACTO y sin estado en memoria (sobrevive a redeploy de Railway).
  · Fail-open total: una pregunta del técnico jamás se traga por telemetría.
"""

import asyncio
import types
import uuid
from unittest.mock import MagicMock

import pytest

import src.bot.telegram_bot as bot
import src.logging_db as logging_db
from src.logging_db import TERMS_VERSION, set_feedback_comment


class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else []

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, status_code=200, payload=None, raise_on_call=False):
        self.status_code = status_code
        self.payload = payload
        self.raise_on_call = raise_on_call
        self.calls: list[dict] = []

    def __call__(self, *a, **k):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def patch(self, url, headers=None, params=None, json=None):
        if self.raise_on_call:
            raise ConnectionError("boom")
        self.calls.append({"url": url, "params": params, "json": json,
                           "headers": headers})
        return _FakeResponse(self.status_code, self.payload)


# ---------------------------------------------------------------- logging_db


def test_comment_es_patch_sobre_el_voto(monkeypatch):
    fake = _FakeClient(status_code=200, payload=[{"id": "x"}])
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    row_id = str(uuid.uuid4())

    assert set_feedback_comment(row_id, 42, "  la ruta de menú está mal  ") is True

    call = fake.calls[0]
    assert call["url"].endswith("/rest/v1/answer_feedback")   # NO la tabla legacy
    assert call["params"]["query_log_id"] == f"eq.{row_id}"
    assert call["json"] == {"comment": "la ruta de menú está mal"}
    assert "return=representation" in call["headers"]["Prefer"]


def test_comment_vacio_no_sale_a_la_red(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert set_feedback_comment(str(uuid.uuid4()), 1, "   ") is False
    assert fake.calls == []


def test_comment_se_recorta(monkeypatch):
    fake = _FakeClient(status_code=200, payload=[{"id": "x"}])
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    set_feedback_comment(str(uuid.uuid4()), 1, "x" * 5000, max_chars=100)
    assert len(fake.calls[0]["json"]["comment"]) == 100


def test_comment_false_si_no_habia_voto(monkeypatch):
    monkeypatch.setattr(
        logging_db.httpx, "Client", _FakeClient(status_code=200, payload=[])
    )
    assert set_feedback_comment(str(uuid.uuid4()), 1, "texto") is False


@pytest.mark.parametrize("kwargs", [{"status_code": 500}, {"raise_on_call": True}])
def test_comment_fail_open(monkeypatch, kwargs):
    monkeypatch.setattr(logging_db.httpx, "Client", _FakeClient(**kwargs))
    assert set_feedback_comment(str(uuid.uuid4()), 1, "texto") is False


def test_terms_version_subida_por_pedir_prosa():
    """Pedir un dato nuevo obliga a re-aceptar (precedente s286: v1→v2)."""
    assert TERMS_VERSION == "v3"
    assert "explicación que escribas" in bot._CONSENT_TERMS


# ------------------------------------------------------------- telegram_bot


class _AsyncRecorder:
    def __init__(self, result=None, raise_exc=None):
        self.calls: list[dict] = []
        self._result = result
        self._raise = raise_exc

    async def __call__(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        if self._raise is not None:
            raise self._raise
        return self._result


def test_boton_explicar_en_el_teclado():
    row_id = str(uuid.uuid4())
    markup = bot._feedback_reason_keyboard(row_id)
    datas = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert f"fb:x:{row_id}" in datas                    # la ACCIÓN de explicar
    assert not any(d.startswith("fb:r:other:") for d in datas)   # «Otra cosa» fuera
    for data in datas:
        assert len(data.encode()) <= 64
        assert data.startswith("fb:")                  # mismo handler


def test_prompt_reusa_el_acuse_de_texto_libre():
    """Alberto: el técnico debe ver el MISMO acuse venga por donde venga."""
    assert bot._FEEDBACK_REASON_PROMPT.startswith("Gracias por el aviso 🙏")
    assert "qué dato concreto" in bot._FEEDBACK_REASON_PROMPT


def _callback_update(data: str, user_id: int = 7, sent=None):
    callback = MagicMock()
    callback.data = data
    callback.from_user = types.SimpleNamespace(id=user_id)
    callback.answer = _AsyncRecorder()
    callback.edit_message_reply_markup = _AsyncRecorder()
    callback.message = types.SimpleNamespace(reply_text=_AsyncRecorder(result=sent))
    update = MagicMock()
    update.callback_query = callback
    return update, callback


def test_explicar_abre_forcereply_y_ESTAMPA_el_mensaje(monkeypatch):
    """Sin estampar la invitación, el reply no resolvería (hallazgo F5 del dúo)."""
    monkeypatch.setattr(bot, "has_consent", lambda _u: True)
    estampado: list = []
    monkeypatch.setattr(
        bot, "stamp_answer_messages",
        lambda *args: estampado.append(args) or True,
    )
    enviado = types.SimpleNamespace(
        message_id=777, chat=types.SimpleNamespace(id=-100555)
    )
    row_id = str(uuid.uuid4())
    update, callback = _callback_update(f"fb:x:{row_id}", sent=enviado)

    asyncio.run(bot.feedback_callback(update, None))

    kwargs = callback.message.reply_text.calls[0]["kwargs"]
    assert isinstance(kwargs["reply_markup"], bot.ForceReply)
    assert estampado == [(row_id, -100555, [777])]


def test_explicar_no_rompe_si_el_transporte_falla(monkeypatch):
    monkeypatch.setattr(bot, "has_consent", lambda _u: True)
    monkeypatch.setattr(bot, "stamp_answer_messages", lambda *a: True)
    update, callback = _callback_update(f"fb:x:{uuid.uuid4()}")
    callback.message.reply_text = _AsyncRecorder(raise_exc=RuntimeError("caido"))
    asyncio.run(bot.feedback_callback(update, None))     # no propaga
    assert callback.answer.calls                          # el spinner se resuelve


# ---- captura del reply -----------------------------------------------------


class _IncomingMessage:
    def __init__(self, text, reply_to=None):
        self.text = text
        self.reply_to_message = reply_to
        self.reply_text = _AsyncRecorder()


def _message_update(text, *, reply_to=None, user_id=7):
    update = MagicMock()
    update.message = _IncomingMessage(text, reply_to)
    update.effective_user = types.SimpleNamespace(id=user_id)
    return update


def _bot_message(message_id=777, chat_id=-100555):
    return types.SimpleNamespace(
        message_id=message_id, chat=types.SimpleNamespace(id=chat_id)
    )


def test_reply_anclado_se_captura_y_no_va_al_rag(monkeypatch):
    row_id = str(uuid.uuid4())
    monkeypatch.setattr(bot, "query_log_id_for_message", lambda c, m: row_id)
    guardado: list = []
    monkeypatch.setattr(
        bot, "set_feedback_comment",
        lambda *args: guardado.append(args) or True,
    )
    update = _message_update("la ruta de menú está mal anidada",
                             reply_to=_bot_message())

    capturado = asyncio.run(
        bot._capture_reply_explanation(update, 7, "la ruta de menú está mal anidada")
    )

    assert capturado is True
    assert guardado == [(row_id, 7, "la ruta de menú está mal anidada")]
    assert update.message.reply_text.calls[0]["args"][0] == bot._FEEDBACK_EXPLAIN_ACK


def test_mensaje_suelto_NO_se_captura(monkeypatch):
    """El aviso de Alberto: si pasa del feedback y pregunta, el bot RESPONDE."""
    monkeypatch.setattr(bot, "query_log_id_for_message", lambda c, m: "no-deberia")
    update = _message_update("¿cuál es el rango de temperatura del ASD535?")
    assert asyncio.run(bot._capture_reply_explanation(update, 7, "…")) is False


def test_reply_a_mensaje_NO_anclado_no_se_captura(monkeypatch):
    """Reply presente pero irresoluble ⇒ NO se degrada a «última consulta»."""
    monkeypatch.setattr(bot, "query_log_id_for_message", lambda c, m: None)
    llamado: list = []
    monkeypatch.setattr(bot, "set_feedback_comment", lambda *a: llamado.append(a))
    update = _message_update("texto", reply_to=_bot_message())
    assert asyncio.run(bot._capture_reply_explanation(update, 7, "texto")) is False
    assert llamado == []


def test_si_no_hay_voto_previo_no_se_traga_el_mensaje(monkeypatch):
    """PATCH sin fila ⇒ False ⇒ el mensaje sigue su curso normal."""
    monkeypatch.setattr(bot, "query_log_id_for_message", lambda c, m: str(uuid.uuid4()))
    monkeypatch.setattr(bot, "set_feedback_comment", lambda *a: False)
    update = _message_update("texto", reply_to=_bot_message())
    assert asyncio.run(bot._capture_reply_explanation(update, 7, "texto")) is False


def test_captura_fail_open(monkeypatch):
    """Un fallo de telemetría NUNCA puede tragarse una pregunta del técnico."""
    def boom(*_a):
        raise ConnectionError("supabase caido")
    monkeypatch.setattr(bot, "query_log_id_for_message", boom)
    update = _message_update("texto", reply_to=_bot_message())
    assert asyncio.run(bot._capture_reply_explanation(update, 7, "texto")) is False
