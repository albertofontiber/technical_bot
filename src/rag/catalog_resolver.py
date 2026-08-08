"""(s91 F2-S1 · flag IDENTITY_RESOLVE=off|shadow|on, default off) Resolución query-side del
CATÁLOGO CANÓNICO GOBERNADO (data/catalog/*.jsonl vía catalog_store, D1 repo-first).

Plan canónico: evals/s91_f2_plan_propuesta.md v2.2 (dúo ×2 rondas) + contrato
IDENTITY_CATALOG_CONTRACT §5.1 ENMENDADO s91 (✅ Alberto): F2 = EXPAND-ONLY — la conducta
answer/clarify del bot queda intacta; clarify conduct-level va en fase posterior por-pregunta.

Mecanismo (NADA aditivo al pool — DEC-069):
  seam 1  la resolución alimenta la lista `models` de extract_product_models (patrón LEVER2,
          pero data-driven). Política por brazo (IDENTITY_RESOLVE_POLICY=add|replace, default
          add): REPLACE es el brazo MEDIDO (hp018 4/4 + regresión hp009); ADD es la hipótesis
          anti-regresión — la famtie arbitra (v2.2 §mecanismo).
  seam 2  expone `allowed_sources` (source_files vía doc_map de los ids resueltos) para el
          whitelist SUSTRACTIVO de _filter_to_query_models (patrón IDENTITY_MAP, fail-open ≥3).

Detección: regex GENERADA de los términos resolubles del catálogo (mismo approach probado que
src/rag/catalog.py::_core — separador-insensible, multi-palabra, longest-first, \\b + (?!\\d)).
Pre-exclusión SOLO normkeys digit-only ('808'/'816' — FP a priori); los alfanuméricos cortos
('zxe') PASAN: excluir ≤3 chars mataría el caso central de un código corto
(bomba cazada dúo r2). NUNCA fuzzy (DEC-074: texto-libre penaliza homónimos).

Fail-fast de flags (v2.1a): IDENTITY_RESOLVE≠off + cualquier flag legacy de identidad ON ⇒
RuntimeError al primer uso — sin precedencia silenciosa (doble expansión = medición sucia).

Shadow (F2.5 del contrato): en modo `shadow` NO muta nada; loggea a Supabase
(identity_resolve_shadow, non-blocking, patrón logging_db) qué habría cambiado + stamp del
catálogo-commit (freeze-contract; posible por el fix D1 s91).

s287 P1 (pieza 1 de la etapa 2, spec `evals/s287_etapa2_design_brief_v1.md` §v3 FINAL) —
REGLA MONÓTONA-SEGURA CORPUS-AWARE del drop: el drop del paraguas/alias bajo `replace` solo
procede si el PROPIO core del token ya NO es una etiqueta viva del corpus. Raíz de la
regresión s287 Grupo B: T3/s285 re-tagueó el corpus a FAMILIA (`pm='ZXe'`, variantes
ZX1e/ZX2e/ZX5e = 0 filas) y el drop dejaba `_filter_to_query_models` con 0 supervivientes →
fail-open → filtro de familia DESARMADO → entran los primos. La regla es MONÓTONA (solo
SUPRIME drops, nunca añade) y confina el comportamiento-ADD a las familias sin tags finos —
el riesgo DEC-091b (valor-coincidente en `zxe`⊂`zxee` vía el substring del filtro) PERSISTE
ahí y se declara, no se niega. Dependencia DB NUEVA en este módulo (era file-only): la
presencia se consulta contra la tabla de chunks (+ `documents` para excluir docs no-activos,
el criterio de vida del retriever — Sol-3); error/indisponibilidad ⇒ FAIL-OPEN a
CONSERVAR el token (nunca peor que add, coherente con el fail-open-por-unidad de la
quarantine). Los HOMÓNIMOS quedan FUERA del scope (H2: 'rp1r' tiene tag vivo y la regla
regresaría el prefer medido de hp011).
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from src.rag import catalog as C
from src.rag import series_registry as _series

ROOT = Path(__file__).resolve().parents[2]
# catalog_store es LA puerta (D1). L1/s309: graduado de scripts/ a src/rag/ — import
# RELATIVO estático (blueprint L1, retiro F4 cumplido); la mutación de sys.path que E1
# permitía queda RETIRADA (el contrato de imports exige ahora CERO mutaciones en src/).
from . import catalog_store  # noqa: E402

logger = logging.getLogger(__name__)

LEGACY_FLAGS = ("LEVER2_IDENTITY", "LEVER2_PM_RESCUE", "IDENTITY_MAP")
_MODES = ("off", "shadow", "on")

_QUARANTINE_PATH = ROOT / "config" / "identity_quarantine_v1.yaml"

_loaded = False
_pattern = None                     # regex compilada de términos resolubles
_quarantine: "frozenset[str] | None" = None   # norm_tokens en cuarentena (cache de módulo)
_cat: "catalog_store.Catalog | None" = None
_docs_by_id: dict[str, frozenset[str]] = {}   # id canónico -> source_files (doc_map)
_document_scopes_by_id: dict[str, tuple[dict[str, str], ...]] = {}
_governed_scope_owners: dict[tuple[str, str], frozenset[str]] = {}
_catalog_commit: str | None = None


def mode() -> str:
    """Modo del flag + FAIL-FAST contra flags legacy (v2.1a: error, no precedencia)."""
    m = (os.getenv("IDENTITY_RESOLVE", "") or "off").strip().lower() or "off"
    if m not in _MODES:
        raise RuntimeError(f"IDENTITY_RESOLVE={m!r} inválido (off|shadow|on)")
    if m != "off":
        on_legacy = [f for f in LEGACY_FLAGS
                     if os.getenv(f, "").strip().lower() in ("1", "true", "yes", "on")]
        if on_legacy:
            raise RuntimeError(
                f"IDENTITY_RESOLVE={m} es EXCLUYENTE con las vías legacy de identidad "
                f"({', '.join(on_legacy)} ON) — apaga una (plan v2.2 v2.1a, anti doble-expansión)")
    return m


def catalog_commit() -> str:
    """Stamp del commit del catálogo (freeze-contract, v2.1b). 'uncommitted' si hay diff local."""
    global _catalog_commit
    if _catalog_commit is None:
        try:
            h = subprocess.run(["git", "-C", str(ROOT), "log", "-n1", "--format=%h",
                                "--", "data/catalog"], capture_output=True, text=True,
                               timeout=10).stdout.strip()
            dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain",
                                    "data/catalog"], capture_output=True, text=True,
                                   timeout=10).stdout.strip()
            _catalog_commit = f"{h}+dirty" if dirty else (h or "unknown")
        except Exception:
            _catalog_commit = "unknown"
    return _catalog_commit


DETECT_ALIAS_TIPOS = {"variante-tipografica", "codigo-comercial", "numero-de-parte"}
# términos reales del catálogo que matarían la precisión en prosa (s92: el 1er replay
# sobre golds cazó 'Solo'→detectortesters en hp005; 'Dimension' colisiona con 'dimensión')
DETECT_STOPWORDS = {"solo", "dimension"}


def _resolvable_terms(cat: "catalog_store.Catalog") -> dict[str, str]:
    """normkey -> término almacenado para el DETECTOR: canonical de consumibles + alias
    MODEL-SHAPED (DETECT_ALIAS_TIPOS — los `nombre-largo` [1.465/1.741] son DESCRIPCIONES
    de la extracción: 'Solo', 'amarillo', 'CARGADOR', 'Deep Base'… válidas como metadato,
    venenosas como detector en prosa) + paraguas no-candidate + términos de homónimo
    (el homónimo DEBE detectarse para poder fail-open/prefer)."""
    terms: dict[str, str] = {}

    import re as _re

    def _add(t: str) -> None:
        nk = C.normkey(t)
        if not nk:
            return
        # pre-exclusión SOLO digit-only (v2.2: '≤3 chars' mataba zxe) — a nivel de SEGMENTOS:
        # 'normkey' conserva '+'/'.' y dejaba pasar alias tipo '2+' cuyo core regex matchea un
        # '2' suelto ("2 lazos") — el smoke S1 lo cazó
        segs = "".join(_re.findall(r"[a-z]+|\d+", C._fold(t)))
        if not segs or segs.isdigit() or nk in DETECT_STOPWORDS:
            return
        terms.setdefault(nk, t)

    for pid, p in cat.products.items():
        if p.get("estado") == "activo" and not p.get("candidate"):
            _add(p["canonical_model"])
    for a in cat.aliases:
        if a.get("candidate") or not cat._consumable(a["id"]):
            continue
        # nombre-largo: DESCRIPCIONES de la extracción — entran SOLO si son model-shaped
        # (llevan dígito: 'ASD535'/'REFLEX 20' sí; 'Solo'/'verde'/'Deep Base' no) — el
        # replay s92 perdía hp002/hp013/hp019 con la exclusión total del tipo
        if a.get("tipo") not in DETECT_ALIAS_TIPOS and not any(
                ch.isdigit() for ch in a["alias"]):
            continue
        _add(a["alias"])
    for u in cat.umbrellas:
        if not u.get("candidate"):
            _add(u["termino"])
    for h in cat.homonyms:
        _add(h["termino"])
    return terms


def _build() -> None:
    global _loaded, _pattern, _cat, _docs_by_id, _document_scopes_by_id
    global _governed_scope_owners
    _loaded = True
    try:
        cat = catalog_store.load()
    except Exception as e:                      # catálogo ausente/roto → resolver inerte
        logger.warning(f"catalog_resolver: catálogo no cargable ({e}) — fail-open total")
        return
    _cat = cat
    docs: dict[str, set[str]] = {}
    document_scopes: dict[str, dict[tuple[str, str], dict[str, str]]] = {}
    governed_scope_owners: dict[tuple[str, str], set[str]] = {}
    for dm in cat.doc_map:
        src = dm.get("source_file") or ""
        document_id = str(dm.get("document_id") or "")
        if not src or not document_id:
            continue
        for e in dm.get("entries") or []:
            product_id = cat.follow_redirect(e["id"])
            docs.setdefault(product_id, set()).add(src)
            document_scopes.setdefault(product_id, {})[(document_id, src)] = {
                "document_id": document_id,
                "source_file": src,
            }
            if e.get("role") == "primary" and e.get("scope") == "doc":
                governed_scope_owners.setdefault((document_id, src), set()).add(
                    product_id
                )
    _docs_by_id = {k: frozenset(v) for k, v in docs.items()}
    _document_scopes_by_id = {
        product_id: tuple(scopes[key] for key in sorted(scopes))
        for product_id, scopes in document_scopes.items()
    }
    _governed_scope_owners = {
        scope: frozenset(owners)
        for scope, owners in governed_scope_owners.items()
    }

    import re
    cores = []
    for nk, term in _resolvable_terms(cat).items():
        core = C._core(term)                    # mismo builder probado que el catálogo legacy
        if core:
            cores.append(core)
    cores.sort(key=len, reverse=True)           # longest-first: 'zx2se' antes que 'zx'
    seen: set[str] = set()
    alts = [c for c in cores if not (c in seen or seen.add(c))]
    if alts:
        # boundary trasero (?![a-z0-9]) — sin él, 'dimensiones' dispara el paraguas
        # 'Dimension' (reproducido por el dúo build-S1); (?!\d) solo no basta
        _pattern = re.compile(r"\b(" + "|".join(alts) + r")(?![a-z0-9])")


def _ensure() -> None:
    if not _loaded:
        _build()


def detect(query: str) -> list[str]:
    """Tokens del catálogo presentes en la query (match exacto word-boundary, folded)."""
    _ensure()
    if _pattern is None:
        return []
    folded = C._fold(query)
    out, seen = [], set()
    for m in _pattern.findall(folded):
        nk = C.normkey(m)
        if nk and nk not in seen:
            seen.add(nk)
            out.append(m)
    return out


def _quarantine_tokens() -> frozenset[str]:
    """(s278 §1a GUARD-3FILAS) norm_tokens en cuarentena: unidades del census pendientes de
    adjudicación de Alberto → su token NUNCA entra en drop_tokens (fail-open-a-add POR
    UNIDAD). Config versionada `config/identity_quarantine_v1.yaml`; keying por
    catalog_store.norm_token (el mismo del drop en apply_to_models). Carga lazy con cache
    de módulo (patrón _ensure); YAML ausente/malformado ⇒ FAIL-FAST — un fallo silencioso
    desactivaría la protección exactamente cuando importa (bajo replace)."""
    global _quarantine
    if _quarantine is None:
        import yaml
        try:
            raw = yaml.safe_load(_QUARANTINE_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            raise RuntimeError(
                f"quarantine de identidad AUSENTE: {_QUARANTINE_PATH} (config versionada "
                f"— sin ella el drop bajo replace queda sin gobierno)") from e
        except yaml.YAMLError as e:
            raise RuntimeError(
                f"quarantine de identidad MALFORMADA ({_QUARANTINE_PATH}): {e}") from e
        rows = raw.get("tokens") if isinstance(raw, dict) else None
        if not isinstance(rows, list):
            raise RuntimeError(
                f"quarantine de identidad MALFORMADA ({_QUARANTINE_PATH}): se espera un "
                f"dict con la lista 'tokens' (vacía es válida)")
        toks: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or not all(
                    row.get(k) for k in ("token", "motivo", "fecha")):
                raise RuntimeError(
                    f"quarantine de identidad MALFORMADA ({_QUARANTINE_PATH}): cada "
                    f"entrada exige token+motivo+fecha no vacíos: {row!r}")
            nk = catalog_store.norm_token(str(row["token"]))
            if not nk:
                raise RuntimeError(
                    f"quarantine de identidad MALFORMADA ({_QUARANTINE_PATH}): token "
                    f"vacío tras norm_token: {row!r}")
            toks.add(nk)
        _quarantine = frozenset(toks)
    return _quarantine


# ───────── (s287 P1) presencia de FAMILIA en el corpus — regla monótona-segura ─────────
# Semántica PINEADA por el spec v3 FINAL: EXACT-TAG POR ELEMENTO. El `product_model` del
# corpus se PARTE por los separadores de composite ('/', '+', espacio) y cada trozo se
# normaliza con LA normalización del filtro de retrieval (series_registry.normalize_model:
# quita '-'/espacio + lowercase). El core del token debe aparecer como ELEMENTO COMPLETO:
#   - NI substring: 'cad150' ⊂ 'cad1508' haría el drop INERTE tras el split D1 (H3a) — y
#     'zxe' ⊂ 'zxee' convertiría un legacy en "presencia" de la familia;
#   - NI exact-crudo: perdería los composites reales del corpus ('ZXe/ZXSe', 'ZX2e/ZX5e' —
#     el tag-familia SÍ está, como elemento) (H3b).
_PM_ELEMENT_SEP = re.compile(r"[/+\s]+")
_PRESENCE_TTL_S = 900.0          # 15 min de vida del set (F6: TTL, JAMÁS catálogo-commit)
_PRESENCE_FAIL_TTL_S = 60.0      # cooldown tras un fallo de DB (no re-pegar en cada query)
_PRESENCE_FP_RECHECK_S = 60.0    # cada cuánto se re-valida el fingerprint DENTRO del TTL
_PRESENCE_PAGE = 1000            # PostgREST capa a max-rows=1000 (lección s64/s65: paginar)
_PRESENCE_MAX_PAGES = 200        # techo duro: si no converge ⇒ EXCEPCIÓN (nunca set parcial:
                                 # un set truncado inventaría "ausencias" y dropearía de más)
_presence: dict | None = None    # {"elements": frozenset|None, "at", "fp", "fp_at"}


def _pm_elements(pm: str | None) -> set[str]:
    """Elementos exact-tag de un `product_model` del corpus (ver semántica arriba).
    'ZXe/ZXSe' → {'zxe','zxse','zxe/zxse'} · 'CAD-150-8' → {'cad1508'} · 'FAAST LT-200' →
    {'faast','lt200','faastlt200'}. (Sol-2, review 30-jul) Además de los elementos PARTIDOS
    entra la forma pm-COMPLETA normalizada: el core de un token multi-palabra del catálogo
    ('FAAST LT-200' → 'faastlt200') jamás aparecería en el split por espacio
    ({'faast','lt200'}) y el drop procedería contra su PROPIA etiqueta exacta viva."""
    out: set[str] = set()
    whole = _series.normalize_model(pm or "")
    if whole:
        out.add(whole)
    for piece in _PM_ELEMENT_SEP.split(pm or ""):
        norm = _series.normalize_model(piece)
        if norm:
            out.add(norm)
    return out


def _chunks_table() -> str:
    return os.getenv("CHUNKS_TABLE", "chunks_v2").strip() or "chunks_v2"


def _supabase_headers() -> dict[str, str]:
    from src.config import SUPABASE_SERVICE_KEY
    return {"apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def _corpus_fingerprint() -> tuple[str, str]:
    """Fingerprint BARATO del corpus (medido: 2 GETs ≈ 0,15-0,30s): count exacto +
    max(created_at) de la tabla de chunks — el mismo par que estampan los manifests de eval
    (bvg_kmajority.corpus_fingerprint). Sirve para invalidar el cache DENTRO del TTL cuando
    el corpus se mueve (re-ingesta/backfill de tags). Lanza si no es obtenible.
    HONESTIDAD (Sol-4, review 30-jul): count+max(created_at) NO detecta UPDATEs in-place de
    `product_model` (mismo count, mismo created_at) — la cota REAL de staleness es el TTL
    (900s); el fingerprint solo ACELERA la detección de ingestas/borrados. chunks_v2 NO
    tiene columna updated_at (verificado 30-jul-2026: GET select=updated_at → 42703
    «column does not exist»); si algún día existe, añadir max(updated_at) al par para
    cubrir también los UPDATEs."""
    import httpx

    from src.config import SUPABASE_URL
    url = f"{SUPABASE_URL}/rest/v1/{_chunks_table()}"
    headers = _supabase_headers()
    with httpx.Client(timeout=10.0) as client:
        r = client.get(url, headers={**headers, "Prefer": "count=exact", "Range": "0-0"},
                       params={"select": "id"})
        if r.status_code not in (200, 206):
            raise RuntimeError(f"count de corpus: HTTP {r.status_code}")
        count = (r.headers.get("content-range") or "*/?").split("/")[-1]
        r2 = client.get(url, headers=headers,
                        params={"select": "created_at", "order": "created_at.desc",
                                "limit": "1"})
        if r2.status_code not in (200, 206):
            raise RuntimeError(f"max(created_at) de corpus: HTTP {r2.status_code}")
        rows = r2.json() or [{}]
        return (str(count), str(rows[0].get("created_at")))


def _try_corpus_fingerprint() -> tuple[str, str] | None:
    """El fingerprint es un EXTRA de invalidación: si no se puede obtener, el TTL manda
    (no se degrada la presencia por eso)."""
    try:
        return _corpus_fingerprint()
    except Exception as e:                                   # noqa: BLE001
        logger.warning(f"fingerprint de corpus no disponible ({e}) — el cache de presencia "
                       f"queda gobernado SOLO por el TTL ({_PRESENCE_TTL_S:.0f}s)")
        return None


def _inactive_document_ids() -> frozenset[str] | None:
    """(Sol-3, review 30-jul) ids de `documents` NO activos — el MISMO criterio de vida que
    aplica el retriever al servir (`_filter_by_document_status`, src/rag/retriever.py): el
    join chunk→documents por `document_id` DROPEA status != 'active' (superseded / draft /
    retired / needs_review, NULL-status incluido); los chunks con document_id NULL (legacy)
    y los document_id sin fila en documents se SIRVEN. Un tag vivo SOLO en docs no-activos
    no es una etiqueta servible y no debe contar como presencia (contaría presencia de algo
    que el retriever jamás devolvería → drop suprimido de más… para siempre).
    `None` = documents NO consultable ⇒ SIN exclusión (keep-all, el mismo fail-open del
    retriever — dirección monótona-segura: la sobre-presencia solo SUPRIME drops)."""
    import httpx

    from src.config import SUPABASE_URL
    headers = _supabase_headers()
    ids: set[str] = set()
    pages = 0
    try:
        with httpx.Client(timeout=10.0) as client:
            while True:
                r = client.get(f"{SUPABASE_URL}/rest/v1/documents", headers=headers,
                               params={"select": "id",
                                       # espejo EXACTO del predicado local del retriever
                                       # `doc.get("status") != "active"` (NULL incluido)
                                       "or": "(status.neq.active,status.is.null)",
                                       "order": "id.asc",
                                       "limit": str(_PRESENCE_PAGE),
                                       "offset": str(pages * _PRESENCE_PAGE)})
                if r.status_code not in (200, 206):
                    raise RuntimeError(f"documents no-activos: HTTP {r.status_code}")
                rows = r.json()
                for row in rows:
                    did = row.get("id")
                    if did:
                        ids.add(str(did))
                pages += 1
                if len(rows) < _PRESENCE_PAGE:
                    break
                if pages >= _PRESENCE_MAX_PAGES:
                    raise RuntimeError("documents no-activos: paginación sin converger")
    except Exception as e:                                   # noqa: BLE001
        logger.warning(f"documents no consultable ({e}) — presencia SIN filtro de estado "
                       f"(keep-all, el fail-open del retriever)")
        return None
    return frozenset(ids)


def _fetch_corpus_pm_elements() -> frozenset[str]:
    """Set COMPLETO de elementos exact-tag presentes en el corpus. Paginado por offset
    (PostgREST no permite agregados en esta instancia: `PGRST123` — verificado; y el keyset
    por valor se atasca si un `pm` supera una página). TODO-o-NADA: cualquier fallo LANZA;
    el llamante fail-open a conservar. (Sol-3) las filas de documentos NO-activos se
    EXCLUYEN (mismo criterio que el retriever al servir). Medido hoy: 1 GET de documents
    no-activos (173) + 26 páginas / 25.088 filas / ~3s."""
    import httpx

    from src.config import SUPABASE_URL
    url = f"{SUPABASE_URL}/rest/v1/{_chunks_table()}"
    headers = _supabase_headers()
    inactive = _inactive_document_ids()
    elements: set[str] = set()
    pages = 0
    with httpx.Client(timeout=20.0) as client:
        while True:
            r = client.get(url, headers=headers,
                           params={"select": "product_model,document_id",
                                   # orden total = paginación estable por offset
                                   "order": "product_model.asc,id.asc",
                                   # (invariante T0 s94b) solo filas SERVIBLES: los
                                   # surrogates jamás definen la identidad del corpus
                                   "parent_id": "is.null",
                                   "limit": str(_PRESENCE_PAGE),
                                   "offset": str(pages * _PRESENCE_PAGE)})
            if r.status_code not in (200, 206):
                raise RuntimeError(f"presencia de corpus: HTTP {r.status_code}")
            rows = r.json()
            for row in rows:
                if inactive:
                    did = row.get("document_id")
                    if did and str(did) in inactive:
                        continue                 # doc no-activo: tag NO servible (Sol-3)
                elements |= _pm_elements(row.get("product_model"))
            pages += 1
            if len(rows) < _PRESENCE_PAGE:
                break
            if pages >= _PRESENCE_MAX_PAGES:
                raise RuntimeError(
                    f"presencia de corpus: paginación sin converger en "
                    f"{_PRESENCE_MAX_PAGES} páginas — set PARCIAL descartado")
    if pages > 50:
        logger.warning(f"presencia de corpus: {pages} páginas — coste creciente con el "
                       f"corpus (revisar si conviene una vista/RPC de pm distintos)")
    return frozenset(elements)


_MISS = object()                          # sentinel del lookup (None es un valor VÁLIDO del cache)
_presence_lock = threading.Lock()         # (Sol-5) anti-stampede del scan en frío


def _presence_lookup(now: float):
    """Valor cacheado vigente o `_MISS`. El re-chequeo de fingerprint DENTRO del TTL vive
    aquí (acotado a 1×/60s para no meter 2 GETs en cada query)."""
    entry = _presence
    if entry is None:
        return _MISS
    ttl = _PRESENCE_TTL_S if entry["elements"] is not None else _PRESENCE_FAIL_TTL_S
    if now - entry["at"] >= ttl:
        return _MISS
    if entry["elements"] is None or now - entry["fp_at"] < _PRESENCE_FP_RECHECK_S:
        return entry["elements"]
    fp = _try_corpus_fingerprint()
    if fp is None or fp == entry["fp"]:
        entry["fp_at"] = now
        return entry["elements"]
    logger.info(f"presencia de corpus: fingerprint cambió ({entry['fp']} → {fp}) "
                f"— recargando el set de etiquetas")
    return _MISS


def _load_presence() -> "tuple[frozenset[str] | None, tuple[str, str] | None]":
    """Scan con fingerprint HONESTO (Sol-4a, review 30-jul): el scan dura ~3-5s (26
    páginas) — una ingesta concurrente lo dejaría TORN (mitad corpus viejo, mitad nuevo =
    "ausencias" inventadas → drops de más). El fingerprint se toma ANTES y se RE-CHEQUEA AL
    ACABAR: si cambió → set descartado y 1 reintento; si vuelve a cambiar → None (fail-open
    a conservar; el cooldown _PRESENCE_FAIL_TTL_S reintenta después). Fingerprint no
    obtenible (None) ⇒ el torn no es validable — el set se acepta y manda el TTL (el
    fingerprint es un EXTRA, nunca degrada la presencia)."""
    fp = _try_corpus_fingerprint()
    for retry in (False, True):
        try:
            elements = _fetch_corpus_pm_elements()
        except Exception as e:                               # noqa: BLE001
            logger.warning(f"presencia de corpus NO consultable ({e}) — FAIL-OPEN: el drop "
                           f"de paraguas/alias queda SUPRIMIDO (nunca peor que add)")
            return None, fp
        fp_after = _try_corpus_fingerprint()
        if fp is None or fp_after is None or fp_after == fp:
            return elements, (fp_after if fp_after is not None else fp)
        logger.warning(f"presencia de corpus: el corpus se movió DURANTE el scan "
                       f"({fp} → {fp_after}) — set torn DESCARTADO"
                       + ("" if retry else "; reintento único"))
        fp = fp_after
    logger.warning("presencia de corpus: fingerprint inestable también en el reintento — "
                   "FAIL-OPEN a conservar")
    return None, fp


def corpus_pm_elements() -> frozenset[str] | None:
    """Elementos exact-tag del corpus, con cache de PROCESO. `None` = la DB no es
    consultable AHORA ⇒ el llamante debe FAIL-OPEN (conservar el token).
    Cache: TTL de 15 min + invalidación por FINGERPRINT de corpus (re-chequeo acotado a
    1×/60s). NUNCA keyed por catálogo-commit (F6: el catálogo puede no moverse y el corpus
    sí — sería un cache que miente). LAZY: la primera resolución que la necesite la paga;
    nada en import-time. (Sol-5) el scan en frío corre bajo LOCK con double-check: N
    queries concurrentes = UN solo scan (quien esperó relee el cache recién poblado);
    TECH_DEBT #58 registra el candidato a vista/RPC cuando haya volumen."""
    global _presence
    hit = _presence_lookup(time.monotonic())
    if hit is not _MISS:
        return hit
    with _presence_lock:
        hit = _presence_lookup(time.monotonic())
        if hit is not _MISS:
            return hit
        elements, fp = _load_presence()
        now = time.monotonic()
        _presence = {"elements": elements, "at": now, "fp": fp, "fp_at": now}
        return elements


