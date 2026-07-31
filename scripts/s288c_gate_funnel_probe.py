#!/usr/bin/env python
"""s288c — probe de FUNNEL de las dos puertas content-keyed existentes (paso 2-3
de la RUTA RE-ADJUDICADA del dúo r2, `evals/s288c_composition_lever_respec_v1.md`).

READ-ONLY: 0 escrituras en DB · 0 llamadas a jueces/LLM · 0 ediciones de código o
config.  El ÚNICO gasto es el embedding de `retrieve_chunks` (Voyage) para
re-derivar el pool — declarado en el recibo (`cost.embedding_calls`).

MISIÓN A (cat017) — ¿por qué la lane `document_local_content_coverage_v1` NO
apendiza `b7633e98` (HOP-138-8ES p.5, el portador del hecho CLSS)?  Se traza el
funnel con las FUNCIONES REALES sobre inputs reales:
  A0  plan puro   : expand_query_facets(v5, multi_match) + _build_document_local_query_plan_v5
  A1  pool fresco : retrieve_chunks (1 embedding) + prefijo servido reconstruido
                    de `topk_ids` del artefacto (hidratación GET-only por id)
  A2  seam real   : apply_profiled_post_rerank_coverage -> traza de lanes completa
  A3  paso a paso : anchors -> scopes -> plan -> candidate pool -> selector

MISIÓN B (hp002) — el singleton del hecho de SEGURIDAD:
  B1  dump del documento ASD535 + adjudicación léxica local contra el hecho
  B2  atestación de la ventana del singleton por los need-groups EXISTENTES de
      `config/evidence_coverage_facets_v5.yaml` (vara REAL: `_facet_best_window`
      de post_rerank_coverage, N_FACET=3 — no se reimplementa)
  B3  funnel de `obligation_warning_reserve_v1`: ¿era candidato el singleton?
      ¿perdió por orden / presupuesto / gate?

Uso:
    python scripts/s288c_gate_funnel_probe.py --mission A
    python scripts/s288c_gate_funnel_probe.py --mission B
    python scripts/s288c_gate_funnel_probe.py --mission AB      (por defecto)
    python scripts/s288c_gate_funnel_probe.py --mission B --no-retrieve
        (B1/B2 y la parte offline de B3, sin gastar el embedding)

Recibo: `evals/s288c_gate_funnel_probe_v1.json`
"""
from __future__ import annotations

import os

# ── Freeze-contract: el MISMO flag-set de la DEMO que mide el instrumento v3.1
# (scripts/factlevel_assessment.py:62-120).  Se exporta ANTES de importar el
# pipeline: src/config.py lee getenv en import-time.  Sin esto el probe mediría
# otra stack de lanes bajo la etiqueta "HEAD".
DEMO_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2",
    "ENUNCIADOS_MULTIVECTOR": "on",
    "IDENTITY_RESOLVE": "on",
    "IDENTITY_RESOLVE_POLICY": "replace",
    "COVERAGE_RELEASE_PROFILE": "coverage_c1_v4",
    "MUST_PRESERVE_CONTRACT": "on",
    "VISUAL_ASSETS_REGISTRY": "on",
    "ANTI_DIAGRAM_INVENTION": "on",
    "WIRING_TOPOLOGY_GUARD": "on",
    "GENERATOR_DIRECT_FIRST": "on",
    "GENERATOR_FOLLOWUPS": "off",
    "VISUAL_ASSETS_LISTING_GATE": "on",
    "LLM_MAX_TOKENS": "3500",
    "RERANK_TOP_K": "10",
    "RERANKER_BACKEND": "llm",
    "MERGE_STRATEGY": "stamps",
    "RERANK_PREVIEW_CHARS": "800",
    "HYDE_ENABLED": "false",
    "DIVERSIFY_TIEBREAK": "off",
    "HYQ_PILOT_FILE": "",
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "HYQ_TABLE": "on",
    "GENERATOR_SELECTION_BLOCK": "on",
    "TABLE_PREAMBLE_CLOSURE": "off",
    "CANONICAL_HYQ_COVERAGE": "off",
    "COMPATIBILITY_BUNDLE_COVERAGE": "off",
    "RERANK_POOL_COVERAGE": "off",
    "STRUCTURAL_CASCADE_COVERAGE": "off",
    "LOGICAL_RECORD_COVERAGE": "off",
    "EVIDENCE_DERIVATION_OVERLAY": "off",
    "STRUCTURAL_NEIGHBOR_SHADOW": "off",
}
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=False)  # NO pisar los DEMO_FLAGS
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v  # re-afirmar tras load_dotenv (patrón _assert_demo_flags)

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL, COVERAGE_RELEASE_POLICY
from src.rag import document_local_coverage as dlc
from src.rag import post_rerank_coverage as prc
from src.rag import rerank_pool_coverage as rpc
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage
from src.rag.query_facets import expand_query_facets
from src.rag.retriever import retrieve_chunks
from src.release_profiles import DOCUMENT_LOCAL_LANE

