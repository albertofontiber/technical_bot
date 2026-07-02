"""
Hybrid retriever: vector similarity search + keyword match by product model.
Ensures that when a technician asks about a specific model (e.g. MAD-491),
we always find the right chunks even if vector similarity alone misses them.
"""

import json
import logging
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from ..config import (SUPABASE_URL, SUPABASE_SERVICE_KEY, RETRIEVAL_TOP_K,
                      CHUNKS_TABLE, RPC_SUFFIX, MERGE_STRATEGY)
from ..ingestion.embedder import embed_query
from .hyde import generate_hypothetical_document, HYDE_ENABLED
from . import catalog as _catalog
from . import series_registry as _series

logger = logging.getLogger(__name__)

# SEED pattern, hand-tuned (multi-manufacturer). Desde Fase 2 ya NO es el
# detector primario en retrieval: extract_product_models usa el catálogo
# dirigido por dato (src/rag/catalog.py). MODEL_PATTERN se conserva como
# (a) fail-safe si el snapshot del catálogo falta, (b) detector en ingest
# (src/reingest/metadata.py, donde depender del catálogo sería circular),
# (c) semilla de la unión en scripts/build_model_catalog.py (garantiza que el
# catálogo ⊇ lo que el bot ya reconocía → cero regresión).
# Separators (-, space) are optional where manufacturers vary between
# forms ("AFP-1010" vs "AFP1010"); normalization happens at the search
# layer via model_to_imatch_pattern (word-boundary + digit-extension guard).
MODEL_PATTERN = re.compile(
    r'\b('
    # === Detnov (clean single-model naming) ===
    r'CAD-\d+(?:-\d+)?|CCD-\d+(?:-\d+)?|CMD-\d+|MAD-\d+(?:-I)?|'
    r'DTD-\d+\w*|DOD-\d+\w*|DGD-\d+|DMD\w?-\d+|DXD-\d+\w*|'
    r'DBD-\d+\w*|'
    r'PCD-\d+|FAD-\d+|TUL-?\d+|SG\d+|SGCP\d+|'
    r'S[23]-(?:T[12]|IR)|'
    r'ASD-?\d+|ADW-?\d+|'
    r'FIREBEAM\s*\w+|'
    r'CALYPSO[\w-]*|'
    r'PGD-\d+|TBUD-\d+|'
    r'T[RMS]D-\d+|TCD-\d+|SCD-\d+|'
    # === Notifier — centrales ===
    r'AFP[- ]?\d{3,4}[A-Z]?|'                      # AFP-200, AFP-400, AFP1010, AFP-200E, AFP4000
    r'AM[- ]?\d{4}[A-Z]?|AM[- ]?\d{3}[A-Z]?|'      # AM2020, AM-6000, AM-8200, AM-200
    r'ID[- ]?\d{2,4}(?:/\d{1,3})?|'                # ID50, ID50/60, ID200, ID-200, ID1000, ID2000, ID3000
    r'ID2net|'
    r'NFS[- ]?(?:Supra|\d+(?:-\d+)?)|'             # NFS Supra, NFS2-8, NFS8
    r'NFG[- ]?\d+|'                                # NFG-8
    r'NFXI[- ]?\w+|NFX[- ]?(?:OPT|SMT|TDIFF|TFIX|BEAM)\w*|'
    r'PEARL|INSPIRE(?:[- ]?E\d+)?|'                # PEARL, INSPIRE, INSPIRE E10
    r'(?:Sistema|System)[- ]?5000|'                # Sistema 5000, System 5000
    r'VESDA[- ]*(?:E[- ]+)?(?:VL[FIPS]|VE[APUS])[\w-]*|'  # VESDA-E VEP, VESDA VLF-250, VESDA-E VEA, etc.
    r'FAAST[- ]?(?:FLEX|LT|XS|XM)?|'
    r'RP[- ]?\d{3,4}[A-Z]?|RP1[rR]|'               # RP-1001, RP1002E, RP1r
    r'M7[012]\d[A-Z]*(?:-\w+)?|'
    r'IDX[- ]?\d+\w*|'
    r'B50\d\w*|B524\w*|'
    r'LTS[- ]?\d+|'                                # LTS2, LTS-240
    r'SMART[- ]?3[G]?|'
    r'40[- ]?40[ILURM]|'
    r'POL[- ]?200(?:[- ]?TS)?|'                    # POL-200-TS (canonical) + POL200 legacy
    r'FSL[- ]?\d+\w*|FS[- ]?(?:24|20)[XSLMRI]?|'
    r'SDX[- ]?\d+[A-Z]*|'                          # SDX-751 (Notifier detector, cm003)
    r'DT[- ]?\d+[A-Z]*|'                           # DT-390, DT-410, DT-951
    r'MN[- ]?DT[- ]?\d+[A-Z]*|MI[- ]?DT[- ]?\d+[A-Z]*|MP[- ]?DT[- ]?\d+[A-Z]*|'
    r'S300\w*|SC[- ]?6|CZ[- ]?6|'
    r'HLSPS\w*|PK[- ]?8200|PK[- ]?AFP[- ]?\d+[A-Z]*|'
    r'Multiscann\+*|SENTOX[- ]?\w*|'
    r'PL4|GALILEO|AgileIQ|'
    # === Morley ===
    r'ZXS?e|ZXr|DXc|'                              # ZXe, ZXSe, ZXr, DXc (4 centrales principales)
    r'MI-\w+(?:-\w+)*|'                            # MI-Gate, MI-DCZM, MI-LPB2-S2I (requiere dash: evita falso positivo de "mi")
    r'ECO10\d{2}|'                                 # ECO1000/1002/1003/1005
    r'F5000|M200E|'                                # Morley literales
    r'AutoSAT[- ]?\d+|'
    r'UCIP|SIMEI|ITAC|WR2001|'
    r'HSR[- ]?\w+|IRK[- ]?\w+|VSN[- ]?\w+|'
    r'MIE[- ]?\d+'                                 # Comunicador MIE-320/330/340/390
    r')\b',
    re.IGNORECASE,
)


def extract_product_models(query: str) -> list[str]:
    """Extract product model codes mentioned in the query — UNIÓN de dos fuentes.

    1. Catálogo dirigido por dato (data/model_catalog.json): cubre TODO el corpus
       de modelos con fabricante conocido — incluidas marcas que el seed no
       conoce (Spectrex, Xtralis...). Devuelve la forma canónica almacenada.
    2. Seed MODEL_PATTERN (hand-tuned): red de seguridad para modelos que el
       patrón reconoce por forma pero que aún NO existen como product_model
       limpio en el corpus (p.ej. SDX-751, ZXe — product_model mal atribuido,
       pendiente de #6). Garantiza CERO regresión de detección vs. el bot actual.

    La unión se deduplica por clave canónica; la forma del catálogo tiene
    precedencia. Cuando #6 limpie product_model, el catálogo absorberá lo que
    hoy aporta el seed y este podrá encogerse.
    """
    out: list[str] = []
    seen: set[str] = set()

    if _catalog.catalog_available():
        for m in _catalog.extract_models(query):
            nk = _catalog.normkey(m)
            if nk not in seen:
                seen.add(nk)
                out.append(m)

    for m in MODEL_PATTERN.findall(query):
        up = m.upper()
        nk = _catalog.normkey(up)
        if nk not in seen:
            seen.add(nk)
            out.append(up)

    # s72 Brazo A (flag LEVER2_IDENTITY, default OFF = prod inerte): resolver el
    # token-paraguas de marketing a sus variantes reales del corpus (ZXe → ZX2e/ZX5e)
    # para que filtro/keyword/content busquen el producto correcto, no el espurio.
    if os.getenv("LEVER2_IDENTITY", "").strip().lower() in ("1", "true", "yes", "on"):
        out = _series.resolve_aliases(out)

    return out


# === Per-manufacturer classifiers for cross-brand intent detection ===
# Pattern-based lookup (no DB roundtrip). Patterns derived from MODEL_PATTERN
# sections. Order matters: first match wins. Each pattern is partial-match
# against an uppercased model token.

_DETNOV_PATTERNS = re.compile(
    r'^(CAD-|CCD-|CMD-|MAD-|DTD-|DOD-|DGD-|DMD|DXD-|DBD-|PCD-|FAD-|TUL-?|'
    r'SG\d|SGCP|S[23]-|ASD-?|ADW-?|FIREBEAM|CALYPSO|PGD-|TBUD-|T[RMS]D-|'
    r'TCD-|SCD-)',
    re.IGNORECASE,
)
_NOTIFIER_PATTERNS = re.compile(
    r'^(AFP|AM-?\d{3,4}|ID[-]?\d|ID2NET|NFS|NFG|NFXI|NFX|PEARL|INSPIRE|'
    r'SISTEMA|SYSTEM|VESDA|FAAST|RP-?\d{3,4}|RP1[RR]|M7[012]|IDX|B50|B524|'
    r'LTS|SMART|40-?40|POL|FSL|FS-?\d|SDX|DT-?\d|MN-?DT|MI-?DT|MP-?DT|'
    r'S300|SC-?6|CZ-?6|HLSPS|PK-?|MULTISCANN|SENTOX|PL4|GALILEO|AGILEIQ)',
    re.IGNORECASE,
)
_MORLEY_PATTERNS = re.compile(
    r'^(ZXS?E|ZXR|DXC|MI-|ECO10|F5000|M200E|AUTOSAT|UCIP|SIMEI|ITAC|'
    r'WR2001|HSR-?|IRK-?|VSN-?|MIE-?)',
    re.IGNORECASE,
)


def classify_model_manufacturer(model: str) -> str | None:
    """Return 'Detnov' / 'Notifier' / 'Morley' for a detected model code,
    or None if it doesn't match any known manufacturer pattern.

    In-memory, no DB roundtrip. Used by cross-brand intent detection where
    latency matters.

    Catalog-first: la marca REAL del dato (catálogo, derivado del corpus) manda.
    El seed per-fabricante queda solo como FALLBACK para modelos fuera del
    catálogo (out-of-corpus).

    Por qué (Alberto, #6): el seed-first generaba un problema estructural — un
    modelo de marca nueva cuyo CÓDIGO encaja en un patrón seed amplio se
    mis-clasificaba a una de las 3 marcas originales (VESDA→Notifier cuando es
    Xtralis; 40-40→Notifier cuando es Spectrex). Catalog-first lo elimina para
    todo modelo del corpus. El seed conserva entradas legacy hoy-erróneas
    (VESDA/40-40/ASD) pero son inocuas: el catálogo las sobreescribe. End-state
    limpio: el seed encoge a cero conforme el catálogo es la fuente única.
    """
    if _catalog.catalog_available():
        mfr = _catalog.model_manufacturer(model)
        if mfr:
            return mfr

    m = model.strip().upper()
    if _DETNOV_PATTERNS.match(m):
        return "Detnov"
    if _NOTIFIER_PATTERNS.match(m):
        return "Notifier"
    if _MORLEY_PATTERNS.match(m):
        return "Morley"
    return None


