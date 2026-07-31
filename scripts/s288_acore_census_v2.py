#!/usr/bin/env python3
"""s288 A-CORE F0 — census v2 ($0, read-only, determinista 2x).

Fase F0 del spec normativo SELLADO ``evals/s288_acore_design_brief_v1.md`` (v3).
Implementa, uno a uno, los modulos F0(a)-(g):

  (a) MANIFEST DE BLOBS      -> evals/s288_acore_blob_manifest_<tag>.jsonl
  (b) PARTICION EXHAUSTIVA   -> status x clase-sha x binding x lineage x language x blob-local
  (c) GATE H1 (no-circular)  -> stem (clave independiente) -> hash -> comparar + colisiones sha
  (d) CENSUS HYQ             -> filas con padre duplicado, padres huerfanos, cobertura
  (e) DETECTOR IDIOMA v2     -> reconstruido aqui + calibracion + PROCEDENCIA de los labels
  (f) SCREENS DE SIBLINGS    -> punteros / stem-normalizado / tupla de identidad
  (g) PRE-REGISTRO DE VOLUMEN-> n exacto de elegibles P-A y P-B + listas de document_ids

HARD RULES honradas (spec §F0 + encargo):
  * DB **SELECT-only**: el unico verbo es GET de PostgREST, con paginacion ordenada por
    clave estable.  CERO escrituras, CERO RPC, CERO llamadas a modelos, CERO embeddings
    de pago.  Coste = $0 estricto.
  * Determinismo 2x: la derivacion COMPLETA corre dos veces (re-fetch incluido) y los dos
    blobs canonicos (sin timestamps) se comparan byte-identicos -> ``deterministic_2x``.
  * Los blobs de disco se hashean UNA sola vez y el manifest se reusa en ambas pasadas:
    los bytes en disco no cambian entre pasadas y re-hashear 1,5 GB duplicaria el coste
    sin anadir poder discriminante (declarado, spec §F0 + encargo).
  * Salidas restringidas al territorio de esta lane (``evals/s288_acore_*``).  El script
    NO escribe ni lee-para-modificar ningun artefacto frozen (``evals/s281_*`` intocado).
  * El repo de OneDrive se toca SOLO en LECTURA (walk + read_bytes de *.pdf).

HERENCIA declarada (encargo): de ``scripts/s281_h0_identity_census.py`` se copia el stack
GET-only (``_init_http``/``_get``/``_get_all`` con paginacion offset ordenada), el
``load_dotenv`` desde ROOT con ``CHUNKS_TABLE=chunks_v2`` forzado antes y despues, el
contrato de determinismo 2x, el freeze-contract (commit HEAD + fingerprint de corpus =
conteos + sha de los conteos ordenados) y el estilo de report.

DESVIACIONES / ELECCIONES CONSERVADORAS (declaradas, spec §F0 no las fija):
  1. **Stem case-insensitive.**  ``document_local_coverage.canonical_blob_stem`` quita
     exactamente un ``.pdf`` CASE-SENSITIVE.  En disco hay 10 blobs con extension
     ``.PDF``, que con esa regla conservarian la extension y no casarian nunca.  Aqui el
     stem (ambos lados) se deriva quitando un unico sufijo ``.pdf`` case-INSENSITIVE; la
     comparacion del cuerpo del nombre sigue siendo EXACTA (sin casefold, igual que
     ``blob_identity_match``).  El report publica cuantos doc-stems difieren entre ambas
     convenciones y cuantos pares casarian solo con casefold (informativo, NO usado).
  2. **`logs/` excluido** del manifest (encargo).  El spec §1 cita "1.334 PDFs en
     Manuales_*"; la realidad medida es 1.323 fuera de `logs/` (todos bajo `Manuales_*`)
     + 11 dentro de `logs/`.  El report publica la reconciliacion; el census usa 1.323.
  3. **`expected_sha` por documento**: ``source_pdf_sha256`` si es 64-hex real; si es
     placeholder ``backfill:*``, la ``extraction_sha256`` de sus chunks SOLO cuando es
     UNICA (single-extraction).  Placeholder multi-extraction o sin chunks -> sin sha
     esperada -> como mucho puede casar por stem (nunca dual-key, nunca elegible P-A).
  4. **binding-ok** = el doc tiene chunks Y todas sus ``extraction_sha256`` distintas
     valen exactamente ``source_pdf_sha256`` (solo aplicable a sha real 64-hex).  Se
     reporta ademas la cardinalidad de extracciones por separado.
  5. **Estratos del gate H1 definidos SOLO por stem-match** (clave independiente del
     hash).  Definirlos por dual-key haria el gate tautologico: el estrato ya asumiria la
     conclusion.  Esta es la lectura no-circular del spec §2.
  6. **P-A**: el predicado literal del spec (activo + single-extraction + dual-key +
     grupo-sha singleton per-mfr) no menciona la clase de sha.  Se publican DOS cifras:
     el predicado literal sobre todas las clases de sha, y — como VOLUMEN DEL PACKET, que
     es lo que el gate F3 compara — el subconjunto con sha placeholder, es decir las
     filas que el UPDATE cambiaria realmente (un doc con sha real ya correcto seria un
     no-op y falsearia el "aplicado == 100% de elegibles").
  7. **Muestra QA-30 de F0(e)(iii)**: este script la EMITE (estratificada, determinista,
     con extracto de contenido) pero NO la adjudica — la regla de aceptacion 30/30-o-HALT
     exige juicio humano y este instrumento es $0/read-only.  Se declara como gate ABIERTO.
  8. **Detector**: muestra los 10 primeros chunks del doc por ``(chunk_index, id)`` (el
     "≥10" del spec, tomado por su piso), sobre TODOS sus chunks (los ``duplicate_of`` no
     se excluyen: su contenido es igualmente evidencia del idioma del documento).
  9b. **FIX 3 — limpieza de INPUT (tag v3).**  Antes de contar marcadores se eliminan los
     spans ``[...]`` que el EXTRACTOR inyecta en ingles para describir figuras.  Ese texto no
     pertenece al documento: lo genera el instrumento.  En documentos ESPANOLES
     *diagram-heavy* dominaba el recuento y producia ``en`` con confianza ALTA -> P-B habria
     hecho un backfill ERRONEO (caso ``bd0c2e27`` = MI-DT-192, notifier.es, "9 AGOSTO 2013").
     **Es limpieza motivada por el MECANISMO, no tuning contra el gate**: criterio sintactico
     fijo, aplicado a TODOS los documentos, antes de contar.  A diferencia de FIX 1/2, SI
     puede cambiar el idioma detectado — es su proposito.  Conservador: solo se elimina el
     span si el corchete cierra en <= ``ANNOTATION_MAX_SPAN`` chars.  Se conserva el rastro
     literal-vs-endurecido por documento (``language_literal``, ``limpieza``,
     ``cambio_idioma_por_limpieza``).
  9. **Endurecimientos del detector — ADOPTADOS (tag v2).**  La regla de confianza literal
     del spec (>=20 marcadores Y >=2x el segundo) admitia dos falsos "alta" que el run v1
     de este mismo census CAZO con casos reales; ambos quedan cableados como FIX en
     ``detect_language`` (ver su docstring): FIX 1 supresion del token dominante (>50% del
     recuento del ganador) con degradacion a baja si el veredicto cambia al quitarlo; FIX 2
     degradacion a baja si los dos idiomas top cruzan familia (en vs romance) con margen
     < 3x.  Ambos solo pueden DEGRADAR alta->baja.  El veredicto LITERAL se sigue calculando
     y publicando (``language_literal``/``confidence_literal``) para poder auditar el delta
     v1->v2 documento a documento.  **Los artefactos ``*_v1.*`` (predicado literal) NO se
     regeneran: son el baseline.**  Ademas, los desacuerdos de calibracion se etiquetan con
     el ORIGEN del label (s282-LLM vs residual pre-s282) para separar "error del detector"
     de "error legacy" (spec riesgo 8).
 10. **La QA-30 se emite como packet legible** (``evals/s288_acore_pB_qa30_<tag>.md``) con 2
     snippets de evidencia por documento y casilla de adjudicacion, pero **NO se adjudica**:
     la regla 30/30-o-HALT exige juicio humano y este instrumento es $0/read-only.

Usage:  python scripts/s288_acore_census_v2.py [--tag v1] [--reuse-manifest]
Outputs: evals/s288_acore_census_v2_result_<tag>.json
         evals/s288_acore_census_v2_report_<tag>.md
         evals/s288_acore_blob_manifest_<tag>.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Force the production corpus BEFORE importing config (env is authority).
os.environ["CHUNKS_TABLE"] = "chunks_v2"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # re-assert after load_dotenv

import src.config as cfg  # noqa: E402

# ── constants ────────────────────────────────────────────────────────────────
BLOB_ROOT = Path(
    os.environ.get(
        "S288_BLOB_ROOT",
        r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot",
    )
)
BLOB_EXCLUDE_TOP = {"logs"}          # encargo: excluir el subdirectorio logs
LANG_SAMPLE_N = 10                   # spec F0(e): >=10 chunks por doc (piso)
LANG_HIGH_MIN_MARKERS = 20           # spec: confianza alta ⇔ >=20 marcadores ...
LANG_HIGH_MIN_RATIO = 2.0            # ... Y margen dominante >= 2x el segundo
LANG_MIN_MARKER_TYPES = 5            # informativo: tipos de marcador distintos que sostienen
                                     # el recuento del idioma ganador
# ── endurecimientos v2 del detector (ADOPTADOS tras el diagnostico del run v1) ────────
DOMINANT_TOKEN_MAX_SHARE = 0.50      # fix 1: un solo TIPO de token no puede aportar >50% del
                                     # recuento del idioma ganador; se SUPRIME como marcador y,
                                     # si al quitarlo cambia el veredicto -> confianza BAJA
CROSS_FAMILY_MIN_RATIO = 3.0         # fix 2: si los dos idiomas top CRUZAN familia (en vs
                                     # romance) y el margen es < 3x -> confianza BAJA
ROMANCE = frozenset({"es", "fr", "it", "pt"})
H1_STRATUM_N = 30                    # spec §2: n>=60 estratificada (30 + 30)
QA30_N = 30                          # spec F0(e)(iii)

_H: dict[str, str] = {}
_BASE = ""


# ── read-only HTTP helpers (inherited from s281_h0_identity_census.py) ────────
def _init_http() -> None:
    global _H, _BASE
    if not cfg.SUPABASE_URL or not cfg.SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable for the census")
    _H = {
        "apikey": cfg.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {cfg.SUPABASE_SERVICE_KEY}",
    }
    _BASE = cfg.SUPABASE_URL.rstrip("/")


def _get(table: str, params: dict[str, str], *, count: bool = False) -> httpx.Response:
    headers = dict(_H)
    if count:
        headers["Prefer"] = "count=exact"
    resp = httpx.get(f"{_BASE}/rest/v1/{table}", headers=headers, params=params, timeout=180)
    resp.raise_for_status()
    return resp


def _get_all(table: str, select: str, *, order: str, page: int = 1000) -> list[dict[str, Any]]:
    """Deterministic full-table read via ordered offset pagination (s281 stack)."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {"select": select, "order": order, "limit": str(page), "offset": str(offset)}
        batch = _get(table, params).json()
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return rows


def _stable_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ── corpus fingerprint (patron s281: conteos + sha de los conteos ordenados) ──
def _count(table: str) -> int:
    resp = _get(table, {"select": "id", "limit": "1"}, count=True)
    return int(resp.headers.get("content-range", "*/0").split("/")[-1])


def _count_and_max(table: str, ts_col: str) -> tuple[int, Any]:
    total = _count(table)
    mx_resp = _get(table, {"select": ts_col, "order": f"{ts_col}.desc.nullslast", "limit": "1"})
    rows = mx_resp.json()
    return total, (rows[0][ts_col] if rows else None)


def corpus_fingerprint() -> dict[str, Any]:
    c_total, c_max = _count_and_max("chunks_v2", "created_at")
    d_total, d_max = _count_and_max("documents", "ingested_at")
    h_total = _count("chunks_v2_hyq")
    payload = {
        "chunks_v2": {"count": c_total, "max_created_at": c_max},
        "chunks_v2_hyq": {"count": h_total},
        "documents": {"count": d_total, "max_ingested_at": d_max},
    }
    return {**payload, "sha256": _stable_sha256(payload)}


# ── (a) MANIFEST DE BLOBS ─────────────────────────────────────────────────────
def _pdf_stem(name: str) -> str:
    """Quita UN sufijo '.pdf' case-INSENSITIVE (desviacion #1 del docstring)."""
    text = str(name or "")
    if text.lower().endswith(".pdf"):
        return text[:-4]
    return text


def build_blob_manifest(root: Path) -> dict[str, Any]:
    """Recorre `root` recursivo, hashea cada *.pdf (excepto bajo `logs/`).

    Determinista: el walk se ordena y la lista final se ordena por path relativo
    POSIX.  Se ejecuta UNA vez y se reusa en ambas pasadas (declarado).
    """
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    # Conteo de los PDF EXCLUIDOS (solo nombres, sin hashear) para poder publicar la
    # reconciliacion con el "1.334" del spec §1.
    skipped_logs = 0
    for top in sorted(BLOB_EXCLUDE_TOP):
        excluded = root / top
        if excluded.is_dir():
            for _dp, _dn, fns in os.walk(excluded):
                skipped_logs += sum(1 for f in fns if f.lower().endswith(".pdf"))
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        parts = rel_dir.parts
        # poda: no descender bajo un top-level excluido
        dirnames[:] = sorted(
            d for d in dirnames
            if not (len(parts) == 0 and d.lower() in BLOB_EXCLUDE_TOP)
        )
        for fname in sorted(filenames):
            if not fname.lower().endswith(".pdf"):
                continue
            fpath = Path(dirpath) / fname
            try:
                data = fpath.read_bytes()
            except OSError as exc:  # OneDrive placeholder / lock / permiso
                entries.append({
                    "rel_path": (rel_dir / fname).as_posix(),
                    "stem": _pdf_stem(fname),
                    "sha256": None,
                    "size": None,
                    "read_error": type(exc).__name__,
                })
                continue
            total_bytes += len(data)
            entries.append({
                "rel_path": (rel_dir / fname).as_posix(),
                "stem": _pdf_stem(fname),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
                "read_error": None,
            })
    entries.sort(key=lambda e: e["rel_path"])
    return {
        "entries": entries,
        "n_blobs": len(entries),
        "n_read_errors": sum(1 for e in entries if e["read_error"]),
        "n_pdf_skipped_under_logs": skipped_logs,
        "total_bytes": total_bytes,
        "root": str(root),
    }


