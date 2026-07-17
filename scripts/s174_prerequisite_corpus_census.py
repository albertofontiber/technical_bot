#!/usr/bin/env python3
"""Census frozen non-target prerequisite opportunities with the S126 grammar."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "evals/s174_prerequisite_corpus_census_prereg_v1.yaml"
SNAPSHOT = ROOT / "tmp/s117_m25/derived_snapshot_v2.jsonl.gz"
OUT = ROOT / "evals/s174_prerequisite_corpus_census_v1.json"
EXPECTED_SNAPSHOT_SHA = "a825e4dd02b918ddafebab4419cb416b6edc5f1b823a7a9d423f96718d7b6217"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def window(content: str, starts: list[int], radius: int = 360) -> tuple[int, int, str]:
    center = sum(starts) // len(starts)
    start = max(0, center - radius)
    end = min(len(content), center + radius)
    return start, end, content[start:end]


def main() -> None:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if file_sha(SNAPSHOT) != EXPECTED_SNAPSHOT_SHA:
        raise ValueError("S174 frozen snapshot drift")
    grammar = prereg["preserved_discovery_grammar"]
    access = re.compile(grammar["access_anchor"], re.I)
    relation = re.compile(grammar["prerequisite_relation"], re.I)
    entitlement = re.compile(grammar["entitlement_anchor"], re.I)
    distributive = re.compile(grammar["distributive_unit"], re.I)
    max_distance = int(grammar["maximum_anchor_distance_chars"])
    target_ids = set(prereg["anti_leakage"]["excluded_target_chunk_ids"])

    rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("kind") != "chunk":
                continue
            rows.append(row)
            if str(row.get("id") or "") in target_ids:
                target_rows.append(row)
    if {str(row.get("id")) for row in target_rows} != target_ids:
        raise ValueError("S174 target exclusion rows incomplete")
    excluded_sources = {str(row.get("source_file") or "") for row in target_rows}

    candidates: list[dict[str, Any]] = []
    scanned_chunks = 0
    scanned_sources: set[str] = set()
    for row in rows:
        source_file = str(row.get("source_file") or "")
        if source_file in excluded_sources:
            continue
        scanned_chunks += 1
        scanned_sources.add(source_file)
        content = str(row.get("content") or "")
        title = str(row.get("section_title") or "")
        if re.search(r"\b(index|contents|indice|contenido)\b", title.casefold()):
            continue
        access_matches = list(access.finditer(content))
        relation_matches = list(relation.finditer(content))
        entitlement_matches = list(entitlement.finditer(content))
        distributive_matches = list(distributive.finditer(content))
        pairs: list[tuple[str, re.Match[str], re.Match[str]]] = []
        for left in access_matches:
            for right in relation_matches:
                if abs(left.start() - right.start()) <= max_distance:
                    pairs.append(("access_prerequisite", left, right))
        for left in entitlement_matches:
            for right in distributive_matches:
                if abs(left.start() - right.start()) <= max_distance:
                    pairs.append(("quantified_entitlement", left, right))
        seen_facets: set[str] = set()
        for facet, left, right in sorted(
            pairs, key=lambda item: (item[0], item[1].start(), item[2].start())
        ):
            if facet in seen_facets:
                continue
            seen_facets.add(facet)
            start, end, quote = window(content, [left.start(), right.start()])
            candidates.append(
                {
                    "candidate_id": hashlib.sha256(
                        f"{row.get('id')}:{facet}:{start}:{end}".encode("utf-8")
                    ).hexdigest()[:16],
                    "facet": facet,
                    "chunk_id": str(row.get("id") or ""),
                    "document_id": str(row.get("document_id") or ""),
                    "extraction_sha256": str(row.get("extraction_sha256") or ""),
                    "source_file": source_file,
                    "manufacturer": str(row.get("manufacturer") or "unknown"),
                    "product_model": str(row.get("product_model") or "unknown"),
                    "chunk_index": row.get("chunk_index"),
                    "page_number": row.get("page_number"),
                    "section_title": title,
                    "start": start,
                    "end": end,
                    "left_anchor": left.group(0),
                    "right_anchor": right.group(0),
                    "quote": quote,
                    "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                    "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    "exact_source_receipt": quote == content[start:end],
                }
            )

    facets = Counter(row["facet"] for row in candidates)
    facet_manufacturers = {
        facet: sorted(
            {row["manufacturer"] for row in candidates if row["facet"] == facet}
        )
        for facet in sorted(facets)
    }
    checks = {
        "all_target_sources_excluded": all(
            row["source_file"] not in excluded_sources for row in candidates
        ),
        "all_exact_source_receipts": all(
            row["exact_source_receipt"] for row in candidates
        ),
        "no_candidate_cap": True,
        "both_facets_scanned": set(facets) == {
            "access_prerequisite",
            "quantified_entitlement",
        },
    }
    body = {
        "instrument": "s174_prerequisite_corpus_census_v1",
        "status": "VALID_CENSUS_REQUIRES_BLINDED_ADJUDICATION"
        if all(checks.values())
        else "VALID_CENSUS_INSUFFICIENT_FACET_APPLICABILITY",
        "snapshot": {
            "sha256": EXPECTED_SNAPSHOT_SHA,
            "total_chunks": len(rows),
            "scanned_non_target_chunks": scanned_chunks,
            "scanned_non_target_sources": len(scanned_sources),
            "excluded_target_sources": sorted(excluded_sources),
            "excluded_target_chunk_ids": sorted(target_ids),
        },
        "checks": checks,
        "summary": {
            "candidate_count": len(candidates),
            "facets": dict(sorted(facets.items())),
            "facet_manufacturers": facet_manufacturers,
            "note": "Candidates are scanner hits, not adjudicated true positives.",
        },
        "candidates": candidates,
        "authorization": {
            "blinded_adjudication": bool(candidates),
            "runtime_change": False,
            "target_probe": False,
            "production": False,
            "facts_moved_to_ok": 0,
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_calls": 0,
            "usd": 0,
        },
    }
    body["result_sha256"] = stable_sha(body)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
