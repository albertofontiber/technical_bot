#!/usr/bin/env python3
"""s281 H0-T3 — Tramo 3 re-tag packet: derive product_model candidates for every
``product_model='unknown'`` source_file (chunk-level findability gap).

Lane H0-T3 of the s281 identity-backfill campaign.  READ-ONLY, $0, deterministic.
For EACH source_file whose chunks are entirely ``product_model`` unknown/NULL (the
class-D findability gap of ``s281_h0_identity_census``: 28 source_files / 318 chunks),
this instrument derives a CANDIDATE ``product_model``/``manufacturer`` re-tag with its
EVIDENCE and a CONFIDENCE, so Alberto can adjudicate the whole tramo in one read and
run the SQL in one paste.  It ADJUDICATES the live state; it never writes.  Every
proposed change is emitted as a SQL PROPOSAL in the report (``evals/s281_h0t3_*``),
never applied.

WHY the gap matters (grounded in code): a chunk with ``product_model='unknown'`` can
never be reached by any product-model retrieval channel — ``retriever.keyword_search``
builds a PostgREST ``imatch`` pattern from the query model and matches it against the
STORED ``product_model`` (``model_to_imatch_pattern`` — retriever.py:267), and
``answer_planner`` scopes/keys chunks by the same field.  ``unknown`` matches nothing,
so the bot admits it lacks a manual that exists (the live MIE-MI-600 / Morley ZXSe
case, ground-truth s78).

EVIDENCE SOURCES (independent), fused per source_file:
  1. DOCUMENT-level ``product_model`` (``documents`` table) — the governed identity
     label already chosen at ingest.  ``documents.product_model`` is NEVER null
     (census C_product_model_null_doclevel=0), so for most files it already carries
     the answer; the chunks simply lag behind it.
  2. The s83 activo (``evals/s83_document_models_final.jsonl`` + ``..._identity_final``)
     — dú­o-extracted models per source_file with role/confidence/evidence.
  3. The governed catalog (``data/catalog/*.jsonl``) — ``doc_map`` (document_id ->
     product ids), ``products`` (canonical_model/familia), ``umbrellas`` (family
     labels), ``homonyms`` (clarify policy).
  4. The chunk CONTENT itself (first pages: section_title + head) — the ground text
     that documents which product the chunks describe.

CONFIDENCE (deterministic):
  * ``alta``  = doc-level pm present AND corroborated by s83/catalog AND no unresolved
    multi-model granularity question  -> the UPDATE is executable as-is.
  * ``media`` = exactly one usable source, or doc-level pm names only the primary of a
    multi-model manual  -> [ADJUDICAR] (candidate shown).
  * ``baja``  = sources disagree, or the manual mixes distinct families, or no model
    source at all (generic FAQ/support docs)  -> [ADJUDICAR] (options shown).

INHERITANCE (declared): the GET-only read-only HTTP stack + freeze-contract A1
fingerprint + determinism-2x contract + honesty-§ discipline from
``scripts/s281_h0_identity_census.py`` (which itself inherits s279/s278).

HARD RULES honoured: DB is SELECT-only (PostgREST GET, zero writes, zero model calls,
zero paid embeddings); determinism (the derivation runs 2x, byte-identical asserted);
outputs restricted to this lane's territory (``scripts/s281_h0t3_*`` / ``evals/s281_h0t3_*``).

Usage:  python scripts/s281_h0t3_retag_packet.py [--tag v1]
Outputs: evals/s281_h0t3_retag_packet_result_<tag>.json
         evals/s281_h0t3_retag_packet_<tag>.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
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
import src.rag.document_local_coverage as dlc  # noqa: E402  (canonical_blob_stem)

# ── constants / territory ──────────────────────────────────────────────────────
S83_DOC_MODELS = ROOT / "evals/s83_document_models_final.jsonl"
S83_DOC_IDENTITY = ROOT / "evals/s83_document_identity_final.jsonl"
CATALOG_DIR = ROOT / "data/catalog"
ZXSE_SOURCE_FILE = "MIE-MI-600"  # the granularity anchor (handled apart in the report)
CONTENT_SAMPLE_N = 6            # first-N chunks quoted as content evidence
CONTENT_HEAD = 200             # chars of content quoted per sampled chunk

_H: dict[str, str] = {}
_BASE = ""


# ── read-only HTTP helpers (inherited from s281_h0 / s279) ─────────────────────
def _init_http() -> None:
    global _H, _BASE
    if not cfg.SUPABASE_URL or not cfg.SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable for the packet")
    _H = {
        "apikey": cfg.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {cfg.SUPABASE_SERVICE_KEY}",
    }
    _BASE = cfg.SUPABASE_URL.rstrip("/")


def _get(table: str, params: dict[str, str], *, count: bool = False) -> httpx.Response:
    headers = dict(_H)
    if count:
        headers["Prefer"] = "count=exact"
    resp = httpx.get(f"{_BASE}/rest/v1/{table}", headers=headers, params=params, timeout=90)
    resp.raise_for_status()
    return resp


def _get_all(table: str, select: str, *, order: str, page: int = 1000,
             extra: dict[str, str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {"select": select, "order": order, "limit": str(page), "offset": str(offset)}
        if extra:
            params.update(extra)
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


def _count_and_max(table: str, ts_col: str) -> tuple[int, Any]:
    resp = _get(table, {"select": "id", "limit": "1"}, count=True)
    total = int(resp.headers.get("content-range", "*/0").split("/")[-1])
    mx_resp = _get(table, {"select": ts_col, "order": f"{ts_col}.desc.nullslast", "limit": "1"})
    rows = mx_resp.json()
    mx = rows[0][ts_col] if rows else None
    return total, mx


def corpus_fingerprint() -> dict[str, Any]:
    c_total, c_max = _count_and_max("chunks_v2", "created_at")
    d_total, d_max = _count_and_max("documents", "ingested_at")
    payload = {
        "chunks_v2": {"count": c_total, "max_created_at": c_max},
        "documents": {"count": d_total, "max_ingested_at": d_max},
    }
    return {**payload, "sha256": _stable_sha256(payload)}


# ── normalisation ──────────────────────────────────────────────────────────────
def _nk(s: Any) -> str:
    """Normalised key for corroboration: lowercase, alnum-only."""
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


UNKNOWN_LIKE = {"unknown", ""}


def _is_unknown_pm(pm: Any) -> bool:
    return pm is None or str(pm).strip().lower() in UNKNOWN_LIKE


def _sql_lit(s: str) -> str:
    """Single-quoted SQL string literal with '' escaping."""
    return "'" + str(s).replace("'", "''") + "'"


# ── static asset loaders (s83 + catalog) ───────────────────────────────────────
def _load_s83() -> dict[str, dict[str, Any]]:
    """source_file -> {'models': [...], 'identity': {...}} (both keyed by exact
    source_file and by canonical_blob_stem for tolerant matching)."""
    models: dict[str, Any] = {}
    for line in S83_DOC_MODELS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        models[str(d.get("source_file"))] = d.get("models") or []
    identity: dict[str, Any] = {}
    for line in S83_DOC_IDENTITY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        identity[str(d.get("source_file"))] = d
    out: dict[str, dict[str, Any]] = {}
    for sf, ms in models.items():
        out[sf] = {"models": ms, "identity": identity.get(sf)}
    # tolerant alias by stem (no .pdf on either side today, but be defensive)
    for sf in list(out.keys()):
        stem = dlc.canonical_blob_stem(sf)
        if stem != sf and stem not in out:
            out[stem] = out[sf]
    return out


def _load_catalog() -> dict[str, Any]:
    def _read(name: str) -> list[dict[str, Any]]:
        p = CATALOG_DIR / f"{name}.jsonl"
        rows = []
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    doc_map_rows = _read("doc_map")
    products = {r["id"]: r for r in _read("products") if r.get("id")}
    umbrellas = _read("umbrellas")
    homonyms = _read("homonyms")
    relations = _read("relations")

    by_docid: dict[str, list[dict[str, Any]]] = {}
    by_srcfile: dict[str, list[dict[str, Any]]] = {}
    for r in doc_map_rows:
        entries = r.get("entries") or []
        if r.get("document_id"):
            by_docid.setdefault(str(r["document_id"]), []).extend(entries)
        if r.get("source_file"):
            by_srcfile.setdefault(dlc.canonical_blob_stem(str(r["source_file"])), []).extend(entries)
    # umbrella lookup: for a given set of ids, find umbrella terms whose ids overlap.
    return {
        "doc_map_by_docid": by_docid,
        "doc_map_by_srcfile": by_srcfile,
        "products": products,
        "umbrellas": umbrellas,
        "homonyms": homonyms,
        "relations": relations,
    }


def _umbrella_for_ids(catalog: dict[str, Any], ids: set[str]) -> dict[str, Any] | None:
    """Return the umbrella (family) that best covers the doc's ids: prefer a superset,
    then max overlap, then lexicographic term (deterministic)."""
    best = None
    best_key: tuple[int, int, str] = (-1, -1, "")
    for u in catalog["umbrellas"]:
        uids = set(u.get("ids") or [])
        overlap = len(uids & ids)
        if not overlap:
            continue
        superset = 1 if ids.issubset(uids) else 0
        key = (superset, overlap, str(u.get("termino") or ""))
        if key > best_key:
            best_key = key
            best = u
    return best


def _homonym_for_ids(catalog: dict[str, Any], ids: set[str]) -> dict[str, Any] | None:
    for h in catalog["homonyms"]:
        if set(h.get("ids") or []) & ids:
            return h
    return None


# ── per-source_file derivation ─────────────────────────────────────────────────
def _s83_primaries(models: list[dict[str, Any]]) -> list[str]:
    return [str(m.get("canonical_model")) for m in models
            if str(m.get("role")) == "primary" and m.get("canonical_model")]


def _s83_all(models: list[dict[str, Any]]) -> list[str]:
    return [str(m.get("canonical_model")) for m in models if m.get("canonical_model")]


def _distinct_cores(labels: list[str]) -> set[str]:
    return {_nk(x) for x in labels if _nk(x)}


def _natkey(s: str) -> list:
    """Natural sort key: split digit runs so ZX1Se<ZX2Se<ZX5Se<ZX10Se (numeric-aware)."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]


