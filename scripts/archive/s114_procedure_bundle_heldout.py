#!/usr/bin/env python3
"""Freeze and replay the preregistered S114 cross-manufacturer held-out."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.procedure_bundle_coverage import (
    MAX_CARD_CHARS,
    MAX_CARDS_PER_ROW,
    select_procedure_bundle_coverage,
    verify_source_span_receipt,
)

HYQ = ROOT / "evals/s99_hyq_generated.jsonl"
SELECTOR = ROOT / "src/rag/procedure_bundle_coverage.py"
FREEZE = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
OUT = ROOT / "evals/s114_procedure_bundle_heldout_replay_v1.json"
SELECTOR_SHA256 = "cbd3902b823fa7d7d4fb4c9c3f6ba3781a5492c0b2e7be6364291d1cd9461a76"
HYQ_SHA256 = "5fb56f1739f8713c263d331b5393ef1904d9a5311ba3f1ac15bd81828b86f8e7"
EXCLUDED = {"Notifier", "Morley", "Securiton", "Detnov"}
MANUFACTURERS = 12
QUESTIONS_PER_MANUFACTURER = 2
BACKUPS_PER_MANUFACTURER = 5
GET_CAP = 25
ROW_SELECT = (
    "id,content,context,source_file,page_number,section_title,section_path,"
    "product_model,manufacturer,document_id,extraction_sha256,chunk_index,language"
)
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


def _rank(item: dict) -> str:
    value = "|".join(
        str(item[key]) for key in ("manufacturer", "product_model", "chunk_id", "question")
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _eligible_hyqs() -> tuple[list[str], dict[str, list[dict]]]:
    by_manufacturer: dict[str, list[dict]] = {}
    counts = Counter()
    with HYQ.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            manufacturer = str(row.get("manufacturer") or "")
            product = str(row.get("product_model") or "")
            chunk_id = str(row.get("chunk_id") or "")
            if (
                not manufacturer
                or manufacturer in EXCLUDED
                or not product
                or not chunk_id
                or row.get("origin") != "synthetic"
            ):
                continue
            for question in row.get("questions") or []:
                if not question or not PROCEDURAL.search(_fold(question)):
                    continue
                item = {
                    "manufacturer": manufacturer,
                    "product_model": product,
                    "chunk_id": chunk_id,
                    "question": str(question),
                    "source_file_s99": row.get("source_file"),
                    "page_number_s99": row.get("page_number"),
                }
                item["rank_sha256"] = _rank(item)
                by_manufacturer.setdefault(manufacturer, []).append(item)
                counts[manufacturer] += 1
    selected_manufacturers = [
        manufacturer
        for manufacturer, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[
            :MANUFACTURERS
        ]
    ]
    backups = {
        manufacturer: sorted(by_manufacturer[manufacturer], key=lambda item: item["rank_sha256"])[
            :BACKUPS_PER_MANUFACTURER
        ]
        for manufacturer in selected_manufacturers
    }
    return selected_manufacturers, backups


def _headers() -> tuple[str, dict[str, str]]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_KEY missing")
    return url, {"apikey": key, "Authorization": f"Bearer {key}"}


def _choose_current(
    manufacturers: list[str], backups: dict[str, list[dict]], sources: dict[str, dict]
) -> tuple[list[dict], list[dict]]:
    chosen: list[dict] = []
    rejected: list[dict] = []
    for manufacturer in manufacturers:
        valid = []
        for item in backups[manufacturer]:
            source = sources.get(item["chunk_id"])
            reason = None
            if source is None:
                reason = "chunk_absent_current_corpus"
            elif source.get("manufacturer") != item["manufacturer"]:
                reason = "manufacturer_identity_changed"
            elif source.get("product_model") != item["product_model"]:
                reason = "product_identity_changed"
            if reason:
                rejected.append({**item, "rejection_reason": reason})
            else:
                valid.append(item)
        if not valid:
            continue
        first = valid[0]
        selected = [first]
        second = next(
            (
                item for item in valid[1:]
                if item["product_model"] != first["product_model"]
                and item["chunk_id"] != first["chunk_id"]
            ),
            None,
        )
        if second is None:
            second = next(
                (item for item in valid[1:] if item["chunk_id"] != first["chunk_id"]),
                None,
            )
        if second is not None:
            selected.append(second)
        chosen.extend(selected[:QUESTIONS_PER_MANUFACTURER])
    return chosen, rejected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    selector_hash = _sha256_path(SELECTOR)
    hyq_hash = _sha256_path(HYQ)
    if selector_hash != SELECTOR_SHA256 or hyq_hash != HYQ_SHA256:
        raise RuntimeError("preregistered selector or HYQ input hash changed")

    manufacturers, backups = _eligible_hyqs()
    all_ids = sorted({item["chunk_id"] for rows in backups.values() for item in rows})
    url, headers = _headers()
    requests = 0
    started = time.perf_counter()
    with httpx.Client(timeout=60.0) as client:
        response = client.get(
            f"{url}/rest/v1/chunks_v2",
            headers=headers,
            params={
                "select": ROW_SELECT,
                "id": f"in.({','.join(all_ids)})",
                "limit": str(len(all_ids)),
            },
        )
        requests += 1
        response.raise_for_status()
        source_rows = response.json()
        sources = {str(row["id"]): row for row in source_rows}
        chosen, rejected = _choose_current(manufacturers, backups, sources)

        scopes: dict[str, list[dict]] = {}
        for manufacturer, product in sorted(
            {(item["manufacturer"], item["product_model"]) for item in chosen}
        ):
            response = client.get(
                f"{url}/rest/v1/chunks_v2",
                headers=headers,
                params={
                    "select": ROW_SELECT,
                    "manufacturer": f"eq.{manufacturer}",
                    "product_model": f"eq.{product}",
                    "order": "id.asc",
                    "limit": "1000",
                },
            )
            requests += 1
            if requests > GET_CAP:
                raise RuntimeError("preregistered database GET cap exceeded")
            response.raise_for_status()
            rows = response.json()
            if len(rows) == 1000:
                raise RuntimeError(f"scope reached safety cap: {manufacturer} | {product}")
            scopes[f"{manufacturer}\u241f{product}"] = rows

    freeze = {
        "instrument": "s114_procedure_bundle_heldout_freeze_v1",
        "status": "read_only_preregistered_heldout_freeze",
        "selector_sha256": selector_hash,
        "hyq_sha256": hyq_hash,
        "manufacturers": manufacturers,
        "backups": backups,
        "chosen": chosen,
        "rejected_backups": rejected,
        "source_rows": {item["chunk_id"]: sources[item["chunk_id"]] for item in chosen},
        "candidate_scopes": scopes,
        "cost_receipt": {
            "database_get_requests": requests,
            "database_writes": 0,
            "model_calls": 0,
        },
    }
    FREEZE.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    replay_rows = []
    for index, item in enumerate(chosen, 1):
        source = sources[item["chunk_id"]]
        scope = scopes[f"{item['manufacturer']}\u241f{item['product_model']}"]
        replay_started = time.perf_counter()
        selected, trace = select_procedure_bundle_coverage(item["question"], [source], scope)
        replay_rows.append(
            {
                "heldout_id": f"ho{index:03d}",
                **item,
                "served_id": item["chunk_id"],
                "candidate_scope_rows": len(scope),
                "selected_ids": [str(row["id"]) for row in selected],
                "selected_facets": [row["procedure_bundle_facet"] for row in selected],
                "selected_receipts": [
                    {
                        "candidate_id": str(row["id"]),
                        "manufacturer": row.get("manufacturer"),
                        "product_model": row.get("product_model"),
                        "source_spans": row["coverage_cards"],
                        "receipt_verified": all(
                            verify_source_span_receipt(row, card)
                            for card in row["coverage_cards"]
                        ),
                    }
                    for row in selected
                ],
                "trace": trace,
                "selector_runtime_ms": round((time.perf_counter() - replay_started) * 1000, 3),
            }
        )

    receipts = [receipt for row in replay_rows for receipt in row["selected_receipts"]]
    potential_by_facet = {
        facet: sum(facet in row["trace"]["potential_facets"] for row in replay_rows)
        for facet in (
            "explicit_intra_document_reference",
            "procedural_access_prerequisite",
            "quantified_licensed_loop_prerequisite",
        )
    }
    selected_by_facet = {
        facet: sum(facet in row["selected_facets"] for row in replay_rows)
        for facet in potential_by_facet
    }
    surviving_manufacturers = sorted({row["manufacturer"] for row in replay_rows})
    execution_valid = bool(
        len(replay_rows) >= 20
        and len(surviving_manufacturers) >= 10
        and requests <= GET_CAP
        and all(receipt["receipt_verified"] for receipt in receipts)
        and all(len(row["selected_ids"]) <= 1 for row in replay_rows)
        and all(
            len(receipt["source_spans"]) <= MAX_CARDS_PER_ROW
            and all(len(card["quote"]) <= MAX_CARD_CHARS for card in receipt["source_spans"])
            for receipt in receipts
        )
    )
    gate = {
        "questions": len(replay_rows),
        "manufacturers": len(surviving_manufacturers),
        "manufacturer_names": surviving_manufacturers,
        "product_scoped_questions": sum(
            row["trace"]["product_scoped_candidates"] > 0 for row in replay_rows
        ),
        "potential_questions_by_facet": potential_by_facet,
        "selected_questions_by_facet": selected_by_facet,
        "questions_with_appends": sum(bool(row["selected_ids"]) for row in replay_rows),
        "all_source_span_receipts_verified": all(
            receipt["receipt_verified"] for receipt in receipts
        ),
        "max_selected_per_question": max((len(row["selected_ids"]) for row in replay_rows), default=0),
        "max_cards_per_selected_row": max(
            (len(receipt["source_spans"]) for receipt in receipts), default=0
        ),
        "max_card_characters": max(
            (len(card["quote"]) for receipt in receipts for card in receipt["source_spans"]),
            default=0,
        ),
        "max_selector_runtime_ms": max(
            (row["selector_runtime_ms"] for row in replay_rows), default=0
        ),
        "total_elapsed_seconds": round(time.perf_counter() - started, 3),
        "database_get_requests": requests,
        "database_writes": 0,
        "model_calls": 0,
        "execution_interpretation": (
            "GO_VALID_HELDOUT_EXECUTION" if execution_valid else "NO_GO_INVALID_HELDOUT_EXECUTION"
        ),
        "adjudication_status": (
            "PENDING_BLINDED_SELECTION_REVIEW"
            if any(row["selected_ids"] for row in replay_rows)
            else "NO_SELECTIONS_CONTAMINATION_PASS_APPLICABILITY_INCONCLUSIVE"
        ),
    }
    payload = {
        "instrument": "s114_procedure_bundle_heldout_replay_v1",
        "status": "preregistered_heldout_not_release_evidence",
        "freeze_sha256": _sha256_path(FREEZE),
        "gate": gate,
        "rows": replay_rows,
        "limitations": [
            "Historical HYQs are independent of S114 but are synthetic questions.",
            "The source chunk is used as served context; this is a precision/applicability replay, not a full retriever replay.",
            "No selection may be labelled correct before blinded manual adjudication.",
            "This held-out cannot authorize serving integration.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if execution_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
