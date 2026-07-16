#!/usr/bin/env python3
"""Screen S116 source PDFs for exact-content and near-duplicate development overlap."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import fitz
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s116_independent_near_duplicate_screen_prereg_v1.yaml"
DEFAULT_OUT = ROOT / "evals/s116_independent_near_duplicate_screen_v1.json"
WORD = re.compile(r"[a-z0-9]+")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(f"{path.name}\0{len(raw)}\0{hashlib.sha256(raw).hexdigest()}\n".encode())
    return digest.hexdigest()


def _tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.casefold()).encode("ascii", "ignore").decode()
    return WORD.findall(folded)


def _fingerprint(tokens: list[str], width: int = 7) -> set[bytes]:
    if len(tokens) < width:
        return {hashlib.blake2b(" ".join(tokens).encode(), digest_size=8).digest()} if tokens else set()
    return {
        hashlib.blake2b(" ".join(tokens[index:index + width]).encode(), digest_size=8).digest()
        for index in range(len(tokens) - width + 1)
    }


def _identifiers(tokens: list[str]) -> set[str]:
    return {
        token for token in tokens
        if 4 <= len(token) <= 30 and any(char.isalpha() for char in token)
        and sum(char.isdigit() for char in token) >= 2
    }


def _pdf_text(path: Path) -> str:
    document = fitz.open(path)
    try:
        return "\n".join(page.get_text("text") for page in document)
    finally:
        document.close()


def _record_text(path: Path) -> tuple[str, str]:
    record = json.loads(path.read_text(encoding="utf-8"))
    pages = record.get("result", {}).get("pages", [])
    text = "\n".join(str(page.get("md") or page.get("text") or "") for page in pages)
    return text, str(record.get("source_path") or path.name)


def _signature(text: str) -> dict:
    tokens = _tokens(text)
    return {
        "token_count": len(tokens),
        "normalized_sha256": hashlib.sha256(" ".join(tokens).encode()).hexdigest(),
        "fingerprint": _fingerprint(tokens),
        "identifiers": _identifiers(tokens),
    }


def _score(candidate: dict, development: dict) -> dict:
    left = candidate["fingerprint"]
    right = development["fingerprint"]
    intersection = len(left & right)
    union = len(left | right)
    smaller = min(len(left), len(right))
    return {
        "jaccard": intersection / union if union else 0.0,
        "containment": intersection / smaller if smaller else 0.0,
        "shared_shingles": intersection,
        "shared_identifiers": sorted(candidate["identifiers"] & development["identifiers"])[:20],
    }


def screen(prereg_path: Path, development_store: Path) -> dict:
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    receipt_path = ROOT / prereg["candidates"]["acquisition_receipt"]
    if _sha(receipt_path) != prereg["candidates"]["acquisition_receipt_sha256"]:
        raise RuntimeError("acquisition receipt drift")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    candidate_rows = receipt["documents"]
    pdf_store = ROOT / prereg["candidates"]["pdf_store"]
    development_files = sorted(development_store.glob("*.json"), key=lambda path: path.name.casefold())
    manifest = _store_manifest(development_files)
    development_gate = (
        len(development_files) == prereg["development"]["expected_json_files"]
        and manifest == prereg["development"]["expected_manifest_sha256"]
    )
    if not development_gate:
        raise RuntimeError("development store drift")
    candidates = {}
    for row in candidate_rows:
        path = pdf_store / row["filename"]
        if row.get("status") != "ok" or not path.is_file() or _sha(path) != row["sha256"]:
            raise RuntimeError(f"candidate drift: {row['filename']}")
        candidates[row["sha256"]] = {**row, **_signature(_pdf_text(path))}
    matches = {sha: [] for sha in candidates}
    exact = []
    failures = []
    processed = 0
    for path in development_files:
        try:
            text, source_path = _record_text(path)
            development = _signature(text)
        except Exception as exc:
            failures.append({"file": path.name, "error_type": type(exc).__name__})
            continue
        processed += 1
        for sha, candidate in candidates.items():
            score = _score(candidate, development)
            row = {"development_file": path.name, "source_path": source_path, **score}
            matches[sha].append(row)
            if candidate["normalized_sha256"] == development["normalized_sha256"]:
                exact.append({"candidate_sha256": sha, **row})
    threshold_flags = []
    output_rows = []
    for sha, candidate in candidates.items():
        ranked = sorted(
            matches[sha], key=lambda row: (row["containment"], row["jaccard"]), reverse=True
        )[:5]
        for row in ranked:
            if row["containment"] >= 0.80 or row["jaccard"] >= 0.65:
                threshold_flags.append({"candidate_sha256": sha, **row})
        output_rows.append({
            "id": candidate["id"],
            "manufacturer": candidate["manufacturer"],
            "sha256": sha,
            "tokens": candidate["token_count"],
            "unique_shingles": len(candidate["fingerprint"]),
            "top_matches": ranked,
        })
    checks = {
        "development_store_frozen": development_gate,
        "all_candidate_hashes_valid": len(candidates) == prereg["candidates"]["documents"],
        "zero_exact_content_duplicates": not exact,
        "zero_near_duplicates": not threshold_flags,
    }
    return {
        "instrument": "s116_independent_near_duplicate_screen_v1",
        "status": "screen_go" if all(checks.values()) else "screen_no_go",
        "checks": checks,
        "source": {
            "candidate_documents": len(candidates),
            "development_json_files": len(development_files),
            "development_records_processed": processed,
            "development_manifest_sha256": manifest,
            "development_errors": failures,
        },
        "exact_content_duplicates": exact,
        "near_duplicate_flags": threshold_flags,
        "candidates": output_rows,
        "cost": {"model_calls": 0, "network_calls": 0, "database_reads": 0, "database_writes": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-store", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = screen(args.prereg, args.development_store)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "checks": payload["checks"],
        "development_records_processed": payload["source"]["development_records_processed"],
        "near_duplicate_flags": len(payload["near_duplicate_flags"]),
    }, indent=2))
    return 0 if payload["status"] == "screen_go" else 1


if __name__ == "__main__":
    raise SystemExit(main())
