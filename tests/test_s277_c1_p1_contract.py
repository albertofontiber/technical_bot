from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator
from scripts import s277_c1_p1 as p1
from scripts import s277_c1_p1_scorer as scorer


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "evals" / "s277_c1_p1_fact_contract_v1.json"
PREREG_PATH = ROOT / "evals" / "s277_c1_p1_prereg_v1.yaml"
RELEASE_SCHEMA_PATH = ROOT / "evals" / "s277_c1_p1_release_config_schema_v1.json"
BUILDER_PATH = ROOT / "scripts" / "s277_build_c1_p1_contract.py"


def _builder():
    spec = importlib.util.spec_from_file_location("s277_build_c1_p1_contract", BUILDER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_contract_rebuilds_byte_semantically_from_frozen_authorities():
    builder = _builder()
    stored = _json(CONTRACT_PATH)
    rebuilt = builder.build_fact_contract()

    assert rebuilt == stored
    payload = dict(stored)
    expected = payload.pop("payload_sha256")
    assert builder.object_sha256(payload) == expected

    receipts = stored["authority"]["source_file_receipts"]
    assert receipts
    for receipt in receipts:
        raw = (ROOT / receipt["path"]).read_bytes()
        assert set(receipt) == {"path", "sha256_lf"}
        assert hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == receipt["sha256_lf"]


def test_lf_receipts_are_cross_platform_and_raw_hashes_are_not_authoritative():
    builder = _builder()
    lf = b"first\nsecond\n"
    crlf = b"first\r\nsecond\r\n"
    assert builder.sha256_lf_bytes(lf) == builder.sha256_lf_bytes(crlf)

    prereg = _yaml(PREREG_PATH)
    sealed = prereg["sealed_inputs"]
    assert "sha256_raw" not in sealed["fact_contract"]
    assert "sha256_raw" not in sealed["release_config_schema"]
    assert "sha256_lf" in sealed["fact_contract"]
    assert "sha256_lf" in sealed["release_config_schema"]


def test_exact_43_row_population_and_machine_readable_transform_diff():
    contract = _json(CONTRACT_PATH)
    facts = contract["protected_facts"]
    population = contract["population"]

    assert population["historical_s113_ok_count"] == 42
    assert population["expected_base_fact_count"] == 43
    assert population["actual_base_fact_count"] == 43
    assert len(facts) == 43
    assert len({fact["fact_id"] for fact in facts}) == 43
    assert population["per_qid_base_counts"] == {
        "cat001": 5,
        "cat017": 4,
        "cat018": 1,
        "cat019": 4,
        "hp002": 4,
        "hp003": 4,
        "hp005": 4,
        "hp011": 1,
        "hp012": 4,
        "hp013": 0,
        "hp014": 4,
        "hp017": 3,
        "hp018": 5,
    }

    by_id = {fact["fact_id"]: fact for fact in facts}
    assert "hp017#1:instruccion de entrada" not in by_id
    assert by_id["hp017#2:Editar Configuracion"]["release_guard_only"] is True
    assert by_id["hp017#2:Editar Configuracion"]["kpi_weight"] == 0
    assert by_id["hp017#3:disclosure_DEC128"]["algorithm"] == "hp017_delay_disclosure_v1"
    assert by_id["hp002#banked:obl_b6f6211be439"]["binding_level"] == "accepted_exact_span"
    assert sum(fact["kpi_weight"] for fact in facts) == 42

    operations = contract["transformation_diff"]["operations"]
    assert [operation["operation"] for operation in operations] == [
        "exclude_historical_fact",
        "add_release_guard_only",
        "replace_fact_in_place",
        "add_live_banked_fact",
    ]
    assert contract["transformation_diff"]["result_count"] == 43


def test_every_fact_has_closed_scoring_and_source_contract():
    builder = _builder()
    contract = _json(CONTRACT_PATH)
    allowed_algorithms = {
        "protected_fact_surface_v1",
        "hp011_rearme_inhibido_v1",
        "hp017_delay_disclosure_v1",
    }
    for fact in contract["protected_facts"]:
        assert fact["algorithm"] in allowed_algorithms
        assert fact["statement"]
        assert len(fact["statement_sha256"]) == 64
        assert fact["clauses"]["required"]
        assert fact["surface_forms"]["required_all_groups"]
        assert all(group for group in fact["surface_forms"]["required_all_groups"])
        assert fact["citation_policy"]["mode"] == "valid_local_citation_required"
        assert fact["binding_level"] in {"gold_verified_page", "accepted_exact_span"}
        assert fact["manual_id"]
        assert fact["pages"]
        assert fact["source_refs"]
        for source in fact["source_refs"]:
            assert {"chunk_id", "source_file", "page"} <= set(source)
            assert source["source_file"]
            assert source["page"] is not None
            if source.get("quote_sha256"):
                assert source.get("quote_text")
                assert (
                    builder.normalized_sha256(source["quote_text"])
                    == source["quote_sha256"]
                )
        if fact["binding_level"] == "accepted_exact_span":
            assert isinstance(fact["source_start"], int)
            assert isinstance(fact["source_end"], int)
            assert len(fact["source_span_sha256"]) == 64
        else:
            assert fact["source_start"] is None
            assert fact["source_end"] is None
            assert fact["source_span_sha256"] is None


def test_hp018_is_reanchored_only_to_mie_mi_530_pages_20_and_21():
    contract = _json(CONTRACT_PATH)
    hp018 = {
        fact["fact_id"]: fact
        for fact in contract["protected_facts"]
        if fact["qid"] == "hp018"
    }
    expected = {
        "hp018#0:4 circuitos": ("90d51dac-bd0b-4051-b414-ced0fe6e33bb", 20),
        "hp018#1:6K8": ("90d51dac-bd0b-4051-b414-ced0fe6e33bb", 20),
        "hp018#2:diodo": ("72fc4c53-f507-4e67-9192-ebc68b94be78", 21),
        "hp018#3:Sirenas A,B,C,D": ("72fc4c53-f507-4e67-9192-ebc68b94be78", 21),
        "hp018#4:1 A": ("90d51dac-bd0b-4051-b414-ced0fe6e33bb", 20),
    }
    assert set(hp018) == set(expected)
    for fact_id, fact in hp018.items():
        expected_chunk, expected_page = expected[fact_id]
        assert {source["chunk_id"] for source in fact["source_refs"]} == {expected_chunk}
        assert {source["source_file"] for source in fact["source_refs"]} == {"MIE-MI-530rv001"}
        assert {source["page"] for source in fact["source_refs"]} == {expected_page}
        assert "MIE-MI-310" not in json.dumps(fact, ensure_ascii=False)

    # A citation to the other physical page is not accredited for this fact.
    assert all(
        source["chunk_id"] != "72fc4c53-f507-4e67-9192-ebc68b94be78"
        for source in hp018["hp018#1:6K8"]["source_refs"]
    )


def test_historical_source_refs_are_derived_from_each_atomic_fact_cita():
    builder = _builder()
    contract = _json(CONTRACT_PATH)
    gold_rows = _yaml(ROOT / "evals" / "gold_answers_v1.yaml")
    gold = {row["qid"]: row for row in gold_rows}
    source_by_hash = {
        builder.object_sha256(source): (qid, source)
        for qid, row in gold.items()
        for source in builder.historical_core_facts(row)
    }

    checked = 0
    for fact in contract["protected_facts"]:
        parent_hash = fact.get("parent_fact_sha256")
        if fact["qid"] == "hp018" or parent_hash not in source_by_hash:
            continue
        if fact["fact_id"] in {
            "hp017#2:Editar Configuracion",
            "hp017#3:disclosure_DEC128",
        }:
            continue
        qid, source_fact = source_by_hash[parent_hash]
        assert qid == fact["qid"]
        assert fact["source_refs"] == builder.fact_source_refs(gold[qid], source_fact)
        assert all(ref["atomic_cita"] == source_fact["cita"] for ref in fact["source_refs"])
        checked += 1
    assert checked == 35

    by_id = {fact["fact_id"]: fact for fact in contract["protected_facts"]}
    cat001_current = by_id["cat001#1:0,75 A"]
    assert {(ref["source_file"], ref["page"]) for ref in cat001_current["source_refs"]} == {
        ("997-669-005-3_Instal-Comm_ES.pdf", 51)
    }
    assert ("997-671-005-3_Configuration_ES.pdf", 20) not in {
        (ref["source_file"], ref["page"]) for ref in cat001_current["source_refs"]
    }


def test_bare_value_and_cross_page_citation_mutations_cannot_pass():
    contract = _json(CONTRACT_PATH)
    facts = {fact["fact_id"]: fact for fact in contract["protected_facts"]}
    current = facts["cat001#1:0,75 A"]
    quote = next(
        ref["quote_text"] for ref in current["source_refs"] if ref.get("quote_text")
    )
    correct_page = [{
        "id": "cat001-p51",
        "source_file": "997-669-005-3_Instal-Comm_ES.pdf",
        "page_number": 51,
        "content": quote,
    }]
    bare = scorer.score_protected_fact("La salida admite 0,75 A [F1].", correct_page, current)
    assert bare.status == scorer.REVIEW
    relational = scorer.score_protected_fact(
        f'{current["statement"]} [F1].', correct_page, current
    )
    assert relational.status == scorer.PASS

    wrong_page = [{
        "id": "cat001-p20",
        "source_file": "997-671-005-3_Configuration_ES.pdf",
        "page_number": 20,
        "content": "La carga maxima del lazo es de 0,75 A.",
    }]
    crossed = scorer.score_protected_fact(
        f'{current["statement"]} [F1].', wrong_page, current
    )
    assert crossed.status == scorer.FAIL

    eol = facts["hp018#1:6K8"]
    hp018_wrong_page = [{
        "id": "72fc4c53-f507-4e67-9192-ebc68b94be78",
        "source_file": "MIE-MI-530rv001",
        "page_number": 21,
        "content": "RFL 6K8, 0,5 W al final del circuito para supervision.",
    }]
    crossed_hp018 = scorer.score_protected_fact(
        f'{eol["statement"]} [F1].',
        hp018_wrong_page,
        eol,
    )
    assert crossed_hp018.status == scorer.FAIL


def test_hp017_target_identity_and_both_physical_spans_are_exact():
    contract = _json(CONTRACT_PATH)
    target = contract["c1_target"]
    freeze = _json(ROOT / "evals" / "s113_full_contexts_freeze_v1.json")
    chunk = _builder().find_freeze_chunk(freeze, target["target_id"])
    content = chunk["content"]

    assert target["compound_obligation_ids"] == ["obl_16637b935bd4", "obl_0d6a30948dfd"]
    assert target["required_replicas"] == target["required_passes"] == 3
    assert target["target_identity"]["manufacturer"] is None
    assert "manufacturer" not in target["target_identity"]["required_identity_fields"]
    assert hashlib.sha256(content.encode("utf-8")).hexdigest() == target["target_identity"]["content_sha256"]
    for clause in target["clauses"]:
        span = content[clause["source_start"] : clause["source_end"]]
        assert clause["exact_text"] in span
        assert hashlib.sha256(span.encode("utf-8")).hexdigest() == clause["source_span_sha256"]


def test_hp013_guard_exists_despite_zero_protected_facts():
    contract = _json(CONTRACT_PATH)
    assert not [fact for fact in contract["protected_facts"] if fact["qid"] == "hp013"]
    guards = [guard for guard in contract["question_guards"] if guard["qid"] == "hp013"]
    assert len(guards) == 1
    guard = guards[0]
    assert guard["algorithm"] == "hp013_safety_guard_v1"
    assert guard["safety_guard_only"] is True
    assert guard["not_a_regression_fact"] is True
    assert guard["kpi_weight"] == 0


def test_hp017_menu_conflict_is_preexisting_hard_negative_not_positive_fact():
    contract = _json(CONTRACT_PATH)
    conflicts = contract["registered_conflicts"]
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict["conflict_id"] == "conf_26f63590494f"
    assert conflict["values"] == ["7", "8"]
    assert conflict["preexisting"] is True
    assert conflict["stored_prior_label"] == "HOLD_PREPAID_KNOWN_CONFLICT_RISK"
    assert contract["exclusions"]["flat_hp017_menu_number"] == "registered_conflict_not_positive_requirement"


def test_prereg_rebuilds_and_seals_questions_models_and_27_replica_order():
    builder = _builder()
    contract = _json(CONTRACT_PATH)
    schema = _json(RELEASE_SCHEMA_PATH)
    stored = _yaml(PREREG_PATH)
    assert builder.build_prereg(contract, schema) == stored

    assert stored["status"] == "PREREGISTERED_OFFLINE_EXECUTION_NOT_AUTHORIZED"
    assert stored["population"]["replica_count"] == 27
    assert len(stored["population"]["replica_order"]) == 27
    assert len(set(stored["population"]["replica_order"])) == 27
    assert stored["population"]["replica_order"][:3] == ["hp017:r1", "hp017:r2", "hp017:r3"]
    assert stored["model_calls"]["expected"] == {
        "voyage_embedding": 27,
        "sonnet_rerank": 27,
        "sonnet_synthesis": 27,
        "total": 81,
    }
    assert stored["cost"]["list_price_cap"] == 30.0
    assert stored["cost"]["free_tier_discount"] is False
    assert stored["cost"]["inference_geo"] == "global"
    assert stored["cost"]["service_tier"] == "standard_sync"
    assert set(stored["cost"]["operations"]) == {"embedding", "rerank", "synthesis"}
    static_bound = sum(
        Decimal(operation["max_cost_usd"]) * stored["cost"]["calls_per_operation"][name]
        for name, operation in stored["cost"]["operations"].items()
    )
    assert static_bound == Decimal(stored["cost"]["static_worst_case_usd"])
    assert static_bound == Decimal("29.727") < Decimal("30.00")
    assert stored["population"]["replica_plan_sha256"] == builder.object_sha256(
        stored["population"]["replica_order"]
    )
    assert stored["release_identity"]["preserved_orthogonal_flags"] == {
        "VISUAL_ASSETS_REGISTRY": {
            "allowed_values": ["on", "off"],
            "source_path": "railway.live_snapshot.VISUAL_ASSETS_REGISTRY",
            "bootstrap_policy": "preserve_exact",
            "target_policy": "preserve_exact",
            "profile_owned": False,
        }
    }
    semantic = stored["semantic_runtime_contract"]
    assert semantic["snapshot_freshness"] == {
        "max_age_seconds": 1800,
        "future_skew_seconds": 60,
        "validated_at": "every_preflight_and_immediately_before_first_paid_call",
    }
    assert semantic["required_raw_env"] == {
        "CHUNKS_TABLE": "chunks_v2",
        "ENUNCIADOS_MULTIVECTOR": "on",
        "HYQ_TABLE": "on",
        "HYQ_PILOT_FILE": "",
        "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "add",
        "GENERATOR_SELECTION_BLOCK": "on",
        "GENERATOR_PROMPT_VARIANT": "fidelity",
        "HYDE_ENABLED": "false",
        "RERANK_TOP_K": "10",
        "LLM_MAX_TOKENS": "3500",
        "MUST_PRESERVE_CONTRACT": "on",
    }
    assert semantic["code_bound_defaults_if_absent_from_raw_env"] == {
        "RERANKER_BACKEND": "llm",
        "MERGE_STRATEGY": "stamps",
        "RERANK_PREVIEW_CHARS": "800",
        "DIVERSIFY_TIEBREAK": "off",
        "RETRIEVAL_TOP_K": 50,
        "LLM_MODEL": "claude-sonnet-4-6",
        "EMBEDDING_MODEL": "voyage-4-large",
    }
    assert len(semantic["cross_field_equalities"]) == 12

    pipeline = stored["receipt_pipeline"]
    assert pipeline["input"]["exact_keys"] == [
        "question", "target_models", "query_for_retrieval", "available_models"
    ]
    assert pipeline["generation_chain"]["stage_order"] == [
        "diagram_postprocess", "answer_planner", "must_preserve", "conflict_guard"
    ]
    assert pipeline["physical_call_envelope"]["max_retries"] == 0
    assert pipeline["physical_call_envelope"]["prompt_cache"] is False
    assert pipeline["physical_call_envelope"]["common_request_exact_keys"] == [
        "replica_key", "operation", "model", "run_genesis_sha256",
        "lineage_input_sha256", "physical_payload", "physical_payload_sha256",
        "input_tokens_upper_bound", "max_output_tokens",
    ]
    assert pipeline["physical_call_envelope"]["provider_token_overhead_reserve"] == 512
    assert pipeline["render"]["recompute_exactly_with"] == (
        "src.bot.response_formatter.format_telegram_messages(answer)"
    )
    assert pipeline["physical_call_envelope"]["reported_usage_must_be_present_nonnegative_and_within_bounds"] is True
    assert stored["wal"]["chain_fields"] == [
        "previous_event_sha256", "event_sha256"
    ]
    assert stored["wal"]["fsync_each_event"] is True

    fence = stored["corpus_fence"]
    assert fence["heartbeat_max_age_seconds"] == 30
    assert fence["declared_surface_hashes_are_live_attestation"] is False
    assert fence["live_rpc_signature_index_config_manifest_materialized"] is True
    assert fence["product_cli_stop_line"] is None
    assert fence["persistent_session_postgres_not_transaction_pooler"] is True
    assert fence["operator_ipc_boundary"] == (
        "credential_free_append_only_single_use_with_hashed_terminal_journal"
    )
    assert fence["abort_protocol"] == (
        "exact_terminal_response_recovery_or_confirmed_rollback_or_ambiguous"
    )
    assert fence["postgrest_guard"]["principal"] == "p1_readonly"
    assert fence["postgrest_guard"]["write_methods_forbidden"] is True
    assert fence["protocol"] == [
        "BEGIN_READ_COMMITTED_READ_ONLY",
        "SHARE_LOCKS_CANONICAL_ORDER_NOWAIT",
        "INITIAL_FINGERPRINT",
        "POST_INITIAL_FINGERPRINT_SESSION_RECHECK",
        "LIVE_MANIFEST_PRE",
        "POST_PRE_MANIFEST_SESSION_RECHECK",
        "27_REPLICAS_WITH_LIVE_MANIFEST_WATCH",
        "LIVE_MANIFEST_POST",
        "FRESH_HEARTBEAT_RECHECK_BEFORE_FINAL_FINGERPRINT",
        "FINAL_FINGERPRINT_UNDER_LOCK",
        "POST_FINAL_FINGERPRINT_SESSION_LOCK_WAITER_RECHECK",
        "COMMIT",
    ]
    assert fence["close_invariants"]["verified_under_lock"] is True
    assert fence["clock_skew_tolerance_seconds"] == 2
    assert fence["fingerprint_ceiling_ms"] == 120000
    assert fence["fingerprint_statement_timeout_ms"] == 130000
    timing = fence["open_close_timing_bounds"]
    assert (
        timing["server_operation_ceiling_seconds"]
        + timing["max_unchecked_block_seconds"]
        + timing["response_allowance_seconds"]
        < timing["client_timeout_seconds"]
        < timing["request_ttl_seconds"]
    )
    assert fence["close_invariants"][
        "fresh_heartbeat_required_before_final_fingerprint"
    ] is True
    assert fence["close_invariants"][
        "fingerprint_is_only_heartbeat_age_exemption_and_is_bounded"
    ] is True
    assert fence["close_invariants"][
        "fresh_session_identity_locks_and_waiters_recheck_after_final_fingerprint"
    ] is True
    assert fence["close_invariants"]["postcheck_heartbeat_fresh_at_close"] is True
    assert fence["terminal_journal"]["abort_after_observed_closed_forbidden"] is True
    assert "final_fingerprint_taken_at" in fence["close_receipt_required_fields"]
    assert "live_manifest_post_capture_sha256" in fence[
        "close_receipt_required_fields"
    ]
    assert fence["close_invariants"][
        "post_manifest_capture_hash_bound_to_close_receipt"
    ] is True

    gold = {row["qid"]: row for row in yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))}
    for row in stored["population"]["rows"]:
        question = gold[row["qid"]]["question"]
        assert row["question"] == question
        assert row["question_sha256"] == hashlib.sha256(question.encode("utf-8")).hexdigest()
        assert row["expected_target_models"]
        assert row["available_models"] is None


