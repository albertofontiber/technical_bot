from __future__ import annotations

import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

import scripts.s197_static_author_luna_gate as s197
from scripts.s196_static_transport_canary import (
    FACETS,
    FORBIDDEN_SCHEMA_KEYS,
    static_transport_schema,
)
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


def _point(*, active, claim="", facet="", supports=("", "", "")):
    return {
        "active": active,
        "claim": claim,
        "facet": facet,
        "support_1": supports[0],
        "support_2": supports[1],
        "support_3": supports[2],
    }


def _row(index=1, *, stratum="table"):
    item_id = f"s197_src_{index:02d}"
    excerpt = "Before service, isolate power.\n\nAfter service, replace the guard."
    units = build_header_aware_evidence_units(
        excerpt, fragment_number=1, candidate_id=item_id
    )
    return {
        "item_id": item_id,
        "stratum": stratum,
        "manufacturer": f"Vendor {index:02d}",
        "product_model": f"Model {index:02d}",
        "document_id": f"00000000-0000-4000-8000-{index:012d}",
        "chunk_id": f"10000000-0000-4000-8000-{index:012d}",
        "excerpt_sha256": f"excerpt-{index:02d}",
        "excerpt": excerpt,
        "evidence_unit_manifest": [
            {
                "unit_id": unit.unit_id,
                "unit_kind": unit.unit_kind,
                "source_spans": [list(span) for span in unit.source_spans],
                "content_sha256": unit.content_sha256,
            }
            for unit in units
        ],
    }


def _eligible_payload(row):
    units = s197.verified_units(row)
    return {
        "item_id": row["item_id"],
        "eligible": True,
        "question": "¿Qué debe hacer el técnico antes y después del servicio?",
        "answer_point_slots": {
            "point_1": _point(
                active=True,
                claim="Aislar la alimentación antes del servicio.",
                facet=FACETS[0],
                supports=(units[0].unit_id, "", ""),
            ),
            "point_2": _point(
                active=True,
                claim="Reponer la protección después del servicio.",
                facet=FACETS[3],
                supports=(units[-1].unit_id, "", ""),
            ),
            "point_3": _point(active=False),
            "point_4": _point(active=False),
        },
    }


