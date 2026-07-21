from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import s277_c1_p1 as p1


NOW = datetime(2026, 7, 20, 18, 0, tzinfo=timezone.utc)
COMMIT = "a" * 40
TREE = "b" * 40


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _release_config() -> dict:
    snapshot = {
        "COVERAGE_RELEASE_PROFILE": "legacy",
        "POST_RERANK_COVERAGE": "off",
        "STRUCTURAL_NEIGHBOR_COVERAGE": "off",
        "COVERAGE_MANDATORY_CALLOUT": "on",
        "MP_MANDATORY_VERB_TRIGGER": "on",
        "MUST_PRESERVE_CONTRACT": "on",
        "HYDE_ENABLED": "false",
        "CHUNKS_TABLE": "chunks_v2",
        "RERANK_TOP_K": "10",
        "RERANK_PREVIEW_CHARS": "800",
        "RERANKER_BACKEND": "llm",
        "MERGE_STRATEGY": "stamps",
        "LLM_MAX_TOKENS": "3500",
        "ENUNCIADOS_MULTIVECTOR": "on",
        "HYQ_TABLE": "on",
        "HYQ_PILOT_FILE": "",
        "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "add",
        "GENERATOR_SELECTION_BLOCK": "on",
        "GENERATOR_PROMPT_VARIANT": "fidelity",
        "VISUAL_ASSETS_REGISTRY": "off",
        **{name: "off" for name in p1.TARGET_OFF_FLAGS},
    }
    patch = {
        "delete": list(p1.PROFILE_OWNED_LEGACY_FLAGS),
        "set": {"COVERAGE_RELEASE_PROFILE": "off"},
    }
    return {
        "schema_version": p1.RELEASE_CONFIG_SCHEMA,
        "status": "MATERIALIZED_SAFE_NO_SECRETS",
        "secret_fields_present": False,
        "candidate": {
            "tested_commit_sha": COMMIT,
            "tested_tree_sha": TREE,
            "detached_worktree": True,
            "git_status_empty": True,
            "untracked_files": [],
            "bot_version": COMMIT,
        },
        "railway": {
            "read_only_snapshot_taken_at": _iso(NOW - timedelta(minutes=5)),
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
            "effective_lock_sha256": p1.sha256_file(
                p1.ROOT / "requirements.txt", lf_normalized=True
            ),
        },
        "implementation_hashes": {
            relative: p1.sha256_file(p1.ROOT / relative, lf_normalized=True)
            for relative in p1.REQUIRED_IMPLEMENTATION_HASHES
        },
        "rpc_allowlist": [
            "match_chunks_v2",
            "search_chunks_text_v2",
            "match_chunks_v2_enunciados",
            "match_hyq",
        ],
        "authorizations": {
            "paid_run": False,
            "railway_mutation": False,
            "supabase_write": False,
        },
    }


def _prereg(_release: dict) -> dict:
    # One fixture exercises the same canonical prereg that a future operator
    # will use, instead of maintaining a permissive test-only dialect.
    return p1.load_data_object(p1.ROOT / "evals/s277_c1_p1_prereg_v1.yaml")


def _fingerprint(release: dict) -> dict:
    return {
        "schema": p1.FINGERPRINT_SCHEMA,
        "status": "PASS",
        "release_config_sha256": p1.sha256_json(release),
        "function_audit_sha256_lf": p1.EXPECTED_FUNCTION_AUDIT_SHA256_LF,
        "function_definition_sha256": p1.EXPECTED_FUNCTION_DEFINITION_SHA256,
        "elapsed_ms": 1_000,
        "ceiling_ms": p1.FINGERPRINT_CEILING_MS,
        "fingerprint": {"digest": "f" * 64, "row_count": 123},
        "expires_at": _iso(NOW + timedelta(hours=1)),
    }


def _fence(release: dict, fingerprint: dict) -> dict:
    semantic = release["derived_config"]["target_semantic_config"]
    relations = p1.expected_surface(semantic)["relations"]
    return {
        "schema": p1.FENCE_OPEN_SCHEMA,
        "status": "OPEN_VERIFIED",
        "release_config_sha256": p1.sha256_json(release),
        "initial_fingerprint": fingerprint["fingerprint"],
        "persistent_session": True,
        "transaction_pooler": False,
        "backend_pid": 1234,
        "txid": "9876",
        "fence_owner": "operator@example.invalid",
        "opened_at": _iso(NOW - timedelta(minutes=1)),
        "last_heartbeat_at": _iso(NOW - timedelta(seconds=2)),
        "heartbeat_max_age_seconds": 30,
        "deadline_at": _iso(NOW + timedelta(minutes=30)),
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


def _closed_fence(opened: dict, closed_at: datetime) -> dict:
    final_check_at = closed_at - timedelta(milliseconds=100)
    return {
        "schema": p1.FENCE_CLOSE_SCHEMA,
        "status": "CLOSED_VERIFIED",
        "live_manifest_post_capture_sha256": "e" * 64,
        **{
            key: opened[key]
            for key in (
                "release_config_sha256",
                "backend_pid",
                "txid",
                "fence_owner",
                "rpc_manifest_sha256",
                "physical_manifest_sha256",
            )
        },
        "initial_fingerprint": opened["initial_fingerprint"],
        "final_fingerprint": opened["initial_fingerprint"],
        "verified_under_lock": True,
        "last_heartbeat_at": _iso(final_check_at),
        "final_fingerprint_taken_at": _iso(final_check_at),
        "relations": opened["relations"],
        "locks": opened["locks"],
        "incompatible_waiters": [],
        "closed_at": _iso(closed_at),
    }


def _authorization(
    release: dict,
    prereg: dict,
    artifact_root: Path | None = None,
    *,
    authorization_id: str = "auth-p1-test-0001",
    run_id: str = "run-p1-test-0001",
) -> dict:
    from scripts.s277_c1_p1_scorer import load_fact_contract, score_stored_controls

    stored = score_stored_controls(
        contract=load_fact_contract(
            p1.ROOT / "evals/s277_c1_p1_fact_contract_v1.json"
        )
    )
    return {
        "schema": p1.AUTHORIZATION_SCHEMA,
        "status": "AUTHORIZED",
        "scope": "P1_E_27_REPLICAS",
        "release_config_sha256": p1.sha256_json(release),
        "prereg_sha256": p1.sha256_json(prereg),
        "replica_plan_sha256": p1.REPLICA_PLAN_SHA256,
        "authorization_id": authorization_id,
        "run_id": run_id,
        "artifact_identity_sha256": p1.artifact_identity_sha256(
            run_id, artifact_root or Path("test-artifacts")
        ),
        "max_usd": "10.00",
        "authorized_by": "Alberto",
        "issued_at": _iso(NOW - timedelta(minutes=1)),
        "expires_at": _iso(NOW + timedelta(hours=1)),
        "prepaid_known_conflict": {
            "conflict_id": "conf_26f63590494f",
            "status": "EXPLICIT_MEASUREMENT_PERMIT",
            "rationale": "test-only permit acknowledging the stored prior",
            "stored_control_score_sha256": p1.sha256_json(stored),
        },
    }


def _bundle() -> tuple[p1.PreflightBundle, dict, dict]:
    release = _release_config()
    prereg = _prereg(release)
    fingerprint = _fingerprint(release)
    fence = _fence(release, fingerprint)
    bundle = p1.build_preflight_bundle(
        release_config=release,
        prereg=prereg,
        fingerprint_receipt=fingerprint,
        fence_open_receipt=fence,
        runtime=p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True),
        now=NOW,
    )
    return bundle, release, prereg


def _visual_bundle() -> tuple[p1.PreflightBundle, dict, dict]:
    release = _release_config()
    snapshot = release["railway"]["live_snapshot"]
    snapshot["VISUAL_ASSETS_REGISTRY"] = "on"
    release["railway"]["railway_live_snapshot_sha256"] = p1.sha256_json(snapshot)
    release["derived_config"] = p1.derive_release_states(
        snapshot, release["railway"]["planned_bootstrap_patch"]
    )
    prereg = _prereg(release)
    fingerprint = _fingerprint(release)
    fence = _fence(release, fingerprint)
    bundle = p1.build_preflight_bundle(
        release_config=release,
        prereg=prereg,
        fingerprint_receipt=fingerprint,
        fence_open_receipt=fence,
        runtime=p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True),
        now=NOW,
    )
    return bundle, release, prereg


def _genesis_for(
    bundle: p1.PreflightBundle,
    release: dict,
    prereg: dict,
    artifact_root: Path,
) -> dict:
    authorization = _authorization(release, prereg, artifact_root)
    return p1.build_run_genesis(bundle, authorization, artifact_root)


class _Prepared:
    def __init__(self, callback):
        self.callback = callback

    def send(self):
        return self.callback()


class _Provider:
    def __init__(self):
        self.prepares: list[str] = []
        self.sends: list[str] = []

    def prepare(self, call: p1.ProviderCall):
        self.prepares.append(call.call_key)

        def send():
            self.sends.append(call.call_key)
            operation = call.call_key.rsplit(":", 1)[-1]
            replica_key = call.call_key.rsplit(":", 1)[0]
            return {
                "id": f"response-{len(self.sends)}",
                "model": call.model,
                "stop_reason": "end_turn" if operation == "synthesis" else None,
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20 if operation != "embedding" else 0,
                },
                "content": f"Respuesta completa para {replica_key} [F1]",
            }

        return _Prepared(send)


class _ReplicaAdapter:
    def __init__(self, provider: _Provider):
        self.provider = provider
        self.inputs = p1.prereg_input_contract(
            p1.load_data_object(p1.CANONICAL_PREREG_PATH)
        )

    def execute_replica(self, replica: p1.Replica, boundary: p1.ProviderBoundary):
        responses: dict[str, dict] = {}
        requests: dict[str, dict] = {}
        input_row = self.inputs[replica.qid]

        def invoke(operation: str, lineage_payload):
            spec = boundary.budget.specs[f"{replica.key}:{operation}"]
            payload = p1.build_operation_payload(
                operation=operation,
                model=spec.model,
                question=input_row["question"],
                lineage_payload=lineage_payload,
                max_output_tokens=spec.max_output_tokens,
            )
            input_bound = p1.physical_input_token_upper_bound(payload)
            lineage_sha = p1.sha256_json(lineage_payload)
            request = {
                "replica_key": replica.key,
                "operation": operation,
                "model": spec.model,
                "run_genesis_sha256": boundary.run_genesis[
                    "run_genesis_sha256"
                ],
                "lineage_input_sha256": lineage_sha,
                "physical_payload": payload,
                "physical_payload_sha256": p1.sha256_json(payload),
                "input_tokens_upper_bound": input_bound,
                "max_output_tokens": spec.max_output_tokens,
            }
            call = p1.ProviderCall(
                call_key=spec.call_key,
                provider=spec.provider,
                model=spec.model,
                request=request,
                run_genesis_sha256=boundary.run_genesis["run_genesis_sha256"],
                lineage_input_sha256=lineage_sha,
                input_tokens_upper_bound=input_bound,
                max_output_tokens=spec.max_output_tokens,
                max_retries=0,
                prompt_cache=False,
            )
            requests[operation] = call.sealed_envelope
            responses[operation] = boundary.invoke(call)
            return responses[operation]

        embedding = invoke("embedding", input_row)
        pool = [{"id": "pool-1", "content": "evidence"}]
        rerank_response = invoke("rerank", pool)
        prefix = [{"id": "prefix-1", "content": "evidence"}]
        structural_output = [{"id": "context-1", "content": "manual"}]
        served_context = list(structural_output)
        if replica.qid == "hp017":
            from scripts import s277_c1_p1_scorer as scorer

            served_context.append(
                {"id": scorer.TARGET_ID, "content": "validated mandatory warning"}
            )
        synthesis = invoke("synthesis", served_context)
        answer = f"Respuesta completa para {replica.key} [F1]"
        answer_sha = hashlib.sha256(answer.encode("utf-8")).hexdigest()
        effective = boundary.run_genesis["target_semantic_config"]
        effective_sha = p1.sha256_json(effective)
        clean_embedding = dict(embedding)
        clean_embedding.pop("_p1_resumed_from_receipt", None)
        clean_rerank = dict(rerank_response)
        clean_rerank.pop("_p1_resumed_from_receipt", None)
        from src.bot.response_formatter import format_telegram_messages

        parts = format_telegram_messages(answer)
        visual_enabled = effective["generation"]["visual_assets_registry"]
        eligible_pages = p1.visual_lookup_keys(answer, served_context)
        visual_receipt = {
            "enabled": visual_enabled,
            "status": "evaluated" if visual_enabled else "not_executed",
            "effective_config_sha256": effective_sha,
            "input_answer_sha256": answer_sha,
            "input_context_sha256": p1.sha256_json(served_context),
            "rest_get_surface": (
                [p1.VISUAL_REST_GET_SURFACE] if visual_enabled else []
            ),
            "eligible_pages": eligible_pages,
            "eligible_pages_sha256": p1.sha256_json(eligible_pages),
            "lookup_receipts": [],
            "selected_assets": [],
            "selected_assets_sha256": p1.sha256_json([]),
        }
        return {
            "schema": p1.REPLICA_RECEIPT_SCHEMA,
            "replica_key": replica.key,
            "qid": replica.qid,
            "replica_id": replica.replica_id,
            "input": input_row,
            "run_identity": {
                key: boundary.run_genesis[key]
                for key in (
                    "authorization_id",
                    "authorization_receipt_sha256",
                    "run_id",
                    "run_genesis_sha256",
                    "runtime_layout_sha256",
                    "release_config_sha256",
                    "prereg_sha256",
                    "tested_commit_sha",
                    "tested_tree_sha",
                )
            },
            "effective_config": {
                "profile": p1.PROFILE,
                "semantic_config": effective,
                "semantic_config_sha256": effective_sha,
                "must_preserve_contract": True,
            },
            "retrieval": {
                "pool": pool,
                "pool_sha256": p1.sha256_json(pool),
                "pool_parent_embedding_response_sha256": p1.sha256_json(
                    clean_embedding
                ),
                "embedding_receipt": embedding,
                "embedding_request_sha256": p1.sha256_json(
                    requests["embedding"]
                ),
                "embedding_response_sha256": p1.sha256_json(clean_embedding),
            },
            "rerank": {
                "prefix": prefix,
                "prefix_sha256": p1.sha256_json(prefix),
                "prefix_parent_rerank_response_sha256": p1.sha256_json(
                    clean_rerank
                ),
                "receipt": rerank_response,
                "request_sha256": p1.sha256_json(requests["rerank"]),
                "response_sha256": p1.sha256_json(clean_rerank),
                "input_pool_sha256": p1.sha256_json(pool),
                "fallback_used": False,
            },
            "served_context": served_context,
            "structural_fetch": {
                "input_prefix_sha256": p1.sha256_json(prefix),
                "output": structural_output,
                "output_sha256": p1.sha256_json(structural_output),
            },
            "coverage": {
                "status": "evaluated",
                "profile": p1.PROFILE,
                "effective_config_sha256": effective_sha,
                "input_context_sha256": p1.sha256_json(structural_output),
                "output_context": served_context,
                "output_context_sha256": p1.sha256_json(served_context),
            },
            "must_preserve": {
                "status": "evaluated",
                "profile": p1.PROFILE,
                "effective_config_sha256": effective_sha,
                "input_answer_sha256": answer_sha,
                "output_answer_sha256": answer_sha,
            },
            "provider": {
                "requested_model": synthesis["model"],
                "reported_model": synthesis["model"],
                "stop_reason": synthesis["stop_reason"],
                "usage": synthesis["usage"],
                "response_id": synthesis["id"],
                "raw_payload": synthesis,
            },
            "answer": answer,
            "answer_sha256": answer_sha,
            "generation_chain": {
                "raw_payload_sha256": p1.sha256_json(synthesis),
                "raw_text": answer,
                "raw_text_sha256": answer_sha,
                "stages": [
                    {
                        "name": name,
                        "input_sha256": answer_sha,
                        "output_text": answer,
                        "output_sha256": answer_sha,
                    }
                    for name in (
                        "diagram_postprocess",
                        "answer_planner",
                        "must_preserve",
                    )
                ],
                "final_answer_sha256": answer_sha,
            },
            "visual_assets": visual_receipt,
            "render": {
                "parts": parts,
                "parts_sha256": p1.sha256_json(parts),
                "render_status": "ok",
                "source_answer_sha256": answer_sha,
                "complete_source_rendered": True,
                "message_parts": len(parts),
            },
            "call_keys": [f"{replica.key}:{op}" for op in p1.CALL_OPERATIONS],
            "call_requests": requests,
        }


