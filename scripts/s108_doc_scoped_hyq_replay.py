#!/usr/bin/env python3
"""Read-only replay of a bounded document-scoped HYQ retrieval lane.

The lane uses the existing canonical catalog to bound source documents and the
already-ingested hypothetical questions only as navigation surrogates.  It
always returns real source chunks, never generated HYQ prose.  Frozen facts are
evaluated only after selection and cannot influence ranking.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import psycopg2
import yaml
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from s108_structural_retrieval_replay import (  # noqa: E402
    _content_sha256,
    evaluate_retrieval_facts,
)
from src.rag.catalog_resolver import resolve_query  # noqa: E402
from src.rag.query_facets import expand_query_facets  # noqa: E402

BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
FACETS = ROOT / "config/retrieval_facets_v3.yaml"
OUT = ROOT / "evals/s108_doc_scoped_hyq_replay_v1.json"
SCOPE_LIMIT = 32
ROW_LIMIT = 4000
SOURCE_LIMIT = 2
PARENTS_PER_SOURCE_NEED = 2
PARENT_LIMIT = 6
_STOP = {
    "de", "del", "la", "las", "el", "los", "un", "una", "y", "o", "en",
    "por", "para", "como", "con", "que", "se", "al", "es", "su", "the",
    "and", "for", "of", "to", "a",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tokens(text: str) -> list[str]:
    value = unicodedata.normalize("NFKD", text or "")
    folded = "".join(
        char for char in value if not unicodedata.combining(char)
    ).casefold()
    return [
        token for token in re.findall(r"[a-z0-9]+", folded)
        if len(token) >= 2 and token not in _STOP
    ]


def _rank_bm25(query: str, rows: list[dict[str, Any]]) -> list[tuple[float, dict]]:
    if not rows:
        return []
    query_terms = _tokens(query)
    documents = [_tokens(row.get("question") or "") for row in rows]
    document_frequency = Counter()
    for terms in documents:
        document_frequency.update(set(terms))
    average_length = sum(map(len, documents)) / len(documents) or 1.0
    ranked = []
    for row, terms in zip(rows, documents):
        frequencies = Counter(terms)
        score = 0.0
        for term in query_terms:
            frequency = document_frequency[term]
            if not frequency:
                continue
            inverse = math.log(
                1 + (len(documents) - frequency + 0.5) / (frequency + 0.5)
            )
            term_frequency = frequencies[term]
            denominator = term_frequency + 1.5 * (
                0.25 + 0.75 * len(terms) / average_length
            )
            if denominator:
                score += inverse * (term_frequency * 2.5 / denominator)
        ranked.append((score, row))
    return sorted(
        ranked,
        key=lambda item: (
            -item[0],
            item[1].get("source_file") or "",
            item[1].get("page_number") or 0,
            item[1].get("chunk_id") or "",
            item[1].get("question") or "",
        ),
    )


def select_document_diverse_parents(
    needs: list[str], rows: list[dict[str, Any]]
) -> tuple[list[str], list[dict[str, Any]]]:
    """Select a bounded parent set while preventing one manual from monopolising it."""
    per_need = []
    source_need_best: dict[str, dict[int, float]] = defaultdict(dict)
    for need_index, need in enumerate(needs):
        grouped: dict[str, list[tuple[float, str, dict]]] = defaultdict(list)
        seen: dict[str, set[str]] = defaultdict(set)
        for score, row in _rank_bm25(need, rows):
            source = row.get("source_file") or ""
            parent_id = str(row.get("chunk_id") or "")
            if score <= 0 or not source or not parent_id or parent_id in seen[source]:
                continue
            seen[source].add(parent_id)
            grouped[source].append((score, parent_id, row))
        for source, parents in grouped.items():
            source_need_best[source][need_index] = parents[0][0]
        per_need.append(grouped)
    source_scores = {
        source: sum(scores.values()) for source, scores in source_need_best.items()
    }
    selected_sources = sorted(
        source_scores, key=lambda source: (-source_scores[source], source)
    )[:SOURCE_LIMIT]
    selected = []
    for local_rank in range(PARENTS_PER_SOURCE_NEED):
        for grouped in per_need:
            for source in selected_sources:
                candidates = grouped.get(source) or []
                if local_rank >= len(candidates):
                    continue
                parent_id = candidates[local_rank][1]
                if parent_id not in selected:
                    selected.append(parent_id)
                if len(selected) == PARENT_LIMIT:
                    break
            if len(selected) == PARENT_LIMIT:
                break
        if len(selected) == PARENT_LIMIT:
            break
    diagnostics = [
        {"source_file": source, "score": round(source_scores[source], 6)}
        for source in sorted(source_scores, key=lambda item: (-source_scores[item], item))
    ]
    return selected, diagnostics


def _fetch_hyq(cursor, scope: list[str]) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT chunk_id::text, question, source_file, page_number
          FROM public.chunks_v2_hyq
         WHERE source_file=ANY(%s)
         ORDER BY source_file, page_number, chunk_id, question
        """,
        (scope,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    if len(rows) > ROW_LIMIT:
        raise RuntimeError(f"HYQ scope overflow: {len(rows)} > {ROW_LIMIT}")
    return rows


def _hydrate(cursor, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    cursor.execute(
        """
        SELECT id::text, content, product_model, source_file, page_number,
               document_id::text, extraction_sha256, chunk_index
          FROM public.chunks_v2
         WHERE id=ANY(%s::uuid[])
        """,
        (ids,),
    )
    by_id = {row["id"]: dict(row) for row in cursor.fetchall()}
    return [by_id[value] for value in ids if value in by_id]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    questions = baseline["per_gold"]
    plans = {}
    for question in questions:
        resolution = resolve_query(question["question"])
        scope = sorted(resolution.get("allowed_sources") or [])
        facet_plan = expand_query_facets(question["question"], FACETS)
        plans[question["qid"]] = {
            "scope": scope,
            "scope_overflow": len(scope) > SCOPE_LIMIT,
            "archetype": facet_plan["archetype"],
            "needs": facet_plan["needs"],
        }

    connection = psycopg2.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=20,
        application_name="codex_s108_doc_scoped_hyq_readonly",
    )
    connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
    started = time.perf_counter()
    selections = []
    overflow_qids = []
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SET LOCAL statement_timeout='30s'; SET LOCAL lock_timeout='3s'")
        cursor.execute(
            "SELECT txid_current_snapshot() AS snapshot, "
            "(SELECT count(*) FROM public.chunks_v2) AS chunks, "
            "(SELECT count(*) FROM public.chunks_v2_hyq) AS hyq_rows"
        )
        snapshot = dict(cursor.fetchone())
        for question in questions:
            plan = plans[question["qid"]]
            selected_ids = []
            source_scores = []
            hyq_rows = []
            if plan["scope"] and not plan["scope_overflow"] and plan["archetype"]:
                try:
                    hyq_rows = _fetch_hyq(cursor, plan["scope"])
                    selected_ids, source_scores = select_document_diverse_parents(
                        plan["needs"], hyq_rows
                    )
                except RuntimeError:
                    overflow_qids.append(question["qid"])
            hydrated = _hydrate(cursor, selected_ids)
            selected = [
                {
                    **row,
                    "rank": index,
                    "content_sha256": _content_sha256(row["content"]),
                }
                for index, row in enumerate(hydrated, 1)
            ]
            selections.append(
                {
                    "qid": question["qid"],
                    "scope": plan["scope"],
                    "scope_overflow": plan["scope_overflow"],
                    "archetype": plan["archetype"],
                    "hyq_rows": len(hyq_rows),
                    "source_scores": source_scores,
                    "selected_ids": [row["id"] for row in selected],
                    "selected": selected,
                }
            )
    connection.rollback()
    connection.close()

    retrieval_facts = evaluate_retrieval_facts(questions, selections)
    supported = [
        row for row in retrieval_facts if row["structural_retrieval_precondition"]
    ]
    hp012_key = "hp012#3:4 lazos / 792"
    gate = {
        "queries": len(questions),
        "retrieval_facts": len(retrieval_facts),
        "model_calls": 0,
        "database_writes": 0,
        "scope_overflow_qids": sorted(set(overflow_qids)),
        "selected_source_chunks": sum(len(row["selected"]) for row in selections),
        "retrieval_precondition_keys": sorted(row["key"] for row in supported),
        "hp012_retrieval_precondition": any(row["key"] == hp012_key for row in supported),
        "serving_integration": False,
        "official_ok_uplift": 0,
    }
    gate["interpretation"] = (
        "GO_DOC_SCOPED_HYQ_HP012_RETRIEVAL_NOT_RELEASED"
        if len(questions) == 39
        and len(retrieval_facts) == 7
        and not gate["scope_overflow_qids"]
        and gate["hp012_retrieval_precondition"]
        else "NO_GO_DOC_SCOPED_HYQ_REPLAY"
    )
    payload = {
        "instrument": "s108_doc_scoped_hyq_replay_v1",
        "read_only": True,
        "selection_contract": {
            "target_facts_available_during_selection": False,
            "generated_hyq_prose_served": False,
            "catalog_bounded_scope": True,
            "scope_limit": SCOPE_LIMIT,
            "hyq_row_limit": ROW_LIMIT,
            "source_limit": SOURCE_LIMIT,
            "parent_limit": PARENT_LIMIT,
        },
        "frozen_inputs": {
            "baseline_sha256": _sha256(BASELINE),
            "facets_sha256": _sha256(FACETS),
            "probe_sha256": _sha256(Path(__file__).resolve()),
            "catalog_resolver_sha256": _sha256(
                ROOT / "src/rag/catalog_resolver.py"
            ),
            "query_facets_sha256": _sha256(ROOT / "src/rag/query_facets.py"),
            "audit_locator_sha256": _sha256(ROOT / "scripts/audit_locator.py"),
        },
        "database_snapshot": snapshot,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "gate": gate,
        "retrieval_facts_after_selection": retrieval_facts,
        "selections": selections,
        "limitations": [
            "This is a known dev cohort and a stage gate, not held-out generalization.",
            "Catalog scope preserves source provenance but downstream must still disclose revision and market conflicts.",
            "The lane is not wired into retrieval or generation.",
            "Rerank, synthesis, and protected-OK regression are separate gates.",
        ],
    }
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate["interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
