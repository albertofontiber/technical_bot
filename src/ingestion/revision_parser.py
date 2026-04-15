r"""Revision parser — extract identity metadata from PDF filenames (+ first pages).

Phase 2 of the document-management refactor. This module is PURE: it has no
database or network dependencies, so it can be unit-tested in isolation and
called safely from both the ingestion pipeline and offline backfill scripts.

What it extracts from a filename (and optionally the first ~2 pages of text):

    document_family   — normalized name without rev/date/lang/type suffixes
    revision          — short human-readable string ("4", "Rev B", "Iss 1 Rev 4", "03", "v2.26")
    revision_date     — datetime.date or None
    language          — 'es' | 'en' | 'fr' | 'pt' | 'multi' | None
    doc_type          — 'instalacion' | 'usuario' | 'programacion' | 'guia_rapida'
                        | 'hoja_datos' | 'comunicacion_tecnica' | 'mantenimiento' | None

Implementation notes:
  - Underscores are treated as word separators by pre-normalizing "_" → " "
    before most regex matches. This is essential because Python's \b word
    boundary treats "_" as a word char, so patterns like "\brv\d+\b" fail
    on "HLSI-MA-025_rv03".
  - The MADT-style internal revision pattern (trailing "_NN" like "MADT015_03")
    is matched on the RAW stem, not the normalized one, because it relies on
    the underscore being present.
  - Regexes are ordered by specificity: most precise patterns first.
  - When in doubt, return None. A NULL revision is safe; a WRONG revision
    would break the supersede chain. Phase 6 eval flags ambiguous cases.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class RevisionInfo:
    document_family: str
    revision: str | None
    revision_date: date | None
    language: str | None
    doc_type: str | None


def _norm(stem: str) -> str:
    """Replace underscores with spaces so \b word boundaries behave."""
    return stem.replace("_", " ")


# ---------------------------------------------------------------------------
# Language detection (from filename tokens)
# ---------------------------------------------------------------------------
# Built against normalized stem (no underscores). Use space/dash/paren/dot
# as separators.
_SEP = r"(?:^|[\s\-\(\.])"
_SEP_END = r"(?=[\s\-\)\.]|$)"

_LANG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"{_SEP}multi(?:ling(?:ual)?)?{_SEP_END}", re.I), "multi"),
    (re.compile(rf"{_SEP}(?:es|sp|spa|spanish|esp)(?:{_SEP_END}|(?=[A-Z][a-z]))", re.I), "es"),
    (re.compile(rf"{_SEP}(?:en|gb|eng|english|uk)(?:{_SEP_END}|(?=[A-Z][a-z]))", re.I), "en"),
    (re.compile(rf"{_SEP}(?:fr|fra|french|francais){_SEP_END}", re.I), "fr"),
    (re.compile(rf"{_SEP}(?:pt|por|portuguese|portugues){_SEP_END}", re.I), "pt"),
    (re.compile(rf"{_SEP}(?:de|ger|german|deutsch){_SEP_END}", re.I), "de"),
    (re.compile(rf"{_SEP}(?:it|ita|italian|italiano){_SEP_END}", re.I), "it"),
]


def detect_language(stem: str) -> str | None:
    s = _norm(stem)
    for pat, lang in _LANG_PATTERNS:
        if pat.search(s):
            return lang
    return None


# ---------------------------------------------------------------------------
# Document type detection (from filename keywords)
# ---------------------------------------------------------------------------
_DOCTYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Guía rápida / quick start — check BEFORE 'manual' because "Quick Start Guide"
    # contains "Guide".
    (re.compile(r"\b(?:guia[\s\-]?rapida|quick[\s\-]?start|guide[\s\-]?rapide|qig|qref|quickguide|qg)\b", re.I), "guia_rapida"),
    # Instalación
    (re.compile(r"\b(?:instalacion|installation|install|instal[\s\-]?comm|commissioning|puesta[\s]en[\s]marcha)\b", re.I), "instalacion"),
    # Usuario / operación — checked BEFORE programacion so "manual de usuario y
    # programacion" classifies as usuario (primary audience).
    (re.compile(r"\b(?:usuario|user|operating|operation|operador|manu[\s\-]?prog|manu[\s\-]?spa)\b", re.I), "usuario"),
    # Programación / configuración
    (re.compile(r"\b(?:programacion|programming|configuration|config(?:ur)?[a-z]*)\b", re.I), "programacion"),
    # Mantenimiento
    (re.compile(r"\b(?:mantenimiento|maintenance|servicing)\b", re.I), "mantenimiento"),
    # Hoja de datos / product guide / datasheet / technical handbook
    (re.compile(r"\b(?:datasheet|hoja[\s]datos|product[\s]guide|technical[\s]handbook|technical[\s]information)\b", re.I), "hoja_datos"),
    # Comunicación técnica / nota técnica
    (re.compile(r"\b(?:comunicacion[\s]tecnica|nota[\s]tecnica|technical[\s]note|application[\s]note|tech[\s]bulletin)\b", re.I), "comunicacion_tecnica"),
]


def detect_doc_type(stem: str) -> str | None:
    s = _norm(stem)
    for pat, dt in _DOCTYPE_PATTERNS:
        if pat.search(s):
            return dt
    return None


# ---------------------------------------------------------------------------
# Date detection
# ---------------------------------------------------------------------------
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

# DD-MM-YYYY, DD/MM/YYYY, DD_MM_YYYY — separator must be the SAME on both sides.
# This avoids matching "issue 4_04-2025" as day=4,month=4.
_RE_DATE_DMY = re.compile(r"(?<!\d)(\d{1,2})([\-_/])(\d{1,2})\2(\d{4})(?!\d)")
# MM-YYYY or MM_YYYY
_RE_DATE_MY = re.compile(r"(?<!\d)(\d{1,2})[\-_/](20\d{2})(?!\d)")
# DDMMYYYY compact (8 digits)
_RE_DATE_COMPACT = re.compile(r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)")
# "17July2015", "20 July 2015"  — (?<!\d) only, since "_" often precedes
_RE_DATE_TEXT = re.compile(
    r"(?<!\d)(\d{1,2})\s*(" + "|".join(_MONTHS.keys()) + r")\s*(20\d{2})(?!\d)",
    re.I,
)


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def detect_date(stem: str) -> date | None:
    s = stem  # keep raw for underscores
    # Text-month form first (unambiguous)
    m = _RE_DATE_TEXT.search(s)
    if m:
        d = int(m.group(1))
        mo = _MONTHS[m.group(2).lower()]
        y = int(m.group(3))
        if dt := _safe_date(y, mo, d):
            return dt
    # DD-MM-YYYY form (same separator enforced)
    m = _RE_DATE_DMY.search(s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(3)), int(m.group(4))
        if dt := _safe_date(y, b, a):
            return dt
    # Compact DDMMYYYY
    m = _RE_DATE_COMPACT.search(s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            if dt := _safe_date(y, mo, d):
                return dt
    # Month-Year (return first of month)
    m = _RE_DATE_MY.search(s)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            if dt := _safe_date(y, mo, 1):
                return dt
    return None


# ---------------------------------------------------------------------------
# Revision detection
# ---------------------------------------------------------------------------
# Each pattern is paired with a format tag so the caller knows how to render
# the output. Patterns run in order; first match wins.
#
# Tags:
#   "iss_rev"   → "Iss {g1} Rev {g2}"
#   "rev_raw"   → "Rev {g1}"
#   "num"       → "{int(g1)}"   (strips leading zeros)
#   "num_raw"   → "{g1}"        (preserves leading zeros — for MADT _NN)
#   "v"         → "v{int(g1)}" if int-able else "v{g1}"
#   "r_firm"    → "R{g1}"
_REVISION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # "ISS 1 Rev 4", "Issue 4 Rev B"
    (re.compile(r"\b(?:ISS|Issue)\s*(\d+)[\s\-]*Rev\.?\s*([A-Z0-9]+)\b", re.I), "iss_rev"),
    # "RV 3", "Rv 4", "RV0" — Notifier style
    (re.compile(r"\bRV\s*(\d+)\b", re.I), "num"),
    # "rv03", "rv05" concatenated
    (re.compile(r"(?:^|[^A-Za-z])rv(\d{1,3})(?![A-Za-z])", re.I), "num"),
    # "Rev. A", "Rev B", "Rev 4", "RevB"
    (re.compile(r"\bRev\.?\s*([A-Z0-9][A-Z0-9\.]*)\b", re.I), "rev_raw"),
    # "issue 4" — numeric issue
    (re.compile(r"\bissue\s*(\d+)(?!\d)", re.I), "num"),
    # "ISS 1" alone
    (re.compile(r"\bISS\s*(\d+)\b", re.I), "num"),
    # "R1.35" firmware-style (check BEFORE v-pattern)
    (re.compile(r"\bR(\d+\.\d+)\b"), "r_firm"),
    # "V04", "v2.26", "v4", "V05"
    (re.compile(r"(?:^|[\s\-])[vV](\d+(?:\.\d+)?)\b"), "v"),
]

# MADT-style trailing "_NN" — matched on RAW stem (with underscores).
# Only fires when filename ends with letter+digits then "_NN" (optionally "_NN_N" for dup files).
_RE_MADT_TRAIL = re.compile(r"[A-Za-z]\d{2,}_(\d{2})(?:_\d+)?$")

# Trailing single-letter rev like "MCDT156_A" — lower priority fallback.
_RE_TRAILING_LETTER = re.compile(r"[A-Za-z]\d{2,}_([A-Z])$")


def _format_revision(raw: str, tag: str, extra: str | None = None) -> str:
    if tag == "iss_rev":
        return f"Iss {raw} Rev {extra}"
    if tag == "num":
        try:
            return str(int(raw))
        except ValueError:
            return raw
    if tag == "num_raw":
        return raw
    if tag == "v":
        try:
            return f"v{int(raw)}"
        except ValueError:
            return f"v{raw}"
    if tag == "r_firm":
        return f"R{raw}"
    if tag == "rev_raw":
        return f"Rev {raw}"
    return raw


def detect_revision(stem: str) -> str | None:
    s = _norm(stem)  # normalized for most patterns

    for pat, tag in _REVISION_PATTERNS:
        m = pat.search(s)
        if m:
            if tag == "iss_rev":
                return _format_revision(m.group(1), tag, m.group(2))
            return _format_revision(m.group(1), tag)

    # MADT trailing pattern — needs RAW stem (underscores)
    m = _RE_MADT_TRAIL.search(stem)
    if m:
        return m.group(1)  # preserve leading zeros ("03")

    # Trailing single letter fallback
    m = _RE_TRAILING_LETTER.search(stem)
    if m:
        letter = m.group(1)
        if letter not in ("E", "F", "G", "S", "P", "I", "D"):
            return f"Rev {letter}"
    return None


# ---------------------------------------------------------------------------
# Document family (normalized name with rev/date/lang/type stripped)
# ---------------------------------------------------------------------------
_FAMILY_STRIP = [
    re.compile(r"\.pdf$", re.I),
    # Rev/date tokens (apply to normalized, underscore→space stem)
    re.compile(r"\bRV\s*\d+\b", re.I),
    re.compile(r"\bRev\.?\s*[A-Z0-9\.]+\b", re.I),
    re.compile(r"(?:^|[^A-Za-z])rv\d{1,3}\b", re.I),
    re.compile(r"\bISS\s*\d+\b", re.I),
    re.compile(r"\bissue\s*\d+\b", re.I),
    re.compile(r"(?:^|[\s\-])[vV]\d+(?:\.\d+)?\b"),
    # Full dates
    _RE_DATE_DMY,
    _RE_DATE_COMPACT,
    _RE_DATE_TEXT,
    _RE_DATE_MY,
    # Language tags
    re.compile(rf"{_SEP}(?:ES|SP|Spanish|GB|Eng|English|FR|PT|Multi|multiling)(?:{_SEP_END}|(?=[A-Z][a-z]))", re.I),
    # Resolution tag (Detnov uses "lores")
    re.compile(r"\blores\b", re.I),
    # Trailing _N or  N duplicates ("MADT015_01_1" → strip _1)
    re.compile(r"[\s_]\d+$"),
]


def normalize_family(stem: str) -> str:
    out = _norm(stem)
    for pat in _FAMILY_STRIP:
        out = pat.sub(" ", out)
    out = re.sub(r"[\-\s]+", " ", out).strip()
    return out or stem


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def parse_revision(filename: str, first_pages_text: str = "") -> RevisionInfo:
    """Parse revision/date/lang/type from filename (+ optional first pages).

    Args:
        filename: PDF filename (with or without .pdf extension, with or
            without directory path).
        first_pages_text: concatenated text from the first ~2 pages of the
            PDF. Optional — only used as a fallback when filename alone is
            insufficient.

    Returns:
        RevisionInfo with best-effort fields. Any field may be None.
    """
    stem = Path(filename).name
    stem_noext = re.sub(r"\.pdf$", "", stem, flags=re.I)

    revision = detect_revision(stem_noext)
    revision_date = detect_date(stem_noext)
    language = detect_language(stem_noext)
    doc_type = detect_doc_type(stem_noext)

    # Fallback: scan first pages for a revision phrase if filename gave nothing
    if revision is None and first_pages_text:
        snippet = first_pages_text[:4000]
        m = re.search(
            r"(?:Revisi[oó]n|Revision|Rev\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\.]{0,6})\b",
            snippet,
            re.I,
        )
        if m:
            revision = f"Rev {m.group(1)}"

    family = normalize_family(stem_noext)

    return RevisionInfo(
        document_family=family,
        revision=revision,
        revision_date=revision_date,
        language=language,
        doc_type=doc_type,
    )
