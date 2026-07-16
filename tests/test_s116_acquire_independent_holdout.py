from __future__ import annotations

from pathlib import Path

import fitz

from scripts.s116_acquire_independent_holdout import evaluate, pdf_receipt


def test_pdf_receipt_opens_real_pdf(tmp_path: Path) -> None:
    path = tmp_path / "sample.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    receipt = pdf_receipt(path)
    assert receipt["pages"] == 1
    assert len(receipt["sha256"]) == 64


def test_gate_rejects_overlap_and_requires_strata() -> None:
    rows = [
        {
            "status": "ok",
            "sha256": f"{index:064x}",
            "pages": 40 if index == 0 else (2 if index in {1, 2} else 10),
            "size_bytes": 100,
            "manufacturer": f"m{index % 4}",
        }
        for index in range(12)
    ]
    assert evaluate(rows, 12, set())["gate"] == "GO"
    assert evaluate(rows, 12, {rows[0]["sha256"]})["gate"] == "NO_GO"