OUT = ROOT / "evals/s288c_gate_funnel_probe_v1.json"
CAT017_ARTIFACTS = {
    "rep1": ROOT / "evals/s100_factlevel_smoke_v31_cat017_head_rep1.yaml",
    "rep2": ROOT / "evals/s100_factlevel_smoke_v31_cat017_head_rep2.yaml",
}
P1MAP_ARTIFACTS = {
    "rep1": ROOT / "evals/s100_factlevel_smoke_v31_p1map_rep1.yaml",
    "rep2": ROOT / "evals/s100_factlevel_smoke_v31_p1map_rep2.yaml",
}
EVIDENCE_V5 = ROOT / "config/evidence_coverage_facets_v5.yaml"
CAT017_CARRIER_PREFIX = "b7633e98"
HP002_DOC = "ASD535_TD_T131192es_h"
HP002_WINNER_PREFIX = "339f06e0"
# Hecho hp002#4 tal y como lo declara el gold (texto del artefacto p1map).
HP002_FACT_TEXT = (
    "Gate de seguridad previo al mantenimiento/diagnostico: bloquear o "
    "desconectar el control de incendios, la alerta remota y las zonas de "
    "extincion en la CDI de orden superior (Indicacion que ENCABEZA el "
    "checklist de mantenimiento, para evitar disparos durante los trabajos)"
)
# Términos de adjudicación léxica LOCAL del hecho (derivados del texto del gold
# de arriba, no del corpus): el probe los usa solo para RANKEAR candidatos del
# dump y que la adjudicación final sea humana sobre la cita.
HP002_FACT_TERMS = [
    "bloquear", "bloqueo", "desconectar", "desconecte", "control de incendios",
    "alerta remota", "extincion", "cdi", "orden superior", "mantenimiento",
    "disparo", "disparos", "antes de", "previo",
]
# Términos NÚCLEO: los que discriminan el gate de seguridad PRE-MANTENIMIENTO de
# los demás avisos del manual (p.ej. el de "disparos de prueba" del cap. 7.7.2,
# que comparte casi todo el léxico pero NO es el hecho: no habla de zonas de
# extinción ni de trabajos de mantenimiento).
HP002_FACT_CORE_TERMS = ["extincion", "mantenimiento", "bloquear", "desconectar"]
_SELECT = (
    "id,document_id,extraction_sha256,chunk_index,content,section_title,"
    "product_model,language,source_file,page_number,duplicate_of"
)
_COST = {"embedding_calls": 0, "llm_calls": 0, "judge_calls": 0, "db_writes": 0}


# ───────────────────────── infraestructura read-only ─────────────────────────
def _get_rows(params: dict[str, str]) -> list[dict[str, Any]]:
    """GET-only contra PostgREST (idéntico patrón a structural_neighbor_shadow)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable")
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            f"{SUPABASE_URL.rstrip('/')}/rest/v1/chunks_v2",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("non-list payload")
    return payload


def _rows_by_id(ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    rows = _get_rows(
        {"select": _SELECT, "id": f"in.({','.join(ids)})", "limit": str(len(ids))}
    )
    return {str(row.get("id") or ""): row for row in rows}


def _doc_rows(source_file: str) -> list[dict[str, Any]]:
    return _get_rows(
        {
            "select": _SELECT,
            "source_file": f"eq.{source_file}",
            "order": "chunk_index.asc,id.asc",
            "limit": "500",
        }
    )


def _gold_entry(artifacts: dict[str, Path], qid: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rep, path in artifacts.items():
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        for gold in payload["per_gold"]:
            if gold["qid"] == qid:
                out[rep] = gold
    return out


def _short(chunk_id: Any) -> str:
    return str(chunk_id or "")[:8]


def _retrieve_pool(query: str, top_k: int) -> list[dict[str, Any]]:
    _COST["embedding_calls"] += 1
    return retrieve_chunks(query, top_k=top_k)


def _rebuild_prefix(
    topk_ids: list[str], pool: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Prefijo servido = las filas de `topk_ids` (orden del artefacto).

    Se prefiere la fila del pool FRESCO (lleva los stamps que el retriever
    añade: similarity, revision, etc.); las que el pool de hoy ya no trae se
    hidratan GET-only por id y se marcan en el recibo — la diferencia de stamps
    se declara, no se esconde.
    """
    by_id = {str(row.get("id") or ""): row for row in pool}
    missing = [cid for cid in topk_ids if cid not in by_id]
    hydrated = _rows_by_id(missing) if missing else {}
    prefix: list[dict[str, Any]] = []
    from_pool, from_db, absent = [], [], []
    for cid in topk_ids:
        if cid in by_id:
            prefix.append(copy.deepcopy(by_id[cid]))
            from_pool.append(cid)
        elif cid in hydrated:
            prefix.append(copy.deepcopy(hydrated[cid]))
            from_db.append(cid)
        else:
            absent.append(cid)
    return prefix, {
        "prefix_rows": len(prefix),
        "from_fresh_pool": len(from_pool),
        "hydrated_from_db": [_short(x) for x in from_db],
        "absent": [_short(x) for x in absent],
    }


