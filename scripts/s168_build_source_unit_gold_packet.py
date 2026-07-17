#!/usr/bin/env python3
"""Build a new document-independent packet for the S168 transport successor."""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s146_build_fresh_source_packet import PRIOR_CHUNKS, SNAPSHOT, _excluded_documents, file_sha
from scripts.s165_answer_archetype_ledger import stable_sha
from scripts.s167_build_independent_ledger_source import build_from_rows
from scripts.s167_build_independent_ledger_source_support import collect_uuid_strings


ROOT = Path(__file__).resolve().parents[1]
PACKETS = (
    ROOT / "evals/s146_fresh_source_packet_v1.json",
    ROOT / "evals/s147_fresh_source_packet_v1.json",
    ROOT / "evals/s167_independent_ledger_source_packet_v1.json",
)
S114 = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
TARGET_FILES = (
    ROOT / "evals/s141_source_bound_technical_obligations_v1.json",
    ROOT / "evals/s149_target_evidence_selector_probe_v1.json",
    ROOT / "evals/s150_target_coverage_verifier_probe_v1.json",
    ROOT / "evals/s158_target_table_preamble_probe_v1.json",
    ROOT / "evals/s159_target_table_preamble_probe_v2.json",
    ROOT / "evals/s160_target_table_preamble_probe_v3.json",
    ROOT / "evals/s163_synthesis_residual_audit_v1.json",
)
DEFAULT_OUT = ROOT / "evals/s168_source_unit_gold_packet_v1.json"
SEED = "s168-source-unit-id-gold-v1"


def build_packet() -> dict[str, Any]:
    prior_packets = [json.loads(path.read_text(encoding="utf-8")) for path in PACKETS]
    s114 = json.loads(S114.read_text(encoding="utf-8"))
    chosen_ids = {row["chunk_id"] for row in s114["chosen"]}
    prior_documents = (
        _excluded_documents()
        | {s114["source_rows"][chunk_id]["document_id"] for chunk_id in chosen_ids}
        | {
            row["document_id"]
            for packet in prior_packets
            for row in packet["items"]
        }
    )
    development_pairs = {
        (row["manufacturer"].casefold(), row["product_model"].casefold())
        for packet in prior_packets
        for row in packet["items"]
    }
    target_ids: set[str] = set()
    for path in TARGET_FILES:
        target_ids.update(
            collect_uuid_strings(json.loads(path.read_text(encoding="utf-8")))
        )
    active: set[str] = set()
    rows: list[dict[str, Any]] = []
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("kind") == "document" and row.get("status") == "active":
                active.add(row["id"])
            elif row.get("kind") == "chunk":
                rows.append(row)
    result = build_from_rows(
        rows,
        active,
        prior_documents,
        target_ids,
        development_pairs,
        seed=SEED,
        instrument="s168_source_unit_gold_packet_v1",
        item_prefix="s168_src",
    )
    result.pop("packet_sha256", None)
    result["dependencies"] = {
        "snapshot_sha256": file_sha(SNAPSHOT),
        "prior_chunks_sha256": file_sha(PRIOR_CHUNKS),
        "s114_sha256": file_sha(S114),
        "prior_packets": {str(path.relative_to(ROOT)): file_sha(path) for path in PACKETS},
        "target_files": {str(path.relative_to(ROOT)): file_sha(path) for path in TARGET_FILES},
    }
    return {**result, "packet_sha256": stable_sha(result)}


def main() -> int:
    result = build_packet()
    DEFAULT_OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], **result["selection"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