def test_prereg_cannot_authorize_paid_calls_or_external_mutation():
    prereg = _yaml(PREREG_PATH)
    assert prereg["authorization"] == {
        "paid_execution": False,
        "railway_mutation": False,
        "supabase_write": False,
        "deploy": False,
        "network_during_offline_commands": False,
        "later_explicit_paid_permit_required": True,
        "paid_permit_required_fields": [
            "authorization_id", "run_id", "artifact_identity_sha256",
            "release_config_sha256", "prereg_sha256", "replica_plan_sha256",
        ],
        "artifact_identity": "sha256_canonical_json(run_id,resolved_artifact_root)",
        "global_atomic_claim_outside_artifact_dir": True,
        "authorization_ledger_derivation": "artifact_root.parent/.s277_c1_p1_authorization_claims_v1",
        "authorization_ledger_root_injection_allowed": False,
        "execution_lease_derivation": "authorization_ledger/leases/{sha256(normcase(resolved_artifact_root))}.json",
        "execution_lease_acquire": "O_EXCL_before_claim_bind_and_recovery",
        "execution_lease_release": "only_after_result_persisted",
        "execution_lease_existing": "HOLD_MANUAL_RECOVERY_NO_AUTO_RECLAIM",
        "execution_lease_scope": "single_host_filesystem_only",
        "execution_lease_multi_host": "STOP_LINE_EXTERNAL_TRANSACTIONAL_LOCK_REQUIRED",
        "execution_lease_recovery_command": "NOT_IMPLEMENTED_FUTURE_REVIEW",
        "authorization_receipt_json_safe_deep_copy_and_seal": True,
        "existing_claim_requires_canonical_resume_state": [
            "calls.jsonl",
            "calls.jsonl.genesis.json",
            "calls.jsonl.claims",
            "run_genesis.json",
        ],
        "claim_resume_policy": "same_authorization_id_run_id_artifact_identity_and_genesis_only",
    }
    assert prereg["sealed_inputs"]["release_config"]["materialized"] is False
    assert prereg["sealed_inputs"]["release_config"]["hold_until_materialized"] == "HOLD_RELEASE_CONFIG_NOT_MATERIALIZED"
    assert "HOLD_PAID_EXECUTION_NOT_AUTHORIZED" in prereg["current_stop_lines"]
    assert "HOLD_LIVE_MANIFEST_NOT_CAPTURED" in prereg["current_stop_lines"]
    assert (
        "HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED"
        not in prereg["current_stop_lines"]
    )
    assert prereg["wal"]["retry_unknown_or_failed"] is False
    assert prereg["candidate_path"]["offline_replay_can_rescue_or_pass"] is False


