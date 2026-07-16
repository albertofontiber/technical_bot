#!/usr/bin/env python3
"""Replay a preregistered explicit-section-reference held-out challenge."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.procedure_bundle_coverage import (
    _SECTION_REFERENCE,
    select_procedure_bundle_coverage,
    verify_source_span_receipt,
)

SELECTOR = ROOT / "src/rag/procedure_bundle_coverage.py"
HYQ = ROOT / "evals/s99_hyq_generated.jsonl"
FREEZE = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
INITIAL = ROOT / "evals/s114_procedure_bundle_heldout_replay_v1.json"
OUT = ROOT / "evals/s114_procedure_bundle_section_challenge_v1.json"
EXPECTED_HASHES = {
    SELECTOR: "cbd3902b823fa7d7d4fb4c9c3f6ba3781a5492c0b2e7be6364291d1cd9461a76",
    HYQ: "5fb56f1739f8713c263d331b5393ef1904d9a5311ba3f1ac15bd81828b86f8e7",
    FREEZE: "227e808a2ba2308acce89f90722fd46a63bad30aae0cde630191154b4ff07d94",
    INITIAL: "f8c40033faf61582729ecd7970f95c45bdcc23bdf40459ea08b163289cc22300",
}
PER_MANUFACTURER_CAP = 10
PROCEDURAL = re.compile(
    r"\b(?:como|how|configur\w*|program\w*|anad\w*|add\w*|comprob\w*|"
    r"check\w*|diagn\w*|leer|read\w*|instal\w*|install\w*|ajust\w*|set|"
    r"cambi\w*|chang\w*)\b",
    re.I,
)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _rank(manufacturer: str, product: str, chunk_id: str, question: str) -> str:
    value = "|".join((manufacturer, product, chunk_id, question))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_payload() -> dict:
    observed_hashes = {str(path.relative_to(ROOT)): _sha256_path(path) for path in EXPECTED_HASHES}
    if any(_sha256_path(path) != expected for path, expected in EXPECTED_HASHES.items()):
        raise RuntimeError("frozen selector or held-out input changed")

    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    initial = json.loads(INITIAL.read_text(encoding="utf-8"))
    used = {(row["served_id"], row["question"]) for row in initial["rows"]}
    scopes = freeze["candidate_scopes"]
    scope_for_row: dict[str, str] = {}
    rows_by_id: dict[str, dict] = {}
    for scope_key, rows in scopes.items():
        for row in rows:
            row_id = str(row["id"])
            rows_by_id[row_id] = row
            scope_for_row[row_id] = scope_key

    questions_by_chunk: dict[str, list[str]] = defaultdict(list)
    with HYQ.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            chunk_id = str(row.get("chunk_id") or "")
            if chunk_id not in rows_by_id or row.get("origin") != "synthetic":
                continue
            for question in row.get("questions") or []:
                if (
                    question
                    and PROCEDURAL.search(_fold(question))
                    and (chunk_id, str(question)) not in used
                ):
                    questions_by_chunk[chunk_id].append(str(question))

    eligible = []
    for chunk_id, questions in questions_by_chunk.items():
        source = rows_by_id[chunk_id]
        if not _SECTION_REFERENCE.search(str(source.get("content") or "")):
            continue
        manufacturer = str(source.get("manufacturer") or "")
        product = str(source.get("product_model") or "")
        ranked_questions = sorted(
            set(questions), key=lambda question: _rank(manufacturer, product, chunk_id, question)
        )
        if not manufacturer or not product or not ranked_questions:
            continue
        question = ranked_questions[0]
        eligible.append(
            {
                "manufacturer": manufacturer,
                "product_model": product,
                "chunk_id": chunk_id,
                "question": question,
                "rank_sha256": _rank(manufacturer, product, chunk_id, question),
                "scope_key": scope_for_row[chunk_id],
            }
        )

    by_manufacturer: dict[str, list[dict]] = defaultdict(list)
    for item in eligible:
        by_manufacturer[item["manufacturer"]].append(item)
    cohort = [
        item
        for manufacturer in sorted(by_manufacturer)
        for item in sorted(
            by_manufacturer[manufacturer], key=lambda candidate: candidate["rank_sha256"]
        )[:PER_MANUFACTURER_CAP]
    ]

    replay_rows = []
    for index, item in enumerate(cohort, 1):
        source = rows_by_id[item["chunk_id"]]
        candidates = scopes[item["scope_key"]]
        started = time.perf_counter()
        selected, trace = select_procedure_bundle_coverage(
            item["question"], [source], candidates
        )
        replay_rows.append(
            {
                "challenge_id": f"sec{index:03d}",
                **item,
                "candidate_scope_rows": len(candidates),
                "selected_ids": [str(row["id"]) for row in selected],
                "selected_facets": [row["procedure_bundle_facet"] for row in selected],
                "selected_receipts": [
                    {
                        "candidate_id": str(row["id"]),
                        "document_id": row.get("document_id"),
                        "section_title": row.get("section_title"),
                        "source_spans": row["coverage_cards"],
                        "receipt_verified": all(
                            verify_source_span_receipt(row, card)
                            for card in row["coverage_cards"]
                        ),
                    }
                    for row in selected
                ],
                "trace": trace,
                "selector_runtime_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )

    receipts = [receipt for row in replay_rows for receipt in row["selected_receipts"]]
    manufacturers = sorted({row["manufacturer"] for row in replay_rows})
    potential = sum(
        "explicit_intra_document_reference" in row["trace"]["potential_facets"]
        for row in replay_rows
    )
    selected = sum(bool(row["selected_ids"]) for row in replay_rows)
    execution_valid = bool(
        len(replay_rows) >= 10
        and len(manufacturers) >= 3
        and all(receipt["receipt_verified"] for receipt in receipts)
    )
    gate = {
        "source_reference_questions": len(replay_rows),
        "manufacturers": len(manufacturers),
        "manufacturer_names": manufacturers,
        "potential_explicit_reference_questions": potential,
        "selected_explicit_reference_questions": selected,
        "all_source_span_receipts_verified": all(
            receipt["receipt_verified"] for receipt in receipts
        ),
        "max_selector_runtime_ms": max(
            (row["selector_runtime_ms"] for row in replay_rows), default=0
        ),
        "database_get_requests": 0,
        "database_writes": 0,
        "model_calls": 0,
        "execution_interpretation": (
            "GO_VALID_SECTION_CHALLENGE_EXECUTION"
            if execution_valid
            else "NO_GO_INVALID_SECTION_CHALLENGE_EXECUTION"
        ),
        "applicability_interpretation": (
            "PENDING_BLINDED_SELECTION_REVIEW"
            if selected
            else (
                "NO_SELECTIONS_WITH_POTENTIAL_CONTAMINATION_PASS_RECALL_INCONCLUSIVE"
                if potential
                else "INCONCLUSIVE_NO_POTENTIAL_EXPLICIT_REFERENCE"
            )
        ),
    }
    return {
        "instrument": "s114_procedure_bundle_section_challenge_v1",
        "status": "preregistered_facet_challenge_not_release_evidence",
        "observed_hashes": observed_hashes,
        "gate": gate,
        "rows": replay_rows,
        "limitations": [
            "The cohort is structurally enriched for section references and is not an incidence estimate.",
            "Historical HYQs are synthetic and the source chunk is injected as served context.",
            "Access/unlock and licensed-loop facets are not exercised by this challenge.",
            "Selections require blinded evidence adjudication before any advancement claim.",
        ],
    }


def main() -> int:
    payload = build_payload()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["gate"], ensure_ascii=False, indent=2))
    return 0 if payload["gate"]["execution_interpretation"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
