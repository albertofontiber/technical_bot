#!/usr/bin/env python3
"""Scan the frozen independent cohort for generic prerequisite opportunities."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reingest.chunk import chunk_document

PREREG = ROOT / "evals" / "s126_prerequisite_independent_prereg_v1.yaml"
STORE = ROOT / "tmp" / "s116_independent_holdout" / "extraction" / "agent_anthropic-sonnet-45"
OUTPUT = ROOT / "evals" / "s126_prerequisite_independent_scan_v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _window(content: str, starts: list[int], radius: int = 360) -> tuple[int, int, str]:
    center = sum(starts) // len(starts)
    start = max(0, center - radius)
    end = min(len(content), center + radius)
    return start, end, content[start:end]


def build_payload() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    chunker = ROOT / prereg["frozen_implementation"]["chunker_path"]
    if _sha(chunker) != prereg["frozen_implementation"]["chunker_sha256"]:
        raise ValueError("frozen chunker drift")
    grammar = prereg["discovery_grammar"]
    access = re.compile(grammar["access_anchor"], re.I)
    relation = re.compile(grammar["prerequisite_relation"], re.I)
    entitlement = re.compile(grammar["entitlement_anchor"], re.I)
    distributive = re.compile(grammar["distributive_unit"], re.I)
    max_distance = grammar["maximum_anchor_distance_chars"]
    documents = []
    opportunities = []
    for document in prereg["cohort"]["documents"]:
        path = STORE / f"{document['pdf_sha256']}.json"
        if not path.is_file() or _sha(path) != document["raw_record_sha256"]:
            raise ValueError(f"raw record drift: {document['id']}")
        record = json.loads(path.read_text(encoding="utf-8"))
        chunks = chunk_document(record)
        documents.append({
            "id": document["id"],
            "manufacturer": document["manufacturer"],
            "chunks": len(chunks),
        })
        for chunk in chunks:
            content = chunk.content
            lowered_title = (chunk.section_title or "").casefold()
            index_only = bool(re.search(r"\b(index|contents|indice|contenido)\b", lowered_title))
            access_matches = list(access.finditer(content))
            relation_matches = list(relation.finditer(content))
            entitlement_matches = list(entitlement.finditer(content))
            distributive_matches = list(distributive.finditer(content))
            pairs = []
            for left in access_matches:
                for right in relation_matches:
                    if abs(left.start() - right.start()) <= max_distance:
                        pairs.append(("access_prerequisite", left, right))
            for left in entitlement_matches:
                for right in distributive_matches:
                    if abs(left.start() - right.start()) <= max_distance:
                        pairs.append(("quantified_entitlement", left, right))
            seen_facets = set()
            for facet, left, right in pairs:
                if facet in seen_facets or index_only:
                    continue
                seen_facets.add(facet)
                start, end, quote = _window(content, [left.start(), right.start()])
                opportunities.append({
                    "document_id": document["id"],
                    "manufacturer": document["manufacturer"],
                    "filename": document["filename"],
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "facet": facet,
                    "start": start,
                    "end": end,
                    "quote": quote,
                    "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                    "exact_source_receipt": quote == content[start:end],
                })
    manufacturers = {row["manufacturer"] for row in documents}
    checks = {
        "exact_documents": len(documents) == 8,
        "manufacturers_at_least_four": len(manufacturers) >= 4,
        "all_exact_source_receipts": all(
            row["exact_source_receipt"] for row in opportunities
        ),
    }
    return {
        "instrument": "s126_scan_independent_prerequisites_v1",
        "status": "VALID_SCAN_REQUIRES_BLINDED_ADJUDICATION" if all(checks.values()) else "INVALID_SCAN",
        "checks": checks,
        "documents": documents,
        "opportunity_count": len(opportunities),
        "opportunities": opportunities,
        "cost": {"model_calls": 0, "network_calls": 0, "database_writes": 0},
        "release_authorization": False,
    }


def main() -> int:
    payload = build_payload()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "opportunity_count": payload["opportunity_count"],
        "checks": payload["checks"],
    }, sort_keys=True))
    return 0 if payload["status"].startswith("VALID_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
