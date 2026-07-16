import json

from scripts.s122_enforced_answer_contract_replay import (
    NOT_MEASURED_QIDS,
    OUTPUT,
    build_report,
)


def test_s122_replay_matches_frozen_population_and_allowlist():
    report = build_report()
    assert report["status"] == "LOCAL_ENFORCED_ANSWER_CONTRACT_GO"
    assert report["counts"]["total_rows"] == 39
    assert report["counts"]["measured_answers"] == 27
    assert report["counts"]["not_measured"] == 12
    assert report["counts"]["unexpected_reconstruction"] == []
    assert report["counts"]["unexpected_fail_closed"] == []
    assert report["counts"]["not_measured_action_leakage"] == []
    assert all(report["checks"].values())


def test_s122_replay_target_actions_and_not_measured_are_exact():
    report = build_report()
    rows = {row["qid"]: row for row in report["rows"]}
    assert rows["hp005"]["action"] == "pass"
    assert rows["hp005"]["answer_byte_identical"] is True
    assert rows["hp009"]["action"] == "source_bound_reconstruction"
    assert rows["hp017"]["action"] == "fail_closed"
    assert {
        qid for qid, row in rows.items() if row["action"] == "not_measured"
    } == set(NOT_MEASURED_QIDS)


def test_s122_replay_safe_outputs_remove_observed_s121_failures():
    report = build_report()
    rows = {row["qid"]: row for row in report["rows"]}
    hp009 = rows["hp009"]["answer_after"]
    assert "Cada circuito" not in hp009
    assert "RFL" in hp009
    assert "circuito cerrado" in hp009
    assert "ZX2e/ZX5e" in hp009
    assert "Inicio Lazo" in hp009 and "Retorno" in hp009

    hp017 = rows["hp017"]["answer_after"]
    assert "procedimiento no completado" in hp017
    assert "cualquier entrada de alarma" in hp017
    assert "Deben eliminarse" in hp017
    assert "No selecciones un numero de menu" in hp017


def test_s122_serialized_replay_matches_in_memory_report():
    report = build_report()
    serialized = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert serialized == json.loads(json.dumps(report, ensure_ascii=False))