class _ReceiptMutationAdapter(_ReplicaAdapter):
    def __init__(self, provider: _Provider, mutation: str):
        super().__init__(provider)
        self.mutation = mutation

    def execute_replica(self, replica, boundary):
        receipt = json.loads(
            json.dumps(super().execute_replica(replica, boundary), ensure_ascii=False)
        )
        if self.mutation == "input":
            receipt["input"]["question"] += " alterada"
        elif self.mutation == "request_input_hash":
            receipt["call_requests"]["synthesis"][
                "lineage_input_sha256"
            ] = "0" * 64
        elif self.mutation == "detached_answer":
            answer = receipt["answer"] + " no derivada"
            answer_sha = hashlib.sha256(answer.encode("utf-8")).hexdigest()
            receipt["answer"] = answer
            receipt["answer_sha256"] = answer_sha
            receipt["render"]["parts"] = [answer]
            receipt["render"]["parts_sha256"] = p1.sha256_json([answer])
            receipt["render"]["source_answer_sha256"] = answer_sha
        elif self.mutation == "provider_top":
            receipt["provider"]["response_id"] = "forged-response-id"
        elif self.mutation == "max_tokens_masquerading_end_turn":
            receipt["provider"]["raw_payload"]["usage"]["output_tokens"] = 3500
            receipt["provider"]["usage"]["output_tokens"] = 3500
        elif self.mutation == "stage_link":
            receipt["generation_chain"]["stages"][1]["input_sha256"] = "0" * 64
        elif self.mutation == "render_hash":
            receipt["render"]["parts_sha256"] = "0" * 64
        elif self.mutation == "render_recomputed_forgery":
            receipt["render"]["parts"] = ["forjado pero autoconsistente"]
            receipt["render"]["parts_sha256"] = p1.sha256_json(
                receipt["render"]["parts"]
            )
        elif self.mutation == "lineage_pool":
            receipt["rerank"]["input_pool_sha256"] = "0" * 64
        elif self.mutation == "effective_config":
            receipt["effective_config"]["profile"] = "off"
        elif self.mutation == "run_identity":
            receipt["run_identity"]["run_id"] = "run-p1-forged-0001"
        elif self.mutation == "visual_executed_off":
            receipt["visual_assets"]["status"] = "evaluated"
            receipt["visual_assets"]["rest_get_surface"] = [
                p1.VISUAL_REST_GET_SURFACE
            ]
        else:  # pragma: no cover - fixture misuse
            raise AssertionError(self.mutation)
        return receipt


class _Watcher:
    def __init__(self, *, now=NOW, mutation=None):
        self.calls = []
        self.now = now
        self.mutation = mutation

    def verify(
        self,
        *,
        phase,
        replica,
        call_key,
        run_genesis,
        fence_open_receipt,
    ):
        self.calls.append((phase, replica.key if replica else None, call_key))
        receipt = {
            "schema": p1.FENCE_WATCH_SCHEMA,
            "status": "OPEN_VERIFIED",
            "phase": phase,
            "call_key": call_key,
            "replica_key": replica.key,
            "checked_at": _iso(self.now),
            "run_genesis_sha256": run_genesis["run_genesis_sha256"],
            "release_config_sha256": fence_open_receipt[
                "release_config_sha256"
            ],
            "fingerprint_sha256": p1.sha256_json(
                fence_open_receipt["initial_fingerprint"]
            ),
            "fence_open_receipt_sha256": p1.sha256_json(fence_open_receipt),
            **{
                key: fence_open_receipt[key]
                for key in (
                    "backend_pid",
                    "txid",
                    "fence_owner",
                    "deadline_at",
                    "last_heartbeat_at",
                    "heartbeat_max_age_seconds",
                    "relations",
                    "locks",
                    "rpc_manifest_sha256",
                    "physical_manifest_sha256",
                )
            },
            "incompatible_waiters": [],
        }
        if self.mutation == "relations":
            receipt["relations"] = receipt["relations"][:-1]
        elif self.mutation == "run_genesis":
            receipt["run_genesis_sha256"] = "0" * 64
        elif self.mutation == "stale":
            receipt["checked_at"] = _iso(self.now - timedelta(seconds=3))
        return receipt


def _runner_for_test(
    *,
    bundle,
    release,
    prereg,
    run_dir,
    provider,
    journal=None,
    runtime_inspector=None,
):
    return p1.P1Runner(
        bundle=bundle,
        permit=p1.ExecutionPermit(
            True, True, True, _authorization(release, prereg, run_dir)
        ),
        artifacts=p1.ArtifactStore(run_dir),
        journal=journal
        or p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW),
        provider_adapter=provider,
        replica_adapter=_ReplicaAdapter(provider),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(run_dir),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=runtime_inspector
        or (lambda: bundle.runtime_identity),
        now=lambda: NOW,
    )


def _test_authoritative_pass_score(replicas, contract, *, bindings=None):
    from scripts import s277_c1_p1_scorer as scorer

    assert isinstance(bindings, dict)
    return {
        "schema_version": scorer.SCHEMA_VERSION,
        "scorer_sha256": scorer.scorer_sha256(),
        "contract_id": contract["contract_id"],
        "contract_sha256": p1.sha256_json(contract),
        "score_bindings": dict(bindings),
        **dict(bindings),
        "replicas_sha256": p1.sha256_json(replicas),
        "status": "PASS",
        "decision": "PASS",
        "claim": "NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS",
        "replica_count": len(replicas),
        "status_counts": {
            "PASS": len(replicas),
            "FAIL": 0,
            "REVIEW": 0,
            "INSTRUMENT_ERROR": 0,
        },
        "replicas": [],
        "review_items": [],
    }


def test_plan_is_exactly_27_independent_replicas_and_81_model_calls():
    assert len(p1.REPLICAS) == 27
    assert [replica.key for replica in p1.REPLICAS] == list(p1.REPLICA_ORDER)
    assert p1.REPLICA_ORDER[:3] == ("hp017:r1", "hp017:r2", "hp017:r3")
    assert len(p1.expected_call_keys()) == 81
    assert len(set(p1.expected_call_keys())) == 81
    assert p1.REPLICA_PLAN_SHA256 == p1.sha256_json(list(p1.REPLICA_ORDER))


def test_bootstrap_patch_is_pure_exact_and_derives_distinct_effective_states():
    config = _release_config()
    live = config["railway"]["live_snapshot"]
    before = json.loads(json.dumps(live))
    derived = p1.derive_release_states(
        live, config["railway"]["planned_bootstrap_patch"]
    )
    assert live == before
    assert derived["bootstrap_profile"] == "off"
    assert derived["p1_target_profile"] == p1.PROFILE
    assert derived["raw_allowlisted_env"]["COVERAGE_RELEASE_PROFILE"] == "off"
    assert derived["bootstrap_effective_config_sha256"] != derived["target_effective_config_sha256"]
    assert not any(
        name in derived["raw_allowlisted_env"]
        for name in p1.PROFILE_OWNED_LEGACY_FLAGS
    )
    bootstrap_semantic = derived["bootstrap_semantic_config"]
    target_semantic = derived["target_semantic_config"]
    assert bootstrap_semantic["retrieval"]["retrieval_top_k"] == 50
    assert bootstrap_semantic["retrieval"]["rerank_top_k"] == 10
    assert bootstrap_semantic["retrieval"]["hyde_enabled"] is False
    assert bootstrap_semantic["retrieval"]["enunciados_multivector"] is True
    assert bootstrap_semantic["retrieval"]["hyq_table"] is True
    assert bootstrap_semantic["retrieval"]["identity_resolve"] is True
    assert bootstrap_semantic["generation"]["selection_block"] is True
    assert bootstrap_semantic["generation"]["max_tokens"] == 3500
    assert bootstrap_semantic["coverage"]["post_rerank_coverage"] is False
    assert target_semantic["coverage"]["post_rerank_coverage"] is True
    assert derived["bootstrap_semantic_config_sha256"] == p1.sha256_json(
        bootstrap_semantic
    )
    assert derived["target_semantic_config_sha256"] == p1.sha256_json(
        target_semantic
    )


def test_visual_assets_registry_on_is_preserved_and_hash_bound():
    release = _release_config()
    snapshot = release["railway"]["live_snapshot"]
    off_derived = release["derived_config"]
    snapshot["VISUAL_ASSETS_REGISTRY"] = "on"
    release["railway"]["railway_live_snapshot_sha256"] = p1.sha256_json(snapshot)
    on_derived = p1.derive_release_states(
        snapshot, release["railway"]["planned_bootstrap_patch"]
    )
    release["derived_config"] = on_derived

    verified = p1.verify_release_config(
        release, p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True), now=NOW
    )

    assert verified["raw_allowlisted_env"]["VISUAL_ASSETS_REGISTRY"] == "on"
    assert (
        on_derived["common_config_sha256"]
        != off_derived["common_config_sha256"]
    )
    assert (
        on_derived["bootstrap_effective_config_sha256"]
        != off_derived["bootstrap_effective_config_sha256"]
    )
    assert (
        on_derived["target_effective_config_sha256"]
        != off_derived["target_effective_config_sha256"]
    )


@pytest.mark.parametrize("invalid", [None, "", "true", "ON", True, 1])
def test_visual_assets_registry_requires_exact_on_or_off(invalid):
    release = _release_config()
    snapshot = release["railway"]["live_snapshot"]
    if invalid is None:
        snapshot.pop("VISUAL_ASSETS_REGISTRY")
    else:
        snapshot["VISUAL_ASSETS_REGISTRY"] = invalid

    with pytest.raises(p1.P1Error) as caught:
        p1.derive_release_states(
            snapshot, release["railway"]["planned_bootstrap_patch"]
        )

    assert caught.value.code == "HOLD_CONFIG_DRIFT"


def test_visual_assets_registry_snapshot_drift_is_caught_by_derived_hashes():
    release = _release_config()
    snapshot = release["railway"]["live_snapshot"]
    snapshot["VISUAL_ASSETS_REGISTRY"] = "on"
    release["railway"]["railway_live_snapshot_sha256"] = p1.sha256_json(snapshot)

    with pytest.raises(p1.P1Error) as caught:
        p1.verify_release_config(
            release, p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True), now=NOW
        )

    assert caught.value.code == "HOLD_CONFIG_DRIFT"


def test_release_config_rejects_semantic_cross_field_and_stale_snapshot():
    release = _release_config()
    release["retrieval"]["rerank_top_k"] = 9
    with pytest.raises(p1.P1Error) as mismatch:
        p1.verify_release_config(
            release,
            p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True),
            now=NOW,
        )
    assert mismatch.value.code == "HOLD_CONFIG_SCHEMA"

    stale = _release_config()
    stale["railway"]["read_only_snapshot_taken_at"] = _iso(
        NOW - timedelta(minutes=31)
    )
    with pytest.raises(p1.P1Error) as expired:
        p1.verify_release_config(
            stale,
            p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True),
            now=NOW,
        )
    assert expired.value.code == "HOLD_RAILWAY_SNAPSHOT_STALE"


@pytest.mark.parametrize(
    "name,value",
    [
        ("HYDE_ENABLED", "true"),
        ("ENUNCIADOS_MULTIVECTOR", "off"),
        ("HYQ_TABLE", "off"),
        ("IDENTITY_RESOLVE", "shadow"),
        ("IDENTITY_RESOLVE_POLICY", "replace"),
        ("GENERATOR_SELECTION_BLOCK", "off"),
        ("GENERATOR_PROMPT_VARIANT", "base"),
        ("RERANK_TOP_K", "9"),
        ("LLM_MAX_TOKENS", "2048"),
    ],
)
def test_semantic_runtime_projection_rejects_live_behavior_drift(name, value):
    release = _release_config()
    snapshot = release["railway"]["live_snapshot"]
    snapshot[name] = value
    release["railway"]["railway_live_snapshot_sha256"] = p1.sha256_json(snapshot)

    with pytest.raises(p1.P1Error) as caught:
        p1.derive_release_states(
            snapshot, release["railway"]["planned_bootstrap_patch"]
        )

    assert caught.value.code == "HOLD_CONFIG_DRIFT"


def test_prereg_requires_exact_visual_preservation_contract():
    prereg = _prereg(_release_config())
    prereg["release_identity"]["preserved_orthogonal_flags"][
        "VISUAL_ASSETS_REGISTRY"
    ]["target_policy"] = "force_off"

    with pytest.raises(p1.P1Error) as caught:
        p1.verify_prereg_release_identity(prereg)

    assert caught.value.code == "HOLD_PREREG_DRIFT"


@pytest.mark.parametrize(
    "mutation",
    [
        "global_claim",
        "ledger_derivation",
        "runtime_layout",
        "run_genesis",
        "fence_surface",
        "renderer",
        "visual_side_path",
    ],
)
def test_prereg_runtime_contract_rejects_crosscut_bypass_mutations(mutation):
    prereg = _prereg(_release_config())
    if mutation == "global_claim":
        prereg["authorization"]["global_atomic_claim_outside_artifact_dir"] = False
    elif mutation == "ledger_derivation":
        prereg["authorization"]["authorization_ledger_derivation"] = "caller/root"
    elif mutation == "runtime_layout":
        prereg["wal"]["canonical_runtime_layout"]["call_journal"] = "elsewhere/calls.jsonl"
    elif mutation == "run_genesis":
        prereg["wal"][
            "run_genesis_sha256_on_every_event_and_atomic_call_claim"
        ] = False
    elif mutation == "fence_surface":
        prereg["corpus_fence"]["base_relations_exact"].pop()
    elif mutation == "renderer":
        prereg["receipt_pipeline"]["render"]["recompute_exactly_with"] = "self_report"
    else:
        prereg["receipt_pipeline"]["visual_assets"]["on_rest_method"] = "POST"
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_prereg_runtime_contract(prereg)
    assert caught.value.code == "HOLD_PREREG_DRIFT"


@pytest.mark.parametrize(
    "patch",
    [
        {"delete": [], "set": {"COVERAGE_RELEASE_PROFILE": "off"}},
        {
            "delete": list(p1.PROFILE_OWNED_LEGACY_FLAGS),
            "set": {"COVERAGE_RELEASE_PROFILE": p1.PROFILE},
        },
        {
            "delete": list(p1.PROFILE_OWNED_LEGACY_FLAGS),
            "set": {"COVERAGE_RELEASE_PROFILE": "off", "EXTRA": "on"},
        },
    ],
)
def test_bootstrap_patch_rejects_any_scope_drift(patch):
    with pytest.raises(p1.P1Error, match="patch"):
        p1.apply_planned_bootstrap_patch({}, patch)


