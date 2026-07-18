from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.rag.query_evidence_compiler import portable_file_sha, stable_sha


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "evals/s213_sharded_unit_selector_preflight_v1.json"
PERMIT = ROOT / "evals/s213_sharded_unit_selector_execution_permit_v1.yaml"
PARTIAL = ROOT / "evals/s213_sharded_unit_selector_calls_v1.partial.jsonl"
CLOSURE = ROOT / "evals/s213_sharded_unit_selector_incomplete_closure_v1.json"


def _assert_sealed(value: dict) -> None:
    body = dict(value)
    expected = body.pop("result_sha256")
    assert stable_sha(body) == expected


def test_s213_permit_remains_exactly_bound_to_merged_preflight_and_artifacts():
    permit = yaml.safe_load(PERMIT.read_text(encoding="utf-8"))
    assert permit["status"] == "EXECUTION_GO_PAID_BOUNDED_NO_RETRY"
    assert permit["preflight_sha256"] == portable_file_sha(PREFLIGHT)
    for row in permit["frozen_artifacts"]:
        assert portable_file_sha(ROOT / row["path"]) == row["sha256"]


def test_s213_incomplete_closure_is_fail_closed_and_awards_no_credit():
    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    _assert_sealed(closure)
    assert closure["status"] == "NO_GO_INCOMPLETE_FAIL_CLOSED"
    assert closure["failure"]["selected_unique_ids"] == 24
    assert closure["failure"]["would_be_appendix_chars"] == 18_956
    assert closure["failure"]["compiled_char_bound"] == 12_000
    assert closure["execution"]["completed_calls"] == 26
    assert closure["execution"]["provider_retries"] == 0
    assert not closure["execution"]["final_receipts_written"]
    assert not closure["execution"]["score_written"]
    assert closure["credit"]["facts_moved_to_ok"] == 0
    assert closure["credit"]["facts_ok_after"] == 143
    assert closure["inputs"]["partial_journal_sha256"] == portable_file_sha(PARTIAL)
    assert not (ROOT / "evals/s213_sharded_unit_selector_receipts_v1.json").exists()
    assert not (ROOT / "evals/s213_sharded_unit_selector_score_v1.json").exists()
