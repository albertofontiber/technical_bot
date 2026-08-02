"""s294 · #60 punto 5 — follow-up del 👎 («¿qué falló?»).

Contrato que se fija aquí:
  · el motivo es un PATCH sobre el voto EXISTENTE, nunca un upsert: un motivo sin
    verdict no es interpretable, así que si no hay fila no se inventa.
  · clases CERRADAS (info/wrong/scope/other); cualquier otra se rechaza sin red.
  · el follow-up sale SOLO tras un 👎 REGISTRADO, solo con su flag propio ON, y
    solo si ese voto aún no tiene motivo (re-pulsar no vuelve a preguntar).
  · nunca tras 👍, nunca si el voto falló.
  · fail-open: si el follow-up revienta, la valoración ya guardada no se toca.
  · el callback del motivo entra por el MISMO handler (`^fb:`) y cabe en los 64
    bytes de Telegram.
"""

import asyncio
import types
import uuid
from unittest.mock import MagicMock

import pytest

import src.bot.telegram_bot as bot
import src.logging_db as logging_db
from src.logging_db import (
    FEEDBACK_REASON_CLASSES,
    has_feedback_reason,
    set_feedback_reason,
)


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
        self.calls.append(
            {"verb": "patch", "url": url, "headers": headers, "params": params,
             "json": json}
        )
        return _FakeResponse(self.status_code, self.payload)

    def get(self, url, headers=None, params=None):
        if self.raise_on_call:
            raise ConnectionError("boom")
        self.calls.append({"verb": "get", "url": url, "params": params})
        return _FakeResponse(self.status_code, self.payload)


# ---------------------------------------------------------------- logging_db


def test_set_reason_es_patch_sobre_el_voto_existente(monkeypatch):
    fake = _FakeClient(status_code=200, payload=[{"id": "x"}])
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    row_id = str(uuid.uuid4())

    assert set_feedback_reason(row_id, 42, "wrong") is True

    call = fake.calls[0]
    assert call["verb"] == "patch"          # NO es upsert: no se crea voto nuevo
    assert call["url"].endswith("/rest/v1/answer_feedback")
    assert call["params"]["query_log_id"] == f"eq.{row_id}"
    assert call["params"]["telegram_user_id"] == "eq.42"
    assert call["json"] == {"reason_class": "wrong"}
    # representation: 204 con filtro que no casa es indistinguible de escritura.
    assert "return=representation" in call["headers"]["Prefer"]


def test_set_reason_false_si_no_habia_voto(monkeypatch):
    """Filtro sin coincidencias ⇒ respuesta vacía ⇒ False (no se inventa fila)."""
    monkeypatch.setattr(
        logging_db.httpx, "Client", _FakeClient(status_code=200, payload=[])
    )
    assert set_feedback_reason(str(uuid.uuid4()), 42, "info") is False


def test_set_reason_rechaza_clase_fuera_de_la_lista(monkeypatch):
    fake = _FakeClient(status_code=200, payload=[{"id": "x"}])
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert set_feedback_reason(str(uuid.uuid4()), 42, "sql-injection") is False
    assert fake.calls == []                 # ni siquiera sale a la red


def test_clases_cerradas_espejan_el_check_del_esquema():
    assert FEEDBACK_REASON_CLASSES == ("info", "wrong", "scope", "other")


@pytest.mark.parametrize("kwargs", [{"status_code": 500}, {"raise_on_call": True}])
def test_set_reason_fail_open(monkeypatch, kwargs):
    monkeypatch.setattr(logging_db.httpx, "Client", _FakeClient(**kwargs))
    assert set_feedback_reason(str(uuid.uuid4()), 1, "info") is False


def test_has_reason_true_y_filtro(monkeypatch):
    fake = _FakeClient(status_code=200, payload=[{"id": "x"}])
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    row_id = str(uuid.uuid4())
    assert has_feedback_reason(row_id, 42) is True
    assert fake.calls[0]["params"]["reason_class"] == "not.is.null"


