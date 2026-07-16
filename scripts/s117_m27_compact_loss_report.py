#!/usr/bin/env python3
"""Extract the frozen M2.7B loss rows and attach raw-block context offline.

This is a diagnostic projection only.  Surface categories describe syntax and
must never be interpreted as authorization to discard source content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import re
from collections import Counter
from pathlib import Path
from typing import Any

from scripts import s117_m27_loss_accounted_alignment as audit
from src.reingest import chunk as chunk_module


ROOT = Path(__file__).resolve().parents[1]
LOSS_ROWS_MARKER = b'\n  "loss_rows": ['
NEXT_KEY_MARKER = b'\n  "manifests":'


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for piece in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(piece)
    return digest.hexdigest()


def _extract_loss_rows(seed_path: Path) -> list[dict[str, Any]]:
    with seed_path.open("rb") as handle:
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as view:
            marker_at = view.find(LOSS_ROWS_MARKER)
            if marker_at < 0:
                raise RuntimeError("loss_rows marker absent from frozen seed")
            array_at = view.find(b"[", marker_at + len(LOSS_ROWS_MARKER) - 1)
            next_key_at = view.find(NEXT_KEY_MARKER, array_at)
            if array_at < 0 or next_key_at < 0:
                raise RuntimeError("loss_rows boundary absent from frozen seed")
            payload = bytes(view[array_at:next_key_at]).rstrip()
    if payload.endswith(b","):
        payload = payload[:-1].rstrip()
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise RuntimeError("loss_rows is not an array")
    return rows


def _surface_category(text: str) -> str:
    stripped = text.strip()
    if re.fullmatch(r"[0-9]+", stripped):
        return "ascii_decimal_only"
    if stripped and all(not char.isalnum() for char in stripped):
        return "symbol_only"
    if len(stripped) == 1 and stripped.isalpha():
        return "single_letter"
    has_alpha = any(char.isalpha() for char in stripped)
    has_digit = any(char.isdigit() for char in stripped)
    if has_alpha and has_digit:
        return "alpha_numeric_mixed"
    if has_alpha and not has_digit:
        return "lexical_no_digits"
    if has_digit:
        return "numeric_mixed"
    return "other"


def _context_row(block: dict[str, Any] | None) -> dict[str, Any] | None:
    if block is None:
        return None
    return {
        "source_block_index": block["source_block_index"],
        "source_page_ordinal": block["source_page_ordinal"],
        "kind": block["kind"],
        "page": block["page"],
        "text": block["text"],
        "text_sha256": block["text_sha256"],
    }


def build_report(seed_path: Path, store: Path) -> dict[str, Any]:
    loss_rows = _extract_loss_rows(seed_path)
    if len(loss_rows) != 100:
        raise RuntimeError(f"expected 100 frozen loss rows, observed {len(loss_rows)}")
    dispositions = Counter(row.get("disposition") for row in loss_rows)
    if dispositions != Counter({"unruled_loss": 87, "authorized_exclusion": 13}):
        raise RuntimeError(f"frozen disposition drift: {dict(dispositions)}")

    blocks_by_sha: dict[str, list[dict[str, Any]]] = {}
    enriched: list[dict[str, Any]] = []
    for row in loss_rows:
        extraction_sha256 = row["extraction_sha256"]
        if extraction_sha256 not in blocks_by_sha:
            raw_path = store / f"{extraction_sha256}.json"
            if not raw_path.is_file():
                raise RuntimeError(f"raw record absent: {extraction_sha256}")
            raw = raw_path.read_bytes()
            record = audit._strict_json(raw)
            if record.get("sha256") != extraction_sha256:
                raise RuntimeError(f"raw record declared identity drift: {extraction_sha256}")
            blocks_by_sha[extraction_sha256] = audit._blocks_with_page_ordinal(record)

        blocks = blocks_by_sha[extraction_sha256]
        block_index = row["source_block_index"]
        if not 0 <= block_index < len(blocks):
            raise RuntimeError("loss row source block index is outside raw record")
        block = blocks[block_index]
        exact_fields = (
            "source_block_index",
            "source_page_ordinal",
            "page",
            "kind",
            "text",
        )
        if any(row[key] != block[key] for key in exact_fields):
            raise RuntimeError("loss row does not match reconstructed raw block")

        evaluation = audit._rule_evaluation(block, [])
        stripped = block["text"].strip()
        enriched.append({
            **row,
            "text_sha256": block["text_sha256"],
            "surface_diagnostic": {
                "category": _surface_category(block["text"]),
                "characters": len(stripped),
                "meaningful_characters": chunk_module._meaningful_len(block["text"]),
                "contains_alpha": any(char.isalpha() for char in stripped),
                "contains_digit": any(char.isdigit() for char in stripped),
                "uppercase_exact": bool(stripped) and stripped == stripped.upper(),
            },
            "rule_evaluation_zero_coverage": evaluation,
            "context": {
                "minus_2": _context_row(blocks[block_index - 2]) if block_index >= 2 else None,
                "minus_1": _context_row(blocks[block_index - 1]) if block_index >= 1 else None,
                "plus_1": _context_row(blocks[block_index + 1]) if block_index + 1 < len(blocks) else None,
                "plus_2": _context_row(blocks[block_index + 2]) if block_index + 2 < len(blocks) else None,
            },
        })

    surface_counts = Counter(
        row["surface_diagnostic"]["category"]
        for row in enriched
        if row["disposition"] == "unruled_loss"
    )
    unique_unruled_texts = sorted({
        row["text"]
        for row in enriched
        if row["disposition"] == "unruled_loss"
    })
    report: dict[str, Any] = {
        "instrument": "s117_m27_compact_loss_report_v1",
        "authority": "diagnostic_only_no_policy_or_semantic_adjudication",
        "source": {
            "path": seed_path.relative_to(ROOT).as_posix(),
            "bytes": seed_path.stat().st_size,
            "sha256": _sha_file(seed_path),
        },
        "counts": {
            "rows": len(enriched),
            "documents": len(blocks_by_sha),
            "dispositions": dict(sorted(dispositions.items())),
            "unruled_surface_categories": dict(sorted(surface_counts.items())),
            "unique_unruled_texts": len(unique_unruled_texts),
        },
        "unique_unruled_texts": unique_unruled_texts,
        "rows": sorted(
            enriched,
            key=lambda item: (item["extraction_sha256"], item["source_block_index"]),
        ),
        "authorization": {
            "policy_change": False,
            "chunk_change": False,
            "semantic_noise_claim": False,
            "facts_moved_to_ok": 0,
        },
    }
    report["logical_payload_sha256"] = audit._sha_bytes(audit._canonical(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.seed.resolve(), args.store.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "DIAGNOSTIC_COMPLETE",
        "counts": report["counts"],
        "logical_payload_sha256": report["logical_payload_sha256"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
