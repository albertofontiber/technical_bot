from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from scripts import s139_schema_hardened_completion as audit


def real_packet_and_prereg() -> tuple[dict, dict]:
    prereg = audit.files.load_yaml(audit.DEFAULT_PREREG)
    packet = audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["packet"]["path"]
    )
    return packet, prereg


def test_prereg_and_all_reused_receipts_are_frozen_and_valid() -> None:
    prereg = audit.files.load_yaml(audit.DEFAULT_PREREG)
    audit.validate_prereg(prereg)
    frozen = audit.load_frozen(prereg)
    assert frozen["sol_valid"]["status"] == "VALIDATED"
    assert frozen["fable_q3_invalid"]["status"] == "PAID_INVALID_NO_RETRY"


def test_hardened_schema_requires_every_set_and_evidence_id_in_packet_order() -> None:
    packet, prereg = real_packet_and_prereg()
    subset = audit.s138.subset_packet(packet, {prereg["completion_question_id"]})
    schema = audit.hardened_schema(subset)
    question = subset["questions"][0]
    qschema = schema["properties"]["judgements"]["prefixItems"][0]
    assert qschema["properties"]["question_id"]["const"] == question["question_id"]
    set_schemas = qschema["properties"]["set_judgements"]["prefixItems"]
    assert len(set_schemas) == 2
    for evidence_set, set_schema in zip(question["evidence_sets"], set_schemas, strict=True):
        assert set_schema["properties"]["evidence_set_id"]["const"] == evidence_set[
            "evidence_set_id"
        ]
        assessments = set_schema["properties"]["evidence_assessments"]
        expected = [row["evidence_id"] for row in evidence_set["evidence"]]
        actual = [
            row["properties"]["evidence_id"]["const"] for row in assessments["prefixItems"]
        ]
        assert actual == expected
        assert assessments["minItems"] == assessments["maxItems"] == 10


def test_hardened_schema_rejects_the_frozen_omission() -> None:
    packet, prereg = real_packet_and_prereg()
    subset = audit.s138.subset_packet(packet, {prereg["completion_question_id"]})
    invalid_receipt = audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["fable_q3_invalid"]["path"]
    )
    invalid_judgement = json.loads(invalid_receipt["raw_output"])
    errors = list(
        Draft202012Validator(audit.hardened_schema(subset)).iter_errors(
            invalid_judgement
        )
    )
    assert errors
    assert any("too short" in error.message for error in errors)


def test_incremental_caps_remain_below_internal_ceiling_with_prior_reserve() -> None:
    _, prereg = real_packet_and_prereg()
    incremental = audit.incremental_worst(
        prereg, prereg["models"]["independent_completion"]["max_counted_input_tokens"]
    )
    total = (
        prereg["budget"]["known_s138_cost_before_s139_usd"]
        + prereg["budget"]["failed_520_unknown_cost_reserve_usd"]
        + incremental
    )
    assert incremental == prereg["budget"]["s139_incremental_caps_worst_case_usd"]
    assert total < prereg["budget"]["s138_internal_ceiling_usd"]
