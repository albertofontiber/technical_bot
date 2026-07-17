#!/usr/bin/env python3
"""Build the exact v5 evidence-derivation registry from source and live chunks."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.supabase_client import SupabaseHTTP
from src.reingest.extraction_derivation import (
    canonical_json_bytes,
    derive_numeric_superscripts,
    validate_derivation,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot"
)
DEFAULT_ENV = DEFAULT_PROJECT / ".env"
DISCOVERY = ROOT / "evals/s162_numeric_superscript_discovery_scan_v1.json"
OUT = ROOT / "config/extraction_derivations_v5.json"
RECEIPT = ROOT / "evals/evidence_derivation_live_read_receipt_v1.json"


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _source_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", re.sub(r"(?i)\.pdf$", "", value).casefold())


def _complete_matches(text: str, token: str) -> list[re.Match[str]]:
    return list(re.finditer(rf"(?<!\d){re.escape(token)}(?!\d)", text))


def _source_line(markdown: str, offset: int) -> str:
    cursor = 0
    for line in markdown.splitlines(keepends=True):
        if cursor <= offset < cursor + len(line):
            return line.rstrip("\r\n")
        cursor += len(line)
    return ""


def _line_span(content: str, source_line: str, token: str) -> tuple[int, int] | None:
    if not source_line:
        return None
    offsets = [match.start() for match in re.finditer(re.escape(source_line), content)]
    matches = _complete_matches(source_line, token)
    if len(offsets) != 1 or len(matches) != 1:
        return None
    return offsets[0] + matches[0].start(), offsets[0] + matches[0].end()


def _client(env_file: Path) -> SupabaseHTTP:
    values = dotenv_values(env_file)
    url = str(values.get("SUPABASE_URL") or "")
    key = str(values.get("SUPABASE_SERVICE_KEY") or "")
    if not url or not key:
        raise RuntimeError("Supabase read credentials are missing")
    return SupabaseHTTP(url=url, service_key=key)


def _fetch_live_rows(client: SupabaseHTTP, shas: list[str]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for extraction_sha in shas:
        rows = client.fetch_rows(
            "chunks_v2",
            select="id,extraction_sha256,chunk_index,content,source_file,page_number",
            filters={"extraction_sha256": f"eq.{extraction_sha}"},
            limit=2000,
        )
        output[extraction_sha] = rows
    return output


def build(project: Path, env_file: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    discovery_raw = DISCOVERY.read_bytes()
    discovery = json.loads(discovery_raw)
    shas = sorted(
        {row["extraction_sha256"] for row in discovery["eligible_candidates"]}
    )
    manifest = json.loads(
        (project / "logs/reingest_manifest.json").read_text(encoding="utf-8")
    )["files"]
    by_sha = {str(row["sha256"]): row for row in manifest}
    store = project / "data/extraction/agent_anthropic-sonnet-45"
    client = _client(env_file)
    try:
        live_by_sha = _fetch_live_rows(client, shas)
    finally:
        client.client.close()

    entries: list[dict[str, Any]] = []
    document_receipts: list[dict[str, Any]] = []
    all_receipts: set[str] = set()
    bound_receipts: set[str] = set()
    unbound_receipts: list[dict[str, Any]] = []
    for extraction_sha in shas:
        source = by_sha[extraction_sha]
        raw = (store / f"{extraction_sha}.json").read_bytes()
        record = json.loads(raw)
        pdf = Path(source["canonical_path"])
        if not pdf.is_absolute():
            pdf = project / pdf
        envelope = derive_numeric_superscripts(raw, pdf)
        integrity = validate_derivation(envelope, source_raw=raw, pdf_path=pdf)
        if integrity:
            raise RuntimeError(f"derivation integrity failed for {extraction_sha}: {integrity}")
        pages = {
            int(page["page"]): str(page.get("md") or "")
            for page in record.get("result", {}).get("pages", [])
            if isinstance(page.get("page"), int)
        }
        live_rows = live_by_sha[extraction_sha]
        replacements: dict[str, list[tuple[int, int, str, str]]] = {}
        rows_by_id = {str(row["id"]): row for row in live_rows}
        for receipt in envelope.manifest["receipts"]:
            receipt_sha = _sha(canonical_json_bytes(receipt))
            if receipt_sha in all_receipts:
                raise RuntimeError(
                    f"duplicate PDF receipt for {extraction_sha}:{receipt_sha}"
                )
            all_receipts.add(receipt_sha)
            source_line = _source_line(
                pages.get(int(receipt["page_number"]), ""),
                int(receipt["source_start"]),
            )
            candidates: list[tuple[dict[str, Any], tuple[int, int]]] = []
            for row in live_rows:
                if _source_key(str(row.get("source_file") or "")) != _source_key(pdf.name):
                    continue
                span = _line_span(
                    str(row.get("content") or ""),
                    source_line,
                    str(receipt["original_token"]),
                )
                if span is not None:
                    candidates.append((row, span))
            if not candidates:
                unbound_receipts.append(
                    {
                        "extraction_sha256": extraction_sha,
                        "source_pdf_receipt_sha256": receipt_sha,
                        "page_number": int(receipt["page_number"]),
                        "source_line_sha256": _sha(source_line.encode("utf-8")),
                        "reason": "exact_source_line_absent_from_live_chunks_v2",
                    }
                )
                continue
            if len(candidates) != 1:
                raise RuntimeError(
                    f"live receipt binding cardinality {len(candidates)} for "
                    f"{extraction_sha}:{receipt_sha}"
                )
            row, span = candidates[0]
            replacements.setdefault(str(row["id"]), []).append(
                (span[0], span[1], str(receipt["derived_token"]), receipt_sha)
            )
            bound_receipts.add(receipt_sha)

        for row_id, patches in replacements.items():
            row = rows_by_id[row_id]
            original = str(row["content"])
            derived = original
            for start, end, replacement, _receipt_sha in sorted(
                patches, key=lambda item: item[0], reverse=True
            ):
                derived = derived[:start] + replacement + derived[end:]
            core = {
                "chunk_id": row_id,
                "extraction_sha256": extraction_sha,
                "source_file": str(row.get("source_file") or ""),
                "chunk_index": int(row["chunk_index"]),
                "original_chunk_content_sha256": _sha(original.encode("utf-8")),
                "derived_chunk_content_sha256": _sha(derived.encode("utf-8")),
                "derived_content": derived,
                "source_pdf_receipt_sha256s": sorted(
                    patch[3] for patch in patches
                ),
                "derivation_manifest_sha256": _sha(
                    canonical_json_bytes(envelope.manifest)
                ),
            }
            entries.append(
                {**core, "chunk_derivation_sha256": _sha(canonical_json_bytes(core))}
            )
        snapshot_rows = [
            {
                "id": row["id"],
                "chunk_index": row["chunk_index"],
                "content_sha256": _sha(str(row.get("content") or "").encode("utf-8")),
            }
            for row in sorted(live_rows, key=lambda item: (item["chunk_index"], item["id"]))
        ]
        document_receipts.append(
            {
                "extraction_sha256": extraction_sha,
                "live_rows": len(live_rows),
                "derived_rows": len(replacements),
                "source_pdf_receipts": len(envelope.manifest["receipts"]),
                "live_snapshot_sha256": _sha(canonical_json_bytes(snapshot_rows)),
            }
        )

    entries.sort(key=lambda row: (row["extraction_sha256"], row["chunk_index"], row["chunk_id"]))
    body = {
        "schema": "runtime_evidence_derivations_v5",
        "version": 5,
        "contract": "active_live_chunk_bound_numeric_superscript_overlay_v5",
        "source_derivation_contract": "numeric_pdf_superscript_overlay_v1",
        "source_discovery_sha256": _sha(discovery_raw),
        "document_snapshots": document_receipts,
        "source_pdf_receipt_count": len(all_receipts),
        "bound_source_pdf_receipt_count": len(bound_receipts),
        "absent_source_pdf_receipt_count": len(unbound_receipts),
        "absent_source_pdf_receipts": unbound_receipts,
        "entry_count": len(entries),
        "entries": entries,
    }
    registry = {**body, "artifact_sha256": _sha(canonical_json_bytes(body))}
    receipt_body = {
        "instrument": "evidence_derivation_live_read_receipt_v1",
        "status": "READ_ONLY_COMPLETE",
        "documents_requested": len(shas),
        "documents_returned": sum(bool(live_by_sha[sha]) for sha in shas),
        "rows_read": sum(len(rows) for rows in live_by_sha.values()),
        "document_snapshots": document_receipts,
        "bound_source_pdf_receipts": len(bound_receipts),
        "absent_source_pdf_receipts": len(unbound_receipts),
        "database_writes": 0,
        "model_calls": 0,
    }
    read_receipt = {
        **receipt_body,
        "result_sha256": _sha(canonical_json_bytes(receipt_body)),
    }
    return registry, read_receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    args = parser.parse_args()
    registry, receipt = build(args.project, args.env_file)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.receipt.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "documents": receipt["documents_returned"],
                "rows_read": receipt["rows_read"],
                "entries": registry["entry_count"],
                "source_pdf_receipts": registry["source_pdf_receipt_count"],
                "bound_source_pdf_receipts": registry[
                    "bound_source_pdf_receipt_count"
                ],
                "absent_source_pdf_receipts": len(
                    registry["absent_source_pdf_receipts"]
                ),
                "artifact_sha256": registry["artifact_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
