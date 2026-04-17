"""
Language filter for multilingual PCI manuals.
Detects and filters content to keep only Spanish sections.

Supported marker styles:
- Short codes in page headers: "ESP", "ESPAÑOL", "FRA", "FRANÇAIS", "GBR",
  "ENGLISH", "ITA", "ITALIANO" (classic Detnov convention).
- Full-name markers embedded in slightly longer header blocks such as
  "ESPAÑOL. 12-15" or "INSTRUCCIONES DE INSTALACIÓN Y MANTENIMIENTO / ESPAÑOL"
  (Notifier / System Sensor convention, e.g. FAAST_XM_8100E_ML.pdf).
- Fallback: per-page function-word detection when no explicit marker appears
  (for multilingual docs where later pages omit the header marker).
"""

import re
from collections import Counter
from dataclasses import dataclass

from .pdf_parser import ParsedDocument, PageContent


# Language markers found in PCI manuals. Regex patterns are matched against
# the text of the first ~10 text blocks per page. Keep patterns specific enough
# to avoid false positives from prose (e.g. don't match "english" inside a
# body paragraph — require word boundaries and common uppercase variants).
#
# Includes the "DEUSTCH" typo observed in Notifier/System Sensor docs like
# FAAST_XM_8100E_ML where the fabricante mistyped "DEUTSCH".
LANG_MARKER_PATTERNS: dict[str, re.Pattern[str]] = {
    "es": re.compile(r"\b(ESP(?:AÑOL)?|CASTELLANO|SPANISH)\b", re.IGNORECASE),
    "en": re.compile(r"\b(GBR|ENGLISH|ANGLAIS|INGL[EÉ]S)\b", re.IGNORECASE),
    "fr": re.compile(r"\b(FRA(?:N[CÇ]AIS)?|FRANCAIS|FRENCH|FRANC[EÉ]S)\b", re.IGNORECASE),
    "it": re.compile(r"\b(ITA(?:LIANO)?|ITALIAN)\b", re.IGNORECASE),
    "de": re.compile(r"\b(DEUTSCH|DEUSTCH|ALEM[AÁ]N|GERMAN)\b", re.IGNORECASE),
    "pt": re.compile(r"\b(PORTUGU[EÊÉ]S|PORTUGUESE)\b", re.IGNORECASE),
    "ru": re.compile(r"\b(RUSSIAN|РУССКИЙ)\b", re.IGNORECASE),
}

# Max chars of a text block in which we'll still look for a marker. Headers
# like "1 / I56-3836-006 / ENGLISH. 12-15" are ~33 chars; full-name titles
# like "INSTRUCCIONES DE INSTALACIÓN Y MANTENIMIENTO / ESPAÑOL" are ~54.
# 100 is loose enough to cover both and tight enough to avoid body paragraphs.
MARKER_BLOCK_MAX_CHARS = 100
MARKER_BLOCKS_TO_SCAN = 10

# Short-code variants that double as ambiguous single-word blocks
# (e.g. "ES" or "FR" on a cover page). Matched via exact uppercase compare.
SHORT_MARKER_MAP = {
    "ES": "es", "ESP": "es", "ESPAÑOL": "es", "CASTELLANO": "es",
    "EN": "en", "GB": "en", "GBR": "en", "ENGLISH": "en",
    "FR": "fr", "FRA": "fr", "FRANÇAIS": "fr", "FRANCAIS": "fr",
    "IT": "it", "ITA": "it", "ITALIANO": "it",
    "DE": "de", "DEUTSCH": "de", "DEUSTCH": "de",
    "PT": "pt", "POR": "pt", "PORTUGUÊS": "pt", "PORTUGUES": "pt",
    "RU": "ru", "РУССКИЙ": "ru", "RUSSIAN": "ru",
}

