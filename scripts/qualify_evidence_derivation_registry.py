#!/usr/bin/env python3
"""Qualify v5 on a fresh read-only snapshot and a frozen answer replay."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s161_table_preamble_answer_probe import score_answer
from scripts.s172_superscript_answer_cascade import supports_exact_exponent
from src.ingestion.supabase_client import SupabaseHTTP
from src.rag.evidence_derivation import (
    apply_evidence_derivations_with_trace,
    load_registry,
    validate_registry,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot"
)
DEFAULT_ENV = DEFAULT_PROJECT / ".env"
REGISTRY = ROOT / "config/extraction_derivations_v5.json"
CONTEXTS = ROOT / "evals/s113_full_contexts_freeze_v1.json"
ANSWER = ROOT / "evals/s161_table_preamble_answer_probe_receipts_v1.json"
PREAMBLE = ROOT / "evals/s160_target_table_preamble_probe_v3.json"
OUT = ROOT / "evals/evidence_derivation_registry_gate_v1.json"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _client(env_file: Path) -> SupabaseHTTP:
    values = dotenv_values(env_file)
    url = str(values.get("SUPABASE_URL") or "")
    key = str(values.get("SUPABASE_SERVICE_KEY") or "")
    if not url or not key:
        raise RuntimeError("Supabase read credentials are missing")
    return SupabaseHTTP(url=url, service_key=key)


def _fresh_snapshot(
    registry: dict[str, Any], env_file: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    client = _client(env_file)
    rows: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    try:
        for expected in registry["document_snapshots"]:
            extraction = expected["extraction_sha256"]
            document_rows = client.fetch_rows(
                "chunks_v2",
                select="id,extraction_sha256,chunk_index,content,source_file,page_number",
                filters={"extraction_sha256": f"eq.{extraction}"},
                limit=2000,
            )
            core = [
                {
                    "id": row["id"],
                    "chunk_index": row["chunk_index"],
                    "content_sha256": _sha(
                        str(row.get("content") or "").encode("utf-8")
                    ),
                }
                for row in sorted(
                    document_rows,
                    key=lambda item: (item["chunk_index"], item["id"]),
                )
            ]
            snapshots.append(
                {
                    "extraction_sha256": extraction,
                    "rows": len(document_rows),
                    "snapshot_sha256": _sha(_canonical(core)),
                    "expected_snapshot_sha256": expected["live_snapshot_sha256"],
                }
            )
            rows.extend(document_rows)
    finally:
        client.client.close()
    return rows, snapshots


def _answer_replay(registry: dict[str, Any]) -> dict[str, Any]:
    entry_by_id = {entry["chunk_id"]: entry for entry in registry["entries"]}
    freeze = json.loads(CONTEXTS.read_text(encoding="utf-8"))
    row = next(item for item in freeze["rows"] if item["qid"] == "cat007")
    contexts: list[dict[str, Any]] = []
    for item in row["context"]:
        updated = dict(item)
        entry = entry_by_id.get(str(item["id"]))
        if entry is not None:
            updated["extraction_sha256"] = entry["extraction_sha256"]
            updated["chunk_index"] = entry["chunk_index"]
        contexts.append(updated)
    preamble = json.loads(PREAMBLE.read_text(encoding="utf-8"))
    contexts.append(
        {"id": preamble["predecessor_id"], "content": preamble["preamble"]}
    )
    derived, trace = apply_evidence_derivations_with_trace(
        contexts, enabled=True, registry_path=REGISTRY
    )
    answer = json.loads(ANSWER.read_text(encoding="utf-8"))["answer"]
    scoring = score_answer(
        answer,
        [str(item["id"]) for item in derived],
        [str(item["content"]) for item in derived],
    )
    life_claim = re.search(
        r"Vida\s+\S*til[^\n]{0,100}(?:10\u2075|10\s*\^\s*5)[^\n]{0,100}",
        answer,
        re.IGNORECASE,
    )
    citations = (
        sorted({int(value) for value in re.findall(r"\[F(\d+)\]", life_claim.group(0))})
        if life_claim
        else []
    )
    exact_supports = sum(
        supports_exact_exponent(derived[index - 1]["content"])
        for index in citations
    )
    return {
        "source_contract_claims": scoring["recovered_covered"],
        "protected_claims": scoring["protected_covered"],
        "invalid_citations": scoring["invalid_citations"],
        "life_citations": citations,
        "life_exact_supports": exact_supports,
        "modified_rows": trace["modified_rows"],
        "applied_derivations": len(trace["applied_derivations"]),
        "abstentions": trace["abstentions"],
    }


def build(env_file: Path) -> dict[str, Any]:
    registry = load_registry(str(REGISTRY))
    live_rows, snapshots = _fresh_snapshot(registry, env_file)
    before = copy.deepcopy(live_rows)
    derived, trace = apply_evidence_derivations_with_trace(
        live_rows, enabled=True, registry_path=REGISTRY
    )
    second, second_trace = apply_evidence_derivations_with_trace(
        derived, enabled=True, registry_path=REGISTRY
    )
    entry_by_id = {entry["chunk_id"]: entry for entry in registry["entries"]}
    exact_rows = all(
        new["content"]
        == entry_by_id.get(str(old["id"]), {}).get("derived_content", old["content"])
        for old, new in zip(live_rows, derived)
    )
    answer = _answer_replay(registry)
    applied = {
        row["chunk_derivation_sha256"] for row in trace["applied_derivations"]
    }
    expected = {
        row["chunk_derivation_sha256"] for row in registry["entries"]
    }
    checks = {
        "registry_valid": not validate_registry(registry),
        "fresh_snapshot_rows_710": len(live_rows) == 710,
        "fresh_snapshots_no_drift": all(
            row["snapshot_sha256"] == row["expected_snapshot_sha256"]
            for row in snapshots
        ),
        "all_13_derivations_applied_once": (
            len(trace["applied_derivations"]) == len(expected) == 13
            and applied == expected
        ),
        "every_live_row_exact": exact_rows,
        "input_rows_immutable": live_rows == before,
        "runtime_abstentions_zero": not trace["abstentions"],
        "second_pass_inert": (
            second_trace["modified_rows"] == 0
            and [row["content"] for row in second]
            == [row["content"] for row in derived]
        ),
        "combined_source_contract_5": answer["source_contract_claims"] == 5,
        "combined_protected_4": answer["protected_claims"] == 4,
        "combined_life_two_exact_supports": (
            answer["life_citations"] == [1, 4] and answer["life_exact_supports"] == 2
        ),
        "combined_invalid_citations_zero": not answer["invalid_citations"],
        "combined_runtime_abstentions_zero": not answer["abstentions"],
    }
    body = {
        "instrument": "evidence_derivation_registry_gate_v1",
        "status": "LOCAL_GO_LIVE_READ_DEFAULT_OFF" if all(checks.values()) else "LOCAL_NO_GO",
        "checks": checks,
        "registry": {
            "path": "config/extraction_derivations_v5.json",
            "artifact_sha256": registry["artifact_sha256"],
            "entries": registry["entry_count"],
            "bound_source_receipts": registry["bound_source_pdf_receipt_count"],
            "absent_source_receipts": registry["absent_source_pdf_receipt_count"],
        },
        "fresh_read": {
            "documents": len(snapshots),
            "rows": len(live_rows),
            "snapshots": snapshots,
            "database_writes": 0,
        },
        "runtime_replay": {
            "modified_rows": trace["modified_rows"],
            "applied_derivations": len(trace["applied_derivations"]),
            "abstentions": trace["abstentions"],
            "second_pass_modified_rows": second_trace["modified_rows"],
        },
        "answer_replay": answer,
        "decision": {
            "local_candidate": "GO" if all(checks.values()) else "NO_GO",
            "release_flag_default": "off",
            "retrieval_or_rerank_changed": False,
            "chunks_v2_mutated": False,
            "facts_added": 0,
            "production_or_deployment": False,
        },
        "cost": {"model_calls": 0, "network_reads": 11, "database_rows_read": len(live_rows), "database_writes": 0, "usd": 0},
    }
    return {**body, "result_sha256": _sha(_canonical(body))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = build(args.env_file)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], **result["checks"]}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "LOCAL_GO_LIVE_READ_DEFAULT_OFF" else 1


if __name__ == "__main__":
    raise SystemExit(main())
