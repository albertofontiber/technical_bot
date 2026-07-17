from __future__ import annotations

from pathlib import Path

from scripts import s136_chunks_v3_loss_attribution as audit


def test_bundle_rank_requires_every_member() -> None:
    rows = [
        {"id": "a", "rank_position": 2},
        {"id": "b", "rank_position": 7},
    ]
    rank, members = audit._bundle_rank(rows, {"a", "b"})
    assert rank == 7
    assert members == {"a": 2, "b": 7}
    missing, members = audit._bundle_rank(rows[:1], {"a", "b"})
    assert missing is None
    assert members == {"a": 2, "b": None}


def test_classification_rules_are_mechanical_and_closed() -> None:
    classification, mechanisms = audit.classify_loss(
        bundle_size=1,
        current_bundle_rank=18,
        current_member_ranks={"gold": 18},
        donor_bundle_rank=9,
        surface_exact=True,
        context_exact=True,
        context_absent=False,
    )
    assert classification == "candidate_population_competition"
    assert mechanisms == ["candidate_population_competition"]

    classification, mechanisms = audit.classify_loss(
        bundle_size=2,
        current_bundle_rank=None,
        current_member_ranks={"first": 3, "second": None},
        donor_bundle_rank=None,
        surface_exact=True,
        context_exact=False,
        context_absent=True,
    )
    assert classification == "mixed"
    assert mechanisms == [
        "evaluation_bundle_overstrict",
        "gold_context_absent_after_resegmentation",
    ]


def test_diagnostic_sql_has_frozen_counterfactual_and_real_fts(tmp_path: Path) -> None:
    sql = audit.diagnostic_sql(
        tmp_path / "chunks.csv",
        tmp_path / "questions.csv",
        "s136_chunks_loss",
        max_rank=200,
    )
    assert "strict_donor_only" in sql
    assert "c.strict_context_donor" in sql
    assert "websearch_to_tsquery" in sql
    assert "spanish_unaccent" in sql
    assert "LIMIT 200" in sql
    assert "DROP SCHEMA s136_chunks_loss CASCADE" in sql


def test_real_attribution_outputs_when_executed() -> None:
    seed1 = audit.ROOT / "evals/s136_chunks_v3_loss_attribution_seed1_v1.json"
    seed2 = audit.ROOT / "evals/s136_chunks_v3_loss_attribution_seed2_v1.json"
    if not seed1.exists() or not seed2.exists():
        return
    assert seed1.read_bytes() == seed2.read_bytes()
    payload = audit.base.load_json(seed1)
    assert (payload["status"] == "GO") is all(payload["checks"].values())
    assert payload["population"]["losses"] == 3
    assert all(row["surface_tokens_exact"] for row in payload["attributions"])
    assert payload["cost"]["external_usd_ceiling"] == 0
