#!/usr/bin/env python3
"""Attribute the three frozen S135 v2 top-10 losses without semantic judgement."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

from scripts import s135_representative_chunks_shadow as base
from scripts import s135_representative_chunks_shadow_v2 as shadow


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s136_chunks_v3_loss_attribution_prereg_v1.yaml"


def validate_contract(prereg: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    if base.file_sha(root / prereg["design"]["path"]) != prereg["design"]["sha256"]:
        raise base.ShadowFailure("S136 design drift")
    for name, spec in prereg["frozen_inputs"].items():
        if base.file_sha(root / spec["path"]) != spec["sha256"]:
            raise base.ShadowFailure(f"S136 frozen input drift: {name}")
    s135 = base.load_json(root / prereg["frozen_inputs"]["s135_seed"]["path"])
    if (
        s135.get("status") != "NO_GO"
        or sorted(s135.get("summary", {}).get("lost_baseline_hits_at_10", []))
        != sorted(prereg["expected_losses"])
    ):
        raise base.ShadowFailure("S135 frozen loss set drift")
    return s135


def diagnostic_sql(
    chunks: Path, questions: Path, schema: str, *, max_rank: int
) -> str:
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
    strict_context_donor BOOLEAN NOT NULL,
    search_vector TSVECTOR,
    PRIMARY KEY (arm, id)
);
CREATE TABLE {schema}.questions (
    question_id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    search_query TEXT NOT NULL,
    manufacturer TEXT NOT NULL,
    product_model TEXT NOT NULL
);
\\copy {schema}.chunks (arm,id,document_id,extraction_sha256,manufacturer,product_model,content,context,section_title,section_path,page_number,strict_context_donor) FROM '{str(chunks.resolve()).replace(chr(92), '/').replace(chr(39), chr(39)+chr(39))}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\\copy {schema}.questions (question_id,question,search_query,manufacturer,product_model) FROM '{str(questions.resolve()).replace(chr(92), '/').replace(chr(39), chr(39)+chr(39))}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
UPDATE {schema}.chunks
SET search_vector =
    setweight(to_tsvector('{schema}.spanish_unaccent',
        coalesce(section_path, section_title, '')), 'A') ||
    setweight(to_tsvector('{schema}.spanish_unaccent', coalesce(content, '')), 'B') ||
    setweight(to_tsvector('{schema}.spanish_unaccent', coalesce(context, '')), 'C');
CREATE INDEX ON {schema}.chunks USING gin (search_vector);
WITH scenarios(arm, scenario) AS (
    VALUES
      ('baseline_v2'::text, 'current'::text),
      ('candidate_v3'::text, 'current'::text),
      ('candidate_v3'::text, 'strict_donor_only'::text)
), ranked AS (
    SELECT q.question_id, s.arm, s.scenario, r.id, r.document_id,
           r.strict_context_donor, r.score,
           row_number() OVER (
               PARTITION BY q.question_id, s.arm, s.scenario
               ORDER BY r.score DESC, r.id ASC
           )::integer AS rank_position
    FROM {schema}.questions AS q
    CROSS JOIN scenarios AS s
    CROSS JOIN LATERAL (
        SELECT c.id, c.document_id, c.strict_context_donor,
               ts_rank(c.search_vector,
                   websearch_to_tsquery(
                       '{schema}.spanish_unaccent', q.search_query
                   ))::double precision AS score
        FROM {schema}.chunks AS c
        WHERE c.arm = s.arm
          AND (s.scenario <> 'strict_donor_only' OR c.strict_context_donor)
          AND c.manufacturer = q.manufacturer
          AND c.product_model = q.product_model
          AND c.search_vector @@ websearch_to_tsquery(
              '{schema}.spanish_unaccent', q.search_query)
        ORDER BY score DESC, c.id ASC
        LIMIT {max_rank}
    ) AS r
)
SELECT jsonb_agg(jsonb_build_object(
    'question_id', question_id,
    'arm', arm,
    'scenario', scenario,
    'id', id,
    'document_id', document_id,
    'strict_context_donor', strict_context_donor,
    'score', score,
    'rank_position', rank_position
) ORDER BY question_id, arm, scenario, rank_position)::text
FROM ranked;
DROP SCHEMA {schema} CASCADE;
"""


def _bundle_rank(
    ranked: list[dict[str, Any]], gold_ids: set[str]
) -> tuple[int | None, dict[str, int | None]]:
    positions = {row["id"]: row["rank_position"] for row in ranked}
    members = {identifier: positions.get(identifier) for identifier in sorted(gold_ids)}
    if not gold_ids or any(position is None for position in members.values()):
        return None, members
    return max(position for position in members.values() if position is not None), members


