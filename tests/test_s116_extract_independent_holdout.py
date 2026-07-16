from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
import pytest

from scripts import s116_extract_independent_holdout as extractor
from scripts import s116_independent_holdout_replay as replay
from scripts.s116_extract_independent_holdout import preflight


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preflight_enforces_receipt_pdfs_and_budget(tmp_path: Path) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    pdf = pdf_dir / "one.pdf"
    pdf.write_bytes(b"%PDF-frozen")
    sha = _sha(pdf)
    receipt = {
        "summary": {"gate": "GO"},
        "documents": [{
            "status": "ok", "sha256": sha, "filename": pdf.name,
            "pages": 2, "manufacturer": "Example",
        }],
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    prereg = {
        "source": {"acquisition_receipt": {"sha256": _sha(receipt_path)}},
        "documents": [{"id": "one", "pages": 2, "sha256": sha}],
        "budget": {"credits_per_page": 45, "pages": 2, "maximum_credits": 90,
                   "displayed_estimate_usd": 0.12},
    }
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text(yaml.safe_dump(prereg), encoding="utf-8")
    plan = preflight(prereg_path, receipt_path, pdf_dir)
    assert plan["pages"] == 2
    assert plan["maximum_credits"] == 90


def test_preflight_rejects_receipt_drift(tmp_path: Path) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text('{"summary":{"gate":"GO"},"documents":[]}', encoding="utf-8")
    prereg_path = tmp_path / "prereg.yaml"
    prereg_path.write_text(
        yaml.safe_dump({"source": {"acquisition_receipt": {"sha256": "0" * 64}}}),
        encoding="utf-8",
    )
    try:
        preflight(prereg_path, receipt_path, tmp_path)
    except RuntimeError as exc:
        assert str(exc) == "acquisition receipt drift"
    else:
        raise AssertionError("receipt drift was accepted")


def _execution_plan(tmp_path: Path, count: int = 12) -> dict:
    rows = [
        {
            "sha256": f"{index + 1:064x}",
            "filename": f"{index}.pdf",
            "pages": 1,
            "manufacturer": "Example",
            "path": tmp_path / f"{index}.pdf",
        }
        for index in range(count)
    ]
    return {
        "prereg": {
            "source": {"acquisition_receipt": {"sha256": "b" * 64}},
            "documents": [
                {"sha256": row["sha256"], "pages": row["pages"], "filename": row["filename"]}
                for row in rows
            ],
            "extraction": {
                "parse_mode": "parse_page_with_agent",
                "vendor_multimodal_model_name": "anthropic-sonnet-4.5",
                "output_store": "raw",
                "attempt_ledger": "attempts.json",
                "exclusive_lock": "attempts.lock",
                "raw_artifact_receipt": "raw_receipt.json",
            },
            "budget": {
                "credits_per_page": 45,
                "pages": count,
                "maximum_credits": count * 45,
            },
        },
        "prereg_sha256": "a" * 64,
        "receipt_sha256": "b" * 64,
        "pdf_manifest_sha256": extractor._pdf_manifest(rows),
        "documents": rows,
        "pages": count,
        "maximum_attempt_pages": count,
        "maximum_submissions": count,
        "maximum_distinct_documents": count,
        "maximum_credits": count * 45,
    }


def test_execute_is_canonical_capped_and_non_retrying(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(extractor, "ROOT", tmp_path)
    monkeypatch.setattr(replay, "ROOT", tmp_path)
    plan = _execution_plan(tmp_path)
    plan["prereg"]["documents"] = [
        {"sha256": row["sha256"], "pages": row["pages"], "filename": row["filename"]}
        for row in plan["documents"]
    ]
    prereg_path = tmp_path / "runtime-prereg.yaml"
    prereg_path.write_text("frozen", encoding="utf-8")
    plan["prereg_sha256"] = _sha(prereg_path)
    submissions = []

    def submit(path, key, mode, model):
        submissions.append(path.name)
        return f"job-{len(submissions)}"

    def collect(job_id, key):
        return {"pages": [{"md": job_id}]}

    first = extractor.execute(plan, "secret", submit=submit, collect=collect)
    assert first["records"] == 12
    assert len(submissions) == 12
    ledger = json.loads((tmp_path / "attempts.json").read_text(encoding="utf-8"))
    assert sum(row["credits"] for row in ledger["attempts"].values()) == 12 * 45
    assert replay._validate_raw_artifact_receipt(
        tmp_path / "raw", plan["prereg"], prereg_path
    )["valid"]
    second = extractor.execute(
        plan,
        "secret",
        submit=lambda *args: (_ for _ in ()).throw(AssertionError("unexpected retry")),
        collect=collect,
    )
    assert second["skipped"] == 12
    first_record = tmp_path / "raw" / f"{1:064x}.json"
    first_record.unlink()
    with pytest.raises(RuntimeError, match="refusing automatic retry"):
        extractor.execute(plan, "secret", submit=submit, collect=collect)


def test_exclusive_lock_rejects_concurrent_execution(tmp_path: Path) -> None:
    lock = tmp_path / "extract.lock"
    with extractor._exclusive_lock(lock):
        with pytest.raises(RuntimeError, match="extraction lock exists"):
            with extractor._exclusive_lock(lock):
                pass


def test_exactly_one_authorized_retry_migrates_ledger_and_cannot_repeat(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(extractor, "ROOT", tmp_path)
    plan = _execution_plan(tmp_path, count=1)
    row = plan["documents"][0]
    plan.update({"maximum_attempt_pages": 2, "maximum_submissions": 2, "maximum_credits": 90})
    plan["prereg"]["budget"].update({
        "maximum_attempt_pages": 2, "maximum_submissions": 2, "maximum_credits": 90,
    })
    prior_identity = {
        "prereg_sha256": "old-prereg",
        "acquisition_receipt_sha256": plan["receipt_sha256"],
        "pdf_manifest_sha256": plan["pdf_manifest_sha256"],
        "planned_documents": 1,
        "planned_pages": 1,
        "maximum_attempt_pages": 1,
        "maximum_submissions": 1,
        "maximum_credits": 45,
    }
    plan["prereg"]["retry_authorization"] = {
        "sha256": row["sha256"],
        "failed_job_id": "failed-job",
        "error_code": "MARKDOWN_EXTRACTION_FAILED",
        "error_message": "five pages failed",
        "maximum_retries": 1,
        "prior_identity": prior_identity,
    }
    ledger = {
        "instrument": "s116_extraction_attempts_v1",
        "identity": prior_identity,
        "attempts": {
            row["sha256"]: {
                "status": "submitted", "filename": row["filename"], "pages": 1,
                "credits": 45, "job_id": "failed-job",
            }
        },
    }
    (tmp_path / "attempts.json").write_text(json.dumps(ledger), encoding="utf-8")
    submissions = []

    def submit(path, key, mode, model):
        submissions.append(path.name)
        return "retry-job"

    result = extractor.execute(
        plan, "secret", submit=submit, collect=lambda job, key: {"pages": [{"md": "ok"}]}
    )
    assert result["records"] == 1
    assert submissions == [row["filename"]]
    migrated = json.loads((tmp_path / "attempts.json").read_text(encoding="utf-8"))
    attempt = migrated["attempts"][row["sha256"]]
    assert attempt["status"] == "completed_after_retry"
    assert attempt["job_id"] == "failed-job"
    assert attempt["successful_job_id"] == "retry-job"
    assert len(attempt["retries"]) == 1
    (tmp_path / "raw" / f"{row['sha256']}.json").unlink()
    with pytest.raises(RuntimeError, match="refusing automatic retry"):
        extractor.execute(plan, "secret", submit=submit, collect=lambda *args: {})


def test_authorized_retry_requires_existing_canonical_ledger(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(extractor, "ROOT", tmp_path)
    plan = _execution_plan(tmp_path, count=1)
    plan["prereg"]["retry_authorization"] = {
        "sha256": plan["documents"][0]["sha256"],
        "failed_job_id": "failed-job",
        "maximum_retries": 1,
        "prior_identity": {"frozen": "old"},
    }
    with pytest.raises(RuntimeError, match="requires the existing canonical ledger"):
        extractor.execute(plan, "secret", submit=lambda *args: "unexpected", collect=lambda *args: {})


def test_resume_skips_completed_retry_and_processes_untouched_document(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(extractor, "ROOT", tmp_path)
    plan = _execution_plan(tmp_path, count=2)
    plan.update({"maximum_attempt_pages": 3, "maximum_submissions": 3, "maximum_credits": 135})
    plan["prereg"]["budget"].update({
        "maximum_attempt_pages": 3, "maximum_submissions": 3, "maximum_credits": 135,
    })
    first, second = plan["documents"]
    plan["prereg"]["retry_authorization"] = {
        "sha256": first["sha256"], "failed_job_id": "failed-job", "maximum_retries": 1,
    }
    ledger = {
        "instrument": "s116_extraction_attempts_v1",
        "identity": extractor._ledger_identity(plan),
        "attempts": {
            first["sha256"]: {
                "status": "completed_after_retry", "filename": first["filename"],
                "pages": 1, "credits": 45, "job_id": "failed-job",
                "successful_job_id": "retry-job",
                "retries": [{
                    "status": "completed", "filename": first["filename"], "pages": 1,
                    "credits": 45, "ordinal": 1, "job_id": "retry-job",
                    "record": f"{first['sha256']}.json",
                }],
            }
        },
    }
    (tmp_path / "attempts.json").write_text(json.dumps(ledger), encoding="utf-8")
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / f"{first['sha256']}.json").write_text(json.dumps({
        "sha256": first["sha256"], "mode": "parse_page_with_agent",
        "model": "anthropic-sonnet-4.5", "job_id": "retry-job",
        "pages": 1, "result": {"pages": [{"md": "retry"}]},
    }), encoding="utf-8")
    submissions = []

    def submit(path, key, mode, model):
        submissions.append(path.name)
        return "second-job"

    result = extractor.execute(
        plan, "secret", submit=submit, collect=lambda job, key: {"pages": [{"md": "second"}]}
    )
    assert result["skipped"] == 1
    assert result["completed"] == 1
    assert submissions == [second["filename"]]


def test_exact_replacement_migrates_terminal_failure_and_preserves_usage(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(extractor, "ROOT", tmp_path)
    monkeypatch.setattr(replay, "ROOT", tmp_path)
    plan = _execution_plan(tmp_path, count=1)
    replacement = plan["documents"][0]
    failed_sha = "f" * 64
    plan.update({
        "maximum_attempt_pages": 3,
        "maximum_submissions": 3,
        "maximum_distinct_documents": 2,
        "maximum_credits": 135,
    })
    plan["prereg"]["budget"].update({
        "maximum_attempt_pages": 3,
        "maximum_submissions": 3,
        "maximum_distinct_documents": 2,
        "maximum_credits": 135,
    })
    prior_identity = {
        "prereg_sha256": "prior",
        "acquisition_receipt_sha256": plan["receipt_sha256"],
        "pdf_manifest_sha256": "old-manifest",
        "planned_documents": 1,
        "planned_pages": 1,
        "maximum_attempt_pages": 2,
        "maximum_submissions": 2,
        "maximum_distinct_documents": 1,
        "maximum_credits": 90,
    }
    plan["prereg"]["replacement_authorization"] = {
        "failed_sha256": failed_sha,
        "original_failed_job_id": "original-failure",
        "retry_failed_job_id": "retry-failure",
        "replacement_sha256": replacement["sha256"],
        "maximum_replacements": 1,
        "error_code": "MARKDOWN_EXTRACTION_FAILED",
        "error_message": "same pages failed",
        "prior_identity": prior_identity,
    }
    prereg_path = tmp_path / "runtime-prereg.yaml"
    prereg_path.write_text("frozen", encoding="utf-8")
    plan["prereg_sha256"] = _sha(prereg_path)
    ledger = {
        "instrument": "s116_extraction_attempts_v1",
        "identity": prior_identity,
        "attempts": {
            failed_sha: {
                "status": "failed", "filename": "failed.pdf", "pages": 1, "credits": 45,
                "job_id": "original-failure",
                "retries": [{
                    "status": "submitted", "filename": "failed.pdf", "pages": 1,
                    "credits": 45, "ordinal": 1, "job_id": "retry-failure",
                }],
            }
        },
    }
    (tmp_path / "attempts.json").write_text(json.dumps(ledger), encoding="utf-8")
    result = extractor.execute(
        plan,
        "secret",
        submit=lambda *args: "replacement-job",
        collect=lambda *args: {"pages": [{"md": "replacement"}]},
    )
    assert result["records"] == 1
    migrated = json.loads((tmp_path / "attempts.json").read_text(encoding="utf-8"))
    assert migrated["attempts"][failed_sha]["status"] == "failed_terminal"
    assert migrated["attempts"][failed_sha]["retries"][0]["status"] == "failed"
    assert migrated["attempts"][replacement["sha256"]]["status"] == "completed"
    assert extractor._attempt_usage(migrated["attempts"]) == {
        "pages": 3, "credits": 135, "submissions": 3,
    }
    assert extractor._final_ledger_failures(plan["prereg"], migrated) == []
    valid = replay._validate_raw_artifact_receipt(
        tmp_path / "raw", plan["prereg"], prereg_path
    )
    assert valid["valid"]

    del migrated["attempts"][failed_sha]
    (tmp_path / "attempts.json").write_text(json.dumps(migrated), encoding="utf-8")
    receipt_path = tmp_path / "raw_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["ledger_sha256"] = _sha(tmp_path / "attempts.json")
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    invalid = replay._validate_raw_artifact_receipt(
        tmp_path / "raw", plan["prereg"], prereg_path
    )
    assert not invalid["valid"]
    assert "attempt_set_drift" in invalid["failures"]
    assert "terminal_failure_drift" in invalid["failures"]