@pytest.mark.parametrize(
    "kwargs, esperado",
    [({"status_code": 200, "payload": []}, False),
     ({"status_code": 500}, False),
     ({"raise_on_call": True}, False)],
)
def test_has_reason_false(monkeypatch, kwargs, esperado):
    monkeypatch.setattr(logging_db.httpx, "Client", _FakeClient(**kwargs))
    assert has_feedback_reason(str(uuid.uuid4()), 1) is esperado


# ------------------------------------------------------------- telegram_bot


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("TELEGRAM_FEEDBACK_REASON", raising=False)
    assert bot._feedback_reason_enabled() is False
    monkeypatch.setenv("TELEGRAM_FEEDBACK_REASON", "on")
    assert bot._feedback_reason_enabled() is True


def test_callback_data_cabe_en_telegram_y_entra_por_el_mismo_handler():
    row_id = str(uuid.uuid4())
    markup = bot._feedback_reason_keyboard(row_id)
    datas = [b.callback_data for row in markup.inline_keyboard for b in row]
    # s294 punto 5b: «Otra cosa» sale del teclado (en la prueba real de Alberto era
    # la única que encajaba y no informaba de nada) y su hueco lo ocupa la ACCIÓN de
    # explicar. La clase `other` sigue siendo válida en el CHECK de la DB.
    assert datas == [
        f"fb:r:info:{row_id}", f"fb:r:wrong:{row_id}",
        f"fb:r:scope:{row_id}", f"fb:x:{row_id}",
    ]
    for data in datas:
        assert len(data.encode()) <= 64
        # el handler se registra con `^fb:` — todo el teclado DEBE entrar por ahí
        assert data.startswith("fb:")
        # cada botón casa con SU patrón (motivo o acción de explicar)…
        assert (
            bot._FEEDBACK_REASON_PATTERN.match(data)
            or bot._FEEDBACK_EXPLAIN_PATTERN.match(data)
        )
        # …y ninguno puede confundirse con un voto
        assert bot._FEEDBACK_CALLBACK_PATTERN.match(data) is None


def test_patron_de_motivo_estricto():
    row_id = str(uuid.uuid4())
    assert bot._FEEDBACK_REASON_PATTERN.match(f"fb:r:info:{row_id}")
    assert not bot._FEEDBACK_REASON_PATTERN.match(f"fb:r:otra:{row_id}")
    assert not bot._FEEDBACK_REASON_PATTERN.match("fb:r:info:no-es-uuid")
    assert not bot._FEEDBACK_REASON_PATTERN.match(f"FB:r:info:{row_id}")


def _callback_update(data: str, user_id: int = 7):
    callback = MagicMock()
    callback.data = data
    callback.from_user = types.SimpleNamespace(id=user_id)
    callback.answer = _AsyncRecorder()
    callback.edit_message_reply_markup = _AsyncRecorder()
    callback.message = types.SimpleNamespace(reply_text=_AsyncRecorder())
    update = MagicMock()
    update.callback_query = callback
    return update, callback


