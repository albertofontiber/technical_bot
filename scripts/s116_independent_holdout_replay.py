#!/usr/bin/env python3
"""Run the frozen S116 baseline/treatment replay over independent raw records."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import yaml

from scripts.s116_cross_extractor_challenge import _run_arm
from scripts.s116_extract_independent_holdout import _final_ledger_failures

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s116_independent_document_holdout_prereg_v4.yaml"
DEFAULT_OUT = ROOT / "evals/s116_independent_document_holdout_replay_v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_chunker_source(source: bytes, name: str, filename: str) -> ModuleType:
    module = ModuleType(name)
    module.__file__ = filename
    sys.modules[name] = module
    exec(compile(source, filename, "exec"), module.__dict__)
    return module


def _load_chunker(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load treatment chunker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _git_source(commit: str, expected_sha: str) -> bytes:
    source = subprocess.run(
        ["git", "show", f"{commit}:src/reingest/chunk.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    candidates = (source, source.replace(b"\n", b"\r\n"))
    for candidate in candidates:
        if hashlib.sha256(candidate).hexdigest() == expected_sha:
            return candidate
    raise RuntimeError("baseline chunker drift")


def _store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(f"{path.name}\0{len(raw)}\0{hashlib.sha256(raw).hexdigest()}\n".encode())
    return digest.hexdigest()


def _verify_frozen_evaluator(prereg: dict) -> None:
    frozen = prereg["implementations"]["frozen_evaluator"]
    if platform.python_version() != frozen.get("python"):
        raise RuntimeError("Python runtime drift")
    for relative, expected in frozen.items():
        if relative == "python":
            continue
        path = ROOT / relative
        if not path.is_file() or _sha(path) != expected:
            raise RuntimeError(f"frozen evaluator drift: {relative}")


def _validate_records(files: list[Path], prereg: dict) -> dict:
    expected = {row["sha256"]: row for row in prereg["documents"]}
    mode = prereg["extraction"]["parse_mode"]
    model = prereg["extraction"]["vendor_multimodal_model_name"]
    failures = []
    seen = set()
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            sha = record.get("sha256")
            frozen = expected.get(sha)
            result_pages = record.get("result", {}).get("pages")
            valid = (
                frozen is not None
                and path.stem == sha
                and record.get("pages") == frozen["pages"]
                and record.get("mode") == mode
                and record.get("model") == model
                and isinstance(result_pages, list)
                and len(result_pages) == frozen["pages"]
            )
            if not valid:
                failures.append({"file": path.name, "error": "record_contract_drift"})
            else:
                seen.add(sha)
        except Exception as exc:
            failures.append({"file": path.name, "error": type(exc).__name__})
    missing = sorted(set(expected) - seen)
    return {
        "valid": not failures and not missing and len(files) == len(expected),
        "expected_records": len(expected),
        "files": len(files),
        "failures": failures,
        "missing_sha256": missing,
    }


def _expected_identity(prereg: dict, prereg_path: Path) -> dict:
    digest = hashlib.sha256()
    for row in sorted(prereg["documents"], key=lambda item: item["sha256"]):
        digest.update(f"{row['sha256']}\0{row['pages']}\0{row['filename']}\n".encode())
    return {
        "prereg_sha256": _sha(prereg_path),
        "acquisition_receipt_sha256": prereg["source"]["acquisition_receipt"]["sha256"],
        "pdf_manifest_sha256": digest.hexdigest(),
        "planned_documents": len(prereg["documents"]),
        "planned_pages": prereg["budget"]["pages"],
        "maximum_attempt_pages": prereg["budget"].get(
            "maximum_attempt_pages", prereg["budget"]["pages"]
        ),
        "maximum_submissions": prereg["budget"].get(
            "maximum_submissions", len(prereg["documents"])
        ),
        "maximum_distinct_documents": prereg["budget"].get(
            "maximum_distinct_documents", len(prereg["documents"])
        ),
        "maximum_credits": prereg["budget"]["maximum_credits"],
    }


def _validate_raw_artifact_receipt(store: Path, prereg: dict, prereg_path: Path) -> dict:
    extraction = prereg["extraction"]
    receipt_path = ROOT / extraction["raw_artifact_receipt"]
    ledger_path = ROOT / extraction["attempt_ledger"]
    failures = []
    if not receipt_path.is_file() or not ledger_path.is_file():
        return {"valid": False, "failures": ["missing_receipt_or_ledger"]}
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        expected_identity = _expected_identity(prereg, prereg_path)
        records = receipt.get("records", [])
        expected = {row["sha256"] for row in prereg["documents"]}
        jobs = [row.get("job_id") for row in records]
        if receipt.get("instrument") != "s116_independent_extraction_receipt_v1":
            failures.append("instrument_drift")
        if receipt.get("identity") != expected_identity or ledger.get("identity") != expected_identity:
            failures.append("identity_drift")
        if receipt.get("mode") != extraction["parse_mode"]:
            failures.append("mode_drift")
        if receipt.get("model") != extraction["vendor_multimodal_model_name"]:
            failures.append("model_drift")
        if receipt.get("ledger_sha256") != _sha(ledger_path):
            failures.append("ledger_hash_drift")
        failures.extend(_final_ledger_failures(prereg, ledger))
        if {row.get("sha256") for row in records} != expected or len(records) != len(expected):
            failures.append("record_set_drift")
        if None in jobs or len(jobs) != len(set(jobs)):
            failures.append("job_id_drift")
        for row in records:
            path = store / str(row.get("raw_record"))
            if not path.is_file() or _sha(path) != row.get("raw_record_sha256"):
                failures.append(f"raw_hash_drift:{row.get('sha256')}")
    except Exception as exc:
        failures.append(type(exc).__name__)
    return {
        "valid": not failures,
        "path": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": _sha(receipt_path) if receipt_path.is_file() else None,
        "failures": failures,
    }


def _documents_with_titles(files: list[Path], module: ModuleType) -> int:
    count = 0
    for path in files:
        record = json.loads(path.read_text(encoding="utf-8"))
        if any(chunk.section_title for chunk in module.chunk_document(record)):
            count += 1
    return count


def decide(
    baseline: dict,
    treatment: dict,
    record_contract_ok: bool,
    stream_mismatches: list[str],
    documents_with_titles: int,
    expected_records: int = 12,
) -> dict:
    growth = treatment["chunks_total"] - baseline["chunks_total"]
    growth_percent = 100 * growth / baseline["chunks_total"] if baseline["chunks_total"] else 0.0
    checks = {
        "record_contract": record_contract_ok,
        "all_records_processed": (
            baseline["processed_files"] == treatment["processed_files"] == expected_records
        ),
        "zero_arm_errors": baseline["errors"] == treatment["errors"] == [],
        "zero_content_stream_mismatches": not stream_mismatches,
        "zero_lineage_state_failures": treatment["chunk_lineage_state_failures"] == 0,
        "zero_orphan_anchors": treatment["orphan_or_stale_anchor_chunks"] == 0,
        "all_titled_anchors_verified": (
            treatment["titled_chunks"] == treatment["internally_verified_anchors"]
        ),
        "all_titled_lineages_resolved": (
            treatment["titled_chunks"] == treatment["resolved_full_lineages"]
        ),
        "non_vacuous_documents": documents_with_titles >= 5,
        "non_vacuous_chunks": treatment["titled_chunks"] >= 30,
        "chunk_growth_within_cap": growth_percent <= 15,
    }
    return {
        "gate": "GO" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "document_stream_mismatches": stream_mismatches,
        "documents_with_section_titles": documents_with_titles,
        "chunk_increase": growth,
        "chunk_increase_percent": round(growth_percent, 4),
    }


def build_payload(store: Path, prereg_path: Path, treatment_path: Path) -> dict:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    _verify_frozen_evaluator(prereg)
    files = sorted(store.glob("[0-9a-fA-F]" * 64 + ".json"), key=lambda path: path.name)
    baseline_config = prereg["implementations"]["baseline"]
    treatment_config = prereg["implementations"]["treatment"]
    baseline_source = _git_source(baseline_config["git_commit"], baseline_config["sha256"])
    if _sha(treatment_path) != treatment_config["sha256"]:
        raise RuntimeError("treatment chunker drift")
    baseline_module = _load_chunker_source(
        baseline_source, "s116_independent_baseline_chunk", "frozen:src/reingest/chunk.py"
    )
    treatment_module = _load_chunker(treatment_path, "s116_independent_treatment_chunk")
    records = _validate_records(files, prereg)
    raw_artifact_receipt = _validate_raw_artifact_receipt(store, prereg, prereg_path)
    baseline = _run_arm(files, baseline_module, False)
    treatment = _run_arm(files, treatment_module, True)
    names = sorted(set(baseline["document_streams"]) | set(treatment["document_streams"]))
    mismatches = [
        name for name in names
        if baseline["document_streams"].get(name) != treatment["document_streams"].get(name)
    ]
    documents_with_titles = _documents_with_titles(files, treatment_module)
    comparison = decide(
        baseline,
        treatment,
        records["valid"] and raw_artifact_receipt["valid"],
        mismatches,
        documents_with_titles,
        len(prereg["documents"]),
    )
    for arm in (baseline, treatment):
        del arm["document_streams"]
    return {
        "instrument": "s116_independent_document_holdout_replay_v1",
        "status": "independent_holdout_go" if comparison["gate"] == "GO" else "independent_holdout_no_go",
        "source": {
            "store_slug": store.name,
            "raw_records": len(files),
            "manifest_sha256": _store_manifest(files),
            "pdf_identity_overlap_with_development": 0,
        },
        "records": records,
        "raw_artifact_receipt": raw_artifact_receipt,
        "implementations": {
            "baseline_sha256": hashlib.sha256(baseline_source).hexdigest(),
            "treatment_sha256": _sha(treatment_path),
            "replay_sha256": _sha(Path(__file__)),
        },
        "baseline": baseline,
        "treatment": treatment,
        "comparison": comparison,
        "authorization_if_go": "design_versioned_persistence_and_provenance_only",
        "cost": {"model_calls": 0, "network_calls": 0, "database_writes": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--treatment-chunker", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = build_payload(args.store, args.prereg, args.treatment_chunker)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["comparison"], ensure_ascii=False, indent=2))
    return 0 if payload["comparison"]["gate"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
