import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


def _module():
    path = Path("scripts/s123_s122_enforced_two_answer_probe.py")
    spec = importlib.util.spec_from_file_location("s123_probe", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_s123_prereg_is_exactly_two_single_attempt_calls():
    prereg = yaml.safe_load(
        Path("evals/s123_s122_enforced_two_answer_probe_prereg_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert prereg["authorization"]["authorized_qids"] == ["hp009", "hp017"]
    assert prereg["scope"]["maximum_fresh_generator_calls"] == 2
    assert prereg["scope"]["maximum_calls_per_qid"] == 1
    assert prereg["scope"]["automatic_retries"] == 0
    assert prereg["scope"]["retrieval_calls"] == 0
    assert prereg["scope"]["database_writes"] == 0


def test_s123_surface_checks_cover_exact_three_claims():
    module = _module()
    answers = {
        "hp009": "Es un lazo cerrado: Inicio Lazo OUT vuelve a Retorno.",
        "hp017": (
            "Regla 1: cualquier entrada de alarma activa todas las sirenas. "
            "Deben eliminarse las dos reglas por defecto."
        ),
    }
    rows = [
        claim
        for qid, answer in answers.items()
        for claim in module.fact_checks(qid, answer)
    ]
    assert len(rows) == 3
    assert all(row["deterministic_surface_present"] for row in rows)


def test_s123_checkpoint_events_are_append_only_and_recoverable(tmp_path):
    module = _module()
    module.CHECKPOINT = tmp_path / "checkpoint.jsonl"
    attempt = {
        "event": "attempt_started",
        "qid": "hp009",
        "generation_contract_sha256": "a" * 64,
    }
    completion = {
        "event": "answer_completed",
        "qid": "hp009",
        "generation_contract_sha256": "a" * 64,
    }
    module._append_event(attempt)
    module._append_event(completion)
    attempts, completions, errors = module._load_events()
    assert attempts["hp009"] == attempt
    assert completions["hp009"] == completion
    assert errors == {}


def test_s123_checkpoint_rejects_completion_before_attempt(tmp_path):
    module = _module()
    module.CHECKPOINT = tmp_path / "checkpoint.jsonl"
    module._append_event(
        {
            "event": "answer_completed",
            "qid": "hp009",
            "generation_contract_sha256": "a" * 64,
        }
    )
    with pytest.raises(RuntimeError, match="out-of-order"):
        module._load_events()


def test_s123_contract_hash_is_stable_and_content_sensitive():
    module = _module()
    assert module.stable_sha256({"b": 2, "a": 1}) == module.stable_sha256(
        {"a": 1, "b": 2}
    )
    assert module.stable_sha256({"a": 1}) != module.stable_sha256({"a": 2})


def test_s123_rejects_two_qids_in_one_invocation(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/s123_s122_enforced_two_answer_probe.py",
            "--env-file",
            str(tmp_path / "unused.env"),
            "--execute-qids",
            "hp009,hp017",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "execute-qids" in result.stderr


def test_s123_atomic_claim_allows_only_one_process_owner(tmp_path):
    module = _module()
    module.CHECKPOINT = tmp_path / "checkpoint.jsonl"
    module._claim_attempt("hp009", "a" * 64)
    with pytest.raises(RuntimeError, match="atomic claim already exists"):
        module._claim_attempt("hp009", "a" * 64)


def test_s123_prior_ambiguous_attempt_blocks_remaining_spend():
    module = _module()
    with pytest.raises(RuntimeError, match="failed or ambiguous"):
        module._assert_probe_open_for_spend(
            ("hp017",),
            {"hp009": {"qid": "hp009"}},
            {},
        )


def test_s123_prior_automatic_no_go_blocks_remaining_spend():
    module = _module()
    failed_completion = {
        "qid": "hp009",
        "stop_reason": "max_tokens",
        "final_validation": {"total": 2, "covered": 2},
        "final_conflict_validation": {"unsafe": False},
        "obligation_citations_present": True,
        "diagnostic_claims": [
            {"claim_id": "x", "deterministic_surface_present": True}
        ],
        "answer_planner": {
            "action": "pass",
            "query_core_coverage": True,
        },
        "unsafe_positive_eol_claim": False,
    }
    with pytest.raises(RuntimeError, match="automatic NO-GO"):
        module._assert_probe_open_for_spend(
            ("hp017",),
            {"hp009": {"qid": "hp009"}},
            {"hp009": failed_completion},
        )


def test_s123_hp017_cannot_run_before_hp009_passes():
    module = _module()
    with pytest.raises(RuntimeError, match="requires a passing hp009"):
        module._assert_probe_open_for_spend(("hp017",), {}, {})