def _source_contract_fixture(tmp_path, monkeypatch):
    empty_authority = tmp_path / "empty-authority.json"
    empty_authority.write_text('{"items": []}\n', encoding="utf-8")
    target_id = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    target_authority = tmp_path / "target.json"
    target_authority.write_text(
        json.dumps({"chunk_id": target_id}) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(s197, "S194_SOURCE", empty_authority)
    monkeypatch.setattr(s197, "S195_SOURCE", empty_authority)
    monkeypatch.setattr(s197, "TARGET_FILES", (target_authority,))
    monkeypatch.setattr(s197, "PRIOR_SOURCE_PACKETS", ())
    items = []
    for index in range(1, 15):
        row = _row(index, stratum="table" if index <= 7 else "prose")
        row["excerpt_sha256"] = hashlib.sha256(
            row["excerpt"].encode("utf-8")
        ).hexdigest()
        row["extraction_sha256"] = f"extract-{index:02d}"
        row["source_file"] = f"synthetic-s197-{index:02d}.pdf"
        items.append(row)
    snapshot = "stable-double-scan-fingerprint"
    scan = {
        "table": "chunks_v2",
        "rows": 25_090,
        "get_requests": 28,
        "database_writes": 0,
        "full_scan_sha256": snapshot,
    }
    target_content = hashlib.sha256(b"protected target").hexdigest()
    source = {
        "instrument": "s197_fresh_source_packet_v1",
        "status": "SEALED_FRESH_LIVE_CHUNKS_V2_GET_ONLY",
        "selection": {
            "fresh_after_s196": True,
            "s194_document_overlap": 0,
            "s195_document_overlap": 0,
            "prior_document_overlap": 0,
            "target_document_overlap": 0,
            "target_chunk_overlap": 0,
            "development_product_pair_overlap": 0,
            "target_exact_content_overlap": 0,
            "target_extraction_overlap": 0,
            "prior_semantic_near_duplicate_overlap_status": "NOT_MEASURED",
            "prior_oem_relabel_overlap_status": "NOT_MEASURED",
        },
        "read_receipt": {
            **scan,
            "get_requests": 56,
            "consistency": "DOUBLE_IDENTICAL_FULL_SCAN",
            "stable_full_scan_sha256": snapshot,
            "scan_1": scan,
            "scan_2": scan,
        },
        "target_equivalence_exclusion": {
            "method": (
                "TARGET_UUID_ROWS_TO_EXACT_CONTENT_AND_EXTRACTION_HASH_EXCLUSION"
            ),
            "target_uuid_count": 1,
            "target_uuid_resolution": [
                {
                    "target_uuid": target_id,
                    "status": "RESOLVED_AS_CHUNK",
                    "chunk_rows": 1,
                    "document_rows": 0,
                    "resolved_rows": 1,
                }
            ],
            "unresolved_target_uuids": [],
            "all_target_uuids_resolved": True,
            "target_rows_resolved": 1,
            "resolved_rows": [
                {
                    "chunk_id": target_id,
                    "document_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                    "content_sha256": target_content,
                    "extraction_sha256": "target-extraction",
                }
            ],
            "content_sha256": [target_content],
            "extraction_sha256": ["target-extraction"],
            "rows_excluded": 1,
            "source_stable_full_scan_sha256": snapshot,
        },
        "items": items,
    }
    source["packet_sha256"] = s197.stable_sha(source)
    return source


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def test_s197_reuses_the_exact_s196_static_schema_without_dynamic_values():
    schema = s197.static_transport_schema()
    assert schema == static_transport_schema()
    assert s197.stable_sha(schema) == (
        "9173461711bf78b7065bc37c3eb91fbe0ef5b641bb72f81c24fb815ea3599624"
    )


def test_static_schema_remains_provider_agnostic_and_rectangular():
    schema = s197.static_transport_schema()
    s197.validate_static_schema(schema)
    assert not any(node.get("type") == "array" for node in _walk_dicts(schema))
    assert not any(
        FORBIDDEN_SCHEMA_KEYS.intersection(node) for node in _walk_dicts(schema)
    )
    serialized = json.dumps(schema)
    assert "s197_src" not in serialized
    assert "E001" not in serialized
    assert not any(facet in serialized for facet in FACETS)


def test_normalizer_reconstructs_canonical_points_and_support_receipts():
    row = _row()
    units = s197.verified_units(row)
    item = s197.normalize_author_payload(_eligible_payload(row), row, units)
    assert item["eligible"] is True
    assert len(item["answer_points"]) == 2
    assert all(point["support_unit_receipts"] for point in item["answer_points"])


def test_normalizer_accepts_a_clean_ineligible_static_payload():
    row = _row()
    payload = {
        "item_id": row["item_id"],
        "eligible": False,
        "question": "",
        "answer_point_slots": {
            f"point_{index}": _point(active=False) for index in range(1, 5)
        },
    }
    item = s197.normalize_author_payload(payload, row, s197.verified_units(row))
    assert item["eligible"] is False
    assert item["answer_points"] == []


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["answer_point_slots"]["point_1"].update(
                support_1="UNKNOWN"
            ),
            "unknown support-unit ID",
        ),
        (
            lambda payload: payload["answer_point_slots"]["point_1"].update(
                support_2=payload["answer_point_slots"]["point_1"]["support_1"]
            ),
            "duplicate support-unit ID",
        ),
        (
            lambda payload: payload["answer_point_slots"]["point_3"].update(
                claim="hidden"
            ),
            "inactive answer-point slot",
        ),
        (
            lambda payload: payload["answer_point_slots"]["point_1"].update(
                support_1="",
                support_2=payload["answer_point_slots"]["point_1"]["support_1"],
            ),
            "support slots must be non-empty then empty",
        ),
    ],
)
def test_deterministic_adapter_rejects_invalid_support_shapes(mutation, message):
    row = _row()
    payload = _eligible_payload(row)
    mutation(payload)
    with pytest.raises(ValueError, match=message):
        s197.normalize_author_payload(payload, row, s197.verified_units(row))