# ─────────────────────────────── MISIÓN A ────────────────────────────────────
def mission_a(do_retrieve: bool) -> dict[str, Any]:
    golds = _gold_entry(CAT017_ARTIFACTS, "cat017")
    rep1 = golds["rep1"]
    query = rep1["question"]
    result: dict[str, Any] = {
        "query": query,
        "artifact_topk_ids": {rep: g["topk_ids"] for rep, g in golds.items()},
        "artifact_appended": {
            rep: {_short(k): v for k, v in g["appended_lane"].items()}
            for rep, g in golds.items()
        },
    }

    # ── A0: el plan, función PURA ($0, sin DB) ────────────────────────────────
    facet_plan = expand_query_facets(
        query, config_path=dlc.QUERY_CONFIG_V5, multi_match=True
    )
    a0: dict[str, Any] = {
        "expand_query_facets_v5_multi_match": {
            "archetype": facet_plan.get("archetype"),
            "archetypes": facet_plan.get("archetypes"),
            "n_needs": len(facet_plan.get("needs") or []),
            "needs": facet_plan.get("needs"),
        },
        "MULTI_MATCH_MAX": 2,
        "MAX_NEED_GROUPS_MULTI": dlc.MAX_NEED_GROUPS_MULTI,
        "MAX_TSQUERY_CHARS": dlc.MAX_TSQUERY_CHARS,
        "NEED_GROUP_GATE_FLOOR": dlc.NEED_GROUP_GATE_FLOOR,
        "N_FACET": prc.N_FACET,
    }
    # Plan con los scopes REALES que el lane usará (se rellenan en A3); aquí un
    # scope representativo del doc dominante para aislar el efecto del TRIM.
    for label, scopes in (
        ("no_scopes", []),
        (
            "inspire_scope",
            [{"manufacturer": "Notifier", "product_model": "INSPIRE"}],
        ),
    ):
        plan = dlc._build_document_local_query_plan_v5(query, scopes)
        a0[f"plan_{label}"] = (
            None
            if plan is None
            else {
                "archetype": plan["archetype"],
                "archetypes": plan["archetypes"],
                "anchor_terms": plan["anchor_terms"],
                "need_groups": plan["need_groups"],
                "trim": plan["trim"],
                "tsquery_len": len(plan["tsquery"]),
                "tsquery": plan["tsquery"],
                "sha256": plan["sha256"],
            }
        )
    # Grupos ANTES del trim (para ver exactamente qué se pierde y dónde).
    needs = rpc._incremental_needs(query, list(facet_plan.get("needs") or []))
    anchors: list[str] = []
    for token in rpc._tokens(query):
        if token not in anchors:
            anchors.append(token)
    anchors = anchors[: dlc.MAX_ANCHOR_TERMS]
    anchor_set = set(anchors)
    untrimmed: list[list[str]] = []
    for need in needs[: dlc.MAX_NEED_GROUPS_MULTI]:
        group: list[str] = []
        for token in rpc._tokens(need):
            if token not in anchor_set and token not in group:
                group.append(token)
        if group:
            untrimmed.append(group[: dlc.MAX_NEED_TERMS_PER_GROUP])
    a0["need_groups_pre_trim"] = untrimmed
    a0["tsquery_len_pre_trim"] = len(
        dlc._compose_document_local_tsquery(anchors, untrimmed)
    )
    result["A0_plan"] = a0

    if not do_retrieve:
        return result

    # ── A1: pool fresco + prefijo reconstruido ───────────────────────────────
    from src.config import RETRIEVAL_TOP_K

    pool = _retrieve_pool(query, RETRIEVAL_TOP_K)
    prefix, prefix_trace = _rebuild_prefix(list(rep1["topk_ids"]), pool)
    carrier = [
        row
        for row in pool
        if str(row.get("id") or "").startswith(CAT017_CARRIER_PREFIX)
    ]
    result["A1_inputs"] = {
        "retrieval_top_k": RETRIEVAL_TOP_K,
        "pool_n": len(pool),
        "prefix": prefix_trace,
        "carrier_in_fresh_pool": bool(carrier),
        "carrier_pool_rank": next(
            (
                index + 1
                for index, row in enumerate(pool)
                if str(row.get("id") or "").startswith(CAT017_CARRIER_PREFIX)
            ),
            None,
        ),
    }

    # ── A2: el SEAM real -> traza de lanes ───────────────────────────────────
    served, trace = apply_profiled_post_rerank_coverage(
        query, copy.deepcopy(prefix), retrieval_pool=copy.deepcopy(pool)
    )
    result["A2_seam"] = {
        "status": trace.get("status"),
        "appended_ids": [_short(x) for x in (trace.get("appended_ids") or [])],
        "served_n": len(served),
        "lanes": trace.get("lanes"),
    }

    # ── A3: el funnel document-local paso a paso ─────────────────────────────
    a3: dict[str, Any] = {}
    contract_anchors, overflow = prc._document_local_source_contract_rows(query)
    a3["source_contract_anchors"] = {
        "n": len(contract_anchors),
        "overflow": overflow,
        "document_ids": [row.get("document_id") for row in contract_anchors],
    }
    served_structural = [
        row
        for row in served[len(prefix) :]
        if row.get("retrieval_lane") == prc.STRUCTURAL_LANE
    ]
    a3["served_structural_anchors"] = [_short(r.get("id")) for r in served_structural]
    anchor_rows = prc._document_local_anchor_rows(
        prefix, served_structural, contract_anchors
    )
    a3["anchor_rows"] = [
        {
            "id": _short(row.get("id")),
            "route": row.get("document_local_anchor_route"),
            "document_id": row.get("document_id"),
            "source_file": row.get("source_file"),
            "chunk_index": row.get("chunk_index"),
        }
        for row in anchor_rows
    ]
    a3["DOCUMENT_LOCAL_ANCHOR_LIMIT"] = prc.DOCUMENT_LOCAL_ANCHOR_LIMIT
    if anchor_rows:
        scopes, scope_reason = dlc._anchor_scopes(anchor_rows)
        a3["anchor_scopes"] = {"reason": scope_reason, "scopes": scopes}
        if scope_reason == "ok":
            plan = dlc.build_document_local_query_plan(query, scopes)
            a3["real_plan"] = (
                None
                if plan is None
                else {
                    "archetypes": plan["archetypes"],
                    "anchor_terms": plan["anchor_terms"],
                    "need_groups": plan["need_groups"],
                    "trim": plan["trim"],
                    "tsquery": plan["tsquery"],
                    "tsquery_len": len(plan["tsquery"]),
                }
            )
            candidates, authorities, read_trace = dlc.fetch_document_local_candidates(
                query, anchor_rows
            )
            a3["fetch"] = {
                "n_candidates": len(candidates),
                "n_authorities": len(authorities),
                "read_trace_status": read_trace.get("status"),
                "read_trace": {
                    k: v
                    for k, v in read_trace.items()
                    if k
                    not in {"prose_source_card"}
                },
                "candidate_ids": [_short(r.get("id")) for r in candidates],
                "carrier_in_candidates": any(
                    str(r.get("id") or "").startswith(CAT017_CARRIER_PREFIX)
                    for r in candidates
                ),
            }
            if candidates and authorities:
                selected, sel_trace = dlc.select_document_local_coverage(
                    query, candidates, served, authorities
                )
                a3["selector"] = {
                    "status": sel_trace.get("status"),
                    "eligible_rows": sel_trace.get("eligible_rows"),
                    "selected_ids": [_short(x) for x in (sel_trace.get("selected_ids") or [])],
                    "satisfied_ids": [
                        _short(x) for x in (sel_trace.get("satisfied_ids") or [])
                    ],
                    "satisfaction_route": sel_trace.get("satisfaction_route"),
                }
                ranked, ranker_trace = rpc.select_rerank_pool_coverage(
                    query, candidates, [], apply_catalog_scope=False
                )
                a3["ranker"] = {
                    "status": ranker_trace.get("status"),
                    "eligible_rows": ranker_trace.get("eligible_rows"),
                    "ranked_ids": [_short(r.get("id")) for r in ranked],
                    "carrier_rank": next(
                        (
                            index + 1
                            for index, row in enumerate(ranked)
                            if str(row.get("id") or "").startswith(
                                CAT017_CARRIER_PREFIX
                            )
                        ),
                        None,
                    ),
                }
    result["A3_funnel"] = a3

    # ── A4: la vía por-faceta (FACET_COMPLEMENT_BUDGET) sobre el mismo estado ─
    a4: dict[str, Any] = {
        "facet_selection_v2_enabled": prc._facet_selection_v2_enabled(),
        "FACET_COMPLEMENT_BUDGET": prc.FACET_COMPLEMENT_BUDGET,
        "MAX_APPENDED_BY_LANE_document_local": prc.MAX_APPENDED_BY_LANE.get(
            DOCUMENT_LOCAL_LANE
        ),
    }
    facet_lane = [
        lane
        for lane in (trace.get("lanes") or [])
        if isinstance(lane, dict) and lane.get("conduct") == "facet_complement"
    ]
    a4["facet_lane_trace"] = facet_lane

    # Sub-funnel PASO A PASO de la vía por-faceta sobre el MISMO estado real:
    # gate A7 -> orden de grupos -> asignación de candidatos -> construcción de
    # fila -> _attest (clases de servido) -> _attest_facet_complement.
    plan = (a3.get("real_plan") or {}) and dlc.build_document_local_query_plan(
        query, (a3.get("anchor_scopes") or {}).get("scopes") or []
    )
    candidate_pool = []
    if plan is not None and anchor_rows:
        candidate_pool, _auth, _rt = dlc.fetch_document_local_candidates(
            query, anchor_rows
        )
    if plan is not None and candidate_pool:
        need_groups = [list(group) for group in plan.get("need_groups") or []]
        grades = [prc._facet_need_group_grade(served, g) for g in need_groups]
        gate_indices = [
            index
            for index, group in enumerate(need_groups)
            if len(group) >= prc.N_FACET and grades[index] < prc.N_FACET
        ]
        ordered = sorted(gate_indices, key=lambda index: (grades[index], index))
        a4["gate_A7"] = {
            "need_groups": need_groups,
            "grades": grades,
            "gate_indices": gate_indices,
            "ordered_groups": ordered,
            "order_key": "(grade asc, index asc)",
        }
        served_ids = {str(row.get("id") or "") for row in served}
        prefix_ids = {str(row.get("id") or "") for row in prefix}
        buckets: dict[int, list[dict[str, Any]]] = {i: [] for i in ordered}
        carrier_detail: dict[str, Any] = {}
        for candidate in candidate_pool:
            candidate_id = str(candidate.get("id") or "")
            is_carrier = candidate_id.startswith(CAT017_CARRIER_PREFIX)
            if is_carrier:
                carrier_detail["id"] = candidate_id
                carrier_detail["page_number"] = candidate.get("page_number")
                carrier_detail["chunk_index"] = candidate.get("chunk_index")
                carrier_detail["windows_by_group"] = {
                    str(index): prc._facet_best_window(
                        str(candidate.get("content") or ""), need_groups[index]
                    )
                    for index in range(len(need_groups))
                }
                carrier_detail["excluded_as_served_or_prefix"] = (
                    candidate_id in served_ids or candidate_id in prefix_ids
                )
            if (
                not candidate_id
                or candidate_id in served_ids
                or candidate_id in prefix_ids
            ):
                continue
            content = str(candidate.get("content") or "")
            for index in ordered:
                window = prc._facet_best_window(content, need_groups[index])
                if window is not None and window["terms_hit"] >= prc.N_FACET:
                    buckets[index].append(
                        {
                            "id": _short(candidate_id),
                            "terms_hit": window["terms_hit"],
                            "density": window["density"],
                            "chunk_index": prc._facet_chunk_index(candidate),
                        }
                    )
                    if is_carrier:
                        carrier_detail["assigned_group"] = index
                    break
            else:
                if is_carrier:
                    carrier_detail["assigned_group"] = None
        a4["buckets"] = {
            str(index): sorted(
                buckets[index],
                key=lambda item: (-item["terms_hit"], item["density"], item["chunk_index"]),
            )
            for index in ordered
        }
        a4["carrier_detail"] = carrier_detail
        selection, status, sel_grades, _groups = prc._facet_gate_and_select(
            served, prefix, plan, candidate_pool
        )
        a4["gate_and_select"] = {
            "status": status,
            "grades": sel_grades,
            "selected_id": (
                _short(selection["candidate"].get("id")) if selection else None
            ),
            "selected_group_index": selection["group_index"] if selection else None,
            "selected_group_terms": selection["group_terms"] if selection else None,
            "selected_window": selection["window"] if selection else None,
        }
        if selection is not None:
            candidate = selection["candidate"]
            probe_row = dict(candidate)
            a4["selected_candidate_authority_stamps"] = {
                key: candidate.get(key)
                for key in (
                    "document_local_authority_document_id",
                    "document_local_authority_extraction_sha256",
                    "document_local_authority_source_file",
                    "document_local_authority_language",
                    "document_local_authority_revision",
                    "duplicate_of",
                )
            }
            built = prc._facet_complement_row(
                selection, served, plan_sha256=str(plan.get("sha256") or "")
            )
            a4["facet_complement_row_built"] = built is not None
            if built is None:
                # ¿murió en _attest o antes?  Se re-hace el prefijo de la función.
                a4["row_build_death"] = _diagnose_row_build(
                    selection, served, plan
                )
            else:
                a4["attest_facet_complement"] = prc._attest_facet_complement(
                    built, served, plan
                )
        # CONTRAFACTUAL decisivo: si la vía iterase el bucket en vez de abortar
        # en el primer fallo (`bucket[0]` único + return inmediato), ¿serviría
        # ALGUNO?  Se prueba cada candidato del bucket del grupo elegido, en su
        # ORDEN pre-registrado, con las MISMAS funciones.
        counterfactual = []
        by_id_pool = {str(row.get("id") or ""): row for row in candidate_pool}
        for group_index in ordered:
            for item in a4["buckets"].get(str(group_index), []):
                full_id = next(
                    (
                        cid
                        for cid in by_id_pool
                        if cid.startswith(item["id"])
                    ),
                    None,
                )
                if full_id is None:
                    continue
                candidate = by_id_pool[full_id]
                window = prc._facet_best_window(
                    str(candidate.get("content") or ""), need_groups[group_index]
                )
                trial = {
                    "group_index": group_index,
                    "id": item["id"],
                    "terms_hit": item["terms_hit"],
                    "density": item["density"],
                    "chunk_index": item["chunk_index"],
                    "page_number": candidate.get("page_number"),
                }
                built = prc._facet_complement_row(
                    {
                        "group_index": group_index,
                        "group_terms": list(need_groups[group_index]),
                        "candidate": candidate,
                        "window": window,
                    },
                    served,
                    plan_sha256=str(plan.get("sha256") or ""),
                )
                trial["row_built"] = built is not None
                if built is None:
                    trial["diagnosis"] = _diagnose_row_build(
                        {
                            "group_index": group_index,
                            "group_terms": list(need_groups[group_index]),
                            "candidate": candidate,
                            "window": window,
                        },
                        served,
                        plan,
                    )
                else:
                    trial["attest_facet_complement"] = prc._attest_facet_complement(
                        built, served, plan
                    )
                    # Qué vería el GENERADOR si esta fila se sirviese: clase de
                    # servido + el texto exacto (coverage_context_content es la
                    # vista servida, no el content completo).
                    trial["served_class"] = built.get(
                        "post_rerank_coverage_contract"
                    )
                    trial["served_text"] = prc.coverage_context_content(built)[:700]
                counterfactual.append(trial)
        a4["counterfactual_iterate_bucket"] = counterfactual
        a4["counterfactual_verdict"] = (
            "ALGUN candidato serviria"
            if any(
                item.get("row_built") and item.get("attest_facet_complement")
                for item in counterfactual
            )
            else "NINGUN candidato pasa _attest — el fallback no bastaria"
        )
    result["A4_facet_complement"] = a4
    return result


