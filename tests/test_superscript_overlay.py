from __future__ import annotations

import copy
import hashlib

import pytest

from src.reingest.superscript_overlay import (
    NumericSuperscriptSignal,
    _numeric_signal_from_spans,
    anchor_tokens,
    preserve_numeric_superscripts,
)


def _signal(
    *,
    page: int = 5,
    base: str = "10",
    script: str = "5",
    anchors: tuple[str, ...] = ("life", "operations", "time"),
) -> NumericSuperscriptSignal:
    return NumericSuperscriptSignal(
        page_number=page,
        base=base,
        script=script,
        flattened_token=base + script,
        explicit_markup=f"{base}<sup>{script}</sup>",
        anchor_tokens=anchors,
        base_font_size=7.98,
        script_font_size=4.98,
        font_size_ratio=0.62406,
        baseline_delta_points=3.0,
        horizontal_gap_points=0.014,
        base_bbox=(243.23, 762.24, 252.11, 771.15),
        script_bbox=(252.124, 761.96, 254.893, 767.515),
    )


def _record(pdf_bytes: bytes, markdown: str) -> dict:
    return {
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "result": {
            "pages": [
                {
                    "page": 5,
                    "md": markdown,
                    "text": "raw text remains unchanged",
                    "images": [],
                }
            ]
        },
    }


def test_geometry_requires_pdf_superscript_flag_and_elevation():
    previous = {
        "text": "10",
        "size": 8.0,
        "origin": (0.0, 10.0),
        "bbox": (0.0, 0.0, 8.0, 10.0),
    }
    script = {
        "text": "5",
        "size": 5.0,
        "origin": (8.0, 7.0),
        "bbox": (8.0, 0.0, 10.0, 7.0),
        "flags": 1,
    }
    assert _numeric_signal_from_spans(previous, script, "Life Time 105 Operations", 5)
    assert _numeric_signal_from_spans(previous, {**script, "flags": 0}, "x", 5) is None
    assert (
        _numeric_signal_from_spans(
            previous, {**script, "origin": (8.0, 9.8)}, "x", 5
        )
        is None
    )


def test_anchor_tokens_are_case_and_accent_insensitive():
    assert anchor_tokens("OPERACIÓN eléctrica, Operacion") == ("electrica", "operacion")


def test_unique_context_bound_token_is_preserved_without_mutating_raw(tmp_path):
    pdf_bytes = b"synthetic-pdf-receipt"
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(pdf_bytes)
    raw = _record(
        pdf_bytes,
        "| Life Time | 105 | Operations |\n| Other | 200 | cycles |",
    )
    frozen = copy.deepcopy(raw)
    result = preserve_numeric_superscripts(raw, pdf, signals=(_signal(),))
    assert raw == frozen
    assert result.record["result"]["pages"][0]["md"] == (
        "| Life Time | 10<sup>5</sup> | Operations |\n| Other | 200 | cycles |"
    )
    assert result.record["result"]["pages"][0]["text"] == "raw text remains unchanged"
    assert len(result.applied) == 1
    assert result.applied[0]["matched_anchors"] == ["life", "operations", "time"]
    assert result.abstained == ()


@pytest.mark.parametrize(
    ("markdown", "reason"),
    [
        ("Life Time 105 Operations and duplicate 105", "flattened_token_not_unique"),
        ("Unrelated token 105 without source anchors", "insufficient_same_line_anchors"),
        ("Life Time 10^5 Operations", "flattened_token_not_unique"),
    ],
)
def test_ambiguous_or_already_explicit_candidates_abstain(tmp_path, markdown, reason):
    pdf_bytes = b"synthetic-pdf-receipt"
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(pdf_bytes)
    raw = _record(pdf_bytes, markdown)
    result = preserve_numeric_superscripts(raw, pdf, signals=(_signal(),))
    assert result.record == raw
    assert result.applied == ()
    assert result.abstained[0]["reason"] == reason


def test_competing_signals_for_one_offset_abstain(tmp_path):
    pdf_bytes = b"synthetic-pdf-receipt"
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(pdf_bytes)
    raw = _record(pdf_bytes, "Life Time 105 Operations")
    result = preserve_numeric_superscripts(
        raw,
        pdf,
        signals=(_signal(), _signal()),
    )
    assert result.record == raw
    assert result.applied == ()
    assert {row["reason"] for row in result.abstained} == {"mapping_conflict"}


def test_second_pass_is_idempotent(tmp_path):
    pdf_bytes = b"synthetic-pdf-receipt"
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(pdf_bytes)
    first = preserve_numeric_superscripts(
        _record(pdf_bytes, "Life Time 105 Operations"),
        pdf,
        signals=(_signal(),),
    )
    second = preserve_numeric_superscripts(first.record, pdf, signals=(_signal(),))
    assert second.record == first.record
    assert second.applied == ()
    assert second.abstained[0]["reason"] == "flattened_token_not_unique"


def test_pdf_sha_mismatch_fails_closed(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"actual")
    raw = _record(b"expected", "Life Time 105 Operations")
    with pytest.raises(ValueError, match="SHA-256"):
        preserve_numeric_superscripts(raw, pdf, signals=(_signal(),))
