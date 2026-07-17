import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

import scripts.s195_build_fresh_source_packet as s195_builder
import scripts.s195_author_transport_gate as s195_gate
from scripts.s165_answer_archetype_ledger import FACETS
from scripts.s194_build_fresh_source_packet import PRIOR_PACKETS
from scripts.s195_author_transport_gate import (
    AUTHOR_SYSTEM,
    S194_SOURCE,
    author_transport_schema,
    canonical_author_schema,
    normalize_transport_payload,
    semantic_validator_payload,
    semantic_checks,
    semantic_validator_schema,
    validate_semantic_review,
    validate_authorization,
    validate_provider_schema,
    verified_units,
    write_json_exclusive,
)
from scripts.s195_build_fresh_source_packet import S194_PACKET


ROOT = Path(__file__).resolve().parents[1]


def _source_and_units():
    source = json.loads(S194_SOURCE.read_text(encoding="utf-8"))["items"][0]
    return source, verified_units(source)


def _point(unit_ids):
    padded = [*unit_ids, None, None][:3]
    return {
        "claim": "Punto comprobable",
        "facet": FACETS[0],
        "support_slots": {
            "primary": padded[0],
            "secondary": padded[1],
            "tertiary": padded[2],
        },
    }


def _eligible_payload(source, units):
    return {
        "item_id": source["item_id"],
        "eligible": True,
        "question": "¿Qué debe comprobar el técnico?",
        "answer_point_slots": {
            "point_1": _point([units[0].unit_id]),
            "point_2": _point(
                [units[1].unit_id, units[2].unit_id, units[3].unit_id]
            ),
            "point_3": None,
            "point_4": None,
        },
    }


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def test_canonical_contract_encodes_exact_support_cardinality():
    support = canonical_author_schema()["properties"]["answer_points"]["items"][
        "properties"
    ]["support_unit_ids"]
    assert support["minItems"] == 1
    assert support["maxItems"] == 3
    assert support["uniqueItems"] is True


def test_provider_transport_is_array_free_and_provider_compatible():
    source, units = _source_and_units()
    schema = author_transport_schema(
        source["item_id"], [unit.unit_id for unit in units]
    )
    validate_provider_schema(schema)
    assert not any(node.get("type") == "array" for node in _walk_dicts(schema))
    assert not any(
        {"maxItems", "uniqueItems"}.intersection(node)
        for node in _walk_dicts(schema)
    )


def test_transport_binds_item_and_support_ids_to_source_enums():
    source, units = _source_and_units()
    ids = [unit.unit_id for unit in units]
    schema = author_transport_schema(source["item_id"], ids)
    assert schema["properties"]["item_id"]["const"] == source["item_id"]
    assert schema["$defs"]["unit_id"]["enum"] == ids


def test_author_system_explains_transport_slots_without_changing_label_task():
    assert "support_slots.primary" in AUTHOR_SYSTEM
    assert "use null" in AUTHOR_SYSTEM
    assert "does not change the labeling task" in AUTHOR_SYSTEM


def test_normalizer_reconstructs_canonical_arrays_and_receipts():
    source, units = _source_and_units()
    item = normalize_transport_payload(_eligible_payload(source, units), source, units)
    assert item["eligible"] is True
    assert [len(point["support_unit_ids"]) for point in item["answer_points"]] == [
        1,
        3,
    ]
    assert all(point["support_unit_receipts"] for point in item["answer_points"])


def test_transport_schema_rejects_unknown_source_unit_id():
    source, units = _source_and_units()
    payload = _eligible_payload(source, units)
    payload["answer_point_slots"]["point_1"]["support_slots"][
        "primary"
    ] = "E999_not_in_source"
    schema = author_transport_schema(
        source["item_id"], [unit.unit_id for unit in units]
    )
    assert list(Draft202012Validator(schema).iter_errors(payload))


def test_normalizer_rejects_duplicate_support_ids():
    source, units = _source_and_units()
    payload = _eligible_payload(source, units)
    support = payload["answer_point_slots"]["point_1"]["support_slots"]
    support["secondary"] = support["primary"]
    with pytest.raises(ValueError, match="duplicate"):
        normalize_transport_payload(payload, source, units)


def test_normalizer_rejects_non_contiguous_answer_points():
    source, units = _source_and_units()
    payload = _eligible_payload(source, units)
    payload["answer_point_slots"]["point_3"] = copy.deepcopy(
        payload["answer_point_slots"]["point_2"]
    )
    payload["answer_point_slots"]["point_2"] = None
    with pytest.raises(ValueError, match="contiguous"):
        normalize_transport_payload(payload, source, units)


def test_provider_guard_rejects_unsupported_array_keywords():
    with pytest.raises(ValueError, match="unsupported Anthropic schema"):
        validate_provider_schema(
            {"type": "array", "items": {"type": "string"}, "maxItems": 3}
        )


def test_semantic_validator_contract_has_exact_point_slots():
    source, units = _source_and_units()
    item = normalize_transport_payload(_eligible_payload(source, units), source, units)
    schema = semantic_validator_schema(item)
    properties = schema["properties"]["point_reviews"]["properties"]
    assert properties["point_1"]["type"] == "object"
    assert properties["point_2"]["type"] == "object"
    assert properties["point_3"] == {"type": "null"}
    assert properties["point_4"] == {"type": "null"}


