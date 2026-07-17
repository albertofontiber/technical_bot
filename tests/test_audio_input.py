import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.bot.audio_input import audio_file_suffix


@pytest.mark.parametrize(
    "file_name,mime_type,expected",
    [
        ("pregunta.MP3", "audio/mpeg", ".mp3"),
        ("pregunta.m4a", "audio/mp4", ".m4a"),
        (None, "audio/webm; codecs=opus", ".webm"),
        (None, "audio/ogg", ".ogg"),
        (None, None, ".ogg"),  # Telegram voice-note default
    ],
)
def test_audio_file_suffix_preserves_supported_container(file_name, mime_type, expected):
    assert audio_file_suffix(file_name=file_name, mime_type=mime_type) == expected


@pytest.mark.parametrize("unsafe", ["voice.exe", "../../secret.txt", "voice.ogg.exe"])
def test_audio_file_suffix_rejects_untrusted_extensions(unsafe):
    assert audio_file_suffix(file_name=unsafe, mime_type=None) == ".ogg"


def test_supported_filename_wins_over_inconsistent_mime():
    assert audio_file_suffix(file_name="voice.wav", mime_type="audio/mpeg") == ".wav"


def test_transcribe_audio_offloads_blocking_provider_call(monkeypatch):
    from src.bot import telegram_bot as bot

    monkeypatch.setattr(bot, "_transcribe_audio_sync", lambda path: f"ok:{path}")

    assert asyncio.run(bot.transcribe_audio("voice.ogg")) == "ok:voice.ogg"


def test_voice_handler_normalizes_for_rag_but_preserves_raw_transcription(monkeypatch):
    from src.bot import telegram_bot as bot

    raw = "fallo en i de tres mil"
    captured = {}

    async def fake_transcribe(_path):
        return raw

    async def fake_process(update, context, query, **kwargs):
        captured.update(query=query, **kwargs)

    downloaded = AsyncMock()
    telegram_file = SimpleNamespace(download_to_drive=downloaded)
    voice = SimpleNamespace(
        file_id="voice-id",
        duration=4,
        file_name=None,
        mime_type="audio/ogg",
    )
    message = SimpleNamespace(
        voice=voice,
        audio=None,
        chat=SimpleNamespace(send_action=AsyncMock()),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(
        message=message,
        effective_user=SimpleNamespace(id=123),
    )
    context = SimpleNamespace(
        bot=SimpleNamespace(get_file=AsyncMock(return_value=telegram_file)),
        user_data={},
    )

    monkeypatch.setattr(bot, "has_consent", lambda _user_id: True)
    monkeypatch.setattr(bot, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(bot, "_process_query", fake_process)

    asyncio.run(bot.handle_voice(update, context))

    assert captured == {
        "query": "fallo en ID3000",
        "source": "voice",
        "transcription": raw,
    }
    confirmation = message.reply_text.await_args.args[0]
    assert raw in confirmation
    assert "Modelo interpretado: ID3000" in confirmation
    assert message.reply_text.await_args.kwargs == {}