# Manufacturer names spelled out in free text (technicians sometimes name
# brands explicitly: "¿el detector Notifier SDX-751 funciona con Morley?").
_MANUFACTURER_NAME_PATTERNS = {
    "Detnov": re.compile(r"\bdetnov\b", re.IGNORECASE),
    "Notifier": re.compile(r"\bnotifier\b", re.IGNORECASE),
    "Morley": re.compile(r"\bmorley(?:\s*-?\s*ias)?\b", re.IGNORECASE),
    "Honeywell": re.compile(r"\bhoneywell\b", re.IGNORECASE),
}


def detect_query_manufacturers(query: str) -> set[str]:
    """Return the set of manufacturers implicitly or explicitly referenced
    in the query.

    Sources:
    1. Manufacturer names mentioned literally in the query.
    2. Product model codes detected via MODEL_PATTERN, classified by
       per-manufacturer pattern.

    "Honeywell" is normalised to its underlying brand when the query
    pairs it with a specific model (Notifier or Morley are Honeywell
    brands). Otherwise it stays as "Honeywell" and is treated as a single
    manufacturer reference.
    """
    detected: set[str] = set()

    # 1. Literal manufacturer names.
    for name, pattern in _MANUFACTURER_NAME_PATTERNS.items():
        if pattern.search(query):
            detected.add(name)

    # 2. Models → manufacturer via pattern classifier.
    for model in extract_product_models(query):
        mfr = classify_model_manufacturer(model)
        if mfr:
            detected.add(mfr)

    # Honeywell collapse: if we detected Honeywell AND a concrete sub-brand
    # (Notifier/Morley), the user is just being specific about the parent
    # group. Drop Honeywell, keep the concrete brand.
    if "Honeywell" in detected and detected & {"Notifier", "Morley"}:
        detected.discard("Honeywell")

    return detected


# Ecosistemas de compatibilidad/distribución: marcas que se integran o
# distribuyen juntas → NO son cross-brand entre sí. OJO: Notifier y Morley son
# ambas Honeywell pero ecosistemas DISTINTOS (sí cross-brand — cm001). Esto NO
# es propiedad corporativa, es compatibilidad real. Mapa acotado a relaciones
# confirmadas (Alberto, #6); extensible. La versión escalable leería la columna
# `distributor` del corpus (hoy poco poblada). Candidato pendiente de confirmar:
# System Sensor↔Notifier.
_ECOSYSTEM_OF = {
    "Xtralis": "Notifier",     # VESDA se integra/distribuye con Notifier/Honeywell
    "Securiton": "Detnov",     # ASD (aspiración) distribuida por Detnov
}


def _ecosystem(mfr: str) -> str:
    return _ECOSYSTEM_OF.get(mfr, mfr)


def is_cross_brand_query(query: str) -> tuple[bool, set[str]]:
    """Decide whether the query references products from 2+ distinct
    ECOSYSTEMS. Returns (is_cross_brand, detected_manufacturers).

    Cuenta ecosistemas, no marcas: una query "VESDA (Xtralis) en central
    Notifier" NO es cross-brand (mismo ecosistema), pero "Notifier + Morley" sí.
    Usado por el generator para forzar admit_no_info en vez de inferir
    compatibilidad cross-brand (política: NO inferir cross-brand).
    """
    mfrs = detect_query_manufacturers(query)
    groups = {_ecosystem(m) for m in mfrs}
    return (len(groups) >= 2, mfrs)


def model_to_imatch_pattern(model: str) -> str:
    """Convert a detected model token into a PostgreSQL regex for the PostgREST
    ``imatch`` operator.

    Design decisions:
    - Separators in the input (``-`` or whitespace) become optional ``[- ]*`` so
      ``AFP-1010`` matches stored ``AM2020/AFP1010`` and ``AFP1010``.
    - PostgreSQL word-boundary ``\\y`` at the start anchors the match; mid-word
      substrings like ``OID200`` don't accidentally match ``ID200``.
    - Negative lookahead ``(?!\\d)`` at the end prevents a digit from extending
      the match — so ``ID-200`` does NOT match stored ``ID2000`` while still
      allowing letter suffixes (``AFP-200`` → ``AFP-200E``).

    Note: PostgreSQL ARE uses ``\\y`` for word boundary, not ``\\b`` (which is
    a backspace in ARE). We emit ``\\y`` for the server; Python-side regex
    (``MODEL_PATTERN``) still uses ``\\b`` because Python's ``re`` follows
    standard conventions.
    """
    parts = [p for p in re.split(r'[- ]+', model.strip()) if p]
    if not parts:
        return ""
    core = r'[- ]*'.join(re.escape(p) for p in parts)
    return rf'\y{core}(?!\d)'


# Words to ignore when extracting search keywords from the query
STOP_WORDS = {
    "qué", "que", "cómo", "como", "cuál", "cual", "cuántos", "cuantos",
    "cuántas", "cuantas", "dónde", "donde", "por", "para", "con", "sin",
    "del", "de", "la", "el", "las", "los", "un", "una", "unos", "unas",
    "en", "es", "son", "tiene", "hay", "puede", "puedo", "ser", "estar",
    "se", "si", "no", "más", "cada", "este", "esta", "estos", "estas",
    "su", "sus", "al", "lo", "le", "me", "te", "nos", "muy", "ya",
    "esa", "ese", "eso", "y", "o", "a", "e", "u",
    "central", "módulo", "modulo", "equipo", "sistema", "modelo",
    "máximo", "maximo", "mínimo", "minimo", "total",
    "cuáles", "cuales", "cuándo", "cuando", "tiene", "tienen",
    "funcionamiento", "información", "informacion", "sobre",
    "aparece", "puede", "estar", "pasando", "pasa",
    "tenéis", "teneis", "disponibles", "disponible", "necesito",
    "quiero", "favor", "decirme", "explicar", "indicar",
    "hacer", "hago", "instalar", "instala", "configurar", "configura",
}

# Map common query terms to their technical equivalents for content search
QUERY_SYNONYMS = {
    "condiciones ambientales": "temperatura",
    "temperatura trabajo": "temperatura",
    "condiciones funcionamiento": "temperatura",
    "rango temperatura": "temperatura",
    "grado protección": "IP",
    "resistencia fin de línea": "resistencia final",
    "resistencia fin de linea": "resistencia final",
    "especificaciones técnicas": "especificaciones",
    "especificaciones tecnicas": "especificaciones",
    "datos técnicos": "especificaciones",
    "fallo": "averías",
    "error": "averías",
    "problema": "averías",
    "avería": "averías",
    "led": "indicador",
}

# Intent detection patterns for targeted content_type retrieval
import re as _re_module
SPEC_INTENT = _re_module.compile(
    r"(especificaciones|datos\s+técnicos|datos\s+tecnicos|características\s+técnicas|"
    r"caracteristicas\s+tecnicas|consumo|tensión|tension|corriente|dimensiones|peso|"
    r"temperatura|humedad|grado\s+protección|grado\s+proteccion|IP\d+|comparar|"
    r"comparativa|diferencia|vs\.?|frente\s+a)",
    _re_module.IGNORECASE,
)
TROUBLESHOOT_INTENT = _re_module.compile(
    r"(fallo|avería|averia|error|problema|no\s+funciona|no\s+arranca|"
    r"parpadea|se\s+enciende|no\s+para|alarma\s+falsa)",
    _re_module.IGNORECASE,
)
# Queries where the bot SHOULD surface a diagram (wiring, install, terminals).
# Used by reranker (prompt hint) and retrieve_chunks (diagram_search path).
# Spanish conjugations covered via \w* tails.
WIRING_INTENT = _re_module.compile(
    r"\b("
    r"conex[ií]on\w*|"     # conexión, conexiones, conexionado
    r"cablea\w*|"          # cableado, cablear, cableamos
    r"cable\b|cables\b|"   # bare 'cable' / 'cables'
    r"instala\w*|"         # instalación, instalar, instala
    r"conect\w*|"          # conectar, conecta, conectan, conectado
    r"borne\w*|"           # borne, bornes
    r"terminal\w*|"        # terminal, terminales
    r"esquema\w*|"         # esquema, esquemas
    r"diagrama\w*|"        # diagrama, diagramas
    r"polaridad|"          # polaridad
    r"montaje|montar|"     # montaje, montar
    r"wirin[gs]"           # wiring / wirings
    r")\b",
    _re_module.IGNORECASE,
)


def extract_search_keywords(query: str) -> list[str]:
    """Extract meaningful search keywords from the query (exclude stop words and model codes)."""
    import re as _re
    # Remove model codes from query
    clean = MODEL_PATTERN.sub("", query)
    # Extract words, lowercase
    words = _re.findall(r'[a-záéíóúñü]+', clean.lower())
    # Filter stop words and short words
    keywords = [w for w in words if w not in STOP_WORDS and len(w) >= 4]
    # Deduplicate preserving order, limit to top 3
    seen = set()
    unique = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique[:3]


def keyword_search(
    product_model: str,
    limit: int = 5,
) -> list[dict]:
    """Search chunks by product_model match via PostgREST ``imatch``.

    Uses a regex with optional separators and word-boundary anchors so that
    a query token like ``AFP1010`` matches compound stored values such as
    ``AM2020/AFP1010`` or ``AM2020 and AFP1010`` — see ``model_to_imatch_pattern``
    for the full design.  Detnov's canonical single-model values (``MAD-567``)
    match their own pattern equivalently.
    """
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    pattern = model_to_imatch_pattern(product_model)
    if not pattern:
        return []

    params = {
        "product_model": f"imatch.{pattern}",
        "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,language,has_diagram,diagram_url,source_file,page_number,document_id",
        "limit": str(limit),
    }
    # s74 Lever 1 / 2b (LEVER1_KEYWORD_ORDER, default off = inerte): sin flag el GET no lleva
    # `order` → los `limit` devueltos son orden FÍSICO arbitrario (PostgREST sin ORDER BY) y el
    # chunk model-correcto en posición física >5 nunca entra (cat016 §3.3). Con flag: `order`
    # DETERMINISTA neutral (page_number,id — anti-flapping; NO content_type, que ordena alfabético
    # y entierra todo bajo 'general' — verificado s74) + limit alto; diversify+reranker seleccionan.
    if os.getenv("LEVER1_KEYWORD_ORDER", "").strip().lower() in ("1", "true", "yes", "on"):
        params["order"] = "page_number.asc,id.asc"
        params["limit"] = "15"

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()

    rows = resp.json()
    # Lower score than content search — these are generic model matches without content relevance
    for row in rows:
        row["similarity"] = 0.65
    return rows


