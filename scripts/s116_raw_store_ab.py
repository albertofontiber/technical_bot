#!/usr/bin/env python3
"""Deterministic, zero-call chunking inventory over paid extraction artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.reingest.chunk import MIN_CHARS, chunk_document
from src.reingest.metadata import detect_document_metadata

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s116_raw_store_baseline_v1.json"
HEADING = re.compile(r"(?m)^\s*#{1,6}\s+(.+?)\s*$")
NUMERIC_SECTION = re.compile(r"^\s*\d+(?:\.\d+)+(?:\s|$)")


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _leaf_heading_in_content(content: str, title: str | None) -> bool:
    leaf = _fold(title)
    return bool(leaf) and any(_fold(match) == leaf for match in HEADING.findall(content))


def _receipt_value(receipt: object, key: str) -> Any:
    if isinstance(receipt, dict):
        return receipt.get(key)
    return getattr(receipt, key, None)


def _verified_receipt(chunk: object) -> bool:
    receipt = getattr(chunk, "section_anchor", None)
    if receipt is None:
        return False
    heading_text = _receipt_value(receipt, "heading_text")
    heading_sha256 = _receipt_value(receipt, "heading_sha256")
    source_page = _receipt_value(receipt, "source_page")
    title = _receipt_value(receipt, "title")
    level = _receipt_value(receipt, "level")
    if not isinstance(heading_text, str) or not HEADING.fullmatch(heading_text.strip()):
        return False
    if not isinstance(heading_sha256, str):
        return False
    if hashlib.sha256(heading_text.encode("utf-8")).hexdigest() != heading_sha256:
        return False
    if not isinstance(source_page, int) or not isinstance(level, int):
        return False
    return _fold(title) == _fold(getattr(chunk, "section_title", None))


def _record_summary(record: dict, file_name: str) -> dict:
    pages = record.get("result", {}).get("pages", [])
    sample = "\n".join(str(page.get("md") or page.get("text") or "") for page in pages)[:4000]
    metadata = detect_document_metadata(str(record.get("source_path") or ""), sample)
    chunks = chunk_document(record)
    metrics: Counter[str] = Counter()
    metrics["records_processed"] = 1
    metrics["pages_total"] = len(pages)
    metrics["chunks_total"] = len(chunks)
    metrics["content_chars_total"] = sum(len(chunk.content) for chunk in chunks)

    samples: list[dict] = []
    for chunk in chunks:
        content = str(chunk.content)
        title = chunk.section_title
        path = chunk.section_path
        headings = HEADING.findall(content)
        own_leaf = _leaf_heading_in_content(content, title)
        verified = _verified_receipt(chunk)
        if path:
            metrics["chunks_with_section_path"] += 1
        if title:
            metrics["chunks_with_section_title"] += 1
            if own_leaf:
                metrics["section_chunks_with_own_leaf_heading"] += 1
            else:
                metrics["section_continuations_without_own_leaf_heading"] += 1
                samples.append(
                    {
                        "file": file_name,
                        "chunk_index": chunk.chunk_index,
                        "section_title": title,
                        "page_number": chunk.page_number,
                        "content_preview": content[:240],
                    }
                )
                if NUMERIC_SECTION.match(str(title)):
                    metrics["numeric_section_continuations_without_own_leaf_heading"] += 1
            if verified:
                metrics["section_chunks_with_verified_anchor_receipt"] += 1
        if len(content) < MIN_CHARS:
            metrics["short_chunks_below_min_chars"] += 1
        if len(headings) >= 2 and not path:
            metrics["multi_heading_chunks_without_section_path"] += 1
    return {
        "manufacturer": metadata.manufacturer or "unknown",
        "metrics": metrics,
        "samples": samples,
    }


def build_payload(store: Path, label: str) -> dict:
    files = sorted(store.glob("*.json"), key=lambda path: path.name.casefold())
    totals: Counter[str] = Counter()
    by_manufacturer: dict[str, Counter[str]] = defaultdict(Counter)
    samples: list[dict] = []
    errors: list[dict] = []
    manifest = hashlib.sha256()

    for path in files:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        manifest.update(f"{path.name}\0{len(raw)}\0{digest}\n".encode("utf-8"))
        try:
            record = json.loads(raw)
            result = _record_summary(record, path.name)
        except Exception as exc:  # corpus audit: isolate malformed records
            totals["record_errors"] += 1
            errors.append({"file": path.name, "error_type": type(exc).__name__})
            continue
        totals.update(result["metrics"])
        by_manufacturer[result["manufacturer"]].update(result["metrics"])
        samples.extend(result["samples"])

    samples = sorted(
        samples,
        key=lambda row: hashlib.sha256(
            f"{row['file']}:{row['chunk_index']}".encode("utf-8")
        ).hexdigest(),
    )[:25]
    chunker = ROOT / "src/reingest/chunk.py"
    return {
        "instrument": "s116_raw_store_ab_v1",
        "label": label,
        "status": "local_inventory_complete",
        "source": {
            "store_slug": store.name,
            "json_files": len(files),
            "manifest_sha256": manifest.hexdigest(),
        },
        "implementation": {
            "chunker_sha256": hashlib.sha256(chunker.read_bytes()).hexdigest(),
        },
        "summary": dict(sorted(totals.items())),
        "by_manufacturer": {
            manufacturer: dict(sorted(counter.items()))
            for manufacturer, counter in sorted(by_manufacturer.items())
        },
        "deterministic_samples": samples,
        "errors": errors,
        "cost": {
            "database_get_requests": 0,
            "database_writes": 0,
            "model_calls": 0,
            "network_calls": 0,
        },
        "limitations": [
            "This inventory measures chunk structure, not retrieval or answer quality.",
            "A metadata-backed continuation is not necessarily wrong; it lacks a self-contained byte anchor.",
            "The manufacturer registry may classify some records as unknown.",
            "No result from this inventory authorizes reingestion, schema, serving, or production changes.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = build_payload(args.store, args.label)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
