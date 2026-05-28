"""Etapa B5 del pipeline de re-ingesta — detección de metadata.

Esto es la INTERFAZ de metadata: una función `detect_document_metadata()` y un
`apply_metadata()` con un nombre y contrato estables. La implementación de Fase 1
es deliberadamente compacta (regex de modelo + mapa de prefijos de fabricante).

La Fase 2 del PLAN_RAG_2026 externaliza las reglas a config/manufacturers/*.yaml
SIN tocar a los llamadores: solo cambia el cuerpo de las funciones de detección.
Por eso las tablas hardcodeadas de abajo están marcadas como seam de Fase 2.

Campos:
  - manufacturer, product_model, doc_type, category → nivel DOCUMENTO (una vez).
  - content_type → nivel CHUNK (depende del contenido del chunk).
  - protocol → no se detecta en Fase 1; la columna queda NULL.

Uso:
    from src.reingest.metadata import detect_document_metadata, apply_metadata
    meta = detect_document_metadata(record["source_path"], text_sample)
    apply_metadata(chunks, meta)
"""
from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass

# === SEAM DE FASE 2 — estas tablas se externalizan a YAML ====================
#
# Verdad por producto: marca REAL (la del datasheet) y, cuando difiere,
# distribuidor (canal por el que llega a Fontiber). Mapeo cerrado con Alberto
# a partir de los datasheets de detnov.com para todo el tail de detectores
# especiales — Securiton (ASD/ADW/ART), Pfannenberg (PA/DS/PY-X), Argus
# Security (SG*), Pepperl-Fuchs (Z728), Xtralis (VESDA), Spectrex (40-40/
# 20-20) y SenseWare (210-Series).
#
# La reconciliación del retriever con esta distinción (su MODEL_PATTERN
# clasifica hoy ASD como Detnov) sigue siendo Fase 2 por diseño — aquí se
# captura el DATO en chunks_v2 para no tener que volver a tocar el corpus.

# (1) Patrones específicos por familia de modelo de marcas distribuidas.
#     Se evalúan ANTES que la detección genérica: un Z728 es Pepperl-Fuchs,
#     no un Z-200-R (zócalo Detnov). Cada entrada: (regex, marca, distribuidor).
_BRAND_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Securiton — aspiración y térmica lineal rearmable.
    # Sufijo de letras acotado (no \w* — engulle "_TD_T131192ES_H" entero);
    # negative lookahead a más dígitos para no comer códigos largos.
    (re.compile(r"\b(ASD-?\d{2,4}[A-Z]{0,3})(?!\d)", re.I),   "Securiton",     "Detnov"),
    (re.compile(r"\b(ADW-?\d{2,4}[A-Z]{0,3})(?!\d)", re.I),   "Securiton",     "Detnov"),
    (re.compile(r"\b(ART-?\d{2,4}[A-Z]{0,3})(?!\d)", re.I),   "Securiton",     "Detnov"),
    # Xtralis — VESDA (Honeywell lo comercializa bajo Notifier).
    # Estructura real: VESDA[-E][-VLF/VLP/VLS/VEA/VEP/...].
    (re.compile(
        r"\b(VESDA(?:[-\s]?E)?(?:[-\s]?(?:VL[FIPS]|VE[APUS])\w{0,6})?)",
        re.I), "Xtralis", "Notifier"),
    # Pfannenberg — sirenas/flashes industriales.
    # Crítico el (?!\d): evita que "DS-000" en metadata interna se infle a
    # "DS-00000-00" (visto en MADT951 = Notifier, falso positivo previo).
    (re.compile(r"\b(PA-?\d{1,3}[A-Z]{0,3})(?!\d)", re.I),    "Pfannenberg",   "Detnov"),
    (re.compile(r"\b(DS-?\d{1,3}[A-Z]{0,3})(?!\d)", re.I),    "Pfannenberg",   "Detnov"),
    (re.compile(
        r"\b(PY[-\s]?X[-\s]?[A-Z]?(?:-\d{1,3}){0,2})", re.I), "Pfannenberg",   "Detnov"),
    # Argus Security — detectores vía radio.
    (re.compile(
        r"\b(SG(?:CP|FI|MI|MCB|WE)?\d{2,3}(?:-IS)?)\b",
        re.I), "Argus Security", "Detnov"),
    # Pepperl-Fuchs — Z728 estricto (Z-200-R de Detnov NO debe caer aquí).
    # Permite continuación con _ o número (sufijos de archivo) pero no letras.
    (re.compile(r"\b(Z728)(?![A-Za-z])", re.I),               "Pepperl-Fuchs", "Detnov"),
    # Spectrex / Emerson — SharpEye 40-40 y 20-20.
    # Permite letra directa (40-40R) o letra tras separador (40-40-series),
    # con sufijo acotado a 3-8 chars (códigos reales: R, ML, MI, LB, D-I,
    # ML-S, R-SINGLE-IR no — eso es ruido del filename, cap a 8).
    (re.compile(
        r"\b((?:40[-/]?40|20[-/]?20)[-\s]?[A-Z][A-Z0-9-]{0,7})(?=[-\s_]|$)",
        re.I), "Spectrex", "Detnov"),
    # SenseWare — 210-Series UV/IR. Requiere "-<dígito>?<letras>" tras 210
    # para no casar "210V"/"210mA" sueltos.
    (re.compile(r"\b(210-\d?[A-Z]+(?:-[A-Z]+)?)", re.I),      "SenseWare",     "Detnov"),
]