def diagram_search(
    product_model: str,
    content_type: str | None = None,
    limit: int = 3,
) -> list[dict]:
    """Search chunks for ``product_model`` that also carry a usable diagram.

    PostgREST filter: ``product_model imatch pattern`` AND ``has_diagram=true``
    AND ``diagram_url IS NOT NULL``, optionally narrowed by ``content_type``.

    Diagram density is low (~3–5% of the corpus), so without this dedicated
    path the vector + keyword merge drowns out has_diagram chunks.  The
    ``content_type`` filter is important for relevance: without it,
    ``diagram_search('ZXe')`` surfaces any ZXe diagram (e.g. 'Bloqueo de
    Memoria') which the reranker will correctly drop as off-topic for a
    sirena-conexionado query.  Pass ``content_type='wiring'`` for
    WIRING_INTENT queries to guarantee both on-topic AND diagram-bearing.

    Similarity is set to 0.82 — below targeted typed_search (0.85) but above
    the plain vector/keyword fallbacks — so the reranker surfaces diagrams
    without overriding an explicitly-requested spec/troubleshoot hit.
    """
    pattern = model_to_imatch_pattern(product_model)
    if not pattern:
        return []
    params = {
        "product_model": f"imatch.{pattern}",
        "has_diagram": "eq.true",
        "diagram_url": "not.is.null",
        "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,language,has_diagram,diagram_url,source_file,page_number,document_id",
        "limit": str(limit),
    }
    if content_type:
        params["content_type"] = f"eq.{content_type}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
    rows = resp.json()
    for row in rows:
        row["similarity"] = 0.82
    return rows


def typed_search(
    product_model: str,
    content_type: str = "specification",
    limit: int = 5,
) -> list[dict]:
    """Search chunks by product_model (imatch) AND content_type. Targeted retrieval."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    pattern = model_to_imatch_pattern(product_model)
    if not pattern:
        return []

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            params={
                "product_model": f"imatch.{pattern}",
                "content_type": f"eq.{content_type}",
                "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,language,has_diagram,diagram_url,source_file,page_number,document_id",
                "limit": str(limit),
            },
        )
        resp.raise_for_status()

    rows = resp.json()
    for row in rows:
        row["similarity"] = 0.85  # High score — targeted match
    return rows


def content_search(
    search_term: str,
    limit: int = 5,
    product_model: str | None = None,
) -> list[dict]:
    """Search chunks by content (+ optional model filter).

    When ``product_model`` is provided, we bypass the ``search_chunks_text`` RPC
    (whose ``filter_product`` clause does strict equality and silently returns
    zero rows for compound stored values like ``AM2020/AFP1010``) and hit
    PostgREST directly with ``imatch`` on ``product_model`` + ``ilike`` on
    ``content``.  Without a model, the RPC's fts ranking is still the best
    path.

    (s85, DEC-071) The ``category`` filter was removed: ``chunks_v2.category`` is
    the DEAD column (0 canonical rows since the SWAP s44) — filtering by it only
    ever returned 0 rows.
    """
    headers_get = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    # Determine score: higher when filtered by model (more targeted)
    has_filter = product_model
    base_score = 0.80 if has_filter else 0.70

    # --- Path A: product_model set → skip RPC, use PostgREST imatch ---
    if product_model:
        pattern = model_to_imatch_pattern(product_model)
        if not pattern:
            return []
        params = {
            "content": f"ilike.*{search_term}*",
            "product_model": f"imatch.{pattern}",
            "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,language,has_diagram,diagram_url,source_file,page_number,document_id",
            "limit": str(limit),
        }
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(
                    f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                    headers=headers_get,
                    params=params,
                )
                resp.raise_for_status()
            rows = resp.json()
            for row in rows:
                row["similarity"] = base_score
            return rows
        except Exception:
            return []

    # --- Path B: no product_model → RPC fts (category filter uses composite GIN) ---
    headers_post = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "search_query": search_term,
        "filter_product": None,
        "filter_manufacturer": None,
        "filter_category": None,
        "match_limit": limit,
    }
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/search_chunks_text{RPC_SUFFIX}",
                headers=headers_post,
                json=payload,
            )
            if resp.status_code == 200:
                rows = resp.json()
                for row in rows:
                    row["similarity"] = base_score
                return rows
    except Exception:
        pass

    # Fallback to ilike (RPC unavailable)
    params = {
        "content": f"ilike.*{search_term}*",
        "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,language,has_diagram,diagram_url,source_file,page_number,document_id",
        "limit": str(limit),
    }
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                headers=headers_get,
                params=params,
            )
            resp.raise_for_status()
        rows = resp.json()
        for row in rows:
            row["similarity"] = base_score
        return rows
    except Exception:
        return []


# Key PCI terms that should trigger content search when no model is detected
PCI_TERMS = {
    "pulsador": "pulsador",
    "pulsadores": "pulsador",
    "sirena": "sirena",
    "sirenas": "sirena",
    "detector": "detector",
    "detectores": "detector",
    "central": "central",
    "centrales": "central",
    "módulo": "módulo",
    "modulo": "módulo",
    "aislador": "aislador",
    "extinción": "extinción",
    "extincion": "extinción",
    "batería": "batería",
    "baterías": "batería",
    "fuente": "fuente alimentación",
    "lazo": "lazo",
    "bucle": "bucle",
    "zona": "zona",
    "relé": "relé",
    "rele": "relé",
    "monóxido": "monóxido",
    "monoxido": "monóxido",
    "gas": "gas",
    "aspiración": "aspiración",
    "aspiracion": "aspiración",
    "evacuación": "evacuación",
    "evacuacion": "evacuación",
}

# Map query keywords to Supabase category filter (unified EN 54 taxonomy).
# IMPORTANT: Compound phrases are checked FIRST (longest match wins) to avoid
# "detector de aspiración" matching the generic "detector" → "Detectores puntuales".
_CATEGORY_PHRASES = [
    # Compound phrases — checked first (order: longest → shortest)
    ("detector de aspiración", "Detectores de aspiración"),
    ("detector de aspiracion", "Detectores de aspiración"),
    ("detectores de aspiración", "Detectores de aspiración"),
    ("detectores de aspiracion", "Detectores de aspiración"),
    ("detector lineal", "Detectores lineales"),
    ("detectores lineales", "Detectores lineales"),
    ("detector de barrera", "Detectores lineales"),
    ("fuente de alimentación", "Fuentes de alimentación"),
    ("fuente de alimentacion", "Fuentes de alimentación"),
    ("módulo de lazo", "Módulos de lazo"),
    ("modulo de lazo", "Módulos de lazo"),
    ("módulo aislador", "Módulos de lazo"),
    ("modulo aislador", "Módulos de lazo"),
    ("sistema de extinción", "Sistemas de extinción"),
    ("sistema de extincion", "Sistemas de extinción"),
    ("monóxido de carbono", "Detectores puntuales"),
    ("monoxido de carbono", "Detectores puntuales"),
    ("detector de gas", "Detectores puntuales"),
    ("detector de humo", "Detectores puntuales"),
]

# Single-word fallbacks — only checked if no compound phrase matched
CATEGORY_TERMS = {
    "central": "Centrales de incendios",
    "centrales": "Centrales de incendios",
    "panel": "Centrales de incendios",
    "aspiración": "Detectores de aspiración",
    "aspiracion": "Detectores de aspiración",
    "vesda": "Detectores de aspiración",
    "faast": "Detectores de aspiración",
    "barrera": "Detectores lineales",
    "lineal": "Detectores lineales",
    "beam": "Detectores lineales",
    "pulsador": "Pulsadores",
    "pulsadores": "Pulsadores",
    "sirena": "Sirenas y balizas",
    "sirenas": "Sirenas y balizas",
    "baliza": "Sirenas y balizas",
    "evacuación": "Sirenas y balizas",
    "evacuacion": "Sirenas y balizas",
    "módulo": "Módulos de lazo",
    "modulo": "Módulos de lazo",
    "aislador": "Módulos de lazo",
    "fuente": "Fuentes de alimentación",
    "batería": "Fuentes de alimentación",
    "extinción": "Sistemas de extinción",
    "extincion": "Sistemas de extinción",
    "software": "Software y programación",
    "programación": "Software y programación",
    "detector": "Detectores puntuales",
    "detectores": "Detectores puntuales",
    "monóxido": "Detectores puntuales",
    "monoxido": "Detectores puntuales",
    "gas": "Detectores puntuales",
    "humo": "Detectores puntuales",
}


def lookup_model_manufacturer(product_model: str) -> str | None:
    """Look up which manufacturer a product model belongs to in the database.

    Returns the manufacturer name if found, None if the model doesn't exist.
    """
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            params={
                "product_model": f"eq.{product_model}",
                "select": "manufacturer",
                "limit": "1",
            },
        )
        resp.raise_for_status()

    rows = resp.json()
    if rows:
        return rows[0].get("manufacturer")
    return None


def get_available_manufacturers() -> list[str]:
    """Get all distinct manufacturers in the database.

    Uses the `documents` table (one row per manual, ~1k rows) instead of
    `chunks` (~168k rows). The previous chunks-based query with `limit=5000`
    returned only the first 5000 chunks, which were dominated by a single
    manufacturer due to insertion order — so `Notifier` and `Morley` chunks
    never appeared and the function returned only `['Detnov']` (sesión 21
    smoke test exposed this on Telegram step 7).
    """
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    # PostgREST capa la respuesta a max-rows=1000 aunque limit pida más (misma
    # lección que el fingerprint s64): con >1000 docs, las filas más allá del
    # corte quedaban fuera y sus marcas desaparecían del catálogo (cazado en el
    # smoke s65: Aritech/Kidde/Edwards invisibles tras el backfill). Paginar.
    rows: list[dict] = []
    offset = 0
    with httpx.Client(timeout=10.0) as client:
        while True:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=headers,
                params={
                    "select": "manufacturer",
                    "limit": "1000",
                    "offset": str(offset),
                },
            )
            resp.raise_for_status()
            batch = resp.json()
            rows.extend(batch)
            if len(batch) < 1000:
                break
            offset += 1000

    manufacturers = sorted(set(
        r["manufacturer"] for r in rows
        if r.get("manufacturer") and r["manufacturer"] != "unknown"
    ))
    return manufacturers


def manufacturer_in_db(manufacturer_name: str) -> bool:
    """Check if a manufacturer has data in the database (case-insensitive)."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            params={
                "manufacturer": f"ilike.{manufacturer_name}",
                "select": "id",
                "limit": "1",
            },
        )
        resp.raise_for_status()

    return len(resp.json()) > 0


def get_all_models_by_category() -> dict[str, list[str]]:
    """Get all distinct product models grouped by category."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            params={
                "select": "product_model,category",
                "product_model": "neq.unknown",
                "limit": "5000",
            },
        )
        resp.raise_for_status()

    rows = resp.json()
    by_category = {}
    for r in rows:
        cat = r.get("category", "General")
        model = r.get("product_model", "")
        if model and cat:
            if cat not in by_category:
                by_category[cat] = set()
            by_category[cat].add(model)

    return {cat: sorted(models) for cat, models in sorted(by_category.items())}


def get_category_models(category: str) -> list[str]:
    """Get distinct product models available in a category."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            params={
                "category": f"eq.{category}",
                "select": "product_model",
                "limit": "2000",
            },
        )
        resp.raise_for_status()

    rows = resp.json()
    models = sorted(set(
        r["product_model"] for r in rows
        if r.get("product_model") and r["product_model"] != "unknown"
    ))
    return models


