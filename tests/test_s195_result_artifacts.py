from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def _load(name: str):
    return json.loads((EVALS / name).read_text(encoding="utf-8"))


def test_s195_provider_rejection_is_sealed_before_any_inference_completed():
    result = _load("s195_author_transport_gate_v1.json")
    receipts_path = EVALS / "s195_author_transport_receipts_v1.json"
    receipts = _load(receipts_path.name)

    assert result["status"] == "NO_GO_EXECUTION_CONTRACT_REJECTED"
    assert result["failure"]["provider_error"] == {
        "status_code": 400,
        "request_id": "req_011Cd7fhSviHCGkSfDeitTjp",
        "error_type": "invalid_request_error",
        "error_code": None,
        "message": (
            "Schema is too complex for compilation. Try reducing the number of "
            "tools or simplifying tool schemas."
        ),
    }
    assert result["failure"]["completed_checkpoint_artifacts"] == {
        "evals/s195_author_transport_receipts_v1.json": hashlib.sha256(
            receipts_path.read_bytes()
        ).hexdigest()
    }
    assert receipts["status"] == "IN_PROGRESS_PRE_PAID_CALL"
    assert receipts["sdk_max_retries"] == 0
    assert receipts["completed_calls"] == 0
    assert receipts["receipts"] == []
    assert len(receipts["job_schema_sha256"]) == 14


def test_s195_stops_upstream_and_keeps_chunks_v3_and_railway_out_of_the_gate():
    result = _load("s195_author_transport_gate_v1.json")

    assert result["decision"] == {
        "same_cohort_retry": False,
        "downstream_opened": False,
        "runtime_integration": False,
        "production": False,
        "official_fact_credit": 0,
        "railway_deploy_gate": False,
    }
    assert result["chunks_v3_lane"]["status"] == (
        "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    )
    assert result["chunks_v3_lane"]["changed_by_s195"] is False
    assert result["chunks_v3_lane"]["migration_or_materialization"] is False

    assert not (EVALS / "s195_author_gold_cohort_v1.json").exists()
    assert not (EVALS / "s195_external_semantic_validator_receipts_v1.json").exists()
    assert not (EVALS / "s195_decomposed_evidence_planner_packet_v1.json").exists()
    assert not (EVALS / "s195_target_planner_receipts_v1.json").exists()