# Patrones a aplicar SOLO al FILENAME, NO al content. Para códigos cortos /
# ambiguos que aparecen frecuentemente como referencia (no como sujeto del doc):
# UCIP-Tabla-compatibilidad MENCIONA "DXc"/"B501" en el content, pero el doc es
# ABOUT UCIP. Filtrar a filename evita marcar el doc como DXc por una mención.
_FILENAME_ONLY_PATTERNS: list[tuple[re.Pattern, str, str | None]] = [
    # Notifier B5xx (B501, B524, B501RF, B501BH).
    (re.compile(r"\b(B5\d{2}[A-Z]{0,4})\b", re.I),            "Notifier",       None),
]

# Modelos puros-letras o letter-suffix-sin-dígitos significativos.
# El _MODEL_RE genérico requiere letras+dígitos y no detecta estos. Match exacto
# por word-boundary en el filename/content; canonical form se devuelve tal cual.
# (Notifier PEARL/INSPIRE/AgileIQ; Morley ZXe/ZXSe/ZXr/DXc).
_LETTER_MODELS: dict[str, tuple[str, str | None]] = {
    # Notifier
    "PEARL":   ("Notifier", None),
    "INSPIRE": ("Notifier", None),
    "AgileIQ": ("Notifier", None),
    # Morley — variantes letter-suffix
    "ZXe":  ("Morley", None),
    "ZXSe": ("Morley", None),
    "ZXr":  ("Morley", None),
    "DXc":  ("Morley", None),
}

# Códigos que el regex genérico marcaría como "modelo" pero son normas/
# certificaciones/grados — NO son productos. Filtra falsos positivos como
# DXc_Manual → product_model="EN-54", B501BH → product_model="NFPA-72".
_NON_PRODUCT_CODES: set[str] = {
    "EN-54", "EN54", "EN-50", "EN50",
    "NFPA-72", "NFPA72",
    "IP-65", "IP65", "IP-66", "IP66", "IP-67", "IP67", "IP-68", "IP68",
    "ISO-9001", "ISO9001", "ISO-14001", "ISO14001",
    "CEM-2004", "CEM2004",
    "UL-268", "UL268",
    "MM-95",  # falso positivo visto en RIF_08791
    "GRANDI-22",  # falso positivo visto en MI-DMMI
    "ULTRA-123",  # falso positivo visto en CALYPSO
}

