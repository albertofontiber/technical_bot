import pytest

from scripts.s133_true_pgvector_runtime_gate import (
    _validate_distances,
    _validate_hnsw_plan,
)


def test_real_vector_distance_contract_accepts_cosine_truth_table():
    _validate_distances(
        {
            "extension_version": "0.8.0",
            "same": 0,
            "orthogonal": 1,
            "opposite": 2,
        },
        "0.8.0",
    )
    with pytest.raises(RuntimeError, match="distance drift"):
        _validate_distances(
            {
                "extension_version": "0.8.0",
                "same": 0,
                "orthogonal": 0.5,
                "opposite": 2,
            },
            "0.8.0",
        )


def test_real_vector_contract_requires_hnsw_index_scan():
    plan = [
        {
            "Plan": {
                "Node Type": "Limit",
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Index Name": "s133_vectors_hnsw",
                    }
                ],
            }
        }
    ]
    assert _validate_hnsw_plan(plan)["status"] == "PASS"
    with pytest.raises(RuntimeError, match="HNSW index was not used"):
        _validate_hnsw_plan([{"Plan": {"Node Type": "Seq Scan"}}])
