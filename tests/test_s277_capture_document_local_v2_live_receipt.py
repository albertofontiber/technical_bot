from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/s277_capture_document_local_v2_live_receipt.py"


def test_capture_script_is_read_only_and_redacts_connection_material() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "set_session(readonly=True" in source
    assert "connection.rollback()" in source
    assert "database_url" not in source[source.index('receipt = {') :]
    forbidden_sql = ("INSERT ", "UPDATE ", "DELETE ", "MERGE ", "TRUNCATE ")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literal = node.value.upper()
            assert not any(token in literal for token in forbidden_sql)


def test_capture_seals_exact_v2_boundary_and_four_migrations() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    for value in (
        "document_local_snapshot_v2(jsonb,text,integer,integer)",
        "20260721210847",
        "20260721220110",
        "20260722013000",
        "20260722014500",
        "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429",
        "e98e05ff-ee1d-5341-869a-65768855dae9",
        "494e71be-873b-48c1-adb3-a21a122da111",
        "definition_sha256_lf",
        "p1_lineage_column_acl_minimal",
    ):
        assert value in source
