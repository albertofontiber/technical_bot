#!/usr/bin/env python3
"""Run the frozen S135 v2/v3 representative lexical shadow locally."""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
import subprocess
from typing import Any

import yaml

from src.reingest import chunk_provenance as materializer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s135_representative_chunks_shadow_prereg_v1.yaml"


class ShadowFailure(RuntimeError):
    pass


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.name):
        raw = path.read_bytes()
        digest.update(
            f"{path.name}\0{len(raw)}\0{hashlib.sha256(raw).hexdigest()}\n".encode(
                "utf-8"
            )
        )
    return digest.hexdigest()


def validate_contract(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    if file_sha(root / prereg["design"]["path"]) != prereg["design"]["sha256"]:
        raise ShadowFailure("design drift")
    for name in (
        "heldout",
        "snapshot",
        "document_metadata",
        "candidate_receipt",
        "chunker",
        "materializer",
    ):
        spec = prereg["frozen_inputs"][name]
        if file_sha(root / spec["path"]) != spec["sha256"]:
            raise ShadowFailure(f"frozen input drift: {name}")
    for name in ("psql", "pg_ctl", "postgres"):
        spec = prereg["runtime"][name]
        if file_sha(root / spec["path"]) != spec["sha256"]:
            raise ShadowFailure(f"runtime drift: {name}")


def load_cohort(
    prereg: dict[str, Any], *, root: Path = ROOT
) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    payload = load_json(root / prereg["frozen_inputs"]["heldout"]["path"])
    chosen = payload.get("chosen")
    sources = payload.get("source_rows")
    if not isinstance(chosen, list) or not isinstance(sources, dict):
        raise ShadowFailure("heldout cohort shape drift")
    rows = []
    for item in chosen:
        source = sources.get(item.get("chunk_id"))
        if not isinstance(source, dict):
            raise ShadowFailure("heldout gold source missing")
        if (
            source.get("id") != item.get("chunk_id")
            or source.get("manufacturer") != item.get("manufacturer")
            or source.get("product_model") != item.get("product_model")
            or not isinstance(item.get("question"), str)
            or not item["question"].strip()
        ):
            raise ShadowFailure("heldout identity drift")
        rows.append(
            {
                "question_id": item["chunk_id"],
                "question": item["question"],
                "manufacturer": item["manufacturer"],
                "product_model": item["product_model"],
                "baseline_gold_chunk_id": item["chunk_id"],
                "gold_extraction_sha256": source["extraction_sha256"],
                "gold_content": source["content"],
            }
        )
    counts = collections.Counter(row["manufacturer"] for row in rows)
    expected = prereg["cohort"]
    if (
        len(rows) != expected["questions"]
        or len(counts) != expected["manufacturers"]
        or set(counts.values()) != {expected["questions_per_manufacturer"]}
        or len({row["question_id"] for row in rows}) != len(rows)
    ):
        raise ShadowFailure("heldout cohort cardinality drift")
    pairs = {(row["manufacturer"], row["product_model"]) for row in rows}
    return sorted(rows, key=lambda row: row["question_id"]), pairs


def load_selected_metadata(
    prereg: dict[str, Any], pairs: set[tuple[str, str]], *, root: Path = ROOT
) -> dict[str, dict[str, Any]]:
    spec = prereg["frozen_inputs"]["document_metadata"]
    payload = load_json(root / spec["path"])
    if (
        payload.get("status") != "GO"
        or payload.get("manifests", {}).get("entries_sha256")
        != spec["entries_sha256"]
    ):
        raise ShadowFailure("canonical metadata receipt drift")
    selected = {
        row["document_id"]: row
        for row in payload["entries"]
        if (row["manufacturer"], row["product_model"]) in pairs
    }
    if not selected:
        raise ShadowFailure("representative metadata population is empty")
    return selected


def load_baseline_rows(
    prereg: dict[str, Any],
    selected: dict[str, dict[str, Any]],
    *,
    root: Path = ROOT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = prereg["frozen_inputs"]["snapshot"]
    rows: list[dict[str, Any]] = []
    logical = hashlib.sha256()
    selected_extractions = {
        extraction: document_id
        for document_id, metadata in selected.items()
        for extraction in metadata["extraction_sha256s"]
    }
    with gzip.open(root / spec["path"], "rb") as stream:
        for raw_line in stream:
            logical.update(raw_line)
            row = json.loads(raw_line)
            if (
                row.get("kind") != "chunk"
                or row.get("parent_id") is not None
                or row.get("document_id") not in selected
            ):
                continue
            document_id = row["document_id"]
            extraction = row.get("extraction_sha256")
            if selected_extractions.get(extraction) != document_id:
                raise ShadowFailure("baseline row/extraction binding drift")
            metadata = selected[document_id]
            for field in ("manufacturer", "product_model", "source_file"):
                if row.get(field) != metadata[field]:
                    raise ShadowFailure(f"baseline canonical metadata drift: {field}")
            rows.append(
                {
                    "arm": "baseline_v2",
                    "id": row["id"],
                    "document_id": document_id,
                    "extraction_sha256": extraction,
                    "manufacturer": metadata["manufacturer"],
                    "product_model": metadata["product_model"],
                    "content": row["content"],
                    "context": row.get("context"),
                    "section_title": row.get("section_title"),
                    "section_path": row.get("section_path"),
                    "page_number": row.get("page_number"),
                }
            )
    if logical.hexdigest() != spec["canonical_jsonl_sha256"]:
        raise ShadowFailure("snapshot logical receipt drift")
    if not rows:
        raise ShadowFailure("representative baseline population is empty")
    rows.sort(key=lambda row: (row["extraction_sha256"], row["id"]))
    return rows, {
        "documents": len({row["document_id"] for row in rows}),
        "extractions": len({row["extraction_sha256"] for row in rows}),
        "chunks": len(rows),
    }


def donor_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["extraction_sha256"],
        row["content"],
        row.get("section_title"),
        row.get("section_path"),
        row.get("page_number"),
    )


def exact_context_donors(
    baseline_rows: list[dict[str, Any]],
) -> dict[tuple[Any, ...], str]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in baseline_rows:
        grouped[donor_key(row)].append(row)
    return {
        key: matches[0]["context"]
        for key, matches in grouped.items()
        if len(matches) == 1 and matches[0].get("context") is not None
    }


def validate_raw_store(
    prereg: dict[str, Any], store: Path
) -> dict[str, Path]:
    spec = prereg["frozen_inputs"]["candidate_receipt"]
    if store.name != spec["source_store_slug"] or not store.is_dir():
        raise ShadowFailure("raw store identity drift")
    files = sorted(store.glob("*.json"), key=lambda path: path.name)
    if (
        len(files) != spec["source_records"] + 1
        or store_manifest(files) != spec["source_store_manifest_sha256"]
    ):
        raise ShadowFailure("raw store manifest drift")
    records = {
        path.stem: path
        for path in files
        if len(path.stem) == 64 and all(ch in "0123456789abcdef" for ch in path.stem)
    }
    if len(records) != spec["source_records"]:
        raise ShadowFailure("raw extraction record count drift")
    return records


def materialize_candidate_rows(
    prereg: dict[str, Any],
    selected: dict[str, dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    records: dict[str, Path],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    donors = exact_context_donors(baseline_rows)
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
                raise ShadowFailure(f"selected raw extraction missing: {extraction}")
            raw = path.read_bytes()
            record = json.loads(raw)
            if record.get("sha256") != extraction:
                raise ShadowFailure("raw extraction identity drift")
            materialized = materializer.materialize_raw_record(
                raw,
                materialization_id=materialization_id,
                chunker_sha256=chunker_sha,
            )
            for row in materialized:
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
                }
                context = donors.get(donor_key(candidate_row))
                if context is not None:
                    candidate_row["context"] = context
                    reused += 1
                candidate.append(candidate_row)
    candidate.sort(key=lambda row: (row["extraction_sha256"], row["id"]))
    if not candidate:
        raise ShadowFailure("representative candidate population is empty")
    return candidate, {
        "documents": len({row["document_id"] for row in candidate}),
        "extractions": len({row["extraction_sha256"] for row in candidate}),
        "chunks": len(candidate),
        "contexts_reused": reused,
        "contexts_absent": len(candidate) - reused,
    }


def build_gold_rows(
    cohort: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, str]], dict[str, int]]:
    by_exact: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for row in candidate_rows:
        by_exact[(row["extraction_sha256"], row["content"])].append(row["id"])
    gold = []
    cardinalities: dict[str, int] = {}
    for row in cohort:
        question_id = row["question_id"]
        gold.append(
            {
                "arm": "baseline_v2",
                "question_id": question_id,
                "chunk_id": row["baseline_gold_chunk_id"],
            }
        )
        matches = sorted(
            by_exact[(row["gold_extraction_sha256"], row["gold_content"])]
        )
        cardinalities[question_id] = len(matches)
        for chunk_id in matches:
            gold.append(
                {
                    "arm": "candidate_v3",
                    "question_id": question_id,
                    "chunk_id": chunk_id,
                }
            )
    return gold, cardinalities


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def shadow_sql(chunks: Path, questions: Path, gold: Path, schema: str) -> str:
    return f"""
\\set ON_ERROR_STOP on
DROP SCHEMA IF EXISTS {schema} CASCADE;
CREATE SCHEMA {schema};
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE TEXT SEARCH CONFIGURATION {schema}.spanish_unaccent
    (COPY = pg_catalog.spanish);
ALTER TEXT SEARCH CONFIGURATION {schema}.spanish_unaccent
    ALTER MAPPING FOR hword, hword_part, word
    WITH public.unaccent, pg_catalog.spanish_stem;
CREATE TABLE {schema}.chunks (
    arm TEXT NOT NULL,
    id UUID NOT NULL,
    document_id UUID NOT NULL,
    extraction_sha256 TEXT NOT NULL,
    manufacturer TEXT NOT NULL,
    product_model TEXT NOT NULL,
    content TEXT NOT NULL,
    context TEXT,
    section_title TEXT,
    section_path TEXT,
    page_number INTEGER,
    search_vector TSVECTOR,
    PRIMARY KEY (arm, id)
);
CREATE TABLE {schema}.questions (
    question_id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    manufacturer TEXT NOT NULL,
    product_model TEXT NOT NULL
);
CREATE TABLE {schema}.gold (
    arm TEXT NOT NULL,
    question_id UUID NOT NULL,
    chunk_id UUID NOT NULL,
    PRIMARY KEY (arm, question_id, chunk_id)
);
\\copy {schema}.chunks (arm,id,document_id,extraction_sha256,manufacturer,product_model,content,context,section_title,section_path,page_number) FROM '{_sql_path(chunks)}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\\copy {schema}.questions (question_id,question,manufacturer,product_model) FROM '{_sql_path(questions)}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\\copy {schema}.gold (arm,question_id,chunk_id) FROM '{_sql_path(gold)}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
UPDATE {schema}.chunks
SET search_vector =
    setweight(to_tsvector('{schema}.spanish_unaccent',
        coalesce(section_path, section_title, '')), 'A') ||
    setweight(to_tsvector('{schema}.spanish_unaccent', coalesce(content, '')), 'B') ||
    setweight(to_tsvector('{schema}.spanish_unaccent', coalesce(context, '')), 'C');
CREATE INDEX ON {schema}.chunks USING gin (search_vector);
WITH arms(arm) AS (
    VALUES ('baseline_v2'::text), ('candidate_v3'::text)
), ranked AS (
    SELECT q.question_id, a.arm, r.id,
           row_number() OVER (
               PARTITION BY q.question_id, a.arm
               ORDER BY r.rank DESC, r.id ASC
           ) AS rank_position
    FROM {schema}.questions AS q
    CROSS JOIN arms AS a
    CROSS JOIN LATERAL (
        SELECT c.id,
               ts_rank(c.search_vector,
                   plainto_tsquery('{schema}.spanish_unaccent', q.question)) AS rank
        FROM {schema}.chunks AS c
        WHERE c.arm = a.arm
          AND c.manufacturer = q.manufacturer
          AND c.product_model = q.product_model
          AND c.search_vector @@ plainto_tsquery(
              '{schema}.spanish_unaccent', q.question)
        ORDER BY rank DESC, c.id ASC
        LIMIT 200
    ) AS r
), gold_ranks AS (
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
)
SELECT jsonb_agg(jsonb_build_object(
    'question_id', q.question_id,
    'manufacturer', q.manufacturer,
    'product_model', q.product_model,
    'baseline_rank', b.gold_rank,
    'candidate_rank', c.gold_rank
) ORDER BY q.question_id)::text
FROM {schema}.questions AS q
LEFT JOIN gold_ranks AS b
  ON b.question_id = q.question_id AND b.arm = 'baseline_v2'
LEFT JOIN gold_ranks AS c
  ON c.question_id = q.question_id AND c.arm = 'candidate_v3';
DROP SCHEMA {schema} CASCADE;
"""