# (2) Marca propia por prefijo de modelo (Detnov / Notifier / Morley).
#     Distribuidor = NULL: no hay canal separado de la marca.
_MAIN_MFR_BY_PREFIX: dict[str, str] = {
    # Detnov
    "CAD": "Detnov", "CCD": "Detnov", "CMD": "Detnov", "MAD": "Detnov",
    "PCD": "Detnov", "FAD": "Detnov", "TCD": "Detnov", "SCD": "Detnov",
    "SFD": "Detnov", "TRD": "Detnov", "TSD": "Detnov", "TMD": "Detnov",
    "PGD": "Detnov", "TBUD": "Detnov", "TED": "Detnov", "DGD": "Detnov",
    "DMD": "Detnov", "DOD": "Detnov", "DTD": "Detnov", "DXD": "Detnov",
    "DBD": "Detnov", "PAD": "Detnov", "MED": "Detnov",
    # Notifier (sin VESDA — la atrapa _BRAND_PATTERNS arriba como Xtralis).
    "AFP": "Notifier", "AM": "Notifier", "ID": "Notifier", "IDX": "Notifier",
    "NFS": "Notifier", "NFG": "Notifier", "NFXI": "Notifier", "NFX": "Notifier",
    "RP": "Notifier", "FAAST": "Notifier", "MIDT": "Notifier",
    "MPDT": "Notifier", "MNDT": "Notifier", "MADT": "Notifier",
    "MCDT": "Notifier",  # otra familia de accesorios Notifier observada en corpus
    # Morley
    "ZX": "Morley", "DXC": "Morley", "ECO": "Morley", "MIE": "Morley",
    "WR": "Morley",
}

# (3) Pistas por carpeta — último recurso cuando el modelo no resuelve.
#     Securiton: sus datasheets a veces vienen con código interno (T140359es)
#     que no parece un modelo; la carpeta los rescata. FireBeam y Signaline
#     son productos de marca propia Detnov (datasheets en detnov.com) — sin
#     código limpio en el nombre, la carpeta los rescata como Detnov.
_FOLDER_HINTS: list[tuple[str, str, str | None]] = [
    ("aspiración securiton", "Securiton", "Detnov"),
    ("adw",                  "Securiton", "Detnov"),
    ("firebeam",             "Detnov",     None),
    ("signaline",            "Detnov",     None),
]
# === FIN SEAM DE FASE 2 ======================================================

# Código de producto: 2-6 letras + dígitos, separador opcional, sufijos.
# Suficiente para Fase 1; la unificación con MODEL_PATTERN del retriever es Fase 2.
_MODEL_RE = re.compile(r"\b([A-Z]{2,6})[-\s]?(\d{2,4})([A-Z]?(?:-\d{1,3})?)\b")

_DOC_TYPE_KEYWORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(instalaci[oó]n|installation|instala)\b", re.I), "instalacion"),
    (re.compile(r"\b(usuario|user|uso)\b", re.I), "usuario"),
    (re.compile(r"\b(programaci[oó]n|programming)\b", re.I), "programacion"),
    (re.compile(r"\b(gu[ií]a r[aá]pida|quick|qr)\b", re.I), "guia_rapida"),
    (re.compile(r"\b(hoja de datos|datasheet|data sheet)\b", re.I), "hoja_datos"),
    (re.compile(r"\b(comunicaci[oó]n t[eé]cnica|technical)\b", re.I), "comunicacion_tecnica"),
]

# content_type por chunk — patrones de palabra clave. Orden = prioridad.
_CONTENT_TYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(aver[ií]a|fallo|error|diagn[oó]stic|no funciona|"
                r"troubleshoot|problema)\w*", re.I), "troubleshooting"),
    (re.compile(r"\b(conexi[oó]n|conexionad|cablead|borne|terminal|esquema|"
                r"wiring|polaridad)\w*", re.I), "wiring"),
    (re.compile(r"\b(especificaci|caracter[ií]sticas t[eé]cnicas|tensi[oó]n|"
                r"consumo|dimensiones|temperatura de|grado de protecci|"
                r"specification)\w*", re.I), "specification"),
    (re.compile(r"\b(paso \d|procedimiento|configurar|programar|pulse|"
                r"seleccione|men[uú]|ajuste)\w*", re.I), "procedure"),
]


