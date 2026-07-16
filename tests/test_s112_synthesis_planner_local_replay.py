import importlib.util
import json

import yaml


def _module():
    spec = importlib.util.spec_from_file_location(
        "s112_synthesis_planner_local_replay",
        "scripts/s112_synthesis_planner_local_replay.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_latest_answer_precedence():
    module = _module()
    row = {"qid": "q1", "baseline_answer": "baseline"}
    assert module.latest_answer(row, {"q1": "new"}, {"q1": "old"}) == (
        "new",
        "s112_incremental_answer_replay_v1",
    )
    assert module.latest_answer(row, {}, {"q1": "old"}) == (
        "old",
        "s109_bounded_synthesis_runtime_pilot_v1",
    )


def test_replay_is_zero_call_and_does_not_adjudicate_release(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "OUT", tmp_path / "result.json")
    assert module.main() == 0
    payload = json.loads(module.OUT.read_text(encoding="utf-8"))
    assert payload["gate"]["projected_synthesis_facts"] == 15
    assert payload["gate"]["model_calls"] == 0
    assert payload["gate"]["database_calls"] == 0
    assert payload["gate"]["release_decision"].startswith("NO_GO_")
    assert all(
        fact["manual_review_required"] is True
        for row in payload["rows"]
        for fact in row["facts"]
    )


def test_root_cause_audit_partitions_all_projected_synthesis_facts():
    payload = yaml.safe_load(
        open("evals/s112_synthesis_root_cause_audit_v1.yaml", encoding="utf-8")
    )
    assert len(payload["rows"]) == 15
    assert len({row["fact_key"] for row in payload["rows"]}) == 15
    assert payload["summary"]["synthesis_candidates"] == 6
    assert sum(
        row["classification"] == "synthesis_candidate"
        for row in payload["rows"]
    ) == 6
    assert payload["release_decision"].startswith("NO_GO_")


def test_real_sibling_holds_and_conflicting_menu_number_remain_fail_closed():
    module = _module()
    from src.rag.answer_planner import build_answer_plan

    freeze = json.loads(module.FREEZE.read_text(encoding="utf-8"))
    rows = {row["qid"]: row for row in freeze["rows"]}
    assert build_answer_plan(
        rows["cat008"]["question"], rows["cat008"]["served_context"]
    ) == []
    assert build_answer_plan(
        rows["hp011"]["question"], rows["hp011"]["served_context"]
    ) == []
    pearl_plan = build_answer_plan(
        rows["hp017"]["question"], rows["hp017"]["served_context"]
    )
    pearl_kinds = {row.kind for row in pearl_plan}
    assert "cause_effect_menu_path" not in pearl_kinds
    assert pearl_kinds == {
        "cause_effect_rule_behavior",
        "cause_effect_default_rules_precondition",
    }
