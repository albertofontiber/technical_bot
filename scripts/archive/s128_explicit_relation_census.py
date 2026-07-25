#!/usr/bin/env python3
"""Deterministic local candidate census for explicit technical relations."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals" / "s128_explicit_relation_census_prereg_v1.yaml"
OUTPUT = ROOT / "evals" / "s128_explicit_relation_census_candidates_v1.json"

PREDICATE_STEMS = {
    "compatible_with": (
        "compatib",
        "homologad",
        "approved for",
        "aprobado para",
        "listed for",
        "indicado para",
    ),
    "supports": (
        "soport",
        "admit",
        "support",
        "accept",
        "acepta",
    ),
    "listed_for": (
        "lista de",
        "list of",
        "modelos",
        "models",
        "dispositivos",
        "devices",
        "equipos",
        "equipment",
    ),
    "requires": (
        "requier",
        "requires",
        "required",
        "debe utilizarse",
        "deberá utilizarse",
        "must be used",
        "only with",
        "solo con",
        "únicamente con",
    ),
    "uses_protocol": ("protocolo", "protocol"),
    "connects_to": (
        "conect",
        "connect",
        "cablead",
        "wired to",
        "se monta en",
        "mounts on",
    ),
    "excludes": (
        "incompatib",
        "not compatible",
        "no compatible",
        "no debe conect",
        "must not be connect",
        "do not connect",
    ),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def _candidate_span(content: str, match_start: int, match_end: int) -> tuple[int, int]:
    """Return one bounded source line/sentence without crossing a paragraph."""
    paragraph_start = content.rfind("\n\n", 0, match_start) + 2
    paragraph_end = content.find("\n\n", match_end)
    if paragraph_end < 0:
        paragraph_end = len(content)
    line_start = content.rfind("\n", paragraph_start, match_start) + 1
    line_end = content.find("\n", match_end, paragraph_end)
    if line_end < 0:
        line_end = paragraph_end
    start, end = line_start, line_end
    if end - start < 40:
        start, end = paragraph_start, paragraph_end
    if end - start > 700:
        start = max(paragraph_start, match_start - 280)
        end = min(paragraph_end, match_end + 360)
    return start, end


def _load_frozen_documents() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    for key, spec in (
        ("snapshot", prereg["inputs"]["snapshot"]),
        ("catalog", prereg["inputs"]["catalog"]),
        ("relation_graph", prereg["inputs"]["relation_graph"]),
    ):
        path = ROOT / spec["path"]
        if _sha(path) != spec["sha256"]:
            raise RuntimeError(f"S128 frozen {key} drift")
    documents = {row["document_id"]: row for row in prereg["selection"]["documents"]}
    if len(documents) != 12:
        raise RuntimeError("S128 requires exactly 12 distinct documents")
    return prereg, documents


def build_payload() -> dict[str, Any]:
    prereg, frozen = _load_frozen_documents()
    chunks: list[dict[str, Any]] = []
    with gzip.open(
        ROOT / prereg["inputs"]["snapshot"]["path"], "rt", encoding="utf-8"
    ) as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("kind") != "chunk" or row.get("document_id") not in frozen:
                continue
            expected = frozen[str(row["document_id"])]
            if row.get("source_file") != expected["source_file"]:
                raise RuntimeError("S128 document/source binding drift")
            chunks.append(row)

    seen: set[tuple[str, int, int]] = set()
    candidates = []
    for row in sorted(
        chunks,
        key=lambda item: (
            str(item.get("source_file") or ""),
            int(item.get("chunk_index") or 0),
            str(item.get("id") or ""),
        ),
    ):
        content = str(row.get("content") or "")
        folded = _fold(content)
        for predicate, stems in sorted(PREDICATE_STEMS.items()):
            for stem in stems:
                for match in re.finditer(re.escape(_fold(stem)), folded):
                    start, end = _candidate_span(content, match.start(), match.end())
                    key = (str(row["id"]), start, end)
                    if key in seen:
                        continue
                    seen.add(key)
                    quote = content[start:end]
                    matched = sorted(
                        family
                        for family, family_stems in PREDICATE_STEMS.items()
                        if any(_fold(term) in _fold(quote) for term in family_stems)
                    )
                    frozen_doc = frozen[str(row["document_id"])]
                    candidates.append(
                        {
                            "candidate_id": f"relcand-{len(candidates) + 1:04d}",
                            "class_id": frozen_doc["class_id"],
                            "governed_subject_ids": frozen_doc["governed_ids"],
                            "predicate_candidates": matched,
                            "document_id": row["document_id"],
                            "source_file": row["source_file"],
                            "extraction_sha256": row.get("extraction_sha256"),
                            "chunk_id": row["id"],
                            "chunk_index": row.get("chunk_index"),
                            "page_number": row.get("page_number"),
                            "section_title": row.get("section_title"),
                            "section_path": row.get("section_path"),
                            "start": start,
                            "end": end,
                            "quote": quote,
                            "quote_sha256": hashlib.sha256(
                                quote.encode("utf-8")
                            ).hexdigest(),
                            "structured_surface": (
                                "table" if "|" in quote else
                                "list" if re.search(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", quote) else
                                "prose"
                            ),
                        }
                    )

    document_receipts = []
    for document_id, spec in sorted(frozen.items()):
        rows = [row for row in chunks if row["document_id"] == document_id]
        extractions = sorted({str(row.get("extraction_sha256") or "") for row in rows})
        document_receipts.append(
            {
                "class_id": spec["class_id"],
                "document_id": document_id,
                "source_file": spec["source_file"],
                "chunk_count": len(rows),
                "extraction_sha256s": extractions,
                "chunk_manifest_sha256": _canonical(
                    [
                        {
                            "id": row["id"],
                            "chunk_index": row.get("chunk_index"),
                            "content_sha256": hashlib.sha256(
                                str(row.get("content") or "").encode("utf-8")
                            ).hexdigest(),
                        }
                        for row in sorted(
                            rows,
                            key=lambda item: (
                                int(item.get("chunk_index") or 0), str(item["id"])
                            ),
                        )
                    ]
                ),
            }
        )

    return {
        "instrument": "s128_explicit_relation_census_candidates_v1",
        "status": "CANDIDATES_ONLY_NOT_ADJUDICATED",
        "prereg_sha256": _sha(PREREG),
        "document_receipts": document_receipts,
        "candidate_count": len(candidates),
        "candidates_sha256": _canonical(candidates),
        "candidates": candidates,
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
        "credit": {"facts_moved_to_ok": 0, "official_funnel_change": False},
    }


def main() -> int:
    payload = build_payload()
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "documents": len(payload["document_receipts"]),
                "candidates": payload["candidate_count"],
                "cost": payload["cost"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
