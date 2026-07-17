"""Build an answer-point-free S147 packet for the S173 synthesis gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s147_fresh_source_packet_v1.json"
GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
OUT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    source_by = {row["item_id"]: row for row in source["items"]}
    gold_by = {row["item_id"]: row for row in gold["items"] if row["eligible"]}
    if len(source_by) != 14 or len(gold_by) != 14:
        raise ValueError("S173 population mismatch")

    rows: list[dict[str, Any]] = []
    for item_id in sorted(source_by):
        source_row = source_by[item_id]
        gold_row = gold_by[item_id]
        for field in (
            "manufacturer",
            "product_model",
            "document_id",
            "chunk_id",
            "excerpt_sha256",
        ):
            if source_row[field] != gold_row[field]:
                raise ValueError(f"S173 identity mismatch: {item_id}:{field}")
        excerpt = source_row["excerpt"]
        if hashlib.sha256(excerpt.encode("utf-8")).hexdigest() != source_row["excerpt_sha256"]:
            raise ValueError(f"S173 excerpt hash mismatch: {item_id}")
        rows.append(
            {
                "item_id": item_id,
                "question": gold_row["question"],
                "stratum": source_row["stratum"],
                "manufacturer": source_row["manufacturer"],
                "product_model": source_row["product_model"],
                "document_id": source_row["document_id"],
                "chunk_id": source_row["chunk_id"],
                "extraction_sha256": source_row["extraction_sha256"],
                "source_file": source_row["source_file"],
                "page_number": source_row["page_number"],
                "section_title": source_row["section_title"],
                "excerpt": excerpt,
                "excerpt_sha256": source_row["excerpt_sha256"],
            }
        )
    body = {
        "instrument": "s173_single_source_omission_cohort_v1",
        "status": "SEALED_GENERATION_PACKET_NO_GOLD_ANSWER_POINTS",
        "population": {
            "items": len(rows),
            "manufacturers": len({row["manufacturer"] for row in rows}),
            "table": sum(row["stratum"] == "table" for row in rows),
            "prose": sum(row["stratum"] == "prose" for row in rows),
            "target_question_overlap": 0,
        },
        "items": rows,
    }
    body["cohort_sha256"] = stable_sha(body)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
