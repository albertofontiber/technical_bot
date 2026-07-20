import asyncio
import json
import re
import types
from pathlib import Path

import pytest

import src.bot.telegram_bot as telegram_bot
from src.rag import serving_pipeline
from src.bot.response_formatter import (
    TELEGRAM_TEXT_LIMIT,
    convert_tables,
    format_for_telegram,
    format_telegram_messages,
    telegram_html_to_plain,
)

_FIXTURES = Path(__file__).parent / "fixtures"


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
        serving_pipeline,
        "apply_profiled_post_rerank_coverage",
        lambda _query, served, **_kwargs: (
            served,
            {
                "enabled": False,
                "status": "disabled_or_not_applicable",
                "protected_prefix_rows": len(served),
                "protected_prefix_equal": True,
                "appended_ids": [],
                "lanes": [],
            },
        ),
    )
    monkeypatch.setattr(
        telegram_bot,
        "generate_answer",
        lambda *_args, **_kwargs: {"answer": raw_answer, "diagrams": []},
    )
    monkeypatch.setattr(telegram_bot, "log_query", lambda **kwargs: logged.update(kwargs))

    asyncio.run(telegram_bot._process_query(update, context, "Estado ID_3000"))

    assert logged["response"] == raw_answer
    assert logged["rag_trace"]["schema"] == "rag_serving_trace_v1"
    assert logged["rag_trace"]["transport"]["message_parts"] == 1
    assert len(update.message.replies) == 1
    rendered, kwargs = update.message.replies[0]
    assert kwargs == {"parse_mode": "HTML"}
    assert "<b>Estado ID_3000__CPU</b>" in rendered
    assert "<b>Fuente:</b> Manual &lt;ID_3000&gt; (rev. 2)" in rendered