def _token_core_absent_in_corpus(token: str) -> bool:
    """True SOLO si estamos SEGUROS de que el core del token NO tiene presencia exact-tag
    POR ELEMENTO en el corpus. Core vacío o DB no consultable ⇒ False = CONSERVAR."""
    core = _series.normalize_model(token or "")
    if not core:
        return False
    elements = corpus_pm_elements()
    if elements is None:
        return False
    return core not in elements


def _replace_policy() -> bool:
    """El brazo del seam 1 (IDENTITY_RESOLVE_POLICY): 'add' (default) | 'replace'."""
    return (os.getenv("IDENTITY_RESOLVE_POLICY", "") or "add").strip().lower() == "replace"


def _drop_gates_pass(tok: str, via: str | None, resolved: dict) -> bool:
    """¿Puede el token REEMPLAZARSE (entrar en `drop_tokens`)? Puertas, en orden:
    1. solo paraguas/alias/homónimo-prefer REEMPLAZAN el token original (exact ya ES el
       canonical — reemplazarlo sería un no-op);
    2. (s278 §1a GUARD-IMPL) la expansión no filtró miembros (`all_members_consumable`);
    3. (s278 §1a) la unidad no está en la quarantine de pendientes-de-adjudicación;
    4. (s287 P1) el PROPIO core del token NO tiene presencia exact-tag en el corpus.
    Las cuatro fail-open-a-add (el token se conserva y la expansión se añade igual)."""
    if via not in ("paraguas", "alias", "homonimo"):
        return False
    if not resolved.get("all_members_consumable"):
        return False
    if catalog_store.norm_token(tok) in _quarantine_tokens():
        return False
    if via == "homonimo":
        # SCOPING s287 P1 (H2): los homónimos NO pasan por la regla corpus-aware y NUNCA
        # consultan el corpus. 'rp1r' TIENE tag vivo ('RP1r-Supra' → elemento 'rp1r'), así
        # que la regla lo conservaría y regresaría el prefer MEDIDO de hp011.
        return True
    if not _replace_policy():
        # brazo add: `drop_tokens` es inerte (apply_to_models lo ignora) → no se paga la
        # consulta de corpus y el campo conserva su semántica histórica.
        return True
    return _token_core_absent_in_corpus(tok)