def index_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Indices MULTI-VALOR por stem y por sha (hay 149 stems duplicados en disco)."""
    by_stem: dict[str, list[dict[str, Any]]] = {}
    by_sha: dict[str, list[dict[str, Any]]] = {}
    for e in manifest["entries"]:
        by_stem.setdefault(e["stem"], []).append(e)
        if e["sha256"]:
            by_sha.setdefault(e["sha256"], []).append(e)
    return {"by_stem": by_stem, "by_sha": by_sha}


# ── (e) DETECTOR DE IDIOMA v2 (reconstruido AQUI — no se importa el audit legacy) ──
# Marcadores fuertes por idioma.  Se INSPIRAN en las listas de
# scripts/audit_chunk_languages.py:89-95 (STRONG_MARKERS) pero el modulo NO se
# importa ni se invoca (lee la tabla `chunks` legacy y muestrea 3 chunks: spec §1
# lo declara "SOLO como referencia").
STRONG_MARKERS: dict[str, frozenset[str]] = {
    "es": frozenset({"el", "que", "los", "se", "por", "para", "del", "las", "una",
                     "como", "pero", "este", "esta", "con", "es", "son", "sus", "mas"}),
    "en": frozenset({"the", "of", "and", "to", "is", "that", "for", "with", "as",
                     "was", "on", "by", "are", "this", "from", "or", "which", "be"}),
    "pt": frozenset({"que", "do", "da", "nao", "os", "uma", "na", "dos", "sao",
                     "das", "no", "ao", "mas", "foi", "pelo", "pela", "esta", "com"}),
    "it": frozenset({"il", "che", "per", "una", "sono", "come", "lo", "le",
                     "anche", "questo", "nel", "della", "gli", "con", "di", "non"}),
    "fr": frozenset({"le", "et", "les", "des", "du", "est", "que", "pour", "une",
                     "dans", "au", "avec", "pas", "sur", "ne", "par", "plus", "ce"}),
}
LANG_UNIVERSE = tuple(sorted(STRONG_MARKERS))  # ('en','es','fr','it','pt')

_WORD_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_ACCENTS = str.maketrans("áàäâãéèëêíìïîóòöôõúùüûñç", "aaaaaeeeeiiiiooooouuuunc")


def _tokenize(text: str) -> list[str]:
    text = (text or "")
    for marker in ("[CONTENIDO VISUAL]", "[TABLA EXTRAÍDA]", "[TABLA EXTRAIDA]"):
        text = text.replace(marker, " ")
    return [m.group(0).lower().translate(_ACCENTS) for m in _WORD_RE.finditer(text)]


# ── FIX 3: limpieza de ANOTACIONES DEL EXTRACTOR (limpieza de INPUT) ──────────
# El extractor inyecta descripciones de figuras EN INGLES dentro del `content`, entre
# corchetes: "[Diagram showing CAB-IDA1 enclosure - a gray rectangular box...]",
# "[Exploded view diagram showing assembly...]", "[Grid paper...]".  Ese texto NO es del
# documento: es del INSTRUMENTO.  En documentos ESPANOLES diagram-heavy llega a dominar el
# recuento y produce `en` con confianza ALTA — caso resuelto por Alberto leyendo la DB:
# bd0c2e27 = MI-DT-192 (notifier.es, "9 AGOSTO 2013") es ESPANOL y salia `en/alta`; sin
# este fix P-B habria escrito `en` en documentos espanoles (backfill ERRONEO).
#
# Es una limpieza de INPUT motivada por el MECANISMO (el texto no pertenece al documento),
# NO un tuning contra el gate: se elimina la misma clase de span en TODOS los documentos,
# antes de contar, sin mirar el resultado de la calibracion.  A diferencia de FIX 1/2, este
# SI puede cambiar el IDIOMA detectado — ese es exactamente su proposito.
#
# Conservador: un span solo se elimina si el corchete CIERRA dentro de ANNOTATION_MAX_SPAN
# caracteres (multi-linea permitido).  Un `[` sin cierre cercano se deja INTACTO.
ANNOTATION_MAX_SPAN = 500
_ANNOTATION_RE = re.compile(r"\[[\s\S]{0,%d}?\]" % ANNOTATION_MAX_SPAN)


def strip_extractor_annotations(text: str) -> tuple[str, int, int]:
    """Devuelve (texto_limpio, n_anotaciones_eliminadas, chars_eliminados)."""
    n = 0
    removed = 0

    def _sub(m: re.Match) -> str:
        nonlocal n, removed
        n += 1
        removed += len(m.group(0))
        return " "

    return _ANNOTATION_RE.sub(_sub, str(text or "")), n, removed


# Pista ADVISORY (solo para el packet QA-30): tokens de idioma en el NOMBRE del fichero.
# No entra en ningun veredicto — es una ayuda al humano para cazar el blind spot declarado
# (documentos multi-idioma que el detector no degrada porque el 2o idioma es romance).
_STEM_LANG_TOKEN_RE = re.compile(
    r"(?<![a-z])(es|en|gb|uk|us|fr|it|pt|de|nl|pl|ru|ml|ita|eng|spa|fra|ger|por)(?![a-z])",
    re.IGNORECASE)


def stem_multilang_hint(stem: str) -> list[str]:
    toks = sorted({t.lower() for t in _STEM_LANG_TOKEN_RE.findall(str(stem or ""))})
    return toks if len(toks) >= 2 else []


def _rank(hits: dict[str, int]) -> list[tuple[str, int]]:
    # Desempate por orden alfabetico de idioma (determinismo).
    return sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))


def detect_language(text: str) -> dict[str, Any]:
    """Detector determinista por marcadores fuertes, ENDURECIDO (v2).

    Base (spec F0(e)): alta ⇔ (marcadores del dominante >= LANG_HIGH_MIN_MARKERS) Y
    (dominante >= LANG_HIGH_MIN_RATIO x el segundo).  Sobre esa base se aplican los DOS
    endurecimientos adoptados tras el diagnostico del run v1 (ambos solo pueden DEGRADAR
    alta->baja; ninguno puede promover baja->alta):

    FIX 1 — token dominante.  Un solo TIPO de token que aporte > DOMINANT_TOKEN_MAX_SHARE
    del recuento del idioma ganador se SUPRIME como marcador en TODOS los idiomas (es un
    token no discriminante en este documento: nombre de producto, cabecera repetida...).
    Se re-decide sobre el recuento depurado; si el veredicto (idioma, alta/baja) CAMBIA al
    quitarlo, la confianza cae a BAJA.  Caso real: 36x ``plus`` (de ``NFS-2 PLUS``) en una
    tabla de equivalencias ESPANOLA daba ``fr/alta``.

    FIX 2 — cruce de familia.  Si los dos idiomas top cruzan familia (exactamente uno es
    ``en``, el otro romance) y el margen es < CROSS_FAMILY_MIN_RATIO, la confianza cae a
    BAJA: es el patron del documento MIXTO (spec §F1 P-B: "mixto -> NULL se queda").  Caso
    real: manual ``..._ES_GB_...`` con 168 ``en`` vs 83 ``es`` (ratio 2.02) daba ``en/alta``.
    Entre romances NO se aplica: alli el 2o puesto es SANGRADO de marcadores compartidos
    (``con``/``una``/``no``/``que`` viven a la vez en es/it/pt), no bilinguismo.
    Blind spot DECLARADO: un documento es+it realmente mixto no se degrada por esta via.

    FIX 3 — limpieza de INPUT (anotaciones del extractor).  Antes de contar se eliminan los
    spans ``[...]`` que el extractor inyecta EN INGLES para describir figuras (ver
    ``strip_extractor_annotations``).  A diferencia de FIX 1/2, este SI puede cambiar el
    IDIOMA detectado: ese es su proposito.  Motivado por el MECANISMO (ese texto no
    pertenece al documento), no por el resultado del gate.

    Trazabilidad: ``*_literal`` = veredicto de la regla LITERAL del spec sobre el texto CRUDO
    (baseline v1, intacto); ``language_sin_limpieza`` = ganador sobre el texto crudo sin
    FIX 1/2, para poder atribuir a FIX 3 los cambios de idioma.
    """
    # -- veredicto LITERAL del spec sobre el texto CRUDO (baseline v1, no se toca) --
    tokens_raw = _tokenize(text)
    c_raw = Counter(tokens_raw)
    raw_hits = {lang: sum(c_raw[w] for w in STRONG_MARKERS[lang]) for lang in LANG_UNIVERSE}
    raw_ranked = _rank(raw_hits)
    raw_top_lang, raw_top = raw_ranked[0]
    raw_second = raw_ranked[1][1]
    raw_high = (raw_top >= LANG_HIGH_MIN_MARKERS) and (raw_top >= LANG_HIGH_MIN_RATIO * raw_second)

    # -- FIX 3: limpiar las anotaciones del extractor y re-tokenizar --
    cleaned_text, n_annot, chars_annot = strip_extractor_annotations(text)
    tokens = _tokenize(cleaned_text)
    c = Counter(tokens)

    def _hits(exclude: frozenset[str] = frozenset()) -> dict[str, int]:
        return {lang: sum(c[w] for w in STRONG_MARKERS[lang] if w not in exclude)
                for lang in LANG_UNIVERSE}

    clean_hits = _hits()
    clean_ranked = _rank(clean_hits)
    clean_top_lang, clean_top = clean_ranked[0]
    clean_second = clean_ranked[1][1]
    clean_high = (clean_top >= LANG_HIGH_MIN_MARKERS) and (clean_top >= LANG_HIGH_MIN_RATIO * clean_second)

    base = {
        "hits_literal": raw_hits,
        "tokens": len(tokens),
        "tokens_crudos": len(tokens_raw),
        "language_literal": raw_top_lang if raw_top else None,
        "confidence_literal": "alta" if (raw_high and raw_top) else "baja",
        "language_sin_limpieza": raw_top_lang if raw_top else None,
        "limpieza": {"n_anotaciones": n_annot, "chars_eliminados": chars_annot,
                     "pct_chars_eliminados": (round(100 * chars_annot / len(str(text or "")), 2)
                                              if text else 0.0)},
        "language_tras_limpieza": clean_top_lang if clean_top else None,
        "cambio_idioma_por_limpieza": bool(
            (clean_top_lang if clean_top else None) != (raw_top_lang if raw_top else None)),
    }

    if clean_top == 0:
        return {**base, "language": None, "confidence": "baja", "hits": clean_hits,
                "reason": "sin_marcadores_tras_limpieza" if raw_top else "sin_marcadores",
                "tipos_marcador": 0, "margin_ratio": None,
                "segundo_idioma": None, "segundo_marcadores": 0,
                "tokens_dominantes_suprimidos": [],
                "degradado_por_token_dominante": False,
                "degradado_por_familia_cruzada": False}

    # -- FIX 1: suprimir tipos de token dominantes y re-decidir (sobre el texto LIMPIO) --
    dominante = frozenset(sorted(
        w for w in STRONG_MARKERS[clean_top_lang]
        if c[w] > DOMINANT_TOKEN_MAX_SHARE * clean_top))
    hits = _hits(dominante) if dominante else clean_hits
    ranked = _rank(hits)
    top_lang, top_hits = ranked[0]
    second_lang, second_hits = ranked[1]

    if top_hits == 0:
        # todo el recuento lo sostenia el token suprimido -> sin evidencia utilizable
        return {**base, "language": None, "confidence": "baja", "hits": hits,
                "reason": "solo_token_dominante", "tipos_marcador": 0, "margin_ratio": None,
                "segundo_idioma": None, "segundo_marcadores": 0,
                "tokens_dominantes_suprimidos": sorted(dominante),
                "degradado_por_token_dominante": True,
                "degradado_por_familia_cruzada": False}

    high = (top_hits >= LANG_HIGH_MIN_MARKERS) and (top_hits >= LANG_HIGH_MIN_RATIO * second_hits)
    ratio = (top_hits / second_hits) if second_hits else None

    # FIX 1 (cont.): el veredicto cambio al suprimir el token -> no es robusto
    deg_token = bool(dominante) and ((top_lang, high) != (clean_top_lang, clean_high))
    # FIX 2: cruce de familia con margen estrecho
    cross_family = ((top_lang == "en") != (second_lang == "en")) and second_hits > 0
    deg_family = bool(high and cross_family and ratio is not None
                      and ratio < CROSS_FAMILY_MIN_RATIO)

    confidence = "alta" if (high and not deg_token and not deg_family) else "baja"
    if high and deg_token:
        reason = "veredicto_cambia_sin_token_dominante"
    elif high and deg_family:
        reason = "familia_cruzada_margen_estrecho"
    elif high:
        reason = "ok"
    elif top_hits < LANG_HIGH_MIN_MARKERS:
        reason = "pocos_marcadores"
    else:
        reason = "margen_insuficiente"

    return {
        **base,
        "language": top_lang,
        "confidence": confidence,
        "hits": hits,
        "margin_ratio": round(ratio, 3) if ratio is not None else None,
        "reason": reason,
        "tipos_marcador": sum(1 for w in STRONG_MARKERS[top_lang]
                              if c[w] and w not in dominante),
        "segundo_idioma": second_lang if second_hits else None,
        "segundo_marcadores": second_hits,
        "tokens_dominantes_suprimidos": sorted(dominante),
        "degradado_por_token_dominante": deg_token,
        "degradado_por_familia_cruzada": deg_family,
    }


# ── (e) PROCEDENCIA de los labels de `documents.language` (scan del repo) ──────
_LANG_WRITE_PATTERNS = [
    re.compile(r"UPDATE\s+(?:public\.)?documents\b[\s\S]{0,400}?\blanguage\s*=", re.IGNORECASE),
    re.compile(r"INSERT\s+INTO\s+(?:public\.)?documents\b[^;]{0,400}?\blanguage\b", re.IGNORECASE),
    re.compile(r"[\"']language[\"']\s*:"),
    re.compile(r"\blanguage\s*=\s*[\"'][a-z]{2}[\"']"),
]
_LANG_SCAN_DIRS = ("scripts/migrations", "supabase/migrations", "migrations", "scripts",
                   "src/ingestion", "src/reingest")
_LANG_SCAN_EXT = {".py", ".sql"}

# El escritor DOMINANTE identificado (verificado regla-C, ver PROVENANCE_VERDICT):
# el paquete s282 "Tramo 2" (fill-only COALESCE, guard `language_set <> 301`).
S282_T2_MANIFEST = ROOT / "evals/s282_t2_manifest_v1.json"


def scan_language_label_provenance() -> dict[str, Any]:
    """Grep determinista (en Python) de escritores de `documents.language` en el repo.

    Emite anclas fichero:linea REPRODUCIBLES.  Es evidencia, no veredicto: el veredicto
    narrado se publica aparte y declara honestamente lo que NO es determinable.
    """
    hits: list[dict[str, Any]] = []
    seen_files: set[Path] = set()
    self_path = Path(__file__).resolve()
    for rel in _LANG_SCAN_DIRS:
        base = ROOT / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in _LANG_SCAN_EXT or not path.is_file():
                continue
            # dedup: `scripts` y `scripts/migrations` se solapan; y este mismo script
            # menciona `documents`+`language` por todas partes (auto-referencia = ruido).
            resolved = path.resolve()
            if resolved in seen_files or resolved == self_path:
                continue
            seen_files.add(resolved)
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "language" not in text:
                continue
            # solo ficheros que mencionan la tabla documents (acota el ruido)
            if "documents" not in text:
                continue
            lines = text.splitlines()
            for i, line in enumerate(lines, 1):
                if "language" not in line:
                    continue
                window = "\n".join(lines[max(0, i - 12):i + 4])
                if not any(p.search(window) for p in _LANG_WRITE_PATTERNS):
                    continue
                hits.append({
                    "file": path.relative_to(ROOT).as_posix(),
                    "line": i,
                    "text": line.strip()[:160],
                })
    hits.sort(key=lambda h: (h["file"], h["line"]))
    by_file = Counter(h["file"] for h in hits)
    return {
        "scanned_dirs": list(_LANG_SCAN_DIRS),
        "n_hits": len(hits),
        "hits_by_file": dict(sorted(by_file.items())),
        "hits": hits[:120],
        "truncated": len(hits) > 120,
    }


def load_s282_t2_manifest() -> list[dict[str, Any]]:
    """Filas del manifest del paquete s282 T2 (escritor dominante candidato)."""
    if not S282_T2_MANIFEST.exists():
        return []
    data = json.loads(S282_T2_MANIFEST.read_text(encoding="utf-8"))
    return [r for r in data.get("rows", []) if r.get("document_id")]


def cross_s282_manifest(t2_rows: list[dict[str, Any]],
                        live_lang: dict[str, str | None]) -> dict[str, Any]:
    """Reconcilia el manifest s282 T2 contra los labels VIVOS (cierra la procedencia).

    El paquete emite `language = COALESCE(d.language, s.language)` (fill-only) con guard
    duro `language_set <> 301` (evals/s282_t2_apply_v1.sql:590-596 y :614).  Si las 301
    filas con idioma del manifest valen HOY exactamente ese idioma y 0 siguen NULL, el
    paste se ejecuto -> la procedencia deja de ser inferencia y pasa a hecho medido.
    """
    if not t2_rows:
        return {"available": False}
    with_lang = [r for r in t2_rows if r.get("language")]
    match = sum(1 for r in with_lang if live_lang.get(str(r["document_id"])) == r["language"])
    still_null = sum(1 for r in with_lang if live_lang.get(str(r["document_id"])) is None)
    n_live_labeled = sum(1 for v in live_lang.values() if v)
    manifest_ids = {str(r["document_id"]) for r in with_lang}
    residual = {k: v for k, v in live_lang.items() if v and k not in manifest_ids}
    return {
        "available": True,
        "manifest_path": S282_T2_MANIFEST.relative_to(ROOT).as_posix(),
        "manifest_sha256_lf": _sha256_lf(S282_T2_MANIFEST),
        "n_rows": len(t2_rows),
        "n_rows_con_language": len(with_lang),
        "n_match_en_vivo": match,
        "n_siguen_null": still_null,
        "n_distinto": len(with_lang) - match - still_null,
        "aplicado": bool(with_lang) and match == len(with_lang) and still_null == 0,
        "distribucion_manifest": dict(sorted(Counter(r["language"] for r in with_lang).items())),
        "n_labels_vivos": n_live_labeled,
        "n_labels_residuales_pre_s282": len(residual),
        "distribucion_residual": dict(sorted(Counter(residual.values()).items())),
    }


# ── (f) normalizacion de stem para el screen de siblings ──────────────────────
_SEPARATORS_RE = re.compile(r"[^a-z0-9]+")
_REV_PATTERNS = [
    re.compile(r"\b(?:19|20)\d{2} (?:0[1-9]|1[0-2])\b"),   # AAAA/MM (separador ya normalizado)
    re.compile(r"\bv ?\d+(?: \d+)*\b"),                     # v2, v.3, v 1.2
    # `rev` + token CORTO: exigir <=4 alfanumericos evita tragarse palabras reales
    # ("reversible", "revision") que el patron literal `rev\.?\s*\w+` del spec si tragaria
    # -> crearia colisiones FALSAS.  Desviacion conservadora declarada.
    re.compile(r"\brev ?[a-z0-9]{1,4}\b"),                  # rev A, rev.02, rev 007
    re.compile(r"\bissue ?\d+\b"),                          # issue 3
    re.compile(r"\br\d{3}\b"),                              # r001
]
_LANG_SUFFIX_RE = re.compile(
    r" (?:es|en|fr|de|pt|it|ml|gb|us|uk|nl|pl|sv|da|no|fi|cz|hu|ro|tr|ru|eng|spa|ita|fra|ger|por)$"
)


def normalize_stem_for_screen(stem: str) -> str:
    """Stem normalizado para el screen (f)(ii): separadores -> espacio, luego strip de
    tokens de revision/fecha y de sufijos de idioma (apilados), luego colapso a [a-z0-9].

    El paso 1 (separadores -> espacio) es OBLIGATORIO antes de los patrones `\\b...`:
    en regex el `_` ES caracter de palabra, asi que `\\brev` NUNCA casaria en `..._rev_a`.
    """
    s = _SEPARATORS_RE.sub(" ", str(stem or "").lower()).strip()
    for pat in _REV_PATTERNS:
        s = pat.sub(" ", s)
    s = re.sub(r" +", " ", s).strip()
    for _ in range(3):  # sufijos apilados: ` v2 es`, ` es gb`
        new = _LANG_SUFFIX_RE.sub("", s).strip()
        if new == s:
            break
        s = new
    return s.replace(" ", "")


# ── clasificacion de sha ──────────────────────────────────────────────────────
def sha_class(sha: str | None) -> str:
    s = (sha or "").strip()
    if not s:
        return "vacio"
    if s.lower().startswith("backfill:"):
        return "placeholder"
    if re.fullmatch(r"[0-9a-f]{64}", s.lower()):
        return "real_64hex"
    return "otro"


def lang_bucket(lang: str | None) -> str:
    l = (lang or "").strip().lower()
    if not l:
        return "null"
    if l in ("es", "en"):
        return l
    return "otro"


# ── LA DERIVACION (pura sobre las filas leidas -> determinista) ────────────────
def derive(documents: list[dict[str, Any]],
           chunks: list[dict[str, Any]],
           hyq: list[dict[str, Any]],
           manifest: dict[str, Any],
           midx: dict[str, Any],
           provenance_scan: dict[str, Any],
           t2_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_stem: dict[str, list[dict[str, Any]]] = midx["by_stem"]
    by_sha: dict[str, list[dict[str, Any]]] = midx["by_sha"]

    # ── indices de chunks por documento ───────────────────────────────────────
    chunks_by_doc: dict[str, list[dict[str, Any]]] = {}
    chunk_by_id: dict[str, dict[str, Any]] = {}
    for r in chunks:
        chunk_by_id[str(r["id"])] = r
        did = r.get("document_id")
        if did:
            chunks_by_doc.setdefault(str(did), []).append(r)
    for lst in chunks_by_doc.values():
        lst.sort(key=lambda r: ((r.get("chunk_index") if r.get("chunk_index") is not None else 10**9),
                                str(r["id"])))

    # ── (b) clasificacion por documento ───────────────────────────────────────
    docs: dict[str, dict[str, Any]] = {}
    for d in documents:
        did = str(d["id"])
        d_chunks = chunks_by_doc.get(did, [])
        extractions = sorted({str(c.get("extraction_sha256") or "") for c in d_chunks
                              if (c.get("extraction_sha256") or "").strip()})
        n_ext = len(extractions)
        raw_sha = d.get("source_pdf_sha256")
        cls_sha = sha_class(raw_sha)

        if not d_chunks:
            binding = "sin_chunks"
        elif n_ext == 1:
            binding = "single_extraction"
        elif n_ext == 0:
            binding = "chunks_sin_extraction_sha"
        else:
            binding = "multi_extraction"

        binding_check = "n/a"
        if cls_sha == "real_64hex" and d_chunks and n_ext >= 1:
            binding_check = ("binding_ok" if extractions == [str(raw_sha).strip()]
                             else "binding_mismatch")

        # sha esperada para el match contra blobs locales (desviacion #3)
        if cls_sha == "real_64hex":
            expected_sha = str(raw_sha).strip()
            expected_src = "source_pdf_sha256"
        elif cls_sha == "placeholder" and n_ext == 1:
            expected_sha = extractions[0]
            expected_src = "extraction_sha256"
        else:
            expected_sha = None
            expected_src = "ninguna"

        stem = _pdf_stem(str(d.get("source_pdf_filename") or ""))
        stem_blobs = by_stem.get(stem, []) if stem else []
        sha_blobs = by_sha.get(expected_sha, []) if expected_sha else []
        dual = [b for b in stem_blobs if expected_sha and b["sha256"] == expected_sha]
        if dual:
            blob_local = "dual_stem_y_sha"
        elif sha_blobs:
            blob_local = "solo_sha"
        elif stem_blobs:
            blob_local = "solo_stem"
        else:
            blob_local = "sin_match"

        docs[did] = {
            "doc": d,
            "stem": stem,
            "n_chunks": len(d_chunks),
            "n_extractions": n_ext,
            "extractions": extractions,
            "sha_class": cls_sha,
            "binding": binding,
            "binding_check": binding_check,
            "expected_sha": expected_sha,
            "expected_sha_source": expected_src,
            "blob_local": blob_local,
            "stem_blobs": [b["rel_path"] for b in stem_blobs],
            "dual_blobs": [b["rel_path"] for b in dual],
            "sha_blobs": [b["rel_path"] for b in sha_blobs],
            "lineage": "not_null" if d.get("revision_lineage_id") else "null",
            "language_bucket": lang_bucket(d.get("language")),
            "status": str(d.get("status") or "∅"),
        }

    # particion exhaustiva -> celdas
    cells: Counter[tuple] = Counter()
    for v in docs.values():
        cells[(v["status"], v["sha_class"], v["binding"], v["binding_check"],
               v["lineage"], v["language_bucket"], v["blob_local"])] += 1
    partition_rows = [
        {"status": k[0], "sha_class": k[1], "binding": k[2], "binding_check": k[3],
         "lineage": k[4], "language": k[5], "blob_local": k[6], "n": n}
        for k, n in sorted(cells.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    partition_sum = sum(r["n"] for r in partition_rows)

    def _margin(field: str) -> dict[str, int]:
        c: Counter[str] = Counter(v[field] for v in docs.values())
        return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))

    margins = {f: _margin(f) for f in
               ("status", "sha_class", "binding", "binding_check", "lineage",
                "language_bucket", "blob_local")}

    # ── (c) GATE H1 — estratos definidos SOLO por stem-match (no-circular) ────
    def _stratum_sort(ids: list[str]) -> list[str]:
        return sorted(ids, key=lambda i: (_md5(i), i))

    stratum_a = _stratum_sort([  # docs con sha REAL, binding-ok, con blob por stem
        i for i, v in docs.items()
        if v["binding_check"] == "binding_ok" and v["stem_blobs"]
    ])[:H1_STRATUM_N]
    stratum_b = _stratum_sort([  # placeholder single-extraction, con blob por stem
        i for i, v in docs.items()
        if v["sha_class"] == "placeholder" and v["binding"] == "single_extraction" and v["stem_blobs"]
    ])[:H1_STRATUM_N]

    def _h1_probe(doc_ids: list[str], label: str) -> dict[str, Any]:
        rows = []
        for did in doc_ids:
            v = docs[did]
            blobs = by_stem.get(v["stem"], [])
            shas = [b["sha256"] for b in blobs]
            exp = v["expected_sha"]
            if not blobs:
                verdict = "ausente"
            elif exp is None:
                verdict = "sin_sha_esperada"
            elif exp in shas:
                verdict = "match"
            else:
                verdict = "mismatch"
            rows.append({
                "document_id": did,
                "manufacturer": v["doc"].get("manufacturer"),
                "stem": v["stem"],
                "n_blobs_por_stem": len(blobs),
                "stem_ambiguo": len(blobs) > 1,
                "expected_sha_source": v["expected_sha_source"],
                "expected_sha16": (exp or "")[:16],
                "blob_sha16": [str(s or "")[:16] for s in shas][:3],
                "verdict": verdict,
            })
        counts = Counter(r["verdict"] for r in rows)
        return {
            "estrato": label,
            "n": len(rows),
            "match": counts.get("match", 0),
            "mismatch": counts.get("mismatch", 0),
            "ausente": counts.get("ausente", 0),
            "sin_sha_esperada": counts.get("sin_sha_esperada", 0),
            "n_stem_ambiguo": sum(1 for r in rows if r["stem_ambiguo"]),
            "by_manufacturer": dict(sorted(Counter(str(r["manufacturer"]) for r in rows).items())),
            "rows": rows,
        }

    h1_a = _h1_probe(stratum_a, "A_binding_ok_sha_real")
    h1_b = _h1_probe(stratum_b, "B_placeholder_single_extraction")
    h1_total = h1_a["n"] + h1_b["n"]
    h1_match = h1_a["match"] + h1_b["match"]
    h1_mismatch = h1_a["mismatch"] + h1_b["mismatch"]
    h1_verdict = ("H1_CONFIRMADA" if (h1_total >= 60 and h1_mismatch == 0 and h1_match == h1_total)
                  else ("H1_REFUTADA_EN_ALGUN_ESTRATO" if h1_mismatch else "H1_INCONCLUSA"))

    # ── (c2) grupos sha-compartido ────────────────────────────────────────────
    per_mfr: dict[tuple[str, str], list[str]] = {}
    per_sha: dict[str, list[str]] = {}
    for did, v in docs.items():
        exp = v["expected_sha"]
        if not exp:
            continue
        mfr = str(v["doc"].get("manufacturer") or "∅")
        per_mfr.setdefault((mfr, exp), []).append(did)
        per_sha.setdefault(exp, []).append(did)
    groups_mfr = sorted(
        [{"manufacturer": k[0], "sha16": k[1][:16], "n": len(ids), "document_ids": sorted(ids)}
         for k, ids in per_mfr.items() if len(ids) > 1],
        key=lambda r: (-r["n"], r["manufacturer"], r["sha16"]))
    groups_global = sorted(
        [{"sha16": k[:16], "n": len(ids), "document_ids": sorted(ids),
          "manufacturers": sorted({str(docs[i]["doc"].get("manufacturer") or "∅") for i in ids})}
         for k, ids in per_sha.items() if len(ids) > 1],
        key=lambda r: (-r["n"], r["sha16"]))
    singleton_per_mfr = {did for (mfr, sha), ids in per_mfr.items() if len(ids) == 1 for did in ids}

    # ── (d) CENSUS HYQ ────────────────────────────────────────────────────────
    hyq_total = len(hyq)
    hyq_parent_missing = 0
    hyq_parent_dup = 0
    hyq_parent_doc_null = 0
    hyq_parents: set[str] = set()
    hyq_srcfiles: set[str] = set()
    hyq_parent_srcfiles: set[str] = set()
    hyq_srcfile_mismatch = 0
    for r in hyq:
        cid = str(r.get("chunk_id") or "")
        hyq_parents.add(cid)
        sf = r.get("source_file")
        if sf:
            hyq_srcfiles.add(str(sf))
        parent = chunk_by_id.get(cid)
        if parent is None:
            hyq_parent_missing += 1
            continue
        if parent.get("duplicate_of"):
            hyq_parent_dup += 1
        if not parent.get("document_id"):
            hyq_parent_doc_null += 1
        psf = parent.get("source_file")
        if psf:
            hyq_parent_srcfiles.add(str(psf))
        if str(psf or "") != str(sf or ""):
            hyq_srcfile_mismatch += 1
    all_chunk_srcfiles = {str(c.get("source_file")) for c in chunks if c.get("source_file")}
    hyq_census = {
        "hyq_rows": hyq_total,
        "hyq_distinct_parents": len(hyq_parents),
        "rows_con_padre_duplicate_of": hyq_parent_dup,
        "pct_rows_con_padre_duplicate_of": round(100 * hyq_parent_dup / (hyq_total or 1), 2),
        "rows_con_padre_document_id_null": hyq_parent_doc_null,
        "rows_con_padre_inexistente": hyq_parent_missing,
        "rows_source_file_distinto_del_padre": hyq_srcfile_mismatch,
        "source_files_en_hyq": len(hyq_srcfiles),
        "source_files_de_los_padres": len(hyq_parent_srcfiles),
        "source_files_en_chunks_v2": len(all_chunk_srcfiles),
        "cobertura_source_files": f"{len(hyq_parent_srcfiles)}/{len(all_chunk_srcfiles)}",
        "source_files_sin_hyq": len(all_chunk_srcfiles - hyq_parent_srcfiles),
    }
    # deriva censada (se reporta, NO se toca)
    drift = {
        "chunks_document_id_null": sum(1 for c in chunks if not c.get("document_id")),
        "chunks_en_docs_no_activos": sum(
            1 for c in chunks
            if c.get("document_id") and str(c["document_id"]) in docs
            and docs[str(c["document_id"])]["status"] != "active"),
        "chunks_con_document_id_inexistente": sum(
            1 for c in chunks
            if c.get("document_id") and str(c["document_id"]) not in docs),
        "docs_no_activos_con_chunks": len({
            str(c["document_id"]) for c in chunks
            if c.get("document_id") and str(c["document_id"]) in docs
            and docs[str(c["document_id"])]["status"] != "active"}),
    }

    # ── (e) DETECTOR + CALIBRACION + CANDIDATOS ───────────────────────────────
    detections: dict[str, dict[str, Any]] = {}
    for did, v in docs.items():
        sample = chunks_by_doc.get(did, [])[:LANG_SAMPLE_N]
        if not sample:
            detections[did] = {"language": None, "confidence": "baja", "tokens": 0,
                               "reason": "sin_chunks", "n_chunks_sampled": 0, "hits": {},
                               "hits_literal": {},
                               "language_literal": None, "confidence_literal": "baja",
                               "limpieza": {"n_anotaciones": 0, "chars_eliminados": 0,
                                            "pct_chars_eliminados": 0.0},
                               "cambio_idioma_por_limpieza": False,
                               "degradado_por_token_dominante": False,
                               "degradado_por_familia_cruzada": False}
            continue
        text = "\n".join(str(c.get("content") or "") for c in sample)
        det = detect_language(text)
        det["n_chunks_sampled"] = len(sample)
        detections[did] = det

    t2_lang_ids = {str(r["document_id"]) for r in t2_rows if r.get("language")}
    labeled = [did for did, v in docs.items() if v["doc"].get("language")]
    confusion: Counter[tuple[str, str]] = Counter()
    for did in labeled:
        lab = str(docs[did]["doc"]["language"]).strip().lower()
        det = detections[did]["language"] or "∅none"
        confusion[(lab, det)] += 1
    conf_rows = [{"label": k[0], "detected": k[1], "n": n}
                 for k, n in sorted(confusion.items(), key=lambda kv: (-kv[1], kv[0]))]
    esen = [did for did in labeled
            if str(docs[did]["doc"]["language"]).strip().lower() in ("es", "en")]
    esen_agree = sum(1 for did in esen
                     if detections[did]["language"] == str(docs[did]["doc"]["language"]).strip().lower())
    esen_agree_high = [did for did in esen if detections[did]["confidence"] == "alta"]
    esen_agree_high_ok = sum(
        1 for did in esen_agree_high
        if detections[did]["language"] == str(docs[did]["doc"]["language"]).strip().lower())
    calibration = {
        "n_docs_etiquetados": len(labeled),
        "n_docs_etiquetados_es_en": len(esen),
        "acuerdo_es_en": esen_agree,
        "pct_acuerdo_es_en": round(100 * esen_agree / (len(esen) or 1), 2),
        "n_es_en_confianza_alta": len(esen_agree_high),
        "acuerdo_es_en_confianza_alta": esen_agree_high_ok,
        "pct_acuerdo_es_en_confianza_alta": round(
            100 * esen_agree_high_ok / (len(esen_agree_high) or 1), 2),
        "gate_ge_99pct": (100 * esen_agree / (len(esen) or 1)) >= 99.0,
        "matriz_confusion": conf_rows,
        "label_distribution": dict(sorted(Counter(
            str(docs[d]["doc"]["language"]).strip().lower() for d in labeled).items())),
        "desacuerdos": sorted([
            {"document_id": did,
             "label": str(docs[did]["doc"]["language"]).strip().lower(),
             "detected": detections[did]["language"],
             "confidence": detections[did]["confidence"],
             "hits": detections[did].get("hits"),
             # pre/post FIX 3 — permite ver si el desacuerdo era ruido del extractor
             "hits_pre_limpieza": detections[did].get("hits_literal"),
             "limpieza": detections[did].get("limpieza"),
             "cambio_idioma_por_limpieza": detections[did].get("cambio_idioma_por_limpieza"),
             "detected_pre_limpieza": detections[did].get("language_literal"),
             # De cual de los dos mecanismos de procedencia (§5.3) viene ESTE label:
             # separa "error del detector" de "posible error legacy" (spec riesgo 8).
             "origen_label": ("s282_T2_extraccion_LLM" if did in t2_lang_ids
                              else "residual_pre_s282_regex_nombre_o_manual"),
             "source_pdf_filename": docs[did]["doc"].get("source_pdf_filename"),
             "manufacturer": docs[did]["doc"].get("manufacturer")}
            for did in labeled
            if detections[did]["language"] != str(docs[did]["doc"]["language"]).strip().lower()
        ], key=lambda r: (str(r["label"]), str(r["detected"]), r["document_id"]))[:60],
    }
    calibration["desacuerdos_por_origen"] = dict(sorted(
        Counter(r["origen_label"] for r in calibration["desacuerdos"]).items()))

    pb_ids = sorted([
        did for did, v in docs.items()
        if v["status"] == "active" and v["language_bucket"] == "null"
        and detections[did]["confidence"] == "alta" and detections[did]["language"]
    ])
    pb_rows = [{"document_id": did,
                "stem": docs[did]["stem"],
                "propuesta_language": detections[did]["language"],
                "marcadores": detections[did]["hits"].get(detections[did]["language"]),
                "margin_ratio": detections[did].get("margin_ratio"),
                "tipos_marcador": detections[did].get("tipos_marcador"),
                "segundo_idioma": detections[did].get("segundo_idioma"),
                "segundo_marcadores": detections[did].get("segundo_marcadores"),
                "tokens_dominantes_suprimidos": detections[did].get("tokens_dominantes_suprimidos"),
                "n_chunks_sampled": detections[did]["n_chunks_sampled"],
                "manufacturer": docs[did]["doc"].get("manufacturer"),
                "source_pdf_filename": docs[did]["doc"].get("source_pdf_filename")}
               for did in pb_ids]
    pb_by_lang = dict(sorted(Counter(r["propuesta_language"] for r in pb_rows).items()))

    # Delta v1->v2: quienes ERAN elegibles con el predicado LITERAL del spec y han caido
    # por cada uno de los dos endurecimientos (auditoria del cambio, no cifra de packet).
    pb_literal_ids = sorted([
        did for did, v in docs.items()
        if v["status"] == "active" and v["language_bucket"] == "null"
        and detections[did].get("confidence_literal") == "alta"
        and detections[did].get("language_literal")
    ])
    # Reconciliacion COMPLETA y aditiva: literal - perdidos + ganados == cohorte actual.
    pb_set, lit_set = set(pb_ids), set(pb_literal_ids)
    perdidos = sorted(lit_set - pb_set)
    ganados = sorted(pb_set - lit_set)
    conservados = sorted(pb_set & lit_set)
    cambian_idioma = sorted([d for d in conservados
                             if detections[d]["language"] != detections[d].get("language_literal")])
    pb_delta = {
        "n_elegibles_predicado_literal_v1": len(pb_literal_ids),
        "n_perdidos": len(perdidos),
        "n_ganados": len(ganados),
        "n_conservados": len(conservados),
        "reconciliacion": (f"{len(pb_literal_ids)} literal - {len(perdidos)} perdidos "
                           f"+ {len(ganados)} ganados = {len(pb_ids)}"),
        "aditiva_ok": len(pb_literal_ids) - len(perdidos) + len(ganados) == len(pb_ids),
        "perdidos_por_motivo": dict(sorted(Counter(
            detections[d].get("reason") for d in perdidos).items())),
        "ganados_por_motivo": dict(sorted(Counter(
            ("limpieza_desbloquea_alta" if detections[d].get("cambio_idioma_por_limpieza")
             else "limpieza_mejora_margen") for d in ganados).items())),
        "n_conservados_que_cambian_de_idioma": len(cambian_idioma),
        "document_ids_perdidos": perdidos,
        "document_ids_ganados": ganados,
        "document_ids_conservados_cambian_idioma": cambian_idioma,
        "por_idioma_literal_v1": dict(sorted(Counter(
            detections[d]["language_literal"] for d in pb_literal_ids).items())),
        "n_caidos_por_token_dominante": sum(
            1 for d in perdidos if detections[d].get("degradado_por_token_dominante")),
        "n_caidos_por_familia_cruzada": sum(
            1 for d in perdidos if detections[d].get("degradado_por_familia_cruzada")),
    }

    # QA-30 estratificada por idioma propuesto (round-robin determinista) — NO adjudicada
    by_lang_pool: dict[str, list[str]] = {}
    for did in pb_ids:
        by_lang_pool.setdefault(detections[did]["language"], []).append(did)
    for lang in by_lang_pool:
        by_lang_pool[lang] = sorted(by_lang_pool[lang], key=lambda i: (_md5(i), i))
    qa30: list[str] = []
    cursor = 0
    langs_sorted = sorted(by_lang_pool)
    while len(qa30) < QA30_N and any(cursor < len(by_lang_pool[l]) for l in langs_sorted):
        for lang in langs_sorted:
            if cursor < len(by_lang_pool[lang]) and len(qa30) < QA30_N:
                qa30.append(by_lang_pool[lang][cursor])
        cursor += 1
    def _snippets(did: str, n: int = 2, width: int = 420) -> list[dict[str, Any]]:
        """`n` extractos de EVIDENCIA deterministas de la muestra del detector.

        Se muestra el texto YA LIMPIO (FIX 3): es exactamente lo que el detector cuenta, y
        evita que el humano adjudique sobre anotaciones inglesas del extractor que no son
        del documento.  Se prefieren chunks con >=80 chars utiles tras la limpieza; se toman
        el PRIMERO y el del MEDIO de esos (no dos consecutivos: la portada suele ser logo).
        """
        sample = chunks_by_doc.get(did, [])[:LANG_SAMPLE_N]
        if not sample:
            return []
        cleaned = []
        for ch in sample:
            txt, n_an, _ = strip_extractor_annotations(str(ch.get("content") or ""))
            txt = " ".join(txt.split())
            cleaned.append((ch.get("chunk_index"), txt, n_an))
        usable = [x for x in cleaned if len(x[1]) >= 80] or cleaned
        idxs = sorted({0, len(usable) // 2})[:n]
        return [{"chunk_index": usable[i][0], "texto": usable[i][1][:width],
                 "anotaciones_eliminadas": usable[i][2]} for i in idxs]

    qa30_rows = [{
        "document_id": did,
        "stem": docs[did]["stem"],
        "propuesta_language": detections[did]["language"],
        "manufacturer": docs[did]["doc"].get("manufacturer"),
        "source_pdf_filename": docs[did]["doc"].get("source_pdf_filename"),
        "marcadores": detections[did]["hits"],
        "margin_ratio": detections[did].get("margin_ratio"),
        "segundo_idioma": detections[did].get("segundo_idioma"),
        "segundo_marcadores": detections[did].get("segundo_marcadores"),
        "n_chunks_sampled": detections[did]["n_chunks_sampled"],
        "pista_multiidioma_en_nombre": stem_multilang_hint(docs[did]["stem"]),
        "evidencia": _snippets(did),
    } for did in qa30]
    qa30_multilang = [r["document_id"] for r in qa30_rows if r["pista_multiidioma_en_nombre"]]

    # ── (f) SCREENS DE SIBLINGS ───────────────────────────────────────────────
    pointed_to: dict[str, list[str]] = {}
    for did, v in docs.items():
        for col in ("supersedes_id", "superseded_by_id"):
            tgt = v["doc"].get(col)
            if tgt:
                pointed_to.setdefault(str(tgt), []).append(f"{did}:{col}")

    norm_groups: dict[str, list[str]] = {}
    for did, v in docs.items():
        key = normalize_stem_for_screen(v["stem"])
        if key:
            norm_groups.setdefault(key, []).append(did)
    norm_collisions = {k: sorted(ids) for k, ids in norm_groups.items() if len(ids) > 1}

    tuple_groups: dict[tuple, list[str]] = {}
    for did, v in docs.items():
        d = v["doc"]
        dt = (d.get("doc_type") or "").strip()
        if not dt:
            continue
        key = ((d.get("manufacturer") or "").strip(),
               (d.get("product_model") or "").strip(),
               dt,
               (d.get("language") or "").strip().lower())
        tuple_groups.setdefault(key, []).append(did)
    tuple_collisions = {k: sorted(ids) for k, ids in tuple_groups.items() if len(ids) > 1}

    screens: dict[str, dict[str, Any]] = {}
    for did, v in docs.items():
        if v["status"] != "active":
            continue
        d = v["doc"]
        s_ptr = bool(d.get("supersedes_id") or d.get("superseded_by_id") or pointed_to.get(did))
        nk = normalize_stem_for_screen(v["stem"])
        s_stem = nk in norm_collisions
        key = ((d.get("manufacturer") or "").strip(), (d.get("product_model") or "").strip(),
               (d.get("doc_type") or "").strip(), (d.get("language") or "").strip().lower())
        s_tuple = bool((d.get("doc_type") or "").strip()) and key in tuple_collisions
        screens[did] = {"punteros": s_ptr, "stem_normalizado": s_stem, "tupla_identidad": s_tuple,
                        "sucio": bool(s_ptr or s_stem or s_tuple)}
    n_active = sum(1 for v in docs.values() if v["status"] == "active")
    screens_summary = {
        "n_activos": n_active,
        "screen_punteros": sum(1 for s in screens.values() if s["punteros"]),
        "screen_stem_normalizado": sum(1 for s in screens.values() if s["stem_normalizado"]),
        "screen_tupla_identidad": sum(1 for s in screens.values() if s["tupla_identidad"]),
        "activos_con_algun_screen_sucio": sum(1 for s in screens.values() if s["sucio"]),
        "activos_limpios": sum(1 for s in screens.values() if not s["sucio"]),
        "n_grupos_stem_normalizado_colision": len(norm_collisions),
        "n_grupos_tupla_colision": len(tuple_collisions),
        "top_grupos_stem": [
            {"clave_normalizada": k, "n": len(v), "document_ids": v[:6],
             "stems": sorted({docs[i]["stem"] for i in v})[:6]}
            for k, v in sorted(norm_collisions.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:15]],
        "top_grupos_tupla": [
            {"manufacturer": k[0], "product_model": k[1], "doc_type": k[2], "language": k[3],
             "n": len(v), "document_ids": v[:6]}
            for k, v in sorted(tuple_collisions.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))[:15]],
        "activos_sucios_ids": sorted([d for d, s in screens.items() if s["sucio"]]),
    }

    # ── (g) PRE-REGISTRO DE VOLUMEN ───────────────────────────────────────────
    def _pa_predicate(v: dict[str, Any], did: str) -> bool:
        return (v["status"] == "active"
                and v["binding"] == "single_extraction"
                and v["blob_local"] == "dual_stem_y_sha"
                and did in singleton_per_mfr)

    pa_all_ids = sorted([did for did, v in docs.items() if _pa_predicate(v, did)])
    pa_placeholder_ids = sorted([did for did in pa_all_ids if docs[did]["sha_class"] == "placeholder"])
    pa_real_noop_ids = sorted([did for did in pa_all_ids if docs[did]["sha_class"] == "real_64hex"])

    pre_registro = {
        "P_A": {
            "definicion_packet": ("activo + single-extraction + dual-key (stem Y sha al MISMO blob) "
                                  "+ grupo-sha singleton per-manufacturer + sha PLACEHOLDER "
                                  "(las filas que el UPDATE cambia realmente)"),
            "n_elegibles": len(pa_placeholder_ids),
            "document_ids": pa_placeholder_ids,
            "n_predicado_literal_todas_clases_sha": len(pa_all_ids),
            "n_ya_con_sha_real_no_op": len(pa_real_noop_ids),
            "document_ids_predicado_literal": pa_all_ids,
        },
        "P_B": {
            "definicion_packet": ("activo + language NULL + detector v2 ENDURECIDO confianza "
                                  "ALTA (base del spec + supresion de token dominante + "
                                  "cruce de familia con margen >= 3x)"),
            "n_elegibles": len(pb_ids),
            "document_ids": pb_ids,
            "por_idioma": pb_by_lang,
            "delta_vs_predicado_literal": pb_delta,
        },
    }

    # ── techos declarados (por que un doc NO es elegible P-A) ─────────────────
    pa_reject: Counter[str] = Counter()
    for did, v in docs.items():
        if v["status"] != "active":
            pa_reject["no_activo"] += 1
        elif v["sha_class"] != "placeholder":
            pa_reject[f"sha_{v['sha_class']}"] += 1
        elif v["binding"] != "single_extraction":
            pa_reject[f"binding_{v['binding']}"] += 1
        elif v["blob_local"] != "dual_stem_y_sha":
            pa_reject[f"blob_{v['blob_local']}"] += 1
        elif did not in singleton_per_mfr:
            pa_reject["grupo_sha_no_singleton"] += 1
        else:
            pa_reject["ELEGIBLE"] += 1

    # ── stem: convencion case-sensitive vs case-insensitive (desviacion #1) ───
    def _cs_stem(name: str) -> str:
        t = str(name or "")
        return t[:-4] if t.endswith(".pdf") else t
    stem_convention = {
        "doc_stems_que_difieren": sum(
            1 for v in docs.values()
            if _cs_stem(str(v["doc"].get("source_pdf_filename") or "")) != v["stem"]),
        "blobs_con_extension_no_lowercase": sum(
            1 for e in manifest["entries"] if not e["rel_path"].endswith(".pdf")),
        "docs_que_ganarian_stem_match_con_casefold": sum(
            1 for v in docs.values()
            if not v["stem_blobs"] and v["stem"]
            and any(s.lower() == v["stem"].lower() for s in by_stem)),
    }

    manifest_stats = {
        "n_blobs": manifest["n_blobs"],
        "n_read_errors": manifest["n_read_errors"],
        "n_pdf_skipped_under_logs": manifest["n_pdf_skipped_under_logs"],
        "total_bytes": manifest["total_bytes"],
        "n_stems_distintos": len(by_stem),
        "n_stems_duplicados": sum(1 for v in by_stem.values() if len(v) > 1),
        "n_shas_distintos": len(by_sha),
        "n_shas_duplicados": sum(1 for v in by_sha.values() if len(v) > 1),
        "top_stems_duplicados": [
            {"stem": k, "n": len(v), "paths": [e["rel_path"] for e in v][:4]}
            for k, v in sorted(by_stem.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:10]
            if len(v) > 1],
    }

    return {
        "a_manifest": manifest_stats,
        "b_particion": {
            "suma": partition_sum,
            "suma_ok_1169": partition_sum == len(documents),
            "n_documents": len(documents),
            "n_celdas_no_vacias": len(partition_rows),
            "celdas": partition_rows,
            "marginales": margins,
            "stem_convention": stem_convention,
        },
        "c_h1": {
            "n_total": h1_total,
            "n_match": h1_match,
            "n_mismatch": h1_mismatch,
            "n_ausente": h1_a["ausente"] + h1_b["ausente"],
            "verdict": h1_verdict,
            "estratos": [h1_a, h1_b],
        },
        "c_colisiones": {
            "n_grupos_sha_per_manufacturer": len(groups_mfr),
            "n_grupos_sha_global": len(groups_global),
            "grupos_per_manufacturer": groups_mfr[:25],
            "grupos_global": groups_global[:25],
            "n_docs_con_sha_esperada": sum(1 for v in docs.values() if v["expected_sha"]),
            "n_docs_grupo_sha_singleton_per_mfr": len(singleton_per_mfr),
        },
        "d_hyq": hyq_census,
        "d_deriva": drift,
        "e_idioma": {
            "detector": {
                "version": "v3_endurecido_fix1_fix2_fix3",
                "fix3_limpieza_anotaciones_extractor": True,
                "fix3_span_max_chars": ANNOTATION_MAX_SPAN,
                "universo": list(LANG_UNIVERSE),
                "muestra_por_doc": LANG_SAMPLE_N,
                "umbral_marcadores_alta": LANG_HIGH_MIN_MARKERS,
                "umbral_ratio_alta": LANG_HIGH_MIN_RATIO,
                "min_tipos_marcador": LANG_MIN_MARKER_TYPES,
                "fix1_share_max_token_dominante": DOMINANT_TOKEN_MAX_SHARE,
                "fix2_ratio_min_cruce_familia": CROSS_FAMILY_MIN_RATIO,
                "familias": {"en": ["en"], "romance": sorted(ROMANCE)},
            },
            "distribucion_detectada": dict(sorted(Counter(
                f"{d['language'] or '∅none'}/{d['confidence']}" for d in detections.values()).items())),
            "limpieza_corpus": {
                "n_docs_con_anotaciones_eliminadas": sum(
                    1 for d in detections.values()
                    if (d.get("limpieza") or {}).get("n_anotaciones")),
                "n_anotaciones_totales": sum(
                    (d.get("limpieza") or {}).get("n_anotaciones", 0) for d in detections.values()),
                "chars_eliminados_totales": sum(
                    (d.get("limpieza") or {}).get("chars_eliminados", 0) for d in detections.values()),
                "n_docs_que_CAMBIAN_de_idioma_por_limpieza": sum(
                    1 for d in detections.values() if d.get("cambio_idioma_por_limpieza")),
                "cambios_de_idioma": sorted(
                    [{"document_id": did,
                      "de": detections[did].get("language_literal"),
                      "a": detections[did].get("language"),
                      "tras_limpieza": detections[did].get("language_tras_limpieza"),
                      "pct_chars_eliminados": (detections[did].get("limpieza") or {}).get(
                          "pct_chars_eliminados"),
                      "source_pdf_filename": docs[did]["doc"].get("source_pdf_filename")}
                     for did in docs if detections[did].get("cambio_idioma_por_limpieza")],
                    key=lambda r: (str(r["de"]), str(r["a"]), r["document_id"]))[:40],
            },
            "degradaciones_corpus": {
                "n_docs_con_token_dominante_suprimido": sum(
                    1 for d in detections.values() if d.get("tokens_dominantes_suprimidos")),
                "n_degradados_por_token_dominante": sum(
                    1 for d in detections.values() if d.get("degradado_por_token_dominante")),
                "n_degradados_por_familia_cruzada": sum(
                    1 for d in detections.values() if d.get("degradado_por_familia_cruzada")),
                "distribucion_literal_v1": dict(sorted(Counter(
                    f"{d.get('language_literal') or '∅none'}/{d.get('confidence_literal')}"
                    for d in detections.values()).items())),
            },
            "calibracion": calibration,
            "procedencia_scan": provenance_scan,
            "procedencia_cross_s282": cross_s282_manifest(
                t2_rows,
                {did: (str(v["doc"].get("language")).strip().lower()
                       if (v["doc"].get("language") or "").strip() else None)
                 for did, v in docs.items()}),
            "candidatos_P_B": {"n": len(pb_rows), "por_idioma": pb_by_lang,
                               "delta_vs_predicado_literal": pb_delta,
                               "rows": pb_rows[:60]},
            "qa30": {"n": len(qa30_rows), "rows": qa30_rows, "adjudicada": False,
                     "n_con_pista_multiidioma_en_nombre": len(qa30_multilang),
                     "document_ids_con_pista_multiidioma": sorted(qa30_multilang)},
        },
        "f_screens": screens_summary,
        "g_pre_registro": pre_registro,
        "g_techos_P_A": dict(sorted(pa_reject.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


# ── freeze contract ───────────────────────────────────────────────────────────
def freeze_contract(spec: Path) -> dict[str, Any]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip())
    return {
        "commit_head": head,
        "worktree_dirty": dirty,
        "spec": {"path": spec.relative_to(ROOT).as_posix() if spec.exists() else str(spec),
                 "sha256_lf": _sha256_lf(spec) if spec.exists() else None},
        "chunks_table": os.environ.get("CHUNKS_TABLE"),
        "blob_root": str(BLOB_ROOT),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


DOC_SELECT = ("id,source_pdf_filename,source_pdf_sha256,status,language,doc_type,"
              "manufacturer,product_model,document_family,revision,supersedes_id,"
              "superseded_by_id,revision_lineage_id")
CHUNK_SELECT = ("id,document_id,chunk_index,extraction_sha256,source_file,duplicate_of,"
                "product_model,language,content")
HYQ_SELECT = "chunk_id,source_file"


def _fetch_all() -> tuple[list, list, list]:
    documents = _get_all("documents", DOC_SELECT, order="id.asc")
    chunks = _get_all("chunks_v2", CHUNK_SELECT, order="id.asc")
    hyq = _get_all("chunks_v2_hyq", HYQ_SELECT, order="id.asc")
    return documents, chunks, hyq


# ── main ──────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="s288 A-CORE F0 census v2 (read-only, $0)")
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--reuse-manifest", action="store_true",
                    help="dev only: reusa el JSONL de manifest si existe (no re-hashea)")
    args = ap.parse_args(argv)
    tag = args.tag

    spec = ROOT / "evals/s288_acore_design_brief_v1.md"
    manifest_path = ROOT / f"evals/s288_acore_blob_manifest_{tag}.jsonl"
    result_path = ROOT / f"evals/s288_acore_census_v2_result_{tag}.json"
    report_path = ROOT / f"evals/s288_acore_census_v2_report_{tag}.md"
    qa30_path = ROOT / f"evals/s288_acore_pB_qa30_{tag}.md"

    _init_http()
    contract = freeze_contract(spec)
    print(f"commit={contract['commit_head'][:10]} dirty={contract['worktree_dirty']} "
          f"CHUNKS_TABLE={contract['chunks_table']}")

    # -- (a) manifest: se construye UNA vez y se reusa en ambas pasadas --------
    if args.reuse_manifest and manifest_path.exists():
        entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        manifest = {"entries": entries, "n_blobs": len(entries),
                    "n_read_errors": sum(1 for e in entries if e.get("read_error")),
                    "n_pdf_skipped_under_logs": -1,
                    "total_bytes": sum(int(e.get("size") or 0) for e in entries),
                    "root": str(BLOB_ROOT)}
        print(f"(a) manifest REUSADO de {manifest_path.name}: {manifest['n_blobs']} blobs")
    else:
        print(f"(a) hasheando PDFs bajo {BLOB_ROOT} (excluye logs/) ...")
        manifest = build_blob_manifest(BLOB_ROOT)
        manifest_path.write_text(
            "".join(json.dumps({k: e[k] for k in ("rel_path", "stem", "sha256", "size", "read_error")},
                               ensure_ascii=False, sort_keys=True) + "\n"
                    for e in manifest["entries"]),
            encoding="utf-8")
        print(f"(a) manifest: {manifest['n_blobs']} blobs · {manifest['total_bytes']/2**30:.2f} GB · "
              f"errores={manifest['n_read_errors']} · pdf-en-logs-excluidos={manifest['n_pdf_skipped_under_logs']}")
    midx = index_manifest(manifest)
    provenance = scan_language_label_provenance()
    t2_rows = load_s282_t2_manifest()
    print(f"(e) scan de procedencia: {provenance['n_hits']} anclas en "
          f"{len(provenance['hits_by_file'])} ficheros · manifest s282 T2: {len(t2_rows)} filas")

    fp_before = corpus_fingerprint()
    print(f"fingerprint: documents={fp_before['documents']['count']} "
          f"chunks_v2={fp_before['chunks_v2']['count']} hyq={fp_before['chunks_v2_hyq']['count']}")

    # -- pass 1 --
    print("pass1: fetch ...")
    d1, c1, h1 = _fetch_all()
    canon1 = derive(d1, c1, h1, manifest, midx, provenance, t2_rows)
    sha1 = _stable_sha256(canon1)
    print(f"pass1 sha={sha1[:16]} | docs={len(d1)} chunks={len(c1)} hyq={len(h1)}")
    payload_census = canon1
    d1 = c1 = h1 = None  # libera memoria antes de la 2a pasada

    # -- pass 2 (contrato de determinismo) --
    print("pass2: fetch ...")
    d2, c2, h2 = _fetch_all()
    canon2 = derive(d2, c2, h2, manifest, midx, provenance, t2_rows)
    sha2 = _stable_sha256(canon2)
    d2 = c2 = h2 = None
    fp_after = corpus_fingerprint()
    deterministic = (sha1 == sha2) and (fp_before["sha256"] == fp_after["sha256"])
    print(f"pass2 sha={sha2[:16]} | deterministic_2x={deterministic}")

    payload = {
        "schema": "s288_acore_census_v2",
        "run_tag": tag,
        "authority": "F0_CENSUS_READ_ONLY_SELECT_ONLY_ZERO_MODEL_CALLS_ZERO_WRITES",
        "freeze_contract": contract,
        "corpus_fingerprint": fp_after,
        "deterministic_2x": deterministic,
        "result_sha256_pass1": sha1,
        "result_sha256_pass2": sha2,
        "blob_manifest_path": manifest_path.relative_to(ROOT).as_posix(),
        "blob_manifest_sha256_lf": _sha256_lf(manifest_path),
        "qa30_packet_path": qa30_path.relative_to(ROOT).as_posix(),
        "census": payload_census,
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str) + "\n",
                           encoding="utf-8")
    report_path.write_text(build_report(payload), encoding="utf-8")
    qa30_path.write_text(build_qa30_packet(payload), encoding="utf-8")
    print(f"\nmanifest: {manifest_path}")
    print(f"result:   {result_path}")
    print(f"report:   {report_path}")
    print(f"qa30:     {qa30_path}")
    return 0 if deterministic else 2


# ── report ────────────────────────────────────────────────────────────────────
def build_qa30_packet(payload: dict[str, Any]) -> str:
    """Packet LEGIBLE de la muestra QA-30 para adjudicacion humana (spec F0(e)(iii)).

    Una ficha por documento: id · stem · idioma propuesto · evidencia del detector · 2
    snippets de texto real.  La regla de aceptacion es **30/30 correctos o HALT**; este
    fichero NO la adjudica (es $0/read-only): trae una casilla por fila para que Alberto
    marque.  Determinista: sale del mismo blob canonico que el census.
    """
    c = payload["census"]
    e = c["e_idioma"]
    qa = e["qa30"]
    det = e["detector"]
    tag = payload.get("run_tag", "v2")
    L: list[str] = []
    A = L.append
    A(f"# s288 A-CORE — packet QA-30 de P-B para adjudicacion — {tag}")
    A("")
    A("**Que hay que decidir (spec F0(e)(iii)):** para cada documento, ¿el idioma PROPUESTO es "
      "el idioma del documento? Regla de aceptacion: **30/30 correctos -> gate (e) verde; "
      "cualquier fallo -> HALT y revision del detector** (y, si el fallo es de un label legacy, "
      "revision de la cohorte etiquetada — spec riesgo 8). Marca `[x] OK` o `[x] MAL` por ficha.")
    A("")
    A("**Los extractos estan LIMPIOS de anotaciones del extractor** (spans `[...]` en ingles "
      "describiendo figuras: «[Diagram showing…]»). Es lo que el detector cuenta, y evita "
      "adjudicar sobre texto que no es del documento.")
    A("")
    A(f"- cohorte P-B (activos, `language IS NULL`, detector v2 confianza alta): "
      f"**{e['candidatos_P_B']['n']}** documentos · `{e['candidatos_P_B']['por_idioma']}`")
    A(f"- muestra: **{qa['n']}** documentos, estratificada por idioma propuesto, round-robin "
      "determinista sobre `md5(document_id)`")
    A(f"- detector: **{det.get('version')}** · muestra {det['muestra_por_doc']} chunks/doc · alta ⇔ "
      f">={det['umbral_marcadores_alta']} marcadores Y >={det['umbral_ratio_alta']}x el segundo, "
      f"+ supresion de token dominante (>{int(det['fix1_share_max_token_dominante']*100)}%) "
      f"+ cruce de familia >= {det['fix2_ratio_min_cruce_familia']}x "
      f"+ limpieza de anotaciones del extractor `[...]`")
    A(f"- freeze: commit `{payload['freeze_contract']['commit_head'][:12]}` · corpus sha "
      f"`{payload['corpus_fingerprint']['sha256'][:16]}` · determinismo 2x "
      f"{'OK' if payload['deterministic_2x'] else 'KO'}")
    A("")
    A("**Aviso de honestidad:** el detector NO es fiable fuera de {es, en} (todos los labels "
      "`it`/`fr`/`pt`/`nl` del corpus se detectan como `en`). Si alguna ficha propone un idioma "
      "distinto de `es`/`en`, trata la propuesta como sospechosa por defecto.")
    A("")
    A(f"**Blind spot declarado:** el FIX 2 solo degrada cuando el 2º idioma cruza familia "
      "(`en` vs romance); un documento realmente mixto **es+fr/it/pt** NO se degrada. Como ayuda, "
      "las fichas cuyo NOMBRE sugiere multi-idioma llevan la marca ⚠️ **PISTA MULTI-IDIOMA** "
      f"(heuristica de nombre, ADVISORY, no entra en ningun veredicto): "
      f"**{qa.get('n_con_pista_multiidioma_en_nombre', 0)} de {qa['n']}** fichas.")
    A("")
    A("---")
    A("")
    for i, r in enumerate(qa["rows"], 1):
        hint = r.get("pista_multiidioma_en_nombre") or []
        badge = f"  ⚠️ **PISTA MULTI-IDIOMA en el nombre: `{hint}`**" if hint else ""
        A(f"## {i}. `{r['document_id']}` — propuesta: **{r['propuesta_language']}**{badge}")
        A("")
        A(f"- stem: `{r.get('stem')}`")
        A(f"- fichero: `{r.get('source_pdf_filename')}` · marca: {r.get('manufacturer')}")
        A(f"- marcadores por idioma: `{r.get('marcadores')}` · 2º idioma: "
          f"`{r.get('segundo_idioma')}` ({r.get('segundo_marcadores')}) · margen: "
          f"{r.get('margin_ratio')}x · chunks muestreados: {r.get('n_chunks_sampled')}")
        A("")
        for j, ev in enumerate(r.get("evidencia") or [], 1):
            extra = (f", {ev['anotaciones_eliminadas']} anotacion(es) del extractor eliminadas"
                     if ev.get("anotaciones_eliminadas") else "")
            A(f"> **evidencia {j}** (chunk_index {ev.get('chunk_index')}{extra}): {ev.get('texto')}")
            A("")
        A("- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______")
        A("")
        A("---")
        A("")
    A(f"**Recuento final:** ____ / {qa['n']} correctos. 30/30 -> gate (e)(iii) verde. "
      "Cualquier fallo -> HALT.")
    A("")
    return "\n".join(L)


def build_report(payload: dict[str, Any]) -> str:
    fc = payload["freeze_contract"]
    c = payload["census"]
    tag = payload.get("run_tag", "v1")
    L: list[str] = []
    A = L.append

    A(f"# s288 A-CORE — F0 census v2 — {tag}")
    A("")
    A("Instrumento: `scripts/s288_acore_census_v2.py`. **READ-ONLY (solo GET de PostgREST), "
      "SELECT-only, 0 escrituras, 0 llamadas a modelos, coste $0.** Implementa F0(a)-(g) del spec "
      "SELLADO `evals/s288_acore_design_brief_v1.md` (v3). Hereda el stack GET-only + paginacion "
      "ordenada + contrato de determinismo 2x + freeze-contract de "
      "`scripts/s281_h0_identity_census.py` (artefactos s281 intocados).")
    A("")
    A("## Freeze-contract")
    A("")
    A(f"- commit HEAD: `{fc['commit_head']}` (worktree dirty: {fc['worktree_dirty']})")
    A(f"- CHUNKS_TABLE forzado: `{fc['chunks_table']}`")
    A(f"- spec: `{fc['spec']['path']}` sha256-LF `{fc['spec']['sha256_lf']}`")
    A(f"- blob root (solo lectura): `{fc['blob_root']}`")
    fp = payload["corpus_fingerprint"]
    A(f"- fingerprint de corpus: documents={fp['documents']['count']} · "
      f"chunks_v2={fp['chunks_v2']['count']} · chunks_v2_hyq={fp['chunks_v2_hyq']['count']} · "
      f"sha256 `{fp['sha256']}`")
    A(f"- manifest de blobs: `{payload['blob_manifest_path']}` sha256-LF "
      f"`{payload['blob_manifest_sha256_lf']}`")
    if payload.get("qa30_packet_path"):
        A(f"- packet QA-30 de P-B (adjudicacion humana): `{payload['qa30_packet_path']}`")
    A(f"- **determinismo 2x: {'IDENTICO ✅' if payload['deterministic_2x'] else 'DIVERGE ❌'}** "
      f"(pass1 `{payload['result_sha256_pass1'][:16]}` vs pass2 `{payload['result_sha256_pass2'][:16]}`; "
      "ambas pasadas RE-LEEN la DB; el hash de los PDFs se calcula UNA vez y se reusa — los bytes "
      "en disco no cambian entre pasadas, declarado)")
    A(f"- generado {fc['generated_utc']}")
    A("")

    # GATE F0
    b = c["b_particion"]; h1 = c["c_h1"]; cal = c["e_idioma"]["calibracion"]
    A("## 0. GATE F0 (spec §F0)")
    A("")
    A("| Condicion del gate | Estado |")
    A("|---|---|")
    A(f"| determinismo 2x byte-identico | {'✅ SI' if payload['deterministic_2x'] else '❌ NO'} |")
    A(f"| particion suma {b['n_documents']} | {'✅ SI' if b['suma_ok_1169'] else '❌ NO'} "
      f"(suma={b['suma']}) |")
    A(f"| H1 explicito | **{h1['verdict']}** ({h1['n_match']}/{h1['n_total']} match, "
      f"{h1['n_mismatch']} mismatch) |")
    A(f"| (e)(ii) acuerdo es/en >= 99% | {'✅ SI' if cal['gate_ge_99pct'] else '❌ NO'} "
      f"({cal['pct_acuerdo_es_en']}%) |")
    A(f"| (e)(i) procedencia de labels documentada | ver §5.3 (scan reproducible + veredicto honesto) |")
    A(f"| (e)(iii) QA 30/30 con HALT | **ABIERTO** — la muestra se EMITE (§5.5) pero exige juicio "
      f"humano; este instrumento es $0/read-only y NO la adjudica |")
    A("")

    # (a)
    m = c["a_manifest"]
    A("## 1. (a) Manifest de blobs locales")
    A("")
    A(f"- PDFs hasheados: **{m['n_blobs']}** ({m['total_bytes']/2**30:.2f} GB) · errores de lectura: "
      f"{m['n_read_errors']}")
    A(f"- PDFs EXCLUIDOS por vivir bajo `logs/`: {m['n_pdf_skipped_under_logs']} "
      f"(reconciliacion con el spec §1, que cita 1.334: {m['n_blobs']} fuera de `logs/` — todos bajo "
      f"`Manuales_*` — + {max(m['n_pdf_skipped_under_logs'], 0)} en `logs/` = "
      f"{m['n_blobs'] + max(m['n_pdf_skipped_under_logs'], 0)})")
    A(f"- stems distintos: {m['n_stems_distintos']} · **stems DUPLICADOS entre carpetas: "
      f"{m['n_stems_duplicados']}** -> el indice por stem es MULTI-VALOR")
    A(f"- shas distintos: {m['n_shas_distintos']} · shas duplicados (mismo fichero en 2+ carpetas): "
      f"{m['n_shas_duplicados']}")
    A("")
    if m["top_stems_duplicados"]:
        A("Top stems duplicados:")
        A("")
        A("| stem | n | paths |")
        A("|---|---:|---|")
        for r in m["top_stems_duplicados"]:
            A(f"| `{r['stem'][:44]}` | {r['n']} | {', '.join('`'+p[:38]+'`' for p in r['paths'])} |")
        A("")
    sc = b["stem_convention"]
    A(f"**Convencion de stem (desviacion declarada #1):** blobs con extension no-lowercase: "
      f"{sc['blobs_con_extension_no_lowercase']} · doc-stems que difieren entre la regla "
      f"case-SENSITIVE de `canonical_blob_stem` y la case-INSENSITIVE usada aqui: "
      f"{sc['doc_stems_que_difieren']} · docs que ganarian stem-match SOLO con casefold del cuerpo "
      f"(informativo, NO usado): {sc['docs_que_ganarian_stem_match_con_casefold']}.")
    A("")

    # (b)
    A("## 2. (b) Particion exhaustiva de los documentos")
    A("")
    A(f"Suma de celdas = **{b['suma']}** / {b['n_documents']} documentos "
      f"({'✅ EXHAUSTIVA' if b['suma_ok_1169'] else '❌ NO CUADRA'}). Celdas no vacias: "
      f"{b['n_celdas_no_vacias']}.")
    A("")
    A("### 2.1 Marginales")
    A("")
    for field, label in [("status", "status"), ("sha_class", "clase de sha"),
                         ("binding", "binding (extracciones)"), ("binding_check", "binding check"),
                         ("lineage", "lineage"), ("language_bucket", "language"),
                         ("blob_local", "blob local")]:
        vals = " · ".join(f"`{k}`={v}" for k, v in b["marginales"][field].items())
        A(f"- **{label}**: {vals}")
    A("")
    A("### 2.2 Celdas (status x clase-sha x binding x binding-check x lineage x language x blob-local)")
    A("")
    A("| status | sha | binding | check | lineage | lang | blob local | n |")
    A("|---|---|---|---|---|---|---|---:|")
    for r in b["celdas"]:
        A(f"| {r['status']} | {r['sha_class']} | {r['binding']} | {r['binding_check']} | "
          f"{r['lineage']} | {r['language']} | {r['blob_local']} | {r['n']} |")
    A("")

    # (c)
    A("## 3. (c) Gate H1 (NO-CIRCULAR) + colisiones de sha")
    A("")
    A("Diseno del gate (spec §2): la clave de localizacion es el **STEM** (nombre), independiente "
      "del hash; el blob se hashea y su sha se compara contra la sha ESPERADA del documento "
      "(`source_pdf_sha256` si es real; `extraction_sha256` si es placeholder single-extraction). "
      "**Los estratos se definen SOLO por existencia de stem-match** — definirlos por dual-key "
      "haria el gate tautologico (desviacion declarada #5).")
    A("")
    A("| estrato | n | match | mismatch | ausente | sin sha esperada | stem ambiguo |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for e in h1["estratos"]:
        A(f"| {e['estrato']} | {e['n']} | {e['match']} | {e['mismatch']} | {e['ausente']} | "
          f"{e['sin_sha_esperada']} | {e['n_stem_ambiguo']} |")
    A(f"| **TOTAL** | **{h1['n_total']}** | **{h1['n_match']}** | **{h1['n_mismatch']}** | "
      f"**{h1['n_ausente']}** | | |")
    A("")
    A(f"**VEREDICTO H1: `{h1['verdict']}`** — "
      + ("`extraction_sha256` ES el sha256 de los bytes del PDF fuente en ambos estratos "
         "(n>=60, 0 mismatch). El estrato placeholder confirma que la sha real recuperable "
         "para el packet P-A es la del blob localizado por nombre."
         if h1["verdict"] == "H1_CONFIRMADA" else
         "revisar los mismatch por estrato antes de habilitar P-A sobre ese estrato "
         "(spec §2: estrato que falla -> fuera de P-A, techo declarado)."))
    A("")
    for e in h1["estratos"]:
        A(f"Marcas del estrato `{e['estrato']}`: `{e['by_manufacturer']}`")
    A("")
    col = c["c_colisiones"]
    A("### 3.1 Grupos de sha compartida (guard del UNIQUE `documents_mfr_hash_unique`)")
    A("")
    A(f"- grupos con n>1 por **(manufacturer, sha)**: **{col['n_grupos_sha_per_manufacturer']}**")
    A(f"- grupos con n>1 por **sha global** (cross-manufacturer incluido): "
      f"**{col['n_grupos_sha_global']}**")
    A("")
    if col["grupos_global"]:
        A("| sha16 | n | marcas | document_ids |")
        A("|---|---:|---|---|")
        for g in col["grupos_global"][:15]:
            A(f"| `{g['sha16']}` | {g['n']} | {g['manufacturers']} | "
              f"{', '.join(str(i)[:8] for i in g['document_ids'][:4])} |")
        A("")
    else:
        A("Ningun grupo con n>1 (coincide con el census del spec §1: **0 colisiones hoy**).")
        A("")

    # (d)
    hq = c["d_hyq"]; dr = c["d_deriva"]
    A("## 4. (d) Census `chunks_v2_hyq`")
    A("")
    A(f"- filas hyq: **{hq['hyq_rows']}** · padres distintos: **{hq['hyq_distinct_parents']}**")
    A(f"- filas cuyo padre tiene `duplicate_of` NOT NULL: **{hq['rows_con_padre_duplicate_of']}** "
      f"({hq['pct_rows_con_padre_duplicate_of']}%)")
    A(f"- filas cuyo padre tiene `document_id` NULL: **{hq['rows_con_padre_document_id_null']}**")
    A(f"- filas con padre inexistente en `chunks_v2`: {hq['rows_con_padre_inexistente']}")
    A(f"- filas cuyo `source_file` desnormalizado difiere del `source_file` del padre: "
      f"{hq['rows_source_file_distinto_del_padre']} (relevante para F2.2: los campos "
      f"desnormalizados quedan como display/debug)")
    A(f"- cobertura de source_files (via padres): **{hq['cobertura_source_files']}** · "
      f"source_files sin ninguna fila hyq: {hq['source_files_sin_hyq']}")
    A("")
    A("**Deriva censada (se reporta, NO se toca — spec §4 fuera de scope):** "
      f"chunks con `document_id` NULL = {dr['chunks_document_id_null']} · chunks vivos en docs "
      f"NO activos = {dr['chunks_en_docs_no_activos']} (en {dr['docs_no_activos_con_chunks']} docs) · "
      f"chunks con `document_id` inexistente = {dr['chunks_con_document_id_inexistente']}.")
    A("")

    # (e)
    e = c["e_idioma"]
    A("## 5. (e) Detector de idioma v2 + calibracion + procedencia")
    A("")
    A("### 5.1 Detector (reconstruido en este script)")
    A("")
    det = e["detector"]
    A(f"- version: **{det.get('version')}** · universo: `{det['universo']}` · muestra por doc: "
      f"**{det['muestra_por_doc']} chunks** (primeros por `(chunk_index, id)`; todos si hay menos)")
    A(f"- base (spec F0(e)): confianza **alta** ⇔ marcadores del dominante >= "
      f"{det['umbral_marcadores_alta']} **Y** dominante >= {det['umbral_ratio_alta']}x el segundo.")
    A(f"- **FIX 1 (token dominante)**: un solo TIPO de token que aporte > "
      f"{int(det['fix1_share_max_token_dominante']*100)}% del recuento del ganador se SUPRIME como "
      "marcador en todos los idiomas y se re-decide; si el veredicto (idioma, alta/baja) CAMBIA al "
      "quitarlo -> **baja**.")
    A(f"- **FIX 2 (cruce de familia)**: si los dos idiomas top cruzan familia "
      f"(`en` vs romance `{sorted(ROMANCE)}`) y el margen es < {det['fix2_ratio_min_cruce_familia']}x "
      "-> **baja** (patron del documento MIXTO, spec §F1 P-B).")
    A(f"- **FIX 3 (limpieza de INPUT — anotaciones del extractor)**: antes de contar se eliminan "
      f"los spans `[...]` que el EXTRACTOR inyecta en ingles para describir figuras "
      f"(«[Diagram showing…]», «[Exploded view…]», «[Grid paper…]»), siempre que el corchete "
      f"cierre en <= {ANNOTATION_MAX_SPAN} chars (si no cierra, se deja intacto). "
      "**A diferencia de FIX 1/2, este SI puede cambiar el idioma detectado — ese es su "
      "proposito.**")
    A("")
    A("  > **Es limpieza de INPUT motivada por el MECANISMO, NO tuning contra el gate.** Ese "
      "texto no pertenece al documento: lo genera el instrumento de extraccion. Se elimina la "
      "misma clase de span en TODOS los documentos, antes de contar, con un criterio "
      "sintactico fijo. Motivo raiz: los documentos ESPANOLES *diagram-heavy* acumulaban "
      "marcadores INGLESES falsos y salian `en` con confianza ALTA — sin este fix P-B habria "
      "escrito `en` en documentos espanoles (**backfill ERRONEO**). Caso que lo destapo: "
      "`bd0c2e27` = MI-DT-192 (notifier.es, «9 AGOSTO 2013»), documento espanol que salia "
      "`en/alta`.")
    A("")
    A("- FIX 1 y FIX 2 solo pueden DEGRADAR alta->baja. FIX 3 actua ANTES, sobre el texto.")
    A("- Rastro completo conservado por documento: `language_literal`/`confidence_literal` "
      "(regla literal del spec sobre texto CRUDO = baseline v1) vs el veredicto endurecido, "
      "mas `limpieza` y `cambio_idioma_por_limpieza`.")
    A("- listas de marcadores INSPIRADAS en `scripts/audit_chunk_languages.py:89-95`; el modulo NO "
      "se importa ni se invoca (lee la tabla `chunks` legacy con muestra de 3 — spec §1 lo declara "
      "solo como referencia). Los acentos se normalizan antes de contar.")
    A("")
    A(f"Distribucion detectada sobre los {c['b_particion']['n_documents']} documentos "
      f"(`idioma/confianza`): `{e['distribucion_detectada']}`")
    A("")
    A("### 5.2 Calibracion contra los labels existentes")
    A("")
    A(f"- documentos YA etiquetados: **{cal['n_docs_etiquetados']}** · distribucion "
      f"`{cal['label_distribution']}`")
    A(f"- subconjunto es/en: **{cal['n_docs_etiquetados_es_en']}** · acuerdo "
      f"**{cal['acuerdo_es_en']}/{cal['n_docs_etiquetados_es_en']} = "
      f"{cal['pct_acuerdo_es_en']}%** (gate >=99%: "
      f"{'✅ PASA' if cal['gate_ge_99pct'] else '❌ NO PASA'})")
    A(f"- restringido a confianza ALTA: {cal['acuerdo_es_en_confianza_alta']}/"
      f"{cal['n_es_en_confianza_alta']} = {cal['pct_acuerdo_es_en_confianza_alta']}% "
      "(es la cohorte que P-B usaria)")
    A("")
    A("Matriz de confusion (label x detectado):")
    A("")
    A("| label | detectado | n |")
    A("|---|---|---:|")
    for r in cal["matriz_confusion"]:
        A(f"| {r['label']} | {r['detected']} | {r['n']} |")
    A("")
    A("**Honestidad (spec §F0(e)(ii) + riesgo 6):** el acuerdo con los labels existentes mide "
      "REPRODUCCION de esos labels, no exactitud — es condicion NECESARIA, no suficiente. La "
      "barrera de exactitud es la QA 30/30 de §5.5, que este instrumento no adjudica.")
    A("")
    if cal["desacuerdos"]:
        A(f"Desacuerdos ({len(cal['desacuerdos'])} sobre TODOS los labels, no solo es/en). La "
          "columna **origen** separa «error del detector» de «posible error LEGACY del label» "
          f"(spec riesgo 8): `{cal.get('desacuerdos_por_origen')}`.")
        A("")
        A("| document_id | label | pre-FIX3 | detectado | conf | anot. | origen del label | fichero |")
        A("|---|---|---|---|---|---:|---|---|")
        for r in cal["desacuerdos"][:20]:
            lp = r.get("limpieza") or {}
            A(f"| `{str(r['document_id'])[:8]}` | {r['label']} | {r.get('detected_pre_limpieza')} | "
              f"{r['detected']} | {r['confidence']} | {lp.get('n_anotaciones')} "
              f"({lp.get('pct_chars_eliminados')}%) | {r.get('origen_label')} | "
              f"`{str(r['source_pdf_filename'])[:34]}` |")
        A("")
        A("Lectura: los labels `it`/`fr`/`pt`/`nl` caen sistematicamente en `en` — son documentos "
          "MULTILINGUES cuyos primeros chunks son ingleses, o idiomas cuyo set de marcadores es "
          "mas debil que el ingles. No entran en la metrica es/en del gate, pero **avisan de que "
          "el detector no es fiable fuera de {es, en}**: P-B solo deberia tocar esas dos.")
        A("")
    A("### 5.2bis Efecto de los endurecimientos (literal -> endurecido)")
    A("")
    lc = e.get("limpieza_corpus") or {}
    dg = e["degradaciones_corpus"]
    A(f"Sobre los {c['b_particion']['n_documents']} documentos:")
    A("")
    A(f"- **FIX 3**: docs con anotaciones del extractor eliminadas: "
      f"**{lc.get('n_docs_con_anotaciones_eliminadas')}** · anotaciones totales: "
      f"{lc.get('n_anotaciones_totales')} · chars eliminados: {lc.get('chars_eliminados_totales')} "
      f"· **docs que CAMBIAN de idioma detectado por la limpieza: "
      f"{lc.get('n_docs_que_CAMBIAN_de_idioma_por_limpieza')}**")
    if lc.get("cambios_de_idioma"):
        A("")
        A("| document_id | crudo | tras limpieza | final | % chars elim. | fichero |")
        A("|---|---|---|---|---:|---|")
        for r in lc["cambios_de_idioma"][:20]:
            A(f"| `{str(r['document_id'])[:8]}` | {r['de']} | {r.get('tras_limpieza')} | "
              f"{r['a']} | {r['pct_chars_eliminados']}% | "
              f"`{str(r['source_pdf_filename'])[:36]}` |")
        A("")
    A(f"- docs con algun token dominante SUPRIMIDO: **{dg['n_docs_con_token_dominante_suprimido']}** "
      f"· de ellos **DEGRADADOS** (el veredicto cambiaba al quitarlo): "
      f"**{dg['n_degradados_por_token_dominante']}**")
    A(f"- docs DEGRADADOS por cruce de familia con margen < {det['fix2_ratio_min_cruce_familia']}x: "
      f"**{dg['n_degradados_por_familia_cruzada']}**")
    A(f"- distribucion `idioma/confianza` con el predicado LITERAL v1: `{dg['distribucion_literal_v1']}`")
    A(f"- distribucion `idioma/confianza` con el detector v2: `{e['distribucion_detectada']}`")
    A("")
    A("Casos reales que motivaron cada fix (ambos cazados por el propio census v1): (1) una tabla "
      "de equivalencias en ESPANOL que repite 36 veces `plus` (de `NFS-2 PLUS`, nombre de "
      "producto) salia `fr/alta` porque `plus` es marcador FR; (2) un manual `..._ES_GB_...` con "
      "168 marcadores `en` vs 83 `es` (ratio 2.02) salia `en/alta` siendo bilingue.")
    A("")
    A("### 5.3 PROCEDENCIA de los labels existentes (scan reproducible del repo)")
    A("")
    pv = e["procedencia_scan"]
    A(f"Scan determinista (regex sobre `{'`, `'.join(pv['scanned_dirs'])}`, extensiones .py/.sql, "
      f"solo ficheros que mencionan la tabla `documents`): **{pv['n_hits']} anclas** en "
      f"{len(pv['hits_by_file'])} ficheros.")
    A("")
    if pv["hits_by_file"]:
        A("| fichero | anclas |")
        A("|---|---:|")
        for f_, n in sorted(pv["hits_by_file"].items(), key=lambda kv: (-kv[1], kv[0]))[:20]:
            A(f"| `{f_}` | {n} |")
        A("")
        A("Anclas fichero:linea (primeras 25):")
        A("")
        for h in pv["hits"][:25]:
            A(f"- `{h['file']}:{h['line']}` — `{h['text'][:110]}`")
        A("")
    cx = e.get("procedencia_cross_s282") or {}
    if cx.get("available"):
        A("**Reconciliacion CUANTITATIVA contra el escritor dominante** (`"
          f"{cx['manifest_path']}` sha256-LF `{cx['manifest_sha256_lf'][:16]}…`):")
        A("")
        A(f"- filas del manifest: {cx['n_rows']} · con `language`: **{cx['n_rows_con_language']}** "
          f"(distribucion `{cx['distribucion_manifest']}`)")
        A(f"- de esas, HOY en DB: **match {cx['n_match_en_vivo']}** · siguen NULL "
          f"{cx['n_siguen_null']} · distinto {cx['n_distinto']}")
        A(f"- **paquete s282 T2 aplicado: {'SI ✅' if cx['aplicado'] else 'NO / PARCIAL ❌'}** "
          "(el guard de la propia SQL exige `language_set = 301`)")
        A(f"- labels vivos totales: {cx['n_labels_vivos']} · **residual NO explicado por s282: "
          f"{cx['n_labels_residuales_pre_s282']}** (distribucion `{cx['distribucion_residual']}`)")
        A("")
    A(PROVENANCE_VERDICT)
    A("")
    A("### 5.4 Candidatos P-B (activos, language NULL, confianza alta)")
    A("")
    cand = e["candidatos_P_B"]
    d0 = cand["delta_vs_predicado_literal"]
    A(f"**{cand['n']} documentos** · por idioma propuesto: `{cand['por_idioma']}`.")
    A("")
    A(f"**Reconciliacion contra el predicado LITERAL** (`{d0['reconciliacion']}` · aditiva: "
      f"{'OK' if d0.get('aditiva_ok') else 'KO'}):")
    A("")
    A(f"- literal (regla del spec sobre texto crudo): **{d0['n_elegibles_predicado_literal_v1']}** "
      f"(`{d0['por_idioma_literal_v1']}`)")
    A(f"- **perdidos: {d0['n_perdidos']}** por motivo: `{d0['perdidos_por_motivo']}` "
      f"(de ellos {d0['n_caidos_por_token_dominante']} con degradacion por token dominante y "
      f"{d0['n_caidos_por_familia_cruzada']} por cruce de familia)")
    A(f"- **ganados: {d0['n_ganados']}** por motivo: `{d0['ganados_por_motivo']}` — documentos que "
      "la regla literal dejaba en `baja` porque las anotaciones inglesas del extractor diluian el "
      "margen, y que tras FIX 3 resuelven limpio")
    A(f"- conservados: {d0['n_conservados']}, de los cuales "
      f"**{d0['n_conservados_que_cambian_de_idioma']} CAMBIAN de idioma propuesto** respecto al "
      "literal (efecto directo de FIX 3 — el caso `bd0c2e27`)")
    A("")
    if cand["rows"]:
        A("| document_id | idioma | marc. | ratio | tipos | 2º idioma (marc.) | fichero |")
        A("|---|---|---:|---:|---:|---|---|")
        for r in cand["rows"][:20]:
            A(f"| `{str(r['document_id'])[:8]}` | {r['propuesta_language']} | {r['marcadores']} | "
              f"{r['margin_ratio']} | {r.get('tipos_marcador')} | "
              f"{r.get('segundo_idioma')} ({r.get('segundo_marcadores')}) | "
              f"`{str(r['source_pdf_filename'])[:34]}` |")
        A("")
    A("### 5.5 Muestra QA-30 (spec F0(e)(iii)) — EMITIDA, NO ADJUDICADA")
    A("")
    qa = e["qa30"]
    A(f"Muestra estratificada por idioma propuesto, round-robin determinista sobre `md5(document_id)`: "
      f"**{qa['n']} documentos**. La regla de aceptacion del spec es **30/30 correctos o HALT**; "
      "requiere lectura humana del extracto y NO la decide este script ($0/read-only). Sin este "
      "gate cerrado, **P-B no se stagea** (spec §F0(e)).")
    A("")
    A("El packet legible para adjudicacion (2 snippets de evidencia por documento) se emite "
      "aparte, ver la cabecera de este report.")
    A("")
    A("| # | document_id | stem | propuesta | 2º (marc.) | marca |")
    A("|---:|---|---|---|---|---|")
    for i, r in enumerate(qa["rows"], 1):
        A(f"| {i} | `{str(r['document_id'])[:8]}` | `{str(r.get('stem'))[:38]}` | "
          f"{r['propuesta_language']} | {r.get('segundo_idioma')} ({r.get('segundo_marcadores')}) | "
          f"{r['manufacturer']} |")
    A("")

    # (f)
    s = c["f_screens"]
    A("## 6. (f) Screens de siblings (docs ACTIVOS, contra TODOS los status)")
    A("")
    A("| screen | activos marcados |")
    A("|---|---:|")
    A(f"| (i) punteros `supersedes_id`/`superseded_by_id` (propios o apuntando al doc) | "
      f"{s['screen_punteros']} |")
    A(f"| (ii) colision de stem NORMALIZADO (strip rev/fecha/idioma/separadores) | "
      f"{s['screen_stem_normalizado']} |")
    A(f"| (iii) misma tupla (mfr, product_model, doc_type, language) con doc_type NO-NULL | "
      f"{s['screen_tupla_identidad']} |")
    A(f"| **ALGUN screen sucio** | **{s['activos_con_algun_screen_sucio']}** de {s['n_activos']} activos |")
    A(f"| limpios en los 3 screens | {s['activos_limpios']} |")
    A("")
    A(f"Grupos de colision: stem-normalizado **{s['n_grupos_stem_normalizado_colision']}** · "
      f"tupla de identidad **{s['n_grupos_tupla_colision']}**.")
    A("")
    if s["top_grupos_stem"]:
        A("Top grupos por stem normalizado:")
        A("")
        A("| clave normalizada | n | stems |")
        A("|---|---:|---|")
        for g in s["top_grupos_stem"][:12]:
            A(f"| `{g['clave_normalizada'][:40]}` | {g['n']} | "
              f"{', '.join('`'+x[:26]+'`' for x in g['stems'][:3])} |")
        A("")
    if s["top_grupos_tupla"]:
        A("Top grupos por tupla de identidad:")
        A("")
        A("| marca | product_model | doc_type | lang | n |")
        A("|---|---|---|---|---:|")
        for g in s["top_grupos_tupla"][:12]:
            A(f"| {g['manufacturer']} | {str(g['product_model'])[:26]} | {g['doc_type']} | "
              f"{g['language']} | {g['n']} |")
        A("")
    A("Los `document_id` activos con algun screen sucio estan en el JSON "
      "(`census.f_screens.activos_sucios_ids`). Alimentan el workstream P-C de TRAMOS (spec §F1) y "
      "el contexto de P-A; **no bloquean P-A por si mismos** (P-A se gatea por dual-key + "
      "singleton per-mfr).")
    A("")

    # (g)
    g = c["g_pre_registro"]
    A("## 7. (g) PRE-REGISTRO DE VOLUMEN (fix r2-3 — el gate F3 compara contra estas cifras)")
    A("")
    A("| packet | definicion | **n elegibles** |")
    A("|---|---|---:|")
    A(f"| **P-A** (sha real) | {g['P_A']['definicion_packet']} | **{g['P_A']['n_elegibles']}** |")
    A(f"| **P-B** (language) | {g['P_B']['definicion_packet']} | **{g['P_B']['n_elegibles']}** |")
    A("")
    A(f"**P-A, desglose (desviacion declarada #6):** el predicado literal del spec no menciona la "
      f"clase de sha; aplicado tal cual da **{g['P_A']['n_predicado_literal_todas_clases_sha']}** "
      f"documentos, de los cuales **{g['P_A']['n_ya_con_sha_real_no_op']}** YA tienen sha real "
      f"(el UPDATE seria un no-op y falsearia el gate «aplicado == 100% de elegibles»). La cifra "
      f"pre-registrada del packet es el subconjunto **placeholder = "
      f"{g['P_A']['n_elegibles']}**. Ambas listas de `document_id` van en el JSON "
      "(`census.g_pre_registro`), ordenadas.")
    A("")
    dl = g["P_B"]["delta_vs_predicado_literal"]
    A(f"**P-B por idioma propuesto:** `{g['P_B']['por_idioma']}`. Cohorte construida con el "
      f"detector **endurecido (FIX 1+2+3)**; reconciliacion contra el predicado literal: "
      f"`{dl['reconciliacion']}` (§5.4).")
    A("")
    A(f"**Gate (e)(iii) sigue ABIERTO**: la QA-30 fresca de esta cohorte se emite como packet "
      "legible pero NO esta adjudicada -> **el staging de P-B NO esta autorizado**.")
    A("")
    A("### 7.1 Techo declarado de P-A — por que cada documento NO entra (primer motivo, excluyente)")
    A("")
    A("| motivo | documentos |")
    A("|---|---:|")
    for k, v in c["g_techos_P_A"].items():
        A(f"| {k} | {v} |")
    A("")

    A("## 8. Honestidad del instrumento — lo que este census NO hace")
    A("")
    A("- **No escribe nada.** Ni DB (solo GET), ni ficheros fuera de `evals/s288_acore_*`. Los "
      "packets SQL de F1 son trabajo posterior y su paste es de Alberto (spec §7 stop-lines).")
    A("- **No adjudica la QA-30 de F0(e)(iii)** (§5.5): la emite estratificada y determinista. "
      "El gate (e) queda por tanto **PARCIALMENTE verde**: (i) documentado y (ii) medido; (iii) abierto.")
    A("- **La calibracion mide reproduccion, no exactitud** (spec riesgo 6/8): si los labels legacy "
      "traen un error sistematico, el acuerdo alto lo reproduce. La QA-30 es la barrera.")
    A("- **El detector NO es fiable fuera de {es, en}** (§5.2): todos los labels `it`/`fr`/`pt`/`nl` "
      "se detectan como `en`. Y dentro de {es, en} tiene dos modos de fallo medidos y con caso "
      "real (§5.2bis): token repetido y documento bilingue. **Este census NO recomienda stagear "
      "P-B**: (e)(ii) no pasa el 99% y (e)(iii) esta sin adjudicar.")
    A("- **El match blob<->doc por sha usa `extraction_sha256` para los placeholder**: es "
      "exactamente la premisa H1, que este mismo census verifica por clave independiente (§3). "
      "Si H1 no fuera CONFIRMADA, la columna `blob_local` de los placeholder quedaria en "
      "cuarentena junto con P-A.")
    A("- **Los stems duplicados en disco** hacen el indice multi-valor: un doc puede casar por stem "
      "con 2+ blobs. El gate H1 acepta match si CUALQUIERA de ellos tiene la sha esperada, y "
      "reporta cuantas filas tuvieron stem ambiguo. El dual-key de P-A exige que stem y sha "
      "coincidan en el **MISMO** blob (spec fix r2-1).")
    A("- **Fuera de scope declarado (spec §4):** remediacion de la deriva (§4), doc_type backfill, "
      "sha/language de retired/needs_review, lineages (P-C = tramos adjudicados por Alberto).")
    A("")
    return "\n".join(L)


# Veredicto narrado de procedencia (§5.3).  Cada ancla fue VERIFICADA contra el codigo
# (regla-C del Protocolo 3); lo no determinable desde el repo se declara como tal.
PROVENANCE_VERDICT = """**VEREDICTO DE PROCEDENCIA: DETERMINABLE.** Los labels vivos de
`documents.language` son la suma de DOS mecanismos disjuntos, y la aritmetica cierra contra la
DB viva (bloque de arriba):

