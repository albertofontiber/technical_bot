#!/usr/bin/env python3
"""Read-only discovery scan for geometry-bound numeric superscripts in PDFs.

The scan uses PDF glyph metadata only. It does not infer that a flattened token
is an exponent: it records an overlay candidate when the PDF itself marks a
numeric span as superscript and the immediately preceding span ends in digits.
An overlay is mechanically eligible only when the flattened token occurs once
as a complete token in the corresponding immutable LlamaParse page.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import fitz


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot"
)
TARGET_SHA256 = "648e8deba384c0a27f7f255a9149f754acb6cca999c586b0667829e457888c72"
_BASE_DIGITS = re.compile(r"(\d+)$")


def _stable_sha(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _page_markdown(record: dict[str, Any], page_number: int) -> str:
    for page in record.get("result", {}).get("pages", []):
        if page.get("page") == page_number:
            return str(page.get("md") or page.get("text") or "")
    return ""


def _complete_token_occurrences(text: str, token: str) -> int:
    return len(re.findall(rf"(?<![\w.]){re.escape(token)}(?![\w.])", text))


def _candidate(
    *,
    previous: dict[str, Any],
    script: dict[str, Any],
) -> dict[str, Any] | None:
    script_text = str(script.get("text") or "").strip()
    if not script_text.isdigit() or not (int(script.get("flags") or 0) & 1):
        return None
    previous_text = str(previous.get("text") or "").rstrip()
    match = _BASE_DIGITS.search(previous_text)
    if match is None:
        return None
    base = match.group(1)
    base_size = float(previous.get("size") or 0)
    script_size = float(script.get("size") or 0)
    if base_size <= 0 or script_size <= 0:
        return None
    ratio = script_size / base_size
    base_origin = previous.get("origin") or (0, 0)
    script_origin = script.get("origin") or (0, 0)
    baseline_delta = float(base_origin[1]) - float(script_origin[1])
    base_bbox = previous.get("bbox") or (0, 0, 0, 0)
    script_bbox = script.get("bbox") or (0, 0, 0, 0)
    horizontal_gap = float(script_bbox[0]) - float(base_bbox[2])
    if ratio > 0.80 or baseline_delta < 0.5:
        return None
    if horizontal_gap < -0.25 or horizontal_gap > max(1.25, base_size * 0.30):
        return None
    return {
        "base": base,
        "script": script_text,
        "flattened_token": base + script_text,
        "explicit_markup": f"{base}<sup>{script_text}</sup>",
        "base_font_size": round(base_size, 6),
        "script_font_size": round(script_size, 6),
        "font_size_ratio": round(ratio, 6),
        "baseline_delta_points": round(baseline_delta, 6),
        "horizontal_gap_points": round(horizontal_gap, 6),
        "base_bbox": [round(float(value), 6) for value in base_bbox],
        "script_bbox": [round(float(value), 6) for value in script_bbox],
    }


def scan(project: Path, limit: int = 0) -> dict[str, Any]:
    manifest_path = project / "logs/reingest_manifest.json"
    extraction_store = project / "data/extraction/agent_anthropic-sonnet-45"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
    if limit:
        manifest = manifest[:limit]

    candidates: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    documents_with_any_superscript: set[str] = set()
    raw_superscript_spans = 0
    pages_scanned = 0

    fitz.TOOLS.mupdf_display_errors(False)
    for document in manifest:
        sha = str(document["sha256"])
        path = Path(document["canonical_path"])
        if not path.is_absolute():
            path = project / path
        extraction_path = extraction_store / f"{sha}.json"
        try:
            extraction = (
                json.loads(extraction_path.read_text(encoding="utf-8"))
                if extraction_path.exists()
                else None
            )
            with fitz.open(path) as pdf:
                for page_index, page in enumerate(pdf):
                    pages_scanned += 1
                    blocks = page.get_text("dict", sort=True).get("blocks", [])
                    for block in blocks:
                        for line in block.get("lines", []):
                            spans = line.get("spans", [])
                            previous_nonblank: dict[str, Any] | None = None
                            for span in spans:
                                text = str(span.get("text") or "")
                                if int(span.get("flags") or 0) & 1 and text.strip():
                                    raw_superscript_spans += 1
                                    documents_with_any_superscript.add(sha)
                                if previous_nonblank is not None:
                                    row = _candidate(previous=previous_nonblank, script=span)
                                    if row is not None:
                                        page_number = page_index + 1
                                        markdown = (
                                            _page_markdown(extraction, page_number)
                                            if extraction is not None
                                            else ""
                                        )
                                        occurrences = _complete_token_occurrences(
                                            markdown, row["flattened_token"]
                                        )
                                        candidates.append(
                                            {
                                                "extraction_sha256": sha,
                                                "manufacturer": document.get("manufacturer"),
                                                "source_file": path.name,
                                                "page_number": page_number,
                                                **row,
                                                "llamaparse_record_present": extraction is not None,
                                                "flattened_token_occurrences": occurrences,
                                                "mechanically_eligible": occurrences == 1,
                                                "target_document": sha == TARGET_SHA256,
                                            }
                                        )
                                if text.strip():
                                    previous_nonblank = span
        except Exception as exc:  # discovery must finish and expose unreadable PDFs
            failures.append(
                {
                    "extraction_sha256": sha,
                    "source_file": path.name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    eligible = [row for row in candidates if row["mechanically_eligible"]]
    held_out = [row for row in eligible if not row["target_document"]]
    body: dict[str, Any] = {
        "instrument": "s162_numeric_superscript_discovery_scan_v1",
        "status": "READ_ONLY_DISCOVERY",
        "population": {
            "manifest_documents": len(manifest),
            "pages_scanned": pages_scanned,
            "documents_with_any_pdf_superscript": len(documents_with_any_superscript),
            "raw_pdf_superscript_spans": raw_superscript_spans,
            "geometry_bound_numeric_candidates": len(candidates),
            "uniquely_mappable_to_llamaparse_page": len(eligible),
            "held_out_uniquely_mappable": len(held_out),
            "failures": len(failures),
        },
        "eligible_by_manufacturer": dict(
            sorted(Counter(str(row["manufacturer"]) for row in eligible).items())
        ),
        "eligible_candidates": eligible,
        "ineligible_candidates": [
            row for row in candidates if not row["mechanically_eligible"]
        ],
        "failures": failures,
        "constraints": {
            "database_reads": 0,
            "database_writes": 0,
            "model_calls": 0,
            "raw_extraction_mutations": 0,
        },
    }
    return {**body, "result_sha256": _stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = scan(args.project, args.limit)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "population": result["population"],
        "eligible_by_manufacturer": result["eligible_by_manufacturer"],
        "result_sha256": result["result_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