def resolve_query(query: str) -> dict:
    """Detecta + resuelve por la puerta. Devuelve el registro completo (para seams y shadow):
    {detected, records[{token, via, politica, expand, ids}], add_models, drop_tokens,
     allowed_sources, resolved_documents[{document_id, source_file}]}.
    expand=False (clarify/candidate/unknown) NO aporta expansión, allowed_sources ni
    documentos — el contrato `expand` del resolve() se respeta literalmente."""
    _ensure()
    detected = detect(query)
    records, add_models, drop_tokens, source_groups = [], [], [], []
    resolved_documents: list[dict[str, str]] = []
    seen_documents: set[tuple[str, str]] = set()
    allowed: set[str] = set()
    if _cat is None:
        return {"detected": detected, "records": [], "add_models": [],
                "drop_tokens": [], "allowed_sources": frozenset(),
                "source_groups": [], "resolved_documents": []}
    for tok in detected:
        r = _cat.resolve(tok)
        if r is None:
            records.append({"token": tok, "via": None, "expand": False, "ids": []})
            continue
        rec = {"token": tok, "via": r.get("via"), "politica": r.get("politica"),
               "expand": bool(r.get("expand")), "ids": r.get("ids", [])}
        records.append(rec)
        if rec["expand"]:
            record_sources: set[str] = set()
            for pid in rec["ids"]:
                p = _cat.products.get(pid)
                if p and p.get("canonical_model"):
                    add_models.append(p["canonical_model"])
                product_sources = _docs_by_id.get(pid, frozenset())
                allowed |= product_sources
                record_sources |= product_sources
                for document in _document_scopes_by_id.get(pid, ()):
                    key = (document["document_id"], document["source_file"])
                    if key not in seen_documents:
                        seen_documents.add(key)
                        resolved_documents.append(dict(document))
            if record_sources:
                source_groups.append({
                    "token": tok,
                    "ids": list(rec["ids"]),
                    "sources": sorted(record_sources),
                })
            # el drop del token original (brazo replace) pasa por las 4 puertas de
            # `_drop_gates_pass` (via-elegible · guard candidate-member s278 · quarantine
            # s278 · regla monótona-segura corpus-aware s287 P1); todas fail-open-a-add.
            if _drop_gates_pass(tok, rec["via"], r):
                drop_tokens.append(tok)
    return {"detected": detected, "records": records, "add_models": add_models,
            "drop_tokens": drop_tokens, "allowed_sources": frozenset(allowed),
            "source_groups": source_groups,
            "resolved_documents": resolved_documents}


