#!/usr/bin/env python3
"""Run the S135 v2 provenance-bundle lexical shadow locally."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

from scripts import s135_representative_chunks_shadow as base
from src.rag.retriever import extract_search_keywords
from src.reingest import chunk as chunk_module
from src.reingest import chunk_provenance as materializer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s135_representative_chunks_shadow_prereg_v2.yaml"


def validate_contract(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    for name in ("base", "amendment"):
        spec = prereg["design"][name]
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise base.ShadowFailure(f"design drift: {name}")
    negative = prereg["negative_control"]
    if base.file_sha(root / negative["path"]) != negative["sha256"]:
        raise base.ShadowFailure("negative control drift")
    for name, spec in prereg["frozen_inputs"].items():
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise base.ShadowFailure(f"frozen input drift: {name}")
    for name in ("psql", "pg_ctl", "postgres"):
        spec = prereg["runtime"][name]
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise base.ShadowFailure(f"runtime drift: {name}")


def plan_queries(cohort: list[dict[str, Any]]) -> list[dict[str, Any]]:
    planned = []
    for row in cohort:
        keywords = extract_search_keywords(row["question"])
        if not keywords:
            raise base.ShadowFailure(f"empty frozen keyword plan: {row['question_id']}")
        planned.append(
            {
                **row,
                "search_keywords": keywords,
                "search_query": " OR ".join(keywords),
            }
        )
    return planned


def materialize_candidate_rows(
    prereg: dict[str, Any],
    selected: dict[str, dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    records: dict[str, Path],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    donors = base.exact_context_donors(baseline_rows)
    candidate: list[dict[str, Any]] = []
    materialization_id = prereg["frozen_inputs"]["candidate_receipt"][
        "materialization_id"
    ]
    chunker_sha = prereg["frozen_inputs"]["chunker"]["sha256"]
    reused = 0
    for document_id in sorted(selected):
        metadata = selected[document_id]
        for extraction in metadata["extraction_sha256s"]:
            path = records.get(extraction)
            if path is None:
                raise base.ShadowFailure(f"selected raw extraction missing: {extraction}")
            raw = path.read_bytes()
            record = json.loads(raw)
            if record.get("sha256") != extraction:
                raise base.ShadowFailure("raw extraction identity drift")
            for row in materializer.materialize_raw_record(
                raw,
                materialization_id=materialization_id,
                chunker_sha256=chunker_sha,
            ):
                candidate_row = {
                    "arm": "candidate_v3",
                    "id": row["id"],
                    "document_id": document_id,
                    "extraction_sha256": extraction,
                    "manufacturer": metadata["manufacturer"],
                    "product_model": metadata["product_model"],
                    "content": row["content"],
                    "context": None,
                    "section_title": row.get("section_title"),
                    "section_path": row.get("section_path"),
                    "page_number": row.get("page_number"),
                    "chunk_index": row["chunk_index"],
                    "source_block_start": row["source_block_start"],
                    "source_block_end": row["source_block_end"],
                }
                context = donors.get(base.donor_key(candidate_row))
                if context is not None:
                    candidate_row["context"] = context
                    reused += 1
                candidate.append(candidate_row)
    candidate.sort(key=lambda row: (row["extraction_sha256"], row["chunk_index"]))
    return candidate, {
        "documents": len({row["document_id"] for row in candidate}),
        "extractions": len({row["extraction_sha256"] for row in candidate}),
        "chunks": len(candidate),
        "contexts_reused": reused,
        "contexts_absent": len(candidate) - reused,
    }


def _subsequence_positions(haystack: list[str], needle: list[str]) -> list[int]:
    if not needle or len(needle) > len(haystack):
        return []
    first = needle[0]
    return [
        index
        for index, token in enumerate(haystack[: len(haystack) - len(needle) + 1])
        if token == first and haystack[index : index + len(needle)] == needle
    ]


def _raw_token_intervals(record: dict[str, Any]) -> tuple[list[str], list[tuple[int, int]]]:
    tokens: list[str] = []
    intervals: list[tuple[int, int]] = []
    blocks = chunk_module._flatten(record.get("result", {}).get("pages", []))
    for block in blocks:
        start = len(tokens)
        tokens.extend(block.text.split())
        intervals.append((start, len(tokens) - 1))
    return tokens, intervals


def build_provenance_gold(
    cohort: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    records: dict[str, Path],
) -> tuple[list[dict[str, str]], dict[str, dict[str, Any]]]:
    rows_by_extraction: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in candidate_rows:
        rows_by_extraction[row["extraction_sha256"]].append(row)
    gold: list[dict[str, str]] = []
    mappings: dict[str, dict[str, Any]] = {}
    record_cache: dict[str, tuple[list[str], list[tuple[int, int]]]] = {}
    for row in cohort:
        question_id = row["question_id"]
        extraction = row["gold_extraction_sha256"]
        path = records.get(extraction)
        if path is None:
            raise base.ShadowFailure(f"gold raw extraction missing: {extraction}")
        if extraction not in record_cache:
            record_cache[extraction] = _raw_token_intervals(json.loads(path.read_bytes()))
        raw_tokens, block_intervals = record_cache[extraction]
        gold_tokens = row["gold_content"].split()
        positions = _subsequence_positions(raw_tokens, gold_tokens)
        if len(positions) != 1:
            raise base.ShadowFailure(
                f"gold raw token occurrence is not unique: {question_id}:{len(positions)}"
            )
        token_start = positions[0]
        token_end = token_start + len(gold_tokens) - 1
        target_blocks = [
            index
            for index, (start, end) in enumerate(block_intervals)
            if start <= token_end and end >= token_start
        ]
        if not target_blocks:
            raise base.ShadowFailure(f"gold raw block interval missing: {question_id}")
        bundle = sorted(
            (
                candidate
                for candidate in rows_by_extraction[extraction]
                if candidate["source_block_start"] <= target_blocks[-1]
                and candidate["source_block_end"] >= target_blocks[0]
            ),
            key=lambda candidate: candidate["chunk_index"],
        )
        covered = {
            block
            for candidate in bundle
            for block in range(
                candidate["source_block_start"], candidate["source_block_end"] + 1
            )
            if target_blocks[0] <= block <= target_blocks[-1]
        }
        candidate_tokens = [
            token for candidate in bundle for token in candidate["content"].split()
        ]
        if (
            not bundle
            or covered != set(target_blocks)
            or candidate_tokens != gold_tokens
        ):
            raise base.ShadowFailure(f"candidate provenance bundle drift: {question_id}")
        gold.append(
            {
                "arm": "baseline_v2",
                "question_id": question_id,
                "chunk_id": row["baseline_gold_chunk_id"],
            }
        )
        for candidate in bundle:
            gold.append(
                {
                    "arm": "candidate_v3",
                    "question_id": question_id,
                    "chunk_id": candidate["id"],
                }
            )
        mappings[question_id] = {
            "raw_token_occurrences": len(positions),
            "raw_token_start": token_start,
            "raw_token_end": token_end,
            "source_block_start": target_blocks[0],
            "source_block_end": target_blocks[-1],
            "candidate_bundle_size": len(bundle),
            "candidate_chunk_indexes": [item["chunk_index"] for item in bundle],
            "mapping_mode": "unique_raw_whitespace_token_interval_exact_v3_bundle",
        }
    return gold, mappings


def shadow_sql_v2(chunks: Path, questions: Path, gold: Path, schema: str) -> str:
    sql = base.shadow_sql(chunks, questions, gold, schema)
    start = sql.index(f"CREATE TABLE {schema}.questions")
    end = sql.index(f"CREATE TABLE {schema}.gold")
    sql = (
        sql[:start]
        + f"""CREATE TABLE {schema}.questions (
    question_id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    search_query TEXT NOT NULL,
    manufacturer TEXT NOT NULL,
    product_model TEXT NOT NULL
);
"""
        + sql[end:]
    )
    sql = sql.replace(
        f"\\copy {schema}.questions (question_id,question,manufacturer,product_model)",
        f"\\copy {schema}.questions (question_id,question,search_query,manufacturer,product_model)",
    )
    sql = sql.replace(
        f"plainto_tsquery('{schema}.spanish_unaccent', q.question)",
        f"websearch_to_tsquery('{schema}.spanish_unaccent', q.search_query)",
    )
    sql = sql.replace("plainto_tsquery(", "websearch_to_tsquery(")
    sql = sql.replace(
        f"'{schema}.spanish_unaccent', q.question)",
        f"'{schema}.spanish_unaccent', q.search_query)",
    )
    old = f"""), gold_ranks AS (
    SELECT q.question_id, a.arm,
           min(r.rank_position) FILTER (WHERE g.chunk_id IS NOT NULL)::integer
               AS gold_rank
    FROM {schema}.questions AS q
    CROSS JOIN arms AS a
    LEFT JOIN ranked AS r
      ON r.question_id = q.question_id AND r.arm = a.arm
    LEFT JOIN {schema}.gold AS g
      ON g.question_id = r.question_id
     AND g.arm = r.arm
     AND g.chunk_id = r.id
    GROUP BY q.question_id, a.arm
)"""
    new = f"""), gold_totals AS (
    SELECT arm, question_id, count(*)::integer AS required_members
    FROM {schema}.gold
    GROUP BY arm, question_id
), retrieved_gold AS (
    SELECT r.question_id, r.arm, r.rank_position, g.chunk_id
    FROM ranked AS r
    JOIN {schema}.gold AS g
      ON g.question_id = r.question_id
     AND g.arm = r.arm
     AND g.chunk_id = r.id
), gold_ranks AS (
    SELECT q.question_id, a.arm,
           CASE WHEN count(rg.chunk_id) = gt.required_members
                THEN max(rg.rank_position)::integer ELSE NULL END AS gold_rank
    FROM {schema}.questions AS q
    CROSS JOIN arms AS a
    JOIN gold_totals AS gt
      ON gt.question_id = q.question_id AND gt.arm = a.arm
    LEFT JOIN retrieved_gold AS rg
      ON rg.question_id = q.question_id AND rg.arm = a.arm
    GROUP BY q.question_id, a.arm, gt.required_members
)"""
    if old not in sql:
        raise base.ShadowFailure("base SQL contract drift")
    return sql.replace(old, new)


def summarize_results(
    prereg: dict[str, Any],
    results: list[dict[str, Any]],
    mappings: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, bool]]:
    cardinalities = {
        question_id: mapping["candidate_bundle_size"]
        for question_id, mapping in mappings.items()
    }
    summary, checks = base.summarize_results(prereg, results, cardinalities)
    summary["candidate_gold_bundles"] = cardinalities
    summary.pop("candidate_gold_cardinalities", None)
    return summary, checks


def build_payload(
    prereg: dict[str, Any], store: Path, generated: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    validate_contract(prereg, root=root)
    cohort, pairs = base.load_cohort(prereg, root=root)
    cohort = plan_queries(cohort)
    selected = base.load_selected_metadata(prereg, pairs, root=root)
    baseline, baseline_population = base.load_baseline_rows(
        prereg, selected, root=root
    )
    records = base.validate_raw_store(prereg, store)
    candidate, candidate_population = materialize_candidate_rows(
        prereg, selected, baseline, records
    )
    gold, mappings = build_provenance_gold(cohort, candidate, records)

    chunks_path = generated / "chunks.csv"
    questions_path = generated / "questions.csv"
    gold_path = generated / "gold.csv"
    base.write_csv(
        chunks_path,
        [
            "arm",
            "id",
            "document_id",
            "extraction_sha256",
            "manufacturer",
            "product_model",
            "content",
            "context",
            "section_title",
            "section_path",
            "page_number",
        ],
        baseline + candidate,
    )
    base.write_csv(
        questions_path,
        [
            "question_id",
            "question",
            "search_query",
            "manufacturer",
            "product_model",
        ],
        cohort,
    )
    base.write_csv(gold_path, ["arm", "question_id", "chunk_id"], gold)
    results = base.execute_postgres(
        prereg,
        shadow_sql_v2(
            chunks_path,
            questions_path,
            gold_path,
            prereg["runtime"]["disposable_schema"],
        ),
        root=root,
    )
    summary, checks = summarize_results(prereg, results, mappings)
    checks.update(
        {
            "cohort_cardinality": len(cohort) == prereg["cohort"]["questions"],
            "runtime_results_complete": len(results) == len(cohort),
            "all_selected_extractions_materialized": (
                baseline_population["extractions"] == candidate_population["extractions"]
            ),
            "query_plans_nonempty": all(row["search_keywords"] for row in cohort),
            "provenance_bundles_exact": len(mappings)
            == prereg["gates"]["candidate_gold_mapped"],
        }
    )
    passed = all(checks.values())
    public_cohort = [
        {
            key: value
            for key, value in row.items()
            if key != "gold_content"
        }
        for row in cohort
    ]
    return {
        "instrument": "s135_representative_chunks_shadow_v2",
        "status": "GO" if passed else "NO_GO",
        "claim": "representative_lexical_chunking_shadow_only",
        "dependencies": {
            "design_base_sha256": prereg["design"]["base"]["sha256"],
            "design_amendment_sha256": prereg["design"]["amendment"]["sha256"],
            "negative_control_sha256": prereg["negative_control"]["sha256"],
            "heldout_sha256": prereg["frozen_inputs"]["heldout"]["sha256"],
            "snapshot_sha256": prereg["frozen_inputs"]["snapshot"]["sha256"],
            "document_metadata_sha256": prereg["frozen_inputs"][
                "document_metadata"
            ]["sha256"],
            "chunker_sha256": prereg["frozen_inputs"]["chunker"]["sha256"],
            "materializer_sha256": prereg["frozen_inputs"]["materializer"][
                "sha256"
            ],
            "retrieval_keyword_planner_sha256": prereg["frozen_inputs"][
                "retrieval_keyword_planner"
            ]["sha256"],
            "base_shadow_runner_sha256": prereg["frozen_inputs"][
                "base_shadow_runner"
            ]["sha256"],
            "raw_store_manifest_sha256": prereg["frozen_inputs"][
                "candidate_receipt"
            ]["source_store_manifest_sha256"],
        },
        "population": {
            "metadata_documents": len(selected),
            "pairs": len(pairs),
            "baseline": baseline_population,
            "candidate": candidate_population,
        },
        "summary": summary,
        "checks": checks,
        "question_results": results,
        "query_plans": [
            {
                "question_id": row["question_id"],
                "search_keywords": row["search_keywords"],
                "search_query": row["search_query"],
            }
            for row in cohort
        ],
        "provenance_mappings": dict(sorted(mappings.items())),
        "manifests": {
            "cohort_sha256": base.canonical_sha(public_cohort),
            "baseline_rows_sha256": base.canonical_sha(baseline),
            "candidate_rows_sha256": base.canonical_sha(candidate),
            "gold_sha256": base.canonical_sha(gold),
            "results_sha256": base.canonical_sha(results),
            "provenance_mappings_sha256": base.canonical_sha(mappings),
        },
        "authorization": prereg["authorization"],
        "cost": prereg["cost"],
        "decision": (
            "GO_TO_VERSIONED_METADATA_SCHEMA_AND_CONTEXT_COST_AUDIT"
            if passed
            else "NO_GO_INVESTIGATE_FAILED_FROZEN_GATE"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prereg_path = args.prereg if args.prereg.is_absolute() else ROOT / args.prereg
    output = args.output if args.output.is_absolute() else ROOT / args.output
    prereg = base.load_yaml(prereg_path)
    allowed = {
        ROOT / value
        for key, value in prereg["execution"].items()
        if key.startswith("seed") and isinstance(value, str)
    }
    if output not in allowed:
        raise base.ShadowFailure("output is not preregistered")
    generated = ROOT / prereg["execution"]["generated_directory"]
    payload = build_payload(prereg, args.store.resolve(), generated)
    base.write_payload(output, payload)
    return 0 if payload["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
