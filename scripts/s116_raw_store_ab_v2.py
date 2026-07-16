#!/usr/bin/env python3
"""Versioned, deterministic A/B inventory for the S116 lineage contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.reingest import chunk as chunk_module
from src.reingest.metadata import detect_document_metadata

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s116_raw_store_baseline_v2.json"
HEADING = re.compile(r"(?m)^\s*(#{1,6})\s+(.+?)\s*$")
NUMERIC_SECTION = re.compile(r"^\s*\d+(?:\.\d+)+(?:\s|$)")
METRIC_KEYS = (
    "records_processed",
    "record_errors",
    "pages_total",
    "source_headings_total",
    "repeated_heading_occurrences",
    "chunks_total",
    "chunks_with_section_path",
    "chunks_with_section_title",
    "content_chars_total",
    "multi_heading_chunks_without_section_path",
    "numeric_section_continuations_without_own_leaf_heading",
    "section_chunks_with_own_leaf_heading",
    "section_continuations_without_own_leaf_heading",
    "section_chunks_with_internally_verified_anchor",
    "section_chunks_with_resolved_full_lineage",
    "section_title_without_internally_verified_anchor",
    "orphan_or_stale_anchor_chunks",
    "short_chunks_below_min_meaningful_chars",
)


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _value(obj: object, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _anchor_identity(anchor: object) -> tuple[Any, Any, Any]:
    return (
        _value(anchor, "source_page"),
        _value(anchor, "source_block_index"),
        _value(anchor, "heading_sha256"),
    )


def _leaf_heading_in_content(content: str, title: str | None) -> bool:
    leaf = _fold(title)
    return bool(leaf) and any(_fold(title_text) == leaf for _, title_text in HEADING.findall(content))


def _anchor_resolves(anchor: object, blocks: list[object]) -> bool:
    heading_text = _value(anchor, "heading_text")
    heading_sha256 = _value(anchor, "heading_sha256")
    source_page = _value(anchor, "source_page")
    source_index = _value(anchor, "source_block_index")
    title = _value(anchor, "title")
    level = _value(anchor, "level")
    if not isinstance(source_index, int) or isinstance(source_index, bool):
        return False
    if source_index < 0 or source_index >= len(blocks):
        return False
    if source_page is not None and (not isinstance(source_page, int) or isinstance(source_page, bool)):
        return False
    if not isinstance(heading_text, str) or not isinstance(heading_sha256, str):
        return False
    match = HEADING.fullmatch(heading_text.strip())
    if match is None or len(match.group(1)) != level or match.group(2).strip() != title:
        return False
    if hashlib.sha256(heading_text.encode("utf-8")).hexdigest() != heading_sha256:
        return False
    block = blocks[source_index]
    return (
        _value(block, "kind") == "heading"
        and _value(block, "text") == heading_text
        and _value(block, "page") == source_page
        and _value(block, "source_block_index", source_index) == source_index
    )


def _common_lineage(blocks: list[object]) -> tuple[object, ...]:
    if not blocks:
        return ()
    lineages = [tuple(_value(block, "lineage", ())) for block in blocks]
    common: list[object] = []
    for tier in zip(*lineages):
        identities = {_anchor_identity(anchor) for anchor in tier}
        if len(identities) != 1:
            break
        common.append(tier[0])
    return tuple(common)


def _lineage_resolves(chunk: object, blocks: list[object]) -> bool:
    lineage = tuple(_value(chunk, "section_lineage", ()))
    anchor = _value(chunk, "section_anchor")
    start = _value(chunk, "source_block_start")
    end = _value(chunk, "source_block_end")
    title = _value(chunk, "section_title")
    path = _value(chunk, "section_path")
    if not lineage or anchor is None:
        return False
    if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
        return False
    if start < 0 or end < start or end >= len(blocks):
        return False
    if any(not _anchor_resolves(item, blocks) for item in lineage):
        return False
    if _anchor_identity(lineage[-1]) != _anchor_identity(anchor):
        return False
    expected = _common_lineage(blocks[start : end + 1])
    if tuple(map(_anchor_identity, expected)) != tuple(map(_anchor_identity, lineage)):
        return False
    return (
        title == _value(lineage[-1], "title")
        and path == " > ".join(str(_value(item, "title")) for item in lineage)
    )


def _dependency_hashes() -> dict[str, str]:
    paths = [
        Path(__file__),
        ROOT / "src/reingest/chunk.py",
        ROOT / "src/reingest/metadata.py",
        ROOT / "src/reingest/manufacturer_registry.py",
    ]
    result = {
        str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }
    config_manifest = hashlib.sha256()
    for path in sorted((ROOT / "config/manufacturers").glob("*.yaml"), key=lambda item: item.name):
        config_manifest.update(path.name.encode("utf-8") + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    result["config/manufacturers/*.yaml"] = config_manifest.hexdigest()
    return result


def _zero_metrics() -> Counter[str]:
    return Counter({key: 0 for key in METRIC_KEYS})


def _record_summary(record: dict, file_name: str) -> dict:
    pages = record.get("result", {}).get("pages", [])
    blocks = chunk_module._flatten(pages)
    sample = "\n".join(str(page.get("md") or page.get("text") or "") for page in pages)[:4000]
    metadata = detect_document_metadata(str(record.get("source_path") or ""), sample)
    chunks = chunk_module.chunk_document(record)
    metrics = _zero_metrics()
    metrics["records_processed"] = 1
    metrics["pages_total"] = len(pages)
    metrics["chunks_total"] = len(chunks)
    metrics["content_chars_total"] = sum(len(chunk.content) for chunk in chunks)
    heading_keys: Counter[tuple[int, str]] = Counter()
    for block in blocks:
        if _value(block, "kind") == "heading":
            heading_keys[(_value(block, "level"), _fold(_value(block, "title")))] += 1
    metrics["source_headings_total"] = sum(heading_keys.values())
    metrics["repeated_heading_occurrences"] = sum(max(0, count - 1) for count in heading_keys.values())

    samples: list[dict] = []
    for chunk in chunks:
        content = str(chunk.content)
        title = chunk.section_title
        path = chunk.section_path
        headings = HEADING.findall(content)
        own_leaf = _leaf_heading_in_content(content, title)
        anchor = _value(chunk, "section_anchor")
        internally_verified = anchor is not None and _anchor_resolves(anchor, blocks)
        lineage_resolved = internally_verified and _lineage_resolves(chunk, blocks)
        if path:
            metrics["chunks_with_section_path"] += 1
        if title:
            metrics["chunks_with_section_title"] += 1
            if own_leaf:
                metrics["section_chunks_with_own_leaf_heading"] += 1
            else:
                metrics["section_continuations_without_own_leaf_heading"] += 1
                samples.append(
                    {
                        "file": file_name,
                        "chunk_index": chunk.chunk_index,
                        "section_title": title,
                        "page_number": chunk.page_number,
                        "content_preview": content[:240],
                    }
                )
                if NUMERIC_SECTION.match(str(title)):
                    metrics["numeric_section_continuations_without_own_leaf_heading"] += 1
            if internally_verified:
                metrics["section_chunks_with_internally_verified_anchor"] += 1
            else:
                metrics["section_title_without_internally_verified_anchor"] += 1
            if lineage_resolved:
                metrics["section_chunks_with_resolved_full_lineage"] += 1
        if anchor is not None and not internally_verified:
            metrics["orphan_or_stale_anchor_chunks"] += 1
        if chunk_module._meaningful_len(content) < chunk_module.MIN_CHARS:
            metrics["short_chunks_below_min_meaningful_chars"] += 1
        if len(headings) >= 2 and not path:
            metrics["multi_heading_chunks_without_section_path"] += 1
    stream = "\n\n".join(chunk.content for chunk in chunks)
    return {
        "manufacturer": metadata.manufacturer or "unknown",
        "metrics": metrics,
        "samples": samples,
        "stream_sha256": hashlib.sha256(stream.encode("utf-8")).hexdigest(),
        "chunks": len(chunks),
    }


def build_payload(store: Path, label: str) -> dict:
    logging.getLogger("src.reingest.metadata").setLevel(logging.ERROR)
    files = sorted(store.glob("*.json"), key=lambda path: path.name.casefold())
    totals = _zero_metrics()
    by_manufacturer: dict[str, Counter[str]] = defaultdict(_zero_metrics)
    samples: list[dict] = []
    errors: list[dict] = []
    document_streams: dict[str, dict] = {}
    manifest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        manifest.update(f"{path.name}\0{len(raw)}\0{digest}\n".encode("utf-8"))
        try:
            result = _record_summary(json.loads(raw), path.name)
        except Exception as exc:
            totals["record_errors"] += 1
            errors.append({"file": path.name, "error_type": type(exc).__name__})
            continue
        totals.update(result["metrics"])
        by_manufacturer[result["manufacturer"]].update(result["metrics"])
        samples.extend(result["samples"])
        document_streams[path.name] = {
            "sha256": result["stream_sha256"],
            "chunks": result["chunks"],
        }
    samples = sorted(
        samples,
        key=lambda row: hashlib.sha256(f"{row['file']}:{row['chunk_index']}".encode()).hexdigest(),
    )[:25]
    stream_manifest = hashlib.sha256()
    for name, receipt in sorted(document_streams.items()):
        stream_manifest.update(f"{name}\0{receipt['sha256']}\n".encode("utf-8"))
    return {
        "instrument": "s116_raw_store_ab_v2",
        "label": label,
        "status": "local_inventory_complete",
        "runtime": {"python": platform.python_version()},
        "source": {
            "store_slug": store.name,
            "json_files": len(files),
            "manifest_sha256": manifest.hexdigest(),
        },
        "dependencies": _dependency_hashes(),
        "summary": {key: totals[key] for key in METRIC_KEYS},
        "output_stream_manifest_sha256": stream_manifest.hexdigest(),
        "document_output_streams": dict(sorted(document_streams.items())),
        "by_manufacturer": {
            manufacturer: {key: counter[key] for key in METRIC_KEYS}
            for manufacturer, counter in sorted(by_manufacturer.items())
        },
        "deterministic_samples": samples,
        "errors": errors,
        "cost": {
            "database_get_requests": 0,
            "database_writes": 0,
            "model_calls": 0,
            "network_calls": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = build_payload(args.store, args.label)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
