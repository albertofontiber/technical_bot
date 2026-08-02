"""s294 · #60 punto 1 — ancla `message_id → query_log_id`.

Contrato que se fija aquí:
  · `stamp_answer_messages`: upsert con `on_conflict` explícito sobre el UNIQUE
    (chat, message) — no la PK; estampa TODAS las partes con su `part_index`.
  · fail-open TOTAL: error HTTP o excepción devuelven False sin propagar; lista
    vacía no llama a la red.
  · `query_log_id_for_message`: búsqueda inversa; None cuando no hay ancla
    (mensaje ajeno, respuesta pre-telemetría, o fila borrada por retención RGPD
    — la cascada se lleva el ancla).
  · cableado del bot: se estampa SOLO si la fila de query_logs está KNOWN
    committed (mismo criterio que el teclado: una FK colgante no aporta señal),
    y el envío de la respuesta jamás depende del ancla.
  · guardas de esquema: `answer_messages` en AMBOS arrays del boundary de datos
    personales + GRANT SELECT,INSERT + CASCADE + UNIQUE, y la migración espeja
    ese endurecimiento.
"""

import asyncio
import re
import types
import uuid
from pathlib import Path

import pytest

import src.bot.telegram_bot as bot
import src.logging_db as logging_db
from src.logging_db import query_log_id_for_message, stamp_answer_messages

REPO = Path(__file__).parent.parent


class _FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else []

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, status_code: int = 201, payload=None, raise_on_call=False):
        self.status_code = status_code
        self.payload = payload
        self.raise_on_call = raise_on_call
        self.calls: list[dict] = []

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, headers=None, json=None, params=None):
        if self.raise_on_call:
            raise ConnectionError("boom")
        self.calls.append(
            {"verb": "post", "url": url, "headers": headers, "json": json,
             "params": params}
        )
        return _FakeResponse(self.status_code, self.payload)

    def get(self, url, headers=None, params=None):
        if self.raise_on_call:
            raise ConnectionError("boom")
        self.calls.append({"verb": "get", "url": url, "params": params})
        return _FakeResponse(self.status_code, self.payload)


# --------------------------------------------------------------- logging_db


def test_stamp_contract_upsert_y_part_index(monkeypatch):
    fake = _FakeClient(status_code=201)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    row_id = str(uuid.uuid4())

    assert stamp_answer_messages(row_id, -100123, [11, 12, 13]) is True

    call = fake.calls[0]
    assert call["url"].endswith("/rest/v1/answer_messages")
    assert call["params"] == {
        "on_conflict": "telegram_chat_id,telegram_message_id"
    }
    # CONTRATO DE PRIVILEGIO (cazado en smoke contra la DB real): el ancla es de
    # ESCRITURA ÚNICA y la tabla solo tiene GRANT SELECT+INSERT. `merge-duplicates`
    # es un UPSERT y PostgREST exige UPDATE ⇒ devolvía 403 y, por el fail-open, el
    # ancla NUNCA se habría estampado sin que nada fallara a la vista.
    # `ignore-duplicates` (ON CONFLICT DO NOTHING) da la idempotencia sin UPDATE.
    assert "resolution=ignore-duplicates" in call["headers"]["Prefer"]
    assert "merge-duplicates" not in call["headers"]["Prefer"]
    assert call["json"] == [
        {"query_log_id": row_id, "telegram_chat_id": -100123,
         "telegram_message_id": 11, "part_index": 0},
        {"query_log_id": row_id, "telegram_chat_id": -100123,
         "telegram_message_id": 12, "part_index": 1},
        {"query_log_id": row_id, "telegram_chat_id": -100123,
         "telegram_message_id": 13, "part_index": 2},
    ]


def test_stamp_sin_mensajes_no_llama_a_la_red(monkeypatch):
    fake = _FakeClient(status_code=201)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert stamp_answer_messages(str(uuid.uuid4()), 1, []) is False
    assert fake.calls == []


@pytest.mark.parametrize(
    "kwargs", [{"status_code": 500}, {"raise_on_call": True}]
)
def test_stamp_fail_open(monkeypatch, kwargs):
    monkeypatch.setattr(logging_db.httpx, "Client", _FakeClient(**kwargs))
    assert stamp_answer_messages(str(uuid.uuid4()), 1, [5]) is False


def test_lookup_devuelve_el_query_log_id(monkeypatch):
    row_id = str(uuid.uuid4())
    fake = _FakeClient(status_code=200, payload=[{"query_log_id": row_id}])
    monkeypatch.setattr(logging_db.httpx, "Client", fake)

    assert query_log_id_for_message(-100123, 11) == row_id
    assert fake.calls[0]["params"] == {
        "telegram_chat_id": "eq.-100123",
        "telegram_message_id": "eq.11",
        "select": "query_log_id",
        "limit": "1",
    }


def test_lookup_none_sin_ancla(monkeypatch):
    monkeypatch.setattr(
        logging_db.httpx, "Client", _FakeClient(status_code=200, payload=[])
    )
    assert query_log_id_for_message(1, 2) is None


