import json

from scripts.s124_renderer_presentation_replay import OUTPUT, build_report
from src.rag.answer_obligation_contract import (
    RENDERER_CONTRACT_VERSION,
    build_enforced_answer_cache_identity,
)
from src.rag.answer_planner import (
    SOURCE_BOUND_RENDERER_CURRENT,
    SOURCE_BOUND_RENDERER_S122_V1,
)


def test_s124_renderer_version_is_coherent_with_cache_identity():
    assert SOURCE_BOUND_RENDERER_CURRENT == "source_bound_renderer_s124_v1"
    assert RENDERER_CONTRACT_VERSION == SOURCE_BOUND_RENDERER_CURRENT


def test_s124_renderer_version_changes_enforced_cache_identity():
    kwargs = {
        "generation_request_envelope": {
            "model": "fixed",
            "messages": [{"role": "user", "content": "fixed"}],
        },
        "plan": [{"obligation_id": "fixed"}],
        "conflicts": [],
    }
    legacy = build_enforced_answer_cache_identity(
        **kwargs,
        renderer_contract_version=SOURCE_BOUND_RENDERER_S122_V1,
    )
    current = build_enforced_answer_cache_identity(
        **kwargs,
        renderer_contract_version=SOURCE_BOUND_RENDERER_CURRENT,
    )
    assert legacy["canonical_enforced_answer_contract_sha256"] != current[
        "canonical_enforced_answer_contract_sha256"
    ]
    assert legacy["cache_key_sha256"] != current["cache_key_sha256"]


def test_s124_renderer_presentation_replay_is_go():
    report = build_report()
    assert report["status"] == "LOCAL_RENDERER_PRESENTATION_GO"
    assert all(report["presentation_checks"].values())
    assert report["counts"]["actions"] == {
        "pass": 25,
        "source_bound_reconstruction": 1,
        "fail_closed": 1,
    }


def test_s124_renderer_preserves_actions_and_improves_both_target_answers():
    rows = {row["qid"]: row for row in build_report()["rows"]}
    hp009 = rows["hp009"]
    hp017 = rows["hp017"]
    assert hp009["action"] == "source_bound_reconstruction"
    assert hp009["query_core_coverage"] is True
    assert "ZX2e/ZX5e" in hp009["answer_after"]
    assert "on right panel" not in hp009["answer_after"]
    assert hp017["action"] == "fail_closed"
    assert hp017["query_core_coverage"] is False
    assert "cause_effect_menu_path" not in hp017["answer_after"]
    assert "número de menú de Causa y Efecto" in hp017["answer_after"]


def test_s124_serialized_replay_matches_in_memory_report():
    report = build_report()
    serialized = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert serialized == json.loads(json.dumps(report, ensure_ascii=False))