def test_release_config_schema_is_valid_and_secret_free_by_construction():
    builder = _builder()
    stored = _json(RELEASE_SCHEMA_PATH)
    assert builder.build_release_config_schema() == stored
    Draft202012Validator.check_schema(stored)
    assert stored["properties"]["secret_fields_present"]["const"] is False
    auth = stored["properties"]["authorizations"]["properties"]
    assert all(value["const"] is False for value in auth.values())
    delete = (
        stored["properties"]["railway"]["properties"]["planned_bootstrap_patch"]
        ["properties"]["delete"]["items"]["enum"]
    )
    assert set(delete) == {
        "POST_RERANK_COVERAGE",
        "STRUCTURAL_NEIGHBOR_COVERAGE",
        "COVERAGE_MANDATORY_CALLOUT",
        "MP_MANDATORY_VERB_TRIGGER",
    }
    railway = stored["properties"]["railway"]
    assert "railway_live_snapshot_sha256" in railway["required"]
    assert "snapshot_max_age_seconds" in railway["required"]
    assert railway["properties"]["snapshot_max_age_seconds"]["const"] == 1800
    assert railway["properties"]["snapshot_future_skew_seconds"]["const"] == 60
    assert "bot_version" in stored["properties"]["candidate"]["required"]
    assert {"inference_geo", "service_tier"} <= set(
        stored["properties"]["models"]["required"]
    )
    safe_names = railway["properties"]["live_snapshot"]["propertyNames"]
    name_validator = Draft202012Validator(safe_names)
    assert name_validator.is_valid("MP_DISTINCTIVE_TOKEN")
    assert not name_validator.is_valid("ANTHROPIC_API_KEY")
    assert not name_validator.is_valid("DEPLOY_TOKEN")
    for location in (
        railway["properties"]["live_snapshot"],
        stored["properties"]["derived_config"]["properties"]["raw_allowlisted_env"],
    ):
        assert "VISUAL_ASSETS_REGISTRY" in location["required"]
        assert location["properties"]["VISUAL_ASSETS_REGISTRY"] == {
            "type": "string",
            "enum": ["on", "off"],
        }
    live_validator = Draft202012Validator(railway["properties"]["live_snapshot"])
    valid_live = {
        **builder.SEMANTIC_ENV_CONSTS,
        **{name: "off" for name in builder.TARGET_OFF_ENV_FLAGS},
        "VISUAL_ASSETS_REGISTRY": "on",
    }
    assert live_validator.is_valid(valid_live)
    assert live_validator.is_valid({**valid_live, "VISUAL_ASSETS_REGISTRY": "off"})
    assert not live_validator.is_valid({})
    assert not live_validator.is_valid({**valid_live, "VISUAL_ASSETS_REGISTRY": "ON"})
    assert not live_validator.is_valid({**valid_live, "VISUAL_ASSETS_REGISTRY": True})
    assert not live_validator.is_valid({**valid_live, "ENUNCIADOS_MULTIVECTOR": "off"})
    assert not live_validator.is_valid({**valid_live, "HYDE_ENABLED": "true"})
    assert not live_validator.is_valid({**valid_live, "LLM_MAX_TOKENS": "2048"})

    models = stored["properties"]["models"]["properties"]
    retrieval = stored["properties"]["retrieval"]["properties"]
    assert models["max_tokens"] == {"const": 3500}
    assert retrieval["retrieval_top_k"] == {"const": 50}
    assert retrieval["rerank_top_k"] == {"const": 10}
    derived = stored["properties"]["derived_config"]
    for field in (
        "semantic_projection_schema", "bootstrap_semantic_config",
        "target_semantic_config", "bootstrap_semantic_config_sha256",
        "target_semantic_config_sha256",
    ):
        assert field in derived["required"]
    assert (
        derived["properties"]["bootstrap_semantic_config"]
        ["properties"]["coverage"]["properties"]["post_rerank_coverage"]["const"]
        is False
    )
    assert (
        derived["properties"]["target_semantic_config"]
        ["properties"]["coverage"]["properties"]["post_rerank_coverage"]["const"]
        is True
    )
    assert not (ROOT / "evals" / "s277_c1_p1_release_config_v1.json").exists()


