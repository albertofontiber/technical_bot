#!/usr/bin/env python3
"""S276: offline screen for a bounded missing-definition-sibling card.

The screen is deliberately narrower than a runtime implementation.  It uses a
fresh, document-disjoint seed-278 corpus sample, performs GET requests only,
calls no models and never scores the six S274 targets.  The reference mechanism
accepts only top-level, contiguous Markdown definition lists of 2--5 items.  If
validated selector cards cover every item but one, it may emit the single
omitted item in a separate, exactly re-derived field (maximum 600 characters).

This establishes structural prevalence and deterministic safety invariants.  It
does *not* establish semantic relevance or answer conversion; those require a
fresh organic A/B if the offline gate is GO.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import random
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml
from dotenv import load_dotenv


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"

DESIGN_PATH = EVALS / "s276_missing_definition_sibling_screen_design_v1.md"
PREREG_PATH = EVALS / "s276_missing_definition_sibling_screen_prereg_v1.yaml"
COHORT_PATH = EVALS / "s276_missing_definition_sibling_cohort_c278.jsonl"
BUILD_PATH = EVALS / "s276_missing_definition_sibling_build_c278_v1.json"
RESULT_ROWS_PATH = EVALS / "s276_missing_definition_sibling_results_c278.jsonl"
RESULT_PATH = EVALS / "s276_missing_definition_sibling_screen_result_v1.json"
GATE_PATH = EVALS / "s276_missing_definition_sibling_screen_gate_v1.yaml"

SEED = 278
SAMPLED_DOCS = 80
MIN_FRAGMENT_CHARS = 200
MAX_BLOCK_ITEMS = 5
MAX_CARD_CHARS = 600
CARD_FIELD = "missing_definition_sibling_cards"
CARD_CLASS = "missing_definition_sibling"

PRIOR_COHORT_PATHS = (
    ("v1", EVALS / "s269_structural_cohort_v1.jsonl"),
    ("seed270", EVALS / "s269_mutation_cohort_v2.jsonl"),
    ("seed271", EVALS / "s269_mutation_cohort_v3.jsonl"),
    ("seed272", EVALS / "s269_mutation_cohort_v4.jsonl"),
    ("seed273", EVALS / "s270_mutation_cohort_v5.jsonl"),
    ("seed274", EVALS / "s270_mutation_cohort_v6.jsonl"),
    ("seed275", EVALS / "s271_mutation_cohort_v7.jsonl"),
    ("seed276", EVALS / "s271_mutation_cohort_v8.jsonl"),
    ("seed277", EVALS / "s274_mutation_cohort_v9.jsonl"),
)

_TOP_LEVEL_BULLET = re.compile(r"^(?P<marker>[*-])\s+(?P<body>\S.*)$")
_DEF_BODY = re.compile(
    r"^(?P<label>(?!https?\b)[^:|]{2,80}?):\s+(?P<description>\S.*)$",
    re.IGNORECASE,
)
_STRUCTURAL_LINE = re.compile(r"^(?:#{1,6}\s|```|~~~|\||>|\d+[.)]\s)")


@dataclass(frozen=True)
class DefinitionItem:
    start: int
    end: int
    header_end: int
    marker: str
    label: str


@dataclass(frozen=True)
class DefinitionBlock:
    start: int
    end: int
    items: tuple[DefinitionItem, ...]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_lf(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _line_records(text: str) -> list[tuple[int, int, str]]:
    records: list[tuple[int, int, str]] = []
    cursor = 0
    for raw in text.splitlines(keepends=True):
        body = raw.rstrip("\r\n")
        records.append((cursor, cursor + len(body), body))
        cursor += len(raw)
    if not records and text:
        records.append((0, len(text), text))
    return records


def _definition_head(line: str) -> tuple[str, str, int] | None:
    bullet = _TOP_LEVEL_BULLET.fullmatch(line)
    if not bullet:
        return None
    body = bullet.group("body")
    match = _DEF_BODY.fullmatch(body)
    if not match:
        return None
    label = match.group("label").strip(" *_`").strip()
    if not label or not any(char.isalpha() for char in label):
        return None
    # Absolute offset from the physical line start through the label colon.
    header_end_rel = line.index(":") + 1
    return bullet.group("marker"), label, header_end_rel


def parse_definition_blocks(text: str) -> list[DefinitionBlock]:
    """Parse only unindented, contiguous Markdown definition-list records.

    A block stops on headings, tables, fences, blockquotes, numbered lists,
    unindented prose or any indentation mismatch.  Continuation lines are
    intentionally unsupported: the screen fails closed instead of guessing a
    Markdown record boundary.
    """

    lines = _line_records(text)
    heads: list[tuple[int, int, int, str, str, int]] = []
    for idx, (start, end, line) in enumerate(lines):
        parsed = _definition_head(line)
        if parsed is None:
            continue
        marker, label, header_end_rel = parsed
        heads.append((idx, start, end, marker, label, start + header_end_rel))

    groups: list[list[tuple[int, int, int, str, str, int]]] = []
    current: list[tuple[int, int, int, str, str, int]] = []
    for head in heads:
        if not current:
            current = [head]
            continue
        previous = current[-1]
        intervening = lines[previous[0] + 1 : head[0]]
        same_marker = head[3] == previous[3]
        whitespace_only = all(not line.strip() for _, _, line in intervening)
        if same_marker and whitespace_only:
            current.append(head)
        else:
            if len(current) >= 2:
                groups.append(current)
            current = [head]
    if len(current) >= 2:
        groups.append(current)

    blocks: list[DefinitionBlock] = []
    for group in groups:
        if len(group) > MAX_BLOCK_ITEMS:
            continue
        items: list[DefinitionItem] = []
        for idx, head in enumerate(group):
            item_end = head[2]
            # Between siblings only blank lines are allowed, so a complete item
            # is exactly its definition line; this makes the receipt unambiguous.
            items.append(
                DefinitionItem(
                    start=head[1],
                    end=item_end,
                    header_end=head[5],
                    marker=head[3],
                    label=head[4],
                )
            )
        # Defensive rejection if a structural line somehow appeared in a span.
        if any(
            _STRUCTURAL_LINE.match(text[item.start : item.end].lstrip())
            for item in items
        ):
            continue
        blocks.append(DefinitionBlock(items[0].start, items[-1].end, tuple(items)))
    return blocks


def _valid_base_receipts(candidate: dict[str, Any]) -> bool:
    content = candidate.get("content")
    candidate_id = str(candidate.get("id") or "")
    cards = candidate.get("coverage_cards")
    if not isinstance(content, str) or not content or not candidate_id:
        return False
    if not isinstance(cards, list) or not cards:
        return False
    for card in cards:
        if not isinstance(card, dict) or card.get("exact_source_span_validated") is not True:
            return False
        start, end, quote = card.get("start"), card.get("end"), card.get("quote")
        if (
            card.get("candidate_id") != candidate_id
            or isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or not isinstance(quote, str)
            or not 0 <= start < end <= len(content)
            or content[start:end] != quote
        ):
            return False
    return True


def _merge_ranges(ranges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(set(ranges)):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _overlap(start: int, end: int, ranges: Iterable[tuple[int, int]]) -> int:
    return sum(max(0, min(end, right) - max(start, left)) for left, right in ranges)


def derive_missing_definition_sibling_cards(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Return zero or one separately receipted omitted definition sibling.

    Fail closed unless exactly one eligible block has exactly one wholly omitted
    item and every other item has an exact selector-card overlap that includes
    the item's bullet and label colon.  Partial selected items are allowed; this
    is the target shape observed in the preflight without reading target text.
    """

    if not _valid_base_receipts(candidate):
        return []
    content = str(candidate["content"])
    candidate_id = str(candidate["id"])
    cards = list(candidate["coverage_cards"])
    ranges = _merge_ranges((int(card["start"]), int(card["end"])) for card in cards)
    candidates: list[tuple[DefinitionBlock, DefinitionItem, list[int]]] = []

    for block in parse_definition_blocks(content):
        omitted: list[DefinitionItem] = []
        support_indices: set[int] = set()
        valid = True
        for item in block.items:
            overlap = _overlap(item.start, item.end, ranges)
            if overlap == 0:
                omitted.append(item)
                continue
            # A selector that touches only a description tail is insufficient.
            item_support = [
                idx
                for idx, card in enumerate(cards)
                if int(card["start"]) <= item.start
                and int(card["end"]) >= item.header_end
                and int(card["start"]) < item.end
                and item.start < int(card["end"])
            ]
            if not item_support:
                valid = False
                break
            support_indices.update(item_support)
        if not valid or len(omitted) != 1:
            continue
        missing = omitted[0]
        if missing.end - missing.start > MAX_CARD_CHARS:
            continue
        candidates.append((block, missing, sorted(support_indices)))

    # One chunk may contain several definition blocks.  Refuse ambiguity instead
    # of silently adding one record selected by ordering.
    if len(candidates) != 1:
        return []
    block, missing, support_indices = candidates[0]
    return [
        {
            "candidate_id": candidate_id,
            "card_class": CARD_CLASS,
            "start": missing.start,
            "end": missing.end,
            "quote": content[missing.start : missing.end],
            "block_start": block.start,
            "block_end": block.end,
            "block_item_count": len(block.items),
            "supporting_coverage_card_indices": support_indices,
            "local_semantic_validated": False,
            "exact_source_span_validated": True,
        }
    ]