def _diagnose_row_build(
    selection: dict[str, Any], served: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    """¿En qué punto exacto muere `_facet_complement_row`?

    Replica sus pasos (post_rerank_coverage.py:1330-1402) para localizar si el
    None viene de los bounds, de `_attest` (clases de servido) o de la clase de
    fila markdown/prosa.
    """
    candidate = selection["candidate"]
    window = selection["window"]
    candidate_id = str(candidate.get("id") or "")
    content = str(candidate.get("content") or "")
    start, end = int(window["start"]), int(window["end"])
    out: dict[str, Any] = {
        "bounds_ok": bool(
            candidate_id and content and 0 <= start < end <= len(content)
        )
    }
    if not out["bounds_ok"]:
        out["death"] = "bounds_or_identity (post_rerank_coverage.py:1345-1346)"
        return out
    quote = content[start:end]
    row = dict(candidate)
    for key in list(row):
        if key.startswith("rerank_pool_"):
            row.pop(key)
    row.pop("local_semantic_validated", None)
    row.pop("prose_source_cards", None)
    row.update(
        {
            "retrieval_lane": DOCUMENT_LOCAL_LANE,
            "document_local_coverage_validated": True,
            "document_local_coverage_validation": prc.DOCUMENT_LOCAL_VALIDATION,
            "facet_complement_validated": True,
            "coverage_cards": [
                {
                    "candidate_id": candidate_id,
                    "candidate_rank": 1,
                    "start": start,
                    "end": end,
                    "quote": quote,
                    "facet": "facet_complement",
                    "exact_source_span_validated": True,
                }
            ],
        }
    )
    out["markdown_record_cards"] = bool(prc._document_local_markdown_record_cards(row))
    out["prose_source_card_enabled"] = prc._prose_source_card_enabled()
    if not out["markdown_record_cards"] and out["prose_source_card_enabled"]:
        prose = dlc.build_prose_source_cards(row)
        out["prose_source_cards_built"] = len(prose or [])
        if prose:
            row["prose_source_cards"] = prose
    out["has_exact_coverage_receipt"] = bool(
        prc.has_exact_coverage_receipt(row)
    )
    out["authority_identity_ok"] = bool(
        prc._has_document_local_authority_identity(row)
    )
    out["authority_stamp_match"] = {
        "document_id": str(row.get("document_id") or ""),
        "authority_document_id": str(
            row.get("document_local_authority_document_id") or ""
        ),
        "extraction_sha256_eq": str(row.get("extraction_sha256") or "").casefold()
        == str(
            row.get("document_local_authority_extraction_sha256") or ""
        ).casefold(),
        "duplicate_of": row.get("duplicate_of"),
    }
    attested = prc._attest(row)
    out["attest_returned_row"] = attested is not None
    if attested is None:
        out["death"] = "_attest (post_rerank_coverage.py:720-820) — clase de servido"
    else:
        out["death"] = "none (la fila se construye; el fallo está aguas abajo)"
    return out


# ─────────────────────────────── MISIÓN B ────────────────────────────────────
def _fold(text: str) -> str:
    return rpc._fold(text or "")


def _fact_score(content: str) -> dict[str, Any]:
    folded = _fold(content)
    hits = [term for term in HP002_FACT_TERMS if _fold(term) in folded]
    return {"n_hits": len(hits), "hits": hits}


def _fact_score_core(content: str) -> dict[str, Any]:
    folded = _fold(content)
    hits = [term for term in HP002_FACT_CORE_TERMS if _fold(term) in folded]
    return {"n_hits": len(hits), "hits": hits}


def _evidence_v5_groups() -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Need-groups EXISTENTES de `config/evidence_coverage_facets_v5.yaml`.

    El schema declara `archetypes: {id: [{id, terms, ...}]}` — los `terms` SON
    el vocabulario del grupo (no hay que derivarlo de un template).  Se devuelve
    también la cabecera del config (`min_distinct_terms`, `window_chars`) para
    poder declarar las DOS varas: la del gate A7 (`N_FACET`=3, la que pide el
    encargo) y la propia del matcher de evidencia.
    """
    payload = yaml.safe_load(EVIDENCE_V5.read_text(encoding="utf-8"))
    header = {
        key: payload.get(key)
        for key in ("schema", "max_cards", "window_chars", "min_window_chars",
                    "min_distinct_terms")
    }
    out: dict[str, list[dict[str, Any]]] = {}
    for archetype_id, groups in (payload.get("archetypes") or {}).items():
        out[archetype_id] = [
            {
                "id": group.get("id"),
                "terms": list(group.get("terms") or []),
                "required_any": list(group.get("required_any") or []),
            }
            for group in groups
        ]
    return header, out


def mission_b(do_retrieve: bool) -> dict[str, Any]:
    golds = _gold_entry(P1MAP_ARTIFACTS, "hp002")
    rep1 = golds["rep1"]
    query = rep1["question"]
    result: dict[str, Any] = {
        "query": query,
        "fact_text": HP002_FACT_TEXT,
        "artifact": {
            rep: {
                "pool_n": g["pool_n"],
                "topk_ids": [_short(x) for x in g["topk_ids"]],
                "appended": {_short(k): v for k, v in g["appended_lane"].items()},
                "best_pool_rank_fact4": next(
                    (
                        f.get("best_pool_rank")
                        for f in g["facts"]
                        if f["key"].startswith("hp002#4")
                    ),
                    None,
                ),
            }
            for rep, g in golds.items()
        },
    }

    # ── B1: dump del documento + adjudicación léxica local ────────────────────
    doc_rows = _doc_rows(HP002_DOC)
    scored = []
    for row in doc_rows:
        content = str(row.get("content") or "")
        score = _fact_score(content)
        core = _fact_score_core(content)
        scored.append(
            {
                "id": str(row.get("id") or ""),
                "extraction_sha256": str(row.get("extraction_sha256") or "")[:12],
                "chunk_index": row.get("chunk_index"),
                "page_number": row.get("page_number"),
                "section_title": row.get("section_title"),
                "n_hits": score["n_hits"],
                "hits": score["hits"],
                "n_core_hits": core["n_hits"],
                "core_hits": core["hits"],
                "content_head": content[:900],
            }
        )
    # Adjudicación: primero por los términos NÚCLEO del hecho (los que sólo el
    # gate de seguridad pre-mantenimiento porta: extincion + mantenimiento +
    # bloquear/desconectar), después por el conjunto ampliado.
    scored.sort(
        key=lambda item: (-item["n_core_hits"], -item["n_hits"], item["chunk_index"] or 0)
    )
    result["B1_doc_dump"] = {
        "source_file": HP002_DOC,
        "n_chunks": len(doc_rows),
        "n_extractions": len({r.get("extraction_sha256") for r in doc_rows}),
        "adjudication_terms": HP002_FACT_TERMS,
        "adjudication_core_terms": HP002_FACT_CORE_TERMS,
        "top_candidates": scored[:12],
    }
    by_id_all = {str(row.get("id") or ""): row for row in doc_rows}

    # ── B2: atestación por los need-groups EXISTENTES de evidence v5 ─────────
    singleton = scored[0] if scored else None
    if singleton:
        result["B1_doc_dump"]["adjudicated_singleton"] = {
            "id": singleton["id"],
            "page_number": singleton["page_number"],
            "chunk_index": singleton["chunk_index"],
            "section_title": singleton["section_title"],
            "core_hits": singleton["core_hits"],
            "full_content": str(by_id_all[singleton["id"]].get("content") or ""),
            "corroboration": (
                "post_rerank_coverage.py:33-38 (docstring s278 §3) nombra el fallo "
                "hp002:r1 como 'el warning ASD535 p121 quedo en el pool #28 sin "
                "servir' — la MISMA pagina que este chunk, escrita antes y por "
                "otra sesion"
            ),
        }
    b2: dict[str, Any] = {
        "N_FACET": prc.N_FACET,
        "WINDOW_CHARS": prc.FACET_WINDOW_CHARS,
        "singleton_id": singleton["id"] if singleton else None,
    }
    header, archetypes = _evidence_v5_groups()
    b2["evidence_v5_header"] = header
    if singleton:
        content = str(by_id_all[singleton["id"]].get("content") or "")
        table = []
        for archetype, groups in archetypes.items():
            for index, group in enumerate(groups):
                window = prc._facet_best_window(content, group["terms"])
                table.append(
                    {
                        "archetype": archetype,
                        "group_id": group["id"],
                        "group_index": index,
                        "n_terms": len(group["terms"]),
                        "terms": group["terms"],
                        "terms_hit": (window or {}).get("terms_hit", 0),
                        "hits": (window or {}).get("hits", []),
                        "window_bounds": (
                            None
                            if window is None
                            else [window["start"], window["end"]]
                        ),
                        "gate_eligible_group": len(group["terms"]) >= prc.N_FACET,
                        "attests_window_N_FACET_3": bool(
                            window and window["terms_hit"] >= prc.N_FACET
                        ),
                        "meets_min_distinct_terms_2": bool(
                            window
                            and window["terms_hit"]
                            >= (header.get("min_distinct_terms") or 2)
                        ),
                    }
                )
        table.sort(key=lambda item: (-item["terms_hit"], item["archetype"]))
        b2["group_x_term_hits"] = table
        b2["n_groups_attesting_N_FACET_3"] = sum(
            1 for row in table if row["attests_window_N_FACET_3"]
        )
        b2["attesting_groups"] = [
            f"{row['archetype']}/{row['group_id']}"
            for row in table
            if row["attests_window_N_FACET_3"]
        ]
    result["B2_need_group_attestation"] = b2

    # ── B3: funnel de obligation_warning_reserve ─────────────────────────────
    b3: dict[str, Any] = {
        "OBLIGATION_WARNING_RESERVE_BUDGET": prc.OBLIGATION_WARNING_RESERVE_BUDGET,
        "is_procedural_diagnostic_query": rpc._is_procedural_diagnostic_query(query),
        "selector_is_first_match_by_pool_rank": True,
    }
    if singleton:
        content = str(by_id_all[singleton["id"]].get("content") or "")
        span = rpc._warning_span(content)
        b3["singleton_warning_span"] = (
            None
            if span is None
            else {
                "start": span[0],
                "end": span[1],
                "triggers": sorted(set(span[2])),
                "quote": content[span[0] : span[1]][:600],
            }
        )
    winner_rows = [
        row
        for row in doc_rows
        if str(row.get("id") or "").startswith(HP002_WINNER_PREFIX)
    ]
    if winner_rows:
        content = str(winner_rows[0].get("content") or "")
        span = rpc._warning_span(content)
        b3["winner_339f06e0"] = {
            "id": str(winner_rows[0].get("id") or ""),
            "chunk_index": winner_rows[0].get("chunk_index"),
            "page_number": winner_rows[0].get("page_number"),
            "section_title": winner_rows[0].get("section_title"),
            "warning_span": (
                None
                if span is None
                else {
                    "start": span[0],
                    "end": span[1],
                    "triggers": sorted(set(span[2])),
                    "quote": content[span[0] : span[1]][:600],
                }
            ),
        }

    if do_retrieve:
        from src.config import RETRIEVAL_TOP_K

        pool = _retrieve_pool(query, RETRIEVAL_TOP_K)
        prefix, prefix_trace = _rebuild_prefix(list(rep1["topk_ids"]), pool)
        served, trace = apply_profiled_post_rerank_coverage(
            query, copy.deepcopy(prefix), retrieval_pool=copy.deepcopy(pool)
        )
        b3["seam"] = {
            "pool_n": len(pool),
            "prefix": prefix_trace,
            "status": trace.get("status"),
            "appended_ids": [_short(x) for x in (trace.get("appended_ids") or [])],
            "lanes": trace.get("lanes"),
        }
        # El orden EXACTO del pool que ve la reserva + qué filas son candidatas.
        # OJO (corrección): la reserva corre ANTES de anexarse a sí misma —
        # `post_rerank_coverage.py:2043-2046` le pasa `output`, la vista SIN la
        # fila de la reserva.  Usar la vista final marcaría su propio ganador
        # como `already_served` y desplazaría el primer-elegible.
        served_pre_reserve = [
            row
            for row in served
            if row.get("retrieval_lane") != rpc.OBLIGATION_WARNING_LANE
        ]
        served_scopes = {
            str(row.get("source_file") or "")
            for row in served_pre_reserve
            if str(row.get("source_file") or "")
        }
        served_ids = {str(row.get("id") or "") for row in served_pre_reserve}
        b3["served_view_used"] = {
            "rows_final": len(served),
            "rows_pre_reserve": len(served_pre_reserve),
            "note": "la reserva ve la vista SIN su propia fila",
        }
        walk = []
        for pool_rank, row in enumerate(pool[: rpc.POOL_LIMIT]):
            row_id = str(row.get("id") or "")
            source_file = str(row.get("source_file") or "")
            content = str(row.get("content") or "")
            reasons = []
            if not row_id:
                reasons.append("no_id")
            if row_id in served_ids:
                reasons.append("already_served")
            if not source_file:
                reasons.append("no_source_file")
            elif source_file not in served_scopes:
                reasons.append("scope_not_served")
            if not content:
                reasons.append("no_content")
            elif rpc.is_toc_page(f"{row.get('section_title') or ''}\n\n{content}"):
                reasons.append("toc_page")
            span = None if reasons else rpc._warning_span(content)
            if not reasons and span is None:
                reasons.append("no_warning_span")
            walk.append(
                {
                    "pool_rank": pool_rank,
                    "id": _short(row_id),
                    "source_file": source_file,
                    "page_number": row.get("page_number"),
                    "chunk_index": row.get("chunk_index"),
                    "eligible": not reasons,
                    "skip_reasons": reasons,
                }
            )
        b3["reserve_pool_walk"] = walk
        b3["first_eligible"] = next(
            (row for row in walk if row["eligible"]), None
        )
        singleton_short = _short(singleton["id"]) if singleton else None
        b3["singleton_pool_entry"] = next(
            (row for row in walk if row["id"] == singleton_short), None
        )
        rows, reserve_trace = rpc.select_obligation_warning_reserve(
            query, copy.deepcopy(pool), copy.deepcopy(served_pre_reserve)
        )
        b3["reserve_direct_call"] = {
            "status": reserve_trace.get("status"),
            "selected_ids": [_short(x) for x in (reserve_trace.get("selected_ids") or [])],
            "input_pool_rows": reserve_trace.get("input_pool_rows"),
            "served_scope_files": reserve_trace.get("served_scope_files"),
        }
    result["B3_obligation_warning_funnel"] = b3
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission", choices=["A", "B", "AB"], default="AB")
    parser.add_argument(
        "--no-retrieve",
        action="store_true",
        help="solo las partes $0 (sin embedding, sin pool fresco)",
    )
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    do_retrieve = not args.no_retrieve

    receipt: dict[str, Any] = {
        "probe": "s288c_gate_funnel_probe_v1",
        "purpose": (
            "funnel de las 2 puertas content-keyed existentes (paso 2-3 de la "
            "ruta re-adjudicada del duo r2)"
        ),
        "read_only": True,
        "release_profile": COVERAGE_RELEASE_POLICY.safe_snapshot(),
        "demo_flags": DEMO_FLAGS,
        "code_anchors": {
            "MAX_APPENDED": prc.MAX_APPENDED,
            "MAX_APPENDED_PER_LANE": prc.MAX_APPENDED_PER_LANE,
            "MAX_APPENDED_BY_LANE": {
                str(k): v for k, v in prc.MAX_APPENDED_BY_LANE.items()
            },
            "OBLIGATION_WARNING_RESERVE_BUDGET": (
                prc.OBLIGATION_WARNING_RESERVE_BUDGET
            ),
            "FACET_COMPLEMENT_BUDGET": prc.FACET_COMPLEMENT_BUDGET,
            "N_FACET": prc.N_FACET,
            "DOCUMENT_LOCAL_ANCHOR_LIMIT": prc.DOCUMENT_LOCAL_ANCHOR_LIMIT,
            "APPEND_LIMIT_document_local": dlc.APPEND_LIMIT,
            "SOURCE_LIMIT": dlc.SOURCE_LIMIT,
            "CANDIDATE_LIMIT": dlc.CANDIDATE_LIMIT,
        },
    }
    if args.mission in {"A", "AB"}:
        receipt["mission_A_cat017"] = mission_a(do_retrieve)
    if args.mission in {"B", "AB"}:
        receipt["mission_B_hp002"] = mission_b(do_retrieve)
    receipt["cost"] = dict(_COST)

    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"receipt -> {out_path}")
    print(f"cost: {json.dumps(_COST)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
