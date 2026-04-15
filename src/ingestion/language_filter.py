"""
Language filter for multilingual Detnov manuals.
Detects and filters content to keep only Spanish sections.

Detnov manuals typically have language sections marked by:
- Headers like "ESP", "ESPAÑOL", "FRA", "FRANÇAIS", "GBR", "ENGLISH", "ITA", "ITALIANO"
- Or the entire document is single-language (Spanish)
"""

import re
from dataclasses import dataclass

from .pdf_parser import ParsedDocument, PageContent


# Language markers found in Detnov manuals
SPANISH_MARKERS = re.compile(
    r"\b(ESP(AÑOL)?|CASTELLANO|ESPAÑOL)\b", re.IGNORECASE
)
NON_SPANISH_MARKERS = re.compile(
    r"\b(FRA(NÇAIS)?|FRANÇAIS|GBR|ENGLISH|ANGLAIS|ITA(LIANO)?|DEUTSCH|GERMAN|RUSSIAN|РУССКИЙ)\b",
    re.IGNORECASE,
)

# Common Spanish words to detect language by content
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


def _detect_page_language_marker(page: PageContent) -> str | None:
    """Detect the language marker on a page by checking short text blocks.

    Many Detnov manuals have a recurring header on each page like "ES", "FR", "GB", "IT".
    The key insight: we need to check which marker appears WITHOUT the others on the same page.
    On cover pages, all markers may appear together — those are ambiguous.
    """
    short_markers = []
    for block in page.text_blocks[:8]:
        text = block.text.strip()
        if len(text) > 30:
            continue

        upper = text.upper()
        if upper in ("ES", "ESP", "ESPAÑOL", "CASTELLANO"):
            short_markers.append("es")
        elif upper in ("FR", "FRA", "FRANÇAIS", "FRANCAIS"):
            short_markers.append("fr")
        elif upper in ("GB", "GBR", "EN", "ENGLISH"):
            short_markers.append("en")
        elif upper in ("IT", "ITA", "ITALIANO"):
            short_markers.append("it")
        elif upper in ("DE", "DEUTSCH"):
            short_markers.append("de")
        elif upper in ("RU", "РУССКИЙ", "RUSSIAN"):
            short_markers.append("ru")

    if not short_markers:
        return None

    # If only one language marker found, that's the page language
    unique = set(short_markers)
    if len(unique) == 1:
        return unique.pop()

    # Multiple markers on the same page (e.g., cover page with ES/FR/GB/IT)
    # Consider this ambiguous — don't assign
    return None


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
    """Return only pages that are in Spanish."""
    sections = detect_language_sections(parsed)

    # Collect page numbers that are Spanish
    spanish_pages = set()
    for section in sections:
        if section.language in ("es", "unknown"):
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