@dataclass
class DocumentMetadata:
    """Metadata a nivel de documento — se aplica a todos sus chunks."""
    manufacturer: str | None = None   # marca real (la del datasheet)
    distributor: str | None = None    # canal de distribución si difiere; None = misma marca
    product_model: str | None = None
    doc_type: str | None = None
    category: str | None = None
    source_file: str | None = None


def _detect_model(text: str) -> str | None:
    """Código de modelo más frecuente en el texto (filename o muestra).

    Filtra primero los códigos de normas/certificaciones (_NON_PRODUCT_CODES)
    para no caer en falsos positivos tipo "EN-54" / "NFPA-72" / "IP-65".

    Prefiere modelos cuyo prefijo está en el mapa de marcas propias — así
    "PCD-100WP" gana a "IP-65" en un filename como "Pulsador IP65 PCD-100WP",
    y "SFD-220" gana al ruido del contenido. Si ninguno está en el mapa,
    cae al más frecuente.
    """
    matches = [f"{m[0]}-{m[1]}{m[2]}" for m in _MODEL_RE.findall(text.upper())]
    matches = [m for m in matches if m not in _NON_PRODUCT_CODES]
    if not matches:
        return None
    counter = Counter(matches)
    in_map = {m: c for m, c in counter.items()
              if (p := re.match(r"[A-Z]+", m)) and p.group() in _MAIN_MFR_BY_PREFIX}
    if in_map:
        return max(in_map, key=in_map.get)
    return counter.most_common(1)[0][0]


def _match_letter_model(text: str) -> tuple[str, str, str | None] | None:
    """Busca modelos puros-letras (PEARL, ZXe, DXc, etc.) por word-boundary.

    Si encuentra varios, devuelve el más LARGO (ZXSe gana a ZXe si ambos
    aparecen — "ZXSe" es más específico).
    """
    found: list[tuple[str, str, str | None]] = []
    for model, (mfr, distr) in _LETTER_MODELS.items():
        if re.search(rf"\b{re.escape(model)}\b", text, re.IGNORECASE):
            found.append((model, mfr, distr))
    if not found:
        return None
    found.sort(key=lambda t: -len(t[0]))
    return found[0]


def _detect_brand(filename: str, text_sample: str, source_path: str
                  ) -> tuple[str | None, str | None, str | None]:
    """Devuelve (modelo, marca_real, distribuidor). Tres pasadas:
      (1) patrones específicos de marcas distribuidas (Securiton, Pfannenberg,
          Argus, Pepperl-Fuchs, Xtralis, Spectrex, SenseWare) — capturan el
          modelo Y asignan marca+distribuidor.
      (2) modelo genérico + prefijo → marca propia (Detnov/Notifier/Morley).
      (3) pista por carpeta para los casos donde el modelo no aparece limpio
          en el nombre del archivo.
    Distribuidor = None cuando coincide con la marca (no hay canal separado).
    """
    # `_` no rompe \b en regex Python (es \w), así que normalizamos a espacios
    # ANTES de buscar — si no, "DXc_Manual" no matchea \bDXc\b y "B501BH_Eng"
    # no matchea \bB5xx\b (filenames muy comunes en el corpus).
    filename_n = filename.replace("_", " ")
    sample_n = text_sample[:4000].replace("_", " ")

    # (1) Filename-only — patrones cortos/ambiguos (B5xx) y pure-letter
    # (DXc/PEARL/AgileIQ/ZXe...). Los códigos cortos aparecen como
    # referencia en muchos contents; restringir a filename evita marcar el
    # doc por una mención. Letter-models prioridad ANTES que B5xx (más larga = más específica).
    match = _match_letter_model(filename_n)
    if match:
        return match
    for pattern, mfr, distr in _FILENAME_ONLY_PATTERNS:
        m = pattern.search(filename_n)
        if m:
            return (m.group(1).upper(), mfr, distr)

    # (2) Patrones específicos — filename con prioridad; contenido como fallback.
    # Estos sí pueden buscarse en content (regex son específicos).
    for haystack in (filename_n, sample_n):
        for pattern, mfr, distr in _BRAND_PATTERNS:
            m = pattern.search(haystack)
            if m:
                model = re.sub(r"\s+", "-", m.group(1)).upper()
                return (model, mfr, distr)

    # (3) Modelo genérico → marca propia por prefijo.
    model = _detect_model(filename_n) or _detect_model(sample_n)
    if model:
        prefix = re.match(r"[A-Z]+", model)
        if prefix and prefix.group() in _MAIN_MFR_BY_PREFIX:
            return (model, _MAIN_MFR_BY_PREFIX[prefix.group()], None)
        return (model, None, None)  # modelo detectado pero prefijo desconocido

    # (3) Pista por carpeta — último recurso.
    folder = source_path.replace("\\", "/").lower()
    for needle, mfr, distr in _FOLDER_HINTS:
        if needle in folder:
            return (None, mfr, distr)

    return (None, None, None)


