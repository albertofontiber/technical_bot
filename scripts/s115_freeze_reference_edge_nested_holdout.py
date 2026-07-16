#!/usr/bin/env python3
"""Seal untouched section-reference HYQs before S115 implementation."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HYQ = ROOT / "evals/s99_hyq_generated.jsonl"
FREEZE = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
INITIAL = ROOT / "evals/s114_procedure_bundle_heldout_replay_v1.json"
DIAGNOSTIC = ROOT / "evals/s114_procedure_bundle_section_challenge_v1.json"
OUT = ROOT / "evals/s115_reference_edge_nested_holdout_freeze_v1.json"
PER_MANUFACTURER_CAP = 10
SECTION_REFERENCE = re.compile(
    r"\b(?:cap(?:[ií]tulo)?\.?|secci[oó]n|section|chapter)\s*"
    r"(\d+(?:\.\d+)+)\b",
    re.I,
)
PROCEDURAL = re.compile(
    r"\b(?:como|how|configur\w*|program\w*|anad\w*|add\w*|comprob\w*|"
    r"check\w*|diagn\w*|leer|read\w*|instal\w*|install\w*|ajust\w*|set|"
    r"cambi\w*|chang\w*)\b",
    re.I,
)


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _rank(manufacturer: str, product: str, chunk_id: str, question: str) -> str:
    raw = "|".join((manufacturer, product, chunk_id, question))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    initial = json.loads(INITIAL.read_text(encoding="utf-8"))
    diagnostic = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
    excluded_chunks = {row["chunk_id"] for row in diagnostic["rows"]}
    excluded_pairs = {(row["served_id"], row["question"]) for row in initial["rows"]}
    rows_by_id = {
        str(row["id"]): row
        for rows in freeze["candidate_scopes"].values()
        for row in rows
    }
    scope_by_id = {
        str(row["id"]): scope_key
        for scope_key, rows in freeze["candidate_scopes"].items()
        for row in rows
    }
    questions_by_chunk: dict[str, list[str]] = defaultdict(list)
    with HYQ.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            chunk_id = str(row.get("chunk_id") or "")
            if (
                chunk_id not in rows_by_id
                or chunk_id in excluded_chunks
                or row.get("origin") != "synthetic"
            ):
                continue
            for question in row.get("questions") or []:
                if (
                    question
                    and PROCEDURAL.search(_fold(question))
                    and (chunk_id, str(question)) not in excluded_pairs
                ):
                    questions_by_chunk[chunk_id].append(str(question))

    by_manufacturer: dict[str, list[dict]] = defaultdict(list)
    for chunk_id, questions in questions_by_chunk.items():
        source = rows_by_id[chunk_id]
        if not SECTION_REFERENCE.search(str(source.get("content") or "")):
            continue
        manufacturer = str(source.get("manufacturer") or "")
        product = str(source.get("product_model") or "")
        if not manufacturer or not product:
            continue
        question = min(
            set(questions), key=lambda value: _rank(manufacturer, product, chunk_id, value)
        )
        by_manufacturer[manufacturer].append(
            {
                "manufacturer": manufacturer,
                "product_model": product,
                "chunk_id": chunk_id,
                "question": question,
                "rank_sha256": _rank(manufacturer, product, chunk_id, question),
                "scope_key": scope_by_id[chunk_id],
            }
        )

    sample = [
        item
        for manufacturer in sorted(by_manufacturer)
        for item in sorted(
            by_manufacturer[manufacturer], key=lambda value: value["rank_sha256"]
        )[:PER_MANUFACTURER_CAP]
    ]
    payload = {
        "instrument": "s115_reference_edge_nested_holdout_freeze_v1",
        "status": "sealed_not_replayed",
        "base_scope_freeze_sha256": hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
        "diagnostic_challenge_sha256": hashlib.sha256(DIAGNOSTIC.read_bytes()).hexdigest(),
        "sample_count": len(sample),
        "manufacturer_count": len({item["manufacturer"] for item in sample}),
        "sample": sample,
        "cost_receipt": {
            "database_get_requests": 0,
            "database_writes": 0,
            "model_calls": 0,
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "sample_count": payload["sample_count"],
                "manufacturer_count": payload["manufacturer_count"],
                "artifact_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
                "cost_receipt": payload["cost_receipt"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
