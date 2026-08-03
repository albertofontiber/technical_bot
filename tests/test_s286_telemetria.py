"""s286 telemetría — tests del paquete (salud + feedback 1-tap).

Cubre los contratos que el dúo r1/r2 fijó:
  · log_query: uuid cliente-side + retorno de éxito (política sin-keyboard).
  · log_answer_feedback: upsert con on_conflict explícito (el conflict target
    es el UNIQUE, no la PK — merge-duplicates solo NO basta, dúo r2).
  · callback: answer() SIEMPRE; consent gatea el write; parse estricto.
  · flags default-off = byte-idéntico; handler registrado incondicional.
  · guardas de esquema (r2 nota 3): answer_feedback en AMBOS arrays del
    boundary + rama de privilegios; DDL paste con CASCADE/UNIQUE/FORCE.
  · digest: semántica declarada (error/direct fuera, dogfooding segmentado,
    no-info heurística).
"""

import asyncio
import re
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

import src.logging_db as logging_db
from src.logging_db import TERMS_VERSION, log_answer_feedback, log_query

REPO = Path(__file__).parent.parent


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def json(self):
        return {}


class _FakeClient:
    """Captures httpx.Client(...).post calls; returns a scripted response."""

    def __init__(self, status_code: int = 201, raise_on_post: bool = False):
        self.status_code = status_code
        self.raise_on_post = raise_on_post
        self.calls: list[dict] = []

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, headers=None, json=None, params=None):
        if self.raise_on_post:
            raise ConnectionError("boom")
        self.calls.append(
            {"url": url, "headers": headers, "json": json, "params": params}
        )
        return _FakeResponse(self.status_code)


# ---------------------------------------------------------------- logging_db


def test_log_query_returns_true_and_sends_client_side_id(monkeypatch):
    fake = _FakeClient(status_code=201)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    row_id = str(uuid.uuid4())
    ok = log_query(
        telegram_user_id=1, query="q", query_log_id=row_id
    )
    assert ok is True
    assert fake.calls[0]["json"]["id"] == row_id


def test_log_query_without_id_omits_id_key(monkeypatch):
    fake = _FakeClient(status_code=201)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert log_query(telegram_user_id=1, query="q") is True
    assert "id" not in fake.calls[0]["json"]


def test_log_query_returns_false_on_http_error(monkeypatch):
    fake = _FakeClient(status_code=500)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert log_query(telegram_user_id=1, query="q") is False


def test_log_query_returns_false_on_exception(monkeypatch):
    fake = _FakeClient(raise_on_post=True)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert log_query(telegram_user_id=1, query="q") is False


def test_log_answer_feedback_upsert_contract(monkeypatch):
    fake = _FakeClient(status_code=201)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    row_id = str(uuid.uuid4())
    assert log_answer_feedback(row_id, 42, "down") is True
    call = fake.calls[0]
    assert call["url"].endswith("/rest/v1/answer_feedback")
    # Conflict target = UNIQUE pair, no la PK → on_conflict OBLIGATORIO (r2).
    assert call["params"] == {"on_conflict": "query_log_id,telegram_user_id"}
    assert "resolution=merge-duplicates" in call["headers"]["Prefer"]
    assert call["json"] == {
        "query_log_id": row_id,
        "telegram_user_id": 42,
        "verdict": "down",
    }
    # created_at nunca se reenvía: el upsert conserva el timestamp del primer voto.
    assert "created_at" not in call["json"]


def test_log_answer_feedback_false_on_fk_reject(monkeypatch):
    fake = _FakeClient(status_code=409)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert log_answer_feedback(str(uuid.uuid4()), 42, "up") is False


def test_terms_version_bumped_for_feedback_consent():
    # Tripwire DELIBERADO: cada dato nuevo que el bot recoge obliga a re-aceptar,
    # así que un cambio de versión debe ser una decisión, nunca un descuido.
    # v2 (s286) = el voto 👍/👎. v3 (s294) = la explicación en texto libre que el
    # bot ahora PIDE tras un 👎 (antes solo recogía lo espontáneo). v4 (s295) = plazo
    # de retención declarado + canal de derechos + corrección del audio.
    # Aquí se comprueba SU dato (el voto) + un suelo de versión; el pin EXACTO vive en
    # UN solo sitio (`test_s295_rgpd_retencion`) para que una subida legítima no rompa
    # tres tests a la vez sin aportar señal (pasó en v2→v3 y otra vez en v3→v4).
    import src.bot.telegram_bot as bot

    assert "👍/👎" in bot._CONSENT_TERMS
    assert int(TERMS_VERSION.lstrip("v")) >= 2


# ------------------------------------------------------------- telegram_bot


@pytest.fixture()
def bot_module():
    import src.bot.telegram_bot as bot

    return bot


def test_consent_terms_list_tap_verdict(bot_module):
    assert "valoración 👍/👎" in bot_module._CONSENT_TERMS


