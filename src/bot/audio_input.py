"""Small, provider-agnostic helpers for Telegram audio ingestion."""

from __future__ import annotations

from pathlib import Path


_SUPPORTED_SUFFIXES = frozenset(
    {".flac", ".m4a", ".mp3", ".mp4", ".mpeg", ".mpga", ".oga", ".ogg", ".wav", ".webm"}
)
_MIME_SUFFIXES = {
    "audio/flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-m4a": ".m4a",
    "audio/x-wav": ".wav",
    "audio/webm": ".webm",
}


def audio_file_suffix(
    *,
    file_name: str | None = None,
    mime_type: str | None = None,
) -> str:
    """Return a safe extension matching the uploaded audio container.

    Telegram voice notes are OGG, but ``filters.AUDIO`` also accepts MP3/M4A
    and other containers.  Labelling every upload ``.ogg`` can make the
    transcription provider reject or mis-detect a valid file.  User-provided
    filenames never reach the filesystem; only a whitelisted suffix is used.
    """
    suffix = Path(file_name or "").suffix.lower()
    if suffix in _SUPPORTED_SUFFIXES:
        return suffix
    normalized_mime = (mime_type or "").split(";", 1)[0].strip().lower()
    return _MIME_SUFFIXES.get(normalized_mime, ".ogg")