def test_adapter_rejects_identity_gaps_and_duplicate_claims():
    row = _row()
    wrong = _eligible_payload(row)
    wrong["item_id"] = "other"
    with pytest.raises(ValueError, match="identity"):
        s197.normalize_author_payload(wrong, row, s197.verified_units(row))

    gap = _eligible_payload(row)
    gap["answer_point_slots"]["point_2"] = _point(active=False)
    gap["answer_point_slots"]["point_3"] = _point(
        active=True,
        claim="Late point",
        facet=FACETS[0],
        supports=(s197.verified_units(row)[0].unit_id, "", ""),
    )
    with pytest.raises(ValueError, match="contiguous"):
        s197.normalize_author_payload(gap, row, s197.verified_units(row))

    duplicate = copy.deepcopy(_eligible_payload(row))
    duplicate["answer_point_slots"]["point_2"]["claim"] = duplicate[
        "answer_point_slots"
    ]["point_1"]["claim"]
    with pytest.raises(ValueError, match="claims must be distinct"):
        s197.normalize_author_payload(duplicate, row, s197.verified_units(row))


def test_semantic_validator_receives_all_units_and_exact_point_slots():
    row = _row()
    units = s197.verified_units(row)
    item = s197.normalize_author_payload(_eligible_payload(row), row, units)
    payload = json.loads(s197.semantic_validator_payload(item, units))
    schema = s197.semantic_output_format(item)["format"]["schema"]
    assert len(payload["all_source_units"]) == len(units)
    assert payload["answer_points"][0]["cited_source_unit_ids"]
    assert schema["properties"]["point_reviews"]["properties"]["point_3"] == {
        "type": "null"
    }
    assert schema["properties"]["question_language_spanish"] == {"type": "boolean"}
    assert schema["properties"]["question_natural_for_field_technician"] == {
        "type": "boolean"
    }
    assert schema["properties"]["answer_points_semantically_distinct"] == {
        "type": "boolean"
    }
    assert schema["properties"][
        "answer_points_complete_for_question_within_excerpt"
    ] == {"type": "boolean"}
    point_schema = schema["properties"]["point_reviews"]["properties"]["point_1"]
    assert {"fully_supported", "support_issue", "facet_correct", "facet_issue"} == set(
        point_schema["required"]
    )


def test_semantic_review_rejects_boolean_issue_contradictions():
    row = _row()
    item = s197.normalize_author_payload(
        _eligible_payload(row), row, s197.verified_units(row)
    )
    review = {
        "item_id": item["item_id"],
        "eligibility_correct": True,
        "eligibility_issue": "",
        "question_language_spanish": True,
        "question_language_issue": "",
        "question_natural_for_field_technician": True,
        "question_naturality_issue": "",
        "answer_points_semantically_distinct": True,
        "answer_point_distinctness_issue": "",
        "answer_points_complete_for_question_within_excerpt": True,
        "answer_point_completeness_issue": "",
        "question_answerable": True,
        "question_issue": "",
        "point_reviews": {
            f"point_{index}": (
                {
                    "fully_supported": True,
                    "support_issue": "",
                    "facet_correct": True,
                    "facet_issue": "",
                }
                if index <= 2
                else None
            )
            for index in range(1, 5)
        },
    }
    assert s197.validate_semantic_review(review, item) == review
    review["point_reviews"]["point_1"]["support_issue"] = "unsupported"
    with pytest.raises(ValueError, match="issue contradiction"):
        s197.validate_semantic_review(review, item)


def test_population_gate_keeps_preregistered_thresholds_and_zero_invalids():
    authored = []
    for index in range(1, 15):
        row = _row(index, stratum="table" if index <= 7 else "prose")
        authored.append(
            s197.normalize_author_payload(
                _eligible_payload(row), row, s197.verified_units(row)
            )
        )
    assert all(s197.population_checks(authored, s197.EXPECTED_VALIDATION, 0).values())
    assert not s197.population_checks(authored, s197.EXPECTED_VALIDATION, 1)[
        "author_invalid_outputs_zero"
    ]


