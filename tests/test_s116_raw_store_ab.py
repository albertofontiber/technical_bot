from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.s116_raw_store_ab import _leaf_heading_in_content, _verified_receipt, build_payload
from src.reingest.chunk import Chunk


def test_leaf_heading_requires_exact_normalized_heading() -> None:
    assert _leaf_heading_in_content("## 8.3 Sustitución del SRG\nBody", "8.3 Sustitucion del SRG")
    assert not _leaf_heading_in_content("## 8 Mantenimiento\nBody", "8.3 Sustitucion del SRG")


def test_verified_receipt_rejects_missing_and_tampered_hash() -> None:
    chunk = Chunk("Body", "8.3 Sustitución", "8 > 8.3 Sustitución", 2, 0)
    assert not _verified_receipt(chunk)
    heading = "## 8.3 Sustitución"
    chunk.section_anchor = {  # type: ignore[attr-defined]
        "heading_text": heading,
        "heading_sha256": hashlib.sha256(heading.encode("utf-8")).hexdigest(),
        "source_page": 1,
        "title": "8.3 Sustitución",
        "level": 2,
    }
    assert _verified_receipt(chunk)
    chunk.section_anchor["heading_sha256"] = "0" * 64  # type: ignore[attr-defined]
    assert not _verified_receipt(chunk)


def test_payload_does_not_persist_absolute_store_path(tmp_path: Path) -> None:
    store = tmp_path / "paid-store"
    store.mkdir()
    record = {
        "sha256": "a" * 64,
        "source_path": "Manuales_Otros/example.pdf",
        "result": {"pages": [{"page": 1, "md": "# Product\n\n## 1.1 Setup\n\nBody"}]},
    }
    (store / "a.json").write_text(json.dumps(record), encoding="utf-8")
    payload = build_payload(store, "baseline")
    encoded = json.dumps(payload)
    assert str(tmp_path) not in encoded
    assert payload["source"]["store_slug"] == "paid-store"
    assert payload["summary"]["records_processed"] == 1
