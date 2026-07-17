from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import s135_representative_chunks_shadow_v2 as shadow


EXTRACTION = "a" * 64
QUESTION = "00000000-0000-0000-0000-000000000001"


def test_query_plan_reuses_frozen_production_keyword_planner() -> None:
    planned = shadow.plan_queries(
        [
            {
                "question_id": QUESTION,
                "question": "¿Cómo se ajusta el retardo de alarma del detector?",
            }
        ]
    )
    assert planned[0]["search_keywords"] == ["ajusta", "retardo", "alarma"]
    assert planned[0]["search_query"] == "ajusta OR retardo OR alarma"


def test_unique_raw_interval_maps_an_exact_two_chunk_bundle(tmp_path: Path) -> None:
    record = {
        "sha256": EXTRACTION,
        "result": {
            "pages": [
                {
                    "page": 1,
                    "md": "alpha beta\n\ngamma delta",
                    "images": [],
                }
            ]
        },
    }
    path = tmp_path / f"{EXTRACTION}.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    raw_tokens, intervals = shadow._raw_token_intervals(record)
    assert raw_tokens == ["alpha", "beta", "gamma", "delta"]
    assert len(intervals) == 2
    candidate = [
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "extraction_sha256": EXTRACTION,
            "content": "alpha beta",
            "chunk_index": 0,
            "source_block_start": 0,
            "source_block_end": 0,
        },
        {
            "id": "00000000-0000-0000-0000-000000000011",
            "extraction_sha256": EXTRACTION,
            "content": "gamma delta",
            "chunk_index": 1,
            "source_block_start": 1,
            "source_block_end": 1,
        },
    ]
    cohort = [
        {
            "question_id": QUESTION,
            "baseline_gold_chunk_id": "00000000-0000-0000-0000-000000000012",
            "gold_extraction_sha256": EXTRACTION,
            "gold_content": "alpha beta\n\ngamma delta",
        }
    ]
    gold, mappings = shadow.build_provenance_gold(
        cohort, candidate, {EXTRACTION: path}
    )
    assert len(gold) == 3
    assert mappings[QUESTION]["candidate_bundle_size"] == 2
    assert mappings[QUESTION]["candidate_chunk_indexes"] == [0, 1]


def test_raw_occurrence_or_bundle_token_drift_fails_closed(tmp_path: Path) -> None:
    record = {
        "sha256": EXTRACTION,
        "result": {"pages": [{"page": 1, "md": "alpha beta", "images": []}]},
    }
    path = tmp_path / f"{EXTRACTION}.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    cohort = [
        {
            "question_id": QUESTION,
            "baseline_gold_chunk_id": "00000000-0000-0000-0000-000000000012",
            "gold_extraction_sha256": EXTRACTION,
            "gold_content": "alpha beta",
        }
    ]
    bad = [
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "extraction_sha256": EXTRACTION,
            "content": "alpha changed",
            "chunk_index": 0,
            "source_block_start": 0,
            "source_block_end": 0,
        }
    ]
    with pytest.raises(shadow.base.ShadowFailure, match="bundle drift"):
        shadow.build_provenance_gold(cohort, bad, {EXTRACTION: path})


def test_v2_sql_uses_or_query_and_requires_complete_bundle(tmp_path: Path) -> None:
    sql = shadow.shadow_sql_v2(
        tmp_path / "chunks.csv",
        tmp_path / "questions.csv",
        tmp_path / "gold.csv",
        "s135_chunks_shadow_v2",
    )
    assert "websearch_to_tsquery" in sql
    assert "q.search_query" in sql
    assert "gold_totals" in sql
    assert "count(rg.chunk_id) = gt.required_members" in sql
    assert "max(rg.rank_position)" in sql
    assert "plainto_tsquery" not in sql


def test_real_v2_shadow_outputs_when_executed() -> None:
    seed1 = shadow.ROOT / "evals/s135_representative_chunks_shadow_seed1_v2.json"
    seed2 = shadow.ROOT / "evals/s135_representative_chunks_shadow_seed2_v2.json"
    if not seed1.exists() or not seed2.exists():
        return
    assert seed1.read_bytes() == seed2.read_bytes()
    payload = shadow.base.load_json(seed1)
    assert (payload["status"] == "GO") is all(payload["checks"].values())
    assert payload["summary"]["questions"] == 24
    assert payload["summary"]["candidate_gold_mapped"] == 24
    assert payload["cost"]["external_usd_ceiling"] == 0
