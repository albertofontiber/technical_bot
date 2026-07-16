#!/usr/bin/env python3
"""Fresh, zero-call audit of byte-backed section continuity."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
OUT = ROOT / "evals/s116_section_lineage_audit_v1.json"
EXCLUDED = {
    "European Safety Systems",
    "LDA audioTech",
    "Sensitron",
    "Spectrex",
    "Xtralis",
}
HEX64 = re.compile(r"[0-9a-fA-F]{64}")
SECTION = re.compile(r"^\s*(\d+(?:\.\d+)+)(?:\s|$)")
TOC_ENTRY = re.compile(
    r"(?im)^[ \t]*(?:\*\*)?\d+(?:\.\d+)+[^\n]{0,160}\.{4,}\s*\d+[ \t]*(?:\*\*)?$"
)


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _section(row: dict) -> str | None:
    match = SECTION.match(str(row.get("section_title") or ""))
    return match.group(1) if match else None


def _heading(row: dict, section: str) -> bool:
    pattern = re.compile(
        rf"(?im)^[ \t]*#{{1,6}}[ \t]*{re.escape(section)}(?:[ \t]|$)"
    )
    return bool(pattern.search(str(row.get("content") or "")[:400]))


def _toc(row: dict) -> bool:
    return len(TOC_ENTRY.findall(str(row.get("content") or ""))) >= 3


def _identity(row: dict) -> tuple[str, str] | None:
    document = str(row.get("document_id") or "")
    extraction = str(row.get("extraction_sha256") or "")
    return (document, extraction.lower()) if document and HEX64.fullmatch(extraction) else None


def classify_rows(rows: list[dict]) -> list[dict]:
    by_identity: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        identity = _identity(row)
        if identity is not None:
            by_identity[identity].append(row)
    output = []
    for row in rows:
        section = _section(row)
        identity = _identity(row)
        index = row.get("chunk_index")
        if section is None or identity is None or not isinstance(index, int):
            continue
        key = _fold(row.get("section_title"))
        compatible = [
            sibling
            for sibling in by_identity[identity]
            if isinstance(sibling.get("chunk_index"), int)
            and abs(sibling["chunk_index"] - index) <= 2
            and _fold(sibling.get("section_title")) == key
            and _heading(sibling, section)
        ]
        valid = [sibling for sibling in compatible if not _toc(sibling)]
        if _heading(row, section) and not _toc(row):
            classification = "self_byte_anchor"
        elif len(valid) == 1:
            classification = "unique_sibling_anchor"
        elif len(valid) > 1:
            classification = "ambiguous_anchor"
        elif compatible:
            classification = "toc_only"
        else:
            classification = "missing_byte_anchor"
        output.append(
            {
                "id": str(row.get("id") or ""),
                "manufacturer": row.get("manufacturer"),
                "product_model": row.get("product_model"),
                "document_id": identity[0],
                "extraction_sha256": identity[1],
                "chunk_index": index,
                "section_title": row.get("section_title"),
                "section": section,
                "classification": classification,
                "compatible_anchor_ids": [str(item.get("id") or "") for item in valid],
                "content_preview": str(row.get("content") or "")[:240],
            }
        )
    return output


def build_payload(source: dict) -> dict:
    unique = {
        str(row["id"]): row
        for rows in source["candidate_scopes"].values()
        for row in rows
        if row.get("id") and str(row.get("manufacturer") or "") not in EXCLUDED
    }
    classified = classify_rows(list(unique.values()))
    counts = Counter(row["classification"] for row in classified)
    by_manufacturer = defaultdict(Counter)
    for row in classified:
        by_manufacturer[str(row.get("manufacturer") or "unknown")][
            row["classification"]
        ] += 1
    samples = {}
    for label in sorted(counts):
        candidates = [row for row in classified if row["classification"] == label]
        samples[label] = sorted(
            candidates,
            key=lambda row: hashlib.sha256(row["id"].encode("utf-8")).hexdigest(),
        )[:10]
    manufacturers = sorted({str(row.get("manufacturer") or "") for row in classified})
    return {
        "instrument": "s116_section_lineage_audit_v1",
        "status": "fresh_local_audit_complete",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "excluded_manufacturers": sorted(EXCLUDED),
        "eligible_manufacturers": manufacturers,
        "summary": {
            "unique_scope_rows": len(unique),
            "eligible_numeric_section_rows": len(classified),
            "manufacturers": len(manufacturers),
            "documents": len({row["document_id"] for row in classified}),
            "classifications": dict(sorted(counts.items())),
            "design_section_lineage": (
                "GO" if counts["missing_byte_anchor"] > 0 else "NO_GO_NO_OBSERVED_GAP"
            ),
            "database_get_requests": 0,
            "database_writes": 0,
            "model_calls": 0,
        },
        "by_manufacturer": {
            manufacturer: dict(sorted(counter.items()))
            for manufacturer, counter in sorted(by_manufacturer.items())
        },
        "samples": samples,
        "limitations": [
            "This is a seven-manufacturer local slice, not a full 31-manufacturer corpus estimate.",
            "Metadata/byte disagreement proves lineage loss, not semantic answer relevance.",
            "The audit authorizes design only; no migration, re-ingestion or serving change.",
        ],
    }


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    payload = build_payload(source)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
