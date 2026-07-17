import asyncio
import re
import types

import pytest

import src.bot.telegram_bot as telegram_bot
from src.bot.response_formatter import (
    TELEGRAM_TEXT_LIMIT,
    convert_tables,
    format_for_telegram,
    format_telegram_messages,
    telegram_html_to_plain,
)


def test_renderer_preserves_technical_content_and_builds_field_hierarchy():
    answer = """## Conexionado NFS2-3030

1. Conecta **TB7 +24 V** al borne `A&B` [F1].
2. Verifica 6,8 kΩ y 0,5 W [F2].

> **Advertencia:** no energices el lazo durante la prueba [F3].

Fuente: Manual <NFS2-3030> (rev. 4)"""

    rendered = format_for_telegram(answer)

    assert rendered.startswith("<b>Conexionado NFS2-3030</b>")
    assert "<b>TB7 +24 V</b>" in rendered
    assert "<code>A&amp;B</code> [F1]" in rendered
    assert "⚠️ <b>Advertencia:</b>" in rendered
    assert "<b>Fuente:</b> Manual &lt;NFS2-3030&gt; (rev. 4)" in rendered

    plain = telegram_html_to_plain(rendered)
    for technical_token in (
        "NFS2-3030",
        "TB7 +24 V",
        "A&B",
        "[F1]",
        "6,8 kΩ",
        "0,5 W",
        "[F2]",
        "[F3]",
        "rev. 4",
    ):
        assert technical_token in plain


def test_raw_html_and_model_underscores_cannot_break_telegram_markup():
    rendered = format_for_telegram(
        "Modelo ID_3000__CPU <script>alert('x')</script> & salida [F7]."
    )

    assert "ID_3000__CPU" in rendered
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&amp; salida [F7]" in rendered


def test_table_conversion_keeps_every_data_cell_and_escaped_pipe():
    table = r"""| Parámetro | Valor |
|:---|---:|
| Salida | `A\|B` |
| Tensión | 24 V | dato adicional |"""

    converted = convert_tables(table)

    assert "• Parámetro: Salida · Valor: `A|B`" in converted
    assert "• Parámetro: Tensión · Valor: 24 V · dato adicional" in converted


def test_code_block_is_escaped_and_kept_as_a_preformatted_unit():
    rendered = format_for_telegram("Esquema:\n```text\nA < B && C > D\n```")

    assert "<pre>A &lt; B &amp;&amp; C &gt; D</pre>" in rendered
    assert "```" not in rendered


def test_long_response_is_split_into_independently_balanced_messages():
    paragraph = "## Procedimiento\n" + " ".join(
        f"**Paso {index}**: comprueba borne A_{index} [F1]."
        for index in range(220)
    )
    answer = paragraph + "\n\nFuente: Manual de instalación (rev. 2)"

    messages = format_telegram_messages(answer, max_length=700)

    assert len(messages) > 1
    assert all(len(message) <= 700 for message in messages)
    assert all(message.count("<b>") == message.count("</b>") for message in messages)
    combined_plain = "\n".join(telegram_html_to_plain(message) for message in messages)
    assert "Paso 0" in combined_plain
    assert "A_219 [F1]" in combined_plain
    assert "Fuente: Manual de instalación (rev. 2)" in combined_plain


def test_message_limit_contract_rejects_invalid_values():
    with pytest.raises(ValueError):
        format_telegram_messages("respuesta", max_length=0)
    with pytest.raises(ValueError):
        format_telegram_messages("respuesta", max_length=TELEGRAM_TEXT_LIMIT + 1)


def test_renderer_is_deterministic():
    answer = "## Estado\n\n• Bucle: OK [F2]\n\nFuentes: M1; M2"
    assert format_telegram_messages(answer) == format_telegram_messages(answer)


def test_output_exposes_only_the_controlled_html_tag_set():
    rendered = format_for_telegram(
        "# Título\n\n**Negrita** y `código` <b>inyectado</b>."
    )
    tags = re.findall(r"</?([a-zA-Z0-9]+)(?:\s[^>]*)?>", rendered)
    assert set(tags) <= {"b", "code", "pre"}


def test_real_handler_logs_raw_answer_and_sends_safe_html(monkeypatch):
    raw_answer = (
        "## Estado ID_3000__CPU\n\n"
        "**Tensión:** 24 V [F1].\n\n"
        "Fuente: Manual <ID_3000> (rev. 2)"
    )
    logged = {}

    class Message:
        def __init__(self):
            self.replies = []

        async def reply_text(self, text, **kwargs):
            self.replies.append((text, kwargs))

    update = types.SimpleNamespace(
        message=Message(), effective_user=types.SimpleNamespace(id=9)
    )
    context = types.SimpleNamespace(user_data={})
    chunks = [{"id": "c1", "content": "evidence"}]

    monkeypatch.setattr(telegram_bot, "extract_product_models", lambda _query: ["ID_3000"])
    monkeypatch.setattr(telegram_bot, "retrieve_chunks", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(telegram_bot, "rerank", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(
        telegram_bot, "observe_structural_neighbor_shadow", lambda *_args: None
    )
    monkeypatch.setattr(
        telegram_bot,
        "apply_post_rerank_coverage",
        lambda _query, served, **_kwargs: served,
    )
    monkeypatch.setattr(
        telegram_bot,
        "generate_answer",
        lambda *_args, **_kwargs: {"answer": raw_answer, "diagrams": []},
    )
    monkeypatch.setattr(telegram_bot, "log_query", lambda **kwargs: logged.update(kwargs))

    asyncio.run(telegram_bot._process_query(update, context, "Estado ID_3000"))

    assert logged["response"] == raw_answer
    assert len(update.message.replies) == 1
    rendered, kwargs = update.message.replies[0]
    assert kwargs == {"parse_mode": "HTML"}
    assert "<b>Estado ID_3000__CPU</b>" in rendered
    assert "<b>Fuente:</b> Manual &lt;ID_3000&gt; (rev. 2)" in rendered
