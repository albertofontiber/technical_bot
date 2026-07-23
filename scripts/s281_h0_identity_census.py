#!/usr/bin/env python3
"""s281 H0 identity census — corpus-wide identity/lineage gap census + backfill plan.

Lane H0-census of s281 (brief: ``evals/s281_f1_h0_lane_briefs_pendientes.md`` §Lane
H0-census).  It measures, READ-ONLY and $0, the identity/lineage state of the LIVE
corpus so a backfill campaign can be prioritised.  It ADJUDICATES the current state;
it never writes.  Every proposed change is emitted as a SQL PROPOSAL in the report,
never applied.

Context (DEC-152 / s279 H0 finding): the s279 selection-reach census found that
12 of 15 P1 QIDs die UPSTREAM of the selection logic at a proximal RPC gate
``unverified_document_lineage``.  Two underlying corpus states sit under that
uniform rejection: (a) ``source_pdf_sha256='backfill:*'`` placeholder + language/
doc_type NULL; (b) complete blob but lineage ``authority_status != 'verified'``.
This census extends that audit from the 15-QID probe to the WHOLE corpus (1171
documents / 25090 chunks) and adds the chunk-level ``product_model`` findability
gap (the live MIE-MI-600 / Morley ZXSe case: 88 chunks ``product_model='unknown'``,
the bot admits it lacks a manual that exists).

INHERITANCE (declared, per brief):
  * from ``scripts/s279_selection_census.py``: the GET-only read-only HTTP stack
    (``_init_http``/``_get``), the corpus fingerprint (A1) + freeze-contract idiom,
    the stable-sha helper, the ``canonical_blob_stem`` source normalisation, and
    the read-only ``_document_identity_audit`` semantics (backfill-placeholder /
    64-hex / lineage authority_status).
  * from ``scripts/s278_identity_census.py``: the determinism contract (run the
    derivation twice, assert byte-identical), the "fuera de census / honesty §"
    reporting discipline, and the class-rank aggregation style.

HARD RULES honoured:
  * DB is SELECT-only.  PostgREST GET is the only verb used.  ZERO writes, ZERO
    model calls, ZERO paid embeddings.
  * Determinism: the whole derivation runs 2x against the live corpus and the two
    canonical result blobs are asserted byte-identical (``deterministic_2x``).
  * Outputs restricted to this lane's territory: ``scripts/s281_h0_*`` /
    ``evals/s281_h0_*``.

Usage:  python scripts/s281_h0_identity_census.py [--tag v1]
Outputs: evals/s281_h0_identity_census_result_<tag>.json
         evals/s281_h0_identity_census_report_<tag>.md   (tag v1 -> ..._v1.md)
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
import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # re-assert after load_dotenv

import src.config as cfg  # noqa: E402
import src.rag.document_local_coverage as dlc  # noqa: E402  (canonical_blob_stem)

# ── constants ────────────────────────────────────────────────────────────────
GOLD_BASELINE = ROOT / "evals/bot_vs_gold_39_baseline_coverage_c1_v4_s281.yaml"
DOC_MAP = ROOT / "data/catalog/doc_map.jsonl"
S83_DOC_MODELS = ROOT / "evals/s83_document_models_final.jsonl"

# The live ZXSe case pinned by the brief (spot-check target).
ZXSE_SOURCE_FILE = "MIE-MI-600"

_H: dict[str, str] = {}
_BASE = ""


# ── read-only HTTP helpers (inherited from s279) ──────────────────────────────
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
    resp = httpx.get(f"{_BASE}/rest/v1/{table}", headers=headers, params=params, timeout=90)
    resp.raise_for_status()
    return resp


def _get_all(table: str, select: str, *, order: str, page: int = 1000) -> list[dict[str, Any]]:
    """Deterministic full-table read via keyset-free offset pagination.

    Ordered by a stable key so two independent reads return byte-identical rows;
    the caller compares the two reads for the determinism contract.
    """
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


# ── corpus fingerprint (A1, inherited from s279) ──────────────────────────────
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


# ── identity classification ───────────────────────────────────────────────────
# The RPC document-local authority gate (src/rag/document_local_coverage.py:887-930)
# requires, for a document to be a servable authority: a present revision_lineage_id
# whose lineage.authority_status=='verified' (proximal gate ``unverified_document_
# lineage``), language present (=='es' for the lane), and every identity field
# non-empty (manufacturer/product_model/doc_type).  The chunk anchor carries the
# real extraction_sha256, so a backfill-placeholder ``source_pdf_sha256`` does not
# by itself reach the RPC, but it is the marker of the un-verified-lineage cohort
# (s279 H0) and it blocks ANY lineage verification that keys on the source blob.
_IDENTITY_FIELDS = ("manufacturer", "product_model", "doc_type", "language")


def _sha_state(sha: str) -> str:
    s = (sha or "").strip()
    if not s:
        return "empty"
    if s.lower().startswith("backfill:"):
        return "backfill_placeholder"
    if re.fullmatch(r"[0-9a-f]{64}", s.lower()):
        return "valid_64hex"
    return "other_nonhex"


def classify_document(doc: dict[str, Any], lineage_status: dict[str, str]) -> dict[str, Any]:
    sha = str(doc.get("source_pdf_sha256") or "")
    sha_state = _sha_state(sha)
    lineage_id = doc.get("revision_lineage_id")
    lineage_present = bool(lineage_id)
    auth = lineage_status.get(str(lineage_id)) if lineage_present else None
    lang = (doc.get("language") or "").strip()
    doc_type = (doc.get("doc_type") or "").strip()
    manufacturer = (doc.get("manufacturer") or "").strip()
    product_model = (doc.get("product_model") or "").strip()

    flags: list[str] = []
    if sha_state == "backfill_placeholder":
        flags.append("sha_backfill_placeholder")
    elif sha_state != "valid_64hex":
        flags.append(f"sha_{sha_state}")
    if not lineage_present:
        flags.append("lineage_id_null")
    elif auth != "verified":
        flags.append(f"lineage_{auth or 'missing_row'}")
    if not lang:
        flags.append("language_null")
    if not doc_type:
        flags.append("doc_type_null")
    if not manufacturer:
        flags.append("manufacturer_null")
    if not product_model:
        flags.append("product_model_null")

    # Servable via the document-local authority lane (proximal-gate model).
    lineage_verified = lineage_present and auth == "verified"
    identity_complete = bool(manufacturer and product_model and doc_type and lang)
    servable_lane = lineage_verified and identity_complete and lang.lower() == "es"

    blocking = []
    if not lineage_verified:
        blocking.append("unverified_document_lineage")
    if lang.lower() != "es":
        blocking.append("language_not_es" if lang else "language_null")
    if not identity_complete:
        blocking.append("incomplete_identity")

    return {
        "sha_state": sha_state,
        "lineage_present": lineage_present,
        "lineage_authority_status": auth,
        "lineage_verified": lineage_verified,
        "identity_complete": identity_complete,
        "servable_document_local_lane": servable_lane,
        "flags": flags,
        "blocking_reasons": sorted(set(blocking)),
    }


# ── the census derivation (pure over fetched rows -> deterministic) ────────────
def derive(documents: list[dict[str, Any]], lineages: list[dict[str, Any]],
           chunk_rows: list[dict[str, Any]]) -> dict[str, Any]:
    lineage_status = {str(l["id"]): str(l.get("authority_status") or "") for l in lineages}

    # -- per-document classification --
    docs_by_id: dict[str, dict[str, Any]] = {}
    for d in documents:
        c = classify_document(d, lineage_status)
        docs_by_id[str(d["id"])] = {"doc": d, "cls": c}

    active = [v for v in docs_by_id.values() if str(v["doc"].get("status")) == "active"]

    # -- gap-class aggregates over ACTIVE docs (serving-relevant) --
    def has(v: dict[str, Any], flag: str) -> bool:
        return flag in v["cls"]["flags"]

    classes = {
        "A_sha_backfill_placeholder": [v for v in active if has(v, "sha_backfill_placeholder")],
        "B_lineage_id_null": [v for v in active if has(v, "lineage_id_null")],
        "B2_lineage_present_unverified": [
            v for v in active if v["cls"]["lineage_present"] and not v["cls"]["lineage_verified"]
        ],
        "C_language_null": [v for v in active if has(v, "language_null")],
        "C_doc_type_null": [v for v in active if has(v, "doc_type_null")],
        "C_product_model_null_doclevel": [v for v in active if has(v, "product_model_null")],
        "C_manufacturer_null": [v for v in active if has(v, "manufacturer_null")],
        # Tramo-1 candidates: identity-complete + Spanish, only missing a verified
        # lineage (the low-risk, high-leverage cohort — same shape as the 6 done).
        "T1_identity_complete_es_unverified": [
            v for v in active
            if v["cls"]["identity_complete"]
            and (v["doc"].get("language") or "").strip().lower() == "es"
            and not v["cls"]["lineage_verified"]
        ],
        "SERVABLE_document_local_lane": [v for v in active if v["cls"]["servable_document_local_lane"]],
    }
    by_class = {k: len(v) for k, v in classes.items()}

    # -- class A/B by manufacturer (marca) --
    def by_marca(subset: list[dict[str, Any]]) -> dict[str, int]:
        out: dict[str, int] = {}
        for v in subset:
            m = (v["doc"].get("manufacturer") or "∅(null)").strip() or "∅(empty)"
            out[m] = out.get(m, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    marca_A = by_marca(classes["A_sha_backfill_placeholder"])
    marca_B = by_marca(classes["B_lineage_id_null"])

    # -- chunk-level product_model findability census (class D) --
    # Group chunks by (manufacturer, source_file); count unknown/NULL product_model.
    src_agg: dict[str, dict[str, Any]] = {}
    UNK = {"unknown", ""}
    for r in chunk_rows:
        sf = str(r.get("source_file") or "")
        pm = (r.get("product_model") or "")
        pm_norm = pm.strip().lower()
        mfr = (r.get("manufacturer") or "").strip()
        dup = r.get("duplicate_of")
        key = sf
        a = src_agg.setdefault(key, {
            "source_file": sf, "manufacturers": {}, "total": 0, "unknown": 0,
            "unknown_nondup": 0, "nondup": 0, "document_ids": set(),
        })
        a["total"] += 1
        a["manufacturers"][mfr] = a["manufacturers"].get(mfr, 0) + 1
        if r.get("document_id"):
            a["document_ids"].add(str(r["document_id"]))
        is_unknown = (pm_norm in UNK) or (pm is None)
        if dup in (None, "", "null"):
            a["nondup"] += 1
            if is_unknown:
                a["unknown_nondup"] += 1
        if is_unknown:
            a["unknown"] += 1

    # source_files that are ENTIRELY unknown/NULL (worst findability) vs partial.
    fully_unknown = []
    partial_unknown = []
    for sf, a in src_agg.items():
        if a["unknown"] == 0:
            continue
        row = {
            "source_file": sf,
            "total_chunks": a["total"],
            "unknown_chunks": a["unknown"],
            "unknown_nondup": a["unknown_nondup"],
            "nondup_chunks": a["nondup"],
            "manufacturers": dict(sorted(a["manufacturers"].items(), key=lambda kv: -kv[1])),
            "n_documents": len(a["document_ids"]),
        }
        if a["unknown"] == a["total"]:
            fully_unknown.append(row)
        else:
            partial_unknown.append(row)
    fully_unknown.sort(key=lambda r: (-r["unknown_chunks"], r["source_file"]))
    partial_unknown.sort(key=lambda r: (-r["unknown_chunks"], r["source_file"]))

    total_unknown_chunks = sum(a["unknown"] for a in src_agg.values())
    total_chunks = sum(a["total"] for a in src_agg.values())

    # source_file -> document_ids map (for the QID cross)
    src_to_docids: dict[str, set[str]] = {}
    for sf, a in src_agg.items():
        src_to_docids[sf] = set(a["document_ids"])

    # document_id -> chunk count (for per-class unlock volume)
    doc_chunk_count: dict[str, int] = {}
    for r in chunk_rows:
        did = str(r.get("document_id") or "")
        if did:
            doc_chunk_count[did] = doc_chunk_count.get(did, 0) + 1

    # -- ZXSe / MIE-MI-600 pinned spot-check --
    zx = src_agg.get(ZXSE_SOURCE_FILE)
    zxse_check = None
    if zx is not None:
        zxse_check = {
            "source_file": ZXSE_SOURCE_FILE,
            "total_chunks": zx["total"],
            "unknown_chunks": zx["unknown"],
            "unknown_nondup": zx["unknown_nondup"],
            "manufacturers": dict(sorted(zx["manufacturers"].items(), key=lambda kv: -kv[1])),
            "document_ids": sorted(zx["document_ids"]),
        }

    # -- catalog cross (docs sin mapeo a producto) --
    catalog = _load_doc_map()
    mapped_docids = catalog["by_document_id"]
    mapped_srcfiles = catalog["by_source_file"]
    unmapped_active = []
    for v in active:
        did = str(v["doc"]["id"])
        stem = dlc.canonical_blob_stem(str(v["doc"].get("source_pdf_filename") or ""))
        if did in mapped_docids or (stem and stem in mapped_srcfiles):
            continue
        unmapped_active.append({
            "document_id": did,
            "source_pdf_filename": v["doc"].get("source_pdf_filename"),
            "manufacturer": v["doc"].get("manufacturer"),
            "product_model": v["doc"].get("product_model"),
        })
    unmapped_active.sort(key=lambda r: (str(r.get("manufacturer") or ""), str(r.get("source_pdf_filename") or "")))

    # -- baseline QID cross (bot_sources -> documents -> gap state) = impacto directo --
    qid_cross = _cross_baseline(docs_by_id, src_to_docids)

    # -- volume unlockable per class (documents + chunks) --
    def volume(subset: list[dict[str, Any]]) -> dict[str, int]:
        dids = [str(v["doc"]["id"]) for v in subset]
        return {"documents": len(dids),
                "chunks": sum(doc_chunk_count.get(d, 0) for d in dids)}

    volume_by_class = {k: volume(v) for k, v in classes.items()}

    canonical = {
        "counts": {
            "documents_total": len(documents),
            "documents_active": len(active),
            "lineages_total": len(lineages),
            "lineages_verified": sum(1 for s in lineage_status.values() if s == "verified"),
            "chunks_total": total_chunks,
            "chunks_unknown_pm": total_unknown_chunks,
        },
        "by_class_active": by_class,
        "lineage_status_distribution": dict(sorted(
            {s or "∅": sum(1 for x in lineage_status.values() if x == s) for s in set(lineage_status.values())}.items())),
        "class_A_by_marca": marca_A,
        "class_B_by_marca": marca_B,
        "chunk_pm_unknown": {
            "fully_unknown_source_files": fully_unknown,
            "partial_unknown_source_files": partial_unknown,
            "n_fully_unknown_source_files": len(fully_unknown),
            "n_partial_unknown_source_files": len(partial_unknown),
        },
        "zxse_pin": zxse_check,
        "catalog_unmapped_active": {
            "n": len(unmapped_active),
            "rows": unmapped_active,
        },
        "baseline_qid_cross": qid_cross,
        "volume_by_class": volume_by_class,
    }
    return canonical


def _load_doc_map() -> dict[str, Any]:
    by_did: set[str] = set()
    by_sf: set[str] = set()
    if DOC_MAP.exists():
        for line in DOC_MAP.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("entries"):
                if d.get("document_id"):
                    by_did.add(str(d["document_id"]))
                if d.get("source_file"):
                    by_sf.add(dlc.canonical_blob_stem(str(d["source_file"])))
    return {"by_document_id": by_did, "by_source_file": by_sf}


def _cross_baseline(docs_by_id: dict[str, dict[str, Any]],
                    src_to_docids: dict[str, set[str]]) -> dict[str, Any]:
    if not GOLD_BASELINE.exists():
        return {"available": False}
    rows = yaml.safe_load(GOLD_BASELINE.read_text(encoding="utf-8"))
    out_rows = []
    # normalise chunk source_file keys for tolerant matching
    norm_src = {dlc.canonical_blob_stem(sf): dids for sf, dids in src_to_docids.items()}
    for r in rows:
        qid = r.get("qid")
        bot_sources = r.get("bot_sources") or []
        cited_docs: set[str] = set()
        unresolved: list[str] = []
        for bs in bot_sources:
            stem = dlc.canonical_blob_stem(str(bs))
            dids = src_to_docids.get(str(bs)) or norm_src.get(stem)
            if not dids:
                # fuzzy: any source_file whose stem contains / is contained
                for sf, d in src_to_docids.items():
                    st = dlc.canonical_blob_stem(sf)
                    if st and (st == stem or st in stem or stem in st):
                        dids = d
                        break
            if dids:
                cited_docs |= dids
            else:
                unresolved.append(str(bs))
        # classify cited docs
        blocked = []
        servable = []
        for did in sorted(cited_docs):
            v = docs_by_id.get(did)
            if v is None:
                continue
            if v["cls"]["servable_document_local_lane"]:
                servable.append(did)
            else:
                blocked.append((did, v["cls"]["blocking_reasons"]))
        out_rows.append({
            "qid": qid,
            "veredicto": r.get("veredicto"),
            "conducta_esperada": r.get("conducta_esperada"),
            "coverage_status": r.get("coverage_status"),
            "n_bot_sources": len(bot_sources),
            "n_cited_docs_resolved": len(cited_docs),
            "n_cited_docs_blocked": len(blocked),
            "n_cited_docs_servable": len(servable),
            "all_cited_blocked": bool(cited_docs) and not servable,
            "unresolved_bot_sources": unresolved,
        })
    n_all_blocked = sum(1 for r in out_rows if r["all_cited_blocked"])
    n_any_servable = sum(1 for r in out_rows if r["n_cited_docs_servable"] > 0)
    return {
        "available": True,
        "n_qids": len(out_rows),
        "n_qids_all_cited_docs_blocked": n_all_blocked,
        "n_qids_with_a_servable_cited_doc": n_any_servable,
        "rows": out_rows,
    }


# ── main ───────────────────────────────────────────────────────────────────────
def freeze_contract() -> dict[str, Any]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip())
    return {
        "commit_head": head,
        "worktree_dirty": dirty,
        "gold_baseline": {"path": str(GOLD_BASELINE.relative_to(ROOT)),
                          "sha256_lf": _sha256_lf(GOLD_BASELINE) if GOLD_BASELINE.exists() else None},
        "doc_map": {"path": str(DOC_MAP.relative_to(ROOT)),
                    "sha256_lf": _sha256_lf(DOC_MAP) if DOC_MAP.exists() else None},
        "s83_asset": {"path": str(S83_DOC_MODELS.relative_to(ROOT)),
                      "present": S83_DOC_MODELS.exists(),
                      "sha256_lf": _sha256_lf(S83_DOC_MODELS) if S83_DOC_MODELS.exists() else None},
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


DOC_SELECT = ("id,status,manufacturer,product_model,doc_type,language,"
              "source_pdf_filename,source_pdf_sha256,revision,revision_lineage_id,"
              "document_family,ingested_at")
CHUNK_SELECT = "document_id,source_file,manufacturer,product_model,duplicate_of"


def _fetch_all() -> tuple[list, list, list]:
    documents = _get_all("documents", DOC_SELECT, order="id.asc")
    lineages = _get_all("document_revision_lineages", "id,authority_status,authority_contract,notes",
                        order="id.asc")
    chunks = _get_all("chunks_v2", CHUNK_SELECT, order="id.asc")
    return documents, lineages, chunks


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
    print(f"corpus fingerprint chunks_v2={fp_before['chunks_v2']['count']} documents={fp_before['documents']['count']}")

    # -- pass 1 --
    docs1, lin1, chk1 = _fetch_all()
    canon1 = derive(docs1, lin1, chk1)
    sha1 = _stable_sha256(canon1)
    print(f"pass1 result sha={sha1[:16]} | docs={len(docs1)} chunks={len(chk1)} lineages={len(lin1)}")

    # -- pass 2 (determinism contract) --
    docs2, lin2, chk2 = _fetch_all()
    canon2 = derive(docs2, lin2, chk2)
    sha2 = _stable_sha256(canon2)
    fp_after = corpus_fingerprint()
    deterministic = sha1 == sha2 and fp_before["sha256"] == fp_after["sha256"]
    print(f"pass2 result sha={sha2[:16]} | deterministic_2x={deterministic}")

    payload = {
        "schema": "s281_h0_identity_census_v1",
        "run_tag": tag,
        "authority": "DEVELOPMENT_CENSUS_READ_ONLY_ZERO_MODEL_CALLS_SELECT_ONLY",
        "freeze_contract": contract,
        "corpus_fingerprint": fp_after,
        "deterministic_2x": deterministic,
        "result_sha256_pass1": sha1,
        "result_sha256_pass2": sha2,
        "census": canon1,
        "spot_checks": _spot_checks(docs1, lin1, canon1),
    }
    result_path = ROOT / f"evals/s281_h0_identity_census_result_{tag}.json"
    report_path = ROOT / f"evals/s281_h0_identity_census_report_{tag}.md"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str) + "\n",
                           encoding="utf-8")
    report = build_report(payload)
    report_path.write_text(report, encoding="utf-8")
    print(f"\nresult: {result_path}")
    print(f"report: {report_path}")
    print("\n" + report[report.find("## 1."):report.find("## 1.") + 2200])
    return 0 if deterministic else 2


def _spot_checks(documents: list[dict[str, Any]], lineages: list[dict[str, Any]],
                 canon: dict[str, Any]) -> dict[str, Any]:
    """3 manually-citable rows per class, with the exact query that reproduces them."""
    lineage_status = {str(l["id"]): str(l.get("authority_status") or "") for l in lineages}
    active = [d for d in documents if str(d.get("status")) == "active"]

    def sample(pred, n=3):
        out = []
        for d in sorted(active, key=lambda x: str(x["id"])):
            if pred(d):
                out.append({
                    "document_id": d["id"],
                    "source_pdf_filename": d.get("source_pdf_filename"),
                    "manufacturer": d.get("manufacturer"),
                    "product_model": d.get("product_model"),
                    "source_pdf_sha256_state": _sha_state(str(d.get("source_pdf_sha256") or "")),
                    "language": d.get("language"),
                    "doc_type": d.get("doc_type"),
                    "revision_lineage_id": d.get("revision_lineage_id"),
                })
            if len(out) >= n:
                break
        return out

    return {
        "class_A_sha_backfill_placeholder": {
            "query": ("GET /documents?status=eq.active&source_pdf_sha256=like.backfill:*"
                      f"&select={DOC_SELECT}"),
            "rows": sample(lambda d: _sha_state(str(d.get("source_pdf_sha256") or "")) == "backfill_placeholder"),
        },
        "class_B_lineage_id_null": {
            "query": ("GET /documents?status=eq.active&revision_lineage_id=is.null"
                      f"&select={DOC_SELECT}"),
            "rows": sample(lambda d: not d.get("revision_lineage_id")),
        },
        "class_C_language_null": {
            "query": ("GET /documents?status=eq.active&language=is.null"
                      f"&select={DOC_SELECT}"),
            "rows": sample(lambda d: not (d.get("language") or "").strip()),
        },
        "class_D_zxse_pin": {
            "query": (f"GET /chunks_v2?source_file=eq.{ZXSE_SOURCE_FILE}"
                      "&product_model=eq.unknown&select=id,product_model,manufacturer (count)"),
            "result": canon.get("zxse_pin"),
        },
        "lineages_present": {
            "query": "GET /document_revision_lineages?select=id,authority_status,notes",
            "rows": [{"id": l["id"], "authority_status": l.get("authority_status"),
                      "notes": (l.get("notes") or "")[:80]} for l in lineages],
        },
    }


# ── report ─────────────────────────────────────────────────────────────────────
def build_report(payload: dict[str, Any]) -> str:
    fc = payload["freeze_contract"]
    c = payload["census"]
    tag = payload.get("run_tag", "v1")
    cnt = c["counts"]
    L: list[str] = []
    A = L.append

    A(f"# s281 H0 — Census de identidad/lineage del corpus + plan de backfill — {tag}")
    A("")
    A("Instrumento: `scripts/s281_h0_identity_census.py`. **READ-ONLY (PostgREST GET), SELECT-only, "
      "0 llamadas a modelos, 0 escrituras.** El census ADJUDICA el estado vivo; toda propuesta de "
      "cambio se emite como PROPUESTA SQL (jamás aplicada). Hereda de `s279_selection_census.py` "
      "(stack GET-only + fingerprint A1 + auditoría de identidad) y de `s278_identity_census.py` "
      "(contrato de determinismo 2× + disciplina de honestidad).")
    A("")
    A("## Freeze-contract")
    A("")
    A(f"- commit HEAD: `{fc['commit_head']}` (worktree dirty: {fc['worktree_dirty']})")
    A(f"- corpus fingerprint: chunks_v2={payload['corpus_fingerprint']['chunks_v2']['count']} · "
      f"documents={payload['corpus_fingerprint']['documents']['count']} · "
      f"sha256 `{payload['corpus_fingerprint']['sha256']}`")
    A(f"- **determinismo 2×: {'IDÉNTICO ✅' if payload['deterministic_2x'] else 'DIVERGE ❌'}** "
      f"(pass1 sha `{payload['result_sha256_pass1'][:16]}` == pass2 sha `{payload['result_sha256_pass2'][:16]}`)")
    A(f"- gold baseline: `{fc['gold_baseline']['path']}` sha256-LF `{fc['gold_baseline']['sha256_lf']}`")
    A(f"- doc_map: `{fc['doc_map']['path']}` sha256-LF `{fc['doc_map']['sha256_lf']}`")
    A(f"- activo s83 (mapa doc→modelos): present={fc['s83_asset']['present']} · "
      f"`{fc['s83_asset']['path']}`" + (f" sha256-LF `{fc['s83_asset']['sha256_lf']}`" if fc['s83_asset']['present'] else ""))
    A(f"- generado {fc['generated_utc']}")
    A("")

    A("## 1. Titular")
    A("")
    lv = cnt["lineages_verified"]
    servable = c["by_class_active"]["SERVABLE_document_local_lane"]
    A(f"De **{cnt['documents_active']} documentos activos** ({cnt['documents_total']} totales), solo "
      f"existen **{cnt['lineages_total']} lineages** en `document_revision_lineages` "
      f"(**{lv} verified**). Bajo el modelo del gate proximal del RPC "
      f"(`unverified_document_lineage` — src/rag/document_local_coverage.py:887-930), hoy son "
      f"servibles por la vía document-local **{servable} documentos activos**. El resto muere "
      f"aguas arriba de toda la lógica de selección (confirma y generaliza el H0 de s279/DEC-152: "
      f"12/15 QIDs P1 bloqueados). El cuello dominante NO es la selección: es un **backfill de "
      f"identidad + verificación de lineage**.")
    A("")
    A(f"Reconciliación con s279: los {servable} docs servibles corpus-wide = los {cnt['lineages_total']} "
      f"lineages verified (HP011 RP1r + CAD-250 MC-380/MS-416 + HOP-138-8/9ES + 4188-1132-ES). De "
      f"esos, solo 3 caen bajo los 15 QIDs-probe de s279 (cat017/cat019/hp011) — de ahí el «3 de 15» "
      f"de aquel census vs los {servable} de éste (corpus completo). El resto de lineages cubre "
      f"revisiones/documentos fuera del set P1.")
    A("")

    A("## 2. Conteos por clase de gap (documentos ACTIVOS)")
    A("")
    A("| Clase de gap | Documentos activos | % de activos |")
    A("|---|---:|---:|")
    order = [
        ("A_sha_backfill_placeholder", "A — `source_pdf_sha256='backfill:*'` (placeholder, no 64-hex)"),
        ("B_lineage_id_null", "B — `revision_lineage_id IS NULL` (sin lineage → unverified)"),
        ("B2_lineage_present_unverified", "B2 — lineage presente pero `authority_status != 'verified'`"),
        ("C_language_null", "C — `language IS NULL`"),
        ("C_doc_type_null", "C — `doc_type IS NULL`"),
        ("C_product_model_null_doclevel", "C — `product_model IS NULL` (nivel documento)"),
        ("C_manufacturer_null", "C — `manufacturer IS NULL`"),
        ("T1_identity_complete_es_unverified", "T1 — identity-completo (es) SOLO falta lineage verified"),
        ("SERVABLE_document_local_lane", "✅ SERVIBLE hoy (lineage verified + identidad completa + es)"),
    ]
    act = cnt["documents_active"] or 1
    for k, label in order:
        n = c["by_class_active"].get(k, 0)
        A(f"| {label} | {n} | {100*n/act:.1f}% |")
    A("")
    A(f"Distribución de `authority_status` en los {cnt['lineages_total']} lineages: "
      f"`{c['lineage_status_distribution']}`. Chunks con `product_model` unknown/NULL: "
      f"**{cnt['chunks_unknown_pm']}** de {cnt['chunks_total']} "
      f"({100*cnt['chunks_unknown_pm']/(cnt['chunks_total'] or 1):.1f}%).")
    A("")

    A("### 2.1 Clase A (backfill sha) por marca — top 15")
    A("")
    A("| Marca | Docs activos con sha backfill |")
    A("|---|---:|")
    for m, n in list(c["class_A_by_marca"].items())[:15]:
        A(f"| {m} | {n} |")
    A("")
    A("### 2.2 Clase B (lineage NULL) por marca — top 15")
    A("")
    A("| Marca | Docs activos sin lineage |")
    A("|---|---:|")
    for m, n in list(c["class_B_by_marca"].items())[:15]:
        A(f"| {m} | {n} |")
    A("")

    A("## 3. Clase D — findability por `product_model='unknown'/NULL` (nivel chunk)")
    A("")
    cu = c["chunk_pm_unknown"]
    A(f"- source_files ENTERAMENTE unknown/NULL (peor findability): **{cu['n_fully_unknown_source_files']}**")
    A(f"- source_files PARCIALMENTE unknown/NULL: **{cu['n_partial_unknown_source_files']}**")
    A("")
    zx = c.get("zxse_pin")
    if zx:
        A(f"**Pin ZXSe (brief):** `{zx['source_file']}` = **{zx['unknown_chunks']} chunks "
          f"`product_model='unknown'`** (de {zx['total_chunks']} totales; {zx['unknown_nondup']} "
          f"no-duplicados) · marcas {zx['manufacturers']} · {len(zx['document_ids'])} documento(s). "
          f"Verifica el ground-truth s78 (Morley ZXSe / MIE-MI-600).")
        A("")
    A("Top 15 source_files enteramente unknown por volumen de chunks:")
    A("")
    A("| source_file | chunks unknown | (no-dup) | marcas |")
    A("|---|---:|---:|---|")
    for r in cu["fully_unknown_source_files"][:15]:
        A(f"| `{r['source_file'][:52]}` | {r['unknown_chunks']} | {r['unknown_nondup']} | "
          f"{list(r['manufacturers'].keys())[:3]} |")
    A("")

    A("## 4. Cruce con catálogo (`doc_map.jsonl`) — documentos sin mapeo a producto")
    A("")
    um = c["catalog_unmapped_active"]
    A(f"Documentos activos SIN entrada de producto en el catálogo gobernado: **{um['n']}**. "
      "Estos no resuelven por identidad query-side (ni por la vía document-local ni por el "
      "model-filter) hasta que se mapean. Muestra (top 15 por marca):")
    A("")
    A("| marca | source_pdf_filename | product_model (doc) |")
    A("|---|---|---|")
    for r in um["rows"][:15]:
        A(f"| {r.get('manufacturer')} | `{str(r.get('source_pdf_filename'))[:48]}` | {r.get('product_model')} |")
    A("")

    A("## 5. Impacto directo en los QIDs del baseline (bot_sources → documentos → estado)")
    A("")
    qc = c["baseline_qid_cross"]
    if qc.get("available"):
        A(f"De **{qc['n_qids']} QIDs** del baseline oficial 39, **{qc['n_qids_all_cited_docs_blocked']}** "
          f"tienen TODOS sus documentos citados bloqueados por el gate de identidad (ninguno servible "
          f"por la vía document-local), y **{qc['n_qids_with_a_servable_cited_doc']}** tienen al menos "
          f"un documento citado servible hoy. NOTA: el bloqueo document-local NO implica que el bot "
          f"falle el QID — el bot sirve por retrieval vector/léxico + rerank; document-local es una "
          f"LANE de recuperación de cobertura. Este cruce mide qué QIDs se beneficiarían del unlock.")
        A("")
        A("| QID | veredicto | conducta | bot_sources | docs resueltos | bloqueados | servibles | todos-bloqueados |")
        A("|---|---|---|---:|---:|---:|---:|:--:|")
        for r in qc["rows"]:
            A(f"| {r['qid']} | {r['veredicto']} | {r['conducta_esperada']} | {r['n_bot_sources']} | "
              f"{r['n_cited_docs_resolved']} | {r['n_cited_docs_blocked']} | {r['n_cited_docs_servable']} | "
              f"{'🔴' if r['all_cited_blocked'] else '·'} |")
        A("")
    else:
        A("(baseline no disponible)")
        A("")

    A("## 6. Plan de backfill priorizado por tramos (PROPUESTAS SQL — JAMÁS aplicadas)")
    A("")
    _write_plan(A, c, cnt)

    A("## 7. Spot-checks (3 filas por clase, con la query exacta)")
    A("")
    for name, blk in payload["spot_checks"].items():
        A(f"### {name}")
        A(f"- query: `{blk.get('query')}`")
        if "rows" in blk:
            for row in blk["rows"]:
                A(f"  - `{json.dumps(row, ensure_ascii=False, default=str)}`")
        if "result" in blk:
            A(f"  - result: `{json.dumps(blk['result'], ensure_ascii=False, default=str)}`")
        A("")

    A("## 8. Honestidad del instrumento — lo que este census NO juzga")
    A("")
    A("- **El gate del RPC es servidor-side.** El census MODELA el gate proximal "
      "(`unverified_document_lineage`) desde el estado de identidad leído read-only; no ejecuta el "
      "RPC ni el retrieve→rerank de pago. Un documento marcado 'servible' aquí es servible por "
      "identidad; su selección real depende del pool y del reranker (fuera de $0). Concuerda con el "
      "corolario de s279 (D1/D2).")
    A("- **`servable_document_local_lane` ≠ 'el bot responde bien el QID'.** El bot sirve por "
      "retrieval vector/léxico+rerank; la vía document-local es una lane de COBERTURA. El cruce §5 "
      "mide beneficiarios del unlock, no fallos causales del bot.")
    A("- **Product decisions son de Alberto.** El split D1 de ZXSe por nº de lazos (ground-truth "
      "s78: ZX1Se/2Se/5Se/10Se en MIE-MI-600) y qué `product_model`/`manufacturer` asignar en el "
      "backfill son [ALBERTO]. El census cuantifica el volumen; NO decide la etiqueta.")
    A("- **El activo s83** (`evals/s83_document_models_final.jsonl`, 1014 source_files → modelos) es "
      "la fuente candidata para poblar `product_model`/identidad en el backfill, pero su aplicación "
      "requiere QA + adjudicación de conflictos (s84, no ejecutado). El census lo referencia, no lo aplica.")
    A("")
    return "\n".join(L)


def _write_plan(A, c: dict[str, Any], cnt: dict[str, Any]) -> None:
    nA = c["by_class_active"]["A_sha_backfill_placeholder"]
    nB = c["by_class_active"]["B_lineage_id_null"]
    nT1 = c["by_class_active"].get("T1_identity_complete_es_unverified", 0)
    zx = c.get("zxse_pin") or {}
    A("Los tramos están ordenados por **palanca/coste**: primero lo que desbloquea más QIDs por "
      "menos decisiones de producto. TODAS las sentencias son PROPUESTAS; requieren GO de Alberto "
      "y se aplicarían vía `supabase/migration_proposals/` (no por este script).")
    A("")
    vbc = c.get("volume_by_class", {})
    A("Volumen por clase (documentos activos afectados + chunks de esos documentos):")
    A("")
    A("| Clase | Documentos | Chunks |")
    A("|---|---:|---:|")
    for k, label in [
        ("T1_identity_complete_es_unverified", "T1 — identity-completo, falta lineage"),
        ("A_sha_backfill_placeholder", "A — sha backfill"),
        ("B_lineage_id_null", "B — lineage NULL"),
        ("B2_lineage_present_unverified", "B2 — lineage no-verified"),
        ("C_language_null", "C — language NULL"),
        ("C_doc_type_null", "C — doc_type NULL"),
        ("C_product_model_null_doclevel", "C — product_model NULL (doc)"),
    ]:
        v = vbc.get(k, {})
        A(f"| {label} | {v.get('documents', 0)} | {v.get('chunks', 0)} |")
    A("")
    A("### Tramo 1 — Verificación de lineage para los documentos ya identity-completos (mayor palanca, menor riesgo)")
    A("")
    A(f"**{nT1} documentos activos** ya están identity-completos (manufacturer+product_model+doc_type "
      f"+language='es') y solo les falta un lineage `verified` — es la cohorte de MENOR riesgo (no "
      f"re-etiqueta identidad, solo firma la verificación). Es el patrón EXACTO que s279 usó para los "
      f"6 docs servibles hoy (HP011 RP1r + 2 probes + lote inicial). Cada uno requiere que Alberto "
      f"confirme la evidencia de autoridad, pero NO decisiones de producto.")
    A("")
    A("```sql")
    A("-- PROPUESTA (NO aplicada). Crear/verificar lineage para un documento identity-completo.")
    A("-- [ALBERTO decide] el authority_contract y la evidencia por documento.")
    A("INSERT INTO document_revision_lineages (id, authority_status, authority_contract, notes)")
    A("VALUES (gen_random_uuid(), 'verified', 'explicit_document_ids_v1', '<qid/motivo>')")
    A("RETURNING id;  -- luego:")
    A("UPDATE documents SET revision_lineage_id = '<nuevo_id>'")
    A(" WHERE id = '<document_id>' AND status='active';  -- solo docs con idioma/doc_type/pm completos")
    A("```")
    A("")
    A("**Desbloquea:** los QIDs del baseline cuyo doc citado ya está identity-completo (ver §5, "
      "columna 'servibles'=0 pero sin gaps de identidad C). Verificar a mano cada uno antes de proponer.")
    A("")
    A(f"### Tramo 2 — Backfill de identidad C (language/doc_type/product_model NULL) — {nA} docs clase A + los C")
    A("")
    A("La clase A (sha `backfill:*`) coincide en gran parte con language/doc_type NULL. Poblar estos "
      "campos es prerequisito de la verificación de lineage para esa cohorte. La fuente candidata de "
      "`product_model` es el activo s83 (`s83_document_models_final.jsonl`), pero **requiere QA + "
      "adjudicación [ALBERTO]** (s84 no ejecutado).")
    A("")
    A("```sql")
    A("-- PROPUESTA (NO aplicada). Poblar identidad desde s83 tras QA de Alberto.")
    A("UPDATE documents SET language='es', doc_type='<tipo>', product_model='<modelo s83 QA'd>'")
    A(" WHERE id='<document_id>' AND status='active';")
    A("-- (el sha real 64-hex se recomputa del PDF fuente en un paso de ingest, no en SQL)")
    A("```")
    A("")
    A(f"### Tramo 3 — Clase D findability: re-tag `product_model='unknown'` en chunks_v2 (ej. ZXSe)")
    A("")
    A(f"El caso vivo: `{zx.get('source_file', 'MIE-MI-600')}` con **{zx.get('unknown_chunks', '?')} "
      f"chunks `unknown`** (Morley ZXSe). El bot admite no tener el manual porque el model-filter no "
      f"lo encuentra por modelo. **[ALBERTO]: split D1 por nº de lazos** (ground-truth s78: "
      f"ZX1Se/2Se/5Se/10Se) — el census NO decide la granularidad. Patrón reversible DB-only (s78/s80).")
    A("")
    A("```sql")
    A("-- PROPUESTA (NO aplicada). Re-tag DB-only reversible (patrón s78/s80).")
    A("-- [ALBERTO decide] si es familia genérica 'ZXSe' o split por lazos.")
    A("UPDATE chunks_v2 SET product_model='ZXSe', manufacturer='Morley'")
    A(f" WHERE source_file='{zx.get('source_file', 'MIE-MI-600')}' AND product_model='unknown';")
    A("```")
    A("")
    A(f"### Tramo 4 — Mapeo a catálogo de los {c['catalog_unmapped_active']['n']} docs sin producto")
    A("")
    A("Los documentos activos sin entrada en `doc_map.jsonl` no resuelven query-side. El activo s83 "
      "cubre 1014 source_files; el gap son los documentos activos no cubiertos. Es trabajo de "
      "curación de catálogo (workstream DEC-074), no SQL puntual.")
    A("")


if __name__ == "__main__":
    sys.exit(main())
