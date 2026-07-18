from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test_s229_closes_transport_without_semantic_or_fact_claim():
    value = yaml.safe_load((ROOT / "evals/s229_clause_bound_synthesis_transport_closeout_v1.yaml").read_text(encoding="utf-8"))
    assert value["status"] == "CLOSED_INSTRUMENT_FAILURE_NO_RETRY"
    assert value["canonical_scoreboard"]["facts_ok"] == 143
    assert value["canonical_scoreboard"]["facts_moved_to_ok"] == 0
    assert value["interpretation"]["mechanism_verdict"] == "UNMEASURED"
    assert value["s228_non_target_diagnostic"]["score_packet_opened"] is False
    assert value["decision"]["target_probe"] is False

def test_s229_preserves_chunks_and_railway_invariants():
    value = yaml.safe_load((ROOT / "evals/s229_clause_bound_synthesis_transport_closeout_v1.yaml").read_text(encoding="utf-8"))
    assert value["invariants"] == {
        "chunks_v2": "ACTIVE_READ_ONLY",
        "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
        "railway_merge_gate": False,
    }
