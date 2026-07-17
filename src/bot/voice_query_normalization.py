"""Conservative post-ASR normalization for spoken product-model codes.

Whisper can render a model spoken letter by letter (``"i de tres mil"``)
instead of using the printed code (``"ID3000"``).  The regular query model
extractor correctly refuses that free prose, so voice queries lose their most
useful retrieval anchor.

This module closes only that representation gap.  It generates spoken forms
from the canonical model catalog, requires an exact full spoken form, and
rewrites a span only when it maps to one canonical model.  There is no fuzzy
or phonetic guessing: unknown and ambiguous speech fails open unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
import unicodedata


_TOKEN_SEPARATOR = r"[\s\-/.+]*"
_SPOKEN_SEPARATOR = r"[\s\-/.+,]+"

_LETTER_NAMES = {
    "a": ("a",),
    "b": ("be",),
    "c": ("ce",),
    "d": ("de",),
    "e": ("e",),
    "f": ("efe",),
    "g": ("ge",),
    "h": ("hache",),
    "i": ("i",),
    "j": ("jota",),
    "k": ("ka",),
    "l": ("ele",),
    "m": ("eme",),
    "n": ("ene",),
    "o": ("o",),
    "p": ("pe",),
    "q": ("cu",),
    "r": ("erre",),
    "s": ("ese",),
    "t": ("te",),
    "u": ("u",),
    "v": ("uve",),
    "w": ("uve doble", "doble uve"),
    "x": ("equis",),
    "y": ("ye", "i griega"),
    "z": ("zeta",),
}

_UNITS = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete",
    "ocho", "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
    "dieciseis", "diecisiete", "dieciocho", "diecinueve", "veinte",
    "veintiuno", "veintidos", "veintitres", "veinticuatro", "veinticinco",
    "veintiseis", "veintisiete", "veintiocho", "veintinueve",
)
_TENS = {
    30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta",
    70: "setenta", 80: "ochenta", 90: "noventa",
}
_HUNDREDS = {
    200: "doscientos", 300: "trescientos", 400: "cuatrocientos",
    500: "quinientos", 600: "seiscientos", 700: "setecientos",
    800: "ochocientos", 900: "novecientos",
}


@dataclass(frozen=True)
class ModelSubstitution:
    """One auditable rewrite of a spoken span to a canonical catalog model."""

    original: str
    canonical: str
    start: int
    end: int


@dataclass(frozen=True)
class VoiceQueryNormalization:
    """Raw and retrieval-ready forms of a voice transcription."""

    raw: str
    normalized: str
    substitutions: tuple[ModelSubstitution, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.substitutions)


@dataclass(frozen=True)
class _ModelPattern:
    canonical: str
    spoken: re.Pattern[str]
    direct: re.Pattern[str]


def _fold(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _segments(value: str) -> list[str]:
    return re.findall(r"[a-z]+|\d+", _fold(value))


def _under_thousand(value: int) -> str:
    if value < 30:
        return _UNITS[value]
    if value < 100:
        tens = value // 10 * 10
        unit = value % 10
        return _TENS[tens] if not unit else f"{_TENS[tens]} y {_UNITS[unit]}"
    if value == 100:
        return "cien"
    hundreds = value // 100 * 100
    rest = value % 100
    prefix = "ciento" if hundreds == 100 else _HUNDREDS[hundreds]
    return prefix if not rest else f"{prefix} {_under_thousand(rest)}"


def _number_words(digits: str) -> str | None:
    """Return a folded Spanish reading for a numeric model-code segment."""
    if not digits or (len(digits) > 1 and digits.startswith("0")):
        return None
    value = int(digits)
    if value < 1000:
        return _under_thousand(value)
    if value >= 1_000_000:
        return None
    thousands, rest = divmod(value, 1000)
    prefix = "mil" if thousands == 1 else f"{_under_thousand(thousands)} mil"
    return prefix if not rest else f"{prefix} {_under_thousand(rest)}"


def _phrase_pattern(value: str) -> str:
    return _SPOKEN_SEPARATOR.join(re.escape(part) for part in value.split())


def _letter_segment_pattern(segment: str) -> str:
    # Intact codes ("afp") plus character-by-character readings
    # ("a efe pe", "a f p", or a mixture of both).
    spelled_chars: list[str] = []
    for char in segment:
        options = {re.escape(char)}
        options.update(_phrase_pattern(name) for name in _LETTER_NAMES[char])
        spelled_chars.append("(?:" + "|".join(sorted(options)) + ")")
    spelled = _SPOKEN_SEPARATOR.join(spelled_chars)
    return f"(?:{re.escape(segment)}|{spelled})"


def _digit_segment_pattern(segment: str) -> str:
    options = {re.escape(segment)}
    as_number = _number_words(segment)
    if as_number:
        options.add(_phrase_pattern(as_number))
    digit_by_digit = " ".join(_UNITS[int(char)] for char in segment)
    options.add(_phrase_pattern(digit_by_digit))
    return "(?:" + "|".join(sorted(options, key=lambda item: (-len(item), item))) + ")"


def _is_plausible_model(model: str, segments: list[str]) -> bool:
    """Bound the index to code-like catalog values, not arbitrary prose."""
    if not segments or len(model) > 48:
        return False
    if any(segment.isdigit() for segment in segments):
        # Two-character codes such as X1 are too easy to trigger in ordinary
        # speech ("equis uno").  Require at least three canonical characters;
        # real compact codes such as E10 and 2X-A remain covered.
        return (
            any(segment.isalpha() for segment in segments)
            and sum(len(segment) for segment in segments) >= 3
        )
    # Alphabetic-only model codes are useful only when short and unspaced
    # (ZXe, DXc, PEARL).  Their normal pronunciation is already detected; the
    # generated spelling only handles explicit letter-by-letter speech.
    return len(segments) == 1 and 2 <= len(segments[0]) <= 10


@lru_cache(maxsize=4)
def _compile_patterns(models: tuple[str, ...]) -> tuple[_ModelPattern, ...]:
    patterns: list[_ModelPattern] = []
    seen: set[str] = set()
    for canonical in models:
        segments = _segments(canonical)
        key = "".join(segments)
        if not key or key in seen or not _is_plausible_model(canonical, segments):
            continue
        seen.add(key)

        spoken_parts = [
            _digit_segment_pattern(segment)
            if segment.isdigit()
            else _letter_segment_pattern(segment)
            for segment in segments
        ]
        direct_parts = [re.escape(segment) for segment in segments]
        spoken_core = _TOKEN_SEPARATOR.join(spoken_parts)
        direct_core = _TOKEN_SEPARATOR.join(direct_parts)
        patterns.append(
            _ModelPattern(
                canonical=canonical,
                spoken=re.compile(rf"(?<![a-z0-9]){spoken_core}(?![a-z0-9])"),
                direct=re.compile(rf"(?<![a-z0-9]){direct_core}(?![a-z0-9])"),
            )
        )
    return tuple(patterns)


def normalize_voice_query(
    transcript: str,
    *,
    models: tuple[str, ...] | None = None,
) -> VoiceQueryNormalization:
    """Rewrite unambiguous spoken model codes using the canonical catalog.

    ``models`` is injectable for deterministic unit tests.  Production reads
    the same catalog snapshot as retrieval.  Missing catalog, unknown speech,
    and ambiguous spans all return the transcription byte-for-byte unchanged.
    """
    raw = transcript or ""
    if not raw.strip():
        return VoiceQueryNormalization(raw=raw, normalized=raw)

    if models is None:
        try:
            from ..rag.catalog import all_models, catalog_available

            if not catalog_available():
                return VoiceQueryNormalization(raw=raw, normalized=raw)
            models = tuple(all_models())
        except Exception:
            return VoiceQueryNormalization(raw=raw, normalized=raw)

    folded = _fold(raw)
    matches: dict[tuple[int, int], dict[str, tuple[str, str]]] = {}
    for model_pattern in _compile_patterns(tuple(models)):
        for match in model_pattern.spoken.finditer(folded):
            start, end = match.span()
            surface = folded[start:end]
            # If the normal catalog representation already recognizes the
            # span, rewriting adds no value and needlessly changes user text.
            if model_pattern.direct.fullmatch(surface):
                continue
            key = "".join(_segments(model_pattern.canonical))
            matches.setdefault((start, end), {})[key] = (
                model_pattern.canonical,
                raw[start:end],
            )

    # A spoken span must identify exactly one canonical key.  Prefer the
    # longest non-overlapping span when one catalog code is a prefix of another.
    candidates: list[ModelSubstitution] = []
    for (start, end), by_key in matches.items():
        if len(by_key) != 1:
            continue
        canonical, original = next(iter(by_key.values()))
        candidates.append(ModelSubstitution(original, canonical, start, end))
    candidates.sort(key=lambda item: (item.start, -(item.end - item.start), item.canonical))

    selected: list[ModelSubstitution] = []
    for candidate in candidates:
        if any(
            candidate.start < existing.end and existing.start < candidate.end
            for existing in selected
        ):
            continue
        selected.append(candidate)
    selected.sort(key=lambda item: item.start)

    if not selected:
        return VoiceQueryNormalization(raw=raw, normalized=raw)

    normalized = raw
    for substitution in reversed(selected):
        normalized = (
            normalized[:substitution.start]
            + substitution.canonical
            + normalized[substitution.end:]
        )
    return VoiceQueryNormalization(
        raw=raw,
        normalized=normalized,
        substitutions=tuple(selected),
    )