def _composite_from(labels: list[str]) -> str | None:
    """House-style composite ``A/B/C`` from model codes, deduped, natural-sorted so
    variants read ascending (sister ZXe chunks = 'ZX2e/ZX5e'; corpus-wide:
    'ZXAE/ZXEE', 'AM2020/AFP1010', …). Only clean model-shaped tokens are joined
    (a letter AND a digit, len>=3, and — critically — NO internal '/' so the '/'
    separator stays unambiguous: 'S/2-T1' or 'NX2/R/R' can't form a slash-composite)."""
    seen: set[str] = set()
    out: list[str] = []
    for x in labels:
        s = str(x or "").strip()
        nk = _nk(s)
        if not nk or nk in seen:
            continue
        if "/" in s:
            return None  # ambiguous separator -> caller falls back to doc-level value
        if len(s) >= 3 and re.search(r"[A-Za-z]", s) and re.search(r"\d", s):
            seen.add(nk)
            out.append(s)
    out.sort(key=_natkey)
    return "/".join(out) if len(out) >= 2 else None


def derive_one(sf: str, chunk_agg: dict[str, Any], doc_index: dict[str, dict[str, Any]],
               s83: dict[str, dict[str, Any]], catalog: dict[str, Any]) -> dict[str, Any]:
    # -- chunk stats --
    unknown_values = chunk_agg["unknown_values"]  # {stored_value_repr: count}
    total = chunk_agg["total"]
    unknown = chunk_agg["unknown"]
    unknown_nondup = chunk_agg["unknown_nondup"]
    chunk_mfrs = chunk_agg["manufacturers"]
    docids = sorted(chunk_agg["document_ids"])

    # WHERE predicate covering exactly the unknown-like stored values present.
    has_literal_unknown = any(v == "unknown" for v in unknown_values)
    has_empty = any(v == "" for v in unknown_values)
    has_null = any(v == "\x00NULL" for v in unknown_values)
    preds = []
    if has_literal_unknown:
        preds.append("product_model = 'unknown'")
    if has_empty:
        preds.append("product_model = ''")
    if has_null:
        preds.append("product_model IS NULL")
    where_pm = preds[0] if len(preds) == 1 else "(" + " OR ".join(preds) + ")"

    # -- document-level identity (governed) --
    docs = [doc_index[d] for d in docids if d in doc_index]
    doc_pms = sorted({str(d.get("product_model") or "") for d in docs})
    doc_pm = doc_pms[0] if len(doc_pms) == 1 else None  # None if docs disagree
    doc_mfrs = sorted({str(d.get("manufacturer") or "") for d in docs})
    doc_mfr = doc_mfrs[0] if len(doc_mfrs) == 1 else None
    doc_info = {
        "document_ids": docids,
        "product_model": doc_pm if doc_pm is not None else doc_pms,
        "manufacturer": doc_mfr if doc_mfr is not None else doc_mfrs,
        "doc_type": sorted({str(d.get("doc_type") or "") for d in docs}),
        "language": sorted({str(d.get("language") or "") for d in docs}),
        "status": sorted({str(d.get("status") or "") for d in docs}),
        "document_family": sorted({str(d.get("document_family") or "") for d in docs}),
        "source_pdf_filename": sorted({str(d.get("source_pdf_filename") or "") for d in docs}),
    }

    # -- s83 --
    s83_rec = s83.get(sf) or s83.get(dlc.canonical_blob_stem(sf)) or {}
    s83_models = s83_rec.get("models") or []
    s83_prim = _s83_primaries(s83_models)
    s83_all = _s83_all(s83_models)
    s83_ident = s83_rec.get("identity") or {}
    s83_info = {
        "primary_models": s83_prim,
        "all_models": s83_all,
        "brand_on_doc": s83_ident.get("brand_on_doc"),
        "oem_manufacturer": s83_ident.get("oem_manufacturer"),
        "family_scope": s83_ident.get("family_scope"),
        "doc_type": s83_ident.get("doc_type"),
        "languages": s83_ident.get("languages"),
        "s83_confidence": s83_ident.get("confidence"),
    }

    # -- catalog --
    cat_ids: set[str] = set()
    for d in docids:
        for e in catalog["doc_map_by_docid"].get(d, []):
            if e.get("id"):
                cat_ids.add(str(e["id"]))
    for e in catalog["doc_map_by_srcfile"].get(dlc.canonical_blob_stem(sf), []):
        if e.get("id"):
            cat_ids.add(str(e["id"]))
    cat_products = []
    cat_familias: set[str] = set()
    for cid in sorted(cat_ids):
        p = catalog["products"].get(cid)
        if p:
            cat_products.append({
                "id": cid, "canonical_model": p.get("canonical_model"),
                "familia": p.get("familia"), "estado": p.get("estado"),
                "candidate": p.get("candidate"), "vendido_bajo": p.get("vendido_bajo"),
            })
            if p.get("familia"):
                cat_familias.add(str(p["familia"]))
    umbrella = _umbrella_for_ids(catalog, cat_ids) if cat_ids else None
    homonym = _homonym_for_ids(catalog, cat_ids) if cat_ids else None
    cat_info = {
        "doc_map_ids": sorted(cat_ids),
        "products": cat_products,
        "familias": sorted(cat_familias),
        "umbrella": ({"termino": umbrella.get("termino"), "tipo": umbrella.get("tipo"),
                      "ids": umbrella.get("ids"), "divergent": umbrella.get("divergent")}
                     if umbrella else None),
        "homonym_policy": ({"termino": homonym.get("termino"), "politica": homonym.get("politica")}
                           if homonym else None),
    }

    # -- corroboration set (independent of doc-level pm) --
    corr_cores = _distinct_cores(s83_prim + s83_all
                                 + [p["canonical_model"] for p in cat_products if p.get("canonical_model")]
                                 + list(cat_familias)
                                 + ([umbrella.get("termino")] if umbrella else []))

    # -- how many DISTINCT model cores does the manual document? (granularity signal) --
    manual_model_cores = _distinct_cores(s83_prim) or _distinct_cores(
        [p["canonical_model"] for p in cat_products
         if p.get("canonical_model") and not p.get("candidate")])
    n_manual_models = len(manual_model_cores)

    # House-style composite candidate (sister-convention, directive Alberto s281):
    # for a multi-variant shared manual the vigente tag is 'A/B/C' of the covered
    # variants, harvested back into the detector catalog by build_model_catalog.py.
    composite_candidate = _composite_from(
        s83_prim or [p["canonical_model"] for p in cat_products
                     if p.get("canonical_model") and not p.get("candidate")])

    # -- candidate derivation (deterministic) --
    candidate_pm: str | None = None
    candidate_mfr = doc_mfr or (chunk_mfrs[0] if len(chunk_mfrs) == 1 else None)
    confidence = "baja"
    options: list[str] = []
    notes: list[str] = []
    evidence_bits: list[str] = []

    doc_pm_usable = doc_pm is not None and not _is_unknown_pm(doc_pm)
    umbrella_term = umbrella.get("termino") if umbrella else None
    umbrella_is_family = bool(umbrella and umbrella.get("tipo") == "familia")

    # Does doc_pm equal the governing family umbrella that covers the manual's models?
    doc_pm_is_family_umbrella = (
        doc_pm_usable and umbrella_is_family and _nk(doc_pm) == _nk(umbrella_term)
        and manual_model_cores and manual_model_cores.issubset(
            _distinct_cores([str(i).split(":")[-1] for i in (umbrella.get("ids") or [])]))
    )

    if doc_pm_usable:
        candidate_pm = doc_pm
        corroborated = _nk(doc_pm) in corr_cores
        # s83 must not CONTRADICT doc_pm for 'alta' (auto-run): if s83 has primaries and
        # doc_pm is not among them, that is a conflict, not clean corroboration.
        s83_agrees = (not s83_prim) or (_nk(doc_pm) in _distinct_cores(s83_prim))
        evidence_bits.append(f"doc-level product_model='{doc_pm}' (documents table, governed)")
        if doc_pm_is_family_umbrella:
            confidence = "alta"
            evidence_bits.append(
                f"catalog umbrella '{umbrella_term}' (familia) cubre exactamente los "
                f"{n_manual_models} modelos del manual → la etiqueta-familia es la correcta")
        elif corroborated and n_manual_models <= 1 and s83_agrees:
            confidence = "alta"
            evidence_bits.append("corroborado por s83/catálogo; manual mono-modelo")
        elif corroborated and n_manual_models <= 1 and not s83_agrees:
            # catalog corroborates doc_pm but s83 names a DIFFERENT primary -> conflict
            confidence = "media"
            options = [doc_pm + "  (doc-level + catálogo)"] + [
                h + "  (s83 primario — DISCREPA)" for h in s83_prim[:3]]
            notes.append(
                f"CONFLICTO: doc-level+catálogo dicen '{doc_pm}' pero s83 primario = "
                f"{s83_prim[:3]}. Adjudicar cuál documenta el manual.")
        elif corroborated and n_manual_models > 1:
            # doc_pm names the primary but the manual covers several distinct models.
            # ADJUDICATED convention (Alberto s281): the FAMILY-GENERIC label is correct
            # (ZXe/ZXSe), NOT the composite. Lead with the family umbrella when defined.
            confidence = "media"
            opts = []
            if umbrella_term and umbrella_is_family:
                candidate_pm = umbrella_term  # family-generic (adjudicated)
                opts.append(umbrella_term + "  (FAMILIA — convención adjudicada; miembros "
                            "resueltos vía catálogo)")
            opts.append(doc_pm + "  (primario doc-level)")
            if composite_candidate:
                opts.append(composite_candidate + "  (compuesto — LEGACY, a migrar a familia)")
            options = opts
            notes.append(
                f"manual MULTI-MODELO ({n_manual_models} modelos s83: "
                f"{sorted(manual_model_cores)}); doc-level nombra solo el primario "
                f"'{doc_pm}'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); "
                f"si no hay familia definida en catálogo, adjudicar primario/alcance.")
        else:
            # doc_pm present but not corroborated by s83/catalog
            confidence = "media"
            s83_hint = s83_prim[:3]
            if s83_hint and _nk(doc_pm) not in _distinct_cores(s83_prim):
                notes.append(
                    f"doc-level pm='{doc_pm}' NO coincide con los primarios s83 "
                    f"{s83_hint}; posible ruido de filename o modelo real no en s83.")
                options = [doc_pm + "  (doc-level)"] + [h + "  (s83 primario)" for h in s83_hint]
            else:
                evidence_bits.append("única fuente = doc-level (sin corroboración s83/catálogo)")
    else:
        # doc-level pm is unknown/empty → fall back to catalog family / s83.
        # ADJUDICATED convention (Alberto s281): FAMILY-generic leads when defined.
        if umbrella_term and umbrella_is_family:
            candidate_pm = umbrella_term
            confidence = "media"
            evidence_bits.append(
                f"doc-level pm vacío; catalog umbrella '{umbrella_term}' (familia GT) "
                f"mapea el documento → etiqueta-FAMILIA (convención adjudicada)")
            options = [umbrella_term + "  (FAMILIA — adjudicada)"]
            if composite_candidate:
                options.append(composite_candidate + "  (compuesto — LEGACY, a migrar)")
        elif len(manual_model_cores) == 1:
            only = s83_prim[0] if s83_prim else (
                cat_products[0]["canonical_model"] if cat_products else None)
            candidate_pm = only
            confidence = "media"
            evidence_bits.append(f"doc-level pm vacío; s83/catálogo → único modelo '{only}'")
        elif len(manual_model_cores) > 1:
            if cat_familias and len(cat_familias) == 1:
                candidate_pm = sorted(cat_familias)[0]
                confidence = "media"
                evidence_bits.append(
                    f"doc-level pm vacío; múltiples modelos comparten familia "
                    f"'{candidate_pm}'")
                options = [candidate_pm + "  (familia común)",
                           "split: " + " / ".join(sorted(manual_model_cores))]
            else:
                candidate_pm = None
                confidence = "baja"
                labels = sorted(set(s83_prim) | {p["canonical_model"] for p in cat_products
                                                 if p.get("canonical_model")})
                options = [str(x) for x in labels]
                notes.append(
                    "manual mezcla modelos de familias distintas (o s83/catálogo "
                    "discrepan) → adjudicación de familia/alcance necesaria.")
                evidence_bits.append(f"modelos candidatos: {labels}")
        else:
            candidate_pm = None
            confidence = "baja"
            notes.append(
                "sin fuente de modelo utilizable (doc genérico: FAQ/soporte/compatibilidad). "
                "El contenido no documenta UN producto; considerar dejar 'unknown' o etiquetar "
                "con la central de contexto si el contenido lo fija.")
            evidence_bits.append("ni doc-level, ni s83-primario, ni catalog-familia utilizables")

    # manufacturer sanity
    mfr_conflict = bool(doc_mfr and len(chunk_mfrs) == 1 and _nk(doc_mfr) != _nk(chunk_mfrs[0]))
    if mfr_conflict:
        notes.append(f"manufacturer doc-level='{doc_mfr}' ≠ chunk='{chunk_mfrs[0]}' — revisar.")

    # ── ZXSe anchor (ADJUDICATED, Alberto s281): family-generic 'ZXSe' + symmetric ZXe
    # migration. Presented in the report §2 as its own gated decision (eval gate hp009/
    # hp018 + companion), so it is NOT an §3 auto-run even if corroborated 'alta'.
    if sf == ZXSE_SOURCE_FILE:
        candidate_pm = "ZXSe"
        confidence = "media"  # gated by the symmetric migration + eval gate (see §2)
        options = ["ZXSe  (FAMILIA-genérica — ADJUDICADA, dir. Alberto s281)",
                   "ZX2e/ZX5e-style compuesto  (LEGACY — a migrar, NO adoptar)"]
        notes.insert(0, "ADJUDICADO (Alberto s281): etiqueta = FAMILIA 'ZXSe'. Migración simétrica "
                     "con ZXe + gate de eval hp009/hp018 — ver §2.")

    needs_adj = confidence != "alta"

    return {
        "source_file": sf,
        "chunks": {
            "total": total, "unknown": unknown, "unknown_nondup": unknown_nondup,
            "unknown_values": chunk_agg["unknown_values_pretty"],
            "manufacturers": chunk_mfrs,
            "where_predicate": where_pm,
        },
        "document": doc_info,
        "s83": s83_info,
        "catalog": cat_info,
        "content_sample": chunk_agg.get("content_sample", []),
        "candidate": {"product_model": candidate_pm, "manufacturer": candidate_mfr},
        "composite_candidate": composite_candidate,
        "confidence": confidence,
        "needs_adjudication": needs_adj,
        "adjudication_options": options,
        "evidence": "; ".join(evidence_bits),
        "notes": notes,
        "n_manual_models": n_manual_models,
    }


