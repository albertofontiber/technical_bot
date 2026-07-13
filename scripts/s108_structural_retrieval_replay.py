#!/usr/bin/env python3
"""Reproduce structural-neighbor retrieval evidence from tracked inputs only.

Unlike the historical S107 probe, this replay needs no untracked pool dump,
question cache, or generator helper.  Selection receives only the frozen
question, its served prefix, and same-blob neighbors.  The seven frozen
retrieval facts are inspected only after every selection is complete.

The probe is read-only, makes no model calls, and cannot award official OK.
"""
from __future__ import annotations

import argparse
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
import yaml
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_locator import support_candidate_priority  # noqa: E402
from src.rag.structural_neighbor_coverage import (  # noqa: E402
    DEFAULT_CONFIG,
    select_structural_neighbors,
)

BASELINE = ROOT / "evals/s100_factlevel_full.yaml"
OUT = ROOT / "evals/s108_structural_retrieval_replay_v1.json"
FETCH_BATCH = 400


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _content_sha256(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _same_family(product_model: str, gold_families: list[str]) -> bool:
    model = _fold(product_model)
    if not model:
        return False
    for family in gold_families:
        normalized = _fold(family)
        if normalized and (
            model == normalized
            or (len(normalized) >= 5 and normalized in model)
            or (len(model) >= 5 and model in normalized)
        ):
            return True
    return False


def _hydrate(cursor, ids: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for start in range(0, len(ids), FETCH_BATCH):
        batch = ids[start : start + FETCH_BATCH]
        cursor.execute(
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
        rows.update({str(row["id"]): dict(row) for row in cursor.fetchall()})
    missing = sorted(set(ids) - set(rows))
    if missing:
        raise RuntimeError(f"frozen served chunks unavailable: {missing[:5]}")
    return rows


def _fetch_neighbors(cursor, seed_ids: list[str], max_gap: int) -> list[dict]:
    cursor.execute(
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
    return [dict(row) for row in cursor.fetchall()]


def _selection_receipt(
    qid: str,
    selected: list[dict[str, Any]],
    trace: dict[str, Any],
) -> dict[str, Any]:
    return {
        "qid": qid,
        "selected_ids": [str(row["id"]) for row in selected],
        "selected": [
            {
                "id": str(row["id"]),
                "document_id": str(row["document_id"]),
                "extraction_sha256": row["extraction_sha256"],
                "document_source_pdf_sha256": row[
                    "document_source_pdf_sha256"
                ],
                "source_file": row["source_file"],
                "product_model": row["product_model"],
                "chunk_index": row["chunk_index"],
                "page_number": row["page_number"],
                "gap": row["structural_neighbor_gap"],
                "rank": row["structural_neighbor_rank"],
                "query_score": row["structural_neighbor_query_score"],
                "facets": row["structural_neighbor_facets"],
                "content_sha256": _content_sha256(row["content"]),
                "content": row["content"],
            }
            for row in selected
        ],
        "trace": trace,
    }


def evaluate_retrieval_facts(
    baseline_rows: list[dict[str, Any]],
    selections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evaluate frozen facts after selection; never feed facts into selection."""
    selection_by_qid = {row["qid"]: row for row in selections}
    evaluated = []
    for question in baseline_rows:
        gold_families = list(question.get("gold_families") or [])
        selected = selection_by_qid[question["qid"]]["selected"]
        for fact in question["facts"]:
            if fact.get("clase") != "retrieval-miss":
                continue
            matches = []
            for candidate in selected:
                same_family = _same_family(
                    candidate.get("product_model") or "", gold_families
                )
                priority = support_candidate_priority(
                    fact["valor"],
                    fact.get("texto") or "",
                    candidate.get("content") or "",
                    same_family=same_family,
                )
                if priority is not None:
                    matches.append(
                        {
                            "chunk_id": candidate["id"],
                            "rank": candidate["rank"],
                            "same_family": same_family,
                            "candidate_priority": list(priority),
                            "content_sha256": candidate["content_sha256"],
                        }
                    )
            supported = [row for row in matches if row["same_family"]]
            evaluated.append(
                {
                    "key": fact["key"],
                    "qid": question["qid"],
                    "baseline_class": fact["clase"],
                    "selected_ids": [row["id"] for row in selected],
                    "matching_candidates": matches,
                    "same_family_supporting_ids": [
                        row["chunk_id"] for row in supported
                    ],
                    "structural_retrieval_precondition": bool(supported),
                }
            )
    return evaluated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)

    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    questions = baseline["per_gold"]
    config = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    max_seeds = config["max_seeds"]
    max_gap = config["max_gap"]
    all_seed_ids = list(
        dict.fromkeys(
            str(chunk_id)
            for question in questions
            for chunk_id in question["served_ids"][:max_seeds]
        )
    )

    connection = psycopg2.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=20,
        application_name="codex_s108_structural_retrieval_readonly",
    )
    connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
    started = time.perf_counter()
    selections = []
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SET LOCAL statement_timeout='30s'; SET LOCAL lock_timeout='3s'")
        cursor.execute(
            "SELECT txid_current_snapshot() AS snapshot, "
            "(SELECT count(*) FROM public.chunks_v2) AS chunks, "
            "(SELECT count(*) FROM public.documents) AS documents"
        )
        database_snapshot = dict(cursor.fetchone())
        hydrated = _hydrate(cursor, all_seed_ids)
        for question in questions:
            seed_ids = [str(value) for value in question["served_ids"][:max_seeds]]
            seeds = [hydrated[chunk_id] for chunk_id in seed_ids]
            candidates = _fetch_neighbors(cursor, seed_ids, max_gap)
            selected, trace = select_structural_neighbors(
                question["question"], seeds, candidates
            )
            selections.append(
                _selection_receipt(question["qid"], selected, trace)
            )
    connection.rollback()
    connection.close()

    retrieval_facts = evaluate_retrieval_facts(questions, selections)
    structurally_supported = [
        row for row in retrieval_facts if row["structural_retrieval_precondition"]
    ]
    confirmatory_expected = {
        "hp011#2:05 a 295 seg",
        "hp014#3:35",
        "hp017#1:instruccion de entrada",
    }
    supported_keys = {row["key"] for row in structurally_supported}
    confirmatory_supported = sorted(confirmatory_expected & supported_keys)
    exploratory_supported = sorted(supported_keys - confirmatory_expected)
    gate = {
        "queries": len(questions),
        "retrieval_facts": len(retrieval_facts),
        "model_calls": 0,
        "database_writes": 0,
        "candidate_overflows": sum(
            row["trace"]["overflow"] for row in selections
        ),
        "structural_retrieval_preconditions": len(structurally_supported),
        "confirmatory_expected_keys": sorted(confirmatory_expected),
        "confirmatory_supported_keys": confirmatory_supported,
        "exploratory_supported_keys": exploratory_supported,
        "structural_retrieval_keys": sorted(supported_keys),
        "serving_integration": False,
        "official_ok_uplift": 0,
    }
    gate["interpretation"] = (
        "GO_CONFIRMATORY_STRUCTURAL_RETRIEVAL_3_OF_3_PLUS_DISCOVERY_NOT_RELEASED"
        if len(questions) == 39
        and len(retrieval_facts) == 7
        and gate["candidate_overflows"] == 0
        and set(confirmatory_supported) == confirmatory_expected
        else "NO_GO_STRUCTURAL_RETRIEVAL_REPLAY"
    )
    payload = {
        "instrument": "s108_structural_retrieval_replay_v1",
        "read_only": True,
        "selection_contract": {
            "target_facts_available_during_selection": False,
            "generated_prose_used": False,
            "same_document_required": True,
            "same_extraction_sha256_required": True,
            "max_seeds": max_seeds,
            "max_gap": max_gap,
            "max_anchors": config["max_anchors"],
        },
        "frozen_inputs": {
            "baseline": BASELINE.relative_to(ROOT).as_posix(),
            "baseline_sha256": _sha256(BASELINE),
            "probe_sha256": _sha256(Path(__file__).resolve()),
            "audit_locator_sha256": _sha256(ROOT / "scripts/audit_locator.py"),
            "selector_sha256": _sha256(
                ROOT / "src/rag/structural_neighbor_coverage.py"
            ),
            "config_sha256": _sha256(DEFAULT_CONFIG),
        },
        "database_snapshot": database_snapshot,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "gate": gate,
        "retrieval_facts_after_selection": retrieval_facts,
        "selections": selections,
        "limitations": [
            "The known dev cohort measures stage movement, not held-out generalization.",
            "The selector remains absent from serving and cannot change official OK.",
            "Fact matching is evaluation-only and never influences selection.",
            "Only the three historical S107 targets are confirmatory; any other support is exploratory until independently frozen.",
            "Synthesis and protected-OK regression remain separate downstream gates.",
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
