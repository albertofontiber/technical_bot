from __future__ import annotations

import json
from pathlib import Path

from scripts import s198_point_first_scope_gate as engine
from scripts import s199_point_first_replay as replay
from scripts.s165_answer_archetype_ledger import stable_sha


ROOT = Path(__file__).resolve().parents[1]


def test_s199_source_satisfies_replay_contract() -> None:
    source = json.loads(replay.SOURCE.read_text(encoding="utf-8"))
    replay.source_contract(source)


def test_adapter_reuses_s198_semantic_functions_without_wrapping() -> None:
    assert replay.engine.point_author_prompt is engine.point_author_prompt
    assert replay.engine.point_screen_schema is engine.point_screen_schema
    assert replay.engine.question_writer_prompt is engine.question_writer_prompt
    assert replay.engine.question_screen_schema is engine.question_screen_schema
    assert replay.engine.normalize_point_author is engine.normalize_point_author
    assert replay.engine.normalize_question is engine.normalize_question


def test_bind_engine_changes_only_population_paths_contract_and_writers() -> None:
    originals = replay.bind_engine()
    try:
        assert engine.SOURCE == replay.SOURCE
        assert engine.OUTPUT_PATHS == replay.OUTPUT_PATHS
        assert engine.source_contract is replay.source_contract
        assert engine.chunks_v3_lane is replay.chunks_v3_lane
        assert engine.point_author_prompt.__module__ == "scripts.s198_point_first_scope_gate"
        assert engine.question_writer_prompt.__module__ == "scripts.s198_point_first_scope_gate"
    finally:
        replay.restore_engine(originals)


def test_lf_writer_renames_namespace_and_reseals(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    old_body = {
        "instrument": "s198_point_first_scope_gate_v2",
        "status": "GO_POINT_FIRST_SCOPE_BOUND_COHORT_SEALED",
        "decision": {
            "next_action": "AUTHORIZE_SEPARATE_S199_PLANNER_PREREGISTRATION",
            "s199_handoff_constraints": {"planner_recall_min": 0.9},
        },
    }
    replay._write_json_atomic_lf(
        path,
        {**old_body, "result_sha256": stable_sha(old_body)},
        replace=False,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = dict(payload)
    seal = body.pop("result_sha256")
    assert payload["instrument"] == "s199_point_first_scope_gate_v1"
    assert (
        payload["decision"]["next_action"]
        == "AUTHORIZE_SEPARATE_S200_PLANNER_PREREGISTRATION"
    )
    assert "s200_handoff_constraints" in payload["decision"]
    assert seal == stable_sha(body)
    assert b"\r\n" not in path.read_bytes()


def test_frozen_authorization_when_present() -> None:
    if not replay.DEFAULT_PREREG.exists() or not replay.DEFAULT_PERMIT.exists():
        return
    prereg = replay.validate_authorization(replay.DEFAULT_PREREG, replay.DEFAULT_PERMIT)
    assert prereg["execution"]["paid_calls_max"] == 56
    assert prereg["execution"]["frontier_execution_calls"] == 0
    assert prereg["validation"]["eligible_questions_min"] == 12
    assert prereg["validation"]["eligible_manufacturers_min"] == 12