1. **Escritor DOMINANTE — paquete s282 «Tramo 2» (301 de los ~400).** El generador
   `scripts/s282_t2_write_package.py` emite `evals/s282_t2_apply_v1.sql`, cuyo UPDATE es
   **fill-only** (`evals/s282_t2_apply_v1.sql:590-596`:
   `language = COALESCE(d.language, s.language)` con `WHERE ... (d.doc_type IS NULL OR
   d.language IS NULL)`) y cuya verificacion post-apply ABORTA si
   `language_set <> 301` (`evals/s282_t2_apply_v1.sql:614`; `n_overwrite <> 0` tambien aborta ->
   **nunca sobreescribe** un label previo). El insumo es `evals/s282_t2_manifest_v1.json`
   (`n_rows=533`, `n_language_writes_expected=301`). **VERIFICADO EN VIVO por este census:** las
   301 filas con idioma del manifest valen HOY exactamente ese idioma y 0 siguen NULL -> el paste
   se ejecuto. (Las tablas `t2_staging`/`t2_apply_audit` son `CREATE TEMP TABLE`
   — `evals/s282_t2_apply_v1.sql:18` y `:578` — por eso no existen hoy en el esquema: su ausencia
   NO es evidencia de no-aplicacion; la reconciliacion fila-a-fila SI es evidencia de aplicacion.)
   **El origen del VALOR no es un detector determinista: es una extraccion LLM dual sobre
   contenido** (`scripts/s83_pilot_extract_duo.py` -> `evals/s83_document_identity_final.jsonl`,
   campo `languages` como LISTA), de la que **solo se escribieron los singletons**; los casos
   multi-idioma y los que contradecian la DB se enrutaron a adjudicacion humana y se dejaron
   intactos (`evals/s282_qa_s83_attestation_v2.md`, ejes `language` SINGLETON=AUTO vs MULTI y
   CONTRADICT=ADVISORY).

