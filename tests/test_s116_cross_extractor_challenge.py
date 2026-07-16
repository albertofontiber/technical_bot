from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import s116_cross_extractor_challenge as challenge


def test_store_manifest_is_deterministic_and_path_independent(tmp_path: Path) -> None:
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text('{"x": 1}', encoding="utf-8")
    files = [first, second]
    assert challenge._store_manifest(files) == challenge._store_manifest(files)
    expected = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        expected.update(f"{path.name}\0{len(raw)}\0{hashlib.sha256(raw).hexdigest()}\n".encode())
    assert challenge._store_manifest(files) == expected.hexdigest()


def test_run_arm_preserves_document_stream(tmp_path: Path) -> None:
    record = {"result": {"pages": [{"page": 1, "md": "# Setup\n\n" + "Body" * 10}]}}
    path = tmp_path / "a.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    module = challenge._load_chunker(
        challenge.ROOT / "src/reingest/chunk.py", "s116_test_treatment_chunk"
    )
    result = challenge._run_arm([path], module, True)
    assert result["processed_files"] == 1
    assert result["chunk_lineage_state_failures"] == 0
    assert result["titled_chunks"] == result["resolved_full_lineages"]