# Function-word sets for per-page content-based language detection. Mirrors
# scripts/audit_chunk_languages.py so behaviour stays consistent between the
# ingestion-time filter and the post-hoc audit.
_CONTENT_FN_WORDS = {
    "es": {"el", "la", "de", "que", "y", "en", "un", "los", "se", "con",
           "por", "para", "del", "las", "es", "una", "al", "lo", "como", "pero",
           "sus", "le", "ha", "este", "esta", "son", "más"},
    "en": {"the", "of", "and", "to", "in", "is", "that", "for", "it", "with",
           "as", "was", "on", "be", "by", "are", "this", "from", "or", "an",
           "which", "have", "has", "been", "will", "not", "at"},
    "pt": {"de", "que", "do", "da", "em", "para", "não", "com", "por", "os",
           "uma", "na", "mais", "dos", "são", "ou", "das", "no", "se", "ao",
           "como", "mas", "foi", "ser", "pelo", "pela", "está"},
    "it": {"il", "di", "che", "la", "in", "un", "non", "per", "è", "una",
           "sono", "con", "si", "su", "da", "come", "al", "lo", "le", "ma",
           "anche", "questo", "nel", "della", "del", "gli", "ha"},
    "fr": {"le", "de", "la", "et", "à", "un", "les", "des", "en", "du",
           "est", "que", "pour", "une", "dans", "il", "au", "avec", "sur", "ne",
           "par", "pas", "plus", "ou", "son", "être", "ce"},
    "de": {"der", "die", "das", "und", "den", "von", "zu", "mit", "ist", "auf",
           "für", "im", "eine", "ein", "als", "sich", "auch", "sie", "an", "es",
           "nicht", "dem", "nach", "nur", "werden", "bei", "dass"},
}

# Words that are strongly indicative of ONE specific language — i.e. NOT shared
# with any other language in this set. Computed as the set difference of each
# _CONTENT_FN_WORDS entry against the union of all the others. These are the
# disambiguators: if a page has "não" or "uma" we know it's PT, if it has "the"
# or "with" it's EN, etc. Overlapping words (de/que/para, shared across
# ES/PT/FR/IT) are deliberately excluded here and only used in the stage-2
# fallback. Without this separation a PT page scores only ~1.3x over ES (both
# romance, heavy function-word overlap) and gets rejected as ambiguous.
_CONTENT_STRONG_MARKERS = {
    "es": {"el", "esta", "este", "las", "los", "más", "pero", "sus", "y"},
    "en": {"and", "are", "as", "at", "be", "been", "by", "for", "from", "has",
           "have", "is", "it", "not", "of", "on", "or", "that", "the", "this",
           "to", "was", "which", "will", "with"},
    "pt": {"ao", "com", "do", "dos", "em", "está", "foi", "mais", "mas", "na",
           "no", "não", "os", "pela", "pelo", "ser", "são", "uma"},
    "it": {"anche", "che", "come", "della", "di", "gli", "ma", "nel", "non",
           "per", "questo", "si", "sono", "su", "è"},
    "fr": {"au", "avec", "ce", "dans", "des", "du", "est", "et", "les", "ne",
           "par", "pas", "plus", "pour", "sur", "une", "à", "être"},
    "de": {"als", "auch", "auf", "bei", "dass", "dem", "den", "der", "die",
           "ein", "eine", "für", "im", "ist", "mit", "nach", "nicht", "nur",
           "sich", "sie", "und", "von", "werden", "zu"},
}
_WORD_RE = re.compile(r"[a-zA-ZÀ-ÿ]+")  # Latin + Latin-1 Supplement (covers ã, ñ, ç, ê, é, ö, ß, ...)

# Min content-detection confidence: winner / runner_up must clear this ratio.
_CONTENT_MIN_RATIO = 1.5
# Min tokens for content detection to be reliable; below this we return None.
_CONTENT_MIN_TOKENS = 30

# Kept for backward compatibility — used in the global fallback when NO page
# carries a marker AND content detection is also inconclusive. Signals that
# the doc is likely a Spanish-only Detnov manual (no multilingual structure).
SPANISH_INDICATORS = re.compile(
    r"\b(instalación|conexión|conexionado|detección|manual|detector|central|"
    r"alimentación|batería|sirena|pulsador|configuración|mantenimiento|"
    r"especificaciones|técnicas|montaje|cableado|bucle|zona|alarma|avería|"
    r"fuego|incendio|extinción|evacuación|módulo|tarjeta|tensión|corriente|"
    r"programación|descripción|precaución|advertencia|importante|nota)\b",
    re.IGNORECASE,
)


@dataclass
class LanguageSection:
    """A section of pages in a specific language."""
    language: str  # "es", "en", "fr", "it", "unknown"
    start_page: int
    end_page: int


