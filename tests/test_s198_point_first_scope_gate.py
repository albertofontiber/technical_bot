from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

import scripts.s198_point_first_scope_gate as s198
from scripts.s196_static_transport_canary import static_transport_schema
from src.rag.evidence_units_v2 import build_header_aware_evidence_units


def _point(active, claim="", facet="", supports=("", "", "")):
    return {
        "active": active,
        "claim": claim,
        "facet": facet,
        "support_1": supports[0],
        "support_2": supports[1],
        "support_3": supports[2],
    }


def _source_item(index=1, stratum="table"):
    return {
        "item_id": f"s198e_src_{index:02d}",
        "stratum": stratum,
        "manufacturer": f"Vendor {index}",
        "product_model": f"Model {index}",
        "document_id": f"doc-{index}",
        "chunk_id": f"chunk-{index}",
        "excerpt_sha256": "unused-by-mocked-source-contract",
        "excerpt": "Desconecte la alimentación.\n\nReinstale la cubierta antes de arrancar.",
    }


def _units(item):
    return build_header_aware_evidence_units(
        item["excerpt"], fragment_number=1, candidate_id=item["item_id"]
    )


def _valid_point_payload(item):
    unit_ids = [unit.unit_id for unit in _units(item)]
    return {
        "item_id": item["item_id"],
        "eligible": True,
        "question": "",
        "answer_point_slots": {
            "point_1": _point(
                True,
                "Desconecte la alimentación.",
                "access_or_prerequisite",
                (unit_ids[0], "", ""),
            ),
            "point_2": _point(
                True,
                "Reinstale la cubierta antes de arrancar.",
                "verification_commissioning_or_recovery",
                (unit_ids[1], "", ""),
            ),
            "point_3": _point(False),
            "point_4": _point(False),
        },
    }


def _normalized_item(index=1, stratum="table"):
    source = _source_item(index, stratum)
    return s198.normalize_point_author(_valid_point_payload(source), source, _units(source))


def _valid_point_review(item):
    point_review = {
        "atomic_claim": True,
        "atomicity_issue": "",
        "fully_supported": True,
        "support_issue": "",
        "support_relevant_and_sufficient": True,
        "support_relevance_issue": "",
        "facet_correct": True,
        "facet_issue": "",
        "materially_useful": True,
        "materiality_issue": "",
    }
    return {
        "item_id": item["item_id"],
        "eligibility_correct": True,
        "eligibility_issue": "",
        "points_semantically_distinct": True,
        "distinctness_issue": "",
        "set_materially_useful": True,
        "set_materiality_issue": "",
        "set_coherent": True,
        "coherence_issue": "",
        "set_nontrivial": True,
        "nontriviality_issue": "",
        "point_reviews": {
            "point_1": copy.deepcopy(point_review),
            "point_2": copy.deepcopy(point_review),
            "point_3": None,
            "point_4": None,
        },
    }


def _valid_question_review(item):
    return {
        "item_id": item["item_id"],
        **{
            key: value
            for flag in s198.QUESTION_SCREEN_FLAGS
            for key, value in ((flag, True), (f"{flag}_issue", ""))
        },
    }


def test_point_author_reuses_static_schema_but_requires_empty_question():
    item = _source_item()
    payload = _valid_point_payload(item)
    normalized = s198.normalize_point_author(payload, item, _units(item))
    assert normalized["question"] == ""
    assert len(normalized["answer_points"]) == 2
    assert static_transport_schema()["required"] == [
        "item_id",
        "eligible",
        "question",
        "answer_point_slots",
    ]
    payload["question"] = "¿Pregunta prematura?"
    with pytest.raises(ValueError, match="exact empty string"):
        s198.normalize_point_author(payload, item, _units(item))


def test_facet_contract_is_exhaustive_and_frozen_in_precedence_order():
    assert set(s198.FACET_PRECEDENCE) == set(s198.FACET_DEFINITIONS)
    assert s198.FACET_PRECEDENCE[:3] == (
        "safety_warning_exception_or_conflict",
        "verification_commissioning_or_recovery",
        "output_action_or_corrective_step",
    )
    assert s198.FACET_PRECEDENCE[-1] == "input_trigger_or_observed_condition"
    assert "two to four atomic" in s198.ELIGIBILITY_DEFINITION
    assert s198.EXPECTED_EXECUTION["paid_calls_max"] == 48
    assert s198.EXPECTED_EXECUTION["provider_requests_max"] == 96


