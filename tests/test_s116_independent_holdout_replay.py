from scripts.s116_independent_holdout_replay import decide


def _arm(chunks: int = 100, titled: int = 30) -> dict:
    return {
        "processed_files": 12,
        "errors": [],
        "chunks_total": chunks,
        "titled_chunks": titled,
        "internally_verified_anchors": titled,
        "resolved_full_lineages": titled,
        "chunk_lineage_state_failures": 0,
        "orphan_or_stale_anchor_chunks": 0,
    }


def test_decide_accepts_frozen_non_vacuous_holdout() -> None:
    result = decide(_arm(), _arm(chunks=110), True, [], 5)
    assert result["gate"] == "GO"
    assert result["chunk_increase_percent"] == 10.0


def test_decide_rejects_content_drift_and_vacuous_titles() -> None:
    result = decide(_arm(), _arm(titled=0), True, ["one.json"], 0)
    assert result["gate"] == "NO_GO"
    assert not result["checks"]["zero_content_stream_mismatches"]
    assert not result["checks"]["non_vacuous_documents"]


def test_decide_rejects_identical_arm_errors_and_only_eleven_records() -> None:
    baseline = _arm()
    treatment = _arm()
    baseline["processed_files"] = treatment["processed_files"] = 11
    baseline["errors"] = treatment["errors"] = [{"file": "bad.json", "error_type": "ValueError"}]
    result = decide(baseline, treatment, True, [], 5)
    assert result["gate"] == "NO_GO"
    assert not result["checks"]["all_records_processed"]
    assert not result["checks"]["zero_arm_errors"]
