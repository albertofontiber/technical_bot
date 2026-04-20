"""
Hybrid retriever: vector similarity search + keyword match by product model.
Ensures that when a technician asks about a specific model (e.g. MAD-491),
we always find the right chunks even if vector similarity alone misses them.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from ..config import SUPABASE_URL, SUPABASE_SERVICE_KEY, RETRIEVAL_TOP_K
from ..ingestion.embedder import embed_query

# Regex to detect product model codes in a query (multi-manufacturer).
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
    """Extract product model codes mentioned in the query."""
    matches = MODEL_PATTERN.findall(query)
    # Preserve order, de-duplicate, uppercase for downstream exact-logic consumers
    seen = set()
    out = []
    for m in matches:
        up = m.upper()
        if up not in seen:
            seen.add(up)
            out.append(up)
    return out


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

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/chunks",
            headers=headers,
            params={
                "product_model": f"imatch.{pattern}",
                "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,has_diagram,diagram_url,source_file,page_number,document_id",
                "limit": str(limit),
            },
        )
        resp.raise_for_status()

    rows = resp.json()
    # Lower score than content search — these are generic model matches without content relevance
    for row in rows:
        row["similarity"] = 0.65
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
            f"{SUPABASE_URL}/rest/v1/chunks",
            headers=headers,
            params={
                "product_model": f"imatch.{pattern}",
                "content_type": f"eq.{content_type}",
                "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,has_diagram,diagram_url,source_file,page_number,document_id",
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
    category: str | None = None,
) -> list[dict]:
    """Search chunks by content (+ optional model/category filters).

    When ``product_model`` is provided, we bypass the ``search_chunks_text`` RPC
    (whose ``filter_product`` clause does strict equality and silently returns
    zero rows for compound stored values like ``AM2020/AFP1010``) and hit
    PostgREST directly with ``imatch`` on ``product_model`` + ``ilike`` on
    ``content``.  Without a model, the RPC's fts ranking is still the best
    path.
    """
    headers_get = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    # Determine score: higher when filtered by model or category (more targeted)
    has_filter = product_model or category
    base_score = 0.80 if has_filter else 0.70

    # --- Path A: product_model set → skip RPC, use PostgREST imatch ---
    if product_model:
        pattern = model_to_imatch_pattern(product_model)
        if not pattern:
            return []
        params = {
            "content": f"ilike.*{search_term}*",
            "product_model": f"imatch.{pattern}",
            "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,has_diagram,diagram_url,source_file,page_number,document_id",
            "limit": str(limit),
        }
        if category:
            params["category"] = f"eq.{category}"
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(
                    f"{SUPABASE_URL}/rest/v1/chunks",
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
        "filter_category": category,
        "match_limit": limit,
    }
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/search_chunks_text",
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
        "select": "id,content,product_model,category,section_title,content_type,manufacturer,protocol,doc_type,has_diagram,diagram_url,source_file,page_number,document_id",
        "limit": str(limit),
    }
    if category:
        params["category"] = f"eq.{category}"
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/chunks",
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
            f"{SUPABASE_URL}/rest/v1/chunks",
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
    """Get all distinct manufacturers in the database."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/chunks",
            headers=headers,
            params={
                "select": "manufacturer",
                "limit": "5000",
            },
        )
        resp.raise_for_status()

    rows = resp.json()
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
            f"{SUPABASE_URL}/rest/v1/chunks",
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
            f"{SUPABASE_URL}/rest/v1/chunks",
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
            f"{SUPABASE_URL}/rest/v1/chunks",
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
            f"{SUPABASE_URL}/rest/v1/rpc/match_chunks",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()

    return resp.json()


