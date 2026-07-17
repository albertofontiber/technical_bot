from __future__ import annotations

import copy

from jsonschema import Draft202012Validator

from scripts import s139_schema_hardened_completion as base
from scripts import s139_schema_hardened_completion_v2 as audit


def packet_and_sol() -> tuple[dict, dict, dict]:
    prereg = audit.files.load_yaml(base.DEFAULT_PREREG)
    packet = audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["packet"]["path"]
    )
    sol = audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["sol_valid"]["path"]
    )["judgement"]
    return packet, sol, prereg


def standard_to_keyed(standard: dict, packet: dict) -> dict:
    rows = {row["question_id"]: row for row in standard["judgements"]}
    questions: dict = {}
    for question in packet["questions"]:
        qid = question["question_id"]
        sets = {row["evidence_set_id"]: row for row in rows[qid]["set_judgements"]}
        set_values: dict = {}
        for evidence_set in question["evidence_sets"]:
            set_id = evidence_set["evidence_set_id"]
            row = sets[set_id]
            assessments = {
                assessment["evidence_id"]: {
                    key: value
                    for key, value in assessment.items()
                    if key != "evidence_id"
                }
                for assessment in row["evidence_assessments"]
            }
            set_values[set_id] = {
                "answerability": row["answerability"],
                "minimum_sufficient_evidence_ids": row[
                    "minimum_sufficient_evidence_ids"
                ],
                "evidence_by_id": assessments,
                "confidence": row["confidence"],
                "rationale": row["rationale"],
            }
        questions[qid] = {"sets_by_id": set_values}
    return {"questions_by_id": questions}


def test_keyed_schema_uses_only_provider_supported_collection_contract() -> None:
    packet, _, prereg = packet_and_sol()
    subset = base.s138.subset_packet(packet, {prereg["completion_question_id"]})
    schema = audit.hardened_schema(subset)
    serialized = str(schema)
    for unsupported in ("maxItems", "minItems", "prefixItems", "uniqueItems"):
        assert unsupported not in serialized


def test_keyed_schema_and_adapter_preserve_a_complete_valid_judgement() -> None:
    packet, sol, prereg = packet_and_sol()
    subset = base.s138.subset_packet(packet, {prereg["completion_question_id"]})
    sol_subset = base.s138.subset_judgement(sol, {prereg["completion_question_id"]})
    keyed = standard_to_keyed(sol_subset, subset)
    assert not list(Draft202012Validator(audit.hardened_schema(subset)).iter_errors(keyed))
    restored = audit.keyed_to_standard(keyed, subset)
    base.s138.validate_judgement(
        restored, subset, question_ids={prereg["completion_question_id"]}
    )
    assert base.s138.semantic_ranks(restored, audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["mapping"]["path"]
    )) == base.s138.semantic_ranks(sol_subset, audit.files.load_json(
        audit.ROOT / prereg["frozen_inputs"]["mapping"]["path"]
    ))


def test_keyed_schema_rejects_one_missing_evidence_property() -> None:
    packet, sol, prereg = packet_and_sol()
    subset = base.s138.subset_packet(packet, {prereg["completion_question_id"]})
    keyed = standard_to_keyed(
        base.s138.subset_judgement(sol, {prereg["completion_question_id"]}), subset
    )
    broken = copy.deepcopy(keyed)
    qid = prereg["completion_question_id"]
    set_id = subset["questions"][0]["evidence_sets"][0]["evidence_set_id"]
    evidence_id = subset["questions"][0]["evidence_sets"][0]["evidence"][0][
        "evidence_id"
    ]
    del broken["questions_by_id"][qid]["sets_by_id"][set_id]["evidence_by_id"][
        evidence_id
    ]
    errors = list(
        Draft202012Validator(audit.hardened_schema(subset)).iter_errors(broken)
    )
    assert errors
    assert any("required property" in error.message for error in errors)