def test_manufacturer_diversity_is_unicode_trim_and_case_normalized():
    authored = []
    aliases = [" ABB ", "abb", "ＡＢＢ", "AbB"]
    for index in range(1, 15):
        row = _row(index, stratum="table" if index <= 7 else "prose")
        item = s197.normalize_author_payload(
            _eligible_payload(row), row, s197.verified_units(row)
        )
        if index <= len(aliases):
            item["manufacturer"] = aliases[index - 1]
        authored.append(item)
    assert len({s197.normalized_identity(value) for value in aliases}) == 1
    checks = s197.population_checks(authored, s197.EXPECTED_VALIDATION, 0)
    assert checks["eligible_manufacturers_gte_12"] is False


def test_author_no_go_precedence_detects_mathematically_impossible_population():
    authored = []
    for index in range(1, 4):
        row = _row(index)
        authored.append({**row, "eligible": False, "answer_points": []})
    remaining = [_row(index) for index in range(4, 15)]
    assert s197.author_population_already_impossible(
        authored, remaining, 0, s197.EXPECTED_VALIDATION
    )


def test_atomic_checkpoint_rejects_a_second_owner(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    s197.write_json_atomic(checkpoint, {"owner": 1}, replace=False)
    with pytest.raises(FileExistsError):
        s197.write_json_atomic(checkpoint, {"owner": 2}, replace=False)


def test_chunks_v3_lane_stays_explicit_and_does_not_copy_old_metrics():
    lane = s197.chunks_v3_lane()
    assert lane["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"
    assert lane["changed_by_s197"] is False
    assert lane["historical_metrics_duplicated"] is False
    assert "baseline" not in lane


def test_authorization_inventory_covers_transitive_prior_and_target_authorities():
    frozen = s197.frozen_runtime_inputs()
    frozen_paths = set(frozen.values())
    assert "scripts/s167_build_independent_ledger_source_support.py" in frozen_paths
    assert "scripts/s146_build_fresh_source_packet.py" in frozen_paths
    assert "evals/s114_procedure_bundle_heldout_freeze_v1.json" in frozen_paths
    assert "evals/s194_fresh_source_packet_v1.json" in frozen_paths
    assert "evals/s195_fresh_source_packet_v1.json" in frozen_paths
    assert {
        str(path.relative_to(s197.ROOT)).replace("\\", "/")
        for path in s197.TARGET_FILES
    }.issubset(frozen_paths)


def test_source_contract_accepts_a_consistent_structurally_fresh_packet(
    tmp_path, monkeypatch
):
    source = _source_contract_fixture(tmp_path, monkeypatch)
    s197.source_contract(source)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda source: source["selection"].update(prior_document_overlap=1),
        lambda source: source["read_receipt"]["scan_2"].update(
            full_scan_sha256="drift"
        ),
        lambda source: source["target_equivalence_exclusion"].update(
            source_stable_full_scan_sha256="unlinked"
        ),
        lambda source: (
            source["target_equivalence_exclusion"]["resolved_rows"].clear(),
            source["target_equivalence_exclusion"].update(
                target_rows_resolved=0,
                content_sha256=[],
                extraction_sha256=[],
            ),
        ),
        lambda source: source["items"][0].update(excerpt="tampered excerpt"),
        lambda source: source["items"][0]["evidence_unit_manifest"][0].update(
            content_sha256="tampered"
        ),
    ],
)
def test_source_contract_rejects_rehashed_overlap_receipt_or_manifest_drift(
    tmp_path, monkeypatch, mutation
):
    source = _source_contract_fixture(tmp_path, monkeypatch)
    mutation(source)
    source.pop("packet_sha256")
    source["packet_sha256"] = s197.stable_sha(source)
    with pytest.raises(RuntimeError, match="source contract|manifest drift"):
        s197.source_contract(source)


