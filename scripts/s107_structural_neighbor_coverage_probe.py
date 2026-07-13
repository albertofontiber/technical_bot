#!/usr/bin/env python3
"""Read-only full-cohort shadow for same-blob structural neighbor coverage.

The selector sees only the question, the frozen served top-10 and current source
rows within a bounded chunk-index radius.  Target facts and IDs are read only
after selection for evaluation.  No model endpoint or database write is used.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from s107_same_source_reference_probe import _load_pools
from src.rag.structural_neighbor_coverage import (
    DEFAULT_CONFIG,
    select_structural_neighbors,
)
from src.rag.generator import _coverage_obligations_block

QUESTIONS = ROOT / "evals/s106_baseline_query_cache_v1.json.questions_v1.json"
PILOT = ROOT / "evals/s107_bounded_synthesis_pilot_v1.json"
OUT = ROOT / "evals/s107_structural_neighbor_coverage_probe_v1.json"
TARGET_QIDS = ("hp011", "hp014", "hp017")
FETCH_BATCH = 400


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: str(item.get("id") or "")):
        digest.update(
            (
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
                + "\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def _hydrate(cur, ids: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for start in range(0, len(ids), FETCH_BATCH):
        batch = ids[start : start + FETCH_BATCH]
        cur.execute(
            """
            SELECT c.id, c.document_id, c.extraction_sha256, c.chunk_index,
                   c.content, c.section_title, c.product_model, c.language,
                   c.source_file, c.page_number, c.duplicate_of,
                   d.source_pdf_sha256 AS document_source_pdf_sha256
              FROM public.chunks_v2 c
              JOIN public.documents d ON d.id=c.document_id
             WHERE c.id=ANY(%s::uuid[])
            """,
            (batch,),
        )
        rows.update({str(row["id"]): dict(row) for row in cur.fetchall()})
    missing = sorted(set(ids) - set(rows))
    if missing:
        raise RuntimeError(f"missing frozen seed chunks: {missing[:5]}")
    return rows


def _fetch_neighbors(cur, seed_ids: list[str], max_gap: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT n.id, n.document_id, n.extraction_sha256, n.chunk_index,
               n.content, n.section_title, n.product_model, n.language,
               n.source_file, n.page_number, n.duplicate_of,
               d.source_pdf_sha256 AS document_source_pdf_sha256,
               min(abs(n.chunk_index-s.chunk_index))::integer AS observed_gap
          FROM public.chunks_v2 s
          JOIN public.chunks_v2 n
            ON n.document_id=s.document_id
           AND n.extraction_sha256=s.extraction_sha256
           AND n.chunk_index BETWEEN s.chunk_index-%s AND s.chunk_index+%s
          JOIN public.documents d ON d.id=n.document_id
         WHERE s.id=ANY(%s::uuid[])
         GROUP BY n.id, d.source_pdf_sha256
         ORDER BY n.id
        """,
        (max_gap, max_gap, seed_ids),
    )
    return [dict(row) for row in cur.fetchall()]


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in value if not unicodedata.combining(char)).casefold()


_FACT_STOP = {"a", "al", "de", "del", "el", "la", "las", "los", "y", "o", "en"}


def _fact_supported(fact: str, text: str) -> bool:
    """Evaluation-only tolerant token check; never used by the selector."""
    fact_tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", _fold(fact))
        if token not in _FACT_STOP
    ]
    source_tokens = re.findall(r"[a-z0-9]+", _fold(text))
    if not fact_tokens:
        return False
    for token in fact_tokens:
        if token.isdigit():
            if token not in source_tokens:
                return False
            continue
        stem = token[: min(8, len(token))]
        if not any(source.startswith(stem) for source in source_tokens):
            return False
    return True


def _pdf_candidates(source_file: str) -> list[Path]:
    wanted = Path(source_file).stem.casefold()
    return sorted(
        path
        for manual_root in ROOT.glob("Manuales_*")
        if manual_root.is_dir()
        for path in manual_root.rglob("*.pdf")
        if path.stem.casefold() == wanted
    )


def _source_receipt(row: dict[str, Any]) -> dict[str, Any]:
    expected = str(row.get("extraction_sha256") or "").lower()
    observed = []
    for path in _pdf_candidates(str(row.get("source_file") or "")):
        actual = _sha256(path)
        observed.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": actual,
                "matches_extraction_sha256": actual == expected,
            }
        )
    matches = [item for item in observed if item["matches_extraction_sha256"]]
    return {
        "source_file": row.get("source_file"),
        "document_id": str(row.get("document_id") or ""),
        "extraction_sha256": expected,
        "document_source_pdf_sha256": row.get("document_source_pdf_sha256"),
        "local_candidates": observed,
        "matching_local_blobs": matches,
        "verified": bool(matches),
        "registry_status": (
            "legacy_backfill_parent"
            if str(row.get("document_source_pdf_sha256") or "").startswith("backfill:")
            else "registered_parent"
        ),
    }


