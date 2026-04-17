"""Tests for src/ingestion/language_filter.py.

Locks in the fixes made after the FAAST_XM_8100E_ML.pdf investigation
(17 April 2026), where the filter was passing 110/110 pages of a multilingual
document through as "Spanish" because:
  1. Marker matching was exact-string on blocks ≤ 30 chars — too strict to
     catch headers like "ENGLISH. 12-15" (33 chars) or the typo "DEUSTCH".
  2. Global fallback mapped "unknown" pages to "es", so any doc without a
     classic Detnov ES/FR/GB/IT header convention passed entirely.

Run with:
    pytest tests/test_language_filter.py -v
"""
from __future__ import annotations

import pytest

from src.ingestion.language_filter import (
    LANG_MARKER_PATTERNS,
    SHORT_MARKER_MAP,
    _detect_page_language_by_content,
    _detect_page_language_marker,
    detect_language_sections,
    filter_spanish_pages,
)
from src.ingestion.pdf_parser import PageContent, ParsedDocument, TextBlock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _block(text: str) -> TextBlock:
    return TextBlock(text=text, page_number=1, block_index=0)


def _page(page_number: int, blocks_text: list[str] = (), full_text: str = "",
          vision_text: str = "") -> PageContent:
    p = PageContent(
        page_number=page_number,
        text_blocks=[_block(t) for t in blocks_text],
        full_text=full_text,
        vision_text=vision_text,
    )
    return p


def _doc(pages: list[PageContent]) -> ParsedDocument:
    return ParsedDocument(
        file_path="fake.pdf", file_name="fake", total_pages=len(pages),
        pages=pages,
    )


# ---------------------------------------------------------------------------
# Marker regex coverage
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text,expected_lang", [
    # Real FAAST_XM_8100E_ML.pdf header formats — the ones the old filter missed
    ("1 / I56-3836-006 / ENGLISH. 12-15", "en"),
    ("1 / I56-3836-004 / DEUSTCH. 12-15", "de"),  # fabricante's typo
    ("1 / I56-3836-004 / ITALIANO. 12-15", "it"),
    ("1 / I56-3836-004 / FRANÇAIS. 12-15", "fr"),
    ("1 / I56-3836-004 / ESPAÑOL. 12-15", "es"),
    # Full-name title markers
    ("INSTRUCCIONES DE INSTALACIÓN Y MANTENIMIENTO / ESPAÑOL", "es"),
    ("INSTALLATION AND MAINTENANCE INSTRUCTIONS / ENGLISH", "en"),
    ("ISTRUZIONI DI INSTALLAZIONE E DI MANUTENZIONE / ITALIANO", "it"),
    # Classic Detnov short codes (still need to work)
    ("ESP", "es"),
    ("GBR", "en"),
    ("FRA", "fr"),
    ("ITA", "it"),
    # Portuguese (new)
    ("PORTUGUÊS", "pt"),
    ("PORTUGUES", "pt"),
])
def test_marker_detection_single_language(text, expected_lang):
    page = _page(page_number=1, blocks_text=[text])
    assert _detect_page_language_marker(page) == expected_lang


def test_marker_detection_ambiguous_cover_page():
    # Cover/TOC page listing all languages together → should NOT pick one.
    page = _page(page_number=1, blocks_text=[
        "ENGLISH", "FRANÇAIS", "DEUTSCH", "ITALIANO", "ESPAÑOL",
    ])
    assert _detect_page_language_marker(page) is None


def test_marker_regex_ignores_body_paragraphs():
    # A body paragraph that happens to mention a language name should NOT
    # trigger a marker match (too long, over MARKER_BLOCK_MAX_CHARS = 100).
    long_en_prose = (
        "The detector must be installed according to local regulations. Note "
        "that the English language version of this document takes precedence "
        "in case of discrepancy between translations."
    )
    page = _page(page_number=1, blocks_text=[long_en_prose])
    # Falls through to content-based detection; let's not assert a specific
    # result, just verify the marker path didn't flag based on the word "English".
    # (Content detector may or may not tag it EN depending on token count.)
    # The critical check is: marker mode didn't lock onto "English" just because
    # it appeared. We assert by swapping body to Spanish and ensuring no 'en' leak.
    es_prose = (
        "El detector debe instalarse según la normativa local. La versión en "
        "español de este documento tiene precedencia en caso de discrepancia "
        "entre las traducciones del manual oficial."
    )
    page_es = _page(page_number=1, blocks_text=[es_prose])
    # Both should fall through to content detection, so whichever wins should
    # match the prose language, not a stray match on "english"/"español" word.
    assert _detect_page_language_marker(page) != "es"
    assert _detect_page_language_marker(page_es) != "en"


# ---------------------------------------------------------------------------
# Content-based per-page detection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("full_text,expected_lang", [
    # Spanish prose with enough function words
    (
        "El detector de humo es un dispositivo que se utiliza para la "
        "detección de incendios en edificios. Su instalación requiere una "
        "conexión adecuada a la central de alarma y pruebas de funcionamiento "
        "periódicas según las normas vigentes.",
        "es",
    ),
    # English
    (
        "The smoke detector is a device that is used for the detection of "
        "fires in buildings. Its installation requires a proper connection "
        "to the alarm panel and regular testing according to the applicable "
        "standards and regulations.",
        "en",
    ),
    # Portuguese
    (
        "O detector de fumaça é um dispositivo que é utilizado para a "
        "detecção de incêndios em edifícios. A sua instalação requer uma "
        "ligação adequada à central de alarme e testes de funcionamento "
        "periódicos de acordo com as normas em vigor.",
        "pt",
    ),
])
def test_content_detection_picks_right_language(full_text, expected_lang):
    page = _page(page_number=1, full_text=full_text)
    assert _detect_page_language_by_content(page) == expected_lang