def governed_catalog_scope_owners() -> dict[tuple[str, str], frozenset[str]]:
    """Return exact primary/document catalog scopes and their canonical owners.

    Callers receive a copy so a runtime registry validator cannot mutate the
    process-wide catalog index.  An unavailable catalog intentionally returns
    an empty mapping; a non-empty governed registry must then fail closed.
    """

    _ensure()
    return dict(_governed_scope_owners)


def apply_to_models(models: list[str], res: dict) -> list[str]:
    """Aplica la resolución a la lista `models` (seam 1). Brazo por env
    IDENTITY_RESOLVE_POLICY: 'add' (default; hipótesis anti-hp009) mantiene el token
    original Y añade variantes; 'replace' (el brazo MEDIDO de LEVER2) retira el token
    paraguas/alias resuelto. Dedup por normkey, orden estable."""
    # keying por catalog_store.norm_token (no C.normkey): C.normkey conserva '+'/'.', y un
    # match 'zx.2e' resolvería bien pero el drop fallaría silencioso (replace→add) — dúo #8
    nt = catalog_store.norm_token
    drop = {nt(t) for t in res["drop_tokens"]} if _replace_policy() else set()
    out, seen = [], set()
    for m in models:
        nk = nt(m)
        if nk in drop or nk in seen:
            continue
        seen.add(nk)
        out.append(m)
    for m in res["add_models"]:
        nk = nt(m)
        if nk not in seen:
            seen.add(nk)
            out.append(m)
    return out