def _detect_page_language_by_content(page: PageContent) -> str | None:
    """Content-based fallback: score a page by function-word frequency.

    Reads page.full_text first (PyMuPDF native extraction). If that's empty
    or too short — typical for scanned PDFs where text only appears after
    Claude Vision processing — falls back to page.vision_text. This matters
    because in the ingestion pipeline, filter_spanish_pages runs AFTER
    enrich_with_vision, so vision_text is populated by then.

    Scoring is two-stage (mirrors scripts/audit_chunk_languages.py):
      1. STRONG_MARKERS pass — words unique to one language. This is the
         primary signal; heavy-overlap words (de/que/para, shared across
         ES/PT/FR/IT) are excluded so they don't dilute the ratio.
      2. If strong markers are zero for every language (rare: very short
         page, mostly numbers/codes), fall back to the full function-word set.

    Returns the winner language if it clears _CONTENT_MIN_RATIO over the
    runner-up; otherwise None (ambiguous). None is preferred over a guess —
    ambiguous pages are handled by the surrounding section logic.
    """
    text = (page.full_text or "").strip()
    if len(text) < 100:
        # Fallback for scanned docs: use Vision-extracted text
        text = (page.vision_text or "").strip()
    if len(text) < 100:
        return None
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if len(words) < _CONTENT_MIN_TOKENS:
        return None
    counter = Counter(words)

    # Stage 1: strong markers (disambiguators)
    strong_scores = {lang: sum(counter[w] for w in markers)
                     for lang, markers in _CONTENT_STRONG_MARKERS.items()}
    best_lang = max(strong_scores, key=strong_scores.get)
    best = strong_scores[best_lang]
    runner = max((s for k, s in strong_scores.items() if k != best_lang),
                 default=0)

    if best > 0:
        # Additive smoothing so we don't divide by ~0 when runner is tiny.
        if best >= (runner + 1) * _CONTENT_MIN_RATIO:
            return best_lang
        # Strong-marker winner is ambiguous; don't fall back to full set
        # (would just reintroduce the overlap problem we're trying to solve).
        return None

    # Stage 2: no strong markers matched. Try full function-word set.
    full_scores = {lang: sum(counter[w] for w in fn)
                   for lang, fn in _CONTENT_FN_WORDS.items()}
    best_lang = max(full_scores, key=full_scores.get)
    best = full_scores[best_lang]
    if best == 0:
        return None
    runner = max((s for k, s in full_scores.items() if k != best_lang),
                 default=0)
    if best >= (runner + 1) * _CONTENT_MIN_RATIO:
        return best_lang
    return None


def _detect_page_language_marker(page: PageContent) -> str | None:
    """Detect the language marker on a page, with progressive fallbacks.

    Strategy (in order):
      1. Scan the first N text blocks for a regex match against known
         language names (ESPAÑOL, ENGLISH, FRANÇAIS, DEUTSCH / DEUSTCH typo,
         ITALIANO, PORTUGUÊS, РУССКИЙ). Works for both short headers like
         "ENGLISH. 12-15" and longer titles like
         "INSTRUCCIONES ... / ESPAÑOL".
      2. Also accept short single-word blocks using the legacy SHORT_MARKER_MAP
         (covers classic Detnov headers: "ES", "FR", "GB", "IT").
      3. If the markers found on the page are unambiguous (all the same
         language), return that language.
      4. If markers on the page conflict (e.g. a cover page listing ES/FR/GB/IT
         together), return None as ambiguous — do NOT guess from markers.
      5. If no markers at all, fall through to content-based detection on the
         page's full_text. Returns None if the page is too short or too
         ambiguous in content.
    """
    markers: list[str] = []
    for block in page.text_blocks[:MARKER_BLOCKS_TO_SCAN]:
        text = (block.text or "").strip()
        if not text or len(text) > MARKER_BLOCK_MAX_CHARS:
            continue
        upper = text.upper()
        # (2) Short single-word exact match (cover pages with just "ES" etc.)
        if upper in SHORT_MARKER_MAP:
            markers.append(SHORT_MARKER_MAP[upper])
            continue
        # (1) Regex search across all configured language patterns.
        # One language hit per block (first match wins).
        for lang, pat in LANG_MARKER_PATTERNS.items():
            if pat.search(upper):
                markers.append(lang)
                break

    if markers:
        unique = set(markers)
        # (3) unambiguous — single language
        if len(unique) == 1:
            return unique.pop()
        # (4) conflicting markers (cover pages, TOC listing all languages): ambiguous
        return None

    # (5) no markers at all on this page — content-based fallback
    return _detect_page_language_by_content(page)