def test_external_semantic_gate_requires_every_claim_and_question():
    source, units = _source_and_units()
    item = normalize_transport_payload(_eligible_payload(source, units), source, units)
    review = {
        "item_id": item["item_id"],
        "eligibility_correct": True,
        "eligibility_issue": "",
        "question_answerable": True,
        "question_issue": "",
        "point_reviews": {
            "point_1": {"fully_supported": True, "issue": ""},
            "point_2": {"fully_supported": True, "issue": ""},
            "point_3": None,
            "point_4": None,
        },
    }
    clean = validate_semantic_review(review, item)
    assert all(semantic_checks([clean], 0, [item]).values())
    review["point_reviews"]["point_2"]["fully_supported"] = False
    assert not semantic_checks([review], 0, [item])["all_claims_fully_supported"]


def test_semantic_validator_sees_full_document_units_and_cited_ids():
    source, units = _source_and_units()
    item = normalize_transport_payload(_eligible_payload(source, units), source, units)
    payload = json.loads(semantic_validator_payload(item, units))
    assert len(payload["all_source_units"]) == len(units)
    assert payload["answer_points"][0]["cited_source_unit_ids"] == item[
        "answer_points"
    ][0]["support_unit_ids"]
    assert "cited_source_units" not in payload["answer_points"][0]


def test_exclusive_checkpoint_rejects_a_second_owner(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    write_json_exclusive(checkpoint, {"owner": 1})
    with pytest.raises(FileExistsError):
        write_json_exclusive(checkpoint, {"owner": 2})


def test_builder_excludes_target_content_and_extraction_twins(tmp_path, monkeypatch):
    target_id = "11111111-1111-1111-8111-111111111111"
    target_file = tmp_path / "target.json"
    target_file.write_text(json.dumps({"chunk_id": target_id}), encoding="utf-8")
    monkeypatch.setattr(s195_builder, "TARGET_FILES", (target_file,))
    rows = [
        {
            "id": target_id,
            "document_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "content": "protected",
            "extraction_sha256": "extract-protected",
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "document_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "content": "protected",
            "extraction_sha256": "other-extraction",
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "document_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "content": "other content",
            "extraction_sha256": "extract-protected",
        },
        {
            "id": "44444444-4444-4444-4444-444444444444",
            "document_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "content": "fresh",
            "extraction_sha256": "extract-fresh",
        },
    ]
    filtered, receipt = s195_builder.exclude_target_equivalents(rows)
    assert [row["content"] for row in filtered] == ["fresh"]
    assert receipt["rows_excluded"] == 3
    assert receipt["target_rows_resolved"] == 1
    assert receipt["target_uuid_count"] == 1
    assert receipt["resolved_rows"][0]["chunk_id"] == target_id


def test_authorization_rejects_self_declared_relaxed_contract(tmp_path):
    prereg = tmp_path / "prereg.yaml"
    permit = tmp_path / "permit.yaml"
    prereg.write_text(
        yaml.safe_dump(
            {
                "instrument": "s195_author_transport_prereg_v1",
                "status": "FROZEN_BEFORE_PAID_EXECUTION",
                "models": {},
            }
        ),
        encoding="utf-8",
    )
    permit.write_text(
        yaml.safe_dump(
            {
                "instrument": "s195_author_transport_execution_permit_v1",
                "status": "EXECUTION_GO_PAID_BOUNDED_NO_RETRY",
                "authority": "user_requested_autonomous_next_segment",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="models contract drift"):
        validate_authorization(prereg, permit)


def test_known_semantic_failure_takes_no_go_precedence_over_provider_hold(
    tmp_path, monkeypatch
):
    author_receipts = tmp_path / "author.json"
    semantic_receipts = tmp_path / "semantic.json"
    result_path = tmp_path / "result.json"
    semantic_receipts.write_text(
        json.dumps(
            {
                "receipts": [
                    {
                        "validation_error": None,
                        "review": {
                            "eligibility_correct": True,
                            "question_answerable": True,
                            "point_reviews": {
                                "point_1": {
                                    "fully_supported": False,
                                    "issue": "unsupported",
                                }
                            },
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(s195_gate, "ROOT", tmp_path)
    monkeypatch.setattr(s195_gate, "DEFAULT_RECEIPTS", author_receipts)
    monkeypatch.setattr(
        s195_gate, "DEFAULT_SEMANTIC_RECEIPTS", semantic_receipts
    )
    monkeypatch.setattr(s195_gate, "DEFAULT_COHORT", tmp_path / "cohort.json")
    monkeypatch.setattr(s195_gate, "DEFAULT_RESULT", result_path)
    result = s195_gate._hold(TimeoutError("provider interrupted"))
    assert result["status"].endswith("AFTER_KNOWN_FAILURE")


def test_s195_builder_excludes_s194_as_an_additional_prior_packet():
    assert S194_PACKET not in PRIOR_PACKETS
    assert S194_PACKET.name == "s194_fresh_source_packet_v1.json"
