#!/usr/bin/env python3
"""Freeze and compare the corpus-wide B1/B2 language profile contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.reingest import language


ROOT = Path(__file__).resolve().parents[1]
_RECORD_NAME = re.compile(r"^[0-9a-f]{64}\.json$")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _strict_json(path: Path) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    value = json.loads(path.read_bytes(), parse_constant=reject)
    if not isinstance(value, dict):
        raise ValueError("raw extraction record must be an object")
    return value


def _store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(
            f"{path.name}\0{len(raw)}\0{_sha_bytes(raw)}\n".encode("utf-8")
        )
    return digest.hexdigest()


def _profile_with_raw(record: dict[str, Any]) -> tuple[Any, dict[int, str]]:
    raw: dict[int, str] = {}
    text_languages: dict[str, str] = {}
    original_detect = language.detect_language
    for page_number, text in language._pages_from_record(record):
        if page_number is None:
            continue
        detected = original_detect(text)
        raw[page_number] = detected
        text_languages[text] = detected

    def cached_detect(text: str) -> str:
        if text not in text_languages:
            raise RuntimeError("language gate cache miss")
        return text_languages[text]

    language.detect_language = cached_detect
    try:
        profile = language.profile_document(record)
    finally:
        language.detect_language = original_detect
    return profile, raw


def _row(path: Path) -> dict[str, Any]:
    record = _strict_json(path)
    if record.get("sha256") != path.stem:
        raise RuntimeError("raw extraction identity drift")
    profile, raw = _profile_with_raw(record)
    page_language = {
        int(page): value for page, value in sorted(profile.page_language.items())
    }
    counts = Counter(value for value in page_language.values() if value != "unknown")
    if not counts:
        winners = ["es"]
        expected_first_known = "es"
    else:
        maximum = max(counts.values())
        winners = sorted(value for value, count in counts.items() if count == maximum)
        expected_first_known = next(
            value
            for _page, value in sorted(raw.items())
            if value != "unknown" and value in winners
        )
    return {
        "extraction_sha256": path.stem,
        "raw_page_language": [[page, value] for page, value in sorted(raw.items())],
        "page_language": [[page, value] for page, value in page_language.items()],
        "counts": dict(sorted(counts.items())),
        "languages_present": sorted(profile.languages_present),
        "verdict": profile.verdict,
        "legacy_dominant": profile.dominant,
        "maximum_is_unique": len(winners) == 1,
        "maximum_languages": winners,
        "expected_first_known_dominant": expected_first_known,
    }


def build_population(store: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    files = sorted(store.glob("*.json"), key=lambda path: path.name)
    records = [path for path in files if _RECORD_NAME.fullmatch(path.name)]
    if len(records) != 1068:
        raise RuntimeError("language gate corpus cardinality drift")
    rows = [_row(path) for path in records]
    return rows, {
        "json_files": len(files),
        "records": len(records),
        "store_manifest_sha256": _store_manifest(files),
        "record_set_sha256": _sha_bytes(
            _canonical([row["extraction_sha256"] for row in rows])
        ),
    }


def freeze(store: Path) -> dict[str, Any]:
    rows, corpus = build_population(store)
    ties = sum(not row["maximum_is_unique"] for row in rows)
    return {
        "instrument": "s117_language_profile_baseline_v1",
        "status": "FROZEN",
        "legacy_language_sha256": _sha_file(ROOT / "src/reingest/language.py"),
        "corpus": corpus,
        "summary": {
            "documents": len(rows),
            "unique_maximum_documents": len(rows) - ties,
            "tied_maximum_documents": ties,
        },
        "rows": rows,
    }


def compare(store: Path, baseline_path: Path) -> dict[str, Any]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    rows, corpus = build_population(store)
    frozen_rows = {
        row["extraction_sha256"]: row for row in baseline["rows"]
    }
    checks = Counter()
    failures: list[dict[str, Any]] = []
    changed_ties = 0

    if corpus != baseline["corpus"]:
        failures.append({"scope": "corpus", "reason": "corpus drift"})
    if set(frozen_rows) != {row["extraction_sha256"] for row in rows}:
        failures.append({"scope": "corpus", "reason": "record set drift"})

    for current in rows:
        sha = current["extraction_sha256"]
        frozen = frozen_rows.get(sha)
        if frozen is None:
            continue
        invariant_fields = (
            "raw_page_language",
            "page_language",
            "counts",
            "languages_present",
            "verdict",
            "maximum_is_unique",
            "maximum_languages",
            "expected_first_known_dominant",
        )
        drifted = [field for field in invariant_fields if current[field] != frozen[field]]
        if drifted:
            failures.append({"extraction_sha256": sha, "invariant_drift": drifted})
            continue
        checks["invariant_documents"] += 1
        observed = current["legacy_dominant"]
        if frozen["maximum_is_unique"]:
            checks["unique_maximum_documents"] += 1
            if observed != frozen["legacy_dominant"]:
                failures.append({
                    "extraction_sha256": sha,
                    "reason": "unique maximum dominant changed",
                    "before": frozen["legacy_dominant"],
                    "after": observed,
                })
        else:
            checks["tied_maximum_documents"] += 1
            expected = frozen["expected_first_known_dominant"]
            if observed != expected:
                failures.append({
                    "extraction_sha256": sha,
                    "reason": "tie did not select first known",
                    "expected": expected,
                    "after": observed,
                })
            elif observed != frozen["legacy_dominant"]:
                changed_ties += 1

    receipt = {
        "instrument": "s117_language_determinism_gate_v1",
        "status": "GO" if not failures else "NO_GO",
        "baseline_sha256": _sha_file(baseline_path),
        "current_language_sha256": _sha_file(ROOT / "src/reingest/language.py"),
        "corpus": corpus,
        "checks": dict(sorted(checks.items())),
        "changed_tied_documents": changed_ties,
        "failures": failures[:100],
        "failure_count": len(failures),
    }
    receipt["payload_sha256"] = _sha_bytes(_canonical(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--mode", choices=("freeze", "compare"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()

    if args.mode == "freeze":
        result = freeze(args.store)
    else:
        if args.baseline is None:
            raise RuntimeError("--baseline is required in compare mode")
        result = compare(args.store, args.baseline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, allow_nan=False, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    return 0 if result["status"] in {"FROZEN", "GO"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