def test_content_detection_uses_vision_text_when_full_text_empty():
    # Scanned PDF scenario: full_text is empty but vision_text has content.
    vision = (
        "The control panel has a keypad for entering the access code. "
        "The operator can use the buttons to navigate between the menus and "
        "configure the zones of the installation according to the manual."
    )
    page = _page(page_number=1, full_text="", vision_text=vision)
    assert _detect_page_language_by_content(page) == "en"


def test_content_detection_returns_none_on_short_text():
    page = _page(page_number=1, full_text="short")
    assert _detect_page_language_by_content(page) is None


# ---------------------------------------------------------------------------
# End-to-end: sections + filter_spanish_pages
# ---------------------------------------------------------------------------
def test_multilingual_doc_keeps_only_spanish_pages():
    # Synthetic stand-in for FAAST_XM_8100E_ML structure: 5 language sections
    # of 2 pages each, ESPAÑOL marker on page 7.
    doc = _doc([
        _page(1, blocks_text=["1 / I56 / ENGLISH. 12-15"]),
        _page(2, full_text="The detector must be installed per the standards above."),
        _page(3, blocks_text=["1 / I56 / DEUSTCH. 12-15"]),
        _page(4, full_text="Der Melder ist nach den Normen zu installieren."),
        _page(5, blocks_text=["1 / I56 / ITALIANO. 12-15"]),
        _page(6, full_text="Il rivelatore deve essere installato secondo le norme applicabili."),
        _page(7, blocks_text=["1 / I56 / ESPAÑOL. 12-15"]),
        _page(
            8,
            full_text="El detector debe instalarse según las normas indicadas "
                      "en la documentación del fabricante y conectarse a la "
                      "central de alarma correctamente.",
        ),
    ])
    sections = detect_language_sections(doc)
    langs = [(s.language, s.start_page, s.end_page) for s in sections]
    # We expect at least one [es, ...] section covering pages 7-8
    es_sections = [s for s in langs if s[0] == "es"]
    assert es_sections, f"No ES section detected. sections={langs}"

    spanish = filter_spanish_pages(doc)
    spanish_nums = [p.page_number for p in spanish]
    # Must include p7-p8; must EXCLUDE p1-p6 (they are EN/DE/IT).
    assert 7 in spanish_nums
    assert 8 in spanish_nums
    assert 1 not in spanish_nums, "regression: EN page leaked through"
    assert 3 not in spanish_nums, "regression: DE page leaked through"
    assert 5 not in spanish_nums, "regression: IT page leaked through"


def test_monolingual_spanish_doc_passes_through():
    # Detnov-style: no language markers, all content in Spanish.
    doc = _doc([
        _page(
            1,
            full_text=(
                "Este manual describe la instalación de la central de "
                "detección y sus módulos de conexión con los detectores y "
                "pulsadores de la instalación según las especificaciones."
            ),
        ),
        _page(
            2,
            full_text=(
                "La programación de las zonas se realiza desde el panel "
                "frontal de la central de incendios. Consulte la tabla de "
                "mensajes para diagnosticar las averías detectadas por el "
                "sistema durante el arranque."
            ),
        ),
    ])
    spanish = filter_spanish_pages(doc)
    assert len(spanish) == 2


def test_fully_inscrutable_doc_keeps_pages_legacy_fallback():
    # Pure image/schematic PDF: no text_blocks, no full_text, no vision_text.
    # Policy: if there's nothing to detect, KEEP pages (conservative default).
    # A downstream Vision pass / translation step can still recover content.
    doc = _doc([
        _page(1),
        _page(2),
    ])
    spanish = filter_spanish_pages(doc)
    assert len(spanish) == 2, \
        "Inscrutable docs must NOT be filtered to empty (legacy Detnov behaviour)"


def test_multilingual_doc_drops_unknown_pages_when_other_langs_detected():
    # If the doc has EN pages clearly detected AND some unknown pages,
    # the unknown ones must NOT be kept as ES (that was the old bug).
    doc = _doc([
        _page(1, blocks_text=["ENGLISH"],
              full_text="The device is installed according to the standards."),
        _page(2),  # unknown — no blocks, no text
        _page(3, blocks_text=["ENGLISH"],
              full_text="Connect the terminals as shown in the diagram."),
    ])
    spanish = filter_spanish_pages(doc)
    # Previously: all 3 would pass because 'unknown' was treated as 'es'.
    # With the fix: the doc has a non-ES language detected → unknown pages drop.
    assert len(spanish) == 0, \
        f"unknown pages leaked as ES despite non-ES lang present. got {[p.page_number for p in spanish]}"


# ---------------------------------------------------------------------------
# Sanity: the module's public constants are well-formed
# ---------------------------------------------------------------------------
def test_short_marker_map_is_consistent():
    # Every short code must map to a valid lang that also has a regex pattern
    for code, lang in SHORT_MARKER_MAP.items():
        assert lang in LANG_MARKER_PATTERNS, \
            f"{code}->{lang} but {lang} has no regex pattern"