def test_preflight_verifies_code_config_budget_fingerprint_and_fence():
    import jsonschema

    release = _release_config()
    schema = json.loads(
        (p1.ROOT / "evals/s277_c1_p1_release_config_schema_v1.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(release, schema)
    bundle, _, _ = _bundle()
    assert bundle.budget.static_worst_case_usd == Decimal("6.777")
    assert bundle.budget.cap_usd == Decimal("10.00")
    assert bundle.fence_open_receipt["transaction_pooler"] is False


def test_preflight_bundle_deep_copies_all_json_safe_mapping_inputs():
    release = _release_config()
    prereg = _prereg(release)
    fingerprint = _fingerprint(release)
    fence = _fence(release, fingerprint)
    bundle = p1.build_preflight_bundle(
        release_config=release,
        prereg=prereg,
        fingerprint_receipt=fingerprint,
        fence_open_receipt=fence,
        runtime=p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True),
        now=NOW,
    )
    sealed = {
        "release": p1.sha256_json(bundle.release_config),
        "prereg": p1.sha256_json(bundle.prereg),
        "fingerprint": p1.sha256_json(bundle.fingerprint_receipt),
        "fence": p1.sha256_json(bundle.fence_open_receipt),
    }
    release["candidate"]["tested_commit_sha"] = "0" * 40
    prereg["authorization"]["paid_execution"] = True
    fingerprint["fingerprint"]["digest"] = "mutated"
    fence["locks"][0]["granted"] = False
    assert {
        "release": p1.sha256_json(bundle.release_config),
        "prereg": p1.sha256_json(bundle.prereg),
        "fingerprint": p1.sha256_json(bundle.fingerprint_receipt),
        "fence": p1.sha256_json(bundle.fence_open_receipt),
    } == sealed


@pytest.mark.parametrize(
    "invalid",
    [
        ("tuple", ("not", "json-native")),
        ("non_string_key", {1: "value"}),
        ("nan", float("nan")),
        ("decimal", Decimal("1.2")),
    ],
)
def test_preflight_snapshot_rejects_non_json_native_values(invalid):
    _name, value = invalid
    release = _release_config()
    prereg = _prereg(release)
    fingerprint = _fingerprint(release)
    fingerprint["invalid"] = value
    fence = _fence(release, fingerprint)

    with pytest.raises(p1.P1Error) as caught:
        p1.build_preflight_bundle(
            release_config=release,
            prereg=prereg,
            fingerprint_receipt=fingerprint,
            fence_open_receipt=fence,
            runtime=p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True),
            now=NOW,
        )

    assert caught.value.code == "HOLD_PREFLIGHT_SNAPSHOT"


@pytest.mark.parametrize(
    "mapping_name",
    [
        "release_config",
        "prereg",
        "fingerprint_receipt",
        "fence_open_receipt",
    ],
)
def test_execution_start_rejects_mutated_preflight_snapshot_before_send(
    tmp_path, mapping_name
):
    bundle, release, prereg = _bundle()
    provider = _Provider()
    runner = _runner_for_test(
        bundle=bundle,
        release=release,
        prereg=prereg,
        run_dir=tmp_path / mapping_name,
        provider=provider,
    )
    mapping = getattr(bundle, mapping_name)
    if mapping_name == "release_config":
        mapping["candidate"]["tested_commit_sha"] = "0" * 40
    elif mapping_name == "prereg":
        mapping["authorization"]["paid_execution"] = True
    elif mapping_name == "fingerprint_receipt":
        mapping["fingerprint"]["digest"] = "mutated"
    else:
        mapping["txid"] = "mutated"

    with pytest.raises(p1.P1Error) as caught:
        runner.run()

    assert caught.value.code == "HOLD_PREFLIGHT_SNAPSHOT_DRIFT"
    assert provider.prepares == provider.sends == []
    assert not (tmp_path / mapping_name / "calls.jsonl").exists()
    assert not (tmp_path / mapping_name / "result.json").exists()


@pytest.mark.parametrize("mutation", ["commit", "tree", "dirty"])
def test_execution_start_rejects_fresh_runtime_identity_drift_before_send(
    tmp_path, mutation
):
    bundle, release, prereg = _bundle()
    values = p1.runtime_identity_payload(bundle.runtime_identity)
    if mutation == "commit":
        values["commit_sha"] = "c" * 40
    elif mutation == "tree":
        values["tree_sha"] = "d" * 40
    else:
        values["clean"] = False
    drifted = p1.RuntimeIdentity(**values)
    provider = _Provider()
    runner = _runner_for_test(
        bundle=bundle,
        release=release,
        prereg=prereg,
        run_dir=tmp_path / mutation,
        provider=provider,
        runtime_inspector=lambda: drifted,
    )

    with pytest.raises(p1.P1Error) as caught:
        runner.run()

    assert caught.value.code == "HOLD_RUNTIME_IDENTITY_DRIFT"
    assert provider.prepares == provider.sends == []
    assert not (tmp_path / mutation / "calls.jsonl").exists()
    assert not (tmp_path / mutation / "result.json").exists()


def test_preflight_fails_closed_on_dirty_or_attached_checkout():
    release = _release_config()
    with pytest.raises(p1.P1Error) as dirty:
        p1.verify_release_config(
            release, p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=False), now=NOW
        )
    assert dirty.value.code == "HOLD_WORKTREE_DIRTY"
    with pytest.raises(p1.P1Error) as attached:
        p1.verify_release_config(
            release, p1.RuntimeIdentity(COMMIT, TREE, detached=False, clean=True), now=NOW
        )
    assert attached.value.code == "HOLD_WORKTREE_NOT_DETACHED"


def test_safe_release_config_rejects_secret_fields():
    release = _release_config()
    release["railway"]["live_snapshot"]["SUPABASE_SERVICE_KEY"] = "redacted"
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_release_config(
            release, p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True), now=NOW
        )
    assert caught.value.code == "HOLD_SECRET_IN_SAFE_ARTIFACT"


def test_release_config_rejects_extra_rpc_not_derived_from_any_lane():
    release = _release_config()
    release["rpc_allowlist"].append("unreviewed_rpc")
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_release_config(
            release, p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True), now=NOW
        )
    assert caught.value.code == "HOLD_RPC_ALLOWLIST_DRIFT"


def test_release_config_rejects_enunciados_lane_without_its_rpc():
    release = _release_config()
    release["rpc_allowlist"].remove("match_chunks_v2_enunciados")
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_release_config(
            release, p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True), now=NOW
        )
    assert caught.value.code == "HOLD_RPC_ALLOWLIST_DRIFT"


def test_release_config_rejects_missing_or_stale_implementation_hash():
    release = _release_config()
    release["implementation_hashes"].pop("src/rag/serving_pipeline.py")
    with pytest.raises(p1.P1Error) as missing:
        p1.verify_release_config(
            release, p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True), now=NOW
        )
    assert missing.value.code == "HOLD_IMPLEMENTATION_DRIFT"

    release = _release_config()
    release["implementation_hashes"]["src/rag/serving_pipeline.py"] = "0" * 64
    with pytest.raises(p1.P1Error) as stale:
        p1.verify_release_config(
            release, p1.RuntimeIdentity(COMMIT, TREE, detached=True, clean=True), now=NOW
        )
    assert stale.value.code == "HOLD_IMPLEMENTATION_DRIFT"


def test_implementation_manifest_is_exactly_the_static_transitive_closure():
    closure = p1.implementation_dependency_closure()
    assert set(closure) == set(p1.REQUIRED_IMPLEMENTATION_HASHES)
    assert len(closure) == len(set(closure))
    assert p1.PRODUCT_ADAPTER_IMPLEMENTATION_PATH in closure
    assert "scripts/s270_etapa2_probe.py" in closure
    assert "src/rag/answer_planner.py" in closure
    assert "src/reingest/embed.py" in closure


def test_each_implementation_dependency_omission_is_rejected():
    manifest = {
        relative: p1.sha256_file(p1.ROOT / relative, lf_normalized=True)
        for relative in p1.REQUIRED_IMPLEMENTATION_HASHES
    }
    for relative in p1.REQUIRED_IMPLEMENTATION_HASHES:
        incomplete = dict(manifest)
        incomplete.pop(relative)
        with pytest.raises(p1.P1Error) as caught:
            p1.verify_implementation_hashes(incomplete)
        assert caught.value.code == "HOLD_IMPLEMENTATION_DRIFT", relative


def test_clean_process_loaded_local_closure_is_fully_manifested():
    child = r'''
import importlib, json, os, sys
from pathlib import Path
root = Path.cwd().resolve()
sys.path.insert(0, str(root))
from scripts import s277_c1_p1 as p1
for relative in p1.REQUIRED_IMPLEMENTATION_HASHES:
    importlib.import_module(p1._implementation_module_name(relative))
observed = p1.loaded_local_implementation_paths(root)
p1.verify_loaded_implementation_closure(
    {relative: "sealed" for relative in p1.REQUIRED_IMPLEMENTATION_HASHES},
    loaded_paths=observed,
)
print(json.dumps(observed))
'''
    environment = {
        key: os.environ[key]
        for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP")
        if key in os.environ
    }
    environment.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "PYTHONIOENCODING": "utf-8",
            "COVERAGE_RELEASE_PROFILE": "off",
            "CHUNKS_TABLE": "chunks_v2",
            "HYDE_ENABLED": "false",
            "ENUNCIADOS_MULTIVECTOR": "off",
            "HYQ_TABLE": "off",
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", child],
        cwd=p1.ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    observed = set(json.loads(completed.stdout.splitlines()[-1]))
    assert observed <= set(p1.REQUIRED_IMPLEMENTATION_HASHES)
    assert {
        p1.PRODUCT_ADAPTER_IMPLEMENTATION_PATH,
        "scripts/s270_etapa2_probe.py",
        "src/rag/answer_planner.py",
        "src/reingest/embed.py",
    } <= observed


def test_fingerprint_and_fence_receipts_expire_and_reject_stale_heartbeat():
    release = _release_config()
    fingerprint = _fingerprint(release)
    fence = _fence(release, fingerprint)
    fence["last_heartbeat_at"] = _iso(NOW - timedelta(minutes=2))
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_fence_open_receipt(
            fence,
            release_config_sha256=p1.sha256_json(release),
            fingerprint=fingerprint["fingerprint"],
            target_semantic_config=release["derived_config"][
                "target_semantic_config"
            ],
            now=NOW,
        )
    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"


def test_fence_watch_rejects_absolute_heartbeat_age_over_maximum():
    bundle, release, prereg = _bundle()
    run_dir = Path("watch-absolute-heartbeat-test")
    authorization = _authorization(release, prereg, run_dir)
    genesis = p1.build_run_genesis(bundle, authorization, run_dir)
    replica = p1.REPLICAS[0]
    call_key = f"{replica.key}:embedding"
    watch = _Watcher(now=NOW).verify(
        phase="before_provider_send",
        replica=replica,
        call_key=call_key,
        run_genesis=genesis,
        fence_open_receipt=bundle.fence_open_receipt,
    )
    watch["checked_at"] = _iso(NOW - timedelta(seconds=1))
    watch["last_heartbeat_at"] = _iso(NOW - timedelta(seconds=31))

    with pytest.raises(p1.P1Error) as caught:
        p1.verify_fence_watch_receipt(
            watch,
            open_receipt=bundle.fence_open_receipt,
            run_genesis=genesis,
            call_key=call_key,
            now=NOW,
        )

    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"


def test_fence_close_requires_same_fingerprint_and_issues_six_hour_ttl():
    release = _release_config()
    fingerprint = _fingerprint(release)
    opened = _fence(release, fingerprint)
    closed_at = NOW + timedelta(minutes=20)
    closed = _closed_fence(opened, closed_at)
    result = p1.verify_fence_close_receipt(
        opened, closed, now=closed_at + timedelta(seconds=1)
    )
    assert result["expired"] is False
    assert p1._parse_time(result["p1_expires_at"], field="expiry") - closed_at == timedelta(hours=6)
    closed["final_fingerprint"] = {"digest": "changed"}
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_fence_close_receipt(opened, closed, now=closed_at + timedelta(seconds=1))
    assert caught.value.code == "HOLD_CORPUS_DRIFT"


def test_fence_close_rejects_after_deadline_stale_heartbeat_or_lost_lock():
    release = _release_config()
    fingerprint = _fingerprint(release)
    opened = _fence(release, fingerprint)
    deadline = p1._parse_time(opened["deadline_at"], field="deadline")

    after_deadline = _closed_fence(opened, deadline + timedelta(seconds=1))
    with pytest.raises(p1.P1Error) as late:
        p1.verify_fence_close_receipt(
            opened, after_deadline, now=deadline + timedelta(seconds=2)
        )
    assert late.value.code == "HOLD_FENCE_CLOSE"

    closed_at = NOW + timedelta(minutes=20)
    stale = _closed_fence(opened, closed_at)
    stale["final_fingerprint_taken_at"] = _iso(
        closed_at - timedelta(seconds=32)
    )
    stale["last_heartbeat_at"] = _iso(closed_at - timedelta(seconds=31))
    with pytest.raises(p1.P1Error) as heartbeat:
        p1.verify_fence_close_receipt(
            opened, stale, now=closed_at + timedelta(seconds=1)
        )
    assert heartbeat.value.code == "HOLD_CORPUS_FENCE_LOST"

    lost_lock = _closed_fence(opened, closed_at)
    lost_lock["locks"] = lost_lock["locks"][:-1]
    with pytest.raises(p1.P1Error) as lock:
        p1.verify_fence_close_receipt(
            opened, lost_lock, now=closed_at + timedelta(seconds=1)
        )
    assert lock.value.code == "HOLD_FENCE_CLOSE"


def _one_spec(key: str) -> p1.CallCostSpec:
    return p1.CallCostSpec.from_mapping(
        key,
        {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "max_input_tokens": 100,
            "max_output_tokens": 100,
            "input_usd_per_mtok": "3",
            "output_usd_per_mtok": "15",
            "max_cost_usd": "0.01",
        },
    )


def test_static_budget_rejects_more_than_ten_dollars():
    bundle, _, _ = _bundle()
    specs = list(bundle.budget.specs.values())
    inflated = [
        p1.CallCostSpec(
            **{
                **spec.__dict__,
                "max_cost_usd": Decimal("1"),
            }
        )
        for spec in specs
    ]
    with pytest.raises(p1.P1Error) as caught:
        p1.BudgetPlan(inflated)
    assert caught.value.code == "HOLD_STATIC_BUDGET_EXCEEDED"


def test_wal_hash_chain_and_reopen_turns_unfinished_reservation_unknown(tmp_path):
    artifact_root = tmp_path / "artifacts"
    path = artifact_root / "calls.jsonl"
    bundle, release, prereg = _bundle()
    genesis = _genesis_for(bundle, release, prereg, artifact_root)
    journal = p1.CallJournal(path, now=lambda: NOW)
    journal.bind_genesis(genesis)
    key = p1.expected_call_keys()[0]
    journal.reserve(
        call_key=key,
        request_sha256="e" * 64,
        max_cost_usd=Decimal("0.01"),
        accumulated_prior_usd=Decimal("0"),
    )
    reopened = p1.CallJournal(path, now=lambda: NOW + timedelta(seconds=1))
    reopened.bind_genesis(genesis)
    assert reopened.records[key]["state"] == "UNKNOWN_BILLED_POST_SEND"
    assert len(reopened.events) == 2
    assert reopened.events[1]["previous_event_sha256"] == reopened.events[0]["event_sha256"]


