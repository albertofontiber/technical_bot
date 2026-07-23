from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest

from scripts import s277_c1_p1_offline_counterfactual as preflight


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _source_review_item(key: str, binding: str, check_id: str) -> dict:
    replica_key = key.rsplit(":", 1)[0]
    return {
        "review_key": key,
        "replica_key": replica_key,
        "check_id": check_id,
        "binding_sha256": binding,
    }


def _score(
    replica_key: str,
    checks: list[dict],
    review_items: list[dict],
) -> dict:
    return {
        "replica_key": replica_key,
        "checks": checks,
        "review_items": review_items,
    }


def test_load_decisions_accepts_canonical_and_all_blind_batch_shapes(
    tmp_path: Path,
) -> None:
    paths = [
        _write(
            tmp_path / "canonical.json",
            {
                "rows": [
                    {
                        "review_key": "q:r1:a",
                        "decision": preflight.BASELINE_PASS,
                        "binding_sha256": "a" * 64,
                    }
                ]
            },
        ),
        _write(
            tmp_path / "batch_b.json",
            {
                "recommendations": [
                    {
                        "review_key": "q:r1:b",
                        "recommendation": preflight.BASELINE_FAIL,
                    }
                ]
            },
        ),
        _write(
            tmp_path / "batch_c.json",
            {
                "rows": [
                    {
                        "review_key": "q:r1:c",
                        "decision": preflight.BASELINE_PASS,
                    }
                ]
            },
        ),
    ]

    decisions = preflight.load_decisions(paths)

    assert set(decisions) == {"q:r1:a", "q:r1:b", "q:r1:c"}
    assert decisions["q:r1:b"]["decision"] == preflight.BASELINE_FAIL


def test_load_decisions_rejects_duplicate_and_unbound_candidate(
    tmp_path: Path,
) -> None:
    first = _write(
        tmp_path / "first.json",
        {"rows": [{"review_key": "q:r1:a", "decision": preflight.BASELINE_PASS}]},
    )
    duplicate = _write(
        tmp_path / "duplicate.json",
        {"rows": [{"review_key": "q:r1:a", "decision": preflight.BASELINE_FAIL}]},
    )

    with pytest.raises(preflight.CounterfactualPreflightError, match="duplicate decision"):
        preflight.load_decisions([first, duplicate])
    with pytest.raises(preflight.CounterfactualPreflightError, match="lacks a hash binding"):
        preflight.load_decisions([first], require_binding=True)


def test_replay_receipt_uses_frozen_draft_and_deterministic_detector() -> None:
    frozen = "draft"
    source_answer = "draft|planner|mp|guard"
    receipt = {
        "schema": "test",
        "replica_key": "q:r1",
        "qid": "q",
        "replica_id": "r1",
        "input": {"question": "question"},
        "served_context": [{"id": "chunk", "content": "source"}],
        "answer": source_answer,
        "answer_sha256": preflight.sha256_text(source_answer),
        "must_preserve": {"status": "evaluated", "profile": "sealed"},
        "generation_chain": {
            "stages": [
                {
                    "name": "diagram_postprocess",
                    "output_text": frozen,
                    "output_sha256": preflight.sha256_text(frozen),
                },
                {"name": "answer_planner"},
                {"name": "must_preserve"},
                {"name": "conflict_guard"},
            ]
        },
    }
    calls: list[tuple] = []
    detector = object()

    def planner(question, context, answer):
        calls.append(("planner", question, context, answer))
        return answer + "|planner", {"planner": True}

    def must_preserve(question, context, answer, *, detect_fn):
        calls.append(("mp", question, context, answer, detect_fn))
        return answer + "|mp", {"must_preserve": True}

    def conflict(question, context, answer):
        calls.append(("guard", question, context, answer))
        return answer + "|guard", {"guard": True}

    row, scoring_view = preflight.replay_receipt(
        receipt,
        apply_answer_planner=planner,
        apply_must_preserve_contract=must_preserve,
        detect_atoms=detector,
        apply_answer_conflict_guard=conflict,
    )

    assert [call[0] for call in calls] == ["planner", "mp", "guard"]
    assert calls[1][-1] is detector
    assert row["candidate_answer"] == source_answer
    assert row["source_answer_byte_exact"] is True
    assert scoring_view["answer"] == source_answer
    assert scoring_view["must_preserve"]["status"] == "evaluated"
    assert receipt["must_preserve"] == {"status": "evaluated", "profile": "sealed"}


