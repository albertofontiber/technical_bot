from __future__ import annotations

from pathlib import Path

from scripts import s135_representative_chunks_shadow as shadow


def _row(identifier: str, *, context: str | None = "ctx") -> dict:
    return {
        "arm": "baseline_v2",
        "id": identifier,
        "document_id": "00000000-0000-0000-0000-000000000001",
        "extraction_sha256": "a" * 64,
        "manufacturer": "Maker",
        "product_model": "Model",
        "content": "exact content",
        "context": context,
        "section_title": "Title",
        "section_path": "Root > Title",
        "page_number": 1,
    }


def test_context_reuse_requires_one_exact_structural_donor() -> None:
    one = _row("00000000-0000-0000-0000-000000000010")
    donors = shadow.exact_context_donors([one])
    assert donors[shadow.donor_key(one)] == "ctx"
    assert shadow.exact_context_donors([one, {**one, "id": "00000000-0000-0000-0000-000000000011"}]) == {}
    assert shadow.exact_context_donors([{**one, "context": None}]) == {}


def test_candidate_gold_is_exact_content_and_same_extraction() -> None:
    candidate = [
        {**_row("00000000-0000-0000-0000-000000000012"), "arm": "candidate_v3"},
        {
            **_row("00000000-0000-0000-0000-000000000013"),
            "arm": "candidate_v3",
            "content": "near content",
        },
    ]
    cohort = [
        {
            "question_id": "00000000-0000-0000-0000-000000000020",
            "baseline_gold_chunk_id": "00000000-0000-0000-0000-000000000021",
            "gold_extraction_sha256": "a" * 64,
            "gold_content": "exact content",
        }
    ]
    gold, cardinalities = shadow.build_gold_rows(cohort, candidate)
    assert cardinalities == {cohort[0]["question_id"]: 1}
    assert len(gold) == 2
    wrong_extraction = [{**candidate[0], "extraction_sha256": "b" * 64}]
    _, missing = shadow.build_gold_rows(cohort, wrong_extraction)
    assert missing[cohort[0]["question_id"]] == 0


def test_summary_detects_losses_and_uses_preregistered_direction() -> None:
    prereg = {
        "gates": {
            "candidate_gold_mapped": 2,
            "lost_baseline_hits_at_10_max": 0,
            "candidate_recall_at_10_gte_baseline": True,
            "candidate_mrr_at_10_gte_baseline": True,
            "manufacturers_with_net_hit_loss_at_10_max": 0,
        }
    }
    results = [
        {
            "question_id": "q1",
            "manufacturer": "A",
            "product_model": "M",
            "baseline_rank": 1,
            "candidate_rank": 2,
        },
        {
            "question_id": "q2",
            "manufacturer": "A",
            "product_model": "M",
            "baseline_rank": 3,
            "candidate_rank": None,
        },
    ]
    summary, checks = shadow.summarize_results(prereg, results, {"q1": 1, "q2": 1})
    assert summary["lost_baseline_hits_at_10"] == ["q2"]
    assert not checks["lost_baseline_hits_at_10"]
    assert not checks["candidate_recall_at_10_gte_baseline"]
    assert not checks["candidate_mrr_at_10_gte_baseline"]
    assert not checks["manufacturers_with_net_hit_loss_at_10"]


def test_sql_uses_real_weighted_postgres_fts_and_exact_filters(tmp_path: Path) -> None:
    sql = shadow.shadow_sql(
        tmp_path / "chunks.csv",
        tmp_path / "questions.csv",
        tmp_path / "gold.csv",
        "s135_chunks_shadow",
    )
    assert "CREATE TEXT SEARCH CONFIGURATION s135_chunks_shadow.spanish_unaccent" in sql
    assert "setweight(to_tsvector" in sql
    assert "plainto_tsquery" in sql
    assert "c.manufacturer = q.manufacturer" in sql
    assert "c.product_model = q.product_model" in sql
    assert "CROSS JOIN LATERAL" in sql
    assert "FILTER (WHERE g.chunk_id IS NOT NULL)" in sql
    assert "LIMIT 200" in sql
    assert "DROP SCHEMA s135_chunks_shadow CASCADE" in sql
    assert "extensions.vector" not in sql.lower()
    assert "<=>" not in sql


def test_real_shadow_outputs_when_executed() -> None:
    seed1 = shadow.ROOT / "evals/s135_representative_chunks_shadow_seed1_v1.json"
    seed2 = shadow.ROOT / "evals/s135_representative_chunks_shadow_seed2_v1.json"
    if not seed1.exists() or not seed2.exists():
        return
    assert seed1.read_bytes() == seed2.read_bytes()
    payload = shadow.load_json(seed1)
    assert payload["status"] == "GO"
    assert payload["summary"]["questions"] == 24
    assert payload["summary"]["candidate_gold_mapped"] == 24
    assert all(payload["checks"].values())
    assert payload["cost"]["external_usd_ceiling"] == 0