def test_wal_rejects_corruption(tmp_path):
    artifact_root = tmp_path / "artifacts"
    path = artifact_root / "calls.jsonl"
    bundle, release, prereg = _bundle()
    genesis = _genesis_for(bundle, release, prereg, artifact_root)
    journal = p1.CallJournal(path, now=lambda: NOW)
    journal.bind_genesis(genesis)
    key = p1.expected_call_keys()[0]
    journal.reserve(
        call_key=key,
        request_sha256="e" * 64,
        max_cost_usd=Decimal("0.01"),
        accumulated_prior_usd=Decimal("0"),
    )
    raw = path.read_text(encoding="utf-8").replace("RESERVED_FSYNCED", "COMPLETED")
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(p1.P1Error) as caught:
        p1.CallJournal(path)
    assert caught.value.code == "HOLD_WAL_CORRUPT"


def test_wal_rejects_orphan_atomic_claim_before_any_possible_send(tmp_path):
    artifact_root = tmp_path / "artifacts"
    path = artifact_root / "calls.jsonl"
    bundle, release, prereg = _bundle()
    genesis = _genesis_for(bundle, release, prereg, artifact_root)
    first = p1.CallJournal(path, now=lambda: NOW)
    first.bind_genesis(genesis)
    key = p1.expected_call_keys()[0]
    p1.write_json_exclusive(
        first._claim_path(key),
        {
            "call_key": key,
            "request_sha256": "e" * 64,
            "max_cost_usd": "0.01",
            "run_genesis_sha256": genesis["run_genesis_sha256"],
        },
    )
    with pytest.raises(p1.P1Error) as caught:
        reopened = p1.CallJournal(path, now=lambda: NOW)
        reopened.bind_genesis(genesis)
    assert caught.value.code == "HOLD_WAL_ORPHAN_CLAIM"


def test_authorization_claim_is_global_atomic_and_resumes_only_same_run(tmp_path):
    bundle, release, prereg = _bundle()
    run_a = tmp_path / "run-a"
    claims = p1.AuthorizationClaimStore(run_a)
    auth_a = _authorization(
        release,
        prereg,
        run_a,
        authorization_id="auth-global-test-0001",
        run_id="run-global-test-0001",
    )
    genesis_a = p1.build_run_genesis(bundle, auth_a, run_a)
    first = claims.claim(
        authorization=auth_a, genesis=genesis_a, artifact_root=run_a
    )
    resumed = claims.claim(
        authorization=auth_a, genesis=genesis_a, artifact_root=run_a
    )
    assert first.created is True
    assert resumed.created is False
    assert resumed.claim == first.claim

    drifted_auth = json.loads(json.dumps(auth_a))
    drifted_auth["authorized_by"] = "another-operator"
    drifted_genesis = p1.build_run_genesis(bundle, drifted_auth, run_a)
    with pytest.raises(p1.P1Error) as permit_drift:
        claims.claim(
            authorization=drifted_auth,
            genesis=drifted_genesis,
            artifact_root=run_a,
        )
    assert permit_drift.value.code == "HOLD_AUTHORIZATION_ALREADY_CONSUMED"

    run_b = tmp_path / "run-b"
    auth_b = _authorization(
        release,
        prereg,
        run_b,
        authorization_id="auth-global-test-0001",
        run_id="run-global-test-0001",
    )
    genesis_b = p1.build_run_genesis(bundle, auth_b, run_b)
    claims_b = p1.AuthorizationClaimStore(run_b)
    assert claims_b.root == claims.root
    with pytest.raises(p1.P1Error) as consumed:
        claims_b.claim(
            authorization=auth_b, genesis=genesis_b, artifact_root=run_b
        )
    assert consumed.value.code == "HOLD_AUTHORIZATION_ALREADY_CONSUMED"


def test_authorization_claim_store_must_be_outside_artifact_dir(tmp_path):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / "run"
    auth = _authorization(release, prereg, run_dir)
    genesis = p1.build_run_genesis(bundle, auth, run_dir)
    claims = p1.AuthorizationClaimStore(run_dir)
    claims.root = run_dir / "claims"
    claims.root.mkdir(parents=True)
    with pytest.raises(p1.P1Error) as caught:
        claims.claim(authorization=auth, genesis=genesis, artifact_root=run_dir)
    assert caught.value.code == "HOLD_RUNTIME_TOPOLOGY"


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("uninitialized", "HOLD_AUTHORIZATION_RESUME_STATE"),
        ("wal", "HOLD_AUTHORIZATION_RESUME_STATE"),
        ("wal_genesis", "HOLD_AUTHORIZATION_RESUME_STATE"),
        ("claims_dir", "HOLD_AUTHORIZATION_RESUME_STATE"),
        ("artifact_genesis", "HOLD_AUTHORIZATION_RESUME_STATE"),
        ("per_call_claim", "HOLD_WAL_CLAIM_MISSING"),
    ],
)
def test_existing_global_claim_requires_complete_canonical_resume_state(
    tmp_path, mutation, expected_code
):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / mutation
    authorization = _authorization(release, prereg, run_dir)
    genesis = p1.build_run_genesis(bundle, authorization, run_dir)
    artifacts = p1.ArtifactStore(run_dir)
    journal = p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW)
    claims = p1.AuthorizationClaimStore(run_dir)
    assert claims.claim(
        authorization=authorization,
        genesis=genesis,
        artifact_root=run_dir,
    ).created is True

    if mutation != "uninitialized":
        artifacts.bind_genesis(genesis)
        journal.bind_genesis(genesis)
    if mutation == "wal":
        journal.path.unlink()
    elif mutation == "wal_genesis":
        journal.genesis_path.unlink()
    elif mutation == "claims_dir":
        journal.claims_dir.rmdir()
    elif mutation == "artifact_genesis":
        (run_dir / "run_genesis.json").unlink()
    elif mutation == "per_call_claim":
        call_key = p1.expected_call_keys()[0]
        journal.reserve(
            call_key=call_key,
            request_sha256="e" * 64,
            max_cost_usd=Decimal("0.01"),
            accumulated_prior_usd=Decimal("0"),
        )
        journal._claim_path(call_key).unlink()

    provider = _Provider()
    resumed = p1.P1Runner(
        bundle=bundle,
        permit=p1.ExecutionPermit(True, True, True, authorization),
        artifacts=p1.ArtifactStore(run_dir),
        journal=p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW),
        provider_adapter=provider,
        replica_adapter=_ReplicaAdapter(provider),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(run_dir),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )

    with pytest.raises(p1.P1Error) as caught:
        resumed.run()

    assert caught.value.code == expected_code
    assert provider.prepares == provider.sends == []


def test_wal_and_artifact_store_reject_cross_genesis_resume(tmp_path):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / "run"
    auth_a = _authorization(release, prereg, run_dir)
    genesis_a = p1.build_run_genesis(bundle, auth_a, run_dir)
    auth_b = _authorization(
        release,
        prereg,
        run_dir,
        authorization_id="auth-p1-test-0002",
        run_id="run-p1-test-0002",
    )
    genesis_b = p1.build_run_genesis(bundle, auth_b, run_dir)
    artifacts = p1.ArtifactStore(run_dir)
    journal = p1.CallJournal(run_dir / "calls.jsonl")
    artifacts.bind_genesis(genesis_a)
    journal.bind_genesis(genesis_a)
    with pytest.raises(p1.P1Error) as artifact_drift:
        artifacts.bind_genesis(genesis_b)
    with pytest.raises(p1.P1Error) as wal_drift:
        journal.bind_genesis(genesis_b)
    assert artifact_drift.value.code == "HOLD_RUN_IDENTITY"
    assert wal_drift.value.code == "HOLD_RUN_IDENTITY"


@pytest.mark.parametrize("mutation", ["journal", "journal_genesis", "claims_dir"])
def test_runner_rejects_noncanonical_journal_or_sidecar_path_before_send(
    tmp_path, mutation
):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / "run"
    artifacts = p1.ArtifactStore(run_dir)
    journal = p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW)
    alternate = (tmp_path / "alternate").resolve()
    alternate.mkdir()
    if mutation == "journal":
        journal.path = alternate / "calls.jsonl"
    elif mutation == "journal_genesis":
        journal.genesis_path = alternate / "calls.jsonl.genesis.json"
    else:
        journal.claims_dir = alternate / "calls.jsonl.claims"
    provider = _Provider()
    runner = p1.P1Runner(
        bundle=bundle,
        permit=p1.ExecutionPermit(
            True, True, True, _authorization(release, prereg, run_dir)
        ),
        artifacts=artifacts,
        journal=journal,
        provider_adapter=provider,
        replica_adapter=_ReplicaAdapter(provider),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(run_dir),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )

    with pytest.raises(p1.P1Error) as caught:
        runner.run()

    assert caught.value.code == "HOLD_RUNTIME_TOPOLOGY"
    assert provider.prepares == provider.sends == []


@pytest.mark.parametrize("consumer", ["journal", "artifacts", "authorization"])
def test_runtime_layout_hash_is_bound_and_revalidated_by_each_store(
    tmp_path, consumer
):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / consumer
    authorization = _authorization(release, prereg, run_dir)
    genesis = p1.build_run_genesis(bundle, authorization, run_dir)
    forged = json.loads(json.dumps(genesis))
    forged["runtime_layout"]["call_journal"]["path_sha256"] = "0" * 64
    forged["runtime_layout_sha256"] = p1.sha256_json(forged["runtime_layout"])
    body = {
        key: value
        for key, value in forged.items()
        if key != "run_genesis_sha256"
    }
    forged["run_genesis_sha256"] = p1.sha256_json(body)
    p1.verify_run_genesis(forged)

    with pytest.raises(p1.P1Error) as caught:
        if consumer == "journal":
            p1.CallJournal(run_dir / "calls.jsonl").bind_genesis(forged)
        elif consumer == "artifacts":
            p1.ArtifactStore(run_dir).bind_genesis(forged)
        else:
            p1.AuthorizationClaimStore(run_dir).claim(
                authorization=authorization,
                genesis=forged,
                artifact_root=run_dir,
            )

    assert caught.value.code == "HOLD_RUNTIME_TOPOLOGY"


def test_journal_opened_before_another_writer_changes_it_is_stale(tmp_path):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / "run"
    genesis = _genesis_for(bundle, release, prereg, run_dir)
    stale = p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW)
    writer = p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW)
    writer.bind_genesis(genesis)

    with pytest.raises(p1.P1Error) as caught:
        stale.bind_genesis(genesis)

    assert caught.value.code == "HOLD_WAL_STALE_OPEN"


def test_existing_run_lease_is_never_auto_reclaimed_or_allowed_to_touch_wal(
    tmp_path,
):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / "run"
    authorization = _authorization(release, prereg, run_dir)
    genesis = p1.build_run_genesis(bundle, authorization, run_dir)
    abandoned = p1.RunLease(run_dir)
    abandoned.acquire(genesis, acquired_at=NOW - timedelta(minutes=10))
    provider = _Provider()
    runner = _runner_for_test(
        bundle=bundle,
        release=release,
        prereg=prereg,
        run_dir=run_dir,
        provider=provider,
    )

    with pytest.raises(p1.P1Error) as caught:
        runner.run()

    assert caught.value.code == "HOLD_RUN_LEASE_ACTIVE"
    assert abandoned.path.is_file()
    assert provider.prepares == provider.sends == []
    assert not (run_dir / "calls.jsonl").exists()
    assert not (run_dir / "result.json").exists()


def test_active_runner_lease_blocks_competitor_during_first_send_without_mutation(
    tmp_path,
):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / "run"
    competitor_provider = _Provider()
    competitor = _runner_for_test(
        bundle=bundle,
        release=release,
        prereg=prereg,
        run_dir=run_dir,
        provider=competitor_provider,
    )

    class _ConcurrentProbeProvider(_Provider):
        def __init__(self):
            super().__init__()
            self.attempted = False
            self.competitor_error = None
            self.wal_unchanged = None
            self.result_absent = None

        def prepare(self, call):
            prepared = super().prepare(call)

            def send():
                if not self.attempted:
                    self.attempted = True
                    wal_path = run_dir / "calls.jsonl"
                    before = wal_path.read_bytes()
                    assert not (run_dir / "result.json").exists()
                    try:
                        competitor.run()
                    except p1.P1Error as exc:
                        self.competitor_error = exc
                    self.wal_unchanged = wal_path.read_bytes() == before
                    self.result_absent = not (run_dir / "result.json").exists()
                return prepared.send()

            return _Prepared(send)

    provider = _ConcurrentProbeProvider()
    runner = _runner_for_test(
        bundle=bundle,
        release=release,
        prereg=prereg,
        run_dir=run_dir,
        provider=provider,
    )

    result = runner.run()

    assert result["status"] == "P1_REPLICAS_COMPLETE_PENDING_FENCE_CLOSE"
    assert len(provider.sends) == 81
    assert isinstance(provider.competitor_error, p1.P1Error)
    assert provider.competitor_error.code == "HOLD_RUN_LEASE_ACTIVE"
    assert provider.wal_unchanged is True
    assert provider.result_absent is True
    assert competitor_provider.prepares == competitor_provider.sends == []
    assert not p1.canonical_run_lease_path(run_dir).exists()
    loaded_result, replicas = p1.load_run_replicas(run_dir)
    assert loaded_result["result_sha256"] == result["result_sha256"]
    assert len(replicas) == 27


class _PrepareFailure:
    def __init__(self):
        self.calls = 0

    def prepare(self, _call):
        self.calls += 1
        raise ValueError("local validation")


class _SendFailure:
    def __init__(self):
        self.prepares = 0
        self.sends = 0

    def prepare(self, _call):
        self.prepares += 1

        def fail():
            self.sends += 1
            raise TimeoutError("ambiguous timeout")

        return _Prepared(fail)


def _boundary_for_first_call(tmp_path: Path, adapter):
    bundle, release, prereg = _bundle()
    artifacts = p1.ArtifactStore(tmp_path / "artifacts")
    journal = p1.CallJournal(artifacts.root / "calls.jsonl", now=lambda: NOW)
    genesis = _genesis_for(bundle, release, prereg, artifacts.root)
    lease = p1.RunLease(artifacts.root)
    lease.acquire(genesis, acquired_at=NOW)
    journal.bind_genesis(genesis)
    artifacts.bind_genesis(genesis)
    boundary = p1.ProviderBoundary(
        bundle.budget,
        journal,
        artifacts,
        adapter,
        fence_watcher=_Watcher(),
        fence_open_receipt=bundle.fence_open_receipt,
        fingerprint_receipt=bundle.fingerprint_receipt,
        run_genesis=genesis,
        run_lease=lease,
        runtime_inspector=lambda: bundle.runtime_identity,
        expected_runtime_identity=bundle.runtime_identity,
        now=lambda: NOW,
    )
    spec = next(iter(bundle.budget.specs.values()))
    input_row = p1.prereg_input_contract(bundle.prereg)["hp017"]
    payload = p1.build_operation_payload(
        operation="embedding",
        model=spec.model,
        question=input_row["question"],
        lineage_payload=input_row,
        max_output_tokens=spec.max_output_tokens,
    )
    input_bound = p1.physical_input_token_upper_bound(payload)
    lineage_sha = p1.sha256_json(input_row)
    call = p1.ProviderCall(
        call_key=spec.call_key,
        provider=spec.provider,
        model=spec.model,
        request={
            "replica_key": spec.call_key.rsplit(":", 1)[0],
            "operation": spec.call_key.rsplit(":", 1)[-1],
            "model": spec.model,
            "run_genesis_sha256": genesis["run_genesis_sha256"],
            "lineage_input_sha256": lineage_sha,
            "physical_payload": payload,
            "physical_payload_sha256": p1.sha256_json(payload),
            "input_tokens_upper_bound": input_bound,
            "max_output_tokens": spec.max_output_tokens,
        },
        run_genesis_sha256=genesis["run_genesis_sha256"],
        lineage_input_sha256=lineage_sha,
        input_tokens_upper_bound=input_bound,
        max_output_tokens=spec.max_output_tokens,
    )
    return boundary, journal, call, artifacts, bundle