def attest_reference(candidate: dict[str, Any], *, enabled: bool) -> dict[str, Any]:
    """Reference attestation used only by the offline screen."""

    output = copy.deepcopy(candidate)
    if not enabled:
        return output
    cards = derive_missing_definition_sibling_cards(output)
    if cards:
        output[CARD_FIELD] = cards
    return output


def has_exact_reference_receipt(candidate: dict[str, Any]) -> bool:
    cards = candidate.get(CARD_FIELD)
    if not isinstance(cards, list) or not cards:
        return False
    base = {key: value for key, value in candidate.items() if key != CARD_FIELD}
    return cards == derive_missing_definition_sibling_cards(base)


def _coverage_card(candidate_id: str, content: str, start: int, end: int) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "start": start,
        "end": end,
        "quote": content[start:end],
        "exact_source_span_validated": True,
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_prereg() -> dict[str, Any]:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    expected = str(prereg["freeze"]["screen_script_sha256_lf"])
    actual = _sha256_lf(Path(__file__))
    if actual != expected:
        raise RuntimeError(f"screen script drift: {actual} != {expected}")
    if int(prereg["seed"]) != SEED:
        raise RuntimeError("preregistered seed drift")
    return prereg


def build_cohort() -> int:
    """GET-only census over the frozen seed-278 document sample."""

    import httpx

    prereg = _load_prereg()
    builder = _load_module("s269_builder_for_s276", "scripts/s269_build_structural_cohort.py")
    rng = random.Random(SEED)
    table = os.environ.get("CHUNKS_TABLE", "chunks_v2")

    prior_docs: set[str] = set()
    prior_manifest: list[dict[str, Any]] = []
    for seed_label, path in PRIOR_COHORT_PATHS:
        rows = _load_jsonl(path)
        docs = {str(row["document_id"]) for row in rows}
        if not docs:
            raise RuntimeError(f"empty prior cohort: {path.name}")
        prior_docs.update(docs)
        prior_manifest.append(
            {
                "seed": seed_label,
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256_lf": _sha256_lf(path),
                "document_count": len(docs),
            }
        )

    with httpx.Client(timeout=30.0) as client:
        corpus = builder.fetch_corpus_docs(client, table)
        base_excluded, base_manifest = builder.build_exclusions(corpus)
        excluded = set(base_excluded) | prior_docs
        eligible = {did: row for did, row in corpus.items() if did not in excluded}
        doc_order = builder.stratified_doc_order(eligible, rng)
        selected_docs = doc_order[:SAMPLED_DOCS]

        fragments_screened = 0
        parsable_blocks = 0
        cohort_rows: list[dict[str, Any]] = []
        for document_id in selected_docs:
            fragments = builder.fetch_doc_fragments(client, table, document_id)
            for fragment in fragments:
                content = str(fragment.get("content") or "")
                if len(content.strip()) < MIN_FRAGMENT_CHARS:
                    continue
                fragments_screened += 1
                blocks = parse_definition_blocks(content)
                parsable_blocks += len(blocks)
                for block_index, block in enumerate(blocks):
                    eligible_targets = [
                        idx
                        for idx, item in enumerate(block.items)
                        if item.end - item.start <= MAX_CARD_CHARS
                    ]
                    if not eligible_targets:
                        continue
                    selector = int(
                        hashlib.sha256(
                            f"{SEED}|{fragment['id']}|{block.start}".encode("utf-8")
                        ).hexdigest(),
                        16,
                    )
                    omitted_index = eligible_targets[selector % len(eligible_targets)]
                    cohort_rows.append(
                        {
                            "schema": "s276_missing_definition_sibling_cohort_row_v1",
                            "seed": SEED,
                            "fragment_id": str(fragment["id"]),
                            "document_id": document_id,
                            "source_file": fragment.get("source_file") or "",
                            "manufacturer": eligible[document_id]["manufacturer"],
                            "content": content,
                            "content_sha256": _sha256_text(content),
                            "block_index": block_index,
                            "block": {
                                "start": block.start,
                                "end": block.end,
                                "items": [asdict(item) for item in block.items],
                            },
                            "omitted_index": omitted_index,
                        }
                    )

    cohort_rows.sort(key=lambda row: (row["manufacturer"], row["document_id"], row["fragment_id"], row["block_index"]))
    with COHORT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in cohort_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    block_docs = {row["document_id"] for row in cohort_rows}
    block_manufacturers = {row["manufacturer"] for row in cohort_rows}
    sibling_histogram: dict[str, int] = {}
    for row in cohort_rows:
        siblings = len(row["block"]["items"]) - 1
        sibling_histogram[str(siblings)] = sibling_histogram.get(str(siblings), 0) + 1

    build = {
        "schema": "s276_missing_definition_sibling_build_c278_v1",
        "created_utc": _now(),
        "seed": SEED,
        "chunks_table": table,
        "access": {"http_methods": ["GET"], "model_calls": 0, "database_writes": 0},
        "corpus_docs_servible": len(corpus),
        "base_excluded_docs": len(base_excluded & set(corpus)),
        "prior_cohort_docs": len(prior_docs & set(corpus)),
        "excluded_docs_total": len(excluded & set(corpus)),
        "eligible_docs": len(eligible),
        "sampled_docs": len(selected_docs),
        "fragments_screened": fragments_screened,
        "parsable_definition_blocks": parsable_blocks,
        "eligible_blocks": len(cohort_rows),
        "eligible_block_documents": len(block_docs),
        "eligible_block_manufacturers": len(block_manufacturers),
        "sibling_count_histogram": dict(sorted(sibling_histogram.items())),
        "sampled_document_ids_sha256": _sha256_text("\n".join(selected_docs)),
        "freshness": {
            "overlap_with_prior_cohort_docs": len(set(selected_docs) & prior_docs),
            "prior_cohorts": prior_manifest,
            "base_exclusion_manifest": base_manifest,
        },
        "cohort_path": str(COHORT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "cohort_sha256_lf": _sha256_lf(COHORT_PATH),
        "prereg_sha256_lf": _sha256_lf(PREREG_PATH),
        "design_sha256_lf": _sha256_lf(DESIGN_PATH),
        "gates": prereg["gates"],
    }
    BUILD_PATH.write_text(json.dumps(build, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        f"seed-{SEED}: {len(selected_docs)} docs, {fragments_screened} fragments, "
        f"{len(cohort_rows)} eligible definition blocks"
    )
    return 0


def _candidate_for_case(row: dict[str, Any], *, truncated: bool, clean: bool = False) -> tuple[dict[str, Any], dict[str, Any] | None]:
    content = str(row["content"])
    candidate_id = f"s276-{row['fragment_id']}-{row['block_index']}"
    items = row["block"]["items"]
    omitted_index = int(row["omitted_index"])
    selected_indices = list(range(len(items))) if clean else [idx for idx in range(len(items)) if idx != omitted_index]
    cards: list[dict[str, Any]] = []
    truncated_done = False
    for idx in selected_indices:
        item = items[idx]
        start, end = int(item["start"]), int(item["end"])
        if truncated and not truncated_done and idx != omitted_index:
            minimum = int(item["header_end"])
            proposed = start + max(1, int((end - start) * 0.72))
            clipped = max(minimum, proposed)
            if clipped < end:
                end = clipped
                truncated_done = True
        cards.append(_coverage_card(candidate_id, content, start, end))
    expected = None if clean else items[omitted_index]
    candidate = {"id": candidate_id, "content": content, "coverage_cards": cards}
    candidate["_truncated_case_valid"] = truncated_done if truncated else True
    return candidate, expected


def _strip_case_metadata(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in candidate.items() if not key.startswith("_")}


def _boundary_controls(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Controls built from fresh item text but separated by forbidden boundaries."""

    content = str(row["content"])
    items = row["block"]["items"]
    if len(items) < 2:
        return []
    left = content[int(items[0]["start"]) : int(items[0]["end"])]
    right = content[int(items[1]["start"]) : int(items[1]["end"])]
    separators = {
        "heading": "\n\n## Control boundary\n\n",
        "prose": "\n\nTexto de control fuera del registro.\n\n",
        "table": "\n\n| Campo | Valor |\n| --- | --- |\n| A | B |\n\n",
    }
    controls: list[dict[str, Any]] = []
    for label, separator in separators.items():
        mutated = left + separator + right
        candidate_id = f"s276-control-{label}-{row['fragment_id']}-{row['block_index']}"
        controls.append(
            {
                "label": label,
                "candidate": {
                    "id": candidate_id,
                    "content": mutated,
                    "coverage_cards": [_coverage_card(candidate_id, mutated, 0, len(left))],
                },
            }
        )
    oversize_right = "* Campo de control: " + ("x" * (MAX_CARD_CHARS + 20))
    oversize = left + "\n\n" + oversize_right
    oversize_id = f"s276-control-oversize-{row['fragment_id']}-{row['block_index']}"
    controls.append(
        {
            "label": "oversize",
            "candidate": {
                "id": oversize_id,
                "content": oversize,
                "coverage_cards": [_coverage_card(oversize_id, oversize, 0, len(left))],
            },
        }
    )
    return controls


def run_screen() -> int:
    prereg = _load_prereg()
    build = json.loads(BUILD_PATH.read_text(encoding="utf-8"))
    if build["cohort_sha256_lf"] != _sha256_lf(COHORT_PATH):
        raise RuntimeError("cohort drift")
    rows = _load_jsonl(COHORT_PATH)
    result_rows: list[dict[str, Any]] = []

    totals = {
        "full_cases": 0,
        "full_hits": 0,
        "truncated_cases": 0,
        "truncated_hits": 0,
        "clean_cases": 0,
        "clean_fp": 0,
        "boundary_controls": 0,
        "boundary_fp": 0,
        "oversize_controls": 0,
        "oversize_fp": 0,
        "cross_record_fp": 0,
        "receipt_tamper_accept": 0,
        "flag_off_drift": 0,
    }
    added_chars: list[int] = []

    for row in rows:
        case_result: dict[str, Any] = {
            "fragment_id": row["fragment_id"],
            "document_id": row["document_id"],
            "manufacturer": row["manufacturer"],
            "block_index": row["block_index"],
            "block_item_count": len(row["block"]["items"]),
        }

        for variant in ("full", "truncated"):
            raw, expected = _candidate_for_case(row, truncated=variant == "truncated")
            valid_case = bool(raw.pop("_truncated_case_valid"))
            if not valid_case:
                case_result[variant] = {"puntuable": False, "reason": "item_too_short_to_truncate"}
                continue
            candidate = _strip_case_metadata(raw)
            cards = derive_missing_definition_sibling_cards(candidate)
            expected_span = (int(expected["start"]), int(expected["end"])) if expected else None
            actual_span = (int(cards[0]["start"]), int(cards[0]["end"])) if len(cards) == 1 else None
            hit = actual_span == expected_span
            totals[f"{variant}_cases"] += 1
            totals[f"{variant}_hits"] += int(hit)
            if cards and actual_span != expected_span:
                totals["cross_record_fp"] += 1
            if hit:
                added_chars.append(actual_span[1] - actual_span[0])
            case_result[variant] = {
                "puntuable": True,
                "hit": hit,
                "expected_span": list(expected_span) if expected_span else None,
                "actual_span": list(actual_span) if actual_span else None,
            }

            if variant == "full" and hit:
                attested = attest_reference(candidate, enabled=True)
                tampered = copy.deepcopy(attested)
                tampered[CARD_FIELD][0]["quote"] += "x"
                totals["receipt_tamper_accept"] += int(has_exact_reference_receipt(tampered))
                off = attest_reference(candidate, enabled=False)
                totals["flag_off_drift"] += int(_canonical(off) != _canonical(candidate))

        clean_raw, _ = _candidate_for_case(row, truncated=False, clean=True)
        clean_raw.pop("_truncated_case_valid")
        clean_cards = derive_missing_definition_sibling_cards(clean_raw)
        totals["clean_cases"] += 1
        totals["clean_fp"] += int(bool(clean_cards))
        case_result["clean_fp"] = bool(clean_cards)

        control_results: dict[str, bool] = {}
        for control in _boundary_controls(row):
            fired = bool(derive_missing_definition_sibling_cards(control["candidate"]))
            label = str(control["label"])
            control_results[label] = fired
            if label == "oversize":
                totals["oversize_controls"] += 1
                totals["oversize_fp"] += int(fired)
            else:
                totals["boundary_controls"] += 1
                totals["boundary_fp"] += int(fired)
        case_result["control_fp"] = control_results
        result_rows.append(case_result)

    with RESULT_ROWS_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in result_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def rate(num: int, den: int) -> float | None:
        return round(num / den, 6) if den else None

    full_recall = rate(totals["full_hits"], totals["full_cases"])
    truncated_recall = rate(totals["truncated_hits"], totals["truncated_cases"])
    manufacturer_count = int(build["eligible_block_manufacturers"])
    document_count = int(build["eligible_block_documents"])
    gates = prereg["gates"]
    checks = {
        "freshness_overlap": {
            "value": int(build["freshness"]["overlap_with_prior_cohort_docs"]),
            "pass": int(build["freshness"]["overlap_with_prior_cohort_docs"]) <= int(gates["freshness_overlap_max"]),
        },
        "sampled_docs": {"value": int(build["sampled_docs"]), "pass": int(build["sampled_docs"]) >= int(gates["sampled_docs_min"])},
        "eligible_blocks": {"value": len(rows), "pass": len(rows) >= int(gates["eligible_blocks_min"])},
        "eligible_documents": {"value": document_count, "pass": document_count >= int(gates["eligible_documents_min"])},
        "eligible_manufacturers": {"value": manufacturer_count, "pass": manufacturer_count >= int(gates["eligible_manufacturers_min"])},
        "full_selection_recall": {"value": full_recall, "pass": full_recall is not None and full_recall >= float(gates["full_selection_recall_min"])},
        "truncated_selection_recall": {"value": truncated_recall, "pass": truncated_recall is not None and truncated_recall >= float(gates["truncated_selection_recall_min"])},
        "clean_fp": {"value": totals["clean_fp"], "pass": totals["clean_fp"] <= int(gates["clean_fp_max"])},
        "boundary_fp": {"value": totals["boundary_fp"], "pass": totals["boundary_fp"] <= int(gates["boundary_fp_max"])},
        "oversize_fp": {"value": totals["oversize_fp"], "pass": totals["oversize_fp"] <= int(gates["oversize_fp_max"])},
        "cross_record_fp": {"value": totals["cross_record_fp"], "pass": totals["cross_record_fp"] <= int(gates["cross_record_fp_max"])},
        "receipt_tamper_accept": {"value": totals["receipt_tamper_accept"], "pass": totals["receipt_tamper_accept"] <= int(gates["receipt_tamper_accept_max"])},
        "flag_off_drift": {"value": totals["flag_off_drift"], "pass": totals["flag_off_drift"] <= int(gates["flag_off_drift_max"])},
    }
    verdict = "GO_OFFLINE_SCREEN" if all(check["pass"] for check in checks.values()) else "NO_GO_OFFLINE_SCREEN"
    result = {
        "schema": "s276_missing_definition_sibling_screen_result_v1",
        "created_utc": _now(),
        "status": verdict,
        "seed": SEED,
        "access": build["access"],
        "population": {
            "sampled_docs": build["sampled_docs"],
            "fragments_screened": build["fragments_screened"],
            "eligible_blocks": len(rows),
            "eligible_documents": document_count,
            "eligible_manufacturers": manufacturer_count,
            "sibling_count_histogram": build["sibling_count_histogram"],
        },
        "measures": totals
        | {
            "full_selection_recall": full_recall,
            "truncated_selection_recall": truncated_recall,
            "added_chars_min": min(added_chars) if added_chars else None,
            "added_chars_max": max(added_chars) if added_chars else None,
            "added_chars_mean": round(sum(added_chars) / len(added_chars), 2) if added_chars else None,
        },
        "checks": checks,
        "artifacts": {
            "design_sha256_lf": _sha256_lf(DESIGN_PATH),
            "prereg_sha256_lf": _sha256_lf(PREREG_PATH),
            "cohort_sha256_lf": _sha256_lf(COHORT_PATH),
            "build_sha256_lf": _sha256_lf(BUILD_PATH),
            "result_rows_sha256_lf": _sha256_lf(RESULT_ROWS_PATH),
            "screen_script_sha256_lf": _sha256_lf(Path(__file__)),
        },
        "scope_limits": [
            "0 FP means no cross-record expansion in deterministic form controls; it is not a user-visible semantic FP estimate.",
            "The corpus cohort is selected by the same explicit structural grammar; false negatives outside that grammar are not measured.",
            "No answer generation, target scoring or conversion credit is part of this screen.",
        ],
        "next_step": (
            "Eligible for adversarial design review of a default-off runtime build and a fresh organic A/B; "
            "not eligible for a fifth probe on the six S274 targets."
            if verdict == "GO_OFFLINE_SCREEN"
            else "Stop this mechanism or revise the preregistered design on a new population; do not run a paid A/B."
        ),
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    gate = {
        "schema": "s276_missing_definition_sibling_screen_gate_v1",
        "status": verdict,
        "seed": SEED,
        "checks": checks,
        "result_path": str(RESULT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "result_sha256_lf": _sha256_lf(RESULT_PATH),
    }
    GATE_PATH.write_text(yaml.safe_dump(gate, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    print(f"{verdict}: {len(rows)} blocks, full={full_recall}, truncated={truncated_recall}, FP={totals['clean_fp'] + totals['boundary_fp'] + totals['oversize_fp'] + totals['cross_record_fp']}")
    return 0 if verdict == "GO_OFFLINE_SCREEN" else 2


def check_artifacts() -> int:
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    gate = yaml.safe_load(GATE_PATH.read_text(encoding="utf-8"))
    if gate["result_sha256_lf"] != _sha256_lf(RESULT_PATH):
        raise RuntimeError("gate/result drift")
    if result["artifacts"]["cohort_sha256_lf"] != _sha256_lf(COHORT_PATH):
        raise RuntimeError("result/cohort drift")
    if result["artifacts"]["result_rows_sha256_lf"] != _sha256_lf(RESULT_ROWS_PATH):
        raise RuntimeError("result rows drift")
    print(f"OK: {gate['status']} ({RESULT_PATH.relative_to(ROOT)})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build-cohort", action="store_true")
    action.add_argument("--run", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    if args.build_cohort:
        return build_cohort()
    if args.run:
        return run_screen()
    return check_artifacts()


if __name__ == "__main__":
    raise SystemExit(main())
