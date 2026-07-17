from __future__ import annotations

import json
from pathlib import Path

from src.rag import catalog_resolver
from src.rag.answer_planner import (
    ANSWER_PLANNER_CONTRACT_S122,
    ANSWER_PLANNER_CONTRACT_S141,
    AnswerObligation,
    build_answer_plan,
    enforce_answer_contract,
    enforceable_answer_plan,
    obligation_covered,
    validate_answer_plan,
)
from src.rag.source_identity_attestation import (
    attach_query_source_identity,
    validated_query_source_identity_sha256,
)
from src.rag.technical_obligations import extract_technical_obligations


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "evals" / "s113_full_contexts_freeze_v1.json"
TARGET_QIDS = {"cat007", "cat018", "hp002", "hp011", "hp017"}
S141_KINDS = {
    "point_programming_fields",
    "software_type_cbe_activation",
    "input_condition_definition",
    "output_condition_action",
    "logic_contradiction_warning",
    "commissioning_rule_verification",
    "option_family_cardinality",
    "maintenance_isolation_prerequisite",
    "initial_reference_calibration",
    "bounded_fault_window",
    "default_latched_faults",
    "extinction_duration_range",
    "reset_inhibit_special_state",
}


def _frozen_rows() -> dict[str, dict]:
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    return {row["qid"]: row for row in payload["rows"]}


def _attested(row: dict) -> list[dict]:
    return attach_query_source_identity(
        row["question"],
        row["context"],
        catalog_resolver.resolve_query(row["question"]),
        catalog_commit="test-catalog-commit",
    )


def _s141_plan(row: dict):
    return build_answer_plan(
        row["question"],
        _attested(row),
        max_obligations=20,
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S141,
    )


def _obligation(kind: str, statement: str, anchors: tuple[str, ...]):
    return AnswerObligation(
        obligation_id=f"obl_{kind}",
        fragment_number=1,
        candidate_id="source",
        facet=f"served_technical:{kind}",
        kind=kind,
        statement=statement,
        required_anchors=anchors,
        source_start=0,
        source_end=len(statement),
    )


def test_query_source_identity_receipt_is_query_and_source_bound():
    query = "How do I reset MODEL-X?"
    chunks = [
        {"id": "a", "source_file": "manual-a", "product_model": "MODEL-X-Pro"},
        {"id": "b", "source_file": "manual-b", "product_model": "MODEL-Y"},
    ]
    resolution = {
        "records": [
            {
                "token": "model-x",
                "via": "alias",
                "politica": "prefer:maker:model-x-pro",
                "expand": True,
                "ids": ["maker:model-x-pro"],
            }
        ],
        "source_groups": [
            {
                "token": "model-x",
                "ids": ["maker:model-x-pro"],
                "sources": ["manual-a"],
            }
        ],
    }
    attached = attach_query_source_identity(
        query, chunks, resolution, catalog_commit="abc123"
    )
    assert validated_query_source_identity_sha256(query, attached[0])
    assert validated_query_source_identity_sha256("different query", attached[0]) is None
    assert "query_source_identity_attestation" not in attached[1]

    tampered = dict(attached[0])
    tampered["source_file"] = "manual-b"
    assert validated_query_source_identity_sha256(query, tampered) is None


def test_ambiguous_shared_source_is_not_attested():
    chunks = [{"source_file": "shared", "product_model": "family"}]
    resolution = {
        "records": [
            {"token": "a", "via": "alias", "expand": True, "ids": ["m:a"]},
            {"token": "b", "via": "alias", "expand": True, "ids": ["m:b"]},
        ],
        "source_groups": [
            {"token": "a", "ids": ["m:a"], "sources": ["shared"]},
            {"token": "b", "ids": ["m:b"], "sources": ["shared"]},
        ],
    }
    assert attach_query_source_identity(
        "compare A and B", chunks, resolution, catalog_commit="abc"
    ) == chunks


def test_frozen_target_extracts_13_served_relations_and_rejects_5_source_gaps():
    rows = _frozen_rows()
    expected = {
        "cat007": set(),
        "cat018": {"point_programming_fields", "software_type_cbe_activation"},
        "hp002": {
            "maintenance_isolation_prerequisite",
            "initial_reference_calibration",
            "bounded_fault_window",
        },
        "hp011": {
            "default_latched_faults",
            "extinction_duration_range",
            "reset_inhibit_special_state",
        },
        "hp017": {
            "input_condition_definition",
            "output_condition_action",
            "logic_contradiction_warning",
            "commissioning_rule_verification",
            "option_family_cardinality",
        },
    }
    total = 0
    for qid, kinds in expected.items():
        plan = _s141_plan(rows[qid])
        emitted = {row.kind for row in plan if row.kind in S141_KINDS}
        assert emitted == kinds
        total += len(emitted)
        for obligation in plan:
            chunk = next(
                row
                for row in _attested(rows[qid])
                if row.get("id") == obligation.candidate_id
            )
            content = str(chunk.get("content") or "")
            assert 0 <= obligation.source_start < obligation.source_end <= len(content)
    assert total == 13