def _provider_call_for(
    boundary: p1.ProviderBoundary,
    bundle: p1.PreflightBundle,
    call_key: str,
    lineage_payload,
) -> p1.ProviderCall:
    spec = bundle.budget.specs[call_key]
    operation = call_key.rsplit(":", 1)[-1]
    replica_key = call_key.rsplit(":", 1)[0]
    qid = replica_key.split(":", 1)[0]
    question = p1.prereg_input_contract(bundle.prereg)[qid]["question"]
    payload = p1.build_operation_payload(
        operation=operation,
        model=spec.model,
        question=question,
        lineage_payload=lineage_payload,
        max_output_tokens=spec.max_output_tokens,
    )
    input_bound = p1.physical_input_token_upper_bound(payload)
    lineage_sha = p1.sha256_json(lineage_payload)
    return p1.ProviderCall(
        call_key=call_key,
        provider=spec.provider,
        model=spec.model,
        request={
            "replica_key": replica_key,
            "operation": operation,
            "model": spec.model,
            "run_genesis_sha256": boundary.run_genesis[
                "run_genesis_sha256"
            ],
            "lineage_input_sha256": lineage_sha,
            "physical_payload": payload,
            "physical_payload_sha256": p1.sha256_json(payload),
            "input_tokens_upper_bound": input_bound,
            "max_output_tokens": spec.max_output_tokens,
        },
        run_genesis_sha256=boundary.run_genesis["run_genesis_sha256"],
        lineage_input_sha256=lineage_sha,
        input_tokens_upper_bound=input_bound,
        max_output_tokens=spec.max_output_tokens,
    )


def _reopen_boundary(boundary: p1.ProviderBoundary, adapter):
    return p1.ProviderBoundary(
        boundary.budget,
        boundary.journal,
        boundary.artifacts,
        adapter,
        fence_watcher=boundary.fence_watcher,
        fence_open_receipt=boundary.fence_open_receipt,
        fingerprint_receipt=boundary.fingerprint_receipt,
        run_genesis=boundary.run_genesis,
        run_lease=boundary.run_lease,
        runtime_inspector=boundary.runtime_inspector,
        expected_runtime_identity=boundary.expected_runtime_identity,
        now=lambda: NOW,
    )


def test_boundary_classifies_pre_send_failure_and_never_retries(tmp_path):
    adapter = _PrepareFailure()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, adapter)
    with pytest.raises(p1.NoRetryError):
        boundary.invoke(call)
    assert journal.records[call.call_key]["state"] == "FAILED_PRE_SEND_NO_RETRY"
    with pytest.raises(p1.NoRetryError):
        boundary.invoke(call)
    assert adapter.calls == 1


@pytest.mark.parametrize(
    "runtime_mode,expected_code",
    [
        ("drift", "HOLD_RUNTIME_IDENTITY_DRIFT"),
        ("exception", "HOLD_RUNTIME_INSPECTION_FAILED"),
    ],
)
def test_runtime_is_reinspected_after_prepare_and_before_send(
    tmp_path, runtime_mode, expected_code
):
    provider = _Provider()
    boundary, journal, call, _, bundle = _boundary_for_first_call(
        tmp_path, provider
    )
    if runtime_mode == "drift":
        boundary.runtime_inspector = lambda: p1.RuntimeIdentity(
            "c" * 40, bundle.runtime_identity.tree_sha, True, True
        )
    else:
        def fail_inspection():
            raise OSError("runtime unavailable")

        boundary.runtime_inspector = fail_inspection

    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(call)

    assert caught.value.code == expected_code
    assert provider.prepares == [call.call_key]
    assert provider.sends == []
    assert journal.records[call.call_key]["state"] == "FAILED_PRE_SEND_NO_RETRY"


def test_prepare_cannot_mutate_reserved_request_before_send(tmp_path):
    class _MutatingPrepare:
        def __init__(self):
            self.prepares = 0
            self.sends = 0

        def prepare(self, call):
            self.prepares += 1
            call.request["physical_payload"]["texts"][0] = "mutated after reserve"

            def send():
                self.sends += 1
                return {}

            return _Prepared(send)

    adapter = _MutatingPrepare()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, adapter)

    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(call)

    assert caught.value.code == "HOLD_REQUEST_PREPARE_DRIFT"
    assert adapter.prepares == 1
    assert adapter.sends == 0
    assert journal.records[call.call_key]["state"] == "FAILED_PRE_SEND_NO_RETRY"


def test_lease_ownership_is_revalidated_after_prepare_and_before_send(tmp_path):
    class _LeaseRemovingPrepare:
        def __init__(self):
            self.boundary = None
            self.prepares = 0
            self.sends = 0

        def prepare(self, _call):
            self.prepares += 1
            self.boundary.run_lease.path.unlink()

            def send():
                self.sends += 1
                return {}

            return _Prepared(send)

    adapter = _LeaseRemovingPrepare()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, adapter)
    adapter.boundary = boundary

    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(call)

    assert caught.value.code == "HOLD_RUN_LEASE_DRIFT"
    assert adapter.prepares == 1
    assert adapter.sends == 0
    assert journal.records[call.call_key]["state"] == "FAILED_PRE_SEND_NO_RETRY"


def test_boundary_classifies_every_post_delegation_exception_unknown(tmp_path):
    adapter = _SendFailure()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, adapter)
    with pytest.raises(p1.NoRetryError):
        boundary.invoke(call)
    assert adapter.prepares == adapter.sends == 1
    assert journal.records[call.call_key]["state"] == "UNKNOWN_BILLED_POST_SEND"
    with pytest.raises(p1.NoRetryError):
        boundary.invoke(call)
    assert adapter.sends == 1


def test_unknown_call_globally_blocks_every_later_new_call_before_prepare(tmp_path):
    adapter = _SendFailure()
    boundary, journal, first_call, _, bundle = _boundary_for_first_call(
        tmp_path, adapter
    )
    with pytest.raises(p1.NoRetryError):
        boundary.invoke(first_call)
    assert journal.records[first_call.call_key]["state"] == "UNKNOWN_BILLED_POST_SEND"
    second_key = p1.expected_call_keys()[1]
    second_call = _provider_call_for(
        boundary, bundle, second_key, [{"id": "pool-1"}]
    )

    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(second_call)

    assert caught.value.code == "HOLD_PRIOR_TERMINAL_CALL"
    assert adapter.prepares == adapter.sends == 1
    assert second_key not in journal.records


def test_out_of_order_registered_call_is_blocked_before_reserve_or_prepare(tmp_path):
    provider = _Provider()
    boundary, journal, _first_call, _, bundle = _boundary_for_first_call(
        tmp_path, provider
    )
    out_of_order_key = p1.expected_call_keys()[1]
    out_of_order = _provider_call_for(
        boundary, bundle, out_of_order_key, [{"id": "pool-1"}]
    )

    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(out_of_order)

    assert caught.value.code == "HOLD_CALL_ORDER_DRIFT"
    assert provider.prepares == provider.sends == []
    assert journal.records == {}


def test_completed_call_resumes_only_from_fsynced_response(tmp_path):
    provider = _Provider()
    boundary, journal, call, artifacts, bundle = _boundary_for_first_call(
        tmp_path, provider
    )
    first = boundary.invoke(call)
    assert journal.records[call.call_key]["state"] == "COMPLETED"
    bomb = _PrepareFailure()
    resumed_boundary = _reopen_boundary(boundary, bomb)
    resumed = resumed_boundary.invoke(call)
    assert resumed["_p1_resumed_from_receipt"] is True
    assert resumed["id"] == first["id"]
    assert bomb.calls == 0
    assert provider.sends == [call.call_key]


def test_completed_resume_rejects_current_request_hash_drift_without_send(tmp_path):
    provider = _Provider()
    boundary, journal, call, artifacts, bundle = _boundary_for_first_call(
        tmp_path, provider
    )
    boundary.invoke(call)
    drifted_payload = {**call.request["physical_payload"], "texts": ["drift"]}
    drifted_bound = p1.physical_input_token_upper_bound(drifted_payload)
    drifted_request = {
        **call.request,
        "physical_payload": drifted_payload,
        "physical_payload_sha256": p1.sha256_json(drifted_payload),
        "input_tokens_upper_bound": drifted_bound,
    }
    drifted = p1.ProviderCall(
        call_key=call.call_key,
        provider=call.provider,
        model=call.model,
        request=drifted_request,
        run_genesis_sha256=call.run_genesis_sha256,
        lineage_input_sha256=call.lineage_input_sha256,
        input_tokens_upper_bound=drifted_bound,
        max_output_tokens=call.max_output_tokens,
    )
    bomb = _PrepareFailure()
    resumed = _reopen_boundary(boundary, bomb)

    with pytest.raises(p1.P1Error) as caught:
        resumed.invoke(drifted)

    assert caught.value.code == "HOLD_REQUEST_REPLAY_DRIFT"
    assert bomb.calls == 0
    assert provider.sends == [call.call_key]


def test_frozen_embedding_question_drift_is_rejected_before_prepare(tmp_path):
    provider = _Provider()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, provider)
    drifted_payload = {**call.request["physical_payload"], "texts": ["pregunta sustituida"]}
    drifted_bound = p1.physical_input_token_upper_bound(drifted_payload)
    drifted_request = {
        **call.request,
        "physical_payload": drifted_payload,
        "physical_payload_sha256": p1.sha256_json(drifted_payload),
        "input_tokens_upper_bound": drifted_bound,
    }
    drifted = p1.ProviderCall(
        call_key=call.call_key,
        provider=call.provider,
        model=call.model,
        request=drifted_request,
        run_genesis_sha256=call.run_genesis_sha256,
        lineage_input_sha256=call.lineage_input_sha256,
        input_tokens_upper_bound=drifted_bound,
        max_output_tokens=call.max_output_tokens,
    )

    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(drifted)

    assert caught.value.code == "HOLD_INPUT_REQUEST_BINDING"
    assert provider.prepares == provider.sends == []
    assert journal.records == {}


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("input_tokens_upper_bound", 1001, "HOLD_INPUT_TOKEN_BOUND"),
        ("max_output_tokens", 1, "HOLD_OUTPUT_TOKEN_BOUND"),
    ],
)
def test_pre_send_token_envelope_drift_is_rejected_before_prepare(
    tmp_path, field, value, code
):
    adapter = _PrepareFailure()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, adapter)
    values = {
        "call_key": call.call_key,
        "provider": call.provider,
        "model": call.model,
        "request": {**call.request, field: value},
        "run_genesis_sha256": call.run_genesis_sha256,
        "lineage_input_sha256": call.lineage_input_sha256,
        "input_tokens_upper_bound": call.input_tokens_upper_bound,
        "max_output_tokens": call.max_output_tokens,
    }
    values[field] = value
    drifted = p1.ProviderCall(**values)

    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(drifted)

    assert caught.value.code == code
    assert adapter.calls == 0
    assert journal.records == {}


def test_oversized_physical_payload_is_blocked_before_prepare(tmp_path):
    provider = _Provider()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, provider)
    oversized_payload = {
        **call.request["physical_payload"],
        "texts": ["x" * 20_000],
    }
    oversized_bound = p1.physical_input_token_upper_bound(oversized_payload)
    request = {
        **call.request,
        "physical_payload": oversized_payload,
        "physical_payload_sha256": p1.sha256_json(oversized_payload),
        "input_tokens_upper_bound": oversized_bound,
    }
    oversized = p1.ProviderCall(
        call_key=call.call_key,
        provider=call.provider,
        model=call.model,
        request=request,
        run_genesis_sha256=call.run_genesis_sha256,
        lineage_input_sha256=call.lineage_input_sha256,
        input_tokens_upper_bound=oversized_bound,
        max_output_tokens=call.max_output_tokens,
    )
    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(oversized)
    assert caught.value.code == "HOLD_INPUT_TOKEN_BOUND"
    assert provider.prepares == provider.sends == []
    assert journal.records == {}


@pytest.mark.parametrize("mutation", ["relations", "run_genesis", "stale"])
def test_strong_fence_watch_is_required_inside_boundary_before_prepare(
    tmp_path, mutation
):
    provider = _Provider()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, provider)
    boundary.fence_watcher = _Watcher(mutation=mutation)
    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(call)
    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert provider.prepares == provider.sends == []
    assert journal.records[call.call_key]["state"] == "FAILED_PRE_SEND_NO_RETRY"


def test_fingerprint_expiry_is_rechecked_before_every_prepare(tmp_path):
    provider = _Provider()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, provider)
    boundary.fingerprint_receipt["expires_at"] = _iso(NOW)
    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(call)
    assert caught.value.code == "HOLD_FINGERPRINT_EXPIRED"
    assert provider.prepares == provider.sends == []
    assert journal.records == {}


def test_watch_receipt_is_revalidated_immediately_before_send(tmp_path):
    provider = _Provider()
    boundary, journal, call, _, _ = _boundary_for_first_call(tmp_path, provider)
    moments = iter([NOW, NOW, NOW + timedelta(seconds=3)])
    boundary._now = lambda: next(moments)
    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(call)
    assert caught.value.code == "HOLD_CORPUS_FENCE_LOST"
    assert provider.prepares == [call.call_key]
    assert provider.sends == []
    assert journal.records[call.call_key]["state"] == "FAILED_PRE_SEND_NO_RETRY"


def test_physical_usage_cannot_exceed_derived_input_bound(tmp_path):
    class _UsageAboveDerived:
        def prepare(self, current):
            return _Prepared(
                lambda: {
                    "id": "over-derived-bound",
                    "model": current.model,
                    "usage": {
                        "input_tokens": current.input_tokens_upper_bound + 1,
                        "output_tokens": 0,
                    },
                }
            )

    boundary, journal, call, _, _ = _boundary_for_first_call(
        tmp_path, _UsageAboveDerived()
    )

    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(call)

    assert caught.value.code == "NO_GO_DECLARED_INPUT_BOUND_BREACH"
    assert journal.records[call.call_key]["state"] == "COMPLETED"


def test_second_successful_invocation_never_delegates_twice(tmp_path):
    provider = _Provider()
    boundary, _, call, _, _ = _boundary_for_first_call(tmp_path, provider)
    boundary.invoke(call)
    boundary.invoke(call)
    assert provider.prepares == [call.call_key]
    assert provider.sends == [call.call_key]


class _BadPhysicalResponse:
    def __init__(
        self, *, wrong_model=False, excessive_usage=False, excessive_output=False
    ):
        self.wrong_model = wrong_model
        self.excessive_usage = excessive_usage
        self.excessive_output = excessive_output

    def prepare(self, call):
        return _Prepared(
            lambda: {
                "id": "bad-but-physical",
                "model": "unexpected-model" if self.wrong_model else call.model,
                "usage": {
                    "input_tokens": 100_000_000 if self.excessive_usage else 100,
                    "output_tokens": 1 if self.excessive_output else 0,
                },
            }
        )


