#!/usr/bin/env python3
"""Build the zero-provider-call S210 frozen execution manifest."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s141_source_bound_technical_obligations import answer_map
from src.rag.query_evidence_compiler import stable_sha


TARGET_FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
RESIDUAL = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
INDEPENDENT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
INDEPENDENT_BASELINE = ROOT / "evals/s173_baseline_answer_receipts_v1.json"
INDEPENDENT_GOLD = ROOT / "evals/s171_s147_source_unit_gold_v1.json"
PREREG = ROOT / "evals/s210_query_evidence_compiler_prereg_v1.yaml"
OUT = ROOT / "evals/s210_query_evidence_compiler_preflight_v1.json"

TARGETS = ("cat018", "hp002", "hp011", "hp017")
REPLICATES = (1, 2)
EXPECTED_TARGET_CHUNKS = 51
EXPECTED_INDEPENDENT_ITEMS = 14

IMPLEMENTATION_FILES = (
    "src/rag/query_evidence_compiler.py",
    "src/rag/query_evidence_obligations.py",
    "scripts/s210_build_query_evidence_compiler_preflight.py",
    "scripts/s210_run_query_evidence_compiler.py",
    "scripts/s210_score_query_evidence_compiler.py",
    "evals/s210_query_evidence_compiler_design_v1.md",
    "evals/s210_query_evidence_compiler_prereg_v1.yaml",
)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_chunk(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["chunk_id"],
        "content": item["excerpt"],
        "context": "",
        "product_model": item["product_model"],
        "manufacturer": item["manufacturer"],
        "source_file": item["source_file"],
        "page_number": item["page_number"],
        "section_title": item["section_title"],
        "content_type": item["stratum"],
        "document_id": item["document_id"],
        "similarity": 1.0,
        "_channel": "S210_FROZEN_INDEPENDENT_GUARDRAIL",
    }


def build_rows() -> list[dict[str, Any]]:
    freeze = json.loads(TARGET_FREEZE.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in freeze["rows"]}
    target_answers = answer_map()
    rows: list[dict[str, Any]] = []
    for qid in TARGETS:
        source = frozen[qid]
        rows.append(
            {
                "qid": qid,
                "role": "target",
                "question": source["question"],
                "context": source["context"],
                "context_sha256": stable_sha(source["context"]),
                "context_rows": len(source["context"]),
                "baseline_answer": target_answers[qid],
                "baseline_answer_sha256": hashlib.sha256(
                    target_answers[qid].encode("utf-8")
                ).hexdigest(),
            }
        )

    cohort = json.loads(INDEPENDENT.read_text(encoding="utf-8"))["items"]
    baseline = {
        str(row["item_id"]): row
        for row in json.loads(INDEPENDENT_BASELINE.read_text(encoding="utf-8"))[
            "receipts"
        ]
    }
    if len(cohort) != EXPECTED_INDEPENDENT_ITEMS or set(baseline) != {
        str(row["item_id"]) for row in cohort
    }:
        raise RuntimeError("S210 independent guardrail population drift")
    for item in cohort:
        item_id = str(item["item_id"])
        context = [_source_chunk(item)]
        base_answer = str(baseline[item_id]["answer"])
        rows.append(
            {
                "qid": item_id,
                "role": "independent_guardrail",
                "stratum": item["stratum"],
                "manufacturer": item["manufacturer"],
                "question": item["question"],
                "context": context,
                "context_sha256": stable_sha(context),
                "context_rows": 1,
                "baseline_answer": base_answer,
                "baseline_answer_sha256": hashlib.sha256(
                    base_answer.encode("utf-8")
                ).hexdigest(),
            }
        )
    return rows


def main() -> int:
    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S210 preregistration is not frozen")
    for spec in prereg["frozen_inputs"].values():
        if file_sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S210 frozen input drift: {spec['path']}")

    rows = build_rows()
    target_chunks = sum(
        len(row["context"]) for row in rows if row["role"] == "target"
    )
    independent_items = sum(row["role"] == "independent_guardrail" for row in rows)
    extraction_calls = sum(len(row["context"]) for row in rows) * len(REPLICATES)
    planner_calls = len(rows) * len(REPLICATES)
    verifier_calls = planner_calls
    implementation = [
        {"path": path, "sha256": file_sha(ROOT / path)}
        for path in IMPLEMENTATION_FILES
    ]
    inputs = [
        {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": file_sha(path),
        }
        for path in (
            TARGET_FREEZE,
            RESIDUAL,
            INDEPENDENT,
            INDEPENDENT_BASELINE,
            INDEPENDENT_GOLD,
            PREREG,
        )
    ]
    checks = {
        "four_targets": sum(row["role"] == "target" for row in rows) == 4,
        "target_chunks_51": target_chunks == EXPECTED_TARGET_CHUNKS,
        "independent_guardrails_14": independent_items == EXPECTED_INDEPENDENT_ITEMS,
        "target_baselines_match_residual_answer_hashes": all(
            {
                residual_row["answer_sha256"]
                for residual_row in json.loads(RESIDUAL.read_text(encoding="utf-8"))[
                    "rows"
                ]
                if residual_row["qid"] == row["qid"]
            }
            == {row["baseline_answer_sha256"]}
            for row in rows
            if row["role"] == "target"
        ),
        "two_full_replicates": list(REPLICATES) == [1, 2],
        "exact_call_geometry": (extraction_calls, planner_calls, verifier_calls)
        == (130, 36, 36),
        "all_files_hashed": all(item["sha256"] for item in (*implementation, *inputs)),
    }
    body = {
        "schema": "s210_query_evidence_compiler_preflight_v1",
        "status": "GO_ZERO_CALL_PREFLIGHT" if all(checks.values()) else "NO_GO",
        "main_sha": "82e42a6a6df4733588e33699e0db999e7b441357",
        "inputs": inputs,
        "implementation": implementation,
        "models": prereg["models"],
        "replicates": list(REPLICATES),
        "call_geometry": {
            "extractor_calls": extraction_calls,
            "planner_calls": planner_calls,
            "verifier_calls": verifier_calls,
            "total_paid_calls_max": extraction_calls + planner_calls + verifier_calls,
            "provider_retries": 0,
        },
        "rows": rows,
        "checks": checks,
        "invariants": {
            "target_fact_names_visible_to_models": False,
            "gold_visible_before_all_responses_sealed": False,
            "baseline_visible_to_models": False,
            "retrieval_calls": 0,
            "database_calls": 0,
            "runtime_integration": False,
            "chunks_v3_status": "FINAL_NO_GO_CHUNKS_V3_WHOLESALE",
            "railway_merge_gate": False,
        },
        "cost": {"model_calls": 0, "network_calls": 0, "usd": 0},
    }
    payload = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": payload["status"], "checks": checks}, ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