def test_actual_exhaustion_aware_packet_passes_the_full_source_contract():
    packet = json.loads(s198.SOURCE.read_text(encoding="utf-8"))
    s198.source_contract(packet)
    assert packet["selection"]["population_contract"] == (
        "EXHAUSTION_AWARE_7_TABLE_5_PROSE"
    )
    assert packet["eligible_inventory"]["post_selection_reserve_definition"].endswith(
        "not a future manufacturer-disjoint cohort capacity claim"
    )


def test_question_writer_is_claim_only_while_final_screen_restores_excerpt():
    item = _normalized_item()
    writer = json.loads(s198.question_writer_prompt(item))
    assert set(writer) == {
        "item_id",
        "bound_product",
        "accepted_points",
        "question_contract",
    }
    assert "excerpt" not in json.dumps(writer)
    assert "support_unit_ids" not in json.dumps(writer)
    item["question"] = "¿Qué pasos deben realizarse antes y después del mantenimiento?"
    screen = json.loads(s198.question_screen_payload(item, _units(_source_item())))
    assert screen["complete_evidence_units"]
    assert screen["accepted_points"][0]["support_unit_ids"]


def test_semantic_review_validators_reject_issue_contradictions():
    item = _normalized_item()
    review = _valid_point_review(item)
    assert s198.point_screen_passes(s198.validate_point_screen(review, item))
    review["point_reviews"]["point_1"]["facet_issue"] = "issue despite true"
    with pytest.raises(ValueError, match="contradiction"):
        s198.validate_point_screen(review, item)
    item["question"] = "¿Qué pasos deben realizarse antes y después del mantenimiento?"
    qreview = _valid_question_review(item)
    assert s198.question_screen_passes(s198.validate_question_screen(qreview, item))
    qreview["scope_not_widened"] = False
    with pytest.raises(ValueError, match="contradiction"):
        s198.validate_question_screen(qreview, item)


def test_population_gate_uses_the_preregistered_denominator():
    items = [
        _normalized_item(index, "table" if index <= 7 else "prose")
        for index in range(1, 13)
    ]
    checks = s198.population_checks(items, 0, s198.EXPECTED_VALIDATION)
    assert all(checks.values())
    items[-1]["eligible"] = False
    items[-1]["answer_points"] = []
    reduced = s198.population_checks(items, 0, s198.EXPECTED_VALIDATION)
    assert reduced["eligible_items_gte_12"] is False
    assert reduced["prose_items_gte_5"] is False
    assert reduced["answer_points_gte_24"] is False
    assert not s198.population_checks(items, 1, s198.EXPECTED_VALIDATION)[
        "invalid_point_author_outputs_zero"
    ]


class _Usage:
    def model_dump(self, *, mode):
        assert mode == "json"
        return {"input_tokens": 100, "output_tokens": 50}


class _AnthropicMessages:
    def __init__(self, events, writer_inputs):
        self.events = events
        self.writer_inputs = writer_inputs

    def count_tokens(self, **kwargs):
        self.events.append("anthropic_preflight")
        return SimpleNamespace(input_tokens=100)

    def create(self, **kwargs):
        payload = json.loads(kwargs["messages"][0]["content"])
        if kwargs["system"] == s198.POINT_AUTHOR_SYSTEM:
            item = _source_item(int(payload["item_id"].rsplit("_", 1)[1]))
            output = _valid_point_payload(item)
            stage = "point_author"
        else:
            self.writer_inputs.append(payload)
            output = {
                "item_id": payload["item_id"],
                "question": "¿Qué pasos deben realizarse antes y después del mantenimiento?",
            }
            stage = "question_writer"
        self.events.append(stage)
        return SimpleNamespace(
            id=f"msg_{stage}_{payload['item_id']}",
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(output))],
            usage=_Usage(),
        )


class _Responses:
    def __init__(self, events, screen_inputs):
        self.events = events
        self.screen_inputs = screen_inputs
        self.input_tokens = SimpleNamespace(count=self.count)

    def count(self, **kwargs):
        self.events.append("openai_preflight")
        return SimpleNamespace(input_tokens=100)

    def create(self, **kwargs):
        payload = json.loads(kwargs["input"])
        if kwargs["instructions"] == s198.POINT_SCREEN_SYSTEM:
            source = _source_item(int(payload["item_id"].rsplit("_", 1)[1]))
            item = s198.normalize_point_author(
                _valid_point_payload(source), source, _units(source)
            )
            output = _valid_point_review(item)
            stage = "point_screen"
        else:
            item = _normalized_item(int(payload["item_id"].rsplit("_", 1)[1]))
            item["question"] = payload["question"]
            output = _valid_question_review(item)
            stage = "question_screen"
        self.screen_inputs.append((stage, payload))
        self.events.append(stage)
        return SimpleNamespace(
            id=f"resp_{stage}_{payload['item_id']}",
            status="completed",
            output_text=json.dumps(output),
            usage=_Usage(),
        )