@pytest.mark.parametrize(
    "adapter,code",
    [
        (_BadPhysicalResponse(wrong_model=True), "NO_GO_MODEL_DRIFT"),
        (
            _BadPhysicalResponse(excessive_usage=True),
            "NO_GO_INPUT_TOKEN_BOUND_BREACH",
        ),
        (
            _BadPhysicalResponse(excessive_output=True),
            "NO_GO_OUTPUT_TOKEN_BOUND_BREACH",
        ),
    ],
)
def test_model_or_cost_mismatch_is_detected_only_after_response_is_fsynced(
    tmp_path, adapter, code
):
    boundary, journal, call, artifacts, _ = _boundary_for_first_call(
        tmp_path, adapter
    )
    with pytest.raises(p1.P1Error) as caught:
        boundary.invoke(call)
    assert caught.value.code == code
    record = journal.records[call.call_key]
    assert record["state"] == "COMPLETED"
    response_path = artifacts.root / record["response_path"]
    assert response_path.is_file()
    assert hashlib.sha256(response_path.read_bytes()).hexdigest() == record["response_sha256"]
    # A later process revalidates the stored physical response and still cannot send.
    bomb = _PrepareFailure()
    resumed = _reopen_boundary(boundary, bomb)
    with pytest.raises(p1.P1Error) as repeated:
        resumed.invoke(call)
    assert repeated.value.code == code
    assert bomb.calls == 0


@pytest.mark.parametrize("execute,confirm,expected", [
    (False, False, "HOLD_EXECUTE_OPT_IN_REQUIRED"),
    (True, False, "HOLD_PAID_OPT_IN_REQUIRED"),
])
def test_paid_permit_requires_both_independent_opt_ins(execute, confirm, expected):
    bundle, release, prereg = _bundle()
    permit = p1.ExecutionPermit(
        execute=execute,
        confirm_paid=confirm,
        credentials_present=True,
        authorization=_authorization(release, prereg),
    )
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_execution_permit(
            permit,
            release_config_sha256=bundle.release_config_sha256,
            prereg_sha256=bundle.prereg_sha256,
            now=NOW,
        )
    assert caught.value.code == expected


def test_execution_permit_deep_copies_and_seals_authorization():
    bundle, release, prereg = _bundle()
    source = _authorization(release, prereg)
    permit = p1.ExecutionPermit(True, True, True, source)
    source["prepaid_known_conflict"]["rationale"] = "external mutation"
    verified = p1.verify_execution_permit(
        permit,
        release_config_sha256=bundle.release_config_sha256,
        prereg_sha256=bundle.prereg_sha256,
        stored_control_score_sha256=bundle.stored_control_score_sha256,
        now=NOW,
    )
    assert verified["prepaid_known_conflict"]["rationale"] != "external mutation"

    permit.authorization["prepaid_known_conflict"]["rationale"] = "internal drift"
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_execution_permit(
            permit,
            release_config_sha256=bundle.release_config_sha256,
            prereg_sha256=bundle.prereg_sha256,
            stored_control_score_sha256=bundle.stored_control_score_sha256,
            now=NOW,
        )
    assert caught.value.code == "HOLD_PAID_AUTHORIZATION_DRIFT"


def test_paid_permit_requires_explicit_disposition_of_known_hp017_prior():
    bundle, release, prereg = _bundle()
    authorization = _authorization(release, prereg)
    authorization.pop("prepaid_known_conflict")
    with pytest.raises(p1.P1Error) as caught:
        p1.verify_execution_permit(
            p1.ExecutionPermit(True, True, True, authorization),
            release_config_sha256=bundle.release_config_sha256,
            prereg_sha256=bundle.prereg_sha256,
            now=NOW,
        )
    assert caught.value.code == "HOLD_PREPAID_KNOWN_CONFLICT_RISK"


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("input", "NO_GO_INPUT_DRIFT"),
        ("request_input_hash", "NO_GO_INPUT_REQUEST_BINDING"),
        ("detached_answer", "NO_GO_GENERATION_CHAIN"),
        ("provider_top", "NO_GO_PROVIDER_RECEIPT_DRIFT"),
        ("max_tokens_masquerading_end_turn", "NO_GO_SYNTHESIS_TOKEN_BOUND"),
        ("stage_link", "NO_GO_GENERATION_CHAIN"),
        ("render_hash", "NO_GO_RENDER_DRIFT"),
        ("render_recomputed_forgery", "NO_GO_RENDER_DRIFT"),
        ("lineage_pool", "NO_GO_RERANK_LINEAGE"),
        ("effective_config", "NO_GO_EFFECTIVE_CONFIG_DRIFT"),
        ("run_identity", "NO_GO_RUN_IDENTITY_DRIFT"),
        ("visual_executed_off", "NO_GO_VISUAL_SIDE_PATH_EXECUTED"),
    ],
)
def test_runner_rejects_mutated_input_generation_provider_and_render_receipts(
    tmp_path, mutation, expected_code
):
    bundle, release, prereg = _bundle()
    provider = _Provider()
    run_dir = tmp_path / mutation
    runner = p1.P1Runner(
        bundle=bundle,
        permit=p1.ExecutionPermit(
            True, True, True, _authorization(release, prereg, run_dir)
        ),
        artifacts=p1.ArtifactStore(run_dir),
        journal=p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW),
        provider_adapter=provider,
        replica_adapter=_ReceiptMutationAdapter(provider, mutation),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(run_dir),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )

    result = runner.run()

    assert result["status"] == "NO_GO_PARTIAL"
    assert result["code"] == expected_code
    assert len(provider.sends) == 3


def test_visual_on_extends_exact_fence_get_surface_and_receipts_side_path(tmp_path):
    bundle, release, prereg = _visual_bundle()
    semantic = release["derived_config"]["target_semantic_config"]
    surface = p1.expected_surface(semantic)
    assert surface["relations"] == [
        *p1.BASE_FENCE_RELATIONS,
        p1.VISUAL_FENCE_RELATION,
    ]
    assert surface["rest_get_allowlist"][-1] == p1.VISUAL_REST_GET_SURFACE
    assert bundle.fence_open_receipt["relations"] == surface["relations"]

    run_dir = tmp_path / "visual-run"
    authorization = _authorization(release, prereg, run_dir)
    genesis = p1.build_run_genesis(bundle, authorization, run_dir)
    artifacts = p1.ArtifactStore(run_dir)
    journal = p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW)
    lease = p1.RunLease(run_dir)
    lease.acquire(genesis, acquired_at=NOW)
    artifacts.bind_genesis(genesis)
    journal.bind_genesis(genesis)
    provider = _Provider()
    boundary = p1.ProviderBoundary(
        bundle.budget,
        journal,
        artifacts,
        provider,
        fence_watcher=_Watcher(),
        fence_open_receipt=bundle.fence_open_receipt,
        fingerprint_receipt=bundle.fingerprint_receipt,
        run_genesis=genesis,
        run_lease=lease,
        runtime_inspector=lambda: bundle.runtime_identity,
        expected_runtime_identity=bundle.runtime_identity,
        now=lambda: NOW,
    )
    replica = p1.REPLICAS[0]
    receipt = _ReplicaAdapter(provider).execute_replica(replica, boundary)
    p1.validate_replica_receipt(
        receipt,
        replica,
        release["models"],
        expected_input=p1.prereg_input_contract(prereg)[replica.qid],
        synthesis_spec=bundle.budget.specs[f"{replica.key}:synthesis"],
        expected_run_genesis=genesis,
        expected_effective_config=semantic,
    )
    assert receipt["visual_assets"]["enabled"] is True
    assert receipt["visual_assets"]["status"] == "evaluated"
    assert receipt["visual_assets"]["rest_get_surface"] == [
        p1.VISUAL_REST_GET_SURFACE
    ]
    assert receipt["visual_assets"]["lookup_receipts"] == []
    assert provider.sends == [f"{replica.key}:{op}" for op in p1.CALL_OPERATIONS]


def test_injected_runner_executes_exactly_27_by_three_and_stops_before_go(
    tmp_path, monkeypatch
):
    bundle, release, prereg = _bundle()
    provider = _Provider()
    watcher = _Watcher()
    artifacts = p1.ArtifactStore(tmp_path / "run")
    journal = p1.CallJournal(tmp_path / "run" / "calls.jsonl", now=lambda: NOW)
    authorization = _authorization(release, prereg, artifacts.root)
    permit = p1.ExecutionPermit(
        execute=True,
        confirm_paid=True,
        credentials_present=True,
        authorization=authorization,
    )
    runner = p1.P1Runner(
        bundle=bundle,
        permit=permit,
        artifacts=artifacts,
        journal=journal,
        provider_adapter=provider,
        replica_adapter=_ReplicaAdapter(provider),
        fence_watcher=watcher,
        authorization_claims=p1.AuthorizationClaimStore(artifacts.root),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )
    result = runner.run()
    assert result["status"] == "P1_REPLICAS_COMPLETE_PENDING_FENCE_CLOSE"
    assert result["code"] == "HOLD_PENDING_FINAL_FINGERPRINT_AND_FENCE_CLOSE"
    assert result["replicas_persisted"] == 27
    assert result["p1_completed_at"] is None
    assert result["p1_expires_at"] is None
    assert len(provider.prepares) == len(provider.sends) == 81
    assert provider.sends == list(p1.expected_call_keys())
    assert len(journal.records) == 81
    assert set(row["state"] for row in journal.records.values()) == {"COMPLETED"}
    assert len(
        [call for call in watcher.calls if call[0] == "before_provider_send"]
    ) == 81
    stored = json.loads((tmp_path / "run" / "result.json").read_text(encoding="utf-8"))
    seal = stored.pop("result_sha256")
    assert seal == p1.sha256_json(stored)
    sends_before_resume = list(provider.sends)
    assert runner.run()["result_sha256"] == result["result_sha256"]
    assert provider.sends == sends_before_resume

    # A fresh process may resume the same durable topology and must replay the
    # completed result without reaching a provider adapter.
    resumed_provider = _Provider()
    resumed_runner = p1.P1Runner(
        bundle=bundle,
        permit=permit,
        artifacts=p1.ArtifactStore(artifacts.root),
        journal=p1.CallJournal(artifacts.root / "calls.jsonl", now=lambda: NOW),
        provider_adapter=resumed_provider,
        replica_adapter=_ReplicaAdapter(resumed_provider),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(artifacts.root),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )
    assert resumed_runner.run()["result_sha256"] == result["result_sha256"]
    assert resumed_provider.prepares == resumed_provider.sends == []

    first_record = journal.records[p1.expected_call_keys()[0]]
    first_physical_response = artifacts.root / first_record["response_path"]
    physical_bytes = first_physical_response.read_bytes()
    first_physical_response.unlink()
    with pytest.raises(p1.P1Error) as physical_drift:
        resumed_runner.run()
    assert physical_drift.value.code == "HOLD_RUN_ARTIFACT_DRIFT"
    assert resumed_provider.prepares == resumed_provider.sends == []
    assert p1.canonical_run_lease_path(artifacts.root).is_file()
    first_physical_response.write_bytes(physical_bytes)

    # The same permit and artifact root cannot be redirected to a second WAL.
    shadow_provider = _Provider()
    shadow_runner = p1.P1Runner(
        bundle=bundle,
        permit=permit,
        artifacts=p1.ArtifactStore(artifacts.root),
        journal=p1.CallJournal(tmp_path / "shadow" / "calls.jsonl", now=lambda: NOW),
        provider_adapter=shadow_provider,
        replica_adapter=_ReplicaAdapter(shadow_provider),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(artifacts.root),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )
    with pytest.raises(p1.P1Error) as shadow:
        shadow_runner.run()
    assert shadow.value.code == "HOLD_RUNTIME_TOPOLOGY"
    assert shadow_provider.prepares == shadow_provider.sends == []

    # Nor can an injected claim-store root bypass the canonical global ledger.
    injected_claims = p1.AuthorizationClaimStore(artifacts.root)
    injected_claims.root = tmp_path / "injected-claims"
    injected_claims.root.mkdir()
    claim_provider = _Provider()
    claim_runner = p1.P1Runner(
        bundle=bundle,
        permit=permit,
        artifacts=p1.ArtifactStore(artifacts.root),
        journal=p1.CallJournal(artifacts.root / "calls.jsonl", now=lambda: NOW),
        provider_adapter=claim_provider,
        replica_adapter=_ReplicaAdapter(claim_provider),
        fence_watcher=_Watcher(),
        authorization_claims=injected_claims,
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )
    with pytest.raises(p1.P1Error) as injected:
        claim_runner.run()
    assert injected.value.code == "HOLD_RUNTIME_TOPOLOGY"
    assert claim_provider.prepares == claim_provider.sends == []
    loaded_result, loaded_replicas = p1.load_run_replicas(tmp_path / "run")
    assert loaded_result["result_sha256"] == result["result_sha256"]
    assert [row["replica_key"] for row in loaded_replicas] == list(p1.REPLICA_ORDER)

    from scripts import s277_c1_p1_scorer as scorer

    # Cross the validator/scorer boundary with the real scorer. The synthetic
    # provider does not contain enough fact evidence for an overall PASS, but
    # its accepted hp017 receipt must make the coverage leaf satisfiable.
    _selected_prereg, contract, bindings = p1._authoritative_scoring_inputs(
        loaded_result
    )
    hp017_score = scorer.score_hp017_case(loaded_replicas[0], contract)
    coverage_leaf = next(
        row
        for row in hp017_score.evidence["checks"]
        if row["check_id"] == "hp017_coverage"
    )
    assert coverage_leaf["status"] == scorer.PASS
    real_score = scorer.score_run(loaded_replicas, contract, bindings=bindings)
    assert real_score["status"] == scorer.INSTRUMENT_ERROR

    real_score_path = tmp_path / "real-score.json"
    p1._cli_score(
        p1.argparse.Namespace(
            run_dir=str(tmp_path / "run"),
            prereg=str(p1.CANONICAL_PREREG_PATH),
            output=str(real_score_path),
        )
    )
    assert p1.load_json_object(real_score_path) == real_score

    # Overall P1 success is a separate finalization step. First prove that a
    # caller-supplied PASS cannot replace the real authoritative score.
    score = {
        "schema_version": scorer.SCHEMA_VERSION,
        "scorer_sha256": scorer.scorer_sha256(),
        "status": "PASS",
        "decision": "PASS",
        "review_items": [],
        "claim": "NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS",
        "run_result_sha256": result["result_sha256"],
    }
    score_path = tmp_path / "score.json"
    open_path = tmp_path / "fence-open.json"
    close_path = tmp_path / "fence-close.json"
    p1.write_json_exclusive(score_path, score)
    p1.write_json_exclusive(open_path, bundle.fence_open_receipt)
    opened = bundle.fence_open_receipt
    close = _closed_fence(opened, NOW)
    p1.write_json_exclusive(close_path, close)

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = NOW + timedelta(seconds=1)
            return value if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr(p1, "datetime", _FrozenDateTime)
    finalize_args = p1.argparse.Namespace(
        run_dir=str(tmp_path / "run"),
        score=str(score_path),
        fence_open_receipt=str(open_path),
        fence_close_receipt=str(close_path),
        adjudication=None,
        output=str(tmp_path / "forged-final.json"),
    )
    with pytest.raises(p1.P1Error) as forged:
        p1._finalize_after_verified_live_manifest(finalize_args)
    assert forged.value.code == "HOLD_SCORE_ARTIFACT_DRIFT"

    # Narrow state-machine coverage only: this explicit double exercises the
    # PASS/fence branch and is not evidence that the synthetic run scored PASS.
    monkeypatch.setattr(scorer, "score_run", _test_authoritative_pass_score)
    authoritative_path = tmp_path / "authoritative-score.json"
    p1._cli_score(
        p1.argparse.Namespace(
            run_dir=str(tmp_path / "run"),
            prereg=str(p1.CANONICAL_PREREG_PATH),
            output=str(authoritative_path),
        )
    )
    finalize_args.score = str(authoritative_path)
    finalize_args.output = str(tmp_path / "final.json")
    finalized = p1._finalize_after_verified_live_manifest(finalize_args)
    assert finalized["status"] == "P1_PASS"
    assert finalized["p1_completed_at"] == _iso(NOW)
    assert finalized["p1_expires_at"] == _iso(NOW + timedelta(hours=6))
    assert finalized["release_deployed"] is False
    assert finalized["post_activation_canary_complete"] is False

    first_receipt = tmp_path / "run" / result["replica_receipts"][0]["path"]
    first_receipt.write_bytes(first_receipt.read_bytes() + b" ")
    with pytest.raises(p1.P1Error) as tampered:
        p1.load_run_replicas(tmp_path / "run")
    assert tampered.value.code == "HOLD_RUN_ARTIFACT_DRIFT"


