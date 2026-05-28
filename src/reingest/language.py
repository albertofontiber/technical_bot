"""Etapa B1/B2 del pipeline de re-ingesta — detección de idioma y política.

B1 — detección de idioma con `lingua` (detector estadístico robusto), no con
heurística de función-palabra. El detector se restringe a los 6 idiomas que
aparecen en el corpus PCI (ES/EN/FR/IT/PT/DE): acotar el espacio sube la
precisión y la velocidad frente al detector de 75 idiomas por defecto.

B2 — política de idiomas. Se INDEXA el contenido es/en; el contenido pt/fr/it/de
se REGISTRA (se anota que la fuente existe) pero no se indexa. La decisión es
por chunk (un manual "ES FR GB IT" tiene páginas de cada idioma); un documento
sin ninguna página indexable se marca register_only a nivel de documento.

Uso típico:
    from src.reingest.language import detect_language, profile_document
    lang = detect_language(chunk_text)          # etiqueta de un chunk (B1)
    prof = profile_document(extraction_record)  # veredicto del documento (B2)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from lingua import Language, LanguageDetectorBuilder

# --- Política B2 -------------------------------------------------------------
# Idiomas que se indexan. 'es' es el objetivo; 'en' se acepta como fallback
# (mucha documentación de fabricantes especiales solo existe en inglés). El
# resto se registra sin indexar — ver docs/PLAN_RAG_2026.md §Fase 1, decisión 3.
INDEXABLE_LANGUAGES: frozenset[str] = frozenset({"es", "en"})

# Idiomas del corpus PCI. Restringir el detector a este conjunto.
_CORPUS_LANGUAGES = [
    Language.SPANISH, Language.ENGLISH, Language.FRENCH,
    Language.ITALIAN, Language.PORTUGUESE, Language.GERMAN,
]

# Por debajo de este nº de caracteres de prosa, lingua no es fiable: la página
# es una portada / esquema / tabla sin texto narrativo → 'unknown'.
_MIN_CHARS_FOR_DETECTION = 40

_detector = None


def _get_detector():
    """Singleton perezoso — construir el detector carga modelos (~1-2 s)."""
    global _detector
    if _detector is None:
        _detector = LanguageDetectorBuilder.from_languages(*_CORPUS_LANGUAGES).build()
    return _detector


# --- Limpieza de markdown ----------------------------------------------------
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_IMG_DESC = re.compile(r"\[Image[^\]]*\]", re.IGNORECASE)  # descripciones VLM (en inglés)
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_SYNTAX = re.compile(r"[#>*_`|\-]+")
_WS = re.compile(r"\s+")


def _strip_markdown(md: str) -> str:
    """Reduce markdown a prosa para el detector.

    Quita fences de código, sintaxis de tabla/header y — deliberadamente — las
    descripciones de imagen `[Image shows ...]` que LlamaParse inserta SIEMPRE
    en inglés: dejarlas sesgaría hacia 'en' una página por lo demás española.
    """
    text = _CODE_FENCE.sub(" ", md)
    text = _IMG_DESC.sub(" ", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_SYNTAX.sub(" ", text)
    return _WS.sub(" ", text).strip()


def detect_language(text: str) -> str:
    """Idioma dominante de un span de texto (chunk, bloque o página).

    Devuelve un código ISO-639-1 en minúsculas ('es', 'en', 'fr', 'it', 'pt',
    'de') o 'unknown' si el texto es demasiado corto o el detector no decide.
    """
    prose = _strip_markdown(text)
    if len(prose) < _MIN_CHARS_FOR_DETECTION:
        return "unknown"
    lang = _get_detector().detect_language_of(prose)
    if lang is None:
        return "unknown"
    return lang.iso_code_639_1.name.lower()


def is_indexable(language: str) -> bool:
    """B2 — ¿se indexa contenido en este idioma?"""
    return language in INDEXABLE_LANGUAGES


@dataclass
class DocLanguageProfile:
    """Perfil de idioma de un documento extraído (veredicto B2)."""
    page_language: dict[int, str] = field(default_factory=dict)
    languages_present: set[str] = field(default_factory=set)
    dominant: str = "unknown"
    verdict: str = "index"  # 'index' | 'register_only'

    @property
    def indexable(self) -> bool:
        return self.verdict == "index"


def _pages_from_record(extraction_record: dict) -> list[tuple[int, str]]:
    """(page_number, markdown) de cada página del JSON de extracción."""
    pages = extraction_record.get("result", {}).get("pages", [])
    out = []
    for p in pages:
        out.append((p.get("page"), p.get("md") or p.get("text") or ""))
    return out


def profile_document(extraction_record: dict) -> DocLanguageProfile:
    """Analiza el idioma de un documento extraído y emite el veredicto B2.

    - Detecta el idioma de cada página.
    - Las páginas 'unknown' (portadas, esquemas) heredan el idioma de la página
      previa conocida — son páginas sin prosa, no de un idioma distinto.
    - verdict='index' si hay ≥1 página es/en; 'register_only' si el documento
      es íntegramente pt/fr/it/de.
    - Caso degenerado (todas las páginas 'unknown' — escaneado ilegible): se
      asume 'es' y se indexa (fail-safe: el corpus es ~66% ES; mejor indexar y
      que un humano lo revise que descartar en silencio).
    """
    prof = DocLanguageProfile()
    pages = _pages_from_record(extraction_record)

    raw: dict[int, str] = {}
    for page_num, md in pages:
        if page_num is None:
            continue
        raw[page_num] = detect_language(md)

    # Relleno de 'unknown' por herencia de la página previa conocida.
    last_known = "unknown"
    for page_num in sorted(raw):
        lang = raw[page_num]
        if lang == "unknown":
            prof.page_language[page_num] = last_known
        else:
            prof.page_language[page_num] = lang
            last_known = lang
    # Páginas iniciales 'unknown' antes del primer idioma conocido: relleno
    # hacia atrás con el primer idioma que aparezca.
    if last_known != "unknown":
        for page_num in sorted(prof.page_language):
            if prof.page_language[page_num] == "unknown":
                prof.page_language[page_num] = last_known
            else:
                break

    prof.languages_present = {l for l in prof.page_language.values() if l != "unknown"}

    if not prof.languages_present:
        # Documento íntegramente ilegible — fail-safe: asumir ES e indexar.
        prof.dominant = "es"
        prof.verdict = "index"
        return prof

    prof.dominant = max(
        prof.languages_present,
        key=lambda l: sum(1 for v in prof.page_language.values() if v == l),
    )
    prof.verdict = (
        "index" if prof.languages_present & INDEXABLE_LANGUAGES else "register_only"
    )
    return prof