def vector_search(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    threshold: float = 0.3,
    product_filter: str | None = None,
    category_filter: str | None = None,
    precomputed_embedding: list[float] | None = None,
) -> list[dict]:
    """Vector similarity search via the match_chunks RPC function."""
    query_embedding = precomputed_embedding or embed_query(query)

    payload = {
        "query_embedding": query_embedding,
        "match_threshold": threshold,
        "match_count": top_k,
        "filter_product": product_filter,
        "filter_category": category_filter,
        "filter_manufacturer": None,
    }

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{SUPABASE_URL}/rest/v1/rpc/match_chunks{RPC_SUFFIX}",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()

    return resp.json()


def _tag_channel(chunks: list[dict], tag: str) -> list[dict]:
    """(s68) Etiqueta el macro-canal de ORIGEN (VECTOR/MODEL/TARGETED/CONTENT) para el
    reporte de composición del merge. Primera etiqueta gana (un chunk dual conserva la
    de su primer canal). El campo viaja con el chunk — inocuo para los consumidores."""
    for c in chunks:
        c.setdefault("_channel", tag)
    return chunks


def _fetch_embeddings_by_id(ids: list[str]) -> dict[str, list[float]]:
    """(s68, V-A′) Embeddings almacenados por id — re-score cliente-side de los
    candidatos léxicos. Sin DDL (diseño v6.1 §2)."""
    out: dict[str, list[float]] = {}
    if not ids:
        return out
    headers = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    for i in range(0, len(ids), 80):
        id_list = ",".join(f'"{x}"' for x in ids[i:i + 80])
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=headers,
                               params={"select": "id,embedding", "id": f"in.({id_list})"})
            for row in r.json():
                emb = row.get("embedding")
                if isinstance(emb, str):
                    emb = json.loads(emb)
                if emb:
                    out[row["id"]] = emb
        except Exception as e:
            logger.warning("fetch embeddings para re-score falló (%s) — %d ids sin coseno", e, len(ids))
    return out


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _rescore_to_cosine(chunks: list[dict], query_embedding: list[float]) -> list[dict]:
    """(s68, V-A′) similarity := coseno real para los chunks que traen stamp (los del
    canal VECTOR ya traen coseno del RPC). Chunk sin embedding recuperable conserva su
    score actual (fallo-abierto declarado: mejor stamp que descartar contenido)."""
    need = [c.get("id") for c in chunks
            if c.get("id") and c.get("_channel") != "VECTOR"]
    embs = _fetch_embeddings_by_id([i for i in dict.fromkeys(need)])
    for c in chunks:
        e = embs.get(c.get("id"))
        if e is not None:
            c["similarity"] = _cos(query_embedding, e)
    return chunks


def _merge_channels(keyword_results: list[dict], vector_results: list[dict],
                    cap: int, strategy: str,
                    query_embedding: list[float] | None = None) -> list[dict]:
    """(s68) Step 4 — fusión de canales bajo MERGE_STRATEGY (diseño _s68_merge_design.md
    v6.1 §2; configs ÚNICAS congeladas, anti-tuning).

    stamps  → comportamiento histórico EXACTO: dedup keyword-first (el stamp PISA al
              duplicado vectorial) + sort por similarity (stamps 0.65-0.85 arriba).
    quota   → V-D composición: léxicos con sus límites actuales (en duales el registro
              VECTOR conserva su coseno — volteo del keyword-first, efecto-vista F4
              declarado) + VECTOR llena hasta `cap` por coseno desc; el sort por
              similarity del pipeline se mantiene (el orden post-merge lo gestionan
              los diversificadores, intocables — F6).
    cosine  → V-A′: similarity := coseno real para TODO candidato (re-score
              cliente-side); dedup simple por id; sort único; sin boosts.
    """
    if strategy == "cosine":
        seen: set = set()
        merged = []
        for c in keyword_results + vector_results:
            cid = c.get("id")
            if cid and cid not in seen:
                seen.add(cid)
                merged.append(c)
        _rescore_to_cosine(merged, query_embedding or [])
        merged.sort(key=lambda c: c.get("similarity", 0), reverse=True)
        return merged

    if strategy == "quota":
        by_id_vec = {}
        for v in vector_results:
            vid = v.get("id")
            if vid and vid not in by_id_vec:
                by_id_vec[vid] = v
        seen = set()
        merged = []
        for c in keyword_results:                      # léxicos: límites actuales
            cid = c.get("id")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            merged.append(by_id_vec.get(cid, c))       # dual → registro VECTOR (coseno)
        for v in vector_results:                       # vector llena hasta cap
            if len(merged) >= cap:
                break
            vid = v.get("id")
            if vid and vid not in seen:
                seen.add(vid)
                merged.append(v)
        merged.sort(key=lambda c: c.get("similarity", 0), reverse=True)
        return merged

    # stamps (default) — histórico exacto
    seen_ids: set = set()
    merged = []
    for chunk in keyword_results:                      # keyword first (exact matches)
        chunk_id = chunk.get("id")
        if chunk_id and chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
    for chunk in vector_results:
        chunk_id = chunk.get("id")
        if chunk_id and chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
    # Sort by similarity (keyword matches have 0.80, so they'll rank high)
    merged.sort(key=lambda c: c.get("similarity", 0), reverse=True)
    return merged