def _selection_row(
    qid: str,
    question: str,
    selected: list[dict[str, Any]],
    trace: dict[str, Any],
    *,
    seed_origin: str,
) -> dict[str, Any]:
    return {
        "qid": qid,
        "seed_origin": seed_origin,
        "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "selected_ids": [str(item["id"]) for item in selected],
        "selected": [
            {
                "id": str(item["id"]),
                "document_id": str(item["document_id"]),
                "extraction_sha256": item["extraction_sha256"],
                "document_source_pdf_sha256": item[
                    "document_source_pdf_sha256"
                ],
                "source_file": item["source_file"],
                "chunk_index": item["chunk_index"],
                "page_number": item["page_number"],
                "gap": item["structural_neighbor_gap"],
                "rank": item["structural_neighbor_rank"],
                "query_score": item["structural_neighbor_query_score"],
                "facets": item["structural_neighbor_facets"],
                "structured_priority_claims": item[
                    "structured_priority_claims"
                ],
                "coverage_cards": item["coverage_cards"],
                "content": item["content"],
            }
            for item in selected
        ],
        "trace": trace,
    }


def main() -> int:
    load_dotenv(ROOT / ".env", override=True)
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    stamp, pools = _load_pools()
    if set(questions) != set(pools):
        raise RuntimeError("question and frozen pool QIDs differ")
    pilot_payload = json.loads(PILOT.read_text(encoding="utf-8"))
    pilot = {row["qid"]: row for row in pilot_payload["rows"]}

    config = __import__("yaml").safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    max_seeds = config["max_seeds"]
    max_gap = config["max_gap"]
    seed_ids = list(
        dict.fromkeys(
            str(row["id"])
            for qid in sorted(pools)
            for row in pools[qid][:max_seeds]
        )
    )

    connection = psycopg2.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=20,
        application_name="codex_s107_structural_neighbor_readonly",
    )
    connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
    started = time.perf_counter()
    rows = []
    pilot_rows = []
    selected_input_rows: dict[str, dict[str, Any]] = {}
    with connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SET LOCAL statement_timeout='30s'; SET LOCAL lock_timeout='3s'")
        cur.execute(
            "SELECT txid_current_snapshot() AS snapshot, "
            "(SELECT count(*) FROM public.chunks_v2) AS chunks, "
            "(SELECT count(*) FROM public.documents) AS documents"
        )
        database_snapshot = dict(cur.fetchone())
        hydrated = _hydrate(cur, seed_ids)
        for qid in sorted(questions):
            safety_ids = [str(row["id"]) for row in pools[qid][:max_seeds]]
            seeds = [hydrated[chunk_id] for chunk_id in safety_ids]
            candidates = _fetch_neighbors(cur, safety_ids, max_gap)
            for item in [*seeds, *candidates]:
                selected_input_rows[str(item["id"])] = item
            selected, trace = select_structural_neighbors(
                questions[qid], seeds, candidates
            )
            rows.append(
                _selection_row(
                    qid,
                    questions[qid],
                    selected,
                    trace,
                    seed_origin="legacy_frozen_pool_prefix",
                )
            )

        # Efficacy transfer uses the exact post-rerank contexts already paid for
        # and frozen by the earlier synthesis pilot.  Expected facts and target
        # IDs remain unavailable until all three selections have completed.
        pilot_seed_ids = list(
            dict.fromkeys(
                str(chunk_id)
                for qid in TARGET_QIDS
                for chunk_id in pilot[qid]["context_ids"][:max_seeds]
            )
        )
        pilot_hydrated = _hydrate(cur, pilot_seed_ids)
        for qid in TARGET_QIDS:
            safety_ids = [
                str(chunk_id) for chunk_id in pilot[qid]["context_ids"][:max_seeds]
            ]
            seeds = [pilot_hydrated[chunk_id] for chunk_id in safety_ids]
            candidates = _fetch_neighbors(cur, safety_ids, max_gap)
            for item in [*seeds, *candidates]:
                selected_input_rows[str(item["id"])] = item
            selected, trace = select_structural_neighbors(
                questions[qid], seeds, candidates
            )
            pilot_rows.append(
                _selection_row(
                    qid,
                    questions[qid],
                    selected,
                    trace,
                    seed_origin="cached_paid_post_rerank_top10",
                )
            )
    connection.rollback()
    connection.close()
    elapsed = time.perf_counter() - started

    by_qid = {row["qid"]: row for row in pilot_rows}
    target_evaluation = {}
    for qid in TARGET_QIDS:
        label = pilot[qid]
        fact = label["fact"]
        selected = by_qid[qid]["selected"]
        supporting = [
            row for row in selected if _fact_supported(fact, row["content"])
        ]
        receipts = [_source_receipt(row) for row in supporting]
        obligations = []
        seen_obligation_facets = set()
        cards_by_priority = [
            (row, card)
            for numeric_first in (True, False)
            for row in selected
            for card in (row.get("coverage_cards") or [])
            if card["facet"].startswith("structured_numeric:") is numeric_first
        ]
        for row, card in cards_by_priority:
            if card["facet"] in seen_obligation_facets:
                continue
            obligations.append(
                {
                    "candidate_id": row["id"],
                    "fragment_number": row["rank"],
                    "quote": card["quote"],
                    "exact_source_span_validated": True,
                    "facet": card["facet"],
                    "required": True,
                }
            )
            seen_obligation_facets.add(card["facet"])
            if len(obligations) == 4:
                break
        obligation_block = _coverage_obligations_block(obligations, selected)
        target_evaluation[qid] = {
            "evaluation_only_fact": fact,
            "evaluation_only_mapped_target_id": label["candidate_id"],
            "mapped_target_selected": label["candidate_id"]
            in by_qid[qid]["selected_ids"],
            "fact_supported_by_selected_source": bool(supporting),
            "supporting_selected_ids": [row["id"] for row in supporting],
            "supporting_source_receipts": receipts,
            "all_supporting_blobs_verified": bool(receipts)
            and all(receipt["verified"] for receipt in receipts),
            "required_obligations": obligations,
            "required_obligation_block_sha256": hashlib.sha256(
                obligation_block.encode("utf-8")
            ).hexdigest(),
            "required_obligation_block_chars": len(obligation_block),
            "fact_supported_by_required_obligation": any(
                _fact_supported(fact, obligation["quote"])
                for obligation in obligations
            ),
        }

    gate = {
        "queries": len(rows),
        "model_calls": 0,
        "database_writes": 0,
        "full_known_diagnostic_cohort": len(rows) == 39,
        "activated_queries": sum(bool(row["selected_ids"]) for row in rows),
        "selected_anchors": sum(len(row["selected_ids"]) for row in rows),
        "candidate_overflows": sum(row["trace"]["overflow"] for row in rows),
        "pilot_candidate_overflows": sum(
            row["trace"]["overflow"] for row in pilot_rows
        ),
        "all_selected_shadow_only": all(
            row["trace"]["shadow_only"] for row in rows
        ),
        "runtime_coverage_attestations": 0,
        "target_facts_supported": sum(
            item["fact_supported_by_selected_source"]
            for item in target_evaluation.values()
        ),
        "target_source_blobs_verified": sum(
            item["all_supporting_blobs_verified"]
            for item in target_evaluation.values()
        ),
        "target_required_obligations_supported": sum(
            item["fact_supported_by_required_obligation"]
            for item in target_evaluation.values()
        ),
        "serving_integration": False,
        "official_ok_uplift": 0,
    }
    gate["interpretation"] = (
        "GO_LOCAL_SAME_BLOB_NEIGHBOR_COVERAGE_3_OF_3_NOT_RELEASED"
        if gate["full_known_diagnostic_cohort"]
        and gate["candidate_overflows"] == 0
        and gate["pilot_candidate_overflows"] == 0
        and gate["target_facts_supported"] == 3
        and gate["target_source_blobs_verified"] == 3
        and gate["target_required_obligations_supported"] == 3
        and gate["runtime_coverage_attestations"] == 0
        else "NO_GO_LOCAL_NEIGHBOR_COVERAGE"
    )
    payload = {
        "instrument": "s107_structural_neighbor_coverage_probe_v1",
        "read_only": True,
        "selection_contract": {
            "target_ids_or_facts_available_during_selection": False,
            "generated_prose_used": False,
            "query_facets": "config/retrieval_facets_v3.yaml",
            "structured_claims": "config/structured_numeric_claims_v2.yaml",
            "structural_neighbor_config": DEFAULT_CONFIG.relative_to(ROOT).as_posix(),
            "same_document_required": True,
            "same_extraction_sha256_required": True,
            "max_gap": max_gap,
            "max_anchors": config["max_anchors"],
        },
        "frozen_inputs": {
            "questions": QUESTIONS.relative_to(ROOT).as_posix(),
            "baseline_pool_stamp": stamp,
            "baseline_pools": "evals/s103_pools_old.jsonl",
            "pilot_labels_evaluation_only": PILOT.relative_to(ROOT).as_posix(),
            "code_sha256": _sha256(ROOT / "src/rag/structural_neighbor_coverage.py"),
            "config_sha256": _sha256(DEFAULT_CONFIG),
        },
        "database_snapshot": database_snapshot,
        "selected_input_rows": len(selected_input_rows),
        "selected_input_sha256": _canonical_hash(list(selected_input_rows.values())),
        "elapsed_seconds": round(elapsed, 6),
        "gate": gate,
        "target_evaluation_after_selection": target_evaluation,
        "pilot_post_rerank_rows": pilot_rows,
        "rows": rows,
        "upstream_findings": {
            "hp011": "one registry document contains two extraction hashes and two manual revisions",
            "hp017": "the mapped target is one chunk after an independently selected source span that states the expected fact",
            "identity_tables_present": False,
            "identity_tables_note": "migrations 014-016 are files only in the connected database; migration 018 page spans is present",
        },
        "limitations": [
            "This is a known dev diagnostic cohort, not held-out or official uplift.",
            "The 39-query legacy pool prefix measures activation and guard behavior; only the three cached post-rerank contexts measure transfer efficacy.",
            "Local source-blob receipts verify bytes, not semantic document admission.",
            "The component remains absent from serving and never sets coverage_validated.",
            "Answer synthesis and protected-OK regression are not evaluated here.",
        ],
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate["interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
