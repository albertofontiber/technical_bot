"""Zero-cost C1 assembly gate over the production orchestration seam.

This deliberately proves component assembly, not live reachability or model
synthesis. It replays the sealed hp017 prefix and the two structural candidates
previously selected by S108, then runs the real selector, coverage attestation,
prompt construction, and must-preserve postcondition. Retrieval I/O and the
Anthropic transport are faked and socket connections are denied.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
FREEZE_SHA256 = "556490dd74056603b6b8f8c8d885c55820957761bbd6407bb1dcf8f533434498"
TARGET_ID = "d27b1a1b-69cd-4318-a459-f3c86eb757ba"
WARNING_LOGIC = "Al programar reglas de causa-efecto evite las lógicas contradictorias."
WARNING_TEST = (
    "Es de vital importancia probar rigurosamente todas las reglas durante la "
    "puesta en marcha del sistema para verificar que no haya conflictos lógicos "
    "entre ellas."
)
_PREFIX_HYDRATION = {
    "570d9951-e3a6-4c64-a927-e26b5e6db842": (
        "17d4b914-fa21-4b41-a928-bafe1846528a",
        "bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b",
        76,
    ),
    "7e34cb72-0183-488a-9aa3-fcc81b40f3ef": (
        "17d4b914-fa21-4b41-a928-bafe1846528a",
        "bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b",
        77,
    ),
    "ac308dbf-357e-4356-9049-1ccfcc6ff749": (
        "e2b44424-92bb-446d-bc05-3a66202399e1",
        "94ee76b62a2360102e7c88870052fb88e497948749ce6ece8066597f8f66230d",
        36,
    ),
    "3ef1b823-b62e-40d4-8a9a-ebac320f6414": (
        "e2b44424-92bb-446d-bc05-3a66202399e1",
        "94ee76b62a2360102e7c88870052fb88e497948749ce6ece8066597f8f66230d",
        13,
    ),
    "13bee205-9f2b-44ba-9891-37d77b5fa110": (
        "17d4b914-fa21-4b41-a928-bafe1846528a",
        "bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b",
        29,
    ),
    "f68b0586-ae54-4089-b286-ee8792834c3d": (
        "17d4b914-fa21-4b41-a928-bafe1846528a",
        "bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b",
        13,
    ),
    "e522c315-ef36-4830-ae62-cf6de8d2d0db": (
        "17d4b914-fa21-4b41-a928-bafe1846528a",
        "bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b",
        14,
    ),
    "51df7a51-4970-4cfc-8ef1-3771f480dd78": (
        "17d4b914-fa21-4b41-a928-bafe1846528a",
        "bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b",
        17,
    ),
    "bc1de145-c91e-4c98-8cf6-4d5d7946ec94": (
        "17d4b914-fa21-4b41-a928-bafe1846528a",
        "bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b",
        38,
    ),
    "9587cd83-e271-42b9-ba8f-dfd05ae94935": (
        "17d4b914-fa21-4b41-a928-bafe1846528a",
        "bcde98794ae968ac43ed5367be231cd5d70f15bc06135c50673360ebc271296b",
        54,
    ),
}

_PROFILE_OWNED_LEGACY_FLAGS = (
    "POST_RERANK_COVERAGE",
    "STRUCTURAL_NEIGHBOR_COVERAGE",
    "COVERAGE_MANDATORY_CALLOUT",
    "MP_MANDATORY_VERB_TRIGGER",
)
_ASSEMBLY_OFF_FLAGS = (
    "TABLE_PREAMBLE_CLOSURE",
    "CANONICAL_HYQ_COVERAGE",
    "COMPATIBILITY_BUNDLE_COVERAGE",
    "RERANK_POOL_COVERAGE",
    "STRUCTURAL_CASCADE_COVERAGE",
    "LOGICAL_RECORD_COVERAGE",
    "EVIDENCE_DERIVATION_OVERLAY",
    "VISUAL_ASSETS_REGISTRY",
    "DEDUP_REFERENCE_NAVIGATION",
    "R2_REPAIR_NAVIGATION",
    "STRUCTURAL_NEIGHBOR_SHADOW",
    "MP_HYBRID_DETECT",
    "MP_SERVED_BINDING",
    "MP_DEFLINE_EQ",
    "MP_STEM_BINDING",
    "MP_DISTINCTIVE_TOKEN",
)
_ASSEMBLY_FIXED_ENV = {
    "PYTHON_DOTENV_DISABLED": "1",
    "COVERAGE_RELEASE_PROFILE": "coverage_c1_v1",
    "MUST_PRESERVE_CONTRACT": "on",
    "ANSWER_OBLIGATION_PLANNER": "off",
    "GENERATOR_PROMPT_VARIANT": "base",
    "GENERATOR_SELECTION_BLOCK": "off",
    "GENERATOR_INCLUDE_CONTEXT": "0",
    "IDENTITY_RESOLVE": "off",
    "IDENTITY_RESOLVE_POLICY": "add",
    "IDENTITY_FETCH": "off",
    "CHUNKS_TABLE": "chunks_v2",
    "RERANKER_BACKEND": "llm",
    "MERGE_STRATEGY": "stamps",
    "RERANK_TOP_K": "10",
    "LLM_MAX_TOKENS": "3500",
}


class GateFailure(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def _configure_offline_profile() -> dict[str, object]:
    # Explicit candidate deployment, isolated from any developer .env legacy
    # switches. These placeholders are never used because all I/O is faked.
    for name in _PROFILE_OWNED_LEGACY_FLAGS:
        os.environ.pop(name, None)
    for name in _ASSEMBLY_OFF_FLAGS:
        os.environ[name] = "off"
    os.environ.update(_ASSEMBLY_FIXED_ENV)
    os.environ["ANTHROPIC_API_KEY"] = "offline-gate"
    os.environ["OPENAI_API_KEY"] = "offline-gate"
    os.environ["SUPABASE_URL"] = "https://offline-gate.invalid"
    os.environ["SUPABASE_KEY"] = "offline-gate"
    os.environ["SUPABASE_SERVICE_KEY"] = "offline-gate"
    os.environ["TELEGRAM_BOT_TOKEN"] = "offline-gate"
    return {
        "profile_owned_legacy_flags_present": sorted(
            name for name in _PROFILE_OWNED_LEGACY_FLAGS if name in os.environ
        ),
        "off_flags": {name: os.environ[name] for name in _ASSEMBLY_OFF_FLAGS},
        "fixed_values": {
            name: os.environ[name] for name in sorted(_ASSEMBLY_FIXED_ENV)
        },
    }


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in value if not unicodedata.combining(char)).casefold()


def _base_candidate(row: dict) -> dict:
    # Remove prior serving outputs from the freeze. The real selector and
    # attestation seam must recreate them during this run.
    rejected_prefixes = (
        "structural_neighbor_",
        "structured_",
        "coverage_",
        "served_",
        "post_rerank_",
        "mandatory_callout_",
        "local_semantic_",
        "retrieval_lane",
    )
    return {
        key: value
        for key, value in row.items()
        if not key.startswith(rejected_prefixes)
    }


def run_gate() -> dict[str, object]:
    assembly_environment = _configure_offline_profile()

    # Release checks must survive ``python -O`` and must prove, rather than
    # merely report, that the offline harness made no network connection.
    network_attempts = [0]

    def deny_socket_connect(event, _args):
        if event in {"socket.connect", "socket.connect_ex"}:
            network_attempts[0] += 1
            raise GateFailure("offline assembly gate attempted network access")

    sys.addaudithook(deny_socket_connect)

    # Imports intentionally happen after the complete boot environment exists.
    from src import config
    from src.bot.response_formatter import format_telegram_messages
    from src.rag import generator
    from src.rag.post_rerank_coverage import (
        coverage_context_content,
        has_exact_mandatory_callout_receipt,
    )
    from src.rag.runtime_trace import build_rag_serving_trace
    from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn

    config.validate_config(require_telegram=True, production=True)
    _require(
        config.COVERAGE_RELEASE_POLICY.profile == "coverage_c1_v1",
        "C1 release profile was not resolved",
    )

    raw_bytes = FREEZE.read_bytes()
    _require(
        hashlib.sha256(raw_bytes.replace(b"\r\n", b"\n")).hexdigest()
        == FREEZE_SHA256,
        "sealed S113 context freeze drifted",
    )
    payload = json.loads(raw_bytes.decode("utf-8"))
    row = next(item for item in payload["rows"] if item["qid"] == "hp017")
    _require(len(row["prefix_ids"]) == 10, "hp017 prefix is not ten rows")
    _require(len(row["context"]) == 14, "hp017 frozen context is not fourteen rows")

    prefix = [dict(item) for item in row["context"][:10]]
    neighbor_candidates = [_base_candidate(item) for item in row["context"][10:12]]
    _require(
        TARGET_ID in {item["id"] for item in neighbor_candidates},
        "known S108 target is absent from the assembly candidates",
    )

    replay_reads = 0

    def replay_fetcher(seeds, **_bounds):
        nonlocal replay_reads
        replay_reads += 1
        hydrated = []
        for seed in seeds:
            document_id, extraction_sha256, chunk_index = _PREFIX_HYDRATION[
                seed["id"]
            ]
            hydrated_seed = dict(seed)
            hydrated_seed.update(
                {
                    "document_id": document_id,
                    "extraction_sha256": extraction_sha256,
                    "chunk_index": chunk_index,
                }
            )
            hydrated.append(hydrated_seed)
        return hydrated, [dict(item) for item in neighbor_candidates], {
            "http_requests": 0
        }

    captured: dict[str, object] = {}
    fake_model_transports = 0

    class FakeMessages:
        def create(self, **request):
            nonlocal fake_model_transports
            fake_model_transports += 1
            captured["request"] = request
            return SimpleNamespace(
                content=[SimpleNamespace(text=captured["draft_answer"])],
                stop_reason="end_turn",
                usage=SimpleNamespace(input_tokens=100, output_tokens=40),
            )

    class FakeAnthropic:
        def __init__(self, **_kwargs):
            self.messages = FakeMessages()

    original_anthropic = generator.anthropic.Anthropic

    def generate(query, chunks, *, available_models=None):
        target_fragment = next(
            index for index, chunk in enumerate(chunks, start=1)
            if chunk.get("id") == TARGET_ID
        )
        captured["draft_answer"] = (
            "Para programar el retardo, configure la instrucción de entrada y la "
            "instrucción de salida de la regla de causa-efecto y verifique el "
            f"retardo [F{target_fragment}]."
        )
        generator.anthropic.Anthropic = FakeAnthropic
        try:
            return generator.generate_answer(
                query,
                chunks,
                available_models=available_models,
            )
        finally:
            generator.anthropic.Anthropic = original_anthropic

    result = execute_rag_turn(
        query=row["question"],
        query_for_retrieval=row["question"],
        target_models=["Pearl"],
        available_models=None,
        retrieval_top_k=50,
        rerank_top_k=10,
        adapters=RagServingAdapters(
            retrieve=lambda _query, **_kwargs: list(prefix),
            rerank=lambda _query, chunks, **_kwargs: list(chunks[:10]),
            observe_structural_shadow=lambda _query, _chunks: None,
            generate=generate,
            structural_fetcher=replay_fetcher,
        ),
    )

    served = result["chunks"]
    coverage_trace = result["coverage_trace"]
    _require(served[:10] == prefix, "protected prefix changed")
    target = next(chunk for chunk in served if chunk.get("id") == TARGET_ID)
    _require(len(served) > 10, "no structural row was appended")
    _require(coverage_trace["status"] == "appended", "coverage did not append")
    _require(
        coverage_trace["protected_prefix_equal"] is True,
        "coverage prefix receipt is false",
    )
    _require(bool(target.get("mandatory_callout_cards")), "target has no callout")
    _require(
        has_exact_mandatory_callout_receipt(target),
        "target callout does not have an exact receipt",
    )

    served_view = _fold(coverage_context_content(target))
    _require(_fold(WARNING_LOGIC) in served_view, "first warning is not served")
    _require(_fold(WARNING_TEST) in served_view, "second warning is not served")

    generation = result["generation"]
    request_text = captured["request"]["messages"][0]["content"]
    _require(_fold(WARNING_LOGIC) in _fold(request_text), "first warning missed prompt")
    _require(_fold(WARNING_TEST) in _fold(request_text), "second warning missed prompt")
    _require(
        _fold(WARNING_LOGIC) in _fold(generation["answer"]),
        "first cited warning was not preserved",
    )
    _require(
        _fold(WARNING_TEST) in _fold(generation["answer"]),
        "second cited warning was not preserved",
    )
    _require(
        generation["must_preserve_outcome"]["status"] == "evaluated",
        "must-preserve was not evaluated",
    )
    _require(
        generation["must_preserve"]["atoms_appended"] >= 2,
        "must-preserve did not append both warnings",
    )
    _require(
        generation["must_preserve"]["appendix_appended"] is True,
        "must-preserve appendix receipt is false",
    )

    # Negative control: current C1 is citation-bound. This prevents this gate
    # from being misread as evidence that the model will choose to cite F12.
    captured["draft_answer"] = "Respuesta provisional sin citas."
    generator.anthropic.Anthropic = FakeAnthropic
    try:
        uncited_generation = generator.generate_answer(
            row["question"],
            served,
            available_models=None,
        )
    finally:
        generator.anthropic.Anthropic = original_anthropic
    _require(
        _fold(WARNING_LOGIC) not in _fold(uncited_generation["answer"])
        and _fold(WARNING_TEST) not in _fold(uncited_generation["answer"]),
        "uncited negative control unexpectedly synthesized target warnings",
    )

    answer_parts = format_telegram_messages(generation["answer"])
    safe_trace = build_rag_serving_trace(
        coverage_trace=coverage_trace,
        served_chunks=served,
        must_preserve_trace=generation.get("must_preserve"),
        must_preserve_outcome=generation.get("must_preserve_outcome"),
        release_policy=config.COVERAGE_RELEASE_POLICY.safe_snapshot(),
        transport_parts=len(answer_parts),
    )
    safe_json = json.dumps(safe_trace, ensure_ascii=False, sort_keys=True)
    _require(TARGET_ID not in safe_json, "chunk identity leaked into telemetry")
    _require("997-671-005-3" not in safe_json, "manual identity leaked into telemetry")
    _require(
        safe_trace["coverage"]["mandatory_callout_cards"] >= 1,
        "telemetry has no revalidated callout receipt",
    )
    _require(
        safe_trace["must_preserve"]["atoms_appended"] >= 2,
        "telemetry has no must-preserve receipt",
    )
    _require(replay_reads == 1, "assembly fetcher was called an unexpected number of times")
    _require(network_attempts[0] == 0, "offline gate attempted external I/O")

    return {
        "gate": "PASS_C1_ASSEMBLY_OFFLINE",
        "profile": config.COVERAGE_RELEASE_POLICY.profile,
        "candidate_scope_rows": len(neighbor_candidates),
        "prefix_rows": 10,
        "served_rows": len(served),
        "target_fragment": next(
            index for index, chunk in enumerate(served, start=1)
            if chunk.get("id") == TARGET_ID
        ),
        "mandatory_callout_cards": safe_trace["coverage"][
            "mandatory_callout_cards"
        ],
        "atoms_appended": safe_trace["must_preserve"]["atoms_appended"],
        "transport_parts": len(answer_parts),
        "forced_target_citation": True,
        "uncited_negative_control_passed": True,
        "assembly_environment": assembly_environment,
        "proves_live_reachability": False,
        "proves_model_synthesis": False,
        "fake_model_transports": fake_model_transports,
        "external_http_requests": network_attempts[0],
        "database_writes": 0,
        "paid_model_calls": 0,
    }


def main() -> int:
    print(json.dumps(run_gate(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