def retrieve_chunks(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    threshold: float = 0.3,
    product_filter: str | None = None,
    category_filter: str | None = None,
    include_superseded: bool = False,
    _trace: dict | None = None,
) -> list[dict]:
    """Hybrid retrieval: vector search + keyword search by product model.

    1. Detects product model codes in the query (e.g. MAD-491, CAD-250).
    2. Runs vector similarity search for semantic matching.
    3. If models detected, also runs keyword search by exact model match.
    4. Merges and deduplicates results, prioritizing keyword matches.
    5. Filters out chunks whose parent document is 'superseded' / 'draft' /
       'retired' / 'needs_review' (lifecycle-aware retrieval — Phase 4 of
       document-management refactor).

    Args:
        include_superseded: if True, disables the document-status filter.
            Use only for explicit audit/history queries. Default False.

    Returns:
        List of chunk dicts with content, metadata, and similarity score.
        Each chunk may include a 'document_revision' and 'document_revision_date'
        field when the parent document is known (used by the generator for
        mandatory citation in Phase 5).
    """
    # Step 1: Detect product models in query
    models = extract_product_models(query)

    # (s91 F2-S1 · flag IDENTITY_RESOLVE=off|shadow|on, default off = prod inerte) Resolución
    # query-side del catálogo canónico gobernado — plan v2.2 + contrato §5.1 enmendado
    # (expand-only). off→passthrough; shadow→log-only; on→seam 1 (models) + seam 2 abajo.
    # UNA llamada por query (aquí, no en extract_product_models: se llama en 3 sitios).
    from src.rag import catalog_resolver as _resolver
    _n_models_pre_resolve = len(models)   # presupuesto ANTES de expandir (anti-confounder, dúo S1)
    models, _identity_res = _resolver.resolve_for_retrieval(query, models)

    # (s85, DEC-071) Query-category detection was removed here: it only ever fed the dead
    # `category` filter (chunks_v2.category = 0 canonical rows since the SWAP s44). The
    # `category_filter` param is kept for API stability but is now inert. The category
    # detection that feeds the CATALOG lives separately in the handler (telegram_bot.py,
    # CATEGORY_TERMS → get_category_models) and is untouched.

    # For comparisons (2+ models), increase top_k to get enough chunks from each model
    # (dúo S1) presupuesto por el nº de modelos PRE-expansión: si el resolver expande
    # (ZXe→3 variantes), NO multiplica top_k — separaría mal la atribución del lever
    # (¿mejora por resolver o por más presupuesto?) y cambiaría coste sin declarar.
    _n_budget = _n_models_pre_resolve if _identity_res else len(models)
    effective_top_k = top_k * _n_budget if _n_budget >= 2 else top_k

    # HyDE (TECH_DEBT #25 Fase 2): generate hypothetical manual passage and use ITS
    # embedding for vector search. Resolves vocabulary mismatch — when técnico uses
    # informal/coloquial terms ("programación", "menú avanzao") and manual uses
    # formal terminology ("AJUSTES > AVANZADO > Sistema"), the hypothesis bridges
    # the two by writing in manual style. Reference: Gao et al. 2022.
    #
    # Keyword search (Step 3) and intent search (Step 3a) keep using the original
    # query because they rely on regex matching of product model codes — those need
    # literal text, not paraphrase.
    #
    # If HyDE disabled (HYDE_ENABLED=false) or fails, falls back to the original
    # query embedding. Pre-computed ONCE and reused across all vector searches.
    embedding_text = generate_hypothetical_document(query) if HYDE_ENABLED else query
    query_embedding = embed_query(embedding_text)

    # Step 2 + 2b: Vector searches run in PARALLEL
    # Main vector channel — runs WITHOUT a category filter (s85, DEC-071: limpieza de raíz).
    # `chunks_v2.category` has been DEAD since the SWAP s44 (0 canonical rows, DEC-040):
    # filtering by it returned 0 rows for ~85% of queries, silently killing the semantic
    # channel. The fix (measured as VECTOR_NOCAT in s84, now permanent) drops the dead filter,
    # and the old broad-5 fallback (the workaround for that dead channel, DEC-040) is removed
    # with it. MERGE_STRATEGY (the merge lever) is untouched downstream.
    try:
        vector_results = vector_search(
            query, effective_top_k, threshold, product_filter, None, query_embedding,
        )
    except Exception:
        vector_results = []
    _tag_channel(vector_results, "VECTOR")

    # Step 3: Keyword search for each detected model
    keyword_results = []
    for model in models:
        kw_chunks = keyword_search(model, limit=5)
        keyword_results.extend(_tag_channel(kw_chunks, "MODEL"))

    # Step 3a-intent: Intent-based targeted search for each model
    if models:
        query_lower_intent = query.lower()

        # Specs/comparison intent → search for spec-related keywords in each model
        if SPEC_INTENT.search(query_lower_intent):
            spec_keywords = ["especificaciones", "tensión", "consumo", "temperatura", "dimensiones"]
            for model in models:
                for kw in spec_keywords:
                    spec_results = content_search(kw, limit=3, product_model=model)
                    for c in spec_results:
                        c["similarity"] = 0.85  # Boost spec matches
                    keyword_results.extend(_tag_channel(spec_results, "TARGETED"))

        # Troubleshooting intent → search for troubleshooting keywords
        if TROUBLESHOOT_INTENT.search(query_lower_intent):
            trouble_keywords = ["avería", "fallo", "problema", "diagnóstico"]
            for model in models:
                for kw in trouble_keywords:
                    trouble_results = content_search(kw, limit=3, product_model=model)
                    for c in trouble_results:
                        c["similarity"] = 0.85
                    keyword_results.extend(_tag_channel(trouble_results, "TARGETED"))

        # Wiring/installation intent → guarantee at least a few diagram chunks
        # for the model. Diagram density (~3-5% of corpus) is too low for
        # vector + keyword merges to surface any has_diagram=true chunks, so
        # the generator has nothing to cite via DIAGRAMAS_RELEVANTES. Narrow
        # to content_type='wiring' so the diagrams are ON-TOPIC (otherwise
        # the reranker correctly drops them as irrelevant — an 'off-topic
        # diagram' is worse than no diagram).
        if WIRING_INTENT.search(query):
            for model in models:
                diag_results = diagram_search(model, content_type="wiring", limit=3)
                keyword_results.extend(_tag_channel(diag_results, "TARGETED"))

    # Step 3b: Content search within detected model's chunks using query keywords + synonyms
    if models:
        query_keywords = extract_search_keywords(query)

        # Add synonym-based keywords (these get higher priority)
        synonym_keywords = []
        query_lower = query.lower()
        for phrase, synonym in QUERY_SYNONYMS.items():
            if phrase in query_lower and synonym not in query_keywords:
                synonym_keywords.append(synonym)

        for model in models:
            # Search each keyword individually
            for kw in query_keywords:
                kw_content = content_search(kw, limit=10, product_model=model)
                keyword_results.extend(_tag_channel(kw_content, "CONTENT"))

            # Synonym-based searches get boosted score (they target the actual topic)
            for kw in synonym_keywords:
                kw_content = content_search(kw, limit=10, product_model=model)
                for c in kw_content:
                    c["similarity"] = 0.85  # Boost synonym matches
                keyword_results.extend(_tag_channel(kw_content, "TARGETED"))

            # Also search for the full query text (without model) to find chunks
            # containing multiple keywords together (e.g. "fallo alimentación")
            query_no_model = MODEL_PATTERN.sub("", query).strip()
            if len(query_no_model) > 10:
                full_content = content_search(query_no_model[:60], limit=5, product_model=model)
                keyword_results.extend(_tag_channel(full_content, "CONTENT"))

    # Step 3c: Content search when no specific model is detected
    # All content_search calls run in PARALLEL to avoid sequential latency.
    if not models:
        query_lower = query.lower()

        # Collect all search tasks: (search_term, limit, boost)
        search_tasks: list[tuple[str, int, float]] = []

        # 3c-i REMOVED (s85, DEC-071): the synonym/keyword tasks here filtered no-model
        # content_search by the DEAD `category` column (0 rows since the SWAP, DEC-040) →
        # they always returned 0. Only the 3c-ii generic fallback (no category) survives.

        # 3c-ii: PCI terms generic search (broader, lower priority)
        for term, search_key in PCI_TERMS.items():
            if term in query_lower:
                search_tasks.append((search_key, 10, 0.70))
                break  # One term match is enough

        # Execute all content searches in parallel (max 6 concurrent)
        if search_tasks:
            def _run_search(task: tuple) -> list[dict]:
                term, lim, boost = task
                results = content_search(term, limit=lim)
                for c in results:
                    c["similarity"] = boost
                return results

            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = [pool.submit(_run_search, t) for t in search_tasks]
                # Iterar en orden de SUBMIT (no as_completed): mantiene el paralelismo
                # pero hace DETERMINISTA el orden de keyword_results. Con as_completed el
                # orden dependía de qué búsqueda terminaba antes → top-15 variaba run-to-run
                # (misma pregunta, respuesta distinta; ±4 facts de ruido en el eval).
                for future in futures:
                    try:
                        keyword_results.extend(_tag_channel(future.result(), "CONTENT"))
                    except Exception:
                        pass

    # (s85 B1) trace inerte: si _trace es un dict, registra la membresía por-etapa (ids) para
    # diagnosticar DÓNDE se pierde un chunk-valor. Default None → cero efecto en prod.
    def _tr(stage, chunks):
        if _trace is not None:
            _trace[stage] = {c.get("id") for c in chunks}

    _tr("channels", vector_results + keyword_results)

    # Step 4: Merge and deduplicate — extraído a _merge_channels (s68): la estrategia
    # de fusión es el LEVER bajo flag; `stamps` reproduce el comportamiento histórico
    # EXACTO (keyword-first dedup + sort por similarity).
    merged = _merge_channels(keyword_results, vector_results, effective_top_k,
                             MERGE_STRATEGY, query_embedding)
    _tr("post_merge", merged)

    # Step 4a (s86 B2 · flag NEIGHBOR_WINDOW, default OFF = prod inerte): neighbor-window /
    # parent-document expansion (cluster RECALL-INTRADOC). ANTES de superseded/model-filter
    # para que los vecinos pasen todos los filtros (dúo s86, CRÍTICO 2).
    _nw = int((os.getenv("NEIGHBOR_WINDOW", "0") or "0").strip() or "0")
    if _nw > 0:
        merged = _expand_neighbors(merged, _nw, models)
    _tr("post_neighbor", merged)

    # Step 4b: Lifecycle filter — drop chunks whose parent document is not
    # 'active' (superseded / draft / retired / needs_review). Also enriches
    # each surviving chunk with document_revision and document_revision_date
    # so the generator can cite the exact revision (Phase 5).
    if not include_superseded:
        merged = _filter_by_document_status(merged)
    _tr("post_superseded", merged)

    # Step 5a-pre: Filter to queried models (TECH_DEBT #11e + #11f fix).
    # When a specific model was mentioned in the query, drop chunks whose
    # product_model doesn't match that family. Prevents cross-product and
    # cross-brand contamination (e.g. CAD-250 chunks answering a CAD-150
    # query, or MINILÁSER 25 Notifier chunks answering an ASD535 Detnov
    # query). Fail-open: if filter would drop too many, keep originals.
    if models and len(merged) > 0:
        merged = _filter_to_query_models(
            merged, models,
            identity_allowed=(_identity_res or {}).get("allowed_sources") or None)
    _tr("post_model_filter", merged)

    # (s93 · flag IDENTITY_FETCH=on, default off; requiere IDENTITY_RESOLVE=on) fetch acotado
    # de la escalera v2.1d — diagnóstico s92: 11/12 misses = doc adjudicado que NUNCA entra
    # al top-50. APPEND puro de ≤3 chunks/doc adjudicado ausente (nunca desplaza — DEC-069;
    # el reranker decide). Fail-open total.
    if _identity_res and _resolver.fetch_enabled():
        fetched = _resolver.fetch_missing_doc_chunks(query, _identity_res, merged)
        if fetched:
            have = {c.get("id") for c in merged}
            merged = merged + [c for c in fetched if c.get("id") not in have]
            _tr("post_identity_fetch", merged)

    # Step 5a: Multi-doc diversity for queries with a specific model.
    # When a product has several source_files in corpus (e.g. CAD-250 has
    # Instalación + Usuario + MC-380 + MS-416), the top-k can be dominated
    # by whichever doc has more chunks — missing the doc that actually
    # holds the answer. Guarantee at least one chunk per source_file.
    if models and len(merged) > 0:
        # (s68, V-A′/F5) bajo `cosine` los SUPLEMENTOS del diversify también van a
        # coseno real (sin esto serían el top absoluto del re-sort interno con su
        # stamp 0.72 > cosenos 0.5x — "sin boosts" incumplido por construcción).
        supp_fn = ((lambda cs: _rescore_to_cosine(_tag_channel(cs, "SUPPLEMENT"),
                                                  query_embedding))
                   if MERGE_STRATEGY == "cosine" else None)
        merged = _diversify_by_source_file(merged, top_k, models, query, query_keywords=None,
                                           include_superseded=include_superseded,
                                           supplement_rescore_fn=supp_fn)

    # Step 5b: Manufacturer diversity for generic queries (no specific model).
    # Ensures technicians see results from ALL manufacturers, not just whichever
    # happens to rank highest by embedding similarity.
    if not models and len(merged) > 0:
        merged = _diversify_by_manufacturer(merged, top_k, query, query_embedding,
                                            include_superseded=include_superseded)

    _tr("post_diversify", merged)

    # Step 5c: Language filter — drop chunks outside the served languages
    # (ES/EN). Runs LAST so it also catches supplementary chunks added by the
    # diversity steps (which fetch fresh from the corpus). ~0.4% of chunks_v2.
    merged = _filter_by_language(merged)
    _tr("post_lang", merged)
    _tr("final", merged[:top_k])

    return merged[:top_k]