2. **Residual pre-s282 (~99 labels).** Proceden del registro de ingesta ORIGINAL,
   `src/ingestion/document_registry.py:206` (`"language": info.language` en la fila POSTeada a
   `/rest/v1/documents`), cuyo valor lo producia un **regex puro sobre el NOMBRE del fichero**
   (`src/ingestion/revision_parser.py`, `_LANG_PATTERNS`/`detect_language`: `es|sp|esp`,
   `en|gb|eng`, `fr`, `pt`, `de`, `it`, `multi`; NULL si no hay token). **Ambos ficheros fueron
   BORRADOS en el commit `202ccb0`** ("s43: limpieza #38 (pipeline v1)"; el diff elimina
   `src/ingestion/document_registry.py` y `src/ingestion/revision_parser.py`) -> se recuperan con
   `git show 202ccb0^:<path>`. A eso se suman ~10 filas adjudicadas A MANO con constante `'es'`:
   `supabase/migrations/20260713141223_reconcile_validated_document_revisions_v1.sql:92,105,126,135`
   y `scripts/s64_lifecycle46.py:95,115`.

3. **Los NULL tambien estan explicados.** `scripts/migrations/001_backfill_documents.py:267`
   escribe `"language": None` POR DISENO en la fase 1 del backfill (mismo sitio que acuna el
   placeholder `backfill:<sha256 del NOMBRE>`, `:261`), y `scripts/s65_capab.py:448` inserta
   `"language": None` para su lote.

4. **NINGUN label salio de un detector estadistico de contenido.** `src/reingest/language.py`
   (lingua) escribe `chunks_v2.language`, NO `documents.language`; el pipeline de re-ingesta
   *lee* `documents.language` como compuerta de admision. Es decir: **el detector v2 de esta F0 es
   independiente del origen de los labels contra los que se calibra** — no hay circularidad de
   instrumento; pero SI hay un riesgo de circularidad de JUICIO con el eje 1 (labels de origen
   LLM-sobre-contenido), asi que el acuerdo alto mide **reproduccion de una extraccion LLM previa
   filtrada por singleton**, no exactitud contra la fuente. Es exactamente el riesgo 6/8 del spec:
   la barrera de exactitud es la QA-30 de §5.5, no esta calibracion.

**Incertidumbre residual declarada:** el reparto EXACTO del residual pre-s282 entre el regex de
nombre y las filas adjudicadas a mano no es reconstruible desde el repo (los ficheros del regex
estan borrados y no hay recibo por-fila de aquella ingesta); solo su magnitud y su forma
(mayoritariamente `es`) son medibles. Ese residual NO entra en P-B (P-B toca solo `language IS
NULL`)."""


if __name__ == "__main__":
    sys.exit(main())