class _Usage:
    def __init__(self, *, input_tokens=100, output_tokens=80):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def model_dump(self, *, mode):
        assert mode == "json"
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class _AuthorMessages:
    def __init__(self, events, lock, prepaid):
        self.events = events
        self.lock = lock
        self.prepaid = prepaid

    def count_tokens(self, **kwargs):
        assert self.lock.exists()
        assert kwargs["output_config"]["format"]["type"] == "json_schema"
        self.events.append("author_preflight")
        return SimpleNamespace(input_tokens=100)

    def create(self, **kwargs):
        assert self.prepaid.exists()
        prompt = json.loads(kwargs["messages"][0]["content"])
        unit_ids = prompt["allowed_support_unit_ids"]
        payload = {
            "item_id": prompt["item_id"],
            "eligible": True,
            "question": "¿Qué debe hacerse antes y después del servicio?",
            "answer_point_slots": {
                "point_1": _point(
                    active=True,
                    claim="Aislar la alimentación antes del servicio.",
                    facet=FACETS[0],
                    supports=(unit_ids[0], "", ""),
                ),
                "point_2": _point(
                    active=True,
                    claim="Reponer la protección después del servicio.",
                    facet=FACETS[3],
                    supports=(unit_ids[-1], "", ""),
                ),
                "point_3": _point(active=False),
                "point_4": _point(active=False),
            },
        }
        self.events.append("author_inference")
        return SimpleNamespace(
            id=f"msg_{prompt['item_id']}",
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(payload))],
            usage=_Usage(),
        )


class _SemanticResponses:
    def __init__(self, events, author_receipts, prepaid):
        self.events = events
        self.author_receipts = author_receipts
        self.prepaid = prepaid
        self.input_tokens = SimpleNamespace(count=self.count)

    def count(self, **kwargs):
        assert self.author_receipts.exists()
        assert kwargs["reasoning"] == {"effort": "none"}
        assert kwargs["text"]["format"]["name"] == (
            "s197_external_semantic_validation"
        )
        self.events.append("semantic_preflight")
        return SimpleNamespace(input_tokens=120)

    def create(self, **kwargs):
        assert self.prepaid.exists()
        assert kwargs["store"] is False
        item = json.loads(kwargs["input"])
        count = len(item["answer_points"])
        review = {
            "item_id": item["item_id"],
            "eligibility_correct": True,
            "eligibility_issue": "",
            "question_language_spanish": True,
            "question_language_issue": "",
            "question_natural_for_field_technician": True,
            "question_naturality_issue": "",
            "answer_points_semantically_distinct": True,
            "answer_point_distinctness_issue": "",
            "answer_points_complete_for_question_within_excerpt": True,
            "answer_point_completeness_issue": "",
            "question_answerable": True,
            "question_issue": "",
            "point_reviews": {
                f"point_{index}": (
                    {
                        "fully_supported": True,
                        "support_issue": "",
                        "facet_correct": True,
                        "facet_issue": "",
                    }
                    if index <= count
                    else None
                )
                for index in range(1, 5)
            },
        }
        self.events.append("semantic_inference")
        return SimpleNamespace(
            id=f"resp_{item['item_id']}",
            status="completed",
            output_text=json.dumps(review),
            usage=_Usage(input_tokens=120, output_tokens=60),
        )


def _execution_prereg():
    return {
        "models": s197.EXPECTED_MODELS,
        "sdk": s197.EXPECTED_SDK,
        "pricing_usd_per_million_tokens": s197.EXPECTED_PRICING,
        "budget": s197.EXPECTED_BUDGET,
        "validation": s197.EXPECTED_VALIDATION,
        "static_transport_schema_sha256": s197.stable_sha(
            s197.static_transport_schema()
        ),
    }