def _shadow_log(query: str, models_before: list[str], models_after: list[str],
                res: dict, applied: bool) -> None:
    """Log non-blocking a Supabase (tabla identity_resolve_shadow) — F2.5. Nunca rompe el path."""
    row = {
        "query": query[:1000],
        "mode": "on" if applied else "shadow",
        "policy": (os.getenv("IDENTITY_RESOLVE_POLICY", "") or "add").strip().lower(),
        "detected": res["detected"],
        "records": json.dumps(res["records"], ensure_ascii=False)[:4000],
        "models_before": models_before,
        "models_after": models_after,
        "allowed_sources_n": len(res["allowed_sources"]),
        "catalog_commit": catalog_commit(),
    }
    def _post() -> None:
        try:
            import httpx

            from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
            headers = {"apikey": SUPABASE_SERVICE_KEY,
                       "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                       "Content-Type": "application/json", "Prefer": "return=minimal"}
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(f"{SUPABASE_URL}/rest/v1/identity_resolve_shadow",
                                   headers=headers, json=row)
                if resp.status_code >= 400:
                    logger.warning(f"identity_resolve_shadow no disponible ({resp.status_code}) "
                                   f"— S2 pierde su artefacto; registro local: "
                                   f"{json.dumps(row, ensure_ascii=False)[:500]}")
        except Exception as e:
            logger.warning(f"shadow-log fallback ({e}): {json.dumps(row, ensure_ascii=False)[:500]}")

    # fire-and-forget (dúo #5): el POST corre ANTES del vector search — 5s de timeout
    # síncrono en el path de cada query con token sería latencia real
    import threading
    threading.Thread(target=_post, daemon=True).start()


def resolve_for_retrieval(query: str, models: list[str]) -> tuple[list[str], dict | None]:
    """Punto de entrada ÚNICO del retriever (retrieve_chunks, una vez por query).
    off → passthrough exacto. shadow → passthrough + log de lo que HABRÍA cambiado.
    on → seam 1 aplicado; devuelve la resolución para el seam 2 (allowed_sources)."""
    m = mode()
    if m == "off":
        return models, None
    res = resolve_query(query)
    if not res["detected"]:
        return models, None
    models_after = apply_to_models(models, res)
    _shadow_log(query, models, models_after, res, applied=(m == "on"))
    if m == "shadow":
        return models, None
    return models_after, res


# ─────────────────────── fetch acotado (s93, escalera v2.1d MEDIDA como brazo nuevo) ───────────────────────
FETCH_PER_DOC = 3          # chunks máx por doc adjudicado (append puro — DEC-069: NUNCA desplazar)
FETCH_MAX_DOCS = 4         # docs máx por query (disciplina de coste/latencia)


def fetch_mode() -> str:
    """(s95 [D-cross-1 CRÍTICO]) Parser 3-ESTADOS de IDENTITY_FETCH: 'off' | 'on'
    (selector léxico s93, NO-OP medido DEC-084) | 'llm' (selector deep-lookup s95).
    El booleano viejo habría hecho de IDENTITY_FETCH=llm un NO-OP SILENCIOSO."""
    raw = os.getenv("IDENTITY_FETCH", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return "on"
    if raw == "llm":
        return "llm"
    if raw in ("", "0", "false", "no", "off"):
        return "off"
    raise RuntimeError(f"IDENTITY_FETCH={raw!r} no reconocido (off|on|llm) — fail-fast")


def fetch_enabled() -> bool:
    """IDENTITY_FETCH∈{on,llm} requiere IDENTITY_RESOLVE=on (config incoherente ⇒ error)."""
    f = fetch_mode() != "off"
    if f and mode() != "on":
        raise RuntimeError("IDENTITY_FETCH=on/llm requiere IDENTITY_RESOLVE=on (fail-fast)")
    return f


# F6 dúo s93: stopwords mínimas — sin ellas 'para'/'como'/'que' puntúan y queman el cap
_QSTOP = {"para", "como", "que", "qué", "con", "una", "uno", "por", "sobre", "tiene",
          "hay", "los", "las", "del", "esta", "este", "cual", "cuál", "cuando", "donde",
          "central", "panel", "detector", "sistema", "manual"}


def _score_chunk(content: str, qtokens: list[str]) -> int:
    import re as _re
    cl = (content or "").lower()
    # word-boundary (F6): 'clip' no debe puntuar dentro de 'eclipse'
    return sum(1 for t in qtokens if _re.search(rf"(?<![a-z0-9]){_re.escape(t)}(?![a-z0-9])", cl))


def fetch_missing_doc_chunks(query: str, res: dict, pool: list[dict]) -> list[dict]:
    """Diagnóstico s92: 11/12 misses = el doc adjudicado NUNCA entra al top-50 (pool-entry
    loss). Para cada doc de allowed_sources SIN chunks en el pool → trae los FETCH_PER_DOC
    chunks con mejor score léxico query-vs-content (patrón fetch_manual_chunks, sin RPC
    nuevo — limitación declarada). APPEND puro con marcador `identity_fetch` (el reranker
    decide; nunca desplaza)."""
    if not res or not res.get("allowed_sources"):
        return []
    in_pool_srcs = {(c.get("source_file") or "") for c in pool}
    missing = [s for s in sorted(res["allowed_sources"]) if s not in in_pool_srcs]
    if not missing:
        return []
    # (s95 piloto D) brazo llm: selector deep-lookup (LLM lee el outline del extraction
    # store y elige páginas) en vez del score léxico (NO-OP medido s93/DEC-084 — "los
    # appends llegan, el selector léxico no elige los chunk-ids juzgados"). Mismo seam,
    # mismos caps de docs, fail-open.
    if fetch_mode() == "llm":
        from src.rag.deep_lookup import deep_lookup
        out_llm: list[dict] = []
        for src in missing[:FETCH_MAX_DOCS]:
            try:
                out_llm.extend(deep_lookup(query, src))
            except Exception as e:
                logger.warning(f"deep_lookup fail-open ({e})")
        return out_llm
    seen_t: set[str] = set()
    qtokens = []
    for tk in re_tokens(query):
        if len(tk) >= 3 and tk not in _QSTOP and tk not in seen_t:   # F6: dedupe + stoplist
            seen_t.add(tk)
            qtokens.append(tk)
    qtokens = qtokens[:12]
    out: list[dict] = []
    try:
        import httpx

        from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
        headers = {"apikey": SUPABASE_SERVICE_KEY,
                   "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
        # F8: timeout 5.0 (patrón de la casa); F3: order=id.asc — PostgREST sin order es
        # NO-DETERMINISTA y limit=300 truncaría un set distinto por run (15088SP=342 chunks);
        # la famtie compara chunk-ids EXACTOS → el brazo debe ser reproducible
        with httpx.Client(timeout=5.0) as client:
            for src in missing[:FETCH_MAX_DOCS]:
                r = client.get(f"{SUPABASE_URL}/rest/v1/{os.getenv('CHUNKS_TABLE', 'chunks_v2')}",
                               headers=headers,
                               params={"select": "id,content,source_file,product_model,"
                                                 "page_number,language",
                                       "source_file": f"eq.{src}", "order": "id.asc",
                                       # (T0 s94b, invariante de no-servicio — CRÍTICO del
                                       # cross-model): este path appendea al pool SIN swap;
                                       # jamás debe servir surrogates, aunque IDENTITY_FETCH
                                       # esté NO-SHIP.
                                       "parent_id": "is.null",
                                       "limit": "400"})
                if r.status_code not in (200, 206):
                    continue
                rows = sorted(r.json(),
                              key=lambda c: (-_score_chunk(c.get("content"), qtokens),
                                             c.get("id") or ""))     # F3: tie-break estable
                for c in rows[:FETCH_PER_DOC]:
                    c["identity_fetch"] = True
                    out.append(c)
    except Exception as e:
        logger.warning(f"identity_fetch fail-open ({e})")
        return out
    return out


def re_tokens(q: str) -> list[str]:
    import re as _re
    return _re.findall(r"[a-záéíóúñ0-9][a-záéíóúñ0-9.-]{1,}", (q or "").lower())