def _detect_doc_type(filename: str) -> str | None:
    for pattern, doc_type in _DOC_TYPE_KEYWORDS:
        if pattern.search(filename):
            return doc_type
    return None


def _detect_category(source_path: str) -> str | None:
    """Categoría = subcarpeta inmediata bajo la raíz de manuales.

    Fase 1: valor crudo de la carpeta (taxonomía propia del corpus). La Fase 2
    lo mapea a la taxonomía canónica EN-54 desde el YAML — la carpeta
    'Detección analógica' mezcla centrales/detectores/módulos, así que la
    categoría real es por producto, no por carpeta.
    """
    parts = source_path.replace("\\", "/").split("/")
    for i, part in enumerate(parts):
        if part.lower().startswith("manuales") and i + 1 < len(parts) - 1:
            return parts[i + 1]
    return None


def detect_document_metadata(source_path: str,
                             text_sample: str = "") -> DocumentMetadata:
    """Detecta la metadata a nivel de documento (B5).

    Resuelve modelo + marca + distribuidor en una sola pasada (ver _detect_brand);
    el nombre del archivo casi siempre contiene el modelo de forma limpia, y se
    cae a una muestra de contenido cuando no.
    """
    filename = os.path.basename(source_path)
    name_no_ext = os.path.splitext(filename)[0]

    model, manufacturer, distributor = _detect_brand(name_no_ext, text_sample, source_path)
    return DocumentMetadata(
        manufacturer=manufacturer,
        distributor=distributor,
        product_model=model,
        doc_type=_detect_doc_type(name_no_ext),
        category=_detect_category(source_path),
        source_file=name_no_ext,
    )


def detect_content_type(content: str) -> str:
    """content_type de un chunk a partir de su texto (B5, nivel chunk).

    Por conteo, no por primer match: gana el tipo con más apariciones y se exige
    un mínimo de 2. Un único término no basta — en PCI 'Led de Avería' es una
    etiqueta de componente ubicua, no contenido de troubleshooting.
    """
    scores = {ctype: len(pattern.findall(content))
              for pattern, ctype in _CONTENT_TYPE_PATTERNS}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "general"


def apply_metadata(chunks: list, meta: DocumentMetadata) -> None:
    """Copia la metadata de documento a cada chunk y detecta su content_type.

    `chunks` es list[Chunk] (src.reingest.chunk). Mutación in-place.
    """
    for ch in chunks:
        ch.source_file = meta.source_file
        ch.manufacturer = meta.manufacturer
        ch.distributor = meta.distributor
        ch.product_model = meta.product_model
        ch.doc_type = meta.doc_type
        ch.category = meta.category
        ch.content_type = detect_content_type(ch.content)