def test_operational_path_is_lock_author_then_luna_with_no_retries(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "items": [
                    _row(index, stratum="table" if index <= 7 else "prose")
                    for index in range(1, 15)
                ]
            }
        ),
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=anthropic-test\nOPENAI_API_KEY=openai-test\n",
        encoding="utf-8",
    )
    paths = {
        "DEFAULT_LOCK": tmp_path / "lock.json",
        "DEFAULT_AUTHOR_PREPAID": tmp_path / "author-prepaid.json",
        "DEFAULT_AUTHOR_RECEIPTS": tmp_path / "author-receipts.json",
        "DEFAULT_SEMANTIC_PREPAID": tmp_path / "semantic-prepaid.json",
        "DEFAULT_SEMANTIC_RECEIPTS": tmp_path / "semantic-receipts.json",
        "DEFAULT_COHORT": tmp_path / "cohort.json",
        "DEFAULT_RESULT": tmp_path / "result.json",
    }
    monkeypatch.setattr(s197, "SOURCE", source)
    monkeypatch.setattr(s197, "source_contract", lambda payload: None)
    for name, path in paths.items():
        monkeypatch.setattr(s197, name, path)
    events = []

    def author_factory(*, api_key, max_retries):
        assert api_key == "anthropic-test"
        assert max_retries == 0
        assert paths["DEFAULT_LOCK"].exists()
        events.append("author_factory")
        return SimpleNamespace(
            messages=_AuthorMessages(
                events,
                paths["DEFAULT_LOCK"],
                paths["DEFAULT_AUTHOR_PREPAID"],
            )
        )

    def semantic_factory(*, api_key, max_retries):
        assert api_key == "openai-test"
        assert max_retries == 0
        assert paths["DEFAULT_LOCK"].exists()
        events.append("semantic_factory")
        return SimpleNamespace(
            responses=_SemanticResponses(
                events,
                paths["DEFAULT_AUTHOR_RECEIPTS"],
                paths["DEFAULT_SEMANTIC_PREPAID"],
            )
        )

    result = s197.execute(
        _execution_prereg(),
        env_file,
        author_client_factory=author_factory,
        semantic_client_factory=semantic_factory,
    )
    assert result["status"] == "GO_STATIC_AUTHOR_LUNA_SCREENED_COHORT_SEALED"
    assert events[:2] == ["author_factory", "semantic_factory"]
    assert events[2:16] == ["author_preflight"] * 14
    assert events[16:30] == ["author_inference"] * 14
    assert events[30:44] == ["semantic_preflight"] * 14
    assert events[44:] == ["semantic_inference"] * 14
    assert result["excerpt_screening"]["model"] == "gpt-5.6-luna"
    assert result["excerpt_screening"]["frontier_execution_calls"] == 0
    assert result["excerpt_screening"]["scope"] == (
        "CROSS_PROVIDER_EXCERPT_INTERNAL"
    )
    assert result["excerpt_screening"]["document_wide_completeness"] == (
        "NOT_MEASURED"
    )
    assert result["excerpt_screening"]["semantic_correctness_claim"] == (
        "SCREEN_ONLY_NOT_GOLD_AUTHORITY"
    )
    assert result["decision"]["next_action"] == (
        "AUTHORIZE_SEPARATE_S198_PREREGISTRATION"
    )
    assert result["decision"]["s198_handoff_constraints"]["status"] == (
        "HEADLINE_CONSTRAINTS_REQUIRE_S198_PREREGISTERED_DEFINITIONS"
    )
    cohort = json.loads(paths["DEFAULT_COHORT"].read_text(encoding="utf-8"))
    assert len(cohort["semantic_reviews"]) == 14
    assert cohort["semantic_receipts_sha256"] == s197.file_sha(
        paths["DEFAULT_SEMANTIC_RECEIPTS"]
    )
    semantic_receipts = json.loads(
        paths["DEFAULT_SEMANTIC_RECEIPTS"].read_text(encoding="utf-8")
    )
    assert all(
        receipt["authored_item_sha256"]
        and receipt["semantic_input_sha256"]
        and receipt["semantic_output_schema_sha256"]
        for receipt in semantic_receipts["receipts"]
    )
    source_items = json.loads(source.read_text(encoding="utf-8"))["items"]
    units_by = {row["item_id"]: s197.verified_units(row) for row in source_items}
    assert s197.semantic_receipts_bound(
        semantic_receipts["receipts"],
        cohort["items"],
        cohort["semantic_reviews"],
        units_by,
    )
    tampered_receipts = copy.deepcopy(semantic_receipts["receipts"])
    tampered_receipts[0]["semantic_input_sha256"] = "tampered"
    assert not s197.semantic_receipts_bound(
        tampered_receipts,
        cohort["items"],
        cohort["semantic_reviews"],
        units_by,
    )
    with pytest.raises(RuntimeError, match="checkpoint exists"):
        s197.execute(
            _execution_prereg(),
            env_file,
            author_client_factory=author_factory,
            semantic_client_factory=semantic_factory,
        )