def test_feedback_flag_default_off(bot_module, monkeypatch):
    monkeypatch.delenv("TELEGRAM_FEEDBACK", raising=False)
    assert bot_module._feedback_keyboard_enabled() is False
    monkeypatch.setenv("TELEGRAM_FEEDBACK", "on")
    assert bot_module._feedback_keyboard_enabled() is True


def test_error_logging_flag_default_off(bot_module, monkeypatch):
    monkeypatch.delenv("BOT_ERROR_LOGGING", raising=False)
    assert bot_module._error_logging_enabled() is False


def test_feedback_keyboard_callback_data_fits_telegram_limit(bot_module):
    row_id = str(uuid.uuid4())
    markup = bot_module._feedback_keyboard(row_id)
    buttons = markup.inline_keyboard[0]
    assert [b.callback_data for b in buttons] == [
        f"fb:u:{row_id}",
        f"fb:d:{row_id}",
    ]
    for button in buttons:
        assert len(button.callback_data.encode()) <= 64


def test_feedback_callback_pattern_strict(bot_module):
    row_id = str(uuid.uuid4())
    pattern = bot_module._FEEDBACK_CALLBACK_PATTERN
    assert pattern.match(f"fb:u:{row_id}")
    assert pattern.match(f"fb:d:{row_id}")
    assert not pattern.match(f"fb:x:{row_id}")
    assert not pattern.match("fb:u:not-a-uuid")
    assert not pattern.match(f"FB:u:{row_id}")


def _fake_callback_update(data: str, user_id: int = 7):
    callback = MagicMock()
    callback.data = data
    callback.from_user.id = user_id
    answered: list = []

    async def _answer(text: str | None = None):
        answered.append(text)

    callback.answer = _answer
    update = MagicMock()
    update.callback_query = callback
    return update, answered


def test_feedback_callback_always_answers_on_malformed(bot_module, monkeypatch):
    writes: list = []
    monkeypatch.setattr(
        bot_module, "log_answer_feedback", lambda **kw: writes.append(kw) or True
    )
    update, answered = _fake_callback_update("fb:u:garbage")
    asyncio.run(bot_module.feedback_callback(update, None))
    assert answered == [None]  # spinner resuelto
    assert writes == []  # y NADA escrito


def test_feedback_callback_consent_gates_write(bot_module, monkeypatch):
    writes: list = []
    monkeypatch.setattr(bot_module, "has_consent", lambda uid: False)
    monkeypatch.setattr(
        bot_module, "log_answer_feedback", lambda **kw: writes.append(kw) or True
    )
    update, answered = _fake_callback_update(f"fb:u:{uuid.uuid4()}")
    asyncio.run(bot_module.feedback_callback(update, None))
    assert len(answered) == 1 and "términos" in answered[0]
    assert writes == []


def test_feedback_callback_writes_verdict(bot_module, monkeypatch):
    writes: list = []
    monkeypatch.setattr(bot_module, "has_consent", lambda uid: True)
    monkeypatch.setattr(
        bot_module,
        "log_answer_feedback",
        lambda **kw: writes.append(kw) or True,
    )
    row_id = str(uuid.uuid4())
    update, answered = _fake_callback_update(f"fb:d:{row_id}", user_id=99)
    asyncio.run(bot_module.feedback_callback(update, None))
    assert writes == [
        {"query_log_id": row_id, "telegram_user_id": 99, "verdict": "down"}
    ]
    assert "Gracias" in answered[0]


