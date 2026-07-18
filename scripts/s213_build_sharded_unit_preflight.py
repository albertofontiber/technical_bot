#!/usr/bin/env python3
"""Build the zero-call S213 sharded-unit execution manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s141_source_bound_technical_obligations import (  # noqa: E402
    TARGET_KINDS,
    plan_for,
)
from scripts.s210_build_query_evidence_compiler_preflight import build_rows  # noqa: E402
from src.rag.query_evidence_compiler import portable_file_sha, stable_sha  # noqa: E402
from src.rag.sharded_unit_selector import (  # noqa: E402
    build_sharded_candidates,
    selector_payload,
    verifier_payload,
)


PREREG = ROOT / "evals/s213_sharded_unit_selector_prereg_v1.yaml"
OUT = ROOT / "evals/s213_sharded_unit_selector_preflight_v1.json"
RESIDUAL = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
REPLICATES = (1, 2)
EXPECTED_ROWS = 18
EXPECTED_CHUNKS = 65
EXPECTED_RESIDUALS = 12
MAX_PROMPT_BYTES = 50_000

IMPLEMENTATION_FILES = (
    "src/rag/evidence_units.py",
    "src/rag/evidence_units_v2.py",
    "src/rag/query_evidence_obligations.py",
    "src/rag/query_evidence_compiler.py",
    "src/rag/sharded_unit_selector.py",
    "scripts/s210_build_query_evidence_compiler_preflight.py",
    "scripts/s210_score_query_evidence_compiler.py",
    "scripts/s213_build_sharded_unit_preflight.py",
    "scripts/s213_run_sharded_unit_selector.py",
    "scripts/s213_score_sharded_unit_selector.py",
    "tests/test_sharded_unit_selector.py",
    "evals/s213_sharded_unit_selector_design_v1.md",
    "evals/s213_sharded_unit_selector_prereg_v1.yaml",
)


def file_sha(path: Path) -> str:
    return portable_file_sha(path)


def _overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return max(left[0], right[0]) < min(left[1], right[1])


def _coverage(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    residual = json.loads(RESIDUAL.read_text(encoding="utf-8"))
    residual_keys = {
        (str(row["qid"]), str(row["kind"]))
        for row in residual["rows"]
        if not row["covered"]
    }
    output: list[dict[str, Any]] = []
    unit_covered = 0
    for row in rows:
        if row["role"] != "target":
            continue
        shards = build_sharded_candidates(row["question"], row["context"])
        by_fragment = {index: shard for index, shard in enumerate(shards, 1)}
        for obligation in plan_for(row):
            key = (row["qid"], obligation.kind)
            if key not in residual_keys or obligation.kind not in TARGET_KINDS[row["qid"]]:
                continue
            candidates = by_fragment[obligation.fragment_number]
            source_span = (obligation.source_start, obligation.source_end)
            covered = any(
                any(_overlaps(span, source_span) for span in candidate.source_spans)
                for candidate in candidates
                if candidate.origin == "deterministic_header_aware_unit"
            )
            unit_covered += int(covered)
            output.append(
                {
                    "qid": row["qid"],
                    "kind": obligation.kind,
                    "deterministic_unit_span": covered,
                }
            )
    return output, unit_covered


def main() -> int:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S213 preregistration is not frozen")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S213 frozen input drift: {spec['path']}")

    rows = build_rows()
    shard_geometry: list[dict[str, Any]] = []
    max_selector_bytes = max_verifier_bytes = total_units = 0
    for row in rows:
        shards = build_sharded_candidates(row["question"], row["context"])
        for fragment_number, shard in enumerate(shards, 1):
            selector_bytes = len(selector_payload(row["question"], shard).encode("utf-8"))
            verifier_bytes = len(
                verifier_payload(row["question"], shard, ()).encode("utf-8")
            )
            max_selector_bytes = max(max_selector_bytes, selector_bytes)
            max_verifier_bytes = max(max_verifier_bytes, verifier_bytes)
            total_units += len(shard)
            shard_geometry.append(
                {
                    "qid": row["qid"],
                    "fragment_number": fragment_number,
                    "units": len(shard),
                    "selector_prompt_bytes": selector_bytes,
                    "verifier_min_prompt_bytes": verifier_bytes,
                }
            )

    coverage, residual_covered = _coverage(rows)
    chunks = sum(len(row["context"]) for row in rows)
    selector_calls = chunks * len(REPLICATES)
    verifier_calls = selector_calls
    implementation = [
        {"path": path, "sha256": file_sha(ROOT / path)}
        for path in IMPLEMENTATION_FILES
    ]
    checks = {
        "rows_18": len(rows) == EXPECTED_ROWS,
        "chunks_65": chunks == EXPECTED_CHUNKS,
        "two_full_replicates": list(REPLICATES) == [1, 2],
        "exact_call_geometry_260": selector_calls + verifier_calls == 260,
        "deterministic_unit_source_coverage_12_of_12": (
            len(coverage) == EXPECTED_RESIDUALS
            and residual_covered == EXPECTED_RESIDUALS
        ),
        "all_prompts_below_50k_bytes": (
            max(max_selector_bytes, max_verifier_bytes) < MAX_PROMPT_BYTES
        ),
        "all_files_hashed": all(item["sha256"] for item in implementation),
    }
    body = {
        "schema": "s213_sharded_unit_selector_preflight_v1",
        "status": "GO_ZERO_CALL_PREFLIGHT" if all(checks.values()) else "NO_GO",
        "main_sha": prereg["main_sha"],
        "implementation": implementation,
        "models": prereg["models"],
        "replicates": list(REPLICATES),
        "call_geometry": {
            "selector_calls": selector_calls,
            "verifier_calls": verifier_calls,
            "total_paid_calls": selector_calls + verifier_calls,
            "provider_retries": 0,
        },
        "source_geometry": {
            "rows": len(rows),
            "chunks": chunks,
            "deterministic_candidates": total_units,
            "max_selector_prompt_bytes": max_selector_bytes,
            "max_verifier_min_prompt_bytes": max_verifier_bytes,
            "hard_prompt_cap_bytes": MAX_PROMPT_BYTES,
            "shards": shard_geometry,
        },
        "upstream_residual_coverage": coverage,
        "rows": rows,
        "checks": checks,
        "invariants": {
            "target_fact_names_visible_to_models": False,
            "gold_visible_before_all_responses_sealed": False,
            "baseline_visible_to_models": False,
            "model_authored_evidence": False,
            "parallel_fallback_lane": False,
            "retrieval_calls": 0,
            "database_calls": 0,
            "runtime_integration": False,
            "production_default": "off",
            "chunks_v2": "ACTIVE_READ_ONLY",
            "chunks_v3": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
        "cost": {"model_calls": 0, "network_calls": 0, "usd": 0},
    }
    payload = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": payload["status"], "checks": checks}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
