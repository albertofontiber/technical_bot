"""Geometry-bound preservation of numeric PDF superscripts.

The immutable extraction record remains the source artifact. This module derives
an in-memory copy whose Markdown preserves an unambiguous numeric superscript as
literal ``<sup>`` markup. It deliberately does not decide whether the script is
an exponent, a footnote, or another typographic relation.
"""
from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import fitz


MAX_SCRIPT_TO_BASE_FONT_RATIO = 0.80
MIN_BASELINE_ELEVATION_POINTS = 0.5
MIN_HORIZONTAL_GAP_POINTS = -0.25
MAX_HORIZONTAL_GAP_POINTS = 1.25
MAX_HORIZONTAL_GAP_BASE_RATIO = 0.30
MIN_MATCHED_ANCHORS = 2
MIN_VISUAL_ROW_OVERLAP_RATIO = 0.60
MAX_VISUAL_ROW_BASELINE_DELTA_POINTS = 1.0
MAX_VISUAL_ROW_HORIZONTAL_FONT_WIDTHS = 25.0

_BASE_DIGITS = re.compile(r"(\d+)$")
_ALPHA_TOKEN = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


@dataclass(frozen=True)
class NumericSuperscriptSignal:
    page_number: int
    base: str
    script: str
    flattened_token: str
    explicit_markup: str
    anchor_tokens: tuple[str, ...]
    base_font_size: float
    script_font_size: float
    font_size_ratio: float
    baseline_delta_points: float
    horizontal_gap_points: float
    base_origin_y: float
    script_origin_y: float
    base_bbox: tuple[float, float, float, float]
    script_bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class SuperscriptOverlayResult:
    record: dict[str, Any]
    applied: tuple[dict[str, Any], ...]
    abstained: tuple[dict[str, Any], ...]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _text_sha256(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def pdf_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fold_token(token: str) -> str:
    decomposed = unicodedata.normalize("NFKD", token.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def anchor_tokens(text: str) -> tuple[str, ...]:
    return tuple(sorted({_fold_token(token) for token in _ALPHA_TOKEN.findall(text)}))


def _numeric_signal_from_spans(
    previous: dict[str, Any],
    script: dict[str, Any],
    line_text: str,
    page_number: int,
) -> NumericSuperscriptSignal | None:
    script_text = str(script.get("text") or "").strip()
    if not script_text.isdigit() or not (int(script.get("flags") or 0) & 1):
        return None
    previous_text = str(previous.get("text") or "").rstrip()
    match = _BASE_DIGITS.search(previous_text)
    if match is None:
        return None
    base = match.group(1)
    base_size = float(previous.get("size") or 0)
    script_size = float(script.get("size") or 0)
    if base_size <= 0 or script_size <= 0:
        return None
    ratio = script_size / base_size
    base_origin = previous.get("origin") or (0, 0)
    script_origin = script.get("origin") or (0, 0)
    baseline_delta = float(base_origin[1]) - float(script_origin[1])
    base_bbox = tuple(float(value) for value in (previous.get("bbox") or (0, 0, 0, 0)))
    script_bbox = tuple(float(value) for value in (script.get("bbox") or (0, 0, 0, 0)))
    horizontal_gap = script_bbox[0] - base_bbox[2]
    max_gap = max(MAX_HORIZONTAL_GAP_POINTS, base_size * MAX_HORIZONTAL_GAP_BASE_RATIO)
    if ratio > MAX_SCRIPT_TO_BASE_FONT_RATIO:
        return None
    if baseline_delta < MIN_BASELINE_ELEVATION_POINTS:
        return None
    if horizontal_gap < MIN_HORIZONTAL_GAP_POINTS or horizontal_gap > max_gap:
        return None
    return NumericSuperscriptSignal(
        page_number=page_number,
        base=base,
        script=script_text,
        flattened_token=base + script_text,
        explicit_markup=f"{base}<sup>{script_text}</sup>",
        anchor_tokens=anchor_tokens(line_text),
        base_font_size=round(base_size, 6),
        script_font_size=round(script_size, 6),
        font_size_ratio=round(ratio, 6),
        baseline_delta_points=round(baseline_delta, 6),
        horizontal_gap_points=round(horizontal_gap, 6),
        base_origin_y=round(float(base_origin[1]), 6),
        script_origin_y=round(float(script_origin[1]), 6),
        base_bbox=tuple(round(value, 6) for value in base_bbox),
        script_bbox=tuple(round(value, 6) for value in script_bbox),
    )


def _visual_row_anchor_tokens(
    spans: list[dict[str, Any]],
    signal: NumericSuperscriptSignal,
) -> tuple[str, ...]:
    """Collect alphabetic anchors from the same geometry row across PDF blocks."""
    base_top, base_bottom = signal.base_bbox[1], signal.base_bbox[3]
    base_height = max(base_bottom - base_top, 0.001)
    interval_left = signal.base_bbox[0]
    interval_right = signal.script_bbox[2]
    max_distance = signal.base_font_size * MAX_VISUAL_ROW_HORIZONTAL_FONT_WIDTHS
    selected: set[str] = set()
    for span in spans:
        bbox = tuple(float(value) for value in (span.get("bbox") or (0, 0, 0, 0)))
        span_top, span_bottom = bbox[1], bbox[3]
        span_height = max(span_bottom - span_top, 0.001)
        overlap = max(0.0, min(base_bottom, span_bottom) - max(base_top, span_top))
        overlap_ratio = overlap / min(base_height, span_height)
        origin = span.get("origin") or (0, 0)
        baseline_delta = abs(float(origin[1]) - signal.base_origin_y)
        if (
            overlap_ratio < MIN_VISUAL_ROW_OVERLAP_RATIO
            and baseline_delta > MAX_VISUAL_ROW_BASELINE_DELTA_POINTS
        ):
            continue
        if bbox[2] < interval_left:
            horizontal_distance = interval_left - bbox[2]
        elif bbox[0] > interval_right:
            horizontal_distance = bbox[0] - interval_right
        else:
            horizontal_distance = 0.0
        if horizontal_distance > max_distance:
            continue
        selected.update(anchor_tokens(str(span.get("text") or "")))
    return tuple(sorted(selected))


def extract_numeric_superscript_signals(
    pdf_path: str | Path,
) -> tuple[NumericSuperscriptSignal, ...]:
    """Return conservative numeric superscript signals from PDF glyph geometry."""
    signals: list[NumericSuperscriptSignal] = []
    fitz.TOOLS.mupdf_display_errors(False)
    with fitz.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf):
            blocks = page.get_text("dict", sort=True).get("blocks", [])
            page_spans = [
                span
                for block in blocks
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ]
            page_signals: list[NumericSuperscriptSignal] = []
            for block in blocks:
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    line_text = "".join(str(span.get("text") or "") for span in spans)
                    previous_nonblank: dict[str, Any] | None = None
                    for span in spans:
                        if previous_nonblank is not None:
                            signal = _numeric_signal_from_spans(
                                previous_nonblank,
                                span,
                                line_text,
                                page_index + 1,
                            )
                            if signal is not None:
                                page_signals.append(signal)
                        if str(span.get("text") or "").strip():
                            previous_nonblank = span
            signals.extend(
                replace(
                    signal,
                    anchor_tokens=_visual_row_anchor_tokens(page_spans, signal),
                )
                for signal in page_signals
            )
    return tuple(signals)


def _complete_token_matches(text: str, token: str) -> list[re.Match[str]]:
    return list(re.finditer(rf"(?<![\w.]){re.escape(token)}(?![\w.])", text))


def _line_window(text: str, offset: int, radius: int = 1) -> str:
    lines = text.splitlines(keepends=True)
    cursor = 0
    target = 0
    for index, line in enumerate(lines):
        if cursor <= offset < cursor + len(line):
            target = index
            break
        cursor += len(line)
    start = max(0, target - radius)
    end = min(len(lines), target + radius + 1)
    return "".join(lines[start:end])


def _abstention(signal: NumericSuperscriptSignal, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "page_number": signal.page_number,
        "flattened_token": signal.flattened_token,
        "reason": reason,
        **extra,
    }


def preserve_numeric_superscripts(
    extraction_record: dict[str, Any],
    pdf_path: str | Path,
    *,
    signals: tuple[NumericSuperscriptSignal, ...] | None = None,
) -> SuperscriptOverlayResult:
    """Derive a Markdown-preserving copy plus exact applied/abstained receipts.

    ``signals`` is injectable for deterministic unit tests. In normal operation
    it must be omitted so geometry is read from the SHA-bound PDF.
    """
    expected_sha = str(extraction_record.get("sha256") or "").casefold()
    actual_sha = pdf_sha256(pdf_path)
    if not expected_sha or actual_sha != expected_sha:
        raise ValueError("PDF SHA-256 does not match extraction record")

    derived = copy.deepcopy(extraction_record)
    pages = {
        page.get("page"): page
        for page in derived.get("result", {}).get("pages", [])
        if isinstance(page, dict)
    }
    source_signals = signals if signals is not None else extract_numeric_superscript_signals(pdf_path)
    proposals: list[dict[str, Any]] = []
    abstained: list[dict[str, Any]] = []

    for signal in source_signals:
        page = pages.get(signal.page_number)
        if page is None or not isinstance(page.get("md"), str):
            abstained.append(_abstention(signal, "missing_markdown_page"))
            continue
        markdown = page["md"]
        matches = _complete_token_matches(markdown, signal.flattened_token)
        if len(matches) != 1:
            abstained.append(
                _abstention(signal, "flattened_token_not_unique", occurrences=len(matches))
            )
            continue
        match = matches[0]
        window = _line_window(markdown, match.start())
        window_anchors = set(anchor_tokens(window))
        matched_anchors = tuple(
            sorted(set(signal.anchor_tokens).intersection(window_anchors))
        )
        if len(matched_anchors) < MIN_MATCHED_ANCHORS:
            abstained.append(
                _abstention(
                    signal,
                    "insufficient_same_line_anchors",
                    matched_anchors=list(matched_anchors),
                )
            )
            continue
        proposals.append(
            {
                "signal": signal,
                "page_number": signal.page_number,
                "start": match.start(),
                "end": match.end(),
                "matched_anchors": matched_anchors,
            }
        )

    by_location: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for proposal in proposals:
        key = (proposal["page_number"], proposal["start"], proposal["end"])
        by_location.setdefault(key, []).append(proposal)

    accepted: list[dict[str, Any]] = []
    for rows in by_location.values():
        replacements = {row["signal"].explicit_markup for row in rows}
        if len(rows) != 1 or len(replacements) != 1:
            for row in rows:
                abstained.append(_abstention(row["signal"], "mapping_conflict"))
            continue
        accepted.append(rows[0])

    accepted.sort(key=lambda row: (row["page_number"], row["start"]))
    non_overlapping: list[dict[str, Any]] = []
    previous_by_page: dict[int, int] = {}
    for row in accepted:
        previous_end = previous_by_page.get(row["page_number"], -1)
        if row["start"] < previous_end:
            abstained.append(_abstention(row["signal"], "overlapping_mapping"))
            continue
        non_overlapping.append(row)
        previous_by_page[row["page_number"]] = row["end"]

    applied: list[dict[str, Any]] = []
    for page_number in sorted({row["page_number"] for row in non_overlapping}):
        page = pages[page_number]
        original = page["md"]
        updated = original
        page_rows = [row for row in non_overlapping if row["page_number"] == page_number]
        for row in sorted(page_rows, key=lambda item: item["start"], reverse=True):
            signal = row["signal"]
            updated = (
                updated[: row["start"]]
                + signal.explicit_markup
                + updated[row["end"] :]
            )
        page["md"] = updated
        for row in page_rows:
            signal = row["signal"]
            applied.append(
                {
                    "pdf_sha256": actual_sha,
                    "page_number": page_number,
                    "source_start": row["start"],
                    "source_end": row["end"],
                    "original_token": signal.flattened_token,
                    "derived_token": signal.explicit_markup,
                    "matched_anchors": list(row["matched_anchors"]),
                    "original_page_markdown_sha256": _text_sha256(original),
                    "derived_page_markdown_sha256": _text_sha256(updated),
                    "geometry": asdict(signal),
                }
            )

    return SuperscriptOverlayResult(
        record=derived,
        applied=tuple(applied),
        abstained=tuple(abstained),
    )
