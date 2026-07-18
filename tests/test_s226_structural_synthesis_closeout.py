import json
from pathlib import Path

import yaml

from src.rag.visual_gold import stable_sha


ROOT = Path(__file__).resolve().parents[1]


def _sealed(name: str) -> dict:
    value = json.loads((ROOT / "evals" / name).read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected
    return value


def test_monotonic_candidates_preserve_every_baseline_byte():
    for name in (
        "s222_monotonic_addendum_generation_v1.json",
        "s223_full_context_addendum_generation_v1.json",
    ):
        generation = _sealed(name)
        assert generation["status"] == "COMPLETE_SCORE_NOT_OPENED"
        assert generation["monotonic_prefix_invariant"] is True
        assert all(
            row["candidate_answer"].startswith(row["baseline_answer"])
            for row in generation["items"]
        )


def test_frontier_failures_cannot_be_promoted_to_pass():
    external = _sealed("s218_kidde_external_cohort_result_v1.json")
    assert external["status"] == "HOLD_S218_EXTERNAL_HTTP_520"
    assert external["frontier_calls"] == 0
    assert external["external_error"]["model_response_returned"] is False

    fable_ledger = _sealed("s224_frontier_call_ledger_v1.json")
    assert len(fable_ledger["calls"]) == 1
    call = fable_ledger["calls"][0]
    assert call["provider"] == "fable"
    assert call["model"] == "claude-fable-5"
    assert call["status"] == "max_tokens"
    assert call["raw_output"].startswith(
        '{"reviewer":"claude-fable-5","verdict":"FAIL"'
    )

    sol = _sealed("s225_s223_sol_principal_review_result_v1.json")
    assert sol["status"] == "HOLD_S225_EXTERNAL_OR_INVALID"
    assert sol["frontier_calls"] == 0
    assert "Error code: 520" in sol["reason"]


def test_closeout_keeps_canonical_score_and_runtime_invariants():
    closeout = yaml.safe_load(
        (ROOT / "evals/s226_structural_synthesis_closeout_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert closeout["status"] == "CLOSED_NO_SAFE_CANONICAL_GAIN"
    assert closeout["canonical_scoreboard"] == {
        "denominator": 157,
        "facts_ok": 143,
        "facts_ok_percent": 91.08,
        "synthesis_miss": 12,
        "retrieval_miss": 2,
        "facts_needed_for_98_percent": 11,
        "facts_moved_to_ok": 0,
    }
    assert closeout["invariants"]["chunks_v2"] == "ACTIVE"
    assert closeout["invariants"]["chunks_v3"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert closeout["invariants"]["railway_merge_gate"] is False
    assert closeout["invariants"]["production_default_changed"] is False
