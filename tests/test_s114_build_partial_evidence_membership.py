import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_s114_selected_receipts_expose_the_causal_boundary():
    data = json.loads(
        (ROOT / "evals/s114_partial_evidence_membership_v1.json").read_text(
            encoding="utf-8"
        )
    )
    rows = {row["qid"]: row for row in data["rows"]}
    assert set(rows) == {"cat017", "hp002", "hp010", "hp013", "hp015"}

    cat017 = {row["role"]: row for row in rows["cat017"]["receipts"]}
    assert cat017["exact_one_licence_per_clip_loop"]["pool_position"] is None
    assert cat017["exact_one_licence_per_clip_loop"]["final_context_position"] is None

    hp002 = {row["role"]: row for row in rows["hp002"]["receipts"]}
    assert hp002["v01_v02_switch_positions"]["pool_position"] is None
    assert hp002["above_below_100_direction"]["final_context_position"] is not None

    hp010 = {row["role"]: row for row in rows["hp010"]["receipts"]}
    assert hp010["autosearch_procedure"]["final_context_position"] is not None
    assert hp010["level3_and_memory_unlock"]["final_context_position"] is None

    hp015 = {row["role"]: row for row in rows["hp015"]["receipts"]}
    assert all(row["final_context_position"] is not None for row in hp015.values())
