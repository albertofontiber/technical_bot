#!/usr/bin/env python3
"""M2.7C v2: token-interval content/span binding for the local probe.

The v1 runner remains frozen as evidence of the failed preregistered attempt.
This wrapper reuses its closed population/delta machinery while replacing only
the prereg loader and the treatment content/span validator in a restored scope.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts import s117_m27_live_evidence as live
from scripts import s117_m27_loss_safe_chunking_probe as base
from scripts import s117_materialize_chunks_v3_local as replay
from src.reingest import chunk as chunk_module


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m27_loss_safe_chunking_probe_prereg_v2.yaml"


def _load_contract(prereg_path: Path) -> dict[str, Any]:
    if prereg_path.resolve() != DEFAULT_PREREG.resolve():
        raise RuntimeError("M2.7C v2 prereg path mismatch")
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("instrument")
        != "s117_m27_loss_safe_chunking_probe_prereg_v2"
        or prereg.get("status") != "frozen_before_seeded_probe"
    ):
        raise RuntimeError("M2.7C v2 prereg drift")
    for item in live._iter_hashed_paths(prereg.get("frozen_inputs", {})):
        path = (ROOT / item["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("M2.7C v2 frozen input escapes workspace") from exc
        if base._sha_file(path) != item["sha256"]:
            raise RuntimeError(f"M2.7C v2 frozen input drift: {item['path']}")
    selected = prereg.get("selected_paths", {})
    bindings = prereg.get("selected_path_bindings", {})
    frozen = prereg.get("frozen_inputs", {})
    if set(selected) != set(bindings):
        raise RuntimeError("M2.7C v2 selected path binding set drift")
    for name, frozen_name in bindings.items():
        item = frozen.get(frozen_name)
        if (
            not isinstance(item, dict)
            or selected[name] != item.get("path")
            or not live._is_sha256(item.get("sha256"))
        ):
            raise RuntimeError("M2.7C v2 selected path is not hash-bound")
    if prereg.get("override_contract") != {
        "symbol": "src.reingest.chunk.NOISE_CHARS",
        "baseline": base.BASELINE_NOISE_CHARS,
        "treatment": base.TREATMENT_NOISE_CHARS,
        "scope": "single_call_with_finally_restore",
        "only_behavioral_override": True,
    }:
        raise RuntimeError("M2.7C v2 override contract drift")
    return prereg


def _validate_treatment_against_raw(
    raw: bytes,
    record: dict[str, Any],
    chunks: list[Any],
    rows: list[dict[str, Any]],
) -> None:
    """Bind each row span to its exact interval in the global raw token stream."""
    if len(chunks) != len(rows):
        raise RuntimeError("treatment chunk/row cardinality drift")
    pages = record.get("result", {}).get("pages", [])
    blocks = chunk_module._flatten(pages)
    image_pages = {
        page.get("page")
        for page in pages
        if page.get("page") is not None and page.get("images")
    }
    page_confidence = {
        page.get("page"): page.get("confidence")
        for page in pages
        if page.get("page") is not None and page.get("confidence") is not None
    }
    lineage_rows = []
    for chunk, row in zip(chunks, rows):
        replay._validate_expected_chunk(chunk)
        start = row["source_block_start"]
        end = row["source_block_end"]
        covered_blocks = blocks[start : end + 1]
        expected_page = next(
            (block.page for block in covered_blocks if block.page is not None), None
        )
        if row["page_number"] != expected_page:
            raise RuntimeError("treatment page number is not raw-span-bound")
        if row["is_flow_diagram"] != any(
            block.kind == "mermaid" for block in covered_blocks
        ):
            raise RuntimeError("treatment flow flag is not raw-span-bound")
        if row["has_diagram"] != (expected_page in image_pages):
            raise RuntimeError("treatment diagram flag is not raw-page-bound")
        if row["confidence"] != page_confidence.get(expected_page):
            raise RuntimeError("treatment confidence is not raw-page-bound")
        lineage_rows.append({
            "chunk_index": row["ordinal"],
            "source_block_start": start,
            "source_block_end": end,
            "section_anchor": row["section_anchor"],
            "section_lineage": row["section_lineage"],
            "section_title": row["section_title"],
            "section_path": row["section_path"],
        })
    failures = replay._validate_lineage(raw, lineage_rows)
    if failures:
        raise RuntimeError(f"treatment lineage is not raw-bound: {failures[:3]}")

    raw_tokens: list[str] = []
    block_intervals: list[tuple[int, int]] = []
    for block in blocks:
        tokens = block.text.split()
        if not tokens:
            raise RuntimeError("parsed raw block has an empty token surface")
        start = len(raw_tokens)
        raw_tokens.extend(tokens)
        block_intervals.append((start, len(raw_tokens)))
    treatment_tokens = [
        token for row in rows for token in row["content"].split()
    ]
    if treatment_tokens != raw_tokens:
        raise RuntimeError("treatment global token surface differs from raw")

    row_token_cursor = 0
    block_cursor = 0
    for row in rows:
        row_tokens = row["content"].split()
        if not row_tokens:
            raise RuntimeError("treatment row has an empty token surface")
        row_start = row_token_cursor
        row_end = row_start + len(row_tokens)
        while (
            block_cursor < len(block_intervals)
            and block_intervals[block_cursor][1] <= row_start
        ):
            block_cursor += 1
        if block_cursor >= len(block_intervals):
            raise RuntimeError("treatment token interval exceeds raw blocks")
        expected_start = block_cursor
        expected_end = block_cursor
        while (
            expected_end + 1 < len(block_intervals)
            and block_intervals[expected_end + 1][0] < row_end
        ):
            expected_end += 1
        if (
            row["source_block_start"] != expected_start
            or row["source_block_end"] != expected_end
        ):
            raise RuntimeError("treatment content token interval is not bound to its raw span")
        row_token_cursor = row_end
    if row_token_cursor != len(raw_tokens):
        raise RuntimeError("treatment token intervals do not cover raw surface")


def build_probe(**kwargs: Any) -> dict[str, Any]:
    original_loader = base._load_contract
    original_validator = base._validate_treatment_against_raw
    original_file = base.__file__
    try:
        base._load_contract = _load_contract
        base._validate_treatment_against_raw = _validate_treatment_against_raw
        base.__file__ = __file__
        result = base.build_probe(**kwargs)
    finally:
        base._load_contract = original_loader
        base._validate_treatment_against_raw = original_validator
        base.__file__ = original_file
    result.pop("determinism", None)
    result["instrument"] = "s117_m27_loss_safe_chunking_probe_v2"
    result["supersedes"] = {
        "instrument": "s117_m27_loss_safe_chunking_probe_v1",
        "reason": "v1_exact_span_group_contract_rejected_legitimate_split_plus_merge_spans",
    }
    result["determinism"] = {
        "logical_payload_sha256": base._sha_bytes(base._canonical(result))
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_probe(
        prereg_path=args.prereg,
        store=args.store,
        sidecar_root=args.sidecar_root,
        source_snapshot=args.source_snapshot,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "population": result["population"],
        "logical_payload_sha256": result["determinism"]["logical_payload_sha256"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