def _diversify_by_manufacturer(chunks: list[dict], top_k: int, original_query: str = "", precomputed_embedding: list[float] | None = None, include_superseded: bool = False) -> list[dict]:
    """Interleave results across manufacturers so each is fairly represented.

    Strategy: round-robin across manufacturers, ordered by their best score.
    This guarantees that if Detnov and Notifier both have relevant chunks,
    the technician sees results from both — not just the 8 nearest from one.
    """
    from collections import defaultdict

    # Group chunks by manufacturer (preserve per-manufacturer ordering by score)
    by_mfr: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        mfr = chunk.get("manufacturer", "unknown")
        by_mfr[mfr].append(chunk)

    # (s85, DEC-071) The manufacturer-diversity fetch no longer gates on category:
    # `chunks[0].category` is the DEAD column (58% NULL / 25% 'ES' / inventory labels,
    # DEC-040) → using it filtered by garbage and degraded diversity. We diversify across
    # manufacturers by query relevance, WITHOUT the dead-category filter.
    category = None

    # Find underrepresented manufacturers: absent or with < min_per_mfr
    # CATEGORY-MATCHED results (off-category results don't count)
    min_per_mfr = max(2, top_k // 4)
    all_known_mfrs = _get_all_known_manufacturers()
    underrepresented = []
    for m in all_known_mfrs:
        mfr_chunks = by_mfr.get(m, [])
        on_category = [c for c in mfr_chunks if c.get("category") == category] if category else mfr_chunks
        if len(on_category) < min_per_mfr:
            underrepresented.append(m)

    # Run supplementary searches for underrepresented manufacturers (in PARALLEL).
    # category is None (dead-column filter removed, s85) → supplement runs WITHOUT category.
    if underrepresented:
        slots_each = max(2, top_k // len(all_known_mfrs))

        def _search_mfr(mfr: str) -> tuple[str, list[dict]]:
            extra = _vector_search_by_manufacturer(
                original_query or category,
                mfr,
                category,
                limit=slots_each,
                precomputed_embedding=precomputed_embedding,
            )
            return mfr, extra

        fetched: list[tuple[str, list[dict]]] = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(_search_mfr, m) for m in underrepresented]
            # Orden de submit (no as_completed) → determinista. underrepresented viene
            # de all_known_mfrs (sorted), así que el orden es estable.
            for future in futures:
                try:
                    other_mfr, extra = future.result()
                except Exception:
                    continue
                if extra:
                    fetched.append((other_mfr, extra))

        # (s64, #46) Cinturón de LIFECYCLE sobre los suplementos ACUMULADOS
        # (1 GET batch para todos los fabricantes): los fetches frescos no
        # pasaron por el Step 4b — sin esto, docs superseded/needs_review
        # re-entran como suplemento. Se omite con include_superseded.
        if not include_superseded and fetched:
            all_extra = [c for _, extra in fetched for c in extra]
            allowed = {c.get("id") for c in _filter_by_document_status(all_extra)}
            fetched = [(m, [c for c in extra if c.get("id") in allowed])
                       for m, extra in fetched]

        for other_mfr, extra in fetched:
            if not extra:
                continue
            # Replace low-quality results (wrong category) with category-matched ones
            existing = by_mfr.get(other_mfr, [])
            category_matched = [c for c in existing if c.get("category") == category]
            # Keep category-matched originals + new supplementary results
            combined = category_matched + extra
            # Deduplicate
            seen = set()
            deduped = []
            for c in combined:
                cid = c.get("id")
                if cid not in seen:
                    seen.add(cid)
                    deduped.append(c)
            by_mfr[other_mfr] = deduped[:slots_each]

    # If still only one manufacturer after supplementary, no interleaving needed
    if len(by_mfr) <= 1:
        return chunks

    # Order manufacturers by their best chunk score (highest first)
    mfr_order = sorted(
        by_mfr.keys(),
        key=lambda m: by_mfr[m][0].get("similarity", 0) if by_mfr[m] else 0,
        reverse=True,
    )

    # Round-robin interleave
    result = []
    indices = {m: 0 for m in mfr_order}
    while len(result) < top_k:
        added_any = False
        for mfr in mfr_order:
            idx = indices[mfr]
            if idx < len(by_mfr[mfr]):
                result.append(by_mfr[mfr][idx])
                indices[mfr] = idx + 1
                added_any = True
                if len(result) >= top_k:
                    break
        if not added_any:
            break

    return result


# ---------------------------------------------------------------------------
# Model-family filter (TECH_DEBT #11e + #11f fix — 22 abril 2026)
# ---------------------------------------------------------------------------
def _filter_to_query_models(chunks: list[dict], models: list[str],
                            identity_allowed: frozenset[str] | None = None) -> list[dict]:
    """Drop chunks whose product_model doesn't match any queried model family.

    Protects against two bugs:
      #11e — retriever brings the wrong product when vector similarity surfaces
             a semantically-similar chunk from a different product. Example:
             hp003 query 'CAD-150 baterías' returned chunks from CAD-250
             Instalación (semantically close, physically wrong product).
      #11f — generator contaminates the answer with cross-brand chunks. Example:
             hp002 query 'ASD535 Detnov flujo bajo' pulled diagnosis steps from
             MIDT732 (MINILÁSER 25 Notifier), violating the user's policy
             'no inferir cross-brand'.

    Matching rule (nivel 1, histórico): normalize both the query model and the
    chunk's product_model by stripping separators (``-``, space) and
    lowercasing. A chunk passes if ANY query-model core appears as substring
    of the normalized product_model. So ``CAD-150`` matches ``CAD-150-8``
    (normalized ``cad1508``) but not ``CAD-250`` (normalized ``cad250``).

    Series-aware rule (nivel 2 — ciclo A s63, DEC-043 / TECH_DEBT #43): si
    algún modelo de la query tiene serie declarada en config/manufacturers
    (series_registry), el substring se complementa con (i) VETO de hermanos
    declarados — la query "AM-8200" deja de arrastrar los manuales de
    AM-8200G/N (cat012) — y (ii) APERTURA de docs compartidos declarados —
    la query "CAD-201" ve el manual de serie MC-380 aunque su product_model
    sea CAD-250 (DEC-032). Sin entrada de registry → nivel 1 intacto.

    Fail-open ESCALONADO: si el nivel 2 dejaría <3 chunks, se relaja a
    nivel 1 (substring sin vetos — nunca peor que el comportamiento
    histórico); si aún <3, return originals (better mixed than empty).
    """
    if not models or not chunks:
        return chunks

    # (s91 F2-S1 · seam 2, solo con IDENTITY_RESOLVE=on) UNIÓN-PROTECTORA doc_map-aware del
    # catálogo gobernado: el filtro medido (nivel-2/nivel-1/rescue) corre INTACTO y después se
    # re-incorporan los chunks YA RECUPERADOS cuyos docs están adjudicados al producto resuelto
    # y que el veto habría tirado (la clase MIE-MI-600: pm=unknown). NO reemplaza el filtro
    # (fix dúo build-S1 #1: el replace estrechaba pools corpus-wide con doc_map 861/1014 y
    # bypasseaba nivel-2) y NO es aditivo al pool (solo protege lo que el retrieval ya trajo).
    if identity_allowed:
        base = _filter_to_query_models(chunks, models, identity_allowed=None)
        seen_ids = {id(c) for c in base}
        protected = [c for c in chunks
                     if id(c) not in seen_ids and (c.get("source_file") or "") in identity_allowed]
        return base + protected

    # (s86 B2 · flag IDENTITY_MAP, default OFF = prod inerte) consumo FILTER-BASED del registro
    # canónico data-driven (índice inverso s84): filtra por membresía-de-doc del query-model
    # (subtractivo → limpia el wrong-family que el substring del tag DB no separa: afp400⊄afp4000,
    # los 4 RP1r, manuales combinados). NO aditivo (DEC-069 fue NO-OP). Fail-open escalonado: si el
    # mapa cubre el modelo y deja ≥3 → filtra; si <3 (o sin cobertura) → cae al substring/nivel-2.
    if os.getenv("IDENTITY_MAP", "").strip().lower() in ("1", "true", "yes", "on"):
        from src.rag.identity_index import allowed_sources
        allowed = allowed_sources(models)
        if allowed:
            by_map = [c for c in chunks if (c.get("source_file") or "") in allowed]
            if len(by_map) >= 3:
                return by_map

    query_cores = [_series.normalize_model(m) for m in models if m]
    if not query_cores:
        return chunks

    if _series.series_enabled() and _series.any_series(models):
        filtered = [c for c in chunks if _series.passes_nivel2(c, models)]
        if len(filtered) >= 3:
            return filtered
        # Escalón del fail-open: cae al nivel 1 (hermanos incluidos) antes
        # que al sin-filtro — nunca más sucio que el comportamiento actual.

    filtered: list[dict] = []
    for c in chunks:
        pm_norm = _series.normalize_model(c.get("product_model", ""))
        if any(core in pm_norm for core in query_cores):
            filtered.append(c)

    # s72 Brazo B (flag LEVER2_PM_RESCUE, default OFF = prod inerte): rescate de chunks
    # cuyo product_model está MAL ATRIBUIDO (TECH_DEBT #43/#18-mfr) y que este filtro
    # expulsa. Para cada modelo de la query con CERO supervivientes, recupera hasta 2
    # chunks del pool de ENTRADA cuyo SOURCE_FILE contiene el token del modelo Y cuyo
    # manufacturer == el del modelo (guarda anti-cross-brand: marca desconocida → NO
    # rescata). cat013: sirve los datasheets SDX-751 (Notifier) mis-atribuidos a
    # LOCAL-360. Append puro (no re-ordena ni re-puntúa; el reranker decide). NO toca el
    # camino nivel-2 (series) ni el fail-open de abajo.
    # Enmiendas del dúo s72: (a) SOLO source_file (no content) — matchear prosa colaba
    # referencias secundarias y, vía seed-classify, marca equivocada (inversión
    # cross-brand VESDA-X→Notifier); source_file es la señal estructurada fuerte y el
    # caso canónico machea por ahí. (b) len(core)>=4 — cores cortos (zxe/dxc/m70)
    # sub-string-matchean source_files ajenos; los modelos objetivo son >=4 (sdx751,
    # midmmi, m710, 4040).
    if os.getenv("LEVER2_PM_RESCUE", "").strip().lower() in ("1", "true", "yes", "on"):
        already = {id(c) for c in filtered}
        for m in models:
            core = _series.normalize_model(m or "")
            if len(core) < 4 or any(
                core in _series.normalize_model(c.get("product_model", ""))
                for c in filtered
            ):
                continue                       # core corto, o el modelo ya tiene supervivientes
            mfr = classify_model_manufacturer(m)
            if mfr is None:
                continue                       # marca desconocida → no rescatar
            added = 0
            for c in chunks:
                if added >= 2:
                    break
                if id(c) in already or c.get("manufacturer") != mfr:
                    continue
                if core in _series.normalize_model(c.get("source_file", "")):
                    filtered.append(c)
                    already.add(id(c))
                    added += 1

    # Fail-open: better a noisy response than an empty one
    if len(filtered) < 3:
        return chunks
    return filtered


# ---------------------------------------------------------------------------
# Language filter (política de idiomas — sesión 38)
# ---------------------------------------------------------------------------
# Idiomas que el bot sirve. El corpus indexa ES, multilingüe-con-ES y EN-only;
# el contenido SOLO en PT/FR/IT/DE se registra pero NO se sirve (un técnico
# español no puede usar un chunk solo-francés). ~0,4% de chunks_v2 es fr/de/pt.
# Filtrarlos en retrieval evita que un chunk extranjero desplace a uno servible
# o contamine la respuesta. Política: PLAN_RAG_2026 §4 (B2) + filtro diferido s30.
_SERVED_LANGUAGES = {"es", "en"}


def _filter_by_language(chunks: list[dict]) -> list[dict]:
    """Drop chunks whose language is outside the served set (ES/EN).

    Rules:
      - language in {es, en}                → KEPT
      - language NULL / missing             → KEPT (unlabeled → don't hide it)
      - any other language (fr/de/pt/it/…)  → DROPPED

    Fail-open: if filtering would leave nothing (e.g. a model documented only
    in PT), return the originals — the generator then decides whether to admit,
    rather than the retriever silently returning zero rows. Mirrors the
    fail-open of _filter_to_query_models.
    """
    if not chunks:
        return chunks
    kept = [
        c for c in chunks
        if not c.get("language") or (c.get("language") or "").lower() in _SERVED_LANGUAGES
    ]
    return kept if kept else chunks


# ---------------------------------------------------------------------------
# Multi-doc diversity (TECH_DEBT #11c fix — 22 abril 2026)
# ---------------------------------------------------------------------------
def _get_source_files_for_model(product_model: str) -> list[str]:
    """Return the distinct source_files that contain chunks of this product_model,
    ordered by chunk_count descending. Returns [] on error (fail-open)."""
    pattern = model_to_imatch_pattern(product_model)
    if not pattern:
        return []
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                headers=headers,
                params={
                    "product_model": f"imatch.{pattern}",
                    "select": "source_file",
                    "limit": "5000",
                },
            )
            resp.raise_for_status()
    except Exception:
        return []

    from collections import Counter
    c = Counter(r["source_file"] for r in resp.json() if r.get("source_file"))
    return [sf for sf, _ in c.most_common()]