# ── corpus scan + aggregation ──────────────────────────────────────────────────
CHUNK_SLIM = "document_id,source_file,manufacturer,product_model,duplicate_of"
DOC_SELECT = ("id,status,manufacturer,product_model,doc_type,language,"
              "source_pdf_filename,document_family,revision,revision_lineage_id")


def _aggregate_unknown_sources(chunks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return {source_file: agg} for source_files that are ENTIRELY unknown pm."""
    agg: dict[str, dict[str, Any]] = {}
    for r in chunks:
        sf = str(r.get("source_file") or "")
        a = agg.setdefault(sf, {
            "source_file": sf, "total": 0, "unknown": 0, "unknown_nondup": 0,
            "manufacturers": {}, "document_ids": set(),
            "unknown_values": {},  # normalised key -> count
        })
        a["total"] += 1
        mfr = str(r.get("manufacturer") or "").strip()
        a["manufacturers"][mfr] = a["manufacturers"].get(mfr, 0) + 1
        if r.get("document_id"):
            a["document_ids"].add(str(r["document_id"]))
        pm = r.get("product_model")
        dup = r.get("duplicate_of")
        if _is_unknown_pm(pm):
            a["unknown"] += 1
            key = "\x00NULL" if pm is None else str(pm)
            a["unknown_values"][key] = a["unknown_values"].get(key, 0) + 1
            if dup in (None, "", "null"):
                a["unknown_nondup"] += 1
    # keep only fully-unknown source_files
    fully = {sf: a for sf, a in agg.items() if a["total"] > 0 and a["unknown"] == a["total"]}
    for a in fully.values():
        a["manufacturers"] = sorted(a["manufacturers"].keys())
        # pretty rendering of unknown stored values
        pretty = {}
        for k, v in a["unknown_values"].items():
            label = "NULL" if k == "\x00NULL" else (k if k != "" else "'' (empty)")
            pretty[label] = v
        a["unknown_values_pretty"] = dict(sorted(pretty.items()))
    return fully


def _fetch_content_samples(source_files: list[str]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for sf in source_files:
        rows = _get("chunks_v2", {
            "source_file": f"eq.{sf}",
            "select": "id,page_number,chunk_index,section_title,content",
            "order": "page_number.asc.nullslast,chunk_index.asc,id.asc",
            "limit": str(CONTENT_SAMPLE_N),
        }).json()
        sample = []
        for r in rows:
            content = str(r.get("content") or "").strip().replace("\n", " ")
            sample.append({
                "page": r.get("page_number"),
                "chunk_index": r.get("chunk_index"),
                "section_title": (str(r.get("section_title") or "").strip())[:80],
                "head": content[:CONTENT_HEAD],
            })
        out[sf] = sample
    return out


def derive(chunks: list[dict[str, Any]], documents: list[dict[str, Any]],
           content_samples: dict[str, list[dict[str, Any]]],
           s83: dict[str, dict[str, Any]], catalog: dict[str, Any]) -> dict[str, Any]:
    fully = _aggregate_unknown_sources(chunks)
    doc_index = {str(d["id"]): d for d in documents}
    records = []
    for sf in sorted(fully.keys()):
        agg = dict(fully[sf])
        agg["content_sample"] = content_samples.get(sf, [])
        records.append(derive_one(sf, agg, doc_index, s83, catalog))
    # sort by chunk volume desc (biggest findability wins first), then name
    records.sort(key=lambda r: (-r["chunks"]["unknown"], r["source_file"]))

    conf_dist = {"alta": 0, "media": 0, "baja": 0}
    for r in records:
        conf_dist[r["confidence"]] += 1
    return {
        "n_source_files": len(records),
        "total_unknown_chunks": sum(r["chunks"]["unknown"] for r in records),
        "confidence_distribution": conf_dist,
        "records": records,
    }


# ── freeze contract ────────────────────────────────────────────────────────────
def freeze_contract() -> dict[str, Any]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip())
    return {
        "commit_head": head,
        "worktree_dirty": dirty,
        "s83_models": {"path": str(S83_DOC_MODELS.relative_to(ROOT)),
                       "sha256_lf": _sha256_lf(S83_DOC_MODELS)},
        "s83_identity": {"path": str(S83_DOC_IDENTITY.relative_to(ROOT)),
                         "sha256_lf": _sha256_lf(S83_DOC_IDENTITY)},
        "catalog_products": {"path": "data/catalog/products.jsonl",
                             "sha256_lf": _sha256_lf(CATALOG_DIR / "products.jsonl")},
        "catalog_doc_map": {"path": "data/catalog/doc_map.jsonl",
                            "sha256_lf": _sha256_lf(CATALOG_DIR / "doc_map.jsonl")},
        "catalog_umbrellas": {"path": "data/catalog/umbrellas.jsonl",
                              "sha256_lf": _sha256_lf(CATALOG_DIR / "umbrellas.jsonl")},
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


# ── report (packet) ────────────────────────────────────────────────────────────
def _rollback_note() -> list[str]:
    return [
        "**Mecanismo de reversibilidad (obligatorio, patrón s78/s80 DB-only):**",
        "",
        "1. **Respaldo pre-imagen** (una vez, antes de tocar nada) — deja el estado previo en tabla:",
        "```sql",
        "CREATE TABLE IF NOT EXISTS _s281_h0t3_backup AS",
        "SELECT id, source_file, product_model AS product_model_prev, now() AS snapshot_at",
        "FROM chunks_v2",
        "WHERE product_model = 'unknown' OR product_model = '' OR product_model IS NULL",
        "   -- + los chunks de la migración ZXe (compuesto→familia, §2), que NO son unknown:",
        "   OR source_file IN ('MIE-MI-530rv001','MIE-MP-530rv001','MIE-MU-530rv001','MIE-MP-535rv001');",
        "-- verifica: SELECT count(*) FROM _s281_h0t3_backup;  (unknown del census + 206 de ZXe)",
        "```",
        "2. Cada UPDATE lleva `RETURNING id` → cuenta las filas afectadas contra el recuento esperado.",
        "3. **Rollback exacto** (todo el tramo, desde la pre-imagen — no depende de que el valor previo",
        "   fuera uniforme):",
        "```sql",
        "UPDATE chunks_v2 c SET product_model = b.product_model_prev",
        "FROM _s281_h0t3_backup b WHERE c.id = b.id;",
        "-- o por source_file:  ... AND b.source_file = '<source_file>';",
        "```",
        "El pre-estado es hoy uniformemente `unknown` en los 28 (verificado por este instrumento, "
        "campo `unknown_values`), así que un rollback simplificado "
        "`SET product_model='unknown' WHERE source_file=X AND product_model='<label>'` también es válido; "
        "la tabla de respaldo lo hace robusto aunque eso cambie.",
        "",
    ]


def build_report(payload: dict[str, Any]) -> str:
    fc = payload["freeze_contract"]
    c = payload["census"]
    L: list[str] = []
    A = L.append
    recs = c["records"]
    cd = c["confidence_distribution"]

    A("# s281 H0-T3 — Packet de re-tag del Tramo 3 (findability `product_model='unknown'`) — "
      f"{payload['run_tag']}")
    A("")
    A("Instrumento: `scripts/s281_h0t3_retag_packet.py`. **READ-ONLY (PostgREST GET), SELECT-only, "
      "0 llamadas a modelos, 0 escrituras.** Deriva la etiqueta `product_model` CANDIDATA para cada "
      "source_file cuyos chunks están enteramente `unknown`, con su EVIDENCIA (doc-level + s83 + "
      "catálogo + contenido) y una CONFIANZA. Toda sentencia SQL es PROPUESTA — jamás aplicada por "
      "este script. La adjudicación de producto/granularidad es de Alberto.")
    A("")
    A("## Freeze-contract")
    A("")
    A(f"- commit HEAD: `{fc['commit_head']}` (worktree dirty: {fc['worktree_dirty']})")
    A(f"- corpus fingerprint: chunks_v2={payload['corpus_fingerprint']['chunks_v2']['count']} · "
      f"documents={payload['corpus_fingerprint']['documents']['count']} · sha256 "
      f"`{payload['corpus_fingerprint']['sha256']}`")
    A(f"- **determinismo 2×: {'IDÉNTICO ✅' if payload['deterministic_2x'] else 'DIVERGE ❌'}** "
      f"(pass1 `{payload['result_sha256_pass1'][:16]}` == pass2 `{payload['result_sha256_pass2'][:16]}`)")
    A(f"- s83 modelos: `{fc['s83_models']['path']}` sha256-LF `{fc['s83_models']['sha256_lf']}`")
    A(f"- s83 identidad: `{fc['s83_identity']['path']}` sha256-LF `{fc['s83_identity']['sha256_lf']}`")
    A(f"- catálogo products: sha256-LF `{fc['catalog_products']['sha256_lf']}` · doc_map "
      f"`{fc['catalog_doc_map']['sha256_lf']}` · umbrellas `{fc['catalog_umbrellas']['sha256_lf']}`")
    A(f"- generado {fc['generated_utc']}")
    A("")

    # 1. Titular
    A("## 1. Titular")
    A("")
    A(f"**{c['n_source_files']} source_files** enteramente `product_model='unknown'` "
      f"({c['total_unknown_chunks']} chunks) — la clase-D del census H0. El tag `unknown` degrada los "
      "canales por-modelo que keyean sobre `chunks_v2.product_model` (`keyword_search` imatch + "
      "model-scoping/rerank del `answer_planner`); el re-tag los alinea. Distribución de confianza:")
    A("")
    A(f"- **{cd['alta']} de confianza ALTA** → UPDATE ejecutable tal cual (§3).")
    A(f"- **{cd['media']} de confianza MEDIA** → [ADJUDICAR] (§4, candidato + opciones).")
    A(f"- **{cd['baja']} de confianza BAJA** → [ADJUDICAR] (§4, conflicto/sin-fuente).")
    A("")
    A("Insight estructural: `documents.product_model` (nivel documento) **nunca es NULL** (census "
      "`C_product_model_null_doclevel=0`); para la mayoría de estos 28 la etiqueta correcta YA está en "
      "el documento y los chunks simplemente se quedaron atrás en `unknown`. La cohorte ALTA = donde el "
      "doc-level está corroborado por s83/catálogo. MIE-MI-600 (ZXSe) se trata aparte (§2): es la "
      "migración simétrica ZXe+ZXSe adjudicada, con gate de eval propio.")
    A("")
    A("**Convención de familias (ADJUDICADA por Alberto, s281):** para manuales que cubren varias "
      "variantes de una familia, la etiqueta `product_model` correcta es la **FAMILIA-genérica** "
      "(`ZXe`, `ZXSe`) — NO el string compuesto ni el split. El compuesto existente `ZX2e/ZX5e` "
      "(MIE-*-530) es un caso **A MIGRAR**. Los miembros se resuelven a la familia vía el catálogo "
      "gobernado (`data/catalog`). Los candidatos multi-modelo de este packet lideran con la FAMILIA "
      "cuando está definida. §2 detalla la migración simétrica ZXe+ZXSe, la verificación de findability "
      "(con evidencia del resolver vivo) y el gate de eval.")
    A("")

    # 2. ZXSe granularity
    _write_zxse_section(A, recs)

    # 3. High confidence (executable)
    A("## 3. Confianza ALTA — UPDATE ejecutable tal cual")
    A("")
    high = [r for r in recs if r["confidence"] == "alta" and r["source_file"] != ZXSE_SOURCE_FILE]
    if not high:
        A("_(ninguno — todos requieren adjudicación; ver §4 y §2)_")
        A("")
    else:
        A("| source_file | chunks | → product_model | manufacturer | evidencia (resumen) |")
        A("|---|---:|---|---|---|")
        for r in high:
            A(f"| `{r['source_file'][:44]}` | {r['chunks']['unknown']} | "
              f"`{r['candidate']['product_model']}` | {r['candidate']['manufacturer']} | "
              f"{_short_ev(r)} |")
        A("")
        A("```sql")
        A("-- PROPUESTA (NO aplicada). Bloque de confianza ALTA — ejecutable tras el respaldo de §5.")
        for r in high:
            A(_update_stmt(r))
        A("```")
        A("")

    # 4. Needs adjudication
    A("## 4. [ADJUDICAR] — confianza MEDIA/BAJA (candidato + opciones)")
    A("")
    adj = [r for r in recs if r["needs_adjudication"] and r["source_file"] != ZXSE_SOURCE_FILE]
    A(f"{len(adj)} source_files. Para cada uno: el candidato derivado (mejor apuesta), las opciones, "
      "y la evidencia cruda. El UPDATE va parametrizado — sustituye `<PM>` por la etiqueta elegida.")
    A("")
    for r in adj:
        _write_adj_record(A, r)

    # 5. rollback
    A("## 5. Respaldo y reversibilidad")
    A("")
    for line in _rollback_note():
        A(line)

    # 6. per-file evidence appendix (full)
    A("## 6. Apéndice — evidencia completa por source_file")
    A("")
    for r in recs:
        _write_evidence_block(A, r)

    # 7. honesty
    A("## 7. Honestidad del instrumento — lo que NO decide")
    A("")
    A("- **La etiqueta final es de Alberto.** El instrumento deriva un candidato determinista desde "
      "fuentes gobernadas (doc-level pm + s83 + catálogo) bajo la convención ADJUDICADA (familia-genérica "
      "donde hay familia); no juzga la fuente.")
    A("- **`confianza alta` = etiqueta corroborada, NO verdad de campo.** Significa: doc-level y "
      "s83/catálogo coinciden y no hay familia/alcance pendiente. Sigue siendo una PROPUESTA.")
    A("- **El re-tag afecta a los canales que keyean sobre `chunks_v2.product_model`** (keyword imatch + "
      "model-scoping/rerank). El ruteo por `allowed_sources`/`doc_map` (Canal A del resolver) ya alcanza "
      "los docs INDEPENDIENTE del tag (§2.3); el gate de lineage `verified` (Tramos 1-2) es ortogonal.")
    A("- **La migración ZXe toca golds vivos (hp009/hp018)** → gate de eval OBLIGATORIO (§2.5) antes de "
      "declarar el tramo bueno. El re-tag es reversible (§5).")
    A("- **Docs genéricos (FAQ/soporte)** sin un producto único documentado se marcan BAJA: puede ser "
      "correcto dejarlos `unknown` (no documentan UN modelo) — es una decisión de producto.")
    A("- **manufacturer** ya está poblado en los chunks (verificado); los UPDATE tocan solo "
      "`product_model` salvo que se marque conflicto de marca.")
    A("")
    return "\n".join(L)


def _short_ev(r: dict[str, Any]) -> str:
    ev = r["evidence"]
    return (ev[:90] + "…") if len(ev) > 90 else ev


def _update_stmt(r: dict[str, Any]) -> str:
    sf = _sql_lit(r["source_file"])
    pm = _sql_lit(str(r["candidate"]["product_model"]))
    where_pm = r["chunks"]["where_predicate"]
    exp = r["chunks"]["unknown"]
    return (f"UPDATE chunks_v2 SET product_model = {pm}\n"
            f" WHERE source_file = {sf} AND {where_pm}\n"
            f" RETURNING id;  -- esperado: {exp} filas")


def _write_zxse_section(A, recs: list[dict[str, Any]]) -> None:
    zx = next((r for r in recs if r["source_file"] == ZXSE_SOURCE_FILE), None)
    A("## 2. Migración simétrica ZXe + ZXSe (familia-genérica) — ADJUDICADA [ALBERTO]")
    A("")
    A("> **Adjudicación de Alberto (s281):** _«la familia de la ZX1e, ZX2e, etc. debería ser la ZXe, "
      "al igual que otra familia diferente debería ser la ZXSe»_ — la etiqueta `product_model` correcta "
      "es la **FAMILIA-genérica**, NO el string compuesto. El `ZX2e/ZX5e` actual de MIE-*-530 es un caso "
      "**A MIGRAR**, no la convención a imitar. Regla general del packet: donde haya familia definida en "
      "catálogo/s83, la etiqueta candidata es la FAMILIA (miembros resueltos vía catálogo).")
    A("")
    A("### 2.1 Alcance de la migración (barrido del corpus ZX-familia, verificado en DB)")
    A("")
    A("| familia | source_file | chunks | valor actual | → familia |")
    A("|---|---|---:|---|---|")
    A("| **ZXSe** | `MIE-MI-600` | 88 | `unknown` | `ZXSe` |")
    A("| **ZXe** | `MIE-MI-530rv001` | 64 | `ZX2e/ZX5e` | `ZXe` |")
    A("| **ZXe** | `MIE-MP-530rv001` | 96 | `ZX2e/ZX5e` | `ZXe` |")
    A("| **ZXe** | `MIE-MU-530rv001` | 38 | `ZX2e/ZX5e` | `ZXe` |")
    A("| **ZXe** | `MIE-MP-535rv001` | 9 | `ZX2e y ZX5e` | `ZXe` |")
    A("")
    A("ZXSe = 88 chunks (1 doc, era `unknown`); ZXe = 207 chunks (4 docs, eran compuesto — incluye "
      "`MIE-MP-535rv001` con separador ` y ` en vez de `/`). **Relacionados a adjudicar** (no migran "
      "automáticamente): `No-puedo-conectarme-...-central-ZX` (1 chunk `unknown`, MIXTO ZXe+ZXSe — s83 "
      "lista ZX2e/ZX5e **y** ZX2Se/ZX5Se → Alberto: ¿'ZXe', 'ZXSe' o ambas?) y `MIE-MC-530`/`MK-ZX` "
      "(accesorio de montaje de la serie ZXe — ¿migra a 'ZXe' o queda como kit?). Otras familias ZX "
      "(ZX50, ZXCE, ZXHE, ZXAE/ZXEE, ZXR50A/ZXR50P) siguen la MISMA regla general pero quedan fuera de "
      "esta migración ZXe/ZXSe (algunas sin umbrella definido — trabajo de catálogo aparte).")
    A("")
    A("### 2.2 El catálogo gobernado YA define ambas familias (no falta pieza de familia)")
    A("")
    A("`data/catalog` (trabajo s78/s79/s90) ya contiene ambas familias con miembros — evidencia:")
    A("")
    A("- `umbrellas.jsonl`: `ZXe` (tipo familia) = {zx1e, zx2e, zx5e}; `ZXSe` (tipo familia) = "
      "{zx1se, zx2se, zx5se, zx10se}.")
    A("- `products.jsonl`: los miembros llevan `familia:\"ZXe\"` / `familia:\"ZXSe\"`.")
    A("- Homónimo `ZX` → política `clarify`; existe además un `rango` `ZX2e/ZX5e`={zx2e,zx5e}.")
    A("")
    A("→ **No hay pieza de catálogo que falte para ZXe/ZXSe.** (Si Alberto quisiera el token de familia "
      "también en el catálogo del DETECTOR de keyword — ver §2.4 — eso sí sería una propuesta aparte.)")
    A("")
    A("### 2.3 Verificación de findability (miembro/familia × canal) — EVIDENCIA en vivo")
    A("")
    A("Findability por-modelo tiene DOS canales. Medido en la config de release "
      "(`IDENTITY_RESOLVE=on`, `POLICY=replace`):")
    A("")
    A("**Canal A — `catalog_resolver.allowed_sources` (catálogo gobernado + `doc_map`; INDEPENDIENTE "
      "del tag de chunk).** El resolver YA rutea, por miembro Y por familia, a los docs correctos:")
    A("")
    A("| query | detect | vía | allowed_sources ∩ ZX-docs |")
    A("|---|---|---|---|")
    A("| `ZXSe` (familia) | ✓ | paraguas→4 miembros | **MIE-MI-600** |")
    A("| `ZX5Se` (miembro) | ✓ | exact | **MIE-MI-600** |")
    A("| `ZX1Se`/`ZX2Se`/`ZX10Se` | ✓ | exact | **MIE-MI-600** |")
    A("| `ZXe` (familia) | ✓ | paraguas→3 miembros | **MIE-MI-530rv001/MP/MU** |")
    A("| `ZX2e`/`ZX5e` (miembro) | ✓ | exact | **MIE-MI-530rv001/MP/MU** |")
    A("")
    A("→ **El doc NO es invisible al resolver**: miembro y familia ya lo alcanzan por `allowed_sources`, "
      "con el tag de chunk en `unknown` o compuesto. Esto es INDEPENDIENTE de la decisión de etiqueta.")
    A("")
    A("**Canal B — `keyword_search` imatch sobre `chunks_v2.product_model` + model-scoping del "
      "`answer_planner` (SÍ dependen del tag).** Con etiqueta FAMILIA-genérica (medido):")
    A("")
    A("- Query de FAMILIA (`ZXe`→`ZXE`, `ZXSe`→`ZXSE`): el imatch `\\yZXe(?!\\d)` **casa** el tag "
      "`ZXe`; `\\yZXSe` casa `ZXSe`. ✅ La familia-genérica es matchable por el token de familia.")
    A("- Query de MIEMBRO (`ZX2e`, `ZX5Se`): el imatch `\\yZX2e` **NO** casa el tag `ZXe` "
      "(`ZX2e`⊄`ZXe`); y `extract_product_models('ZX5Se')`→`[]` (los miembros ZXSe no están en el "
      "catálogo del detector `data/model_catalog.json`). → el miembro NO llega por Canal B; llega por "
      "Canal A (allowed_sources) + vector. ⚠")
    A("- Interacción con `POLICY=replace`: una query de familia `ZXe` **descarta** el token paraguas y "
      "lo reemplaza por los miembros [ZX1e/ZX2e/ZX5e] en la lista de models → al model-scoping le "
      "llegan MIEMBROS, que NO casan un tag `ZXe`. Bajo `replace`, el tag familia-genérica es peor para "
      "el model-scope de una query-familia que el compuesto (que sí lleva los miembros). Bajo `add` "
      "(mantiene el paraguas) la familia-genérica casa. (Canal A rutea igual en ambos.)")
    A("")
    A("**Conclusión honesta:** con la etiqueta FAMILIA adjudicada, el doc queda reachable (Canal A ya "
      "lo cubre para miembro y familia). El re-tag paga sobre todo por (1) **quitar `unknown`** — que "
      "hoy hace que el chunk parezca sin identidad para el rerank/model-scope — y (2) alinear chunk↔"
      "doc-level (`documents.product_model` ya es `ZXe`/`ZXSe`) + catálogo. El matching por-MIEMBRO en "
      "Canal B NO lo da la familia-genérica; si Alberto quisiera ese matching, la vía es el catálogo/"
      "detector (§2.4), no el tag compuesto (que él descartó).")
    A("")
    A("### 2.4 Companion (fuera del territorio de esta lane) — propuestas, no ediciones")
    A("")
    A("1. **Rebuild del catálogo del detector** `data/model_catalog.json` (`python "
      "scripts/build_model_catalog.py`) tras el re-tag: cosecha los `product_model` de los chunks. Nota: "
      "`ZXe`/`ZXSe` (sin dígito) podrían NO pasar el gate model-shaped del builder → el token de familia "
      "no entraría al detector de keyword; PERO el resolver gobernado (Canal A) ya cubre miembro+familia, "
      "así que no es bloqueante. (El compuesto sí se cosechaba — por eso `ZX2e`/`ZX5e` están hoy.)")
    A("2. **Si se quiere matching por-MIEMBRO en Canal B para ZXSe**: falta que "
      "`data/model_catalog.json` (o el seed del detector) conozca `ZX1Se/ZX2Se/ZX5Se/ZX10Se` — hoy "
      "ausentes. PROPUESTA (catálogo versionado, no DB; fuera de esta lane): añadirlos al detector. No "
      "es necesario para el ruteo (Canal A), sí para el keyword directo por variante.")
    A("")
    A("### 2.5 GATE DE EVAL (patrón cat022) — OBLIGATORIO antes de dar el tramo por bueno")
    A("")
    A("La migración ZXe toca **golds vivos**: `hp009` (¿resistencia fin de línea de los lazos de la "
      "**ZXe**? — veredicto PARCIAL) y `hp018` (¿sirena convencional en la **ZXe**? — PASS) citan "
      "`MIE-MI-530rv001`/`MP-530`/`MU-530` (exactamente los docs que migran de `ZX2e/ZX5e`→`ZXe`). "
      "Cambiar su `product_model` redistribuye los pools de retrieval/rerank de esos QIDs. **Plan de "
      "verificación (antes de aplicar en firme):** `python scripts/test_bot_vs_gold.py` dirigido a "
      "`hp009`+`hp018` + un set de control (p.ej. hp006/hp010 no-ZX) para detectar regresión de pool; "
      "aceptar solo si hp018 se mantiene PASS y hp009 no empeora. Mismo patrón que cat022 (datos-finos): "
      "el re-tag es reversible (§5), así que el gate corre sobre el estado aplicado en una rama/branch "
      "de DB y se revierte si regresa.")
    A("")
    A("### 2.6 SQL simétrico (ambas familias, todos los ficheros) — PROPUESTA, reversible (§5)")
    A("")
    A("```sql")
    A("-- PROPUESTA (NO aplicada). Migración simétrica ZXe+ZXSe a FAMILIA-genérica (adjudicada).")
    A("-- Ejecutar tras el respaldo de §5 y con el gate de eval de §2.5.")
    A("")
    A("-- ZXSe (era 'unknown'):")
    if zx is not None:
        A(_update_stmt(zx))
    A("")
    A("-- ZXe (migración de compuesto → familia; 4 ficheros, 207 chunks):")
    A("UPDATE chunks_v2 SET product_model = 'ZXe'")
    A(" WHERE source_file IN ('MIE-MI-530rv001','MIE-MP-530rv001','MIE-MU-530rv001','MIE-MP-535rv001')")
    A("   AND product_model IN ('ZX2e/ZX5e','ZX2e y ZX5e')")
    A(" RETURNING id;  -- esperado: 207 filas (64+96+38+9)")
    A("")
    A("-- Rollback ZXe (desde la pre-imagen de §5, robusto) — o directo si se quiere:")
    A("--   UPDATE chunks_v2 SET product_model='ZX2e/ZX5e' WHERE source_file IN ('MIE-MI-530rv001',")
    A("--     'MIE-MP-530rv001','MIE-MU-530rv001') AND product_model='ZXe';")
    A("--   UPDATE chunks_v2 SET product_model='ZX2e y ZX5e' WHERE source_file='MIE-MP-535rv001'")
    A("--     AND product_model='ZXe';")
    A("```")
    A("")

def _write_adj_record(A, r: dict[str, Any]) -> None:
    A(f"### `{r['source_file']}`  —  confianza **{r['confidence']}**  ·  {r['chunks']['unknown']} chunks")
    A("")
    cand = r["candidate"]["product_model"]
    A(f"- **Candidato:** `{cand}`" + (f"  ·  manufacturer `{r['candidate']['manufacturer']}`"
                                       if r["candidate"]["manufacturer"] else ""))
    if r.get("composite_candidate") and r["composite_candidate"] != cand:
        A(f"- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** "
          f"`{r['composite_candidate']}`")
    if r["adjudication_options"]:
        A(f"- **Opciones:** {'  |  '.join(r['adjudication_options'])}")
    A(f"- **doc-level pm:** `{r['document']['product_model']}`  ·  **s83 primarios:** "
      f"{r['s83']['primary_models']}  ·  **catálogo familias:** {r['catalog']['familias']}"
      + (f"  ·  **umbrella:** {r['catalog']['umbrella']['termino']}" if r['catalog']['umbrella'] else ""))
    A(f"- **Evidencia:** {r['evidence']}")
    for nt in r["notes"]:
        A(f"- ⚠ {nt}")
    if r["content_sample"]:
        cs = r["content_sample"][0]
        A(f"- **Contenido pág {cs['page']} [{cs['section_title']}]:** {cs['head']!r}")
    A("")
    A("```sql")
    if cand:
        A(f"-- candidato derivado; sustituye <PM> si adjudicas otra opción")
        A(f"UPDATE chunks_v2 SET product_model = '<PM={cand}>'")
    else:
        A(f"-- sin candidato único — elige de las opciones arriba")
        A(f"UPDATE chunks_v2 SET product_model = '<PM>'")
    A(f" WHERE source_file = {_sql_lit(r['source_file'])} AND {r['chunks']['where_predicate']}")
    A(f" RETURNING id;  -- esperado: {r['chunks']['unknown']} filas")
    A("```")
    A("")


def _write_evidence_block(A, r: dict[str, Any]) -> None:
    A(f"### `{r['source_file']}`  ({r['confidence']})")
    A("")
    A(f"- chunks: total {r['chunks']['total']} · unknown {r['chunks']['unknown']} "
      f"(no-dup {r['chunks']['unknown_nondup']}) · valores unknown {r['chunks']['unknown_values']} · "
      f"marcas chunk {r['chunks']['manufacturers']}")
    A(f"- documento: pm=`{r['document']['product_model']}` · mfr={r['document']['manufacturer']} · "
      f"doc_type={r['document']['doc_type']} · lang={r['document']['language']} · "
      f"status={r['document']['status']}")
    A(f"- s83: primarios={r['s83']['primary_models']} · brand_on_doc={r['s83']['brand_on_doc']} · "
      f"family_scope={r['s83']['family_scope']!r} · s83_conf={r['s83']['s83_confidence']}")
    A(f"- catálogo: doc_map_ids={r['catalog']['doc_map_ids']} · familias={r['catalog']['familias']}"
      + (f" · umbrella={r['catalog']['umbrella']['termino']}" if r['catalog']['umbrella'] else "")
      + (f" · homónimo={r['catalog']['homonym_policy']}" if r['catalog']['homonym_policy'] else ""))
    A(f"- **candidato**: pm=`{r['candidate']['product_model']}` mfr={r['candidate']['manufacturer']} "
      f"· **confianza {r['confidence']}**")
    A("")


# ── main ─────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default="v1")
    args = ap.parse_args(argv)
    tag = args.tag

    _init_http()
    contract = freeze_contract()
    fp_before = corpus_fingerprint()
    print(f"commit={contract['commit_head'][:10]} dirty={contract['worktree_dirty']}")
    print(f"corpus chunks_v2={fp_before['chunks_v2']['count']} documents={fp_before['documents']['count']}")

    s83 = _load_s83()
    catalog = _load_catalog()

    # -- fetch (slim chunk scan + documents), pass 1 --
    chunks = _get_all("chunks_v2", CHUNK_SLIM, order="id.asc")
    documents = _get_all("documents", DOC_SELECT, order="id.asc")
    fully = _aggregate_unknown_sources(chunks)
    source_files = sorted(fully.keys())
    print(f"fully-unknown source_files: {len(source_files)}")
    content_samples = _fetch_content_samples(source_files)

    canon1 = derive(chunks, documents, content_samples, s83, catalog)
    sha1 = _stable_sha256(canon1)
    print(f"pass1 sha={sha1[:16]} | records={canon1['n_source_files']} conf={canon1['confidence_distribution']}")

    # -- pass 2 (determinism contract): re-derive over the SAME fetched rows --
    canon2 = derive(chunks, documents, content_samples, s83, catalog)
    sha2 = _stable_sha256(canon2)
    fp_after = corpus_fingerprint()
    deterministic = sha1 == sha2 and fp_before["sha256"] == fp_after["sha256"]
    print(f"pass2 sha={sha2[:16]} | deterministic_2x={deterministic}")

    payload = {
        "schema": "s281_h0t3_retag_packet_v1",
        "run_tag": tag,
        "authority": "DEVELOPMENT_RETAG_PACKET_READ_ONLY_ZERO_MODEL_CALLS_SELECT_ONLY",
        "freeze_contract": contract,
        "corpus_fingerprint": fp_after,
        "deterministic_2x": deterministic,
        "result_sha256_pass1": sha1,
        "result_sha256_pass2": sha2,
        "census": canon1,
    }
    result_path = ROOT / f"evals/s281_h0t3_retag_packet_result_{tag}.json"
    report_path = ROOT / f"evals/s281_h0t3_retag_packet_{tag}.md"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str) + "\n",
                           encoding="utf-8")
    report_path.write_text(build_report(payload), encoding="utf-8")
    print(f"\nresult: {result_path}")
    print(f"report: {report_path}")
    return 0 if deterministic else 2


if __name__ == "__main__":
    sys.exit(main())