def test_budget_failure_after_author_execution_is_atomically_sealed(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(s197, "ROOT", tmp_path)
    paths = {
        "DEFAULT_LOCK": tmp_path / "lock.json",
        "DEFAULT_AUTHOR_PREPAID": tmp_path / "author-prepaid.json",
        "DEFAULT_AUTHOR_RECEIPTS": tmp_path / "author-receipts.json",
        "DEFAULT_SEMANTIC_PREPAID": tmp_path / "semantic-prepaid.json",
        "DEFAULT_SEMANTIC_RECEIPTS": tmp_path / "semantic-receipts.json",
        "DEFAULT_COHORT": tmp_path / "cohort.json",
        "DEFAULT_RESULT": tmp_path / "result.json",
    }
    for name, path in paths.items():
        monkeypatch.setattr(s197, name, path)
    paths["DEFAULT_LOCK"].write_text("{}\n", encoding="utf-8")
    paths["DEFAULT_AUTHOR_RECEIPTS"].write_text(
        '{"status":"COMPLETE"}\n', encoding="utf-8"
    )
    result = s197.seal_failure(
        "NO_GO_SEMANTIC_BUDGET_AFTER_AUTHOR_EXECUTION",
        RuntimeError("preflight exceeds budget"),
        stage="semantic_preflight_budget",
        known_failure=False,
    )
    assert paths["DEFAULT_RESULT"].exists()
    assert result["status"] == "NO_GO_SEMANTIC_BUDGET_AFTER_AUTHOR_EXECUTION"
    assert result["cost"]["status"] == "PARTIAL_SEE_CHECKPOINT_RECEIPTS"
    assert set(result["failure"]["completed_checkpoint_artifacts"]) == {
        "lock.json",
        "author-receipts.json",
    }


def test_unhandled_client_constructor_failure_after_new_lock_is_sealed(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(s197, "ROOT", tmp_path)
    lock = tmp_path / "lock.json"
    result_path = tmp_path / "result.json"
    monkeypatch.setattr(s197, "DEFAULT_LOCK", lock)
    monkeypatch.setattr(s197, "DEFAULT_RESULT", result_path)
    monkeypatch.setattr(s197, "DEFAULT_AUTHOR_PREPAID", tmp_path / "author-prepaid.json")
    monkeypatch.setattr(s197, "DEFAULT_AUTHOR_RECEIPTS", tmp_path / "author-receipts.json")
    monkeypatch.setattr(
        s197, "DEFAULT_SEMANTIC_PREPAID", tmp_path / "semantic-prepaid.json"
    )
    monkeypatch.setattr(
        s197, "DEFAULT_SEMANTIC_RECEIPTS", tmp_path / "semantic-receipts.json"
    )
    monkeypatch.setattr(s197, "DEFAULT_COHORT", tmp_path / "cohort.json")

    def fail_after_lock(*args, **kwargs):
        s197.write_json_exclusive(
            lock,
            {
                "status": "LOCKED",
                "execution_owner_token": kwargs["execution_owner_token"],
            },
        )
        raise RuntimeError("client constructor failed")

    monkeypatch.setattr(s197, "_execute_once", fail_after_lock)
    result = s197.execute({}, tmp_path / ".env")
    assert result["status"] == "HOLD_UNEXPECTED_EXCEPTION_AFTER_LOCK"
    assert result_path.exists()


def test_lock_race_loser_never_seals_the_winners_execution(tmp_path, monkeypatch):
    lock = tmp_path / "lock.json"
    result_path = tmp_path / "result.json"
    monkeypatch.setattr(s197, "DEFAULT_LOCK", lock)
    monkeypatch.setattr(s197, "DEFAULT_RESULT", result_path)

    def lose_race(*args, **kwargs):
        s197.write_json_exclusive(
            lock,
            {"execution_owner_token": "winner-token"},
        )
        raise FileExistsError("lost exclusive lock race")

    monkeypatch.setattr(s197, "_execute_once", lose_race)
    with pytest.raises(FileExistsError, match="lost exclusive lock race"):
        s197.execute({}, tmp_path / ".env")
    assert not result_path.exists()