def retrieve_chunks(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    threshold: float = 0.3,
    product_filter: str | None = None,
    category_filter: str | None = None,
    include_superseded: bool = False,
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

    # Step 1b: Detect category from query keywords
    # Check compound phrases first (longest match wins), then single words
    detected_category = category_filter
    if not detected_category:
        query_lower = query.lower()
        # Phase 1: compound phrases (more specific)
        for phrase, cat in _CATEGORY_PHRASES:
            if phrase in query_lower:
                detected_category = cat
                break
        # Phase 2: single-word fallback
        if not detected_category:
            for term, cat in CATEGORY_TERMS.items():
                if term in query_lower:
                    detected_category = cat
                    break

    # For comparisons (2+ models), increase top_k to get enough chunks from each model
    effective_top_k = top_k * len(models) if len(models) >= 2 else top_k

    # Pre-compute embedding ONCE (reused across all vector searches)
    query_embedding = embed_query(query)

    # Step 2 + 2b: Vector searches run in PARALLEL
    # (category-filtered + broad fallback)
    vector_results = []
    vector_futures = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        # Main vector search (with category filter if detected)
        vector_futures.append(pool.submit(
            vector_search, query, effective_top_k, threshold,
            product_filter, detected_category, query_embedding,
        ))
        # Broad search without category (only if category was auto-detected)
        if detected_category and not category_filter:
            vector_futures.append(pool.submit(
                vector_search, query, 5, threshold,
                product_filter, None, query_embedding,
            ))
        for f in vector_futures:
            try:
                vector_results.extend(f.result())
            except Exception:
                pass

    # Step 3: Keyword search for each detected model
    keyword_results = []
    for model in models:
        kw_chunks = keyword_search(model, limit=5)
        keyword_results.extend(kw_chunks)

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
                    keyword_results.extend(spec_results)

        # Troubleshooting intent → search for troubleshooting keywords
        if TROUBLESHOOT_INTENT.search(query_lower_intent):
            trouble_keywords = ["avería", "fallo", "problema", "diagnóstico"]
            for model in models:
                for kw in trouble_keywords:
                    trouble_results = content_search(kw, limit=3, product_model=model)
                    for c in trouble_results:
                        c["similarity"] = 0.85
                    keyword_results.extend(trouble_results)

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
                keyword_results.extend(kw_content)

            # Synonym-based searches get boosted score (they target the actual topic)
            for kw in synonym_keywords:
                kw_content = content_search(kw, limit=10, product_model=model)
                for c in kw_content:
                    c["similarity"] = 0.85  # Boost synonym matches
                keyword_results.extend(kw_content)

            # Also search for the full query text (without model) to find chunks
            # containing multiple keywords together (e.g. "fallo alimentación")
            query_no_model = MODEL_PATTERN.sub("", query).strip()
            if len(query_no_model) > 10:
                full_content = content_search(query_no_model[:60], limit=5, product_model=model)
                keyword_results.extend(full_content)

    # Step 3c: Content search when no specific model is detected
    # All content_search calls run in PARALLEL to avoid sequential latency.
    if not models:
        query_lower = query.lower()
        query_keywords = extract_search_keywords(query)

        # Collect all search tasks: (search_term, limit, category, boost)
        search_tasks: list[tuple[str, int, str | None, float]] = []

        # 3c-i: Synonym-based content search within detected category (high priority)
        if detected_category:
            for phrase, synonym in QUERY_SYNONYMS.items():
                if phrase in query_lower:
                    search_tasks.append((synonym, 10, detected_category, 0.85))

            # Also search each keyword within the category
            for kw in query_keywords:
                search_tasks.append((kw, 10, detected_category, 0.80))

        # 3c-ii: PCI terms generic search (broader, lower priority)
        for term, search_key in PCI_TERMS.items():
            if term in query_lower:
                search_tasks.append((search_key, 10, None, 0.70))
                break  # One term match is enough

        # Execute all content searches in parallel (max 6 concurrent)
        if search_tasks:
            def _run_search(task: tuple) -> list[dict]:
                term, lim, cat, boost = task
                results = content_search(term, limit=lim, category=cat)
                for c in results:
                    c["similarity"] = boost
                return results

            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = [pool.submit(_run_search, t) for t in search_tasks]
                for future in as_completed(futures):
                    try:
                        keyword_results.extend(future.result())
                    except Exception:
                        pass

    # Step 4: Merge and deduplicate (keyword results take priority)
    seen_ids = set()
    merged = []

    # Add keyword results first (they're exact matches)
    for chunk in keyword_results:
        chunk_id = chunk.get("id")
        if chunk_id and chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)

    # Add vector results
    for chunk in vector_results:
        chunk_id = chunk.get("id")
        if chunk_id and chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)

    # Sort by similarity (keyword matches have 0.80, so they'll rank high)
    merged.sort(key=lambda c: c.get("similarity", 0), reverse=True)

    # Step 4b: Lifecycle filter — drop chunks whose parent document is not
    # 'active' (superseded / draft / retired / needs_review). Also enriches
    # each surviving chunk with document_revision and document_revision_date
    # so the generator can cite the exact revision (Phase 5).
    if not include_superseded:
        merged = _filter_by_document_status(merged)

    # Step 5: Manufacturer diversity for generic queries (no specific model).
    # Ensures technicians see results from ALL manufacturers, not just whichever
    # happens to rank highest by embedding similarity.
    if not models and len(merged) > 0:
        merged = _diversify_by_manufacturer(merged, top_k, query, query_embedding)

    return merged[:top_k]


def _diversify_by_manufacturer(chunks: list[dict], top_k: int, original_query: str = "", precomputed_embedding: list[float] | None = None) -> list[dict]:
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

    # Identify the dominant category from the top results
    category = chunks[0].get("category") if chunks else None

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

    # Run supplementary searches for underrepresented manufacturers (in PARALLEL)
    if category and underrepresented:
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

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(_search_mfr, m) for m in underrepresented]
            for future in as_completed(futures):
                try:
                    other_mfr, extra = future.result()
                except Exception:
                    continue
                if extra:
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
                    f"{SUPABASE_URL}/rest/v1/chunks",
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
            f"{SUPABASE_URL}/rest/v1/chunks",
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
                f"{SUPABASE_URL}/rest/v1/rpc/match_chunks",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    return []
