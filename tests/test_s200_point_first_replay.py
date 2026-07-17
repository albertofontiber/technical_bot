from __future__ import annotations

import json
from pathlib import Path

from scripts import s198_point_first_scope_gate as engine
from scripts import s200_point_first_replay as replay
from scripts.s165_answer_archetype_ledger import stable_sha


def test_s200_source_satisfies_final_replay_contract() -> None:
    replay.source_contract(json.loads(replay.SOURCE.read_text(encoding="utf-8")))


def test_replay_keeps_s198_semantic_functions() -> None:
    assert replay.engine.point_author_prompt is engine.point_author_prompt
    assert replay.engine.point_screen_schema is engine.point_screen_schema
    assert replay.engine.question_writer_prompt is engine.question_writer_prompt
    assert replay.engine.question_screen_schema is engine.question_screen_schema


def test_binding_is_scoped_and_restorable() -> None:
    originals = replay.bind_engine()
    try:
        assert engine.SOURCE == replay.SOURCE
        assert engine.OUTPUT_PATHS == replay.OUTPUT_PATHS
        assert engine.source_contract is replay.source_contract
        assert engine.chunks_v3_lane is replay.chunks_v3_lane
    finally:
        replay.restore_engine(originals)
    assert engine.SOURCE == originals["SOURCE"]


def test_writer_uses_s200_namespace_reseals_and_lf(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    body = {
        "instrument": "s198_point_first_scope_gate_v2",
        "status": "GO_POINT_FIRST_SCOPE_BOUND_COHORT_SEALED",
        "decision": {
            "next_action": "AUTHORIZE_SEPARATE_S199_PLANNER_PREREGISTRATION",
            "s199_handoff_constraints": {"planner_recall_min": 0.9},
        },
    }
    replay._write_json_atomic_lf(
        path, {**body, "result_sha256": stable_sha(body)}, replace=False
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    sealed = payload.pop("result_sha256")
    assert payload["instrument"] == "s200_point_first_scope_gate_v1"
    assert (
        payload["decision"]["next_action"]
        == "AUTHORIZE_SEPARATE_S201_PLANNER_PREREGISTRATION"
    )
    assert "s201_handoff_constraints" in payload["decision"]
    assert sealed == stable_sha(payload)
    assert b"\r\n" not in path.read_bytes()


def test_frozen_authorization_when_present() -> None:
    if not replay.DEFAULT_PREREG.exists() or not replay.DEFAULT_PERMIT.exists():
        return
    prereg = replay.validate_authorization(replay.DEFAULT_PREREG, replay.DEFAULT_PERMIT)
    assert prereg["execution"]["paid_calls_max"] == 96
    assert prereg["validation"]["eligible_questions_min"] == 12
    assert prereg["validation"]["eligible_manufacturers_min"] == 8
    assert prereg["execution"]["frontier_execution_calls"] == 0