def test_callback_handler_registered_unconditionally():
    source = (REPO / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    registration = re.search(
        r"app\.add_handler\(CallbackQueryHandler\(feedback_callback", source
    )
    assert registration, "CallbackQueryHandler(feedback_callback) no registrado"
    # El registro NO puede estar gateado por el flag (r1: apagar el flag no
    # debe dejar botones muertos girando en el historial): la línea vive al
    # nivel de los demás add_handler (indent 4), no dentro de un if.
    run_bot_body = source[source.index("def run_bot") :]
    registration_line = next(
        line
        for line in run_bot_body.splitlines()
        if "CallbackQueryHandler(feedback_callback" in line
    )
    assert registration_line.startswith("    app.add_handler(")
    assert "if _feedback_keyboard_enabled" not in run_bot_body


# ------------------------------------------------------------ schema guards


def test_schema_boundary_covers_answer_feedback():
    schema = (REPO / "supabase_schema.sql").read_text(encoding="utf-8")
    # r2 nota 3: las postcondiciones iteran arrays — answer_feedback debe estar
    # en AMBOS FOREACH o un bootstrap fresco la crearía sin hardening.
    # s294: la guarda ya NO fija el literal del array — se rompía al añadir una
    # tabla legítima (`answer_messages`) y eso la convertía en fricción, no en
    # protección. Fija lo que de verdad importa: que `answer_feedback` esté en
    # los DOS FOREACH del boundary.
    boundary_arrays = re.findall(
        r"FOREACH table_name IN ARRAY ARRAY\[(.*?)\]", schema, re.DOTALL
    )
    with_feedback = [a for a in boundary_arrays if "'answer_feedback'" in a]
    assert len(with_feedback) == 2, "answer_feedback falta en un FOREACH del boundary"
    assert "ANY(ARRAY['user_consent', 'answer_feedback'])" in schema
    assert (
        "GRANT SELECT, INSERT, UPDATE ON TABLE public.answer_feedback" in schema
    )
    assert "REFERENCES query_logs(id) ON DELETE CASCADE" in schema
    assert "UNIQUE (query_log_id, telegram_user_id)" in schema


def test_ddl_paste_mirrors_schema_hardening():
    ddl = (REPO / "evals" / "s286_answer_feedback_ddl_v1.sql").read_text(
        encoding="utf-8"
    )
    for marker in (
        "FORCE ROW LEVEL SECURITY",
        "REFERENCES query_logs(id) ON DELETE CASCADE",
        "UNIQUE (query_log_id, telegram_user_id)",
        "GRANT SELECT, INSERT, UPDATE ON TABLE public.answer_feedback",
        "security_invoker = true",
        "ROLLBACK",
    ):
        assert marker in ddl, f"DDL paste sin {marker!r}"


def test_health_views_exclude_error_and_direct():
    schema = (REPO / "supabase_schema.sql").read_text(encoding="utf-8")
    for view in ("bot_health_daily", "bot_health_semanal"):
        assert view in schema
    assert "source <> 'error' AND category IS DISTINCT FROM 'direct'" in schema


# ------------------------------------------------------------------- digest


def _row(**kw):
    base = {
        "telegram_user_id": 100,
        "source": "text",
        "category": None,
        "response": "La central admite 2 lazos.",
        "response_time_ms": 4000,
        "bot_version": "abc1234",
        "created_at": "2026-07-29T10:00:00Z",
    }
    base.update(kw)
    return base


def test_summarize_excludes_error_and_direct_rows():
    from scripts.bot_health_report import summarize

    rows = [
        _row(),
        _row(source="error", response="TimeoutError@process_query"),
        _row(category="direct"),
    ]
    summary = summarize(rows, internal=set())
    assert summary["consultas_rag"] == 1
    assert summary["filas_error"] == 1


def test_summarize_segments_dogfooding():
    from scripts.bot_health_report import summarize

    rows = [_row(telegram_user_id=1), _row(telegram_user_id=2)]
    summary = summarize(rows, internal={1})
    assert summary["consultas_rag"] == 2
    assert summary["consultas_rag_tecnicos"] == 1
    assert summary["consultas_rag_internas"] == 1
    assert summary["tecnicos_unicos"] == 1


def test_summarize_no_info_heuristic_is_prefix_and_case_insensitive():
    from scripts.bot_health_report import summarize

    rows = [
        _row(response="No tengo información sobre Cofem en mi base."),
        _row(response="no dispongo de manuales de esa marca."),
        _row(response="El relé soporta no tengo información..."),  # no-prefijo
    ]
    summary = summarize(rows, internal=set())
    assert summary["no_info_heuristica"] == 2


def test_summarize_counts_transport_fallback_separately():
    from scripts.bot_health_report import summarize

    rows = [_row(response="No he podido generar una respuesta completa y segura. Inténtalo de nuevo.")]
    summary = summarize(rows, internal=set())
    assert summary["errores_transporte"] == 1
    assert summary["no_info_heuristica"] == 0


def test_internal_ids_parses_csv(monkeypatch):
    from scripts.bot_health_report import internal_ids

    monkeypatch.setenv("INTERNAL_TELEGRAM_IDS", "123, 456,abc,")
    assert internal_ids() == {123, 456}


# -------------------------------------------------------------- review_logs


def test_attach_tap_verdicts_exact_fk_join():
    from scripts.review_logs import _attach_tap_verdicts

    queries = pd.DataFrame(
        [{"id": "q1", "query": "a"}, {"id": "q2", "query": "b"}]
    )
    taps = pd.DataFrame(
        [
            {"query_log_id": "q1", "telegram_user_id": 1, "verdict": "up"},
            {"query_log_id": "q1", "telegram_user_id": 2, "verdict": "down"},
        ]
    )
    joined = _attach_tap_verdicts(queries, taps)
    assert joined.loc[joined["id"] == "q1", "tap_verdict"].iloc[0] == "up,down"
    assert pd.isna(joined.loc[joined["id"] == "q2", "tap_verdict"].iloc[0])


def test_attach_tap_verdicts_empty_frame():
    from scripts.review_logs import _attach_tap_verdicts

    queries = pd.DataFrame([{"id": "q1", "query": "a"}])
    joined = _attach_tap_verdicts(queries, pd.DataFrame())
    assert "tap_verdict" in joined.columns
    assert joined["tap_verdict"].isna().all()