def _sources_with_only_inactive_docs(source_files: list[str]) -> set[str]:
    """Sources cuyos document_id conocidos están TODOS no-activos (s64, #46).

    Pre-filtro de lifecycle para el universo de diversify: sin él, los sources
    de docs superseded son "missing eternos" que queman slots del cap de fetch
    (fetch→descarte) en cada query del producto. La identidad source→doc es
    débil (puede haber mezcla de docs o chunks legacy bajo un mismo source) →
    un source SOLO se excluye si ninguno de sus chunks es legacy (document_id
    NULL) y todos sus docs resuelven a status ≠ 'active'; cualquier ambigüedad
    lo deja pasar y el cinturón post-fetch (_filter_by_document_status) decide
    por chunk. Fail-open: error de red → set() (no se excluye nada).
    """
    if not source_files:
        return set()
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    try:
        quoted = ",".join('"' + sf.replace('"', '\\"') + '"' for sf in source_files)
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                headers=headers,
                params={
                    "source_file": f"in.({quoted})",
                    "select": "source_file,document_id",
                    "limit": "5000",
                },
            )
            resp.raise_for_status()
        docids_by_source: dict[str, set] = {}
        for r in resp.json():
            sf = r.get("source_file")
            if sf:
                docids_by_source.setdefault(sf, set()).add(r.get("document_id"))
        all_ids = {d for ids in docids_by_source.values() for d in ids if d}
        if not all_ids:
            return set()
        id_list = ",".join(f'"{d}"' for d in all_ids)
        with httpx.Client(timeout=5.0) as client:
            resp2 = client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=headers,
                params={"id": f"in.({id_list})", "select": "id,status"},
            )
            resp2.raise_for_status()
        status_by_id = {r["id"]: r.get("status") for r in resp2.json()}
        out: set[str] = set()
        for sf, ids in docids_by_source.items():
            if None in ids:  # chunk legacy → el source no es excluible
                continue
            statuses = {status_by_id.get(d) for d in ids}
            # doc no resuelto (None) → ambigüedad → no excluible (fail-open,
            # espejo de _filter_by_document_status con doc inexistente)
            if statuses and all(s is not None and s != "active" for s in statuses):
                out.add(sf)
        return out
    except Exception:
        return set()


def _get_pm_for_sources(source_files: list[str]) -> dict[str, str]:
    """product_model dominante por source_file, en UN GET (pre-filtro de series
    en diversify — ciclo A s63, FINAL §1c-2). Fail-open: {} si la consulta
    falla; un source ausente del resultado simplemente no se excluye."""
    if not source_files:
        return {}
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    quoted = ",".join('"' + sf.replace('"', '\\"') + '"' for sf in source_files)
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                headers=headers,
                params={
                    "source_file": f"in.({quoted})",
                    "select": "source_file,product_model",
                    "limit": "5000",
                },
            )
            resp.raise_for_status()
    except Exception:
        return {}

    from collections import Counter
    per_source: dict[str, Counter] = {}
    for r in resp.json():
        sf, pm = r.get("source_file"), r.get("product_model")
        if sf and pm:
            per_source.setdefault(sf, Counter())[pm] += 1
    return {sf: cnt.most_common(1)[0][0] for sf, cnt in per_source.items()}


def _content_keywords(query: str) -> list[str]:
    """Keywords de la query SIN los tokens de IDENTIDAD (modelos detectados +
    marcas del catálogo) — para búsquedas DENTRO de un doc ya fijado por
    source_file (s63, gate G3): la identidad no discrimina contenido ahí;
    'detnov' vive en los headers de todas las páginas → el FTS AND moría y el
    fallback ilike cortaba en 2 chunks genéricos sin llegar a la keyword de
    contenido ('candado'). Fail-open: si el filtro vacía la lista, devuelve
    las originales."""
    keywords = extract_search_keywords(query)
    if not keywords:
        return keywords
    model_cores = {_series.normalize_model(m) for m in extract_product_models(query)}
    mfrs = _catalog.known_manufacturers()
    content = [kw for kw in keywords
               if _series.normalize_model(kw) not in model_cores
               and kw.lower() not in mfrs]
    return content or keywords


def _fetch_top_chunks_by_source_file(
    source_file: str,
    query: str,
    limit: int = 2,
) -> list[dict]:
    """Fetch chunks from a specific source_file, ranked by relevance to query.

    Uses full-text search (plfts) on content for relevance. Falls back to
    most-similar-to-first-keyword via ilike if FTS returns nothing.

    Keywords de CONTENIDO (no identidad) — ver ``_content_keywords`` (s63).
    """
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    keywords = _content_keywords(query)
    select_cols = (
        "id,content,product_model,category,section_title,content_type,"
        "manufacturer,protocol,doc_type,language,has_diagram,diagram_url,source_file,"
        "page_number,document_id"
    )
    # Try FTS first (post spanish_unaccent fix: 'menú' matches chunks with accent)
    if keywords:
        fts_query = " & ".join(keywords[:3])
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(
                    f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                    headers=headers,
                    params={
                        "source_file": f"eq.{source_file}",
                        "search_vector": f"plfts.{fts_query}",
                        "select": select_cols,
                        "limit": str(limit),
                    },
                )
                if resp.status_code == 200:
                    rows = resp.json()
                    if rows:
                        return rows
        except Exception:
            pass

    # Fallback: ilike on each keyword (stemmed as prefix to catch conjugations)
    # e.g. keyword 'conectan' is stored as 'Conexión' / 'conecte' — so stem
    # to 'conect' (first 6 chars) and match as substring.
    for kw in keywords[:3]:
        stem = kw[:6] if len(kw) > 6 else kw  # rough stem
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(
                    f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                    headers=headers,
                    params={
                        "source_file": f"eq.{source_file}",
                        "content": f"ilike.*{stem}*",
                        "select": select_cols,
                        "limit": str(limit),
                    },
                )
                if resp.status_code == 200:
                    rows = resp.json()
                    if rows:
                        return rows
        except Exception:
            continue
    return []


# columnas completas (idénticas a los canales) + chunk_index para el neighbor-window.
_NEIGHBOR_SELECT = (
    "id,content,product_model,category,section_title,content_type,manufacturer,"
    "protocol,doc_type,language,has_diagram,diagram_url,source_file,page_number,"
    "document_id,chunk_index"
)


def _fetch_chunk_index_by_id(ids: list[str]) -> dict[str, int]:
    """id -> chunk_index (batched). El canal VECTOR (RPC match_chunks) no devuelve
    chunk_index, así que las anclas que vengan de ahí lo necesitan por lookup."""
    headers = {"apikey": SUPABASE_SERVICE_KEY,
               "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    out: dict[str, int] = {}
    for i in range(0, len(ids), 50):
        batch = [x for x in ids[i:i + 50] if x]
        if not batch:
            continue
        inlist = "(" + ",".join(batch) + ")"
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=headers,
                    params={"id": f"in.{inlist}", "select": "id,chunk_index",
                            "limit": "1000"})
                if resp.status_code in (200, 206):
                    for r in resp.json():
                        if r.get("chunk_index") is not None:
                            out[r["id"]] = r["chunk_index"]
        except Exception:
            continue
    return out


def _fetch_neighbor_chunks(source_file: str, indices: list[int]) -> list[dict]:
    """Chunks de un source_file con chunk_index ∈ indices (rango de vecinos)."""
    headers = {"apikey": SUPABASE_SERVICE_KEY,
               "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    inlist = "(" + ",".join(str(j) for j in sorted(set(indices))) + ")"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=headers,
                params={"source_file": f"eq.{source_file}",
                        "chunk_index": f"in.{inlist}",
                        "select": _NEIGHBOR_SELECT, "limit": "1000"})
            if resp.status_code in (200, 206):
                return resp.json()
    except Exception:
        pass
    return []


def _expand_neighbors(chunks: list[dict], window: int, models: list[str] | None = None) -> list[dict]:
    """(s86 B2 · flag NEIGHBOR_WINDOW, default OFF = prod inerte) Neighbor-window /
    parent-document expansion para el cluster RECALL-INTRADOC: para cada chunk-ancla,
    trae sus vecinos posicionales chunk_index ∈ [i−W, i+W] del MISMO source_file y los
    añade al pool con `similarity = sim_ancla − ε` (sortean adyacentes al ancla → sobreviven
    el corte final; CRÍTICO 1 del dúo s86). Se inserta ANTES de superseded/model-filter →
    los vecinos pasan TODOS los filtros (CRÍTICO 2). Diagnóstico: el chunk-valor bare/token-corto
    tiene baja findability propia PERO vecino findable → recall por adyacencia, ortogonal a FTS.

    Restricción a FAMILIA-OBJETIVO (s86, flag NEIGHBOR_MODELS_ONLY): si hay `models` en la
    query, SOLO se expanden anclas cuyo product_model matchea (nivel-1 substring, como
    `_filter_to_query_models`) → evita floodear el pool con vecinos de docs irrelevantes
    (broad = −29 regresiones, medido s86).
    """
    if window <= 0 or not chunks:
        return chunks
    models_only = os.getenv("NEIGHBOR_MODELS_ONLY", "").strip().lower() in ("1", "true", "yes", "on")
    query_cores = [_series.normalize_model(m) for m in (models or []) if m] if models_only else []

    def _anchor_ok(c):
        if not query_cores:
            return True
        pm = _series.normalize_model(c.get("product_model") or "")
        return any(core and core in pm for core in query_cores)

    anchors = [c for c in chunks if _anchor_ok(c)]
    if not anchors:
        return chunks
    present_ids = {c.get("id") for c in chunks if c.get("id")}
    # anclas sin chunk_index (canal vector) → backfill por lookup
    missing = [c["id"] for c in anchors
               if c.get("source_file") and c.get("chunk_index") is None and c.get("id")]
    if missing:
        idx_map = _fetch_chunk_index_by_id(missing)
        for c in anchors:
            if c.get("id") in idx_map:
                c["chunk_index"] = idx_map[c["id"]]
    # rango deseado por source_file + mejor similarity de ancla que alcanza cada índice
    wanted: dict[str, dict[int, float]] = {}
    EPS = 1e-4
    for c in anchors:
        sf, ci = c.get("source_file"), c.get("chunk_index")
        if not sf or ci is None:
            continue
        sim = c.get("similarity", 0) or 0
        bucket = wanted.setdefault(sf, {})
        for j in range(ci - window, ci + window + 1):
            if j < 0 or j == ci:
                continue
            if sim > bucket.get(j, -1):
                bucket[j] = sim
    neighbors: list[dict] = []
    for sf, idx_sims in wanted.items():
        for row in _fetch_neighbor_chunks(sf, list(idx_sims.keys())):
            rid = row.get("id")
            if not rid or rid in present_ids:
                continue
            present_ids.add(rid)
            row["similarity"] = idx_sims.get(row.get("chunk_index"), 0) - EPS
            neighbors.append(_tag_channel([row], "NEIGHBOR")[0])
    return chunks + neighbors