def test_schema_valid_release_fixture_is_consumed_by_runner_preflight():
    now = datetime(2026, 7, 20, 18, 0, tzinfo=timezone.utc)
    commit = "a" * 40
    tree = "b" * 40
    snapshot = {
        "COVERAGE_RELEASE_PROFILE": "legacy",
        "POST_RERANK_COVERAGE": "off",
        "STRUCTURAL_NEIGHBOR_COVERAGE": "off",
        "COVERAGE_MANDATORY_CALLOUT": "on",
        "MP_MANDATORY_VERB_TRIGGER": "on",
        "MUST_PRESERVE_CONTRACT": "on",
        "HYDE_ENABLED": "false",
        "CHUNKS_TABLE": "chunks_v2",
        "ENUNCIADOS_MULTIVECTOR": "on",
        "HYQ_TABLE": "on",
        "HYQ_PILOT_FILE": "",
        "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "add",
        "GENERATOR_SELECTION_BLOCK": "on",
        "GENERATOR_PROMPT_VARIANT": "fidelity",
        "RERANK_TOP_K": "10",
        "LLM_MAX_TOKENS": "3500",
        "VISUAL_ASSETS_REGISTRY": "on",
        **{name: "off" for name in p1.TARGET_OFF_FLAGS},
    }
    patch = {
        "delete": list(p1.PROFILE_OWNED_LEGACY_FLAGS),
        "set": {"COVERAGE_RELEASE_PROFILE": "off"},
    }
    release = {
        "schema_version": p1.RELEASE_CONFIG_SCHEMA,
        "status": "MATERIALIZED_SAFE_NO_SECRETS",
        "secret_fields_present": False,
        "candidate": {
            "tested_commit_sha": commit,
            "tested_tree_sha": tree,
            "detached_worktree": True,
            "git_status_empty": True,
            "untracked_files": [],
            "bot_version": commit,
        },
        "railway": {
            "read_only_snapshot_taken_at": (now - timedelta(minutes=5)).isoformat(),
            "snapshot_max_age_seconds": 1800,
            "snapshot_future_skew_seconds": 60,
            "live_snapshot": snapshot,
            "railway_live_snapshot_sha256": p1.sha256_json(snapshot),
            "planned_bootstrap_patch": patch,
        },
        "derived_config": p1.derive_release_states(snapshot, patch),
        "models": {
            "embedding": "voyage-4-large",
            "reranker": "claude-sonnet-4-6",
            "generator": "claude-sonnet-4-6",
            "temperature": 0,
            "max_tokens": 3500,
            "prompt_cache": False,
            "inference_geo": "global",
            "service_tier": "standard_sync",
        },
        "retrieval": {
            "chunks_table": "chunks_v2",
            "retrieval_top_k": 50,
            "rerank_top_k": 10,
            "reranker_backend": "llm",
            "hyde_enabled": False,
        },
        "runtime": {
            "python_version": sys.version.split()[0],
            "anthropic_sdk_version": p1.package_version("anthropic"),
            "voyage_sdk_version": p1.package_version("voyageai"),
            "effective_lock_sha256": p1.sha256_file(ROOT / "requirements.txt", lf_normalized=True),
        },
        "implementation_hashes": {
            relative: p1.sha256_file(ROOT / relative, lf_normalized=True)
            for relative in p1.REQUIRED_IMPLEMENTATION_HASHES
        },
        "rpc_allowlist": p1.derive_rpc_allowlist(p1.apply_planned_bootstrap_patch(snapshot, patch)),
        "authorizations": {
            "paid_run": False,
            "railway_mutation": False,
            "supabase_write": False,
        },
    }
    schema = _json(RELEASE_SCHEMA_PATH)
    Draft202012Validator(schema).validate(release)

    release_hash = p1.sha256_json(release)
    fingerprint = {
        "schema": p1.FINGERPRINT_SCHEMA,
        "status": "PASS",
        "release_config_sha256": release_hash,
        "function_audit_sha256_lf": p1.EXPECTED_FUNCTION_AUDIT_SHA256_LF,
        "function_definition_sha256": p1.EXPECTED_FUNCTION_DEFINITION_SHA256,
        "elapsed_ms": 1000,
        "ceiling_ms": p1.FINGERPRINT_CEILING_MS,
        "fingerprint": {"digest": "f" * 64, "row_count": 123},
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }
    semantic = release["derived_config"]["target_semantic_config"]
    relations = p1.expected_surface(semantic)["relations"]
    fence = {
        "schema": p1.FENCE_OPEN_SCHEMA,
        "status": "OPEN_VERIFIED",
        "release_config_sha256": release_hash,
        "initial_fingerprint": fingerprint["fingerprint"],
        "persistent_session": True,
        "transaction_pooler": False,
        "backend_pid": 1234,
        "txid": "9876",
        "fence_owner": "operator@example.invalid",
        "opened_at": (now - timedelta(minutes=1)).isoformat(),
        "last_heartbeat_at": (now - timedelta(seconds=2)).isoformat(),
        "heartbeat_max_age_seconds": 30,
        "deadline_at": (now + timedelta(minutes=30)).isoformat(),
        "relations": relations,
        "locks": [
            {"relation": relation, "mode": "ShareLock", "granted": True}
            for relation in relations
        ],
        "incompatible_waiters": [],
        "rpc_manifest_sha256": p1.expected_declared_rpc_surface_sha256(semantic),
        "physical_manifest_sha256": p1.expected_declared_lock_surface_sha256(
            semantic
        ),
    }
    prereg = _yaml(PREREG_PATH)
    bundle = p1.build_preflight_bundle(
        release_config=release,
        prereg=prereg,
        fingerprint_receipt=fingerprint,
        fence_open_receipt=fence,
        runtime=p1.RuntimeIdentity(commit, tree, detached=True, clean=True),
        now=now,
    )
    assert bundle.release_config_sha256 == release_hash
    assert bundle.budget.static_worst_case_usd == Decimal("29.727")
    assert bundle.release_config["railway"]["live_snapshot"]["VISUAL_ASSETS_REGISTRY"] == "on"
    assert bundle.release_config["derived_config"]["raw_allowlisted_env"]["VISUAL_ASSETS_REGISTRY"] == "on"