class _AsyncRecorder:
    def __init__(self, raise_exc=None):
        self.calls: list[dict] = []
        self._raise = raise_exc

    async def __call__(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        if self._raise is not None:
            raise self._raise


def _wire(monkeypatch, *, verdict_ok=True, ya_tiene_motivo=False, reason_ok=True):
    monkeypatch.setattr(bot, "has_consent", lambda _u: True)
    monkeypatch.setattr(bot, "log_answer_feedback", lambda **_k: verdict_ok)
    monkeypatch.setattr(bot, "has_feedback_reason", lambda *_a: ya_tiene_motivo)
    monkeypatch.setattr(bot, "set_feedback_reason", lambda **_k: reason_ok)
    monkeypatch.setenv("TELEGRAM_FEEDBACK_REASON", "on")


def test_pulgar_abajo_lanza_el_followup(monkeypatch):
    _wire(monkeypatch)
    update, callback = _callback_update(f"fb:d:{uuid.uuid4()}")
    asyncio.run(bot.feedback_callback(update, None))

    assert len(callback.message.reply_text.calls) == 1
    enviado = callback.message.reply_text.calls[0]
    assert enviado["args"][0] == bot._FEEDBACK_REASON_PROMPT
    assert enviado["kwargs"]["reply_markup"] is not None


def test_pulgar_arriba_no_lanza_followup(monkeypatch):
    _wire(monkeypatch)
    update, callback = _callback_update(f"fb:u:{uuid.uuid4()}")
    asyncio.run(bot.feedback_callback(update, None))
    assert callback.message.reply_text.calls == []


def test_sin_flag_no_hay_followup(monkeypatch):
    _wire(monkeypatch)
    monkeypatch.setenv("TELEGRAM_FEEDBACK_REASON", "off")
    update, callback = _callback_update(f"fb:d:{uuid.uuid4()}")
    asyncio.run(bot.feedback_callback(update, None))
    assert callback.message.reply_text.calls == []


def test_voto_fallido_no_lanza_followup(monkeypatch):
    """Sin voto registrado no hay nada que cualificar."""
    _wire(monkeypatch, verdict_ok=False)
    update, callback = _callback_update(f"fb:d:{uuid.uuid4()}")
    asyncio.run(bot.feedback_callback(update, None))
    assert callback.message.reply_text.calls == []


def test_no_repregunta_si_ya_hay_motivo(monkeypatch):
    _wire(monkeypatch, ya_tiene_motivo=True)
    update, callback = _callback_update(f"fb:d:{uuid.uuid4()}")
    asyncio.run(bot.feedback_callback(update, None))
    assert callback.message.reply_text.calls == []


def test_followup_roto_no_tumba_la_valoracion(monkeypatch):
    """La valoración ya está guardada: el follow-up jamás puede ponerla en riesgo."""
    _wire(monkeypatch)
    update, callback = _callback_update(f"fb:d:{uuid.uuid4()}")
    callback.message.reply_text = _AsyncRecorder(raise_exc=RuntimeError("telegram caido"))
    asyncio.run(bot.feedback_callback(update, None))          # no propaga
    assert callback.answer.calls[0]["args"][0] == "¡Gracias por tu valoración!"


def test_tap_de_motivo_anota_y_retira_el_teclado(monkeypatch):
    _wire(monkeypatch)
    anotado: list = []
    monkeypatch.setattr(
        bot, "set_feedback_reason",
        lambda **kw: anotado.append(kw) or True,
    )
    row_id = str(uuid.uuid4())
    update, callback = _callback_update(f"fb:r:scope:{row_id}")
    asyncio.run(bot.feedback_callback(update, None))

    assert anotado == [
        {"query_log_id": row_id, "telegram_user_id": 7, "reason_class": "scope"}
    ]
    assert len(callback.edit_message_reply_markup.calls) == 1
    assert callback.answer.calls[0]["args"][0].startswith("Gracias")


def test_tap_de_motivo_sin_voto_no_retira_teclado(monkeypatch):
    _wire(monkeypatch, reason_ok=False)
    update, callback = _callback_update(f"fb:r:info:{uuid.uuid4()}")
    asyncio.run(bot.feedback_callback(update, None))
    assert callback.edit_message_reply_markup.calls == []
    assert "No se pudo" in callback.answer.calls[0]["args"][0]


def test_sin_consentimiento_ni_vota_ni_cualifica(monkeypatch):
    _wire(monkeypatch)
    monkeypatch.setattr(bot, "has_consent", lambda _u: False)
    anotado: list = []
    monkeypatch.setattr(bot, "set_feedback_reason", lambda **kw: anotado.append(kw))
    update, callback = _callback_update(f"fb:r:info:{uuid.uuid4()}")
    asyncio.run(bot.feedback_callback(update, None))
    assert anotado == []
    assert "acepta primero los términos" in callback.answer.calls[0]["args"][0]
