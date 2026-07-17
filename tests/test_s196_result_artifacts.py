from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.s196_static_transport_canary import normalize_canary, stable_sha


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def _load(name: str):
    return json.loads((EVALS / name).read_text(encoding="utf-8"))


def test_s196_static_transport_compiled_once_and_matches_its_receipts():
    lock = _load("s196_static_transport_canary_execution_lock_v1.json")
    prepaid = _load("s196_static_transport_canary_prepaid_v1.json")
    receipts_path = EVALS / "s196_static_transport_canary_receipts_v1.json"
    receipts = _load(receipts_path.name)
    result = _load("s196_static_transport_canary_result_v1.json")

    assert lock["status"] == "LOCKED_BEFORE_PROVIDER_REQUEST"
    assert lock["provider_requests_completed"] == 0
    assert prepaid["status"] == "IN_PROGRESS_PRE_PAID_CALL"
    assert prepaid["completed_calls"] == 0
    assert receipts["status"] == "COMPLETE"
    assert receipts["completed_calls"] == 1
    assert receipts["provider_accepted_schema"] is True
    assert receipts["sdk_max_retries"] == 0
    assert receipts["anthropic_sdk"] == "0.97.0"
    assert result["status"] == "GO_STATIC_TRANSPORT_COMPILED"
    assert result["provider_schema_compiles"] is True
    assert result["deterministic_transport_validation"] is True
    assert result["validation_error"] is None
    assert result["receipts_sha256"] == hashlib.sha256(
        receipts_path.read_bytes()
    ).hexdigest()

    raw = receipts["receipts"][0]["raw_synthetic_output"]
    assert result["normalized_synthetic_output"] == normalize_canary(json.loads(raw))
    assert receipts["receipts"][0]["raw_text_sha256"] == hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()
    assert receipts["receipts"][0]["validation_error"] is None
    assert receipts["receipts"][0]["response_id"] == (
        "msg_011Cd7jEfzEosL3Vc6YfaQFt"
    )
    assert result["cost"] == {"total_usd": 0.002583, "worst_case_usd": 0.004958}


def test_s196_result_is_self_consistent_and_opens_only_a_separate_s197():
    result = _load("s196_static_transport_canary_result_v1.json")
    body = dict(result)
    result_sha = body.pop("result_sha256")
    assert result_sha == stable_sha(body)
    assert result["decision"] == {
        "same_canary_retry": False,
        "fresh_document_cohort_opened": False,
        "next_action": "AUTHORIZE_SEPARATE_FRESH_S197_AUTHOR_LUNA_COHORT",
        "runtime_integration": False,
        "production": False,
        "official_fact_credit": 0,
        "railway_deploy_gate": False,
    }
    lane = result["chunks_v3_lane"]
    assert lane["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert lane["changed_by_s196"] is False
    assert lane["historical_metrics_duplicated"] is False
    assert "baseline" not in lane

    serialized = json.dumps(result)
    assert "document_id" not in serialized
    assert "chunk_id" not in serialized
    s197 = _load("s197_fresh_source_packet_v1.json")
    assert s197["selection"]["fresh_after_s196"] is True
    assert s197["selection"]["s194_document_overlap"] == 0
    assert s197["selection"]["s195_document_overlap"] == 0
    assert not (EVALS / "s197_author_gold_cohort_v1.json").exists()