def _materialize_complete_run(run_dir: Path, *, at: datetime = NOW):
    bundle, release, prereg = _bundle()
    provider = _Provider()
    run_suffix = hashlib.sha256(str(run_dir.resolve()).encode()).hexdigest()[:12]
    runner = p1.P1Runner(
        bundle=bundle,
        permit=p1.ExecutionPermit(
            True,
            True,
            True,
            _authorization(
                release,
                prereg,
                run_dir,
                authorization_id=f"auth-p1-{run_suffix}",
                run_id=f"run-p1-{run_suffix}",
            ),
        ),
        artifacts=p1.ArtifactStore(run_dir),
        journal=p1.CallJournal(run_dir / "calls.jsonl", now=lambda: at),
        provider_adapter=provider,
        replica_adapter=_ReplicaAdapter(provider),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(run_dir),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: at,
    )
    result = runner.run()
    assert result["status"] == "P1_REPLICAS_COMPLETE_PENDING_FENCE_CLOSE"
    assert len(provider.sends) == 81
    return bundle, result


def test_offline_gate_reopens_every_wal_physical_call_artifact_fail_closed(
    tmp_path,
):
    run_dir = tmp_path / "run"
    _bundle_value, result = _materialize_complete_run(run_dir)
    genesis = p1.load_json_object(run_dir / "run_genesis.json")
    journal = p1.CallJournal(run_dir / "calls.jsonl")
    journal.bind_genesis(genesis)
    first = journal.records[p1.expected_call_keys()[0]]

    for field in ("response_path", "fence_watch_path"):
        path = run_dir / first[field]
        original = path.read_bytes()
        path.unlink()
        with pytest.raises(p1.P1Error) as missing:
            p1.load_run_replicas(run_dir)
        assert missing.value.code == "HOLD_RUN_ARTIFACT_DRIFT"
        path.write_bytes(original)

        path.write_bytes(original + b" ")
        with pytest.raises(p1.P1Error) as corrupt:
            p1.load_run_replicas(run_dir)
        assert corrupt.value.code == "HOLD_RUN_ARTIFACT_DRIFT"
        path.write_bytes(original)

    for dirname in ("provider_responses", "fence_watches"):
        extra = run_dir / dirname / "unexpected.json"
        p1.write_json_exclusive(extra, {"unexpected": True})
        with pytest.raises(p1.P1Error) as unexpected:
            p1.load_run_replicas(run_dir)
        assert unexpected.value.code == "HOLD_RUN_ARTIFACT_DRIFT"
        extra.unlink()

    first_manifest = result["replica_receipts"][0]
    replica_path = run_dir / first_manifest["path"]
    replica = p1.load_json_object(replica_path)
    replica["retrieval"]["embedding_receipt"]["id"] = "forged-physical-binding"
    replica_path.write_bytes(p1.canonical_json_bytes(replica) + b"\n")
    rewritten_result = p1.load_json_object(run_dir / "result.json")
    rewritten_result["replica_receipts"][0]["sha256"] = hashlib.sha256(
        replica_path.read_bytes()
    ).hexdigest()
    rewritten_result.pop("result_sha256")
    rewritten_result["result_sha256"] = p1.sha256_json(rewritten_result)
    (run_dir / "result.json").write_bytes(
        p1.canonical_json_bytes(rewritten_result) + b"\n"
    )

    with pytest.raises(p1.P1Error) as cross_binding:
        p1.load_run_replicas(run_dir)
    assert cross_binding.value.code == "HOLD_RUN_ARTIFACT_DRIFT"


def test_completed_call_artifact_paths_are_derived_only_from_call_key(tmp_path):
    bundle, release, prereg = _bundle()
    run_dir = tmp_path / "run"
    authorization = _authorization(release, prereg, run_dir)
    genesis = p1.build_run_genesis(bundle, authorization, run_dir)
    artifacts = p1.ArtifactStore(run_dir)
    artifacts.bind_genesis(genesis)
    call_key = p1.expected_call_keys()[0]
    forged_record = {
        "state": "COMPLETED",
        "response_path": "provider_responses/alternate.json",
        "response_sha256": "0" * 64,
        "fence_watch_path": "fence_watches/alternate.json",
        "fence_watch_sha256": "0" * 64,
    }

    with pytest.raises(p1.P1Error) as caught:
        artifacts.load_completed_call_artifacts(call_key, forged_record)

    assert caught.value.code == "HOLD_RUN_ARTIFACT_DRIFT"


def test_cli_score_binds_canonical_prereg_contract_run_and_replica_manifest(tmp_path):
    run_dir = tmp_path / "run"
    _bundle_value, result = _materialize_complete_run(run_dir)
    output = tmp_path / "score.json"

    p1._cli_score(
        p1.argparse.Namespace(
            run_dir=str(run_dir),
            prereg=str(p1.CANONICAL_PREREG_PATH),
            output=str(output),
        )
    )

    score = p1.load_json_object(output)
    prereg = p1.load_data_object(p1.CANONICAL_PREREG_PATH)
    fact_spec = prereg["sealed_inputs"]["fact_contract"]
    assert score["score_bindings"] == {
        "run_result_sha256": result["result_sha256"],
        "prereg_sha256": p1.sha256_json(prereg),
        "fact_contract_sha256_lf": fact_spec["sha256_lf"],
        "fact_contract_payload_sha256": fact_spec["payload_sha256"],
        "replica_manifest_sha256": p1.sha256_json(result["replica_receipts"]),
    }
    assert score["replicas_sha256"] == p1.sha256_json(
        p1.load_run_replicas(run_dir)[1]
    )


def test_offline_load_revalidates_all_27_against_genesis_snapshot(
    tmp_path, monkeypatch
):
    run_dir = tmp_path / "run"
    _bundle_value, result = _materialize_complete_run(run_dir)
    genesis = p1.load_json_object(run_dir / "run_genesis.json")
    snapshot = genesis["validation_snapshot"]
    assert result["validation_snapshot_sha256"] == p1.sha256_json(snapshot)
    assert result["implementation_hashes_sha256"] == snapshot[
        "implementation_hashes_sha256"
    ]

    calls: list[str] = []
    original = p1.validate_replica_receipt

    def observed(receipt, replica, models, **kwargs):
        calls.append(replica.key)
        return original(receipt, replica, models, **kwargs)

    monkeypatch.setattr(p1, "validate_replica_receipt", observed)
    p1.load_run_replicas(run_dir)
    assert calls == list(p1.REPLICA_ORDER)


def _overwrite_canonical_json(path: Path, value: dict) -> None:
    path.write_bytes(p1.canonical_json_bytes(value) + b"\n")


def _load_wal_events(run_dir: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (run_dir / "calls.jsonl").read_bytes().splitlines()
    ]