def _diversify_by_source_file(
    chunks: list[dict],
    top_k: int,
    models: list[str],
    original_query: str,
    query_keywords: list[str] | None = None,
    include_superseded: bool = False,
    supplement_rescore_fn=None,
) -> list[dict]:
    """Guarantee at least one chunk per source_file when a product has
    multiple docs in corpus.

    The bug this fixes (TECH_DEBT #11c): when CAD-250 has 4 manuals
    (Instalación + Usuario + MC-380 + MS-416) but the answer to a query
    lives in only one of them, the retriever's top-k can be dominated
    by chunks from an unrelated doc (the biggest one by chunk count or
    the one with highest average vector similarity). Confirmed causing
    eval fails in hp001, hp003, hp005, hp006, hp013, hp017.

    Strategy:
      1. Identify distinct source_files for each queried product_model.
      2. Check which are already present in ``chunks`` (top of current ranking).
      3. For under-represented source_files, do supplementary content_search
         filtered by (source_file) with query keywords — small boost so they
         compete with keyword results but don't override the best ones.
      4. Re-merge, deduplicate, re-sort.
    """
    if not chunks or not models:
        return chunks

    series_active = _series.series_enabled() and _series.any_series(models)

    # Identify corpus source_files for each detected model
    all_corpus_sources: list[str] = []
    for model in models:
        for sf in _get_source_files_for_model(model):
            if sf not in all_corpus_sources:
                all_corpus_sources.append(sf)

    # (s63 ciclo A, FINAL §1c-1) Los docs COMPARTIDOS declarados de las series
    # de la query entran al universo de sources: el doc de serie (p.ej. MC-380
    # para una query CAD-201) no llega ni por imatch del modelo ni —de forma
    # fiable— por recall vectorial; sin este fetch dirigido, d2 sigue cerrado
    # aunque el filtro lo permita (r2 R5/Z2, medido: pool 17/17 MI-715).
    if series_active:
        for sf in _series.shared_sources_for(models):
            if sf not in all_corpus_sources:
                all_corpus_sources.append(sf)

    # No diversification needed if models have only 1 doc total
    if len(all_corpus_sources) < 2:
        return chunks

    # Supplementary fetches for source_files NOT yet in merged
    sources_in_results: set[str] = {c.get("source_file") for c in chunks if c.get("source_file")}
    missing_sources = [sf for sf in all_corpus_sources if sf not in sources_in_results]

    # (s63 FINAL §1c-2) Pre-filtro ANTES del cap [:4]: sin él, los docs de
    # hermanos vetados queman slots de fetch (fetch→veto) y los docs legítimos
    # que vienen detrás nunca se intentan (r2 R6/Z3: 3/4 slots en cat012).
    # Fail-open: un source sin product_model conocido no se excluye.
    if series_active and missing_sources:
        shared_lower = {s.lower() for s in _series.shared_sources_for(models)}
        pm_by_source = _get_pm_for_sources(
            [sf for sf in missing_sources if sf.lower() not in shared_lower])

        def _source_allowed(sf: str) -> bool:
            if sf.lower() in shared_lower:
                return True
            pm = pm_by_source.get(sf)
            if not pm:
                return True
            return _series.passes_nivel2({"product_model": pm, "source_file": sf}, models)

        missing_sources = [sf for sf in missing_sources if _source_allowed(sf)]

    # (s64, #46) PRE-FILTRO de lifecycle del universo: los sources cuyos docs
    # están TODOS no-activos no queman slots del cap [:4] — misma lección que
    # el pre-filtro de series §1c-2 (fetch→veto desperdicia el slot y los docs
    # legítimos detrás del cap no se intentan). Identidad débil → solo se
    # excluye lo inequívoco; el cinturón de abajo corrige por chunk.
    if not include_superseded and missing_sources:
        only_inactive = _sources_with_only_inactive_docs(missing_sources)
        if only_inactive:
            missing_sources = [sf for sf in missing_sources
                               if sf not in only_inactive]

    seen_ids = {c.get("id") for c in chunks if c.get("id")}
    supplementary: list[dict] = []
    for sf in missing_sources[:4]:
        extra = _fetch_top_chunks_by_source_file(sf, original_query, limit=2)
        # (s63 FINAL §1c-3) Cinturón post-fetch: el MISMO predicado del filtro
        # sobre los suplementos (sin fail-open — el pool principal ya está).
        if series_active:
            extra = [c for c in extra if _series.passes_nivel2(c, models)]
        supplementary.extend(extra)

    # (s64, #46) Cinturón de LIFECYCLE sobre los suplementos ACUMULADOS (1 GET):
    # los fetches frescos no pasaron por el Step 4b — sin esto, un doc
    # superseded/needs_review re-entra al pool como suplemento 0.72 justo
    # después de que 4b lo filtrara (variante lifecycle del patrón F1-r1 s63).
    # Enriquece además document_revision (el generador cita revisión también
    # en suplementos). Se omite con include_superseded (consistencia con 4b).
    if not include_superseded and supplementary:
        supplementary = _filter_by_document_status(supplementary)

    for c in supplementary:
        c["similarity"] = 0.72  # competitive but won't override direct matches
    if supplement_rescore_fn:
        # (s68, V-A′/F5) bajo MERGE_STRATEGY=cosine el stamp 0.72 se sustituye por el
        # coseno real — la LÓGICA de selección/interleave de este diversify es intocable
        # (consenso dúo s59 ×2); solo se parametriza el score del suplemento inyectado.
        supplementary = supplement_rescore_fn(supplementary)
    for c in supplementary:
        cid = c.get("id")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            chunks.append(c)

    # Re-sort by similarity
    chunks.sort(key=lambda c: c.get("similarity", 0), reverse=True)

    # ROUND-ROBIN interleave: guarantees multi-source representation in top_k
    # even when one source has many high-similarity chunks. Caps per-source
    # contribution so no single doc monopolizes top_k.
    from collections import defaultdict
    by_source: dict[str, list[dict]] = defaultdict(list)
    for c in chunks:
        by_source[c.get("source_file") or "_nosrc"].append(c)

    # Best-first source order
    source_order = sorted(
        by_source.keys(),
        key=lambda s: by_source[s][0].get("similarity", 0) if by_source[s] else 0,
        reverse=True,
    )
    max_per_source = max(2, top_k // 3)  # at least 3 sources represented

    result: list[dict] = []
    indices = {s: 0 for s in source_order}
    per_source_count: dict[str, int] = defaultdict(int)

    while len(result) < top_k:
        added = False
        # Pass 1: respect max_per_source cap
        for s in source_order:
            if len(result) >= top_k:
                break
            if per_source_count[s] >= max_per_source:
                continue
            idx = indices[s]
            if idx < len(by_source[s]):
                result.append(by_source[s][idx])
                indices[s] = idx + 1
                per_source_count[s] += 1
                added = True
        if not added:
            # Pass 2: cap relaxed to fill remaining slots
            for s in source_order:
                if len(result) >= top_k:
                    break
                idx = indices[s]
                if idx < len(by_source[s]):
                    result.append(by_source[s][idx])
                    indices[s] = idx + 1
                    added = True
            if not added:
                break

    return result if result else chunks


# ---------------------------------------------------------------------------
# Lifecycle-aware filter (Phase 4 of document-management refactor)
# ---------------------------------------------------------------------------
def _filter_by_document_status(chunks: list[dict]) -> list[dict]:
    """Drop chunks whose parent document is not 'active'.

    Rules:
      - chunks with document_id == NULL → KEPT (legacy, pre-refactor data)
      - chunks whose document row has status == 'active' → KEPT
      - chunks whose document row has any other status → DROPPED
      - if the /documents query fails for any reason → KEEP ALL (fail-open:
        a retrieval failure must not silently hide answers)

    Additionally enriches each surviving chunk with:
      - document_revision (str or None)
      - document_revision_date (ISO date str or None)
      - document_status (for transparency/debugging)

    The generator (Phase 5) uses these to cite the revision in every answer.
    """
    if not chunks:
        return chunks

    # Step A: Enrich chunks that lack document_id (vector_search via the
    # match_chunks RPC doesn't return it; we need a secondary lookup).
    missing_ids = [c.get("id") for c in chunks if c.get("document_id") is None and c.get("id")]
    if missing_ids:
        try:
            headers = {
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            }
            id_list = ",".join(f'"{i}"' for i in missing_ids)
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                    headers=headers,
                    params={
                        "id": f"in.({id_list})",
                        "select": "id,document_id",
                    },
                )
                resp.raise_for_status()
            id_to_docid = {r["id"]: r.get("document_id") for r in resp.json()}
            for c in chunks:
                if c.get("document_id") is None:
                    c["document_id"] = id_to_docid.get(c.get("id"))
        except Exception:
            # Fail-open: if enrichment fails, chunks without document_id will
            # be treated as legacy and kept unfiltered.
            pass

    # Step B: Collect unique document_ids (skip chunks with no document_id → legacy)
    doc_ids: set[str] = set()
    for c in chunks:
        did = c.get("document_id")
        if did:
            doc_ids.add(did)

    if not doc_ids:
        return chunks  # all chunks are legacy, nothing to filter

    # Batch-fetch document status + revision for these ids
    try:
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        }
        # PostgREST "in.()" filter for batch lookup
        id_list = ",".join(f'"{d}"' for d in doc_ids)
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=headers,
                params={
                    "id": f"in.({id_list})",
                    "select": "id,status,revision,revision_date",
                },
            )
            resp.raise_for_status()
        docs = {row["id"]: row for row in resp.json()}
    except Exception:
        # Fail-open: if the documents table can't be queried (not migrated yet,
        # network, etc.), return all chunks untouched. Better to answer with
        # possibly-stale data than to return nothing.
        return chunks

    filtered: list[dict] = []
    for c in chunks:
        did = c.get("document_id")
        if not did:
            # Legacy chunk — keep, but no revision metadata
            filtered.append(c)
            continue
        doc = docs.get(did)
        if doc is None:
            # document_id points to a non-existent row (shouldn't happen, but
            # fail-open: keep the chunk so we don't lose data).
            filtered.append(c)
            continue
        if doc.get("status") != "active":
            # Superseded / draft / retired / needs_review — drop.
            continue
        # Enrich with revision metadata for the generator
        c["document_revision"] = doc.get("revision")
        c["document_revision_date"] = doc.get("revision_date")
        c["document_status"] = doc.get("status")
        filtered.append(c)

    return filtered


_KNOWN_MANUFACTURERS_CACHE: list[str] | None = None


def _get_all_known_manufacturers() -> list[str]:
    """Get all distinct manufacturers in the database (cached)."""
    global _KNOWN_MANUFACTURERS_CACHE
    if _KNOWN_MANUFACTURERS_CACHE is not None:
        return _KNOWN_MANUFACTURERS_CACHE

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            params={
                "select": "manufacturer",
                "limit": "200",
            },
        )
        resp.raise_for_status()

    rows = resp.json()
    _KNOWN_MANUFACTURERS_CACHE = sorted(set(
        r["manufacturer"] for r in rows
        if r.get("manufacturer") and r["manufacturer"] != "unknown"
    ))
    return _KNOWN_MANUFACTURERS_CACHE


def _vector_search_by_manufacturer(
    query_text: str,
    manufacturer: str,
    category: str,
    limit: int = 3,
    precomputed_embedding: list[float] | None = None,
) -> list[dict]:
    """Run a vector search filtered to a specific manufacturer + category.

    Uses the original user query (semantically richer than just the category name)
    to find relevant chunks from the target manufacturer within the same category.
    """

    try:
        query_embedding = precomputed_embedding or embed_query(query_text)

        payload = {
            "query_embedding": query_embedding,
            "match_threshold": 0.2,
            "match_count": limit,
            "filter_product": None,
            "filter_category": category,
            "filter_manufacturer": manufacturer,
        }

        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/match_chunks{RPC_SUFFIX}",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    return []