def ensure_postgres(prereg: dict[str, Any], *, root: Path = ROOT) -> None:
    runtime = prereg["runtime"]
    pg_ctl = root / runtime["pg_ctl"]["path"]
    data = root / runtime["data_directory"]
    environment = os.environ.copy()
    environment["PGCLIENTENCODING"] = "UTF8"
    status = subprocess.run(
        [str(pg_ctl), "status", "-D", str(data)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        check=False,
    )
    if status.returncode == 0:
        return
    log = root / "tmp/s135_representative_chunks_shadow/postgres.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    started = subprocess.run(
        [
            str(pg_ctl),
            "start",
            "-w",
            "-D",
            str(data),
            "-l",
            str(log),
            "-o",
            f"-p {runtime['port']}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=environment,
        check=False,
    )
    if started.returncode != 0:
        raise ShadowFailure("disposable PostgreSQL failed to start")


def execute_postgres(
    prereg: dict[str, Any], sql: str, *, root: Path = ROOT
) -> list[dict[str, Any]]:
    ensure_postgres(prereg, root=root)
    runtime = prereg["runtime"]
    environment = os.environ.copy()
    environment["PGCLIENTENCODING"] = "UTF8"
    process = subprocess.run(
        [
            str(root / runtime["psql"]["path"]),
            "-X",
            "-h",
            runtime["host"],
            "-p",
            str(runtime["port"]),
            "-U",
            "postgres",
            "-d",
            runtime["database"],
            "-v",
            "ON_ERROR_STOP=1",
            "-A",
            "-t",
            "-q",
        ],
        input=sql,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        check=False,
    )
    if process.returncode != 0:
        raise ShadowFailure(f"PostgreSQL shadow failed: {process.stderr}")
    json_lines = [line for line in process.stdout.splitlines() if line.startswith("[")]
    if len(json_lines) != 1:
        raise ShadowFailure(f"unexpected PostgreSQL result: {process.stdout}")
    result = json.loads(json_lines[0])
    if not isinstance(result, list):
        raise ShadowFailure("PostgreSQL result is not a list")
    return result


def metric(ranks: list[int | None], cutoff: int) -> tuple[int, Fraction]:
    hits = sum(rank is not None and rank <= cutoff for rank in ranks)
    reciprocal = sum(
        (Fraction(1, rank) if rank is not None and rank <= cutoff else Fraction(0))
        for rank in ranks
    ) / len(ranks)
    return hits, reciprocal


def summarize_results(
    prereg: dict[str, Any],
    results: list[dict[str, Any]],
    cardinalities: dict[str, int],
) -> tuple[dict[str, Any], dict[str, bool]]:
    results = sorted(results, key=lambda row: row["question_id"])
    baseline_ranks = [row.get("baseline_rank") for row in results]
    candidate_ranks = [row.get("candidate_rank") for row in results]
    b5, _ = metric(baseline_ranks, 5)
    c5, _ = metric(candidate_ranks, 5)
    b10, bmrr = metric(baseline_ranks, 10)
    c10, cmrr = metric(candidate_ranks, 10)
    losses = [
        row["question_id"]
        for row in results
        if row.get("baseline_rank") is not None
        and row["baseline_rank"] <= 10
        and (row.get("candidate_rank") is None or row["candidate_rank"] > 10)
    ]
    by_manufacturer: dict[str, dict[str, int]] = {}
    for manufacturer, rows in _group_rows(results, "manufacturer").items():
        by_manufacturer[manufacturer] = {
            "baseline_hits_at_10": sum(
                row.get("baseline_rank") is not None and row["baseline_rank"] <= 10
                for row in rows
            ),
            "candidate_hits_at_10": sum(
                row.get("candidate_rank") is not None and row["candidate_rank"] <= 10
                for row in rows
            ),
        }
    manufacturers_with_loss = sorted(
        manufacturer
        for manufacturer, counts in by_manufacturer.items()
        if counts["candidate_hits_at_10"] < counts["baseline_hits_at_10"]
    )
    expected = prereg["gates"]
    checks = {
        "candidate_gold_mapped": sum(count > 0 for count in cardinalities.values())
        == expected["candidate_gold_mapped"],
        "lost_baseline_hits_at_10": len(losses)
        <= expected["lost_baseline_hits_at_10_max"],
        "candidate_recall_at_10_gte_baseline": c10 >= b10,
        "candidate_mrr_at_10_gte_baseline": cmrr >= bmrr,
        "manufacturers_with_net_hit_loss_at_10": len(manufacturers_with_loss)
        <= expected["manufacturers_with_net_hit_loss_at_10_max"],
    }
    summary = {
        "questions": len(results),
        "candidate_gold_mapped": sum(count > 0 for count in cardinalities.values()),
        "candidate_gold_cardinalities": dict(sorted(cardinalities.items())),
        "baseline": {
            "hits_at_5": b5,
            "recall_at_5": round(b5 / len(results), 8),
            "hits_at_10": b10,
            "recall_at_10": round(b10 / len(results), 8),
            "mrr_at_10": round(float(bmrr), 8),
        },
        "candidate": {
            "hits_at_5": c5,
            "recall_at_5": round(c5 / len(results), 8),
            "hits_at_10": c10,
            "recall_at_10": round(c10 / len(results), 8),
            "mrr_at_10": round(float(cmrr), 8),
        },
        "lost_baseline_hits_at_10": losses,
        "manufacturers": dict(sorted(by_manufacturer.items())),
        "manufacturers_with_net_hit_loss_at_10": manufacturers_with_loss,
    }
    return summary, checks


def _group_rows(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return dict(grouped)


def build_payload(
    prereg: dict[str, Any], store: Path, generated: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    validate_contract(prereg, root=root)
    cohort, pairs = load_cohort(prereg, root=root)
    selected = load_selected_metadata(prereg, pairs, root=root)
    baseline, baseline_population = load_baseline_rows(prereg, selected, root=root)
    records = validate_raw_store(prereg, store)
    candidate, candidate_population = materialize_candidate_rows(
        prereg, selected, baseline, records
    )
    gold, cardinalities = build_gold_rows(cohort, candidate)

    chunks_path = generated / "chunks.csv"
    questions_path = generated / "questions.csv"
    gold_path = generated / "gold.csv"
    write_csv(
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
    write_csv(
        questions_path,
        ["question_id", "question", "manufacturer", "product_model"],
        cohort,
    )
    write_csv(gold_path, ["arm", "question_id", "chunk_id"], gold)
    results = execute_postgres(
        prereg,
        shadow_sql(
            chunks_path,
            questions_path,
            gold_path,
            prereg["runtime"]["disposable_schema"],
        ),
        root=root,
    )
    summary, checks = summarize_results(prereg, results, cardinalities)
    checks.update(
        {
            "cohort_cardinality": len(cohort) == prereg["cohort"]["questions"],
            "runtime_results_complete": len(results) == len(cohort),
            "all_selected_extractions_materialized": (
                baseline_population["extractions"] == candidate_population["extractions"]
            ),
        }
    )
    return {
        "instrument": "s135_representative_chunks_shadow_v1",
        "status": "GO" if all(checks.values()) else "NO_GO",
        "claim": "representative_lexical_chunking_shadow_only",
        "dependencies": {
            "design_sha256": prereg["design"]["sha256"],
            "heldout_sha256": prereg["frozen_inputs"]["heldout"]["sha256"],
            "snapshot_sha256": prereg["frozen_inputs"]["snapshot"]["sha256"],
            "document_metadata_sha256": prereg["frozen_inputs"][
                "document_metadata"
            ]["sha256"],
            "chunker_sha256": prereg["frozen_inputs"]["chunker"]["sha256"],
            "materializer_sha256": prereg["frozen_inputs"]["materializer"][
                "sha256"
            ],
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
        "manifests": {
            "cohort_sha256": canonical_sha(
                [{key: value for key, value in row.items() if key != "gold_content"} for row in cohort]
            ),
            "baseline_rows_sha256": canonical_sha(baseline),
            "candidate_rows_sha256": canonical_sha(candidate),
            "gold_sha256": canonical_sha(gold),
            "results_sha256": canonical_sha(results),
        },
        "authorization": prereg["authorization"],
        "cost": prereg["cost"],
        "decision": (
            "GO_TO_VERSIONED_METADATA_SCHEMA_AND_CONTEXT_COST_AUDIT"
            if all(checks.values())
            else "NO_GO_INVESTIGATE_FAILED_FROZEN_GATE"
        ),
    }


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, allow_nan=False, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prereg_path = args.prereg if args.prereg.is_absolute() else ROOT / args.prereg
    output = args.output if args.output.is_absolute() else ROOT / args.output
    prereg = load_yaml(prereg_path)
    allowed = {
        ROOT / value
        for key, value in prereg["execution"].items()
        if key.startswith("seed") and isinstance(value, str)
    }
    if output not in allowed:
        raise ShadowFailure("output is not preregistered")
    generated = ROOT / prereg["execution"]["generated_directory"]
    payload = build_payload(prereg, args.store.resolve(), generated)
    write_payload(output, payload)
    return 0 if payload["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