def test_new_runtime_extractor_contains_no_benchmark_or_product_literals():
    runtime = (ROOT / "src" / "rag" / "technical_obligations.py").read_text(
        encoding="utf-8"
    ).casefold()
    forbidden = {
        "cat007",
        "cat018",
        "hp002",
        "hp011",
        "hp017",
        "faast lt-200",
        "pearl",
        "am-8200",
        "asd535",
        "rp1r",
        "notifier",
        "detnov",
        "morley",
        "honeywell",
    }
    assert not {term for term in forbidden if term in runtime}


def test_s122_does_not_silently_promote_s141_kinds():
    rows = _frozen_rows()
    legacy = build_answer_plan(
        rows["cat018"]["question"],
        rows["cat018"]["context"],
        max_obligations=20,
        planner_contract_version=ANSWER_PLANNER_CONTRACT_S122,
    )
    assert "point_programming_fields" in {row.kind for row in legacy}
    assert "point_programming_fields" not in {
        row.kind
        for row in enforceable_answer_plan(
            legacy, planner_contract_version=ANSWER_PLANNER_CONTRACT_S122
        )
    }


def test_cardinality_validator_rejects_seven_items_declared_as_six():
    row = _obligation(
        "option_family_cardinality",
        "One of six delay types can be assigned to a rule.",
        ("six", "delay types", "rule"),
    )
    six = "Six delay types can be assigned to a rule:\n" + "\n".join(
        f"- Type {index}" for index in range(1, 7)
    )
    seven = six + "\n- Type 7"
    assert obligation_covered(six, row)
    assert not obligation_covered(seven, row)


def test_relational_validator_rejects_disconnected_anchor_bags():
    row = _obligation(
        "maintenance_isolation_prerequisite",
        "Isolate fire controls, remote alerts and extinguishing zones.",
        ("fire controls", "remote alerts", "extinguishing zones", "isolate"),
    )
    assert obligation_covered(
        "Before maintenance, isolate fire controls, remote alerts and extinguishing zones.",
        row,
    )
    disconnected = (
        "Isolate the fire controls before maintenance.\n\n"
        + "Unrelated diagnostic guidance. " * 80
        + "\n\nRemote alerts and extinguishing zones are described elsewhere."
    )
    assert not obligation_covered(disconnected, row)


def test_source_bound_reconstruction_covers_all_13_target_relations():
    rows = _frozen_rows()
    answer_sources = [
        ROOT / "evals" / "s113_full_answer_regression_v1.json",
        ROOT / "evals" / "s133_unmeasured_answer_probe_v1.json",
    ]
    answers = {}
    for path in answer_sources:
        payload = json.loads(path.read_text(encoding="utf-8"))
        answers.update({row["qid"]: row.get("answer") or "" for row in payload["rows"]})

    expected_counts = {"cat018": 2, "hp002": 3, "hp011": 3, "hp017": 5}
    recovered = 0
    for qid, expected in expected_counts.items():
        plan = _s141_plan(rows[qid])
        target = [row for row in plan if row.kind in S141_KINDS]
        revised, metadata = enforce_answer_contract(
            rows[qid]["question"],
            answers[qid],
            plan,
            [],
            planner_contract_version=ANSWER_PLANNER_CONTRACT_S141,
        )
        validation = validate_answer_plan(revised, target)
        assert validation["covered"] == validation["total"] == expected
        assert metadata["action"] in {"source_bound_reconstruction", "fail_closed"}
        recovered += validation["covered"]
    assert recovered == 13


def test_all_34_non_target_frozen_questions_are_negative_controls():
    rows = _frozen_rows()
    for qid, row in rows.items():
        if qid in TARGET_QIDS:
            continue
        emitted = {
            obligation.kind
            for obligation in _s141_plan(row)
            if obligation.kind in S141_KINDS
        }
        assert emitted == set(), qid


def test_extractor_is_byte_deterministic_on_target_contexts():
    rows = _frozen_rows()
    for qid in TARGET_QIDS:
        aligned = list(enumerate(_attested(rows[qid]), 1))
        first = [row.__dict__ for row in extract_technical_obligations(rows[qid]["question"], aligned)]
        second = [row.__dict__ for row in extract_technical_obligations(rows[qid]["question"], aligned)]
        assert first == second
