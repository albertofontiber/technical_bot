import copy
import json
from pathlib import Path

import pytest

from src.reingest import extraction_derivation as derivation
from src.reingest.superscript_overlay import SuperscriptOverlayResult


def _raw() -> bytes:
    return json.dumps(
        {
            "sha256": "a" * 64,
            "source_path": "manual.pdf",
            "result": {"pages": [{"page": 1, "md": "Life time 105 operations"}]},
        },
        separators=(",", ":"),
    ).encode()


def _overlay(record, _pdf_path):
    derived = copy.deepcopy(record)
    derived["result"]["pages"][0]["md"] = "Life time 10<sup>5</sup> operations"
    receipt = {
        "pdf_sha256": "a" * 64,
        "page_number": 1,
        "source_start": 10,
        "source_end": 13,
        "original_token": "105",
        "derived_token": "10<sup>5</sup>",
        "matched_anchors": ["life", "time", "operations"],
        "geometry": {"font_size_ratio": 0.7},
    }
    return SuperscriptOverlayResult(
        record=derived,
        applied=(receipt,),
        abstained=(),
    )


def test_derivation_is_deterministic_content_addressed_and_source_immutable(monkeypatch):
    raw = _raw()
    monkeypatch.setattr(derivation, "preserve_numeric_superscripts", _overlay)
    first = derivation.derive_numeric_superscripts(raw, Path("manual.pdf"))
    second = derivation.derive_numeric_superscripts(raw, Path("manual.pdf"))

    assert first == second
    assert json.loads(raw)["result"]["pages"][0]["md"] == "Life time 105 operations"
    assert first.manifest["applied_count"] == 1
    assert first.manifest["changed_pages"] == [1]
    assert not derivation.validate_derivation(first)


def test_derivation_integrity_detects_record_and_receipt_tampering(monkeypatch):
    monkeypatch.setattr(derivation, "preserve_numeric_superscripts", _overlay)
    envelope = derivation.derive_numeric_superscripts(_raw(), Path("manual.pdf"))

    changed_record = copy.deepcopy(envelope.record)
    changed_record["result"]["pages"][0]["md"] += " tampered"
    assert "derived_artifact_sha256" in derivation.validate_derivation(
        derivation.ExtractionDerivation(changed_record, envelope.manifest)
    )

    changed_manifest = copy.deepcopy(envelope.manifest)
    changed_manifest["receipts"][0]["derived_token"] = "10<sup>6</sup>"
    failures = derivation.validate_derivation(
        derivation.ExtractionDerivation(envelope.record, changed_manifest)
    )
    assert "applied_receipts_sha256" in failures

    assert "source_raw_artifact_sha256" in derivation.validate_derivation(
        envelope, source_raw=_raw() + b" "
    )


def test_derivation_rejects_source_mutation(monkeypatch):
    def mutating_overlay(record, _pdf_path):
        record["result"]["pages"][0]["md"] = "mutated"
        return SuperscriptOverlayResult(record=record, applied=(), abstained=())

    monkeypatch.setattr(
        derivation, "preserve_numeric_superscripts", mutating_overlay
    )
    with pytest.raises(RuntimeError, match="mutated its source"):
        derivation.derive_numeric_superscripts(_raw(), Path("manual.pdf"))