def detect_language_sections(parsed: ParsedDocument) -> list[LanguageSection]:
    """Detect language boundaries in a multilingual PDF.

    Strategy:
    1. Check per-page language markers (ES, FR, GB, IT headers)
    2. Track when marker changes → language section boundary
    3. For pages without markers, inherit from previous page
    4. If no markers at all, use content-based detection
    """
    # First pass: detect language per page
    page_langs = {}
    for page in parsed.pages:
        lang = _detect_page_language_marker(page)
        if lang:
            page_langs[page.page_number] = lang

    # If we got good per-page detection, build sections from transitions
    if page_langs:
        sections = []
        current_lang = "unknown"
        current_start = 1

        for page in parsed.pages:
            pn = page.page_number
            detected = page_langs.get(pn)

            if detected and detected != current_lang:
                # Language changed
                if current_start <= pn - 1 and current_lang != "unknown":
                    sections.append(LanguageSection(
                        language=current_lang,
                        start_page=current_start,
                        end_page=pn - 1,
                    ))
                elif current_lang == "unknown" and current_start < pn:
                    # Initial pages before first marker
                    sections.append(LanguageSection(
                        language=detected,  # Assume same as first detected
                        start_page=current_start,
                        end_page=pn - 1,
                    ))
                current_lang = detected
                current_start = pn

        # Final section
        if parsed.pages:
            sections.append(LanguageSection(
                language=current_lang if current_lang != "unknown" else "es",
                start_page=current_start,
                end_page=parsed.pages[-1].page_number,
            ))

        # Merge initial unknown section with first detected language
        if sections and sections[0].language == "unknown" and len(sections) > 1:
            sections[0].language = sections[1].language

        return sections if sections else [LanguageSection("unknown", 1, parsed.total_pages)]

    # Fallback: no per-page markers found. Use content-based detection.
    # Check if the whole document is Spanish by content
    full_text = " ".join(p.full_text[:300] for p in parsed.pages[:10])
    spanish_matches = len(SPANISH_INDICATORS.findall(full_text))

    lang = "es" if spanish_matches >= 3 else "unknown"
    return [LanguageSection(lang, 1, parsed.total_pages)]


def filter_spanish_pages(parsed: ParsedDocument) -> list[PageContent]:
    """Return only pages that are in Spanish.

    Policy for 'unknown' sections:
      - If the document has at least one section in a non-ES language,
        'unknown' pages are assumed to belong to an adjacent non-ES section
        (common case: table/schematic page with no prose, sandwiched between
        EN pages). They are DROPPED.
      - If the document has no detected non-ES language at all (either all ES,
        or entirely inscrutable — scanned with no Vision text, pure schematic,
        etc.), 'unknown' pages are kept. This preserves the original
        Detnov-mono-idioma behaviour where the filter opens fail-safe.
    """
    sections = detect_language_sections(parsed)
    has_non_es_lang = any(
        s.language not in ("es", "unknown") for s in sections
    )

    spanish_pages: set[int] = set()
    for section in sections:
        if section.language == "es":
            for pn in range(section.start_page, section.end_page + 1):
                spanish_pages.add(pn)
        elif section.language == "unknown" and not has_non_es_lang:
            # Legacy fallback: homogeneous / unrecognizable doc → keep pages
            for pn in range(section.start_page, section.end_page + 1):
                spanish_pages.add(pn)

    return [
        page for page in parsed.pages
        if page.page_number in spanish_pages
    ]


def is_single_language_spanish(parsed: ParsedDocument) -> bool:
    """Quick check: is this document entirely in Spanish (no multilingual sections)?"""
    sections = detect_language_sections(parsed)
    return len(sections) == 1 and sections[0].language == "es"


if __name__ == "__main__":
    import sys
    from .pdf_parser import parse_pdf

    if len(sys.argv) < 2:
        print("Usage: python -m src.ingestion.language_filter <pdf_path>")
        sys.exit(1)

    parsed = parse_pdf(sys.argv[1])
    sections = detect_language_sections(parsed)

    print(f"Document: {parsed.file_name}")
    print(f"Total pages: {parsed.total_pages}")
    print(f"Language sections detected: {len(sections)}")
    for s in sections:
        print(f"  [{s.language}] pages {s.start_page}-{s.end_page}")

    spanish = filter_spanish_pages(parsed)
    print(f"\nSpanish pages: {len(spanish)} / {parsed.total_pages}")