def _mock_source():
    items = [
        _source_item(index, "table" if index <= 7 else "prose")
        for index in range(1, 13)
    ]
    return {
        "items": items,
        "eligible_inventory": {
            "counts": {"documents": 30, "manufacturers": 20},
            "selected_identities": [{"item_id": item["item_id"]} for item in items],
            "post_selection_reserve": {"documents": 16, "manufacturers": 6},
        },
    }


def _isolate_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(s198, "ROOT", tmp_path)
    source = tmp_path / "source.json"
    source.write_text(json.dumps(_mock_source()), encoding="utf-8")
    monkeypatch.setattr(s198, "SOURCE", source)
    names = [
        "DEFAULT_LOCK",
        "DEFAULT_POINT_AUTHOR_PREPAID",
        "DEFAULT_POINT_AUTHOR_RECEIPTS",
        "DEFAULT_POINT_SCREEN_PREPAID",
        "DEFAULT_POINT_SCREEN_RECEIPTS",
        "DEFAULT_QUESTION_WRITER_PREPAID",
        "DEFAULT_QUESTION_WRITER_RECEIPTS",
        "DEFAULT_QUESTION_SCREEN_PREPAID",
        "DEFAULT_QUESTION_SCREEN_RECEIPTS",
        "DEFAULT_COHORT",
        "DEFAULT_RESULT",
    ]
    paths = {}
    for name in names:
        path = tmp_path / f"{name.lower()}.json"
        paths[name] = path
        monkeypatch.setattr(s198, name, path)
    monkeypatch.setattr(s198, "OUTPUT_PATHS", tuple(paths[name] for name in names))
    monkeypatch.setattr(s198, "source_contract", lambda value: None)
    monkeypatch.setattr(s198, "verified_units", _units)
    monkeypatch.setattr(s198.importlib.metadata, "version", lambda name: s198.EXPECTED_SDK[name])
    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=a\nOPENAI_API_KEY=o\n", encoding="utf-8")
    return paths, env


def _prereg():
    return {
        "models": s198.EXPECTED_MODELS,
        "sdk": s198.EXPECTED_SDK,
        "pricing_usd_per_million_tokens": s198.EXPECTED_PRICING,
        "budget": s198.EXPECTED_BUDGET,
        "validation": s198.EXPECTED_VALIDATION,
    }


def test_full_mocked_package_orders_48_calls_and_seals_go(tmp_path, monkeypatch):
    paths, env = _isolate_execution(tmp_path, monkeypatch)
    events = []
    writer_inputs = []
    screen_inputs = []

    def anthropic_factory(*, api_key, max_retries):
        assert (api_key, max_retries) == ("a", 0)
        return SimpleNamespace(messages=_AnthropicMessages(events, writer_inputs))

    def openai_factory(*, api_key, max_retries):
        assert (api_key, max_retries) == ("o", 0)
        return SimpleNamespace(responses=_Responses(events, screen_inputs))

    result = s198.execute(
        _prereg(),
        env,
        anthropic_client_factory=anthropic_factory,
        openai_client_factory=openai_factory,
    )
    assert result["status"] == "GO_POINT_FIRST_SCOPE_BOUND_COHORT_SEALED"
    assert result["decision"]["downstream_planner_opened"] is False
    assert result["decision"]["diagnostic_facts_moved_to_ok"] == 0
    assert events.count("point_author") == 12
    assert events.count("point_screen") == 12
    assert events.count("question_writer") == 12
    assert events.count("question_screen") == 12
    assert events.count("anthropic_preflight") == 24
    assert events.count("openai_preflight") == 24
    assert all("excerpt" not in json.dumps(payload) for payload in writer_inputs)
    assert all(
        payload["complete_evidence_units"]
        for stage, payload in screen_inputs
        if stage == "question_screen"
    )
    assert paths["DEFAULT_RESULT"].exists()
    assert paths["DEFAULT_COHORT"].exists()
    assert result["chunks_v3_lane"]["status"] == "FINAL_NO_GO_CHUNKS_V3_WHOLESALE"


def test_existing_lock_blocks_before_client_construction(tmp_path, monkeypatch):
    paths, env = _isolate_execution(tmp_path, monkeypatch)
    paths["DEFAULT_LOCK"].write_text("{}", encoding="utf-8")

    def forbidden(**kwargs):
        raise AssertionError("clients must not be constructed")

    with pytest.raises(RuntimeError, match="checkpoint exists"):
        s198.execute(
            _prereg(),
            env,
            anthropic_client_factory=forbidden,
            openai_client_factory=forbidden,
        )
