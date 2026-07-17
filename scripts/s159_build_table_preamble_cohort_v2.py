"""Build the fresh document-disjoint S159 table-preamble v2 cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_PRIOR = ROOT / "evals/s158_independent_table_preamble_packet_v1.json"
DEFAULT_OUTPUT = ROOT / "evals/s159_independent_table_preamble_packet_v2.json"
TARGET_DOCUMENT_IDS = {"eef91711-fcb7-4b46-ab86-21657490df40"}
TARGET_SOURCE_MARKERS = ("faast lt",)


def _stable_rank(row: dict[str, Any]) -> str:
    return hashlib.sha256(("s159:" + str(row["id"])).encode("utf-8")).hexdigest()


def _choose_diverse(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=_stable_rank)
    chosen: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    manufacturers: set[str] = set()
    titles: set[str] = set()
    for row in ordered:
        manufacturer = str(row.get("manufacturer") or "").strip().casefold()
        title = str(row.get("section_title") or "").strip().casefold()
        if manufacturer not in manufacturers or title not in titles:
            chosen.append(row)
            seen_ids.add(str(row["id"]))
            if manufacturer:
                manufacturers.add(manufacturer)
            if title:
                titles.add(title)
        if len(chosen) >= limit:
            return chosen
    for row in ordered:
        if str(row["id"]) not in seen_ids:
            chosen.append(row)
        if len(chosen) >= limit:
            break
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file")
    parser.add_argument("--prior-packet", type=Path, default=DEFAULT_PRIOR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    load_dotenv(args.env_file)

    import os

    from scripts.s158_build_table_preamble_cohort import _fetch_rows
    from src.rag.table_preamble_closure import select_table_preambles

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_KEY are required")
    if not 20 <= args.limit <= 60:
        raise ValueError("limit must be between 20 and 60")

    prior = json.loads(args.prior_packet.read_text(encoding="utf-8"))
    excluded_documents = {
        str(row.get("document_id") or "") for row in prior.get("rows") or []
    } | TARGET_DOCUMENT_IDS
    corpus = _fetch_rows(url, key)
    positions = {
        (
            str(row.get("document_id") or ""),
            str(row.get("extraction_sha256") or ""),
            row.get("chunk_index"),
        ): row
        for row in corpus
    }
    eligible: list[dict[str, Any]] = []
    cross_table_rejections = 0
    for seed in corpus:
        document_id = str(seed.get("document_id") or "")
        source = str(seed.get("source_file") or "")
        if document_id in excluded_documents or any(
            marker in source.casefold() for marker in TARGET_SOURCE_MARKERS
        ):
            continue
        index = seed.get("chunk_index")
        if isinstance(index, bool) or not isinstance(index, int) or index < 1:
            continue
        predecessor = positions.get(
            (document_id, str(seed.get("extraction_sha256") or ""), index - 1)
        )
        if predecessor is None:
            continue
        selected, trace = select_table_preambles(
            [seed], [predecessor], max_preambles=1
        )
        cross_table_rejections += int(trace["cross_table_rejected_rows"])
        if not selected:
            continue
        candidate = selected[0]
        card = candidate["coverage_cards"][0]
        eligible.append(
            {
                "id": str(seed["id"]),
                "seed_id": str(seed["id"]),
                "predecessor_id": str(candidate["id"]),
                "document_id": document_id,
                "extraction_sha256": str(seed.get("extraction_sha256") or ""),
                "seed_chunk_index": index,
                "predecessor_chunk_index": candidate.get("chunk_index"),
                "source_file": source,
                "manufacturer": seed.get("manufacturer"),
                "product_model": seed.get("product_model"),
                "language": seed.get("language"),
                "page_number": seed.get("page_number"),
                "section_title": seed.get("section_title"),
                "preamble_start": card["start"],
                "preamble_end": card["end"],
                "preamble": card["quote"],
                "seed_table_prefix": str(seed.get("content") or "")[:2400],
            }
        )

    chosen = _choose_diverse(eligible, args.limit)
    payload = {
        "instrument": "s159_independent_table_preamble_packet_v2",
        "status": "FROZEN_BEFORE_SEMANTIC_REVIEW",
        "selection": {
            "corpus_table": "chunks_v2",
            "canonical_only": True,
            "known_target_documents_excluded": True,
            "s158_document_ids_excluded": True,
            "semantic_labels_available_during_selection": False,
            "sort": "sha256(s159:seed_id)_with_mechanical_manufacturer_title_diversity",
            "model_calls": 0,
            "database_writes": 0,
        },
        "prior_packet": str(args.prior_packet.relative_to(ROOT)).replace("\\", "/"),
        "excluded_document_ids": len(excluded_documents),
        "corpus_rows_read": len(corpus),
        "cross_table_pairs_rejected_before_sampling": cross_table_rejections,
        "eligible_pairs": len(eligible),
        "selected_pairs": len(chosen),
        "manufacturers": sorted(
            {str(row.get("manufacturer") or "") for row in chosen if row.get("manufacturer")}
        ),
        "section_titles": sorted(
            {str(row.get("section_title") or "") for row in chosen if row.get("section_title")}
        ),
        "rows": chosen,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "corpus_rows_read": len(corpus),
                "cross_table_rejections": cross_table_rejections,
                "eligible_pairs": len(eligible),
                "selected_pairs": len(chosen),
                "manufacturers": len(payload["manufacturers"]),
                "section_titles": len(payload["section_titles"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

