#!/usr/bin/env python3
"""Build the local S162 target and document-disjoint qualification packet."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reingest.superscript_overlay import preserve_numeric_superscripts


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot"
)
DISCOVERY = ROOT / "evals/s162_numeric_superscript_discovery_scan_v1.json"
TARGET_SHA256 = "648e8deba384c0a27f7f255a9149f754acb6cca999c586b0667829e457888c72"


def _stable_sha(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _line_at(text: str, offset: int) -> str:
    cursor = 0
    for line in text.splitlines(keepends=True):
        if cursor <= offset < cursor + len(line):
            return line.rstrip("\r\n")
        cursor += len(line)
    return ""


def build(project: Path) -> dict[str, Any]:
    manifest = json.loads(
        (project / "logs/reingest_manifest.json").read_text(encoding="utf-8")
    )["files"]
    by_sha = {str(row["sha256"]): row for row in manifest}
    discovery = json.loads(DISCOVERY.read_text(encoding="utf-8"))
    candidate_shas = sorted(
        {row["extraction_sha256"] for row in discovery["eligible_candidates"]}
    )
    extraction_store = project / "data/extraction/agent_anthropic-sonnet-45"

    documents: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for sha in candidate_shas:
        source = by_sha[sha]
        pdf_path = Path(source["canonical_path"])
        if not pdf_path.is_absolute():
            pdf_path = project / pdf_path
        extraction_path = extraction_store / f"{sha}.json"
        try:
            raw = json.loads(extraction_path.read_text(encoding="utf-8"))
            result = preserve_numeric_superscripts(raw, pdf_path)
            original_pages = {
                page.get("page"): str(page.get("md") or "")
                for page in raw.get("result", {}).get("pages", [])
            }
            rows = []
            for receipt in result.applied:
                original = original_pages[receipt["page_number"]]
                derived_page = next(
                    page
                    for page in result.record["result"]["pages"]
                    if page.get("page") == receipt["page_number"]
                )["md"]
                prior_delta = sum(
                    len(other["derived_token"]) - len(other["original_token"])
                    for other in result.applied
                    if other["page_number"] == receipt["page_number"]
                    and other["source_start"] < receipt["source_start"]
                )
                derived_offset = receipt["source_start"] + prior_delta
                rows.append(
                    {
                        **receipt,
                        "original_markdown_line": _line_at(original, receipt["source_start"]),
                        "derived_markdown_line": _line_at(
                            derived_page, derived_offset
                        ),
                    }
                )
            documents.append(
                {
                    "extraction_sha256": sha,
                    "manufacturer": source.get("manufacturer"),
                    "source_file": pdf_path.name,
                    "target_document": sha == TARGET_SHA256,
                    "applied": rows,
                    "abstained": list(result.abstained),
                    "raw_record_unchanged": raw == json.loads(
                        extraction_path.read_text(encoding="utf-8")
                    ),
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "extraction_sha256": sha,
                    "source_file": pdf_path.name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    target = [row for row in documents if row["target_document"]]
    independent = [row for row in documents if not row["target_document"]]
    body: dict[str, Any] = {
        "instrument": "s162_numeric_superscript_overlay_qualification_packet_v1",
        "status": "LOCAL_PACKET_BUILT",
        "target": target,
        "independent": independent,
        "summary": {
            "documents_processed": len(documents),
            "failures": len(failures),
            "target_documents": len(target),
            "target_applied": sum(len(row["applied"]) for row in target),
            "independent_documents": len(independent),
            "independent_documents_with_applied": sum(
                bool(row["applied"]) for row in independent
            ),
            "independent_applied": sum(len(row["applied"]) for row in independent),
            "independent_abstained": sum(
                len(row["abstained"]) for row in independent
            ),
            "raw_records_unchanged": all(
                row["raw_record_unchanged"] for row in documents
            ),
        },
        "failures": failures,
        "constraints": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
            "raw_extraction_writes": 0,
        },
    }
    return {**body, "result_sha256": _stable_sha(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals/s162_numeric_superscript_overlay_packet_v1.json",
    )
    args = parser.parse_args()
    result = build(args.project)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
