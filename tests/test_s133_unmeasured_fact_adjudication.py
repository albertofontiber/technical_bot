import hashlib
import json
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ADJUDICATION = ROOT / "evals/s133_unmeasured_fact_adjudication_v1.yaml"

# Commit that sealed the adjudication and its authority receipts ("rag:
# consolidate S133-S193 structural evaluation milestone", PR #120; the
# adjudication records no commit id). Authority hashes are physical blob
# bytes, so they are verified against the sealed git blobs, not a
# CRLF-smudging checkout (DEC-147: version, do not relax).
ADJUDICATION_SEAL_COMMIT = "5868c9b11e3c6219dc9e8db6e377315ceb0572c6"


def _sealed_sha256(relative: str) -> str:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{ADJUDICATION_SEAL_COMMIT}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, f"sealed blob missing: {relative}"
    return hashlib.sha256(completed.stdout).hexdigest()


def test_s133_fact_adjudication_is_complete_bijective_and_receipted():
    payload = yaml.safe_load(ADJUDICATION.read_text(encoding="utf-8"))
    reconciliation = yaml.safe_load(
        (ROOT / "evals/s130_unmeasured_answer_reconciliation_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    answers = json.loads(
        (ROOT / "evals/s133_unmeasured_answer_probe_v1.json").read_text(
            encoding="utf-8"
        )
    )

    for receipt in payload["authority"].values():
        assert _sealed_sha256(receipt["path"]) == receipt["sha256"]

    expected_qid = {
        claim_id: question["qid"]
        for question in reconciliation["questions"]
        for claim_id in question["claim_ids"]
    }
    answer_sha = {row["qid"]: row["answer_sha256"] for row in answers["rows"]}
    rows = payload["rows"]
    assert len(rows) == len(expected_qid) == 27
    assert {row["claim_id"] for row in rows} == set(expected_qid)
    assert len({row["claim_id"] for row in rows}) == len(rows)

    histogram = {"OK": 0, "synthesis-miss": 0}
    for row in rows:
        assert row["qid"] == expected_qid[row["claim_id"]]
        assert row["answer_sha256"] == answer_sha[row["qid"]]
        assert row["contradicted"] is False
        assert row["answer_evidence"].strip()
        histogram[row["stage_bucket"]] += 1
        if row["stage_bucket"] == "OK":
            assert row["complete_entailment"] is True
            assert row["qualifiers_preserved"] is True
            assert not row.get("missing_elements")
        else:
            assert row["complete_entailment"] is False
            assert row["missing_elements"]

    assert histogram == payload["summary"]["stage_histogram"]
    assert histogram == {"OK": 23, "synthesis-miss": 4}
    assert payload["summary"]["facts_reclassified_from_unmeasured"] == 27
    assert payload["summary"]["judge_calls"] == 0
