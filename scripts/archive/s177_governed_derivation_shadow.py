#!/usr/bin/env python3
"""Replay governed extraction derivations into the current chunker, locally."""
from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reingest.chunk import chunk_document
from src.reingest.extraction_derivation import (
    canonical_json_bytes,
    derive_numeric_superscripts,
    validate_derivation,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot"
)
DISCOVERY = ROOT / "evals/s162_numeric_superscript_discovery_scan_v1.json"
PREREG = ROOT / "evals/s177_governed_derivation_shadow_prereg_v1.yaml"
OUT = ROOT / "evals/s177_governed_derivation_shadow_v1.json"


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _propagated(receipt: dict[str, Any], chunks: list[Any]) -> bool:
    token = str(receipt["derived_token"])
    anchors = {_fold(str(value)) for value in receipt["matched_anchors"]}
    for chunk in chunks:
        folded = _fold(chunk.content)
        if token in chunk.content and sum(anchor in folded for anchor in anchors) >= 2:
            return True
    return False


def build(project: Path) -> dict[str, Any]:
    discovery = json.loads(DISCOVERY.read_text(encoding="utf-8"))
    candidate_shas = sorted(
        {row["extraction_sha256"] for row in discovery["eligible_candidates"]}
    )
    manifest_rows = json.loads(
        (project / "logs/reingest_manifest.json").read_text(encoding="utf-8")
    )["files"]
    source_by_sha = {str(row["sha256"]): row for row in manifest_rows}
    store = project / "data/extraction/agent_anthropic-sonnet-45"
    documents: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for extraction_sha in candidate_shas:
        raw_path = store / f"{extraction_sha}.json"
        raw_before = raw_path.read_bytes()
        source = source_by_sha[extraction_sha]
        pdf_path = Path(source["canonical_path"])
        if not pdf_path.is_absolute():
            pdf_path = project / pdf_path
        try:
            first = derive_numeric_superscripts(raw_before, pdf_path)
            second = derive_numeric_superscripts(raw_before, pdf_path)
            chunks = chunk_document(first.record)
            receipts = first.manifest["receipts"]
            propagated = sum(_propagated(receipt, chunks) for receipt in receipts)
            integrity = validate_derivation(
                first, source_raw=raw_before, pdf_path=pdf_path
            )
            deterministic = (
                canonical_json_bytes(first.record) == canonical_json_bytes(second.record)
                and canonical_json_bytes(first.manifest)
                == canonical_json_bytes(second.manifest)
            )
            raw_after = raw_path.read_bytes()
            documents.append(
                {
                    "extraction_sha256": extraction_sha,
                    "source_file": pdf_path.name,
                    "manufacturer": source.get("manufacturer"),
                    "target_document": extraction_sha
                    == "648e8deba384c0a27f7f255a9149f754acb6cca999c586b0667829e457888c72",
                    "raw_artifact_sha256": _sha(raw_before),
                    "raw_artifact_unchanged": raw_before == raw_after,
                    "derived_artifact_sha256": first.manifest[
                        "derived_artifact_sha256"
                    ],
                    "manifest_sha256": _sha(canonical_json_bytes(first.manifest)),
                    "applied": len(receipts),
                    "abstained": first.manifest["abstained_count"],
                    "propagated_to_chunks": propagated,
                    "chunk_count": len(chunks),
                    "deterministic_replay": deterministic,
                    "integrity_failures": integrity,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "extraction_sha256": extraction_sha,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    target = [row for row in documents if row["target_document"]]
    independent = [row for row in documents if not row["target_document"]]
    applied = sum(row["applied"] for row in documents)
    propagated = sum(row["propagated_to_chunks"] for row in documents)
    checks = {
        "eleven_documents": len(documents) == 11,
        "target_applied_one": sum(row["applied"] for row in target) == 1,
        "independent_applied_at_least_32": sum(
            row["applied"] for row in independent
        )
        >= 32,
        "zero_integrity_failures": all(
            not row["integrity_failures"] for row in documents
        ),
        "deterministic_replay": all(row["deterministic_replay"] for row in documents),
        "all_receipts_propagated_to_chunks": propagated == applied,
        "raw_artifacts_unchanged": all(
            row["raw_artifact_unchanged"] for row in documents
        ),
        "zero_execution_failures": not failures,
    }
    body = {
        "instrument": "s177_governed_derivation_shadow_v1",
        "status": "LOCAL_GO" if all(checks.values()) else "LOCAL_NO_GO",
        "checks": checks,
        "summary": {
            "documents": len(documents),
            "target_documents": len(target),
            "independent_documents": len(independent),
            "applied": applied,
            "propagated_to_chunks": propagated,
            "propagation_rate": propagated / applied if applied else 0,
            "failures": len(failures),
        },
        "documents": documents,
        "failures": failures,
        "constraints": {
            "model_calls": 0,
            "network_calls": 0,
            "database_calls": 0,
            "raw_artifact_writes": 0,
            "chunks_v2_writes": 0,
            "production_or_deployment": False,
        },
    }
    return {**body, "result_sha256": _sha(canonical_json_bytes(body))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = build(args.project)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0 if result["status"] == "LOCAL_GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