def test_compare_scores_preserves_pass_and_measures_machine_fix() -> None:
    replica = "q:r1"
    pass_key = f"{replica}:review_pass"
    fail_key = f"{replica}:review_fail"
    source_items = [
        _source_review_item(pass_key, "a" * 64, "review_pass"),
        _source_review_item(fail_key, "b" * 64, "review_fail"),
    ]
    source_score = {
        "review_items": source_items,
        "replicas": [
            _score(
                replica,
                [
                    {"check_id": "automatic", "status": "PASS"},
                    {"check_id": "review_pass", "status": "REVIEW"},
                    {"check_id": "review_fail", "status": "REVIEW"},
                ],
                source_items,
            )
        ],
    }
    decisions = {
        pass_key: {"decision": preflight.BASELINE_PASS},
        fail_key: {"decision": preflight.BASELINE_FAIL},
    }
    candidate = _score(
        replica,
        [
            {"check_id": "automatic", "status": "PASS"},
            {"check_id": "review_pass", "status": "PASS"},
            {"check_id": "review_fail", "status": "PASS"},
        ],
        [],
    )

    result = preflight.compare_scores(
        source_score=source_score,
        baseline_decisions=decisions,
        candidate_scores=[candidate],
    )
    by_key = {row["review_key"]: row for row in result["review_comparisons"]}

    assert by_key[pass_key]["classification"] == "PRESERVED_MACHINE_PASS"
    assert by_key[fail_key]["classification"] == "FIXED_MACHINE_PASS"
    assert result["summary"]["automatic_pass_regressions"] == 0
    assert result["summary"]["baseline_adjudicated_fail_fixed"] == 1


def test_changed_review_binding_requires_fresh_blind_decision() -> None:
    replica = "q:r1"
    key = f"{replica}:review"
    source_item = _source_review_item(key, "a" * 64, "review")
    candidate_item = _source_review_item(key, "b" * 64, "review")
    source_score = {
        "review_items": [source_item],
        "replicas": [_score(replica, [{"check_id": "review", "status": "REVIEW"}], [source_item])],
    }
    candidate_score = _score(
        replica,
        [{"check_id": "review", "status": "REVIEW"}],
        [candidate_item],
    )
    baseline = {key: {"decision": preflight.BASELINE_PASS}}

    pending = preflight.compare_scores(
        source_score=source_score,
        baseline_decisions=baseline,
        candidate_scores=[candidate_score],
    )
    assert pending["pending_review_keys"] == [key]
    assert (
        pending["review_comparisons"][0]["classification"]
        == "HOLD_FRESH_BLIND_REVIEW_REQUIRED"
    )

    resolved = preflight.compare_scores(
        source_score=source_score,
        baseline_decisions=baseline,
        candidate_scores=[candidate_score],
        candidate_decisions={
            key: {
                "decision": preflight.BASELINE_PASS,
                "binding_sha256": "b" * 64,
            }
        },
    )
    assert resolved["pending_review_keys"] == []
    assert (
        resolved["review_comparisons"][0]["classification"]
        == "PRESERVED_AFTER_FRESH_BLIND_PASS"
    )


def test_automatic_pass_review_is_a_regression_even_after_human_review() -> None:
    replica = "q:r1"
    source_score = {
        "review_items": [],
        "replicas": [_score(replica, [{"check_id": "automatic", "status": "PASS"}], [])],
    }
    candidate_item = _source_review_item(
        f"{replica}:automatic", "c" * 64, "automatic"
    )
    candidate_score = _score(
        replica,
        [{"check_id": "automatic", "status": "REVIEW"}],
        [candidate_item],
    )

    result = preflight.compare_scores(
        source_score=source_score,
        baseline_decisions={},
        candidate_scores=[candidate_score],
        candidate_decisions={
            candidate_item["review_key"]: {
                "decision": preflight.BASELINE_PASS,
                "binding_sha256": "c" * 64,
            }
        },
    )

    assert result["summary"]["automatic_pass_regressions"] == 1
    assert result["gate"] == preflight.HOLD


def test_network_guard_fails_closed_and_restores_socket() -> None:
    original = socket.create_connection
    with pytest.raises(preflight.CounterfactualPreflightError, match="network access attempted"):
        with preflight.deny_network() as attempts:
            socket.create_connection(("example.invalid", 443))
    assert attempts == ["blocked_network_attempt"]
    assert socket.create_connection is original


def test_output_cannot_be_written_into_frozen_run(tmp_path: Path) -> None:
    source = tmp_path / "run"
    source.mkdir()
    with pytest.raises(
        preflight.CounterfactualPreflightError,
        match="may not modify the frozen source run",
    ):
        preflight.assert_output_outside_source_run(source / "preflight.json", source)


def test_candidate_identity_gate_requires_committed_clean_bytes() -> None:
    gate, reasons = preflight.apply_candidate_identity_gate(
        preflight.FROZEN_CONTEXT_PASS,
        {"dirty": True},
    )
    assert gate == preflight.HOLD
    assert reasons == ["CANDIDATE_WORKTREE_DIRTY"]

    gate, reasons = preflight.apply_candidate_identity_gate(
        preflight.FROZEN_CONTEXT_PASS,
        {"dirty": False},
    )
    assert gate == preflight.FROZEN_CONTEXT_PASS
    assert reasons == []
