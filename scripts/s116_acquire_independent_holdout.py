#!/usr/bin/env python3
"""Download and validate the preregistered S116 independent PDF cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import fitz
import yaml
import certifi

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s116_independent_holdout_acquisition_prereg_v1.yaml"
DEFAULT_OUT = ROOT / "evals/s116_independent_holdout_acquisition_v1.json"
HEX64 = re.compile(r"[0-9a-fA-F]{64}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pdf_receipt(path: Path) -> dict:
    raw_prefix = path.read_bytes()[:5]
    if raw_prefix != b"%PDF-":
        raise ValueError("missing_pdf_magic")
    document = fitz.open(path)
    try:
        pages = len(document)
        if pages < 1:
            raise ValueError("empty_pdf")
    finally:
        document.close()
    return {"sha256": _sha256(path), "pages": pages, "size_bytes": path.stat().st_size}


def development_hashes(store: Path) -> set[str]:
    return {
        path.stem.lower()
        for path in store.glob("*.json")
        if HEX64.fullmatch(path.stem)
    }


def evaluate(rows: list[dict], expected: int, development: set[str]) -> dict:
    successful = [row for row in rows if row.get("status") == "ok"]
    hashes = [row["sha256"] for row in successful]
    pages = [row["pages"] for row in successful]
    manufacturers = {row["manufacturer"] for row in successful}
    failures = [row for row in rows if row.get("status") != "ok"]
    checks = {
        "all_documents_valid": len(successful) == expected and not failures,
        "unique_sha256": len(hashes) == len(set(hashes)) == expected,
        "zero_development_overlap": not any(value in development for value in hashes),
        "minimum_manufacturers": len(manufacturers) >= 4,
        "long_document_present": any(page_count > 30 for page_count in pages),
        "two_short_documents_present": sum(page_count <= 5 for page_count in pages) >= 2,
    }
    return {
        "gate": "GO" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "successful_documents": len(successful),
        "manufacturers": len(manufacturers),
        "total_pages": sum(pages),
        "total_size_bytes": sum(row["size_bytes"] for row in successful),
        "development_overlap": sorted(value for value in hashes if value in development),
        "failures": failures,
    }


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TechnicalBot-S116-Holdout/1.0"},
    )
    temporary = destination.with_suffix(destination.suffix + ".part")
    tls_context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=120, context=tls_context) as response, temporary.open("wb") as output:
        while block := response.read(1024 * 1024):
            output.write(block)
    os.replace(temporary, destination)


def acquire(prereg: Path, out_dir: Path, development_store: Path) -> dict:
    contract = yaml.safe_load(prereg.read_text(encoding="utf-8"))
    cohort = contract["cohort"]
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for candidate in cohort:
        destination = out_dir / candidate["filename"]
        row = {
            "id": candidate["id"],
            "manufacturer": candidate["manufacturer"],
            "stratum": candidate["stratum"],
            "filename": candidate["filename"],
            "source_host": urlparse(candidate["url"]).hostname,
        }
        try:
            if not destination.exists():
                _download(candidate["url"], destination)
            row.update(pdf_receipt(destination))
            row["status"] = "ok"
        except Exception as exc:
            row.update({"status": "error", "error_type": type(exc).__name__, "error": str(exc)[:160]})
        rows.append(row)
    development = development_hashes(development_store)
    summary = evaluate(rows, len(cohort), development)
    return {
        "instrument": "s116_independent_holdout_acquisition_v1",
        "status": "acquisition_go" if summary["gate"] == "GO" else "acquisition_no_go",
        "prereg_sha256": _sha256(prereg),
        "source": {"documents": len(cohort), "store_slug": out_dir.name},
        "summary": summary,
        "documents": rows,
        "cost": {
            "download_calls": sum(1 for row in rows if row["status"] == "ok"),
            "model_calls": 0,
            "database_get_requests": 0,
            "database_writes": 0,
        },
        "authorization": {
            "estimate_extraction_cost": summary["gate"] == "GO",
            "run_paid_extraction": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--development-store", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = acquire(args.prereg, args.out_dir, args.development_store)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0 if payload["summary"]["gate"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