def _reseal_complete_run_for_adversarial_test(
    run_dir: Path,
    events: list[dict],
    result: dict,
    *,
    recompute_accounting: bool = False,
) -> None:
    if recompute_accounting:
        prior = Decimal("0")
        for index in range(0, len(events), 2):
            events[index]["accumulated_prior_usd"] = p1._money(prior)
            prior += p1._decimal(
                events[index + 1]["actual_cost_usd"], field="test actual"
            )
        result["budget"] = {
            "cap_usd": "10.00",
            "observed_list_price_usd": p1._money(prior),
            "unknown_reserved_usd": "0",
            "projected_total_usd": p1._money(prior),
        }

    previous = None
    raw_lines: list[bytes] = []
    for sequence, event in enumerate(events, 1):
        if event["state"] == "COMPLETED":
            response = run_dir / event["response_path"]
            watch = run_dir / event["fence_watch_path"]
            event["response_sha256"] = hashlib.sha256(response.read_bytes()).hexdigest()
            event["fence_watch_sha256"] = hashlib.sha256(watch.read_bytes()).hexdigest()
        body = {
            key: value
            for key, value in event.items()
            if key != "event_sha256"
        }
        body["sequence"] = sequence
        body["previous_event_sha256"] = previous
        event.clear()
        event.update({**body, "event_sha256": p1.sha256_json(body)})
        previous = event["event_sha256"]
        raw_lines.append(p1.canonical_json_bytes(event) + b"\n")
    (run_dir / "calls.jsonl").write_bytes(b"".join(raw_lines))

    for index in range(0, len(events), 2):
        reserved = events[index]
        claim = {
            "call_key": reserved["call_key"],
            "request_sha256": reserved["request_sha256"],
            "max_cost_usd": reserved["max_cost_usd"],
            "run_genesis_sha256": reserved["run_genesis_sha256"],
        }
        claim_path = (
            run_dir
            / "calls.jsonl.claims"
            / f"{hashlib.sha256(reserved['call_key'].encode()).hexdigest()}.json"
        )
        _overwrite_canonical_json(claim_path, claim)

    for manifest in result["replica_receipts"]:
        receipt_path = run_dir / manifest["path"]
        manifest["sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    result["wal_head_sha256"] = previous
    result.pop("result_sha256", None)
    result["result_sha256"] = p1.sha256_json(result)
    _overwrite_canonical_json(run_dir / "result.json", result)


def test_offline_gate_rejects_resealed_call_wal_and_budget_drift(tmp_path):
    run_dir = tmp_path / "run"
    bundle, _initial_result = _materialize_complete_run(run_dir)
    originals = {
        path.relative_to(run_dir): path.read_bytes()
        for path in run_dir.rglob("*")
        if path.is_file()
    }
    first_replica_path = run_dir / "replicas" / "hp017_r1.json"

    cases = (
        ("embedding_model", "NO_GO_MODEL_DRIFT"),
        ("rerank_model", "NO_GO_MODEL_DRIFT"),
        ("rerank_envelope_model", "HOLD_RUN_ARTIFACT_DRIFT"),
        ("embedding_usage", "NO_GO_INPUT_TOKEN_BOUND_BREACH"),
        ("wal_actual", "HOLD_RESPONSE_RECEIPT_DRIFT"),
        ("wal_max", "HOLD_RUN_ARTIFACT_DRIFT"),
        ("wal_prior", "HOLD_RUN_ARTIFACT_DRIFT"),
        ("result_budget", "HOLD_RUN_ARTIFACT_DRIFT"),
    )
    for mutation, expected_code in cases:
        for relative, raw in originals.items():
            (run_dir / relative).write_bytes(raw)
        events = _load_wal_events(run_dir)
        result = p1.load_json_object(run_dir / "result.json")
        replica = p1.load_json_object(first_replica_path)
        recompute_accounting = False

        if mutation in {"embedding_model", "rerank_model", "embedding_usage"}:
            operation = mutation.split("_", 1)[0]
            call_key = f"hp017:r1:{operation}"
            completed = next(
                event
                for event in events
                if event["call_key"] == call_key
                and event["state"] == "COMPLETED"
            )
            response_path = run_dir / completed["response_path"]
            response = p1.load_json_object(response_path)
            if mutation.endswith("model"):
                response["model"] = "forged-model"
            else:
                spec = bundle.budget.specs[call_key]
                response["usage"]["input_tokens"] = spec.max_input_tokens + 1
                completed["actual_cost_usd"] = p1._money(
                    spec.observed_cost(response["usage"])
                )
                recompute_accounting = True
            _overwrite_canonical_json(response_path, response)
            observed = (
                replica["retrieval"]["embedding_receipt"]
                if operation == "embedding"
                else replica["rerank"]["receipt"]
            )
            observed.clear()
            observed.update(response)
            _overwrite_canonical_json(first_replica_path, replica)
        elif mutation == "rerank_envelope_model":
            call_key = "hp017:r1:rerank"
            envelope = replica["call_requests"]["rerank"]
            envelope["model"] = "forged-model"
            envelope["request"]["model"] = "forged-model"
            envelope["request"]["physical_payload"]["model"] = "forged-model"
            envelope["request"]["physical_payload_sha256"] = p1.sha256_json(
                envelope["request"]["physical_payload"]
            )
            request_sha = p1.sha256_json(envelope)
            for event in events:
                if event["call_key"] == call_key:
                    event["request_sha256"] = request_sha
            _overwrite_canonical_json(first_replica_path, replica)
        elif mutation == "wal_actual":
            completed = events[1]
            completed["actual_cost_usd"] = p1._money(
                p1._decimal(completed["actual_cost_usd"], field="test actual")
                + Decimal("0.0001")
            )
            recompute_accounting = True
        elif mutation == "wal_max":
            events[0]["max_cost_usd"] = "0.002"
            events[1]["max_cost_usd"] = "0.002"
        elif mutation == "wal_prior":
            events[2]["accumulated_prior_usd"] = "9"
        elif mutation == "result_budget":
            result["budget"]["observed_list_price_usd"] = "9"
        else:  # pragma: no cover - fixture misuse
            raise AssertionError(mutation)

        _reseal_complete_run_for_adversarial_test(
            run_dir,
            events,
            result,
            recompute_accounting=recompute_accounting,
        )
        with pytest.raises(p1.P1Error) as caught:
            p1.load_run_replicas(run_dir)
        assert caught.value.code == expected_code, mutation


def test_cli_score_rejects_weakened_caller_prereg_contract_selection(tmp_path):
    run_dir = tmp_path / "run"
    _materialize_complete_run(run_dir)
    weakened = p1.load_data_object(p1.CANONICAL_PREREG_PATH)
    weakened["sealed_inputs"]["fact_contract"]["payload_sha256"] = "0" * 64
    weakened_path = tmp_path / "weakened-prereg.json"
    p1.write_json_exclusive(weakened_path, weakened)

    with pytest.raises(p1.P1Error) as caught:
        p1._cli_score(
            p1.argparse.Namespace(
                run_dir=str(run_dir),
                prereg=str(weakened_path),
                output=str(tmp_path / "score.json"),
            )
        )

    assert caught.value.code == "HOLD_PREREG_DRIFT"


def test_finalize_rejects_tampered_authoritative_score(tmp_path):
    run_dir = tmp_path / "run"
    _materialize_complete_run(run_dir)
    score_path = tmp_path / "score.json"
    p1._cli_score(
        p1.argparse.Namespace(
            run_dir=str(run_dir),
            prereg=str(p1.CANONICAL_PREREG_PATH),
            output=str(score_path),
        )
    )
    score = p1.load_json_object(score_path)
    score["status"] = "PASS"
    score["decision"] = "PASS"
    tampered_path = tmp_path / "tampered-score.json"
    p1.write_json_exclusive(tampered_path, score)

    with pytest.raises(p1.P1Error) as caught:
        p1._finalize_after_verified_live_manifest(
            p1.argparse.Namespace(
                run_dir=str(run_dir),
                score=str(tampered_path),
                prereg=str(p1.CANONICAL_PREREG_PATH),
                fence_open_receipt=str(tmp_path / "not-read-open.json"),
                fence_close_receipt=str(tmp_path / "not-read-close.json"),
                adjudication=None,
                output=str(tmp_path / "final.json"),
            )
        )

    assert caught.value.code == "HOLD_SCORE_ARTIFACT_DRIFT"


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_score_rejects_missing_or_extra_physical_replica_receipt(tmp_path, mutation):
    run_dir = tmp_path / "run"
    _bundle_value, result = _materialize_complete_run(run_dir)
    if mutation == "missing":
        (run_dir / result["replica_receipts"][0]["path"]).unlink()
    else:
        p1.write_json_exclusive(
            run_dir / "replicas" / "unexpected.json",
            {"schema": p1.REPLICA_RECEIPT_SCHEMA, "replica_key": "extra:r1"},
        )

    with pytest.raises(p1.P1Error) as caught:
        p1._cli_score(
            p1.argparse.Namespace(
                run_dir=str(run_dir),
                prereg=str(p1.CANONICAL_PREREG_PATH),
                output=str(tmp_path / "score.json"),
            )
        )

    assert caught.value.code == "HOLD_RUN_ARTIFACT_DRIFT"


def test_finalize_rejects_score_bound_to_a_different_run(tmp_path):
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    _materialize_complete_run(run_a, at=NOW)
    _materialize_complete_run(run_b, at=NOW + timedelta(seconds=1))
    score_a = tmp_path / "score-a.json"
    p1._cli_score(
        p1.argparse.Namespace(
            run_dir=str(run_a),
            prereg=str(p1.CANONICAL_PREREG_PATH),
            output=str(score_a),
        )
    )

    with pytest.raises(p1.P1Error) as caught:
        p1._finalize_after_verified_live_manifest(
            p1.argparse.Namespace(
                run_dir=str(run_b),
                score=str(score_a),
                prereg=str(p1.CANONICAL_PREREG_PATH),
                fence_open_receipt=str(tmp_path / "not-read-open.json"),
                fence_close_receipt=str(tmp_path / "not-read-close.json"),
                adjudication=None,
                output=str(tmp_path / "final.json"),
            )
        )

    assert caught.value.code == "HOLD_SCORE_ARTIFACT_DRIFT"


def test_resealed_visual_and_renderer_drift_is_revalidated_by_every_offline_gate(
    tmp_path,
):
    run_dir = tmp_path / "run"
    bundle, result = _materialize_complete_run(run_dir)
    first_manifest = result["replica_receipts"][0]
    replica_path = run_dir / first_manifest["path"]
    receipt = p1.load_json_object(replica_path)
    receipt["visual_assets"]["status"] = "evaluated"
    receipt["visual_assets"]["rest_get_surface"] = [
        p1.VISUAL_REST_GET_SURFACE
    ]
    receipt["render"]["parts"] = ["renderer local re-sellado"]
    receipt["render"]["parts_sha256"] = p1.sha256_json(
        receipt["render"]["parts"]
    )
    receipt["render"]["message_parts"] = 1
    replica_path.write_bytes(p1.canonical_json_bytes(receipt) + b"\n")

    rewritten_result = p1.load_json_object(run_dir / "result.json")
    rewritten_result["replica_receipts"][0]["sha256"] = hashlib.sha256(
        replica_path.read_bytes()
    ).hexdigest()
    rewritten_result.pop("result_sha256")
    rewritten_result["result_sha256"] = p1.sha256_json(rewritten_result)
    (run_dir / "result.json").write_bytes(
        p1.canonical_json_bytes(rewritten_result) + b"\n"
    )

    with pytest.raises(p1.P1Error) as loaded:
        p1.load_run_replicas(run_dir)
    assert loaded.value.code == "NO_GO_VISUAL_SIDE_PATH_EXECUTED"

    suffix = hashlib.sha256(str(run_dir.resolve()).encode()).hexdigest()[:12]
    provider = _Provider()
    resumed = p1.P1Runner(
        bundle=bundle,
        permit=p1.ExecutionPermit(
            True,
            True,
            True,
            _authorization(
                bundle.release_config,
                bundle.prereg,
                run_dir,
                authorization_id=f"auth-p1-{suffix}",
                run_id=f"run-p1-{suffix}",
            ),
        ),
        artifacts=p1.ArtifactStore(run_dir),
        journal=p1.CallJournal(run_dir / "calls.jsonl", now=lambda: NOW),
        provider_adapter=provider,
        replica_adapter=_ReplicaAdapter(provider),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(run_dir),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )
    with pytest.raises(p1.P1Error) as resume:
        resumed.run()
    assert resume.value.code == "NO_GO_VISUAL_SIDE_PATH_EXECUTED"
    assert provider.prepares == provider.sends == []

    with pytest.raises(p1.P1Error) as score:
        p1._cli_score(
            p1.argparse.Namespace(
                run_dir=str(run_dir),
                prereg=str(p1.CANONICAL_PREREG_PATH),
                output=str(tmp_path / "score.json"),
            )
        )
    assert score.value.code == "NO_GO_VISUAL_SIDE_PATH_EXECUTED"

    with pytest.raises(p1.P1Error) as finalize:
        p1._finalize_after_verified_live_manifest(
            p1.argparse.Namespace(
                run_dir=str(run_dir),
                score=str(tmp_path / "not-read-score.json"),
                prereg=str(p1.CANONICAL_PREREG_PATH),
                fence_open_receipt=str(tmp_path / "not-read-open.json"),
                fence_close_receipt=str(tmp_path / "not-read-close.json"),
                adjudication=None,
                output=str(tmp_path / "final.json"),
            )
        )
    assert finalize.value.code == "NO_GO_VISUAL_SIDE_PATH_EXECUTED"


def _materialize_shadow_scoring_checkout(shadow_root: Path) -> None:
    for relative in p1.REQUIRED_IMPLEMENTATION_HASHES:
        source = p1.ROOT / relative
        target = shadow_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    prereg = p1.load_data_object(p1.CANONICAL_PREREG_PATH)
    for role in (
        "fact_contract",
        "model_extraction_receipt",
        "release_config_schema",
    ):
        relative = prereg["sealed_inputs"][role]["path"]
        source = p1.ROOT / relative
        target = shadow_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


def _assert_score_and_finalize_hold_before_scoring(
    run_dir: Path,
    output_root: Path,
    expected_code: str,
) -> None:
    with pytest.raises(p1.P1Error) as score:
        p1._cli_score(
            p1.argparse.Namespace(
                run_dir=str(run_dir),
                prereg=str(p1.CANONICAL_PREREG_PATH),
                output=str(output_root / "score.json"),
            )
        )
    assert score.value.code == expected_code
    with pytest.raises(p1.P1Error) as finalize:
        p1._finalize_after_verified_live_manifest(
            p1.argparse.Namespace(
                run_dir=str(run_dir),
                score=str(output_root / "not-read-score.json"),
                prereg=str(p1.CANONICAL_PREREG_PATH),
                fence_open_receipt=str(output_root / "not-read-open.json"),
                fence_close_receipt=str(output_root / "not-read-close.json"),
                adjudication=None,
                output=str(output_root / "final.json"),
            )
        )
    assert finalize.value.code == expected_code


def test_each_transitive_implementation_mutation_is_rejected(
    tmp_path, monkeypatch
):
    shadow_root = tmp_path / "shadow-checkout"
    _materialize_shadow_scoring_checkout(shadow_root)
    manifest = {
        relative: p1.sha256_file(shadow_root / relative, lf_normalized=True)
        for relative in p1.REQUIRED_IMPLEMENTATION_HASHES
    }
    monkeypatch.setattr(p1, "ROOT", shadow_root)

    for relative in p1.REQUIRED_IMPLEMENTATION_HASHES:
        path = shadow_root / relative
        original = path.read_bytes()
        path.write_bytes(original + b"\n# transitive implementation mutation\n")
        try:
            with pytest.raises(p1.P1Error) as caught:
                p1.verify_implementation_hashes(manifest)
            assert caught.value.code == "HOLD_IMPLEMENTATION_DRIFT", relative
        finally:
            path.write_bytes(original)


def test_static_closure_rejects_new_unsealed_local_import(
    tmp_path, monkeypatch
):
    shadow_root = tmp_path / "shadow-checkout"
    _materialize_shadow_scoring_checkout(shadow_root)
    unsealed_relative = "src/rag/deep_lookup.py"
    unsealed_source = p1.ROOT / unsealed_relative
    unsealed_target = shadow_root / unsealed_relative
    unsealed_target.parent.mkdir(parents=True, exist_ok=True)
    unsealed_target.write_bytes(unsealed_source.read_bytes())
    importer = shadow_root / p1.PRODUCT_ADAPTER_IMPLEMENTATION_PATH
    importer.write_bytes(importer.read_bytes() + b"\nimport src.rag.deep_lookup\n")
    manifest = {
        relative: p1.sha256_file(shadow_root / relative, lf_normalized=True)
        for relative in p1.REQUIRED_IMPLEMENTATION_HASHES
    }
    monkeypatch.setattr(p1, "ROOT", shadow_root)

    with pytest.raises(p1.P1Error) as caught:
        p1.verify_implementation_hashes(manifest)
    assert caught.value.code == "HOLD_IMPLEMENTATION_DRIFT"
    assert unsealed_relative in str(caught.value)


def test_score_and_finalize_reject_post_run_implementation_drift(
    tmp_path, monkeypatch
):
    run_dir = tmp_path / "run"
    _materialize_complete_run(run_dir)
    shadow_root = tmp_path / "shadow-checkout"
    _materialize_shadow_scoring_checkout(shadow_root)
    monkeypatch.setattr(p1, "ROOT", shadow_root)

    for relative in (
        "scripts/s277_c1_p1.py",
        p1.PRODUCT_ADAPTER_IMPLEMENTATION_PATH,
        "scripts/s277_c1_p1_scorer.py",
        "scripts/s270_etapa2_probe.py",
        "src/bot/response_formatter.py",
        "src/rag/answer_planner.py",
        "src/reingest/embed.py",
    ):
        path = shadow_root / relative
        original = path.read_bytes()
        path.write_bytes(original + b"\n# post-run implementation drift\n")
        _assert_score_and_finalize_hold_before_scoring(
            run_dir,
            tmp_path,
            "HOLD_IMPLEMENTATION_DRIFT",
        )
        path.write_bytes(original)


def test_score_and_finalize_reject_post_run_fact_contract_drift(
    tmp_path, monkeypatch
):
    run_dir = tmp_path / "run"
    _materialize_complete_run(run_dir)
    shadow_root = tmp_path / "shadow-checkout"
    _materialize_shadow_scoring_checkout(shadow_root)
    monkeypatch.setattr(p1, "ROOT", shadow_root)
    prereg = p1.load_data_object(p1.CANONICAL_PREREG_PATH)
    contract_path = shadow_root / prereg["sealed_inputs"]["fact_contract"]["path"]
    contract_path.write_bytes(contract_path.read_bytes() + b"\n")

    _assert_score_and_finalize_hold_before_scoring(
        run_dir,
        tmp_path,
        "HOLD_PREREG_DRIFT",
    )


def test_runner_materializes_no_go_partial_after_ambiguous_first_send(tmp_path):
    bundle, release, prereg = _bundle()
    provider = _SendFailure()
    artifacts = p1.ArtifactStore(tmp_path / "run")
    journal = p1.CallJournal(tmp_path / "run" / "calls.jsonl", now=lambda: NOW)
    runner = p1.P1Runner(
        bundle=bundle,
        permit=p1.ExecutionPermit(
            True, True, True, _authorization(release, prereg, artifacts.root)
        ),
        artifacts=artifacts,
        journal=journal,
        provider_adapter=provider,
        replica_adapter=_ReplicaAdapter(provider),
        fence_watcher=_Watcher(),
        authorization_claims=p1.AuthorizationClaimStore(artifacts.root),
        scorer=lambda _receipt: {"status": "PASS"},
        runtime_inspector=lambda: bundle.runtime_identity,
        now=lambda: NOW,
    )
    result = runner.run()
    assert result["status"] == "NO_GO_PARTIAL"
    assert result["code"] == "NO_GO_UNKNOWN_BILLED_POST_SEND"
    assert result["replicas_persisted"] == 0
    assert result["budget"]["unknown_reserved_usd"] == "0.001"
    assert provider.prepares == provider.sends == 1
    assert (tmp_path / "run" / "result.json").is_file()


def test_cli_plan_is_offline_and_cli_run_refuses_before_reading_paths(tmp_path):
    root = Path(__file__).resolve().parents[1]
    plan = subprocess.run(
        [sys.executable, str(root / "scripts/s277_c1_p1.py"), "plan"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert plan.returncode == 0
    assert json.loads(plan.stdout)["paid_model_calls"] == 0

    missing = tmp_path / "does-not-exist"
    command = [
        sys.executable,
        str(root / "scripts/s277_c1_p1.py"),
        "run",
        "--release-config", str(missing),
        "--prereg", str(missing),
        "--authorization-receipt", str(missing),
        "--credentials", str(missing),
        "--artifact-dir", str(tmp_path / "artifacts"),
        "--ipc-dir", str(missing),
        "--live-manifest-contract", str(missing),
        "--live-manifest-pre", str(missing),
        "--live-http-evidence", str(missing),
        "--postgrest-post-snapshot", str(missing),
    ]
    refused = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(root)},
    )
    assert refused.returncode == 2
    payload = json.loads(refused.stdout)
    assert payload["code"] == "HOLD_EXECUTE_OPT_IN_REQUIRED"
    assert payload["paid_model_calls"] == 0
    assert payload["railway_mutations"] == 0
    assert payload["supabase_mutations"] == 0

    stored = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/s277_c1_p1.py"),
            "score-stored-controls",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert stored.returncode == 0
    stored_payload = json.loads(stored.stdout)
    assert stored_payload["decision"] == "HOLD_PREPAID_KNOWN_CONFLICT_RISK"
    assert stored_payload["confirmed_3_of_3"] is True
    assert stored_payload["candidate_runtime_measured"] is False
    assert stored_payload["paid_model_calls"] == 0
    assert stored_payload["network_calls"] == 0


def test_product_and_live_fence_clis_are_wired_without_implementation_stopline():
    parser = p1.build_parser()
    run = parser.parse_args(
        [
            "run",
            "--execute",
            "--confirm-paid",
            "--release-config", "release.json",
            "--prereg", "prereg.yaml",
            "--authorization-receipt", "authorization.json",
            "--credentials", ".env",
            "--artifact-dir", "artifacts",
            "--ipc-dir", "ipc",
            "--live-manifest-contract", "contract.json",
            "--live-manifest-pre", "pre.json",
            "--live-http-evidence", "http.json",
            "--postgrest-post-snapshot", "post.json",
        ]
    )
    assert run.handler is p1._cli_run_product
    assert not hasattr(p1, "_cli_run_unwired")
    assert not hasattr(p1, "_enforce_materialized_live_fence_manifest_contract")

    fence_open = parser.parse_args(
        [
            "fence-open-verify",
            "--operator-receipt", "open.json",
            "--fingerprint-receipt", "fingerprint.json",
            "--release-config", "release.json",
            "--live-manifest-contract", "contract.json",
            "--live-manifest-pre", "pre.json",
        ]
    )
    assert fence_open.handler is p1._cli_fence_open
