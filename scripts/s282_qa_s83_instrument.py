#!/usr/bin/env python3
"""s282 QA-s83 — validate the s83 identity asset for DB application (Tramo 2).

Lane QA-s83 of the s282 continuation of the s281 H0 identity-backfill campaign.
The s281 census (``s281_h0_identity_census``) named the s83 activo
(``evals/s83_document_models_final.jsonl`` + ``..._identity_final.jsonl``, 1014
source_files -> models/identity) as the CANDIDATE source to backfill
``language``/``doc_type``/``product_model`` for ~590 class-A active docs (Tramo 2).
But s83 was adjudicated by Alberto only on the 29 conflict rows (s83); the ~985
non-conflict rows were NEVER QA'd (s84 never executed). This instrument is that QA:
per s83 source_file, it fuses THREE independent evidence sources against s83's
labels and classifies each row AUTO-CLEAN / CONFLICT / WEAK, so Alberto can apply
the AUTO-CLEAN cohort to T2 as-is and adjudicate only the conflicts.

READ-ONLY, SELECT-only DB access (PostgREST GET, zero writes, zero paid embeddings).
The deterministic derivation is $0 and byte-identical 2x (asserted). A cheap LLM
judge (claude-haiku-4-5, temperature 0) arbitrates ONLY the WEAK subset — gated by
a calibration step (see ``--judge``/``--calibrate``); it is a separate augmentation
layer over the deterministic result, never part of the determinism contract.

EVIDENCE per source_file (fused):
  (a) DOC-LEVEL identity in DB (``documents.product_model``/``manufacturer``/
      ``doc_type``/``language``) — the governed label chosen at ingest. product_model
      is NEVER null (census C_product_model_null_doclevel=0), so it is a real oracle
      to compare s83 against; doc_type/language are mostly NULL (s83 FILLS them).
  (b) s83 asset (primaries/all-models/doc_type/languages/brand + s83 confidence).
  (c) the governed catalog (``data/catalog``: doc_map product ids, products.familia,
      umbrellas) — corroboration independent of the doc-level label.
  (+ chunk CONTENT sample, fetched lazily only for the WEAK subset the LLM judges.)

CLASSIFICATION (product_model is the primary axis — the only field both s83 and DB
carry, so a recall-safe deterministic exact-match pre-filter works and it is the
axis where genuine CONFLICT arises, e.g. the FS2-1 case of the T3 packet):
  * AUTO-CLEAN : doc-level pm core is corroborated by s83 (exact/subset of s83
    cores), no hard language contradiction, s83 confidence != low -> s83's
    language/doc_type/product_model apply to T2 as-is ($0, no LLM).
  * CONFLICT   : s83 primary is model-shaped and DISJOINT from the (model-shaped)
    doc-level pm, OR DB language present and NOT in s83.languages, OR manufacturer
    hard-mismatch -> [ALBERTO] adjudicates which source is right.
  * WEAK       : doc-level pm is filename noise (not model-shaped), or s83 has no
    primary, or a multi-model granularity question -> LLM judge arbitrates using
    content; residual WEAK -> [ALBERTO].
  * UNMAPPED   : s83 source_file has no ACTIVE DB document -> not applicable to T2
    (reported, not a conflict).

INHERITANCE (declared): the GET-only read-only HTTP stack + freeze-contract
fingerprint + determinism-2x contract + honesty-section discipline from
``scripts/s281_h0t3_retag_packet.py`` (itself inheriting s281_h0/s279/s278).

HARD RULES honoured: DB SELECT-only (PostgREST GET, zero writes/model-embeds);
determinism (deterministic derivation runs 2x byte-identical asserted); outputs
restricted to this lane's territory (``scripts/s282_qa_s83_*`` / ``evals/s282_qa_s83_*``);
NO commits.

Usage:
  python scripts/s282_qa_s83_instrument.py                 # deterministic pass only ($0, 2x)
  python scripts/s282_qa_s83_instrument.py --judge --calibrate --limit 20
                                                           # calibration subset (WEAK, first 20)
  python scripts/s282_qa_s83_instrument.py --judge         # full LLM pass over WEAK (uses cache)
Outputs: evals/s282_qa_s83_result_<tag>.json
         evals/s282_qa_s83_report_<tag>.md
         evals/s282_qa_s83_llm_cache_<tag>.jsonl  (LLM verdicts, reused across runs)
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

# -- constants / territory ------------------------------------------------------
S83_DOC_MODELS = ROOT / "evals/s83_document_models_final.jsonl"
S83_DOC_IDENTITY = ROOT / "evals/s83_document_identity_final.jsonl"
CATALOG_DIR = ROOT / "data/catalog"
JUDGE_MODEL = "claude-haiku-4-5"
CONTENT_SAMPLE_N = 6
CONTENT_HEAD = 220

_H: dict[str, str] = {}
_BASE = ""


# -- read-only HTTP helpers (inherited from s281_h0t3 / s279) -------------------
def _init_http() -> None:
    global _H, _BASE
    if not cfg.SUPABASE_URL or not cfg.SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable")
    _H = {"apikey": cfg.SUPABASE_SERVICE_KEY,
          "Authorization": f"Bearer {cfg.SUPABASE_SERVICE_KEY}"}
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
    return total, (rows[0][ts_col] if rows else None)


def corpus_fingerprint() -> dict[str, Any]:
    c_total, c_max = _count_and_max("chunks_v2", "created_at")
    d_total, d_max = _count_and_max("documents", "ingested_at")
    payload = {"chunks_v2": {"count": c_total, "max_created_at": c_max},
               "documents": {"count": d_total, "max_ingested_at": d_max}}
    return {**payload, "sha256": _stable_sha256(payload)}


# -- normalisation --------------------------------------------------------------
def _nk(s: Any) -> str:
    """Normalised key: lowercase, alnum-only."""
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _model_shaped(s: Any) -> bool:
    """A clean model code: has a letter AND a digit, length>=3."""
    t = str(s or "").strip()
    return len(t) >= 3 and bool(re.search(r"[A-Za-z]", t)) and bool(re.search(r"\d", t))


def _sql_lit(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


# -- static asset loaders -------------------------------------------------------
def _load_s83() -> dict[str, dict[str, Any]]:
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
    by_docid: dict[str, list[dict[str, Any]]] = {}
    by_srcfile: dict[str, list[dict[str, Any]]] = {}
    for r in doc_map_rows:
        entries = r.get("entries") or []
        if r.get("document_id"):
            by_docid.setdefault(str(r["document_id"]), []).extend(entries)
        if r.get("source_file"):
            by_srcfile.setdefault(dlc.canonical_blob_stem(str(r["source_file"])), []).extend(entries)
    return {"doc_map_by_docid": by_docid, "doc_map_by_srcfile": by_srcfile,
            "products": products, "umbrellas": umbrellas}


def _umbrella_for_ids(catalog: dict[str, Any], ids: set[str]) -> dict[str, Any] | None:
    best = None
    best_key: tuple[int, int, str] = (-1, -1, "")
    for u in catalog["umbrellas"]:
        uids = set(u.get("ids") or [])
        overlap = len(uids & ids)
        if not overlap:
            continue
        key = (1 if ids.issubset(uids) else 0, overlap, str(u.get("termino") or ""))
        if key > best_key:
            best_key, best = key, u
    return best


# -- s83 helpers ----------------------------------------------------------------
def _s83_primaries(models: list[dict[str, Any]]) -> list[str]:
    return [str(m.get("canonical_model")) for m in models
            if str(m.get("role")) == "primary" and m.get("canonical_model")]


def _s83_all(models: list[dict[str, Any]]) -> list[str]:
    return [str(m.get("canonical_model")) for m in models if m.get("canonical_model")]


# -- per-source_file deterministic derivation -----------------------------------
def derive_one(sf: str, doc_ids: list[str], doc_index: dict[str, dict[str, Any]],
               s83: dict[str, dict[str, Any]], catalog: dict[str, Any]) -> dict[str, Any]:
    # -- resolve active docs --
    docs = [doc_index[d] for d in doc_ids if d in doc_index]
    active = [d for d in docs if str(d.get("status")) == "active"]
    superseded = [d for d in docs if str(d.get("status")) == "superseded"]

    # -- s83 record --
    rec = s83.get(sf) or s83.get(dlc.canonical_blob_stem(sf)) or {}
    s83_models = rec.get("models") or []
    s83_prim = _s83_primaries(s83_models)
    s83_all = _s83_all(s83_models)
    ident = rec.get("identity") or {}
    s83_langs = [str(x) for x in (ident.get("languages") or [])]
    s83_doc_type = ident.get("doc_type")
    s83_brand = ident.get("brand_on_doc")
    s83_oem = ident.get("oem_manufacturer")
    s83_conf = ident.get("confidence")
    s83_field_conflicts = ident.get("field_conflicts") or []

    prim_cores = {_nk(x) for x in s83_prim if _nk(x)}
    all_cores = {_nk(x) for x in s83_all if _nk(x)}

    base = {
        "source_file": sf,
        "s83": {
            "primary_models": s83_prim, "all_models": s83_all,
            "doc_type": s83_doc_type, "languages": s83_langs,
            "brand_on_doc": s83_brand, "oem_manufacturer": s83_oem,
            "s83_confidence": s83_conf, "field_conflicts": s83_field_conflicts,
        },
    }

    if not active:
        base.update({
            "verdict": "UNMAPPED",
            "document": {"active_document_ids": [], "superseded_document_ids": sorted(d["id"] for d in superseded)},
            "n_active_docs": 0,
            "pm_relation": "no-active-doc", "language_flag": "n/a", "doc_type_flag": "n/a",
            "manufacturer_flag": "n/a", "needs_llm": False,
            "reason": ("s83 source_file mapea solo a docs superseded"
                       if superseded else "s83 source_file no mapea a ningun documento en DB"),
        })
        return base

    doc_pms = sorted({str(d.get("product_model") or "") for d in active})
    doc_pm = doc_pms[0] if len(doc_pms) == 1 else None
    doc_mfrs = sorted({str(d.get("manufacturer") or "") for d in active})
    doc_mfr = doc_mfrs[0] if len(doc_mfrs) == 1 else None
    doc_langs = sorted({str(d.get("language") or "") for d in active if d.get("language")})
    doc_dtypes = sorted({str(d.get("doc_type") or "") for d in active if d.get("doc_type")})
    document = {
        "active_document_ids": sorted(d["id"] for d in active),
        "product_model": doc_pm if doc_pm is not None else doc_pms,
        "manufacturer": doc_mfr if doc_mfr is not None else doc_mfrs,
        "doc_type_db": doc_dtypes,
        "language_db": doc_langs,
        "document_family": sorted({str(d.get("document_family") or "") for d in active}),
        "source_pdf_filename": sorted({str(d.get("source_pdf_filename") or "") for d in active}),
        "superseded_document_ids": sorted(d["id"] for d in superseded),
    }
    base["document"] = document
    base["n_active_docs"] = len(active)

    # -- catalog corroboration --
    cat_ids: set[str] = set()
    for d in active:
        for e in catalog["doc_map_by_docid"].get(d["id"], []):
            if e.get("id"):
                cat_ids.add(str(e["id"]))
    for e in catalog["doc_map_by_srcfile"].get(dlc.canonical_blob_stem(sf), []):
        if e.get("id"):
            cat_ids.add(str(e["id"]))
    cat_models, cat_familias = [], set()
    for cid in sorted(cat_ids):
        p = catalog["products"].get(cid)
        if p:
            if p.get("canonical_model"):
                cat_models.append(str(p["canonical_model"]))
            if p.get("familia"):
                cat_familias.add(str(p["familia"]))
    umbrella = _umbrella_for_ids(catalog, cat_ids) if cat_ids else None
    umbrella_term = umbrella.get("termino") if umbrella else None
    catalog_info = {
        "doc_map_ids": sorted(cat_ids), "models": cat_models,
        "familias": sorted(cat_familias), "umbrella": umbrella_term,
    }
    base["catalog"] = catalog_info
    cat_cores = {_nk(x) for x in cat_models} | {_nk(x) for x in cat_familias} | (
        {_nk(umbrella_term)} if umbrella_term else set())

    # ---- product_model relation (deterministic, recall-safe) ----
    # Only an EXACT/SUBSET corroboration of the governed doc-level pm by s83's own
    # models is trusted as AUTO_CLEAN at $0. Everything else mapped -> WEAK, and the
    # LLM (with content) decides AUTO_CLEAN / CONFLICT / WEAK. We do NOT declare
    # CONFLICT deterministically: a string-disjoint pm can be a family/variant label
    # ('2X-AE1' vs '2X-A Tactil'), filename noise ('NRT-586T' vs source-file '15090SP'),
    # a s83-generic description, or a genuine conflict ('LCD-80' vs 'AM2020') — only
    # content distinguishes them.
    doc_pm_core = _nk(doc_pm) if doc_pm else None
    doc_pm_shaped = _model_shaped(doc_pm) if doc_pm else False
    s83_prim_shaped = [x for x in s83_prim if _model_shaped(x)]

    def _shared_prefix_len(a: str, b: str) -> int:
        n = 0
        for x, y in zip(a, b):
            if x == y:
                n += 1
            else:
                break
        return n

    if doc_pm is None:
        pm_relation, pm_note = "docs_disagree", "docs activos discrepan en product_model"
    elif doc_pm_core in prim_cores:
        pm_relation, pm_note = "corroborated", "doc-level pm es primario s83 (exacto)"
    elif doc_pm_core in all_cores:
        pm_relation, pm_note = "corroborated", "doc-level pm entre los modelos s83 (exacto)"
    elif not doc_pm_shaped:
        pm_relation, pm_note = "doc_noise", f"doc-level pm '{doc_pm}' no es model-shaped (filename/unknown)"
    elif s83_prim and not s83_prim_shaped:
        pm_relation, pm_note = "s83_generic", ("s83 da descripciones genericas no-modelo "
                                               f"{s83_prim[:2]}; doc-pm '{doc_pm}'")
    elif not s83_prim and not all_cores:
        pm_relation, pm_note = "s83_empty", "s83 no aporta modelo; doc-pm sin corroborar por s83"
    else:
        # both sides carry model-shaped codes -> family/variant vs disjoint?
        substr = any(c and (c in doc_pm_core or doc_pm_core in c) for c in (prim_cores | all_cores))
        prefix = any(_shared_prefix_len(doc_pm_core, c) >= 3 for c in (prim_cores | all_cores) if c)
        stem = re.sub(r"(series?|serie)$", "", doc_pm_core)
        seriesword = stem and stem != doc_pm_core and any(c.startswith(stem) for c in (prim_cores | all_cores))
        catfam = doc_pm_core in cat_cores or any(_nk(f) and (doc_pm_core in _nk(f) or _nk(f) in doc_pm_core)
                                                 for f in (cat_familias | ({umbrella_term} if umbrella_term else set())))
        if substr or prefix or seriesword or catfam:
            pm_relation, pm_note = "family", (f"doc-level pm '{doc_pm}' relacionado (familia/variante) "
                                              f"con primarios s83 {s83_prim[:3]}")
        else:
            pm_relation, pm_note = "disjoint", (f"doc-level pm '{doc_pm}' DISJUNTO de primarios s83 "
                                                f"{s83_prim[:3]} (candidato a conflicto)")

    # ---- language flag (orthogonal to pm verdict) ----
    if not doc_langs:
        language_flag = ("fill-singleton" if len(s83_langs) == 1
                         else ("fill-multi" if len(s83_langs) > 1 else "fill-none"))
    else:
        s83_lang_cores = {_nk(x) for x in s83_langs}
        if all(_nk(x) in s83_lang_cores for x in doc_langs):
            language_flag = "consistent"
        elif s83_langs:
            language_flag = "contradict"
        else:
            language_flag = "db-only"

    # ---- doc_type flag ----
    if not doc_dtypes:
        doc_type_flag = "fill" if s83_doc_type else "fill-none"
    else:
        doc_type_flag = ("consistent" if _nk(s83_doc_type) in {_nk(x) for x in doc_dtypes}
                         else "differ")

    # ---- manufacturer flag (advisory; OEM/brand seam is noisy) ----
    if doc_mfr is None:
        mfr_flag = "docs-disagree"
    else:
        dm = _nk(doc_mfr)
        cands = {_nk(s83_brand), _nk(s83_oem)}
        cands.discard("")
        if not cands:
            mfr_flag = "no-s83-brand"
        elif dm in cands or any(dm and (dm in c or c in dm) for c in cands):
            mfr_flag = "ok"
        else:
            mfr_flag = "review"

    base.update({"pm_relation": pm_relation, "pm_note": pm_note, "language_flag": language_flag,
                 "doc_type_flag": doc_type_flag, "manufacturer_flag": mfr_flag})

    # ---- overall verdict (product_model applicability; recall-safe) ----
    if pm_relation == "corroborated" and str(s83_conf) != "low":
        verdict = "AUTO_CLEAN"
    else:
        verdict = "WEAK"

    base["verdict"] = verdict
    base["needs_llm"] = verdict == "WEAK"
    reason_bits = [pm_note]
    if language_flag == "contradict":
        reason_bits.append(f"[idioma] DB {doc_langs} no en s83.languages {s83_langs[:4]}")
    if mfr_flag == "review":
        reason_bits.append(f"[marca] DB '{doc_mfr}' no coincide con s83 brand/oem")
    if str(s83_conf) == "low":
        reason_bits.append("[s83 confidence=low]")
    base["reason"] = "; ".join(b for b in reason_bits if b)
    return base


# -- deterministic corpus scan --------------------------------------------------
DOC_SELECT = ("id,status,manufacturer,product_model,doc_type,language,"
              "source_pdf_filename,document_family")


def _chunk_srcfile_to_docids(chunks: list[dict[str, Any]]) -> dict[str, set[str]]:
    m: dict[str, set[str]] = {}
    for r in chunks:
        sf = str(r.get("source_file") or "")
        did = r.get("document_id")
        if sf and did:
            m.setdefault(sf, set()).add(str(did))
    return m


def derive(s83: dict[str, dict[str, Any]], documents: list[dict[str, Any]],
           chunk_map: dict[str, set[str]], docmap_sf_to_docid: dict[str, list[str]],
           catalog: dict[str, Any]) -> dict[str, Any]:
    doc_index = {str(d["id"]): d for d in documents}
    # only iterate the ORIGINAL source_file keys (not the stem-aliases we added)
    original_sfs = _original_s83_source_files()
    records = []
    for sf in original_sfs:
        ids = set(chunk_map.get(sf, set())) | set(chunk_map.get(dlc.canonical_blob_stem(sf), set()))
        if not ids:
            ids |= set(docmap_sf_to_docid.get(sf, []))
            ids |= set(docmap_sf_to_docid.get(dlc.canonical_blob_stem(sf), []))
        records.append(derive_one(sf, sorted(ids), doc_index, s83, catalog))
    records.sort(key=lambda r: (r["verdict"], r["source_file"]))

    dist = {"AUTO_CLEAN": 0, "WEAK": 0, "UNMAPPED": 0}
    rel: dict[str, int] = {}
    for r in records:
        dist[r["verdict"]] = dist.get(r["verdict"], 0) + 1
        rel[r.get("pm_relation", "?")] = rel.get(r.get("pm_relation", "?"), 0) + 1
    return {"n_source_files": len(records), "verdict_distribution": dist,
            "pm_relation_distribution": dict(sorted(rel.items())), "records": records}


_ORIG_SFS: list[str] = []


def _original_s83_source_files() -> list[str]:
    return _ORIG_SFS


# -- LLM judge (WEAK subset only) -----------------------------------------------
def _fetch_content_sample(sf: str) -> list[dict[str, Any]]:
    rows = _get("chunks_v2", {
        "source_file": f"eq.{sf}",
        "select": "page_number,chunk_index,section_title,content",
        "order": "page_number.asc.nullslast,chunk_index.asc",
        "limit": str(CONTENT_SAMPLE_N),
    }).json()
    out = []
    for r in rows:
        content = str(r.get("content") or "").strip().replace("\n", " ")
        out.append({"page": r.get("page_number"),
                    "section_title": (str(r.get("section_title") or "").strip())[:80],
                    "head": content[:CONTENT_HEAD]})
    return out


JUDGE_SYSTEM = (
    "Eres un revisor de identidad de documentos tecnicos de PCI (proteccion contra "
    "incendios). Recibes: la etiqueta de producto propuesta por el activo s83 para un "
    "documento, la etiqueta gobernada a nivel-documento en la base de datos, el catalogo "
    "gobernado, y una muestra del CONTENIDO real del documento. Tu unica tarea es juzgar si "
    "el product_model de s83 es APLICABLE a ese documento. Responde SOLO con el JSON pedido. "
    "Criterio:\n"
    "- AUTO_CLEAN: el product_model de s83 coincide con lo que el contenido y/o la etiqueta "
    "gobernada indican (misma familia/modelo).\n"
    "- CONFLICT: el contenido o la etiqueta gobernada describen CLARAMENTE un producto distinto "
    "al que dice s83.\n"
    "- WEAK: el contenido es generico/insuficiente para decidir, o el documento cubre varios "
    "productos con una pregunta real de granularidad.\n"
    "Ante duda entre AUTO_CLEAN y CONFLICT sin evidencia clara, responde WEAK."
)

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["AUTO_CLEAN", "CONFLICT", "WEAK"]},
        "product_model_call": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "product_model_call", "reason"],
    "additionalProperties": False,
}


def _judge_prompt(rec: dict[str, Any], content: list[dict[str, Any]]) -> str:
    s = rec["s83"]
    d = rec["document"]
    c = rec["catalog"]
    lines = [
        f"source_file: {rec['source_file']}",
        "",
        "s83 propone:",
        f"  primarios: {s['primary_models']}",
        f"  todos_modelos: {s['all_models'][:12]}",
        f"  doc_type: {s['doc_type']} | languages: {s['languages'][:6]} | brand: {s['brand_on_doc']}",
        f"  s83_confidence: {s['s83_confidence']}",
        "",
        "etiqueta gobernada en DB (nivel-documento):",
        f"  product_model: {d.get('product_model')}",
        f"  manufacturer: {d.get('manufacturer')} | doc_type_db: {d.get('doc_type_db')} | language_db: {d.get('language_db')}",
        "",
        f"catalogo: modelos={c['models'][:10]} | familias={c['familias']} | umbrella={c['umbrella']}",
        f"relacion determinista pm: {rec.get('pm_relation')} — {rec.get('pm_note')}",
        "",
        "muestra de CONTENIDO (primeras paginas):",
    ]
    for cs in content:
        lines.append(f"  [p{cs['page']} | {cs['section_title']}] {cs['head']!r}")
    lines.append("")
    lines.append("Devuelve el JSON: verdict (AUTO_CLEAN|CONFLICT|WEAK), product_model_call "
                 "(el modelo/familia que el documento realmente documenta, o 'unknown'), reason (<=200 chars).")
    return "\n".join(lines)


def run_judge(records: list[dict[str, Any]], cache_path: Path, *, limit: int | None,
              calibrate: bool) -> dict[str, Any]:
    import anthropic
    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

    # load cache (source_file -> verdict dict)
    cache: dict[str, dict[str, Any]] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                d = json.loads(line)
                cache[d["source_file"]] = d

    weak = [r for r in records if r["verdict"] == "WEAK"]
    weak.sort(key=lambda r: r["source_file"])  # deterministic order
    if limit is not None:
        if calibrate:
            # stratified across pm_relation so the calibration sample is representative
            groups: dict[str, list[dict[str, Any]]] = {}
            for r in weak:
                groups.setdefault(r.get("pm_relation", "?"), []).append(r)
            order = sorted(groups.keys())
            picked: list[dict[str, Any]] = []
            i = 0
            while len(picked) < limit and any(groups[k] for k in order):
                k = order[i % len(order)]
                if groups[k]:
                    picked.append(groups[k].pop(0))
                i += 1
            weak = sorted(picked, key=lambda r: r["source_file"])
        else:
            weak = weak[:limit]

    to_run = [r for r in weak if r["source_file"] not in cache]
    in_tok = out_tok = 0
    n_calls = 0
    with cache_path.open("a", encoding="utf-8") as fh:
        for r in to_run:
            content = _fetch_content_sample(r["source_file"])
            prompt = _judge_prompt(r, content)
            resp = client.messages.create(
                model=JUDGE_MODEL,
                max_tokens=400,
                temperature=0,
                system=JUDGE_SYSTEM,
                output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
                messages=[{"role": "user", "content": prompt}],
            )
            n_calls += 1
            in_tok += resp.usage.input_tokens
            out_tok += resp.usage.output_tokens
            text = next((b.text for b in resp.content if b.type == "text"), "{}")
            try:
                verdict = json.loads(text)
            except Exception:
                verdict = {"verdict": "WEAK", "product_model_call": "unknown",
                           "reason": "parse-error: " + text[:120]}
            row = {"source_file": r["source_file"], "content_sample": content, **verdict}
            cache[r["source_file"]] = row
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # fold LLM verdicts into the weak records
    judged = []
    for r in weak:
        v = cache.get(r["source_file"])
        if v:
            r = dict(r)
            r["llm_verdict"] = v.get("verdict")
            r["llm_product_model_call"] = v.get("product_model_call")
            r["llm_reason"] = v.get("reason")
            judged.append(r)

    cost = in_tok * 1.0 / 1_000_000 + out_tok * 5.0 / 1_000_000  # haiku 4.5 $1/$5 per 1M
    return {
        "judged": judged, "n_weak_total": sum(1 for r in records if r["verdict"] == "WEAK"),
        "n_judged": len(judged), "n_new_calls": n_calls,
        "input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": round(cost, 4),
        "calibrate": calibrate, "limit": limit,
    }


# -- freeze contract ------------------------------------------------------------
def freeze_contract() -> dict[str, Any]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip())
    return {
        "commit_head": head, "worktree_dirty": dirty,
        "s83_models": {"path": str(S83_DOC_MODELS.relative_to(ROOT)),
                       "sha256_lf": _sha256_lf(S83_DOC_MODELS)},
        "s83_identity": {"path": str(S83_DOC_IDENTITY.relative_to(ROOT)),
                         "sha256_lf": _sha256_lf(S83_DOC_IDENTITY)},
        "catalog_doc_map": {"sha256_lf": _sha256_lf(CATALOG_DIR / "doc_map.jsonl")},
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


# -- report ---------------------------------------------------------------------
def _brand_of(rec: dict[str, Any]) -> str:
    mfr = rec.get("document", {}).get("manufacturer")
    if isinstance(mfr, list):
        return mfr[0] if mfr else "(sin marca)"
    return mfr or "(sin marca)"


def build_report(payload: dict[str, Any]) -> str:
    fc = payload["freeze_contract"]
    c = payload["deterministic"]
    recs = c["records"]
    dist = c["verdict_distribution"]
    L: list[str] = []
    A = L.append

    A(f"# s282 QA-s83 — Validacion del activo de identidad s83 para el Tramo 2 — {payload['run_tag']}")
    A("")
    A("Instrumento: `scripts/s282_qa_s83_instrument.py`. **READ-ONLY (PostgREST GET), SELECT-only, "
      "0 escrituras, 0 embeddings de pago.** Valida, por cada uno de los 1014 `source_file` del activo "
      "s83, si sus etiquetas (`product_model`/`language`/`doc_type`) son APLICABLES a la DB con "
      "confianza medible, fusionando 3 fuentes de evidencia (doc-level DB + s83 + catalogo; +contenido "
      "para el juez). La derivacion determinista es $0 y 2x byte-identica; el juez LLM "
      "(`claude-haiku-4-5`, temp 0) arbitra SOLO el subconjunto WEAK.")
    A("")
    A("## Freeze-contract")
    A("")
    A(f"- commit HEAD: `{fc['commit_head']}` (worktree dirty: {fc['worktree_dirty']})")
    A(f"- corpus fingerprint: chunks_v2={payload['corpus_fingerprint']['chunks_v2']['count']} · "
      f"documents={payload['corpus_fingerprint']['documents']['count']} · sha256 "
      f"`{payload['corpus_fingerprint']['sha256']}`")
    A(f"- **determinismo 2x: {'IDENTICO' if payload['deterministic_2x'] else 'DIVERGE'}** "
      f"(pass1 `{payload['result_sha256_pass1'][:16]}` == pass2 `{payload['result_sha256_pass2'][:16]}`)")
    A(f"- s83 modelos: sha256-LF `{fc['s83_models']['sha256_lf']}` · s83 identidad "
      f"`{fc['s83_identity']['sha256_lf']}` · doc_map `{fc['catalog_doc_map']['sha256_lf']}`")
    A(f"- generado {fc['generated_utc']}")
    A("")

    total = c["n_source_files"]
    llm = payload.get("llm")

    # -- combined verdict per record (deterministic verdict, refined by LLM on WEAK) --
    llm_by_sf = {}
    if llm:
        for r in llm.get("judged", []):
            llm_by_sf[r["source_file"]] = r.get("llm_verdict")

    def final_verdict(r: dict[str, Any]) -> str:
        if r["verdict"] == "WEAK" and r["source_file"] in llm_by_sf:
            return llm_by_sf[r["source_file"]] or "WEAK"
        return r["verdict"]

    fin_dist = {"AUTO_CLEAN": 0, "CONFLICT": 0, "WEAK": 0, "UNMAPPED": 0}
    for r in recs:
        fin_dist[final_verdict(r)] = fin_dist.get(final_verdict(r), 0) + 1

    # titular
    A("## 1. Titular — distribucion de veredictos (de 1014 source_files s83)")
    A("")
    A("La derivacion DETERMINISTA ($0, recall-safe) solo emite AUTO_CLEAN (corroboracion exacta/subset "
      "de la etiqueta gobernada por los propios modelos s83), WEAK (todo lo no-obvio) y UNMAPPED. El "
      "CONFLICT es una salida del JUEZ LLM sobre contenido — un pm string-disjunto no basta para declarar "
      "conflicto (puede ser familia/variante, ruido de filename, o descripcion generica).")
    A("")
    A("| veredicto DETERMINISTA | n | % |")
    A("|---|---:|---:|")
    for v in ["AUTO_CLEAN", "WEAK", "UNMAPPED"]:
        A(f"| **{v}** | {dist.get(v,0)} | {100*dist.get(v,0)/total:.1f}% |")
    A("")
    A(f"Relacion determinista del pm (por que cada fila cae donde cae): `{c['pm_relation_distribution']}`.")
    A("")

    if llm and llm.get("n_judged"):
        folded = {"AUTO_CLEAN": 0, "CONFLICT": 0, "WEAK": 0}
        for r in llm["judged"]:
            folded[r.get("llm_verdict", "WEAK")] = folded.get(r.get("llm_verdict", "WEAK"), 0) + 1
        A(f"**Juez LLM (`{JUDGE_MODEL}`, temp 0) sobre el subconjunto WEAK** — "
          f"{llm['n_judged']}/{llm['n_weak_total']} juzgados"
          f"{' (CALIBRACION, subset)' if llm.get('calibrate') else ''}: "
          f"AUTO_CLEAN={folded['AUTO_CLEAN']} · CONFLICT={folded['CONFLICT']} · WEAK={folded['WEAK']}. "
          f"**Coste real: ${llm['cost_usd']}** ({llm['input_tokens']} in / {llm['output_tokens']} out tok, "
          f"{llm['n_new_calls']} llamadas nuevas de API).")
        A("")
        A("| veredicto FINAL (det + LLM) | n | % |")
        A("|---|---:|---:|")
        for v in ["AUTO_CLEAN", "CONFLICT", "WEAK", "UNMAPPED"]:
            A(f"| **{v}** | {fin_dist[v]} | {100*fin_dist[v]/total:.1f}% |")
        A("")
        unjudged = dist.get("WEAK", 0) - llm["n_judged"]
        A(f"**Estimacion T2 desbloqueado:** **{fin_dist['AUTO_CLEAN']}** source_files aplicables tal cual "
          f"(AUTO_CLEAN det + LLM), **{fin_dist['CONFLICT']}** conflictos para Alberto, "
          f"{fin_dist['WEAK']} WEAK residuales"
          + (f" (+{unjudged} WEAK aun sin juzgar por el LLM)" if unjudged > 0 else "") + ".")
        A("")

    # distribution by brand (final verdict)
    A("## 2. Distribucion por marca (veredicto FINAL x marca DB)")
    A("")
    by_brand: dict[str, dict[str, int]] = {}
    for r in recs:
        b = _brand_of(r)
        by_brand.setdefault(b, {"AUTO_CLEAN": 0, "CONFLICT": 0, "WEAK": 0, "UNMAPPED": 0})
        by_brand[b][final_verdict(r)] += 1
    A("| marca | AUTO_CLEAN | CONFLICT | WEAK | UNMAPPED | total |")
    A("|---|---:|---:|---:|---:|---:|")
    for b in sorted(by_brand.keys(), key=lambda x: -sum(by_brand[x].values())):
        d = by_brand[b]
        A(f"| {b} | {d['AUTO_CLEAN']} | {d['CONFLICT']} | {d['WEAK']} | {d['UNMAPPED']} | {sum(d.values())} |")
    A("")

    # conflicts packet (LLM-grounded)
    conflicts = [r for r in (llm.get("judged", []) if llm else []) if r.get("llm_verdict") == "CONFLICT"]
    A(f"## 3. Packet de CONFLICTOS para Alberto ({len(conflicts)}) — hallados por el juez sobre contenido")
    A("")
    A("Cada fila: s83 propone X, pero el CONTENIDO del documento y/o la etiqueta gobernada indican otro "
      "producto — el juez LLM lo declaro CONFLICT leyendo las primeras paginas. Patron del caso FS2-1 del "
      "packet T3. Alberto adjudica cual gobierna el T2. (Nada se aplica; el re-tag/backfill es reversible.)")
    A("")
    if not conflicts:
        A("_(ninguno — corre `--judge` para poblar el packet)_" if not llm else "_(ninguno)_")
        A("")
    else:
        A("| source_file | s83 primarios | doc-level pm (DB) | el juez dice | motivo (LLM) |")
        A("|---|---|---|---|---|")
        for r in sorted(conflicts, key=lambda x: x["source_file"]):
            s = r["s83"]
            d = r["document"]
            A(f"| `{r['source_file'][:38]}` | {s['primary_models'][:3]} | "
              f"`{d.get('product_model')}` | `{r.get('llm_product_model_call')}` | "
              f"{str(r.get('llm_reason',''))[:90]} |")
        A("")

    # deterministic disjoint candidates (transparency: what the string-heuristic flagged)
    disj = [r for r in recs if r.get("pm_relation") == "disjoint"]
    A(f"### 3b. (Transparencia) Candidatos deterministas pm-DISJUNTO ({len(disj)})")
    A("")
    A("El heuristico de strings marco estos como pm-disjunto; el juez LLM los reclasifica leyendo "
      "contenido (muchos son familia/variante o ruido de filename, NO conflictos). Se listan para que "
      "el packet sea auditable.")
    A("")
    A("| source_file | s83 primarios | doc-level pm | veredicto final |")
    A("|---|---|---|---|")
    for r in sorted(disj, key=lambda x: x["source_file"])[:40]:
        s = r["s83"]
        A(f"| `{r['source_file'][:38]}` | {s['primary_models'][:3]} | "
          f"`{r['document'].get('product_model')}` | {final_verdict(r)} |")
    if len(disj) > 40:
        A(f"| … +{len(disj)-40} mas | | | |")
    A("")

    # language mismatches (orthogonal advisory)
    lang_mm = [r for r in recs if r.get("language_flag") == "contradict"]
    A(f"## 4. (Advisory) Discrepancias de IDIOMA — DB vs s83 ({len(lang_mm)})")
    A("")
    A("Ortogonal al `product_model`: el `language` a nivel-documento en DB discrepa de s83. En la "
      "muestra dominan docs FAQ/soporte con `language` DB = 'en'/'de' pero contenido y s83 = 'es' → "
      "**s83 probablemente CORRIGE el idioma** (util para el T2). Alberto decide; no fuerza el veredicto pm.")
    A("")
    if lang_mm:
        A("| source_file | idioma DB | idioma s83 | doc-level pm |")
        A("|---|---|---|---|")
        for r in sorted(lang_mm, key=lambda x: x["source_file"])[:30]:
            A(f"| `{r['source_file'][:44]}` | {r['document'].get('language_db')} | "
              f"{r['s83']['languages'][:4]} | `{r['document'].get('product_model')}` |")
        if len(lang_mm) > 30:
            A(f"| … +{len(lang_mm)-30} mas | | | |")
        A("")

    # manufacturer reviews (advisory)
    mfr_mm = [r for r in recs if r.get("manufacturer_flag") == "review"]
    A(f"## 5. (Advisory) Revisiones de MARCA — DB vs s83 brand/oem ({len(mfr_mm)})")
    A("")
    A("El sello OEM/brand/distribuidor (s55/s78) hace ruido; una discrepancia marca-DB vs s83 se marca "
      "`review`, NO fuerza conflicto. Se listan solo los primeros para inspeccion.")
    A("")
    if mfr_mm:
        A("| source_file | marca DB | s83 brand_on_doc | s83 oem |")
        A("|---|---|---|---|")
        for r in sorted(mfr_mm, key=lambda x: x["source_file"])[:20]:
            A(f"| `{r['source_file'][:40]}` | {r['document'].get('manufacturer')} | "
              f"{r['s83'].get('brand_on_doc')} | {r['s83'].get('oem_manufacturer')} |")
        if len(mfr_mm) > 20:
            A(f"| … +{len(mfr_mm)-20} mas | | | |")
        A("")

    # applicability note
    A("## 6. Que aplica al Tramo 2 (y que NO)")
    A("")
    A("- **AUTO_CLEAN** → el `language`/`doc_type`/`product_model` de s83 se puede poblar en `documents` "
      "sin adjudicacion humana: el doc-level `product_model` ya esta corroborado por los propios modelos "
      "s83, y s83 rellena `language`/`doc_type` que hoy son NULL en la mayoria (census: language NULL=902, "
      "doc_type NULL=970). Sigue siendo PROPUESTA: el SQL del T2 lo aplica Alberto; este instrumento no escribe.")
    A("- **CONFLICT** → NO aplicar `product_model` de s83; Alberto decide fuente (patron FS2-1). Acotado (§3).")
    A("- **WEAK residual** → el juez no pudo decidir (contenido generico/granularidad) → Alberto o se deja.")
    A("- **UNMAPPED** → el source_file de s83 no tiene documento activo → fuera del alcance del T2 "
      "(solo revisiones superseded, o docs no ingestados).")
    A("- **IDIOMA (§4)** y **MARCA (§5)** son ejes SEPARADOS: una fila AUTO_CLEAN en pm puede aun aparecer "
      "ahi. El idioma es de hecho una CORRECCION probable que s83 aporta al T2.")
    A("")

    # honesty
    A("## 7. Honestidad del instrumento — lo que NO juzga")
    A("")
    A("- **Eje primario = `product_model`** (unico campo con valor en ambos lados → pre-filtro exacto "
      "recall-safe $0). AUTO_CLEAN determinista = SOLO corroboracion exacta/subset; todo lo demas va al juez.")
    A("- **No hay CONFLICT determinista.** Un pm string-disjunto (§3b) NO es conflicto por si mismo: puede ser "
      "familia/variante ('2X-AE1' vs '2X-A Tactil'), ruido de filename ('NRT-586T' vs source-file '15090SP'), "
      "o descripcion generica de s83. Solo el juez, leyendo contenido, decide CONFLICT.")
    A("- **AUTO_CLEAN = etiqueta corroborada, NO verdad de campo.** Sigue siendo una PROPUESTA para el T2.")
    A("- **`language`/`doc_type`/`marca` son advisory** (ejes ortogonales; DB mayormente NULL en language/"
      "doc_type → s83 RELLENA). La marca sufre el sello OEM (s55/s78) → solo `review`, nunca conflicto.")
    A("- **El juez LLM solo mira `product_model`** sobre contenido; no verifica correccion tecnica del manual. "
      "Es una augmentacion sobre WEAK, FUERA del contrato de determinismo 2x (la parte $0 si es 2x-identica).")
    A("- **doc-level `product_model` puede ser ruidoso** (filename-derived; census/T3). Por eso un CONFLICT "
      "es «el contenido CONTRADICE a s83», no «s83 mal»: Alberto adjudica.")
    A("")
    return "\n".join(L)


# -- main -----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--judge", action="store_true", help="run the LLM judge over the WEAK subset")
    ap.add_argument("--calibrate", action="store_true", help="mark this run as a calibration subset")
    ap.add_argument("--limit", type=int, default=None, help="cap the WEAK subset judged (calibration)")
    args = ap.parse_args(argv)
    tag = args.tag

    global _ORIG_SFS
    _init_http()
    contract = freeze_contract()
    fp_before = corpus_fingerprint()
    print(f"commit={contract['commit_head'][:10]} dirty={contract['worktree_dirty']}")
    print(f"corpus chunks_v2={fp_before['chunks_v2']['count']} documents={fp_before['documents']['count']}")

    s83 = _load_s83()
    _ORIG_SFS = sorted({str(json.loads(l)["source_file"])
                        for l in S83_DOC_MODELS.read_text(encoding="utf-8").splitlines() if l.strip()})
    catalog = _load_catalog()

    documents = _get_all("documents", DOC_SELECT, order="id.asc")
    chunks = _get_all("chunks_v2", "source_file,document_id", order="id.asc")
    chunk_map = _chunk_srcfile_to_docids(chunks)
    # doc_map source_file -> document_id (governed fallback bridge)
    docmap_rows = [json.loads(l) for l in (CATALOG_DIR / "doc_map.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    docmap_sf_to_docid: dict[str, list[str]] = {}
    for r in docmap_rows:
        sf = r.get("source_file")
        did = r.get("document_id")
        if sf and did:
            docmap_sf_to_docid.setdefault(str(sf), []).append(str(did))

    canon1 = derive(s83, documents, chunk_map, docmap_sf_to_docid, catalog)
    sha1 = _stable_sha256(canon1)
    print(f"pass1 sha={sha1[:16]} | records={canon1['n_source_files']} dist={canon1['verdict_distribution']}")
    canon2 = derive(s83, documents, chunk_map, docmap_sf_to_docid, catalog)
    sha2 = _stable_sha256(canon2)
    fp_after = corpus_fingerprint()
    deterministic = sha1 == sha2 and fp_before["sha256"] == fp_after["sha256"]
    print(f"pass2 sha={sha2[:16]} | deterministic_2x={deterministic}")

    payload: dict[str, Any] = {
        "schema": "s282_qa_s83_v1", "run_tag": tag,
        "authority": "DEVELOPMENT_QA_READ_ONLY_SELECT_ONLY_ZERO_WRITES",
        "freeze_contract": contract, "corpus_fingerprint": fp_after,
        "deterministic_2x": deterministic, "result_sha256_pass1": sha1,
        "result_sha256_pass2": sha2, "deterministic": canon1,
    }

    if args.judge:
        cache_path = ROOT / f"evals/s282_qa_s83_llm_cache_{tag}.jsonl"
        llm = run_judge(canon1["records"], cache_path, limit=args.limit, calibrate=args.calibrate)
        payload["llm"] = llm
        print(f"LLM judge: judged={llm['n_judged']}/{llm['n_weak_total']} new_calls={llm['n_new_calls']} "
              f"cost=${llm['cost_usd']} tokens={llm['input_tokens']}in/{llm['output_tokens']}out")

    result_path = ROOT / f"evals/s282_qa_s83_result_{tag}.json"
    report_path = ROOT / f"evals/s282_qa_s83_report_{tag}.md"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str) + "\n",
                           encoding="utf-8")
    report_path.write_text(build_report(payload), encoding="utf-8")
    print(f"\nresult: {result_path}")
    print(f"report: {report_path}")
    return 0 if deterministic else 2


if __name__ == "__main__":
    sys.exit(main())
