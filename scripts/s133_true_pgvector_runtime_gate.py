#!/usr/bin/env python3
"""Run the frozen S131 gates on disposable PostgreSQL with real pgvector."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "evals/s133_true_pgvector_runtime_gate_v1.json"
ROLLBACK = ROOT / "scripts/s131_m0b_rollback.sql"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _configure_s131():
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import s131_m0b_disposable_gate as positive

    psql = os.getenv("S133_PSQL") or shutil.which("psql")
    if not psql:
        raise RuntimeError("psql is not available")
    positive.PSQL = Path(psql)
    positive.HOST = os.getenv("S133_PGHOST", "127.0.0.1")
    positive.PORT = os.getenv("S133_PGPORT", "55432")
    positive.DATABASE = os.getenv("S133_PGDATABASE", "s131_m0b")
    positive.USER = os.getenv("S133_PGUSER", "postgres")

    # The negative harness imports the frozen positive module by this exact name.
    sys.modules["s131_m0b_disposable_gate"] = positive
    import s131_m0b_negative_gate as negative

    return positive, negative


def _validate_distances(payload: dict[str, Any], expected_version: str) -> None:
    if payload.get("extension_version") != expected_version:
        raise RuntimeError(f"unexpected pgvector version: {payload!r}")
    expected = {"same": 0.0, "orthogonal": 1.0, "opposite": 2.0}
    for name, value in expected.items():
        if abs(float(payload.get(name, -999)) - value) > 1e-6:
            raise RuntimeError(f"pgvector cosine distance drift for {name}: {payload!r}")


def _plan_nodes(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [plan]
    for child in plan.get("Plans", []):
        rows.extend(_plan_nodes(child))
    return rows


def _validate_hnsw_plan(payload: list[dict[str, Any]]) -> dict[str, Any]:
    if not payload or "Plan" not in payload[0]:
        raise RuntimeError(f"invalid EXPLAIN JSON: {payload!r}")
    nodes = _plan_nodes(payload[0]["Plan"])
    index_nodes = [row for row in nodes if row.get("Index Name") == "s133_vectors_hnsw"]
    if not index_nodes or not any("Index Scan" in row.get("Node Type", "") for row in index_nodes):
        raise RuntimeError(f"real HNSW index was not used: {nodes!r}")
    return {
        "status": "PASS",
        "index_name": "s133_vectors_hnsw",
        "node_type": index_nodes[0]["Node Type"],
    }


def _real_pgvector_probe(positive) -> dict[str, Any]:
    expected_version = os.getenv("S133_EXPECTED_PGVECTOR", "0.8.0")
    distances = json.loads(
        positive.psql(
            "SELECT jsonb_build_object("
            "'extension_version', (SELECT extversion FROM pg_catalog.pg_extension WHERE extname='vector'), "
            "'same', ('[1,0,0]'::extensions.vector OPERATOR(extensions.<=>) '[1,0,0]'::extensions.vector), "
            "'orthogonal', ('[1,0,0]'::extensions.vector OPERATOR(extensions.<=>) '[0,1,0]'::extensions.vector), "
            "'opposite', ('[1,0,0]'::extensions.vector OPERATOR(extensions.<=>) '[-1,0,0]'::extensions.vector));"
        )
    )
    _validate_distances(distances, expected_version)

    explain = positive.psql(
        "BEGIN; "
        "CREATE TEMP TABLE s133_vectors (id integer PRIMARY KEY, embedding extensions.vector(3)); "
        "INSERT INTO s133_vectors "
        "SELECT g, ARRAY[1.0, ((g % 97) + 1) / 100.0, ((g % 53) + 1) / 100.0]::real[]::extensions.vector "
        "FROM pg_catalog.generate_series(1, 2048) AS g; "
        "CREATE INDEX s133_vectors_hnsw ON s133_vectors USING hnsw "
        "(embedding extensions.vector_cosine_ops); "
        "ANALYZE s133_vectors; SET LOCAL enable_seqscan=off; "
        "EXPLAIN (FORMAT JSON, COSTS OFF) "
        "SELECT id FROM s133_vectors "
        "ORDER BY embedding OPERATOR(extensions.<=>) '[1,0,0]'::extensions.vector LIMIT 5; "
        "ROLLBACK;"
    )
    # psql emits command tags before the final JSON and ROLLBACK after it. Extract the
    # single JSON array rather than relying on client-specific command-tag settings.
    start = explain.find("[")
    end = explain.rfind("]")
    if start < 0 or end < start:
        raise RuntimeError(f"missing EXPLAIN JSON: {explain!r}")
    hnsw = _validate_hnsw_plan(json.loads(explain[start : end + 1]))
    return {
        "status": "PASS",
        "extension_version": expected_version,
        "cosine_distance_semantics": {"status": "PASS", **distances},
        "hnsw_index_behavior": hnsw,
        "semantic_retrieval_quality": "NOT_MEASURED_SYNTHETIC_CONTENT",
    }


def _negative_gate(negative, positive) -> dict[str, Any]:
    baseline_state = positive.psql(
        "SELECT state FROM public.chunk_materializations_v1 "
        f"WHERE id='{positive.MATERIALIZATION_ID}'::uuid;"
    )
    if baseline_state != "validated":
        raise positive.GateFailure("validated baseline is required before negative M0b tests")
    payload = negative.candidate_payload()
    path = negative.candidate_bindings_path(payload)
    return {
        "instrument": "s131_m0b_negative_gate_v1",
        "static_rejections": negative.exercise_static_rejections(payload),
        "validator_rejections": negative.exercise_validator_rejections(path, payload),
        "transition_race": negative.exercise_transition_race(path),
        "models": 0,
        "retrieval_quality": "NOT_MEASURED_SYNTHETIC_CONTENT",
    }


def main() -> int:
    report_path = Path(os.getenv("S133_REPORT_PATH", REPORT))
    positive, negative = _configure_s131()
    report: dict[str, Any] = {
        "instrument": "s133_true_pgvector_runtime_gate_v1",
        "status": "RUNNING",
        "runtime": {
            "kind": "disposable_github_actions_service",
            "production_data": False,
            "railway": False,
        },
        "authority": {
            "positive_harness_sha256": _sha256(ROOT / "scripts/s131_m0b_disposable_gate.py"),
            "negative_harness_sha256": _sha256(ROOT / "scripts/s131_m0b_negative_gate.py"),
            "s117_migration_sha256": _sha256(
                ROOT
                / "supabase/migration_proposals/20260714102428_chunks_v3_provenance_shadow.sql"
            ),
            "s131_migration_sha256": _sha256(
                ROOT
                / "supabase/migration_proposals/20260716120000_chunks_v3_shadow_binding_v2.sql"
            ),
        },
        "cost": {"model_calls": 0, "embedding_calls": 0, "production_database_writes": 0},
    }
    failure: BaseException | None = None
    try:
        baseline_load = positive.load_baseline()
        verification = positive.verify_runtime(
            expected_server_version_prefix=os.getenv("S133_EXPECTED_POSTGRES", "17.6"),
            expected_vector_extension_version=os.getenv(
                "S133_EXPECTED_PGVECTOR", "0.8.0"
            ),
        )
        historical_vector_note = verification.pop("pgvector_semantics")
        verification["pgvector_semantics"] = {
            "status": "DELEGATED_TO_S133_REAL_PROBE",
            "historical_s131_default": historical_vector_note,
        }
        report["positive"] = {
            "load": baseline_load,
            "verification": verification,
        }
        report["negative"] = _negative_gate(negative, positive)
        report["true_pgvector"] = _real_pgvector_probe(positive)
        report["status"] = "GO_TRUE_PGVECTOR_RUNTIME_CONTRACT"
    except BaseException as error:  # persist evidence before propagating CI failure
        failure = error
        report["status"] = "NO_GO"
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        try:
            positive.psql(ROLLBACK.read_text(encoding="utf-8"))
            report["rollback"] = {"status": "PASS", "residual_shadow_objects": 0}
        except BaseException as rollback_error:
            report["rollback"] = {
                "status": "FAIL",
                "error": f"{type(rollback_error).__name__}: {rollback_error}",
            }
            if failure is None:
                failure = rollback_error
                report["status"] = "NO_GO"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if failure is not None:
        raise failure
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