@pytest.mark.parametrize(
    "kwargs", [{"status_code": 500}, {"raise_on_call": True}]
)
def test_lookup_fail_open(monkeypatch, kwargs):
    monkeypatch.setattr(logging_db.httpx, "Client", _FakeClient(**kwargs))
    assert query_log_id_for_message(1, 2) is None


# ------------------------------------------------------------- telegram_bot


class _Message:
    """Doble del transporte: `reply_text` devuelve un Message con id, como Telegram."""

    def __init__(self, start_id: int = 100):
        self.replies: list[str] = []
        self._next_id = start_id

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)
        sent = types.SimpleNamespace(message_id=self._next_id)
        self._next_id += 1
        return sent


class _MessageSinId(_Message):
    """Transporte que NO devuelve Message (librería antigua / doble de test)."""

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)
        return None


class _Update:
    def __init__(self, message):
        self.message = message
        self.effective_user = types.SimpleNamespace(id=7)
        self.effective_chat = types.SimpleNamespace(id=-100123)


def _run(monkeypatch, update, *, query_logged: bool, stamped: list):
    served = [{"id": "served", "content": "evidencia", "similarity": 1.0}]
    monkeypatch.setattr(bot, "extract_product_models", lambda _q: ["CAD-250"])
    monkeypatch.setattr(bot, "retrieve_chunks", lambda *a, **k: served)
    monkeypatch.setattr(bot, "rerank", lambda *a, **k: served)
    monkeypatch.setattr(
        bot, "generate_answer",
        lambda *a, **k: {"answer": "respuesta", "diagrams": []},
    )
    monkeypatch.setattr(bot, "log_query", lambda **_k: query_logged)
    monkeypatch.setattr(
        bot, "stamp_answer_messages",
        lambda *args: stamped.append(args) or True,
    )
    context = types.SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "¿Conexionado CAD-250?"))


def test_bot_estampa_el_ancla_cuando_el_log_esta_committed(monkeypatch):
    stamped: list = []
    update = _Update(_Message())
    _run(monkeypatch, update, query_logged=True, stamped=stamped)

    assert len(stamped) == 1
    query_log_id, chat_id, message_ids = stamped[0]
    assert uuid.UUID(query_log_id)          # uuid client-side de log_query
    assert chat_id == -100123
    assert message_ids == [100 + i for i in range(len(update.message.replies))]


def test_bot_no_estampa_si_el_log_no_esta_committed(monkeypatch):
    """FK colgante = señal rota. Mismo criterio que el teclado de feedback."""
    stamped: list = []
    update = _Update(_Message())
    _run(monkeypatch, update, query_logged=False, stamped=stamped)
    assert stamped == []
    assert update.message.replies                      # la respuesta SÍ se envía


def test_bot_no_rompe_si_el_transporte_no_devuelve_message(monkeypatch):
    """El ancla es telemetría: sin `message_id` no se estampa y el envío sigue."""
    stamped: list = []
    update = _Update(_MessageSinId())
    _run(monkeypatch, update, query_logged=True, stamped=stamped)
    assert stamped == []
    assert update.message.replies


# ----------------------------------------------------------- guardas de esquema


def test_boundary_cubre_answer_messages():
    schema = (REPO / "supabase_schema.sql").read_text(encoding="utf-8")
    arrays = re.findall(
        r"FOREACH table_name IN ARRAY ARRAY\[\s*'query_logs', 'feedback', "
        r"'answer_feedback', 'answer_messages',\s*'user_consent'\s*\]",
        schema,
    )
    # Las postcondiciones iteran arrays: si falta en uno, un bootstrap fresco
    # crearía la tabla SIN hardening (nota r2 de s286, misma clase).
    assert len(arrays) == 2, "answer_messages falta en un FOREACH del boundary"
    assert "GRANT SELECT, INSERT ON TABLE public.answer_messages" in schema
    # NO lleva UPDATE: el ancla se inserta una vez y no se reescribe.
    assert "UPDATE ON TABLE public.answer_messages" not in schema
    assert "UNIQUE (telegram_chat_id, telegram_message_id)" in schema


def test_migracion_espeja_el_endurecimiento():
    path = (
        REPO / "supabase" / "migrations"
        / "20260802120000_s294_answer_message_anchor_v1.sql"
    )
    ddl = path.read_text(encoding="utf-8")
    for marker in (
        "CREATE TABLE IF NOT EXISTS answer_messages",
        "REFERENCES query_logs(id) ON DELETE CASCADE",
        "UNIQUE (telegram_chat_id, telegram_message_id)",
        "ENABLE ROW LEVEL SECURITY",
        "FORCE ROW LEVEL SECURITY",
        "GRANT SELECT, INSERT ON TABLE public.answer_messages TO service_role",
        "RAISE EXCEPTION",
    ):
        assert marker in ddl, f"falta en la migración: {marker}"