def test_handler_logs_and_sends_plain_text_when_formatter_fails(monkeypatch):
    raw_answer = "Respuesta técnica [F1]"
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
    monkeypatch.setattr(telegram_bot, "extract_product_models", lambda _query: ["P"])
    monkeypatch.setattr(telegram_bot, "retrieve_chunks", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(telegram_bot, "rerank", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(
        telegram_bot, "observe_structural_neighbor_shadow", lambda *_args: None
    )
    monkeypatch.setattr(
        serving_pipeline,
        "apply_profiled_post_rerank_coverage",
        lambda _query, served, **_kwargs: (
            served,
            {"enabled": False, "status": "disabled_or_not_applicable", "lanes": []},
        ),
    )
    monkeypatch.setattr(
        telegram_bot,
        "generate_answer",
        lambda *_args, **_kwargs: {"answer": raw_answer, "diagrams": []},
    )
    monkeypatch.setattr(telegram_bot, "log_query", lambda **kwargs: logged.update(kwargs))
    monkeypatch.setattr(
        telegram_bot,
        "format_telegram_messages",
        lambda _answer: (_ for _ in ()).throw(ValueError("formatter bug")),
    )

    asyncio.run(telegram_bot._process_query(update, context, "Pregunta P"))

    assert logged["response"] == raw_answer
    assert logged["rag_trace"]["transport"] == {
        "message_parts": 1,
        "render_status": "plain_fallback",
        "error_type": "ValueError",
    }
    assert update.message.replies == [(raw_answer, {})]


@pytest.mark.parametrize(
    "empty_answer",
    [
        "",
        "\u200b",
        "\ufeff",
        "\u2060",
        "\ufe0f",
        "\ufe0e",
        "\u034f",
        "\u180b",
        "\u2800",
        "\u3164",
        "\u115f",
        "\u1160",
        "\uffa0",
    ],
)
def test_handler_never_logs_or_sends_an_empty_generation(monkeypatch, empty_answer):
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
    monkeypatch.setattr(telegram_bot, "extract_product_models", lambda _query: ["P"])
    monkeypatch.setattr(telegram_bot, "retrieve_chunks", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(telegram_bot, "rerank", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(
        telegram_bot, "observe_structural_neighbor_shadow", lambda *_args: None
    )
    monkeypatch.setattr(
        serving_pipeline,
        "apply_profiled_post_rerank_coverage",
        lambda _query, served, **_kwargs: (
            served,
            {"enabled": False, "status": "disabled_or_not_applicable", "lanes": []},
        ),
    )
    monkeypatch.setattr(
        telegram_bot,
        "generate_answer",
        lambda *_args, **_kwargs: {"answer": empty_answer, "diagrams": []},
    )
    monkeypatch.setattr(telegram_bot, "log_query", lambda **kwargs: logged.update(kwargs))

    asyncio.run(telegram_bot._process_query(update, context, "Pregunta P"))

    fallback = telegram_bot._EMPTY_ANSWER_FALLBACK
    assert logged["response"] == fallback
    assert logged["response_length"] == len(fallback)
    assert logged["rag_trace"]["transport"] == {
        "message_parts": 1,
        "render_status": "empty_answer_fallback",
        "error_type": "RuntimeError",
    }
    assert update.message.replies == [(fallback, {"parse_mode": "HTML"})]


@pytest.mark.parametrize("formatted_parts", [[], ["\u200b"]])
def test_handler_rejects_empty_formatter_parts_and_uses_plain_fallback(
    monkeypatch, formatted_parts
):
    raw_answer = "Respuesta técnica [F1]"
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
    monkeypatch.setattr(telegram_bot, "extract_product_models", lambda _query: ["P"])
    monkeypatch.setattr(telegram_bot, "retrieve_chunks", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(telegram_bot, "rerank", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(
        telegram_bot, "observe_structural_neighbor_shadow", lambda *_args: None
    )
    monkeypatch.setattr(
        serving_pipeline,
        "apply_profiled_post_rerank_coverage",
        lambda _query, served, **_kwargs: (
            served,
            {"enabled": False, "status": "disabled_or_not_applicable", "lanes": []},
        ),
    )
    monkeypatch.setattr(
        telegram_bot,
        "generate_answer",
        lambda *_args, **_kwargs: {"answer": raw_answer, "diagrams": []},
    )
    monkeypatch.setattr(telegram_bot, "log_query", lambda **kwargs: logged.update(kwargs))
    monkeypatch.setattr(
        telegram_bot,
        "format_telegram_messages",
        lambda _answer: formatted_parts,
    )

    asyncio.run(telegram_bot._process_query(update, context, "Pregunta P"))

    assert logged["rag_trace"]["transport"] == {
        "message_parts": 1,
        "render_status": "plain_fallback",
        "error_type": "ValueError",
    }
    assert update.message.replies == [(raw_answer, {})]


def test_handler_wires_appended_coverage_through_generation_and_receipt(monkeypatch):
    logged = {}
    generated = {}

    class Message:
        def __init__(self):
            self.replies = []

        async def reply_text(self, text, **kwargs):
            self.replies.append((text, kwargs))

    update = types.SimpleNamespace(
        message=Message(), effective_user=types.SimpleNamespace(id=9)
    )
    context = types.SimpleNamespace(user_data={})
    prefix = [{"id": "prefix", "content": "base"}]
    appended = {"id": "coverage", "content": "bounded evidence"}

    monkeypatch.setattr(telegram_bot, "extract_product_models", lambda _query: ["P"])
    monkeypatch.setattr(telegram_bot, "retrieve_chunks", lambda *_args, **_kwargs: prefix)
    monkeypatch.setattr(telegram_bot, "rerank", lambda *_args, **_kwargs: prefix)
    monkeypatch.setattr(
        telegram_bot, "observe_structural_neighbor_shadow", lambda *_args: None
    )
    monkeypatch.setattr(
        serving_pipeline,
        "apply_profiled_post_rerank_coverage",
        lambda _query, served, **_kwargs: (
            served + [appended],
            {
                "enabled": True,
                "status": "appended",
                "lanes": [
                    {
                        "lane": "same_blob_structural_neighbor_coverage_v1",
                        "status": "selected",
                        "selected_ids": ["coverage"],
                    }
                ],
            },
        ),
    )

    def generate(_query, chunks, **_kwargs):
        generated["ids"] = [chunk["id"] for chunk in chunks]
        return {"answer": "Respuesta [F2]", "diagrams": []}

    monkeypatch.setattr(telegram_bot, "generate_answer", generate)
    monkeypatch.setattr(telegram_bot, "log_query", lambda **kwargs: logged.update(kwargs))

    asyncio.run(telegram_bot._process_query(update, context, "Pregunta P"))

    assert generated["ids"] == ["prefix", "coverage"]
    assert logged["chunks_used"] == 2
    assert logged["rag_trace"]["coverage"]["appended_rows"] == 1
    assert logged["rag_trace"]["coverage"]["executed_lanes"] == [
        "same_blob_structural_neighbor_coverage_v1"
    ]
    assert len(update.message.replies) == 1


# ─── s272: feedback vivo de Alberto (respuesta ASD535, query_logs 16:26Z) ───


def test_source_line_with_trailing_bold_marker_renders_clean():
    # El generador vivo emitió "**Fuente:** X" → el patrón viejo dejaba "** X"
    # literal en Telegram (el ** visible que reportó Alberto).
    rendered = format_for_telegram(
        "**Fuente:** ASD535, Descripción técnica, T 131 192 h es"
    )
    assert rendered == (
        "📄 <b>Fuente:</b> ASD535, Descripción técnica, T 131 192 h es"
    )
    assert "**" not in rendered


def test_blockquote_with_own_emoji_is_not_double_prefixed():
    rendered = format_for_telegram(
        "> ⚠️ **Importante**: bloquea la alerta remota antes de intervenir [F10]."
    )
    assert rendered.startswith("⚠️ <b>Importante</b>:")
    assert "ℹ️" not in rendered


def test_blockquote_importante_counts_as_warning():
    rendered = format_for_telegram("> **Importante**: no cortes la alimentación.")
    assert rendered.startswith("⚠️ ")


def test_caps_section_header_gets_bold_and_blank_line():
    rendered = format_for_telegram("Texto previo.\nCABLEADO:\n- Usa par trenzado.")
    assert rendered == "Texto previo.\n\n<b>CABLEADO:</b>\n• Usa par trenzado."


def test_step_bold_line_gets_wrench_and_blank_line():
    rendered = format_for_telegram(
        "Sigue el orden.\n**1. Leer el valor de flujo actual**\nColoca el conmutador."
    )
    assert (
        rendered
        == "Sigue el orden.\n\n🔧 <b>1. Leer el valor de flujo actual</b>\nColoca el conmutador."
    )


def test_heading_inside_block_gets_blank_line_before():
    rendered = format_for_telegram("Párrafo pegado.\n### Diagnóstico\nSiguiente línea.")
    assert rendered == "Párrafo pegado.\n\n<b>Diagnóstico</b>\nSiguiente línea."


def test_appendix_quoted_blockquote_marker_is_stripped_in_bullets():
    # Respuestas históricas ya almacenadas arrastran el marcador dentro de la cita.
    rendered = format_for_telegram(
        '- "> Para evitar disparos, es **imprescindible** bloquearlos." [F10]'
    )
    assert "&gt;" not in rendered
    assert '• "Para evitar disparos, es <b>imprescindible</b> bloquearlos." [F10]' == rendered


def test_appendix_bullet_comparison_operator_survives():
    rendered = format_for_telegram('- "> 100 mA de consumo máximo" [F2]')
    assert '• "&gt; 100 mA de consumo máximo" [F2]' == rendered


def _live_fixture() -> dict:
    return json.loads(
        (_FIXTURES / "s272_asd535_live_response.json").read_text(encoding="utf-8")
    )


def test_live_asd535_response_renders_without_raw_markdown():
    """Caso real (recibo vivo s272): ni ** ni > crudos; negrita y apéndice legibles."""
    fixture = _live_fixture()
    parts = format_telegram_messages(fixture["response"])
    assert parts, "la respuesta viva debe producir mensajes"
    combined = "\n\n".join(parts)
    assert "**" not in combined
    assert "&gt; Para evitar" not in combined  # blockquote crudo del apéndice
    assert "<b>imprescindible</b>" in combined
    assert "📄 <b>Fuente:</b>" in combined
    assert "ℹ️ ⚠️" not in combined  # doble emoji del aviso vivo
    assert "🔧 <b>1. Leer el valor de flujo actual</b>" in combined
    # el apéndice sigue identificable como sección
    assert "Información adicional del manual:" in telegram_html_to_plain(combined)
    for part in parts:
        assert len(part) <= 4000
        assert part.count("<b>") == part.count("</b>")


def test_live_asd535_response_preserves_every_numeric_and_model_token():
    """La vara del formatter: 0 tokens numéricos/modelo perdidos (byte-preservación
    del contenido técnico; solo cambia presentación)."""
    fixture = _live_fixture()
    raw = fixture["response"]
    parts = format_telegram_messages(raw)
    plain = "\n".join(telegram_html_to_plain(part) for part in parts)

    numeric_tokens = re.findall(r"\d+(?:[.,]\d+)?", raw)
    for token in set(numeric_tokens):
        assert plain.count(token) >= raw.count(token), f"token numérico perdido: {token}"

    for model_token in (
        "ASD535",
        "AMB 35",
        "LS-Ü",
        "12,3 a 13,8 V-CC",
        "21,6 a 27,6 V-CC",
        "10,4 V-CC",
        "T 131 192 h es",
        "[F1]",
        "[F10]",
        "bornes 1 (+) y 2 (-)",
    ):
        assert model_token in plain, f"token de modelo perdido: {model_token}"
