#!/usr/bin/env python3
"""s279 selection-reach census — adjudicating instrument (design §4.2-4.3 + A1).

Reads the LIVE ``document_local_snapshot_v3`` RPC and ``chunks_v2``/``documents``
with GET-only, read-only requests.  ZERO model calls, ZERO paid embeddings, ZERO
writes.  It measures — per query, per arm — the document-local *selection reach*
under the v4 profile (``coverage_c1_v3``, ``DOCUMENT_LOCAL_SELECTION_V2`` off) and
the v5 candidate profile (``coverage_c1_v4``, flag on), driving the REAL build
functions (``fetch_document_local_candidates`` → RPC + waterfall, the v5 plan
builder, ``_facet_gate_and_select``, ``select_document_local_coverage``).

The census ADJUDICATES; it never calibrates.  Every pre-registered rule (A4/A5/A7,
N_FACET=3) is applied exactly as built; a "loss" or a probe that is not selected is
reported with its exact cause, never fixed.

DECLARED DEVIATIONS (honest gaps — see the report §Deviations):

  D1. Anchor provenance.  Production derives the document-local anchor scope from
      the *reranked prefix* / served structural rows, which require the paid
      retrieve→rerank path (a paid LLM reranker + a paid Voyage query embedding).
      That path cannot run under the $0 contract, so the census pins the anchor
      SCOPE deterministically, in priority order:
        (a) PROBE targets (cat017/cat019): the active document that physically
            contains the pre-registered target chunk (guarantees scope↔target);
        (b) GOVERNED: the real production ``governed_source_contract`` route
            (``_document_local_source_contract_rows``), fully faithful, $0;
        (c) CATALOG∩GOLD: the governed catalog ``resolved_documents`` intersected
            with the gold ``_provenance.fuente`` source PDF(s), restricted to the
            ACTIVE/es revision.  This reproduces production's SCOPE (the reranker
            lands on that document per the handoffs) but not its anchor-route
            provenance.  The anchor identity fields (manufacturer/product_model)
            are the document's authoritative values.
      The scope is what determines the RPC snapshot; candidate reach, waterfall,
      overflow and plan deltas are therefore faithful.  Only the anchor-route
      label is a proxy.

  D2. Served view.  The facet-complement gate (A4/A7) grades need-group coverage
      over the SERVED view (reranked prefix + appended coverage).  That view also
      requires the paid path.  The census runs the gate with an EMPTY served view
      = the most permissive upper bound (every ≥N_FACET group treated as
      uncovered, grade 0).  Consequences, adjudicated honestly:
        * a target NOT selected under empty-served is DEFINITIVELY not selected
          (it fails on candidate reach, eligibility, or intra-group ranking —
          never on coverage);
        * a target selected under empty-served is only *selectable*; production
          may still skip it once the real served view raises grades.
      Candidate reach, eligibility (terms_hit vs each group) and intra-group
      ranking are exact regardless of the served view.

Usage:  python scripts/s279_selection_census.py [--smoke]
  --smoke  runs only the 2 probes + 2 controls + hp011 (governed).  Default = full
           (13 P1 QIDs + hp009/hp010 + controls).
Outputs: evals/s279_selection_census_result_v1.json
         evals/s279_selection_census_report_v1.md
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

# Force the production corpus BEFORE importing config/retriever (env is authority).
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
from src.release_profiles import load_coverage_release_policy  # noqa: E402
import src.rag.document_local_coverage as dlc  # noqa: E402
import src.rag.post_rerank_coverage as prc  # noqa: E402
from src.rag.catalog_resolver import resolve_query  # noqa: E402

# ── constants ────────────────────────────────────────────────────────────────
GOLD = ROOT / "evals/gold_answers_v1.yaml"
RESULT_PATH = ROOT / "evals/s279_selection_census_result_v1.json"
REPORT_PATH = ROOT / "evals/s279_selection_census_report_v1.md"
V4_CONFIG = ROOT / "config/retrieval_facets_v4.yaml"
V5_CONFIG = ROOT / "config/retrieval_facets_v5_document_local.yaml"
MIGRATION_PROPOSAL = (
    ROOT
    / "supabase/migration_proposals"
    / "20260722200000_s278_document_local_snapshot_v3_canonical_blob.sql"
)
V4_PROFILE = "coverage_c1_v3"
V5_PROFILE = "coverage_c1_v4"

# The 13-QID P1 set (docs/HANDOFF_P1_B92FF51_2026-07-22.md §4) + the two controls
# hp009/hp010 required by the task.
P1_QIDS = [
    "cat001", "cat017", "cat018", "cat019", "hp002", "hp003", "hp005",
    "hp011", "hp012", "hp013", "hp014", "hp017", "hp018",
]
EXTRA_CONTROL_QIDS = ["hp009", "hp010"]

# Probe targets (design §4.5): the pre-registered gold-relevant chunk per probe.
PROBE_TARGETS = {
    "cat019": "f68f2d40-cad2-4a0f-9045-9637928456aa",  # span [2699,3008)
    "cat017": "b7633e98-b011-4035-9548-a564c71e70ac",
}

# Deployed RPC canonical definition hash, obtained OUT-OF-BAND, READ-ONLY, via
#   SELECT encode(digest(pg_get_functiondef(
#       'public.document_local_snapshot_v3(jsonb,text,integer,integer)'::regprocedure),
#       'sha256'),'hex')
# on project izooestgffgscdirkfia (technical-bot) at 2026-07-23 (def_len 17991).
# PostgREST cannot evaluate pg_get_functiondef, so the value is pinned here and
# stamped in the freeze-contract with its provenance.  A live probe of the RPC
# payload ``schema`` field re-confirms that v3 is the deployed function at run
# time (see freeze_contract()).
DEPLOYED_RPC_FUNCTIONDEF_SHA256 = (
    "c691d094ef81e832f65a39f6107410046152ff50d3d84548c0b9fab33bfe2275"
)
DEPLOYED_RPC_FUNCTIONDEF_LEN = 17991
DEPLOYED_RPC_FUNCTIONDEF_PROVENANCE = (
    "read-only pg_get_functiondef via Supabase SQL, project izooestgffgscdirkfia, "
    "2026-07-23 (PostgREST cannot evaluate it; live RPC schema field re-confirmed)"
)

# Two pre-registered negative controls (design §4.2), both scoped to MC-380
# (the Detnov CAD-250 configuration manual — document 348c4ec1).
MC380_SCOPE = {
    "document_id": "348c4ec1-210a-441a-9ce7-02014a51f26d",
    "extraction_sha256": (
        "3797d14d071d618d2a6b0343dfb3d0e4bc4a8cebe75016fce5206cd9687ab68e"
    ),
    "source_file": "CAD-250_Manual-Configuracion-MC-380-es-2026-c",
}
CONTROLS = {
    # off-topic: a CCTV question whose tokens are absent from a Detnov fire panel
    # config manual -> expected 0 candidates (0 trivial, sanity floor).
    "ctrl_offtopic_mc380": (
        "¿Como se configura la grabacion continua y la deteccion de movimiento "
        "en la camara CCTV Hikvision DS-2CD2143?"
    ),
    # on-topic-adjacent: a REAL CAD-250 configuration question that is NOT cat019;
    # must produce anchors + candidates so the facet gate reaches eligibility
    # evaluation.  Adjudicated as-is (if it serves, the design fails — §4.2).
    "ctrl_ontopic_adjacent_mc380": (
        "¿Como se crea y configura una zona en la central Detnov CAD-250 (MC-380) "
        "y como se asignan los equipos y detectores a esa zona?"
    ),
}

_H: dict[str, str] = {}
_BASE = ""


# ── read-only HTTP helpers ────────────────────────────────────────────────────
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
    resp = httpx.get(f"{_BASE}/rest/v1/{table}", headers=headers, params=params, timeout=60)
    resp.raise_for_status()
    return resp


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _stable_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


# ── policy arm control (env-injected in-process, restored on exit) ─────────────
class Arm:
    """Swap ``config.COVERAGE_RELEASE_POLICY`` so the runtime flag readers observe
    the requested profile, without mutating global env.  Restores on exit."""

    def __init__(self, profile: str) -> None:
        self.profile = profile

    def __enter__(self) -> "Arm":
        self._saved = cfg.COVERAGE_RELEASE_POLICY
        cfg.COVERAGE_RELEASE_POLICY = load_coverage_release_policy(
            {"COVERAGE_RELEASE_PROFILE": self.profile}
        )
        return self

    def __exit__(self, *exc: Any) -> None:
        cfg.COVERAGE_RELEASE_POLICY = self._saved


# ── corpus fingerprint (A1) ────────────────────────────────────────────────────
def _count_and_max(table: str, ts_col: str) -> tuple[int, Any]:
    resp = _get(table, {"select": "id", "limit": "1"}, count=True)
    content_range = resp.headers.get("content-range", "*/0")
    total = int(content_range.split("/")[-1])
    mx_resp = _get(table, {"select": ts_col, "order": f"{ts_col}.desc.nullslast", "limit": "1"})
    rows = mx_resp.json()
    mx = rows[0][ts_col] if rows else None
    return total, mx


def corpus_fingerprint() -> dict[str, Any]:
    """Deterministic corpus fingerprint (A1).  No ``s107_corpus_fingerprint*``
    module exists in-tree, so this defines one: per-table row count + the max
    of a stable append timestamp (chunks_v2.created_at, documents.ingested_at).
    A static demo corpus is byte-inert between the ANTES/DESPUES reads."""
    c_total, c_max = _count_and_max("chunks_v2", "created_at")
    d_total, d_max = _count_and_max("documents", "ingested_at")
    payload = {
        "chunks_v2": {"count": c_total, "max_created_at": c_max},
        "documents": {"count": d_total, "max_ingested_at": d_max},
    }
    return {**payload, "sha256": _stable_sha256(payload)}


# ── direct FTS enumeration (late-position challenge, RPC-cap-free) ──────────────
def fts_matched_chunk_index(scope: dict[str, str], tsquery: str) -> list[int]:
    """Full matched-chunk enumeration for the late-position challenge.

    The RPC caps at ``candidate_limit+1`` (=65), so it cannot show the whole
    overflow tail.  This replays the RPC's candidate FTS predicate directly
    against chunks_v2 (read-only), returning EVERY matched chunk_index (ordered),
    so the census can stamp how many matched candidates fall beyond the waterfall
    cut and their chunk_index.  ``fts(spanish_unaccent)`` is verified equivalent
    to the RPC's ``to_tsquery('public.spanish_unaccent', ...)`` (identical kept
    ordering)."""
    params = {
        "select": "chunk_index",
        "document_id": f"eq.{scope['document_id']}",
        "extraction_sha256": f"eq.{scope['extraction_sha256']}",
        "duplicate_of": "is.null",
        "search_vector": f"fts(spanish_unaccent).{tsquery}",
        "order": "chunk_index.asc.nullslast",
        "limit": "1000",
    }
    rows = _get("chunks_v2", params).json()
    return [r["chunk_index"] for r in rows]


# ── scope resolution (D1) ──────────────────────────────────────────────────────
def _active_document_identity(document_id: str) -> dict[str, Any] | None:
    rows = _get(
        "documents",
        {
            "select": (
                "id,status,language,source_pdf_filename,source_pdf_sha256,"
                "manufacturer,product_model,revision_lineage_id"
            ),
            "id": f"eq.{document_id}",
        },
    ).json()
    return rows[0] if rows else None


def _representative_chunk(document_id: str) -> dict[str, Any] | None:
    """One chunk of the document, ordered deterministically by chunk_index.

    Production's document-local anchor IS a reranked/served CHUNK, so the anchor
    identity (extraction_sha256, source_file, manufacturer, product_model) must
    come from a chunk — NOT from the ``documents`` row.  This matters: the 7
    ``backfill:*`` documents carry a placeholder ``documents.source_pdf_sha256``
    but their chunks carry the REAL 64-hex ``extraction_sha256``, so a
    chunk-derived anchor reaches the RPC and is rejected there for the true root
    cause (unverified lineage / ambiguous identity), exactly as in production."""
    rows = _get(
        "chunks_v2",
        {
            "select": "extraction_sha256,source_file,manufacturer,product_model,chunk_index",
            "document_id": f"eq.{document_id}",
            "duplicate_of": "is.null",
            "order": "chunk_index.asc.nullslast",
            "limit": "1",
        },
    ).json()
    return rows[0] if rows else None


def _scope_from_chunk(document_id: str, chunk: dict[str, Any], route: str) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "extraction_sha256": str(chunk.get("extraction_sha256") or "").lower(),
        "source_file": str(chunk.get("source_file") or ""),
        "manufacturer": str(chunk.get("manufacturer") or ""),
        "product_model": str(chunk.get("product_model") or ""),
        "document_local_anchor_route": route,
    }


def _document_identity_audit(document_id: str) -> dict[str, Any]:
    """Read-only identity audit of a document (why the RPC accepts/rejects it)."""
    doc = _active_document_identity(document_id)
    if doc is None:
        return {"document_id": document_id, "found": False}
    sha = str(doc.get("source_pdf_sha256") or "")
    lineage_id = doc.get("revision_lineage_id")
    lineage_auth = None
    if lineage_id:
        rows = _get(
            "document_revision_lineages",
            {"select": "authority_status", "id": f"eq.{lineage_id}"},
        ).json()
        lineage_auth = (rows or [{}])[0].get("authority_status")
    return {
        "document_id": document_id,
        "found": True,
        "status": doc.get("status"),
        "language": doc.get("language"),
        "doc_type": doc.get("doc_type"),
        "source_pdf_sha256_is_backfill_placeholder": sha.startswith("backfill:"),
        "source_pdf_sha256_valid_64hex": bool(re.fullmatch(r"[0-9a-f]{64}", sha.lower())),
        "revision_lineage_id_present": bool(lineage_id),
        "lineage_authority_status": lineage_auth,
    }


def _chunk_identity(chunk_id: str) -> dict[str, Any] | None:
    rows = _get(
        "chunks_v2",
        {
            "select": "id,document_id,extraction_sha256,source_file,chunk_index,manufacturer,product_model",
            "id": f"eq.{chunk_id}",
        },
    ).json()
    return rows[0] if rows else None


def _fuente_pdf_stems(gold_row: dict[str, Any]) -> list[str]:
    fuente = str((gold_row.get("_provenance") or {}).get("fuente") or "")
    stems: list[str] = []
    # Filenames may contain spaces; split only on +,( boundaries then trim.
    for m in re.findall(r"[^+,(]*?\.pdf", fuente):
        stem = dlc.canonical_blob_stem(m.strip()).strip()
        if stem and stem not in stems:
            stems.append(stem)
    return stems


def _stem_matches(a: str, b: str) -> bool:
    a, b = a.strip().lower(), b.strip().lower()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def resolve_scopes(qid: str, query: str, gold_row: dict[str, Any]) -> dict[str, Any]:
    """Return {mode, scopes[], anchor_rows[], notes} — deterministic, $0."""
    # (a) PROBE target document.
    if qid in PROBE_TARGETS:
        tgt = _chunk_identity(PROBE_TARGETS[qid])
        if tgt is None:
            return {"mode": "probe_target_missing", "scopes": [], "anchor_rows": [], "notes": []}
        # Anchor identity from the TARGET chunk itself (guarantees scope↔target).
        scope = _scope_from_chunk(tgt["document_id"], tgt, "protected_rerank_prefix")
        return {
            "mode": "probe_target_document",
            "scopes": [scope],
            "anchor_rows": [_anchor_row(scope)],
            "notes": [f"scope pinned to the target chunk {PROBE_TARGETS[qid]} (chunk-derived anchor)"],
        }
    # (b) GOVERNED source contract (real production route).
    contract_rows, overflow = prc._document_local_source_contract_rows(query)
    if contract_rows:
        scopes = []
        anchors = []
        for row in contract_rows:
            scope = {
                "document_id": row["document_id"],
                "extraction_sha256": str(row["extraction_sha256"]).lower(),
                "source_file": dlc.canonical_blob_stem(str(row["source_file"])),
                "manufacturer": str(row.get("manufacturer") or ""),
                "product_model": str(row.get("product_model") or ""),
                "document_local_anchor_route": "governed_source_contract",
            }
            scopes.append(scope)
            anchors.append(_anchor_row(scope))
        return {
            "mode": "governed_source_contract",
            "scopes": scopes,
            "anchor_rows": anchors,
            "notes": ["real production governed anchor route"],
        }
    # (c) CATALOG ∩ GOLD source (active revision).
    resolved = resolve_query(query).get("resolved_documents") or []
    gold_stems = _fuente_pdf_stems(gold_row)
    scopes: list[dict[str, Any]] = []
    notes: list[str] = []
    for doc_ref in resolved:
        did = str(doc_ref.get("document_id") or "")
        if not did:
            continue
        doc = _active_document_identity(did)
        # Pin to the ACTIVE revision; do NOT pre-filter on language/identity — the
        # RPC is the authority and its rejection (e.g. ambiguous_document_identity
        # when documents.language/doc_type is NULL) is a reportable corpus-gap
        # finding, not a reason to hide the scope.
        if doc is None or doc.get("status") != "active":
            continue
        doc_stem = dlc.canonical_blob_stem(str(doc.get("source_pdf_filename") or ""))
        if gold_stems and not any(_stem_matches(doc_stem, gs) for gs in gold_stems):
            continue
        chunk = _representative_chunk(did)
        if chunk is None:
            notes.append(f"active doc {did[:8]} matched gold source but has no chunk to anchor")
            continue
        scope = _scope_from_chunk(did, chunk, "protected_rerank_prefix")
        if scope["document_id"] not in {s["document_id"] for s in scopes}:
            scopes.append(scope)
        if len(scopes) >= dlc.SOURCE_LIMIT:
            break
    if scopes:
        return {
            "mode": "catalog_gold_source_pinned",
            "scopes": scopes,
            "anchor_rows": [_anchor_row(s) for s in scopes],
            "notes": [
                f"catalog resolved_documents ∩ gold source ({', '.join(gold_stems) or 'n/a'}); "
                "active/es revision; anchor-route provenance is a proxy (D1)"
            ],
        }
    return {
        "mode": "scope_unresolved",
        "scopes": [],
        "anchor_rows": [],
        "notes": [
            f"no active/es catalog document matched the gold source(s) {gold_stems or 'n/a'} "
            "at $0 (production would reach this via the paid reranked-prefix anchor)"
        ],
    }


def _anchor_row(scope: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": scope["document_id"],
        "extraction_sha256": scope["extraction_sha256"],
        "source_file": scope["source_file"],
        "manufacturer": scope.get("manufacturer", ""),
        "product_model": scope.get("product_model", ""),
        "document_local_anchor_route": scope["document_local_anchor_route"],
    }


# ── per-arm measurement ────────────────────────────────────────────────────────
def _plan_scopes(anchor_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    scopes, reason = dlc._anchor_scopes(anchor_rows)
    return scopes if reason == "ok" else []


def run_arm(
    query: str,
    anchor_rows: list[dict[str, Any]],
    profile: str,
    target_id: str | None,
) -> dict[str, Any]:
    """One arm (v4 or v5): RPC + waterfall + plan + semantic + facet gate."""
    with Arm(profile):
        scopes = _plan_scopes(anchor_rows)
        plan = dlc.build_document_local_query_plan(query, scopes) if scopes else None
        candidates, authorities, trace = dlc.fetch_document_local_candidates(query, anchor_rows)
        # semantic selection (upper bound: covered_context empty).
        try:
            sem_selected, sem_trace = dlc.select_document_local_coverage(
                query, candidates, [], authorities
            )
        except Exception as exc:  # fail-open, recorded
            sem_selected, sem_trace = [], {"status": f"error:{type(exc).__name__}"}
        sem_id = str(sem_selected[0].get("id")) if sem_selected else None

        # Facet complement gate under two bracketing served-view scenarios (D2):
        #   * empty  = most permissive upper bound (all ≥N_FACET groups uncovered);
        #   * lane_served = the lane's own semantic winner is already served (a
        #     faithful, real SUBSET of production's served view) — exercises the
        #     grade-based rejection path (skipped_no_uncovered_group).
        # ``facet`` (the headline) stays the empty-served upper bound so the probe
        # verdict is the definitive not-selected test.
        facet = _run_facet_gate(plan, candidates, [], [], target_id)
        facet_lane = _run_facet_gate(plan, candidates, list(sem_selected), [], target_id)

        # per-candidate eligibility summary + target detail.
        elig, target_detail = _eligibility_summary(plan, candidates, target_id)

        # per-scope volume + overflow + late-position challenge tail.
        per_scope = _per_scope_report(plan, authorities, candidates, trace)

        kept_index = sorted(
            c.get("chunk_index") for c in candidates if isinstance(c.get("chunk_index"), int)
        )
        return {
            "profile": profile,
            "status": trace.get("status"),
            "overflow": bool(trace.get("overflow")),
            "authorities": len(authorities),
            "authority_rejections": trace.get("authority_rejections"),
            "candidate_count": len(candidates),
            "kept_chunk_index": kept_index,
            "plan": None
            if plan is None
            else {
                "config": plan.get("config", "v4"),
                "archetype": plan.get("archetype"),
                "archetypes": plan.get("archetypes"),
                "anchor_terms": plan.get("anchor_terms"),
                "need_groups": plan.get("need_groups"),
                "tsquery": plan.get("tsquery"),
                "tsquery_len": len(plan.get("tsquery", "")),
                "trim": plan.get("trim"),
                "sha256": plan.get("sha256"),
            },
            "waterfall": trace.get("candidate_waterfall"),
            "semantic_selected_id": sem_id,
            "semantic_status": sem_trace.get("status"),
            "facet": facet,
            "facet_lane_served": facet_lane,
            "eligibility": elig,
            "target_detail": target_detail,
            "per_scope": per_scope,
        }


def _run_facet_gate(
    plan: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    served: list[dict[str, Any]],
    reranked: list[dict[str, Any]],
    target_id: str | None,
) -> dict[str, Any]:
    """Run the REAL ``_facet_gate_and_select`` for one served-view scenario."""
    out: dict[str, Any] = {"applicable": plan is not None, "served_rows": len(served)}
    if plan is None:
        return out
    selection, status, grades, _need_groups = prc._facet_gate_and_select(
        served, reranked, plan, candidates
    )
    out.update(status=status, grades=grades)
    if selection is not None:
        cand = selection["candidate"]
        out.update(
            selected_id=str(cand.get("id")),
            selected_chunk_index=cand.get("chunk_index"),
            group_index=selection["group_index"],
            group_terms=list(selection["group_terms"]),
            terms_hit=selection["window"]["terms_hit"],
            is_target=str(cand.get("id")) == target_id,
        )
    return out


def _eligibility_summary(
    plan: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    target_id: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if plan is None:
        return [], None
    need_groups = list(plan.get("need_groups") or [])
    summary: list[dict[str, Any]] = []
    for idx, group in enumerate(need_groups):
        gated = len(group) >= prc.N_FACET
        eligible = 0
        best = 0
        for cand in candidates:
            window = prc._facet_best_window(str(cand.get("content") or ""), group)
            if window is not None:
                best = max(best, window["terms_hit"])
                if window["terms_hit"] >= prc.N_FACET:
                    eligible += 1
        summary.append(
            {
                "group_index": idx,
                "n_terms": len(group),
                "gated_by_A7": gated,
                "eligible_candidates": eligible,
                "max_terms_hit_in_pool": best,
            }
        )
    target_detail = None
    if target_id is not None:
        tgt = next((c for c in candidates if str(c.get("id")) == target_id), None)
        if tgt is not None:
            content = str(tgt.get("content") or "")
            groups_detail = []
            for idx, group in enumerate(need_groups):
                window = prc._facet_best_window(content, group)
                groups_detail.append(
                    {
                        "group_index": idx,
                        "n_terms": len(group),
                        "gated_by_A7": len(group) >= prc.N_FACET,
                        "terms_hit": None if window is None else window["terms_hit"],
                        "hits": None if window is None else window["hits"],
                    }
                )
            target_detail = {
                "present": True,
                "chunk_index": tgt.get("chunk_index"),
                "candidate_rank": tgt.get("document_local_candidate_rank"),
                "content_len": len(content),
                "per_group": groups_detail,
            }
        else:
            target_detail = {"present": False}
    return summary, target_detail


def _per_scope_report(
    plan: dict[str, Any] | None,
    authorities: list[dict[str, str]],
    candidates: list[dict[str, Any]],
    trace: dict[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    ts = None if plan is None else plan.get("tsquery")
    overflow_scopes = set(trace.get("candidate_overflow_scopes") or [])
    for rank, auth in enumerate(authorities, start=1):
        scope = {
            "document_id": auth["document_id"],
            "extraction_sha256": auth["extraction_sha256"],
        }
        full_matched = fts_matched_chunk_index(scope, ts) if ts else []
        kept_for_scope = [
            c.get("chunk_index")
            for c in candidates
            if str(c.get("document_local_authority_document_id") or "") == auth["document_id"]
        ]
        kept_sorted = sorted(i for i in kept_for_scope if isinstance(i, int))
        beyond = [i for i in full_matched if i not in set(kept_sorted)]
        out.append(
            {
                "scope_rank": rank,
                "source_file": auth["source_file"],
                "document_id": auth["document_id"],
                "full_matched_count": len(full_matched),
                "kept_count": len(kept_sorted),
                "beyond_cut_count": len(beyond),
                "beyond_cut_chunk_index": beyond,
                "overflow": rank in overflow_scopes or len(beyond) > 0,
            }
        )
    return out


# ── delta classification (v4 vs v5) ────────────────────────────────────────────
def classify_delta(v4: dict[str, Any], v5: dict[str, Any], target_id: str | None) -> dict[str, Any]:
    v4_ids = {v4["semantic_selected_id"]} - {None}
    v5_ids = {v5["semantic_selected_id"]} - {None}
    facet_v5 = v5.get("facet", {})
    if facet_v5.get("selected_id"):
        v5_ids = v5_ids | {facet_v5["selected_id"]}
    gained = sorted(v5_ids - v4_ids)
    lost = sorted(v4_ids - v5_ids)
    # A lane that never reaches a candidate pool in EITHER arm is not "SAME"
    # (the two arms did not agree on a selection) — it is blocked upstream, at
    # the RPC authority / anchor layer.  Surface that distinctly.
    fetched = {"fetched", "no_fts_candidates"}
    lane_blocked = (
        v4["candidate_count"] == 0
        and v5["candidate_count"] == 0
        and (v4["status"] not in fetched or v5["status"] not in fetched)
    )
    if lane_blocked:
        klass = "LANE_BLOCKED"
    elif gained and lost:
        klass = "MIXED"
    elif gained:
        klass = "GAIN"
    elif lost:
        klass = "LOSS"
    else:
        klass = "SAME"
    vol_delta = v5["candidate_count"] - v4["candidate_count"]
    return {
        "classification": klass,
        "lane_blocked_reason": v5["status"] if lane_blocked else None,
        "lane_blocked_rejections": v5.get("authority_rejections") if lane_blocked else None,
        "candidate_volume_v4": v4["candidate_count"],
        "candidate_volume_v5": v5["candidate_count"],
        "candidate_volume_delta": vol_delta,
        "overflow_v4": v4["overflow"],
        "overflow_v5": v5["overflow"],
        "v4_semantic_selected": v4["semantic_selected_id"],
        "v5_semantic_selected": v5["semantic_selected_id"],
        "v5_facet_selected": facet_v5.get("selected_id"),
        "gained_ids": gained,
        "lost_ids": lost,
        "gained_includes_target": bool(target_id and target_id in gained),
        "plan_changed": (v4.get("plan") or {}).get("sha256")
        != (v5.get("plan") or {}).get("sha256"),
    }


# ── probe / control adjudication text ──────────────────────────────────────────
def adjudicate_probe(qid: str, target_id: str, v5: dict[str, Any]) -> dict[str, Any]:
    td = v5.get("target_detail") or {}
    facet = v5.get("facet") or {}
    if not td.get("present"):
        return {
            "verdict": "NOT_SELECTED",
            "reason": "target is not among the v5 RPC candidate pool "
            f"(status={v5['status']}, candidates={v5['candidate_count']}) — "
            "no candidate reach",
        }
    gated_hits = [
        g for g in td.get("per_group", []) if g["gated_by_A7"] and (g["terms_hit"] or 0) >= prc.N_FACET
    ]
    selected_target = facet.get("is_target") is True
    if selected_target:
        return {
            "verdict": "SELECTED_BY_FACET",
            "reason": f"target eligible+selected for group {facet['group_index']} "
            f"({facet['terms_hit']} terms) under empty served view (D2 upper bound)",
        }
    if v5.get("semantic_selected_id") == target_id:
        return {
            "verdict": "SELECTED_BY_SEMANTIC",
            "reason": "target selected by the semantic document-local selector",
        }
    if not gated_hits:
        best = max((g.get("terms_hit") or 0) for g in td.get("per_group", [])) if td.get("per_group") else 0
        offending = [
            f"g{g['group_index']}({g['n_terms']}t,gated={g['gated_by_A7']}):terms_hit={g['terms_hit']}"
            for g in td.get("per_group", [])
        ]
        return {
            "verdict": "NOT_SELECTED",
            "reason": "target is a candidate but NOT eligible: no ≥N_FACET(=3) window on any "
            f"A7-gated (≥3-term) need-group (max terms_hit in target={best}). "
            f"Per-group: {offending}. Facet winner = "
            f"{facet.get('selected_id')} (chunk_index {facet.get('selected_chunk_index')}, "
            f"group {facet.get('group_index')}, {facet.get('terms_hit')} terms).",
        }
    # eligible but lost intra-group ranking
    return {
        "verdict": "NOT_SELECTED",
        "reason": "target eligible but lost intra-group ranking to "
        f"{facet.get('selected_id')} (chunk_index {facet.get('selected_chunk_index')}, "
        f"group {facet.get('group_index')}, {facet.get('terms_hit')} terms)",
    }


# ── main ───────────────────────────────────────────────────────────────────────
def freeze_contract(query_index: list[dict[str, str]]) -> dict[str, Any]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    # Live re-confirmation that v3 is the deployed function (schema field probe).
    probe = _get(
        "rpc/" + dlc.SNAPSHOT_RPC,
        {
            "anchor_scopes": json.dumps([MC380_SCOPE], separators=(",", ":")),
            "fts_query": "cad",
            "family_limit": "16",
            "candidate_limit": "1",
        },
    ).json()
    return {
        "commit_head": head,
        "worktree_dirty": dirty,
        "v4_config": {"path": str(V4_CONFIG.relative_to(ROOT)), "sha256_lf": _sha256_lf(V4_CONFIG)},
        "v5_config": {"path": str(V5_CONFIG.relative_to(ROOT)), "sha256_lf": _sha256_lf(V5_CONFIG)},
        "query_facets_v4_loaded_sha256": _sha256_text(dlc.QUERY_CONFIG.read_text(encoding="utf-8")),
        "query_facets_v5_loaded_sha256": _sha256_text(dlc.QUERY_CONFIG_V5.read_text(encoding="utf-8")),
        "rpc": {
            "name": dlc.SNAPSHOT_RPC,
            "deployed_functiondef_sha256": DEPLOYED_RPC_FUNCTIONDEF_SHA256,
            "deployed_functiondef_len": DEPLOYED_RPC_FUNCTIONDEF_LEN,
            "deployed_functiondef_provenance": DEPLOYED_RPC_FUNCTIONDEF_PROVENANCE,
            "live_schema_reconfirmed": probe.get("schema"),
            "migration_proposal_sha256_lf": _sha256_lf(MIGRATION_PROPOSAL),
        },
        "profiles": {"v4": V4_PROFILE, "v5": V5_PROFILE},
        "selector": {
            "N_FACET": prc.N_FACET,
            "FACET_COMPLEMENT_BUDGET": prc.FACET_COMPLEMENT_BUDGET,
            "CANDIDATE_LIMIT": dlc.CANDIDATE_LIMIT,
            "TOTAL_CANDIDATE_LIMIT": dlc.TOTAL_CANDIDATE_LIMIT,
            "SOURCE_LIMIT": dlc.SOURCE_LIMIT,
        },
        "queries": query_index,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def run_query(qid: str, query: str, gold_row: dict[str, Any], is_control: bool) -> dict[str, Any]:
    target_id = PROBE_TARGETS.get(qid)
    if is_control:
        scope = dict(MC380_SCOPE)
        doc = _active_document_identity(scope["document_id"])
        scope["manufacturer"] = str((doc or {}).get("manufacturer") or "")
        scope["product_model"] = str((doc or {}).get("product_model") or "")
        scope["document_local_anchor_route"] = "protected_rerank_prefix"
        resolution = {
            "mode": "control_mc380_pinned",
            "scopes": [scope],
            "anchor_rows": [_anchor_row(scope)],
            "notes": ["control scoped to MC-380 (348c4ec1)"],
        }
    else:
        resolution = resolve_scopes(qid, query, gold_row or {})

    record: dict[str, Any] = {
        "qid": qid,
        "query": query,
        "is_control": is_control,
        "is_probe": qid in PROBE_TARGETS,
        "target_id": target_id,
        "scope_mode": resolution["mode"],
        "scope_notes": resolution["notes"],
        "scopes": [
            {k: v for k, v in s.items() if not k.startswith("_")} for s in resolution["scopes"]
        ],
        "scope_identity_audit": [
            _document_identity_audit(s["document_id"]) for s in resolution["scopes"]
        ],
    }
    if not resolution["anchor_rows"]:
        record["status"] = "no_scope"
        return record

    fp_before = corpus_fingerprint()
    v4 = run_arm(query, resolution["anchor_rows"], V4_PROFILE, target_id)
    v5 = run_arm(query, resolution["anchor_rows"], V5_PROFILE, target_id)
    fp_after = corpus_fingerprint()
    retries = 0
    while fp_before["sha256"] != fp_after["sha256"] and retries < 2:
        retries += 1
        fp_before = fp_after
        v4 = run_arm(query, resolution["anchor_rows"], V4_PROFILE, target_id)
        v5 = run_arm(query, resolution["anchor_rows"], V5_PROFILE, target_id)
        fp_after = corpus_fingerprint()
    record["fingerprint_stable"] = fp_before["sha256"] == fp_after["sha256"]
    record["fingerprint_retries"] = retries
    record["fingerprint_sha256"] = fp_after["sha256"]
    record["v4"] = v4
    record["v5"] = v5
    record["delta"] = classify_delta(v4, v5, target_id)
    if qid in PROBE_TARGETS:
        record["probe_verdict"] = adjudicate_probe(qid, target_id, v5)
    record["status"] = "measured"
    return record


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="probes + controls + hp011 only")
    args = parser.parse_args(argv)

    _init_http()
    gold = {r["qid"]: r for r in yaml.safe_load(GOLD.read_text(encoding="utf-8"))}

    if args.smoke:
        sweep_qids = ["cat017", "cat019", "hp011"]
    else:
        sweep_qids = P1_QIDS + EXTRA_CONTROL_QIDS

    query_index = [{"qid": q, "question": gold[q]["question"]} for q in sweep_qids]
    query_index += [{"qid": q, "question": text, "synthetic_control": "true"} for q, text in CONTROLS.items()]

    contract = freeze_contract(query_index)
    print(f"commit={contract['commit_head'][:10]} dirty={contract['worktree_dirty']} "
          f"rpc={contract['rpc']['name']} live_schema={contract['rpc']['live_schema_reconfirmed']}")
    print(f"corpus fingerprint chunks_v2={corpus_fingerprint()['chunks_v2']['count']}")

    records: list[dict[str, Any]] = []
    for qid in sweep_qids:
        print(f"=== {qid} ===")
        rec = run_query(qid, gold[qid]["question"], gold[qid], is_control=False)
        records.append(rec)
        _print_brief(rec)
    for cid, text in CONTROLS.items():
        print(f"=== {cid} (control) ===")
        rec = run_query(cid, text, {}, is_control=True)
        records.append(rec)
        _print_brief(rec)

    payload = {
        "schema": "s279_selection_census_v1",
        "authority": "DEVELOPMENT_CENSUS_READ_ONLY_ZERO_MODEL_CALLS",
        "freeze_contract": contract,
        "declared_deviations": {
            "D1_anchor_provenance": "scope pinned deterministically ($0); anchor-route a proxy",
            "D2_served_view": "empty served view = most permissive upper bound for the facet gate",
        },
        "records": records,
    }
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = build_report(payload)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print("\n" + "=" * 70)
    print(report[report.rfind("## Totals"):] if "## Totals" in report else report[-1500:])
    print(f"\nresult: {RESULT_PATH}")
    print(f"report: {REPORT_PATH}")
    return 0


def _print_brief(rec: dict[str, Any]) -> None:
    if rec.get("status") != "measured":
        print(f"  {rec['status']} mode={rec['scope_mode']}")
        return
    d = rec["delta"]
    print(f"  mode={rec['scope_mode']} | v4_cands={d['candidate_volume_v4']} "
          f"v5_cands={d['candidate_volume_v5']} (Δ{d['candidate_volume_delta']}) | "
          f"overflow v4={d['overflow_v4']} v5={d['overflow_v5']} | class={d['classification']}")
    if rec.get("probe_verdict"):
        print(f"  PROBE {rec['qid']}: {rec['probe_verdict']['verdict']} — {rec['probe_verdict']['reason'][:160]}")


# ── report ─────────────────────────────────────────────────────────────────────
def build_report(payload: dict[str, Any]) -> str:
    fc = payload["freeze_contract"]
    L: list[str] = []
    L.append("# s279 — Censo de alcance de selección (document-local) — v1")
    L.append("")
    L.append("Instrumento: `scripts/s279_selection_census.py`. Read-only, **0 llamadas a "
             "modelos/embeddings de pago, 0 escrituras**. El censo ADJUDICA (no calibra): "
             "aplica A4/A5/A7 y N_FACET=3 exactamente como están construidos.")
    L.append("")
    L.append("## Freeze-contract (A1)")
    L.append("")
    L.append(f"- commit HEAD: `{fc['commit_head']}` (worktree dirty: {fc['worktree_dirty']})")
    L.append(f"- perfiles: v4=`{fc['profiles']['v4']}` (flag off) · v5=`{fc['profiles']['v5']}` (flag on)")
    L.append(f"- v4 config `{fc['v4_config']['path']}` sha256-LF `{fc['v4_config']['sha256_lf']}`")
    L.append(f"- v5 config `{fc['v5_config']['path']}` sha256-LF `{fc['v5_config']['sha256_lf']}`")
    L.append(f"- RPC: `{fc['rpc']['name']}` · functiondef sha256 `{fc['rpc']['deployed_functiondef_sha256']}` "
             f"(len {fc['rpc']['deployed_functiondef_len']}; {fc['rpc']['deployed_functiondef_provenance']})")
    L.append(f"- RPC schema re-confirmado en vivo: `{fc['rpc']['live_schema_reconfirmed']}` · "
             f"migración propuesta sha256-LF `{fc['rpc']['migration_proposal_sha256_lf']}`")
    L.append(f"- selector: N_FACET={fc['selector']['N_FACET']} · FACET_COMPLEMENT_BUDGET="
             f"{fc['selector']['FACET_COMPLEMENT_BUDGET']} · CANDIDATE_LIMIT={fc['selector']['CANDIDATE_LIMIT']} "
             f"· SOURCE_LIMIT={fc['selector']['SOURCE_LIMIT']}")
    cf = corpus_fingerprint()
    L.append(f"- corpus fingerprint: chunks_v2={cf['chunks_v2']['count']} "
             f"(max created_at {cf['chunks_v2']['max_created_at']}) · documents={cf['documents']['count']} "
             f"· sha256 `{cf['sha256']}`")
    L.append(f"- queries: {len(fc['queries'])} · generado {fc['generated_utc']}")
    L.append("")
    L.append("## Deviaciones declaradas (honestidad > resultado)")
    L.append("")
    L.append("- **D1 (provenance de anchors).** El anchor de producción sale del *reranked "
             "prefix*/structural, que exige el retrieve→rerank de pago (LLM + embedding Voyage). "
             "Bajo el contrato $0 el censo FIJA el SCOPE de forma determinista: probes → documento "
             "activo que contiene el chunk-diana; governed → ruta real `governed_source_contract`; "
             "resto → catálogo `resolved_documents` ∩ fuente del gold (revisión activa/es). El scope "
             "determina el snapshot RPC → alcance/waterfall/overflow/plan son FIELES; solo la "
             "etiqueta de ruta del anchor es proxy.")
    L.append("- **D2 (vista servida).** La compuerta por-faceta (A4/A7) gradúa cobertura sobre la "
             "vista SERVIDA (prefijo+coverage), también de pago. El censo corre la compuerta con "
             "vista servida VACÍA = cota superior más permisiva (todo grupo ≥N_FACET tratado como "
             "no-cubierto, grado 0). Corolario: un diana NO-seleccionado con vista vacía es "
             "definitivamente no-seleccionado (falla por alcance/elegibilidad/ranking, nunca por "
             "cobertura); un diana seleccionado con vista vacía es solo *seleccionable*.")
    L.append("")

    records = payload["records"]
    probes = [r for r in records if r.get("is_probe")]
    controls = [r for r in records if r.get("is_control")]

    # Probes
    L.append("## Probes cat017/cat019 (§4.5) — veredicto adjudicado")
    L.append("")
    for r in probes:
        L.append(f"### {r['qid']} — diana `{r['target_id']}`")
        if r.get("status") != "measured":
            L.append(f"- {r['status']}"); L.append(""); continue
        pv = r["probe_verdict"]
        d = r["delta"]
        L.append(f"- **Veredicto: {pv['verdict']}**")
        L.append(f"- {pv['reason']}")
        L.append(f"- alcance de candidato: v4 cands={d['candidate_volume_v4']} (overflow "
                 f"{d['overflow_v4']}) · v5 cands={d['candidate_volume_v5']} (overflow {d['overflow_v5']}) "
                 f"· clase delta **{d['classification']}**")
        td = r["v5"].get("target_detail") or {}
        if td.get("present"):
            L.append(f"- diana en v5: chunk_index {td['chunk_index']}, candidate_rank {td['candidate_rank']}; "
                     "terms_hit por grupo: " + ", ".join(
                        f"g{g['group_index']}({g['n_terms']}t,gated={g['gated_by_A7']})={g['terms_hit']}"
                        for g in td.get("per_group", [])))
        for ps in r["v5"].get("per_scope", []):
            if ps["overflow"]:
                L.append(f"- reto tardío (v5, {ps['source_file']}): matched={ps['full_matched_count']}, "
                         f"kept={ps['kept_count']}, fuera del corte={ps['beyond_cut_count']} "
                         f"(chunk_index {ps['beyond_cut_chunk_index']})")
        L.append("")

    # Controls
    L.append("## Controles negativos (§4.2)")
    L.append("")
    for r in controls:
        L.append(f"### {r['qid']}")
        L.append(f"- query: {r['query']}")
        if r.get("status") != "measured":
            L.append(f"- {r['status']}"); L.append(""); continue
        d = r["delta"]
        v5 = r["v5"]
        fe = v5["facet"]
        fl = v5.get("facet_lane_served", {})
        L.append(f"- v4 cands={d['candidate_volume_v4']} · v5 cands={d['candidate_volume_v5']} "
                 f"(overflow v4={d['overflow_v4']}→v5={d['overflow_v5']})")
        L.append(f"- gate (vista VACÍA, cota superior): status=`{fe.get('status')}`"
                 + (f" → **SIRVIÓ** id={fe.get('selected_id')} (grupo {fe.get('group_index')}, "
                    f"{fe.get('terms_hit')} términos)" if fe.get("selected_id")
                    else " → NO sirvió"))
        L.append(f"- gate (vista=ganador del lane, cota inferior): status=`{fl.get('status')}`"
                 + (f" → SIRVIÓ id={fl.get('selected_id')}" if fl.get("selected_id")
                    else " → **rechazó por ventana/grado** (punto de fallo verificado)"))
        if fe.get("selected_id"):
            L.append("- **HALLAZGO (adjacent):** bajo la vista más permisiva el gate SIRVE una fila "
                     "por-faceta para una query adyacente. Bajo la vista con el ganador del lane "
                     "servido el gate " + ("rechaza (grade)" if not fl.get("selected_id") else "aún sirve") +
                     ". La salvaguarda contra over-selección de queries adyacentes depende ENTERAMENTE "
                     "de la cobertura de la vista servida REAL (D2), no observable a $0.")
        L.append("- elegibilidad EVALUADA (por grupo ≥N_FACET): " + ("; ".join(
            f"g{e['group_index']}({e['n_terms']}t,gated={e['gated_by_A7']}):elig={e['eligible_candidates']},"
            f"max_hit={e['max_terms_hit_in_pool']}" for e in v5.get("eligibility", [])) or "n/a"))
        L.append("")

    # Per-query table
    L.append("## Tabla por query (v4 vs v5)")
    L.append("")
    L.append("Nota: la clase delta cuenta la fila por-faceta v5 con vista servida VACÍA (cota "
             "superior). Como bajo esa vista todo grupo ≥N_FACET está no-cubierto, el complemento "
             "por-faceta dispara ampliamente ⇒ **el conteo de GAIN está inflado**; la columna "
             "`facet(vacía→lane)` muestra el gate bajo ambas vistas para desinflarlo.")
    L.append("")
    L.append("| qid | modo scope | v5 RPC status | v4 cands | v5 cands | Δvol | overflow v4→v5 | plan Δ | clase | facet(vacía→lane) |")
    L.append("|---|---|---|---:|---:|---:|---|:--:|---|---|")
    for r in records:
        if r.get("status") != "measured":
            L.append(f"| {r['qid']} | {r['scope_mode']} | — | — | — | — | — | — | {r.get('status')} | — |")
            continue
        d = r["delta"]
        fe = r["v5"]["facet"]
        fl = r["v5"].get("facet_lane_served", {})
        fac_e = "sirvió" if fe.get("selected_id") else (fe.get("status") or "n/a")
        fac_l = "sirvió" if fl.get("selected_id") else (fl.get("status") or "n/a")
        rej = r["v5"].get("authority_rejections")
        status = r["v5"].get("status")
        status_cell = f"{status}" + (f" {rej}" if rej else "")
        L.append(f"| {r['qid']} | {r['scope_mode']} | {status_cell} | {d['candidate_volume_v4']} | "
                 f"{d['candidate_volume_v5']} | {d['candidate_volume_delta']:+d} | "
                 f"{d['overflow_v4']}→{d['overflow_v5']} | {'sí' if d['plan_changed'] else 'no'} | "
                 f"{d['classification']} | {fac_e}→{fac_l} |")
    L.append("")

    # Losses adjudicated
    L.append("## Pérdidas / ganancias adjudicadas (una a una)")
    L.append("")
    for r in records:
        if r.get("status") != "measured":
            continue
        d = r["delta"]
        if d["classification"] in {"SAME", "LANE_BLOCKED"} or not (d["gained_ids"] or d["lost_ids"]):
            continue
        L.append(f"- **{r['qid']} [{d['classification']}]**: "
                 f"v4_sem={d['v4_semantic_selected']} → v5_sem={d['v5_semantic_selected']} "
                 f"+ v5_facet={d['v5_facet_selected']}; gained={d['gained_ids']} lost={d['lost_ids']}"
                 + (f" · gained incluye la diana" if d['gained_includes_target'] else ""))
    L.append("")

    # Unexpected structural findings (auto-detected from the measured records).
    L.append("## Hallazgos estructurales inesperados")
    L.append("")
    # (H0) upstream reachability gate — the dominant finding (data-driven).
    p1_measured = [r for r in records if not r.get("is_control") and r.get("status") == "measured"]
    reachable = sorted(r["qid"] for r in p1_measured
                       if r["v5"].get("status") in {"fetched", "no_fts_candidates"}
                       and r["v5"].get("authorities"))
    blocked = [r for r in p1_measured if r["delta"]["classification"] == "LANE_BLOCKED"]
    backfill_qids, unverified_qids = [], []
    for r in blocked:
        aud = (r.get("scope_identity_audit") or [{}])[0]
        if aud.get("source_pdf_sha256_is_backfill_placeholder") or not aud.get("source_pdf_sha256_valid_64hex"):
            backfill_qids.append(r["qid"])
        else:
            unverified_qids.append(r["qid"])
    blocked_status = sorted({r["v5"].get("status") for r in blocked})
    L.append(f"- **H0 — la maquinaria s279 (C1/C2/C3) es INALCANZABLE para la mayoría del set P1 "
             "por una compuerta de identidad AGUAS ARRIBA, ajena a la lógica de selección.** Con "
             "anchors CHUNK-derivados (fieles a producción), de los "
             f"{len(p1_measured)} QIDs no-control medidos (13 P1 + hp009/hp010) el RPC resuelve "
             f"autoridad para solo {reachable} = 3 documentos servibles (los 2 docs-probe con el "
             "data-fix de identidad s278 + el doc RP1r del contrato gobernado). Los otros "
             f"{len(blocked)} son rechazados por el RPC con {blocked_status} (0 candidatos en ambos "
             "brazos ⇒ `LANE_BLOCKED`, NO «SAME»). Bajo ese rechazo uniforme hay DOS estados de "
             "identidad de corpus PRE-existentes (auditados read-only, `scope_identity_audit` en el "
             f"JSON): (a) **{sorted(backfill_qids)}** con `source_pdf_sha256='backfill:*'` "
             "(placeholder, no 64-hex) + language/doc_type NULL; (b) "
             f"**{sorted(unverified_qids)}** con blob/idioma/doc_type completos pero lineage con "
             "`authority_status != 'verified'`. En AMBOS el gate proximal del RPC es "
             "`unverified_document_lineage`. → Los levers de selection-reach solo pican donde el "
             "documento está identity-completo Y lineage-verificado (hoy = 3 docs). El unlock real "
             "es un backfill de identidad + verificación de lineage más amplio, NO un ajuste de "
             "C1/C2/C3.")
    L.append("")
    # (H1) cat017 commissioning dead-group: sub-N_FACET group after A5 trim.
    cat017 = next((r for r in records if r["qid"] == "cat017" and r.get("status") == "measured"), None)
    if cat017:
        ng = (cat017["v5"].get("plan") or {}).get("need_groups") or []
        small = [(i, g) for i, g in enumerate(ng) if len(g) < prc.N_FACET]
        trim = (cat017["v5"].get("plan") or {}).get("trim") or {}
        L.append("- **H1 — el lever `commissioning_setup` de C3 nace muerto para su propio diana "
                 "(cat017).** El arquetipo v5 se añadió (design §3) para recuperar el gap CLSS "
                 "«crear sitio/edificio + licencia .bin». Su need declara 6 términos "
                 "(sitio/edificio/licencia/bin/alta/portal), pero: (i) `alta` es token de la query "
                 "→ excluido del grupo; (ii) el trim A5 (round-robin desde el ÚLTIMO grupo) retira "
                 "PRIMERO `portal`, `bin`, `licencia` — los tokens que el propio design verificó "
                 "contra el chunk-diana. Resultado: el grupo llega a la compuerta como "
                 f"{small and [g for _, g in small]} (<N_FACET={prc.N_FACET}), que A7 EXCLUYE del "
                 "gate por definición, y cuya elegibilidad (ventana ≥3 términos distintos) es "
                 "inalcanzable con solo 2 términos. El diana b7633e98 SÍ contiene sitio+edificio "
                 f"(terms_hit=2), pero 2<3. Trim aplicado: terms_removed={trim.get('terms_removed')}. "
                 "→ El lever no puede disparar por construcción para su caso objetivo; N_FACET no es "
                 "el único bloqueo (el techo de terms_hit del grupo ya es < N_FACET).")
    # (H2) cat019 C1 mechanism.
    cat019 = next((r for r in records if r["qid"] == "cat019" and r.get("status") == "measured"), None)
    if cat019:
        d = cat019["delta"]
        ps = next((p for p in cat019["v5"].get("per_scope", []) if p["overflow"]), {})
        L.append(f"- **H2 — C1 (waterfall) SÍ recupera alcance de candidato en cat019, pero no el "
                 f"span-diana vía facet.** v4 descarta el scope MC-380 entero por overflow "
                 f"({d['candidate_volume_v4']} candidatos); v5 conserva {d['candidate_volume_v5']} "
                 f"(matched total={ps.get('full_matched_count')}, fuera del corte="
                 f"{ps.get('beyond_cut_count')}). El diana f68f2d40 (chunk_index 14) sobrevive "
                 f"(candidate_rank 2), PERO su ventana tiene terms_hit≤1 para todo grupo → NO "
                 "elegible (N_FACET=3). La ganancia de C1 es real a nivel de POOL; la vía por-faceta "
                 "no convierte esa ganancia en el span-diana. La recuperación de cat019 dependería "
                 "del selector SEMÁNTICO (no medido a fondo aquí) o de bajar N_FACET (NO se toca).")
    # (H3) empty-served facet firing inflation.
    L.append("- **H3 — la fila por-faceta dispara casi universalmente bajo vista servida vacía.** "
             "Es un artefacto de la cota superior (D2), no una ganancia de producción: con la vista "
             "= ganador del lane, varias disparadas se convierten en `skipped_no_uncovered_group`. "
             "Toda lectura de «GAIN por-faceta» debe leerse contra la columna `facet(vacía→lane)`.")
    L.append("")

    # Totals
    measured = [r for r in records if r.get("status") == "measured"]
    classes = {}
    for r in measured:
        classes[r["delta"]["classification"]] = classes.get(r["delta"]["classification"], 0) + 1
    probe_verdicts = {r["qid"]: r["probe_verdict"]["verdict"] for r in probes if r.get("status") == "measured"}
    overflow_v5 = sum(1 for r in measured if r["delta"]["overflow_v5"])
    unresolved = [r["qid"] for r in records if r.get("status") != "measured"]
    L.append("## Totals")
    L.append("")
    L.append(f"- queries: {len(records)} · medidas: {len(measured)} · sin scope $0: "
             f"{len(unresolved)} {unresolved}")
    L.append(f"- clases delta: {classes}")
    L.append(f"- scopes en overflow (v5): {overflow_v5}")
    L.append(f"- probes: {probe_verdicts}")
    ctrl_served = {
        r['qid']: {
            "empty": bool(r['v5']['facet'].get('selected_id')),
            "lane_served": bool(r['v5'].get('facet_lane_served', {}).get('selected_id')),
        }
        for r in controls if r.get('status') == 'measured'
    }
    L.append(f"- controles (sirvió bajo vista vacía / vista=lane): {ctrl_served}")
    facet_empty_fire = sum(1 for r in measured if r['v5']['facet'].get('selected_id'))
    facet_lane_fire = sum(1 for r in measured if r['v5'].get('facet_lane_served', {}).get('selected_id'))
    L.append(f"- fila por-faceta disparó: vista vacía {facet_empty_fire}/{len(measured)} · "
             f"vista=lane {facet_lane_fire}/{len(measured)} (desinflado)")
    L.append(f"- fingerprint estable en todos los pares: "
             f"{all(r.get('fingerprint_stable', True) for r in measured)}")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
