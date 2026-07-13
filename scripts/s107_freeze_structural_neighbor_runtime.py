#!/usr/bin/env python3
"""Freeze the deployable default-off structural-neighbor shadow candidate."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals/s107_structural_neighbor_runtime_freeze_v2.json"
PREREG = ROOT / "evals/s107_structural_neighbor_shadow_prereg_v1.yaml"
PILOT = ROOT / "evals/s107_bounded_synthesis_pilot_v1.json"
FILES = (
    ".env.example",
    "config/evidence_coverage_facets_v2.yaml",
    "config/evidence_coverage_facets_v4.yaml",
    "config/structural_neighbor_coverage_v1.yaml",
    "config/retrieval_facets_v3.yaml",
    "config/structured_numeric_claims_v2.yaml",
    "src/config.py",
    "src/bot/telegram_bot.py",
    "src/rag/evidence_coverage.py",
    "src/rag/evidence_window.py",
    "src/rag/structural_neighbor_coverage.py",
    "src/rag/structural_neighbor_shadow.py",
    "src/rag/query_facets.py",
    "src/rag/structured_claims.py",
    "src/rag/toc_detection.py",
    "scripts/s107_freeze_structural_neighbor_runtime.py",
    "scripts/s107_structural_neighbor_coverage_probe.py",
    "scripts/s107_shadow_adjudication_join.py",
    "scripts/s107_shadow_adjudication_panel.py",
    "tests/test_structural_neighbor_coverage.py",
    "tests/test_structural_neighbor_shadow.py",
    "tests/test_structural_neighbor_handler_hook.py",
    "tests/test_structural_neighbor_adjudication.py",
    "tests/test_query_facets.py",
    "tests/test_structured_claims.py",
    "tests/test_evidence_coverage.py",
    "tests/test_evidence_window.py",
    "tests/test_generator_coverage_obligations.py",
    "tests/test_config_governed_chunks.py",
    "evals/s107_structural_neighbor_shadow_prereg_v1.yaml",
    "evals/s107_structural_neighbor_coverage_probe_v1.json",
    "evals/s107_document_revision_reconciliation_apply_v1.json",
    "evals/s107_m014_corpus_fingerprint_apply_v1.json",
    "evals/s107_personal_data_hardening_apply_v1.json",
    "evals/s107_bounded_synthesis_pilot_v1.json",
    "supabase/migrations/20260713141223_reconcile_validated_document_revisions_v1.sql",
    "supabase/migrations/20260713164800_harden_personal_data_tables_v1.sql",
)


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _stable_sha(value: Any) -> str:
    return _sha_bytes(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    )


def _reranker_prompt_ast_sha() -> str:
    tree = ast.parse((ROOT / "src/rag/reranker.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "rerank_chunks":
            for child in ast.walk(node):
                if isinstance(child, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "prompt"
                    for target in child.targets
                ):
                    return _sha_bytes(
                        ast.dump(child.value, include_attributes=False).encode("utf-8")
                    )
    raise RuntimeError("reranker prompt assignment not found")


def _corpus_fingerprint(database_url: str) -> dict[str, Any]:
    connection = psycopg2.connect(
        database_url,
        connect_timeout=20,
        application_name="s107_freeze_structural_neighbor_runtime",
    )
    connection.set_session(readonly=True, autocommit=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '300s'")
            cursor.execute("SELECT public.corpus_fingerprint_v1()")
            payload = cursor.fetchone()[0]
        connection.rollback()
    finally:
        connection.close()
    if payload.get("schema") != "corpus_fingerprint_v1":
        raise RuntimeError("invalid corpus fingerprint")
    return payload


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL missing")

    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    pilot_flags = pilot["frozen_inputs"]["flags"]
    if pilot["frozen_inputs"]["model"] != "claude-sonnet-4-6":
        raise RuntimeError("cached served receipt model drift")
    if pilot_flags["RERANK_TOP_K"] != "10" or pilot_flags["RERANKER_BACKEND"] != "llm":
        raise RuntimeError("cached served receipt reranker contract drift")

    file_receipts = []
    for relative in FILES:
        path = ROOT / relative
        file_receipts.append(
            {"path": relative, "bytes": path.stat().st_size, "sha256": _sha_file(path)}
        )

    served_receipt = [
        {"qid": row["qid"], "context_ids": row["context_ids"]}
        for row in sorted(pilot["rows"], key=lambda item: item["qid"])
    ]
    local_effective_top_k = int(os.environ.get("RERANK_TOP_K", "5"))
    local_key_version = os.environ.get(
        "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION", ""
    ).strip()
    local_secret = os.environ.get("STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY", "")
    retention_verified = os.environ.get(
        "STRUCTURAL_NEIGHBOR_SHADOW_RETENTION_VERIFIED", "off"
    ).strip().lower() == "on"
    access_verified = os.environ.get(
        "STRUCTURAL_NEIGHBOR_SHADOW_ACCESS_VERIFIED", "off"
    ).strip().lower() == "on"
    blockers = []
    if len(local_secret) < 32 or local_key_version != "v1":
        blockers.append("deployment_hmac_secret_and_key_version_v1_not_verified")
    if not retention_verified or not access_verified:
        blockers.append("deployment_14_day_retention_and_restricted_access_not_verified")
    if local_effective_top_k != 10:
        blockers.append("deployment_rerank_top_k_10_not_verified_in_current_environment")

    corpus = _corpus_fingerprint(database_url)
    payload = {
        "schema": "s107_structural_neighbor_runtime_freeze_v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "worktree_policy": (
            "deployment dependency closure listed explicitly; validate again from a "
            "clean checkout before release"
        ),
        "status": (
            "frozen_ready_for_preregistered_shadow"
            if not blockers
            else "frozen_activation_blocked_by_external_runtime_configuration"
        ),
        "official_ok_baseline": "93/127 unchanged",
        "stage": "R2_observer_safety_and_precision_precondition",
        "candidate": {
            "feature_flag": "STRUCTURAL_NEIGHBOR_SHADOW",
            "default": "off",
            "serving_effect": "none",
            "sample_basis_points": 1000,
            "hmac_key_version": "v1",
            "hmac_secret_in_manifest": False,
            "retention_days_max": 14,
            "access": "operations_and_named_evaluators_only",
        },
        "corpus_fingerprint": corpus,
        "selector": {
            "code_sha256": _sha_file(ROOT / "src/rag/structural_neighbor_coverage.py"),
            "config_sha256": _sha_file(ROOT / "config/structural_neighbor_coverage_v1.yaml"),
            "query_facet_sha256": _sha_file(ROOT / "config/retrieval_facets_v3.yaml"),
            "structured_claim_config_sha256": _sha_file(
                ROOT / "config/structured_numeric_claims_v2.yaml"
            ),
        },
        "reranker_receipt": {
            "model_alias": "claude-sonnet-4-6",
            "backend": "llm",
            "rerank_top_k": 10,
            "preview_chars": 800,
            "temperature": 0,
            "prompt_ast_sha256": _reranker_prompt_ast_sha(),
            "cached_served_artifact": PILOT.relative_to(ROOT).as_posix(),
            "cached_served_artifact_sha256": _sha_file(PILOT),
            "cached_context_ids_sha256": _stable_sha(served_receipt),
            "cached_queries": len(served_receipt),
        },
        "adjudication_rubric_sha256": _stable_sha(prereg["adjudication"]),
        "adjudication_join": {
            "pure_join_sha256": _sha_file(
                ROOT / "scripts/s107_shadow_adjudication_join.py"
            ),
            "local_panel_sha256": _sha_file(
                ROOT / "scripts/s107_shadow_adjudication_panel.py"
            ),
            "raw_query_or_content_in_durable_receipt": False,
            "synthetic_http_smoke": "GET_200_POST_303_completion_200",
        },
        "personal_data_boundary": {
            "receipt": "evals/s107_personal_data_hardening_apply_v1.json",
            "receipt_sha256": _sha_file(
                ROOT / "evals/s107_personal_data_hardening_apply_v1.json"
            ),
            "status": "applied_and_postgrest_verified",
        },
        "preregistration_sha256": _sha_file(PREREG),
        "focused_regression": "106 passed from the explicit deployable closure",
        "post_migration_local_probe": "3/3 target facts; 14/39 activations; 28 anchors; 0 overflow",
        "external_activation_checks": {
            "current_environment_rerank_top_k": local_effective_top_k,
            "hmac_secret_configured": len(local_secret) >= 32,
            "hmac_key_version": local_key_version or None,
            "retention_verified": retention_verified,
            "access_verified": access_verified,
        },
        "activation_blockers": blockers,
        "files": file_receipts,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "activation_blockers": blockers,
                "corpus_content_sha256": corpus["content_sha256"],
                "corpus_embedding_sha256": corpus["embedding_sha256"],
                "files": len(file_receipts),
                "output": OUT.relative_to(ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
