#!/usr/bin/env python3
"""Capped, resumable extractor for the preregistered S116 holdout."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import platform
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s116_independent_document_holdout_prereg_v4.yaml"
API = "https://api.cloud.llamaindex.ai/api/v1/parsing"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_key(env_file: Path | None) -> str | None:
    if value := os.environ.get("LLAMAPARSE_API_KEY"):
        return value
    if env_file and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("LLAMAPARSE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _pdf_manifest(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["sha256"]):
        digest.update(f"{row['sha256']}\0{row['pages']}\0{row['filename']}\n".encode())
    return digest.hexdigest()


def _verify_frozen_evaluator(prereg: dict) -> None:
    frozen = prereg.get("implementations", {}).get("frozen_evaluator")
    if not frozen:
        return
    if platform.python_version() != frozen.get("python"):
        raise RuntimeError("Python runtime drift")
    for relative, expected in frozen.items():
        if relative == "python":
            continue
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"frozen evaluator drift: {relative}")


def preflight(prereg_path: Path, receipt_path: Path, pdf_dir: Path) -> dict:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    _verify_frozen_evaluator(prereg)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_receipt_hash = prereg["source"]["acquisition_receipt"]["sha256"]
    if _sha256(receipt_path) != expected_receipt_hash:
        raise RuntimeError("acquisition receipt drift")
    if receipt.get("summary", {}).get("gate") != "GO":
        raise RuntimeError("acquisition gate is not GO")
    expected = {row["sha256"]: row for row in prereg["documents"]}
    rows = receipt.get("documents", [])
    if len(rows) != len(expected):
        raise RuntimeError("document count drift")
    checked = []
    for row in rows:
        sha = row.get("sha256")
        if row.get("status") != "ok" or sha not in expected:
            raise RuntimeError("document identity drift")
        path = pdf_dir / row["filename"]
        frozen = expected[sha]
        if not path.is_file() or _sha256(path) != sha:
            raise RuntimeError(f"PDF drift: {row['filename']}")
        if row.get("pages") != frozen["pages"]:
            raise RuntimeError(f"page-count drift: {row['filename']}")
        checked.append({**row, "path": path})
    pages = sum(row["pages"] for row in checked)
    first_attempt_credits = pages * prereg["budget"]["credits_per_page"]
    if (
        pages != prereg["budget"]["pages"]
        or first_attempt_credits > prereg["budget"]["maximum_credits"]
    ):
        raise RuntimeError("budget gate failed")
    return {
        "prereg": prereg,
        "prereg_sha256": _sha256(prereg_path),
        "receipt_sha256": _sha256(receipt_path),
        "pdf_manifest_sha256": _pdf_manifest(checked),
        "documents": checked,
        "pages": pages,
        "first_attempt_credits": first_attempt_credits,
        "maximum_attempt_pages": prereg["budget"].get("maximum_attempt_pages", pages),
        "maximum_submissions": prereg["budget"].get("maximum_submissions", len(checked)),
        "maximum_distinct_documents": prereg["budget"].get(
            "maximum_distinct_documents", len(checked)
        ),
        "maximum_credits": prereg["budget"]["maximum_credits"],
        "estimated_usd": prereg["budget"]["displayed_estimate_usd"],
    }


def _write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextmanager
def _exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"extraction lock exists: {path}") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        path.unlink(missing_ok=True)


def _canonical_paths(plan: dict) -> dict[str, Path]:
    extraction = plan["prereg"]["extraction"]
    return {
        "out_dir": ROOT / extraction["output_store"],
        "ledger": ROOT / extraction["attempt_ledger"],
        "lock": ROOT / extraction["exclusive_lock"],
        "seal": ROOT / extraction["raw_artifact_receipt"],
    }


def _ledger_identity(plan: dict) -> dict:
    return {
        "prereg_sha256": plan["prereg_sha256"],
        "acquisition_receipt_sha256": plan["receipt_sha256"],
        "pdf_manifest_sha256": plan["pdf_manifest_sha256"],
        "planned_documents": len(plan["documents"]),
        "planned_pages": plan["pages"],
        "maximum_attempt_pages": plan["maximum_attempt_pages"],
        "maximum_submissions": plan["maximum_submissions"],
        "maximum_distinct_documents": plan["maximum_distinct_documents"],
        "maximum_credits": plan["maximum_credits"],
    }


def _load_or_create_ledger(path: Path, plan: dict) -> dict:
    identity = _ledger_identity(plan)
    if path.exists():
        ledger = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(ledger.get("attempts"), dict):
            raise RuntimeError("attempt ledger schema drift")
        if ledger.get("identity") != identity:
            replacement = plan["prereg"].get("replacement_authorization") or {}
            failed_sha = replacement.get("failed_sha256")
            failed_attempt = ledger["attempts"].get(failed_sha, {})
            retries = failed_attempt.get("retries", [])
            if replacement:
                if (
                    ledger.get("identity") != replacement.get("prior_identity")
                    or failed_attempt.get("status") != "failed"
                    or failed_attempt.get("job_id") != replacement.get("original_failed_job_id")
                    or len(retries) != 1
                    or retries[0].get("status") != "submitted"
                    or retries[0].get("job_id") != replacement.get("retry_failed_job_id")
                    or replacement.get("maximum_replacements") != 1
                    or replacement.get("replacement_sha256") in ledger["attempts"]
                ):
                    raise RuntimeError("replacement ledger identity drift")
                ledger.setdefault("prior_identities", []).append(ledger["identity"])
                ledger["identity"] = identity
                retries[0].update({
                    "status": "failed",
                    "error_code": replacement.get("error_code"),
                    "error_message": replacement.get("error_message"),
                })
                failed_attempt.update({
                    "status": "failed_terminal",
                    "replacement_sha256": replacement.get("replacement_sha256"),
                    "error_code": replacement.get("error_code"),
                    "error_message": replacement.get("error_message"),
                })
                ledger.setdefault("retired_documents", []).append({
                    "sha256": failed_sha,
                    "reason": "deterministic_extraction_failure",
                    "replacement_sha256": replacement.get("replacement_sha256"),
                })
                _write_json_atomic(path, ledger)
                return ledger
            authorization = plan["prereg"].get("retry_authorization") or {}
            failed_sha = authorization.get("sha256")
            attempt = ledger["attempts"].get(failed_sha, {})
            prior = authorization.get("prior_identity")
            if (
                ledger.get("identity") != prior
                or attempt.get("status") != "submitted"
                or attempt.get("job_id") != authorization.get("failed_job_id")
                or authorization.get("maximum_retries") != 1
            ):
                raise RuntimeError("attempt ledger identity drift")
            ledger.setdefault("prior_identities", []).append(ledger["identity"])
            ledger["identity"] = identity
            attempt.update({
                "status": "failed",
                "error_code": authorization.get("error_code"),
                "error_message": authorization.get("error_message"),
                "retries": [],
            })
            _write_json_atomic(path, ledger)
        return ledger
    if plan["prereg"].get("retry_authorization") or plan["prereg"].get("replacement_authorization"):
        raise RuntimeError("authorized recovery requires the existing canonical ledger")
    ledger = {"instrument": "s116_extraction_attempts_v1", "identity": identity, "attempts": {}}
    _write_json_atomic(path, ledger)
    return ledger


def _seal_records(plan: dict, paths: dict[str, Path], ledger: dict) -> dict:
    ledger_failures = _final_ledger_failures(plan["prereg"], ledger)
    if ledger_failures:
        raise RuntimeError(f"terminal ledger contract failed: {','.join(ledger_failures)}")
    mode = plan["prereg"]["extraction"]["parse_mode"]
    model = plan["prereg"]["extraction"]["vendor_multimodal_model_name"]
    records = []
    job_ids = []
    for row in sorted(plan["documents"], key=lambda item: item["sha256"]):
        sha = row["sha256"]
        record_path = paths["out_dir"] / f"{sha}.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        attempt = ledger["attempts"].get(sha, {})
        job_id = record.get("job_id")
        successful_job_id = (
            attempt.get("successful_job_id")
            if attempt.get("status") == "completed_after_retry"
            else attempt.get("job_id")
        )
        if (
            record.get("sha256") != sha
            or record.get("mode") != mode
            or record.get("model") != model
            or attempt.get("status") not in {"completed", "completed_after_retry"}
            or successful_job_id != job_id
        ):
            raise RuntimeError(f"cannot seal record: {record_path.name}")
        job_ids.append(job_id)
        records.append({
            "sha256": sha,
            "job_id": job_id,
            "pages": row["pages"],
            "raw_record": record_path.name,
            "raw_record_sha256": _sha256(record_path),
        })
    if len(job_ids) != len(set(job_ids)):
        raise RuntimeError("duplicate extraction job id")
    payload = {
        "instrument": "s116_independent_extraction_receipt_v1",
        "identity": _ledger_identity(plan),
        "mode": mode,
        "model": model,
        "ledger_sha256": _sha256(paths["ledger"]),
        "records": records,
    }
    _write_json_atomic(paths["seal"], payload)
    return payload


def _attempt_usage(attempts: dict) -> dict:
    pages = credits = submissions = 0
    for attempt in attempts.values():
        pages += int(attempt["pages"])
        credits += int(attempt["credits"])
        submissions += 1
        for retry in attempt.get("retries", []):
            pages += int(retry["pages"])
            credits += int(retry["credits"])
            submissions += 1
    return {"pages": pages, "credits": credits, "submissions": submissions}


def _final_ledger_failures(prereg: dict, ledger: dict) -> list[str]:
    """Validate the final cumulative denominator, not only its file hash."""
    attempts = ledger.get("attempts")
    if not isinstance(attempts, dict):
        return ["attempt_schema_drift"]
    successful = {row["sha256"] for row in prereg["documents"]}
    replacement = prereg.get("replacement_authorization") or {}
    failed_sha = replacement.get("failed_sha256")
    expected_attempts = successful | ({failed_sha} if failed_sha else set())
    failures = []
    if set(attempts) != expected_attempts:
        failures.append("attempt_set_drift")
    for sha in successful:
        attempt = attempts.get(sha, {})
        if attempt.get("status") not in {"completed", "completed_after_retry"}:
            failures.append(f"successful_attempt_status_drift:{sha}")
        if not attempt.get("job_id"):
            failures.append(f"successful_attempt_job_drift:{sha}")
    if not replacement:
        return failures

    failed = attempts.get(failed_sha, {})
    retries = failed.get("retries")
    if (
        failed.get("status") != "failed_terminal"
        or failed.get("job_id") != replacement.get("original_failed_job_id")
        or failed.get("error_code") != replacement.get("error_code")
        or failed.get("error_message") != replacement.get("error_message")
        or failed.get("replacement_sha256") != replacement.get("replacement_sha256")
    ):
        failures.append("terminal_failure_drift")
    if (
        not isinstance(retries, list)
        or len(retries) != 1
        or retries[0].get("status") != "failed"
        or retries[0].get("job_id") != replacement.get("retry_failed_job_id")
        or retries[0].get("error_code") != replacement.get("error_code")
        or retries[0].get("error_message") != replacement.get("error_message")
    ):
        failures.append("terminal_retry_drift")
    retired = [{
        "sha256": failed_sha,
        "reason": "deterministic_extraction_failure",
        "replacement_sha256": replacement.get("replacement_sha256"),
    }]
    if ledger.get("retired_documents") != retired:
        failures.append("retired_mapping_drift")
    replacement_attempt = attempts.get(replacement.get("replacement_sha256"), {})
    if (
        replacement_attempt.get("status") != "completed"
        or replacement_attempt.get("retries")
    ):
        failures.append("replacement_attempt_drift")
    usage = _attempt_usage(attempts)
    budget = prereg["budget"]
    expected_usage = {
        "pages": budget["maximum_attempt_pages"],
        "credits": budget["maximum_credits"],
        "submissions": budget["maximum_submissions"],
    }
    if usage != expected_usage:
        failures.append("cumulative_usage_drift")
    if len(attempts) != budget["maximum_distinct_documents"]:
        failures.append("distinct_document_drift")
    return failures


def _budget_allows(plan: dict, usage: dict, pages: int, credits: int) -> bool:
    return (
        usage["submissions"] + 1 <= plan["maximum_submissions"]
        and usage["pages"] + pages <= plan["maximum_attempt_pages"]
        and usage["credits"] + credits <= plan["maximum_credits"]
    )


def _submit(path: Path, key: str, mode: str, model: str) -> str:
    headers = {"Authorization": f"Bearer {key}"}
    data = {"parse_mode": mode, "vendor_multimodal_model_name": model}
    with path.open("rb") as handle:
        response = httpx.post(
            f"{API}/upload",
            headers=headers,
            data=data,
            files={"file": (path.name, handle, "application/pdf")},
            timeout=300,
        )
    if response.status_code != 200:
        raise RuntimeError(f"upload HTTP {response.status_code}: {response.text[:200]}")
    return response.json()["id"]


def _collect(job_id: str, key: str) -> dict:
    headers = {"Authorization": f"Bearer {key}"}
    for _ in range(400):
        status = httpx.get(f"{API}/job/{job_id}", headers=headers, timeout=30)
        status.raise_for_status()
        state = status.json().get("status")
        if state == "SUCCESS":
            break
        if state in {"ERROR", "FAILED"}:
            raise RuntimeError(f"job {state}")
        time.sleep(3)
    else:
        raise RuntimeError("job polling timeout")
    response = httpx.get(f"{API}/job/{job_id}/result/json", headers=headers, timeout=120)
    response.raise_for_status()
    return response.json()


def execute(
    plan: dict,
    key: str,
    *,
    submit=_submit,
    collect=_collect,
) -> dict:
    prereg = plan["prereg"]
    mode = prereg["extraction"]["parse_mode"]
    model = prereg["extraction"]["vendor_multimodal_model_name"]
    paths = _canonical_paths(plan)
    with _exclusive_lock(paths["lock"]):
        ledger = _load_or_create_ledger(paths["ledger"], plan)
        attempts = ledger["attempts"]
        completed = skipped = 0
        for row in plan["documents"]:
            sha = row["sha256"]
            destination = paths["out_dir"] / f"{sha}.json"
            if destination.exists():
                record = json.loads(destination.read_text(encoding="utf-8"))
                attempt = attempts.get(sha, {})
                successful_job_id = (
                    attempt.get("successful_job_id")
                    if attempt.get("status") == "completed_after_retry"
                    else attempt.get("job_id")
                )
                if (
                    record.get("sha256") != sha
                    or record.get("mode") != mode
                    or record.get("model") != model
                    or attempt.get("status") not in {"completed", "completed_after_retry"}
                    or successful_job_id != record.get("job_id")
                ):
                    raise RuntimeError(f"existing record drift: {destination.name}")
                skipped += 1
                continue
            if sha in attempts:
                attempt = attempts[sha]
                authorization = prereg.get("retry_authorization") or {}
                retries = attempt.get("retries", [])
                if (
                    sha != authorization.get("sha256")
                    or attempt.get("status") != "failed"
                    or attempt.get("job_id") != authorization.get("failed_job_id")
                    or authorization.get("maximum_retries") != 1
                    or len(retries) >= 1
                ):
                    raise RuntimeError(f"refusing automatic retry for {sha}; inspect canonical ledger")
                row_credits = row["pages"] * prereg["budget"]["credits_per_page"]
                usage = _attempt_usage(attempts)
                if not _budget_allows(plan, usage, row["pages"], row_credits):
                    raise RuntimeError("retry budget exceeded")
                retry = {
                    "status": "prepared",
                    "filename": row["filename"],
                    "pages": row["pages"],
                    "credits": row_credits,
                    "ordinal": 1,
                }
                retries.append(retry)
                _write_json_atomic(paths["ledger"], ledger)
                job_id = submit(row["path"], key, mode, model)
                retry.update({"status": "submitted", "job_id": job_id})
                _write_json_atomic(paths["ledger"], ledger)
                result = collect(job_id, key)
                extracted_pages = result.get("pages")
                if not isinstance(extracted_pages, list) or len(extracted_pages) != row["pages"]:
                    retry["status"] = "page_count_mismatch"
                    _write_json_atomic(paths["ledger"], ledger)
                    raise RuntimeError(f"retry page-count mismatch: {row['filename']}")
                record = {
                    "sha256": sha,
                    "source_path": str(row["path"]),
                    "manufacturer": row["manufacturer"],
                    "pages": row["pages"],
                    "mode": mode,
                    "model": model,
                    "job_id": job_id,
                    "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "result": result,
                }
                _write_json_atomic(destination, record)
                retry.update({"status": "completed", "record": destination.name})
                attempt.update({"status": "completed_after_retry", "successful_job_id": job_id})
                _write_json_atomic(paths["ledger"], ledger)
                completed += 1
                continue
            usage = _attempt_usage(attempts)
            row_credits = row["pages"] * prereg["budget"]["credits_per_page"]
            if (
                len(attempts) + 1 > plan["maximum_distinct_documents"]
                or not _budget_allows(plan, usage, row["pages"], row_credits)
            ):
                raise RuntimeError("attempt budget exceeded")
            attempts[sha] = {
                "status": "prepared",
                "filename": row["filename"],
                "pages": row["pages"],
                "credits": row_credits,
            }
            _write_json_atomic(paths["ledger"], ledger)
            job_id = submit(row["path"], key, mode, model)
            attempts[sha].update({"status": "submitted", "job_id": job_id})
            _write_json_atomic(paths["ledger"], ledger)
            result = collect(job_id, key)
            extracted_pages = result.get("pages")
            if not isinstance(extracted_pages, list) or len(extracted_pages) != row["pages"]:
                attempts[sha].update({"status": "page_count_mismatch"})
                _write_json_atomic(paths["ledger"], ledger)
                raise RuntimeError(f"extracted page-count mismatch: {row['filename']}")
            record = {
                "sha256": sha,
                "source_path": str(row["path"]),
                "manufacturer": row["manufacturer"],
                "pages": row["pages"],
                "mode": mode,
                "model": model,
                "job_id": job_id,
                "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "result": result,
            }
            _write_json_atomic(destination, record)
            attempts[sha].update({"status": "completed", "record": destination.name})
            _write_json_atomic(paths["ledger"], ledger)
            completed += 1
        seal = _seal_records(plan, paths, ledger)
        return {
            "completed": completed,
            "skipped": skipped,
            "records": completed + skipped,
            "raw_artifact_receipt": paths["seal"].name,
            "sealed_records": len(seal["records"]),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    prereg = yaml.safe_load(DEFAULT_PREREG.read_text(encoding="utf-8"))
    receipt = ROOT / prereg["source"]["acquisition_receipt"]["path"]
    pdf_dir = ROOT / prereg["extraction"]["pdf_store"]
    plan = preflight(DEFAULT_PREREG, receipt, pdf_dir)
    public = {key: plan[key] for key in ("pages", "maximum_credits", "estimated_usd")}
    public["documents"] = len(plan["documents"])
    public["mode"] = plan["prereg"]["extraction"]["parse_mode"]
    public["model"] = plan["prereg"]["extraction"]["vendor_multimodal_model_name"]
    public["execute"] = args.execute
    if not args.execute:
        print(json.dumps(public, indent=2))
        return 0
    key = _load_key(args.env_file)
    if not key:
        raise RuntimeError("LLAMAPARSE_API_KEY is not available")
    result = execute(plan, key)
    print(json.dumps({**public, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
