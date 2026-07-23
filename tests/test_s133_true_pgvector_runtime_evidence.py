import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evals/s133_true_pgvector_runtime_gate_v1.json"


def _sha256(path: Path) -> str:
    # Receipts are sealed over the repository's canonical LF representation,
    # independent of a Windows checkout's core.autocrlf setting.
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def test_s133_true_pgvector_evidence_is_go_isolated_and_current():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["status"] == "GO_TRUE_PGVECTOR_RUNTIME_CONTRACT"
    assert payload["runtime"] == {
        "kind": "disposable_github_actions_service",
        "production_data": False,
        "railway": False,
    }
    assert payload["cost"] == {
        "model_calls": 0,
        "embedding_calls": 0,
        "production_database_writes": 0,
    }
    assert payload["positive"]["verification"]["pgvector_semantics"]["status"] == (
        "DELEGATED_TO_S133_REAL_PROBE"
    )
    vector = payload["true_pgvector"]
    assert vector["status"] == "PASS"
    assert vector["extension_version"] == "0.8.0"
    assert vector["cosine_distance_semantics"] == {
        "status": "PASS",
        "same": 0,
        "opposite": 2,
        "orthogonal": 1,
        "extension_version": "0.8.0",
    }
    assert vector["hnsw_index_behavior"] == {
        "status": "PASS",
        "index_name": "s133_vectors_hnsw",
        "node_type": "Index Scan",
    }
    assert payload["rollback"] == {"status": "PASS", "residual_shadow_objects": 0}

    assert payload["authority"]["positive_harness_sha256"] == _sha256(
        ROOT / "scripts/s131_m0b_disposable_gate.py"
    )
    assert payload["authority"]["negative_harness_sha256"] == _sha256(
        ROOT / "scripts/s131_m0b_negative_gate.py"
    )
    assert payload["authority"]["s117_migration_sha256"] == _sha256(
        ROOT
        / "supabase/migration_proposals/20260714102428_chunks_v3_provenance_shadow.sql"
    )
    assert payload["authority"]["s131_migration_sha256"] == _sha256(
        ROOT
        / "supabase/migration_proposals/20260716120000_chunks_v3_shadow_binding_v2.sql"
    )