def classify_loss(
    *,
    bundle_size: int,
    current_bundle_rank: int | None,
    current_member_ranks: dict[str, int | None],
    donor_bundle_rank: int | None,
    surface_exact: bool,
    context_exact: bool,
    context_absent: bool,
) -> tuple[str, list[str]]:
    observed = [rank for rank in current_member_ranks.values() if rank is not None]
    best_member = min(observed) if observed else None
    mechanisms = []
    if (
        bundle_size > 1
        and best_member is not None
        and best_member <= 10
        and (current_bundle_rank is None or current_bundle_rank > 10)
    ):
        mechanisms.append("evaluation_bundle_overstrict")
    if (
        bundle_size == 1
        and surface_exact
        and context_exact
        and donor_bundle_rank is not None
        and donor_bundle_rank <= 10
        and (current_bundle_rank is None or current_bundle_rank > 10)
    ):
        mechanisms.append("candidate_population_competition")
    if bundle_size > 1 and context_absent:
        mechanisms.append("gold_context_absent_after_resegmentation")
    if not mechanisms:
        return "unresolved", []
    if len(mechanisms) > 1:
        return "mixed", mechanisms
    return mechanisms[0], mechanisms


def attribute(
    prereg: dict[str, Any],
    s135: dict[str, Any],
    cohort: list[dict[str, Any]],
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
    gold: list[dict[str, str]],
    mappings: dict[str, dict[str, Any]],
    ranked: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    losses = set(prereg["expected_losses"])
    cohort_by_id = {row["question_id"]: row for row in cohort}
    baseline_by_id = {row["id"]: row for row in baseline}
    candidate_by_id = {row["id"]: row for row in candidate}
    gold_by: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for row in gold:
        gold_by[(row["question_id"], row["arm"])].add(row["chunk_id"])
    ranked_by: dict[tuple[str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in ranked:
        ranked_by[(row["question_id"], row["arm"], row["scenario"])].append(row)
    output = []
    for question_id in sorted(losses):
        baseline_gold_ids = gold_by[(question_id, "baseline_v2")]
        candidate_gold_ids = gold_by[(question_id, "candidate_v3")]
        current_baseline = ranked_by[(question_id, "baseline_v2", "current")]
        current_candidate = ranked_by[(question_id, "candidate_v3", "current")]
        donor_candidate = ranked_by[(question_id, "candidate_v3", "strict_donor_only")]
        baseline_rank, baseline_members = _bundle_rank(current_baseline, baseline_gold_ids)
        candidate_rank, candidate_members = _bundle_rank(
            current_candidate, candidate_gold_ids
        )
        donor_rank, donor_members = _bundle_rank(donor_candidate, candidate_gold_ids)

        baseline_gold = baseline_by_id[next(iter(baseline_gold_ids))]
        candidate_gold = [candidate_by_id[item] for item in sorted(candidate_gold_ids)]
        candidate_gold.sort(key=lambda row: row["chunk_index"])
        surface_exact = baseline_gold["content"].split() == [
            token for row in candidate_gold for token in row["content"].split()
        ]
        context_absent = any(row.get("context") is None for row in candidate_gold)
        context_exact = (
            len(candidate_gold) == 1
            and baseline_gold.get("context") == candidate_gold[0].get("context")
        )
        classification, mechanisms = classify_loss(
            bundle_size=len(candidate_gold_ids),
            current_bundle_rank=candidate_rank,
            current_member_ranks=candidate_members,
            donor_bundle_rank=donor_rank,
            surface_exact=surface_exact,
            context_exact=context_exact,
            context_absent=context_absent,
        )
        observed_gold_ranks = [
            rank for rank in candidate_members.values() if rank is not None
        ]
        comparison_rank = (
            candidate_rank
            if candidate_rank is not None
            else (max(observed_gold_ranks) if observed_gold_ranks else None)
        )
        gold_documents = {row["document_id"] for row in candidate_gold}
        above = [
            row
            for row in current_candidate
            if comparison_rank is not None and row["rank_position"] < comparison_rank
        ]
        top_limit = prereg["diagnostics"]["top_competitors_reported"]
        top_rows = []
        for row in current_candidate[:top_limit]:
            top_rows.append(
                {
                    "id": row["id"],
                    "rank": row["rank_position"],
                    "score": row["score"],
                    "is_gold_member": row["id"] in candidate_gold_ids,
                    "strict_context_donor": row["strict_context_donor"],
                    "same_document_as_gold": row["document_id"] in gold_documents,
                }
            )
        s135_result = next(
            row for row in s135["question_results"] if row["question_id"] == question_id
        )
        output.append(
            {
                "question_id": question_id,
                "manufacturer": cohort_by_id[question_id]["manufacturer"],
                "product_model": cohort_by_id[question_id]["product_model"],
                "search_keywords": cohort_by_id[question_id]["search_keywords"],
                "s135_baseline_rank": s135_result["baseline_rank"],
                "s135_candidate_rank": s135_result["candidate_rank"],
                "recomputed_baseline_rank": baseline_rank,
                "recomputed_candidate_rank": candidate_rank,
                "strict_donor_only_candidate_rank": donor_rank,
                "baseline_member_ranks": baseline_members,
                "candidate_member_ranks": candidate_members,
                "strict_donor_only_member_ranks": donor_members,
                "candidate_bundle_size": len(candidate_gold_ids),
                "surface_tokens_exact": surface_exact,
                "single_member_context_exact": context_exact,
                "candidate_gold_context_absent": context_absent,
                "competitors_above_comparison_rank": {
                    "comparison_rank": comparison_rank,
                    "total": len(above),
                    "strict_context_donors": sum(
                        row["strict_context_donor"] for row in above
                    ),
                    "new_or_resegmented": sum(
                        not row["strict_context_donor"] for row in above
                    ),
                    "same_document_as_gold": sum(
                        row["document_id"] in gold_documents for row in above
                    ),
                },
                "classification": classification,
                "mechanisms": mechanisms,
                "top_candidate_rows": top_rows,
                "provenance_mapping": mappings[question_id],
            }
        )
    return output


def build_payload(
    prereg: dict[str, Any], store: Path, generated: Path, *, root: Path = ROOT
) -> dict[str, Any]:
    s135 = validate_contract(prereg, root=root)
    s135_prereg = base.load_yaml(
        root / prereg["frozen_inputs"]["s135_prereg"]["path"]
    )
    shadow.validate_contract(s135_prereg, root=root)
    cohort, pairs = base.load_cohort(s135_prereg, root=root)
    cohort = shadow.plan_queries(cohort)
    selected = base.load_selected_metadata(s135_prereg, pairs, root=root)
    baseline, _ = base.load_baseline_rows(s135_prereg, selected, root=root)
    records = base.validate_raw_store(s135_prereg, store)
    candidate, _ = shadow.materialize_candidate_rows(
        s135_prereg, selected, baseline, records
    )
    gold, mappings = shadow.build_provenance_gold(cohort, candidate, records)
    losses = set(prereg["expected_losses"])
    loss_cohort = [row for row in cohort if row["question_id"] in losses]

    candidate_donor_ids = set(base.exact_context_donors(baseline))
    # The keys above are donor signatures; use actual context presence because the
    # S135 builder assigns context only through that exact unique-donor map.
    chunk_rows = []
    for row in baseline + candidate:
        chunk_rows.append(
            {
                **row,
                "strict_context_donor": (
                    True if row["arm"] == "baseline_v2" else row.get("context") is not None
                ),
            }
        )
    chunks_path = generated / "chunks.csv"
    questions_path = generated / "questions.csv"
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
            "strict_context_donor",
        ],
        chunk_rows,
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
        loss_cohort,
    )
    ranked = base.execute_postgres(
        s135_prereg,
        diagnostic_sql(
            chunks_path,
            questions_path,
            "s136_chunks_loss",
            max_rank=prereg["diagnostics"]["rank_limit"],
        ),
        root=root,
    )
    attributions = attribute(
        prereg, s135, cohort, baseline, candidate, gold, mappings, ranked
    )
    checks = {
        "loss_set_exact": [row["question_id"] for row in attributions]
        == sorted(prereg["expected_losses"]),
        "s135_ranks_reproduced": all(
            row["s135_baseline_rank"] == row["recomputed_baseline_rank"]
            and row["s135_candidate_rank"] == row["recomputed_candidate_rank"]
            for row in attributions
        ),
        "surface_tokens_exact": all(
            row["surface_tokens_exact"] for row in attributions
        ),
        "all_losses_classified": all(
            row["classification"] != "unresolved" for row in attributions
        ),
        "thresholds_unchanged": prereg["diagnostics"]["thresholds_changed"] is False,
    }
    counts = collections.Counter(row["classification"] for row in attributions)
    return {
        "instrument": "s136_chunks_v3_loss_attribution_v1",
        "status": "GO" if all(checks.values()) else "NO_GO",
        "claim": "mechanical_loss_attribution_only",
        "dependencies": {
            "design_sha256": prereg["design"]["sha256"],
            "s135_seed_sha256": prereg["frozen_inputs"]["s135_seed"]["sha256"],
            "s135_gate_sha256": prereg["frozen_inputs"]["s135_gate"]["sha256"],
            "s135_runner_sha256": prereg["frozen_inputs"]["s135_runner"]["sha256"],
        },
        "population": {"losses": len(attributions)},
        "classification_counts": dict(sorted(counts.items())),
        "checks": checks,
        "attributions": attributions,
        "manifests": {
            "attributions_sha256": base.canonical_sha(attributions),
            "ranked_rows_sha256": base.canonical_sha(ranked),
        },
        "authorization": prereg["authorization"],
        "cost": prereg["cost"],
        "decision": (
            "GO_TO_SCOPED_CORRECTION_DECISION"
            if all(checks.values())
            else "NO_GO_REVIEW_ATTRIBUTION_CONTRACT"
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
