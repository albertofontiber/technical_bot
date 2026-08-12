"""Privacy-bounded telemetry for the live RAG serving path.

Raw coverage and must-preserve traces contain source/chunk identifiers.  This
module deliberately does not offer a generic serializer: it builds a new object
from a closed allowlist of booleans, counters, and controlled status tokens.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


TRACE_SCHEMA = "rag_serving_trace_v1"
TRACE_MAX_BYTES = 8192
_MAX_LANE_OUTCOMES = 8
_ALLOWED_PROFILES = frozenset(
    {"legacy", "off", "coverage_c1_v1", "coverage_c1_v2"}
)
_ALLOWED_COVERAGE_STATUSES = frozenset(
    {"disabled_or_not_applicable", "appended", "no_append", "error"}
)
_DOCUMENT_LOCAL_LANE_STATUSES = frozenset(
    {
        "selected",
        "no_validated_structural_anchor",
        "unverified_document_lineage",
        "ambiguous_document_identity",
        "lineage_identity_drift",
        "source_scope_overflow",
        "no_bounded_query_plan",
        "invalid_anchor_scope",
        "document_seed_not_found",
        "ambiguous_document_family",
        "unsupported_document_language",
        "active_revision_not_bound_to_anchor_blob",
        "document_scope_overflow",
        "invalid_revision_status",
        "ambiguous_active_revision",
        "branched_or_cyclic_revision_chain",
        "nonreciprocal_revision_chain",
        "incomplete_revision_chain",
        "no_authoritative_source_scope",
        "candidate_scope_mismatch",
        "combined_candidate_cap_exceeded",
        "candidate_cap_exceeded",
        "no_fts_candidates",
        "no_candidates",
        "fetched",
        "selector_pool_overflow",
        "no_query_aligned_candidate",
        "best_candidate_already_covered",
        "winner_scope_mismatch",
        "skipped_no_append_capacity",
        "skipped_no_served_structural_anchor",
        "skipped_no_exact_blob_anchor",
        "error",
    }
)
_ALLOWED_LANE_STATUSES = frozenset(
    {
        "selected",
        "selected_complete_relational_bundle",
        "no_validated_source_span",
        "no_exact_table_preamble",
        "no_pool_seed",
        "no_query_aligned_candidate",
        "no_complete_relational_bundle",
        "not_applicable",
        "not_applicable_or_pool_overflow",
        "no_canonical_candidates",
        "skipped_no_append_capacity",
        "skipped_no_served_pool_seed",
        "error",
    }
) | _DOCUMENT_LOCAL_LANE_STATUSES
_ALLOWED_MP_STATUSES = frozenset(
    {"disabled", "evaluated", "error", "not_available", "not_applicable"}
)
_ALLOWED_ERROR_TYPES = frozenset(
    {
        "Exception",
        "RuntimeError",
        "TypeError",
        "ValueError",
        "KeyError",
        "TimeoutError",
        "ReadTimeout",
        "ConnectTimeout",
        "ConnectError",   # s306 (sub-agente): DNS/conexión rechazada — el fallo de
                          # red más común tras timeout; sin él degradaba a OtherError
        "HTTPStatusError",
        "JSONDecodeError",
    }
)
_ALLOWED_LANES = frozenset(
    {
        "same_blob_structural_neighbor_coverage_v1",
        "same_blob_table_preamble_closure_v3",
        "canonical_document_hyq_coverage_v1",
        "canonical_compatibility_bundle_coverage_v2",
        "retrieval_pool_coverage_v1",
        "document_local_content_coverage_v1",
        "cascaded_structural_neighbor_coverage_v1",
    }
)
_ALLOWED_MP_REASONS = frozenset({"identity_unresolved"})
# (s306/#63) Canales de retrieval con fail-open registrable. Cerrado a los sitios
# reales del retriever (s289 el exterior, s306 los 3 interiores; s317/#72 fase 2
# añade CONTENT y DIVERSIFY — Sol r15 M5: sus fail-open eran INVISIBLES, y con
# reintentos el fallo que persiste es señal fuerte) — un canal nuevo exige tocar
# esta allowlist a la vez que su `except`, que es el punto: el trace jamás
# persiste strings libres.
_ALLOWED_CHANNELS = frozenset(
    {"VECTOR", "ENUNCIADOS", "HYQ_TABLE", "HYQ_HYDRATE", "CONTENT", "DIVERSIFY"}
)
_MAX_CHANNEL_FAILURES = 8
_ALLOWED_RENDER_STATUSES = frozenset(
    {"html", "plain_fallback", "empty_answer_fallback"}
)
_DOCUMENT_LOCAL_SEED_ROUTE_MAP = {
    "governed_source_contract": "governed",
    "protected_rerank_prefix": "prefix",
    "served_structural_append": "structural",
}
_ALLOWED_DOCUMENT_LOCAL_SEED_ROUTES = frozenset(
    {"none", "governed", "prefix", "structural", "mixed"}
)
_ALLOWED_DOCUMENT_LOCAL_SATISFACTION_ROUTES = frozenset(
    {"none", "coverage_append", "already_served"}
)
# (s316h — gate 1 del flip, DEC-203b) Sección `intent`: la decisión del lever
# INTENT_LLM (s316g) por turno. Tokens CERRADOS: la política solo produce
# compat/switch/None y el seam del transporte solo estampa sus estados —
# jamás cruza texto del técnico ni del modelo. `not_wired` (Sol r12 M1) es la
# marca de «nadie estampó»: solo el builder la produce, nunca el seam — así
# «flag OFF declarado» y «telemetría sin cablear» son distinguibles, la misma
# distinción que `measured` da a `retrieval` (s306) y `timings` (s315).
_ALLOWED_INTENT_STATUSES = frozenset(
    {"not_wired", "off", "not_invoked", "invoked", "construction_failed"}
)
_ALLOWED_INTENT_DECISIONS = frozenset({"none", "compat", "switch", "fail_open"})
# Timeout servido = 6 s con max_retries=0; 60 s ya es un colgado, no una medida.
_INTENT_LATENCY_MAX_MS = 60_000

# Used only by tests/audits; no value from these fields is ever copied.
SENSITIVE_RAW_KEYS = frozenset(
    {
        "query",
        "qid",
        "question",
        "answer",
        "expected_fact",
        "gold",
        "content",
        "quote",
        "source_file",
        "candidate_id",
        "selected_ids",
        "appended_ids",
        "resolved_ids",
        "cited_fragments",
        "document_id",
        "chunk_id",
    }
)


def _bounded_int(value: Any, *, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, min(value, maximum))


def _safe_enum(value: Any, allowed: frozenset[str], *, default: str) -> str:
    text = str(value or "")
    return text if text in allowed else default


def _safe_error_type(value: Any) -> str:
    return _safe_enum(value, _ALLOWED_ERROR_TYPES, default="OtherError")


_TIMING_STAGES = ("retrieve_ms", "rerank_ms", "coverage_ms", "generate_ms")
# Latencia por etapa acotada a 10 min: por encima es un colgado, no una medida.
_TIMING_MAX_MS = 600_000


def _timings_section(stage_timings: Mapping[str, Any] | None) -> dict[str, Any]:
    """Sección `timings` (s315/punto-1): desglose de latencia del turno.

    Mismo contrato tri-estado que `retrieval` (s306): `measured=false` = el caller
    no midió (ruta orchestrator, fakes de test) — distinguible de «midió y dio 0».
    Solo cruzan enteros acotados de una lista cerrada de etapas: nada de strings.
    """
    # `measured` exige las 4 etapas como int reales — un mapping parcial o con
    # tipos rotos NO puede disfrazarse de medida con ceros (hallazgo #8 del dúo
    # s315; la clase exacta que el tri-estado existe para eliminar).
    measured = isinstance(stage_timings, Mapping) and all(
        isinstance(stage_timings.get(stage), int)
        and not isinstance(stage_timings.get(stage), bool)
        for stage in _TIMING_STAGES
    )
    section: dict[str, Any] = {"measured": measured}
    for stage in _TIMING_STAGES:
        raw = stage_timings.get(stage) if measured else 0
        section[stage] = _bounded_int(raw, maximum=_TIMING_MAX_MS)
    return section


def _retrieval_section(retrieval_health: Mapping[str, Any] | None) -> dict[str, Any]:
    """Sección `retrieval` (s306/#63): fail-opens de canal del turno, acotados.

    Del seam del retriever solo cruzan TOKENS (canal + tipo de error, ambos de
    allowlist) — el `error` crudo (repr, puede llevar URL/payload) no entra en el
    trace PERSISTIDO (al log operacional sí va, como siempre desde s96/s289: ese
    perímetro es otro y es deliberado).

    `measured` (cross-model s306): exigir la sección no bastaba — un adapter sin
    el seam `_trace` producía lista vacía, indistinguible de «medido y sano», que
    era EXACTAMENTE la confusión del defecto #63 reapareciendo un nivel más
    arriba. Tres estados, los tres distinguibles: sin sección (imposible: clave
    requerida) / `measured=false` (seam no conectado) / `measured=true` + lista
    (medido; vacía = sano).
    """
    measured = isinstance(retrieval_health, Mapping)
    failures: list[dict[str, Any]] = []
    raw = retrieval_health.get("channel_failures") if measured else None
    if isinstance(raw, list):
        for item in raw[:_MAX_CHANNEL_FAILURES]:
            if not isinstance(item, Mapping):
                continue
            failures.append({
                "channel": _safe_enum(
                    item.get("channel"), _ALLOWED_CHANNELS,
                    default="unknown_channel",
                ),
                "error_type": _safe_error_type(item.get("error_type")),
            })
    return {"measured": measured, "channel_failures": failures}


def _intent_section(intent_obs: Mapping[str, Any] | None) -> dict[str, Any]:
    """Sección `intent` (s316h/DEC-203b, gate 1 del flip): el lever por turno.

    Mismo contrato de coherencia que el resto del esquema: `decision` y
    `latency_ms` solo existen (≠ none/0) cuando hubo invocación REAL — un estado
    off/not_invoked/construction_failed no puede disfrazar una decisión, y una
    invocación no puede colarse sin decisión (`fail_open` ES una decisión del
    seam: el clasificador devolvió None y la política siguió con carry).
    Un mapping ausente, vacío o roto degrada a "not_wired" (Sol r12 M1) — jamás
    a "off": un caller futuro que olvide cablear la telemetría no puede producir
    una fila indistinguible de «lever apagado de verdad».
    """
    if not isinstance(intent_obs, Mapping):
        return {"status": "not_wired", "decision": "none", "latency_ms": 0}
    status = _safe_enum(
        intent_obs.get("status"), _ALLOWED_INTENT_STATUSES, default="not_wired"
    )
    if status != "invoked":
        return {"status": status, "decision": "none", "latency_ms": 0}
    decision = _safe_enum(
        intent_obs.get("decision"),
        _ALLOWED_INTENT_DECISIONS - {"none"},
        default="fail_open",
    )
    return {
        "status": "invoked",
        "decision": decision,
        "latency_ms": _bounded_int(
            intent_obs.get("latency_ms"), maximum=_INTENT_LATENCY_MAX_MS
        ),
    }


def _selected_count(lane_trace: Mapping[str, Any]) -> int:
    for field in ("selected_ids", "selected_parent_ids"):
        selected = lane_trace.get(field)
        if isinstance(selected, list):
            return min(len(selected), 1000)
    return 0


def _document_local_seed_route(lane_trace: Mapping[str, Any]) -> str:
    sources = lane_trace.get("seed_sources")
    if not isinstance(sources, Mapping):
        return "none"
    routes = {
        _DOCUMENT_LOCAL_SEED_ROUTE_MAP[key]
        for key, value in sources.items()
        if key in _DOCUMENT_LOCAL_SEED_ROUTE_MAP
        and isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
    }
    if not routes:
        return "none"
    if len(routes) > 1:
        return "mixed"
    return next(iter(routes))


def _lane_outcomes(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    outcomes: list[dict[str, Any]] = []
    lanes = raw.get("lanes")
    if not isinstance(lanes, list):
        return outcomes
    for item in lanes[:_MAX_LANE_OUTCOMES]:
        if not isinstance(item, Mapping):
            continue
        lane = str(item.get("lane") or "")
        if lane not in _ALLOWED_LANES:
            lane = "unknown_lane"
        outcome: dict[str, Any] = {
            "lane": lane,
            "status": _safe_enum(
                item.get("status"), _ALLOWED_LANE_STATUSES, default="unknown"
            ),
            "selected_rows": _selected_count(item),
        }
        if item.get("error_type"):
            outcome["error_type"] = _safe_error_type(item.get("error_type"))
        if lane == "document_local_content_coverage_v1":
            outcome.update(
                {
                    "seed_route": _document_local_seed_route(item),
                    "seed_scopes": _bounded_int(
                        item.get("seed_scope_count"), maximum=2
                    ),
                    "seed_scopes_truncated": bool(
                        item.get("seed_scopes_truncated")
                    ),
                    "satisfaction_route": _safe_enum(
                        item.get("satisfaction_route"),
                        _ALLOWED_DOCUMENT_LOCAL_SATISFACTION_ROUTES,
                        default="none",
                    ),
                }
            )
        outcomes.append(outcome)
    return outcomes


def _mandatory_card_count(
    chunks: list[dict[str, Any]],
    coverage_trace: Mapping[str, Any],
    *,
    enabled: bool,
) -> int:
    """Count only exact, attested callouts that were appended and served."""
    if not enabled:
        return 0
    appended = coverage_trace.get("appended_ids")
    if not isinstance(appended, list):
        return 0
    appended_ids = {str(value) for value in appended if value}
    if not appended_ids:
        return 0

    # Import lazily to keep this privacy serializer independent at import time.
    from .post_rerank_coverage import (
        has_exact_mandatory_callout_receipt,
        is_validated_coverage_chunk,
    )

    count = 0
    for chunk in chunks[:100]:
        if (
            str(chunk.get("id") or "") not in appended_ids
            or not is_validated_coverage_chunk(chunk)
            or not has_exact_mandatory_callout_receipt(chunk)
        ):
            continue
        cards = chunk.get("mandatory_callout_cards")
        if isinstance(cards, list):
            count += min(len(cards), 4)
    return min(count, 100)


def _coverage_section(
    raw: Mapping[str, Any],
    chunks: list[dict[str, Any]],
    release_policy: Mapping[str, Any],
) -> dict[str, Any]:
    lane_outcomes = _lane_outcomes(raw)
    executed_lanes = [item["lane"] for item in lane_outcomes]
    configured_lanes: list[str] = []
    if (
        release_policy.get("structural_neighbor_coverage") is True
        and "same_blob_structural_neighbor_coverage_v1" not in configured_lanes
    ):
        configured_lanes.append("same_blob_structural_neighbor_coverage_v1")
    if release_policy.get("document_local_coverage") is True:
        configured_lanes.append("document_local_content_coverage_v1")

    appended = raw.get("appended_ids")
    section: dict[str, Any] = {
        "enabled": bool(raw.get("enabled")),
        "status": _safe_enum(
            raw.get("status"), _ALLOWED_COVERAGE_STATUSES, default="unknown"
        ),
        "configured_lanes": configured_lanes[:_MAX_LANE_OUTCOMES],
        "executed_lanes": executed_lanes[:_MAX_LANE_OUTCOMES],
        "prefix_rows": _bounded_int(raw.get("protected_prefix_rows")),
        "appended_rows": min(len(appended), 100) if isinstance(appended, list) else 0,
        "protected_prefix_equal": bool(raw.get("protected_prefix_equal")),
        "lane_outcomes": lane_outcomes,
        "mandatory_callout_enabled": bool(
            release_policy.get("coverage_mandatory_callout")
        ),
        "mandatory_callout_cards": _mandatory_card_count(
            chunks,
            raw,
            enabled=bool(release_policy.get("coverage_mandatory_callout")),
        ),
    }
    if raw.get("error_type"):
        section["error_type"] = _safe_error_type(raw.get("error_type"))
    return section


def _must_preserve_section(
    raw: Mapping[str, Any] | None,
    outcome: Mapping[str, Any] | None,
) -> dict[str, Any]:
    raw = raw if isinstance(raw, Mapping) else {}
    outcome = outcome if isinstance(outcome, Mapping) else {}
    status = _safe_enum(
        outcome.get("status"), _ALLOWED_MP_STATUSES, default="not_available"
    )
    section: dict[str, Any] = {
        "status": status,
        "identity_resolved": bool(raw.get("identity_resolved")),
        "cited_fragment_count": (
            min(len(raw.get("cited_fragments")), 100)
            if isinstance(raw.get("cited_fragments"), list)
            else 0
        ),
        "atoms_detected": _bounded_int(raw.get("atoms_detected")),
        "atoms_bound": _bounded_int(raw.get("atoms_bound")),
        "atoms_missing": _bounded_int(raw.get("atoms_missing")),
        "atoms_appended": _bounded_int(raw.get("atoms_appended")),
        "appendix_appended": bool(raw.get("appendix_appended")),
    }
    reason = str(raw.get("reason") or "")
    if reason in _ALLOWED_MP_REASONS:
        section["reason"] = reason
    if outcome.get("error_type"):
        section["error_type"] = _safe_error_type(outcome.get("error_type"))
    return section


def build_rag_serving_trace(
    *,
    coverage_trace: Mapping[str, Any] | None,
    served_chunks: list[dict[str, Any]],
    must_preserve_trace: Mapping[str, Any] | None,
    must_preserve_outcome: Mapping[str, Any] | None,
    release_policy: Mapping[str, Any],
    transport_parts: int,
    transport_status: str = "html",
    transport_error_type: str | None = None,
    retrieval_health: Mapping[str, Any] | None = None,
    stage_timings: Mapping[str, Any] | None = None,
    intent_obs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the only runtime trace shape allowed into ``query_logs``."""
    profile = _safe_enum(
        release_policy.get("profile"), _ALLOWED_PROFILES, default="unknown"
    )
    trace = {
        "schema": TRACE_SCHEMA,
        "release_profile": profile,
        "coverage": _coverage_section(
            coverage_trace if isinstance(coverage_trace, Mapping) else {},
            served_chunks,
            release_policy,
        ),
        "must_preserve": _must_preserve_section(
            must_preserve_trace,
            must_preserve_outcome,
        ),
        "retrieval": _retrieval_section(retrieval_health),
        "timings": _timings_section(stage_timings),
        "intent": _intent_section(intent_obs),
        "transport": {
            "message_parts": _bounded_int(transport_parts, maximum=100),
            "render_status": _safe_enum(
                transport_status,
                _ALLOWED_RENDER_STATUSES,
                default="plain_fallback",
            ),
        },
    }
    if transport_error_type:
        trace["transport"]["error_type"] = _safe_error_type(transport_error_type)
    encoded = json.dumps(
        trace, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if len(encoded) > TRACE_MAX_BYTES:
        raise RuntimeError("bounded RAG trace unexpectedly exceeds size contract")
    return trace


def _validate_rag_serving_trace(value: Any) -> dict[str, Any] | None:
    """Implement the closed-schema validation without trusting input types.

    This is the defense-in-depth boundary used by the database sink. A future
    caller cannot persist arbitrary JSON merely by bypassing the builder.
    """

    def exact_keys(
        item: Any,
        required: set[str],
        optional: set[str] | None = None,
    ) -> bool:
        if not isinstance(item, dict):
            return False
        keys = set(item)
        return required <= keys <= required | (optional or set())

    def safe_int(item: Any, maximum: int = 1_000_000) -> bool:
        return isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= maximum

    if not exact_keys(
        value,
        # `retrieval` es REQUERIDA (s306/#63), no opcional: si fuera opcional, un
        # builder futuro que la omitiera volvería a confundir «sin datos» con «sin
        # fallos» — la clase exacta que esta sección elimina. Solo el sink de
        # escritura valida (verificado): las filas históricas no se re-validan.
        # `timings` (s315) es REQUERIDA por la misma razón: tri-estado explícito.
        # `intent` (s316h) también: si fuera opcional, un builder que la omitiera
        # confundiría «lever apagado» con «telemetría no cableada» — la clase de
        # silencio que el gate 1 del flip existe para eliminar.
        {"schema", "release_profile", "coverage", "must_preserve", "retrieval",
         "timings", "transport", "intent"},
    ):
        return None
    retrieval = value["retrieval"]
    if not exact_keys(retrieval, {"measured", "channel_failures"}):
        return None
    timings = value["timings"]
    if not exact_keys(timings, {"measured", *_TIMING_STAGES}):
        return None
    if type(timings["measured"]) is not bool:
        return None
    if any(not safe_int(timings[stage], _TIMING_MAX_MS) for stage in _TIMING_STAGES):
        return None
    if type(retrieval["measured"]) is not bool:
        return None
    intent = value["intent"]
    if not exact_keys(intent, {"status", "decision", "latency_ms"}):
        return None
    if (
        intent["status"] not in _ALLOWED_INTENT_STATUSES
        or intent["decision"] not in _ALLOWED_INTENT_DECISIONS
        or not safe_int(intent["latency_ms"], _INTENT_LATENCY_MAX_MS)
    ):
        return None
    # Coherencia CERRADA (no advisory): sin invocación no hay decisión ni
    # latencia; con invocación la decisión es obligatoria (fail_open incluido).
    if intent["status"] != "invoked":
        if intent["decision"] != "none" or intent["latency_ms"] != 0:
            return None
    elif intent["decision"] == "none":
        return None
    channel_failures = retrieval["channel_failures"]
    if (
        not isinstance(channel_failures, list)
        or len(channel_failures) > _MAX_CHANNEL_FAILURES
    ):
        return None
    for failure in channel_failures:
        if not exact_keys(failure, {"channel", "error_type"}):
            return None
        if failure["channel"] not in (_ALLOWED_CHANNELS | {"unknown_channel"}):
            return None
        if failure["error_type"] not in (_ALLOWED_ERROR_TYPES | {"OtherError"}):
            return None
    if value["schema"] != TRACE_SCHEMA or value["release_profile"] not in (
        _ALLOWED_PROFILES | {"unknown"}
    ):
        return None

    coverage = value["coverage"]
    coverage_required = {
        "enabled",
        "status",
        "configured_lanes",
        "executed_lanes",
        "prefix_rows",
        "appended_rows",
        "protected_prefix_equal",
        "lane_outcomes",
        "mandatory_callout_enabled",
        "mandatory_callout_cards",
    }
    if not exact_keys(coverage, coverage_required, {"error_type"}):
        return None
    if (
        type(coverage["enabled"]) is not bool
        or coverage["status"] not in (_ALLOWED_COVERAGE_STATUSES | {"unknown"})
        or type(coverage["protected_prefix_equal"]) is not bool
        or type(coverage["mandatory_callout_enabled"]) is not bool
        or not safe_int(coverage["prefix_rows"])
        or not safe_int(coverage["appended_rows"], 100)
        or not safe_int(coverage["mandatory_callout_cards"], 100)
    ):
        return None
    for field in ("configured_lanes", "executed_lanes"):
        lanes = coverage[field]
        if (
            not isinstance(lanes, list)
            or len(lanes) > _MAX_LANE_OUTCOMES
            or any(lane not in (_ALLOWED_LANES | {"unknown_lane"}) for lane in lanes)
        ):
            return None
    outcomes = coverage["lane_outcomes"]
    if not isinstance(outcomes, list) or len(outcomes) > _MAX_LANE_OUTCOMES:
        return None
    for outcome in outcomes:
        base_keys = {"lane", "status", "selected_rows"}
        document_local_keys = {
            "seed_route",
            "seed_scopes",
            "seed_scopes_truncated",
            "satisfaction_route",
        }
        optional_keys = {"error_type"}
        if outcome.get("lane") == "document_local_content_coverage_v1":
            required_keys = base_keys | document_local_keys
        else:
            required_keys = base_keys
        if not exact_keys(outcome, required_keys, optional_keys):
            return None
        if (
            outcome["lane"] not in (_ALLOWED_LANES | {"unknown_lane"})
            or outcome["status"] not in (_ALLOWED_LANE_STATUSES | {"unknown"})
            or not safe_int(outcome["selected_rows"], 1000)
            or (
                "error_type" in outcome
                and outcome["error_type"] not in (_ALLOWED_ERROR_TYPES | {"OtherError"})
            )
        ):
            return None
        if outcome["lane"] == "document_local_content_coverage_v1" and (
            outcome["seed_route"] not in _ALLOWED_DOCUMENT_LOCAL_SEED_ROUTES
            or not safe_int(outcome["seed_scopes"], 2)
            or type(outcome["seed_scopes_truncated"]) is not bool
            or outcome["satisfaction_route"]
            not in _ALLOWED_DOCUMENT_LOCAL_SATISFACTION_ROUTES
        ):
            return None
    if "error_type" in coverage and coverage["error_type"] not in (
        _ALLOWED_ERROR_TYPES | {"OtherError"}
    ):
        return None

    must_preserve = value["must_preserve"]
    mp_required = {
        "status",
        "identity_resolved",
        "cited_fragment_count",
        "atoms_detected",
        "atoms_bound",
        "atoms_missing",
        "atoms_appended",
        "appendix_appended",
    }
    if not exact_keys(must_preserve, mp_required, {"reason", "error_type"}):
        return None
    if (
        must_preserve["status"] not in _ALLOWED_MP_STATUSES
        or type(must_preserve["identity_resolved"]) is not bool
        or type(must_preserve["appendix_appended"]) is not bool
        or any(
            not safe_int(must_preserve[field], 1_000_000)
            for field in (
                "cited_fragment_count",
                "atoms_detected",
                "atoms_bound",
                "atoms_missing",
                "atoms_appended",
            )
        )
        or (
            "reason" in must_preserve
            and must_preserve["reason"] not in _ALLOWED_MP_REASONS
        )
        or (
            "error_type" in must_preserve
            and must_preserve["error_type"] not in (_ALLOWED_ERROR_TYPES | {"OtherError"})
        )
    ):
        return None

    transport = value["transport"]
    if not exact_keys(transport, {"message_parts", "render_status"}, {"error_type"}):
        return None
    if (
        not safe_int(transport["message_parts"], 100)
        or transport["render_status"] not in _ALLOWED_RENDER_STATUSES
        or (
            "error_type" in transport
            and transport["error_type"] not in (_ALLOWED_ERROR_TYPES | {"OtherError"})
        )
    ):
        return None

    encoded = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if len(encoded) > TRACE_MAX_BYTES:
        return None
    return json.loads(encoded.decode("utf-8"))


def validate_rag_serving_trace(value: Any) -> dict[str, Any] | None:
    """Return a detached trace only when it matches the closed storage schema.

    Malformed caller input is treated as absent telemetry, never as a reason to
    lose the underlying query log.
    """
    try:
        return _validate_rag_serving_trace(value)
    except (TypeError, ValueError, OverflowError):
        return None
